# Findings

What the dataset shows, in one place, with the number and the file to check it
in. Everything here is computed from the committed tables — nothing is quoted
from memory, and every row can be re-derived by running `make figures`.

Each finding names the figure that draws it and the CSV that holds its numbers.
The CSVs are the authoritative form: `figures/output/figNN_name.csv` sits beside
every PNG for exactly this purpose.

> **Read the coverage caveat first.** Person-level data exists for **six** of the
> nineteen chamber-terms: 1956, 2005–11, 2011–14, 2014–19, 2019–21 and 2023–. The
> other thirteen — almost the whole single-party era — are present as
> institutions, usually with only a presiding officer named. Any statement below
> about "Tunisian parliamentarians" describes those six chambers, and the gap is
> **not random**: it is exactly the authoritarian period. The one exception is the
> Chamber of Advisors, the upper house of 2005–11, whose roster survives because
> its own website was archived; it has members but no biography, no votes and no
> parties, so it appears below only where a roster is enough. See
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
| Committee co-membership | assigned | ARP-2014 | 231 | 11,940 | **−0.01** |
| Committee co-membership | assigned | ARP-2019 | 184 | 3,099 | **−0.04** |
| Committee co-membership | assigned | ARP-2023 | 152 | 1,579 | **−0.07** |
| Amendment co-sponsorship | chosen | NCA-2011 | 203 | 9,361 | **+0.13** |
| Written-question co-signature | chosen | ARP-2023 | 114 | 1,663 | **+0.18** |

Committee assignment does not track bloc lines in any chamber — the coefficient
is slightly *negative* throughout. The two chosen-tie networks, among the same
people in the same chambers, both run positive: 3,016 of 9,361 amendment ties
and 553 of 1,663 co-signature ties are within-bloc.

**The 2014–2019 row is new and it is the hardest test in the table.** That
chamber's committee pages were recovered from the Internet Archive after the
rest of this section was written, and it is the chamber whose governing
coalition broke apart: 108 of its 246 members changed bloc mid-term. If
committee seats were traded along bloc lines anywhere in this dataset, they
would be traded there. The coefficient is −0.01. Two cautions travel with it,
both pushing the same way: 803 of its 985 committee spells have bracketed dates,
and the tie unions the whole term, so its ties are over- rather than
under-counted — which inflates density (0.45 against 0.14–0.21 elsewhere)
without giving bloc any purchase it did not have.

**The contrast replicates across two chambers twelve years apart**, under
different institutions and different sources — the constituent assembly tabling
amendments to the constitution in 2011–2014, and the 2023 chamber co-signing
written questions to ministers. That is what makes it worth more than either
figure alone: it is not an artefact of one chamber's committee-allocation rule.
· *Figures 14–16, 18, 22, 41 · `fig14–16_*.csv`,
`fig41_committee_network_arp2014.csv`,
`fig18_cosignature_network_arp2023.csv`,
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
each committee and joining all its members. Its density (0.14–0.21, and 0.45 for
ARP-2014) is manufactured by projection, not observed. 247 memberships stand
behind ARP-2023's 1,579 dyads.
· *Figure 17 · `fig17_committee_bipartite_arp2023.csv`* — build your own
projection from this incidence structure rather than inheriting a weighting.

**Most deputies bridge committees.** 151 of 194 (2011), 219 of 231 (2014), 151 of
184 (2019), 80 of 152 (2023) sit on more than one. The 2014 chamber is the
outlier: 4.3 committees per deputy against 2.3 in 2011, so almost nobody sat on
one committee alone. Figures 14–17 place a deputy by *which*
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
destination. The Pétition Populaire list dissolves hardest, losing 26 members and
gaining none; the Alliance Démocratique gains most at +11.
· *Figure 28 · `data/processed/party_switches.csv`*

**Two-thirds of the chamber's recorded voting happened in three months**, and
nine months passed after the election before its first recorded division. The
peak is December 2013 to January 2014, the article-by-article passage of the
constitution; April 2014, *after* adoption, is the third. The opening silence is
a source boundary as much as a political fact — Al Bawsala's series begins in
July 2012, and whether earlier recorded votes went uncaptured is not answerable
here.
· *Figure 24 · `fig24_voting_calendar_nca2011.csv`*

**Read two coverage facts before any of the above.** Both bound what the
roll-call analyses can support:

- **Participation collapses across the term.** The share of listed members
  casting neither pour nor contre runs at a median of 18% in July 2012 and 56%
  across the assembly's last three months. Any estimate from late-term divisions
  rests on a much smaller share of the chamber than the same estimate early on.
  · *Figure 25*
- **42% of divisions were near-unanimous**, with a margin above 0.95 and a
  median margin of 0.92. That is the cut figure 21 makes before scaling, and it
  is a large one. A constituent assembly passes most of a founding text by
  consensus and fights over a minority of it; figure 31 shows which parts.
  · *Figure 26*

**Bloc cohesion is high everywhere and mostly tells you about bloc size.** The
Rice index runs at a median of 1.00 for seven of eight blocs; what separates them
is how *often* they were unanimous, from 83% (Democratic Alliance, 10 members)
down to 58% (Ennahdha, 87). Since a ten-member bloc can only divide on a coarse
grid, that ordering is as much arithmetic as discipline, and the defensible
comparison is Ennahdha against its own size. The non-attached, who were under no
obligation to agree, sit at 33% and show what an undisciplined group looks like.
· *Figure 23 · `fig23_bloc_cohesion_nca2011.csv`*

**The preamble was the most-amended part of the draft constitution** — 19
amendments, more than twice any single article — followed by articles 39, 127, 6
and 46. The 251 amendments spread over 98 targets, so no single article
dominated: the busiest drew nine. Article numbers are the source's own and
numbering shifted between drafts, so match a number to a subject against the
draft it was tabled on rather than against the adopted text.
· *Figure 31 · `fig31_contested_articles_nca2011.csv`*

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
· *Figure 19 · `fig19_participation_arp2019.csv`* — both rates now carry the
denominators Al Bawsala publishes on the member pages (`plenary_denominator`,
`vote_denominator`), so they can be recomputed and checked. They still describe
this chamber's own sittings and divisions, so compare within it only.

**Written questions are the most unequally distributed activity in the dataset.**
6,603 filings by 154 deputies; the median deputy files 28, the busiest 201, and
the top twenty account for **42%** of all filings.
· *Figure 20 · `fig20_written_questions_arp2023.csv`*

**Two totals for written questions, both correct.** The chamber holds **6,332
distinct questions** (the basis for figure 18); per-deputy filings sum to
**6,603** (figure 20), because each signatory of the 78 jointly signed questions
is credited. Use the first for question counts and the second for individual
activity.

**Concentration is not the same in both chambers.** Amendment tabling in 2011
gives a Gini of **0.43** across 203 members; written questions in 2023 give
**0.51** across 154. Both are unequal, and the later chamber more so — but the
comparison is between two different activities under two different institutions,
so it separates "parliamentary work is always concentrated" from "these chambers
concentrated it differently" without settling which mechanism produced either.
Members with nothing recorded are excluded from both curves, since for 2011 the
source does not distinguish tabling nothing from not being covered.
· *Figure 27 · `fig27_activity_inequality.csv`*

**Whether women reach committee leadership less often cannot be resolved here.**
Chair-or-vice-chair shares run 6.5% against 10.0% (2011), 9.9% against 10.2%
(2019) and 14.8% against 23.7% (2023). Every point estimate runs against women;
every pair of 95% intervals overlaps, including 2023, where 54 female memberships
give an interval from 7.7% to 26.6%. This is an underpowered null and should be
reported as one — not as evidence of parity, and not as evidence of a gap.
· *Figure 29 · `fig29_women_committee_leadership.csv`*

---

## 9. Polarisation in the 2011 Constituent Assembly

Sixteen figures ask one question in sixteen ways: how far do the lines the
chamber divided on coincide with its bloc boundaries? Most are built on a derived
layer, `edges_vote_agreement.csv`, scoring every pair of members on the share of
*contested* divisions they voted the same way; the last of them asks the question
without bloc labels at all, because this chamber's are undated.

**Bloc predicts agreement sharply, and the chamber is still not two camps.**
Within-bloc pairs average **0.84**, cross-bloc pairs **0.67** — Cohen's d 1.36,
with only 0.9% of cross-bloc pairs reaching the within-bloc median. And yet 92%
of cross-bloc pairs agree more often than they disagree. Both hold at once.
· *Figure 33 · `fig33_agreement_distribution_nca2011.csv`*

**One bloc is a clique. Ennahdha's 87 members have an internal density of
0.998** at a 75%-agreement threshold — 3,735 of 3,741 possible pairs. The other
130 members sit at 0.269. Louvain community detection, given no bloc
information, returns Ennahdha at **88% purity**.
· *Figures 34, 36 · `fig34_*.csv`, `fig36_*.csv`*

**But the graph is not really a community structure.** Modularity is 0.12 under
the bloc partition and 0.21 under the detected one, both below the ~0.3 usually
taken as evidence of real communities. It is one tight clique plus a
weakly-differentiated remainder, not a set of camps.
· *Figure 36*

**Every bloc coheres more than chance; the margins are what differ.** Raw E-I
indices say the small blocs are outward-looking and Ennahdha insular — but that
ordering is arithmetic, since a ten-member bloc has 45 internal pairs against
2,070 external. Against a null that reassigns labels while holding sizes fixed,
**seven of the eight groups fall below their null**. The exception is the
non-attached, who are a residual category and should not cohere — which is the
best available evidence the method works. Ennahdha's margin is 0.59 below its
null mean; the median bloc's is under 0.08.
· *Figure 35 · `fig35_ei_index_nca2011.csv`*

**Ask who each member is *closest* to, and every bloc becomes distinctive.**
Give each member their three strongest alignments — the colleagues they voted
with most often — and **477 of 651** of those nearest ties stay inside their own
bloc, against **23.7%** if partners were drawn at random. This is a different
question from the ones above and a sharper one: not who a member agrees with,
which in this chamber is nearly everyone, but who they agree with *most*.

It has to be asked this way because a threshold has almost nothing to cut. The
agreement graph is **99.6% complete** — 23,337 of 23,436 possible pairs carry a
score — with weights packed around a mean of 0.71, and the disparity filter, the
standard method for extracting a weighted network's backbone, returns **nothing**
at any conventional significance level. No member's alignment with anyone is
disproportionate.

**Correcting for size inverts the ranking, and that is the result.** Ennahdha has
the highest raw share of co-partisan nearest allies (92.7%) and the *lowest* lift
over chance (2.3×), because at 87 of 217 members a random partner is already a
co-partisan 39.8% of the time. The Democratic Alliance, ten members, reaches
**16.8×** on a raw share of 70%. Read the raw column and Ennahdha is the
disciplined bloc; correct for size and it is the least distinctive one in the
chamber. This is the same size trap figure 35's null was built to defeat,
arriving by a different route and pointing the same way.

**And the non-attached are not one group but eleven.** 59% of their nearest
allies are also non-attached — a 2.5× lift for a residual category that should
have no reason to cohere. Restricted to its own members, the non-attached
subgraph breaks into **eleven** disconnected pockets: 26, 13, 4, 2 and seven
isolated individuals. Ennahdha, CPR and Ettakatol each form a single pocket. So
figure 35's null was right that the non-attached do not cohere *as a category*,
and they still contain two sizeable clusters that do — most likely members who
left blocs late and together, though bloc here is the last recorded spell and
this cannot be separated from affinity that was always there.
· *Figure 42 · `fig42_alignment_network_nca2011.csv`*

**The chamber did not polarise as it went.** Across six windows of equal
contested divisions the within/cross gap holds between **0.15 and 0.20** with no
monotone movement — through the constitution's drafting, two assassinations and
a change of government. It began divided along bloc lines and ended that way.
· *Figure 38 · `fig38_polarisation_over_time_nca2011.csv`*

**The chamber's worst crisis registers as a walkout, not a realignment.**
Mohamed Brahmi, an opposition member, was assassinated on 25 July 2013. Over the
four months that followed, the Democratic Bloc's turnout fell from **51% to 21%**
and the Democratic Alliance's from 50% to 26%, while Ennahdha went 79% to 80%
and CPR 57% to 58%. The split is clean: the chamber's two largest parties did
not move, and the rest largely stopped. By December **seven of the eight blocs**
are back at or above where they started; the exception is Loyalty to the
Revolution, which recovers only from 40% to 43% against 50% before. August 2013
produced a single contested division, fewer than any other month in which this
chamber divided at all.
· *Figure 43 · `fig43_brahmi_crisis_nca2011.csv`*

**For the crisis itself there is no comparable affinity estimate, and the reason
is selection rather than sample size.** A within-versus-cross-bloc gap *could* be
computed from the 35 contested divisions: 4,259 pairs clear the scoring floor.
But **zero of the eighteen Democratic Bloc members appear in a single scoreable
pair**, one of ten Democratic Alliance members does, and 52% of the surviving
pairs are Ennahdha with Ennahdha. That number would measure the governing side's
internal cohesion under the chamber's name.

**Across the crisis, no change in affinity is detectable — and the method
decides that.** On 94 contested divisions either side, the gap runs +0.21 before
and +0.18 after. Bootstrapping over *pairs* gives intervals of about ±0.01 and
makes the narrowing look real; but every member sits in more than a hundred
pairs, so pair resampling counts one person's behaviour as a hundred independent
observations. Resampling *members* widens the intervals to ±0.05 and ±0.09 and
they overlap comfortably. The first version of this analysis reported a
significant narrowing and was wrong. The remaining limit is not fixable by
resampling: the 127 members scoreable in every window are 90% of Ennahdha and 6%
of the Democratic Bloc, so the comparison is only available for a sample selected
on the very behaviour the crisis changed.
· *Figure 43*

**Matched properly, the crisis did change the affinity network — and in the
direction neither standard account predicts.** Figure 43 could not settle this
because matching the windows on *divisions* left the post window four days long
and its panel 90% Ennahdha. Matching on **sitting days** instead — 32 either
side, then subsampling the post window back to the same division count — gives a
panel of **196 of 217 members**, including 16 of the 18 Democratic Bloc members
whose withdrawal figure 43 documents. On that panel:

| | before | after | 32 days later |
| --- | --- | --- | --- |
| mean within-bloc agreement | **0.930** | 0.879 | 0.873 |
| mean cross-bloc agreement | 0.672 | **0.679** | 0.658 |
| gap | 0.258 | 0.200 | 0.215 |
| strong ties (≥90% agreement) | 4,792 | 2,553 | 2,542 |
| of which cross-bloc | 1,209 | **453** | 363 |

The polarisation account predicts within-bloc agreement rises and cross-bloc
falls; the elite-settlement account predicts cross-bloc rises. Neither happens.
**Within-bloc agreement falls and cross-bloc agreement does not move**: the blocs
loosened rather than closing ranks, and nobody picked up the ground they lost.
The gap narrows because its top came down.

**The strong ties carry the sharper version.** Reliable voting partnerships —
pairs agreeing on at least 90% of the divisions they both cast — nearly halve,
and unevenly: within-bloc down 41%, cross-bloc down **63%**. Steady average
cross-bloc agreement conceals the collapse of its upper tail. After the crisis a
member could still expect to agree with someone from another bloc about
two-thirds of the time, and could no longer expect any of them to be a dependable
ally. The next 32 sitting days, to August 2014, look the same, so this is not a
transient.

**What it does not establish.** That the assassination caused it. The National
Dialogue, a change of government and the constitution's drafting endgame sit in
the same gap; this is a before-and-after, not an identification strategy.
· *Figures 44, 45 · `fig44_*.csv`, `fig45_*.csv`*

**The same result in the field's three standard presentations.** Everything
above uses a form chosen for its question rather than one a reader of the
literature would recognise, so the conventional three were fitted afterwards to
the same data and the same filters.

- *Distributions of position.* On the first dimension of the vote space,
  Ennahdha's median sits **18.6** above the rest of the chamber's, on an axis
  spanning −16.3 to +16.2. The scale-free version of that: a random Ennahdha
  member outscores a random non-member **98.9%** of the time. The distributions
  are not disjoint — 35 of 87 sit below the highest-scoring non-member — which
  the medians alone would hide. Ordered by median, Ennahdha at +11.2 is 14 points
  from its nearest neighbour, wider than the 8 points containing the other seven
  blocs.
- *Small multiples over time.* Drawn once per quarter of the term, the share of
  ties crossing a bloc goes 61% → 48% → 52% → 58%: no trend, and the first panel
  is high because equal-division windows make it seventeen months where the
  others are one to five.
- *The sorted matrix.* Ennahdha agrees internally at **0.915** against **0.670**
  with everyone else. The other **named** blocs manage **0.803** against
  **0.679** — half the gap, not none.

That last figure corrected a claim. Read with the 52 unaffiliated members
counted as a bloc, the non-Ennahdha gap collapses to 0.689 against 0.667 and the
other blocs look as though they barely cohere at all. They are a residual
category, their 1,326 pairs outnumber every real bloc's put together, and the
difference between the two readings is the whole distance between "one bloc and
an unstructured remainder" and "one bloc that coheres twice as hard as seven
others that also cohere".
· *Figures 47, 48, 49 · `fig47_*.csv`, `fig48_*.csv`, `fig49_*.csv`*

**Voting together is not working together.** Ennahdha agrees most with Ettakatol
(0.79, above the chamber mean of 0.71) — the bloc it co-sponsored amendments
with at 0.65× the chamber rate. At the level of individual pairs the correlation
between agreement and ever co-sponsoring is **r = +0.14**: agreement explains
under 2% of the variance, and +0.11 within cross-bloc pairs alone, so it is not
simply bloc membership. This is why the dataset carries chosen and revealed tie
layers separately rather than treating either as a proxy for cooperation.
· *Figures 39, 40 · `fig39_*.csv`, `fig40_*.csv`*

**Polarised throughout, and no more so at the end than at the start — which are
two findings, not one.** Nugent's *After Repression* (2020) argues that Tunisia's
transition held because indiscriminate repression under Ben Ali left its
opposition comparatively unpolarised, where Egypt's narrowly-targeted repression
did not. That is a claim about a *level*, and a comparative one: testing it needs
Egypt, and this dataset has one chamber. What one chamber's roll calls can settle
is whether polarisation grew, and what its level looks like against the only
benchmark available — chance. Two measures, quarter by quarter, both read against
the same permutation null (each division's votes reshuffled among the members who
cast them, its margin held fixed):

- *Cross-cutting wins.* A coalition carrying more than half of Ennahdha's voters
  **and** more than half of everyone else's won **75%** of the 993 contested
  divisions. A bloc-blind chamber with the same margins gives **96%** — a
  70-30 division in a chamber that is 40% Ennahdha is carried inside both groups
  by arithmetic. The observed share is **20 points below chance**, and below it in
  every quarter.
- *Division similarity.* Mean |φ| between pairs of divisions, over the members
  voting in both and using no bloc labels at all, runs **two to four times** its
  null in every quarter.

So the chamber is polarised on both measures, which is what figures 21, 34 and 35
find by other routes. But neither deepens. The similarity excess **falls from
+0.27 to +0.11**, the three quarters carrying 73% of the term's contested business
are its three least structured, and the cross-cutting deficit ends at −15 points
against −13 at the start, at its widest mid-term rather than at the end.

Neither trend is an artefact of the later quarters being larger: cutting every
quarter to the smallest one's 17 divisions moves no excess by more than 0.03. Nor
of turnout: the permutation null tracks √(2/π·overlap) to within 0.003 everywhere,
which is what absorbs the fall in common voters from 118 per division-pair in
2014Q1 to 52 in 2014Q3.

**What it does not establish.** The level implication of Nugent's argument, which
is comparative and needs a second case. Not her mechanism — repression type
shaping perceived distance — which roll calls cannot reach. Roll-call behaviour is
disciplined and agenda-conditioned, so behavioural cooperation and attitudinal
polarisation are different constructs. And the NCA is where the consensus outcome
was produced, so cross-cutting votes in it confirm the outcome was real rather
than explain it.
· *Figure 46 · `fig46_cooperation_over_time_nca2011.csv`*

**What none of this establishes.** Agreement is a correlation between voting
records, not an act: two opponents both backing an uncontroversial motion are
"tied" in the same sense two allies are. The layer covers one chamber, because
only NCA-2011 has a roll-call record. Bloc is each member's last recorded spell
applied to the whole term, which matters in a chamber where 105 of 217 changed
party. And participation falls from 18% to 56% not voting across the term
(figure 25), so later windows describe a smaller and more selective slice.

---

## 10. The upper house of 2005–2011

The Chamber of Advisors is the only chamber in this dataset that was *designed*
rather than elected: two-thirds returned indirectly by local councils and
professional bodies, one-third appointed by the President. Its own site was
archived before it died with the chamber, and reading it closes the last empty
chamber-term of the period. What follows is what a roster alone can support —
there is no biography, no party, no vote and no attendance for this chamber
anywhere, so nothing below is about behaviour.

**The seat counts reconcile exactly, which settles a figure the frame had
flagged.** 43 governorate representatives + 28 professional-organisation
representatives + 41 presidential appointees = 112, the chamber's nominal size,
split 71 selected to 41 appointed. `assemblies.csv` had carried "112 at creation
and 126 after the 2008 partial renewal; both figures require verification"; the
chamber's own pages in 2010, two years after that renewal, list 112.
· *`mandates.csv` filtered to `ADV-2005`*

**A third of the chamber represented "professional organisations", and labour is
not among them.** The 28 professional seats sit in exactly two colleges of 14 —
employers (`المنظمة المهنية للأعراف`) and farmers (`المنظمة المهنية للفلاحين`).
The chamber's own page has no column for a workers' organisation. Whether seats
for one were never allotted or were allotted and left unfilled, the site does not
say; what is observable is that the corporatist third of Tunisia's upper house
was capital and agriculture, with no labour representation listed.
· *`constituencies.csv` filtered to `ADV-2005`*

**Every under-represented governorate is an interior one.** Nineteen governorates
return two advisors and five return one — Kebili, Siliana, Tataouine, Tozeur and
Zaghouan. All five are non-littoral. All thirteen coastal governorates return
two. That is consistent with a population rule rather than a coastal bias, since
those five are also the least populous, and this dataset cannot separate the two
readings — but the *effect* is that every reduced seat falls in the interior, on
exactly the cleavage the post-2011 politics of regional inequality runs along.
· *`constituencies.csv`, `magnitude` column*

**It shares one member with the rest of the dataset and none after 2011.** Rachid
Sfar, prime minister in the 1980s and a member of the 1986 Chamber of Deputies,
appears in the upper house's appointed third. No advisor sits in any chamber
after the revolution. That is a striking zero, and it is worth almost nothing as
evidence: the lower house sitting beside this one has no roster, so the dataset
cannot see the population where continuity would be most likely.
· *Figure 10 · `fig10_chamber_overlap.csv`*

**Seven seats change hands in a window that contains the dissolution.** Between
captures of 21 August 2010 and 1 September 2011, six of the 41 appointed slots go
blank on the chamber's own page and a seventh changes hands. The dissolution of
23 March 2011 falls inside that window, so the site cannot say whether those
seats were vacated while the chamber sat or the page was edited after it ceased
to exist. Those mandates end on an empty date with `exit_mode = unknown` and the
interval in `mandates.notes`. The chamber's alphabetical index, a separately
maintained page, agrees exactly — it lists 106 names and omits precisely those
seven.
· *`mandates.csv`, `notes` column*

---

## 11. What the dataset says about itself

**Career data is the thinnest layer and should be treated as a lead, not
evidence.** 171 roles for 114 people — 13% of the dataset — all from one source,
the 2011 assembly's narrative biographies, all rule-extracted from French prose
rather than hand-coded. Education (46) and the judiciary (36) lead. Nothing here
supports a claim about recruitment into Tunisian parliament generally, and
hand-coding these rows is the repository's standing request.
· *Figure 30 · `fig30_career_sectors.csv`*

**Fields are not equally sourced, and the difference is large.** `name_ar` and
`assembly_id` draw on all six collectors; `birth_date`, `biography_ar`,
`marital_status` and `languages` each rest on one. Any individual cell has one
source, but a field supported by six independent collections is a different
object from one resting on a single observatory's biographies, and a reader
quoting two columns of the same table should know which is which. Height there
is coverage and not accuracy — `gender` appears at full height for the 2011
chamber because the inference returned a value for everyone, not because it was
published.
· *Figure 32 · `fig32_provenance_by_source.csv`*

---

## What this dataset cannot support

Stated plainly, because the absences are as important as the findings.

- **Any claim about parliamentary elites 1959–2011.** Eleven chambers across the
  single-party and Ben Ali eras have no roster — the upper house of 2005–11 is
  the one exception, and it has a roster and nothing else. Elite continuity
  across the revolution is unmeasurable here: the lower house sitting through
  2011 is exactly the chamber still missing.
- **Comparative participation rates across chambers.** Denominators are
  published for ARP-2019 and recorded, so rates there are checkable; for the
  other chambers they are not, and a rate without its denominator cannot be
  compared to one with a different denominator.
- **Fine-grained committee timing for 2014–2019.** The committee panel is
  continuous now, but that chamber's spells come from diffing twelve web
  captures, so 803 of 985 have bracketed boundaries and the recorded span is an
  outer bound. Co-membership over the whole term is sound; anything that slices
  the term into months is not.
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
- **Anything behavioural about the upper house of 2005–11.** Its site published
  a roster and not member profiles: no dates of birth, no parties, no
  biographies, no attendance and no votes exist for that chamber anywhere. Even
  its members' sex is unrecorded, so it is absent from every figure that splits
  by sex.
- **Causal claims from any of the above.** These are descriptive results on
  observational data with a non-random coverage gap.

---

*Regenerate every number here with `make figures`; §7 with
`python examples/surname_persistence.py`; each figure writes its own
table. Method and design notes are in [`figures/README.md`](../figures/README.md);
the network layer's construction is in [NETWORK_GUIDE.md](NETWORK_GUIDE.md);
variable definitions are in [CODEBOOK.md](CODEBOOK.md).*
