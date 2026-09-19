"""How much does the Latin-spelling rule move the dataset?

`build.py` merges two records when their normalised Arabic names agree.
Requiring the romanisations to agree as well was the rule here until the eleven
records it held apart were read individually and every one proved to be the
same person twice. This script builds the dataset both ways in one process —
the current default, and `--strict-latin-match` — and diffs them, so the size
of that correction stays checkable instead of being taken on trust.

    python examples/latin_veto_impact.py

**Why the old rule misfired.** French transliteration of Tunisian Arabic is not
standardised, and the two civic monitors this dataset draws on romanise
independently. *Khmais* and *Khemais*, *Iyed* and *Iyad*, *Ibrahim* and
*Brahim*, *Ouej* and *Elouej* are one name each; the Arabic strings behind them
are byte-identical after normalisation. So the guard fired precisely where the
Arabic evidence was strongest, and split one deputy into two people.

**Why that was not a cosmetic problem.** A split person cannot be observed
returning to parliament, so every re-election, every career length and every
elite-circulation measure was biased downward — and the dataset still looked
well formed, which is what made the error dangerous rather than merely wrong.

**What this does not settle.** The script shows the rule was costing real
merges; it cannot prove each merge is correct. Every one is a claim about
identity that a birth date would settle and a name cannot, and only 158 of 957
persons carry one. The eleven are listed individually in
`data/processed/_latin_veto_report.csv`; that file, not this summary, is where
a disputed case gets settled.
"""

from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parliamentarians_tn.build import build  # noqa: E402

# The post-2011 chambers in order. Continuity is only measurable here: the
# single-party era has no rosters, so a career cannot be traced through it.
SEQ = ("NCA-2011", "ARP-2014", "ARP-2019", "ARP-2023")


def profile(builder) -> dict:
    """Reduce a build to the quantities the veto can move."""
    held = collections.defaultdict(set)
    members = collections.defaultdict(set)
    for row in builder.mandates:
        held[row["person_id"]].add(row["assembly_id"])
        members[row["assembly_id"]].add(row["person_id"])
    return {
        "persons": len(builder.person_rows()),
        "mandates": len(builder.mandates),
        "multi_chamber": sum(1 for a in held.values() if len(a) > 1),
        "returns": {
            (SEQ[i - 1], SEQ[i]): (
                len(members[SEQ[i]] & members[SEQ[i - 1]]), len(members[SEQ[i]])
            )
            for i in range(1, len(SEQ))
        },
    }


def main() -> None:
    held = profile(build(relax_latin_veto=False, write=False))
    relaxed_builder = build(relax_latin_veto=True, write=False)
    relaxed = profile(relaxed_builder)

    print("\nthe eleven merges the old rule refused")
    print("-" * 78)
    for veto in relaxed_builder.latin_vetoes:
        print(f"  {veto['kept_name_lat']:<20} = {veto['incoming_name_lat']:<20} "
              f"{veto['kept_assembly_id']} / {veto['incoming_assembly_id']}")

    print("\nstrict Latin matching (old) -> Arabic key decides (current)")
    print("-" * 78)
    for label, key in (("persons", "persons"), ("mandate rows", "mandates"),
                       ("people in >1 chamber", "multi_chamber")):
        before, after = held[key], relaxed[key]
        print(f"  {label:<24} {before:>6} -> {after:>6}  ({after - before:+d})")

    print("\nreturning members, chamber to chamber")
    print("-" * 78)
    for pair in held["returns"]:
        (r0, n0), (r1, n1) = held["returns"][pair], relaxed["returns"][pair]
        print(f"  {pair[0]} -> {pair[1]}: {r0}/{n0} ({r0 / n0 * 100:.0f}%)"
              f"  ->  {r1}/{n1} ({r1 / n1 * 100:.0f}%)")

    gained = relaxed["multi_chamber"] - held["multi_chamber"]
    print(f"\nThe old rule suppressed {gained} multi-chamber careers, "
          f"{gained / relaxed['multi_chamber'] * 100:.0f}% of the "
          f"{relaxed['multi_chamber']} the current build finds.")


if __name__ == "__main__":
    main()
