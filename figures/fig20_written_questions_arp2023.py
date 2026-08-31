"""Figure 20 — Written questions filed, chamber elected in 2023.

Oversight activity, and the most unequal distribution in the dataset: the busiest
few deputies account for a large share of it while others file almost none.

A counting note, because two totals in this repository look contradictory and are
not. The chamber's database holds 6,332 distinct written questions, and that is
the number figure 18 builds its co-signature network from. Summing this figure's
per-deputy counts gives 6,603, because 78 of those questions carry more than one
signatory and each signer is credited with filing it. The bars here are per-deputy
filings — signatures, not distinct questions — which is the right unit for
comparing how actively individual members use the instrument.

Form: a ranked horizontal bar of the twenty most active, plus a note carrying the
rest. One hue — these are nominal categories and shading by value would
double-encode the axis. The full distribution is in the companion CSV.

Written questions are the one oversight instrument an individual deputy can use
without anyone's permission, which makes the spread a reasonable proxy for how
differently members interpret the job.
"""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2023"
TOP = 20


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    rows = []
    for r in S.load("participation"):
        if r["assembly_id"] != ASSEMBLY:
            continue
        n = S.num(r["n_written_questions"])
        if n is None:
            continue
        rows.append((r["person_id"], int(n)))

    rows.sort(key=lambda t: -t[1])
    total = sum(n for _, n in rows)
    top = rows[:TOP]
    top_share = 100.0 * sum(n for _, n in top) / total
    median = statistics.median(n for _, n in rows)

    fig, ax = plt.subplots(figsize=S.figsize(7.4, 6.0))
    blue = S.categorical(1)[0]

    labels = [S.label(LBL.person_name(persons.get(pid, {}).get("name_lat", "")) or pid)
              for pid, _ in top]
    values = [n for _, n in top]
    bars = ax.barh(list(reversed(labels)), list(reversed(values)),
                   height=0.68, color=blue, linewidth=0)
    for bar, value in zip(bars, reversed(values)):
        ax.annotate(f"{value}", xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points", va="center",
                    fontsize=7.6, color=S.CHROME["text_secondary"])

    ax.axvline(median, color=S.CHROME["muted"], linewidth=1.0, zorder=3)
    ax.annotate(f"chamber median: {median:.0f}", xy=(median, -0.9), xytext=(4, 0),
                textcoords="offset points", ha="left", va="bottom", fontsize=7.4,
                color=S.CHROME["muted"])

    ax.set_xlim(0, max(values) * 1.14)
    S.frame(ax, x_grid=True, y_grid=False)
    S.titles(
        ax,
        "Twenty of 154 deputies file 42% of the chamber's written questions",
        f"{total:,} filings by {len(rows)} deputies in the chamber elected in 2023. "
        f"These twenty account for {top_share:.0f}% of them;\nthe median deputy filed "
        f"{median:.0f}. Counted per signer, so the 78 jointly signed questions are "
        "credited to each\nsignatory — hence more filings than the 6,332 distinct "
        "questions behind figure 18.",
        xlabel="Written questions",
    )
    S.source_note(fig, "ParliamentariansTN · participation.csv (from arp.tn)")

    S.save(fig, "fig20_written_questions_arp2023", [
        {"rank": i + 1, "person_id": pid,
         "name_lat": persons.get(pid, {}).get("name_lat", ""),
         "written_questions": n}
        for i, (pid, n) in enumerate(rows)
    ])


if __name__ == "__main__":
    main()
