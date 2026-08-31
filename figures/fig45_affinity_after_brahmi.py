"""Figure 45 — The affinity network after the shock: discipline decays, bridges do not.

The second of a matched pair. Figure 44 draws the 2011 Constituent Assembly's
voting affinity over its last 32 ordinary sitting days before Mohamed Brahmi was
assassinated. This draws **the same 196 members, in the same positions, at the
same threshold, over the same number of divisions**, across the first 32 sitting
days after the chamber resumed contested business. Anything that differs between
the two pictures is a difference in ties.

**The two standing accounts of what political violence does to a legislature
both fail here.** The *polarisation* account predicts that co-partisans close
ranks and cross-cutting ties are cut: within-bloc agreement up, cross-bloc down.
The *elite settlement* account predicts the reverse for the second term:
cross-bloc agreement up as the threat forces negotiation. What the record shows
is neither.

    mean agreement          before    after     later
    within bloc              0.930    0.879     0.873
    across blocs             0.672    0.679     0.658
    gap                      0.258    0.200     0.215

Within-bloc agreement falls by 0.05 and cross-bloc agreement does not move.
Blocs did not close ranks; they loosened, and the ground they lost was not
picked up by anybody else. The gap narrows because its top end came down, not
because its bottom came up.

**The strong ties tell the sharper version.** Pairs agreeing on at least 90% of
the divisions they both cast fall from 4,792 to 2,553 — nearly half the
chamber's reliable voting partnerships gone. The fall is not even: within-bloc
strong ties drop 41% (3,583 to 2,100) while cross-bloc strong ties drop **63%**
(1,209 to 453). So average cross-bloc agreement holding steady conceals the
collapse of its upper tail. A member could still expect to agree with someone
from another bloc about two-thirds of the time, and could no longer expect
anyone from another bloc to be a dependable ally.

**It is not a transient.** The next 32 sitting days, running to August 2014,
give 0.873 within and 0.658 across, with 2,542 strong ties of which only 363
cross a bloc. Whatever the crisis changed had not reverted a year later.

**What this pair cannot establish.** That the assassination *caused* any of it.
Between the two windows sit the National Dialogue, a change of government and
the drafting endgame of a constitution, and this design cannot separate them —
it is a before-and-after, not an identification strategy. The honest claim is
that the chamber on the far side of the crisis had measurably weaker voting
blocs and measurably fewer reliable cross-party partners, not that the killing
produced that.

Four of the 196 members sit outside the frame; both figures use the identical
box, so the comparison is unaffected. `_crisis.py` sets out the four controls
that make these two drawings comparable at all — one panel, one set of
coordinates, one threshold, one division count — and why matching on divisions
alone would have manufactured this figure's result.

A tie is a correlation between two voting records, not an act, and bloc is each
member's last recorded spell in a chamber where 105 of 217 changed party.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _crisis as C  # noqa: E402
import _style as S  # noqa: E402

WINDOW = "after"
SLUG = "fig45_affinity_after_brahmi"


def main() -> None:
    data = C.prepare()
    fig, ax = plt.subplots(figsize=S.figsize(9.4, 5.6))
    C.draw(ax, data, WINDOW)
    bloc = data["bloc"]

    stats = {}
    for name in ("before", "after", "after_later"):
        if name not in data["full"]:
            continue
        pairs = [p for p in data["panel"] if p in data["full"][name]]
        stats[name] = C.means(data["full"][name], pairs, bloc)
    graphs = {
        name: C.graph_of(data["scores"][name],
                         [p for p in data["panel"] if p in data["scores"][name]],
                         data["members"])
        for name in data["scores"]
    }
    ties = {name: C.tie_counts(g, bloc) for name, g in graphs.items()}
    days = len({data["dates"][v] for v in data["segments"][WINDOW]})

    before_w, before_c = stats["before"]
    after_w, after_c = stats["after"]
    bw, bc = ties["before"]
    aw, ac = ties["after"]

    S.titles(
        ax,
        "After the shock: blocs loosen, and reliable cross-bloc allies mostly vanish",
        f"Voting affinity in the 2011 Constituent Assembly over the {days} sitting "
        f"days after it resumed contested business, following the assassination\nof "
        f"Mohamed Brahmi on 25 July 2013. An edge joins two of the "
        f"{len(data['members'])} members who voted the same way on at least "
        f"{C.THRESHOLD:.0%} of the divisions both\ncast — same members, same "
        f"positions, same threshold and same division count as figure 44, which "
        f"draws the window before. Mean within-bloc\nagreement falls "
        f"{before_w:.3f} to {after_w:.3f} while cross-bloc agreement does not "
        f"move ({before_c:.3f} to {after_c:.3f}): blocs loosened rather than "
        f"closing ranks, which is what\nneither the polarisation account "
        f"(within up, cross down) nor the elite-settlement account (cross up) "
        f"predicts. Ties at the {C.THRESHOLD:.0%} threshold fall\nfrom "
        f"{bw + bc:,} to {aw + ac:,}, and unevenly — within-bloc down "
        f"{1 - aw / bw:.0%}, cross-bloc down {1 - ac / bc:.0%}. Steady average "
        "cross-bloc agreement hides the loss of its upper\ntail: a member could "
        "still expect to agree with someone from another bloc two thirds of the "
        "time, and could no longer expect any of them to be a\ndependable ally. "
        "The next 32 sitting days look the same, so this is not a transient — but "
        "the National Dialogue and a change of government sit in the\nsame gap, "
        "so read this as a before-and-after, not a cause.",
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for person in data["members"]:
        own = bloc.get(person, "No bloc")
        entry = {
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": own,
        }
        for name in graphs:
            neighbours = list(graphs[name].neighbors(person))
            entry[f"strong_ties_{name}"] = len(neighbours)
            entry[f"strong_ties_cross_{name}"] = sum(
                1 for n in neighbours if bloc.get(n, "No bloc") != own)
        rows.append(entry)
    for name, (within, cross) in ties.items():
        rows.append({
            "person_id": f"[window: {name}]",
            "name_lat": f"{len(data['segments'][name])} contested divisions, "
                        f"{len(data['drawn'][name])} drawn",
            "bloc": f"mean within {stats[name][0]:.4f} / cross {stats[name][1]:.4f}",
            **{f"strong_ties_{k}": (within if k == name else "") for k in graphs},
            **{f"strong_ties_cross_{k}": (cross if k == name else "") for k in graphs},
        })
    S.save(fig, SLUG, rows)


if __name__ == "__main__":
    main()
