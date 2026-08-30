"""Figure 46 — Did cooperation erode in the 2011 assembly? Two measures, quarter by quarter.

Elizabeth Nugent's *After Repression* (2020) argues that Tunisia's transition
survived because its opposition entered it comparatively **unpolarised** —
Ben Ali's repression having fallen indiscriminately on Islamists and secularists
alike, where Egypt's fell narrowly on the Brotherhood — and that the low
perceived distance between those groups is what made a negotiated constitution
possible. The argument is about elite perceptions, measured by interview and
survey. It is not about roll calls.

What roll calls can do is check an observable implication: if the chamber that
produced the 2014 constitution was genuinely, not merely procedurally, working
across the Islamist/secular line, cooperation there should be high and should
**not erode** across the term. A transition that consensus-ed on paper while its
legislature hardened into two camps would be a problem for the account.

**Two measures, and why neither uses bloc labels for its headline.** This
chamber's bloc data is undated — one spell per member covering the whole term —
while 105 of 217 members changed party (figure 28). Any within/cross bloc series
is therefore scored against an end-of-term map (figure 38 says so and reports one
anyway). Both measures here avoid that, in different ways:

*Cross-cutting wins* (panel A) asks, per contested division, whether the winning
side was carried by more than half of the Ennahdha members voting **and** more
than half of everyone else voting. It uses one bloc distinction only, the one
Nugent's argument is about, and Ennahdha membership is the one label in this
chamber that barely moves: the switching in figure 28 is overwhelmingly among the
smaller secular lists.

*Division similarity* (panel B) uses no labels at all. For every pair of
contested divisions in a quarter it computes |φ| between the two yes/no splits
over the members who voted in both, and averages. A chamber with one recurring
cleavage returns a high value however its parties are named; a chamber whose
majorities re-form question by question returns a low one. The benchmark is a
permutation null — each division's votes reshuffled among the members who cast
them, holding its margin fixed — which is what the same measure returns when
nothing but the margins is structured.

**What the record shows.** Cross-cutting wins carry 75% of the term's 993
contested divisions and 86% of all 1,724 recorded ones, with no downward trend:
the last quarter of the term (78%) sits above the two before it. Division
similarity runs well above its null in every quarter, so this is not a chamber
without structure — but the excess *falls*, from +0.27 in late 2012 to +0.11 in
its final quarter, and the three quarters carrying 73% of all contested business
are the three least structured. The chamber's divisions grew less alike as it
went, not more.

The falling excess is not an artefact of the later quarters being larger. Mean
|φ| is an average over pairs of divisions, so a random subsample of a quarter
estimates the same quantity; cutting every quarter to the smallest one's 17
divisions moves no excess by more than 0.03 and changes no ordering. Nor is it
participation, which varies far more than the roster does. |φ| is a magnitude, so
two divisions compared over few common voters return a larger one by chance
alone, and the median pair of divisions shares 118 voters in 2014Q1 against 52 in
2014Q3. The permutation null absorbs exactly that: it tracks √(2/π·overlap), the
expected |φ| between independent splits, to within 0.003 in every quarter. That
is why panel B annotates the excess over the null rather than the raw value, and
why the raw line alone would be misread.

On this implication the account survives: there is no build-up of polarisation to
find, and the constitution was carried by coalitions that crossed the cleavage in
question rather than by one side of it.

**Four things this does not establish.** It does not test Nugent's mechanism —
repression type shaping perceived distance — which roll calls cannot reach.
It says nothing about Egypt, the comparison the argument rests on. Roll-call
behaviour is disciplined and agenda-conditioned, so behavioural cooperation and
attitudinal polarisation are different constructs that can move apart. And the
NCA is where the consensus outcome was produced, so finding cross-cutting votes
in it is closer to confirming the outcome was real than to explaining it.

The 2013Q3 gap is not missing data: seven contested divisions fell in the quarter
of the Brahmi assassination, too few to estimate from (figures 43-45).
"""

from __future__ import annotations

import collections
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _polarization as POL  # noqa: E402
import _style as S  # noqa: E402

ASSEMBLY = "NCA-2011"
# The contested-division filter used throughout this repo's vote layer.
MIN_CAST, MIN_MINORITY = 40, 0.025
# A pair of divisions is comparable only over members who voted in both.
MIN_OVERLAP = 30
# Below this a quarter's estimate would be mostly sampling noise, so it is left
# blank rather than drawn faintly and read anyway.
MIN_DIVISIONS = 12
BOOTSTRAP, NULLS = 400, 10
SEED = 20260830


def load() -> tuple[list[str], list[str], dict[str, str], np.ndarray]:
    """Members, divisions in date order, dates, and the ±1 vote matrix."""
    dates = {r["vote_id"]: r["vote_date"] for r in S.load("votes")
             if r["assembly_id"] == ASSEMBLY and r["vote_date"]}
    positions: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for row in S.load("vote_positions"):
        if row["vote_id"] not in dates:
            continue
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1
    people = sorted(positions)
    # Sorted by date then id: date alone leaves same-day divisions in dict order,
    # which is not stable across processes.
    votes = sorted(dates, key=lambda v: (dates[v], v))
    index = {v: j for j, v in enumerate(votes)}
    matrix = np.zeros((len(people), len(votes)), dtype=np.int8)
    for i, person in enumerate(people):
        for vote_id, side in positions[person].items():
            matrix[i, index[vote_id]] = side
    return people, votes, dates, matrix


def contested(matrix: np.ndarray) -> np.ndarray:
    yes = (matrix == 1).sum(0)
    no = (matrix == -1).sum(0)
    cast = yes + no
    with np.errstate(invalid="ignore", divide="ignore"):
        minority = np.where(cast > 0, np.minimum(yes, no) / np.maximum(cast, 1), 0.0)
    return np.flatnonzero((cast >= MIN_CAST) & (minority >= MIN_MINORITY))


def phi_matrix(yes: np.ndarray, no: np.ndarray) -> np.ndarray:
    """|φ| between every pair of divisions, over members voting in both.

    Computed from the four cell counts rather than by looping over pairs: the
    counts are four matrix products, and the pairwise-complete handling falls
    out of them, because a member absent from either division contributes to no
    cell. Pairs sharing fewer than ``MIN_OVERLAP`` members come back as NaN.
    """
    y, n = yes.astype(np.float64), no.astype(np.float64)
    n11, n00 = y.T @ y, n.T @ n
    n10, n01 = y.T @ n, n.T @ y
    total = n11 + n00 + n10 + n01
    denominator = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    with np.errstate(invalid="ignore", divide="ignore"):
        phi = np.abs((n11 * n00 - n10 * n01) / np.sqrt(denominator))
    return np.where((total >= MIN_OVERLAP) & np.isfinite(phi), phi, np.nan)


def mean_phi(phi: np.ndarray, take: np.ndarray | None = None) -> float:
    """Mean of the upper triangle, optionally over a subset of divisions."""
    block = phi if take is None else phi[np.ix_(take, take)]
    upper = block[np.triu_indices(block.shape[0], 1)]
    upper = upper[~np.isnan(upper)]
    return float(upper.mean()) if upper.size else float("nan")


def permuted(yes: np.ndarray, no: np.ndarray, rng) -> tuple[np.ndarray, np.ndarray]:
    """Reshuffle each division's sides among the members who voted in it.

    Holds every division's margin and every member's participation fixed, and
    destroys only the alignment between divisions — which is exactly the thing
    the measure is supposed to detect.
    """
    y, n = yes.copy(), no.copy()
    for k in range(yes.shape[1]):
        who = np.flatnonzero(yes[:, k] | no[:, k])
        drawn = yes[who, k].copy()
        rng.shuffle(drawn)
        y[who, k], n[who, k] = drawn, ~drawn
    return y, n


def crossing(matrix: np.ndarray, columns: np.ndarray, ennahdha: np.ndarray) -> float:
    """Share of divisions whose winning side carried both sides of the cleavage.

    "Carried" is more than half of the group's members who actually voted, so a
    bloc that mostly abstained cannot veto the classification by absence.
    """
    hits = 0
    for j in columns:
        column = matrix[:, j]
        winner = 1 if (column == 1).sum() >= (column == -1).sum() else -1
        for group in (ennahdha, ~ennahdha):
            side = column[group]
            voted = (side != 0).sum()
            if not voted or (side == winner).sum() / voted <= 0.5:
                break
        else:
            hits += 1
    return hits / len(columns)


def quarter_of(date: str) -> str:
    return f"{date[:4]}Q{(int(date[5:7]) - 1) // 3 + 1}"


def main() -> None:
    people, votes, dates, matrix = load()
    if not votes:
        raise SystemExit("no dated divisions for NCA-2011; run `make build`")
    columns = contested(matrix)
    bloc = POL.blocs(ASSEMBLY)
    ennahdha = np.array([bloc.get(p, "No bloc") == "Ennahdha" for p in people])
    rng = np.random.default_rng(SEED)

    by_quarter: dict[str, list[int]] = collections.defaultdict(list)
    for j in columns:
        by_quarter[quarter_of(dates[votes[j]])].append(int(j))

    first, last = sorted(by_quarter)[0], sorted(by_quarter)[-1]
    axis: list[str] = []
    year, q = int(first[:4]), int(first[-1])
    while f"{year}Q{q}" <= last:
        axis.append(f"{year}Q{q}")
        year, q = year + (q == 4), q % 4 + 1

    rows = []
    for name in axis:
        picked = np.array(sorted(by_quarter.get(name, [])), dtype=int)
        days = len({dates[votes[j]] for j in picked}) if picked.size else 0
        entry = {
            "quarter": name,
            "contested_divisions": int(picked.size),
            "sitting_days": days,
            "cross_cutting_wins": "", "division_similarity": "",
            "ci_low": "", "ci_high": "", "permutation_null": "", "excess": "",
        }
        if picked.size >= MIN_DIVISIONS:
            yes = matrix[:, picked] == 1
            no = matrix[:, picked] == -1
            phi = phi_matrix(yes, no)
            observed = mean_phi(phi)
            # Resample divisions, not pairs: the pairs are not independent, and
            # the phi matrix is fixed, so a bootstrap draw is a submatrix.
            draws = sorted(
                mean_phi(phi, np.unique(rng.integers(0, picked.size, picked.size)))
                for _ in range(BOOTSTRAP))
            null = float(np.mean([mean_phi(phi_matrix(*permuted(yes, no, rng)))
                                  for _ in range(NULLS)]))
            entry.update({
                "cross_cutting_wins": round(crossing(matrix, picked, ennahdha), 4),
                "division_similarity": round(observed, 4),
                "ci_low": round(draws[int(0.025 * len(draws))], 4),
                "ci_high": round(draws[int(0.975 * len(draws))], 4),
                "permutation_null": round(null, 4),
                "excess": round(observed - null, 4),
            })
        rows.append(entry)

    drawn = [r for r in rows if r["division_similarity"] != ""]
    if len(drawn) < 3:
        raise SystemExit("too few quarters to draw a series")
    term_cross = crossing(matrix, columns, ennahdha)
    all_cross = crossing(matrix, np.arange(matrix.shape[1]), ennahdha)

    # Marker area carries the quarter's volume, because these quarters differ by
    # a factor of forty in how much business they contain and a plain line would
    # give a 17-division quarter the same visual weight as a 279-division one.
    biggest = max(r["contested_divisions"] for r in drawn)
    accent, = S.categorical(1, all_pairs=True)
    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=S.figsize(10.4, 5.4), gridspec_kw={"wspace": 0.22})
    x = {name: i for i, name in enumerate(axis)}
    xs = [x[r["quarter"]] for r in drawn]
    grid = np.arange(len(axis), dtype=float)

    def series(field):
        """Full-width array with NaN where a quarter has no estimate.

        The line has to break at those quarters rather than run through them:
        joining 2013Q2 to 2013Q4 across the assassination would draw a
        trajectory over a gap where the chamber barely voted.
        """
        lookup = {r["quarter"]: r[field] for r in drawn}
        return np.array([lookup.get(n, np.nan) for n in axis], dtype=float)

    # A — cross-cutting winning coalitions
    ax_a.axhline(term_cross, color=S.CHROME["axis"], linewidth=1.0,
                 linestyle=(0, (4, 2)), zorder=2)
    ax_a.plot(grid, series("cross_cutting_wins"), color=accent,
              linewidth=2.0, zorder=3)
    ax_a.scatter(xs, [r["cross_cutting_wins"] for r in drawn],
                 s=[26 + 150 * r["contested_divisions"] / biggest for r in drawn],
                 color=accent, zorder=4, edgecolors=S.CHROME["surface"], linewidths=0.8)
    for r in drawn:
        ax_a.annotate(f"{r['cross_cutting_wins']:.0%}",
                      xy=(x[r["quarter"]], r["cross_cutting_wins"]), xytext=(0, 12),
                      textcoords="offset points", ha="center", fontsize=7.6,
                      color=S.CHROME["text_primary"], zorder=6)
    ax_a.set_ylim(0.4, 1.0)
    ax_a.annotate(
        S.label(f"Dashed line: {term_cross:.0%}, the whole term.\nMarker area is "
                f"the quarter's division count "
                f"({min(r['contested_divisions'] for r in drawn)} to {biggest})."),
        xy=(len(axis) - 0.7, 0.415), ha="right", va="bottom", fontsize=7.4,
        color=S.CHROME["text_secondary"], zorder=5)
    ax_a.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax_a.set_title(S.label("A · Divisions won by a coalition that crossed the "
                           "Ennahdha line"),
                   loc="left", fontsize=9.6, color=S.CHROME["text_primary"], pad=8)
    ax_a.set_ylabel(S.label("Share of the quarter's contested divisions"), fontsize=8.4)

    # B — division similarity against its permutation null
    nulls = series("permutation_null")
    ax_b.fill_between(grid, nulls, 0, where=np.isfinite(nulls),
                      color=S.CHROME["deemph"], alpha=0.55, zorder=1)
    ax_b.annotate(S.label("Reshuffled votes, same margins"),
                  xy=(xs[0] + 0.1, drawn[0]["permutation_null"]), xytext=(0, 6),
                  textcoords="offset points", ha="left", fontsize=7.6,
                  color=S.CHROME["text_secondary"], zorder=5)
    for r in drawn:
        ax_b.plot([x[r["quarter"]]] * 2, [r["ci_low"], r["ci_high"]],
                  color=S.CHROME["deemph"], linewidth=7, solid_capstyle="butt", zorder=2)
    ax_b.plot(grid, series("division_similarity"), color=accent,
              linewidth=2.0, marker="o", markersize=6, zorder=4,
              markeredgecolor=S.CHROME["surface"], markeredgewidth=0.8)
    for r in drawn:
        ax_b.annotate(f"{r['excess']:+.2f}",
                      xy=(x[r["quarter"]], r["ci_high"]), xytext=(0, 7),
                      textcoords="offset points", ha="center", fontsize=7.6,
                      color=S.CHROME["text_primary"], zorder=6)
    ax_b.set_ylim(0, 0.55)
    ax_b.set_title(S.label("B · How alike the quarter's divisions were, and how "
                           "far above chance"),
                   loc="left", fontsize=9.6, color=S.CHROME["text_primary"], pad=8)
    ax_b.set_ylabel(S.label("Mean |φ| between pairs of divisions"), fontsize=8.4)

    silent = [r for r in rows if r["division_similarity"] == ""]
    for ax in (ax_a, ax_b):
        ax.set_xlim(-0.5, len(axis) - 0.5)
        ax.set_xticks(range(len(axis)))
        ax.set_xticklabels([S.label(f"{n[:4]}\n{n[4:]}") for n in axis], fontsize=7.8)
        S.frame(ax)
        for r in silent:
            ax.axvspan(x[r["quarter"]] - 0.5, x[r["quarter"]] + 0.5,
                       color=S.CHROME["deemph"], alpha=0.35, zorder=0)
            # Labelled at the top: the bottom of panel A carries the note about
            # the dashed line, and a label there would sit on top of it.
            ax.annotate(S.label(f"{r['contested_divisions']} contested\ndivisions"),
                        xy=(x[r["quarter"]], ax.get_ylim()[1]), xytext=(0, -8),
                        textcoords="offset points", ha="center", va="top",
                        fontsize=7.0, color=S.CHROME["text_secondary"], zorder=5)

    fig.subplots_adjust(left=0.062, right=0.985, top=0.70, bottom=0.085)
    fig.text(0.010, 0.985,
             "No build-up of polarisation to find: the assembly's divisions grew "
             "less alike as it went, not more",
             ha="left", va="top", fontsize=13.5, fontweight="bold",
             color=S.CHROME["text_primary"])
    fig.text(
        0.010, 0.948,
        f"Nugent (2020) argues Tunisia's transition held because indiscriminate "
        f"repression left its opposition comparatively unpolarised. That claim is "
        f"about elite perceptions and roll calls cannot test it,\nbut it implies "
        f"something checkable: cooperation in the chamber that wrote the "
        f"constitution should be high and should not erode. It is and it does not. "
        f"A coalition carrying more than half of\nEnnahdha's voters and more than "
        f"half of everyone else's won {term_cross:.0%} of the "
        f"{len(columns)} contested divisions and {all_cross:.0%} of all "
        f"{matrix.shape[1]:,} recorded ones, ending the term above the two quarters "
        f"before it. Panel B\nneeds no bloc labels at all — this chamber's are "
        f"undated while 105 of 217 members switched party — and asks instead "
        f"whether the same line keeps reappearing. It runs above\nchance "
        f"everywhere, so the assembly is structured, not random; but the excess "
        f"falls from {drawn[0]['excess']:+.2f} to {drawn[-1]['excess']:+.2f}, and "
        f"the three quarters holding 73% of the term's business are its three "
        f"least\nstructured. What this cannot do is test Nugent's mechanism, speak "
        f"to Egypt, or separate disciplined behaviour from held belief — and the "
        f"NCA is where the consensus was produced,\nso cross-cutting votes in it "
        f"confirm the outcome was real rather than explain it. Bloc is each "
        f"member's last recorded spell: the source publishes no dated bloc history.",
        ha="left", va="top", fontsize=8.2, color=S.CHROME["text_secondary"],
        linespacing=1.35,
    )
    S.source_note(fig, "ParliamentariansTN · votes.csv × vote_positions.csv")
    S.save(fig, "fig46_cooperation_over_time_nca2011", rows)


if __name__ == "__main__":
    main()
