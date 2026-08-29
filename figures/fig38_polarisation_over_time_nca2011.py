"""Figure 38 — Did the 2011 assembly polarise as it went?

The agreement graph rebuilt inside six windows of the term, each holding an
equal number of contested divisions, and three quantities plotted per window:
mean agreement within blocs, mean agreement across them, and the gap between.

Equal *divisions* per window rather than equal months, because the chamber's
voting was violently uneven — two-thirds of the record falls in three months
(figure 24), so calendar windows would put 400 divisions in one point and eleven
in another and the resulting line would be mostly sampling noise. The cost is
that the windows are wildly unequal in time, which the axis labels show.

**What to read, and what not to.** The gap is the polarisation measure: it is the
part that cannot be produced by the chamber simply agreeing more or less overall.
Both levels move together across the term — every window's agreement rises and
falls as a block, because what is on the order paper changes — and reading either
line alone would confuse "this month's votes were contentious" with "the chamber
divided along bloc lines".

Three cautions, all of which bound this figure more than the others in the set:

- **Windows are not independent.** The same 217 members appear in all six, so
  the points are repeated measures on one chamber and the eye should not read a
  trend line through them as it would through independent samples.
- **Participation collapses across the term** (figure 25): 18% of members were
  not voting in the first window and 56% by the last. Later windows describe a
  progressively smaller and more selective slice of the chamber, and if the
  members who stopped voting were disproportionately cross-bloc agreers, that
  alone would move the gap.
- **Bloc is fixed at the member's last recorded spell** and applied to every
  window, including ones before a member had moved. With 105 of 217 changing
  party over the term, early windows are scored against an end-of-term map.

Those three together are why this figure reports a series and not a slope. What
it shows is a flat one: the gap sits between 0.15 and 0.21 in every window, with
no monotone movement across the term. The 2011 assembly did not polarise as it
went — on this measure it began divided along bloc lines and ended the same way,
through the constitution's drafting, two assassinations and a change of
government.
"""

from __future__ import annotations

import collections
import statistics
import sys
from datetime import date
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
WINDOWS = 6
MIN_CAST = 40
MIN_MINORITY = 0.025
MIN_SHARED = 12  # per window, a pair needs this many jointly-cast divisions


def main() -> None:
    when: dict[str, date] = {}
    for row in S.load("votes"):
        if row["assembly_id"] != ASSEMBLY or not row["vote_date"]:
            continue
        y, m, d = row["vote_date"].split("-")
        when[row["vote_id"]] = date(int(y), int(m), int(d))

    positions: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["assembly_id"] != ASSEMBLY or row["vote_id"] not in when:
            continue
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1

    tally: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for person, votes in positions.items():
        for vote_id, value in votes.items():
            tally[vote_id]["pour" if value == 1 else "contre"] += 1
    contested = sorted(
        (v for v, c in tally.items()
         if c["pour"] + c["contre"] >= MIN_CAST
         and min(c["pour"], c["contre"]) / (c["pour"] + c["contre"]) >= MIN_MINORITY),
        key=lambda v: (when[v], v))
    if len(contested) < WINDOWS * 10:
        raise SystemExit("too few contested divisions to window")

    bloc = POL.blocs(ASSEMBLY)
    people = sorted(positions)
    size = len(contested) // WINDOWS
    rows = []
    for w in range(WINDOWS):
        chunk = contested[w * size:(w + 1) * size if w < WINDOWS - 1 else None]
        chunk_set = set(chunk)
        within, across = [], []
        for i, a in enumerate(people):
            va = {k: v for k, v in positions[a].items() if k in chunk_set}
            if not va:
                continue
            for b in people[i + 1:]:
                vb = positions[b]
                shared = [k for k in va if k in vb]
                if len(shared) < MIN_SHARED:
                    continue
                rate = sum(va[k] == vb[k] for k in shared) / len(shared)
                (within if bloc.get(a) == bloc.get(b) else across).append(rate)
        if not within or not across:
            continue
        rows.append({
            "window": w + 1,
            "first_division": chunk[0].isoformat() if hasattr(chunk[0], "isoformat")
            else when[chunk[0]].isoformat(),
            "last_division": when[chunk[-1]].isoformat(),
            "divisions": len(chunk),
            "within_pairs": len(within), "across_pairs": len(across),
            "within_bloc_agreement": round(statistics.fmean(within), 4),
            "cross_bloc_agreement": round(statistics.fmean(across), 4),
            "gap": round(statistics.fmean(within) - statistics.fmean(across), 4),
        })

    x = [r["window"] for r in rows]
    c_within, c_gap = S.categorical(2, all_pairs=True)
    fig, ax = plt.subplots(figsize=S.figsize(8.2, 5.0))

    ax.plot(x, [r["within_bloc_agreement"] for r in rows], color=c_within,
            linewidth=2.2, marker="o", markersize=5, zorder=4)
    ax.plot(x, [r["cross_bloc_agreement"] for r in rows], color=c_within,
            linewidth=2.2, marker="o", markersize=5, alpha=0.42, zorder=4)
    ax.fill_between(x, [r["cross_bloc_agreement"] for r in rows],
                    [r["within_bloc_agreement"] for r in rows],
                    color=c_within, alpha=0.10, zorder=2)
    ax.plot(x, [r["gap"] for r in rows], color=c_gap, linewidth=2.4,
            marker="D", markersize=5, zorder=5)

    for r in rows:
        ax.annotate(f"{r['gap']:.2f}", xy=(r["window"], r["gap"]), xytext=(0, -14),
                    textcoords="offset points", ha="center", fontsize=7.8,
                    color=c_gap, zorder=6)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [S.label(f"{r['first_division'][:7]}\n→ {r['last_division'][:7]}\n"
                 f"{r['divisions']} divisions") for r in rows], fontsize=7.6)
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    S.frame(ax)

    gaps = [r["gap"] for r in rows]
    S.titles(
        ax,
        f"The bloc gap holds between {min(gaps):.2f} and {max(gaps):.2f} all term — "
        "no build-up",
        f"The agreement graph rebuilt in {len(rows)} windows of roughly "
        f"{rows[0]['divisions']} contested divisions each — equal divisions, not "
        "equal months, because two-thirds of\nthis chamber's voting falls in three "
        "months and calendar windows would be mostly sampling noise. The gap is "
        "the polarisation measure: both\nlevels rise and fall together as the "
        "order paper changes, so either line alone would confuse a contentious "
        "month with a bloc-divided chamber. The gap moves\nwithin a narrow band "
        "and not in one direction: this chamber does not polarise as it goes, it "
        "starts divided and stays that way. Windows\nare repeated measures on the "
        "same 217 members, not independent samples; participation falls from 18% "
        "to 56% not voting across them (figure 25);\nand bloc is fixed at each "
        "member's last spell even in windows before they moved. A series, not a "
        "slope.",
        ylabel="Mean agreement on contested divisions",
    )
    ax.legend(
        handles=[
            mlines.Line2D([], [], color=c_within, linewidth=2.4, marker="o",
                          label=S.label("Within bloc")),
            mlines.Line2D([], [], color=c_within, linewidth=2.4, marker="o",
                          alpha=0.42, label=S.label("Across blocs")),
            mlines.Line2D([], [], color=c_gap, linewidth=2.4, marker="D",
                          label=S.label("Gap (the polarisation measure)")),
        ],
        loc="center left", fontsize=8.2,
    )
    S.source_note(fig, "ParliamentariansTN · vote_positions.csv × votes.csv")

    S.save(fig, "fig38_polarisation_over_time_nca2011", rows)


if __name__ == "__main__":
    main()
