"""Figure 49 — The agreement matrix, members sorted by bloc and by position.

The blockmodel: every member on both axes, every cell the share of contested
divisions the pair voted alike on, rows and columns ordered by bloc and, inside
each bloc, by the member's position on the first dimension of the vote space.
It is the standard way to show that a chamber's behaviour has block structure,
and it is the one presentation in this set that shows *every* pair at once —
figure 34 draws only the ties above a threshold, figure 39 aggregates to eight
bloc-by-bloc cells, and both hide the within-block variation this shows.

**Sorting is the whole method.** A matrix in an arbitrary order is noise; the
same matrix ordered by a grouping shows whether the grouping is real. The
ordering here is not fitted to the matrix — bloc comes from the roster and
position from figure 21's decomposition — so the blocks that appear on the
diagonal are a prediction being met, not a partition read off the data it is
being tested against. Figure 36 does the fitted version, running Louvain on the
same graph without being told about blocs, and recovers Ennahdha at 88% purity.

**What it shows, and one thing it corrected.** One block is much darker than the
rest: Ennahdha's 87 members agree with each other at a mean of **0.915** against
**0.670** with everyone else — a gap of 0.25.

The first reading of this matrix was that the other blocs barely cohered at all,
their diagonal squares scarcely darker than the band between them. That was
wrong, and wrong for an instructive reason: it counted the 52 members recorded
under **No bloc** as a bloc. They are not one, and their square on the diagonal
is 1,326 pairs of unaffiliated members agreeing at 0.647 — which is not cohesion
but the absence of it, and it outweighs every real bloc's pairs put together.

Restricted to members in a *named* bloc other than Ennahdha, sharing a bloc is
worth **0.803** against **0.679** across bloc lines: a gap of 0.124, half
Ennahdha's but not nothing. So the honest reading is a matter of degree rather
than of kind. Every named bloc coheres; Ennahdha coheres twice as hard, over four
times as many pairs, and it is that asymmetry — not an absence of structure
elsewhere — that figures 21, 34 and 48 also report. The **No bloc** square is
labelled on the axis and should be read as a residual category, not compared with
the others.

Bloc size bounds every cohesion measure — a ten-member bloc has 45 internal
pairs to be cohesive with, against Ennahdha's 3,741 — so the squares are not
comparable as evidence of discipline. Figure 35 handles that properly, with a
size-matched null.

**Reading the ramp.** A single hue, light to dark, on a fixed 0.2–1.0 scale
rather than one stretched to the data, so a reader comparing this to a rebuild on
other data is comparing like with like. The diagonal is blank: a member's
agreement with themselves is 1.0 by construction and would draw a dark line
through the middle of every block, exaggerating each one.

**What it does not say.** Agreement is a correlation between voting records, not
an act — two opponents both backing an uncontroversial motion are shaded the
same as two allies. Pairs sharing fewer than 20 contested divisions are left
blank rather than estimated from a handful, which is why some rows are sparse:
participation collapses across the term (figure 25). Bloc is each member's last
recorded spell in a chamber where 105 of 217 changed party, so a member sorted
into the wrong block blurs a boundary that behaviour may well respect.
"""

from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fig21_rollcall_scaling_nca2011 as SCALING  # noqa: E402
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_CAST, MIN_MINORITY = 40, 0.025
FLOOR = 20
# A fixed scale, so the ramp means the same thing in a rebuild — but set where
# the data is, not at the theoretical floor. Agreement here runs 0.16 to 1.00
# with a median of 0.71 and a 5th percentile of 0.47; anchoring at 0.2 spent
# most of the ramp on the 5% of pairs below 0.45 and left the Ennahdha block
# indistinguishable from the rest. Cells at or under VMIN take the lightest
# step, and the figure says how many.
VMIN, VMAX = 0.45, 1.0


def load():
    dates = {r["vote_id"] for r in S.load("votes") if r["assembly_id"] == ASSEMBLY}
    positions: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["vote_id"] not in dates:
            continue
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1
    people = sorted(positions)
    votes = sorted(dates)
    index = {v: j for j, v in enumerate(votes)}
    matrix = np.zeros((len(people), len(votes)), dtype=np.int8)
    for i, person in enumerate(people):
        for vote_id, side in positions[person].items():
            matrix[i, index[vote_id]] = side
    return people, matrix


def contested(matrix: np.ndarray) -> np.ndarray:
    yes, no = (matrix == 1).sum(0), (matrix == -1).sum(0)
    cast = yes + no
    with np.errstate(invalid="ignore", divide="ignore"):
        minority = np.where(cast > 0, np.minimum(yes, no) / np.maximum(cast, 1), 0.0)
    return np.flatnonzero((cast >= MIN_CAST) & (minority >= MIN_MINORITY))


def agreement(matrix: np.ndarray, columns: np.ndarray) -> np.ndarray:
    sub = matrix[:, columns]
    yes, no = (sub == 1).astype(float), (sub == -1).astype(float)
    voted = (sub != 0).astype(float)
    shared = voted @ voted.T
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(shared >= FLOOR, (yes @ yes.T + no @ no.T) / shared, np.nan)
    np.fill_diagonal(rate, np.nan)
    return rate


def main() -> None:
    people, matrix = load()
    if not people:
        raise SystemExit("no recorded divisions for NCA-2011; run `make build`")
    columns = contested(matrix)
    rate = agreement(matrix, columns)

    kept, blocs, coords, *_ = SCALING.scale()
    place = {person: float(coords[i, 0]) for i, person in enumerate(kept)}
    bloc = POL.blocs(ASSEMBLY)
    label_of = {p: bloc.get(p, "No bloc") for p in people}

    by_bloc: dict[str, list[str]] = collections.defaultdict(list)
    for person in people:
        by_bloc[label_of[person]].append(person)
    # Blocs ordered by median position, members inside a bloc likewise, and
    # ties broken by id: an unstable order would redraw the figure each run.
    medians = {b: statistics.median([place.get(p, 0.0) for p in group])
               for b, group in by_bloc.items()}
    order_blocs = sorted(by_bloc, key=lambda b: (-medians[b], b))
    order: list[str] = []
    bounds: list[tuple[str, int, int]] = []
    for name in order_blocs:
        start = len(order)
        order.extend(sorted(by_bloc[name], key=lambda p: (-place.get(p, 0.0), p)))
        bounds.append((name, start, len(order)))

    index = {p: i for i, p in enumerate(people)}
    picked = [index[p] for p in order]
    grid = rate[np.ix_(picked, picked)]

    fig, ax = plt.subplots(figsize=S.figsize(8.8, 8.2))
    ramp = LinearSegmentedColormap.from_list("agreement", S.sequential(9))
    ramp.set_bad(S.CHROME["surface"])
    image = ax.imshow(np.ma.masked_invalid(grid), cmap=ramp, vmin=VMIN, vmax=VMAX,
                      interpolation="nearest")

    for _name, start, end in bounds[:-1]:
        for draw in (ax.axhline, ax.axvline):
            draw(end - 0.5, color=S.CHROME["text_primary"], linewidth=0.7, alpha=0.55)
    ticks = [(start + end - 1) / 2 for _n, start, end in bounds]
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_yticklabels([S.label(f"{n} ({e - s})") for n, s, e in bounds], fontsize=7.8)
    ax.set_xticklabels([S.label(n) for n, _s, _e in bounds], fontsize=7.4,
                       rotation=38, ha="right", rotation_mode="anchor")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    bar = fig.colorbar(image, ax=ax, fraction=0.030, pad=0.02)
    bar.set_label(S.label(f"Share of shared contested divisions voted alike "
                          f"({VMIN:.2f} and under take the lightest step)"),
                  fontsize=8.2)
    bar.ax.tick_params(labelsize=7.8)
    bar.outline.set_visible(False)

    rows = []
    for name, start, end in bounds:
        block = grid[start:end, start:end]
        inside = block[np.isfinite(block)]
        outside_mask = np.ones(len(order), dtype=bool)
        outside_mask[start:end] = False
        across = grid[start:end][:, outside_mask]
        across = across[np.isfinite(across)]
        rows.append({
            "bloc": name, "members": end - start,
            "within_mean": round(float(inside.mean()), 4) if inside.size else "",
            "within_pairs": int(inside.size // 2),
            "across_mean": round(float(across.mean()), 4) if across.size else "",
            "median_position": round(medians[name], 3),
        })
    biggest = max(rows, key=lambda r: r["members"])
    # Pair-weighted, and with the unaffiliated excluded from "same bloc": they
    # are a residual category, and their 1,326 pairs would otherwise swamp every
    # real bloc's and make the named blocs look as though they did not cohere.
    labels = np.array([label_of[p] for p in order])
    upper = np.triu_indices(len(order), 1)
    values = grid[upper]
    finite = np.isfinite(values)
    left, right = labels[upper[0]], labels[upper[1]]
    named = ((left != "No bloc") & (right != "No bloc")
             & (left != biggest["bloc"]) & (right != biggest["bloc"]))
    named_within = float(values[finite & named & (left == right)].mean())
    named_across = float(values[finite & named & (left != right)].mean())
    scored = np.isfinite(grid).sum() // 2
    floored = int((values[finite] <= VMIN).sum())
    rows.append({
        "bloc": "named blocs other than the largest, pair-weighted",
        "members": int(sum(r["members"] for r in rows
                           if r["bloc"] not in (biggest["bloc"], "No bloc"))),
        "within_mean": round(named_within, 4),
        "within_pairs": int((finite & named & (left == right)).sum()),
        "across_mean": round(named_across, 4), "median_position": "",
    })

    S.titles(
        ax,
        f"Sorted by bloc, one square is far darker than the rest of the diagonal",
        f"Every pair of the {len(order)} members on both axes, shaded by the share "
        f"of contested divisions they voted alike on; {scored:,} pairs clear the "
        f"20-division floor and the rest are blank. The ramp runs from "
        f"{VMIN:.2f}, below which\n{floored:,} pairs are clipped to its lightest "
        f"step. Rows and columns are ordered "
        f"by bloc and, within a bloc, by position on figure 21's first dimension — "
        f"an ordering taken from the roster and the vote space, not fitted to this\n"
        f"matrix, so the blocks on the diagonal are a prediction being met rather "
        f"than a partition read off its own data.\n{biggest['bloc']}'s "
        f"{biggest['members']} members agree at "
        f"{biggest['within_mean']:.2f} against "
        f"{biggest['across_mean']:.2f} with everyone else. The named blocs below "
        f"it cohere too, at {named_within:.2f} within against {named_across:.2f} "
        f"across — half the gap, not none — so this is a difference of degree. The "
        f"52 members under No bloc are\na residual category and their square is "
        f"not cohesion; read it apart from the others. Size bounds every cohesion "
        f"measure, so the squares are not comparable as discipline (figure 35 uses "
        f"a null).\nThe diagonal is blank because a member agrees with themselves "
        f"by construction, and agreement is a correlation between voting records, "
        f"not an act. Bloc is each member's last recorded spell.",
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")
    S.save(fig, "fig49_agreement_matrix_sorted_nca2011", rows)


if __name__ == "__main__":
    main()
