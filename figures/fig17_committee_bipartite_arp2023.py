"""Figure 17 — Deputies and committees as a bipartite network, 2023 chamber.

The one-mode projection in figure 16 is dense because projection *creates*
density: put twenty people on a committee and you have created 190 ties. This
figure shows the structure that projection starts from — an edge wherever a
deputy sits on a committee — which is sparse, countable, and closer to the
underlying fact. 247 memberships stand behind 1,579 projected dyads.

**It uses figure 16's exact coordinates.** Same deputies, same committee anchors,
same positions; only the ties differ. That is the point of the pair: whatever
looks like structure in figure 16 can be checked here against the memberships it
was manufactured from, with nothing moved in between. Anyone whose argument
depends on tie strength should build their own projection from this incidence
structure rather than inherit someone else's weighting.

Drawing the memberships rather than the dyads is also what makes a deputy's
position legible: her spokes fan out to each committee she sits on, so the rule
behind the layout — angle is which committees, depth is how many — is visible
rather than asserted.

The 2023 chamber is used because it is the only one whose committees carry
Latin-script names in the data, so the anchors can be labelled without inventing
translations.

An earlier version laid this out with a spring simulation, which put the
committees wherever the physics landed and made the comparison with figure 16
impossible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2023"


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    frame = NET.Frame(ASSEMBLY)
    if not frame.order:
        raise SystemExit(f"no committee data for {ASSEMBLY}")

    roles = {}
    for r in S.load("bipartite_person_committee"):
        if r["assembly_id"] == ASSEMBLY and r["committee_id"] in frame.rows:
            roles.setdefault((r["person_id"], r["committee_id"]), set()).add(r["role"])

    people = sorted(frame.portfolio)
    memberships = sorted(
        (p, c) for p in people for c in frame.portfolio[p] if c in frame.anchors
    )

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 8.2))
    blue, orange = S.categorical(2, all_pairs=True)

    frame.draw_rim(ax)
    for person, cid in memberships:
        (x0, y0), (x1, y1) = frame.pos[person], frame.anchors[cid]
        ax.plot([x0, x1], [y0, y1], color=S.CHROME["axis"], linewidth=0.45,
                alpha=0.55, zorder=1, solid_capstyle="round")

    ax.scatter(
        [frame.pos[p][0] for p in people], [frame.pos[p][1] for p in people],
        s=[16 + 22 * len(frame.portfolio[p]) for p in people],
        c=blue, linewidths=0.8, edgecolors=S.CHROME["surface"], zorder=3,
    )
    ax.scatter(
        [frame.anchors[c][0] for c in frame.order],
        [frame.anchors[c][1] for c in frame.order],
        s=[26 + 5.5 * frame.seats[c] for c in frame.order], marker="s",
        c=orange, linewidths=1.0, edgecolors=S.CHROME["surface"], zorder=4,
    )

    frame.set_limits(ax)
    multi = sum(1 for p in people if len(frame.portfolio[p]) > 1)
    S.titles(
        ax,
        "Deputies and committees, chamber elected in 2023",
        f"{len(people)} deputies, {len(frame.order)} committees, {len(memberships)} "
        "memberships — the incidence structure figure 16's 1,579 ties are\nprojected from. "
        "Identical coordinates to figure 16, so the two differ only in which ties are "
        f"drawn. {multi} deputies\nsit on more than one committee; their spokes are what "
        "makes the projection dense. Committee names are the\nchamber's own French "
        "labels, shortened, with the boilerplate prefix dropped.",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], marker="o", linestyle="none", markersize=6,
                          color=blue, label="Deputy (size = committees sat on)"),
            mlines.Line2D([], [], marker="s", linestyle="none", markersize=8,
                          color=orange, label="Committee (size = members)"),
        ],
        loc="lower left", bbox_to_anchor=(-0.01, -0.005), ncol=2, fontsize=7.6,
    )
    S.source_note(fig, "ParliamentariansTN · data/networks/bipartite_person_committee.csv")

    S.save(fig, "fig17_committee_bipartite_arp2023", [
        {
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "committee_id": cid,
            "committee": LBL.committee(frame.rows[cid]["name_ar"],
                                       frame.rows[cid]["name_lat"],
                                       frame.rows[cid]["name_en"], limit=70),
            "committee_label": frame.label(cid),
            "roles": " ".join(sorted(roles.get((person, cid), ()))),
        }
        for person, cid in memberships
    ])


if __name__ == "__main__":
    main()
