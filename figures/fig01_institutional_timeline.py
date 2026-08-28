"""Figure 1 — Every Tunisian chamber-term, 1956 to the present.

The frame the whole dataset hangs on. One bar per chamber-term on a single time
axis, so the seventy-year sequence, its interruptions, and the two bicameral
episodes are visible at once.

Form: a horizontal timeline, because the data's job is duration-and-sequence,
not magnitude. Colour does one job only — whether the chamber exists here as
people or merely as an institution — so it is two classes, blue against the
de-emphasis gray, not a rainbow of regime periods. Regime eras are carried by
vertical hairlines and text instead, which keeps the one colour channel for the
one thing a reader of this dataset most needs to know.

Where a chamber was cut short, the bar is drawn to the date it actually stopped
functioning and a lighter tail runs on to the term it should have served. That
is the 2019 ARP's whole story: frozen in July 2021, nominally seated to 2024.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

TODAY = dt.date(2026, 8, 27)

# Era boundaries worth marking. Kept few: a timeline with a line every few years
# is a grid, not an annotation.
ERAS = [
    (dt.date(1957, 7, 25), "Republic\nproclaimed"),
    (dt.date(1987, 11, 7), "Ben Ali\ntakes power"),
    (dt.date(2011, 1, 14), "Revolution"),
    (dt.date(2021, 7, 25), "Parliament\nfrozen"),
]


def parse(value: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    rows = [r for r in S.assemblies_in_order() if r.get("start_date") or r.get("end_date")]

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 6.6))
    blue = S.categorical(1)[0]
    gray = S.CHROME["deemph"]

    table = []
    yticks, ylabels = [], []

    for i, row in enumerate(reversed(rows)):
        start = parse(row["start_date"])
        end = parse(row["end_date"]) or TODAY
        nominal_end = parse(row["nominal_end_date"])
        has_people = row.get("coverage_status") == "full"
        colour = blue if has_people else gray

        if start is None:
            # The Chamber of Advisors has no established first sitting. Rather
            # than invent a start, mark the end with a caret so the row is
            # present and visibly incomplete.
            ax.plot([end], [i], marker="<", markersize=7, color=gray,
                    markeredgecolor=S.CHROME["surface"], markeredgewidth=1.2,
                    linestyle="none")
            ax.annotate("start not established", xy=(end, i),
                        xytext=(-8, 0), textcoords="offset points",
                        ha="right", va="center", fontsize=7,
                        color=S.CHROME["muted"])
        else:
            # the term it should have served, where that differs
            if nominal_end and nominal_end > end:
                ax.barh(i, (nominal_end - end).days, left=end, height=0.52,
                        color=colour, alpha=0.28, linewidth=0)
            ax.barh(i, (end - start).days, left=start, height=0.52,
                    color=colour, linewidth=0)

            seats = row.get("seats_nominal") or ""
            if seats:
                anchor = nominal_end if (nominal_end and nominal_end > end) else end
                ax.annotate(f"{seats}", xy=(anchor, i), xytext=(6, 0),
                            textcoords="offset points", va="center", fontsize=7.6,
                            color=S.CHROME["text_secondary"])

        yticks.append(i)
        ylabels.append(S.label(LBL.assembly(row["assembly_id"])))
        table.append({
            "assembly_id": row["assembly_id"],
            "name_en": row["name_en"],
            "type": row["type"],
            "start_date": row["start_date"],
            "end_date": row["end_date"],
            "nominal_end_date": row["nominal_end_date"],
            "seats_nominal": row["seats_nominal"],
            "regime_period": row["regime_period"],
            "coverage_status": row["coverage_status"],
        })

    for when, text in ERAS:
        ax.axvline(when, color=S.CHROME["axis"], linewidth=0.8, zorder=0)
        ax.annotate(text, xy=(when, len(rows) + 2.25), xytext=(3, 0),
                    textcoords="offset points", ha="left", va="top",
                    fontsize=7, color=S.CHROME["muted"], linespacing=1.25)

    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=8.2)
    ax.set_ylim(-0.9, len(rows) + 2.4)
    ax.set_xlim(dt.date(1954, 1, 1), dt.date(2029, 6, 1))
    S.frame(ax, x_grid=True, y_grid=False)

    S.titles(
        ax,
        "Nineteen chamber-terms, 1956–2026",
        "Bar length is the period actually sat; the faded tail is the term the chamber "
        "was seated for but never served.\nNumbers at the bar end are nominal seats. "
        "Blue = members recorded individually in this dataset; grey = institutional frame only.",
    )
    ax.legend(
        handles=[
            mpatches.Patch(color=blue, label="Person-level roster present"),
            mpatches.Patch(color=gray, label="Institutional frame only"),
        ],
        loc="lower right", bbox_to_anchor=(1.0, -0.13), ncol=2,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/assemblies.csv")
    S.save(fig, "fig01_institutional_timeline", table)


if __name__ == "__main__":
    main()
