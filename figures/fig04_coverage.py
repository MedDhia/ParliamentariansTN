"""Figure 4 — What this dataset actually has, chamber by chamber.

The honesty figure, and the one to read before any of the others. A dumbbell per
chamber: the open marker is the seats the chamber had, the filled marker is the
members this dataset records individually. The gap between them is the gap in the
data.

A dumbbell rather than two bars because the reader's job is to compare two values
*per item* and see the distance; two shades of one hue rather than two categorical
colours because these are the same measure — seats — under two definitions.

Two things it shows that a coverage table does not. First, the twelve chambers of
the single-party era collapse to a near-zero column: fifty-two years of parliament
present only through their eight presiding officers. Second, three chambers
overshoot their seat count, which is not an error — a five-year term seats more
people than it has seats, because members are replaced.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402


def main() -> None:
    assemblies = S.assemblies_in_order()
    recorded = Counter(m["assembly_id"] for m in S.load("mandates"))

    fig, ax = plt.subplots(figsize=S.figsize(7.8, 6.4))
    blue = S.categorical(1)[0]

    labels, table = [], []
    for i, a in enumerate(reversed(assemblies)):
        seats = S.num(a["seats_nominal"])
        n = recorded.get(a["assembly_id"], 0)
        y = i
        if seats:
            ax.plot([n, seats], [y, y], color=S.CHROME["axis"], linewidth=1.4,
                    zorder=1, solid_capstyle="round")
            ax.plot([seats], [y], "o", markersize=6.5, markerfacecolor=S.CHROME["surface"],
                    markeredgecolor=blue, markeredgewidth=1.6, zorder=2)
        ax.plot([n], [y], "o", markersize=6.5, color=blue,
                markeredgecolor=S.CHROME["surface"], markeredgewidth=1.2, zorder=3)

        share = (100.0 * n / seats) if seats else None
        note = f"{n} of {int(seats)}" if seats else f"{n}"
        if share is not None and share > 100:
            note += "  (replacements)"
        ax.annotate(note, xy=(max(n, seats or 0), y), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=7.4,
                    color=S.CHROME["text_secondary"])

        labels.append(S.label(LBL.assembly(a["assembly_id"])))
        table.append({
            "assembly_id": a["assembly_id"],
            "seats_nominal": a["seats_nominal"],
            "mandates_recorded": n,
            "share_of_seats_pct": round(share, 1) if share is not None else "",
            "coverage_status": a["coverage_status"],
        })

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_ylim(-0.8, len(labels) - 0.2)
    ax.set_xlim(-8, 300)
    S.frame(ax, x_grid=True, y_grid=False)
    S.titles(
        ax,
        "Fifty-two years of parliament, eight presiding officers",
        "One row per chamber-term, 1956–2026. Open marker: seats the chamber had. Filled "
        "marker: members this\ndataset records individually — the distance between them is "
        "the coverage gap. Five terms are recorded member\nby member, one partly, and "
        "thirteen only as an institution: the twelve chambers of the single-party era "
        "collapse\nto a near-zero column, fifty-two years of parliament present through "
        "their eight presiding officers alone. Three\nterms overshoot their seat count, "
        "which is not an error — a five-year term seats more people than it has seats, "
        "because\nmembers are replaced. Read this figure before the rest: it is the bound "
        "on every claim the others make.",
        xlabel="Members",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=6.5,
                          markerfacecolor=S.CHROME["surface"], markeredgecolor=blue,
                          markeredgewidth=1.6, label="Nominal seats"),
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=6.5,
                          color=blue, label="Members recorded here"),
        ],
        loc="lower right", bbox_to_anchor=(1.0, 0.02),
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/assemblies.csv, mandates.csv")
    S.save(fig, "fig04_coverage", list(reversed(table)))


if __name__ == "__main__":
    main()
