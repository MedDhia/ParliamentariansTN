"""Shared machinery for the pre/post Brahmi affinity networks (figures 44 and 45).

Two network drawings are only comparable if everything except the ties is held
identical, and almost nothing about a spring layout is identical by default.
This module fixes the four things that would otherwise differ and make the
comparison meaningless:

**One panel.** Both figures draw the same 196 members — those scoreable in both
windows — so a node never appears in one drawing and not the other.

**One set of coordinates.** The layout is computed once, on the *pooled* graph
of both windows, and reused. Laying each period out separately would produce two
pictures whose differences are mostly the optimiser's, and a reader would have no
way to tell those apart from a change in the chamber. Pooling rather than using
the pre-crisis layout keeps either period from being the privileged one.

**One threshold.** Applied to both.

**One division count.** This is the subtle one. Agreement is a *rate*, and a rate
estimated from 94 divisions is noisier than one estimated from 417. Thresholding
a noisy estimate keeps more pairs by chance alone, so a window with fewer
divisions looks denser at any cut-off — an artefact that runs in exactly the
direction that would flatter a "the chamber fell apart" story. The windows are
matched on *sitting days* to keep exposure comparable, and the post window is
then subsampled to the pre window's division count, spread across its days, so
the drawn edges are estimated from the same amount of evidence.

Why sitting days and not divisions alone: the pre-crisis window is 94 contested
divisions spread over 32 sitting days across a year, while the 94 divisions
immediately after resumption fall on four days, 78 of them in a single sitting.
Matching on divisions alone would compare a year of ordinary business against one
afternoon. Matching days first and subsampling second matches both.

The statistics the figures quote are *mean* agreement, which needs no threshold
and carries no such artefact; the threshold exists only so there is something to
draw.
"""

from __future__ import annotations

import collections
import random
import statistics
import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import fig43_brahmi_crisis_nca2011 as CRISIS  # noqa: E402

# Ties drawn at nine divisions in ten. High enough that an edge means "these two
# reliably vote together" rather than "these two are both in the chamber", which
# at a chamber-wide mean of 0.71 is what a lower cut-off would mean.
THRESHOLD = 0.90
SEED = 20260830
LAYOUT_SEED = 44


def windows() -> dict[str, list[str]]:
    """Return contested divisions for the pre window and the two after it.

    Each window is the same number of *sitting days* as the pre-crisis window,
    so the three cover comparable stretches of parliamentary time rather than
    comparable counts of votes.
    """
    dates, positions = CRISIS.load()
    people = sorted(positions)
    contested = CRISIS.contested(dates, positions, people)
    by_window: dict[str, list[str]] = collections.defaultdict(list)
    for vote_id in contested:
        by_window[CRISIS.window(dates[vote_id])].append(vote_id)
    for name in by_window:
        by_window[name].sort(key=lambda v: (dates[v], v))
    pre_days = sorted({dates[v] for v in by_window["before"]})
    post_days = sorted({dates[v] for v in by_window["after"]})
    span = len(pre_days)
    out = {"before": by_window["before"]}
    for index, name in enumerate(("after", "after_later")):
        chunk = set(post_days[index * span:(index + 1) * span])
        if len(chunk) < span:
            break
        out[name] = [v for v in by_window["after"] if dates[v] in chunk]
    return out


def subsample(vote_ids: list[str], target: int, dates: dict[str, str],
              seed: int = SEED) -> list[str]:
    """Take ``target`` divisions spread evenly across the window's sitting days.

    Drawing at random from the window as a whole would over-weight the days that
    produced the most divisions, which for this chamber means a single sitting in
    December 2013. Taking an equal share from each day first keeps the subsample
    spread the way the pre-crisis window is spread.
    """
    if len(vote_ids) <= target:
        return sorted(vote_ids)
    rng = random.Random(seed)
    by_day: dict[str, list[str]] = collections.defaultdict(list)
    for vote_id in vote_ids:
        by_day[dates[vote_id]].append(vote_id)
    days = sorted(by_day)
    picked: list[str] = []
    per_day = target // len(days)
    for day in days:
        pool = sorted(by_day[day])
        rng.shuffle(pool)
        picked.extend(pool[:per_day])
    remainder = sorted(set(vote_ids) - set(picked))
    rng.shuffle(remainder)
    picked.extend(remainder[:target - len(picked)])
    return sorted(picked)


def prepare() -> dict[str, object]:
    """Build both windows' scores, the shared panel and the shared coordinates."""
    dates, positions = CRISIS.load()
    people = sorted(positions)
    segments = windows()
    target = len(segments["before"])

    drawn = {
        name: (ids if name == "before" else subsample(ids, target, dates))
        for name, ids in segments.items()
    }
    scores = {name: CRISIS.agreement(positions, people, ids)
              for name, ids in drawn.items()}
    full = {name: CRISIS.agreement(positions, people, ids)
            for name, ids in segments.items()}

    panel = sorted(set(scores["before"]) & set(scores["after"]))
    members = sorted({p for pair in panel for p in pair})

    pos = mds_layout(panel, members, scores)

    # One frame for both figures. Four members sit far enough out that letting
    # them set the axis limits squashes the other 192 into a band across the
    # middle, so the frame is the 1st-to-99th percentile of the coordinates with
    # a margin. They are clipped, not dropped: both figures use the identical
    # box, so the comparison is unaffected, and each says how many are outside.
    xs = sorted(p[0] for p in pos.values())
    ys = sorted(p[1] for p in pos.values())
    n = len(xs)
    lo, hi = int(0.01 * n), int(0.99 * n)
    pad_x = (xs[hi] - xs[lo]) * 0.06
    pad_y = (ys[hi] - ys[lo]) * 0.06
    limits = (xs[lo] - pad_x, xs[hi] + pad_x, ys[lo] - pad_y, ys[hi] + pad_y)
    clipped = sum(1 for q in pos.values()
                  if not (limits[0] <= q[0] <= limits[1]
                          and limits[2] <= q[1] <= limits[3]))

    return {
        "dates": dates, "positions": positions, "segments": segments,
        "drawn": drawn, "scores": scores, "full": full,
        "panel": panel, "members": members, "pos": pos,
        "bloc": POL.blocs(), "target": target,
        "limits": limits, "clipped": clipped,
    }



def mds_layout(panel, members, scores) -> dict[str, tuple[float, float]]:
    """Position every member by classical MDS on the pooled agreement distances.

    Both figures share this frame. Distance between two members is one minus
    their mean agreement across the two windows, so neither period is the
    reference the other is judged against.

    **Why not a spring layout.** A force simulation on a near-complete weighted
    graph pushes its weakest-tied nodes to the edge of the canvas, and half a
    dozen of them then set the axis limits while the other 190 collapse into a
    knot in the middle. MDS places every member by its distance to all 195
    others at once, which spreads the middle and keeps the outliers in
    proportion. It is also deterministic: no seed, so the two figures cannot
    drift apart between runs.

    **What the axes are.** The first two dimensions of the agreement structure,
    carrying most of what a 2-D picture of it can carry. They are not
    ideal points: figure 21 fits the comparable thing properly, by decomposing
    the vote matrix rather than the pairwise agreements derived from it. Read
    position here as "who this member votes like", not as a policy coordinate.

    The sign of an eigenvector is arbitrary, so the frame is oriented
    explicitly — largest bloc to the left, and the second axis fixed by the same
    rule — or the two figures could come out mirrored from one run to the next.
    """
    import numpy as np

    index = {member: i for i, member in enumerate(members)}
    n = len(members)
    distances = np.zeros((n, n))
    for pair in panel:
        mean = (scores["before"][pair] + scores["after"][pair]) / 2
        i, j = index[pair[0]], index[pair[1]]
        distances[i, j] = distances[j, i] = 1.0 - mean

    centring = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centring.dot(distances ** 2).dot(centring)
    values, vectors = np.linalg.eigh(gram)
    order = np.argsort(values)[::-1][:2]
    coords = vectors[:, order] * np.sqrt(np.maximum(values[order], 0))

    bloc = POL.blocs()
    sizes = collections.Counter(bloc.get(m, "No bloc") for m in members)
    biggest = max(sorted(sizes), key=lambda b: sizes[b])
    mask = np.array([bloc.get(m, "No bloc") == biggest for m in members])
    for axis in (0, 1):
        # Orient so the largest bloc sits on the negative side of both axes.
        # np.linalg.eigh fixes an eigenvector only up to sign.
        if coords[mask, axis].mean() > coords[~mask, axis].mean():
            coords[:, axis] *= -1
    return {member: (float(coords[i, 0]), float(coords[i, 1]))
            for member, i in index.items()}


def means(scores, panel, bloc) -> tuple[float, float]:
    """Mean within-bloc and cross-bloc agreement over a set of pairs."""
    within = [scores[p] for p in panel
              if bloc.get(p[0], "No bloc") == bloc.get(p[1], "No bloc")]
    cross = [scores[p] for p in panel
             if bloc.get(p[0], "No bloc") != bloc.get(p[1], "No bloc")]
    return statistics.fmean(within), statistics.fmean(cross)


def graph_of(scores, panel, members, threshold: float = THRESHOLD) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(members)
    for pair in panel:
        if scores[pair] >= threshold:
            graph.add_edge(pair[0], pair[1], weight=scores[pair])
    return graph


def tie_counts(graph, bloc) -> tuple[int, int]:
    within = sum(1 for a, b in graph.edges()
                 if bloc.get(a, "No bloc") == bloc.get(b, "No bloc"))
    return within, graph.number_of_edges() - within


def draw(ax, data, name: str):
    """Render one window's network into ``ax``. Both figures call this.

    Sharing the routine rather than copying it is part of the comparison's
    integrity: node size, edge width, opacity and colour rules cannot drift
    between the two figures if there is only one copy of them.

    Within-bloc ties are drawn in the neutral and cross-bloc ties in the accent,
    because the count that moves most between the two periods is the cross-bloc
    one and a reader should be able to see it rather than take it on trust.
    """
    import matplotlib.lines as mlines

    import _style as S

    bloc, panel, members, pos = data["bloc"], data["panel"], data["members"], data["pos"]
    scores = data["scores"][name]
    pairs = [p for p in panel if p in scores]
    graph = graph_of(scores, pairs, members)

    sizes = collections.Counter(bloc.get(p, "No bloc") for p in members)
    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour = {b: palette[i] for i, b in enumerate(top)}
    other_colour = palette[-1]
    accent = palette[1]

    within_edges, cross_edges = [], []
    for a, b in graph.edges():
        (within_edges if bloc.get(a, "No bloc") == bloc.get(b, "No bloc")
         else cross_edges).append((a, b))
    # Both kinds are drawn at the same width and near the same opacity. An
    # earlier version gave cross-bloc ties twice the width and five times the
    # opacity, which made a quarter of the edges look like most of the ink and
    # would have inverted the figure's own finding.
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=within_edges, width=0.3,
                           edge_color=[(0.0, 0.0, 0.0, 0.085)] * len(within_edges))
    nx.draw_networkx_edges(graph, pos, ax=ax, edgelist=cross_edges, width=0.3,
                           edge_color=[accent] * len(cross_edges), alpha=0.16)

    degree = dict(graph.degree())
    ceiling = max(degree.values()) or 1
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, nodelist=members,
        node_size=[14 + 74 * (degree[p] / ceiling) for p in members],
        node_color=[colour.get(bloc.get(p, "No bloc"), other_colour) for p in members],
        linewidths=0.6, edgecolors=S.CHROME["surface"])
    ax.set_axis_off()
    # Equal aspect: MDS coordinates are distances, so stretching one axis to
    # fill the canvas would misstate how far apart two members are.
    ax.set_aspect("equal")
    ax.set_xlim(data["limits"][0], data["limits"][1])
    ax.set_ylim(data["limits"][2], data["limits"][3])

    handles = [mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                             color=colour[b], label=S.label(f"{b} ({sizes[b]})"))
               for b in top]
    handles.append(mlines.Line2D(
        [], [], marker="o", linestyle="none", markersize=7, color=other_colour,
        label=S.label(f"Other blocs ({sum(v for k, v in sizes.items() if k not in top)})")))
    handles.append(mlines.Line2D([], [], color=accent, linewidth=1.6,
                                 label=S.label("Cross-bloc tie")))
    handles.append(mlines.Line2D([], [], color=(0.0, 0.0, 0.0, 0.35), linewidth=1.0,
                                 label=S.label("Within-bloc tie")))
    ax.legend(handles=handles, loc="upper right", fontsize=8.0, framealpha=0.92)
    return graph
