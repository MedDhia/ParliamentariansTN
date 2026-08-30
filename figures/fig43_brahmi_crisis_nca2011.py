"""Figure 43 — What the Brahmi assassination did to the chamber's voting.

Mohamed Brahmi, an opposition member of the Constituent Assembly, was
assassinated on 25 July 2013. This asks what the roll-call record shows either
side of that date, and the answer has three parts, only one of which is about
affinity.

**The crisis is unmistakable in participation, and it is precisely structured.**
In the four months after the assassination the Democratic Bloc's turnout fell
from 51% to 21% and the Democratic Alliance's from 50% to 26%, while Ennahdha
went from 79% to 80% and CPR from 57% to 58%. The blocs that stopped voting
stopped nearly completely; the chamber's two largest parties did not move at all.
By December **seven of the eight are back at or above where they started** — the
exception is Loyalty to the Revolution, which went 50% to 40% in the crisis and
recovers only to 43%, the one bloc whose participation the episode appears to
have dented for good. That is a withdrawal and, for almost everyone, a return.

**During the crisis there is no comparable estimate, and the reason is not
simply that the numbers are small.** The chamber divided 35 times on contested
business between 25 July and 30 November. A gap could be computed from that:
4,259 pairs of the 23,436 possible — 18% — clear the 20-division floor this
figure uses. The problem is which pairs survive. **Zero of the eighteen
Democratic Bloc members appear in a single scoreable pair**, along with one of
ten from the Democratic Alliance and two of ten from Loyalty to the Revolution,
while 75 of 87 Ennahdha members do; 52% of the surviving pairs are Ennahdha with
Ennahdha. A within-versus-cross-bloc gap computed on that sample would not be a
measurement of the chamber, it would be a measurement of the governing side's
internal cohesion wearing the chamber's name. So panel C leaves the slot empty.

**Across the crisis, no change in affinity is detectable.** On 94 contested
divisions before and 94 immediately after, the gap between within-bloc and
cross-bloc agreement goes from +0.21 to +0.18 — and the intervals overlap.

**That last result rests on a resampling choice, and the choice reverses it.**
Bootstrapping over *pairs* gives intervals of about ±0.01 and makes the change
look real. But pairs are not independent: every member appears in over a hundred
of them, so one member behaving differently moves many pairs at once. Resampling
*members* instead — the cluster bootstrap, which respects that dependence —
widens the intervals to ±0.05 and ±0.09, and they overlap comfortably. The
narrowing is not distinguishable from noise. The pair-level version of this
figure said otherwise and was wrong.

**And the comparison can only ask the members the crisis did not silence.**
Scoring a pair in every window needs both members voting in all of them, which
127 of 217 manage. That panel is 90% of Ennahdha and **6%** of the Democratic
Bloc — one of its eighteen members. The blocs that withdrew are almost absent
from the only group whose affinity is measurable throughout, so "affinity did
not change" is close to a statement about the people who kept turning up. This
is the figure's real limit, and no amount of resampling repairs it: the
comparison is only available for a sample selected on the very behaviour the
crisis changed.

**A claim this figure does not make.** The 38-day silence after the assassination
is conspicuous but not unprecedented: two longer gaps sit in this record, 107
days in 2012 and 75 over the winter of 2012–13, both ordinary recesses. What is
unusual is how thin the months either side of it are: August 2013 produced a
single contested division, the fewest of any month in which this chamber divided
at all, and September two — which only ties July 2012 rather than beating it.

Bloc is each member's last recorded spell — the source publishes no dated bloc
history for this chamber — so a member who moved is labelled here by where they
ended up, which matters more for a before-and-after question than for any other
in this set.
"""

from __future__ import annotations

import collections
import random
import statistics
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSASSINATION = "2013-07-25"
# The crisis window closes at the end of November: the assembly's output returns
# to its earlier rate in October and November, and December begins the
# constitutional endgame, which is a different agenda rather than a different
# political temperature.
CRISIS_END = "2013-12-01"
MIN_CAST, MIN_MINORITY = 40, 0.025
# Lower than the 30 the network layer uses. 30 leaves the pre-crisis window with
# too few scored pairs to compare; 20 is the loosest floor that still refuses to
# score a pair on a handful of votes, and it is applied identically to every
# window so no window is advantaged by it.
FLOOR = 20
BOOTSTRAP = 400
SEED = 20260830


def load():
    dates = {r["vote_id"]: r["vote_date"] for r in S.load("votes")
             if r["assembly_id"] == POL.ASSEMBLY}
    positions: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1
    return dates, positions


def window(date: str) -> str:
    if date < ASSASSINATION:
        return "before"
    if date < CRISIS_END:
        return "crisis"
    return "after"


def contested(dates, positions, people) -> list[str]:
    """The same filter the vote-agreement layer uses, applied per division."""
    keep = []
    for vote_id in dates:
        yes = sum(1 for p in people if positions[p].get(vote_id) == 1)
        no = sum(1 for p in people if positions[p].get(vote_id) == -1)
        if yes + no >= MIN_CAST and min(yes, no) / (yes + no) >= MIN_MINORITY:
            keep.append(vote_id)
    return keep


def agreement(positions, people, vote_ids) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for i, a in enumerate(people):
        pa = positions[a]
        for b in people[i + 1:]:
            pb = positions[b]
            shared = agreed = 0
            for vote_id in vote_ids:
                va, vb = pa.get(vote_id), pb.get(vote_id)
                if va and vb:
                    shared += 1
                    agreed += va == vb
            if shared >= FLOOR:
                out[(a, b)] = agreed / shared
    return out


def gap(scores, pairs, bloc) -> float:
    within = [scores[k] for k in pairs
              if bloc.get(k[0], "No bloc") == bloc.get(k[1], "No bloc")]
    cross = [scores[k] for k in pairs
             if bloc.get(k[0], "No bloc") != bloc.get(k[1], "No bloc")]
    if not within or not cross:
        return float("nan")
    return statistics.fmean(within) - statistics.fmean(cross)


def cluster_interval(scores, panel, members, bloc, rng) -> tuple[float, float]:
    """95% interval, resampling MEMBERS rather than pairs.

    Every member sits in more than a hundred pairs, so pair-level resampling
    treats one person's behaviour as a hundred independent observations and
    returns an interval several times too narrow. Resampling members and taking
    the pairs they induce keeps the dependence intact.
    """
    values = []
    for _ in range(BOOTSTRAP):
        counts = collections.Counter(
            members[rng.randrange(len(members))] for _ in range(len(members)))
        sample = []
        for pair in panel:
            multiplicity = counts[pair[0]] * counts[pair[1]]
            if multiplicity:
                sample.extend([pair] * multiplicity)
        if sample:
            values.append(gap(scores, sample, bloc))
    values.sort()
    return values[int(0.025 * len(values))], values[int(0.975 * len(values))]


def main() -> None:
    dates, positions = load()
    if not dates:
        raise SystemExit("no dated divisions for NCA-2011; run `make build`")
    bloc = POL.blocs()
    people = sorted(positions)
    rng = random.Random(SEED)

    keep = contested(dates, positions, people)
    by_window: dict[str, list[str]] = collections.defaultdict(list)
    for vote_id in keep:
        by_window[window(dates[vote_id])].append(vote_id)
    for name in ("before", "crisis", "after"):
        by_window[name].sort(key=lambda v: (dates[v], v))  # ties broken by id

    # -- turnout, every division not just contested ones -------------------
    counts = collections.Counter(window(d) for d in dates.values())
    cast: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in S.load("vote_positions"):
        if row["position"] in ("pour", "contre", "abstenu"):
            cast[row["person_id"]][window(dates[row["vote_id"]])] += 1
    members_by_bloc: dict[str, list[str]] = collections.defaultdict(list)
    for person in people:
        members_by_bloc[bloc.get(person, "No bloc")].append(person)
    turnout = {
        name: {w: sum(cast[p][w] for p in group) / (len(group) * counts[w])
               for w in ("before", "crisis", "after")}
        for name, group in members_by_bloc.items()
    }

    # -- affinity, on the pairs scoreable in every window ------------------
    before = agreement(positions, people, by_window["before"])
    after_all = agreement(positions, people, by_window["after"])
    # Volume-matched: the same number of contested divisions, taken immediately
    # after the chamber resumes. Comparing 94 divisions with 864 would compare
    # agendas as much as periods.
    after_eq = agreement(positions, people, by_window["after"][:len(by_window["before"])])
    panel = sorted(set(before) & set(after_all) & set(after_eq))
    panel_members = sorted({p for pair in panel for p in pair})

    measured = []
    for label, scores in (("Before\n25 Jul 2013", before),
                          ("After, matched\nvolume", after_eq),
                          ("After, all\n864 divisions", after_all)):
        value = gap(scores, panel, bloc)
        low, high = cluster_interval(scores, panel, panel_members, bloc, rng)
        measured.append((label, value, low, high))

    # What survives in the crisis window, and who is missing from it. The
    # arithmetic works; the sample is the problem, so measure the sample.
    crisis_scores = agreement(positions, people, by_window["crisis"])
    crisis_members = collections.Counter()
    for a, b in crisis_scores:
        crisis_members[a] += 1
        crisis_members[b] += 1
    present = {name: sum(1 for p in group if crisis_members[p])
               for name, group in members_by_bloc.items()}
    # Ties broken by name: dict order would otherwise decide, and it is not
    # stable across processes once string hashing enters.
    biggest = max(sorted(members_by_bloc), key=lambda b: len(members_by_bloc[b]))
    enn_internal = sum(1 for k in crisis_scores
                       if bloc.get(k[0]) == biggest == bloc.get(k[1]))
    absent = sorted((b for b in members_by_bloc if present[b] == 0),
                    key=lambda b: (-len(members_by_bloc[b]), b))

    # -- draw ---------------------------------------------------------------
    fig = plt.figure(figsize=S.figsize(9.4, 8.4))
    grid = fig.add_gridspec(2, 2, height_ratios=(0.92, 1.0), hspace=0.46, wspace=0.34)
    ax_a = fig.add_subplot(grid[0, :])
    ax_b = fig.add_subplot(grid[1, 0])
    ax_c = fig.add_subplot(grid[1, 1])
    # One hue for the bars, one pair for the two behaviours in panel B, and the
    # third for the estimates in panel C. A hue never means two things across
    # panels: panel A is a single series and is drawn in the neutral.
    fell, held, accent = S.categorical(3, all_pairs=True)

    # A — contested divisions per month
    # Every month between the first and last division, not only the months that
    # produced one: skipping the empty ones would space the bars evenly in
    # *sittings* and hide the silences, which is most of what this panel is for.
    span = sorted({d[:7] for d in dates.values()})
    months, cursor = [], span[0]
    while cursor <= span[-1]:
        months.append(cursor)
        year, month = int(cursor[:4]), int(cursor[5:7]) + 1
        cursor = f"{year + (month > 12)}-{(month - 1) % 12 + 1:02d}"
    per_month = collections.Counter(dates[v][:7] for v in keep)
    ax_a.bar(range(len(months)), [per_month[m] for m in months], width=0.72,
             color=S.CHROME["axis"], zorder=3)
    first_crisis = months.index(ASSASSINATION[:7])
    last_crisis = max(i for i, m in enumerate(months) if m < CRISIS_END[:7])
    ax_a.axvspan(first_crisis - 0.5, last_crisis + 0.5,
                 color=S.CHROME["deemph"], alpha=0.55, zorder=1)
    ax_a.set_xticks(range(len(months)))
    ax_a.set_xticklabels([m[2:] if m[5:7] in ("01", "04", "07", "10") else ""
                          for m in months], fontsize=7.4)
    ax_a.set_ylabel(S.label("Contested divisions"), fontsize=8.4)
    ax_a.set_title(S.label("A · The chamber's contested business, by month"),
                   loc="left", fontsize=9.8, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_a)
    ax_a.axvline(first_crisis - 0.5, color=S.CHROME["text_primary"], linewidth=1.1,
                 linestyle=(0, (4, 2)), zorder=4)
    top = ax_a.get_ylim()[1]
    ax_a.annotate(S.label("Brahmi assassinated, 25 July 2013.\nAugust yields a single "
                          "contested division — the fewest\nof any month this chamber "
                          "divided in at all."),
                  xy=(first_crisis + 0.3, top * 0.92), fontsize=7.8,
                  ha="left", va="top", color=S.CHROME["text_primary"], zorder=5)

    # B — turnout by bloc across the three windows
    stages = ("before", "crisis", "after")
    order = sorted(turnout, key=lambda b: turnout[b]["crisis"] - turnout[b]["before"])
    label_y: list[tuple[float, str, bool]] = []
    for name in order:
        series = [turnout[name][s] for s in stages]
        dropped = series[1] - series[0] < -0.05
        ax_b.plot(range(3), series, marker="o", markersize=4.6,
                  linewidth=2.2 if dropped else 1.4,
                  color=fell if dropped else held, zorder=4 if dropped else 3)
        label_y.append((series[2], name, dropped))
    # Four blocs end the term within five points of each other, so their labels
    # would print on top of one another. Push them apart from the bottom up and
    # draw a leader where a label has moved off its own line.
    gap_y = 0.031
    placed_y: list[float] = []
    for y, name, dropped in sorted(label_y):
        target = y if not placed_y else max(y, placed_y[-1] + gap_y)
        placed_y.append(target)
        if abs(target - y) > 0.004:
            ax_b.plot([2.0, 2.03], [y, target], color=S.CHROME["axis"],
                      linewidth=0.7, zorder=2)
        ax_b.annotate(S.label(f"{name} ({len(members_by_bloc[name])})"),
                      xy=(2.05, target), fontsize=7.4, va="center", ha="left",
                      color=S.CHROME["text_primary"] if dropped
                      else S.CHROME["text_secondary"])
    ax_b.set_xlim(-0.1, 4.35)
    ax_b.set_xticks(range(3))
    ax_b.set_xticklabels([S.label(t) for t in
                          ("to 23 Jul\n2013", "25 Jul –\n30 Nov", "Dec 2013 –\nSep 2014")],
                         fontsize=7.8)
    ax_b.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax_b.set_ylabel(S.label("Share of divisions a member voted in"), fontsize=8.4)
    ax_b.set_title(S.label("B · Who stopped voting, and who did not"),
                   loc="left", fontsize=9.8, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_b)
    ax_b.legend(handles=[
        mlines.Line2D([], [], color=fell, linewidth=2.2,
                      label=S.label("Turnout fell in the crisis window")),
        mlines.Line2D([], [], color=held, linewidth=1.4,
                      label=S.label("Held or rose")),
    ], loc="lower right", fontsize=7.6, framealpha=0.9)

    # C — the within/cross agreement gap, where the sample supports one
    for i, (label, value, low, high) in enumerate(measured):
        x = i if i == 0 else i + 1
        ax_c.plot([x, x], [low, high], color=S.CHROME["deemph"], linewidth=9,
                  solid_capstyle="butt", zorder=2)
        ax_c.plot([x], [value], marker="D", markersize=8, color=accent, zorder=4,
                  markeredgecolor=S.CHROME["surface"], markeredgewidth=1.0)
        ax_c.annotate(f"{value:+.2f}", xy=(x, high), xytext=(0, 7),
                      textcoords="offset points", ha="center", fontsize=8.4,
                      color=S.CHROME["text_primary"])
    ax_c.set_xlim(-0.6, 3.6)
    lo_y, hi_y = ax_c.get_ylim()
    ax_c.axvspan(0.45, 1.55, color=S.CHROME["deemph"], alpha=0.4, zorder=1)
    ax_c.annotate(
        S.label(f"No comparable\nestimate:\n{len(by_window['crisis'])} contested\n"
                f"divisions, and\n{present[absent[0]]} of "
                f"{len(members_by_bloc[absent[0]])}\n{absent[0]}\nmembers in any\n"
                f"scoreable pair"),
        xy=(1.0, (lo_y + hi_y) / 2), ha="center", va="center", fontsize=7.0,
        color=S.CHROME["text_secondary"], zorder=5)
    ax_c.set_xticks([0, 1, 2, 3])
    ax_c.set_xticklabels([S.label(measured[0][0]), S.label("Crisis"),
                          S.label(measured[1][0]), S.label(measured[2][0])],
                         fontsize=7.6)
    ax_c.set_ylabel(S.label("Within-bloc minus cross-bloc agreement"), fontsize=8.4)
    ax_c.set_title(S.label("C · Did affinity change? Not detectably"),
                   loc="left", fontsize=9.8, color=S.CHROME["text_primary"], pad=6)
    S.frame(ax_c)

    dem = "Democratic Bloc"
    returned = sum(1 for b in turnout if turnout[b]["after"] >= turnout[b]["before"])
    in_panel = set(panel_members)
    panel_share = {name: sum(1 for p in group if p in in_panel) / len(group)
                   for name, group in members_by_bloc.items()}
    # Figure-level title and subtitle, as in figure 21: with three panels there
    # is no one axes for S.titles to hang them on.
    # subplots_adjust rather than tight_layout: the header is a fixed block of
    # figure text, and tight_layout does not know it is there.
    fig.subplots_adjust(left=0.075, right=0.985, top=0.755, bottom=0.075)
    fig.text(0.012, 0.985,
             "The Brahmi crisis shows up as a walkout, not as a change in who votes with whom",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.012, 0.952,
        f"The 2011 Constituent Assembly either side of the assassination of "
        f"Mohamed Brahmi on 25 July 2013. Over the next four months turnout fell "
        f"from {turnout[dem]['before']:.0%} to\n{turnout[dem]['crisis']:.0%} for the "
        f"Democratic Bloc and {turnout['Democratic Alliance']['before']:.0%} to "
        f"{turnout['Democratic Alliance']['crisis']:.0%} for the Democratic "
        f"Alliance, while Ennahdha went {turnout['Ennahdha']['before']:.0%} to "
        f"{turnout['Ennahdha']['crisis']:.0%} and CPR "
        f"{turnout['CPR']['before']:.0%} to {turnout['CPR']['crisis']:.0%}. By "
        f"December {returned} of the eight are back at or above where they started."
        f"\nAffinity is a different matter. Across the "
        f"crisis the within/cross gap moves from {measured[0][1]:+.2f} to "
        f"{measured[1][1]:+.2f} on matched volume, with intervals that overlap — "
        f"resampling members, not\npairs, because one member sits in over a hundred "
        f"pairs and pair-level resampling would report that noise as a finding. And "
        f"the {len(panel_members)} members scoreable in every\nwindow are "
        f"{panel_share['Ennahdha']:.0%} of Ennahdha against {panel_share[dem]:.0%} of "
        f"the Democratic Bloc, so the affinity question is largely being put to the "
        f"people who never stopped\nvoting. Bloc is each member's last recorded "
        f"spell: the source publishes no dated bloc history for this chamber.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")

    rows = []
    for name in order:
        rows.append({
            "series": "turnout",
            "group": name,
            "members": len(members_by_bloc[name]),
            "members_scoreable_in_crisis": present[name],
            "share_in_affinity_panel": round(panel_share[name], 4),
            "value_before": round(turnout[name]["before"], 4),
            "value_crisis": round(turnout[name]["crisis"], 4),
            "value_after": round(turnout[name]["after"], 4),
            "crisis_change": round(turnout[name]["crisis"] - turnout[name]["before"], 4),
            "ci_low": "", "ci_high": "",
        })
    rows.append({
        "series": "crisis_window_composition",
        "group": f"{biggest} x {biggest} share of scoreable crisis pairs",
        "members": len(crisis_scores),
        "members_scoreable_in_crisis": enn_internal,
        "share_in_affinity_panel": round(enn_internal / len(crisis_scores), 4),
        "value_before": "", "value_crisis": "", "value_after": "",
        "crisis_change": "", "ci_low": "", "ci_high": "",
    })
    for label, value, low, high in measured:
        rows.append({
            "series": "within_minus_cross_agreement",
            "group": label.replace("\n", " "),
            "members": len(panel_members),
            "members_scoreable_in_crisis": "",
            "share_in_affinity_panel": "",
            "value_before": "", "value_crisis": "", "value_after": round(value, 4),
            "crisis_change": "",
            "ci_low": round(low, 4), "ci_high": round(high, 4),
        })
    S.save(fig, "fig43_brahmi_crisis_nca2011", rows)


if __name__ == "__main__":
    main()
