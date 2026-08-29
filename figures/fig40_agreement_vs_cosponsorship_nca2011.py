"""Figure 40 — Voting together and working together are different things.

Every pair of members in the 2011 assembly placed on two axes: how much they
agreed on contested divisions (horizontal) and whether they ever co-sponsored an
amendment (the bars). Pairs are binned by agreement; each bar is the share of
that bin's pairs who also put their names to the same amendment.

The relationship is real and very weak. Across all 23,337 pairs the
point-biserial correlation is **+0.14**, so agreement accounts for under 2% of
the variance in whether a pair ever co-sponsored. The bars rise from 29% to 54%
across the range but not monotonically, and the top bin — pairs agreeing more
than 95% of the time — falls back to 42%.

It is not simply bloc membership doing the work. Within cross-bloc pairs alone
the correlation is +0.11, barely lower, so agreeing more predicts co-sponsoring
slightly more even between members of different blocs.

**This is the chosen/revealed distinction made concrete at the level of two
people.** Amendment co-sponsorship is an act: two members decided to be seen
supporting the same text. Vote agreement is a correlation: it occurs whether or
not either intended it, and two members on opposite sides of the chamber who
both back an uncontroversial measure are "agreeing" in exactly the same sense as
two allies. Knowing that a pair votes together tells you remarkably little about
whether they work together, which is why this dataset carries both layers rather
than treating either as a proxy for cooperation.

**Correlation is not the mechanism, and the arrow could point either way.**
Members who co-sponsor may vote alike because they were already allies; or
co-sponsoring may be what allies do once they find themselves voting together;
or bloc membership may produce both with no direct link. Nothing here separates
those, and the flatness of the middle of the range is if anything evidence
against a strong direct link in either direction.

The bars carry Wilson intervals, because the extreme bins hold few pairs and a
bare percentage there would invite reading noise as a trend. Bins with fewer
than 50 pairs are dropped; the companion CSV has every bin including those.
"""

from __future__ import annotations

import collections
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
BIN_WIDTH = 0.05
MIN_PAIRS = 50


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if not total:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def main() -> None:
    dyads = POL.agreement_dyads(ASSEMBLY)
    if not dyads:
        raise SystemExit("no vote-agreement edges; run `make networks`")

    cosponsored = {
        tuple(sorted((r["source"], r["target"])))
        for r in S.load("edges_amendment_cosponsorship")
        if r["assembly_id"] == ASSEMBLY
    }

    bins: dict[int, list[bool]] = collections.defaultdict(list)
    for a, b, weight, _ in dyads:
        bins[int(weight / BIN_WIDTH)].append(tuple(sorted((a, b))) in cosponsored)

    rows = []
    for key in sorted(bins):
        flags = bins[key]
        hits = sum(flags)
        lo, hi = wilson(hits, len(flags))
        rows.append({
            "agreement_from": round(key * BIN_WIDTH, 3),
            "agreement_to": round((key + 1) * BIN_WIDTH, 3),
            "pairs": len(flags),
            "cosponsoring_pairs": hits,
            "share_cosponsoring": round(hits / len(flags), 4),
            "ci_low": round(lo, 4), "ci_high": round(hi, 4),
            "in_figure": len(flags) >= MIN_PAIRS,
        })

    drawn = [r for r in rows if r["in_figure"]]
    x = [(r["agreement_from"] + r["agreement_to"]) / 2 for r in drawn]
    share = [r["share_cosponsoring"] for r in drawn]

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 5.0))
    bar_colour = S.categorical(1)[0]
    ax.bar(x, share, width=BIN_WIDTH * 0.88, color=bar_colour, zorder=3)
    ax.errorbar(x, share,
                yerr=[[s - r["ci_low"] for s, r in zip(share, drawn)],
                      [r["ci_high"] - s for s, r in zip(share, drawn)]],
                fmt="none", ecolor=S.CHROME["axis"], elinewidth=1.1, capsize=2.5,
                zorder=4)

    overall = sum(r["cosponsoring_pairs"] for r in rows) / sum(r["pairs"] for r in rows)
    ax.axhline(overall, color=S.CHROME["text_secondary"], linewidth=1.2,
               linestyle=(0, (5, 4)), zorder=5)
    ax.annotate(f"all pairs: {overall:.0%}", xy=(x[0], overall), xytext=(0, 6),
                textcoords="offset points", ha="left", va="bottom", fontsize=8,
                color=S.CHROME["text_secondary"], zorder=6)

    for value, r in zip(x, drawn):
        ax.annotate(f"{r['pairs']:,}", xy=(value, 0), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=6.8, color="#ffffff", rotation=90, zorder=6)

    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlim(min(x) - BIN_WIDTH, max(x) + BIN_WIDTH)
    S.frame(ax, x_grid=True)
    S.titles(
        ax,
        "Voting together barely predicts working together: r = +0.14",
        "Every scored pair of members in the 2011 Constituent Assembly, binned by "
        "how much they agreed on contested divisions; each bar is the share of "
        "that\nbin's pairs who ever co-sponsored an amendment together. The "
        "correlation across all 23,337 pairs is +0.14 — agreement accounts for "
        "under 2% of the variance\nin whether a pair co-sponsored — and the rise "
        "is not monotone: the top bin falls back to 42%. Within cross-bloc pairs "
        "alone it is +0.11, so this is not\nsimply bloc membership. "
        "Agreement is a correlation that occurs whether or not either member "
        "intended it; co-sponsorship is an act\ntwo people chose. Nothing here "
        "identifies which way any influence runs, or whether bloc membership "
        "simply produces both. Bars carry 95% Wilson\nintervals and the pair count "
        f"in white; bins under {MIN_PAIRS} pairs are dropped from the drawing but "
        "kept in the CSV.",
        xlabel="Share of jointly-cast contested divisions voted the same way",
        ylabel="Share of pairs who co-sponsored an amendment",
    )
    S.source_note(fig, "ParliamentariansTN · edges_vote_agreement.csv × edges_amendment_cosponsorship.csv")

    S.save(fig, "fig40_agreement_vs_cosponsorship_nca2011", rows)


if __name__ == "__main__":
    main()
