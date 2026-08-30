"""Figure 29 — Do women reach committee leadership at the rate they sit?

Committee memberships split by whether the role is a leading one — chair or
vice-chair — and by the member's sex, in the four chambers with committee data.
The bar is the share of each group's memberships that carry a leading role, and
the interval is a 95% Wilson score interval, because the counts behind these
percentages are small and a bare bar would hide that.

The answer is that this design cannot tell. In all four chambers the two
intervals overlap — 6.5% against 10.0% in 2011, 7.5% against 8.8% in 2014, 9.9%
against 10.2% in 2019, and 14.8% against 23.7% in 2023, where the female
interval runs from 7.7% to 26.6% and swallows the male estimate whole. Every
point estimate runs against women, which is worth noting as a direction, but not
one of the four differences is distinguishable from chance at this sample size.
The largest apparent gap sits in the chamber with the fewest female memberships,
which is exactly where noise is largest.

**The 2014 chamber is the one that carries weight.** Its 985 memberships are
more than the other three chambers combined, and they buy the tightest intervals
in the figure — 5.2–10.6% for women against 6.8–11.3% for men. Those still
overlap heavily. Where the other columns say "we cannot see a difference", this
one says a difference large enough to matter would have shown.

Report the rest as an underpowered null, not as evidence of parity: 54 female
memberships cannot resolve a difference of the size that would matter.

**Why memberships and not people.** A deputy on three committees contributes
three rows, so someone with many seats counts more than someone with one. That
is deliberate — the question is what share of leadership positions a group
holds relative to its presence in committee rooms — but it means a small number
of heavily-appointed individuals can move a bar, especially in the smaller
female group.

**Sex for the 2011 chamber is inferred, not recorded.** Marsad publishes no sex
field; it is inferred from French grammatical agreement in each member's own
biography and never from the name. That inference has its own error rate and it
lands entirely on the NCA-2011 column here.

Chair and vice-chair count as leading; rapporteur and assistant rapporteur do
not. That line is a judgement — a rapporteurship is real influence over a text —
and moving it would change the numbers, so the companion CSV breaks out all five
roles for anyone who would draw it elsewhere.
"""

from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

LEADING = ("chair", "vice_chair")
SEXES = ("female", "male")


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval — behaves at small n, where normal-approx does not."""
    if not total:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> None:
    sex = {r["person_id"]: r["gender"] for r in S.load("persons")}
    roles: dict[tuple[str, str], collections.Counter] = collections.defaultdict(
        collections.Counter)
    for row in S.load("committee_memberships"):
        g = sex.get(row["person_id"], "")
        if g in SEXES:
            roles[(row["assembly_id"], g)][row["role"]] += 1

    chambers = sorted({a for a, _ in roles},
                      key=lambda a: [x["assembly_id"] for x in S.assemblies_in_order()].index(a))
    fig, ax = plt.subplots(figsize=S.figsize(7.8, 5.0))
    palette = S.categorical(2, all_pairs=True)
    width = 0.34
    x = np.arange(len(chambers))

    rows = []
    for offset, (g, colour) in enumerate(zip(SEXES, palette)):
        shares, los, his = [], [], []
        for chamber in chambers:
            counts = roles[(chamber, g)]
            total = sum(counts.values())
            lead = sum(counts[r] for r in LEADING)
            share = lead / total if total else 0.0
            lo, hi = wilson(lead, total)
            shares.append(share)
            los.append(share - lo)
            his.append(hi - share)
            rows.append({
                "assembly_id": chamber, "sex": g, "memberships": total,
                "chair": counts["chair"], "vice_chair": counts["vice_chair"],
                "rapporteur": counts["rapporteur"],
                "assistant_rapporteur": counts["assistant_rapporteur"],
                "member": counts["member"],
                "leading_share": round(share, 4),
                "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            })
        pos = x + (offset - 0.5) * width
        ax.bar(pos, shares, width=width * 0.92, color=colour, zorder=3)
        ax.errorbar(pos, shares, yerr=[los, his], fmt="none", ecolor=S.CHROME["axis"],
                    elinewidth=1.2, capsize=3, zorder=4)
        for px, share, chamber in zip(pos, shares, chambers):
            n = sum(roles[(chamber, g)].values())
            ax.annotate(f"{share:.0%}\nn={n}", xy=(px, 0), xytext=(0, 5),
                        textcoords="offset points", ha="center", va="bottom",
                        fontsize=7.6, color="#ffffff", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels([S.label(LBL.assembly(c)) for c in chambers], fontsize=8.6)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    S.frame(ax)

    S.titles(
        ax,
        "Too few women in committee to tell whether they lead less often",
        "Share of each group's committee memberships that carry a chair or "
        "vice-chair role, with 95% Wilson intervals. Every pair of\nintervals "
        "overlaps, including the 2023 chamber's 15% against 24%, where 54 female "
        "memberships give an interval from 8% to 27%.\nRead this as an "
        "underpowered null: the point estimates all run against women, but none "
        "of the four gaps is distinguishable from\nchance here — and the 2014 "
        "chamber, whose 985 memberships buy the tightest intervals in the "
        "figure, still overlaps heavily.\nThe unit is the "
        "membership, not the person, so a deputy on three committees counts "
        "three times: this asks what share of leading roles a group\nholds "
        "relative to its presence in committee rooms. Rapporteurships are not "
        "counted as leading, which is a judgement — the CSV\nbreaks out all five "
        "roles. Sex in the 2011 chamber is inferred from French grammatical "
        "agreement in each member's biography,\nnever from the name, and that "
        "inference's error lands on that column alone.",
        ylabel="Share of memberships that lead a committee",
    )
    ax.legend(
        handles=[mlines.Line2D([], [], color=c, linewidth=7, label=S.label(g.capitalize()))
                 for g, c in zip(SEXES, palette)],
        loc="upper left", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · committee_memberships.csv × persons.csv")

    S.save(fig, "fig29_women_committee_leadership", rows)


if __name__ == "__main__":
    main()
