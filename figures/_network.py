"""Shared drawing for the committee co-membership networks.

Three chambers get the same treatment, so the layout, colour rule and filtering
live here and the per-chamber scripts stay thin.

Two decisions worth defending.

**The whole graph is drawn, with weight carried by opacity.** Committee
co-membership is dense — density runs about 0.14 to 0.21, so 150–200 deputies
produce three to four thousand edges. Filtering to the strong ties was tried
first and rejected: keeping only pairs who shared two or more committees
disconnected four fifths of the chamber and produced a ring of isolates orbiting
a small core, which is a picture of the threshold rather than of the parliament.
Instead every tie is drawn, with width and opacity scaled by the number of shared
committees, so heavy ties read as structure and the mass of single-committee ties
recedes to a wash that shows where density lies.

**Node colour is capped at three classes.** Node colour in a node-link diagram is
an all-pairs form — any two nodes can end up adjacent on screen — and the
validated palette clears the separation floors for three slots under that
condition, not eight. So the two largest blocs get a hue each and everything else
is one "Other" class. Bloc identity beyond that belongs in the companion CSV,
which every figure writes.

Layout is a seeded spring layout, so the same data always draws the same picture.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

SEED = 20260827
MIN_WEIGHT = 2
TOP_BLOCS = 2


def _bloc_of(assembly_id: str) -> dict[str, str]:
    """person_id -> display bloc label, using the member's last spell."""
    blocs = {b["bloc_id"]: b for b in S.load("blocs")}
    latest: dict[str, tuple[str, str]] = {}
    for r in S.load("bloc_memberships"):
        if r["assembly_id"] != assembly_id:
            continue
        start = r["start_date"] or ""
        if r["person_id"] not in latest or start >= latest[r["person_id"]][0]:
            bloc = blocs[r["bloc_id"]]
            latest[r["person_id"]] = (start, LBL.bloc(bloc["name_ar"], bloc["name_lat"]))
    return {p: label for p, (_, label) in latest.items()}


def build_graph(assembly_id: str) -> tuple[nx.Graph, nx.Graph]:
    """Return (full graph, backbone) from the derived committee edge list."""
    full = nx.Graph()
    for r in S.load("edges_committee_comembership"):
        if r["assembly_id"] != assembly_id:
            continue
        weight = int(r["weight"])
        full.add_edge(r["source"], r["target"], weight=weight,
                      weight_newman=float(r["weight_newman"]))
    backbone = nx.Graph()
    backbone.add_nodes_from(full.nodes())
    for u, v, d in full.edges(data=True):
        if d["weight"] >= MIN_WEIGHT:
            backbone.add_edge(u, v, **d)
    return full, backbone


def draw(assembly_id: str, slug: str, title: str, note: str = "") -> None:
    full, backbone = build_graph(assembly_id)
    if full.number_of_nodes() == 0:
        raise SystemExit(f"no committee co-membership edges for {assembly_id}")

    persons = {p["person_id"]: p for p in S.load("persons")}
    bloc_of = _bloc_of(assembly_id)

    sizes = Counter(bloc_of.get(n, "No bloc") for n in full.nodes())
    top = [b for b, _ in sizes.most_common(TOP_BLOCS)]
    palette = S.categorical(len(top) + 1, all_pairs=True)
    colour_for = {b: palette[i] for i, b in enumerate(top)}
    other_colour = palette[-1]

    def node_colour(n: str) -> str:
        return colour_for.get(bloc_of.get(n, "No bloc"), other_colour)

    degree = dict(full.degree())
    max_degree = max(degree.values()) or 1

    # Lay out and draw the FULL graph. An earlier draft drew only ties of weight
    # >= 2, which disconnected four fifths of the chamber and produced a ring of
    # isolates orbiting a small core — a picture of the filter, not of the
    # parliament. Dense co-membership graphs are better shown whole with
    # translucent edges: the giant component and its clusters stay visible, and
    # nothing is silently removed.
    pos = nx.spring_layout(full, seed=SEED, k=0.32, iterations=260, weight="weight")

    fig, ax = plt.subplots(figsize=S.figsize(7.8, 6.8))

    weights = [d["weight"] for _, _, d in full.edges(data=True)]
    max_w = max(weights) if weights else 1
    # Heavier ties (more shared committees) draw darker and thicker; the mass of
    # single-committee ties recedes to a wash that shows where density is.
    nx.draw_networkx_edges(
        full, pos, ax=ax,
        width=[0.18 + 0.9 * (w / max_w) for w in weights],
        edge_color=[(0.0, 0.0, 0.0, 0.025 + 0.16 * (w / max_w)) for w in weights],
    )
    nx.draw_networkx_nodes(
        full, pos, ax=ax,
        node_size=[26 + 260 * (degree[n] / max_degree) for n in full.nodes()],
        node_color=[node_colour(n) for n in full.nodes()],
        linewidths=1.0, edgecolors=S.CHROME["surface"],  # surface ring, not a border
    )

    # Label only the most central members, and only where they are not stacked on
    # top of one another: a name on every node is noise, and overlapping names
    # are worse than none.
    placed: list[tuple[float, float]] = []
    for n in sorted(full.nodes(), key=lambda x: -degree[x]):
        if len(placed) >= 5:
            break
        x, y = pos[n]
        if any((x - px) ** 2 + (y - py) ** 2 < 0.10 for px, py in placed):
            continue
        placed.append((x, y))
        name = LBL.person_name(persons.get(n, {}).get("name_lat", "")) or n
        ax.annotate(
            S.label(name), xy=(x, y), xytext=(0, 11), textcoords="offset points",
            ha="center", fontsize=7.2, color=S.CHROME["text_primary"], zorder=6,
            bbox=dict(boxstyle="round,pad=0.18", facecolor=S.CHROME["surface"],
                      edgecolor="none", alpha=0.82),
        )

    ax.set_axis_off()
    density = nx.density(full)
    S.titles(
        ax,
        title,
        f"{full.number_of_nodes()} deputies, {full.number_of_edges():,} ties, density "
        f"{density:.2f}. Every tie is drawn; edge weight (shared committees) sets width and\n"
        f"opacity, so the {backbone.number_of_edges():,} ties of weight ≥ {MIN_WEIGHT} stand "
        "out against the wash of single-committee ties. Node size is degree.\n"
        f"The {len(sizes) - len(top)} smaller blocs share one colour — node colour is an "
        "all-pairs form, capped at three classes. " + note,
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=colour_for[b], label=S.label(f"{b} ({sizes[b]})"))
            for b in top
        ] + [
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=other_colour,
                          label=S.label(f"Other blocs ({sum(v for k, v in sizes.items() if k not in top)})"))
        ],
        loc="lower left", bbox_to_anchor=(-0.02, -0.04), ncol=3, fontsize=7.6,
    )
    S.source_note(
        fig, "ParliamentariansTN · data/networks/edges_committee_comembership.csv")

    table = []
    for n in sorted(full.nodes(), key=lambda x: -degree[x]):
        table.append({
            "person_id": n,
            "name_lat": persons.get(n, {}).get("name_lat", ""),
            "bloc": bloc_of.get(n, ""),
            "degree_full_graph": degree[n],
            "degree_backbone": backbone.degree(n),
            "weighted_degree_newman": round(
                sum(d["weight_newman"] for _, _, d in full.edges(n, data=True)), 4),
        })
    S.save(fig, slug, table)
