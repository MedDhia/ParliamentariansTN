# Findings

What the dataset shows, in one place, with the number and the file to check it
in. Everything here is computed from the committed tables — nothing is quoted
from memory, and every row can be re-derived by running `make figures`.

Each finding names the figure that draws it and the CSV that holds its numbers.
The CSVs are the authoritative form: `figures/output/figNN_name.csv` sits beside
every PNG for exactly this purpose.

> **Read the coverage caveat first.** Person-level data exists for **five** of the
> nineteen chamber-terms: 1956, 2011–14, 2014–19, 2019–21 and 2023–. The other
> fourteen — the whole single-party era and both upper houses — are present as
> institutions, usually with only a presiding officer named. Any statement below
> about "Tunisian parliamentarians" describes those five chambers, and the gap is
> **not random**: it is exactly the authoritarian period. See
> [COVERAGE.md](COVERAGE.md) and figure 4.

---

## 1. The institutional frame

**Nineteen chamber-terms across seventy years, and the chamber has been
shrinking.** Seats climb from 98 (1956) to 217 (2011–2021), then fall to 161 in
2023 — the only sustained contraction in the series, and the first under
single-member districts rather than closed-list PR.
· *Figures 1–2 · `fig01_institutional_timeline.csv`, `fig02_chamber_size.csv`*

**Coverage is bimodal, not graded.** Five chambers are near-complete (96–113% of
nominal seats, the excess being mid-term replacements); the other fourteen record
between 0 and 3 people each. There is no partial middle.
· *Figure 4 · `fig04_coverage.csv`*

| | chambers | mandates recorded |
| --- | --- | --- |
| Person-level roster | 5 | 942 |
| Institutional frame only | 14 | 17 |

---

## 2. Who sits

**Women's share rose under list PR with parity, then halved under single-member
districts.** 31% (2011) → 35% (2014) → 27% (2019) → **16%** (2023). The 2023 fall
coincides with the electoral-system change, though this dataset alone cannot
establish that as the cause.
· *Figure 3 · `fig03_women_share.csv`* — sex for 2011 is inferred from French
grammatical agreement in the source biographies, not recorded.

**The 2014 chamber was drawn from a narrow professional base.** Lawyers 16%,
secondary teachers 10%, company directors 9%, university professors 9%. Farmers:
**2 of 223 coded members (0.9%)**, in a country where agriculture is a major
employer.
· *Figure 5 · `fig05_professions_arp2014.csv`* — the CSV carries the full
unfolded distribution, including the tail the chart folds into "Other".

**Diaspora representation was a post-2011 novelty that has now collapsed.**
Out-of-country seats fell from 8.4% of mapped members (2011) to **1.9%** (2023).
· *Figure 6 · `fig06_region_heatmap.csv`*

**The 1956 assembly cannot be placed regionally.** Its compound districts
("Sidi Bouzid–Gafsa–Tozeur") predate the modern governorates; only 13 of 98
members map. It is excluded from figure 6 rather than silently mis-assigned.

---

## 3. Elite circulation

**Tunisia's democratic parliaments were not staffed by a stable political
class.** No chamber draws even a quarter of its members from its predecessor, and
the 2023 chamber draws **3%**.

| chamber | members | returning from previous | share |
| --- | --- | --- | --- |
| NCA-2011 | 217 | — | — |
| ARP-2014 | 246 | 31 | 12.6% |
| ARP-2019 | 216 | 50 | 23.1% |
| ARP-2023 | 155 | **5** | **3.2%** |

· *Figure 9 · `fig09_elite_flow.csv`*

**Almost nobody sits more than twice.** 772 of 856 parliamentarians appear in one
chamber only; 68 in two; 14 in three; 2 in four or more.
· *Figure 8 · `fig08_chambers_served.csv`*

**A pairwise overlap is not a skip count.** 13 people sat in both 2011 and 2019 —
but 12 of them also sat in 2014. Exactly **one** member left and returned.
Compute skip patterns from `mandates.csv`, not from the matrix.
· *Figure 10 · `fig10_chamber_overlap.csv`*

**The pre-2011 rows are the substantive gap, not a rounding error.** The only
links across 2011 are between the sparse Ben Ali-era rows themselves. Whether the
people who sat under Ben Ali returned after the revolution is a question this
dataset **cannot currently answer**, because those chambers have no roster.

---

## 4. Bloc dynamics, 2014–2019

Only possible because that chamber was reconstructed from ~29 monthly Internet
Archive captures, which turn bloc membership into dated spells. Boundaries are
bracketed to the interval between two captures — read trends, not months.

**The party that won the election was not the largest bloc by the end of the
term.** Nidaa Tounes enters with 86 seats against Ennahdha's 69 — the official
2014 result exactly — and finishes on 38 against Ennahdha's 68, behind the
National Coalition's 44.
· *Figure 11 · `fig11_bloc_composition_arp2014.csv`*

**Fragmentation rose from 3.6 to 5.3 effective blocs**, essentially all of it
from Nidaa Tounes dissolving rather than from small blocs appearing at the
margins.
· *Figure 12 · `fig12_effective_blocs_arp2014.csv`* (Laakso–Taagepera, 1/Σs²)

**108 of the 238 members with a recorded bloc history changed bloc**, across 240
moves. Nidaa's members disperse rather than relocating together — 28 to Al Horra,
21 to the National Coalition, 16 to no bloc — which is the signature of a party
dissolving, not splitting cleanly in two.
· *Figure 13 · `fig13_bloc_switching_arp2014.csv`*

**The reconstruction's error is shown, not smoothed.** The monthly panel totals
212–220 members against 217 seats. That spread is the uncertainty; 478 spells
carry `dates_bracketed = true` with the bracketing interval in `notes`.

---

## 5. Networks: assigned ties versus chosen ties

**The headline result of the network layer.** Committee membership is assigned by
the chamber; co-signing a written question is chosen by the deputy. They behave
oppositely with respect to bloc.

| network | tie is | chamber | n | ties | bloc assortativity |
| --- | --- | --- | --- | --- | --- |
| Committee co-membership | assigned | NCA-2011 | 194 | 4,009 | **−0.03** |
| Committee co-membership | assigned | ARP-2019 | 184 | 3,099 | **−0.04** |
| Committee co-membership | assigned | ARP-2023 | 152 | 1,579 | **−0.07** |
| Amendment co-sponsorship | chosen | NCA-2011 | 203 | 9,361 | **+0.13** |
| Written-question co-signature | chosen | ARP-2023 | 114 | 1,663 | **+0.18** |

Committee assignment does not track bloc lines in any chamber — the coefficient
is slightly *negative* throughout. The two chosen-tie networks, among the same
people in the same chambers, both run positive: 3,016 of 9,361 amendment ties
and 553 of 1,663 co-signature ties are within-bloc.

**The contrast replicates across two chambers twelve years apart**, under
different institutions and different sources — the constituent assembly tabling
amendments to the constitution in 2011–2014, and the 2023 chamber co-signing
written questions to ministers. That is what makes it worth more than either
figure alone: it is not an artefact of one chamber's committee-allocation rule.
· *Figures 14–16, 18, 22 · `fig14–16_*.csv`, `fig18_cosignature_network_arp2023.csv`,
`fig22_amendment_mixing_nca2011.csv`*

**Where the 2011 assortativity comes from: one bloc, not all of them.** Read as a
bloc × bloc mixing matrix, the amendment network puts every off-diagonal cell in
Ennahdha's row *below* the chamber-wide rate — 0.34× with the Democratic Bloc,
0.52× with CPR, 0.96× at its most collaborative. No other bloc has that property,
and the small blocs co-sponsor with each other at up to 2.2× the chamber rate.
The positive coefficient is the largest bloc keeping to itself rather than
general bloc discipline. The diagonal is a weaker guide: a ten-member bloc has 45
internal pairs and an 87-member one has 3,741, so within-bloc density rises as
bloc size falls for arithmetic reasons.
· *Figure 22 · `fig22_amendment_mixing_nca2011.csv`*

**Treat the committee projection with care: it is exactly the union of the
committee cliques.** Every tie in NCA-2011 and ARP-2019 is reproduced by taking
each committee and joining all its members. Its density (0.14–0.21) is
manufactured by projection, not observed. 247 memberships stand behind ARP-2023's
1,579 dyads.
· *Figure 17 · `fig17_committee_bipartite_arp2023.csv`* — build your own
projection from this incidence structure rather than inheriting a weighting.

**Most deputies bridge committees.** 151 of 194 (2011), 151 of 184 (2019), 80 of
152 (2023) sit on more than one. Figures 14–17 place a deputy by *which*
committees she sits on (angle) and *how many* (distance from the centre), so
bridging is the readable structure.

**Joint action is rare.** Of 6,332 written questions in the 2023 chamber, only
**78** carry more than one signatory, and **41 of 155** deputies never co-signed
anything at all.
· *Figure 18*

---

## 6. The 2011-2014 roll-call record

**370,922 recorded positions across 1,724 divisions**, for the 217 members of the
constituent assembly — the only chamber in the dataset with a division-level
voting record. Published as pour / contre / abstenu / absent.

Two cautions before anyone estimates ideal points from it. "Absent" conflates
being away with being present and not voting, because the source does not
separate them, so an abstention rate computed from these positions is a lower
bound. And a division missing from a member's page has no row rather than a row
reading absent: members who joined late or left early are simply not listed, and
manufacturing an absence for them would assert something the source does not.
· *`data/processed/votes.csv`, `vote_positions.csv`*

**The chamber's main cleavage is Ennahdha against everyone, not government
against opposition.** A singular value decomposition of the member × division
matrix — 217 members over the 993 divisions that were actually contested — gives
a first dimension carrying **22%** of the variance, and it separates Ennahdha
(mean **+10.2**) from every other bloc. Its own Troika coalition partners sit on
the far side of zero from it, CPR at −4.0 and Ettakatol at −3.2, and the
Democratic Bloc anchors the other pole at −11.8. The gap from Ennahdha to the
nearest other bloc is wider than the range containing all seven of them.

This is a first cut and is reported as one: no error model, no bootstrap, no
claim to be an ideal point. Abstention and absence are both coded 0, which pulls
frequent abstainers toward the centre, and near-unanimous divisions are dropped
because they locate nobody. Fit ideal points with uncertainty from
`vote_positions.csv` if that is what you need.

**It agrees with the co-sponsorship record, from a different table.** Figure 22
finds the same shape in who tabled amendments with whom: the largest bloc keeping
to itself while the small blocs work with each other. Two independent behavioural
records of the same chamber, pointing the same way.
· *Figure 21 · `fig21_rollcall_scaling_nca2011.csv`*

**But the axis is not reducible to Ennahdha membership, and saying so matters.**
That bloc held 87 of 217 seats and voted cohesively, and a principal component is
the direction of greatest variance — so a leading dimension aligned with a large
cohesive bloc is partly arithmetic rather than a discovery. Two checks bound how
much:

- Regressing dimension 1 on an Ennahdha dummy gives **R² = 0.760**. Membership
  accounts for three-quarters of the spread along the axis; the remaining
  **24%** is within- and between-bloc variation a dummy cannot produce.
- Removing all 87 Ennahdha members and rescaling the other 130 from scratch —
  re-filtering to the 908 divisions contested among *them*, since the contested
  set is a property of who is voting — leaves a coherent second cleavage at
  **11.3%** of variance, ordering Loyalty to the Revolution (+6.2), Democratic
  Transition (+5.7) and CPR (+4.4) against the Democratic Bloc (−8.0).

So the chamber was not one-dimensional. It had one strong cleavage with real
structure underneath it, and the position of Ennahdha's coalition partners on
that first axis is a fact about how they voted rather than a restatement of who
they were not — which it would be if the axis were defined as distance from the
governing bloc.
· *Reproduce with `python examples/voting_space.py`*

**105 of the 217 ended the term in a party other than the one they were elected
on.** The dataset previously recorded zero, and the source metadata asserted that
switching was not recoverable here; both were wrong. The rows are undated and
cannot be chained — a member who moved twice appears once, as origin and
destination.
· *`data/processed/party_switches.csv`*

## 7. Long-run elite persistence: no surname signal

**Surnames from the 1956 Constituent Assembly do not reach modern parliament more
than chance.** 51 of 742 post-2011 deputies (6.9%) carry a surname also borne by
a 1956 member, and 29 of the 105 distinct 1956 surnames reappear. Both look like
persistence and neither is: a null cohort of the same size, drawn from the modern
pool itself, covers **9.2%** (sd 1.2). The observed value sits 1.9 standard
deviations *below* chance, so the raw overlap is fully explained by how common
Tunisian surnames are.

| specification | observed | null | z |
| --- | --- | --- | --- |
| nasab particle kept | 6.9% | 9.2% | −1.90 |
| nasab particle dropped | 8.0% | 11.0% | −2.23 |
| given-name-like candidates removed | 6.8% | 9.5% | −2.13 |

· *Reproduce with `python examples/surname_persistence.py`*

**The design is blunt, and that is the more important result.** Injecting
artificial descendants shows it detects persistence only at **≥5% of the modern
chamber** (40 people; at 30 the power is zero). And it finds nothing in a
positive control either: between chambers five years apart, with the members who
actually sat in both removed, surname continuity runs z = +0.5 and +0.4 —
directionally positive, nowhere near significant.

So the defensible claim is narrow: **large-scale dynastic reproduction of the
founding elite can be ruled out; a handful of persistent families cannot.** Three
limits do the work here and none is fixable with the present data:

- **A shared surname is not kinship.** 62% of modern deputies have a surname
  unique within modern parliament, so the name space is wide — but matching on
  names identifies neither descent nor its absence.
- **There is a fifty-five-year hole in the middle.** Twelve chambers between 1959
  and 2011 have no roster, so this compares 1956 against 2011+ directly. Families
  could have held seats throughout the single-party era and left before 2011, and
  nothing here would show it.
- **The null is a demanding benchmark.** Its cohorts are drawn from the modern
  pool, so they are frequency-matched to the target by construction. The observed
  falling *below* it is consistent with 1956 surnames simply having become less
  common in the parliamentary population — plausibly regional recomposition — which
  is not the same thing as the absence of dynasties.

## 8. Floor behaviour

**Turning up and voting are not the same thing.** Across 216 members of the
2019 chamber the median gap between plenary attendance and vote participation is
**8.9 points**, reaching 56 points at the extreme.
· *Figure 19 · `fig19_participation_arp2019.csv`* — both rates are proportions
published by Al Bawsala without denominators, so compare within this chamber only.

**Written questions are the most unequally distributed activity in the dataset.**
6,603 filings by 154 deputies; the median deputy files 28, the busiest 201, and
the top twenty account for **42%** of all filings.
· *Figure 20 · `fig20_written_questions_arp2023.csv`*

**Two totals for written questions, both correct.** The chamber holds **6,332
distinct questions** (the basis for figure 18); per-deputy filings sum to
**6,603** (figure 20), because each signatory of the 78 jointly signed questions
is credited. Use the first for question counts and the second for individual
activity.

---

## What this dataset cannot support

Stated plainly, because the absences are as important as the findings.

- **Any claim about parliamentary elites 1959–2011.** Twelve chambers across the
  single-party and Ben Ali eras have no roster. Elite continuity across the
  revolution is unmeasurable here.
- **Comparative participation rates across chambers.** Denominators are
  published for ARP-2019 and recorded, so rates there are checkable; for the
  other chambers they are not, and a rate without its denominator cannot be
  compared to one with a different denominator.
- **Committee networks for 2014–2019.** The mandate panel is continuous but the
  committee panel is not; the archived observatory pages should yield to the same
  method used for the roster.
- **Roll-call votes outside 2011–2014.** Only the constituent assembly publishes
  a division-level record. Nothing equivalent exists here for 2014–19, 2019–21 or
  2023–, so a voting-behaviour comparison across chambers is not available.
- **When a 2011–2014 party switch happened.** The rows are from/to pairs without
  dates, and a member who moved twice appears once.
- **Exact dates for 2014–2019 bloc changes.** They are bracketed to the interval
  between web captures, never to the day.
- **Kinship, or dynastic descent.** There is no genealogical field. Section 7
  tests the closest available proxy — shared surnames — and can only rule out
  persistence at a scale of roughly 5% of a chamber. Small numbers of persistent
  families are invisible to it, and a surname match is never itself evidence of
  descent.
- **Causal claims from any of the above.** These are descriptive results on
  observational data with a non-random coverage gap.

---

*Regenerate every number here with `make figures`; §7 with
`python examples/surname_persistence.py`; each figure writes its own
table. Method and design notes are in [`figures/README.md`](../figures/README.md);
the network layer's construction is in [NETWORK_GUIDE.md](NETWORK_GUIDE.md);
variable definitions are in [CODEBOOK.md](CODEBOOK.md).*
