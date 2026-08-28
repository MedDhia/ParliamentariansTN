"""Figure 18 — Who co-signs written questions with whom, 2023 chamber.

The only *behavioural* network in the dataset. Committee and bloc ties are
assignments — someone put these members together. A co-signature is a choice: two
deputies decided to put their names on the same written question to a minister.

Built from 6,332 written questions, of which 78 carry more than one signatory.
That ratio is itself the finding: joint action is rare in this chamber, and the
network is correspondingly sparse — a few dense clusters of habitual co-signers
against a majority who never co-sign at all.

Deputies who never co-signed are drawn as unconnected marks rather than dropped,
because their absence from the network is the substantive point and silently
removing them would make the chamber look far more collaborative than it is.

Edge weight is the number of jointly signed questions. Because some questions
carry twenty or more signatories, a single mass filing can manufacture hundreds
of dyads; the companion CSV carries the Newman-corrected weight, which discounts
ties formed inside large groups, and that is the one to use for centrality.
"""

from __future__ import annotations

import sys
from pathlib import Path

from collections import Counter

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2023"
SEED = 20260827


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    roster = {m["person_id"] for m in S.load("mandates")
              if m["assembly_id"] == ASSEMBLY}

    graph = nx.Graph()
    # Sorted, not the raw set. Python randomises string hashing per process, so
    # iterating a set of person_ids gives a different node order on every run —
    # which reorders equal-degree rows in the companion table and, because the
    # spring layout seeds from node order, moves the drawing too. The figure was
    # silently not reproducible until this was pinned.
    graph.add_nodes_from(sorted(roster))
    for r in S.load("edges_question_cosignature"):
        graph.add_edge(r["source"], r["target"],
                       weight=int(r["weight"]),
                       weight_newman=float(r["weight_newman"]))

    connected = [n for n in graph.nodes() if graph.degree(n) > 0]
    isolated = [n for n in graph.nodes() if graph.degree(n) == 0]

    # Lay out the giant component alone and let it fill the frame. A single
    # spring layout over the whole graph pushes disconnected pieces far apart —
    # one stray co-signing pair ends up in a corner and squeezes the structure
    # everyone actually wants to see into a fraction of the canvas. Small
    # components and never-co-signers are packed into bands beneath instead:
    # present and countable, not competing for space.
    components = sorted(nx.connected_components(graph.subgraph(connected)),
                        key=len, reverse=True)
    giant = components[0] if components else set()
    small = [c for c in components[1:]]

    pos = nx.spring_layout(graph.subgraph(giant), seed=SEED, k=0.5,
                           iterations=300, weight="weight")
    xs = [p[0] for p in pos.values()] or [0.0]
    ys = [p[1] for p in pos.values()] or [0.0]
    span_x = (max(xs) - min(xs)) or 1.0
    span_y = (max(ys) - min(ys)) or 1.0
    # normalise the giant component into the unit square
    pos = {n: ((x - min(xs)) / span_x, (y - min(ys)) / span_y)
           for n, (x, y) in pos.items()}

    slot = 0
    for component in small:
        for k, n in enumerate(sorted(component)):
            pos[n] = (0.02 + 0.055 * slot + 0.022 * k, -0.13)
        slot += len(component) + 1

    per_row = 30
    for i, n in enumerate(sorted(isolated)):
        col, row = i % per_row, i // per_row
        pos[n] = (0.02 + 0.965 * col / max(per_row - 1, 1), -0.28 - 0.075 * row)

    # Colour is bloc, on the same three-class cap as the committee networks, so
    # the two are directly comparable. Never-co-signers are told apart by
    # *position* — they sit in their own labelled band below — which leaves
    # colour free to carry the substantive variable rather than participation.
    bloc_of = NET._bloc_of(ASSEMBLY)
    bloc_sizes = Counter(bloc_of.get(n, "No bloc") for n in graph.nodes())
    top_blocs = [b for b, _ in bloc_sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    bloc_colour = {b: palette[i] for i, b in enumerate(top_blocs)}
    other_colour = palette[-1]

    def colour(n: str) -> str:
        return bloc_colour.get(bloc_of.get(n, "No bloc"), other_colour)

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 7.4))

    weights = [d["weight"] for _, _, d in graph.edges(data=True)]
    max_w = max(weights) if weights else 1
    nx.draw_networkx_edges(
        graph, pos, ax=ax,
        width=[0.3 + 2.0 * (w / max_w) for w in weights],
        edge_color=[(0.0, 0.0, 0.0, 0.08 + 0.42 * (w / max_w)) for w in weights],
    )
    degree = dict(graph.degree())
    max_degree = max(degree.values()) or 1
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=connected,
        node_size=[18 + 150 * (degree[n] / max_degree) for n in connected],
        node_color=[colour(n) for n in connected],
        linewidths=1.0, edgecolors=S.CHROME["surface"],
    )
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=isolated, node_size=22,
        node_color=[colour(n) for n in isolated],
        linewidths=0.6, edgecolors=S.CHROME["surface"],
    )

    placed: list[tuple[float, float]] = []
    for n in sorted(connected, key=lambda x: (-degree[x], x)):
        if len(placed) >= 5:
            break
        x, y = pos[n]
        if any((x - px) ** 2 + (y - py) ** 2 < 0.030 for px, py in placed):
            continue
        placed.append((x, y))
        ax.annotate(
            S.label(LBL.person_name(persons.get(n, {}).get("name_lat", "")) or n), xy=(x, y),
            xytext=(0, 11), textcoords="offset points", ha="center", fontsize=7.2,
            color=S.CHROME["text_primary"], zorder=6,
            bbox=dict(boxstyle="round,pad=0.18", facecolor=S.CHROME["surface"],
                      edgecolor="none", alpha=0.85),
        )

    if small:
        ax.annotate(
            f"{sum(len(c) for c in small)} deputies in {len(small)} small separate "
            f"group{'s' if len(small) != 1 else ''}",
            xy=(0.02, -0.085), ha="left", va="bottom", fontsize=7.4,
            color=S.CHROME["text_secondary"],
        )
    if isolated:
        ax.annotate(
            f"{len(isolated)} deputies never co-signed a written question",
            xy=(0.02, -0.21), ha="left", va="bottom", fontsize=7.6,
            color=S.CHROME["text_secondary"],
        )

    ax.set_axis_off()

    nx.set_node_attributes(graph, {n: bloc_of.get(n, "No bloc") for n in graph}, "bloc")
    try:
        assortativity = nx.attribute_assortativity_coefficient(graph, "bloc")
    except (ZeroDivisionError, ValueError):
        assortativity = float("nan")
    within = sum(1 for u, v in graph.edges()
                 if bloc_of.get(u, "a") == bloc_of.get(v, "b"))

    # Recompute figure 16's coefficient rather than quoting a remembered one:
    # the contrast is the whole point of the sentence, and a hardcoded number
    # goes stale silently the next time the collectors change.
    committee_graph, _ = NET.build_graph(ASSEMBLY)
    nx.set_node_attributes(
        committee_graph,
        {n: bloc_of.get(n, "No bloc") for n in committee_graph}, "bloc")
    try:
        committee_assortativity = nx.attribute_assortativity_coefficient(
            committee_graph, "bloc")
    except (ZeroDivisionError, ValueError):
        committee_assortativity = float("nan")

    S.titles(
        ax,
        "Written-question co-signature, chamber elected in 2023",
        f"{len(connected)} of {graph.number_of_nodes()} deputies co-signed at least one "
        f"question with another; {graph.number_of_edges():,} ties.\nFrom 6,332 written "
        "questions, of which only 78 carry more than one signatory — joint filing is rare. "
        "Edge weight is\nthe number of shared questions; use the Newman-corrected weight in "
        "the CSV for centrality, since one mass filing\ncan manufacture hundreds of dyads.\n"
        f"Bloc assortativity {assortativity:+.2f} ({within} of {graph.number_of_edges():,} "
        "ties are within-bloc): unlike committee membership, which is assigned and\nignores "
        f"bloc (figure 16, {committee_assortativity:+.2f}), co-signing is chosen — and it "
        "follows bloc lines.",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=bloc_colour[b], label=S.label(f"{b} ({bloc_sizes[b]})"))
            for b in top_blocs
        ] + [
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=other_colour, label=S.label(
                              f"Other blocs ({sum(v for k, v in bloc_sizes.items() if k not in top_blocs)})")),
        ],
        loc="upper right", bbox_to_anchor=(1.02, 1.02), fontsize=7.6,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_question_cosignature.csv")

    S.save(fig, "fig18_cosignature_network_arp2023", [
        {
            "person_id": n,
            "name_lat": persons.get(n, {}).get("name_lat", ""),
            "bloc": bloc_of.get(n, ""),
            "cosignature_degree": degree[n],
            "cosigned_questions_total": sum(
                d["weight"] for _, _, d in graph.edges(n, data=True)),
            "weighted_degree_newman": round(
                sum(d["weight_newman"] for _, _, d in graph.edges(n, data=True)), 4),
        }
        for n in sorted(graph.nodes(), key=lambda x: (-degree[x], x))
    ])


if __name__ == "__main__":
    main()
