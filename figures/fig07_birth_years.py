"""Figure 7 — Birth years of the 2011 constituent assembly.

A distribution, so: a histogram, one hue, no legend. Restricted to the 2011
Constituent Assembly because it is the only chamber with real birth dates for a
substantial share of members — Al Bawsala published narrative biographies for all
217, and 156 of them state a date of birth.

This figure is deliberately *not* drawn for the other chambers, and the reason is
worth stating on the figure: the 2014 and 2019 sources publish an age with no
reference date, which fixes a birth year only to within a year, so the dataset
preserves the raw age rather than converting it. A histogram of ages silently
converted to birth years would look identical to this one and be partly fictional.

The median line is the one direct label: the assembly that wrote the 2014
constitution was, at the time it sat, a middle-aged body.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
FIRST_SITTING_YEAR = 2011


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    members = [persons[m["person_id"]] for m in S.load("mandates")
               if m["assembly_id"] == ASSEMBLY]

    years, precision = [], {"day": 0, "year": 0, "other": 0}
    for p in members:
        birth = p["birth_date"]
        if not birth:
            continue
        years.append(int(birth[:4]))
        key = p["birth_date_precision"]
        precision[key if key in precision else "other"] += 1

    median_year = statistics.median(years)
    fig, ax = plt.subplots(figsize=S.figsize(7.4, 4.2))
    blue = S.categorical(1)[0]

    lo, hi = min(years), max(years)
    bins = range(lo - lo % 5, hi + 6, 5)
    ax.hist(years, bins=list(bins), color=blue, linewidth=0)

    ax.axvline(median_year, color=S.CHROME["muted"], linewidth=1.0, zorder=3)
    ax.annotate(
        f"median birth year {median_year:.0f}\n"
        f"({FIRST_SITTING_YEAR - median_year:.0f} years old at the first sitting)",
        xy=(median_year, ax.get_ylim()[1]), xytext=(7, -8),
        textcoords="offset points", ha="left", va="top", fontsize=7.8,
        color=S.CHROME["text_secondary"], linespacing=1.35,
    )

    S.frame(ax)
    S.integer_axis(ax, "y")
    S.titles(
        ax,
        "Birth years, 2011 Constituent Assembly",
        f"{len(years)} of {len(members)} members state a date of birth "
        f"({precision['day']} to the day, {precision['year']} to the year only).\n"
        "Drawn for this chamber alone: the 2014 and 2019 sources publish an age with no "
        "reference date, which the dataset preserves rather than converting.",
        ylabel="Members",
        xlabel="Year of birth (5-year bins)",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/persons.csv (birth_date)")

    counts: dict[str, int] = {}
    edges = list(bins)
    for i in range(len(edges) - 1):
        label = f"{edges[i]}–{edges[i + 1] - 1}"
        counts[label] = sum(1 for y in years if edges[i] <= y < edges[i + 1])
    S.save(fig, "fig07_birth_years",
           [{"birth_year_bin": k, "members": v} for k, v in counts.items()])


if __name__ == "__main__":
    main()
