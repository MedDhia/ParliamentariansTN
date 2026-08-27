# Coverage

Generated from the built data on 2026-08-27. Run `make codebook` to refresh.

This is the document to read before using the dataset for anything comparative. Coverage is deeply uneven, and the unevenness is not random: it tracks what Tunisian institutions and civic monitors chose to publish, which in turn tracks the political openness of each period. Any analysis pooling across chambers is implicitly comparing well-documented democratic terms with barely-documented authoritarian ones, and needs to say so.

## Person-level coverage by chamber

| Chamber | Period | Seats | Mandates | % | Committee rows | Bloc rows | Behavioural rows | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ANC-1956` | 1956–1959 | 98 | 108 | 110% | 0 | 0 | 0 | full |
| `NA-1959` | 1959–1964 | 90 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `NA-1964` | 1964–1969 | 101 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `NA-1969` | 1969–1974 | 101 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `NA-1974` | 1974–1979 | 112 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `NA-1979` | 1979–1981 | 121 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `COD-1981` | 1981–1986 | 136 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `COD-1986` | 1986–1989 | 125 | 3 | 2% | 0 | 0 | 0 | frame_only |
| `COD-1989` | 1989–1994 | 141 | 3 | 2% | 0 | 0 | 0 | frame_only |
| `COD-1994` | 1994–1999 | 163 | 2 | 1% | 0 | 0 | 0 | frame_only |
| `COD-1999` | 1999–2004 | 182 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `COD-2004` | 2004–2009 | 189 | 1 | 1% | 0 | 0 | 0 | frame_only |
| `COD-2009` | 2009–2011 | 214 | 1 | 0% | 0 | 0 | 0 | frame_only |
| `NCA-2011` | 2011–2014 | 217 | 217 | 100% | 448 | 217 | 213 | full |
| `ARP-2014` | 2014–2019 | 217 | 0 | 0% | 0 | 0 | 0 | frame_only |
| `ARP-2019` | 2019–2021 | 217 | 216 | 100% | 357 | 216 | 216 | full |
| `ARP-2023` | 2023–present | 161 | 155 | 96% | 324 | 205 | 154 | full |
| `CNRD-2023` | 2024–present | 77 | 0 | 0% | 0 | 0 | 0 | frame_only |
| `ADV-2005` | ?–2011 | 112 | 0 | 0% | 0 | 0 | 0 | frame_only |

## What `coverage_status` means

- **`full`** — a roster covering essentially every seat is present.
- **`frame_only`** — the chamber is described in `assemblies.csv` (dates, seats, electoral system, regime context) but few or no members are individually recorded. The chamber exists in the dataset as an institution, not as a set of people.

## Attribute completeness, persons table

| Attribute | Non-empty | of 682 persons |
| --- | --- | --- |
| `name_ar` | 682 | 100% |
| `name_lat` | 682 | 100% |
| `gender` | 568 | 83% |
| `birth_date` | 158 | 23% |
| `birth_place_ar` | 114 | 17% |
| `birth_governorate_id` | 68 | 10% |
| `occupation_raw` | 52 | 8% |
| `biography_ar` | 222 | 33% |
| `marital_status` | 62 | 9% |
| `languages` | 47 | 7% |
| `education_raw` | 217 | 32% |
| `wikidata_qid` | 0 | 0% |

Persons with at least one extracted career row: 114.

## Known gaps, in order of how much they matter

1. **1959–2011 has no rosters.** Eleven chambers across fifty-two years are represented only by their eight presiding officers. Neither the chamber's own database nor any civic monitor covers the single-party era, and no published list of members exists in machine-readable form. Closing this gap requires archival work in the *Journal Officiel*; `docs/RECONSTRUCTION_PROTOCOL.md` specifies how.
2. **ARP-2014 is missing entirely.** This is the most painful gap because it is a democratic term sitting between two well-covered ones, and it breaks any continuous 2011–2023 panel. Al Bawsala's first observatory stops at 2014 and its second starts at 2019, while the chamber's own database restricts closed mandates to internal users. The data almost certainly exists; see the leads in `docs/SOURCES.md`.
3. **Bloc switching is only partly observable.** Blocs are recorded as spells, but the sources publish end-of-term snapshots for 2011 and 2019, so within-term defection — central to explaining the fragmentation of both chambers — cannot be recovered from what is collected here. The 2023 chamber is the exception: `arp.tn` publishes appointment and departure dates, so switching *is* observable there.
4. **Biography depth is thin for the sitting chamber.** The 2011–14 Constituent Assembly is by far the best-documented body: Al Bawsala published narrative biographies for all 217 members. The current chamber's own site exposes almost no biographical fields publicly, so birth dates and careers are largely absent for 2023 — the opposite of what one would expect from recency.
5. **Career rows are rule-extracted from prose.** They carry `extraction_method='rule'` and a confidence grade. They are a starting point for hand-coding, not a finished career-history dataset, and the `shared_organisation` network layer inherits this uncertainty.

