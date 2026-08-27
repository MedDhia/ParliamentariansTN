"""Generate docs/CODEBOOK.md and docs/COVERAGE.md from the schema and the data.

Documentation that is written by hand drifts from the data it describes, and a
codebook that lies is worse than no codebook. Both files are therefore
generated: the variable definitions come from :mod:`parliamentarians_tn.schema`,
and every completeness figure is counted from the built CSVs at generation time.

Run ``python -m parliamentarians_tn.codebook`` after a build.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from typing import Any

from . import schema
from .io import DOCS, log, read_table, today


def _fill_rate(rows: list[dict[str, str]], column: str) -> tuple[int, float]:
    if not rows:
        return 0, 0.0
    n = sum(1 for r in rows if (r.get(column) or "").strip())
    return n, 100.0 * n / len(rows)


def codebook_markdown() -> str:
    out: list[str] = []
    add = out.append

    add("# Codebook")
    add("")
    add(
        "Generated from `src/parliamentarians_tn/schema.py` and the built data on "
        f"{today()}. Do not edit by hand — run `make codebook` instead."
    )
    add("")
    add("## Reading this codebook")
    add("")
    add(
        "**An empty cell means the value was not recorded by any source we consulted.** "
        "It never means zero, never means false, and never means the attribute does not "
        "apply. Coverage varies enormously across the seventy years the dataset spans, "
        "so a column that is 95 per cent complete for the sitting chamber may be empty "
        "for the single-party era; the fill rates below are computed over all rows and "
        "should be read alongside `docs/COVERAGE.md`, which breaks completeness down by "
        "chamber."
    )
    add("")
    add(
        "Dates are ISO 8601. Where a date is known only to the year, it is stored as "
        "1 January of that year and the companion `*_precision` column records `year`; "
        "treating such a value as a known day is a mistake the precision column exists "
        "to prevent."
    )
    add("")
    add(
        "Rates are proportions in [0, 1], not percentages. Denominators differ across "
        "sources and terms, so rates should not be compared across chambers without "
        "checking `sources.csv` for how each was computed."
    )
    add("")

    # -- table of contents
    add("## Tables")
    add("")
    add("| Table | Unit of observation | Rows |")
    add("| --- | --- | --- |")
    row_counts = {}
    for tbl in schema.TABLES:
        rows = read_table(tbl.name)
        row_counts[tbl.name] = len(rows)
        add(f"| [`{tbl.name}`](#{tbl.name}) | {tbl.unit} | {len(rows):,} |")
    add("")

    for tbl in schema.TABLES:
        rows = read_table(tbl.name)
        add(f"## `{tbl.name}`")
        add("")
        add(f"**Unit of observation.** {tbl.unit}")
        add("")
        add(tbl.description)
        add("")
        if tbl.primary_key:
            add(f"**Primary key.** `{', '.join(tbl.primary_key)}`")
            add("")
        if tbl.notes:
            add(f"**Notes.** {tbl.notes}")
            add("")
        add(f"**Rows.** {len(rows):,}")
        add("")
        add("| Variable | Type | Non-empty | Description |")
        add("| --- | --- | --- | --- |")
        for col in tbl.columns:
            n, pct = _fill_rate(rows, col.name)
            dtype = col.dtype
            if col.references:
                dtype += f" → `{col.references}`"
            flags = []
            if col.required:
                flags.append("required")
            if col.unique:
                flags.append("unique")
            desc = col.description
            if col.enum:
                desc += f" One of: {', '.join(f'`{e}`' for e in col.enum)}."
            if col.example:
                desc += f" Example: `{col.example}`."
            if flags:
                desc = f"*({', '.join(flags)})* " + desc
            fill = f"{n:,} ({pct:.0f}%)" if rows else "—"
            add(f"| `{col.name}` | {dtype} | {fill} | {desc} |")
        add("")

        # value distributions for small vocabularies, which is what an analyst
        # actually wants to see before using a categorical variable
        for col in tbl.columns:
            if col.dtype != "enum" or not rows:
                continue
            counts = Counter((r.get(col.name) or "").strip() for r in rows)
            counts.pop("", None)
            if not counts or len(counts) > 25:
                continue
            add(f"<details><summary>Distribution of <code>{col.name}</code></summary>")
            add("")
            add("| Value | n |")
            add("| --- | --- |")
            for val, n in counts.most_common():
                add(f"| `{val}` | {n:,} |")
            add("")
            add("</details>")
            add("")

    return "\n".join(out) + "\n"


def coverage_markdown() -> str:
    assemblies = read_table("assemblies")
    persons = {p["person_id"]: p for p in read_table("persons")}
    mandates = read_table("mandates")
    participation = read_table("participation")
    committee_mem = read_table("committee_memberships")
    bloc_mem = read_table("bloc_memberships")
    careers = read_table("careers")

    by_assembly: dict[str, list[dict[str, str]]] = defaultdict(list)
    for m in mandates:
        by_assembly[m["assembly_id"]].append(m)

    com_by_assembly = Counter(r["assembly_id"] for r in committee_mem)
    bloc_by_assembly = Counter(r["assembly_id"] for r in bloc_mem)
    part_by_assembly = Counter(r["assembly_id"] for r in participation)
    careers_by_person = {c["person_id"] for c in careers}

    out: list[str] = []
    add = out.append
    add("# Coverage")
    add("")
    add(f"Generated from the built data on {today()}. Run `make codebook` to refresh.")
    add("")
    add(
        "This is the document to read before using the dataset for anything "
        "comparative. Coverage is deeply uneven, and the unevenness is not random: it "
        "tracks what Tunisian institutions and civic monitors chose to publish, which "
        "in turn tracks the political openness of each period. Any analysis pooling "
        "across chambers is implicitly comparing well-documented democratic terms with "
        "barely-documented authoritarian ones, and needs to say so."
    )
    add("")

    add("## Person-level coverage by chamber")
    add("")
    add("| Chamber | Period | Seats | Mandates | % | Committee rows | Bloc rows | Behavioural rows | Status |")
    add("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for a in sorted(assemblies, key=lambda r: r.get("start_date") or "zzz"):
        aid = a["assembly_id"]
        seats = (a.get("seats_nominal") or "").strip()
        n = len(by_assembly.get(aid, []))
        pct = f"{100.0 * n / int(seats):.0f}%" if seats.isdigit() and int(seats) else "—"
        period = f"{(a.get('start_date') or '?')[:4]}–{(a.get('end_date') or '')[:4] or 'present'}"
        add(
            f"| `{aid}` | {period} | {seats or '?'} | {n} | {pct} | "
            f"{com_by_assembly.get(aid, 0)} | {bloc_by_assembly.get(aid, 0)} | "
            f"{part_by_assembly.get(aid, 0)} | {a.get('coverage_status', '')} |"
        )
    add("")

    add("## What `coverage_status` means")
    add("")
    add("- **`full`** — a roster covering essentially every seat is present.")
    add(
        "- **`frame_only`** — the chamber is described in `assemblies.csv` (dates, seats, "
        "electoral system, regime context) but few or no members are individually "
        "recorded. The chamber exists in the dataset as an institution, not as a set of "
        "people."
    )
    add("")

    add("## Attribute completeness, persons table")
    add("")
    add("| Attribute | Non-empty | of 682 persons |")
    add("| --- | --- | --- |")
    person_rows = list(persons.values())
    for col in ("name_ar", "name_lat", "gender", "birth_date", "birth_place_ar",
                "birth_governorate_id", "occupation_raw", "biography_ar",
                "marital_status", "languages", "education_raw", "wikidata_qid"):
        n, pct = _fill_rate(person_rows, col)
        add(f"| `{col}` | {n:,} | {pct:.0f}% |")
    add("")
    add(f"Persons with at least one extracted career row: {len(careers_by_person):,}.")
    add("")

    add("## Known gaps, in order of how much they matter")
    add("")
    add(
        "1. **1959–2011 has no rosters.** Eleven chambers across fifty-two years are "
        "represented only by their eight presiding officers. Neither the chamber's own "
        "database nor any civic monitor covers the single-party era, and no published "
        "list of members exists in machine-readable form. Closing this gap requires "
        "archival work in the *Journal Officiel*; `docs/RECONSTRUCTION_PROTOCOL.md` "
        "specifies how."
    )
    add(
        "2. **ARP-2014 is missing entirely.** This is the most painful gap because it is "
        "a democratic term sitting between two well-covered ones, and it breaks any "
        "continuous 2011–2023 panel. Al Bawsala's first observatory stops at 2014 and "
        "its second starts at 2019, while the chamber's own database restricts closed "
        "mandates to internal users. The data almost certainly exists; see the leads in "
        "`docs/SOURCES.md`."
    )
    add(
        "3. **Bloc switching is only partly observable.** Blocs are recorded as spells, "
        "but the sources publish end-of-term snapshots for 2011 and 2019, so "
        "within-term defection — central to explaining the fragmentation of both "
        "chambers — cannot be recovered from what is collected here. The 2023 chamber is "
        "the exception: `arp.tn` publishes appointment and departure dates, so switching "
        "*is* observable there."
    )
    add(
        "4. **Biography depth is thin for the sitting chamber.** The 2011–14 Constituent "
        "Assembly is by far the best-documented body: Al Bawsala published narrative "
        "biographies for all 217 members. The current chamber's own site exposes almost "
        "no biographical fields publicly, so birth dates and careers are largely absent "
        "for 2023 — the opposite of what one would expect from recency."
    )
    add(
        "5. **Career rows are rule-extracted from prose.** They carry "
        "`extraction_method='rule'` and a confidence grade. They are a starting point "
        "for hand-coding, not a finished career-history dataset, and the "
        "`shared_organisation` network layer inherits this uncertainty."
    )
    add("")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "CODEBOOK.md").write_text(codebook_markdown(), encoding="utf-8")
    (DOCS / "COVERAGE.md").write_text(coverage_markdown(), encoding="utf-8")
    log("wrote docs/CODEBOOK.md and docs/COVERAGE.md")


if __name__ == "__main__":
    main()
