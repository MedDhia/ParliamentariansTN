"""Bloc-spell helpers shared by the bloc-dynamics figures.

Bloc membership is stored as dated spells, so two derived views are needed
repeatedly: a month-by-month panel of bloc sizes, and the sequence of moves each
member made. Both are computed here so the three figures that use them cannot
drift apart.

One caveat travels with everything in this module. For the 2014-2019 chamber the
spell boundaries were reconstructed by diffing monthly web captures, so a change
is located only to the interval between two captures — the rows carry
``dates_bracketed``. Monthly resolution is therefore about as fine as the
underlying evidence supports, and anything finer would be false precision.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _labels as LBL  # noqa: E402
import _style as S  # noqa: E402


def _month_start(value: str) -> date | None:
    try:
        d = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return date(d.year, d.month, 1)


def _months(first: date, last: date) -> list[date]:
    out, cur = [], first
    while cur <= last:
        out.append(cur)
        cur = date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
    return out


def spells(assembly_id: str) -> list[dict[str, str]]:
    blocs = {b["bloc_id"]: b for b in S.load("blocs")}
    rows = []
    for r in S.load("bloc_memberships"):
        if r["assembly_id"] != assembly_id:
            continue
        bloc = blocs[r["bloc_id"]]
        rows.append({
            **r,
            "bloc_name_ar": bloc["name_ar"],
            "bloc_label": LBL.bloc(bloc["name_ar"], bloc["name_lat"]),
        })
    return rows


def monthly_panel(assembly_id: str, keep: int = 6) -> tuple[list[date], dict[str, list[int]], dict]:
    """Bloc sizes month by month.

    Returns (months, {bloc_label: counts}, meta). Blocs beyond ``keep`` — ranked
    by peak size, so a bloc that was briefly large is not hidden by one that was
    persistently small — are summed into "Other blocs".
    """
    rows = spells(assembly_id)
    if not rows:
        return [], {}, {}

    starts = [_month_start(r["start_date"]) for r in rows if r["start_date"]]
    ends = [_month_start(r["end_date"]) for r in rows if r["end_date"]]
    first, last = min(starts), max(ends or starts)
    months = _months(first, last)

    # Assign each person to exactly ONE bloc per month. Spell boundaries are
    # bracketed to the interval between captures, so an outgoing spell's end
    # month and the incoming spell's start month are frequently the same month;
    # counting both would double-count that member and push the chamber total
    # above its seat count. Where a person has more than one candidate spell in a
    # month, the one that started most recently wins — that is the bloc they were
    # observed in at that point.
    per_person: dict[tuple[str, int], tuple[str, str]] = {}
    for r in rows:
        start = _month_start(r["start_date"]) or first
        end = _month_start(r["end_date"]) or last
        for i, m in enumerate(months):
            if not (start <= m <= end):
                continue
            key = (r["person_id"], i)
            incumbent = per_person.get(key)
            if incumbent is None or (r["start_date"] or "") >= incumbent[1]:
                per_person[key] = (r["bloc_label"], r["start_date"] or "")

    per_bloc: dict[str, list[int]] = defaultdict(lambda: [0] * len(months))
    for (_, i), (bloc_label, _start) in per_person.items():
        per_bloc[bloc_label][i] += 1

    peak = {name: max(series) for name, series in per_bloc.items()}
    ranked = [name for name, _ in sorted(peak.items(), key=lambda kv: (-kv[1], kv[0]))]
    head, tail = ranked[:keep], ranked[keep:]

    panel = {name: per_bloc[name] for name in head}
    if tail:
        merged = [0] * len(months)
        for name in tail:
            for i, v in enumerate(per_bloc[name]):
                merged[i] += v
        panel["Other blocs"] = merged

    meta = {
        "n_blocs": len(per_bloc),
        "n_folded": len(tail),
        "folded_names": tail,
        "n_spells": len(rows),
        "n_bracketed": sum(1 for r in rows if r["dates_bracketed"] == "true"),
    }
    return months, panel, meta


def effective_number(counts: list[int]) -> float:
    """Laakso-Taagepera effective number of blocs for one month.

    1 / sum(share^2). Reads as "how many equally sized blocs would produce this
    much fragmentation" — 1.0 is a single bloc holding everything.
    """
    total = sum(counts)
    if not total:
        return 0.0
    return 1.0 / sum((c / total) ** 2 for c in counts if c)


def transitions(assembly_id: str) -> tuple[Counter, dict]:
    """Count moves from one bloc to another within a chamber.

    A member's spells are ordered by start date and consecutive pairs are read as
    a move. Spells that merely end at the term's close are not moves.
    """
    rows = spells(assembly_id)
    by_person: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_person[r["person_id"]].append(r)

    moves: Counter = Counter()
    n_switchers = 0
    for person, person_spells in by_person.items():
        ordered = sorted(person_spells, key=lambda r: r["start_date"] or "")
        if len(ordered) < 2:
            continue
        n_switchers += 1
        for a, b in zip(ordered, ordered[1:]):
            moves[(a["bloc_label"], b["bloc_label"])] += 1

    meta = {
        "n_members": len(by_person),
        "n_switchers": n_switchers,
        "n_moves": sum(moves.values()),
    }
    return moves, meta
