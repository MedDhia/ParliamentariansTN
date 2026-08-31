"""Figure 47 — The chamber's voting dimension, as distributions rather than a scatter.

The standard way to show legislative polarisation is the distribution of members'
positions on the first dimension of the vote space, one curve per party, with the
party medians marked and the distance between them read as the polarisation
measure. That form is not in this set: figure 21 fits the same scaling but
facets it as a scatter, one panel per bloc, which shows *where* each bloc sits
and hides how far its members overlap with anyone else's. Overlap is what the
conventional picture is for.

**Same scaling as figure 21, imported rather than refitted** — a singular value
decomposition of the 217 × 993 member-by-contested-division matrix, pour +1,
contre −1, everything else 0, signs pinned so the largest bloc sits right. It is
not NOMINATE and carries no error model; anyone wanting ideal points with
uncertainty should fit them from `vote_positions.csv`. Dimension 1 carries 22.5%
of the variance, dimension 2 6.1%.

**Panel A takes the cleavage the data actually has.** In a two-party chamber this
panel would be two curves and no argument. Here the first dimension separates
Ennahdha from every other bloc — its own Troika partners included, which is
figure 21's finding — so the two-group reduction is Ennahdha against the rest
rather than government against opposition, and it is a finding rather than a
convenience.

Median gap **18.6** on a dimension spanning −16.3 to +16.2, and a random
Ennahdha member scores above a random non-Ennahdha member **98.9%** of the time.
That last number is the one to quote: it is the probability of superiority, a
rank statistic, so it does not depend on the arbitrary scale of an SVD dimension
the way the raw gap does. The distributions are nonetheless not disjoint — 35
Ennahdha members sit below the highest-scoring non-member — which the medians
alone would hide and is exactly why the conventional form draws the whole curve.

**Panel B keeps the blocs the reduction discards**, as a ridgeline ordered by
median: the usual presentation when there are more than two groups, and the only
one that avoids putting eight intermixed hues in a single point cloud. The
ordering is itself the result. Ennahdha at +11.2 and then a 14-point drop to
Democratic Transition at −3.1, with the remaining seven blocs spread over eight
points between −3.1 and −11.8. The gap between the largest bloc and its nearest
neighbour is wider than the range containing all seven others.

**What the curves are.** Gaussian kernel density with a Silverman bandwidth,
drawn because that is the convention; the medians and the rank statistic beneath
them are computed from the members, not from the curves, so no smoothing choice
touches a number reported here. Blocs with fewer than five scaled members would
be drawn as a bandwidth artefact rather than a distribution, and none in this
chamber falls below ten.

**What it does not say.** Position here is a summary of voting, not of belief:
a member votes with a whip as readily as with a conviction, and the axis is
whatever the chamber most divided on rather than a left-right scale imported
from elsewhere. Abstention and absence are both 0 in the matrix, which pulls
frequent abstainers toward the centre and is a real assumption (figure 21 argues
it). Bloc is each member's last recorded spell in a chamber where 105 of 217
changed party, so a member scored under the wrong bloc blurs both panels.
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
import fig21_rollcall_scaling_nca2011 as SCALING  # noqa: E402
import _style as S  # noqa: E402

# Below this a kernel density is drawing its own bandwidth rather than a
# distribution. No bloc in this chamber is anywhere near it; the guard is here so
# that a rebuild on different data cannot quietly produce a smooth lie.
MIN_FOR_A_CURVE = 5
GRID = 400


def density(values: np.ndarray, grid: np.ndarray) -> np.ndarray:
    """Gaussian KDE with a Silverman bandwidth, in numpy.

    scipy is not in this repo's figure stack, and the estimator is four lines.
    Nothing reported in the figure depends on it: the medians, the gap and the
    rank statistic all come from the members themselves.
    """
    n = len(values)
    bandwidth = 1.06 * float(np.std(values)) * n ** (-0.2)
    # A bandwidth narrower than the drawing resolution is not a density, it is an
    # invisible spike: a bloc whose members all scored alike would silently draw
    # nothing at all. Floor it at half a percent of the grid so the spike is at
    # least visible as one.
    bandwidth = max(bandwidth, (grid[-1] - grid[0]) / 200)
    z = (grid[:, None] - values[None, :]) / bandwidth
    return np.exp(-0.5 * z ** 2).sum(axis=1) / (n * bandwidth * np.sqrt(2 * np.pi))


def superiority(higher: np.ndarray, lower: np.ndarray) -> float:
    """P(a random member of `higher` scores above a random member of `lower`).

    The rank form of the gap. Unlike the distance between medians it is
    invariant to the scale of the dimension, which for an SVD is arbitrary, so
    it is the number that survives a change of decomposition.
    """
    above = (higher[:, None] > lower[None, :]).mean()
    tied = (higher[:, None] == lower[None, :]).mean()
    return float(above + 0.5 * tied)


def main() -> None:
    kept, blocs, coords, _cast, share, n_contested, n_votes = SCALING.scale()
    if not kept:
        raise SystemExit("no scaled members for NCA-2011; run `make build`")
    position = coords[:, 0]

    by_bloc: dict[str, list[float]] = collections.defaultdict(list)
    for bloc, value in zip(blocs, position):
        by_bloc[bloc].append(float(value))
    # Ties broken by name: dict order would otherwise decide, and it is not
    # stable across processes once string hashing enters.
    biggest = max(sorted(by_bloc), key=lambda b: len(by_bloc[b]))
    inside = np.array(by_bloc[biggest])
    outside = np.array([v for b, v in zip(blocs, position) if b != biggest])

    gap = float(np.median(inside) - np.median(outside))
    auc = superiority(inside, outside)
    overlap = int((inside < outside.max()).sum())

    grid = np.linspace(position.min() - 1.5, position.max() + 1.5, GRID)
    inner, outer = S.categorical(2, all_pairs=True)

    fig = plt.figure(figsize=S.figsize(10.0, 7.4))
    layout = fig.add_gridspec(2, 1, height_ratios=(0.80, 1.0), hspace=0.34)
    ax_a, ax_b = fig.add_subplot(layout[0]), fig.add_subplot(layout[1])

    # A — the two-group reduction, the conventional polarisation picture
    for values, colour, name in ((outside, outer, f"All other blocs ({len(outside)})"),
                                 (inside, inner, f"{biggest} ({len(inside)})")):
        curve = density(values, grid)
        ax_a.fill_between(grid, curve, color=colour, alpha=0.30, zorder=2)
        ax_a.plot(grid, curve, color=colour, linewidth=2.0, zorder=3, label=S.label(name))
        ax_a.axvline(np.median(values), color=colour, linewidth=1.6,
                     linestyle=(0, (4, 2)), zorder=4)
    ceiling = max(density(inside, grid).max(), density(outside, grid).max())
    # Headroom for the gap arrow and the rank statistic, which both need to sit
    # clear of the taller curve rather than over it.
    ax_a.set_ylim(0, ceiling * 1.60)
    bar = ceiling * 1.42
    ax_a.annotate("", xy=(np.median(outside), bar), xytext=(np.median(inside), bar),
                  arrowprops=dict(arrowstyle="<->", color=S.CHROME["text_primary"],
                                  linewidth=1.1), zorder=5)
    ax_a.annotate(S.label(f"Median gap {gap:.1f}"),
                  xy=((np.median(inside) + np.median(outside)) / 2, bar),
                  xytext=(0, 5), textcoords="offset points", ha="center",
                  fontsize=8.4, color=S.CHROME["text_primary"], zorder=6)
    ax_a.set_yticks([])
    ax_a.set_ylabel(S.label("Density"), fontsize=8.4)
    ax_a.set_title(S.label(f"A · {biggest} against the rest of the chamber"),
                   loc="left", fontsize=9.8, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_a, y_grid=False)
    ax_a.legend(loc="upper left", fontsize=8.2, framealpha=0.92)
    ax_a.annotate(
        S.label(f"A random {biggest} member scores above a random other member "
                f"{auc:.1%} of the time.\nThe curves still overlap: {overlap} of "
                f"{len(inside)} sit below the highest-scoring non-member."),
        xy=(0.995, 0.80), xycoords="axes fraction", ha="right", va="top",
        fontsize=7.8, color=S.CHROME["text_secondary"], zorder=6)

    # B — every bloc, ordered by median, as a ridgeline
    order = sorted(by_bloc, key=lambda b: (statistics.median(by_bloc[b]), b))
    step = 1.0
    for row, bloc in enumerate(order):
        values = np.array(by_bloc[bloc])
        if len(values) < MIN_FOR_A_CURVE:
            continue
        curve = density(values, grid)
        curve = curve / curve.max() * (step * 0.92)
        colour = inner if bloc == biggest else outer
        base = row * step
        ax_b.fill_between(grid, base, base + curve, color=colour, alpha=0.32,
                          zorder=2 + row)
        ax_b.plot(grid, base + curve, color=colour, linewidth=1.4, zorder=2 + row)
        median = statistics.median(values)
        ax_b.plot([median, median], [base, base + step * 0.42],
                  color=S.CHROME["text_primary"], linewidth=1.2, zorder=40 + row)
        # Above the median tick, not beside it: several blocs have medians far
        # enough left that a label on the baseline would run into their own tick.
        ax_b.annotate(S.label(f"{bloc} ({len(values)})") + f"  {median:+.1f}".replace("-", "−"),
                      xy=(grid[0], base + step * 0.52), fontsize=8.0, ha="left",
                      va="bottom", color=S.CHROME["text_primary"], zorder=60)
    ax_b.set_yticks([])
    ax_b.set_ylim(-0.15, len(order) * step + 0.15)
    ax_b.set_title(S.label("B · Every bloc by median. The largest sits further "
                           "from its neighbour than the other seven span"),
                   loc="left", fontsize=9.8, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_b, y_grid=False)

    for ax in (ax_a, ax_b):
        ax.set_xlim(grid[0], grid[-1])
    ax_b.set_xlabel(S.label(f"First dimension of the vote space "
                            f"({share[0]:.0%} of variance)"), fontsize=8.4)

    medians = {b: statistics.median(v) for b, v in by_bloc.items()}
    runner_up = max((m for b, m in medians.items() if b != biggest))
    spread = runner_up - min(medians.values())
    fig.subplots_adjust(left=0.055, right=0.985, top=0.815, bottom=0.075)
    fig.text(0.010, 0.985,
             "One bloc, and then everyone else: the assembly's voting dimension",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.010, 0.950,
        f"The distribution of members on the first dimension of the vote space — "
        f"the conventional presentation of legislative polarisation, and the one "
        f"this set was missing: figure 21 fits the same\nscaling but facets it as "
        f"a scatter, which shows where each bloc sits and hides how far its "
        f"members overlap. Same decomposition, imported rather than refitted: "
        f"{len(kept)} members over the {n_contested}\nof {n_votes:,} divisions that "
        f"were contested, dimension 1 carrying {share[0]:.0%} of the variance. "
        f"{biggest}'s median sits {gap:.1f} above the rest of the chamber's on a "
        f"dimension spanning {position.min():+.0f} to {position.max():+.0f}".replace("-", "−") + f", and a "
        f"random\n{biggest} member outscores a random other member {auc:.1%} of the "
        f"time — a rank statistic, so unlike the raw gap it does not depend on the "
        f"arbitrary scale of an SVD dimension. It is not\nNOMINATE: no error model, "
        f"no uncertainty, and abstention and absence are both zero in the matrix, "
        f"which pulls frequent abstainers toward the centre. Bloc is each member's "
        f"last recorded spell.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")

    rows = []
    for bloc in sorted(by_bloc, key=lambda b: -medians[b]):
        values = by_bloc[bloc]
        rows.append({
            "series": "bloc", "group": bloc, "members": len(values),
            "median": round(medians[bloc], 3),
            "mean": round(statistics.fmean(values), 3),
            "sd": round(statistics.pstdev(values), 3),
            "min": round(min(values), 3), "max": round(max(values), 3),
        })
    rows.append({
        "series": "two_group_reduction", "group": f"{biggest} vs all others",
        "members": len(kept), "median": round(gap, 3),
        "mean": round(auc, 4), "sd": "", "min": round(float(position.min()), 3),
        "max": round(float(position.max()), 3),
    })
    S.save(fig, "fig47_ideal_point_distributions_nca2011", rows)


if __name__ == "__main__":
    main()
