"""Figure 17 — Deputies and committees as a bipartite network, 2023 chamber.

The one-mode projections in figures 14–16 are dense because projection *creates*
density: put nine people on a committee and you have created 36 ties. This figure
shows the structure those projections are derived from — deputies on one side,
committees on the other, an edge where a deputy sits on a committee — which is
sparse, legible, and closer to the underlying fact.

It is the honest companion to the projections, and the network guide recommends
starting here: anyone whose argument depends on tie strength should build their
own projection from this incidence structure rather than inherit someone else's
weighting.

Committees are drawn as labelled squares sized by membership; deputies as small
circles. The 2023 chamber is used because it is the only one whose committees
carry Latin-script names in the data, so the hubs can be labelled without
inventing translations.

What it shows: committee sizes are uneven, and a visible minority of deputies sit
on two or more committees — those are the members who generate most of the ties
in figure 16.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2023"
SEED = 20260827


def main() -> None:
    committees = {c["committee_id"]: c for c in S.load("committees")
                  if c["assembly_id"] == ASSEMBLY}
    persons = {p["person_id"]: p for p in S.load("persons")}

    graph = nx.Graph()
    seats: defaultdict[str, int] = defaultdict(int)
    memberships: defaultdict[str, int] = defaultdict(int)
    rows = []
    for r in S.load("bipartite_person_committee"):
        if r["assembly_id"] != ASSEMBLY:
            continue
        cid, pid = r["committee_id"], r["person_id"]
        if cid not in committees:
            continue
        graph.add_node(cid, kind="committee")
        graph.add_node(pid, kind="person")
        graph.add_edge(pid, cid)
        rows.append({
            "person_id": pid,
            "name_lat": persons.get(pid, {}).get("name_lat", ""),
            "committee_id": cid,
            "committee": LBL.committee(committees[cid]["name_ar"],
                                       committees[cid]["name_lat"],
                                       committees[cid]["name_en"], limit=70),
            "role": r["role"],
        })

    if not graph:
        raise SystemExit(f"no bipartite committee data for {ASSEMBLY}")

    people = [n for n, d in graph.nodes(data=True) if d["kind"] == "person"]
    comms = [n for n, d in graph.nodes(data=True) if d["kind"] == "committee"]

    # Count distinct committees per deputy, and distinct deputies per committee,
    # from the graph rather than from the input rows. The bipartite table carries
    # one row per *role* and per dated spell, so a deputy who chairs a committee
    # appears on it twice (once as member, once as chair) and one who leaves and
    # rejoins appears twice again. Counting rows put 117 deputies on more than one
    # committee out of 152 — arithmetically impossible against 247 memberships.
    for n in people:
        memberships[n] = graph.degree(n)
    for c in comms:
        seats[c] = graph.degree(c)

    pos = nx.spring_layout(graph, seed=SEED, k=0.42, iterations=300)

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 7.0))
    blue, orange = S.categorical(2, all_pairs=True)

    nx.draw_networkx_edges(graph, pos, ax=ax, width=0.5,
                           edge_color=S.CHROME["axis"], alpha=0.55)
    # Deputies: small circles, sized by how many committees they sit on.
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=people,
        node_size=[16 + 26 * memberships[n] for n in people],
        node_color=blue, linewidths=0.8, edgecolors=S.CHROME["surface"],
    )
    # Committees: squares, sized by membership.
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=comms, node_shape="s",
        node_size=[40 + 7.0 * seats[n] for n in comms],
        node_color=orange, linewidths=1.0, edgecolors=S.CHROME["surface"],
    )

    # Label above the square by default, below when that would land on a label
    # already placed. Two committees whose squares sit close together otherwise
    # print one name over the other.
    placed: list[tuple[float, float]] = []
    for cid in sorted(comms, key=lambda c: -seats[c]):
        name = LBL.committee(committees[cid]["name_ar"], committees[cid]["name_lat"],
                             committees[cid]["name_en"], limit=26)
        x, y = pos[cid]
        above = not any(abs(x - px) < 0.28 and abs((y + 0.035) - py) < 0.05
                        for px, py in placed)
        dy, va = (10, "bottom") if above else (-11, "top")
        placed.append((x, y + (0.035 if above else -0.035)))
        ax.annotate(
            S.label(name), xy=(x, y), xytext=(0, dy), textcoords="offset points",
            ha="center", va=va, fontsize=6.6, color=S.CHROME["text_primary"], zorder=6,
            bbox=dict(boxstyle="round,pad=0.18", facecolor=S.CHROME["surface"],
                      edgecolor="none", alpha=0.85),
        )

    ax.set_axis_off()
    multi = sum(1 for n in people if memberships[n] > 1)
    S.titles(
        ax,
        "Deputies and committees, chamber elected in 2023",
        f"{len(people)} deputies, {len(comms)} committees, {graph.number_of_edges()} "
        f"memberships. {multi} deputies sit on more than one committee — they are what\n"
        "makes the one-mode projection in figure 16 dense. Committee names are the "
        "chamber's own French labels, shortened.",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=6,
                          color=blue, label="Deputy (size = committees sat on)"),
            mlines.Line2D([], [], marker="s", linestyle="none", markersize=8,
                          color=orange, label="Committee (size = members)"),
        ],
        loc="lower left", bbox_to_anchor=(-0.02, -0.02), ncol=2, fontsize=7.6,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/bipartite_person_committee.csv")
    S.save(fig, "fig17_committee_bipartite_arp2023", rows)


if __name__ == "__main__":
    main()
