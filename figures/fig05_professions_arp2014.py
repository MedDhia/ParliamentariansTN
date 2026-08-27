"""Figure 5 — What the 2014–2019 deputies did before parliament.

Occupation is recorded for 223 of the 246 members of the 2014 chamber, which is
the only near-complete occupational profile in the dataset. (The 2011 chamber has
narrative biographies but a coded profession for only 29 members; the sitting
chamber publishes almost none.)

A horizontal bar chart, sorted, because the category names are long and the job
is ranking magnitudes. One hue for every bar: these are nominal categories, so
shading them by their own length would double-encode the axis and burn the only
free channel.

The tail is folded into one bucket rather than given more colours or a longer
axis. Note what the top of the distribution is: lawyers and teachers, the
professional middle class, with almost no one from agriculture — a chamber drawn
from a narrow social base.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "ARP-2014"
KEEP = 14


def main() -> None:
    persons = {p["person_id"]: p for p in S.load("persons")}
    members = [persons[m["person_id"]] for m in S.load("mandates")
               if m["assembly_id"] == ASSEMBLY]

    raw = Counter()
    n_missing = 0
    for p in members:
        occupation = p["occupation_raw"].strip()
        if not occupation:
            n_missing += 1
            continue
        raw[LBL.profession(occupation)] += 1

    folded = S.fold_to_other(raw, KEEP, other_label="All other categories")
    # Draw largest at the top: a ranked bar chart read top-down should descend.
    folded_for_plot = list(reversed(folded))

    fig, ax = plt.subplots(figsize=S.figsize(7.6, 5.6))
    blue = S.categorical(1)[0]
    gray = S.CHROME["deemph"]

    labels = [S.label(name) for name, _ in folded_for_plot]
    values = [v for _, v in folded_for_plot]
    colours = [gray if name.startswith("All other") else blue
               for name, _ in folded_for_plot]

    bars = ax.barh(labels, values, height=0.66, color=colours, linewidth=0)
    total = sum(raw.values())
    for bar, value in zip(bars, values):
        ax.annotate(f"{value}  ({100.0 * value / total:.0f}%)",
                    xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points",
                    va="center", fontsize=7.6, color=S.CHROME["text_secondary"])

    ax.set_xlim(0, max(values) * 1.28)
    S.frame(ax, x_grid=True, y_grid=False)
    S.titles(
        ax,
        "Occupation before parliament: the 2014–2019 chamber",
        f"Al Bawsala's own occupational categories, glossed into English for display. "
        f"{total} of {len(members)} members coded; "
        f"{n_missing} not recorded.\nThe smallest categories are folded into one bucket "
        "rather than given further colours.",
        xlabel="Members",
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/persons.csv (occupation_raw)")

    S.save(fig, "fig05_professions_arp2014", [
        {"profession_en": name, "members": value,
         "share_of_coded_pct": round(100.0 * value / total, 1)}
        for name, value in folded
    ])


if __name__ == "__main__":
    main()
