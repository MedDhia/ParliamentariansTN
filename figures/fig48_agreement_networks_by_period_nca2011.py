"""Figure 48 — The agreement network, one panel per quarter of the term.

The small-multiples form Andris et al. (2015) used for the US House: a
force-directed agreement network per period, nodes coloured by party, one
threshold throughout, read left to right for whether the parties pull apart.
It is the standard picture of polarisation-over-time in a legislature and this
set did not have it — figure 34 draws the same network once, for the whole term.

**The construction.** The 993 contested divisions are cut into four consecutive
blocks of ~248. The panel is the 206 of 217 members scoreable in all four, so a
node never appears in one drawing and not another, and two members are joined
wherever they voted alike on at least 75% of the divisions they both cast in that
block — the repo's tie threshold throughout the polarisation figures, chosen
because it sits above the chamber-wide mean of 0.72.

**The layouts are independent, which is the convention and also its weakness.**
Andris et al. lay each Congress out separately, and that is what this figure
does: same algorithm, same seed, same parameters, run four times. The cost is
that a force simulation moves nodes for reasons of its own, so *how far apart the
two clumps look* between panels is not evidence of anything. That is the standard
criticism of the form, and rather than quietly inherit it this figure prints the
number the geometry is standing in for — the share of ties that cross a bloc
boundary — under every panel. Read those; use the drawings for shape.

**What the numbers say.** The cross-bloc share moves within a narrow band and
not in one direction, which is figure 46's finding arriving by a third route:
this chamber does not polarise as it goes. It begins bloc-structured and ends
bloc-structured, through the constitution's drafting, two assassinations and a
change of government.

**What the drawings say that the numbers do not.** Every panel has the same
shape — one dense clump and one loose cloud, not two comparable clusters. That
asymmetry is figure 34's finding: Ennahdha's internal density at this threshold
is 0.998 against 0.269 for the other 130 members. A reader who knows the US
House figure will expect two lobes pulling apart and should see instead a clique
and a crowd, stable across the term.

**Three cautions.** The panels are repeated measures on one chamber, not
independent samples, so no trend line belongs on them. Participation falls
across the term (figure 25), and the fixed panel handles that only for the 206
who cleared the floor everywhere — the 11 who did not are absent from all four
drawings rather than from one. And bloc is each member's last recorded spell in a
chamber where 105 of 217 changed party, so early panels are coloured by an
end-of-term map.
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
BLOCKS = 4
FLOOR = 20
THRESHOLD = POL.TIE_THRESHOLD
SEED = 20260831


def load():
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
    sub = matrix[:, columns]
    yes, no = (sub == 1).astype(float), (sub == -1).astype(float)
    voted = (sub != 0).astype(float)
    shared = voted @ voted.T
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = np.where(shared >= FLOOR, (yes @ yes.T + no @ no.T) / shared, np.nan)
    np.fill_diagonal(rate, np.nan)
    return rate


def main() -> None:
    people, votes, dates, matrix = load()
    if not votes:
        raise SystemExit("no dated divisions for NCA-2011; run `make build`")
    columns = contested(matrix)
    size = len(columns) // BLOCKS
    chunks = [columns[i * size:(i + 1) * size if i < BLOCKS - 1 else None]
              for i in range(BLOCKS)]
    rates = [agreement(matrix, chunk) for chunk in chunks]

    keep = np.flatnonzero(np.all([np.isfinite(r).any(axis=1) for r in rates], axis=0))
    names = [people[i] for i in keep]
    rates = [r[np.ix_(keep, keep)] for r in rates]
    bloc = POL.blocs(ASSEMBLY)
    labels = [bloc.get(p, "No bloc") for p in names]
    sizes = collections.Counter(labels)
    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour_of = {b: palette[i] for i, b in enumerate(top)}
    node_colours = [colour_of.get(b, palette[-1]) for b in labels]

    fig, axes = plt.subplots(2, 2, figsize=S.figsize(9.8, 8.6))
    flat = list(np.ravel(axes))
    rows = []
    for panel, (ax, chunk, rate) in enumerate(zip(flat, chunks, rates)):
        graph = nx.Graph()
        # Nodes added in sorted order so the layout is reproducible: iterating a
        # set of ids is not, once Python's string hashing enters.
        graph.add_nodes_from(range(len(names)))
        upper = np.triu_indices(len(names), 1)
        chosen = np.isfinite(rate[upper]) & (rate[upper] >= THRESHOLD)
        graph.add_edges_from(zip(upper[0][chosen].tolist(), upper[1][chosen].tolist()))
        # Independent layout per panel: the convention this figure follows, and
        # the reason the cross-bloc share is printed rather than left to the eye.
        pos = nx.spring_layout(graph, seed=SEED, k=0.30, iterations=240)

        crossing = sum(1 for a, b in graph.edges() if labels[a] != labels[b])
        total = graph.number_of_edges()
        nx.draw_networkx_edges(graph, pos, ax=ax, width=0.25,
                               edge_color=[(0.0, 0.0, 0.0, 0.06)] * total)
        degree = dict(graph.degree())
        ceiling = max(degree.values()) or 1
        nx.draw_networkx_nodes(
            graph, pos, ax=ax,
            node_size=[10 + 46 * degree[i] / ceiling for i in range(len(names))],
            node_color=node_colours, linewidths=0.4,
            edgecolors=S.CHROME["surface"])
        ax.set_axis_off()
        ax.set_aspect("equal")
        # A spring layout parks its weakest-tied nodes far from everything else,
        # and with an equal aspect two of them are enough to squash the other
        # 204 into a dot. Frame each panel on the 1st-to-99th percentile of its
        # own coordinates; the outliers are clipped, not dropped, and the count
        # is printed under the panel.
        xs = sorted(q[0] for q in pos.values())
        ys = sorted(q[1] for q in pos.values())
        lo, hi = int(0.01 * len(xs)), int(0.99 * len(xs)) - 1
        pad_x = (xs[hi] - xs[lo]) * 0.07
        pad_y = (ys[hi] - ys[lo]) * 0.07
        box = (xs[lo] - pad_x, xs[hi] + pad_x, ys[lo] - pad_y, ys[hi] + pad_y)
        clipped = sum(1 for q in pos.values()
                      if not (box[0] <= q[0] <= box[1] and box[2] <= q[1] <= box[3]))
        ax.set_xlim(box[0], box[1])
        ax.set_ylim(box[2], box[3])
        first, last = dates[votes[chunk[0]]], dates[votes[chunk[-1]]]
        ax.set_title(S.label(f"{first[:7]} → {last[:7]} · {len(chunk)} divisions"),
                     loc="left", fontsize=9.4, color=S.CHROME["text_primary"], pad=4)
        ax.annotate(
            S.label(f"{total:,} ties · {crossing / total:.0%} cross a bloc"
                    + (f" · {clipped} outside the frame" if clipped else "")),
            xy=(0.5, -0.01), xycoords="axes fraction", ha="center", va="top",
            fontsize=8.4, color=S.CHROME["text_primary"])
        rows.append({
            "period": panel + 1, "first_division": first, "last_division": last,
            "divisions": len(chunk), "members": len(names), "ties": total,
            "cross_bloc_ties": crossing,
            "cross_bloc_share": round(crossing / total, 4) if total else "",
            "nodes_outside_frame": clipped,
        })

    fig.legend(handles=[
        mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                      color=colour_of[b], label=S.label(f"{b} ({sizes[b]})"))
        for b in top
    ] + [
        mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                      color=palette[-1],
                      label=S.label(f"Other blocs "
                                    f"({sum(v for k, v in sizes.items() if k not in top)})")),
    ], loc="upper left", bbox_to_anchor=(0.010, 0.845), ncols=3, fontsize=8.4,
        frameon=False)

    shares = [r["cross_bloc_share"] for r in rows]
    fig.subplots_adjust(left=0.02, right=0.98, top=0.78, bottom=0.045,
                        hspace=0.16, wspace=0.04)
    fig.text(0.010, 0.985,
             "A clique and a crowd, four times: the assembly does not pull apart "
             "as it goes",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.010, 0.950,
        f"The agreement network drawn once per quarter of the term, as Andris et "
        f"al. (2015) drew the US House Congress by Congress. Same {len(names)} "
        f"members in all four panels — those scoreable in every\nblock — same "
        f"{THRESHOLD:.0%} threshold, and two members joined wherever they voted "
        f"alike that often on the divisions they both cast. The share of ties "
        f"crossing a bloc goes "
        f"{' → '.join(f'{s:.0%}' for s in shares)} — down and back up, with no\n"
        f"trend in it, which is figure 46's finding by a third route. The first "
        f"panel is the outlier and the reason is its span: equal *divisions* per "
        f"panel makes it seventeen months where the others are one to five, so it "
        f"mixes\nmore agendas. The layouts are independent, as in the original, so how far "
        f"apart two clumps *look* between panels is not evidence — the printed "
        f"share is what\ncarries the comparison. What the drawings do add is the "
        f"shape a reader of the US figure will not expect: not two lobes pulling "
        f"apart but one dense clique and one loose cloud, stable across the term "
        f"(figure 34\nputs Ennahdha's internal density at 0.998 against 0.269 for "
        f"everyone else). Panels are repeated measures on one chamber, not "
        f"independent samples. Bloc is each member's last recorded spell.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")
    S.save(fig, "fig48_agreement_networks_by_period_nca2011", rows)


if __name__ == "__main__":
    main()
