"""Figure 23 — How reliably each bloc voted together, 2011 Constituent Assembly.

The Rice index of cohesion, per bloc, per division: the absolute difference
between a bloc's pour and contre votes over the total it cast. 1.0 is unanimity,
0.0 is an even split. It is the oldest measure in legislative studies and it
answers a question the network figures cannot — not *whether* bloc members were
tied to each other, but whether they actually voted the same way.

Each mark is one bloc on one division, so the spread matters more than the
midpoint: a bloc that is unanimous on most votes and splits badly on a few looks
very different from one that is mildly divided throughout, and a single mean
hides that. Divisions where a bloc cast fewer than five pour-or-contre votes are
dropped, because Rice on two votes is either 1.0 or 0.0 and carries no
information about discipline.

**A bloc's size bounds its own measure.** A ten-member bloc has far fewer ways to
be divided than an eighty-member one, so small blocs sit high on this index for
arithmetic reasons before any politics enters. The counts are on the figure for
that reason: read Ennahdha's median against its size, not against a bloc a
seventh of its size.

Abstention and absence are excluded rather than counted as dissent — Rice is
defined over votes cast. That means this measures discipline *among those who
turned up*, and figure 25 shows how many did not.
"""

from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_CAST = 5  # a bloc casting fewer votes than this on a division is skipped


def main() -> None:
    bloc_of = NET._bloc_of(ASSEMBLY)
    tally: dict[tuple[str, str], collections.Counter] = collections.defaultdict(
        collections.Counter)
    for row in S.load("vote_positions"):
        if row["assembly_id"] != ASSEMBLY:
            continue
        if row["position"] in ("pour", "contre"):
            bloc = bloc_of.get(row["person_id"], "No bloc")
            tally[(bloc, row["vote_id"])][row["position"]] += 1

    scores: dict[str, list[float]] = collections.defaultdict(list)
    for (bloc, _), counts in tally.items():
        cast = counts["pour"] + counts["contre"]
        if cast >= MIN_CAST:
            scores[bloc].append(abs(counts["pour"] - counts["contre"]) / cast)

    sizes = collections.Counter(bloc_of.values())
    unanimous = {b: sum(1 for v in vals if v == 1.0) / len(vals)
                 for b, vals in scores.items()}
    # Sorting by the median is useless here: seven of the eight blocs sit at
    # exactly 1.00, because a bloc of ten voting on a near-unanimous chamber is
    # unanimous by default. What separates them is how often they are *not*.
    order = sorted(scores, key=lambda b: (unanimous[b], b))
    y = np.arange(len(order))

    fig, ax = plt.subplots(figsize=S.figsize(8.6, 5.4))
    mark, accent = S.categorical(2, all_pairs=True)
    rng = np.random.default_rng(20260829)  # jitter only; seeded so it is stable

    for i, bloc in enumerate(order):
        vals = np.array(scores[bloc])
        # Jitter vertically so overlapping marks read as a distribution rather
        # than a line. It carries no information. The vertical striping in the
        # small blocs is real: ten members can only produce Rice values on a
        # coarse grid, which is itself part of why they score high.
        ax.scatter(vals, i + rng.uniform(-0.26, 0.26, len(vals)), s=5,
                   c=mark, alpha=0.16, linewidths=0, zorder=2)
        med = statistics.median(vals)
        ax.plot([med, med], [i - 0.34, i + 0.34], color=accent, linewidth=2.4,
                solid_capstyle="butt", zorder=4)
        ax.annotate(f"{unanimous[bloc]:.0%}", xy=(1.10, i), ha="right",
                    va="center", fontsize=8.6, color=S.CHROME["text_primary"],
                    zorder=5)

    ax.annotate("unanimous", xy=(1.10, len(order) - 0.55), ha="right",
                va="bottom", fontsize=8, color=S.CHROME["text_secondary"])
    ax.set_yticks(y)
    ax.set_yticklabels([S.label(f"{b}  ({sizes.get(b, 0)})") for b in order],
                       fontsize=8.4)
    ax.set_xlim(-0.02, 1.12)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylim(-0.7, len(order) - 0.15)
    S.frame(ax, x_grid=True, y_grid=False)

    S.titles(
        ax,
        "Ennahdha split more often than any bloc a seventh of its size",
        f"Rice index of cohesion for each bloc on each of the {len(tally):,} "
        "bloc-divisions where it cast at least five pour-or-contre votes, 2011 "
        "Constituent Assembly. One\nfaint mark per bloc-division, jittered "
        "vertically; the bar is the median, and the right-hand column is the "
        "share of divisions the bloc was unanimous on.\n1.0 is unanimity, 0.0 an "
        "even split. Bloc size bounds the measure: ten members can only divide "
        "on a coarse grid — the vertical striping in the small blocs is\nthat "
        "grid — so this ordering is as much arithmetic as discipline, and the "
        "honest comparison is Ennahdha against its own 87. The non-attached are "
        "not a\nbloc and are shown only as a baseline: nothing obliged them to "
        "agree, and at 33% they are what an undisciplined group looks like. "
        "Abstentions and\nabsences are excluded, because Rice is defined over "
        "votes cast: this is discipline among those who turned up, and figure 25 "
        "counts who did not.",
        xlabel="Rice index of cohesion on one division",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/vote_positions.csv × bloc_memberships.csv")

    S.save(fig, "fig23_bloc_cohesion_nca2011", [
        {
            "bloc": bloc,
            "members": sizes.get(bloc, 0),
            "divisions_scored": len(scores[bloc]),
            "median_rice": round(statistics.median(scores[bloc]), 4),
            "mean_rice": round(statistics.fmean(scores[bloc]), 4),
            "share_unanimous": round(
                sum(1 for v in scores[bloc] if v == 1.0) / len(scores[bloc]), 4),
        }
        for bloc in reversed(order)
    ])


if __name__ == "__main__":
    main()
