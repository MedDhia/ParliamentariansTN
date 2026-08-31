"""Figure 42 — Who is each member's closest voting ally?

Nodes are the 217 members of the 2011 Constituent Assembly. An edge joins two
members where at least one of them counts the other among their **three closest
alignments** — the three colleagues they voted with most often across the
contested divisions they both cast. Edge width and opacity carry the alignment
level itself, from 0.71 at the thinnest to 1.00 at the heaviest.

**Why a nearest-neighbour graph rather than a threshold.** Figure 34 draws this
chamber's agreement graph by cutting at 75%. That cut is defensible but it
answers a different question, and it hides how little room a threshold has to
work with here: the full agreement graph is **99.6% complete** — 23,337 of the
23,436 possible pairs have a score — with weights packed around a mean of 0.71.
Nearly everyone agrees with nearly everyone, because most divisions are
lopsided. The disparity filter, the standard method for extracting a weighted
backbone, returns *nothing* on this graph at any conventional significance
level: with weights that uniform, no member's alignment with anyone is
disproportionate. So the useful question is not "who agrees a lot" — everyone
does — but "who does each member agree with **most**", which is what this graph
asks and what a threshold cannot express.

**73% of members' closest allies are co-partisans, against a 24% baseline.**
477 of 651 nearest alignments stay inside the member's own bloc, where picking
partners at random would put 23.7% there. That is the polarisation result in its
sharpest available form: bloc predicts not just who you vote with, but who you
vote with *most*.

**And the ranking inverts once size is accounted for, which is the finding.**
Ennahdha has the highest raw share — 92.7% of its members' closest allies are
fellow Ennahdha — and the *lowest* lift over chance, 2.3×, because it is 87 of
217 members and a randomly chosen partner is a co-partisan 39.8% of the time.
The Democratic Alliance, ten members, sits at 70% against a 4.2% baseline: a
lift of 16.8×. Read the raw column and Ennahdha looks like the disciplined bloc;
correct for size and it is the least distinctive one in the chamber. Every bloc's
observed share, chance share and lift is in the companion CSV.

**The non-attached are not one group but eleven.** 52 members carry no bloc in
their last recorded spell, and 59% of *their* closest allies are also
non-attached — a 2.5× lift for a category that should be a residual with no
reason to cohere at all. The resolution is visible in the drawing and countable
in the graph: restricted to its own members, the non-attached subgraph breaks
into **eleven** disconnected pockets, the largest holding 26 members and the
next 13, with seven isolated individuals. Ennahdha, CPR and Ettakatol each form
a single pocket; the non-attached form a scattering of them, which is why they
are the only group here whose members do not share a region of the canvas and
the only one left unlabelled on it.

That reconciles this figure with figure 35, where a size-matched null found the
non-attached sitting *inside* it, uncohesive. Both are right. They do not cohere
as a category, and they contain two sizeable clusters that do. Bloc here is the
member's *last* recorded spell in a chamber where 105 of 217 changed party, so
the likeliest reading is that these pockets are members who left blocs late and
together — but this figure cannot separate that from affinity that was there
all along.

**What the weights are not.** A high score is not evidence of coordination: two
members who both back a routine motion are aligned in exactly the sense two
allies are. And the scores are not thin — a drawn edge's weight correlates
*positively* with the number of divisions behind it (+0.54), so the heaviest
lines are the best-evidenced ones, not the ones resting on the fewest votes.

Colour is capped at three classes, as everywhere in this set: eight hues would
fail the colourblind separation check at any palette length. Identity for the
other blocs is carried by a direct label placed on each one's **medoid** — the
member nearest its centre — so a label always sits on a real node rather than
in the empty space a centroid can fall into. The non-attached get no label
because they have no centre to put one on, which is the point about them.
"""

from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

SEED = 20260830
# Each member keeps their K strongest alignments. Three is the smallest K that
# leaves the graph connected with no isolates, so every member is placed by
# their own ties rather than parked at the edge of the canvas by a layout with
# nothing to hold them. It is also where the co-partisan share peaks: at K=5 it
# is 70.9% and at K=8, 67.8%, which is what you would expect if the nearest
# alignments are the most bloc-bound ones. K=2 leaves the graph in two pieces.
K = 3
# A member ranked in this many others' top three is drawn larger. The scale is
# capped so one very central member cannot swamp the rest.
MAX_NODE = 150
MIN_NODE = 14
# A bloc whose members are spread over more than this share of the canvas gets
# no label: there is no point on the drawing that stands for it.
MAX_LABEL_SPREAD = 0.20
LABEL_OFFSET = 0.022
LABEL_GAP_X = 0.20
LABEL_GAP_Y = 0.034
# Past this displacement a label no longer reads as belonging to its cluster,
# so it gets a leader line back to the member it was placed on.
LEADER_AT = 0.05


def nearest_alignments(dyads, k: int = K):
    """Return (graph, per-member top-k list) for the k-nearest alignment graph.

    The graph is the *union* of each member's top k, not the mutual
    intersection: A may be B's closest ally without B being A's. Taking the
    intersection would drop exactly the asymmetric relations that make some
    members hubs, which is the structure worth seeing.
    """
    adjacency: dict[str, list[tuple[float, str]]] = collections.defaultdict(list)
    for a, b, weight, _shared in dyads:
        adjacency[a].append((weight, b))
        adjacency[b].append((weight, a))
    graph = nx.Graph()
    graph.add_nodes_from(sorted(adjacency))  # sorted: the layout is reproducible
    picks: dict[str, list[tuple[float, str]]] = {}
    for person in sorted(adjacency):
        # Sort on (weight, id) so ties between equal weights break the same way
        # on every run and in every Python process.
        chosen = sorted(adjacency[person], key=lambda wp: (-wp[0], wp[1]))[:k]
        picks[person] = chosen
        for weight, other in chosen:
            graph.add_edge(person, other, weight=weight)
    return graph, picks


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    graph, picks = nearest_alignments(dyads)
    people = sorted(graph)
    sizes = collections.Counter(bloc.get(p, "No bloc") for p in people)

    if nx.number_connected_components(graph) != 1:
        raise SystemExit("the nearest-alignment graph fragmented; K needs revisiting")

    pos = nx.spring_layout(graph, seed=SEED, weight="weight", k=0.55, iterations=400)
    xs = [pos[p][0] for p in people]
    ys = [pos[p][1] for p in people]
    layout_span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    mid_x = (max(xs) + min(xs)) / 2
    mid_y = (max(ys) + min(ys)) / 2

    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour = {b: palette[i] for i, b in enumerate(top)}
    other_colour = palette[-1]

    fig, ax = plt.subplots(figsize=S.figsize(8.4, 6.5))

    # Edge ink IS the alignment level: both width and opacity scale with it.
    # Redundant encoding on one variable, which for hairline strokes buys
    # legibility without implying a second dimension.
    weights = [d["weight"] for *_e, d in graph.edges(data=True)]
    lo, hi = min(weights), max(weights)
    span = (hi - lo) or 1.0

    def scaled(weight: float) -> float:
        return (weight - lo) / span

    nx.draw_networkx_edges(
        graph, pos, ax=ax,
        width=[0.35 + 2.0 * scaled(w) ** 1.6 for w in weights],
        edge_color=[(0.0, 0.0, 0.0, 0.10 + 0.42 * scaled(w) ** 1.6) for w in weights],
    )

    # Node size = how many members count this one among their three closest.
    chosen_by = collections.Counter(
        other for person in people for _w, other in picks[person])
    ceiling = max(chosen_by.values()) or 1
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=people,
        node_size=[MIN_NODE + (MAX_NODE - MIN_NODE) * (chosen_by[p] / ceiling)
                   for p in people],
        node_color=[colour.get(bloc.get(p, "No bloc"), other_colour) for p in people],
        linewidths=0.7, edgecolors=S.CHROME["surface"],
    )
    ax.set_axis_off()
    ax.margins(0.06)

    # Direct labels carry identity for the blocs colour folds into "Other",
    # since eight hues would fail the colourblind separation check at any
    # palette length this set allows.
    #
    # Each label sits on its bloc's MEDOID, the member closest to the bloc's
    # centre, not on the centroid: a centroid can land in empty space, and for a
    # scattered group it lands somewhere none of its members are. A group too
    # dispersed for a label to mean anything is left unlabelled rather than
    # labelled misleadingly — which here means the non-attached, whose spread is
    # twice that of any real bloc.
    placed: list[tuple[float, float]] = []
    for name, count in sizes.most_common():
        members = [p for p in people if bloc.get(p, "No bloc") == name]
        if not members:
            continue
        cx = sum(pos[p][0] for p in members) / len(members)
        cy = sum(pos[p][1] for p in members) / len(members)
        spread = sum(math.hypot(pos[p][0] - cx, pos[p][1] - cy)
                     for p in members) / len(members)
        if spread / layout_span > MAX_LABEL_SPREAD:
            continue
        medoid = min(members, key=lambda p: math.hypot(pos[p][0] - cx, pos[p][1] - cy))
        lx, ly = pos[medoid]
        # Push the label off its own node, outward from the drawing's centre, so
        # it never sits on top of the member it names.
        angle = math.atan2(ly - mid_y, lx - mid_x) or 0.0
        lx += LABEL_OFFSET * layout_span * math.cos(angle)
        ly += LABEL_OFFSET * layout_span * math.sin(angle)
        # Then nudge vertically until it clears every label already placed.
        for _ in range(60):
            clash = next((q for q in placed
                          if abs(q[0] - lx) < LABEL_GAP_X * layout_span
                          and abs(q[1] - ly) < LABEL_GAP_Y * layout_span), None)
            if clash is None:
                break
            ly += LABEL_GAP_Y * layout_span * (1 if ly >= clash[1] else -1)
        placed.append((lx, ly))
        # A label pushed clear of its neighbours can end up reading as a label
        # for whatever it landed next to. A leader line back to the medoid says
        # which cluster it belongs to without moving it back into a collision.
        if math.hypot(lx - pos[medoid][0], ly - pos[medoid][1]) > LEADER_AT * layout_span:
            ax.plot([pos[medoid][0], lx], [pos[medoid][1], ly],
                    color=S.CHROME["axis"], linewidth=0.7, zorder=5,
                    solid_capstyle="round")
        ax.annotate(
            S.label(f"{name} ({count})"), xy=(lx, ly),
            ha="center", va="center", fontsize=8.2, zorder=6,
            color=S.CHROME["text_primary"],
            bbox=dict(boxstyle="round,pad=0.22", facecolor=S.CHROME["surface"],
                      edgecolor="none", alpha=0.86),
        )

    # The headline numbers, recomputed here rather than quoted from prose.
    inside = sum(1 for p in people for _w, q in picks[p]
                 if bloc.get(q, "No bloc") == bloc.get(p, "No bloc"))
    total = sum(len(picks[p]) for p in people)
    n = len(people)
    chance = sum(c * (c - 1) for c in sizes.values()) / (n * (n - 1))

    per_bloc = {}
    for name, count in sizes.items():
        members = [p for p in people if bloc.get(p, "No bloc") == name]
        hits = sum(1 for p in members for _w, q in picks[p]
                   if bloc.get(q, "No bloc") == name)
        picked = sum(len(picks[p]) for p in members)
        bloc_chance = (count - 1) / (n - 1)
        per_bloc[name] = (hits, picked, hits / picked, bloc_chance,
                          (hits / picked) / bloc_chance if bloc_chance else float("nan"))
    biggest = top[0]
    largest_lift = max(per_bloc.items(), key=lambda kv: kv[1][4])

    S.titles(
        ax,
        "Every bloc votes closest to its own — the biggest least distinctively",
        f"Each of the {n} members of the 2011 Constituent Assembly is joined to "
        f"their {K} closest voting alignments: the colleagues they voted with "
        f"most often\nacross the contested divisions both cast. Edge width and "
        f"opacity are the alignment level itself, {lo:.2f} to {hi:.2f}; node size "
        "is how many members count that one\namong their three closest. "
        f"{inside} of {total} nearest alignments stay inside the member's own "
        f"bloc, against {chance:.1%} if partners were drawn at random.\n"
        f"Correcting for bloc size inverts the ranking: {biggest} has the "
        f"highest raw share ({per_bloc[biggest][2]:.0%}) and the lowest lift over "
        f"chance ({per_bloc[biggest][4]:.1f}x), being\n{sizes[biggest]} of {n} "
        f"members, while {largest_lift[0]} reaches {largest_lift[1][4]:.1f}x on "
        f"{largest_lift[1][2]:.0%}. A threshold cannot show this: the full "
        "agreement graph is 99.6%\ncomplete and its weights are uniform enough "
        "that the disparity filter extracts no backbone at all. A tie is a "
        "correlation between two voting records,\nnot an act, and bloc is each "
        "member's last recorded spell in a chamber where 105 of 217 changed "
        "party.",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=colour[b], label=S.label(f"{b} ({sizes[b]})"))
            for b in top
        ] + [
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=other_colour,
                          label=S.label(f"Other blocs ({sum(v for k_, v in sizes.items() if k_ not in top)})")),
        ],
        loc="upper right", fontsize=8.2, framealpha=0.92,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for person in people:
        own = bloc.get(person, "No bloc")
        chosen = picks[person]
        rows.append({
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": own,
            "closest_allies_in_own_bloc": sum(
                1 for _w, q in chosen if bloc.get(q, "No bloc") == own),
            "closest_ally": persons.get(chosen[0][1], {}).get("name_lat", chosen[0][1]),
            "closest_ally_bloc": bloc.get(chosen[0][1], "No bloc"),
            "closest_ally_agreement": round(chosen[0][0], 4),
            "mean_agreement_of_top3": round(sum(w for w, _q in chosen) / len(chosen), 4),
            "times_chosen_by_others": chosen_by[person],
            "bloc_observed_share": round(per_bloc[own][2], 4),
            "bloc_chance_share": round(per_bloc[own][3], 4),
            "bloc_lift": round(per_bloc[own][4], 3),
        })
    S.save(fig, "fig42_alignment_network_nca2011", rows)


if __name__ == "__main__":
    main()
