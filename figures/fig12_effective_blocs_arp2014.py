"""Figure 12 — Fragmentation of the 2014–2019 chamber as a single number.

Figure 11 shows every band; this reduces the same panel to one quantity — the
Laakso–Taagepera effective number of blocs, 1 / Σ shareᵢ². It reads as "how many
equally sized blocs would produce this much fragmentation", so 1.0 would be a
single bloc holding every seat.

One series, so one line and no legend. Deliberately a separate figure rather than
a second axis on figure 11: two y-scales on one plot invent a relationship
between them that is not in the data, and the alignment of the two scales would
be arbitrary.

The chamber begins at 3.6 effective blocs — already fragmented for a parliament
produced by a two-party contest — and climbs to 5.3, the whole of the rise coming
from Nidaa Tounes splitting. Fragmentation here is not an artefact of small blocs
appearing at the margins: it is the largest bloc dissolving.

The series rises monotonically enough that its peak is its final month, so the
peak callout is suppressed rather than duplicating the end label.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blocs as BL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2014"


def main() -> None:
    # keep=None equivalent: use every bloc, unfolded, or the index is wrong —
    # folding small blocs into one bucket would understate fragmentation.
    months, panel, meta = BL.monthly_panel(ASSEMBLY, keep=99)
    if not months:
        raise SystemExit(f"no bloc spells for {ASSEMBLY}")

    series = []
    for i in range(len(months)):
        counts = [panel[name][i] for name in panel]
        series.append(BL.effective_number(counts))

    fig, ax = plt.subplots(figsize=S.figsize(7.8, 4.2))
    blue = S.categorical(1)[0]
    ax.plot(months, series, color=blue, linewidth=2.0, solid_capstyle="round")
    ax.fill_between(months, series, color=blue, alpha=0.10, linewidth=0)

    # Direct-label the two ends only. Anchor each label inward from its own end:
    # centring them puts half of the first label outside the axes, where the
    # tight-bbox render clips it against the y-axis.
    last = len(months) - 1
    for idx, ha, dx in ((0, "left", 2), (last, "right", -2)):
        ax.annotate(f"{series[idx]:.1f}", xy=(months[idx], series[idx]),
                    xytext=(dx, 8), textcoords="offset points", ha=ha, va="bottom",
                    fontsize=8.6, fontweight="bold", color=S.CHROME["text_primary"])

    # Call out the peak only when it is somewhere a reader would otherwise miss
    # it. Test the value, not the index: this series climbs to its maximum and
    # then plateaus, so argmax lands mid-series while the peak value is also the
    # final value — a callout there would just restate the end label at a
    # different date, implying a fall that never happens.
    peak = max(range(len(months)), key=lambda i: series[i])
    plateau = abs(series[peak] - series[last]) < 0.05
    if 2 <= peak <= last - 3 and not plateau:
        ax.annotate(
            f"peak {series[peak]:.1f} effective blocs\n({months[peak]:%b %Y})",
            xy=(months[peak], series[peak]), xytext=(-10, -34),
            textcoords="offset points", ha="right", va="top", fontsize=7.6,
            color=S.CHROME["text_secondary"], linespacing=1.35,
            arrowprops=dict(arrowstyle="-", color=S.CHROME["axis"], linewidth=0.8,
                            shrinkA=0, shrinkB=5),
        )
    else:
        ax.annotate(
            f"rises from {series[0]:.1f} to {series[last]:.1f} over the term",
            xy=(0.5, 0.06), xycoords="axes fraction", ha="center", fontsize=7.6,
            color=S.CHROME["text_secondary"],
        )

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(months[0], months[-1])
    ax.set_ylim(0, max(series) * 1.25)
    S.frame(ax)
    S.titles(
        ax,
        "Effective number of parliamentary blocs, 2014–2019 chamber",
        "Laakso–Taagepera index, 1 / Σ share². Computed over all "
        f"{meta['n_blocs']} blocs — unfolded, since grouping the small ones\nwould "
        "understate fragmentation. Monthly resolution, from bracketed spells: read the "
        "trend, not individual months.",
        ylabel="Effective number of blocs",
    )
    S.source_note(fig, "ParliamentariansTN · bloc_memberships.csv × blocs.csv")

    S.save(fig, "fig12_effective_blocs_arp2014", [
        {"month": m.isoformat()[:7],
         "effective_number_of_blocs": round(v, 3),
         "blocs_with_members": sum(1 for name in panel if panel[name][i] > 0),
         "members_assigned": sum(panel[name][i] for name in panel)}
        for i, (m, v) in enumerate(zip(months, series))
    ])


if __name__ == "__main__":
    main()
