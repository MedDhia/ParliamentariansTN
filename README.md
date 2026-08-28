# ParliamentariansTN

A relational dataset of Tunisian parliamentarians from the 1956 Constituent
Assembly to the sitting chamber, built for social science and network analysis.

The dataset covers **nineteen chamber-terms across seventy years**, **856
individual parliamentarians**, and **959 mandates**, with committee memberships,
parliamentary blocs, constituencies, biographical attributes, extra-parliamentary
careers, and behavioural indicators — assembled from the chamber's own database,
both of Al Bawsala's observatories, and archival reconstruction, with cell-level
provenance for every value.

It is also, deliberately, honest about what it does not have. Fourteen of the
nineteen chambers — the whole single-party era plus both upper houses — are
present as institutions but not as people. See [Coverage](#coverage) before using
it comparatively, and [Findings](docs/FINDINGS.md) for what the covered chambers
show.

## Start here

| If you want to… | Go to |
| --- | --- |
| **See what the data shows** | [docs/FINDINGS.md](docs/FINDINGS.md) — every result, with the file to check it in |
| **Look at the figures** | [figures/output/](figures/output/) — 20 PNGs, each beside its CSV |
| **Know what a column means** | [docs/CODEBOOK.md](docs/CODEBOOK.md) — every variable, with fill rates |
| **Know which chambers are usable** | [docs/COVERAGE.md](docs/COVERAGE.md) — completeness by chamber. **Read before comparing across time.** |
| **Use the network layer** | [docs/NETWORK_GUIDE.md](docs/NETWORK_GUIDE.md), then [examples/](examples/) |
| **Judge a source** | [docs/SOURCES.md](docs/SOURCES.md) — what each one is, and what it gets wrong |
| **Rebuild or extend it** | [Reproducing](#reproducing) below, then [docs/RECONSTRUCTION_PROTOCOL.md](docs/RECONSTRUCTION_PROTOCOL.md) |
| **Just load the tables** | `data/processed/*.csv` — 17 UTF-8 CSVs, committed and ready |

Everything under `docs/` is indexed in [docs/README.md](docs/README.md).

## Why this exists

Tunisia is the central case in the comparative literature on democratisation and
autocratisation in the Arab world, and its parliament is the institution that
carried the transition and then registered its collapse. But no dataset lets you
follow parliamentary elites across that span. The chamber's own database begins
in 2011 and hides closed terms; the civic observatories that covered each
democratic term were built separately and one of them has been taken offline; the
single-party era is on paper. Anyone studying elite survival, recruitment, or the
networks that structure legislative behaviour has had to rebuild the data from
scratch each time.

## Quickstart

```bash
git clone https://github.com/MedDhia/ParliamentariansTN
cd ParliamentariansTN
pip install -r requirements.txt

# The built dataset is committed, so you can use it immediately:
python -c "import csv; print(len(list(csv.DictReader(open('data/processed/persons.csv')))))"

# Or rebuild everything from cached staging data (no network required):
make build validate networks codebook

# Or re-collect from upstream (~15 minutes, rate-limited):
make collect
```

Worked examples: `examples/example_python.py` (networkx) and
`examples/example_r.R` (igraph).

Twenty descriptive and exploratory figures, each with its numbers as a companion
CSV, are in [`figures/`](figures/README.md):

```bash
pip install -r requirements-figures.txt
make figures        # -> figures/output/figNN_name.png + .csv
```

**[docs/FINDINGS.md](docs/FINDINGS.md) collects what the figures show** — the
results in one place, each with the number and the file to verify it in. Start
there if you want the substance before the method.

## What is in it

Seventeen tables in `data/processed`, all UTF-8 CSV with a header row.

| Table | Rows | Unit |
| --- | --- | --- |
| `assemblies` | 19 | one chamber-term, 1956–present |
| `persons` | 856 | one parliamentarian |
| `mandates` | 959 | one person × one chamber × one spell of service |
| `constituencies` | 260 | one constituency × one chamber |
| `governorates` | 25 | 24 governorates + out-of-country |
| `parties` | 70 | political parties, with succession links |
| `party_affiliations` | 217 | dated party membership |
| `blocs` | 40 | parliamentary bloc × chamber |
| `bloc_memberships` | 1,116 | dated bloc membership |
| `committees` | 54 | committee × chamber |
| `committee_memberships` | 1,129 | dated committee membership with role |
| `offices` | 47 | speaker, vice-speaker, bureau tenures |
| `careers` | 171 | extra-parliamentary roles |
| `participation` | 583 | attendance, voting, written questions |
| `person_xref` | 950 | crosswalk to every upstream identifier |
| `sources` | 6 | source register with access conditions |
| `provenance` | 5,039 | which source supplied which field of which record |

Plus eight network files in `data/networks` — node attributes, two bipartite
incidence lists, and five one-mode projections. See
[docs/NETWORK_GUIDE.md](docs/NETWORK_GUIDE.md).

Full variable definitions with fill rates: [docs/CODEBOOK.md](docs/CODEBOOK.md).

## Four design decisions worth knowing

**Persons and mandates are separate.** A deputy returned three times is one row
in `persons` and three in `mandates`. Collapsing them is the most common error in
legislator datasets and it silently destroys any analysis of re-election or
elite persistence.

**Affiliations are dated spells, not snapshots.** A deputy who leaves a bloc
mid-term produces two rows, not one overwritten value. Where a *source* only
publishes a snapshot, that is recorded as a limitation rather than presented as
a spell — see the notes on bloc switching in
[docs/COVERAGE.md](docs/COVERAGE.md).

**Empty means "not recorded", always.** Never zero, never false, never "probably
around then". Dates known only to the year are stored as 1 January with a
companion `*_precision` column saying so. The Chamber of Advisors has an empty
`start_date` because its first sitting could not be established, and inventing a
plausible date would have been worse than leaving it blank.

**Names are bilingual.** No romanisation of Tunisian Arabic names is
authoritative — the chamber, Al Bawsala and the electoral commission spell the
same name three ways. Every person carries an Arabic form and a Latin form, with
source-supplied romanisations preferred and machine transliteration used only as
a flagged fallback. Cross-source matching runs on a normalised Arabic key.

## Coverage

Person-level data exists for five chambers. The rest are institutional frame
only.

| Chamber | Period | Seats | Mandates | Status |
| --- | --- | --- | --- | --- |
| ANC-1956 | 1956–1959 | 98 | 108 | full |
| NA-1959 → COD-2009 (12 chambers) | 1959–2011 | 90–214 | 1–3 each | frame only |
| ADV-2005 | 2005–2011 | 112 | 0 | frame only |
| NCA-2011 | 2011–2014 | 217 | 217 | full |
| ARP-2014 | 2014–2019 | 217 | 246 | full |
| ARP-2019 | 2019–2021 | 217 | 216 | full |
| ARP-2023 | 2023– | 161 | 155 | full |
| CNRD-2023 | 2024– | 77 | 0 | frame only |

The democratic period is a **continuous panel** (NCA-2011 → ARP-2014 → ARP-2019
→ ARP-2023): 84 people appear in more than one chamber and 16 in three or more.
The 2014–2019 term was recovered from Internet Archive captures of an Al Bawsala
observatory the live site no longer serves — see
[docs/SOURCES.md](docs/SOURCES.md).

Two consequences you cannot design around:

- **`n_mandates` is biased downward** for anyone who served before 2011. Someone
  elected in 1994 and again in 2011 shows one mandate, because the 1994 chamber
  has no roster. The bias is systematic, not noise.
- **ARP-2014 has no committee data**, so a committee-network panel still has a
  hole in the middle even though the mandate panel does not. Its archived
  committee pages are the cheapest remaining win.

Closing the remaining gaps is archival work, and
[docs/RECONSTRUCTION_PROTOCOL.md](docs/RECONSTRUCTION_PROTOCOL.md) specifies how
to do it so the rows merge cleanly: which JORT series to consult, how to code
entry and exit modes, and the priority order.

## Sources

| Source | Covers | Access |
| --- | --- | --- |
| `arp.tn` (chamber's own Odoo backend) | ARP-2023 | Public JSON-RPC, read-only |
| `majles.marsad.tn` (Al Bawsala) | ARP-2019 | HTML |
| `majles.marsad.tn/2014` via Internet Archive | ARP-2014 | Wayback CDX + raw captures |
| `marsad.tn` (Al Bawsala) | NCA-2011 | HTML |
| Arabic Wikipedia | ANC-1956 | MediaWiki API |
| Curated in `reference.py` | all 19 chambers | hand-coded |

The chamber's website exposes the same JSON-RPC endpoint its own public pages
use, which yields structured records rather than scraped markup — including a
bilingual name for every sitting member. Only models the public site itself
queries are read; Odoo's access-control layer is respected rather than probed,
and personal contact details are not carried into the published tables even
where the upstream field is readable.

Each source's reliability, quirks and known errors are documented in
[docs/SOURCES.md](docs/SOURCES.md), including the upstream contradictions the
pipeline reports rather than papers over.

## Reproducing

```
make collect     # run all five collectors -> data/raw/staging_*.json
make build       # merge staging -> data/processed/*.csv
make validate    # schema, referential integrity, date logic, substance
make networks    # derive data/networks/*.csv
make codebook    # regenerate docs/CODEBOOK.md and docs/COVERAGE.md
make all         # build, validate, networks, codebook
make test        # unit tests
make figures     # render figures/ (needs requirements-figures.txt)
```

Every upstream response is cached in `data/raw`, so a rebuild needs no network
and upstream servers are hit once per object rather than once per run. Collection
is rate-limited to roughly one request per second and identifies itself in the
`User-Agent`. The cache is gitignored; the staging documents are committed, so
`make build` works on a fresh clone.

`make validate` exits non-zero on any error and is usable as a CI gate. It
distinguishes errors (dangling keys, duplicate keys, values outside a declared
vocabulary, end dates before start dates) from warnings — things that look wrong
but may be true of the world, like a chamber having more mandates than seats
because members were replaced mid-term.

## Layout

```
data/
  reference/    curated frame: assemblies, governorates, parties
  raw/          cached upstream responses (gitignored) + staging documents
  processed/    the 17 analysis-ready tables
  networks/     node attributes, bipartite lists, projections
docs/
  README.md                 index: which document answers what, and in what order
  FINDINGS.md               what the data shows, with the file to check each number in
  CODEBOOK.md               generated: every variable, with fill rates
  COVERAGE.md               generated: completeness by chamber and attribute
  SOURCES.md                what each source is, and what it gets wrong
  NETWORK_GUIDE.md          what each network layer means, and its traps
  RECONSTRUCTION_PROTOCOL.md how to close the 1959-2011 gap
src/parliamentarians_tn/
  schema.py     single source of truth for all tables and vocabularies
  ids.py        Arabic name normalisation, romanisation, ID minting
  io.py         paths, CSV round-tripping, cached rate-limited HTTP
  reference.py  the hand-curated institutional frame
  collect/      one module per source
  build.py      entity resolution and table assembly
  validate.py   schema and substantive checks
  networks.py   network derivation
  codebook.py   documentation generation
examples/       worked analyses in Python and R, runnable on the committed data
figures/
  figNN_*.py    one figure each, numbered in reading order
  _*.py         shared: style and palette, label glosses, bloc and network helpers
  output/       figNN_name.png beside figNN_name.csv (the table view)
tests/          unit tests
```

Reading the tree: anything with a leading `_` is shared machinery rather than a
thing to run, and anything generated is marked as such where it is listed.
`data/raw` holds the cached upstream responses (gitignored) plus the staging
documents (committed), which is why `make build` works offline on a fresh clone.

`schema.py` is the single source of truth: the builder, the validator, the
network derivation and the codebook all read the same column declarations, so
documentation cannot drift from the data.

## Figures

[`figures/`](figures/README.md) holds twenty figures over the dataset —
institutional timeline, composition, coverage, elite circulation, bloc dynamics,
four network views, and behavioural distributions. Each script writes one PNG and
one CSV, so every figure states its own numbers.

Three conventions worth knowing: **no figure renders Arabic** (matplotlib has no
shaping or bidi, so `_style.label()` raises and `_labels.py` supplies short
English glosses — the Arabic in the data stays authoritative); **node colour in
the network figures is capped at three classes**, because that is what the
validated palette clears for a form where any two marks can end up adjacent; and
**every subtitle carries n and the relevant caveat**, because a figure travels
without its caption.

Drawing the data also found three bugs in the 2014–2019 collector. It dated every
member's opening bloc spell to the chamber's first sitting, including
replacements who first appear in a 2017 capture; it closed departed members'
spells at the end of term (together these pushed the reconstructed chamber to 238
members against 217 seats); and it closed a spell at the previous observation
rather than where the next one starts, which left members in no bloc across the
capture gap. All three are fixed; the monthly panel now sits at 212–220, and that
residual spread is the reconstruction's error rather than something smoothed
away.

## Caveats

- **Career rows are rule-extracted from narrative prose**, carry
  `extraction_method='rule'` and a confidence grade, and are a starting point for
  hand-coding rather than a finished career history. The `shared_organisation`
  network layer inherits that uncertainty.
- **Cross-source person matches are recorded, not assumed.** Every match is
  listed with its method in `data/processed/_match_review.csv` for audit — 94
  matches over 80 people, of whom 14 were matched to more than one source.
  Matching never collapses two members of the same chamber on a name alone,
  because Tunisian homonyms are common.
- **Bloc switching is measured for two chambers only.** ARP-2014 — 108 of the 238
  members with a recorded bloc history changed bloc, reconstructed by diffing
  monthly web captures, so boundaries are bracketed not exact — and ARP-2023,
  where 29 of 155 changed bloc from dates the chamber publishes (44 have more
  than one spell, but 15 of those return to a bloc they had already sat in). For
  NCA-2011 and ARP-2019 the sources give end-of-term snapshots, so a zero there
  means "not measured", not "did not happen".
- **Sex for the 2011–2014 chamber is inferred, not recorded.** Marsad publishes
  no sex field, which would have left a third of the dataset unusable for any
  gender analysis. It is inferred from French grammatical agreement in each
  member's own biography (`Née`/`Né`, `Mariée`/`Marié`, `elle`/`il`) — never
  from the name. This yields 66 women of 217, against the 65 independently
  recorded for that chamber, which is a reassuring but not conclusive check.
- **Behavioural rates are not comparable across chambers.** Denominators differ
  by source and term and are often unpublished.
- **The 1956 roster rests on a tertiary source** and needs JORT verification
  before being used as evidence.
- **Seat counts were checked** against reported election results: the 1964 and
  1969 chambers had 101 seats, not the 90 frequently repeated from the 1959
  figure.

## Citation

See [CITATION.cff](CITATION.cff). Please cite the dataset version and note which
chambers your analysis actually covers.

## Licence

Code and curated reference data: MIT (see [LICENSE](LICENSE)). Collected data
remains subject to its upstream terms, summarised per source in
[docs/SOURCES.md](docs/SOURCES.md); it is public-record information about people
acting in public office.

## Contributing

The most valuable contributions, in order: ARP-2014 committee membership from
the archived `/2014/` committee pages (the same Wayback method that recovered its
roster should work); a `marsad.tn/mercato` collector to recover bloc switching
for 2011-2014; a roll-call votes table; hand-coded career histories to replace
the rule-extracted rows. Add a source by writing a collector that emits the staging shape in
`src/parliamentarians_tn/collect/base.py` — entity resolution and provenance are
handled centrally, so a new source is a self-contained job.
