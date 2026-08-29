"""Figure 25 — The 2011 assembly stopped voting long before it stopped sitting.

For every recorded division, the share of listed members who cast neither pour
nor contre — absent, or abstaining. It runs at 18% in the first recorded month
of July 2012 and at a median of 56% across the assembly's last three months.

This is the caveat behind figures 21 and 23 drawn as its own picture. Both treat
the pour/contre record as the chamber's position; this shows how much of the
chamber that record covers, and that the coverage moves systematically over
time. A cohesion or scaling estimate late in the term rests on a much smaller
share of the assembly than the same estimate early in it.

**The two series are drawn apart, but the boundary between them is not clean.**
Marsad publishes four positions — pour, contre, abstenu, absent — and "absent"
conflates being away with being present and not voting. So the absence series is
an upper bound on real absence and the abstention series a lower bound on real
abstention. They are still worth separating, because their shapes differ and the
difference is the informative part: recorded abstention stays low and flat while
absence climbs steadily. What cannot be said from this source is how much of
that climbing absence was really silent presence.

A member who joined late or left early is not listed on a division at all and so
never enters the denominator, which is `n_recorded` on each division rather than
the chamber's 217 seats.
"""

from __future__ import annotations

import collections
import statistics
import sys
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_PER_MONTH = 5  # months with fewer divisions get no median point


def _parse(value: str) -> date | None:
    try:
        y, m, d = value.split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None


def main() -> None:
    when = {}
    for row in S.load("votes"):
        if row["assembly_id"] == ASSEMBLY:
            day = _parse(row["vote_date"])
            if day:
                when[row["vote_id"]] = day

    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in S.load("vote_positions"):
        if row["assembly_id"] == ASSEMBLY and row["vote_id"] in when:
            tally[row["vote_id"]][row["position"]] += 1

    points = []
    for vote_id, counts in tally.items():
        total = sum(counts.values())
        if total:
            points.append((when[vote_id], counts["absent"] / total,
                           counts["abstenu"] / total, total))
    points.sort()

    days = [p[0] for p in points]
    absent = [p[1] for p in points]
    abstained = [p[2] for p in points]

    fig, ax = plt.subplots(figsize=S.figsize(8.4, 5.0))
    c_absent, c_abstain = S.categorical(2, all_pairs=True)

    ax.scatter(days, absent, s=9, c=c_absent, alpha=0.35, linewidths=0, zorder=3)
    ax.scatter(days, abstained, s=9, c=c_abstain, alpha=0.35, linewidths=0, zorder=3)

    # A monthly median rather than a fitted line: the series is bursty and a
    # regression through it would imply a smoothness the sittings do not have.
    # Months carrying fewer than MIN_PER_MONTH divisions are left out of the
    # line entirely — a "median" of two votes swung it to 0% in July 2013 and
    # drew a cliff that was an artefact of the denominator, not the chamber.
    monthly: dict[date, list[tuple[float, float]]] = collections.defaultdict(list)
    for day, a, b, _ in points:
        monthly[date(day.year, day.month, 15)].append((a, b))
    months = [m for m in sorted(monthly) if len(monthly[m]) >= MIN_PER_MONTH]
    for series, colour in ((0, c_absent), (1, c_abstain)):
        ax.plot(months, [statistics.median(v[series] for v in monthly[m]) for m in months],
                color=colour, linewidth=2.0, marker="o", markersize=3.4, zorder=4)

    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylim(-0.02, 0.72)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    S.frame(ax)

    S.titles(
        ax,
        "By its final months, more than half the chamber sat out each division",
        f"Share of listed members casting neither pour nor contre, on each of the "
        f"{len(points):,} dated divisions of the 2011 Constituent Assembly: a "
        "median of 18% in July 2012\nand 56% across the last three months. One "
        "mark per division; the line is the monthly median, not a fitted trend — "
        "the sittings are too bursty for a regression\nthrough them to mean much, "
        f"and months with fewer than {MIN_PER_MONTH} divisions get no point at "
        "all. The denominator is the members listed on that division, so\nanyone "
        "who joined late or left early never enters it. Absence and abstention are "
        "drawn apart because their shapes\ndiffer, but the source conflates being "
        "away with being present and not voting, so the absence series is an "
        "upper bound on real absence and the\nabstention series a lower bound on "
        "real abstention. This is the coverage behind figures 21 and 23.",
        ylabel="Share of listed members not voting",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], color=c_absent, linewidth=2.4, label=S.label("Absent")),
            mlines.Line2D([], [], color=c_abstain, linewidth=2.4, label=S.label("Abstained")),
        ],
        loc="upper left", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/vote_positions.csv × votes.csv")

    S.save(fig, "fig25_participation_decay_nca2011", [
        {
            "vote_date": day.isoformat(),
            "listed_members": total,
            "share_absent": round(a, 4),
            "share_abstained": round(b, 4),
            "share_not_voting": round(a + b, 4),
        }
        for day, a, b, total in points
    ])


if __name__ == "__main__":
    main()
