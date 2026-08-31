"""Figure 50 — Every career that spans more than one post-2011 chamber.

Figure 9 counts continuity as returning from the chamber *immediately* before,
which is the standard measure and the one that undercounts. Someone who sat in
2014, sat out 2019 and came back in 2023 is "new" by that definition. This
figure counts every career instead, and the correction is not cosmetic: the
2023 chamber has 5 members who sat in 2019 and **10** who sat in some earlier
chamber, so consecutive-only counting halves the continuity in exactly the
chamber whose 3% figure gets quoted.

**Why the map starts in 2011.** The four chambers from 2011 have full rosters,
so a career either appears in them or did not happen. Before that, twelve
chambers between 1959 and 2011 record only their presiding officer, and the
seven multi-chamber careers involving a pre-2011 chamber are *all* presiding
officers — Sadok Mokaddem across five assemblies from 1956, Fouad Mebazaa across
four from 1994. Drawing them beside the post-2011 flows would invite the reading
that elite persistence was higher under the single-party state, when what is
higher is the chance of being recorded: a speaker is the one member of those
chambers this dataset knows. They are excluded from the map and counted in the
table instead.

**One row per career pattern, not per person.** The 78 people with two or more
of these four chambers occupy only eight distinct patterns, so a row per pattern
is exhaustive and a row per person would be 78 near-identical lines. The count
on each row is the people in it, and the eight sum to 78.

**What the shape shows.** Continuity is concentrated in one link. The 2014 → 2019
transition carries 50 of the 78 careers, and 2011 → 2014 carries 31. Then it
stops: only 10 careers reach 2023 at all, and half of those skip a chamber to get
there. The 2021 dissolution and the move to single-member districts did not
thin the returning class so much as change who it was — after 2023 the modal
returner is someone who had already been out of parliament for a term, which the
consecutive measure cannot see by construction.

**What a gap in a row does not mean.** That the member was out of politics. They
may have held office elsewhere, stood and lost, or not stood; this dataset
records parliamentary mandates and nothing else, so a gap is an absence from
these four chambers and not a biography.

**Two further limits.** A person is one identity resolved across sources by name
and, where published, birth date, so a split identity would appear as two
one-chamber members and depress every count here — `docs/COVERAGE.md` reports
the matching. And the 2023 chamber is the sitting one: careers spanning into it
are still open, so its counts are a floor.
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _style as S  # noqa: E402

# The four chambers with a full roster, in order. Continuity is only observable
# where the roster is complete: see the docstring on why 1959-2011 is excluded.
SEQ = ("NCA-2011", "ARP-2014", "ARP-2019", "ARP-2023")
SHORT = {"NCA-2011": "Constituent\n2011", "ARP-2014": "ARP\n2014",
         "ARP-2019": "ARP\n2019", "ARP-2023": "ARP\n2023"}


def careers() -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """person -> chambers sat in, and chamber -> members."""
    held: dict[str, set[str]] = collections.defaultdict(set)
    members: dict[str, set[str]] = collections.defaultdict(set)
    for row in S.load("mandates"):
        held[row["person_id"]].add(row["assembly_id"])
        members[row["assembly_id"]].add(row["person_id"])
    return held, members


def main() -> None:
    held, members = careers()
    if not held:
        raise SystemExit("no mandates recorded; run `make build`")
    order = [a["assembly_id"] for a in S.assemblies_in_order()]
    rank = {a: i for i, a in enumerate(order)}

    # Careers inside the four full-roster chambers, grouped by pattern.
    patterns: dict[tuple[str, ...], list[str]] = collections.defaultdict(list)
    for person, chambers in held.items():
        inside = tuple(c for c in SEQ if c in chambers)
        if len(inside) > 1:
            patterns[inside].append(person)
    if not patterns:
        raise SystemExit("no multi-chamber careers in the post-2011 chambers")

    def gapped(pattern: tuple[str, ...]) -> bool:
        """Did this career sit out a chamber between its first and last?"""
        span = SEQ.index(pattern[-1]) - SEQ.index(pattern[0]) + 1
        return span > len(pattern)

    # Sorted so patterns starting in the same chamber block together, and the
    # gapped ones fall to the bottom of each block rather than being scattered.
    rows = sorted(patterns, key=lambda p: (SEQ.index(p[0]), gapped(p),
                                           SEQ.index(p[-1]), -len(patterns[p])))

    # Per chamber, split the returners the way figure 9 cannot: those who sat in
    # the chamber immediately before, and those who came back after a gap.
    consecutive, after_gap = {}, {}
    for i, chamber in enumerate(SEQ):
        if i == 0:
            consecutive[chamber] = after_gap[chamber] = 0
            continue
        prev = members[SEQ[i - 1]]
        earlier = set().union(*(members[c] for c in order if rank[c] < rank[chamber]))
        returning = members[chamber] & earlier
        consecutive[chamber] = len(members[chamber] & prev)
        after_gap[chamber] = len(returning) - consecutive[chamber]

    # The pre-2011 multi-chamber careers, kept out of the map and counted here.
    pre_2011 = [p for p, chambers in held.items()
                if len(chambers) > 1
                and any(rank[c] < rank[SEQ[0]] for c in chambers)]

    same, gap = S.categorical(2, all_pairs=True)
    fig = plt.figure(figsize=S.figsize(9.4, 6.6))
    grid = fig.add_gridspec(1, 2, width_ratios=(1.0, 0.52), wspace=0.30)
    ax_a, ax_b = fig.add_subplot(grid[0]), fig.add_subplot(grid[1])

    # A — one row per career pattern
    for y, pattern in enumerate(rows):
        colour = gap if gapped(pattern) else same
        xs = [SEQ.index(c) for c in pattern]
        # Draw each consecutive run as its own segment, so a chamber sat out
        # leaves a visible break rather than a line through it.
        run = [xs[0]]
        for x in xs[1:]:
            if x == run[-1] + 1:
                run.append(x)
            else:
                ax_a.plot(run, [y] * len(run), color=colour, linewidth=2.0, zorder=3)
                run = [x]
        ax_a.plot(run, [y] * len(run), color=colour, linewidth=2.0, zorder=3)
        ax_a.scatter(xs, [y] * len(xs), s=46, color=colour, zorder=4,
                     edgecolors=S.CHROME["surface"], linewidths=0.8)
        ax_a.annotate(f"{len(patterns[pattern])}",
                      xy=(len(SEQ) - 0.82, y), fontsize=8.6, ha="left", va="center",
                      color=S.CHROME["text_primary"], zorder=5)
    # Column heading, above the first count: the y axis is inverted, so the
    # smallest coordinate is the top row.
    ax_a.annotate(S.label("people"), xy=(len(SEQ) - 0.82, -0.5),
                  fontsize=8.0, ha="left", va="center",
                  color=S.CHROME["text_secondary"])
    ax_a.set_xlim(-0.45, len(SEQ) - 0.30)
    ax_a.set_ylim(-0.9, len(rows) - 0.4)
    ax_a.set_xticks(range(len(SEQ)))
    ax_a.set_xticklabels([S.label(SHORT[c]) for c in SEQ], fontsize=8.2)
    ax_a.set_yticks([])
    ax_a.invert_yaxis()
    S.frame(ax_a, x_grid=True, y_grid=False)
    ax_a.set_title(S.label(f"A · The {len(rows)} career patterns that span more "
                           f"than one chamber"),
                   loc="left", fontsize=9.6, color=S.CHROME["text_primary"], pad=6)
    ax_a.legend(handles=[
        mlines.Line2D([], [], color=same, linewidth=2.4, marker="o",
                      label=S.label("Consecutive chambers")),
        mlines.Line2D([], [], color=gap, linewidth=2.4, marker="o",
                      label=S.label("Returned after sitting one out")),
    ], loc="lower left", fontsize=8.2, framealpha=0.92)

    # B — the two ways of counting a returner
    ys = range(1, len(SEQ))
    labels = [SEQ[i] for i in ys]
    base = [consecutive[c] for c in labels]
    extra = [after_gap[c] for c in labels]
    ax_b.barh(list(ys), base, height=0.55, color=same, zorder=3,
              label=S.label("Sat in the chamber before"))
    ax_b.barh(list(ys), extra, height=0.55, left=base, color=gap, zorder=3,
              label=S.label("Returned after a gap"))
    for y, c in zip(ys, labels):
        total = consecutive[c] + after_gap[c]
        share = total / len(members[c])
        note = f"{consecutive[c]}" + (f" + {after_gap[c]}" if after_gap[c] else "")
        ax_b.annotate(f"{note}  ({share:.0%} of {len(members[c])})",
                      xy=(total, y), xytext=(6, 0), textcoords="offset points",
                      ha="left", va="center", fontsize=8.2,
                      color=S.CHROME["text_primary"], zorder=4)
    ax_b.set_yticks(list(ys))
    ax_b.set_yticklabels([S.label(SHORT[c].replace("\n", " ")) for c in labels],
                         fontsize=8.2)
    ax_b.invert_yaxis()
    ax_b.set_xlim(0, max(consecutive[c] + after_gap[c] for c in labels) * 1.95)
    ax_b.set_xlabel(S.label("Members with earlier service"), fontsize=8.4)
    S.frame(ax_b, x_grid=True, y_grid=False)
    ax_b.set_title(S.label("B · Figure 9 counts only the first bar"),
                   loc="left", fontsize=9.6, color=S.CHROME["text_primary"], pad=6)

    total_people = sum(len(v) for v in patterns.values())
    last = SEQ[-1]
    fig.subplots_adjust(left=0.035, right=0.985, top=0.775, bottom=0.095)
    fig.text(0.010, 0.985,
             "Continuity runs through one link, and the 2023 chamber's returners "
             "mostly skipped a term",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.010, 0.948,
        f"Every career spanning more than one of Tunisia's four full-roster "
        f"chambers: {total_people} people in {len(rows)} distinct patterns, which "
        f"is all of them. A dot is a chamber sat in, a line joins\nconsecutive "
        f"ones, and a break is a chamber sat out. Figure 9 counts a returner only "
        f"if they sat in the chamber immediately before, which is the standard "
        f"measure and the one that\nundercounts: {last} has "
        f"{consecutive[last]} members who sat in {SHORT[SEQ[-2]].replace(chr(10), ' ')} "
        f"and {consecutive[last] + after_gap[last]} who sat in some earlier chamber, "
        f"so consecutive-only counting halves it. The 2014 → 2019 link carries "
        f"{consecutive['ARP-2019']}\nof the {total_people} careers and 2011 → 2014 "
        f"carries {consecutive['ARP-2014']}; then it stops. The map starts in 2011 "
        f"because the twelve chambers between 1959 and 2011 record only their "
        f"presiding officer, and\nall {len(pre_2011)} multi-chamber careers touching "
        f"them are presiding officers — persistence that is really a fact about who "
        f"got recorded, so they are excluded here. A gap in a row means absent from "
        f"these\nfour chambers, not out of politics; and 2023 is the sitting "
        f"chamber, so careers reaching it are still open and its counts are a floor.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · data/processed/mandates.csv")

    table = []
    for pattern in rows:
        table.append({
            "series": "career_pattern",
            "pattern": " → ".join(pattern),
            "people": len(patterns[pattern]),
            "chambers": len(pattern),
            "sat_out_a_chamber": gapped(pattern),
            "consecutive_returners": "", "gap_returners": "", "members": "",
        })
    for chamber in SEQ[1:]:
        table.append({
            "series": "returners_by_chamber", "pattern": chamber, "people": "",
            "chambers": "", "sat_out_a_chamber": "",
            "consecutive_returners": consecutive[chamber],
            "gap_returners": after_gap[chamber],
            "members": len(members[chamber]),
        })
    table.append({
        "series": "excluded", "pattern": "multi-chamber careers touching a "
                                         "pre-2011 chamber (presiding officers only)",
        "people": len(pre_2011), "chambers": "", "sat_out_a_chamber": "",
        "consecutive_returners": "", "gap_returners": "", "members": "",
    })
    S.save(fig, "fig50_elite_continuity_nca_arp", table)


if __name__ == "__main__":
    main()
