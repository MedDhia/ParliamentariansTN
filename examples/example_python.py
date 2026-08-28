"""Worked example: committee co-membership networks, chamber by chamber.

Runs on the committed data with no dependencies beyond the standard library, so
it works on a fresh clone. It builds its own projection from the bipartite
incidence file rather than reading the pre-made edge list, because that is what
the network guide recommends and because it shows how.

What it reports, in this order:

1. missingness, before any statistic;
2. size, density and degree for each chamber's committee network;
3. Newman's categorical assortativity on parliamentary bloc, region and sex;
4. the coastal/interior comparison, which is the cleavage most likely to matter.

    python examples/example_python.py

If networkx is installed it also cross-checks the density figure, as a guard
against a hand-rolled arithmetic error.
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NETWORKS = ROOT / "data" / "networks"
PROCESSED = ROOT / "data" / "processed"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def project(incidence: list[dict[str, str]], assembly_id: str) -> set[tuple[str, str]]:
    """Unweighted one-mode projection within one chamber, respecting date overlap."""
    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in incidence:
        if row["assembly_id"] == assembly_id:
            by_group[row["committee_id"]].append(row)

    edges: set[tuple[str, str]] = set()
    for members in by_group.values():
        for a, b in combinations(sorted(members, key=lambda r: r["person_id"]), 2):
            if a["person_id"] == b["person_id"]:
                continue
            # spells must intersect; empty bounds are open
            lo = max(a["start_date"] or "0000", b["start_date"] or "0000")
            highs = [x for x in (a["end_date"], b["end_date"]) if x]
            if highs and lo > min(highs):
                continue
            edges.add(tuple(sorted((a["person_id"], b["person_id"]))))
    return edges


def assortativity(edges: set[tuple[str, str]], attr: dict[str, str]) -> tuple[float, int]:
    """Newman's assortativity coefficient for a categorical attribute.

        r = (sum_i e_ii - sum_i a_i b_i) / (1 - sum_i a_i b_i)

    Edges with a missing value on either endpoint are dropped, and the number
    used is returned so the reader can judge how much was thrown away.
    """
    mixing: Counter[tuple[str, str]] = Counter()
    used = 0
    for u, v in edges:
        au, av = attr.get(u, ""), attr.get(v, "")
        if not au or not av:
            continue
        used += 1
        # undirected: count both orientations
        mixing[(au, av)] += 1
        mixing[(av, au)] += 1
    if not used:
        return float("nan"), 0

    total = sum(mixing.values())
    categories = {c for pair in mixing for c in pair}
    e = {pair: n / total for pair, n in mixing.items()}
    a = {c: sum(e.get((c, d), 0.0) for d in categories) for c in categories}

    trace = sum(e.get((c, c), 0.0) for c in categories)
    expected = sum(a[c] * a[c] for c in categories)
    if abs(1 - expected) < 1e-12:
        return float("nan"), used
    return (trace - expected) / (1 - expected), used


def main() -> None:
    incidence = load(NETWORKS / "bipartite_person_committee.csv")
    nodes = {n["person_id"]: n for n in load(NETWORKS / "nodes.csv")}
    bloc_inc = load(NETWORKS / "bipartite_person_bloc.csv")

    bloc_of = {(r["person_id"], r["assembly_id"]): r["bloc_name_ar"] for r in bloc_inc}

    chambers = sorted({r["assembly_id"] for r in incidence})

    print("ParliamentariansTN — committee co-membership networks")
    print("=" * 68)
    print()
    # Counted, not hardcoded: a literal here went stale the moment the 2014
    # chamber was recovered and the dataset grew from 682 people to 856.
    print(f"Missingness across all {len(nodes)} persons in the dataset:")
    for field in ("gender", "birth_year", "governorate_id", "birth_governorate_id",
                  "occupation_raw"):
        n = sum(1 for v in nodes.values() if v.get(field))
        print(f"  {field:24s} {n:4d} / {len(nodes)}  ({100 * n / len(nodes):.0f}%)")
    print()
    print("  Note: governorate_id is the CONSTITUENCY's governorate (where the")
    print("  member was elected); birth_governorate_id is where they are from.")
    print("  These are different variables and are not interchangeable.")
    print()

    for assembly_id in chambers:
        edges = project(incidence, assembly_id)
        people = {p for edge in edges for p in edge}
        n, m = len(people), len(edges)
        density = (2 * m) / (n * (n - 1)) if n > 1 else 0.0

        degree: Counter[str] = Counter()
        for u, v in edges:
            degree[u] += 1
            degree[v] += 1

        print(f"{assembly_id}")
        print("-" * 68)
        print(f"  nodes {n}   edges {m}   density {density:.3f}   "
              f"mean degree {(2 * m / n if n else 0):.1f}")

        bloc_attr = {p: bloc_of.get((p, assembly_id), "") for p in people}
        region_attr = {p: nodes.get(p, {}).get("region", "") for p in people}
        gender_attr = {p: nodes.get(p, {}).get("gender", "") for p in people}

        for label, attr in (("bloc", bloc_attr), ("region", region_attr),
                            ("sex", gender_attr)):
            r, used = assortativity(edges, attr)
            if used == 0:
                print(f"  assortativity by {label:8s} n/a (no edge has the attribute on both ends)")
            else:
                print(f"  assortativity by {label:8s} r = {r:+.3f}   "
                      f"(on {used}/{m} edges)")

        top = degree.most_common(3)
        if top:
            print("  highest degree:")
            for pid, d in top:
                nm = nodes.get(pid, {}).get("name_lat") or pid
                bl = bloc_of.get((pid, assembly_id), "")
                print(f"    {nm:30s} {d:3d}  {bl}")
        print()

    # coastal / interior, pooled over chambers with data
    print("Coastal vs interior representation (constituency governorate)")
    print("-" * 68)
    littoral = Counter()
    for v in nodes.values():
        if v.get("littoral"):
            littoral[v["littoral"]] += 1
    total = sum(littoral.values())
    for key, count in littoral.most_common():
        label = {"true": "coastal", "false": "interior"}.get(key, key)
        print(f"  {label:10s} {count:4d}  ({100 * count / total:.0f}% of {total} with a governorate)")
    print()
    print("  The coastal/interior cleavage is the standard operationalisation of")
    print("  regional inequality in Tunisian politics. Read this alongside")
    print("  docs/COVERAGE.md: it pools three chambers with very different")
    print("  electoral systems, and says nothing about 1959-2011.")

    try:
        import networkx as nx  # noqa: PLC0415
    except ImportError:
        print()
        print("(install networkx to cross-check the density figures)")
        return
    print()
    print("Cross-check with networkx:")
    for assembly_id in chambers:
        edges = project(incidence, assembly_id)
        g = nx.Graph()
        g.add_edges_from(edges)
        print(f"  {assembly_id}: density {nx.density(g):.3f}, "
              f"components {nx.number_connected_components(g)}")


if __name__ == "__main__":
    main()
