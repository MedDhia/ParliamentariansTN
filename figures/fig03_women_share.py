"""Figure 3 — Women's share of each chamber, where sex is recorded.

Only five chambers have person-level sex, so this is five bars, not a time series
pretending to nineteen. One series, one hue: colouring bars by their own height
would double-encode what the axis already says.

The parity reference line is the point of the figure. Tunisia's 2011 electoral
law required vertical parity on candidate lists, and the three chambers elected
under it sit between a quarter and a third women. The 2023 chamber, elected in
single-member districts where a list-parity rule has nothing to act on, sits at
15 per cent — a halving against 2014.

Sex for the 2011 chamber is inferred from French grammatical agreement in each
member's own biography, not recorded by the source; the subtitle says so, because
a figure that leans on an inferred variable should say it on the figure.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

INFERRED = {"NCA-2011"}


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    order = [a["assembly_id"] for a in S.assemblies_in_order()]

    by_chamber: dict[str, list[str]] = defaultdict(list)
    for m in S.load("mandates"):
        gender = persons[m["person_id"]]["gender"]
        if gender in ("male", "female"):
            by_chamber[m["assembly_id"]].append(gender)

    # A chamber with a handful of known members (the pre-2011 speakers) would
    # produce a meaningless percentage; require a real roster.
    rows = [(a, by_chamber[a]) for a in order if len(by_chamber.get(a, [])) >= 50]

    fig, ax = plt.subplots(figsize=S.figsize(7.2, 4.3))
    blue = S.categorical(1)[0]

    labels, shares, table = [], [], []
    for assembly_id, genders in rows:
        n = len(genders)
        women = sum(1 for g in genders if g == "female")
        share = 100.0 * women / n
        labels.append(S.label(LBL.assembly(assembly_id))
                      + ("*" if assembly_id in INFERRED else ""))
        shares.append(share)
        table.append({
            "assembly_id": assembly_id,
            "members_with_sex_recorded": n,
            "women": women,
            "men": n - women,
            "women_share_pct": round(share, 1),
            "sex_source": "inferred from French grammatical agreement"
                          if assembly_id in INFERRED else "recorded by source",
        })

    bars = ax.bar(labels, shares, width=0.6, color=blue, linewidth=0)
    for bar, row in zip(bars, table):
        ax.annotate(
            f"{row['women_share_pct']:.0f}%\n{row['women']}/{row['members_with_sex_recorded']}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 5), textcoords="offset points", ha="center", va="bottom",
            fontsize=8, color=S.CHROME["text_secondary"], linespacing=1.3,
        )

    # The parity line needs to be distinguishable from the gridlines it crosses,
    # so it takes the muted ink rather than the (near-grid) axis colour.
    ax.axhline(50, color=S.CHROME["muted"], linewidth=1.0, zorder=2)
    ax.annotate("parity (50%)", xy=(-0.42, 50), xytext=(0, 4),
                textcoords="offset points", ha="left", va="bottom",
                fontsize=7.4, color=S.CHROME["muted"])

    ax.set_ylim(0, 56)
    ax.set_yticks([0, 10, 20, 30, 40, 50])
    ax.set_yticklabels([f"{v}%" for v in [0, 10, 20, 30, 40, 50]])
    S.frame(ax)
    S.titles(
        ax,
        "List parity delivered a third; 2023's districts, 15.5%",
        "Chambers with a person-level roster only; the 1956 assembly is excluded because no "
        "member's sex is recorded\n(women were not enfranchised until 1957). "
        "* sex inferred from French grammatical agreement in the source's own biographies.",
        ylabel="Share of members whose sex is recorded",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/persons.csv, mandates.csv")
    S.save(fig, "fig03_women_share", table)


if __name__ == "__main__":
    main()
