"""Figure 37 — Who agrees across bloc lines, and who does not.

Every member of the 2011 assembly by two quantities from the vote-agreement
graph: how many members they agree with at all (degree, horizontal) and what
share of those agreements reach outside their own bloc (vertical).

The chamber separates into two regimes, and they are not two wings. Ennahdha's
members cluster at high degree and *low* cross-bloc share: they agree with many
people, most of them each other. Members of the small blocs and the non-attached
sit at lower degree and cross-bloc shares near 1.0 — almost every agreement they
have is with someone from another bloc, which is what having nine colleagues
mechanically produces.

**So the vertical axis is not a measure of open-mindedness.** A member of a
ten-person bloc cannot have a low cross-bloc share; there are not enough
co-partisans to agree with. The dashed curve is what each member's share would
be if their agreements were distributed at random across the chamber, given
their own bloc's size. Distance below that curve is the interpretable quantity,
and it is almost entirely an Ennahdha phenomenon.

The members worth looking at individually are the ones sitting furthest from
their expectation in either direction: Ennahdha members with unusually outward
agreement, and small-bloc members with unusually inward. Six are labelled, drawn
only from members with at least fifteen agreements — below that a single tie
swings the share to 0% or 100% and the residual is noise dressed as an outlier.
The companion CSV ranks every member.

A tie is agreement on at least 75% of the contested divisions both cast; bloc is
the member's last recorded spell; and everything inherits figure 34's caveat that
an agreement tie is a correlation between voting records, not an act of
cooperation. A member is not choosing these ties.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

LABEL_EXTREMES = 3
# Below this, the share is degenerate: one tie makes it 0% or 100%, and the
# residual against a smooth expectation is noise dressed as an outlier.
MIN_DEGREE_FOR_LABEL = 15


def main() -> None:
    dyads = POL.agreement_dyads()
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")
    bloc = POL.blocs()
    people = sorted({p for d in dyads for p in d[:2]})
    sizes = collections.Counter(bloc.get(p, "No bloc") for p in people)

    neighbours: dict[str, list[str]] = collections.defaultdict(list)
    for a, b, *_ in POL.ties(dyads):
        neighbours[a].append(b)
        neighbours[b].append(a)

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for person in people:
        own = bloc.get(person, "No bloc")
        nb = neighbours.get(person, [])
        if not nb:
            continue
        cross = sum(1 for n in nb if bloc.get(n, "No bloc") != own)
        # If agreements fell at random across the chamber, this is the share
        # that would leave the bloc — it depends only on the bloc's size.
        expected = (len(people) - sizes[own]) / (len(people) - 1)
        rows.append({
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": own,
            "degree": len(nb),
            "cross_bloc_share": cross / len(nb),
            "expected_share": expected,
            "residual": cross / len(nb) - expected,
        })

    top = [b for b, _ in sizes.most_common(2)]
    palette = S.categorical(3, all_pairs=True)
    colour = {b: palette[i] for i, b in enumerate(top)}
    other = palette[-1]

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 5.6))
    for group, marks in ((None, [r for r in rows if r["bloc"] not in top]),
                         *[(b, [r for r in rows if r["bloc"] == b]) for b in top]):
        if not marks:
            continue
        ax.scatter([m["degree"] for m in marks], [m["cross_bloc_share"] for m in marks],
                   s=40, c=colour.get(group, other), alpha=0.85, linewidths=0.7,
                   edgecolors=S.CHROME["surface"], zorder=3)

    # The random-agreement expectation. Several blocs are close enough in size
    # that their levels coincide to the pixel, so identical levels are drawn once.
    span = max(r["degree"] for r in rows) * 1.02
    for level in sorted({round((len(people) - sizes[r["bloc"]]) / (len(people) - 1), 3)
                         for r in rows}):
        ax.plot([0, span], [level, level], color=S.CHROME["axis"], linewidth=0.8,
                linestyle=(0, (5, 4)), alpha=0.75, zorder=2)

    labelled = [r for r in rows if r["degree"] >= MIN_DEGREE_FOR_LABEL]
    extremes = (sorted(labelled, key=lambda r: r["residual"])[:LABEL_EXTREMES]
                + sorted(labelled, key=lambda r: -r["residual"])[:LABEL_EXTREMES])
    # Staggered offsets: the extremes cluster, and a fixed offset stacks them.
    for k, mark in enumerate(extremes):
        name = LBL.person_name(mark["name_lat"]) or mark["person_id"]
        dy = 9 if k % 2 == 0 else -13
        ax.annotate(S.label(name), xy=(mark["degree"], mark["cross_bloc_share"]),
                    xytext=(7, dy), textcoords="offset points", fontsize=7.4,
                    color=S.CHROME["text_secondary"], zorder=5)

    ax.set_ylim(-0.03, 1.06)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    S.frame(ax, x_grid=True)
    S.titles(
        ax,
        "Ennahdha members agree widely and inwardly; everyone else agrees outwardly",
        "Each member of the 2011 Constituent Assembly by how many others they "
        f"agree with on at least {POL.TIE_THRESHOLD:.0%} of the contested "
        "divisions both cast, and what\nshare of those agreements leave their own "
        "bloc. The dashed lines are what each bloc's members would show if "
        "agreements fell at random across the\nchamber, which depends only on "
        "bloc size — so the vertical axis is not open-mindedness, and a "
        "ten-member bloc cannot score low on it. Distance below\nthe relevant "
        "dashed line is the interpretable quantity, and it is almost entirely an "
        f"Ennahdha phenomenon. The {len(extremes)} members furthest from their own\n"
        f"expectation in either direction are named, among members with at least "
        f"{MIN_DEGREE_FOR_LABEL} agreements — below that a single tie swings the "
        "share to 0% or\n100% and the residual is noise. The CSV ranks every "
        "member.",
        xlabel="Members agreed with (degree)",
        ylabel="Share of agreements outside the member's bloc",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=colour[b], label=S.label(f"{b} ({sizes[b]})"))
            for b in top
        ] + [
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=7,
                          color=other, label=S.label("Other blocs")),
            mlines.Line2D([], [], color=S.CHROME["axis"], linewidth=1.2,
                          linestyle=(0, (5, 4)),
                          label=S.label("Expected under random agreement")),
        ],
        loc="lower left", fontsize=8.2,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/edges_vote_agreement.csv")

    S.save(fig, "fig37_cross_bloc_brokers_nca2011", [
        {**r,
         "cross_bloc_share": round(r["cross_bloc_share"], 4),
         "expected_share": round(r["expected_share"], 4),
         "residual": round(r["residual"], 4)}
        for r in sorted(rows, key=lambda r: r["residual"])
    ])


if __name__ == "__main__":
    main()
