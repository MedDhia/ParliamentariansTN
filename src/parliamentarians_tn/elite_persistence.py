"""The parliamentarians, reduced to surnames, for the elite-persistence comparison.

The comparison is assembled in EliteNetworksTN and asks whether the families the
Tunisian genealogies record hold position out of proportion to their share of
the population, and whether that has survived the changes of regime. The
denominator is the 2024 electoral register, built in ElectionsTN. This module
supplies two of the numerators: everyone who has sat in a chamber, and the
party each of them sat for.

What this layer can and cannot carry
------------------------------------
The chambers are covered very unevenly, and the unevenness is not random: it is
the single-party era that is missing. Of nineteen chamber-terms, six have a
roster -- 1956, 2005, 2011, 2014, 2019 and 2023 -- and the thirteen between
1959 and 2009 are in the data as institutions with no people in them. See
`docs/COVERAGE.md`. So this layer can compare the constituent assembly of 1956
against the assemblies of the transition and of the Third Republic, and it
cannot say anything about the Neo-Destour and RCD chambers in between. A reader
who wants the Bourguiba and Ben Ali periods has to take them from the ministers
in GovMembersTN, which do cover them, and accept that ministers and deputies
are not the same selection.

Why one row per person per chamber
----------------------------------
The question is about persistence, so the unit is the member *in a chamber*: a
deputy returned in 2011 and again in 2014 is evidence about both. Deduplicate
on `person_id` for a headcount of the 968 individuals.

Which name is read
------------------
`persons.csv` gives a split `family_name_ar` for only 154 of the 968, and a
full `name_ar` for all of them, so the surname is found by reading the full
name -- last token plus whatever particles bind onto it. `surname_spine.py`
does that, and it is the same file, byte for byte, that ElectionsTN uses on the
register and GovMembersTN on the ministers.

What is written
---------------
`data/processed/elite_persistence/`

`layer_legislators.csv`
    one row per member per chamber, in the schema the four repositories share.
`layer_party_affiliations.csv`
    one row per member per party, pooled from the three places the party is
    recorded: the affiliation table, the bloc they sat in, and the list they
    were elected on. Parties are a subgroup of the same people, not a separate
    population: no Tunisian party membership roll is public, so nothing here
    speaks to party membership at large.

Surnames are written as *candidates*, longest first, rather than resolved: only
the register can say whether `بن سالم` is a family in its own right, and this
repository does not hold the register.

Run with::

    python3 -m parliamentarians_tn.elite_persistence     # or: make elite-persistence

Standard library only, about a second, byte-identical on every run.
"""

from __future__ import annotations

import collections
import csv
import sys
from pathlib import Path

try:
    from .surname_spine import is_arabic, family_candidates, spine
except ImportError:                                      # run as a bare script
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from surname_spine import is_arabic, family_candidates, spine

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "elite_persistence"

PERSONS = PROCESSED / "persons.csv"
MANDATES = PROCESSED / "mandates.csv"
ASSEMBLIES = PROCESSED / "assemblies.csv"
PARTIES = PROCESSED / "parties.csv"
BLOCS = PROCESSED / "blocs.csv"
BLOC_MEMBERSHIPS = PROCESSED / "bloc_memberships.csv"
PARTY_AFFILIATIONS = PROCESSED / "party_affiliations.csv"

LAYER_FIELDS = [
    "layer", "person_id", "name_raw", "script",
    "surname_candidates", "spine_candidates", "period", "subgroup",
    "assembly_id", "coverage_status", "entry_mode", "gender",
]

PARTY_FIELDS = [
    "layer", "person_id", "name_raw", "script",
    "surname_candidates", "spine_candidates", "period", "subgroup",
    "party_id", "party_name", "evidence",
]


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _surname_columns(name: str) -> dict:
    cands = family_candidates(name)
    return {
        "script": "ar" if is_arabic(name) else "lat",
        "surname_candidates": "|".join(cands),
        "spine_candidates": "|".join(spine(c) for c in cands),
    }


def build_legislators(persons, mandates, assemblies) -> list[dict]:
    rows = []
    for m in mandates:
        p = persons.get(m["person_id"])
        if not p:
            continue
        name = (p["name_ar"] or p["name_lat"] or "").strip()
        if not name:
            continue
        a = assemblies.get(m["assembly_id"], {})
        rows.append({
            "layer": "legislators",
            "person_id": m["person_id"],
            "name_raw": name,
            **_surname_columns(name),
            # The chamber's own regime period, this repository's vocabulary.
            # EliteNetworksTN maps it onto the shared periods.
            "period": a.get("regime_period", ""),
            "subgroup": m["electoral_list_lat"] or m["electoral_list_ar"] or "",
            "assembly_id": m["assembly_id"],
            "coverage_status": a.get("coverage_status", ""),
            "entry_mode": m["entry_mode"],
            "gender": p["gender"],
        })
    return sorted(rows, key=lambda r: (r["assembly_id"], r["person_id"]))


def build_party_affiliations(persons, mandates, assemblies, parties, blocs,
                             bloc_memberships, affiliations) -> list[dict]:
    """One row per member per party, from the three places a party is recorded.

    None of the three is complete on its own: the affiliation table covers the
    2011 constituent assembly, the bloc table covers the chambers Al Bawsala
    observed, and the electoral list is recorded wherever the mandate came from
    an election on a list -- which the 2023 chamber, elected on individual
    candidacies, has none of. Pooling them and naming the evidence for each row
    is the honest form: it says which members have a party attached and why,
    rather than implying a register that does not exist.
    """
    seen: dict[tuple[str, str], dict] = {}

    def add(person_id, party_id, party_name, period, evidence):
        p = persons.get(person_id)
        name = (p or {}).get("name_ar") or (p or {}).get("name_lat") or ""
        if not p or not name.strip() or not party_name:
            return
        key = (person_id, party_name)
        if key in seen:
            if evidence not in seen[key]["evidence"]:
                seen[key]["evidence"] += f"|{evidence}"
            return
        seen[key] = {
            "layer": "party_affiliations",
            "person_id": person_id,
            "name_raw": name,
            **_surname_columns(name),
            "period": period,
            "subgroup": party_name,
            "party_id": party_id,
            "party_name": party_name,
            "evidence": evidence,
        }

    def party_name(pid):
        p = parties.get(pid, {})
        return (p.get("name_fr") or p.get("name_ar") or "").strip()

    person_period = {}
    for m in mandates:
        period = assemblies.get(m["assembly_id"], {}).get("regime_period", "")
        person_period.setdefault(m["person_id"], period)

    for a in affiliations:
        add(a["person_id"], a["party_id"], party_name(a["party_id"]),
            person_period.get(a["person_id"], ""), "affiliation")
    for b in bloc_memberships:
        bloc = blocs.get(b["bloc_id"], {})
        pid = bloc.get("party_id", "")
        name = party_name(pid) or (bloc.get("name_lat") or bloc.get("name_ar") or "")
        add(b["person_id"], pid, name.strip(),
            assemblies.get(b["assembly_id"], {}).get("regime_period", ""), "bloc")
    for m in mandates:
        name = (m["electoral_list_lat"] or m["electoral_list_ar"] or "").strip()
        add(m["person_id"], m["party_id_at_election"], name,
            assemblies.get(m["assembly_id"], {}).get("regime_period", ""), "list")

    return [seen[k] for k in sorted(seen)]


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    persons = {r["person_id"]: r for r in _read(PERSONS)}
    mandates = _read(MANDATES)
    assemblies = {r["assembly_id"]: r for r in _read(ASSEMBLIES)}
    parties = {r["party_id"]: r for r in _read(PARTIES)}
    blocs = {r["bloc_id"]: r for r in _read(BLOCS)}

    legislators = build_legislators(persons, mandates, assemblies)
    _write(OUT / "layer_legislators.csv", LAYER_FIELDS, legislators)

    affiliations = build_party_affiliations(
        persons, mandates, assemblies, parties, blocs,
        _read(BLOC_MEMBERSHIPS), _read(PARTY_AFFILIATIONS))
    _write(OUT / "layer_party_affiliations.csv", PARTY_FIELDS, affiliations)

    people = {r["person_id"] for r in legislators}
    print(f"wrote {(OUT / 'layer_legislators.csv').relative_to(ROOT)}")
    print(f"  {len(legislators):,} member-chamber rows over {len(people):,} people")
    print("  by chamber (only the six with a roster carry people):")
    by_asm = collections.Counter(r["assembly_id"] for r in legislators)
    for asm, n in sorted(by_asm.items(), key=lambda kv: -kv[1]):
        a = assemblies.get(asm, {})
        print(f"    {asm:<12} {n:>4}  {a.get('regime_period', ''):<24}"
              f"{a.get('coverage_status', '')}")

    party_people = {r["person_id"] for r in affiliations}
    print(f"\nwrote {(OUT / 'layer_party_affiliations.csv').relative_to(ROOT)}")
    print(f"  {len(affiliations):,} member-party rows over {len(party_people):,} "
          f"people ({len(party_people) / len(people):.0%} of those who sat)")
    ev = collections.Counter(e for r in affiliations for e in r["evidence"].split("|"))
    print(f"  evidence: {dict(ev)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
