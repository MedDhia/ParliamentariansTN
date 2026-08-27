# Figures

Twenty descriptive and exploratory figures over the dataset. Each is a
standalone script that writes one image and one CSV:

```
figures/figNN_name.py  →  figures/output/figNN_name.png
                          figures/output/figNN_name.csv
```

```bash
make figures                          # render all twenty
python figures/make_all.py 11 12      # just those two
python figures/fig11_bloc_composition_arp2014.py   # or run one directly
FIGURES_PDF=1 make figures            # also write PDFs, for LaTeX
FIGURES_DARK=1 make figures           # dark-surface variants
```

Rendering the set takes about 25 seconds and needs `matplotlib` and `networkx`
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
| 14–16 | Committee co-membership, one chamber each | Dense (0.14–0.21). Blocs are interspersed, not segregated — committee ties are not simply bloc ties. |
| 17 | Deputies × committees, bipartite | The sparse structure the projections are derived from. Start here if tie strength matters to your argument. |
| 18 | Written-question co-signature | The only *behavioural* network. 41 of 155 deputies never co-signed anything. |

**Behaviour**

| | Figure | What to look at |
| --- | --- | --- |
| 19 | Attendance vs voting, ARP-2019 | The gap between turning up and voting, which is not uniform. |
| 20 | Written questions filed | The most unequal distribution in the dataset. |

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
