"""Is the 2011 chamber's voting axis anything more than Ennahdha membership?

Figure 21 scales the 2011 Constituent Assembly's roll-call record and finds a
first dimension that separates Ennahdha from every other bloc. This script asks
the sceptical question that finding invites, and prints the numbers quoted in
`docs/FINDINGS.md` §6.

    python examples/voting_space.py        # needs numpy; nothing else

**Why the question is sharp.** Ennahdha held 87 of 217 seats and voted
cohesively. A principal component is the direction of greatest variance in the
member × division matrix, and a large cohesive bloc *is* a large source of
variance — so a leading component that lines up with that bloc is partly
arithmetic, not a discovery. If the axis were nothing but membership re-expressed
as a number, then every statement of the form "bloc X sits on the far side of it
from Ennahdha" would be a restatement of "X is not Ennahdha", and worthless.

**Two checks separate the cases.**

1. *How much of the axis is membership?* Regress the first dimension on an
   Ennahdha dummy. R² is the share of the spread that membership alone accounts
   for; 1 − R² is what it cannot produce, including all within-bloc dispersion.
2. *Does anything survive its removal?* Drop all 87 Ennahdha members, re-filter
   the divisions to those contested among the remaining 130 — otherwise votes
   that were only contested because Ennahdha opposed them come through as
   near-unanimous noise — and rescale from scratch. If the residual structure is
   a coherent ordering of the other blocs rather than noise, the chamber's
   voting space has more than one dimension of content.

**Caveats inherited from the scaling itself**, all of them stated on figure 21:
pour is +1, contre is −1, and abstention, absence and non-listing are all 0,
which pulls frequent abstainers toward the centre and conflates being away with
being present and not voting. Near-unanimous divisions are dropped because a
division everyone agrees on locates nobody. This is a singular value
decomposition, not NOMINATE or an IRT model — no error model, no bootstrap, no
claim that a coordinate is a latent ideal point. The sign of any component is
arbitrary; read orderings and gaps, never which end is positive.
"""

from __future__ import annotations

import collections
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSEMBLY = "NCA-2011"
MIN_CAST = 40         # divisions with fewer recorded pour/contre are dropped
MIN_MINORITY = 0.025  # and so are near-unanimous ones
MIN_MEMBER_VOTES = 30


def load(name: str) -> list[dict[str, str]]:
    directory = "networks" if name.startswith(("edges_", "nodes", "bipartite_")) else "processed"
    with (ROOT / "data" / directory / f"{name}.csv").open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def matrix() -> tuple[list[str], list[str], np.ndarray]:
    """The member × division matrix, pour +1 / contre −1 / everything else 0."""
    positions: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for row in load("vote_positions"):
        if row["assembly_id"] == ASSEMBLY:
            positions[row["person_id"]][row["vote_id"]] = row["position"]
    votes = [v["vote_id"] for v in load("votes") if v["assembly_id"] == ASSEMBLY]
    index = {v: j for j, v in enumerate(votes)}

    people = sorted(positions)
    m = np.zeros((len(people), len(votes)))
    for i, person in enumerate(people):
        for vote_id, position in positions[person].items():
            if position == "pour":
                m[i, index[vote_id]] = 1.0
            elif position == "contre":
                m[i, index[vote_id]] = -1.0

    # A member's last recorded spell, which for this chamber is their bloc at the
    # end of the term. Names are the source's own French forms, so they read
    # "Mouvement Nahdha" and "Aucun bloc" rather than figure 21's English glosses
    # — this script deliberately has no dependency on the figures package.
    names = {b["bloc_id"]: (b["name_lat"] or b["name_ar"]) for b in load("blocs")}
    latest: dict[str, tuple[str, str]] = {}
    for row in load("bloc_memberships"):
        if row["assembly_id"] != ASSEMBLY:
            continue
        start = row["start_date"] or ""
        if row["person_id"] not in latest or start >= latest[row["person_id"]][0]:
            latest[row["person_id"]] = (start, names[row["bloc_id"]])
    return people, [latest.get(p, ("", "Not recorded"))[1] for p in people], m


def scale(m: np.ndarray, rows: list[int]) -> tuple[list[int], np.ndarray, np.ndarray, int]:
    """Filter to divisions contested *within these members*, then decompose.

    Re-filtering matters: the contested set is a property of who is voting. Keep
    the whole chamber's filter after removing a bloc and you carry divisions that
    were only contested because that bloc opposed them, which is noise once it is
    gone.
    """
    sub = m[rows]
    cast = (sub != 0).sum(axis=0)
    minority = np.minimum((sub == 1).sum(axis=0), (sub == -1).sum(axis=0))
    minority = minority / np.maximum(cast, 1)
    keep_votes = np.where((cast >= MIN_CAST) & (minority >= MIN_MINORITY))[0]
    sub = sub[:, keep_votes]

    keep_people = np.where((sub != 0).sum(axis=1) >= MIN_MEMBER_VOTES)[0]
    sub = sub[keep_people]
    centred = sub - sub.mean(axis=0)
    u, s, _ = np.linalg.svd(centred, full_matrices=False)
    return ([rows[i] for i in keep_people], u[:, :2] * s[:2],
            s ** 2 / (s ** 2).sum(), len(keep_votes))


def report(blocs: list[str], kept: list[int], coords: np.ndarray) -> None:
    means: dict[str, list[float]] = collections.defaultdict(list)
    for i, row in enumerate(kept):
        means[blocs[row]].append(float(coords[i, 0]))
    for bloc, xs in sorted(means.items(), key=lambda kv: -np.mean(kv[1])):
        print(f"    {np.mean(xs):+7.2f}  (n={len(xs):3d})  {bloc}")


def main() -> None:
    people, blocs, m = matrix()
    largest = collections.Counter(blocs).most_common(1)[0][0]

    print("=" * 78)
    print(f"The voting space of {ASSEMBLY}: is dimension 1 just {largest} membership?")
    print("=" * 78)

    kept, coords, share, n_votes = scale(m, list(range(len(people))))
    # Orient so the largest bloc sits positive; the sign of a component is
    # arbitrary and this only makes the printout stable across runs.
    if np.mean([coords[i, 0] for i, r in enumerate(kept) if blocs[r] == largest]) < 0:
        coords[:, 0] *= -1

    print(f"\n── the whole chamber ──")
    print(f"  {len(kept)} members × {n_votes} contested divisions")
    print(f"  dimension 1 = {share[0]:.1%} of variance, dimension 2 = {share[1]:.1%}")
    report(blocs, kept, coords)

    dummy = np.array([1.0 if blocs[r] == largest else 0.0 for r in kept])
    r = float(np.corrcoef(coords[:, 0], dummy)[0, 1])
    print(f"\n  corr(dimension 1, '{largest}' dummy) = {r:+.3f}, R² = {r ** 2:.3f}")
    print(f"  → membership accounts for {r ** 2:.0%} of the spread along the axis;")
    print(f"    {1 - r ** 2:.0%} is something membership alone cannot produce.")

    rest = [i for i in range(len(people)) if blocs[i] != largest]
    kept2, coords2, share2, n_votes2 = scale(m, rest)
    print(f"\n── {largest} removed, the rest rescaled from scratch ──")
    print(f"  {len(kept2)} members × {n_votes2} divisions contested among them")
    print(f"  dimension 1 = {share2[0]:.1%} of variance, dimension 2 = {share2[1]:.1%}")
    report(blocs, kept2, coords2)

    print()
    print("=" * 78)
    print("A coherent ordering here means the chamber was not one-dimensional: one")
    print("strong cleavage with real structure underneath it, rather than a single")
    print("axis of who was and was not in the governing bloc. The sign is arbitrary")
    print("— read the ordering and the gaps, never which end is positive. See the")
    print("docstring for what this decomposition is not.")


if __name__ == "__main__":
    main()
