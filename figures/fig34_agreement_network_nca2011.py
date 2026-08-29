"""Figure 34 — The 2011 assembly's agreement network, drawn.

Every member is a node; two members are joined where they voted the same way on
at least 75% of the contested divisions they both cast. Position is a spring
layout weighted by agreement, so members who vote together are pulled together.

**This is the only revealed tie layer in the dataset.** Committee co-membership
is assigned by the chamber and co-sponsorship is chosen by the member; agreement
is neither. Two members are tied here whether or not either wanted the
association, which is what makes it the right layer for polarisation and the
wrong one for anything about intent. A tie is a correlation between two voting
records, not an act.

**Ennahdha is very nearly a complete clique.** Its 87 members have an internal
density of 0.998 at this threshold: 3,735 of the 3,741 possible pairs agree on
at least three-quarters of the contested divisions they both cast. The other 130
members sit at 0.269. That asymmetry, not a left-right split, is what the
drawing shows — one clique and one cloud.

Community detection makes the same point without being told about blocs. Louvain
on this graph returns three communities, and the largest is 96 members of whom
84 are Ennahdha: bloc membership is recovered at 88% purity from voting
behaviour alone. Figure 36 pursues that.

**The threshold is a choice and the figure shows its cost.** At 0.75 the graph
has 9,126 edges among 217 members — a density of 0.39, which is dense enough
that a spring layout is doing as much averaging as revealing. The inset counts
edges at other thresholds so a reader can see how fast the structure thins;
`edges_vote_agreement.csv` carries every dyad's raw score for anyone who wants
a different cut.

Colour is capped at three classes, as everywhere in this set, so it carries the
two largest blocs against everyone else. The companion CSV has each member's
bloc unfolded along with their degree and cross-bloc tie share.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

SEED = 20260829
SWEEP = (0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90)


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    people = sorted({p for d in dyads for p in d[:2]})
    sizes = collections.Counter(bloc.get(p, "No bloc") for p in people)

    graph = nx.Graph()
    graph.add_nodes_from(people)  # sorted, so the layout is reproducible
    for a, b, weight, _ in POL.ties(dyads):
        graph.add_edge(a, b, weight=weight)

    pos = nx.spring_layout(graph, seed=SEED, weight="weight", k=0.28, iterations=260)

    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour = {b: palette[i] for i, b in enumerate(top)}
    other = palette[-1]

    def node_colour(person: str) -> str:
        return colour.get(bloc.get(person, "No bloc"), other)

    fig, ax = plt.subplots(figsize=S.figsize(8.0, 7.6))
    nx.draw_networkx_edges(graph, pos, ax=ax, width=0.28,
                           edge_color=[(0.0, 0.0, 0.0, 0.045)] * graph.number_of_edges())
    degree = dict(graph.degree())
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=people,
        node_size=[16 + 90 * (degree[p] / max(degree.values() or [1])) for p in people],
        node_color=[node_colour(p) for p in people],
        linewidths=0.7, edgecolors=S.CHROME["surface"],
    )
    ax.set_axis_off()

    # Threshold sweep, inset: how fast does the graph thin?
    inset = ax.inset_axes((0.0, 0.0, 0.27, 0.19))
    counts = [sum(1 for d in dyads if d[2] >= t) for t in SWEEP]
    inset.plot(SWEEP, counts, color=S.CHROME["text_secondary"], linewidth=1.6,
               marker="o", markersize=3)
    inset.axvline(POL.TIE_THRESHOLD, color=palette[1], linewidth=1.4)
    inset.set_title(S.label("edges by threshold"), fontsize=7.4,
                    color=S.CHROME["text_secondary"], loc="left", pad=3)
    inset.tick_params(labelsize=6.4)
    inset.set_facecolor(S.CHROME["surface"])
    for side in ("top", "right"):
        inset.spines[side].set_visible(False)
    inset.grid(False)

    density = nx.density(graph)
    # Quoted in the subtitle because the overall density averages two very
    # different regimes and on its own would hide the finding.
    enn_members = {p for p in people if bloc.get(p) == "Ennahdha"}
    enn_n = len(enn_members)
    enn_density = nx.density(graph.subgraph(enn_members))
    rest_density = nx.density(graph.subgraph(set(people) - enn_members))
    S.titles(
        ax,
        "Ennahdha is almost a perfect clique; the rest of the chamber is a cloud",
        f"Members of the 2011 Constituent Assembly joined where they voted the "
        f"same way on at least {POL.TIE_THRESHOLD:.0%} of the contested divisions "
        f"both cast:\n{graph.number_of_edges():,} ties among {len(people)} members, "
        f"a density of {density:.2f} overall — but {enn_density:.3f} inside "
        f"Ennahdha and {rest_density:.3f} among\nthe other {len(people) - enn_n} "
        "members. Spring layout weighted by agreement, so members who vote "
        "together sit together. This is the only revealed tie layer\nhere: "
        "committee seats are assigned and co-sponsorship is chosen, but two "
        "members are tied on this graph whether or not either wanted it, so a "
        "tie is a\ncorrelation and not an act. The threshold is an analytical "
        "choice — the inset shows how fast the graph thins, and the edge list "
        "carries every dyad's raw score.",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=colour[b], label=S.label(f"{b} ({sizes[b]})"))
            for b in top
        ] + [
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=other, label=S.label(
                              f"Other blocs ({sum(v for k, v in sizes.items() if k not in top)})"))
        ],
        loc="upper right", fontsize=8.2,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for person in people:
        neighbours = list(graph.neighbors(person))
        cross = sum(1 for n in neighbours if bloc.get(n) != bloc.get(person))
        rows.append({
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": bloc.get(person, "No bloc"),
            "degree": len(neighbours),
            "cross_bloc_ties": cross,
            "cross_bloc_share": round(cross / len(neighbours), 4) if neighbours else "",
        })
    S.save(fig, "fig34_agreement_network_nca2011",
           sorted(rows, key=lambda r: (-r["degree"], r["person_id"])))


if __name__ == "__main__":
    main()
