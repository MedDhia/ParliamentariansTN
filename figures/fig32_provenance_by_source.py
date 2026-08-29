"""Figure 32 — Which source stands behind which field.

The dataset records provenance at cell level: 5,039 rows saying that this field
of this record came from that source. This is that table drawn — for each
person- or mandate-level field, how many values each source supplied.

It is the figure to read before quoting any single variable. Across the dataset
`name_ar` draws on all five collectors, while `birth_date` draws on one — any
individual cell has exactly one source, but a *field* supported by five
independent collections is a different object from one resting on a single
observatory's biographies. A reader who knows the first fact
and not the second will treat two columns of the same table as equally solid
when they are not, and no amount of caveat text elsewhere fixes that as
efficiently as seeing the bars.

**A tall bar is coverage, not accuracy.** These are counts of values supplied,
so a field can be broadly sourced and still wrong: `gender` for the 2011 chamber
is *inferred* from French grammatical agreement rather than published, and it
appears here at full height because the inference produced a value for every
member. Height answers "how many records have this, and from where", nothing
more.

**Only two tables carry cell-level provenance**, `persons` and `mandates`. The
spell tables — bloc, committee and office memberships, votes, amendments —
record their source on the row itself in a `source_ids` column instead, because
a spell comes from one source as a unit and per-field attribution would repeat
the same identifier across every column. So the absence of, say,
`committee_memberships` here is a design decision, not a gap.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

SOURCE_LABEL = {
    "MARSAD_ANC": "Marsad (2011)",
    "ARP_ODOO": "arp.tn (2023)",
    "MARSAD_ARP2014": "Marsad 2014, archived",
    "MARSAD_MAJLES": "Marsad Majles (2019)",
    "WIKI_AR_ANC1956": "Arabic Wikipedia (1956)",
}


def main() -> None:
    rows = S.load("provenance")
    if not rows:
        raise SystemExit("no provenance rows")

    per_field: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    tables: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        per_field[row["field_name"]][row["source_id"]] += 1
        tables[row["field_name"]].add(row["table_name"])

    totals = collections.Counter({f: sum(c.values()) for f, c in per_field.items()})
    # Sources ordered by overall contribution so the stacks read consistently.
    sources = [s for s, _ in collections.Counter(
        {s: sum(per_field[f][s] for f in per_field)
         for s in {r["source_id"] for r in rows}}).most_common()]
    order = [f for f, _ in totals.most_common()][::-1]
    palette = S.sequential(len(sources), ordinal=True)[::-1]

    fig, ax = plt.subplots(figsize=S.figsize(8.4, 6.2))
    y = np.arange(len(order))
    left = np.zeros(len(order))
    for source, colour in zip(sources, palette):
        widths = np.array([per_field[f][source] for f in order], dtype=float)
        ax.barh(y, widths, left=left, height=0.68, color=colour, zorder=3,
                label=S.label(SOURCE_LABEL.get(source, source)))
        left += widths

    for i, field in enumerate(order):
        n_src = sum(1 for s in sources if per_field[field][s])
        ax.annotate(f"{int(left[i]):,}  ·  {n_src} source{'s' if n_src > 1 else ''}",
                    xy=(left[i], i), xytext=(5, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=7.8,
                    color=S.CHROME["text_secondary"])

    ax.set_yticks(y)
    ax.set_yticklabels(
        [S.label(f"{f}  ({'/'.join(sorted(tables[f]))})") for f in order], fontsize=8)
    ax.set_ylim(-0.7, len(order) - 0.3)
    ax.set_xlim(0, left.max() * 1.22)
    S.frame(ax, x_grid=True, y_grid=False)

    S.titles(
        ax,
        "Names are sourced from all five collectors — birth dates from one",
        f"Cell-level provenance: {len(rows):,} records of which source supplied "
        "which field of which row, across the two tables that carry per-field "
        "attribution.\nThe spell tables — bloc, committee and office "
        "memberships, votes, amendments — record their source on the row instead, "
        "so their absence here is a design\nchoice rather than a gap. Height is "
        "coverage and not accuracy: sex for the 2011 chamber is inferred from "
        "grammatical agreement rather than published,\nand appears at full height "
        "because the inference returned a value for everyone.",
        xlabel="Values supplied",
    )
    ax.legend(loc="lower right", fontsize=8.2)
    S.source_note(fig, "ParliamentariansTN · data/processed/provenance.csv")

    S.save(fig, "fig32_provenance_by_source", [
        {
            "field_name": field,
            "table_name": "/".join(sorted(tables[field])),
            "values": sum(per_field[field].values()),
            "n_sources": sum(1 for s in sources if per_field[field][s]),
            **{s: per_field[field][s] for s in sources},
        }
        for field in reversed(order)
    ])


if __name__ == "__main__":
    main()
