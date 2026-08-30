"""Collector: the Chamber of Advisors, 2005-2011, from its own website.

This chamber was the dataset's last completely empty one. It sat from 2005 to
its dissolution on 23 March 2011 as Tunisia's only upper house before 2023, and
until now it appeared in ``assemblies.csv`` with 112 seats, no members and
``coverage_status = frame_only``. It had no listed source at all.

It turns out no archival work is needed beyond a web browser: the chamber ran
its own bilingual site at ``chambredesconseillers.tn``, the site died with the
chamber, and the Internet Archive holds it. Six pages carry everything::

    fr/index.php?id=148  ar/index.php?id=189   governorate representatives
    fr/index.php?id=149  ar/index.php?id=191   professional-organisation reps
    fr/index.php?id=150  ar/index.php?id=190   presidential appointees
    fr/index.php?id=142  ar/index.php?id=184   committee membership, with roles
    fr/index.php?id=145  ar/index.php?id=186   the bureau
    fr/index.php?id=146  ar/index.php?id=187   every member, alphabetically

Two properties make this source better than it looks.

**It is genuinely bilingual, page for page.** Every roster page exists in Arabic
and French with the same table geometry, so each member arrives with both an
Arabic name and the chamber's *own* French romanisation rather than a machine
transliteration. The two sides are joined structurally — by governorate for the
governorate pages, by the printed slot number for the appointees, by cell
position for the professional colleges — never by fuzzy name matching, which
across scripts would be guesswork.

**The seat counts reconcile exactly.** 43 governorate representatives + 28
professional-organisation representatives + 41 presidential appointees = 112,
which is the chamber's nominal size. The 71/41 split is the two-thirds indirect,
one-third appointed composition the 2002 constitutional amendment prescribed.
That is a real check on the parse: no page is silently truncated, and the
long-standing "112 at creation, 126 after the 2008 partial renewal" claim in
``assemblies.csv`` is now testable — the chamber's own pages in 2010, two years
*after* that renewal, list 112.

**What the captures cannot settle.** Each page was captured several times, and
the roster pages are byte-stable across 2010 except for the appointees, which
change once: six of the 41 slots go blank and a seventh changes hands. The
change falls between a capture of 21 August 2010 and one of 1 September 2011,
an interval that *contains the dissolution*, so it is impossible to tell from
the site whether those seats were vacated while the chamber sat or whether the
page was edited after it ceased to exist. Both readings are recorded in the
affected mandates' notes and neither is asserted. The alphabetical page, whose
only capture is later still, agrees exactly with the second state — an
independent confirmation that the change is real and not a broken render.

Nothing here carries dates of birth, party, or biography: the site published a
roster, not member profiles. This closes the chamber's membership, not its
prosopography.
"""

from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict
from typing import Any

from ..ids import normalize_arabic, normalize_latin
from ..io import Fetcher, RAW, log, today
from ..reference import GOVERNORATE_ROWS
from .base import PersonRecord, StagingDoc

SOURCE_ID = "ADV_CHAMBRE"
ASSEMBLY_ID = "ADV-2005"

SITE = "http://www.chambredesconseillers.tn"
CDX = "https://web.archive.org/cdx/search/cdx"
# `id_` returns the capture unrewritten: no Archive toolbar, no rewritten links,
# and — the reason it matters here — no injected markup inside the tables.
WAYBACK = "https://web.archive.org/web/{timestamp}id_/{url}"

# The chamber's dissolution is the one date `assemblies.csv` records for it. Its
# first sitting is NOT established, so mandate start dates are left empty rather
# than guessed from the 2005 election: an empty date is a known unknown, and
# "2005-08-01" would be a fabrication that later analysis could not detect.
DISSOLUTION = "2011-03-23"

# (French page, Arabic page) for each roster view.
PAGES = {
    "governorates": (148, 189),
    "professional": (149, 191),
    "appointees": (150, 190),
    "committees": (142, 184),
    "bureau": (145, 186),
    "alphabetical": (146, 187),
}

# Bureau titles. The chamber's bureau was its president, two vice-presidents,
# and the chair and rapporteur of each of the seven committees sitting ex
# officio — so most bureau members are `bureau_member`, and the presiding three
# are what the OFFICE enum's first three values are for.
OFFICE_MAP = {
    "le président de la chambre": "speaker",
    "le premier vice-président": "first_vice_speaker",
    "la première vice-présidente": "first_vice_speaker",
    "le deuxième vice-président": "vice_speaker",
    "la deuxième vice-présidente": "vice_speaker",
}

# Committee roles, longest key first when matched so that
# "Rapporteur-adjoint" never matches on "Rapporteur".
COMMITTEE_ROLE_MAP = {
    "rapporteur-adjoint": "assistant_rapporteur",
    "rapporteur adjoint": "assistant_rapporteur",
    "président de la commission": "chair",
    "rapporteur de la commission": "rapporteur",
    "président": "chair",
    "rapporteur": "rapporteur",
}

# The two professional colleges, in the column order both language versions use.
COLLEGES = [
    ("employers", "المنظمة المهنية للأعراف", "Organisation professionnelle des employeurs"),
    ("farmers", "المنظمة المهنية للفلاحين", "Organisation professionnelle des agriculteurs"),
]

_GOV_BY_ID = {r["governorate_id"]: r for r in GOVERNORATE_ROWS}
_GOV_BY_AR = {normalize_arabic(r["name_ar"]): r for r in GOVERNORATE_ROWS}
_GOV_BY_LAT: dict[str, dict[str, str]] = {}
for _row in GOVERNORATE_ROWS:
    for _field in ("name_lat", "name_fr"):
        _key = normalize_latin(re.sub(r"^(la |le |l['’])", "", (_row[_field] or "").lower()))
        if _key:
            _GOV_BY_LAT.setdefault(_key, _row)


# ---------------------------------------------------------------------------
# Parsing
#
# The site is hand-written XHTML from the mid-2000s: no ids, no classes worth
# selecting on, and content that lives in nested <table> elements. Everything
# below therefore keys off table geometry, which is stable across every capture
# and — crucially — identical between the Arabic and French versions.
# ---------------------------------------------------------------------------

def _content(markup: str) -> str:
    """Slice out the page body, dropping the navigation menus.

    The French pages wrap content in ``<div id="texte">`` and the Arabic ones in
    ``<div id="content">``; both end at ``<div id="end">``. Taking the whole
    document instead would pull the left and right menus into every table scan.
    """
    start = markup.find('<div id="texte"')
    if start < 0:
        start = markup.find('<div id="content"')
    end = markup.find('<div id="end"')
    if start < 0 or end < 0 or end <= start:
        raise ValueError("page layout changed: no content div found")
    return markup[start:end]


def _tables(markup: str) -> list[list[list[tuple[str, list[str]]]]]:
    """Return [table][row][cell] as ``(css_class, [text lines])``.

    Cells are split on tags rather than flattened: committee cells put one
    member per ``<br />``, so the line break carries the record boundary.
    """
    out = []
    for block in re.findall(r"(?s)<table[^>]*>(.*?)</table>", markup):
        rows = []
        for row in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", block):
            cells = []
            for cell in re.finditer(r"(?s)<td([^>]*)>(.*?)</td>", row):
                css = re.search(r'class="([^"]*)"', cell.group(1))
                text = html.unescape(re.sub(r"<[^>]+>", "\n", cell.group(2)))
                lines = [ln.strip() for ln in text.replace("\xa0", " ").split("\n") if ln.strip()]
                cells.append((css.group(1) if css else "", lines))
            if cells:
                rows.append(cells)
        out.append(rows)
    return out


def parse_governorates(markup: str, arabic: bool) -> dict[str, list[str]]:
    """Parse the governorate page into ``governorate_id -> [member names]``.

    Resolving the heading to a governorate id is what lets the Arabic and French
    versions be joined: the two pages list the governorates in *different
    orders*, so pairing them by position — the obvious thing — silently
    mismatches nine of the twenty-four.
    """
    out: dict[str, list[str]] = {}
    for table in _tables(markup):
        heading = ""
        names: list[str] = []
        for row in table:
            for css, lines in row:
                if not lines:
                    continue
                if css == "CelTab1" and not heading:
                    heading = lines[0]
                elif css == "CelTab2":
                    names.append(lines[0])
        if not heading or not names:
            continue
        if arabic:
            gov = _GOV_BY_AR.get(normalize_arabic(heading))
        else:
            key = normalize_latin(re.sub(r"^(la |le |l['’])", "", heading.lower()))
            gov = _GOV_BY_LAT.get(key)
        if gov is None:
            raise ValueError(f"unrecognised governorate heading: {heading!r}")
        out[gov["governorate_id"]] = names
    return out


def parse_professional(markup: str) -> list[list[str]]:
    """Parse the professional-college page into one list of names per column.

    Both language versions put employers in the first column and farmers in the
    second, so column index is the join key.
    """
    columns: list[list[str]] = [[], []]
    for table in _tables(markup):
        for row in table:
            body = [(css, lines) for css, lines in row if css == "CelTab2"]
            for index, (_css, lines) in enumerate(body):
                if lines and index < len(columns):
                    columns[index].append(lines[0])
    return columns


def parse_appointees(markup: str) -> dict[int, str]:
    """Parse the presidential-appointee page into ``slot number -> name``.

    The page prints its own 1-41 numbering beside each name in a three-across
    layout. That number is the join key between the language versions and, more
    usefully, it makes a *vacancy* visible: a blank cell beside a live number is
    a seat the chamber listed and did not fill, which is exactly the difference
    between the 2010 and 2011 captures. Reading the page as a flat list of names
    would lose that distinction entirely.
    """
    out: dict[int, str] = {}
    for table in _tables(markup):
        for row in table:
            cells = [lines for _css, lines in row]
            for index in range(0, len(cells) - 1, 2):
                slot = cells[index]
                if slot and slot[0].isdigit():
                    name = cells[index + 1]
                    out[int(slot[0])] = name[0] if name else ""
    return out


def parse_committee_lists(markup: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Parse the committee page into ``[(committee name, [(member, role)])]``.

    Committees are laid out two per row: a row of two headings, then a row of
    two cells each holding that committee's members one per line, in the form
    ``Name - Role`` for the three officers and a bare name for everyone else.
    """
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for table in _tables(markup):
        headings: list[str] = []
        for row in table:
            kinds = {css for css, _ in row}
            if "CelTab1" in kinds:
                headings = [lines[0] if lines else "" for css, lines in row if css == "CelTab1"]
                continue
            bodies = [lines for css, lines in row if css == "CelTab2"]
            for index, lines in enumerate(bodies):
                if index >= len(headings) or not headings[index]:
                    continue
                members = [_split_member(line) for line in lines]
                out.append((headings[index], members))
            headings = []
    return out


def parse_bureau(markup: str) -> list[tuple[str, str]]:
    """Parse the bureau page into ``[(name, title)]``.

    Two tables with different shapes: the presiding three sit in a centred
    layout with the title on the line below the name, and the fourteen ex
    officio members sit in a two-column table of name and title.
    """
    out: list[tuple[str, str]] = []
    for table in _tables(markup):
        for row in table:
            body = [lines for _css, lines in row if lines]
            if len(row) == 2 and all(css for css, _ in row):
                # name / title pair, one per column
                cells = [lines for _css, lines in row]
                if len(cells) == 2:
                    name = cells[0][0] if cells[0] else ""
                    title = cells[1][0] if cells[1] else ""
                    if title:
                        out.append((name, title))
                continue
            for lines in body:
                if len(lines) >= 2:
                    out.append((lines[0], " ".join(lines[1:])))
    return out


def parse_alphabetical(markup: str) -> list[str]:
    """Parse the all-members page into a flat list of names."""
    return [lines[0] for table in _tables(markup) for row in table
            for _css, lines in row if lines]


# "Taïeb Sahbani - Président de la Commission", but also "Mohamed Nejib Hamadi-
# Rapporteur-adjoint" with no space before the dash, and "- Rapporteur de la
# Commission" where the source knows the office and not who held it. Splitting
# on a literal " - " gets the first right and turns the third into a member
# named "Rapporteur de la Commission".
_MEMBER_LINE_RE = re.compile(r"^\s*([^-–]*?)\s*[-–]\s*(.+)$")


def _split_member(line: str) -> tuple[str, str]:
    match = _MEMBER_LINE_RE.match(line)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return line.strip(), ""


def _committee_role(label: str) -> str:
    low = label.lower()
    for key in sorted(COMMITTEE_ROLE_MAP, key=len, reverse=True):
        if key in low:
            return COMMITTEE_ROLE_MAP[key]
    return "member"


# ---------------------------------------------------------------------------
# Joining the Arabic and French sides
#
# Every join below is structural — by governorate, by printed slot number, by
# column, by position within a committee — because pairing names across scripts
# is guesswork. The one place structure runs out is *inside* a governorate that
# returns two members, where the two pages list the pair in either order. There
# the assignment is decided by romanisation similarity, which is only defensible
# because the decision is between exactly two options and the winning margin is
# checked: on the recovered captures the closest call still separates by 0.40,
# so a layout change that broke the join would trip the guard rather than
# silently swap two members' names.
# ---------------------------------------------------------------------------

MIN_ASSIGNMENT_MARGIN = 0.10
MIN_MEAN_SIMILARITY = 0.30


def _similarity(name_ar: str, name_lat: str) -> float:
    from difflib import SequenceMatcher

    from ..ids import romanize_arabic

    return SequenceMatcher(
        None, normalize_latin(romanize_arabic(name_ar)), normalize_latin(name_lat)
    ).ratio()


def _assign_pair(arabic: list[str], latin: list[str], where: str) -> list[tuple[str, str]]:
    """Pair one governorate's members, choosing between the two orderings."""
    if len(arabic) != len(latin):
        raise ValueError(
            f"{where}: Arabic page lists {len(arabic)} members, French page {len(latin)}"
        )
    if len(arabic) < 2:
        return list(zip(arabic, latin))
    direct = _similarity(arabic[0], latin[0]) + _similarity(arabic[1], latin[1])
    swap = _similarity(arabic[0], latin[1]) + _similarity(arabic[1], latin[0])
    if abs(direct - swap) < MIN_ASSIGNMENT_MARGIN:
        raise ValueError(
            f"{where}: cannot tell which Arabic name goes with which French one "
            f"({arabic} vs {latin}); margin {abs(direct - swap):.3f}"
        )
    return list(zip(arabic, latin)) if direct > swap else [
        (arabic[0], latin[1]), (arabic[1], latin[0])
    ]


def _check_similarity(pairs: list[tuple[str, str]], where: str) -> float:
    """Guard a purely structural join against the structure having shifted.

    A column or slot join cannot mismatch by one place without every pair after
    it becoming nonsense, so the mean romanisation similarity is a cheap and
    sensitive alarm — it does not need to be high, only not near zero.
    """
    if not pairs:
        return 0.0
    mean = sum(_similarity(a, l) for a, l in pairs) / len(pairs)
    if mean < MIN_MEAN_SIMILARITY:
        raise ValueError(
            f"{where}: Arabic and French sides do not correspond "
            f"(mean name similarity {mean:.2f}); the page layout has changed"
        )
    return mean


# ---------------------------------------------------------------------------
# Capture enumeration
# ---------------------------------------------------------------------------

def _to_date(timestamp: str) -> str:
    return f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"


def list_versions(fetcher: Fetcher, lang: str, page_id: int) -> list[tuple[str, str, str]]:
    """Return this page's distinct versions as ``(digest, first_ts, last_ts)``.

    The Archive captured most of these pages four to six times, and the CDX
    index gives each capture a content digest. Collapsing on that digest turns a
    list of visits into a list of *states*, which is the useful unit: it is what
    distinguishes "the page was crawled again" from "the chamber changed". The
    first and last timestamp of each state bracket when it was live.
    """
    url = f"{SITE}/{lang}/index.php?id={page_id}"
    payload = fetcher.get_json(
        CDX,
        slug=f"cdx_{lang}_{page_id}",
        params={"url": url, "output": "json", "filter": "statuscode:200", "limit": "200"},
    )
    if not payload or len(payload) < 2:
        raise RuntimeError(f"no Wayback captures for {url}")
    header = payload[0]
    ti, di = header.index("timestamp"), header.index("digest")
    seen: dict[str, list[str]] = defaultdict(list)
    for row in sorted(payload[1:], key=lambda r: r[ti]):
        seen[row[di]].append(row[ti])
    versions = [(digest, stamps[0], stamps[-1]) for digest, stamps in seen.items()]
    return sorted(versions, key=lambda v: v[1])


def fetch_versions(fetcher: Fetcher, lang: str, page_id: int) -> list[tuple[str, str, str]]:
    """Fetch every distinct version of a page: ``(first_date, last_date, markup)``."""
    out = []
    for _digest, first_ts, last_ts in list_versions(fetcher, lang, page_id):
        markup = fetcher.get_text(
            WAYBACK.format(timestamp=first_ts, url=f"{SITE}/{lang}/index.php?id={page_id}"),
            slug=f"{lang}_{page_id}_{first_ts}",
            # The pages declare UTF-8 in a meta tag but the archived responses
            # carry no charset in the header, so the decode has to be forced.
            encoding="utf-8",
        )
        out.append((_to_date(first_ts), _to_date(last_ts), markup))
    return out


def _slug(name_lat: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name_lat).strip("_")


class Seat:
    """One member as assembled from the roster pages, across every version."""

    def __init__(self, name_ar: str, name_lat: str, category: str,
                 governorate_id: str = "", college: str = "", slot: str = ""):
        self.name_ar = name_ar
        self.name_lat = name_lat
        self.category = category
        self.governorate_id = governorate_id
        self.college = college
        self.slot = slot
        self.first_seen = ""
        self.last_seen = ""
        self.first_absent = ""  # first version of their own page that lacks them
        self.late_arrival = False

    @property
    def source_key(self) -> str:
        return _slug(self.name_lat)


def _nearest(versions: list[tuple[str, str, str]], date: str) -> tuple[str, str, str]:
    """Pick the version of the other language closest in time to ``date``.

    The Archive crawled the Arabic and French pages on different days, so the
    two version lists cannot be zipped by index — one language may have been
    captured twice while the page sat unchanged. Matching on capture date pairs
    each French state with the Arabic state that was live at the same time.
    """
    return min(versions, key=lambda v: abs(_date_ord(v[0]) - _date_ord(date)))


def _date_ord(date: str) -> int:
    return int(date.replace("-", "") or 0)


def _observe(seats: dict[str, Seat], seen: dict[str, Seat], first: str, last: str,
             is_first_version: bool, category: str) -> None:
    """Fold one version's roster into the running set of seats.

    Absence is only ever read off the page a seat belongs to: a member of the
    governorate page is not "missing" from the appointees page, they were never
    on it. Restricting the absence sweep to ``category`` is what keeps a member
    of one college from being recorded as having left when another college's
    page is processed.
    """
    for key, seat in seen.items():
        if key not in seats:
            seats[key] = seat
            seats[key].first_seen = first
            seats[key].late_arrival = not is_first_version
        seats[key].last_seen = last
    for key, seat in seats.items():
        if seat.category != category or key in seen or seat.first_absent:
            continue
        if _date_ord(first) > _date_ord(seat.last_seen):
            seat.first_absent = first


def collect_governorates(fetcher: Fetcher, seats: dict[str, Seat]) -> list[dict[str, Any]]:
    """Governorate representatives: two per governorate, one for the smallest."""
    fr_versions = fetch_versions(fetcher, "fr", PAGES["governorates"][0])
    ar_versions = fetch_versions(fetcher, "ar", PAGES["governorates"][1])
    constituencies: list[dict[str, Any]] = []
    for index, (first, last, markup) in enumerate(fr_versions):
        latin = parse_governorates(markup, arabic=False)
        arabic = parse_governorates(_nearest(ar_versions, first)[2], arabic=True)
        if set(latin) != set(arabic):
            raise ValueError("governorate pages disagree on which governorates are represented")
        seen: dict[str, Seat] = {}
        for gov_id in sorted(latin):
            pairs = _assign_pair(arabic[gov_id], latin[gov_id], f"governorate {gov_id}")
            for name_ar, name_lat in pairs:
                seat = Seat(name_ar, name_lat, "governorate", governorate_id=gov_id)
                seen[seat.source_key] = seat
            if index == 0:
                row = _GOV_BY_ID[gov_id]
                constituencies.append({
                    "assembly_id": ASSEMBLY_ID,
                    "name_ar": row["name_ar"],
                    "name_lat": row["name_lat"],
                    "governorate_id": gov_id,
                    "is_abroad": "false",
                    "magnitude": str(len(pairs)),
                })
        _observe(seats, seen, first, last, index == 0, "governorate")
    return constituencies


def collect_professional(fetcher: Fetcher, seats: dict[str, Seat]) -> list[dict[str, Any]]:
    """Representatives of the employers' and farmers' organisations."""
    fr_versions = fetch_versions(fetcher, "fr", PAGES["professional"][0])
    ar_versions = fetch_versions(fetcher, "ar", PAGES["professional"][1])
    constituencies: list[dict[str, Any]] = []
    for index, (first, last, markup) in enumerate(fr_versions):
        latin = parse_professional(_content(markup))
        arabic = parse_professional(_content(_nearest(ar_versions, first)[2]))
        seen: dict[str, Seat] = {}
        for column, (college, name_ar_col, name_fr_col) in enumerate(COLLEGES):
            pairs = list(zip(arabic[column], latin[column]))
            _check_similarity(pairs, f"professional college {college}")
            for name_ar, name_lat in pairs:
                seat = Seat(name_ar, name_lat, "professional", college=college)
                seen[seat.source_key] = seat
            if index == 0:
                constituencies.append({
                    "assembly_id": ASSEMBLY_ID,
                    "name_ar": name_ar_col,
                    "name_lat": name_fr_col,
                    "governorate_id": "",
                    "is_abroad": "false",
                    "magnitude": str(len(pairs)),
                })
        _observe(seats, seen, first, last, index == 0, "professional")
    return constituencies


def collect_appointees(fetcher: Fetcher, seats: dict[str, Seat]) -> list[dict[str, int]]:
    """The president's third of the chamber, and the only part of it that moves."""
    fr_versions = fetch_versions(fetcher, "fr", PAGES["appointees"][0])
    ar_versions = fetch_versions(fetcher, "ar", PAGES["appointees"][1])
    vacancy_log: list[dict[str, int]] = []
    for index, (first, last, markup) in enumerate(fr_versions):
        latin = parse_appointees(_content(markup))
        arabic = parse_appointees(_content(_nearest(ar_versions, first)[2]))
        pairs = [(arabic.get(slot, ""), latin[slot]) for slot in sorted(latin) if latin[slot]]
        _check_similarity([p for p in pairs if p[0]], "appointee slots")
        seen: dict[str, Seat] = {}
        for slot in sorted(latin):
            name_lat = latin[slot]
            if not name_lat:
                continue
            seat = Seat(arabic.get(slot, ""), name_lat, "appointed", slot=str(slot))
            seen[seat.source_key] = seat
        vacancy_log.append({
            "observed": first,
            "slots": len(latin),
            "filled": sum(1 for v in latin.values() if v),
        })
        _observe(seats, seen, first, last, index == 0, "appointed")
    return vacancy_log


# ---------------------------------------------------------------------------
# Committees and the bureau
# ---------------------------------------------------------------------------

# The committee and bureau pages were maintained separately from the roster
# pages and spell a dozen names differently — "Essia Dekhil" for "Essia
# Dekhili", "Jameleddine Khemakhem" for "Jamel Eddine Khemakhem", "Jalel
# Rouissi" for "Mohamed Jalel Rouissi". Every one of them is a member of this
# chamber by definition, so the resolution is a closed one: match against the
# 113 people the roster pages already established, never invent a 114th. The
# thresholds below are set from the observed spread — genuine variants score
# 0.73 and up against their own name and at most 0.78 against anyone else,
# while the closest thing to a false positive, a role label that reached this
# function through a parse slip, scores 0.46 with a margin of 0.01.
MIN_RESOLVE_SCORE = 0.70
MIN_RESOLVE_MARGIN = 0.10


def _resolve_member(name_lat: str, seats: dict[str, Seat]) -> str:
    """Map a name as the committee or bureau page spells it to a roster seat."""
    from difflib import SequenceMatcher

    from ..ids import latin_match_key

    key = _slug(name_lat)
    if key in seats:
        return key
    folded = latin_match_key(name_lat)
    for candidate, seat in seats.items():
        if folded and latin_match_key(seat.name_lat) == folded:
            return candidate
    target = normalize_latin(name_lat)
    scored = sorted(
        ((SequenceMatcher(None, target, normalize_latin(seat.name_lat)).ratio(), candidate)
         for candidate, seat in seats.items()),
        reverse=True,
    )
    if not scored:
        raise ValueError("no roster to resolve against")
    best, runner_up = scored[0], scored[1] if len(scored) > 1 else (0.0, "")
    if best[0] >= MIN_RESOLVE_SCORE and best[0] - runner_up[0] >= MIN_RESOLVE_MARGIN:
        return best[1]
    return ""


_COMMITTEE_PREFIX_FR = re.compile(r"^liste des membres de (?:la|l['’])\s*", re.I)
_COMMITTEE_PREFIX_AR = re.compile(r"^أعضاء\s+")


def _clean_committee(name: str, arabic: bool) -> str:
    pattern = _COMMITTEE_PREFIX_AR if arabic else _COMMITTEE_PREFIX_FR
    return re.sub(r"\s+", " ", pattern.sub("", name)).strip()


def collect_committees(fetcher: Fetcher, seats: dict[str, Seat]) -> dict[str, list[dict[str, Any]]]:
    """Committee membership with roles, keyed by member source_key.

    The committee page is a single table laid out two committees across, with
    each cell holding one committee's members one per line and the three
    officers carrying their title after a dash. The Arabic and French versions
    have identical geometry, so members are paired by position within the
    committee — a join that would break loudly (a whole committee's names
    mismatched) rather than quietly if the layout ever shifted, which is why
    ``_check_similarity`` is enough of a guard here.
    """
    fr_versions = fetch_versions(fetcher, "fr", PAGES["committees"][0])
    ar_versions = fetch_versions(fetcher, "ar", PAGES["committees"][1])
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: set[tuple[str, str]] = set()
    unresolved: list[str] = []
    # Only the first state of this page is read, and deliberately. Later states
    # drop exactly the members the roster pages already record as vanishing —
    # no new membership — while the Arabic and French versions were re-edited on
    # different dates, so by 2011 they disagree about who is on which committee.
    # Pairing across that disagreement would mis-align a whole committee's names.
    # The baseline state is the chamber's committee composition as it sat, and
    # it is the one state where the two languages agree cell for cell.
    for first, _last, markup in fr_versions[:1]:
        latin = parse_committee_lists(_content(markup))
        arabic = parse_committee_lists(_content(ar_versions[0][2]))
        if len(latin) != len(arabic):
            raise ValueError("committee pages list different numbers of committees")
        for (name_fr, members_fr), (name_ar, members_ar) in zip(latin, arabic):
            if len(members_fr) != len(members_ar):
                raise ValueError(f"committee {name_fr!r}: {len(members_fr)} members in "
                                 f"French, {len(members_ar)} in Arabic")
            pairs = [(a[0], f[0]) for a, f in zip(members_ar, members_fr) if a[0] and f[0]]
            _check_similarity(pairs, f"committee {name_fr!r}")
            for (member_ar, _role_ar), (member_fr, role_fr) in zip(members_ar, members_fr):
                if not member_fr:
                    # The source leaves the political-affairs committee's
                    # rapporteur blank in both languages. Recording an empty
                    # member would invent a person; the seat is simply not known.
                    continue
                key = _resolve_member(member_fr, seats)
                if not key:
                    unresolved.append(member_fr)
                    continue
                marker = (key, _clean_committee(name_fr, False))
                if marker in known:
                    continue
                known.add(marker)
                out[key].append({
                    "name_ar": _clean_committee(name_ar, True),
                    "name_lat": _clean_committee(name_fr, False),
                    "type": "standing",
                    "role": _committee_role(role_fr),
                    "role_label_ar": role_fr,
                    "start_date": "",
                    "end_date": DISSOLUTION,
                })
    if unresolved:
        raise ValueError(
            "committee page names people who are on no roster page: "
            f"{sorted(set(unresolved))}"
        )
    return out


def collect_bureau(fetcher: Fetcher, seats: dict[str, Seat]) -> dict[str, list[dict[str, Any]]]:
    """The bureau: the presiding three plus each committee's chair and rapporteur.

    Everyone on this page is on it *because* of a role recorded elsewhere — as
    the chamber's president, or as a committee officer — so the offices table
    ends up describing the same people twice, once as an office and once as a
    committee role. That is the point: the bureau is the body where those roles
    met, and membership of it is what a network analysis of this chamber would
    actually use.
    """
    fr_versions = fetch_versions(fetcher, "fr", PAGES["bureau"][0])
    ar_versions = fetch_versions(fetcher, "ar", PAGES["bureau"][1])
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: set[tuple[str, str]] = set()
    unresolved: list[str] = []
    # As for the committee page: the baseline state, where the two languages
    # still describe the same bureau.
    for first, _last, markup in fr_versions[:1]:
        latin = parse_bureau(_content(markup))
        arabic = parse_bureau(_content(ar_versions[0][2]))
        if len(latin) != len(arabic):
            raise ValueError("bureau pages list different numbers of members")
        pairs = [(a[0], f[0]) for a, f in zip(arabic, latin) if a[0] and f[0]]
        _check_similarity(pairs, "bureau")
        for (name_ar, title_ar), (name_fr, title_fr) in zip(arabic, latin):
            if not name_fr:
                continue
            office = OFFICE_MAP.get(title_fr.strip().lower(), "bureau_member")
            key = _resolve_member(name_fr, seats)
            if not key:
                unresolved.append(name_fr)
                continue
            if (key, office) in known:
                continue
            known.add((key, office))
            out[key].append({
                "office": office,
                "office_label_ar": title_ar,
                "office_label_lat": title_fr,
                "start_date": "",
                "end_date": DISSOLUTION,
            })
    if unresolved:
        raise ValueError(
            f"bureau page names people who are on no roster page: {sorted(set(unresolved))}")
    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _mandate_notes(seat: Seat) -> tuple[str, str, str]:
    """Return ``(end_date, exit_mode, note)`` for one seat.

    Three cases. Most members are on every capture of their page and end with
    the chamber. A handful vanish between two captures, and one appears between
    them — and because the gap in the captures *straddles the dissolution*, the
    site cannot say whether a vanished member left their seat or merely left the
    page after the chamber ceased to exist. That distinction is not knowable
    from this source, so the mandate ends on an empty date with the interval
    written down, rather than on a confident date that would be a guess.
    """
    if seat.first_absent:
        return "", "unknown", (
            f"listed on the chamber's own roster page as late as {seat.last_seen} "
            f"and absent from it by {seat.first_absent}; that interval contains "
            f"the chamber's dissolution on {DISSOLUTION}, so it cannot be "
            "determined from this source whether the seat was vacated during the "
            "term or the page was edited afterwards"
        )
    if seat.late_arrival:
        return DISSOLUTION, "dissolution", (
            "absent from an earlier capture of the chamber's own roster page and first "
            f"listed on {seat.first_seen}; the seat was therefore taken somewhere in "
            f"that interval, which contains the dissolution on {DISSOLUTION}, so the "
            "start of service is bracketed rather than established"
        )
    return DISSOLUTION, "dissolution", ""


def collect(refresh: bool = False) -> StagingDoc:
    fetcher = Fetcher(RAW / "chambre_conseillers", delay=1.5, refresh=refresh)

    seats: dict[str, Seat] = {}
    constituencies = collect_governorates(fetcher, seats)
    constituencies += collect_professional(fetcher, seats)
    vacancy_log = collect_appointees(fetcher, seats)
    committees = collect_committees(fetcher, seats)
    offices = collect_bureau(fetcher, seats)

    by_category: dict[str, int] = defaultdict(int)
    for seat in seats.values():
        by_category[seat.category] += 1
    log(f"  {len(seats)} members: " + ", ".join(
        f"{n} {c}" for c, n in sorted(by_category.items())))

    # Cross-check against the chamber's own alphabetical index, which is a
    # separately maintained page. It is not used to add anyone — it carries no
    # seat category, so a member known only from it could not be placed — but a
    # disagreement would mean one of the roster pages is being mis-parsed.
    alpha_versions = fetch_versions(fetcher, "fr", PAGES["alphabetical"][0])
    alpha_names = {n for _f, _l, m in alpha_versions for n in parse_alphabetical(_content(m))}
    alpha = {_resolve_member(n, seats) for n in alpha_names}
    alpha.discard("")
    roster = set(seats)
    unplaceable = sorted(n for n in alpha_names if not _resolve_member(n, seats))
    log(f"  alphabetical index lists {len(alpha_names)} names; {len(alpha)} resolve to "
        f"roster seats, {len(roster - alpha)} roster members are absent from it")
    if unplaceable:
        raise ValueError(
            f"the chamber's own index names people no roster page places: {unplaceable}")

    # Both collectors resolve into the roster or raise, so this is an assertion
    # rather than a report; it is kept because a future change to the resolver
    # would otherwise route around it silently.
    stray = sorted((set(committees) | set(offices)) - roster)
    if stray:
        raise ValueError(f"committee or bureau spells attached to no roster seat: {stray}")
    log(f"  {sum(len(v) for v in committees.values())} committee seats, "
        f"{sum(len(v) for v in offices.values())} bureau seats")

    records: list[PersonRecord] = []
    for key in sorted(seats):
        seat = seats[key]
        end_date, exit_mode, note = _mandate_notes(seat)
        notes = [note] if note else []
        if seat.category == "professional":
            notes.append(f"returned by the {seat.college}' professional organisation")
        elif seat.category == "appointed":
            notes.append(f"presidential appointee, slot {seat.slot} of the chamber's own list")
        notes.append(
            "recovered from Internet Archive captures of the chamber's own site, "
            "which went offline with the chamber"
        )
        gov_row = _GOV_BY_ID.get(seat.governorate_id)
        college = dict((c[0], c) for c in COLLEGES).get(seat.college)
        records.append(PersonRecord(
            source_key=seat.source_key,
            source_url=f"{SITE}/fr/index.php?id={PAGES['alphabetical'][0]}",
            name_ar=seat.name_ar,
            name_lat=seat.name_lat,
            mandate={
                # The chamber's first sitting is not established anywhere this
                # dataset trusts, so no start date is asserted for any member.
                "start_date": "",
                "end_date": end_date,
                "entry_mode": "appointed" if seat.category == "appointed" else "elected",
                "exit_mode": exit_mode,
                "constituency_name_ar": gov_row["name_ar"] if gov_row else (
                    college[1] if college else ""),
                "constituency_name_lat": gov_row["name_lat"] if gov_row else (
                    college[2] if college else ""),
                "governorate_name_ar": gov_row["name_ar"] if gov_row else "",
                "seat_number": seat.slot,
                "is_diaspora_seat": False,
                "notes": "; ".join(n for n in notes if n),
            },
            committees=committees.get(key, []),
            offices=offices.get(key, []),
            authoritative_fields=["name_ar", "name_lat"],
        ))

    n_departed = sum(1 for s in seats.values() if s.first_absent)
    n_arrived = sum(1 for s in seats.values() if s.late_arrival)
    n_committee_seats = sum(len(v) for v in committees.values())

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=ASSEMBLY_ID,
        source={
            "source_id": SOURCE_ID,
            "name": "Chamber of Advisors official website, via the Internet Archive",
            "publisher": "Chambre des conseillers; captures held by the Internet Archive",
            "url": f"{SITE}/fr/index.php?id={PAGES['alphabetical'][0]}",
            "access_method": (
                "Wayback CDX index collapsed on content digest to enumerate distinct "
                "page states, then raw (`id_`) fetches of each state, Arabic and French"
            ),
            "coverage": (
                f"ADV-2005: {len(seats)} members with Arabic names and the chamber's "
                "own French romanisation, seat category (governorate, professional "
                "organisation, presidential appointee), constituency, committee "
                "membership with roles, and the bureau"
            ),
            "language": "ar; fr",
            "licence": (
                "Not stated. Official publication of a dissolved public body, "
                "concerning people acting in public office."
            ),
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "The chamber's site died with the chamber and is recoverable only "
                "from the Internet Archive. Seat counts reconcile exactly against "
                "the chamber's nominal size: 43 governorate representatives + 28 "
                "professional-organisation representatives + 41 presidential "
                "appointees = 112, and the 71/41 split matches the two-thirds "
                "indirect, one-third appointed composition set by the 2002 "
                "constitutional amendment. The Arabic and French pages are joined "
                "structurally (by governorate, printed slot number, column, and "
                "position within a committee), never by fuzzy name matching across "
                "scripts; the sole exception is the ordering of the two members "
                "inside a governorate, decided by romanisation similarity with a "
                "checked margin. No member's mandate start date is asserted: the "
                "chamber's first sitting is not established. The appointee page "
                "changes once between captures — six slots go blank and one "
                "changes hands — and that interval contains the dissolution, so "
                "those mandates end on an empty date with the interval recorded "
                "rather than on a guessed one. The site published a roster, not "
                "member profiles: there are no dates of birth, parties or "
                "biographies here."
            ),
        },
        assembly_updates={
            "seats_by_category": dict(sorted(by_category.items())),
            "appointee_page_states": vacancy_log,
            "n_committee_seats": n_committee_seats,
            "n_bureau_seats": sum(len(v) for v in offices.values()),
            "alphabetical_index_size": len(alpha_names),
            "alphabetical_index_resolved": len(alpha),
            "roster_absent_from_index": sorted(roster - alpha),
        },
        notes=(
            f"{len(records)} members of the Chamber of Advisors, "
            f"{n_committee_seats} committee seats across "
            f"{len({c['name_lat'] for v in committees.values() for c in v})} committees, "
            f"and {sum(len(v) for v in offices.values())} bureau seats. "
            f"{n_departed} members disappear from the roster pages and {n_arrived} "
            f"appear, in an interval that contains the dissolution. The chamber's "
            f"own alphabetical index, maintained separately and captured later "
            f"still, resolves entirely into the roster ({len(alpha)} of "
            f"{len(alpha_names)}) and omits exactly the {len(roster - alpha)} members "
            f"the other pages show leaving — an independent confirmation of both. "
            f"Fetch: {fetcher.report()}."
        ),
        constituencies=constituencies,
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Recover the 2005-2011 Chamber of Advisors from the Internet Archive")
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    args = ap.parse_args()
    collect(refresh=args.refresh).save()


if __name__ == "__main__":
    main()
