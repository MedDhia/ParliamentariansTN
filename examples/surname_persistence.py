"""Do surnames from the 1956 Constituent Assembly persist into modern parliament?

A test of long-run elite persistence at the only level this dataset can reach:
the family name. Runs on the committed tables with no dependencies beyond the
standard library.

    python examples/surname_persistence.py

**Why the naive version is worthless.** Counting how many modern deputies share
a surname with a 1956 member returns a large number — 51 of 742 here — and means
nothing, because Tunisian surnames are common and their frequency distribution is
skewed. Any set of a hundred Tunisian surnames will "match" a chunk of any other
set. The number only becomes interpretable against a null model.

**The null.** Draw an arbitrary cohort of the same size (108) from the modern
parliamentary pool, take *their* surnames, and score how much of the rest of the
pool they cover. Repeat 10,000 times. This asks the question that matters: does
the 1956 cohort reach modern parliament better than an ordinary cohort of the
same size does? Every extraction rule below is applied identically to the
observed statistic and to the null, so a rule that over- or under-matches biases
both together and largely cancels.

**Three robustness checks**, because a null result is only worth reporting if the
test could have found something:

1. *Particle rule.* Tunisian names carry nasab particles (بن، بو، ولد) that
   sources attach and detach inconsistently — the repo's own `ids` module exists
   partly to absorb that. Keeping the particle treats "بن علي" and "علي" as
   different surnames (false negatives when sources disagree); dropping it
   conflates them (false positives). Both are run.
2. *Given-name filter.* 78 of the 108 recorded 1956 names have only two tokens,
   and some of those are given + given rather than given + family, so a
   last-token rule sometimes extracts a first name. Each candidate surname is
   scored on how often that token appears in first versus last position across
   the whole corpus, and the ones that behave like given names are dropped.
3. *Positive control and power.* The same test is run on chamber pairs five years
   apart, where continuity should be easiest to find, and a simulation injects a
   known number of artificial "descendants" to establish the smallest effect the
   design could detect.

**What this cannot do.** A shared surname is not kinship. The test can reject
strong persistence; it cannot establish descent, and it cannot see the twelve
chambers between 1959 and 2011 for which no roster exists.
"""

from __future__ import annotations

import collections
import csv
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from parliamentarians_tn.ids import normalize_arabic, _DETACHABLE_PREFIXES  # noqa: E402

SEED = 20260828
N_PERM = 10_000
FOUNDING = "ANC-1956"
MODERN = ("NCA-2011", "ARP-2014", "ARP-2019", "ARP-2023")
# The nasab particles the ids module already knows about, plus the two spellings
# of أبو that appear in these rosters.
PARTICLES = set(_DETACHABLE_PREFIXES) | {"ابو", "أبو"}


def load() -> tuple[dict, dict]:
    persons = {p["person_id"]: p
               for p in csv.DictReader(open(ROOT / "data/processed/persons.csv"))}
    by_chamber: dict[str, set[str]] = collections.defaultdict(set)
    for r in csv.DictReader(open(ROOT / "data/processed/mandates.csv")):
        by_chamber[r["assembly_id"]].add(r["person_id"])
    return persons, by_chamber


def surname(name_ar: str, keep_particle: bool = True) -> str:
    """Family element of a normalised Arabic name.

    Tunisian names run [given] [father] [family]; the family element is the last
    token, except that a nasab particle binds to it — "بن جعفر" is one surname,
    not the token "جعفر".
    """
    toks = normalize_arabic(name_ar).split()
    if not toks:
        return ""
    if len(toks) >= 2 and toks[-2] in PARTICLES:
        return f"{toks[-2]} {toks[-1]}" if keep_particle else toks[-1]
    return toks[-1]


def position_profile(persons: dict, ids: list[str]) -> tuple[collections.Counter,
                                                             collections.Counter]:
    """How often each token appears first (given) versus last (family)."""
    first: collections.Counter = collections.Counter()
    last: collections.Counter = collections.Counter()
    for pid in ids:
        toks = normalize_arabic(persons[pid]["name_ar"]).split()
        if len(toks) >= 2:
            first[toks[0]] += 1
            last[toks[-1]] += 1
    return first, last


def permutation_test(surnames: dict[str, str], donor_names: set[str],
                     target: list[str], n_donor: int, n_perm: int = N_PERM,
                     seed: int = SEED) -> dict:
    """Coverage of `target` by `donor_names`, against a same-size null cohort
    drawn from the target pool and scored on the members it does not contain."""
    target = [p for p in target if surnames[p]]
    observed = sum(1 for p in target if surnames[p] in donor_names) / len(target)

    rng = random.Random(seed)
    tset, null = set(target), []
    for _ in range(n_perm):
        drawn = set(rng.sample(target, n_donor))
        names = {surnames[p] for p in drawn}
        rest = tset - drawn
        null.append(sum(1 for p in rest if surnames[p] in names) / len(rest))

    mean, sd = statistics.mean(null), statistics.pstdev(null)
    return {
        "observed": observed, "null_mean": mean, "null_sd": sd,
        "z": (observed - mean) / sd if sd else float("nan"),
        # One-sided: persistence predicts observed ABOVE the null.
        "p_higher": (sum(1 for v in null if v >= observed) + 1) / (n_perm + 1),
        "n_target": len(target), "null": null,
    }


def line(label: str, r: dict) -> None:
    print(f"  {label:<38} obs {r['observed']:.3f}   null {r['null_mean']:.3f} "
          f"(sd {r['null_sd']:.3f})   z {r['z']:+5.2f}   p {r['p_higher']:.3f}")


def main() -> None:
    persons, by_chamber = load()
    founders = sorted(by_chamber[FOUNDING])
    modern = sorted({p for c in MODERN for p in by_chamber[c]} - set(founders))

    print("Surname persistence: the 1956 Constituent Assembly and modern parliament")
    print("=" * 78)
    print(f"  founding cohort {len(founders)} members · modern pool {len(modern)} members")
    print(f"  shared person_ids between the two: "
          f"{len(set(founders) & set(modern))}  (nobody sat in both)")

    for keep in (True, False):
        sn = {pid: surname(p["name_ar"], keep) for pid, p in persons.items()}
        founding_names = {sn[p] for p in founders if sn[p]}
        modern_freq = collections.Counter(sn[p] for p in modern if sn[p])
        rule = "particle kept (بن علي ≠ علي)" if keep else "particle dropped (بن علي ≡ علي)"

        print()
        print(f"── {rule} " + "─" * (74 - len(rule)))
        print(f"  {len(founding_names)} distinct 1956 surnames · "
              f"{len(modern_freq)} distinct modern surnames")
        reappearing = {s for s in founding_names if s in modern_freq}
        carriers = sum(1 for p in modern if sn[p] in founding_names)
        print(f"  raw overlap: {carriers} of {len(modern)} modern deputies "
              f"({carriers / len(modern):.1%}) carry a 1956 surname; "
              f"{len(reappearing)} of {len(founding_names)} 1956 surnames reappear")
        print()
        r = permutation_test(sn, founding_names, modern, len(founders))
        line("1956 -> all post-2011", r)
        for c in MODERN:
            line(f"1956 -> {c}",
                 permutation_test(sn, founding_names, sorted(by_chamber[c]), len(founders)))

        if keep:
            main_result = r
            main_sn, main_names = sn, founding_names
            main_freq = modern_freq

    # ---- given-name filter -------------------------------------------------
    print()
    print("── robustness: drop candidates that behave like given names " + "─" * 19)
    first, last = position_profile(persons, sorted(set(founders) | set(modern)))

    def credible(s: str) -> bool:
        head = s.split()[-1]
        return last[head] >= first[head] or (first[head] + last[head]) == 0

    keep_names = {s for s in main_names if credible(s)}
    dropped = sorted(main_names - keep_names, key=lambda s: -first[s.split()[-1]])
    print(f"  {len(keep_names)} of {len(main_names)} 1956 surnames survive "
          f"({len(keep_names) / len(main_names):.0%}); rejected, most given-like first:")
    for s in dropped[:5]:
        head = s.split()[-1]
        print(f"    {s:<20} first-position {first[head]:3d}  last-position {last[head]:3d}")
    filtered_target = [p for p in modern if main_sn[p] and credible(main_sn[p])]
    line("credible surnames only",
         permutation_test(main_sn, keep_names, filtered_target, len(founders)))

    # ---- positive control --------------------------------------------------
    print()
    print("── positive control: can the test see continuity where it should be? ──")
    print("  Consecutive chambers, five years apart, with the members who actually")
    print("  sat in both removed — so any signal left is surname-borne, not the")
    print("  same people reappearing.")
    for a, b in (("NCA-2011", "ARP-2014"), ("ARP-2014", "ARP-2019")):
        donors = sorted(by_chamber[a] - by_chamber[b])
        target = sorted(p for p in by_chamber[b] - by_chamber[a] if main_sn[p])
        # Cap the cohort at a third of the target. A donor set nearly as large as
        # the target leaves the null almost nothing to score — at n_donor =
        # len(target) - 1 the remainder is a single person and the null variance
        # is meaningless. The observed side is subsampled to the same size so the
        # two remain comparable.
        n = min(len(donors), max(len(target) // 3, 2))
        rng = random.Random(SEED)
        obs = statistics.mean(
            sum(1 for p in target
                if main_sn[p] in {main_sn[q] for q in rng.sample(donors, n)}) / len(target)
            for _ in range(200)
        )
        r = permutation_test(main_sn, set(), target, n)
        r["observed"] = obs
        r["z"] = (obs - r["null_mean"]) / r["null_sd"] if r["null_sd"] else float("nan")
        r["p_higher"] = (sum(1 for v in r["null"] if v >= obs) + 1) / (len(r["null"]) + 1)
        line(f"{a} -> {b}  (cohort of {n})", r)

    # ---- power -------------------------------------------------------------
    print()
    print("── power: how much persistence would this design detect? " + "─" * 22)
    print("  Overwrite k modern deputies' surnames with real 1956 surnames, then")
    print("  re-run the identical test.")
    threshold = sorted(main_result["null"])[int(0.95 * len(main_result["null"]))]
    print(f"  rejection threshold (null 95th percentile): {threshold:.3f}")
    rng = random.Random(SEED)
    pool = sorted(main_names)
    for k in (0, 10, 20, 30, 40, 50, 80):
        hits = 0
        for _ in range(200):
            sn2 = dict(main_sn)
            for pid in rng.sample(modern, k):
                sn2[pid] = rng.choice(pool)
            share = sum(1 for p in modern if sn2[p] in main_names) / len(modern)
            hits += share >= threshold
        print(f"    k={k:3d} descendants ({k / len(modern):5.1%} of the modern pool)"
              f"   power {hits / 200:4.0%}")

    # ---- where the matches sit --------------------------------------------
    print()
    print("── where the reappearing surnames sit in the frequency distribution ──")
    bands: collections.Counter = collections.Counter()
    for s in (main_names & set(main_freq)):
        f = main_freq[s]
        bands["1 (unique)" if f == 1 else "2" if f == 2 else "3-5" if f <= 5 else "6+"] += 1
    for b in ("1 (unique)", "2", "3-5", "6+"):
        print(f"    carried by {b:<11} modern deputies: {bands[b]:3d} surnames")
    print(f"  for reference, {sum(1 for p in modern if main_freq[main_sn[p]] == 1) / len(modern):.0%}"
          " of modern deputies have a surname unique within modern parliament")

    print()
    print("=" * 78)
    print("READ THE DOCSTRING BEFORE QUOTING ANY OF THIS. A shared surname is not")
    print("kinship, and no roster exists for the twelve chambers between 1959 and")
    print("2011, so this compares 1956 with 2011+ across a fifty-five-year hole.")


if __name__ == "__main__":
    main()
