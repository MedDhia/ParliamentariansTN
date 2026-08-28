"""Figure 10 — Shared members between every pair of chambers.

Figure 9 counts only consecutive chambers. This one gives all pairs, so the
non-consecutive overlaps are visible at all.

A caution the matrix itself cannot carry: a pairwise cell is not a skip count. The
2011 × 2019 cell reads 13, but 12 of those 13 also sat in 2014 — only one member
actually left and returned. Read pairwise cells as "sat in both", and compute
skip-a-chamber patterns from `mandates.csv` if that is the argument.

Form: a symmetric matrix as a heatmap, one hue light-to-dark, with the count in
every cell so nothing is encoded by colour alone. The diagonal carries each
chamber's own size and is drawn in the de-emphasis grey rather than on the ramp —
it is a different quantity from the off-diagonal cells and putting it on the same
scale would make every real overlap look like nothing by comparison.

The pre-2011 chambers are included deliberately, and their near-empty row is the
substantive point: the dataset cannot yet say whether the people who sat under
Ben Ali returned after 2011, because those chambers have no roster. The one
visible link is Fouad Mebazaa, who presided over the Chamber of Deputies and
became interim President in 2011.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

MIN_MEMBERS = 2


def main() -> None:
    order = [a["assembly_id"] for a in S.assemblies_in_order()]
    by_chamber: dict[str, set[str]] = defaultdict(set)
    for m in S.load("mandates"):
        by_chamber[m["assembly_id"]].add(m["person_id"])

    chambers = [c for c in order if len(by_chamber.get(c, ())) >= MIN_MEMBERS]

    n = len(chambers)
    overlap = np.zeros((n, n), dtype=int)
    for i, a in enumerate(chambers):
        for j, b in enumerate(chambers):
            overlap[i, j] = len(by_chamber[a] & by_chamber[b])

    off_diag = overlap.copy()
    np.fill_diagonal(off_diag, 0)
    vmax = max(off_diag.max(), 1)

    ramp = LinearSegmentedColormap.from_list("seq_blue", S.sequential(9))
    masked = np.ma.masked_array(off_diag, mask=np.eye(n, dtype=bool))

    fig, ax = plt.subplots(figsize=S.figsize(6.6, 5.4))
    im = ax.imshow(masked, cmap=ramp, vmin=0, vmax=vmax, aspect="equal")

    # Diagonal in de-emphasis grey: it is the chamber's own size, not an overlap.
    for i in range(n):
        ax.add_patch(plt.Rectangle((i - 0.5, i - 0.5), 1, 1,
                                   color=S.CHROME["deemph"], linewidth=0, zorder=2))

    ax.set_xticks(range(n))
    # Rotated rather than wrapped: "Constituent 1956" is wider than its column,
    # so a horizontal label — wrapped or not — runs into its neighbours.
    ax.set_xticklabels([S.label(LBL.assembly(c)) for c in chambers],
                       fontsize=7.4, rotation=38, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels([S.label(LBL.assembly(c)) for c in chambers], fontsize=7.6)

    midpoint = vmax * 0.58
    for i in range(n):
        for j in range(n):
            value = overlap[i, j]
            if i == j:
                colour = S.CHROME["text_secondary"]
            else:
                colour = "#ffffff" if value > midpoint else S.CHROME["text_secondary"]
            text = "·" if (i != j and value == 0) else str(value)
            ax.annotate(text, xy=(j, i), ha="center", va="center", fontsize=7.2,
                        color=colour, zorder=3)

    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color=S.CHROME["surface"], linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    bar = fig.colorbar(im, ax=ax, pad=0.02, fraction=0.036)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=7.2, length=0, colors=S.CHROME["text_secondary"])
    bar.set_label("Members in common", fontsize=7.4, color=S.CHROME["text_secondary"])

    S.titles(
        ax,
        "Members shared between chambers",
        "Every pair, not just consecutive ones. Grey diagonal = the chamber's own recorded "
        "size.\n“·” means no member in common. Chambers with fewer than two recorded members "
        "are omitted.\nA cell counts members who sat in both, not members who skipped what "
        "lies between: 12 of the 13\nin 2011 × 2019 also sat in 2014.",
    )
    # Clear of the rotated tick labels.
    S.source_note(fig, "ParliamentariansTN · data/processed/mandates.csv", y=-0.10)

    table = []
    for i, a in enumerate(chambers):
        for j, b in enumerate(chambers):
            if j <= i:
                continue
            table.append({
                "assembly_a": a, "assembly_b": b,
                "members_in_common": int(overlap[i, j]),
                "members_a": int(overlap[i, i]), "members_b": int(overlap[j, j]),
            })
    S.save(fig, "fig10_chamber_overlap", table)


if __name__ == "__main__":
    main()
