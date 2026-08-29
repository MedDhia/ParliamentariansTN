"""Figure 31 — Which articles of the 2014 constitution were fought over.

Amendments tabled against each part of the draft, for the parts that drew the
most. All 251 recorded amendments carry a target and they spread across 98 of
them, so the concentration is mild — the busiest *article* drew nine amendments,
not ninety.

The exception is the preamble, with 19: more than twice any single article. The
source encodes it as "article 0", and it is relabelled here rather than dropped,
because a preamble attracting twice the amendment traffic of any operative
clause is a fact about what the assembly argued over rather than a parsing
artefact. An earlier draft of this figure did drop it and lost the largest bar
on the chart.

This is the contested tail of figure 26 given a subject. That figure shows that
42% of the assembly's divisions were near-unanimous and the argument lived in a
minority of votes; this shows what the minority was about. Article 6, on the
state's relationship to religion, is in the top handful, which is where the
public argument of 2012-2014 was too.

**Two amendments on one article are not two equal things.** One may be a
drafting tidy-up with a single sponsor and the next a rewrite carrying fifty,
so the bars are split by how many members co-signed: an article that drew many
lightly-sponsored amendments is a different object from one that drew a few
heavily-sponsored ones. The count of amendments alone would flatten that.

**The article number comes from a link, not from a reading of the text.** Each
amendment carries a target label and a URL, and the number is parsed out of
them. Article numbering shifted between drafts, so a number here is the one the
source recorded at the time and may not be that article's number in the adopted
constitution. Nothing is excluded from this figure — every recorded amendment
resolves to a target — but only the eighteen busiest are drawn, and the
companion CSV carries all 98 with an `in_figure` column saying which were.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
TOP = 18
BANDS = ((1, 4, "1–4 sponsors"), (5, 19, "5–19"), (20, 10 ** 6, "20 or more"))
_ARTICLE = re.compile(r"article[\s/]*(\d+)", re.I)


def main() -> None:
    per_article: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    untargeted = []
    for row in S.load("amendments"):
        if row["assembly_id"] != ASSEMBLY:
            continue
        found = _ARTICLE.search(f"{row['target_label']} {row['target_url']}")
        if not found:
            # Every row currently resolves. Kept as a guard rather than an
            # assumption: if the source adds a target shape this pattern misses,
            # the count should surface rather than the rows vanishing silently.
            untargeted.append(row["amendment_id"])
            continue
        n = int(S.num(row["n_sponsors"], 0) or 0)
        # The source numbers the preamble "article 0". Relabel rather than drop:
        # it is the single most-amended part of the text.
        band = next(name for lo, hi, name in BANDS if lo <= n <= hi)
        per_article[found.group(1)][band] += 1

    if not per_article:
        raise SystemExit(f"no amendments resolve to a target for {ASSEMBLY}")
    if untargeted:
        raise SystemExit(
            f"{len(untargeted)} amendments carry a target this figure cannot "
            f"parse, e.g. {untargeted[0]}; widen _ARTICLE rather than dropping them")

    resolved = sum(sum(c.values()) for c in per_article.values())
    order = sorted(per_article, key=lambda a: (sum(per_article[a].values()), -int(a)))[-TOP:]
    labels = [name for _, _, name in BANDS]
    palette = S.sequential(len(labels), ordinal=True)

    fig, ax = plt.subplots(figsize=S.figsize(7.6, 6.0))
    y = np.arange(len(order))
    left = np.zeros(len(order))
    for band, colour in zip(labels, palette):
        widths = np.array([per_article[a][band] for a in order], dtype=float)
        ax.barh(y, widths, left=left, height=0.66, color=colour, zorder=3)
        left += widths

    ax.set_yticks(y)
    ax.set_yticklabels(
        [S.label("Preamble" if a == "0" else f"Article {a}") for a in order],
        fontsize=8.4)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlim(0, left.max() * 1.04)
    S.frame(ax, x_grid=True, y_grid=False)
    S.integer_axis(ax, "x")

    S.titles(
        ax,
        "The preamble drew twice as many amendments as any single article",
        f"Amendments tabled against each part of the draft constitution: the "
        f"{TOP} busiest of {len(per_article)} targets named. All {resolved} "
        "recorded amendments carry a target, so\nnothing is excluded — the "
        "source numbers the preamble “article 0”, and it is relabelled rather "
        "than dropped, because a preamble drawing more\namendments than any "
        "operative clause is a fact about the argument and not a parsing "
        "artefact. Bars are split by how many members co-signed,\nbecause one "
        "amendment can be a drafting tidy-up and the next a rewrite carrying "
        "fifty names. Numbering shifted between drafts, so an article\nnumber "
        "here is the one the source recorded at the time, not necessarily the "
        "adopted one.",
        xlabel="Amendments tabled",
    )
    ax.legend(
        handles=[mlines.Line2D([], [], color=c, linewidth=7, label=S.label(b))
                 for b, c in zip(labels, palette)],
        loc="lower right", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/amendments.csv")

    S.save(fig, "fig31_contested_articles_nca2011", [
        {
            "target": "Preamble" if a == "0" else f"Article {a}",
            "article_number": int(a),
            "amendments": sum(per_article[a].values()),
            **{b.replace("–", "-").replace(" ", "_"): per_article[a][b] for b in labels},
            "in_figure": a in order,
        }
        for a in sorted(per_article, key=lambda a: (-sum(per_article[a].values()), int(a)))
    ])


if __name__ == "__main__":
    main()
