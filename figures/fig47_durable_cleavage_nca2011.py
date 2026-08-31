"""Figure 47 — The polarisation as a network: what persists against what does not.

Figure 46 established that the 2011 assembly's dividing line is one line and a
durable one. Sittings a year apart split the chamber as similarly as sittings a
month apart — mean |φ| 0.210 against 0.198, correlation with elapsed days
+0.006 — and a network of the 87 sitting days has a modularity of 0.052, which is
no community structure at all. There are no episodes here to separate.

That is what makes a *tie-level* map worth drawing. If the cleavage were a
sequence of issue coalitions, a network of who agrees with whom would be an
average over several different chambers and would mean little. Because it is one
line, the interesting question is which ties belong to it.

**The construction.** The term's 993 contested divisions are cut into four
consecutive blocks of ~248, and every pair scoreable in all four (18,428 pairs
over 206 of 217 members) is asked how many blocks it clears the repo's 0.75 tie
threshold in. Two panels then draw the same members in the same coordinates:
those clearing it in **all four** blocks, and those clearing it in **exactly
one**.

**The result is a clean separation, and it runs the length of the scale.** Of the
pairs that clear the threshold in one block only, 5.9% are co-partisans. Of those
clearing it in all four, 76.5% are. The intermediate counts sit in order between
them — 9.4% at two blocks, 16.9% at three — so this is not a threshold artefact
but a monotone relationship between how durable a tie is and how likely it is to
be a bloc tie. At the stricter 0.90 cut the same ordering runs 30.0%, 76.6%,
94.2%, 97.3%.

So the two panels are not two views of one network. Panel A is the chamber's
skeleton: bloc structure, and almost nothing else. Panel B is a mesh that mostly
ignores bloc boundaries. Only 34% of the ties that are ever strong are strong
throughout, so most high agreement in this chamber is transient and
cross-cutting, and the part that persists is the part that is partisan.

This is the same fact figures 44 and 45 met from the other direction: cross-bloc
strong ties survived one 32-sitting-day gap 19–23% of the time whether or not an
assassination fell in it, because they were never durable to begin with.

**What the panels do not say.** Nothing here is causal, and "durable" is a
property of a measurement window, not a claim about intent: a pair may agree
throughout because they share a bloc whip, a constituency, or a view. The panel
is the 206 members scoreable in all four blocks, which is nearly the whole
chamber but not quite — 11 members voted too little in at least one block.
Bloc is each member's last recorded spell, undated, in a chamber where 105 of 217
changed party, so the within-bloc shares above are measured against an
end-of-term map; that biases *against* the finding, since a member scored in the
wrong bloc adds noise to both panels alike.

**Why both edge kinds are drawn identically.** Same width, same opacity, same
colour. An earlier figure in this set gave one kind twice the width and five
times the opacity of the other and inverted its own finding; here the whole claim
is a comparison between two panels, so any asymmetry in how they are drawn would
be the thing the reader sees.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_CAST, MIN_MINORITY = 40, 0.025
# Four blocks: enough that "all four" is a real demand, few enough that each
# still carries ~248 divisions and most pairs clear the scoring floor in all of
# them. At eight blocks the panel falls to 150 members and the floor, not
# behaviour, decides who appears.
BLOCKS = 4
FLOOR = 20
# The repo's tie threshold throughout the polarisation figures: above the
# chamber-wide mean of 0.72, so an edge means "agrees more than the average pair".
THRESHOLD = POL.TIE_THRESHOLD


def load() -> tuple[list[str], list[str], dict[str, str], np.ndarray]:
    dates = {r["vote_id"]: r["vote_date"] for r in S.load("votes")
             if r["assembly_id"] == ASSEMBLY and r["vote_date"]}
    positions: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["vote_id"] not in dates:
            continue
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1
    people = sorted(positions)
    votes = sorted(dates, key=lambda v: (dates[v], v))
    index = {v: j for j, v in enumerate(votes)}
    matrix = np.zeros((len(people), len(votes)), dtype=np.int8)
    for i, person in enumerate(people):
        for vote_id, side in positions[person].items():
            matrix[i, index[vote_id]] = side
    return people, votes, dates, matrix


def contested(matrix: np.ndarray) -> np.ndarray:
    yes, no = (matrix == 1).sum(0), (matrix == -1).sum(0)
    cast = yes + no
    with np.errstate(invalid="ignore", divide="ignore"):
        minority = np.where(cast > 0, np.minimum(yes, no) / np.maximum(cast, 1), 0.0)
    return np.flatnonzero((cast >= MIN_CAST) & (minority >= MIN_MINORITY))


def agreement(matrix: np.ndarray, columns: np.ndarray) -> np.ndarray:
    """Pairwise agreement over one block; NaN below the shared-division floor."""
    sub = matrix[:, columns]
    yes, no = (sub == 1).astype(float), (sub == -1).astype(float)
    voted = (sub != 0).astype(float)
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(voted @ voted.T >= FLOOR,
                        (yes @ yes.T + no @ no.T) / (voted @ voted.T), np.nan)
    np.fill_diagonal(rate, np.nan)
    return rate


def mds_layout(mean_agreement: np.ndarray, is_biggest: np.ndarray):
    """Classical MDS on 1 − mean agreement, oriented so the run is repeatable.

    The same choice as figures 44 and 45, and for the same reason: a force
    simulation on a near-complete weighted graph pushes its weakest-tied nodes to
    the canvas edge and collapses everything else into the middle, and it moves
    them for reasons of its own that a reader cannot distinguish from the data.
    MDS places every member against all 205 others at once and needs no seed.
    """
    distance = 1.0 - np.where(np.isnan(mean_agreement),
                              np.nanmean(mean_agreement), mean_agreement)
    np.fill_diagonal(distance, 0.0)
    n = distance.shape[0]
    centring = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centring.dot(distance ** 2).dot(centring)
    values, vectors = np.linalg.eigh(gram)
    order = np.argsort(values)[::-1][:2]
    coords = vectors[:, order] * np.sqrt(np.maximum(values[order], 0))
    for axis in (0, 1):
        # eigh fixes an eigenvector only up to sign; pin it or the two panels
        # can come out mirrored between runs.
        if coords[is_biggest, axis].mean() > coords[~is_biggest, axis].mean():
            coords[:, axis] *= -1
    return coords


def draw(ax, edges, coords, colours, sizes, title, note):
    """Render one edge set. Both panels call this, so nothing can drift."""
    graph = nx.Graph()
    graph.add_nodes_from(range(len(coords)))
    graph.add_edges_from(edges)
    pos = {i: (float(coords[i, 0]), float(coords[i, 1])) for i in range(len(coords))}
    nx.draw_networkx_edges(graph, pos, ax=ax, width=0.3,
                           edge_color=[(0.0, 0.0, 0.0, 0.075)] * graph.number_of_edges())
    degree = dict(graph.degree())
    ceiling = max(degree.values()) or 1
    nx.draw_networkx_nodes(
        graph, pos, ax=ax, node_size=[14 + 70 * degree[i] / ceiling for i in range(len(coords))],
        node_color=colours, linewidths=0.6, edgecolors=S.CHROME["surface"])
    ax.set_axis_off()
    # Equal aspect: MDS coordinates are distances, so stretching an axis to fill
    # the canvas would misstate how far apart two members are.
    ax.set_aspect("equal")
    ax.set_title(S.label(title), loc="left", fontsize=9.6,
                 color=S.CHROME["text_primary"], pad=6)
    ax.annotate(S.label(note), xy=(0.5, -0.02), xycoords="axes fraction",
                ha="center", va="top", fontsize=8.0,
                color=S.CHROME["text_secondary"])
    return graph


def main() -> None:
    people, votes, dates, matrix = load()
    if not votes:
        raise SystemExit("no dated divisions for NCA-2011; run `make build`")
    columns = contested(matrix)
    size = len(columns) // BLOCKS
    chunks = [columns[i * size:(i + 1) * size if i < BLOCKS - 1 else None]
              for i in range(BLOCKS)]
    blocks = [agreement(matrix, chunk) for chunk in chunks]

    scoreable = np.all([np.isfinite(b) for b in blocks], axis=0)
    panel = np.flatnonzero(scoreable.any(axis=1))
    blocks = [b[np.ix_(panel, panel)] for b in blocks]
    scoreable = scoreable[np.ix_(panel, panel)]
    names = [people[i] for i in panel]
    bloc = POL.blocs(ASSEMBLY)
    labels = np.array([bloc.get(p, "No bloc") for p in names])

    hits = np.sum([b >= THRESHOLD for b in blocks], axis=0)
    upper = np.triu_indices(len(panel), 1)
    usable = scoreable[upper]
    same = labels[upper[0]] == labels[upper[1]]

    ladder = []
    for count in range(1, BLOCKS + 1):
        picked = usable & (hits[upper] == count)
        ladder.append({
            "ties_clearing_blocks": count,
            "pairs": int(picked.sum()),
            "within_bloc_pairs": int(same[picked].sum()),
            "within_bloc_share": round(float(same[picked].mean()), 4) if picked.sum() else "",
        })

    def edge_set(count_test):
        keep = scoreable & count_test(hits)
        a, b = np.triu_indices(len(panel), 1)
        chosen = keep[a, b]
        return list(zip(a[chosen].tolist(), b[chosen].tolist()))

    durable = edge_set(lambda h: h == BLOCKS)
    episodic = edge_set(lambda h: h == 1)

    # Mean over the blocks a pair is scoreable in. np.nanmean would do it but
    # warns on the all-NaN rows of members who never clear the floor, and a
    # warning in a figure script is noise a reader learns to ignore.
    stack = np.stack(blocks)
    seen = np.isfinite(stack).sum(axis=0)
    mean_agreement = np.where(seen > 0, np.nansum(stack, axis=0) / np.maximum(seen, 1),
                              np.nan)
    sizes = collections.Counter(labels)
    # Ties broken by name: dict order would otherwise decide, and it is not
    # stable across processes once string hashing enters.
    biggest = max(sorted(sizes), key=lambda b: sizes[b])
    coords = mds_layout(mean_agreement, labels == biggest)

    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour_of = {b: palette[i] for i, b in enumerate(top)}
    node_colours = [colour_of.get(b, palette[-1]) for b in labels]

    ever_strong = sum(entry["pairs"] for entry in ladder)

    def within_share(edges):
        if not edges:
            return float("nan")
        return float(np.mean([labels[a] == labels[b] for a, b in edges]))

    fig = plt.figure(figsize=S.figsize(10.2, 7.2))
    grid = fig.add_gridspec(2, 2, height_ratios=(1.0, 0.40), hspace=0.30, wspace=0.06)
    ax_a, ax_b = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, :])

    graph_a = draw(ax_a, durable, coords, node_colours, sizes,
                   f"A · Ties that clear {THRESHOLD:.2f} in all {BLOCKS} blocks",
                   f"{len(durable):,} ties · {within_share(durable):.0%} within bloc")
    draw(ax_b, episodic, coords, node_colours, sizes,
         f"B · Ties that clear it in exactly one",
         f"{len(episodic):,} ties · {within_share(episodic):.0%} within bloc")
    # One frame for both, so a reader cannot mistake a change of scale for a
    # change in the chamber.
    limits = (coords[:, 0].min(), coords[:, 0].max(),
              coords[:, 1].min(), coords[:, 1].max())
    pad_x = (limits[1] - limits[0]) * 0.06
    pad_y = (limits[3] - limits[2]) * 0.06
    for ax in (ax_a, ax_b):
        ax.set_xlim(limits[0] - pad_x, limits[1] + pad_x)
        ax.set_ylim(limits[2] - pad_y, limits[3] + pad_y)
    ax_a.legend(handles=[
        mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                      color=colour_of[b], label=S.label(f"{b} ({sizes[b]})"))
        for b in top
    ] + [
        mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                      color=palette[-1],
                      label=S.label(f"Other blocs ({sum(v for k, v in sizes.items() if k not in top)})")),
    ], loc="upper left", fontsize=8.0, framealpha=0.92)

    # C — the ladder the two panels are the ends of. Drawn in the neutral: it is
    # a single series, and every hue in this figure already means a bloc.
    xs = [r["ties_clearing_blocks"] for r in ladder]
    ys = [r["within_bloc_share"] for r in ladder]
    ax_c.bar(xs, ys, width=0.55, color=S.CHROME["axis"], zorder=3)
    for r in ladder:
        ax_c.annotate(f"{r['within_bloc_share']:.1%}\n{r['pairs']:,} pairs",
                      xy=(r["ties_clearing_blocks"], r["within_bloc_share"]),
                      xytext=(0, 5), textcoords="offset points", ha="center",
                      fontsize=8.0, color=S.CHROME["text_primary"], zorder=4)
    ax_c.set_xticks(xs)
    ax_c.set_xticklabels([S.label(f"{k} of {BLOCKS}") for k in xs], fontsize=8.4)
    ax_c.set_ylim(0, max(ys) * 1.32)
    ax_c.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax_c.set_ylabel(S.label("Share within a bloc"), fontsize=8.4)
    ax_c.set_xlabel(S.label("Blocks of the term in which the pair clears the threshold"),
                    fontsize=8.4)
    ax_c.set_title(S.label("C · The two panels are the ends of a ladder, not a "
                           "dichotomy"),
                   loc="left", fontsize=9.6, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_c)

    fig.subplots_adjust(left=0.045, right=0.985, top=0.775, bottom=0.075)
    fig.text(0.010, 0.985,
             "What persists is partisan; what does not is cross-cutting",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.010, 0.952,
        f"Figure 46 found one dividing line in this chamber rather than a "
        f"sequence of them: sittings a year apart split it as similarly as "
        f"sittings a month apart, and a network of its 87 sitting days\nhas a "
        f"modularity of 0.052. That is what makes a map of the ties worth "
        f"drawing. The term's {len(columns)} contested divisions are cut into "
        f"{BLOCKS} consecutive blocks and each of the {int(usable.sum()):,} pairs "
        f"scoreable in all\nfour — {len(panel)} of 217 members — is asked how many "
        f"blocks it agrees in at least {THRESHOLD:.0%} of the time. Same members, "
        f"same coordinates, same threshold, same edge width and opacity in both "
        f"panels;\nonly the edge set differs. Of the ties that survive every "
        f"block {within_share(durable):.0%} are between members of one bloc, "
        f"against {within_share(episodic):.0%} of those that appear in a single "
        f"block, and the intermediate counts sit in order between them —\njust "
        f"{len(durable) / max(ever_strong, 1):.0%} "
        f"of the ties that are ever strong are strong throughout. Position is "
        f"classical MDS on mean agreement, shared by both panels, and is not an "
        f"ideal point: figure 21 fits those. Bloc is each\nmember's last recorded "
        f"spell, undated in a chamber where 105 of 217 changed party, which adds "
        f"noise to both panels alike rather than favouring either.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")

    rows = []
    for label, edges in (("durable_all_blocks", durable), ("single_block", episodic)):
        rows.append({
            "series": "edge_set", "group": label, "ties": len(edges),
            "within_bloc_ties": int(sum(labels[a] == labels[b] for a, b in edges)),
            "within_bloc_share": round(within_share(edges), 4),
            "ties_clearing_blocks": "", "pairs": "", "within_bloc_pairs": "",
        })
    for entry in ladder:
        rows.append({
            "series": "durability_ladder", "group": f"{entry['ties_clearing_blocks']} of {BLOCKS}",
            "ties": "", "within_bloc_ties": "", "within_bloc_share": entry["within_bloc_share"],
            "ties_clearing_blocks": entry["ties_clearing_blocks"],
            "pairs": entry["pairs"], "within_bloc_pairs": entry["within_bloc_pairs"],
        })
    rows.append({
        "series": "panel", "group": f"members scoreable in all {BLOCKS} blocks",
        "ties": len(panel), "within_bloc_ties": "", "within_bloc_share": "",
        "ties_clearing_blocks": "", "pairs": int(usable.sum()), "within_bloc_pairs": "",
    })
    S.save(fig, "fig47_durable_cleavage_nca2011", rows)


if __name__ == "__main__":
    main()
