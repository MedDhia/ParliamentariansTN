"""Validate the built dataset against the schema and against substantive logic.

Two kinds of check run here, and the distinction matters:

**Errors** are things that make the dataset wrong as data — a dangling foreign
key, a duplicate primary key, a value outside its declared vocabulary, an end
date before its start date. These fail the build.

**Warnings** are things that are suspicious but may be true of the world. A
chamber with more mandates than seats is usually a coding error, but it is also
what genuinely happens when members are replaced mid-term. A mandate starting
before its assembly's first sitting looks wrong but is correct for the ARP,
whose members' mandates begin at their election. Warnings are reported and
counted, never silently dropped, and never treated as failures.

Run ``python -m parliamentarians_tn.validate`` after a build. Exit status is 1
if any error was found, so this works as a CI gate.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from typing import Any

from . import schema
from .io import PROCESSED, log

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
BOOL_OK = {"", "true", "false"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def note(self, msg: str) -> None:
        self.notes.append(msg)

    def summary(self) -> str:
        return f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)"


def _load(name: str) -> list[dict[str, str]]:
    path = PROCESSED / f"{name}.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _valid_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    year, month, day = (int(x) for x in value.split("-"))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return False
    return 1850 <= year <= 2100


def check_schema(report: Report, tables: dict[str, list[dict[str, str]]]) -> None:
    for tbl in schema.TABLES:
        rows = tables.get(tbl.name)
        if rows is None:
            report.warn(f"{tbl.name}: table file missing")
            continue
        if not rows:
            report.note(f"{tbl.name}: empty")
            continue

        actual = set(rows[0].keys())
        expected = set(tbl.column_names)
        if actual - expected:
            report.error(f"{tbl.name}: unexpected column(s) {sorted(actual - expected)}")
        if expected - actual:
            report.error(f"{tbl.name}: missing column(s) {sorted(expected - actual)}")

        for col in tbl.columns:
            if col.name not in actual:
                continue
            missing = 0
            for i, row in enumerate(rows, start=2):
                val = (row.get(col.name) or "").strip()
                if not val:
                    if col.required:
                        missing += 1
                    continue
                if col.dtype == "date" and not _valid_date(val):
                    report.error(f"{tbl.name} row {i}: {col.name}={val!r} is not a valid ISO date")
                elif col.dtype == "integer":
                    if not re.match(r"^-?\d+$", val):
                        report.error(f"{tbl.name} row {i}: {col.name}={val!r} is not an integer")
                elif col.dtype == "number":
                    try:
                        float(val)
                    except ValueError:
                        report.error(f"{tbl.name} row {i}: {col.name}={val!r} is not numeric")
                elif col.dtype == "boolean" and val not in BOOL_OK:
                    report.error(f"{tbl.name} row {i}: {col.name}={val!r} is not a boolean")
                elif col.dtype == "enum" and col.enum and val not in col.enum:
                    report.error(
                        f"{tbl.name} row {i}: {col.name}={val!r} outside vocabulary "
                        f"{list(col.enum)[:6]}{'...' if len(col.enum) > 6 else ''}"
                    )
            if missing:
                report.error(f"{tbl.name}: {missing} row(s) missing required {col.name}")

        # primary keys
        if tbl.primary_key and all(k in actual for k in tbl.primary_key):
            keys = [tuple(r.get(k, "") for k in tbl.primary_key) for r in rows]
            dupes = [k for k, n in Counter(keys).items() if n > 1]
            if dupes:
                report.error(
                    f"{tbl.name}: {len(dupes)} duplicate primary key(s), e.g. {dupes[:3]}"
                )


def check_references(report: Report, tables: dict[str, list[dict[str, str]]]) -> None:
    # Build the set of valid values for every referenced column.
    universe: dict[str, set[str]] = {}
    for tbl in schema.TABLES:
        for col in tbl.columns:
            universe.setdefault(f"{tbl.name}.{col.name}",
                                {(r.get(col.name) or "") for r in tables.get(tbl.name, [])})

    for tbl in schema.TABLES:
        rows = tables.get(tbl.name, [])
        if not rows:
            continue
        for col in tbl.columns:
            if not col.references or col.name not in rows[0]:
                continue
            valid = universe.get(col.references, set())
            if not valid:
                continue
            bad: Counter[str] = Counter()
            for row in rows:
                raw = (row.get(col.name) or "").strip()
                if not raw:
                    continue
                # source_ids columns hold semicolon-separated lists
                values = raw.split(";") if col.name.endswith("_ids") else [raw]
                for val in values:
                    val = val.strip()
                    if val and val not in valid:
                        bad[val] += 1
            if bad:
                report.error(
                    f"{tbl.name}.{col.name} -> {col.references}: "
                    f"{sum(bad.values())} dangling reference(s), e.g. {list(bad)[:3]}"
                )


def check_dates(report: Report, tables: dict[str, list[dict[str, str]]]) -> None:
    spans = [
        ("assemblies", "assembly_id", "start_date", "end_date"),
        ("mandates", "mandate_id", "start_date", "end_date"),
        ("bloc_memberships", "bloc_membership_id", "start_date", "end_date"),
        ("committee_memberships", "committee_membership_id", "start_date", "end_date"),
        ("offices", "office_id", "start_date", "end_date"),
        ("careers", "career_id", "start_date", "end_date"),
        ("party_affiliations", "affiliation_id", "start_date", "end_date"),
    ]
    for name, key, start_col, end_col in spans:
        for row in tables.get(name, []):
            start, end = (row.get(start_col) or ""), (row.get(end_col) or "")
            if start and end and _valid_date(start) and _valid_date(end) and end < start:
                report.error(f"{name} {row.get(key)}: {end_col} {end} precedes {start_col} {start}")

    # vital dates
    for row in tables.get("persons", []):
        birth, death = (row.get("birth_date") or ""), (row.get("death_date") or "")
        if birth and death and _valid_date(birth) and _valid_date(death) and death < birth:
            report.error(f"persons {row['person_id']}: death {death} precedes birth {birth}")
        first = row.get("first_mandate_start") or ""
        if birth and first and _valid_date(birth) and _valid_date(first):
            age = (int(first[:4]) - int(birth[:4]))
            if age < 18:
                report.warn(
                    f"persons {row['person_id']}: first mandate at apparent age {age}"
                )
            if age > 90:
                report.warn(
                    f"persons {row['person_id']}: first mandate at apparent age {age}"
                )


def check_substance(report: Report, tables: dict[str, list[dict[str, str]]]) -> None:
    assemblies = {r["assembly_id"]: r for r in tables.get("assemblies", [])}
    mandates = tables.get("mandates", [])

    # one person should not hold two mandates in the same chamber
    seen: dict[tuple[str, str], int] = Counter()
    for m in mandates:
        seen[(m["person_id"], m["assembly_id"])] += 1
    dupes = {k: v for k, v in seen.items() if v > 1}
    if dupes:
        report.error(
            f"mandates: {len(dupes)} person-assembly pair(s) appear more than once, "
            f"e.g. {list(dupes)[:3]}"
        )

    # mandate counts against nominal seats
    per_assembly = Counter(m["assembly_id"] for m in mandates)
    for assembly_id, count in sorted(per_assembly.items()):
        a = assemblies.get(assembly_id)
        if not a:
            continue
        seats = (a.get("seats_nominal") or "").strip()
        if seats.isdigit() and count > int(seats):
            report.warn(
                f"{assembly_id}: {count} mandates for {seats} nominal seats "
                "(expected where members were replaced mid-term)"
            )
        coverage = a.get("coverage_status", "")
        if coverage == "full" and seats.isdigit() and count < int(seats) * 0.9:
            report.warn(
                f"{assembly_id}: coverage_status='full' but only {count} of {seats} "
                "seats have a mandate"
            )

    # mandates outside their assembly's dates
    outside = 0
    for m in mandates:
        a = assemblies.get(m["assembly_id"])
        if not a or not m.get("start_date"):
            continue
        a_start, a_end = a.get("start_date") or "", a.get("end_date") or ""
        if a_start and m["start_date"] < a_start:
            outside += 1
        elif a_end and m["start_date"] > a_end:
            outside += 1
    if outside:
        report.warn(
            f"mandates: {outside} mandate(s) start outside their assembly's sitting dates "
            "(correct where a mandate is dated from the election rather than the first sitting)"
        )

    # rates must be proportions
    for row in tables.get("participation", []):
        for field in ("plenary_attendance_rate", "committee_attendance_rate",
                      "vote_participation_rate", "vote_discipline_rate"):
            val = (row.get(field) or "").strip()
            if not val:
                continue
            try:
                num = float(val)
            except ValueError:
                continue
            if not 0.0 <= num <= 1.0:
                report.error(
                    f"participation {row['person_id']}/{row['assembly_id']}: "
                    f"{field}={val} is not a proportion in [0,1]"
                )

    # every person should have at least one mandate
    with_mandate = {m["person_id"] for m in mandates}
    orphans = [r["person_id"] for r in tables.get("persons", []) if r["person_id"] not in with_mandate]
    if orphans:
        report.warn(f"persons: {len(orphans)} person(s) with no mandate, e.g. {orphans[:3]}")

    # coverage summary, for the reader's benefit
    report.note("person-level coverage by chamber:")
    for assembly_id, a in sorted(assemblies.items(), key=lambda kv: kv[1].get("start_date") or ""):
        count = per_assembly.get(assembly_id, 0)
        seats = a.get("seats_nominal") or "?"
        report.note(
            f"    {assembly_id:12s} {count:4d} / {seats:>4} seats  "
            f"[{a.get('coverage_status', '')}]"
        )


def validate() -> Report:
    tables = {tbl.name: _load(tbl.name) for tbl in schema.TABLES}
    report = Report()
    check_schema(report, tables)
    check_references(report, tables)
    check_dates(report, tables)
    check_substance(report, tables)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="only print the summary")
    args = ap.parse_args()

    report = validate()
    if not args.quiet:
        for note in report.notes:
            print(note)
        for warning in report.warnings:
            print(f"WARNING  {warning}")
        for error in report.errors:
            print(f"ERROR    {error}")
    print(f"\nvalidation: {report.summary()}")
    sys.exit(1 if report.errors else 0)


if __name__ == "__main__":
    main()
