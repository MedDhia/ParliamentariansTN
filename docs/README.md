# Documentation index

Six documents. Two are generated from the data on every `make codebook` and
should never be hand-edited; four are written.

| Document | What it answers | Kind |
| --- | --- | --- |
| [FINDINGS.md](FINDINGS.md) | What does this dataset show? Every result, with the number and the file to verify it in. | written |
| [COVERAGE.md](COVERAGE.md) | Which chambers can I actually use, and how complete is each attribute? | **generated** |
| [CODEBOOK.md](CODEBOOK.md) | What does this column mean, what values may it take, how often is it filled? | **generated** |
| [SOURCES.md](SOURCES.md) | Where did this come from, how reliable is it, and what does it get wrong? | written |
| [NETWORK_GUIDE.md](NETWORK_GUIDE.md) | What does each network layer mean, and what are its traps? | written |
| [RECONSTRUCTION_PROTOCOL.md](RECONSTRUCTION_PROTOCOL.md) | How do I close the 1959–2011 gap so the new rows merge cleanly? | written |

## Reading order

**Using the data for the first time.** COVERAGE.md → CODEBOOK.md → FINDINGS.md.
Coverage first is not politeness: person-level data exists for five of nineteen
chamber-terms, and the gap is the entire authoritarian period, so it is not
missing at random. Any comparison across time has to be designed around that.

**Doing network analysis.** NETWORK_GUIDE.md → [`examples/`](../examples/) →
FINDINGS.md §5. The guide's central warning is that the committee co-membership
network is a *projection* whose density is manufactured by projection rather than
observed; build from the bipartite incidence file instead.

**Assessing whether to trust a number.** SOURCES.md for the upstream, then
`data/processed/provenance.csv`, which records which source supplied which field
of which record.

**Extending the dataset.** RECONSTRUCTION_PROTOCOL.md for archival work, or
`src/parliamentarians_tn/collect/base.py` for the staging shape a new collector
must emit.

## The generated two

`CODEBOOK.md` and `COVERAGE.md` are written by `make codebook` from
`src/parliamentarians_tn/schema.py` and the built tables. Editing them by hand
gets your changes overwritten and, worse, lets the documentation drift from the
data — which is the failure mode the generation exists to prevent. Change
`schema.py` instead.

## Related, elsewhere in the repo

- [`figures/README.md`](../figures/README.md) — how the twenty figures are built,
  the design rules they follow, and the catalogue. Results live in FINDINGS.md;
  this is method.
- [`examples/`](../examples/) — worked analyses in Python and R that run on the
  committed data with no network access.
- [`README.md`](../README.md) — the project front door: coverage summary, design
  decisions, caveats, and how to reproduce the build.
