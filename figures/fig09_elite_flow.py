"""Figure 9 — Who stays: continuity across the four democratic chambers.

The figure the ARP-2014 recovery made possible. Before that chamber was recovered
from web archives there was no continuous panel, so this could not be drawn.

Form: a stacked bar per chamber, split by whether the member also sat in the
chamber immediately before. An earlier draft drew this as an alluvial diagram with
ribbons; the ribbons were dropped because between consecutive chambers there is
only one flow to show, so the bands added geometry without adding information —
and they crowded the labels. Where the *non*-consecutive overlaps matter,
figure 10 gives all pairs at once.

Colour does one job — returning against new — so it is two classes. The returning
segment carries only its count and share, not the word "returning": the word is
wider than the bar and wider than the gap between bars, so it would sit on a
neighbour either way, and the legend already supplies it.

The headline is how little is recycled. Tunisia's democratic parliaments were not
staffed by a stable political class: no chamber draws even a quarter of its
members from its predecessor, and the 2023 chamber, elected on an 11 per cent
turnout under a new electoral system after the previous parliament was dissolved,
draws 3 per cent.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

CHAMBERS = ["NCA-2011", "ARP-2014", "ARP-2019", "ARP-2023"]
GAP = 2.0  # the 2px surface gap between stacked segments, in data units


def main() -> None:
    served: dict[str, set[str]] = defaultdict(set)
    for m in S.load("mandates"):
        if m["assembly_id"] in CHAMBERS:
            served[m["person_id"]].add(m["assembly_id"])
    members = {c: {p for p, v in served.items() if c in v} for c in CHAMBERS}

    fig, ax = plt.subplots(figsize=S.figsize(7.6, 4.5))
    blue, orange = S.categorical(2)

    table = []
    for i, c in enumerate(CHAMBERS):
        n = len(members[c])
        prev = CHAMBERS[i - 1] if i > 0 else None
        returning = len(members[c] & members[prev]) if prev else 0
        new = n - returning

        ax.bar(i, returning, width=0.52, color=blue, linewidth=0, zorder=3)
        ax.bar(i, new, bottom=returning + GAP, width=0.52, color=orange,
               linewidth=0, zorder=3)

        ax.annotate(f"{n}", xy=(i, n + GAP + 7), ha="center", fontsize=9.5,
                    fontweight="bold", color=S.CHROME["text_primary"])
        ax.annotate(f"{new} new", xy=(i, returning + GAP + new / 2), ha="center",
                    va="center", fontsize=8.2, color="#ffffff", zorder=4)
        if prev:
            # The word "returning" does not fit anywhere: it is wider than the
            # 0.52-unit bar, and the 0.48-unit gap between bars is narrower
            # still, so an outside label lands on the next chamber's bar. The
            # legend already carries the word, so the mark carries only the
            # numbers — stacked on two lines, which is narrow enough to sit
            # inside the segment it describes.
            share = 100.0 * returning / n
            if returning >= 20:
                ax.annotate(f"{returning}\n{share:.0f}%", xy=(i, returning / 2),
                            ha="center", va="center", fontsize=8.2, color="#ffffff",
                            linespacing=1.25, zorder=4)
            else:
                # Too short to hold two lines; one compact line beside it.
                ax.annotate(f"{returning} ({share:.0f}%)", xy=(i + 0.26, 7),
                            xytext=(5, 0), textcoords="offset points",
                            ha="left", va="center", fontsize=8.2,
                            color=S.CHROME["text_secondary"], zorder=4)

        table.append({
            "assembly_id": c,
            "members": n,
            "previous_chamber": prev or "",
            "returning_from_previous": returning,
            "returning_share_pct": round(100.0 * returning / n, 1) if n else "",
            "new_to_this_chamber": new,
        })

    ax.set_xticks(range(len(CHAMBERS)))
    ax.set_xticklabels([S.label(LBL.assembly(c)) for c in CHAMBERS], fontsize=9)
    # Right edge leaves room for the last bar's compact outside label.
    ax.set_xlim(-0.6, len(CHAMBERS) - 0.05)
    ax.set_ylim(0, 285)
    S.frame(ax)
    ax.legend(
        handles=[
            mpatches.Patch(color=blue, label="Also sat in the previous chamber"),
            mpatches.Patch(color=orange, label="New to this chamber"),
        ],
        loc="upper left", bbox_to_anchor=(0.005, 0.99),
    )
    S.titles(
        ax,
        "No chamber draws a quarter of its members from the last",
        "Each chamber's recorded members, split by whether they also sat in the chamber "
        "immediately before.\nOnly consecutive pairs count here, so someone who sat in 2011 "
        "and 2023 but not 2019 is “new” in 2023;\nfigure 10 gives every pair.",
        ylabel="Members",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/mandates.csv")
    S.save(fig, "fig09_elite_flow", table)


if __name__ == "__main__":
    main()
