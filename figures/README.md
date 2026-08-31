# Figures

Forty-six descriptive and exploratory figures over the dataset. Each is a
standalone script that writes one image and one CSV.

**Looking for the results rather than the method?**
[`docs/FINDINGS.md`](../docs/FINDINGS.md) collects what these figures show, with
the number and the file to check it in. This file is about how they are built.

```
figures/figNN_name.py  →  figures/output/figNN_name.png
                          figures/output/figNN_name.csv
```

```bash
make figures                          # render all forty-six
python figures/make_all.py 11 12      # just those two
python figures/fig11_bloc_composition_arp2014.py   # or run one directly
FIGURES_PDF=1 make figures            # also write PDFs, for LaTeX
FIGURES_DARK=1 make figures           # dark-surface variants
```

Rendering the set takes about a minute and needs `matplotlib` and `networkx`
(`pip install -r requirements-figures.txt`). Nothing here touches the network or
regenerates the dataset — figures read `data/processed` and `data/networks`.

## The catalogue

**Institutions and coverage**

| | Figure | What to look at |
| --- | --- | --- |
| 1 | Institutional timeline | Nineteen chamber-terms; blue where members are recorded individually, grey where only the institution is. The faded tails are terms a chamber was seated for but never served. |
| 2 | Chamber size | Seats climb 98 → 217 over fifty-five years, then fall to 161 in 2023 — the only sustained contraction. |
| 3 | Women's share | 31% → 35% → 27% under list PR with parity; **16%** in the single-member districts of 2023. |
| 4 | Coverage vs seats | The honesty figure. Read it before the rest. |

**Composition**

| | Figure | What to look at |
| --- | --- | --- |
| 5 | Professions, ARP-2014 | Lawyers and teachers dominate; almost no one from agriculture. |
| 6 | Regional origin | Shares by region and chamber. The "Abroad" column is a post-2011 novelty that collapses in 2023. |
| 7 | Birth years, NCA-2011 | The only chamber with real birth dates. |
| 8 | Chambers served | Log scale, because nearly everyone sits once. |

**Elite circulation**

| | Figure | What to look at |
| --- | --- | --- |
| 9 | Continuity across chambers | No chamber draws even a quarter of its members from its predecessor; 2023 draws 3%. |
| 10 | Shared members, all pairs | Every pair, so the non-consecutive overlaps are visible. Read a cell as "sat in both", not as a skip count: 13 sat in 2011 and 2019, but 12 of them also sat in 2014. |

**Bloc dynamics, 2014–2019**

Only possible because that chamber was recovered from ~29 monthly Internet
Archive captures, which turn bloc membership into dated spells.

| | Figure | What to look at |
| --- | --- | --- |
| 11 | Bloc composition, month by month | Nidaa Tounes enters with 86 seats and bleeds out; the winning party is not the largest bloc by the end. |
| 12 | Effective number of blocs | Fragmentation rises from 3.6 to 5.3, all of it from Nidaa Tounes splitting. |
| 13 | Bloc-to-bloc moves | 108 of the 238 members with a recorded bloc history moved. Nidaa's members disperse rather than relocating together. |

**Networks**

| | Figure | What to look at |
| --- | --- | --- |
| 14–16 | Committee co-membership, one chamber each | Which committees a deputy bridges, and how little that tracks her bloc: assortativity −0.03, −0.04, −0.07. |
| 17 | Deputies × committees, bipartite | The 247 memberships behind figure 16's 1,579 ties, in figure 16's exact coordinates. |
| 18 | Written-question co-signature | A *behavioural* network — and the contrast: +0.18. 41 of 155 deputies never co-signed anything. |
| 22 | Amendment co-sponsorship, bloc × bloc | The same contrast in the 2011 chamber, twelve years earlier. Every off-diagonal cell in Ennahdha's row is below the chamber rate; no other bloc's is. |
| 41 | Committee co-membership, ARP-2014 | The fourth panel of 14–16, missing until the chamber's committee pages were pulled out of the Internet Archive. Densest of the four by far (0.45): 219 of 231 deputies bridge committees, at 4.3 each. |

**Reading 14–17 and 41.** These are not force-directed drawings. A committee
co-membership network is a projection, and the projection is *exactly* the union
of the committee cliques — every tie in NCA-2011 and ARP-2019 is reproduced by
taking each committee and joining all its members. A spring layout of overlapping
cliques is a hairball whose only content is the roster it came from, so position
is computed instead:

- **angle** — which committees. They are anchored around the rim, ordered by
  spectral seriation so committees sharing members sit near each other.
- **distance from the centre** — how many. One committee puts a deputy on the
  rim; each further one pulls her in, so the biggest bridges are in the middle.
- **identical portfolios sit together**, being computed from the same set.

Only ties of weight ≥ 2 are drawn, bundled toward the centre; the weight-1 mass
is what the lobes already say. Nothing is seeded, so the drawing never drifts
between runs. Figure 41 draws weight ≥ 4 instead, and says so in its subtitle:
the 2014 chamber's projection has 11,940 ties and at the usual threshold its
centre renders as solid ink. Density and assortativity there are still computed
over every tie — only the drawing is thinned.

**The finding these figures are for.** Colour is bloc, position is committee, so
the figures answer whether committee assignment follows bloc lines. It does not —
assortativity is slightly *negative* in all four chambers, including the 2014
chamber whose coalition fell apart mid-term. Co-signing a written question, which
a deputy chooses rather than is assigned, runs **+0.18**. Assigned ties ignore
bloc; chosen ties follow it.

Committee names for NCA-2011, ARP-2014 and ARP-2019 exist only in Arabic and so
cannot be drawn (see the Arabic rule below); those rims carry keys like
"Standing 7", and the companion CSV has a `committee_labels` column that resolves
them.

**Behaviour**

| | Figure | What to look at |
| --- | --- | --- |
| 19 | Attendance vs voting, ARP-2019 | The gap between turning up and voting, which is not uniform. |
| 20 | Written questions filed | The most unequal distribution in the dataset. |
| 27 | Activity inequality, Lorenz | Amendments (2011) and questions (2023) on one axis: Gini 0.43 against 0.51. Two chambers, two activities, different shapes. |
| 29 | Women in committee leadership | An underpowered null. Every point estimate runs against women; every interval overlaps. 54 female memberships in 2023 cannot resolve it. |
| 30 | Career sectors | Teachers and judges — from the 13% of the dataset with any career recorded, all of it rule-extracted from one chamber's prose. |

**The 2011–2014 roll-call record**

370,922 positions across 1,724 divisions, the only chamber with a division-level
voting record. Read 25 and 26 before 21 and 23: they say how much of the chamber
the record covers and how much of it was contested.

| | Figure | What to look at |
| --- | --- | --- |
| 21 | Roll-call scaling | The positions reduced to two dimensions, faceted per bloc. Ennahdha at one pole and every other bloc at the other, its own Troika partners included. |
| 23 | Bloc cohesion, Rice index | Every bloc votes together most of the time — but bloc size bounds the measure, so the ordering is as much arithmetic as discipline. |
| 24 | The voting calendar | Two-thirds of the record falls in three months. Nine months pass after the election before the first recorded division. |
| 25 | Participation decay | 18% of members not voting in July 2012; 56% across the last three months. This is the coverage behind 21 and 23. |
| 26 | Vote margins | 42% of divisions clear a 0.95 margin — the cut figure 21 makes before scaling, shown rather than asserted. |

**Polarisation, 2011 Constituent Assembly (33–40, 42–46)**

Twelve figures asking one question in twelve ways: how far do the lines this
chamber divided on coincide with its bloc boundaries? Six are built on
`edges_vote_agreement.csv`, a layer derived for this set — every pair of members
scored on the share of *contested* divisions they voted the same way. Read
`docs/NETWORK_GUIDE.md` before using it: it is revealed rather than assigned or
chosen, near-complete rather than sparse, and its weight is a rate rather than a
count, so it does not behave like the other layers.

| | Figure | What to look at |
| --- | --- | --- |
| 33 | Agreement distribution | Within-bloc 0.84 against cross-bloc 0.67, Cohen's d 1.36 — yet 92% of cross-bloc pairs still agree more often than not. Both facts at once. |
| 34 | The agreement network | Ennahdha's internal density is **0.998** — 3,735 of 3,741 possible pairs. The other 130 members sit at 0.269. One clique and one cloud. |
| 35 | E-I index against a size-matched null | The figure that corrects itself: raw E-I says the small blocs are outward-looking, the null says that is arithmetic. Seven of eight cohere; Ennahdha by eight times the median margin. |
| 36 | Communities vs blocs | Louvain, told nothing about blocs, returns Ennahdha at 88% purity. Modularity 0.21 — below the usual 0.3 threshold, so this is not really a community structure. |
| 37 | Cross-bloc brokers | Ennahdha members agree widely and inwardly; everyone else outwardly. The dashed lines are what bloc size alone forces, so read distance from them. |
| 38 | Polarisation over the term | Six windows of equal contested divisions. The gap holds between 0.15 and 0.20 throughout — the chamber starts divided and stays that way. |
| 39 | Bloc × bloc agreement | Figure 22's form on revealed rather than chosen ties. Ennahdha agrees most with Ettakatol (0.79) — the partner it co-sponsored with least (0.65×). |
| 40 | Agreement vs co-sponsorship | r = +0.14. Voting together explains under 2% of whether a pair ever co-sponsored. |
| 42 | Nearest-alignment network | Each member joined to their three closest allies, edges weighted by alignment level. 73% stay inside the member's bloc against a 24% baseline — but Ennahdha, highest on the raw share, has the **lowest** lift over chance. |
| 43 | The Brahmi assassination | An event study on 25 July 2013. The crisis is a walkout, not a realignment: Democratic Bloc turnout 51% → 21%, Ennahdha 79% → 80%, everyone back by December. Affinity has no comparable estimate during it — **0 of 18** Democratic Bloc members appear in a scoreable pair. |
| 44 | Affinity before the shock | The baseline the crisis has to be measured against: within-bloc agreement 0.930, cross-bloc 0.672, and 1,209 of 4,792 strong ties crossing a bloc. |
| 45 | Affinity after the shock | Same members, positions, threshold and division count. Within-bloc agreement falls to 0.879 and cross-bloc does not move — blocs **loosened** rather than closing ranks. Reliable cross-bloc allies fall 63%. |
| 46 | Polarisation, level and trend | Against Nugent (2020). Level and trend disagree: cross-cutting wins take 75% of contested divisions where a bloc-blind chamber gives **96%**, so the chamber is 20 points of bloc structure below chance — but nothing deepens, the similarity excess falling +0.27 → +0.11. "No build-up" is not "none". |

**Why these are thirteen figures and not one.** Polarisation has no single
operationalisation, and the measures disagree in informative ways: 33 says the
chamber is strongly bloc-structured, 34 says only one bloc is, 36 says the
structure is too weak to call communities, 38 says none of it moves over time,
42 says every bloc is distinctive once you ask who its members are *closest* to
rather than who they merely agree with, 43 says the chamber's worst political
crisis left no trace in any of it — because the members it silenced are the ones
the measure needs — and 46 says level and trend answer differently — bloc
structure well beyond chance on both its measures, and thinning rather than
hardening across the term.

**44 and 45 are the pair that answers what 43 could not.** 43's affinity panel
was 90% Ennahdha and 6% Democratic Bloc, because matching the windows on
*divisions* left the post window four days long. Matching on *sitting days*
instead gives 32 days either side, 196 of 217 members and 16 of the 18 Democratic
Bloc, which is enough to compare the networks properly. The answer is that
neither standard account holds: within-bloc agreement fell and cross-bloc
agreement held, so blocs loosened rather than closing ranks. A single number would have had to
pick one of those. Two of the nine exist mainly to stop the others being
over-read — 35's null and 40's correlation both say "less than it looks".

**Why 34 and 42 are both here.** They draw the same layer and answer different
questions, and the difference is forced by the data rather than chosen. The
agreement graph is 99.6% complete with weights packed around 0.71, so a
threshold (34) has very little room to work and the disparity filter — the
standard weighted-backbone method — extracts nothing at all. 42 therefore asks a
question a threshold cannot express: not "who agrees above a cut" but "who does
each member agree with most". That reframing is what makes the small blocs
visible; on 34 they are indistinguishable cloud.

**Party, constitution and provenance**

| | Figure | What to look at |
| --- | --- | --- |
| 28 | Party switching, NCA-2011 | 105 of 217 ended the term in a different party. Undated from/to pairs, so a lower bound on moves. |
| 31 | Contested constitutional articles | The preamble drew 19 amendments, twice any single article. Bars split by how many members co-signed. |
| 32 | Provenance by field | Which source stands behind which column. Names draw on all five collectors; birth dates on one. |

**Why 21 is faceted, 22 is a matrix, 42 labels instead of colouring, 43 leaves a
panel blank, and 44–45 share one frame.** Five cases where the obvious form
fails. Eight blocs is five past the all-pairs colour cap, so 21 repeats the whole
chamber in grey behind one highlighted bloc per panel rather than putting eight
hues in one point cloud. And the 2011 amendment network has a density of 0.40 —
9,361 of 23,436 possible pairs — so a node-link drawing of it is a solid disc;
22 shows the same ties as bloc-by-bloc mixing instead. And 42 needs to name
eight blocs on one canvas, so it colours three and gives the rest a direct label
on each bloc's *medoid* — the member nearest its centre, which guarantees the
label sits on a real node instead of in the empty space a centroid can fall
into. The non-attached get no label at all: their spread is twice that of any
real bloc, so no point on the drawing stands for them. None of these is a
stylistic preference — in each case the discarded form would have shown less, or
would have shown something untrue.

46 is the one that had to give up a variable to say anything. Every other figure
in this block uses bloc labels; this chamber's are undated, one spell per member
across a term in which 105 of 217 changed party, so a longitudinal series built
on them measures the end-of-term map applied backwards. Panel B therefore uses no
labels at all — it asks whether the same line keeps reappearing across pairs of
divisions — and panel A uses the single distinction the argument is about and the
one that barely moves. What the pair loses in resolution it gains in being about
the period it is plotted against.

44 and 45 are the case where the obvious form fails *silently*. Two network
drawings laid out independently are not comparable: a force simulation moves
nodes for its own reasons, and a reader has no way to tell that from a change in
the chamber. So the pair shares one panel, one set of coordinates, one threshold
and one division count, computed once in `_crisis.py`. The last of those is the
one that would have been easiest to miss — agreement is a rate, and a rate from
94 divisions clears a threshold by chance more often than one from 417, which
would have manufactured exactly the thinning figure 45 reports.

43 is the strongest version of that last point. Its middle slot *could* carry a
number: 4,259 pairs clear the scoring floor during the crisis months, which is
plenty to average. But zero of the eighteen Democratic Bloc members are in any of
them and 52% are Ennahdha with Ennahdha, so the number would describe the
governing side's internal cohesion while wearing the chamber's name. Leaving the
slot empty and printing why is the only reading that does not mislead.

**Three figures exist to qualify other figures.** 25 and 26 are the coverage and
contestedness behind the roll-call analyses, and 32 is the provenance behind
every variable in the dataset. They are not decoration: figure 21 drops 42% of
divisions and figure 23 measures discipline only among members who turned up, and
a reader who does not know the size of those exclusions will over-read both. The
set treats "here is the caveat, drawn at the same resolution as the claim" as
part of the argument rather than a footnote.

## Design rules these figures follow

The method is from the `dataviz` skill; what matters for reading and extending
the set is the following.

**Form before colour.** The data's job picks the chart type. Sequential
single-hue for magnitude, categorical only when the series *are* the subject,
emphasis (one hue plus grey) when one series is the point.

**The palette is validated, not chosen.** The categorical order is a documented,
CVD-tested sequence, run through the validator rather than eyeballed. Two caps
follow and `_style.categorical()` enforces them by raising:

- **all-pairs forms — scatter, network node colour, choropleth — cap at three
  classes.** Past three, the fourth slot puts yellow beside orange and fails the
  separation floor. Fold the tail into "Other" or facet.
- adjacent forms — stacked areas, grouped bars, lines — may use up to eight, with
  direct labels mandatory from four.

Never solve "too many series" by generating another hue.

**Sequential for magnitude, diverging for departure.** `_style.sequential()` is
one hue light→dark. `_style.diverging()` is for a value read against a reference
— figure 22's ratios against the chamber-wide rate — and takes the *signed* log
departure plus a symmetric limit, so 2× and ½× land the same distance from
neutral. Its poles are the categorical blue and orange with a near-surface
neutral between them: two hues and a grey midpoint, never a hue at the middle and
never a rainbow. It returns the ink colour with the fill, chosen against the fill
rather than the surface, so a pale cell takes dark ink in either mode.

**Every figure ships a table.** `figNN_name.csv` beside the PNG. This is the
accessible twin of the chart (three light-mode palette slots sit below 3:1
contrast, and a table view is the documented relief), and for a research
repository it is how a reader checks a number without re-deriving it. Where the
chart folds a tail into "Other", the table carries the *unfolded* distribution
and a column saying where each category was drawn — folding is a drawing
decision, and a table that folds too puts the tail out of reach.

**No dual axes, ever.** Two measures of different scale get two figures. That is
why fragmentation (fig 12) is separate from composition (fig 11).

**Arabic is never rendered.** Matplotlib has no Arabic shaping or bidi, so it
would draw disconnected letters in reversed order — worse than an error, because
it looks like a rendering. `_style.label()` therefore *raises* on Arabic, and
`_labels.py` holds short English display glosses. The Arabic in
`data/processed` stays authoritative; the glosses are display-only and are not
data. A missing gloss fails the build rather than shipping broken glyphs.

**Missingness is stated on the figure.** Every subtitle carries n and the
relevant caveat, because a figure travels without its caption. Where a variable
is inferred rather than recorded — sex for the 2011 chamber, from French
grammatical agreement — the figure says so.

## Layout of the code

```
_style.py     palette, chrome, the Arabic guard, save() and the table contract
_labels.py    Arabic → English display glosses (blocs, professions, chambers)
_blocs.py     bloc-spell helpers: monthly panel, effective number, transitions
_network.py   shared drawing for the three committee networks
figNN_*.py    one figure each; docstring explains the form choice and the caveats
make_all.py   discovers and runs them in subprocesses
```

Each figure's docstring is the place its choices are argued, including the ones
that were tried and rejected — figures 14–16 record why the strong-tie filter was
dropped, and 9 why the ribbons were.

## Two caveats that apply to the whole set

**Coverage is uneven and not random.** Five chambers have person-level data;
eleven have only their presiding officer. Any figure aggregating "Tunisian
parliamentarians" is describing 1956, 2011–14, 2014–19, 2019–21 and 2023–.
See `docs/COVERAGE.md`.

**Two totals for written questions, both correct.** The chamber's database holds
**6,332 distinct questions** (figure 18's co-signature network), but per-deputy
filings sum to **6,603** (figure 20), because 78 questions carry more than one
signatory and each signer is credited. Likewise, `bipartite_person_committee`
carries one row per *role* and per dated spell, so counting its rows overstates
how many committees a deputy sits on — count distinct committees.

**The 2014–2019 bloc figures rest on bracketed dates.** Spell boundaries are
located to the interval between two web captures, not to the day, and the monthly
panel totals 212–220 against 217 seats — that spread is the reconstruction's
error, shown rather than smoothed away. Read trends, not individual months.
