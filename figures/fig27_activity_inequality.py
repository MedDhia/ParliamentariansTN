"""Figure 27 — How unequally parliamentary work is distributed.

Lorenz curves for the two activities this dataset counts per member: amendments
tabled in the 2011 Constituent Assembly, and written questions filed in the 2023
chamber. The x-axis is the share of members, ranked from least to most active;
the y-axis is the share of all activity they account for. The diagonal is
perfect equality — every member doing the same amount.

Two chambers a decade apart, two different activities, two different sources,
and the curves are not the same shape. That is the point of putting them
together: it distinguishes "parliamentary activity is always unequal" from
"these chambers were unequal in different ways".

**Why a Lorenz curve rather than a ranked bar.** Figure 20 already ranks the
2023 chamber's questioners individually and shows the top of the distribution.
This shows the whole distribution as one line, which makes two chambers of
different sizes directly comparable — 203 members against 154 — in a way that
two bar charts of different lengths are not. Gini coefficients are printed
because they are the number people will ask for, but the curve is the honest
object: two distributions can share a Gini and cross each other.

**The denominators differ and are stated.** The 2011 curve counts members who
tabled at least one amendment, not all 217; the 2023 curve counts members who
filed at least one question, not all 161. Members with nothing recorded are
excluded from both, because for the 2011 chamber the source does not distinguish
"tabled nothing" from "not covered", and including them would encode that
uncertainty as a zero. Both curves would run lower with the silent members added.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402


def lorenz(values: list[int]) -> tuple[np.ndarray, np.ndarray, float]:
    """Cumulative share of activity against cumulative share of members."""
    v = np.sort(np.array(values, dtype=float))
    cum = np.concatenate([[0.0], np.cumsum(v) / v.sum()])
    frac = np.linspace(0.0, 1.0, len(v) + 1)
    # Gini as twice the area between the diagonal and the curve.
    gini = 1.0 - 2.0 * np.trapezoid(cum, frac) if hasattr(np, "trapezoid") \
        else 1.0 - 2.0 * np.trapz(cum, frac)
    return frac, cum, float(gini)


def main() -> None:
    amendments = collections.Counter(
        r["person_id"] for r in S.load("amendment_sponsorships")
        if r["assembly_id"] == "NCA-2011")
    questions = collections.Counter()
    for row in S.load("participation"):
        if row["assembly_id"] == "ARP-2023":
            n = S.num(row["n_written_questions"], 0)
            if n:
                questions[row["person_id"]] = int(n)

    series = [
        ("Amendments tabled, 2011 assembly", list(amendments.values())),
        ("Written questions filed, 2023 chamber", list(questions.values())),
    ]
    palette = S.categorical(2, all_pairs=True)

    fig, ax = plt.subplots(figsize=S.figsize(6.8, 6.0))
    ax.plot([0, 1], [0, 1], color=S.CHROME["axis"], linewidth=1.0, zorder=2)
    ax.annotate("perfect equality", xy=(0.62, 0.62), xytext=(6, -6),
                textcoords="offset points", ha="left", va="top", fontsize=8,
                rotation=45, rotation_mode="anchor", color=S.CHROME["muted"])

    rows = []
    # Anchor each label part-way along its own curve and let it run down-right
    # into the empty region below both. Anchoring further along would push the
    # text past the right edge of the axes.
    for (name, values), colour, anchor in zip(series, palette, (0.50, 0.62)):
        frac, cum, gini = lorenz(values)
        ax.plot(frac, cum, color=colour, linewidth=2.4, zorder=4)
        idx = int(len(frac) * anchor)
        ax.annotate(f"{name}\n{len(values)} members · Gini {gini:.2f}",
                    xy=(frac[idx], cum[idx]), xytext=(9, -8),
                    textcoords="offset points", ha="left", va="top",
                    fontsize=8.4, color=colour, zorder=5)
        top = sorted(values, reverse=True)
        rows.append({
            "series": name,
            "members": len(values),
            "total_activity": sum(values),
            "gini": round(gini, 4),
            "median_per_member": int(np.median(values)),
            "max_per_member": max(values),
            "share_from_busiest_tenth": round(
                sum(top[:max(1, len(top) // 10)]) / sum(values), 4),
        })

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    S.frame(ax, x_grid=True)

    S.titles(
        ax,
        "Both chambers concentrate their work, but not to the same degree",
        "Lorenz curves: cumulative share of recorded activity against cumulative "
        "share of members, ranked least to most\nactive. The diagonal is perfect "
        "equality; the further a curve falls below it, the more the work sits "
        "with a few people.\nOnly members with at least one recorded item are "
        "counted — for the 2011 chamber the source does not\ndistinguish tabling "
        "nothing from not being covered, so a zero would encode an uncertainty as "
        "a fact, and both\ncurves would run lower with the silent members added.",
        xlabel="Share of members, least active first",
        ylabel="Share of all recorded activity",
    )
    S.source_note(fig, "ParliamentariansTN · amendment_sponsorships.csv · participation.csv")

    S.save(fig, "fig27_activity_inequality", rows)


if __name__ == "__main__":
    main()
