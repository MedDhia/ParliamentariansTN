"""Figure 39 — Which blocs voted with which, 2011 Constituent Assembly.

Mean agreement between every pair of blocs on contested divisions: the average
over all member pairs with one member in each. The diagonal is agreement inside
a bloc.

**Read this beside figure 22, which is deliberately the same form on different
data.** That one shows who co-sponsored amendments with whom — a *chosen* tie,
where a member puts their name to something. This shows who voted the same way —
a *revealed* tie, which happens whether or not either member intended an
association. Putting them in the same shape is the point: the two need not agree
and where they diverge, something is being learnt about the difference between
what members chose to be seen doing and what they actually did.

They do diverge. Ennahdha's co-sponsorship row in figure 22 is below the chamber
rate against every bloc — Ettakatol at 0.65×, CPR at 0.52×. Its agreement row
here is not: Ettakatol at 0.79 is above the chamber mean of 0.71 and is
Ennahdha's closest relationship with anyone outside itself, and CPR at 0.72 sits
right on it. Both were its Troika coalition partners. They voted with Ennahdha
while putting their names to its amendments less than the average pair did.

**A cell is a mean over member pairs, so bloc size shapes its precision but not
its value.** A pair of ten-member blocs contributes 100 member pairs and a pair
of large ones thousands; the cell means are comparable but the small ones are
noisier, and the companion CSV carries the pair counts so that can be weighed.
The diagonal is not comparable to the off-diagonal at all — a bloc of ten has 45
internal pairs, and figure 23 covers within-bloc cohesion properly.

Contested divisions only, both members must have cast pour or contre, pairs need
30 shared divisions, and bloc is the member's last recorded spell.
"""

from __future__ import annotations

import collections
import itertools
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

MIN_MEMBERS = 5


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    people = sorted({p for d in dyads for p in d[:2]})
    sizes = collections.Counter(bloc.get(p, "No bloc") for p in people)
    blocs = [b for b, n in sizes.most_common() if n >= MIN_MEMBERS]

    cells: dict[tuple[str, str], list[float]] = collections.defaultdict(list)
    for a, b, weight, _ in dyads:
        ba, bb = bloc.get(a, "No bloc"), bloc.get(b, "No bloc")
        if ba in blocs and bb in blocs:
            cells[tuple(sorted((ba, bb)))].append(weight)

    overall = statistics.fmean(w for _, _, w, _ in dyads)
    grid = np.full((len(blocs), len(blocs)), np.nan)
    rows = []
    for a, b in itertools.combinations_with_replacement(blocs, 2):
        values = cells.get(tuple(sorted((a, b))), [])
        if not values:
            continue
        mean = statistics.fmean(values)
        i, j = blocs.index(a), blocs.index(b)
        grid[i, j] = grid[j, i] = mean
        rows.append({
            "bloc_a": a, "bloc_b": b,
            "members_a": sizes[a], "members_b": sizes[b],
            "member_pairs": len(values),
            "mean_agreement": round(mean, 4),
            "vs_chamber_mean": round(mean - overall, 4),
        })

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 6.2))
    # Diverging around the chamber-wide mean: the question is which pairs agree
    # more or less than an average pair, not the level, which is high throughout.
    limit = float(np.nanmax(np.abs(grid - overall)))
    for i in range(len(blocs)):
        for j in range(len(blocs)):
            if np.isnan(grid[i, j]):
                fill, ink, text = S.CHROME["deemph"], S.CHROME["muted"], "—"
            else:
                fill, ink = S.diverging(grid[i, j] - overall, limit)
                text = f"{grid[i, j]:.2f}"
            ax.add_patch(plt.Rectangle((j - 0.49, i - 0.49), 0.98, 0.98,
                                       facecolor=fill, edgecolor="none"))
            ax.annotate(text, xy=(j, i), ha="center", va="center", fontsize=8,
                        color=ink)

    ax.set_xlim(-0.5, len(blocs) - 0.5)
    ax.set_ylim(len(blocs) - 0.5, -0.5)
    ax.set_xticks(range(len(blocs)))
    ax.set_yticks(range(len(blocs)))
    ax.set_xticklabels([str(i + 1) for i in range(len(blocs))], fontsize=8)
    ax.set_yticklabels([S.label(f"{i + 1}  {b}  ({sizes[b]})")
                        for i, b in enumerate(blocs)], fontsize=8)
    ax.grid(False)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

    S.titles(
        ax,
        "Ennahdha voted closest with the partners it co-sponsored least with",
        "Mean agreement on contested divisions between every pair of blocs, "
        f"averaged over member pairs. Blue is above the chamber-wide mean of "
        f"{overall:.2f},\norange below. The matrix is symmetric: columns are the "
        "same blocs as the rows, numbered. This is deliberately figure 22's form "
        "on different data —\nthat one is who co-sponsored amendments together, a "
        "chosen tie; this is who voted the same way, which happens whether or not "
        "either member meant it.\nThey diverge: Ennahdha co-sponsored below the "
        "chamber rate with every bloc, including Ettakatol at 0.65×, yet agrees "
        "with Ettakatol at 0.79 — above the\nchamber mean and its closest "
        "relationship outside itself. Small blocs give noisier cells — the CSV "
        "carries pair counts — "
        "and the diagonal is not comparable to the off-diagonal; figure 23 handles "
        "within-bloc cohesion.",
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    S.save(fig, "fig39_bloc_agreement_matrix_nca2011",
           sorted(rows, key=lambda r: -r["mean_agreement"]))


if __name__ == "__main__":
    main()
