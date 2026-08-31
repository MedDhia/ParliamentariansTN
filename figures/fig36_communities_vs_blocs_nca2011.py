"""Figure 36 — Can you recover the blocs from the votes alone?

Louvain community detection on the vote-agreement graph, run without any bloc
information, against the blocs the chamber actually had. Rows are the detected
communities; columns are the recorded blocs; each cell is how many members fall
in both.

The answer is: partly, and asymmetrically. The algorithm finds three
communities. The largest is 96 members of whom 84 are Ennahdha — that bloc is
recovered from voting behaviour at 88% purity, without being told it exists. The
other two communities are mixtures: neither corresponds to any single bloc, and
the seven non-Ennahdha blocs are spread across both.

**Modularity puts a number on how weak that structure is.** The bloc partition
scores 0.12 on this graph and the detected partition 0.21 — both low. A
partition scoring 0.3 or more is normally taken as evidence of real community
structure; this chamber does not reach it under either labelling. So the
agreement graph is not well described as a set of communities at all. It is one
tight clique plus a weakly-differentiated remainder, which is what figure 34
draws and what figure 35 measures a different way.

**Community detection is not a bloc detector and this figure is not a test of
one.** Louvain optimises modularity, a quantity with no political content; its
communities depend on the resolution parameter, the threshold used to build the
graph, and the seed. The seed is fixed here so the figure is reproducible, and
the count of communities is not stable across every reasonable alternative. What
is stable across those choices is the Ennahdha block: it comes out as one lump
whatever else moves.

Blocs with fewer than eight members are folded into "Other blocs" for width;
the companion CSV is unfolded and carries every member's community assignment.
"""

from __future__ import annotations

import collections
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

SEED = 7
MIN_BLOC = 8
OTHER = "Other blocs"


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    people = sorted({p for d in dyads for p in d[:2]})

    graph = nx.Graph()
    graph.add_nodes_from(people)
    for a, b, weight, _ in POL.ties(dyads):
        graph.add_edge(a, b, weight=weight)

    communities = sorted(
        nx.community.louvain_communities(graph, seed=SEED, weight="weight"),
        key=len, reverse=True)
    bloc_partition = [
        {p for p in people if bloc.get(p, "No bloc") == name}
        for name in sorted({bloc.get(p, "No bloc") for p in people})
    ]
    q_found = nx.community.modularity(graph, communities, weight="weight")
    q_blocs = nx.community.modularity(graph, bloc_partition, weight="weight")

    sizes = collections.Counter(bloc.get(p, "No bloc") for p in people)
    named = [b for b, n in sizes.most_common() if n >= MIN_BLOC]
    columns = named + ([OTHER] if len(named) < len(sizes) else [])

    def column_of(person: str) -> str:
        name = bloc.get(person, "No bloc")
        return name if name in named else OTHER

    grid = np.zeros((len(communities), len(columns)), dtype=int)
    for i, community in enumerate(communities):
        for person in community:
            grid[i, columns.index(column_of(person))] += 1

    fig, ax = plt.subplots(figsize=S.figsize(8.6, 4.2))
    ramp = S.sequential(9)
    top = grid.max()
    for i in range(len(communities)):
        for j in range(len(columns)):
            value = grid[i, j]
            shade = ramp[min(len(ramp) - 1, int(round(value / top * (len(ramp) - 1))))]
            fill = S.CHROME["deemph"] if value == 0 else shade
            ax.add_patch(plt.Rectangle((j - 0.49, i - 0.49), 0.98, 0.98,
                                       facecolor=fill, edgecolor="none"))
            if value:
                ax.annotate(str(value), xy=(j, i), ha="center", va="center",
                            fontsize=8.6,
                            color="#ffffff" if value > top * 0.55 else "#0b0b0b")

    ax.set_xlim(-0.5, len(columns) - 0.5)
    ax.set_ylim(len(communities) - 0.5, -0.5)
    ax.set_xticks(range(len(columns)))
    # Wrapped rather than rotated: eight bloc names at an angle run off the
    # bottom of the canvas and into the source line.
    ax.set_xticklabels(
        [S.label("\n".join(textwrap.wrap(c, 12))) for c in columns], fontsize=7.8)
    ax.set_yticks(range(len(communities)))
    ax.set_yticklabels(
        [S.label(f"Community {i + 1}  ({len(c)})") for i, c in enumerate(communities)],
        fontsize=8.4)
    ax.grid(False)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)

    biggest = max(range(len(communities)), key=lambda i: grid[i].max())
    purity = grid[biggest].max() / len(communities[biggest])
    S.titles(
        ax,
        "Voting alone recovers Ennahdha, and nothing else",
        f"Louvain communities on the 2011 Constituent Assembly's vote-agreement graph, "
        "found without any bloc "
        f"information, against the blocs the chamber had. {len(communities)} "
        "communities;\nthe largest is "
        f"{purity:.0%} one bloc. The other two are mixtures corresponding to no "
        "recorded bloc. Modularity is low under both labellings — "
        f"{q_blocs:.2f} for the\nblocs, {q_found:.2f} for the detected partition, "
        "against roughly 0.3 as the usual threshold for real community structure — "
        "so this graph is not well\ndescribed as communities at all: one tight "
        "clique and a weakly-differentiated remainder. Louvain optimises a "
        "quantity with no political content and\nits output moves with the seed, "
        "the resolution and the tie threshold; the Ennahdha lump is what survives "
        f"those choices. Blocs under {MIN_BLOC} members are folded.",
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for i, community in enumerate(communities):
        for person in sorted(community):
            rows.append({
                "person_id": person,
                "name_lat": persons.get(person, {}).get("name_lat", ""),
                "bloc": bloc.get(person, "No bloc"),
                "community": i + 1,
                "community_size": len(community),
                "modularity_detected": round(q_found, 4),
                "modularity_blocs": round(q_blocs, 4),
            })
    S.save(fig, "fig36_communities_vs_blocs_nca2011", rows)


if __name__ == "__main__":
    main()
