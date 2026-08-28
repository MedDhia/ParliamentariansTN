"""Figure 22 — Who co-sponsors amendments with whom, 2011 Constituent Assembly.

Figure 18 showed the *other* behavioural network — written-question co-signature
in the 2023 chamber — as a drawing. This one cannot be drawn the same way. The
2011 chamber co-sponsored amendments constantly: 9,361 of the 23,436 possible
pairs of members are tied, a density of 0.40. A node-link diagram of a graph that
dense is a solid disc, and a solid disc says nothing.

So the same information is shown as a mixing matrix instead. Each cell is one
pair of blocs; the value is how much denser co-sponsorship is between those two
blocs than between two members picked at random from the chamber. 1.0 is exactly
the chamber-wide rate, 2.0 is twice it, 0.5 is half. Colour is the log of that
ratio, so twice-as-dense and half-as-dense sit the same distance from neutral —
on a linear scale the "above" side would look twice as large as the "below" side
at equal magnitude.

**Small blocs are denser by construction.** A ten-member bloc has 45 internal
pairs and it takes little joint activity to fill them, while Ennahdha's 87
members span 3,741. The diagonal therefore rises as bloc size falls, and that
part of the pattern is arithmetic rather than politics. Read the *rows*, which
compare a bloc against the same chamber-wide denominator, before reading the
diagonal.

What survives that caveat is the row for Ennahdha: every off-diagonal cell in it
is below 1.0, and no other bloc has that property. The chamber's largest bloc
co-sponsored below the chamber's own rate with all seven of the others — while
the small blocs co-sponsored with each other well above it. Figure 21 finds the
same shape in the roll-call record, from an entirely separate source table.

The measure is presence of a tie, not its weight. Two deputies who co-sponsored
thirty amendments and two who co-sponsored one both count once, because the
question here is who ever works with whom. `edges_amendment_cosponsorship.csv`
carries both the raw count and the Newman-corrected weight for anyone asking the
other question.
"""

from __future__ import annotations

import collections
import itertools
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
LIMIT = math.log2(2.5)  # the diverging scale runs 1/2.5x to 2.5x, symmetric


def main() -> None:
    bloc_of = NET._bloc_of(ASSEMBLY)
    roster = sorted({m["person_id"] for m in S.load("mandates")
                     if m["assembly_id"] == ASSEMBLY})
    bloc = {p: bloc_of.get(p, "No bloc") for p in roster}
    sizes = collections.Counter(bloc.values())
    blocs = [b for b, _ in sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))]

    observed: collections.Counter[tuple[str, str]] = collections.Counter()
    total = 0
    for row in S.load("edges_amendment_cosponsorship"):
        if row["assembly_id"] != ASSEMBLY:
            continue
        if row["source"] not in bloc or row["target"] not in bloc:
            continue
        observed[tuple(sorted((bloc[row["source"]], bloc[row["target"]])))] += 1
        total += 1
    if not total:
        raise SystemExit(f"no amendment co-sponsorship edges for {ASSEMBLY}")

    n = len(roster)
    chamber_density = total / (n * (n - 1) / 2)

    def possible(a: str, b: str) -> int:
        if a == b:
            return sizes[a] * (sizes[a] - 1) // 2
        return sizes[a] * sizes[b]

    ratio = np.full((len(blocs), len(blocs)), np.nan)
    rows = []
    for a, b in itertools.combinations_with_replacement(blocs, 2):
        pairs = possible(a, b)
        ties = observed[tuple(sorted((a, b)))]
        value = (ties / pairs) / chamber_density if pairs else np.nan
        i, j = blocs.index(a), blocs.index(b)
        ratio[i, j] = ratio[j, i] = value
        rows.append({
            "bloc_a": a, "bloc_b": b,
            "members_a": sizes[a], "members_b": sizes[b],
            "pairs_possible": pairs, "pairs_tied": ties,
            "density": round(ties / pairs, 4) if pairs else "",
            "ratio_to_chamber": round(value, 4) if pairs else "",
        })

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 6.4))
    for i in range(len(blocs)):
        for j in range(len(blocs)):
            if np.isnan(ratio[i, j]):
                fill, ink, text = S.CHROME["deemph"], S.CHROME["muted"], "—"
            else:
                fill, ink = S.diverging(math.log2(ratio[i, j]), LIMIT)
                text = f"{ratio[i, j]:.2f}"
            # A 2px surface gap between cells rather than a drawn border: the
            # gap separates without adding a line to every edge in the grid.
            ax.add_patch(plt.Rectangle((j - 0.49, i - 0.49), 0.98, 0.98,
                                       facecolor=fill, edgecolor="none"))
            ax.annotate(text, xy=(j, i), ha="center", va="center",
                        fontsize=8, color=ink)

    ax.set_xlim(-0.5, len(blocs) - 0.5)
    ax.set_ylim(len(blocs) - 0.5, -0.5)
    ax.set_xticks(range(len(blocs)))
    ax.set_yticks(range(len(blocs)))
    # The matrix is symmetric, so the columns repeat the rows. Spelling the bloc
    # names out twice would either rotate them into the source note or force the
    # cells narrower than their values; numbering the columns against numbered
    # rows costs one glance and keeps the grid square.
    ax.set_xticklabels([str(i + 1) for i in range(len(blocs))], fontsize=8)
    ax.set_yticklabels([S.label(f"{i + 1}  {b}  ({sizes[b]})")
                        for i, b in enumerate(blocs)], fontsize=8)
    ax.grid(False)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

    S.titles(
        ax,
        "Ennahdha co-sponsored below the chamber's own rate with every other bloc",
        f"Amendment co-sponsorship in the 2011 Constituent Assembly: {total:,} of "
        f"the {int(n * (n - 1) / 2):,} possible pairs of members are tied, a "
        f"chamber-wide density of {chamber_density:.2f}. Each cell is\nthat pair "
        "of blocs' own density divided by the chamber's, so 1.00 is the chamber "
        "rate; blue is above it, orange below, on a log scale so 2× and ½× sit "
        "equally far\nfrom neutral. The matrix is symmetric: columns are the same "
        "blocs as the rows, in the same order, numbered. Read rows before the "
        "diagonal — a ten-member\nbloc has 45 internal pairs to fill and an "
        "87-member one has 3,741, so the diagonal rises as bloc size falls for "
        "arithmetic reasons. A tie is counted once\nhowever many amendments "
        "produced it.",
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_amendment_cosponsorship.csv")

    S.save(fig, "fig22_amendment_mixing_nca2011", rows)


if __name__ == "__main__":
    main()
