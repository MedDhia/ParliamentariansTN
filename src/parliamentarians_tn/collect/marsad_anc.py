"""Collector: the 2011-2014 National Constituent Assembly, from Al Bawsala's Marsad.

Al Bawsala's original observatory (marsad.tn) is the richest biographical source
that exists for any Tunisian legislature. For each of the 217 members it
publishes a narrative profile in Arabic *and* French, plus bloc, electoral list,
constituency, party, committee assignments with roles, and a vote-participation
rate with the member's rank in the chamber.

The French profiles are parsed in preference to the Arabic ones for structured
attributes, for a practical reason: they render dates in a single predictable
form (``Né le 02 Novembre 1975, à Sidi Khlif dans le gouvernorat de Sidi
Bouzid``), whereas the Arabic profiles use several date idioms. Both are stored
— the Arabic text as ``biography_ar``, the French as the extraction substrate —
so nothing is discarded.

The career extraction here is deliberately conservative. Profiles are prose, and
prose does not parse cleanly into spells. Only high-precision patterns are
converted into ``careers`` rows, each stamped ``extraction_method='rule'`` with
an explicit confidence, and the full biography is retained so that a researcher
can hand-code the remainder. Treating a regex over a narrative as if it were a
structured career history is exactly the kind of silent error this dataset is
built to avoid.
"""

from __future__ import annotations

import argparse
import html
import re
from typing import Any, Iterable

from ..io import Fetcher, RAW, log, today
from .base import PersonRecord, StagingDoc

SOURCE_ID = "MARSAD_ANC"
ASSEMBLY_ID = "NCA-2011"
SITE = "https://www.marsad.tn"
ROSTER_URL = f"{SITE}/assemblee"

FIRST_SITTING = "2011-11-22"
ELECTION_DATE = "2011-10-23"
DISSOLUTION = "2014-12-01"

FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

COMMITTEE_TYPE_MAP = {
    "لجنة تأسيسية": "constituent",
    "لجنة تشريعية": "legislative",
    "لجنة خاصة": "special",
    "لجنة تحقيق": "inquiry",
    "الهيئة المشتركة": "joint",
    "هيئة مشتركة": "joint",
}

COMMITTEE_ROLE_MAP = {
    "المقرر المساعد الأول": "assistant_rapporteur",
    "المقرر المساعد الثاني": "assistant_rapporteur",
    "المقرر المساعد": "assistant_rapporteur",
    "مقرر مساعد": "assistant_rapporteur",
    "المقرر": "rapporteur",
    "مقرر": "rapporteur",
    "نائب الرئيس": "vice_chair",
    "نائب رئيس": "vice_chair",
    "الرئيس": "chair",
    "رئيس": "chair",
    "عضو": "member",
}

# Arabic labels on the profile sidebar -> our field names.
AR_LABELS = {
    "الكتلة البرلمانية": "bloc",
    "القائمة الانتخابية": "list",
    "الدائرة الانتخابية": "constituency",
    "الحزب السياسي": "party",
    "نسبة المشاركة في التصويت": "participation",
}

FR_LABELS = {
    "Bloc parlementaire": "bloc",
    "Liste électorale": "list",
    "Circonscription": "constituency",
    "Parti politique": "party",
    "Taux de participation aux votes": "participation",
}


# ---------------------------------------------------------------------------
# HTML to text nodes
# ---------------------------------------------------------------------------

def text_nodes(markup: str) -> list[str]:
    """Flatten HTML to a list of visible text nodes.

    Marsad's markup is a stable Jinja/Flask render with no client-side
    templating, so text-node order is a reliable proxy for document order and
    label/value pairs sit adjacent. This avoids a parser dependency.
    """
    body = re.sub(r"<(script|style|head)[^>]*>.*?</\1>", " ", markup, flags=re.S | re.I)
    body = re.sub(r"<title[^>]*>.*?</title>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", "\x00", body)
    body = html.unescape(body)
    nodes = [re.sub(r"\s+", " ", n).strip() for n in body.split("\x00")]
    return [n for n in nodes if n and n != "."]


TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def title_name(markup: str) -> str:
    """Extract the member's name from the page title.

    The title is ``"<name> | مرصد"`` (or ``"| Marsad"``), which is the most
    reliable anchor on the page: the body's first text node is a navigation
    link, and the heading markup varies between profiles.
    """
    m = TITLE_RE.search(markup)
    if not m:
        return ""
    raw = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
    name = raw.split("|")[0]
    return re.sub(r"\s+", " ", name).strip(" .-—")


def _value_after(nodes: list[str], label: str) -> str:
    """Return the first non-empty node following ``label``."""
    for i, node in enumerate(nodes):
        if node == label or node.rstrip(":") == label:
            for candidate in nodes[i + 1 : i + 3]:
                if candidate and candidate not in ("(", ")"):
                    return candidate
    return ""


def _around(nodes: list[str], label: str, span: int = 4) -> str:
    """Join the nodes following ``label``, for values split across nodes."""
    for i, node in enumerate(nodes):
        if node == label or node.rstrip(":") == label:
            return " ".join(nodes[i + 1 : i + 1 + span])
    return ""


def _sidebar(nodes: list[str], labels: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for label, key in labels.items():
        val = _value_after(nodes, label)
        if val:
            out[key] = val
    return out


# ---------------------------------------------------------------------------
# Biography parsing
# ---------------------------------------------------------------------------

# Some profiles are pasted from Wikipedia and carry footnote markers glued to
# the year ("né le 1er mai 19561"). The old pattern refused to match those and
# silently fell through to an unrelated date later in the biography — which is
# how one member acquired a birth year of 1998 and an apparent age of 13 at
# election. `\d{0,2}(?!\d)` absorbs the footnote; excluding digits from the
# place groups stops a marker being captured as part of a place name.
BIRTH_RE = re.compile(
    r"Né[e]?\s+le\s+(\d{1,2})\s*(?:er)?\s+([A-Za-zéûôàèî]+)\s+(\d{4})\d{0,2}(?!\d)"
    r"(?:\s*,?\s*à\s+([^,\.;0-9]+?))?"
    r"(?:\s*(?:dans le gouvernorat de|gouvernorat de)\s+([^,\.;0-9]+?))?"
    r"\s*(?:[,\.;]|\d|$)",
    re.I,
)

# A parliamentarian seated in 2011 was not born after 1993 or before 1911.
# Anything outside that window is a parse failure, not a finding, so it is
# dropped rather than published.
PLAUSIBLE_BIRTH_YEARS = (1911, 1993)
BIRTH_YEAR_ONLY_RE = re.compile(r"Né[e]?\s+en\s+(\d{4})", re.I)

CHILDREN_RE = re.compile(r"p[èe]re de (\w+) enfants?|m[èe]re de (\w+) enfants?", re.I)
NUM_WORDS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
}

MARITAL_RE = re.compile(r"\b(mari[ée]+|célibataire|celibataire|divorc[ée]+|veu[fv]e?)\b", re.I)

LANG_RE = re.compile(
    r"ma[îi]trise[^.]*?\b(arabe|fran[çc]ais[e]?|anglais[e]?|italien[ne]?|allemand[e]?|espagnol[e]?)",
    re.I,
)
LANG_TOKENS = {
    "arabe": "ar", "français": "fr", "francais": "fr", "française": "fr",
    "anglais": "en", "anglaise": "en", "italien": "it", "italienne": "it",
    "allemand": "de", "allemande": "de", "espagnol": "es", "espagnole": "es",
}

# High-precision career patterns. Each maps to (sector, confidence).
CAREER_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"membre\s+du\s+syndicat|syndicaliste|UGTT", re.I), "trade_union", "membre du syndicat", "medium"),
    (re.compile(r"membre\s+(?:d['’]une?|de la|du)\s+association[^.,;]{0,60}", re.I), "civil_society", "", "medium"),
    (re.compile(r"membre\s+du\s+bureau\s+politique[^.,;]{0,60}", re.I), "party", "", "medium"),
    (re.compile(r"\b(?:ancien\s+)?ministre\b[^.,;]{0,60}", re.I), "state_executive", "", "medium"),
    (re.compile(r"\b(?:ancien\s+)?gouverneur\b[^.,;]{0,60}", re.I), "state_executive", "", "medium"),
    (re.compile(r"\bavocat[e]?\b", re.I), "judiciary", "avocat", "medium"),
    (re.compile(r"\b(?:magistrat|juge)\b", re.I), "judiciary", "", "medium"),
    (re.compile(r"\bm[ée]decin\b|\bchirurgien\b|\bdentiste\b", re.I), "health", "", "medium"),
    (re.compile(r"\bpharmacien[ne]?\b", re.I), "health", "", "medium"),
    (re.compile(r"\bing[ée]nieur\b", re.I), "other", "ingénieur", "medium"),
    (re.compile(r"\b(?:enseignant[e]?|professeur|instituteur|institutrice)\b", re.I), "education", "", "medium"),
    (re.compile(r"\buniversitaire\b|\bma[îi]tre de conf[ée]rences\b", re.I), "academia", "", "medium"),
    (re.compile(r"\bjournaliste\b", re.I), "media", "", "medium"),
    (re.compile(r"\b(?:imam|prédicateur)\b", re.I), "religious", "", "medium"),
    (re.compile(r"\b(?:officier|militaire)\b", re.I), "military", "", "low"),
    (re.compile(r"\b(?:homme|femme) d['’]affaires\b|\bentrepreneur\b|\bcommer[çc]ant[e]?\b", re.I), "business", "", "medium"),
    (re.compile(r"\bagriculteur\b|\bexploitant agricole\b", re.I), "other", "agriculteur", "medium"),
    (re.compile(r"\bfonctionnaire\b", re.I), "state_administration", "fonctionnaire", "medium"),
]


def _year_plausible(year: int) -> bool:
    lo, hi = PLAUSIBLE_BIRTH_YEARS
    return lo <= year <= hi


def parse_birth(bio_fr: str) -> dict[str, str]:
    out: dict[str, str] = {}
    m = BIRTH_RE.search(bio_fr)
    if m and not _year_plausible(int(m.group(3))):
        m = None
    if m:
        day, month_name, year, place, gov = m.groups()
        month = FRENCH_MONTHS.get((month_name or "").lower())
        if month:
            out["birth_date"] = f"{int(year):04d}-{month:02d}-{int(day):02d}"
            out["birth_date_precision"] = "day"
        else:
            out["birth_date"] = f"{int(year):04d}-01-01"
            out["birth_date_precision"] = "year"
        if place:
            out["birth_place_ar"] = place.strip()
        if gov:
            out["birth_governorate_name"] = gov.strip()
        return out
    m = BIRTH_YEAR_ONLY_RE.search(bio_fr)
    if m and _year_plausible(int(m.group(1))):
        out["birth_date"] = f"{int(m.group(1)):04d}-01-01"
        out["birth_date_precision"] = "year"
    return out


def parse_gender(bio_fr: str) -> str:
    """Infer sex from French grammatical agreement in the biography.

    Marsad does not publish a sex field for the Constituent Assembly, which
    would leave 217 members — nearly a third of the dataset — unusable for any
    analysis involving gender, including the parity provisions that governed the
    2011 lists. French agreement carries the information unambiguously:
    ``Née le`` versus ``Né le``, ``Mariée`` versus ``Marié``, ``elle`` versus
    ``il``.

    This is an inference, not a recorded value. It is drawn only from
    grammatical agreement in the source's own prose — never from the name, which
    would be guesswork — and the source register records that NCA-2011 sex is
    inferred this way. Participles are checked before pronouns because a
    biography may quote or refer to other people.
    """
    if re.search(r"\bNée\b", bio_fr):
        return "female"
    if re.search(r"\bNé\b", bio_fr):
        return "male"
    if re.search(r"\bMariée\b|\bDivorcée\b|\bVeuve\b|\bmère de\b", bio_fr, re.I):
        return "female"
    if re.search(r"\bMarié\b|\bDivorcé\b|\bVeuf\b|\bpère de\b", bio_fr, re.I):
        return "male"
    feminine = len(re.findall(r"\belle\b", bio_fr, re.I))
    masculine = len(re.findall(r"\bil\b", bio_fr, re.I))
    if feminine > masculine:
        return "female"
    if masculine > feminine:
        return "male"
    return "unknown"


def parse_personal(bio_fr: str) -> dict[str, str]:
    out: dict[str, str] = {}
    m = MARITAL_RE.search(bio_fr)
    if m:
        out["marital_status"] = m.group(1).lower()
    m = CHILDREN_RE.search(bio_fr)
    if m:
        word = (m.group(1) or m.group(2) or "").lower()
        if word.isdigit():
            out["n_children"] = word
        elif word in NUM_WORDS:
            out["n_children"] = str(NUM_WORDS[word])
    langs: list[str] = []
    for m in LANG_RE.finditer(bio_fr):
        code = LANG_TOKENS.get(m.group(1).lower())
        if code and code not in langs:
            langs.append(code)
    # the pattern only catches the first language of a list; sweep the tail
    tail = bio_fr[bio_fr.lower().find("maîtrise"):] if "maîtrise" in bio_fr.lower() else ""
    for token, code in LANG_TOKENS.items():
        if tail and re.search(rf"\b{token}\b", tail, re.I) and code not in langs:
            langs.append(code)
    if langs:
        out["languages"] = ";".join(langs)
    return out


def extract_careers(bio_fr: str) -> list[dict[str, Any]]:
    """Rule-based extraction of extra-parliamentary roles from French prose."""
    careers: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for pattern, sector, role_hint, confidence in CAREER_PATTERNS:
        m = pattern.search(bio_fr)
        if not m:
            continue
        snippet = re.sub(r"\s+", " ", m.group(0)).strip(" ,.;")
        role = role_hint or snippet
        key = (sector, role.lower()[:40])
        if key in seen:
            continue
        seen.add(key)
        careers.append({
            "role_raw": role,
            "organisation_raw": snippet if snippet != role else "",
            "sector": sector,
            "relative_to_mandate": "unknown",
            "extraction_method": "rule",
            "confidence": confidence,
            "evidence": snippet,
        })
    return careers


def _pct(value: str) -> tuple[str, str]:
    """Split '44.88%' / '(178ème)' style values into rate and rank."""
    rate = ""
    m = re.search(r"([\d.,]+)\s*%", value)
    if m:
        try:
            rate = f"{float(m.group(1).replace(',', '.')) / 100:.4f}"
        except ValueError:
            rate = ""
    rank = ""
    # French renders the rank as "(178ème)", Arabic as "(المرتبة 178)".
    m = re.search(r"(\d+)\s*(?:ème|er|th)", value) or re.search(r"المرتبة\s*(\d+)", value)
    if m:
        rank = m.group(1)
    return rate, rank


# ---------------------------------------------------------------------------
# Committee page
# ---------------------------------------------------------------------------

def parse_committees(markup: str) -> list[dict[str, Any]]:
    """Parse a member's committee page into (committee, type, role) triples.

    The page is a bare fragment of repeated three-node groups, e.g.
    ``لجنة الحقوق والحريات`` / ``لجنة تأسيسية`` / ``المقرر المساعد الأول``.
    """
    nodes = text_nodes(markup)
    out: list[dict[str, Any]] = []
    i = 0
    while i + 1 < len(nodes):
        name = nodes[i]
        kind = nodes[i + 1] if i + 1 < len(nodes) else ""
        role_label = nodes[i + 2] if i + 2 < len(nodes) else ""
        if kind not in COMMITTEE_TYPE_MAP:
            i += 1
            continue
        role = "member"
        for key, val in sorted(COMMITTEE_ROLE_MAP.items(), key=lambda kv: -len(kv[0])):
            if key in role_label:
                role = val
                break
        out.append({
            "name_ar": name,
            "type": COMMITTEE_TYPE_MAP[kind],
            "type_label_ar": kind,
            "role": role,
            "role_label_ar": role_label,
            "start_date": FIRST_SITTING,
            "end_date": DISSOLUTION,
        })
        i += 3
    return out


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Activity pages
# ---------------------------------------------------------------------------
# Every member profile links five sub-pages. An earlier version of this
# collector followed only /commissions, which left the chamber's entire
# behavioural record on the table: 1,724 recorded divisions per member, the
# constitutional amendments they co-sponsored, and the party-switching series.

MERCATO_URL = f"{SITE}/fr/mercato"

# "25 sept. 2014" — the abbreviated forms Marsad renders, which differ from the
# full month names used in the biographies.
FRENCH_MONTHS_ABBR = {
    "janv": 1, "févr": 2, "fevr": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6,
    "juil": 7, "août": 8, "aout": 8, "sept": 9, "oct": 10, "nov": 11, "déc": 12,
    "dec": 12,
}

# Compact position codes. The staging document stores one character per member
# per division rather than a row per pair: 217 members x 1,724 divisions is
# 374,000 rows, which as JSON objects would bloat the committed staging file by
# tens of megabytes for no gain. The build expands this back to one row per
# pair. "-" means the division is not listed on that member's page at all,
# which happens for members who joined late or left early.
POSITION_CODES = {"pour": "P", "contre": "C", "abstenu": "A", "absent": "X"}
CODE_POSITIONS = {v: k for k, v in POSITION_CODES.items()}

_VOTE_ROW_RE = re.compile(
    r'<div class="vote-date[^"]*">\s*([^<]+?)\s*</div>.*?'
    r'<a href="/fr/vote/([0-9a-f]{24})"[^>]*class="vote-article">\s*'
    r'<span class="[^"]*\bvoted-([a-z]+)\b[^"]*">\s*</span>\s*(.*?)</a>',
    re.S,
)


def parse_french_date(text: str) -> str:
    """'25 sept. 2014' -> '2014-09-25'; empty string when unparseable."""
    m = re.match(r"(\d{1,2})\s+([^\s.]+)\.?\s+(\d{4})", text.strip())
    if not m:
        return ""
    month = FRENCH_MONTHS_ABBR.get(m.group(2).lower().rstrip("."))
    if not month:
        return ""
    return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"


def parse_votes(markup: str) -> list[dict[str, str]]:
    """Roll-call rows from a member's /votes page.

    Each row carries the division's own id, so divisions are identified
    consistently across the 217 member pages and can be deduplicated into a
    chamber-level vote register. The member's own position is encoded in a CSS
    class (``voted-pour``, ``voted-contre``, ``voted-abstenu``, ``voted-absent``)
    rather than in text, which is why a text-node walk misses it entirely.
    """
    out = []
    for date_raw, vote_key, position, title_html in _VOTE_ROW_RE.findall(markup):
        title = html.unescape(re.sub(r"<[^>]+>", " ", title_html))
        out.append({
            "vote_source_key": vote_key,
            "date": parse_french_date(date_raw),
            "date_raw": date_raw.strip(),
            "title": re.sub(r"\s+", " ", title).strip(),
            "position": position,
        })
    return out


def parse_amendments(markup: str) -> list[dict[str, Any]]:
    """Constitutional amendments and their co-sponsors from /amendements.

    Co-sponsors are published as links carrying deputy ids, so this yields a
    sponsorship network keyed to the same identifiers as the roster — no name
    matching required, which for Arabic names would be the weakest link.
    """
    out = []
    for block in re.split(r'(?=<p class="grey">)', markup):
        if "Soumis par" not in block:
            continue
        target = re.search(r'<a href="(/fr/constitution/[^"]*)">\s*([^<]+?)\s*</a>', block)
        group = re.search(r'<a href="#" class="show-deps" data-id="([0-9a-f]{24})"', block)
        sponsors = re.findall(r'<a href="/fr/deputes/([0-9a-f]{24})">', block)
        if not sponsors:
            continue
        # The amendment's own wording is in the paragraphs *after* the sponsor
        # list. Taking the first <p> that follows the header picks up the list
        # of sponsor names instead, which is why the class filter matters.
        body = " ".join(
            para for attrs, para in re.findall(r'<p([^>]*)>(.*?)</p>', block, re.S)
            if "deps" not in attrs and "grey" not in attrs
        )
        out.append({
            "amendment_source_key": group.group(1) if group else "",
            "target_url": target.group(1) if target else "",
            "target_label": target.group(2).strip() if target else "",
            "text": re.sub(r"\s+", " ", html.unescape(
                re.sub(r"<[^>]+>", " ", body))).strip(),
            "sponsor_source_keys": sponsors,
        })
    return out


def _balanced_json(markup: str, marker: str) -> Any:
    """Read a brace-balanced JSON literal that follows ``marker`` in a script."""
    start = markup.find(marker)
    if start < 0:
        return None
    start = markup.find("{", start)
    if start < 0:
        return None
    depth, in_str, escape = 0, False, False
    for i in range(start, len(markup)):
        ch = markup[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                import json as _json
                try:
                    return _json.loads(markup[start:i + 1])
                except ValueError:
                    return None
    return None


def parse_mercato(markup: str) -> list[dict[str, str]]:
    """Party switching from the /mercato page's inline JSON.

    The page renders a d3 diagram from a literal assigned to ``mercato_map``:
    for each party of election, how many members it had ``then`` and has ``now``,
    and for each destination party the ids of the members who moved there.

    This is the source the collector previously declared switching
    "not recoverable" from — wrongly. It is an aggregate of moves rather than
    dated spells, so each move is a from/to pair without a date; that is stated
    on the rows rather than smoothed into an invented date.
    """
    data = _balanced_json(markup, "mercato_map")
    if not isinstance(data, dict):
        return []
    moves = []
    for origin, info in data.items():
        for destination, deputies in (info.get("partis") or {}).items():
            for deputy in deputies:
                moves.append({
                    "deputy_source_key": deputy,
                    "party_from": origin,
                    "party_to": destination,
                })
    return moves


def _is_empty_page(markup: str) -> bool:
    """True for Marsad's 'nothing here' placeholders on questions/transparence."""
    text = " ".join(text_nodes(markup)).lower()
    return ("aucune question" in text or "aucune publication" in text
            or len(text.strip()) < 40)


def _roster_ids(fetcher: Fetcher) -> list[str]:
    markup = fetcher.get_text(ROSTER_URL, slug="roster_assemblee")
    ids = sorted(set(re.findall(r"/deputes/([0-9a-f]{24})", markup)))
    if not ids:
        raise RuntimeError("no deputy ids found on the roster page; upstream layout changed")
    return ids


def collect(refresh: bool = False, limit: int | None = None) -> StagingDoc:
    fetcher = Fetcher(RAW / "marsad_anc", delay=0.8, refresh=refresh)
    ids = _roster_ids(fetcher)
    if limit:
        ids = ids[:limit]
    log(f"  roster: {len(ids)} members")

    records: list[PersonRecord] = []
    n_bio_fr = n_birth = n_committees = n_gender = 0
    # Activity, accumulated across members. The vote register is the union of
    # every member's page keyed on the division's own id; each member then
    # contributes one position per division.
    vote_register: dict[str, dict[str, str]] = {}
    member_positions: dict[str, dict[str, str]] = {}
    amendments: dict[str, dict[str, Any]] = {}
    n_empty_questions = n_empty_transparence = 0

    for idx, oid in enumerate(ids, start=1):
        if idx % 25 == 0:
            log(f"  ... {idx}/{len(ids)}")
        ar = fetcher.get_text(f"{SITE}/deputes/{oid}", slug=f"{oid}_ar")
        fr = fetcher.get_text(f"{SITE}/fr/deputes/{oid}", slug=f"{oid}_fr")
        com = fetcher.get_text(f"{SITE}/deputes/{oid}/commissions", slug=f"{oid}_com")

        # The four activity pages the earlier version of this collector never
        # followed. /votes is the large one — roughly 1,700 divisions each.
        votes_page = fetcher.get_text(f"{SITE}/fr/deputes/{oid}/votes", slug=f"{oid}_votes")
        amend_page = fetcher.get_text(f"{SITE}/fr/deputes/{oid}/amendements",
                                      slug=f"{oid}_amend")
        quest_page = fetcher.get_text(f"{SITE}/fr/deputes/{oid}/questions",
                                      slug=f"{oid}_quest")
        transp_page = fetcher.get_text(f"{SITE}/fr/deputes/{oid}/transparence",
                                       slug=f"{oid}_transp")

        positions: dict[str, str] = {}
        for row in parse_votes(votes_page):
            key = row["vote_source_key"]
            vote_register.setdefault(key, {
                "source_key": key, "date": row["date"], "title": row["title"],
            })
            positions[key] = POSITION_CODES.get(row["position"], "?")
        if positions:
            member_positions[oid] = positions

        for amendment in parse_amendments(amend_page):
            key = amendment["amendment_source_key"] or amendment["text"][:80]
            amendments.setdefault(key, amendment)

        n_empty_questions += _is_empty_page(quest_page)
        n_empty_transparence += _is_empty_page(transp_page)

        ar_nodes = text_nodes(ar)
        fr_nodes = text_nodes(fr)

        name_ar = title_name(ar)
        name_lat = title_name(fr)

        ar_side = _sidebar(ar_nodes, AR_LABELS)
        fr_side = _sidebar(fr_nodes, FR_LABELS)

        # Biography: everything between the name and the first sidebar label.
        # A length threshold alone loses short but information-dense sentences
        # such as "Marié et père de deux enfants, il maîtrise l'arabe et le
        # français." — which carries marital status, children and languages.
        def _bio(nodes: list[str], labels: dict[str, str]) -> str:
            stop = len(nodes)
            for i, node in enumerate(nodes):
                if node in labels:
                    stop = i
                    break
            paras = [n for n in nodes[1:stop] if len(n) > 30]
            return " ".join(paras)

        bio_ar = _bio(ar_nodes, AR_LABELS)
        bio_fr = _bio(fr_nodes, FR_LABELS)
        if bio_fr:
            n_bio_fr += 1

        attrs = parse_birth(bio_fr)
        if attrs.get("birth_date"):
            n_birth += 1
        attrs.update(parse_personal(bio_fr))

        # The rate and the chamber rank are separate text nodes ("44.88%" then
        # "(178ème)"), so both label neighbourhoods are swept together.
        rate, rank = _pct(_around(fr_nodes, "Taux de participation aux votes"))
        if not rate:
            rate, rank = _pct(_around(ar_nodes, "نسبة المشاركة في التصويت"))

        committees = parse_committees(com)
        if committees:
            n_committees += 1
        gender = parse_gender(bio_fr)
        if gender != "unknown":
            n_gender += 1

        bloc_ar = ar_side.get("bloc", "")
        bloc_fr = fr_side.get("bloc", "")

        rec = PersonRecord(
            source_key=oid,
            source_url=f"{SITE}/deputes/{oid}",
            name_ar=name_ar,
            name_lat=name_lat,
            gender=gender,
            birth_date=attrs.get("birth_date", ""),
            birth_date_precision=attrs.get("birth_date_precision", ""),
            birth_place_ar=attrs.get("birth_place_ar", ""),
            birth_governorate_name=attrs.get("birth_governorate_name", ""),
            marital_status=attrs.get("marital_status", ""),
            n_children=attrs.get("n_children", ""),
            languages=attrs.get("languages", ""),
            biography_ar=bio_ar,
            mandate={
                "start_date": FIRST_SITTING,
                "end_date": DISSOLUTION,
                "entry_mode": "elected",
                "exit_mode": "end_of_term",
                "constituency_name_ar": ar_side.get("constituency", ""),
                "constituency_name_lat": fr_side.get("constituency", ""),
                "electoral_list_ar": ar_side.get("list", ""),
                "electoral_list_lat": fr_side.get("list", ""),
                "party_name_ar": ar_side.get("party", ""),
                "party_name_lat": fr_side.get("party", ""),
                "election_date": ELECTION_DATE,
            },
            blocs=(
                [{
                    "source_key": bloc_ar or bloc_fr,
                    "name_ar": bloc_ar,
                    "name_lat": bloc_fr,
                    "role": "unknown",
                    "start_date": FIRST_SITTING,
                    "end_date": DISSOLUTION,
                }]
                if (bloc_ar or bloc_fr) else []
            ),
            committees=committees,
            careers=extract_careers(bio_fr),
            party_affiliations=(
                [{
                    "name_ar": ar_side.get("party", ""),
                    "name_lat": fr_side.get("party", ""),
                    "start_date": "",
                    "end_date": "",
                    "role": "",
                }]
                if ar_side.get("party") or fr_side.get("party") else []
            ),
            participation=(
                {
                    "vote_participation_rate": rate,
                    "vote_participation_rank": rank,
                }
                if rate else {}
            ),
            authoritative_fields=[
                "name_ar", "name_lat", "birth_date", "birth_place_ar",
                "marital_status", "languages", "biography_ar", "gender",
            ],
        )
        # The French narrative is the extraction substrate; keep it verbatim so
        # the rule-based fields can be audited or re-coded by hand.
        rec.education_raw = bio_fr
        records.append(rec)

    # Party switching, from the site-level diagram rather than a member page.
    mercato = parse_mercato(fetcher.get_text(MERCATO_URL, slug="mercato"))

    # Order the register by date then id so the position strings are stable
    # across runs, then encode each member's record as one character per
    # division. "-" marks a division absent from that member's page entirely,
    # which is how members who joined late or left early appear.
    ordered = sorted(vote_register.values(), key=lambda v: (v["date"], v["source_key"]))
    order_keys = [v["source_key"] for v in ordered]
    position_strings = {
        oid: "".join(pos.get(key, "-") for key in order_keys)
        for oid, pos in member_positions.items()
    }
    n_positions = sum(sum(1 for c in s if c != "-") for s in position_strings.values())
    log(f"  activity: {len(ordered)} divisions, {n_positions} recorded positions, "
        f"{len(amendments)} amendments, {len(mercato)} party rows")

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=ASSEMBLY_ID,
        assembly_updates={
            "votes": ordered,
            # person -> one position code per division, aligned to `votes`.
            # P pour, C contre, A abstenu, X absent, - not listed for them.
            "vote_position_codes": position_strings,
            "amendments": sorted(amendments.values(),
                                 key=lambda a: a["amendment_source_key"]),
            # from/to party pairs; where they are equal the member kept the
            # party they were elected on. Aggregate, so the moves carry no date.
            "party_switching": sorted(
                mercato, key=lambda m: (m["deputy_source_key"], m["party_to"])),
        },
        source={
            "source_id": SOURCE_ID,
            "name": "Marsad (Al Bawsala) — National Constituent Assembly observatory",
            "publisher": "Al Bawsala",
            "url": ROSTER_URL,
            "access_method": "HTML scrape of server-rendered profile pages (Arabic and French)",
            "coverage": (
                "NCA-2011: 217 members with narrative biographies in Arabic and "
                "French, birth date and place, marital status, languages, "
                "parliamentary bloc, electoral list, party, constituency, "
                "committee memberships with roles, vote-participation rate and rank, "
                "the full roll-call record (every recorded division with each "
                "member's position), constitutional amendments with their "
                "co-sponsors, and party of election against party at end of term"
            ),
            "language": "ar; fr",
            "licence": "Not stated. Civic-monitoring data on public office-holders.",
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "Sex is NOT published by this source and is inferred from French "
                "grammatical agreement in the member's own biography (Née/Né, "
                "Mariée/Marié, elle/il) — never from the name. "
                "The most biographically complete source for any Tunisian "
                "legislature. Compiled by an NGO from member questionnaires and "
                "declarations, so biographies are partly self-reported: "
                "occupations and civic roles are the member's own account. "
                "Bloc affiliation is a single end-of-term snapshot rather than a "
                "spell, so *bloc* switching within 2011-2014 is not recoverable "
                "and must not be inferred from its absence. *Party* switching "
                "is: the site's mercato diagram publishes each member's party of "
                "election against their party at the end of the term, which is "
                "how 105 of the 217 are recorded here as having changed party. "
                "Those are from/to pairs without dates, so they establish that a "
                "move happened, not when. "
                "Roll-call positions are published per member as pour / contre / "
                "abstenu / absent. 'Absent' conflates being away with being "
                "present and not voting; the source does not distinguish them. "
                "The site has not been updated since 2021 and is effectively an "
                "archive, which makes it stable to cite."
            ),
        },
        notes=(
            f"{len(records)} members; {n_bio_fr} with a French biography; "
            f"{n_birth} with a parsed birth date; {n_gender} with sex inferred from "
            f"French agreement; {n_committees} with committee rows. "
            f"Fetch: {fetcher.report()}."
        ),
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect the 2011-14 NCA from marsad.tn")
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    ap.add_argument("--limit", type=int, default=None, help="only the first N members (testing)")
    args = ap.parse_args()
    collect(refresh=args.refresh, limit=args.limit).save()


if __name__ == "__main__":
    main()
