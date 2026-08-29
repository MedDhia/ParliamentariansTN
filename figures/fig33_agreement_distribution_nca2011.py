"""Figure 33 — How much bloc membership predicts who votes with whom.

Every pair of members in the 2011 Constituent Assembly, scored on the share of
contested divisions where they voted the same way, split by whether the two sat
in the same bloc. Within-bloc pairs average 0.84, cross-bloc pairs 0.67.

The separation is large: Cohen's d is 1.36, and only 0.9% of cross-bloc pairs
reach the within-bloc median. Bloc predicts agreement well.

And yet **92% of cross-bloc pairs still agree more often than they disagree**.
Both facts hold at once, and holding them together is the point of drawing the
whole distribution rather than reporting two means. This is a chamber with a
strong bloc structure that is not split into two hostile camps: even the
contested divisions mostly pass with majorities that cross bloc lines. Read
against figure 21, which finds a clean Ennahdha/everyone split on the first
principal component, the two are consistent — a leading dimension can separate
blocs sharply while most pairs still agree most of the time, because that
dimension carries 22% of the variance and not all of it.

**Contested divisions only.** On the full record every pair looks agreeable:
42% of divisions are near-unanimous, and including them pulls the chamber-wide
mean to 0.84 and squeezes both distributions into the top of the range. The
filter is figure 26's, and dropping it is the single change that would most
distort this picture.

**A pair is scored only on divisions where both cast pour or contre.** Absence
and abstention are not agreement or disagreement, and treating them as either
would manufacture consensus between two members who simply were not there.
Pairs sharing fewer than 30 such divisions are dropped.

Bloc is the member's last recorded spell, so a member who switched is counted
under where they ended. In a chamber where 105 of 217 changed party this is a
real simplification, and it biases toward *understating* within-bloc agreement.
"""

from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

BINS = 34


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()

    within = np.array([w for a, b, w, _ in dyads if bloc.get(a) == bloc.get(b)])
    across = np.array([w for a, b, w, _ in dyads if bloc.get(a) != bloc.get(b)])

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 4.8))
    c_within, c_across = S.categorical(2, all_pairs=True)
    edges = np.linspace(0, 1, BINS + 1)

    # Densities, not counts: there are three times as many cross-bloc pairs as
    # within-bloc ones, and raw counts would make the comparison unreadable.
    for values, colour in ((across, c_across), (within, c_within)):
        heights, _ = np.histogram(values, bins=edges, density=True)
        ax.stairs(heights, edges, fill=True, color=colour, alpha=0.55, zorder=3)
        ax.stairs(heights, edges, color=colour, linewidth=1.8, zorder=4)

    for values, colour, side in ((across, c_across, -1), (within, c_within, 1)):
        m = statistics.fmean(values)
        ax.axvline(m, color=colour, linewidth=1.4, linestyle=(0, (4, 3)), zorder=5)
        ax.annotate(f"mean {m:.2f}", xy=(m, ax.get_ylim()[1] * 0.80),
                    xytext=(6 * side, 0), textcoords="offset points",
                    ha="left" if side > 0 else "right", va="top", fontsize=8.4,
                    color=colour, zorder=6)

    ax.set_xlim(0, 1)
    S.frame(ax, x_grid=True)
    S.titles(
        ax,
        "Bloc predicts agreement sharply — and 92% of cross-bloc pairs still agree",
        f"Every scored pair of members ({len(dyads):,} of the 23,436 possible), by "
        "the share of contested divisions on which the two voted the same way. "
        "The two distributions\nseparate strongly — Cohen's d 1.36, and only 0.9% "
        "of cross-bloc pairs reach the within-bloc median — yet 92% of cross-bloc "
        "pairs still sit above 0.5.\nDensities, not counts: there are three times "
        "as many cross-bloc pairs as within-bloc ones. Contested divisions only — "
        "including the 42% that were near-unanimous pulls\nevery pair toward 0.84 "
        "and flattens the difference. "
        "A pair is scored only where both cast pour or contre, since absence is "
        "neither agreement nor\ndisagreement, and pairs sharing fewer than 30 such "
        "divisions are dropped. Bloc is the member's last recorded spell.",
        xlabel="Share of jointly-cast contested divisions voted the same way",
        ylabel="Density of pairs",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], color=c_within, linewidth=7,
                          label=S.label(f"Same bloc ({len(within):,} pairs)")),
            mlines.Line2D([], [], color=c_across, linewidth=7,
                          label=S.label(f"Different blocs ({len(across):,} pairs)")),
        ],
        loc="upper left", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    rows = [{
        "group": "same bloc", "pairs": len(within),
        "mean": round(float(np.mean(within)), 4),
        "median": round(float(np.median(within)), 4),
        "sd": round(float(np.std(within)), 4),
        "p10": round(float(np.percentile(within, 10)), 4),
        "p90": round(float(np.percentile(within, 90)), 4),
    }, {
        "group": "different blocs", "pairs": len(across),
        "mean": round(float(np.mean(across)), 4),
        "median": round(float(np.median(across)), 4),
        "sd": round(float(np.std(across)), 4),
        "p10": round(float(np.percentile(across, 10)), 4),
        "p90": round(float(np.percentile(across, 90)), 4),
    }]
    # Per-bloc internal agreement, so the table answers "which bloc?" too.
    by_bloc: dict[str, list[float]] = collections.defaultdict(list)
    for a, b, w, _ in dyads:
        if bloc.get(a) == bloc.get(b):
            by_bloc[bloc.get(a, "No bloc")].append(w)
    rows += [
        {"group": f"within {name}", "pairs": len(vals),
         "mean": round(statistics.fmean(vals), 4),
         "median": round(statistics.median(vals), 4),
         "sd": round(statistics.pstdev(vals), 4),
         "p10": round(float(np.percentile(vals, 10)), 4),
         "p90": round(float(np.percentile(vals, 90)), 4)}
        for name, vals in sorted(by_bloc.items(), key=lambda kv: -statistics.fmean(kv[1]))
    ]
    S.save(fig, "fig33_agreement_distribution_nca2011", rows)


if __name__ == "__main__":
    main()
