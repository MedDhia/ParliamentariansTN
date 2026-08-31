"""Figure 35 — Which blocs actually behave like blocs, size held constant.

The Krackhardt–Stern E-I index for each bloc on the vote-agreement graph:
(external − internal) / (external + internal) over its members' ties. −1 is a
group every one of whose ties stays inside it; +1 is one whose ties all leave.

**The raw index is almost useless on its own, and that is the point of the
figure.** In a 217-member chamber a ten-member bloc has 45 possible internal
ties and 2,070 external ones, so its E-I sits near +0.9 before any politics
enters. Reading the raw column would say the small blocs are outward-looking and
Ennahdha is insular, when most of that ordering is arithmetic.

So each bloc is drawn against a null: 400 reassignments of bloc labels across
the same members, holding every bloc's size fixed, and recomputing E-I each
time. The grey interval is the middle 95% of that null. What matters is the
distance from the bar to its own interval, not the position of the bar on the
axis.

Read that way, **seven of the eight groups fall below their null**: every actual
bloc is more internally cohesive than a random group of its size would be. The
single exception is "No bloc", the non-attached, who sit inside their null — as
they should, being a residual category with no reason to agree about anything.
That the method returns the right answer for the one group whose answer we know
in advance is the best evidence available that it is working.

But the *margins* are not comparable. Ennahdha sits 0.59 below its null mean;
the Democratic Bloc 0.26; the remaining five between 0.05 and 0.08. So the
finding is not "blocs cohere" — nearly all of them do, weakly — but that one
bloc's cohesion is an order of magnitude larger than any other's.

This is worth stating because the raw index says something different and wrong.
Uncorrected, Ennahdha has the *lowest* E-I and the small blocs the highest,
which reads as "the small blocs are outward-looking". The null reverses that:
the small blocs' high scores are what their size forces, and relative to size
they are cohesive too, just barely.

The measure inherits everything from the graph beneath it: the 0.75 threshold,
contested divisions only, and bloc taken as the member's last recorded spell.
The companion CSV carries the internal and external tie counts so the index can
be recomputed or replaced.
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

DRAWS = 400
MIN_MEMBERS = 5


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    people = sorted({p for d in dyads for p in d[:2]})
    tied = POL.ties(dyads)

    members: dict[str, set[str]] = collections.defaultdict(set)
    for person in people:
        members[bloc.get(person, "No bloc")].add(person)
    keep = {b: m for b, m in members.items() if len(m) >= MIN_MEMBERS}
    sizes = {b: len(m) for b, m in keep.items()}

    observed = {b: POL.ei_index(m, tied) for b, m in keep.items()}
    null = POL.ei_null(sizes, tied, people, draws=DRAWS)

    order = sorted(keep, key=lambda b: observed[b][2])
    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=S.figsize(8.4, 5.2))
    bar_colour, accent = S.categorical(2, all_pairs=True)

    for i, name in enumerate(order):
        draws = sorted(null[name])
        lo, hi = np.percentile(draws, 2.5), np.percentile(draws, 97.5)
        ax.plot([lo, hi], [i, i], color=S.CHROME["deemph"], linewidth=9,
                solid_capstyle="butt", zorder=2)
        value = observed[name][2]
        below = value < lo
        ax.plot([value], [i], marker="D", markersize=8, zorder=4,
                color=accent if below else bar_colour,
                markeredgecolor=S.CHROME["surface"], markeredgewidth=1.0)
        gap = value - statistics.fmean(draws)
        ax.annotate(f"{value:+.2f}   ({gap:+.2f} vs null)", xy=(1.04, i),
                    ha="left", va="center", fontsize=8, annotation_clip=False,
                    color=accent if below else S.CHROME["text_secondary"], zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels([S.label(f"{b}  ({sizes[b]})") for b in order], fontsize=8.4)
    # Room on the right for the value column, but ticks stop at the true bound.
    ax.set_xlim(-1.0, 1.62)
    ax.set_xticks([-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.axvline(0, color=S.CHROME["axis"], linewidth=0.9, zorder=1)
    S.frame(ax, x_grid=True, y_grid=False)

    S.titles(
        ax,
        "Every bloc coheres more than chance — Ennahdha by an order of magnitude",
        "Krackhardt–Stern E-I index on the 2011 Constituent Assembly's vote-agreement "
        "graph — (external − "
        "internal) / (external + internal) over each bloc's ties. −1 is a group "
        "whose ties all\nstay inside it. The grey bar is the middle 95% of a null "
        f"that reassigns bloc labels at random {DRAWS} times while holding every "
        "bloc's size fixed, which is\nwhat makes blocs of 10 and 87 comparable: "
        "a small group's E-I sits near +0.9 for arithmetic reasons alone. Read the "
        "distance from the diamond to its\nown grey bar, not its position on the "
        "axis. Seven of the eight fall below their null; the exception is the "
        "non-attached, who are a residual\ncategory rather than a bloc and have no "
        "reason to cohere. Ennahdha's margin (0.59 below its null mean) is roughly "
        "eight times the median bloc's.\nBlocs under "
        f"{MIN_MEMBERS} members are omitted.",
        xlabel="E-I index   ←  ties stay inside the bloc      ties leave the bloc  →",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="D", linestyle="none", markersize=8,
                          color=accent, label=S.label("Below its null — internally cohesive")),
            mlines.Line2D([], [], marker="D", linestyle="none", markersize=8,
                          color=bar_colour, label=S.label("At or above its null")),
            mlines.Line2D([], [], color=S.CHROME["deemph"], linewidth=9,
                          label=S.label("95% of the size-matched null")),
        ],
        loc="upper left", fontsize=8.2,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    S.save(fig, "fig35_ei_index_nca2011", [
        {
            "bloc": name,
            "members": sizes[name],
            "internal_ties": observed[name][0],
            "external_ties": observed[name][1],
            "ei_observed": round(observed[name][2], 4),
            "ei_null_mean": round(statistics.fmean(null[name]), 4),
            "ei_null_p2_5": round(float(np.percentile(null[name], 2.5)), 4),
            "ei_null_p97_5": round(float(np.percentile(null[name], 97.5)), 4),
            "below_null": observed[name][2] < float(np.percentile(null[name], 2.5)),
        }
        for name in order
    ])


if __name__ == "__main__":
    main()
