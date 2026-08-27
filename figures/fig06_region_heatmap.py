"""Figure 6 — Where members were elected from, by chamber and region.

A grid of magnitudes, so: a heatmap with a single-hue sequential ramp, light to
dark. Every cell also carries its number, so the encoding is never colour-alone
and the figure survives being printed in greyscale.

Regions are the seven statistical regions used by Tunisia's own statistics
institute, plus out-of-country seats. Cells are shares rather than counts because
the chambers differ in size — 161 seats in 2023 against 217 before, so raw counts
would make the current chamber look under-represented everywhere. The denominator
is the members of that chamber whose constituency resolves to a region, which is
not the whole chamber, so each row carries its own n.

Two things to read carefully. The "Abroad" column is a real institutional novelty:
out-of-country constituencies were created in 2011, and their share collapses in
2023 when the electoral system changed. And the denominators differ by row, which
is why each row carries its own n — the 1956 assembly drops out of the figure
entirely because its compound districts ("Sidi Bouzid-Gafsa-Tozeur") predate the
modern governorates and only 13 of 98 can be mapped without inventing a
correspondence.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

REGION_ORDER = [
    "Grand Tunis", "North East", "North West", "Centre East",
    "Centre West", "South East", "South West", "abroad",
]
# Short forms so the tick row reads horizontally: rotated labels collided with
# the source note, and rotation is a cost paid for no information.
REGION_LABEL = {
    "Grand Tunis": "Gr. Tunis", "North East": "N. East", "North West": "N. West",
    "Centre East": "C. East", "Centre West": "C. West",
    "South East": "S. East", "South West": "S. West", "abroad": "Abroad",
}
MIN_MEMBERS = 50


def main() -> None:
    governorates = {g["governorate_id"]: g for g in S.load("governorates")}
    constituencies = {c["constituency_id"]: c for c in S.load("constituencies")}
    order = [a["assembly_id"] for a in S.assemblies_in_order()]

    per_chamber: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for m in S.load("mandates"):
        cid = m["constituency_id"]
        if not cid:
            continue
        gov = governorates.get(constituencies.get(cid, {}).get("governorate_id", ""))
        region = gov["region"] if gov else ""
        if not region:
            continue
        per_chamber[m["assembly_id"]][region] += 1
        totals[m["assembly_id"]] += 1

    chambers = [a for a in order if totals.get(a, 0) >= MIN_MEMBERS]

    grid = np.zeros((len(chambers), len(REGION_ORDER)))
    counts = np.zeros_like(grid, dtype=int)
    for i, chamber in enumerate(chambers):
        for j, region in enumerate(REGION_ORDER):
            n = per_chamber[chamber][region]
            counts[i, j] = n
            grid[i, j] = 100.0 * n / totals[chamber]

    # One hue, light -> dark. Built from the documented blue ramp rather than a
    # matplotlib default so it matches every other figure in the set.
    ramp = LinearSegmentedColormap.from_list("seq_blue", S.sequential(9))

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 3.9))
    im = ax.imshow(grid, cmap=ramp, aspect="auto", vmin=0, vmax=grid.max())

    ax.set_xticks(range(len(REGION_ORDER)))
    ax.set_xticklabels([S.label(REGION_LABEL.get(r, r)) for r in REGION_ORDER],
                       fontsize=8)
    ax.set_yticks(range(len(chambers)))
    # n is on the row label because the denominator differs per chamber: these are
    # shares of the members whose constituency resolves to a region, not of the
    # whole chamber.
    ax.set_yticklabels(
        [S.label(f"{LBL.assembly(c)}  (n={totals[c]})") for c in chambers],
        fontsize=8.2)

    # Value in every cell: the colour is a summary, the number is the datum.
    midpoint = grid.max() * 0.58
    for i in range(len(chambers)):
        for j in range(len(REGION_ORDER)):
            share = grid[i, j]
            text = "—" if counts[i, j] == 0 else f"{share:.0f}%"
            ax.annotate(
                text, xy=(j, i), ha="center", va="center", fontsize=7.6,
                color="#ffffff" if share > midpoint else S.CHROME["text_secondary"],
            )

    ax.set_xticks(np.arange(-0.5, len(REGION_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(chambers), 1), minor=True)
    # A 2px surface gap between cells, rather than a border drawn around them.
    ax.grid(which="minor", color=S.CHROME["surface"], linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)

    bar = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.028)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=7.4, length=0, colors=S.CHROME["text_secondary"])
    bar.set_label("Share of the row's mapped members", fontsize=7.6,
                  color=S.CHROME["text_secondary"])

    S.titles(
        ax,
        "Regional origin of seats, by chamber",
        "Share of the members whose constituency resolves to a region (n per row), using "
        "Tunisia's seven statistical\nregions. Shares, not counts, because chambers differ "
        "in size. The 1956 assembly is absent: its compound districts\n"
        "(“Sidi Bouzid–Gafsa–Tozeur”) predate the modern governorates and only 13 of 98 map. "
        "“—” means none.",
    )
    S.source_note(
        fig, "ParliamentariansTN · mandates.csv × constituencies.csv × governorates.csv")

    table = []
    for i, chamber in enumerate(chambers):
        for j, region in enumerate(REGION_ORDER):
            table.append({
                "assembly_id": chamber,
                "region": region,
                "members": int(counts[i, j]),
                "share_pct": round(grid[i, j], 1),
                "chamber_members_with_constituency": totals[chamber],
            })
    S.save(fig, "fig06_region_heatmap", table)


if __name__ == "__main__":
    main()
