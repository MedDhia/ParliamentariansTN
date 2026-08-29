"""Shared machinery for the polarisation figures (33-40).

Five of them read the same objects — the vote-agreement dyads, a bloc label per
member, and an E-I index — so those live here rather than being rebuilt eight
times with eight chances to diverge.

**What "polarisation" means in these figures.** Not distance between party
platforms, which this dataset has no measure of, but the degree to which the
lines a chamber divides on coincide with its bloc boundaries. A chamber where
members agree with their own bloc and disagree with everyone else is polarised
in this sense; one where agreement cuts across blocs is not, whatever the
rhetoric outside the chamber. Every figure here operationalises that in a
different way, and where they disagree the disagreement is the finding.

**The size trap, and why the null matters.** Every count-based network measure
of homophily is bounded by group size. A ten-member bloc in a 217-member chamber
has 45 possible internal ties and 2,070 external ones, so its E-I index is near
+1 before any politics enters; a bloc of 87 can be internally dense at no
particular cost. Comparing raw E-I across blocs of different sizes therefore
compares arithmetic, not behaviour. `ei_null` shuffles bloc labels while holding
the sizes fixed, which is the benchmark that makes the comparison legitimate.
"""

from __future__ import annotations

import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _network as NET  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
# A "tie" in the agreement graph. 0.75 is a choice, not a discovery: it sits
# above the chamber-wide mean of 0.72 on contested divisions, so a tie means
# "agrees more than the average pair does". Figures that depend on it show the
# sensitivity rather than asking the reader to trust the number.
TIE_THRESHOLD = 0.75


def agreement_dyads(assembly_id: str = ASSEMBLY) -> list[tuple[str, str, float, int]]:
    """(source, target, agreement, shared divisions) for every scored pair."""
    return [
        (r["source"], r["target"], float(r["weight"]), int(r["shared_count"]))
        for r in S.load("edges_vote_agreement")
        if r["assembly_id"] == assembly_id
    ]


def blocs(assembly_id: str = ASSEMBLY) -> dict[str, str]:
    return NET._bloc_of(assembly_id)


def ei_index(members: set[str], dyads) -> tuple[int, int, float]:
    """Krackhardt-Stern E-I: (external - internal) / (external + internal).

    −1 is a group whose every tie is internal, +1 one whose every tie leaves it.
    Returns the two counts as well, because the index alone hides whether it
    rests on twenty ties or two thousand.
    """
    internal = external = 0
    for a, b, *_ in dyads:
        in_a, in_b = a in members, b in members
        if in_a and in_b:
            internal += 1
        elif in_a or in_b:
            external += 1
    total = internal + external
    return internal, external, (external - internal) / total if total else float("nan")


def ei_null(sizes: dict[str, int], dyads, everyone: list[str],
            draws: int = 400, seed: int = 20260829) -> dict[str, list[float]]:
    """E-I for each bloc under randomly reassigned labels of the same sizes.

    Holding the size distribution fixed is the whole point: it isolates whatever
    is left once the arithmetic of "small groups have few internal pairs" is
    accounted for. The observed value is interesting only against this.
    """
    rng = random.Random(seed)
    pool = sorted(everyone)
    out: dict[str, list[float]] = collections.defaultdict(list)
    for _ in range(draws):
        shuffled = pool[:]
        rng.shuffle(shuffled)
        cursor = 0
        for bloc, n in sorted(sizes.items()):
            members = set(shuffled[cursor:cursor + n])
            cursor += n
            out[bloc].append(ei_index(members, dyads)[2])
    return dict(out)


def ties(dyads, threshold: float = TIE_THRESHOLD) -> list[tuple[str, str, float, int]]:
    return [d for d in dyads if d[2] >= threshold]


def label_of(bloc: str, sizes: collections.Counter, cap: int = 2) -> str:
    """Fold to the ``cap`` largest blocs plus 'Other blocs', for colour."""
    top = [b for b, _ in sizes.most_common(cap)]
    return bloc if bloc in top else "Other blocs"
