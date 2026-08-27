"""Figure 8 — How many chambers each parliamentarian sat in.

The elite-persistence distribution. One series, one hue; an emphasis treatment
would be wrong here because no single bar is the story — the shape is.

The caveat in the subtitle is not boilerplate, it is the main threat to reading
this figure. The count is of mandates *in this dataset*, and eleven chambers
between 1959 and 2011 have no roster. Someone elected in 1994 and again in 2011
appears here as a one-term member. The bias is therefore systematic, not noise:
it pushes every bar left, and it pushes hardest on exactly the people whose
careers spanned the authoritarian and democratic periods — the population an
elite-survival argument most wants to observe.

Within the democratic period, where coverage is continuous, the counts are sound.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

DEMOCRATIC = ("NCA-2011", "ARP-2014", "ARP-2019", "ARP-2023")


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    served: dict[str, set[str]] = defaultdict(set)
    for m in S.load("mandates"):
        served[m["person_id"]].add(m["assembly_id"])

    all_counts = Counter(len(v) for v in served.values())
    dem_counts = Counter(
        len(v & set(DEMOCRATIC)) for v in served.values() if v & set(DEMOCRATIC)
    )

    fig, ax = plt.subplots(figsize=S.figsize(7.2, 4.2))
    blue, orange = S.categorical(2)

    ks = sorted(set(all_counts) | set(dem_counts))
    width = 0.4
    xs = range(len(ks))
    a = [all_counts.get(k, 0) for k in ks]
    b = [dem_counts.get(k, 0) for k in ks]

    ax.bar([x - width / 2 for x in xs], a, width=width, color=blue,
           label="All chambers in the dataset", linewidth=0)
    ax.bar([x + width / 2 for x in xs], b, width=width, color=orange,
           label="Counting only the four democratic chambers", linewidth=0)

    for x, (va, vb) in zip(xs, zip(a, b)):
        for offset, value in ((-width / 2, va), (width / 2, vb)):
            if value:
                ax.annotate(f"{value}", xy=(x + offset, value), xytext=(0, 3),
                            textcoords="offset points", ha="center", fontsize=7.6,
                            color=S.CHROME["text_secondary"])

    ax.set_xticks(list(xs))
    ax.set_xticklabels([str(k) for k in ks])
    ax.set_yscale("log")
    ax.set_ylim(0.7, max(a) * 2.2)
    S.frame(ax)
    ax.legend(loc="upper right")
    S.titles(
        ax,
        "Chambers served per parliamentarian",
        "Log scale: most members sit once, so a linear axis would flatten the tail into "
        "nothing.\nCounts are of mandates recorded HERE — the eleven chambers of 1959–2011 "
        "have no roster, so anyone whose\nearlier service falls in that gap is undercounted.",
        ylabel="Parliamentarians (log)",
        xlabel="Number of chambers served",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/mandates.csv")

    S.save(fig, "fig08_chambers_served", [
        {"chambers_served": k,
         "parliamentarians_all_chambers": all_counts.get(k, 0),
         "parliamentarians_democratic_only": dem_counts.get(k, 0)}
        for k in ks
    ])


if __name__ == "__main__":
    main()
