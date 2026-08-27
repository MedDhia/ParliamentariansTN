"""Figure 13 — Who moved where: bloc-to-bloc transitions, 2014–2019 chamber.

108 of the 238 members whose bloc history is recorded changed bloc at least once.
This is where they went: rows are the bloc left, columns the bloc joined, cells
the number of moves. The denominator is 238 rather than the chamber's 246
mandates because eight members appear in no capture's bloc list at all.

Form: a matrix heatmap with counts in every cell. A chord or Sankey diagram is
the tempting choice for flows, but with 15 blocs and a long tail of one-off moves
it would be unreadable, and the reader's real question here is a lookup —
"how many went from Nidaa Tounes to Machrouu Tounes?" — which a matrix answers
directly and a chord diagram does not.

Blocs are ordered by total involvement so the dense corner sits top-left. Zero
cells are left blank rather than filled with "0": an empty cell reads as "this
did not happen" faster than a zero does, and it keeps the ink on what did.

The row to read is Nidaa Tounes. It is the source of most movement in the
chamber, and its members disperse rather than relocating together — the signature
of a party dissolving rather than splitting cleanly in two.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blocs as BL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2014"
MAX_BLOCS = 11


def main() -> None:
    moves, meta = BL.transitions(ASSEMBLY)
    if not moves:
        raise SystemExit(f"no bloc transitions for {ASSEMBLY}")

    involvement: dict[str, int] = {}
    for (src, dst), n in moves.items():
        involvement[src] = involvement.get(src, 0) + n
        involvement[dst] = involvement.get(dst, 0) + n
    blocs = [b for b, _ in sorted(involvement.items(), key=lambda kv: (-kv[1], kv[0]))]
    shown, hidden = blocs[:MAX_BLOCS], blocs[MAX_BLOCS:]

    index = {b: i for i, b in enumerate(shown)}
    n = len(shown)
    grid = np.zeros((n, n), dtype=int)
    n_hidden_moves = 0
    for (src, dst), count in moves.items():
        if src in index and dst in index:
            grid[index[src], index[dst]] += count
        else:
            n_hidden_moves += count

    ramp = LinearSegmentedColormap.from_list("seq_blue", S.sequential(9))
    masked = np.ma.masked_equal(grid, 0)

    fig, ax = plt.subplots(figsize=S.figsize(7.6, 6.2))
    im = ax.imshow(masked, cmap=ramp, vmin=0, vmax=grid.max(), aspect="equal")

    labels = [S.label(b) for b in shown]
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=38, ha="right", fontsize=7.4)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=7.4)

    midpoint = grid.max() * 0.58
    for i in range(n):
        for j in range(n):
            if grid[i, j] == 0:
                continue
            ax.annotate(str(grid[i, j]), xy=(j, i), ha="center", va="center",
                        fontsize=7.4,
                        color="#ffffff" if grid[i, j] > midpoint
                        else S.CHROME["text_secondary"])

    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color=S.CHROME["grid"], linewidth=1.0)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    bar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.036)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=7.2, length=0, colors=S.CHROME["text_secondary"])
    bar.set_label("Moves", fontsize=7.4, color=S.CHROME["text_secondary"])

    ax.set_ylabel("Bloc left", fontsize=8.4)
    ax.set_xlabel("Bloc joined", fontsize=8.4)
    S.titles(
        ax,
        "Bloc-to-bloc moves within the 2014–2019 chamber",
        f"{meta['n_moves']} moves by {meta['n_switchers']} of {meta['n_members']} members. "
        f"Blank = no move. The {len(hidden)} least-involved blocs are omitted\n"
        f"({n_hidden_moves} moves). Timing is bracketed to the interval between web "
        "captures; the counts are not.",
    )
    # Below the rotated tick labels and the x-axis label, both of which hang well
    # past the axes here; at the default y the note lands on top of them.
    S.source_note(fig, "ParliamentariansTN · bloc_memberships.csv × blocs.csv",
                  y=-0.16)

    S.save(fig, "fig13_bloc_switching_arp2014", [
        {"bloc_left": src, "bloc_joined": dst, "moves": count}
        for (src, dst), count in sorted(moves.items(), key=lambda kv: -kv[1])
    ])


if __name__ == "__main__":
    main()
