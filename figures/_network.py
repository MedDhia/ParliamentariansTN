"""Shared coordinate system and drawing for the committee networks.

Three chambers get the same treatment, so the layout, colour rule and edge
filtering live here and the per-chamber scripts stay thin. ``Frame`` is the
coordinate system on its own: figure 17 draws the 2023 chamber's memberships in
exactly the positions figure 16 draws its projected ties in, so the pair can be
read against each other without anything having moved.

**Why this is not a force-directed drawing.** A committee co-membership network
is a *projection*: two deputies are tied because a roster put them on the same
committee. Checked against the data, the graph is exactly the union of the
committee cliques — every edge in NCA-2011 and ARP-2019 is reproduced by taking
each committee and joining all its members. A spring layout of a union of
overlapping cliques is a hairball, and worse, a hairball whose only real content
is the committee roster it started from. The earlier draft of these figures was
exactly that: 194 nodes, 4,009 edges, one dark blob.

So position is **computed from committee membership** rather than from a physics
simulation, and it means something specific:

- **angle** — which committees a deputy sits on. Committees are anchored around
  the rim; a deputy points toward hers.
- **distance from the centre** — how many. Sitting on one committee puts you on
  the rim inside that committee's lobe; each additional committee pulls you
  further in, so the deputies who bridge the most committees are the ones in the
  middle.
- **deputies with identical committee portfolios sit together**, because their
  position is computed from the same set.

This is deterministic — no seed, no run-to-run drift — and it is readable: the
lobes are the committees, and the interior is the bridging structure.

**Only ties of weight >= 2 are drawn.** In the previous version every one of the
several thousand ties was drawn with opacity scaled by weight, because filtering
to strong ties under a *spring* layout disconnected four fifths of the chamber
and left a ring of isolates orbiting a small core — a picture of the threshold
rather than of the parliament. That objection was about the layout, not the
filter: it applied because a spring layout gives a node with no surviving edges
no meaningful position. Here position comes from committee membership, so a
deputy with no weight->=2 tie still sits exactly where she belongs, and the
weight-1 mass is *implied by the lobes* rather than drawn as thousands of
redundant chords. Drawing them added ink, not information: everyone sharing a
lobe shares a committee by construction.

**Node colour is capped at three classes.** Node colour in a node-link diagram is
an all-pairs form — any two nodes can end up adjacent on screen — and the
validated palette clears the separation floors for three slots under that
condition, not eight. So the two largest blocs get a hue each and everything else
is one "Other" class. Bloc identity beyond that belongs in the companion CSV.

Because colour is bloc and position is committee, the figure answers a question
directly: do committee assignments follow bloc lines? The subtitle carries the
measured answer — attribute assortativity by bloc, which runs slightly *negative*
in all three chambers — so the claim is a number rather than an impression.
"""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

MIN_WEIGHT = 2
TOP_BLOCS = 2

# Radius for a deputy sitting on k committees. One committee puts her on the rim;
# each further committee pulls her in, so depth reads as "bridges more". Set out
# as an explicit table rather than a formula: 1/k**0.8 crushed the k=2 and k=3
# bands — where most of the chamber sits — into a thin annulus, and the whole
# picture jammed there. These steps give the crowded bands the most room.
_RADIUS = {1: 1.00, 2: 0.76, 3: 0.54, 4: 0.36, 5: 0.22, 6: 0.12}


def _radius(k: int) -> float:
    return _RADIUS.get(max(k, 1), 0.08)


def _seriate(order: list[str], shared: dict[tuple[str, str], int]) -> list[str]:
    """Order committees so that ones sharing members sit near each other.

    Without this the rim order is arbitrary, and a deputy on two committees that
    happen to land on opposite sides is placed on their bisector — a direction
    that means nothing — with her ties drawn straight across the middle. Ordering
    by the Fiedler vector of the committee-overlap Laplacian puts committees that
    share members next to each other, so most bridging is local and the chords
    stop piling through the centre.

    Falls back to the given order if the overlap graph is degenerate.
    """
    import numpy as np

    n = len(order)
    if n < 3:
        return order
    index = {c: i for i, c in enumerate(order)}
    weights = np.zeros((n, n))
    for (a, b), count in shared.items():
        if a in index and b in index:
            weights[index[a], index[b]] = count
            weights[index[b], index[a]] = count
    laplacian = np.diag(weights.sum(axis=1)) - weights
    try:
        values, vectors = np.linalg.eigh(laplacian)
    except np.linalg.LinAlgError:
        return order
    positive = [i for i, v in enumerate(values) if v > 1e-9]
    if not positive:
        return order
    fiedler = vectors[:, positive[0]]
    return [order[i] for i in sorted(range(n), key=lambda i: fiedler[i])]


def _draw_bundled(ax, pos, edges, max_w: float, beta: float = 0.26) -> None:
    """Draw ties as quadratic Béziers pulled toward the centre.

    The standard decluttering move for a radial layout. A straight chord between
    two lobes is a secant, and a few hundred secants cross everything and pile
    into a knot at the middle; bowing them all the same way just adds a false
    swirl. Pulling each edge's control point toward the centre by ``beta``
    instead means ties between neighbouring lobes stay short and local, while
    long ties dive inward and *overlap each other* — so they read as a few
    bundles rather than a uniform mesh, and the bundles are themselves the
    signal about which parts of the chamber bridge to which.

    This is the cheap approximation of hierarchical edge bundling: one control
    point, no hierarchy, no iteration.
    """
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    for u, v, data in edges:
        (x0, y0), (x1, y1) = pos[u], pos[v]
        share = data["weight"] / max_w
        control = ((x0 + x1) / 2 * beta, (y0 + y1) / 2 * beta)
        ax.add_patch(PathPatch(
            MPath([(x0, y0), control, (x1, y1)],
                  [MPath.MOVETO, MPath.CURVE3, MPath.CURVE3]),
            facecolor="none", edgecolor=(0.0, 0.0, 0.0, 0.035 + 0.22 * share),
            linewidth=0.35 + 1.1 * share, zorder=1,
        ))


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


def _committees(assembly_id: str) -> tuple[dict[str, dict], dict[str, set[str]]]:
    """Return (committee rows by id, person_id -> set of committee_ids)."""
    rows = {c["committee_id"]: c for c in S.load("committees")
            if c["assembly_id"] == assembly_id}
    portfolio: dict[str, set[str]] = defaultdict(set)
    for r in S.load("bipartite_person_committee"):
        if r["assembly_id"] != assembly_id or r["committee_id"] not in rows:
            continue
        portfolio[r["person_id"]].add(r["committee_id"])
    return rows, portfolio


def _anchor_label(row: dict, ordinal: int) -> str:
    """Short ASCII label for a committee anchor.

    Only the 2023 chamber publishes Latin committee names. Where there is none,
    the anchor is labelled by the committee's type and an ordinal — Arabic cannot
    be drawn (see ``_style.label``) and inventing a translation would be worse
    than an honest key. The committee_id and Arabic name are in the companion CSV.
    """
    if row.get("name_lat", "").strip() or row.get("name_en", "").strip():
        return LBL.committee_short(row["name_ar"], row.get("name_lat", ""),
                                   row.get("name_en", ""), limit=24)
    return f"{(row.get('type') or 'committee').replace('_', ' ').title()} {ordinal}"


def _layout(portfolio: dict[str, set[str]],
            order: list[str]) -> tuple[dict[str, tuple[float, float]],
                                       dict[str, tuple[float, float]]]:
    """Positions for deputies and for committee anchors.

    Committees are spaced evenly around a circle. A deputy is placed in the mean
    direction of her committees, at a radius set by how many she sits on, and
    deputies sharing an identical portfolio are packed into a small disc around
    that point rather than stacked on it.
    """
    n = len(order)
    anchors = {
        cid: (math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n))
        for i, cid in enumerate(order)
    }

    groups: dict[frozenset[str], list[str]] = defaultdict(list)
    for person, committees in portfolio.items():
        groups[frozenset(committees)].append(person)

    pos: dict[str, tuple[float, float]] = {}
    for key, members in groups.items():
        vectors = [anchors[c] for c in key if c in anchors]
        if not vectors:
            continue
        mx = sum(v[0] for v in vectors) / len(vectors)
        my = sum(v[1] for v in vectors) / len(vectors)
        norm = math.hypot(mx, my)
        if norm < 1e-9:
            # Committees cancel out — she bridges opposite sides of the rim, so
            # the centre is the honest place for her. Nudge along the first
            # committee's direction to keep such groups from stacking.
            first = anchors[sorted(key)[0]]
            mx, my, norm = first[0], first[1], 1.0
            base_r = 0.08
        else:
            base_r = _radius(len(key))
        ux, uy = mx / norm, my / norm

        # Phyllotaxis inside the group's disc: even packing, no randomness.
        spread = 0.055 * math.sqrt(len(members))
        for j, person in enumerate(sorted(members)):
            if len(members) == 1:
                dx = dy = 0.0
            else:
                t = (j + 0.5) / len(members)
                angle = j * 2.399963229728653  # golden angle
                radius = spread * math.sqrt(t)
                dx, dy = radius * math.cos(angle), radius * math.sin(angle)
            pos[person] = (ux * base_r + dx, uy * base_r + dy)
    return pos, anchors


def build_graph(assembly_id: str, min_weight: int = MIN_WEIGHT) -> tuple[nx.Graph, nx.Graph]:
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
        if d["weight"] >= min_weight:
            backbone.add_edge(u, v, **d)
    return full, backbone


class Frame:
    """The committee-anchored coordinate system for one chamber.

    Held as one object because the bipartite figure draws the same deputies in
    the same places as the one-mode figure for that chamber: sharing the frame is
    what makes the two directly comparable, so the pair differs only in which
    ties are drawn, never in where anyone sits.
    """

    def __init__(self, assembly_id: str) -> None:
        self.assembly_id = assembly_id
        self.rows, self.portfolio = _committees(assembly_id)

        sizes_by_committee: Counter = Counter()
        shared: Counter = Counter()
        for committees in self.portfolio.values():
            mine = sorted(committees)
            for c in mine:
                sizes_by_committee[c] += 1
            for i, a in enumerate(mine):
                for b in mine[i + 1:]:
                    shared[(a, b)] += 1
        self.seats = sizes_by_committee

        # Ordinals come from the stable type/size order, so a committee's key
        # ("Legislative 3") does not move when the seriation reorders the rim.
        stable = sorted(
            self.rows,
            key=lambda c: (self.rows[c].get("type") or "", -sizes_by_committee[c], c),
        )
        self.ordinal = {}
        seen: Counter = Counter()
        for cid in stable:
            kind = self.rows[cid].get("type") or "committee"
            seen[kind] += 1
            self.ordinal[cid] = seen[kind]

        self.order = _seriate(stable, shared)
        self.pos, self.anchors = _layout(self.portfolio, self.order)

    @property
    def unnamed(self) -> bool:
        """True when no committee in this chamber has a renderable name."""
        return not any(self.rows[c].get("name_lat", "").strip()
                       or self.rows[c].get("name_en", "").strip() for c in self.order)

    def label(self, cid: str) -> str:
        return _anchor_label(self.rows[cid], self.ordinal[cid])

    def require(self, nodes) -> None:
        missing = [n for n in nodes if n not in self.pos]
        if missing:
            raise SystemExit(
                f"{len(missing)} deputies in the {self.assembly_id} edge list have "
                f"no committee rows to position them by, e.g. {missing[:3]}"
            )

    def draw_rim(self, ax) -> None:
        """Anchor ticks and rotated rim labels."""
        for cid in self.order:
            x, y = self.anchors[cid]
            ax.plot([x * 1.01, x * 1.07], [y * 1.01, y * 1.07],
                    color=S.CHROME["axis"], linewidth=0.8, zorder=0)
            angle = math.degrees(math.atan2(y, x))
            ha = "left" if -90 <= angle <= 90 else "right"
            ax.annotate(
                S.label(self.label(cid)), xy=(x * 1.10, y * 1.10),
                ha=ha, va="center", fontsize=6.4,
                rotation=angle if ha == "left" else angle + 180,
                rotation_mode="anchor", color=S.CHROME["text_secondary"], zorder=6,
            )

    def set_limits(self, ax) -> None:
        # Generous limits: the rim labels are drawn outside the anchor circle and
        # radiate outward, so a tight frame runs them into the subtitle at the
        # top and the legend at the bottom.
        ax.set_xlim(-1.62, 1.62)
        ax.set_ylim(-1.76, 1.86)
        ax.set_aspect("equal")
        ax.set_axis_off()


def draw(assembly_id: str, slug: str, title: str, note: str = "",
         min_weight: int = MIN_WEIGHT) -> None:
    """Draw one chamber's committee co-membership network.

    ``min_weight`` is the threshold above which a tie is *drawn*; every tie is
    still counted in the density and assortativity the subtitle reports. The
    default suits chambers whose projection has a few thousand ties. A chamber
    dense enough that the default fills the centre with solid ink needs a higher
    one — an unreadable drawing is not a more honest drawing, and the caption
    says which threshold produced it either way.
    """
    full, backbone = build_graph(assembly_id, min_weight)
    if full.number_of_nodes() == 0:
        raise SystemExit(f"no committee co-membership edges for {assembly_id}")

    persons = {p["person_id"]: p for p in S.load("persons")}
    bloc_of = _bloc_of(assembly_id)
    frame = Frame(assembly_id)
    portfolio, order, pos = frame.portfolio, frame.order, frame.pos
    frame.require(full.nodes())

    sizes = Counter(bloc_of.get(n, "No bloc") for n in full.nodes())
    top = [b for b, _ in sizes.most_common(TOP_BLOCS)]
    palette = S.categorical(len(top) + 1, all_pairs=True)
    colour_for = {b: palette[i] for i, b in enumerate(top)}
    other_colour = palette[-1]

    def node_colour(n: str) -> str:
        return colour_for.get(bloc_of.get(n, "No bloc"), other_colour)

    degree = dict(full.degree())
    max_degree = max(degree.values()) or 1

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 8.2))

    # A short tick outside each lobe marks the anchor's axis. Full spokes to the
    # centre were tried and dropped: twenty-two lines crossing the node mass is
    # more chrome than the labels need.
    frame.draw_rim(ax)

    # Only the strong ties. The weight-1 mass is what the lobes already say.
    strong = [(u, v, d) for u, v, d in full.edges(data=True)
              if d["weight"] >= min_weight]
    max_w = max((d["weight"] for _, _, d in strong), default=1)
    _draw_bundled(ax, pos, strong, max_w)
    nx.draw_networkx_nodes(
        full, pos, ax=ax,
        node_size=[20 + 150 * (degree[n] / max_degree) for n in full.nodes()],
        node_color=[node_colour(n) for n in full.nodes()],
        linewidths=0.9, edgecolors=S.CHROME["surface"],  # surface ring, not a border
    )

    # Label the deputies sitting on the most committees — in this layout those
    # are the ones nearest the centre, and they are the substantive subject.
    placed: list[tuple[float, float]] = []
    ranked = sorted(full.nodes(),
                    key=lambda x: (-len(portfolio.get(x, ())), -degree[x], x))
    for n in ranked:
        if len(placed) >= 5:
            break
        x, y = pos[n]
        # Anisotropic: a name is wide and short, so two labels collide at a
        # horizontal separation an isotropic radius would call clear.
        if any(abs(x - px) < 0.55 and abs(y - py) < 0.24 for px, py in placed):
            continue
        placed.append((x, y))
        name = LBL.person_name(persons.get(n, {}).get("name_lat", "")) or n
        ax.annotate(
            S.label(f"{name} ({len(portfolio.get(n, ()))})"),
            xy=(x, y), xytext=(0, 10), textcoords="offset points",
            ha="center", fontsize=7.0, color=S.CHROME["text_primary"], zorder=7,
            bbox=dict(boxstyle="round,pad=0.18", facecolor=S.CHROME["surface"],
                      edgecolor="none", alpha=0.85),
        )

    frame.set_limits(ax)

    nx.set_node_attributes(full, {n: bloc_of.get(n, "No bloc") for n in full}, "bloc")
    try:
        assortativity = nx.attribute_assortativity_coefficient(full, "bloc")
    except (ZeroDivisionError, ValueError):  # degenerate: one bloc only
        assortativity = float("nan")
    bridging = sum(1 for n in full.nodes() if len(portfolio.get(n, ())) > 1)
    density = nx.density(full)
    # Say so when the rim keys are placeholders rather than names, and where the
    # reader can resolve them — otherwise "Standing 7" is a dead end.
    naming = ("\nThis chamber's committee names exist only in Arabic, which cannot be "
              "rendered here; the rim keys resolve to names in the CSV."
              if frame.unnamed else "")

    S.titles(
        ax,
        title,
        f"{full.number_of_nodes()} deputies on {len(order)} committees. Position is "
        "computed, not simulated: angle = which committees, distance\nfrom the centre = "
        f"how many, so the {bridging} deputies who bridge committees sit inside the rim "
        "and identical portfolios sit\ntogether. The projection is exactly the union of "
        f"the committee cliques ({full.number_of_edges():,} ties, density {density:.2f}), "
        f"so only the\n{backbone.number_of_edges():,} ties of weight ≥ {min_weight} are "
        "drawn — the rest is what the lobes already say. Colour is bloc: assortativity "
        f"{assortativity:+.2f},\nso committee assignment does not track bloc. "
        + note + naming,
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
        loc="lower left", bbox_to_anchor=(-0.01, -0.005), ncol=3, fontsize=7.6,
    )
    S.source_note(
        fig, "ParliamentariansTN · data/networks/edges_committee_comembership.csv "
             "× bipartite_person_committee.csv")

    table = []
    for n in sorted(full.nodes(), key=lambda x: (-len(portfolio.get(x, ())), -degree[x])):
        mine = sorted(portfolio.get(n, ()))
        table.append({
            "person_id": n,
            "name_lat": persons.get(n, {}).get("name_lat", ""),
            "bloc": bloc_of.get(n, ""),
            "n_committees": len(mine),
            "committee_ids": " ".join(mine),
            # The rim keys are the only handle a reader has on a committee whose
            # name is Arabic-only and so cannot be drawn; without this column
            # "Standing 7" on the chart maps to nothing.
            "committee_labels": " | ".join(
                frame.label(c) for c in mine),
            "degree_full_graph": degree[n],
            "degree_backbone": backbone.degree(n),
            "weighted_degree_newman": round(
                sum(d["weight_newman"] for _, _, d in full.edges(n, data=True)), 4),
        })
    S.save(fig, slug, table)
