"""Figure 28 — Which parties gained and lost members in the 2011 assembly.

105 of the 217 members of the Constituent Assembly ended the term in a party
other than the one they were elected on. This is the net effect on each party:
members lost to it, members gained by it, and the balance.

**These are party switches, not bloc switches, and the two are different
things.** A parliamentary bloc is a group inside the chamber; a party is an
organisation outside it. A member can leave a party and keep sitting with the
same bloc, or the reverse. Figure 13 shows bloc-to-bloc movement in the
2014-2019 chamber; this is a different measure of a different chamber and the
two should not be read as a series.

**The rows are undated and cannot be chained.** The source publishes each
member's party of election against their party at the end of the term — a
from/to pair, with no date attached. A member who moved twice appears once, as
origin and destination, and the intermediate stop is invisible. So this shows
where the term started and ended for each member, not a sequence of moves, and
the count of switches is a lower bound on the number of moves.

Parties with fewer than three arrivals or departures are folded into "Other
parties" for the drawing; the companion CSV carries every party unfolded, which
is the point of shipping a table with each figure.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_MOVES = 3  # parties below this in both directions fold into "Other parties"
OTHER = "Other parties"


def main() -> None:
    switches = [r for r in S.load("party_switches") if r["assembly_id"] == ASSEMBLY]
    if not switches:
        raise SystemExit(f"no party switches recorded for {ASSEMBLY}")

    lost: collections.Counter[str] = collections.Counter()
    gained: collections.Counter[str] = collections.Counter()
    for row in switches:
        lost[row["party_from_name"] or "Not recorded"] += 1
        gained[row["party_to_name"] or "Not recorded"] += 1

    every = sorted(set(lost) | set(gained))
    big = [p for p in every if lost[p] >= MIN_MOVES or gained[p] >= MIN_MOVES]
    folded_lost = sum(lost[p] for p in every if p not in big)
    folded_gained = sum(gained[p] for p in every if p not in big)

    shown = {p: (lost[p], gained[p]) for p in big}
    if folded_lost or folded_gained:
        shown[OTHER] = (folded_lost, folded_gained)
    order = sorted(shown, key=lambda p: (shown[p][1] - shown[p][0], p))
    y = np.arange(len(order))

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 6.2))
    c_gain, c_loss = S.categorical(2, all_pairs=True)

    for i, party in enumerate(order):
        out, into = shown[party]
        ax.barh(i, -out, height=0.62, color=c_loss, zorder=3)
        ax.barh(i, into, height=0.62, color=c_gain, zorder=3)
        net = into - out
        # Net printed past the longer arm, so it never sits on top of a bar.
        pad = 0.6 if net >= 0 else -0.6
        ax.annotate(f"{net:+d}", xy=(into + pad if net >= 0 else -out + pad, i),
                    ha="left" if net >= 0 else "right", va="center", fontsize=8,
                    color=S.CHROME["text_primary"], zorder=5)

    ax.axvline(0, color=S.CHROME["axis"], linewidth=0.9, zorder=4)
    ax.set_yticks(y)
    ax.set_yticklabels([S.label(p) for p in order], fontsize=8.2)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.xaxis.set_major_formatter(lambda v, _: f"{abs(int(v))}")
    S.frame(ax, x_grid=True, y_grid=False)
    S.integer_axis(ax, "x")

    S.titles(
        ax,
        "Half the constituent assembly ended the term in a different party",
        f"{len(switches)} of the 217 members of the 2011 Constituent Assembly are "
        "recorded with a party of election different from their party at the end "
        "of the term.\nLeft of the line is members lost, right is members gained, "
        "and the number is the net. Parties with fewer than "
        f"{MIN_MOVES} moves in both directions are folded\ninto “{OTHER}”; "
        "the companion CSV carries every party unfolded. These are party "
        "switches, not bloc switches — a member can change one and keep the\n"
        "other, and figure 13 measures the other thing in a different chamber. "
        "The rows are undated from/to pairs and cannot be chained: someone who "
        "moved twice\nappears once, so the switch count is a lower bound on the "
        "number of moves.",
        xlabel="Members lost  ←   |   →  members gained",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], color=c_loss, linewidth=7, label=S.label("Lost")),
            mlines.Line2D([], [], color=c_gain, linewidth=7, label=S.label("Gained")),
        ],
        loc="lower right", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/party_switches.csv")

    S.save(fig, "fig28_party_switching_nca2011", [
        {
            "party": party,
            "members_lost": lost[party],
            "members_gained": gained[party],
            "net": gained[party] - lost[party],
            "drawn_as": party if party in big else OTHER,
        }
        for party in sorted(every, key=lambda p: (lost[p] - gained[p], p))
    ])


if __name__ == "__main__":
    main()
