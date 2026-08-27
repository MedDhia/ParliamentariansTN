"""Collector: the 1956 National Constituent Assembly, from Arabic Wikipedia.

The 1956 Constituent Assembly is the dataset's anchor: it is the first elected
Tunisian body, and the elite it seated supplied independent Tunisia's founding
cabinet. No institution publishes its roster in machine-readable form, and the
chamber's own successor (arp.tn) carries nothing before 2011. Arabic Wikipedia's
article, however, reproduces the full 98-member list by constituency, together
with the August 1956 by-elections that replaced ten members.

That makes this source uniquely valuable and also the dataset's weakest link
evidentially: it is an encyclopaedia, not a gazette. Everything collected here
is therefore written with ``match_confidence``/``confidence`` of ``medium``, and
docs/RECONSTRUCTION_PROTOCOL.md specifies the JORT verification each row still
needs. Two internal contradictions in the article are detected and reported
rather than silently resolved (see ``_reconcile_replacements``).
"""

from __future__ import annotations

import argparse
import re
from typing import Any

from ..io import Fetcher, RAW, log, today
from .base import PersonRecord, StagingDoc

SOURCE_ID = "WIKI_AR_ANC1956"
ASSEMBLY_ID = "ANC-1956"
PAGE = "المجلس القومي التأسيسي التونسي 1956"
API = "https://ar.wikipedia.org/w/api.php"
PAGE_URL = "https://ar.wikipedia.org/wiki/" + PAGE.replace(" ", "_")

# Election dates established by the article and corroborated by the standard
# secondary literature (Martin 2003, Histoire de la Tunisie contemporaine).
GENERAL_ELECTION = "1956-03-25"
BYELECTION = "1956-08-26"
FIRST_SITTING = "1956-04-08"
DISSOLUTION = "1959-06-01"


# ---------------------------------------------------------------------------
# wikitext helpers
# ---------------------------------------------------------------------------

def _strip_links(text: str) -> tuple[str, str]:
    """Return (display_text, wiki_title) for a wikitext fragment.

    ``[[عز الدين العباسي|عز الدين عباسي]]`` yields the piped display form and
    the article title, which is what we key on for later Wikidata linkage.
    """
    title = ""
    m = re.search(r"\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]", text)
    if m:
        title = m.group(1).strip()
        display = (m.group(2) or m.group(1)).strip()
        text = text[: m.start()] + display + text[m.end():]
    text = re.sub(r"\[\[([^\]\|]+\|)?([^\]]+)\]\]", r"\2", text)
    text = re.sub(r"\{\{[^}]*\}\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"''+", "", text)
    return text.strip(), title


def _is_file_cell(cell: str) -> bool:
    return bool(re.match(r"\s*\[\[\s*(ملف|File|صورة|Image)\s*:", cell))


def _split_cells(row: str) -> list[str]:
    """Split one wikitable row into cells, honouring both `|` and `||`."""
    cells: list[str] = []
    for line in row.split("\n"):
        line = line.strip()
        if not line or line.startswith("!"):
            continue
        if line.startswith("|"):
            line = line[1:]
        for part in line.split("||"):
            part = part.strip()
            if part:
                cells.append(part)
    return cells


REPLACED_INLINE = re.compile(r"\(\s*عوضه\s+([^)]+)\)")


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def _parse_member_table(wikitext: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse the members-by-constituency table.

    Returns (members, warnings). Each member carries name, wiki title,
    constituency, and any inline replacement note.
    """
    warnings: list[str] = []
    tables = re.findall(r"\{\|.*?\n\|\}", wikitext, re.S)
    target = None
    for t in tables:
        if "الدائرة" in t and t.count("|-") > 50:
            target = t
            break
    if target is None:
        raise RuntimeError("members-by-constituency table not found; upstream layout changed")

    members: list[dict[str, str]] = []
    for row in target.split("|-")[1:]:
        cells = _split_cells(row)
        cells = [c for c in cells if not _is_file_cell(c)]
        if len(cells) < 2:
            if cells:
                warnings.append(f"row with {len(cells)} usable cell(s) skipped: {cells!r:.80}")
            continue
        constituency, _ = _strip_links(cells[0])
        raw_name = cells[1]
        replaced_by = ""
        m = REPLACED_INLINE.search(raw_name)
        if m:
            replaced_by, _ = _strip_links(m.group(1))
            raw_name = REPLACED_INLINE.sub("", raw_name)
        name, title = _strip_links(raw_name)
        name = name.strip(" .،")
        if not name:
            continue
        members.append({
            "name_ar": name,
            "wiki_title": title,
            "constituency_ar": constituency,
            "inline_replaced_by": replaced_by,
        })
    return members, warnings


def _parse_byelection(wikitext: str) -> list[dict[str, str]]:
    """Parse the 'التغييرات والتعيينات' list of August 1956 replacements.

    Each bullet reads ``X، عوض Y`` — X took the seat of Y.
    """
    section = re.search(r"==\s*التغييرات والتعيينات\s*==(.*?)(?=\n==[^=])", wikitext, re.S)
    if not section:
        return []
    out = []
    for line in section.group(1).split("\n"):
        line = line.strip()
        if not line.startswith("*"):
            continue
        body = line.lstrip("* ").strip()
        if "عوض" not in body:
            continue
        successor_raw, predecessor_raw = body.split("عوض", 1)
        successor, s_title = _strip_links(successor_raw.strip(" ،"))
        predecessor, p_title = _strip_links(predecessor_raw.strip(" .،"))
        if successor and predecessor:
            out.append({
                "successor": successor,
                "successor_title": s_title,
                "predecessor": predecessor,
                "predecessor_title": p_title,
            })
    return out


def _parse_professions(wikitext: str) -> dict[str, int]:
    """Parse the aggregate occupational composition of the chamber.

    The article reports professions only as counts, not per member, so this is
    stored as an assembly-level attribute. It is still substantively useful: it
    is the only occupational profile available for any pre-2011 chamber.
    """
    section = re.search(r"===\s*الأعضاء حسب المهن\s*===(.*?)(?=\n==)", wikitext, re.S)
    if not section:
        return {}
    out: dict[str, int] = {}
    for m in re.finditer(r"\*\s*([^:*\n]+?)\s*:\s*(\d+)", section.group(1)):
        out[m.group(1).strip()] = int(m.group(2))
    return out


def _reconcile_replacements(
    members: list[dict[str, str]], byelection: list[dict[str, str]]
) -> list[str]:
    """Cross-check the table's inline replacement notes against the by-election list.

    The article contradicts itself: the roster table annotates Salah Bel Aiech
    as replaced by Ahmed Amara, while the by-election list has Ahmed Amara
    replacing Sheikh Ali Ben Aissa Bouhjar and Bahri Barbouch replacing Bel
    Aiech. We treat the dedicated by-election list as authoritative because it
    is the more specific claim, and surface the conflict instead of hiding it.
    """
    conflicts: list[str] = []
    by_pred = {r["predecessor"]: r["successor"] for r in byelection}
    for m in members:
        inline = m.get("inline_replaced_by")
        if not inline:
            continue
        listed = by_pred.get(m["name_ar"])
        if listed and listed != inline:
            conflicts.append(
                f"{m['name_ar']}: roster table says replaced by '{inline}', "
                f"by-election list says '{listed}' (by-election list preferred)"
            )
    return conflicts


# ---------------------------------------------------------------------------
# collection
# ---------------------------------------------------------------------------

def collect(refresh: bool = False) -> StagingDoc:
    fetcher = Fetcher(RAW / "wikipedia", delay=1.5, refresh=refresh)
    payload = fetcher.get_json(
        API,
        slug="anc1956_wikitext",
        params={"action": "parse", "page": PAGE, "prop": "wikitext", "format": "json"},
    )
    wikitext = payload["parse"]["wikitext"]["*"]

    members, warnings = _parse_member_table(wikitext)
    byelection = _parse_byelection(wikitext)
    professions = _parse_professions(wikitext)
    conflicts = _reconcile_replacements(members, byelection)

    for w in warnings:
        log(f"  warning: {w}")
    for c in conflicts:
        log(f"  CONFLICT {c}")
    log(f"  parsed {len(members)} seated members, {len(byelection)} by-election replacements")

    replaced = {r["predecessor"] for r in byelection}
    records: list[PersonRecord] = []

    for i, m in enumerate(members, start=1):
        vacated = m["name_ar"] in replaced
        records.append(PersonRecord(
            source_key=m["wiki_title"] or f"anc1956-seat-{i:03d}",
            source_url=(
                "https://ar.wikipedia.org/wiki/" + m["wiki_title"].replace(" ", "_")
                if m["wiki_title"] else PAGE_URL
            ),
            name_ar=m["name_ar"],
            mandate={
                "start_date": FIRST_SITTING,
                # Members whose seat was filled at the by-election left before
                # the chamber's dissolution; the exact date is not recorded.
                "end_date": BYELECTION if vacated else DISSOLUTION,
                "entry_mode": "elected",
                "exit_mode": "unknown" if vacated else "end_of_term",
                "constituency_name_ar": m["constituency_ar"],
                "election_date": GENERAL_ELECTION,
                "electoral_list_ar": "الجبهة الوطنية",
                "electoral_list_lat": "Front National",
                "party_name_ar": "الحزب الحر الدستوري الجديد",
                "notes": (
                    "seat vacated before dissolution; filled at the 26 Aug 1956 "
                    "by-election. Article attributes the vacancies collectively to "
                    "six governor appointments, one délégué appointment and two deaths, "
                    "without naming which member fell in which category."
                ) if vacated else "",
            },
            authoritative_fields=["name_ar"],
        ))

    # A by-election fills the seat that fell vacant, so the successor inherits
    # the predecessor's constituency. This is an inference, not a stated fact,
    # and is flagged as such in the mandate note.
    constituency_by_member = {m["name_ar"]: m["constituency_ar"] for m in members}

    for r in byelection:
        inherited = constituency_by_member.get(r["predecessor"], "")
        records.append(PersonRecord(
            source_key=r["successor_title"] or f"anc1956-by-{r['successor']}",
            source_url=(
                "https://ar.wikipedia.org/wiki/" + r["successor_title"].replace(" ", "_")
                if r["successor_title"] else PAGE_URL
            ),
            name_ar=r["successor"],
            mandate={
                "start_date": BYELECTION,
                "end_date": DISSOLUTION,
                "entry_mode": "elected_byelection",
                "exit_mode": "end_of_term",
                "constituency_name_ar": inherited,
                "election_date": BYELECTION,
                "electoral_list_ar": "الجبهة الوطنية",
                "electoral_list_lat": "Front National",
                "party_name_ar": "الحزب الحر الدستوري الجديد",
                "notes": (
                    f"took the seat of {r['predecessor']} at the 26 Aug 1956 by-election"
                    + ("; constituency inferred from the predecessor's seat, not stated by the source"
                       if inherited else "; predecessor not found in the roster table, constituency unknown")
                ),
            },
            authoritative_fields=["name_ar"],
        ))

    # Presiding officers, from the article's dedicated section.
    for name, start, end, label in [
        ("الحبيب بورقيبة", "1956-04-09", "1956-04-15", "رئيس المجلس القومي التأسيسي"),
        ("الجلولي فارس", "1956-04-15", DISSOLUTION, "رئيس المجلس القومي التأسيسي"),
    ]:
        for rec in records:
            if rec.name_ar == name:
                rec.offices.append({
                    "office": "speaker",
                    "office_label_ar": label,
                    "start_date": start,
                    "end_date": end,
                    "notes": (
                        "Bourguiba was elected speaker on 9 April 1956 and vacated "
                        "the chair on becoming prime minister; the article does not "
                        "date the handover, so 15 April 1956 is an approximation."
                    ) if name == "الحبيب بورقيبة" else "",
                })
                break

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=ASSEMBLY_ID,
        source={
            "source_id": SOURCE_ID,
            "name": "Arabic Wikipedia — 1956 Tunisian National Constituent Assembly",
            "publisher": "Wikimedia Foundation (community-authored)",
            "url": PAGE_URL,
            "access_method": "MediaWiki action=parse API, wikitext",
            "coverage": "ANC-1956: full 98-member roster with constituencies; Aug 1956 by-elections; presiding officers; aggregate occupational composition",
            "language": "ar",
            "licence": "CC BY-SA 4.0",
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "Tertiary source. Names and constituencies are reproduced from "
                "Martin (2003) and Ghorbal (2011) but are not individually "
                "footnoted. The article contradicts itself on which member Ahmed "
                "Amara replaced. No birth dates, occupations or biographies are "
                "given per member. All rows require JORT verification before use "
                "as evidence; see docs/RECONSTRUCTION_PROTOCOL.md."
            ),
        },
        assembly_updates={
            "occupational_composition": professions,
            "internal_conflicts": conflicts,
            "n_seated_parsed": len(members),
            "n_byelection_parsed": len(byelection),
        },
        notes=(
            f"Parsed {len(members)} seated members and {len(byelection)} by-election "
            f"replacements. {len(conflicts)} internal contradiction(s) detected and "
            "recorded rather than resolved."
        ),
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    args = ap.parse_args()
    collect(refresh=args.refresh).save()


if __name__ == "__main__":
    main()
