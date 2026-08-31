"""Figure 30 — Where the deputies with a recorded career came from.

Extra-parliamentary roles by sector: education and the judiciary first, then
academia, party organisations and the trade-union movement. It is the elite
recruitment layer the dataset was built to support, and it is the thinnest
layer in it.

**Read the denominator before the bars.** 171 roles are recorded for 114 people
out of 856 in the dataset — 13%. Every one of them comes from a single source,
the 2011 assembly's narrative biographies on Marsad, so this is not "Tunisian
parliamentarians" but "the minority of one chamber's members whose biography
mentioned a prior role, as parsed". Nothing here supports a claim about
recruitment into parliament generally, and the figure says so rather than
letting a clean bar chart imply otherwise.

**The rows are rule-extracted from prose, not hand-coded.** A parser reads
sentences like "membre du syndicat" out of a French biography and assigns a
sector. Every row carries `extraction_method='rule'` and a confidence grade, and
the bars are split by that grade so the reader can see how much of each sector
rests on a confident match. They are a starting point for hand-coding, which is
the repository's standing request in its contributing notes.

Sectors are not mutually exclusive across people: a member who was both a
lawyer and a party official contributes a row to each, so the bars count roles
rather than people and sum to more than 114.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

GRADES = ("high", "medium", "low")
SECTOR_LABEL = {
    "state_executive": "State executive",
    "state_administration": "State administration",
    "trade_union": "Trade union",
    "civil_society": "Civil society",
}


def main() -> None:
    careers = S.load("careers")
    if not careers:
        raise SystemExit("no career rows recorded")

    by_sector: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in careers:
        sector = row["sector"] or "unknown"
        by_sector[sector][row["confidence"] or "unknown"] += 1

    people = len({r["person_id"] for r in careers})
    total_persons = sum(1 for _ in S.load("persons"))
    order = sorted(by_sector, key=lambda s: (sum(by_sector[s].values()), s))
    grades = [g for g in GRADES if any(by_sector[s][g] for s in order)]
    palette = S.sequential(max(len(grades), 2), ordinal=True)[::-1]

    fig, ax = plt.subplots(figsize=S.figsize(7.8, 5.6))
    y = np.arange(len(order))
    left = np.zeros(len(order))
    for grade, colour in zip(grades, palette):
        widths = np.array([by_sector[s][grade] for s in order], dtype=float)
        ax.barh(y, widths, left=left, height=0.66, color=colour, zorder=3)
        left += widths

    for i, sector in enumerate(order):
        ax.annotate(f"{sum(by_sector[sector].values())}", xy=(left[i], i),
                    xytext=(4, 0), textcoords="offset points", ha="left",
                    va="center", fontsize=8, color=S.CHROME["text_secondary"])

    ax.set_yticks(y)
    ax.set_yticklabels(
        [S.label(SECTOR_LABEL.get(s, s.replace("_", " ").capitalize())) for s in order],
        fontsize=8.4)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlim(0, left.max() * 1.08)
    S.frame(ax, x_grid=True, y_grid=False)
    S.integer_axis(ax, "x")

    S.titles(
        ax,
        "Teachers and judges, from the 13% with any career recorded",
        f"Extra-parliamentary roles by sector: {len(careers)} roles for "
        f"{people} people out of {total_persons:,} in the dataset. All of them "
        "come from one source, the 2011\nassembly's narrative biographies, so "
        "this describes the minority of one chamber whose biography mentioned a "
        "prior role — not recruitment into\nTunisian parliament, which this "
        "cannot speak to. The rows are rule-extracted from French prose rather "
        "than hand-coded, and the bars are split by\nthe extraction's own "
        "confidence grade so the softer matches are visible. A member with two "
        "prior roles contributes two rows, so these count roles,\nnot people.",
        xlabel="Recorded roles",
    )
    ax.legend(
        handles=[mlines.Line2D([], [], color=c, linewidth=7,
                               label=S.label(f"{g} confidence"))
                 for g, c in zip(grades, palette)],
        loc="lower right", fontsize=8.4,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/careers.csv")

    S.save(fig, "fig30_career_sectors", [
        {
            "sector": sector,
            "roles": sum(by_sector[sector].values()),
            **{f"confidence_{g}": by_sector[sector][g] for g in grades},
        }
        for sector in reversed(order)
    ])


if __name__ == "__main__":
    main()
