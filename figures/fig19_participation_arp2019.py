"""Figure 19 — Attendance against voting participation, 2019–2021 chamber.

Two behavioural measures for the same 216 members, so a scatter: the reader's job
is to see whether they move together and where the outliers are.

Both axes are proportions of the same kind, which is why this is one chart and
not two. It is emphatically *not* a dual-axis plot — that would put two different
scales on one frame and invent a relationship between them.

Colour is capped at three classes because a scatter is an all-pairs form: the two
largest blocs and everything else.

The diagonal is the reference. A member on it attends and votes at the same rate;
below it they turn up but abstain or leave before the vote. The gap between
showing up and voting is the interesting quantity, and it is not uniform.
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

ASSEMBLY = "ARP-2019"


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    blocs = {b["bloc_id"]: b for b in S.load("blocs")}
    bloc_of = {}
    for r in S.load("bloc_memberships"):
        if r["assembly_id"] == ASSEMBLY:
            b = blocs[r["bloc_id"]]
            bloc_of[r["person_id"]] = LBL.bloc(b["name_ar"], b["name_lat"])

    points = []
    for r in S.load("participation"):
        if r["assembly_id"] != ASSEMBLY:
            continue
        attendance = S.num(r["plenary_attendance_rate"])
        voting = S.num(r["vote_participation_rate"])
        if attendance is None or voting is None:
            continue
        points.append((r["person_id"], attendance, voting))

    sizes = Counter(bloc_of.get(p, "No bloc") for p, _, _ in points)
    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour_for = {b: palette[i] for i, b in enumerate(top)}

    fig, ax = plt.subplots(figsize=S.figsize(6.8, 5.6))
    for pid, attendance, voting in points:
        ax.plot(attendance, voting, "o", markersize=6,
                color=colour_for.get(bloc_of.get(pid, "No bloc"), palette[-1]),
                markeredgecolor=S.CHROME["surface"], markeredgewidth=0.9,
                alpha=0.9, zorder=3)

    ax.plot([0, 1], [0, 1], color=S.CHROME["muted"], linewidth=1.0, zorder=2)
    # Low on the diagonal, where the cloud is empty. At the top-right corner the
    # label sits in the densest part of the scatter and runs off the frame.
    ax.annotate("votes as often as present", xy=(0.20, 0.20), xytext=(-3, 5),
                textcoords="offset points", ha="left", va="bottom", fontsize=7.4,
                color=S.CHROME["muted"], rotation=45, rotation_mode="anchor")

    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "25%", "50%", "75%", "100%"])
    ax.set_yticklabels(["0", "25%", "50%", "75%", "100%"])
    S.frame(ax, x_grid=True)
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=6,
                          color=colour_for[b], label=S.label(f"{b} ({sizes[b]})"))
            for b in top
        ] + [mlines.Line2D([], [], marker="o", linestyle="none", markersize=6,
                           color=palette[-1],
                           label=S.label(f"Other blocs ({sum(v for k, v in sizes.items() if k not in top)})"))],
        loc="lower right", fontsize=7.6,
    )
    S.titles(
        ax,
        "Turning up and voting are not the same thing",
        f"{len(points)} members. Both rates are proportions published by Al Bawsala; their "
        "denominators are not published\nalongside them, so compare within this chamber only "
        "and not against other terms.",
        xlabel="Plenary attendance rate",
        ylabel="Vote participation rate",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/participation.csv")

    S.save(fig, "fig19_participation_arp2019", [
        {"person_id": pid,
         "name_lat": persons.get(pid, {}).get("name_lat", ""),
         "bloc": bloc_of.get(pid, ""),
         "plenary_attendance_rate": a,
         "vote_participation_rate": v,
         "gap_attendance_minus_voting": round(a - v, 4)}
        for pid, a, v in sorted(points, key=lambda t: -(t[1] - t[2]))
    ])


if __name__ == "__main__":
    main()
