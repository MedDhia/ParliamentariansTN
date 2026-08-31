"""Figure 2 — How big parliament has been, 1956 to now.

A single series over time, so: one line, one hue, no legend — the title names it.
Drawn as a step because a chamber's size is constant within a term and changes
discontinuously at an election; a smooth line between points would imply seats
were added gradually, which is not what happened.

The shape is the argument. Seats climb almost monotonically for fifty-five years,
from 98 to 217, and then fall by a quarter in 2023 — the only sustained
contraction in the series, and the one that coincides with the move from
closed-list PR to single-member districts.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

TODAY = dt.date(2026, 8, 27)


def main() -> None:
    rows = []
    for r in S.assemblies_in_order():
        # One series means one comparable unit: directly elected lower chambers
        # and the constituent assemblies that stood in their place. Mixing in the
        # indirectly chosen upper houses would put two different things on one line.
        if r["type"] not in ("ordinary_lower", "constituent"):
            continue
        seats = S.num(r["seats_nominal"])
        start = r["start_date"]
        if seats is None or not start:
            continue
        rows.append((dt.date.fromisoformat(start), int(seats), r))

    fig, ax = plt.subplots(figsize=S.figsize(7.8, 4.3))
    blue = S.categorical(1)[0]

    xs = [d for d, _, _ in rows] + [TODAY]
    ys = [s for _, s, _ in rows] + [rows[-1][1]]
    ax.step(xs, ys, where="post", color=blue, linewidth=2.0, solid_capstyle="round")
    ax.plot([d for d, _, _ in rows], [s for _, s, _ in rows], "o",
            color=blue, markersize=5,
            markeredgecolor=S.CHROME["surface"], markeredgewidth=1.4, zorder=3)

    # Direct-label selectively: the endpoints and the turn. A number on every
    # point would be chaos and goes unread.
    highlight = {rows[0][2]["assembly_id"], rows[-1][2]["assembly_id"]}
    peak = max(rows, key=lambda t: t[1])
    highlight.add(peak[2]["assembly_id"])
    for when, seats, row in rows:
        if row["assembly_id"] not in highlight:
            continue
        ax.annotate(
            f"{seats}", xy=(when, seats), xytext=(0, 9), textcoords="offset points",
            ha="center", fontsize=8.6, fontweight="bold",
            color=S.CHROME["text_primary"],
        )

    ax.annotate(
        "2023: single-member districts\nreplace closed-list PR — seats fall to 161",
        xy=(rows[-1][0], rows[-1][1]), xytext=(-14, -52), textcoords="offset points",
        ha="right", va="top", fontsize=7.6, color=S.CHROME["text_secondary"],
        linespacing=1.35,
        arrowprops=dict(arrowstyle="-", color=S.CHROME["axis"], linewidth=0.8,
                        shrinkA=0, shrinkB=6),
    )

    ax.set_ylim(0, 240)
    ax.set_xlim(dt.date(1954, 1, 1), dt.date(2029, 6, 1))
    S.frame(ax)
    S.titles(
        ax,
        "Seats climb 98 to 217, then fall by a quarter in 2023",
        "Nominal seats provided by law, held constant within each term. Directly elected "
        "lower chambers and\nthe two constituent assemblies only; the indirectly chosen "
        "upper houses are excluded as a different unit.",
        ylabel="Seats",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/assemblies.csv")

    S.save(fig, "fig02_chamber_size", [
        {
            "assembly_id": r["assembly_id"],
            "name_en": r["name_en"],
            "start_date": r["start_date"],
            "end_date": r["end_date"],
            "seats_nominal": s,
            "electoral_system": r["electoral_system"],
        }
        for _, s, r in rows
    ])


if __name__ == "__main__":
    main()
