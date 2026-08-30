"""Figure 44 — The affinity network before the shock: a chamber run by blocs.

The first of a matched pair. This is the 2011 Constituent Assembly's voting
affinity network over the 94 contested divisions it held on 32 sitting days
between July 2012 and 17 July 2013 — the last ordinary business before Mohamed
Brahmi was assassinated on 25 July. Figure 45 draws the same 196 members, in the
same positions, at the same threshold, over the same number of divisions, after
the crisis.

**The theoretical question this panel sets up.** A shock of this kind is usually
argued to do one of two things to a legislature. The *polarisation* account says
it hardens group boundaries: co-partisans close ranks and cross-cutting ties are
cut, so within-bloc agreement rises and cross-bloc agreement falls. The *elite
settlement* account says the opposite: the threat to the transition forces
negotiation, and cross-cutting agreement rises. Both are claims about a
**change**, and neither can be assessed without the level they change from.
That is what this figure is: the baseline, not a finding.

**What the baseline looks like.** Bloc predicts voting almost deterministically
inside blocs and weakly across them. Mean agreement between two members of the
same bloc is **0.930**; between members of different blocs, **0.672** — a gap of
0.258. Of the 4,792 ties drawn here (pairs agreeing on at least 90% of the
contested divisions they both cast), 3,583 are within-bloc and 1,209 cross it.
This is a chamber with disciplined blocs that nonetheless sustains a substantial
number of reliable cross-bloc partnerships.

**Why the window is 32 sitting days and not 94 divisions.** Both, in fact: the
comparison window in figure 45 is matched on days first and then subsampled to
the same division count. Matching on divisions alone would set this year of
ordinary business against the four days in December 2013 that produced the next
94 contested divisions — 78 of them in a single sitting. Matching on days alone
would leave figure 45 estimating its agreement rates from 417 divisions against
this one's 94, and a rate estimated from more evidence is less likely to clear a
threshold by chance, which would manufacture exactly the thinning that figure 45
reports. `_crisis.py` sets both controls out in full.

**The panel is nearly the whole chamber, which figure 43's was not.** 196 of 217
members appear here, including 16 of the 18 Democratic Bloc members whose
withdrawal figure 43 documents. Day-matching is what buys that: 32 sitting days
after the crisis contain 417 contested divisions, enough for even a
low-participation member to clear the scoring floor. Figure 43's
division-matched panel was 90% Ennahdha and 6% Democratic Bloc and could not
support this comparison; this one can.

Colour is capped at three classes as everywhere in this set. Edges are split by
kind — cross-bloc ties in the accent, within-bloc in the neutral — because the
count that moves between the two figures is the cross-bloc one. Both are drawn
at the same width and near the same opacity: an earlier draft gave the
cross-bloc ties twice the width and five times the opacity, which made a quarter
of the edges look like most of the ink.

Four of the 196 members sit outside the frame. Letting them set the axis limits
squashed the other 192 into a band, so the box is the 1st-to-99th percentile of
the coordinates; figure 45 uses the identical box, so the comparison is
unaffected.

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

WINDOW = "before"
SLUG = "fig44_affinity_before_brahmi"


def main() -> None:
    data = C.prepare()
    fig, ax = plt.subplots(figsize=S.figsize(9.4, 5.6))
    graph = C.draw(ax, data, WINDOW)
    bloc = data["bloc"]
    pairs = [p for p in data["panel"] if p in data["full"][WINDOW]]
    within_mean, cross_mean = C.means(data["full"][WINDOW], pairs, bloc)
    within_ties, cross_ties = C.tie_counts(graph, bloc)
    days = len({data["dates"][v] for v in data["segments"][WINDOW]})

    S.titles(
        ax,
        "Before the shock: disciplined blocs, and cross-bloc allies in numbers",
        f"Voting affinity in the 2011 Constituent Assembly over the "
        f"{len(data['segments'][WINDOW])} contested divisions of its last "
        f"{days} ordinary sitting days before\nMohamed Brahmi was assassinated on "
        f"25 July 2013. An edge joins two of the {len(data['members'])} members "
        f"who voted the same way on at least {C.THRESHOLD:.0%} of the divisions "
        f"both cast:\n{graph.number_of_edges():,} such ties, {within_ties:,} inside "
        f"a bloc and {cross_ties:,} across one. Mean agreement is "
        f"{within_mean:.3f} within a bloc against {cross_mean:.3f} across, a gap "
        f"of {within_mean - cross_mean:.3f}.\nThis panel is a baseline rather than "
        "a finding: the polarisation account of political violence predicts the "
        "within figure rises and the cross figure falls\nafter the shock, the "
        "elite-settlement account predicts the cross figure rises, and neither "
        "can be read without the level it moves from. Figure 45\ndraws the same "
        "members in the same positions at the same threshold over the same number "
        "of divisions, after.",
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")

    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for person in data["members"]:
        neighbours = list(graph.neighbors(person))
        own = bloc.get(person, "No bloc")
        rows.append({
            "person_id": person,
            "name_lat": persons.get(person, {}).get("name_lat", ""),
            "bloc": own,
            "window": WINDOW,
            "strong_ties": len(neighbours),
            "strong_ties_cross_bloc": sum(
                1 for n in neighbours if bloc.get(n, "No bloc") != own),
        })
    S.save(fig, SLUG, rows)


if __name__ == "__main__":
    main()
