"""Figure 26 — Most of what the 2011 assembly voted on, it agreed about.

The margin of every recorded division: the gap between pour and contre as a
share of the two combined. 0.0 is a dead heat, 1.0 is nobody dissenting. The
distribution is heaped almost entirely at the right — 42% of divisions clear
0.95, and the median is 0.92.

This is the figure that justifies a filter used elsewhere in the set. Figure 21
scales the chamber's voting space and drops near-unanimous divisions before
decomposing, on the grounds that a vote everyone agrees on locates nobody: it
places every member at the same point and so contributes variance without
contributing information. That filter removes 42% of the record, which is a
large enough cut to deserve showing rather than asserting, and this is what is
being cut.

It also says something about the assembly itself. A constituent assembly writing
a founding text passes most of it by consensus and fights over a minority of
articles; the contested tail here is where the politics is, and figure 31 shows
which constitutional articles it attached to.

The denominator is pour plus contre only. Abstentions and absences are excluded
because a margin is a property of the contest, not of turnout — figure 25 covers
turnout, and it is not small.
"""

from __future__ import annotations

import collections
import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
NEAR_UNANIMOUS = 0.95  # figure 21's filter, expressed as a margin
BINS = 40


def main() -> None:
    ours = {r["vote_id"] for r in S.load("votes") if r["assembly_id"] == ASSEMBLY}
    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in S.load("vote_positions"):
        if row["vote_id"] in ours and row["position"] in ("pour", "contre"):
            tally[row["vote_id"]][row["position"]] += 1

    margins = []
    for vote_id, counts in tally.items():
        cast = counts["pour"] + counts["contre"]
        if cast:
            margins.append((vote_id, abs(counts["pour"] - counts["contre"]) / cast, cast))
    values = np.array([m for _, m, _ in margins])

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 4.6))
    kept, dropped = S.categorical(2, all_pairs=True)

    edges = np.linspace(0, 1, BINS + 1)
    counts_, _ = np.histogram(values, bins=edges)
    # Two colours carry one distinction — kept by figure 21's filter or not —
    # so the cut is visible in the same picture as the distribution it cuts.
    colours = [dropped if e >= NEAR_UNANIMOUS else kept for e in edges[:-1]]
    ax.bar(edges[:-1], counts_, width=1 / BINS * 0.92, align="edge",
           color=colours, zorder=3)

    share = (values >= NEAR_UNANIMOUS).mean()
    ax.axvline(NEAR_UNANIMOUS, color=S.CHROME["axis"], linewidth=0.8, zorder=4)
    ax.annotate(
        f"{share:.0%} of divisions sit above {NEAR_UNANIMOUS:g}\n"
        "— dropped by figure 21 as uninformative",
        xy=(NEAR_UNANIMOUS, counts_.max() * 0.86), xytext=(-12, 0),
        textcoords="offset points", ha="right", va="center", fontsize=8,
        color=S.CHROME["text_secondary"], zorder=5,
    )

    S.frame(ax)
    S.titles(
        ax,
        "Two in five divisions had essentially no opposition",
        f"Margin of every recorded division in the 2011 Constituent Assembly "
        f"({len(margins):,} with at least one pour or contre): the gap between "
        "the two sides as a share of\nvotes cast, so 0.0 is a dead heat and 1.0 "
        f"is unopposed. Median {statistics.median(values):.2f}. Abstentions and "
        "absences are excluded — a margin describes the contest, not\nthe "
        "turnout, which figure 25 covers and which is not small. The shaded bars "
        "are the near-unanimous divisions figure 21 removes before scaling the "
        "chamber:\nthat filter is a large cut, so this is what it cuts.",
        xlabel="Margin between pour and contre, as a share of votes cast",
        ylabel="Divisions",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/vote_positions.csv × votes.csv")

    S.save(fig, "fig26_vote_margins_nca2011", [
        {
            "vote_id": vote_id,
            "votes_cast": cast,
            "margin": round(margin, 4),
            "near_unanimous": margin >= NEAR_UNANIMOUS,
        }
        for vote_id, margin, cast in sorted(margins, key=lambda r: (r[1], r[0]))
    ])


if __name__ == "__main__":
    main()
