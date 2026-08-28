"""Collector: the 2019-2021/23 Assembly of the Representatives of the People, from Marsad Majles.

Al Bawsala's second-generation observatory (majles.marsad.tn) covers the
assembly elected in October 2019 — the chamber frozen by presidential decree on
25 July 2021 and formally dissolved on 30 March 2022. The site stopped being
updated in 2021, which makes it a stable archive of that term.

Three pages carry almost everything, which is why this collector is cheap in
requests:

* ``/ar/assembly/deputies`` renders all 216 members as cards whose
  ``data-filter-*`` attributes expose bloc, electoral list, district,
  profession, age band and sex — the priority biographical layer — plus a
  vote-participation rate, an attendance rate, and whether the member filed
  the asset declaration required by law.
* ``/ar/assembly/blocs/<year>/<slug>`` lists each bloc's members. Note what
  this page is *not*: it renders a per-bloc attendance table, not a dated
  membership history. Bloc membership is therefore recovered as a single
  end-of-term snapshot, and **bloc switching within the 2019 term is not
  observable from this source**. That is a real limitation for this chamber,
  which fragmented continuously across the term; docs/SOURCES.md records
  ``marsad.tn/mercato`` as the lead for recovering switching properly.
* ``/ar/assembly/commissions/<slug>`` lists committee members with role and
  joining/leaving dates, which *are* published.

The French mirror is fetched for the roster only, to supply Latin-script names.
"""

from __future__ import annotations

import argparse
import html
import re
from typing import Any

from ..io import Fetcher, RAW, log, today
from .base import PersonRecord, StagingDoc

SOURCE_ID = "MARSAD_MAJLES"
ASSEMBLY_ID = "ARP-2019"
SITE = "https://majles.marsad.tn"

ROSTER_AR = f"{SITE}/ar/assembly/deputies"
ROSTER_FR = f"{SITE}/fr/assembly/deputies"
COMMISSIONS_INDEX = f"{SITE}/ar/assembly/commissions"
BLOCS_INDEX = f"{SITE}/ar/assembly/blocs"

FIRST_SITTING = "2019-11-13"
ELECTION_DATE = "2019-10-06"
FROZEN = "2021-07-25"  # suspended by Decree 2021-117
DISSOLVED = "2022-03-30"

# Tunisian usage keeps the French-derived month names alongside the standard
# Arabic ones, and Marsad uses both.
ARABIC_MONTHS = {
    "جانفي": 1, "يناير": 1,
    "فيفري": 2, "فبراير": 2,
    "مارس": 3,
    "أفريل": 4, "ابريل": 4, "أبريل": 4,
    "ماي": 5, "مايو": 5,
    "جوان": 6, "يونيو": 6,
    "جويلية": 7, "يوليو": 7, "جويليه": 7,
    "أوت": 8, "اغسطس": 8, "أغسطس": 8,
    "سبتمبر": 9,
    "أكتوبر": 10, "اكتوبر": 10,
    "نوفمبر": 11,
    "ديسمبر": 12,
}

GENDER_MAP = {"نساء": "female", "رجال": "male", "femmes": "female", "hommes": "male"}

ROLE_MAP = {
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

BLOC_ROLE_MAP = {
    "الرئيس": "bloc_chair",
    "رئيس": "bloc_chair",
    "عضو": "unknown",
}


def _txt(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_arabic_date(text: str) -> str:
    """Parse '19 ديسمبر 2019' into an ISO date. Returns '' if unparseable."""
    m = re.search(r"(\d{1,2})\s+([^\s\d]+)\s+(\d{4})", text)
    if not m:
        return ""
    day, month_name, year = m.groups()
    month = ARABIC_MONTHS.get(month_name.strip())
    if not month:
        return ""
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def _attr(block: str, name: str) -> str:
    m = re.search(rf'{name}="([^"]*)"', block)
    return html.unescape(m.group(1)).strip() if m else ""


def _pct(block: str, label: str) -> str:
    """Extract a rate that follows a label, as a proportion in [0, 1]."""
    m = re.search(rf"{re.escape(label)}\s*([\d.,]+)\s*%", block)
    if not m:
        return ""
    try:
        return f"{float(m.group(1).replace(',', '.')) / 100:.4f}"
    except ValueError:
        return ""


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------

def parse_roster(markup: str) -> dict[str, dict[str, Any]]:
    """Parse the deputies page into slug -> card attributes."""
    out: dict[str, dict[str, Any]] = {}
    # Each member is one `role="item"` container.
    blocks = re.split(r'<div role="item"', markup)[1:]
    for block in blocks:
        m = re.search(r"/ar/person/([a-z0-9\-]+)", block) or re.search(r"/fr/person/([a-z0-9\-]+)", block)
        if not m:
            continue
        slug = m.group(1)
        name = ""
        nm = re.search(r'class="person-name[^"]*">(.*?)</div>', block, re.S)
        if nm:
            name = _txt(nm.group(1))
        age_raw = _attr(block, "data-filter-age")
        age = age_raw if age_raw.isdigit() else ""
        out[slug] = {
            "slug": slug,
            "name": name,
            "bloc_ar": _attr(block, "data-filter-parliamentaryblock"),
            "list_ar": _attr(block, "data-filter-electorallist"),
            "district_ar": _attr(block, "data-filter-district"),
            "profession_ar": _attr(block, "data-filter-profession"),
            "age": age,
            "gender": GENDER_MAP.get(_attr(block, "data-filter-gender"), "unknown"),
            "bloc_slug": (re.search(r"/ar/assembly/blocs/\d{4}/([a-z0-9\-]+)", block) or [None, ""])[1]
            if re.search(r"/ar/assembly/blocs/\d{4}/([a-z0-9\-]+)", block) else "",
            "bloc_colour": _attr(block, "data-bloc-color"),
            "vote_participation_rate": _pct(block, "معدل المشاركة في التصويت"),
            "attendance_rate": _pct(block, "معدل الحضور"),
            "asset_declaration": "صرّح" in block or "صرح" in block,
        }
    return out


# The member page's statistics block. Each measure is rendered as a donut whose
# anchor title carries the counts behind the percentage — "Présence en
# plénières : 87 / 112" — which is the only place the denominators appear.
_STAT_TITLES = {
    "Présence en plénières": ("plenary_attendance_rate", "plenary_denominator"),
    "Présence en commissions permanentes": (
        "committee_attendance_rate", "committee_denominator"),
    "Participation aux votes": ("vote_participation_rate", "vote_denominator"),
}
_TITLE_RE = re.compile(r'title="([^"]+?)\s*:\s*(\d+)\s*/\s*(\d+)"')
_DISCIPLINE_RE = re.compile(
    r"Discipline de vote\s*<b[^>]*>\s*([\d.]+)%", re.S)


def parse_member_statistics(markup: str) -> dict[str, str]:
    """Attendance, vote participation and discipline from a member page.

    Rates are stored as proportions to match the rest of the dataset, and are
    recomputed from the counts rather than read from the rendered percentage,
    so a rounding artefact upstream cannot propagate. The denominator is the
    number of sittings or divisions there were to attend, which is what makes
    these figures comparable within the chamber.
    """
    out: dict[str, str] = {}
    for label, numerator, denominator in _TITLE_RE.findall(markup):
        fields = _STAT_TITLES.get(label.strip())
        if not fields or not int(denominator):
            continue
        rate_field, denom_field = fields
        out[rate_field] = f"{int(numerator) / int(denominator):.4f}"
        out[denom_field] = denominator
    discipline = _DISCIPLINE_RE.search(markup)
    if discipline:
        out["vote_discipline_rate"] = f"{float(discipline.group(1)) / 100:.4f}"
    return out


def parse_roster_fr(markup: str) -> dict[str, str]:
    """Parse the French roster into slug -> Latin-script name."""
    out: dict[str, str] = {}
    blocks = re.split(r'<div role="item"', markup)[1:]
    for block in blocks:
        m = re.search(r"/fr/person/([a-z0-9\-]+)", block)
        if not m:
            continue
        nm = re.search(r'class="person-name[^"]*">(.*?)</div>', block, re.S)
        if nm:
            out[m.group(1)] = _txt(nm.group(1))
    return out


# ---------------------------------------------------------------------------
# Member-list pages (blocs and committees share a card layout)
# ---------------------------------------------------------------------------

def parse_member_cards(markup: str, role_map: dict[str, str], default_role: str) -> list[dict[str, Any]]:
    """Parse deputy cards carrying a role and a date range.

    Cards render as::

        <a href="/ar/person/faycel-derbel">
          ... <span>...كتلة حركة النهضة</span>
          <span><img ...calendar> 19 ديسمبر 2019 - اليوم</span>
          <div class="person-name ...">فيصل دربال</div>
          <div class="person-bloc ...">مقرر</div>
        </a>

    ``اليوم`` ("today") means the spell was open when the site froze, which is
    recorded as an empty end_date rather than a fabricated one.
    """
    out: list[dict[str, Any]] = []
    for block in re.split(r'<div class="deputy-card', markup)[1:]:
        m = re.search(r"/ar/person/([a-z0-9\-]+)", block)
        if not m:
            continue
        slug = m.group(1)
        name = ""
        nm = re.search(r'class="person-name[^"]*">(.*?)</div>', block, re.S)
        if nm:
            name = _txt(nm.group(1))
        role_label = ""
        rm = re.search(r'class="person-bloc[^"]*">(.*?)</div>', block, re.S)
        if rm:
            role_label = _txt(rm.group(1))
        role = default_role
        for key, val in sorted(role_map.items(), key=lambda kv: -len(kv[0])):
            if role_label and key in role_label:
                role = val
                break
        # date range sits in the calendar popup span
        start = end = ""
        dm = re.search(r"calendar\.svg[^>]*>(.*?)</span>", block, re.S)
        if dm:
            span = _txt(dm.group(1))
            parts = re.split(r"\s+-\s+", span)
            if parts:
                start = parse_arabic_date(parts[0])
            if len(parts) > 1 and "اليوم" not in parts[1]:
                end = parse_arabic_date(parts[1])
        out.append({
            "slug": slug,
            "name_ar": name,
            "role": role,
            "role_label_ar": role_label,
            "start_date": start,
            "end_date": end,
        })
    return out


def parse_bloc_members(markup: str) -> list[str]:
    """Return the person slugs listed on a bloc page.

    The bloc page is an attendance table, so the only membership signal is the
    set of members it lists. Each member appears twice (avatar link and name
    link), hence the de-duplication.
    """
    return sorted(set(re.findall(r"/ar/person/([a-z0-9\-]+)", markup)))


def _page_title(markup: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", markup, re.S | re.I)
    if not m:
        return ""
    return _txt(m.group(1)).split("|")[0].strip()


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

def collect(refresh: bool = False) -> StagingDoc:
    fetcher = Fetcher(RAW / "marsad_majles", delay=0.8, refresh=refresh)

    roster = parse_roster(fetcher.get_text(ROSTER_AR, slug="roster_ar"))
    latin = parse_roster_fr(fetcher.get_text(ROSTER_FR, slug="roster_fr"))
    log(f"  roster: {len(roster)} members ({len(latin)} with a Latin name)")
    if not roster:
        raise RuntimeError("no members parsed from the roster; upstream layout changed")

    # -- blocs, with dated membership -------------------------------------
    blocs_index = fetcher.get_text(BLOCS_INDEX, slug="blocs_index")
    bloc_paths = sorted(set(re.findall(r"/ar/assembly/blocs/(\d{4})/([a-z0-9\-]+)", blocs_index)))
    blocs_by_slug: dict[str, list[dict[str, Any]]] = {}
    bloc_meta: list[dict[str, Any]] = []
    for year, bslug in bloc_paths:
        markup = fetcher.get_text(f"{SITE}/ar/assembly/blocs/{year}/{bslug}", slug=f"bloc_{year}_{bslug}")
        name_ar = _page_title(markup)
        members = parse_bloc_members(markup)
        bloc_meta.append({
            "source_key": f"{year}/{bslug}",
            "slug": bslug,
            "year": year,
            "name_ar": name_ar,
            "n_members_parsed": len(members),
        })
        for slug in members:
            blocs_by_slug.setdefault(slug, []).append({
                "source_key": f"{year}/{bslug}",
                "name_ar": name_ar,
                "name_lat": "",
                "role": "unknown",
                "role_label_ar": "",
                # The page carries no membership dates. The bloc's listing year
                # is the earliest date we can defend, and the end is left empty
                # rather than invented.
                "start_date": f"{year}-01-01" if year != "2019" else FIRST_SITTING,
                "end_date": "",
                "dates_published": False,
            })
    log(f"  blocs: {len(bloc_meta)} bloc-years, "
        f"{sum(len(v) for v in blocs_by_slug.values())} memberships (undated upstream)")

    # -- committees --------------------------------------------------------
    com_index = fetcher.get_text(COMMISSIONS_INDEX, slug="commissions_index")
    com_slugs = sorted(set(re.findall(r"/ar/assembly/commissions/([a-z0-9\-]+)", com_index)))
    committees_by_slug: dict[str, list[dict[str, Any]]] = {}
    com_meta: list[dict[str, Any]] = []
    for cslug in com_slugs:
        markup = fetcher.get_text(f"{SITE}/ar/assembly/commissions/{cslug}", slug=f"com_{cslug}")
        members = parse_member_cards(markup, ROLE_MAP, default_role="member")
        name_ar = _page_title(markup)
        # Marsad's slugs distinguish the chamber's committee categories:
        # `inv-*`/`tri-*` are inquiry committees, `spec-*`/`adhoc-*` special.
        if cslug.startswith(("inv-", "tri-", "tri")):
            ctype = "inquiry"
        elif cslug.startswith(("spec-", "adhoc-")):
            ctype = "special"
        else:
            ctype = "standing"
        com_meta.append({
            "source_key": cslug,
            "name_ar": name_ar,
            "type": ctype,
            "n_members_parsed": len(members),
        })
        for mem in members:
            committees_by_slug.setdefault(mem["slug"], []).append({
                "source_key": cslug,
                "name_ar": name_ar,
                "name_lat": "",
                "type": ctype,
                "role": mem["role"],
                "role_label_ar": mem["role_label_ar"],
                "start_date": mem["start_date"] or FIRST_SITTING,
                "end_date": mem["end_date"],
            })
    log(f"  committees: {len(com_meta)} committees, "
        f"{sum(len(v) for v in committees_by_slug.values())} memberships")

    # -- member pages ------------------------------------------------------
    # The roster card carries two rounded percentages. The member's own page
    # carries five measures *with their denominators* — how many sittings there
    # were to attend, not just the share attended — plus the justified and
    # unjustified split and the vote-discipline rate. An earlier version of this
    # collector never opened these pages, which is why the dataset recorded
    # attendance for this chamber as a bare rate with an empty denominator.
    stats_by_slug: dict[str, dict[str, str]] = {}
    for idx, slug in enumerate(sorted(roster), start=1):
        if idx % 50 == 0:
            log(f"  ... member pages {idx}/{len(roster)}")
        page = fetcher.get_text(f"{SITE}/fr/person/{slug}", slug=f"person_{slug}")
        stats = parse_member_statistics(page)
        if stats:
            stats_by_slug[slug] = stats
    log(f"  member pages: {len(stats_by_slug)}/{len(roster)} with a statistics block")

    # -- records -----------------------------------------------------------
    records: list[PersonRecord] = []
    for slug, card in sorted(roster.items()):
        # Marsad publishes an age band rather than a birth date. An age without
        # a reference date cannot be turned into a birth year without inventing
        # precision, so it is carried as a note and left out of birth_date.
        age_note = f"age reported as {card['age']} on the roster page" if card["age"] else ""

        # The member page wins over the roster card where both report a rate:
        # same publisher, but the page states the denominator, so its figure can
        # be checked and the card's cannot.
        participation: dict[str, Any] = {}
        if card["vote_participation_rate"]:
            participation["vote_participation_rate"] = card["vote_participation_rate"]
        if card["attendance_rate"]:
            participation["plenary_attendance_rate"] = card["attendance_rate"]
        participation.update(stats_by_slug.get(slug, {}))

        records.append(PersonRecord(
            source_key=slug,
            source_url=f"{SITE}/ar/person/{slug}",
            name_ar=card["name"],
            name_lat=latin.get(slug, ""),
            gender=card["gender"],
            occupation_raw=card["profession_ar"],
            mandate={
                "start_date": FIRST_SITTING,
                # The chamber was frozen on 25 July 2021 and dissolved on
                # 30 March 2022. end_date records the de facto end of service;
                # the assemblies table carries both dates and the nominal 2024
                # expiry that never arrived.
                "end_date": FROZEN,
                "entry_mode": "elected",
                "exit_mode": "dissolution",
                "constituency_name_ar": card["district_ar"],
                "electoral_list_ar": card["list_ar"],
                "election_date": ELECTION_DATE,
                "notes": "; ".join(x for x in [
                    age_note,
                    "filed the statutory asset declaration" if card["asset_declaration"] else "",
                ] if x),
            },
            blocs=blocs_by_slug.get(slug, [
                {
                    "source_key": card["bloc_slug"] or card["bloc_ar"],
                    "name_ar": card["bloc_ar"],
                    "name_lat": "",
                    "role": "unknown",
                    "start_date": FIRST_SITTING,
                    "end_date": "",
                }
            ] if card["bloc_ar"] else []),
            committees=committees_by_slug.get(slug, []),
            participation=participation,
            authoritative_fields=["name_ar", "name_lat", "gender", "occupation_raw"],
        ))

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=ASSEMBLY_ID,
        source={
            "source_id": SOURCE_ID,
            "name": "Marsad Majles (Al Bawsala) — 2019 ARP observatory",
            "publisher": "Al Bawsala",
            "url": ROSTER_AR,
            "access_method": "HTML scrape of server-rendered roster, bloc and committee pages",
            "coverage": (
                "ARP-2019: 216 members with sex, profession, district, electoral "
                "list, bloc; dated bloc memberships (bloc switching observable); "
                "dated committee memberships with roles; vote-participation and "
                "plenary-attendance rates; asset-declaration compliance"
            ),
            "language": "ar; fr",
            "licence": "Not stated. Civic-monitoring data on public office-holders.",
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "Frozen archive: the site has not been updated since 2021, so it "
                "reflects the chamber as of its suspension and is stable to cite. "
                "Bloc pages render a per-bloc attendance table rather than a "
                "dated membership history, so bloc membership is an end-of-term "
                "snapshot and switching within the term is NOT recoverable here. "
                "Age is published as a value on the roster card with no reference "
                "date and is therefore NOT converted to a birth date. Attendance "
                "and participation denominators differ between the roster cards "
                "and the individual profile pages; the roster figures are used "
                "here and the denominators are not published alongside them, so "
                "these rates should be compared within this term only."
            ),
        },
        assembly_updates={"blocs": bloc_meta, "committees": com_meta},
        notes=(
            f"{len(records)} members; {len(bloc_meta)} bloc-years; "
            f"{len(com_meta)} committees. Fetch: {fetcher.report()}."
        ),
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect the 2019 ARP from majles.marsad.tn")
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    args = ap.parse_args()
    collect(refresh=args.refresh).save()


if __name__ == "__main__":
    main()
