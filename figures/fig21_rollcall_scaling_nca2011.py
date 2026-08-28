"""Figure 21 — The voting space of the 2011 Constituent Assembly.

The chamber's 1,724 recorded divisions reduced to two dimensions, then faceted
one panel per bloc. The horizontal axis is the first principal component of the
voting record: the axis along which the chamber most disagreed with itself.

**What this is and is not.** It is a singular value decomposition of a member ×
division matrix with pour as +1, contre as −1 and everything else as 0. It is
*not* NOMINATE or an IRT model: there is no error model, no bootstrap, and no
claim that the axis is a latent ideal point. It is the standard first cut, and it
is reported as one. Anyone wanting ideal points with uncertainty should fit them
from `data/processed/vote_positions.csv`, which is why that table exists.

Two filters, both stated on the figure. Divisions where fewer than 40 members
cast a pour or contre are dropped, and so are near-unanimous ones — where the
smaller side is under 2.5% of those voting — because a division everyone agrees
on locates nobody. 993 of 1,724 survive.

Treating abstention and absence as 0 is a real assumption, not a neutral one: it
pulls members who abstain often toward the centre. The source also does not
distinguish being absent from being present and not voting, so that 0 is carrying
two different behaviours. The alternative — dropping those cells — would leave a
matrix too sparse to decompose, so the assumption is made explicitly here rather
than hidden.

Why facets rather than eight colours on one scatter: eight intermixed hues in a
single point cloud is exactly the case the palette rules refuse. Each panel
repeats the whole chamber in grey and lights up one bloc, so every bloc is read
against the same backdrop and the panel order — by bloc mean, right to left — is
itself the finding.

What it shows: the first dimension is not government versus opposition. It
separates Ennahdha (+10.2) from every other bloc, its own governing partners
included — CPR (−4.0) and Ettakatol (−3.2) shared the Troika with it and still
sit on the far side of zero, though nearer the centre than the Democratic Bloc
(−11.8). The gap from Ennahdha to the nearest other bloc is wider than the range
containing all seven of them. Set this against figures 14–16: committee
assignment in the same chamber does not track bloc at all, while voting does.
"""

from __future__ import annotations

import collections
import statistics
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
MIN_CAST = 40         # divisions with fewer recorded pour/contre are dropped
MIN_MINORITY = 0.025  # and so are near-unanimous ones
MIN_MEMBER_VOTES = 30
COLUMNS = 4


def scale() -> tuple[list[str], list[str], np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Return kept members, blocs, coordinates, votes cast, variance shares, n."""
    positions: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["assembly_id"] == ASSEMBLY:
            positions[row["person_id"]][row["vote_id"]] = row["position"]
    votes = [v["vote_id"] for v in S.load("votes") if v["assembly_id"] == ASSEMBLY]
    if not votes:
        raise SystemExit(f"no recorded divisions for {ASSEMBLY}")

    people = sorted(positions)
    index = {v: j for j, v in enumerate(votes)}
    matrix = np.zeros((len(people), len(votes)))
    for i, person in enumerate(people):
        for vote_id, position in positions[person].items():
            if position == "pour":
                matrix[i, index[vote_id]] = 1.0
            elif position == "contre":
                matrix[i, index[vote_id]] = -1.0

    cast = (matrix != 0).sum(axis=0)
    minority = np.minimum((matrix == 1).sum(axis=0), (matrix == -1).sum(axis=0))
    minority = minority / np.maximum(cast, 1)
    keep_votes = np.where((cast >= MIN_CAST) & (minority >= MIN_MINORITY))[0]
    reduced = matrix[:, keep_votes]

    keep_people = np.where((reduced != 0).sum(axis=1) >= MIN_MEMBER_VOTES)[0]
    reduced = reduced[keep_people]
    kept = [people[i] for i in keep_people]

    centred = reduced - reduced.mean(axis=0)
    u, s, _ = np.linalg.svd(centred, full_matrices=False)
    coords = u[:, :2] * s[:2]

    bloc_of = NET._bloc_of(ASSEMBLY)
    blocs = [bloc_of.get(p, "No bloc") for p in kept]
    # The sign of a singular vector is arbitrary; orient so the largest bloc
    # sits on the right, purely so the picture is stable across runs.
    counts = collections.Counter(blocs)
    largest = max(sorted(counts), key=lambda b: counts[b])
    if np.mean([coords[i, 0] for i, b in enumerate(blocs) if b == largest]) < 0:
        coords[:, 0] *= -1

    share = s ** 2 / (s ** 2).sum()
    return (kept, blocs, coords, (reduced != 0).sum(axis=1), share,
            len(keep_votes), len(votes))


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    kept, blocs, coords, cast_by_member, share, n_contested, n_votes = scale()

    members: dict[str, list[int]] = collections.defaultdict(list)
    for i, bloc in enumerate(blocs):
        members[bloc].append(i)
    means = {b: statistics.fmean(coords[idx, 0]) for b, idx in members.items()}
    order = sorted(members, key=lambda b: (-means[b], b))

    rows = -(-len(order) // COLUMNS)
    fig, axes = plt.subplots(rows, COLUMNS, sharex=True, sharey=True,
                             figsize=S.figsize(9.6, 2.7 * rows + 0.6))
    flat = list(np.ravel(axes))
    highlight = S.categorical(1)[0]

    for ax, bloc in zip(flat, order):
        idx = members[bloc]
        ax.scatter(coords[:, 0], coords[:, 1], s=9, c=S.CHROME["deemph"],
                   linewidths=0, zorder=2)
        ax.axvline(means[bloc], color=highlight, linewidth=1.4, alpha=0.85,
                   zorder=3)
        ax.scatter(coords[idx, 0], coords[idx, 1], s=26, c=highlight, alpha=0.9,
                   linewidths=0.5, edgecolors=S.CHROME["surface"], zorder=4)
        S.frame(ax, x_grid=True, y_grid=True)
        # Bloc names run to 25 characters and the panels are 2.2 inches wide, so
        # wrap rather than let one title run over its neighbour's.
        wrapped = textwrap.wrap(bloc, 24) or [bloc]
        ax.set_title(S.label("\n".join(wrapped)), loc="left", fontsize=9, pad=18)
        ax.annotate(
            f"{len(idx)} members · mean {means[bloc]:+.1f}".replace("-", "−"),
            xy=(0, 1), xycoords="axes fraction", xytext=(0, 4),
            textcoords="offset points", ha="left", va="bottom",
            fontsize=8, color=S.CHROME["text_secondary"],
        )
    for ax in flat[len(order):]:
        ax.set_visible(False)

    # Both sup-labels are placed after tight_layout: called before, they are
    # counted as furniture and the panels are inset a second time for them.
    fig.tight_layout(rect=(0.014, 0.05, 1, 0.755))
    fig.supxlabel(f"First dimension — the axis the chamber most divided on "
                  f"({share[0]:.0%} of variance)",
                  fontsize=9, color=S.CHROME["text_secondary"], y=0.034)
    fig.supylabel(f"Second dimension ({share[1]:.0%})",
                  fontsize=9, color=S.CHROME["text_secondary"], x=0.006)
    fig.text(0.014, 0.965, "Ennahdha on one side, every other bloc on the other",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.014, 0.925,
        f"{len(kept)} members of the 2011 Constituent Assembly positioned by "
        f"{n_contested} contested divisions of {n_votes:,} recorded, one panel per "
        "bloc, ordered by bloc mean.\nGrey is the whole chamber, repeated in every "
        "panel. The gap from Ennahdha to the nearest other bloc is wider than the "
        "range holding all seven of\nthem, and CPR and Ettakatol — its Troika "
        "coalition partners — sit on the far side of zero from it. Singular value "
        "decomposition of a pour/contre\nmatrix: a first cut, not an ideal-point "
        "model with uncertainty; fit those from vote_positions.csv. Abstention and "
        "absence both count as 0, which\npulls frequent abstainers toward the "
        "centre, and the source does not distinguish absence from not voting while "
        "present. Near-unanimous\ndivisions are dropped: they locate nobody.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/vote_positions.csv × votes.csv")

    S.save(fig, "fig21_rollcall_scaling_nca2011", [
        {
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": blocs[i],
            "bloc_mean_dim1": round(means[blocs[i]], 4),
            "dim1": round(float(coords[i, 0]), 4),
            "dim2": round(float(coords[i, 1]), 4),
            "votes_cast": int(cast_by_member[i]),
        }
        for i, person in enumerate(kept)
    ])


if __name__ == "__main__":
    main()
