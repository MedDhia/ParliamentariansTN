"""Figure 24 — When the 2011 Constituent Assembly actually voted.

Recorded divisions per month, July 2012 to September 2014. The assembly was
elected in October 2011, so nine months passed before its first recorded
division, and two-thirds of its entire voting record falls in just three months:
December 2013, January 2014 and April 2014.

That shape is the constitution-drafting process made visible. The chamber spent
its first year in committee and in the crisis that followed the Belaïd and
Brahmi assassinations; the article-by-article votes on the constitution are the
December-January peak, and it was adopted on 26 January 2014. The April spike is
after adoption — the electoral law and the legislative business the assembly had
deferred while it wrote the constitution.

**The gap at the start is a source boundary as much as a political fact.** These
are the divisions Marsad recorded, and its coverage begins in July 2012. Whether
the assembly held earlier recorded votes that the observatory did not capture is
not answerable from this data, so the empty months are drawn as empty rather
than omitted — a reader can see exactly where the record starts and decide what
to make of it. Read this as the shape of the *recorded* voting series, not as
proof that nothing was voted on before July 2012.
"""

from __future__ import annotations

import collections
import sys
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
ELECTED = date(2011, 10, 23)
ADOPTED = date(2014, 1, 26)  # the constitution's adoption vote


def _months(first: date, last: date) -> list[date]:
    out, cur = [], first
    while cur <= last:
        out.append(cur)
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
    return out


def main() -> None:
    per_month: collections.Counter[date] = collections.Counter()
    for row in S.load("votes"):
        if row["assembly_id"] != ASSEMBLY or not row["vote_date"]:
            continue
        y, m, _ = row["vote_date"].split("-")
        per_month[date(int(y), int(m), 1)] += 1
    if not per_month:
        raise SystemExit(f"no dated divisions for {ASSEMBLY}")

    # Start the axis at the election, not at the first division, so the silent
    # opening months are visible rather than cropped away.
    axis = _months(date(ELECTED.year, ELECTED.month, 1), max(per_month))
    counts = [per_month.get(m, 0) for m in axis]

    fig, ax = plt.subplots(figsize=S.figsize(8.4, 4.4))
    bar, accent = S.categorical(2, all_pairs=True)
    ax.bar(axis, counts, width=24, color=bar, zorder=3)

    ax.axvline(ADOPTED, color=accent, linewidth=1.6, zorder=4)
    # The bars either side of the adoption date are the two tallest on the
    # chart, so the label goes out into the empty left half on a leader line
    # rather than on top of the peak it is describing.
    ax.annotate(
        "Constitution adopted\n26 January 2014",
        xy=(ADOPTED, max(counts) * 0.86), xytext=(date(2012, 10, 1), max(counts) * 0.86),
        ha="left", va="center", fontsize=8, color=S.CHROME["text_secondary"],
        arrowprops={"arrowstyle": "-", "color": S.CHROME["axis"], "linewidth": 0.8},
        zorder=5,
    )

    first = min(per_month)
    silent = sum(1 for m in axis if m < first)
    ax.annotate(
        f"{silent} months from the election\nwith no division in the record",
        xy=(axis[silent // 2], max(counts) * 0.62), ha="center", va="center",
        fontsize=8, color=S.CHROME["muted"],
    )

    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 7)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    S.frame(ax)
    S.integer_axis(ax)
    S.titles(
        ax,
        "Two-thirds of the assembly's recorded votes fall in three months",
        f"Recorded divisions per month, 2011 Constituent Assembly: "
        f"{sum(counts):,} across {sum(1 for c in counts if c)} months with any "
        "vote. The axis starts at the October 2011 election,\nso the months "
        "before the record begins are shown as empty rather than cropped. That "
        "opening gap is a property of the source as much as of the chamber: "
        "these\nare the divisions Al Bawsala recorded, and its series starts in "
        "July 2012. Whether earlier recorded votes existed and went uncaptured "
        "is not answerable here.",
        ylabel="Recorded divisions",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/votes.csv")

    S.save(fig, "fig24_voting_calendar_nca2011", [
        {"month": m.isoformat()[:7], "divisions": c,
         "before_record_starts": m < first}
        for m, c in zip(axis, counts)
    ])


if __name__ == "__main__":
    main()
