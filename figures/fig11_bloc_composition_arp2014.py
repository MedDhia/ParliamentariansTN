"""Figure 11 — The 2014–2019 chamber pulling itself apart, month by month.

This is the figure that only exists because the term was recovered from web
archives: roughly 29 monthly captures survive, and diffing them turns bloc
membership into dated spells. No other Tunisian chamber can be drawn this way.

Form: a stacked area over time, because the job is part-to-whole *and* change —
how the same 217 seats redistribute across blocs. Seven series, which is inside
the eight-slot ceiling for stacked forms, so the tail is folded into one bucket
rather than given more hues. Direct labels are mandatory past four series and are
placed at each band's widest point.

What it shows is the collapse of the winning coalition. Nidaa Tounes enters with
86 seats — the largest bloc, having just won the election — and bleeds members
continuously: first into Al Horra in early 2016, then into the Machrouu Tounes
bloc that December, while the National Coalition assembles in 2017 out of the
pieces. By the end of the term the chamber's largest bloc is no longer the party
that won it.

Because the spell boundaries are bracketed to the interval between captures, the
month at which a band steps is accurate to within about a month, not to the day.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _blocs as BL  # noqa: E402
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2014"
KEEP = 6


def main() -> None:
    months, panel, meta = BL.monthly_panel(ASSEMBLY, keep=KEEP)
    if not months:
        raise SystemExit(f"no bloc spells for {ASSEMBLY}")

    # Largest first at the bottom of the stack, "Other" always last, so the
    # baseline band is stable and the eye can follow it.
    names = [n for n in panel if n != "Other blocs"]
    names.sort(key=lambda n: -max(panel[n]))
    if "Other blocs" in panel:
        names.append("Other blocs")

    colours = S.categorical(len(names))
    if names and names[-1] == "Other blocs":
        colours[-1] = S.CHROME["deemph"]

    fig, ax = plt.subplots(figsize=S.figsize(8.2, 4.9))
    stacks = ax.stackplot(
        months, [panel[n] for n in names],
        colors=colours, labels=[S.label(n) for n in names],
        linewidth=0.8, edgecolor=S.CHROME["surface"],  # 2px surface gap between fills
    )

    # Direct-label each band at its widest month, but only where the band is tall
    # enough to hold text — otherwise the legend carries it.
    cumulative = [0] * len(months)
    for name, colour in zip(names, colours):
        series = panel[name]
        # Keep the label off the axes edges: a band whose widest month is the
        # first or last would otherwise have its label half outside the plot.
        margin = max(2, len(months) // 12)
        candidates = range(margin, max(margin + 1, len(months) - margin))
        widest = max(candidates, key=lambda i: series[i])
        centre = cumulative[widest] + series[widest] / 2
        if series[widest] >= 16:
            ax.annotate(
                S.label(name), xy=(months[widest], centre), ha="center", va="center",
                fontsize=7.8, color="#ffffff" if name != "Other blocs"
                else S.CHROME["text_secondary"], zorder=5,
            )
        for i, v in enumerate(series):
            cumulative[i] += v

    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlim(months[0], months[-1])
    ax.set_ylim(0, max(cumulative) * 1.06)
    S.frame(ax)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=4, fontsize=7.6)
    S.titles(
        ax,
        "The 2014 election winner did not end as the largest bloc",
        f"Each band is one parliamentary bloc, its height the members it held that month, "
        f"across the 2014–2019 chamber.\nNidaa Tounes enters with 86 seats having just won "
        f"the election, and bleeds continuously into Al Horra, then\nMachrouu Tounes, while "
        f"the National Coalition assembles out of the pieces.\nReconstructed from ~29 "
        f"monthly Internet Archive captures into "
        f"{meta['n_spells']} dated bloc spells. Every boundary is bracketed to the\n"
        f"interval between two captures, so a step is accurate to about a month, not to "
        f"the day. {meta['n_blocs']} blocs existed; the {meta['n_folded']}\nsmallest are "
        "folded into one band. The total sits at 212–220 against 217 seats — that spread "
        "is the reconstruction's error.",
        ylabel="Members",
    )
    S.source_note(
        fig, "ParliamentariansTN · bloc_memberships.csv × blocs.csv  ·  Internet Archive "
             "captures of majles.marsad.tn/2014", y=-0.075)

    table = []
    for i, month in enumerate(months):
        for name in names:
            table.append({
                "month": month.isoformat()[:7],
                "bloc": name,
                "members": panel[name][i],
            })
    S.save(fig, "fig11_bloc_composition_arp2014", table)


if __name__ == "__main__":
    main()
