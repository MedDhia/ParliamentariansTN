# Reconstruction protocol for the undocumented chambers

Twelve of the nineteen chambers in this dataset have no roster: the National
Assembly of 1959-1981, the Chamber of Deputies of 1981-2011, the Chamber of
Advisors of 2005-2011, and the National Council of Regions and Districts. The
pre-2011 chambers alone cover fifty-two years and roughly 1,700 individual
mandates. This document specifies how to fill them, because the gap is
closable — it is an archival problem, not a data-availability problem — and
because whoever attempts it should produce rows that merge cleanly into the
existing tables rather than a parallel spreadsheet.

It also specifies the verification still owed for the 1956 Constituent Assembly,
whose roster is present but rests on a tertiary source.

## Why the gap exists

Nothing digital covers it. The chamber's own Odoo database begins with the 2011
Constituent Assembly and restricts even closed post-2011 mandates to internal
users. Al Bawsala was founded in 2011. Wikidata holds 243 ARP members and 100
Constituent Assembly members but only five people carrying the pre-2011 Chamber
of Deputies position. Arabic Wikipedia has a members category for the 1956
assembly and none for any later chamber. The searches are recorded in
`SOURCES.md` so they are not repeated.

The information itself is not lost. Election results and the composition of each
chamber were published contemporaneously; they are simply on paper.

## Before an archival trip: exhaust the source you already have

Archival work is expensive, so it is worth being certain that what you are going
to Tunis for is not already sitting in a cache. Two of this dataset's largest
gains came from re-reading a source that had been declared collected.

**Enumerate a source's endpoints before declaring it exhausted.** A collector
cannot report data it never requested, so an incomplete extraction looks exactly
like a complete one: the run is clean, the parsed pages are correct, and nothing
anywhere says "there is more". The `marsad.tn` collector fetched three pages per
member for months and looked finished. Listing the outbound links on a page
already in the cache showed five sub-pages per member, of which one was being
followed — and the unfollowed ones held roughly 1,700 recorded divisions per
member, the constitutional amendments each had tabled, and the party-switching
series the documentation had described as unrecoverable.

The check costs one command against a page you already hold:

```bash
grep -oE 'href="/[^"]*"' cached_page.html | sort -u
```

Do it for a member page, a committee page and the site root, and do it again
when a source is revisited. Where a site renders a chart, look for the data
behind it: `mercato`'s party-switching series is a JSON literal inline in the
page, not an image.

**Prefer a published denominator to a published rate.** Where a source offers
both a summary figure and the counts behind it, the counts are worth an extra
request per member: "87 of 112 sittings" can be checked and recomputed, "77.68%"
cannot.

## Primary sources, in order of authority

**1. *Journal Officiel de la République Tunisienne* (JORT).** The authoritative
record. For each legislature it publishes the proclamation of results by
constituency, which names every returned member, and subsequently records
resignations, deaths, replacements and the composition of the bureau. Before 1957
it appears as the *Journal Officiel Tunisien*. Holdings: the Imprimerie
Officielle de la République Tunisienne, with partial runs in the Bibliothèque
Nationale de Tunisie. Coverage of digitised issues is incomplete and varies by
decade; assume on-site consultation is required.

**2. The chamber's own library and archive.** `bibliotheque.arp.tn` and
`archive.arp.tn` (the Hichem Djaït library) hold the chamber's deliberation
records, which name speakers in debate and committee members. The public catalogue
is searchable; the documents themselves are largely not online. This is the best
source for **committee composition**, which the JORT does not systematically
report.

**3. The Internet Archive.** Worth trying *before* any archival trip for
anything that was once on the web. The 2014-2019 chamber was recovered entirely
this way after the live site stopped serving it: the Wayback CDX index enumerates
captures and the `id_` modifier returns them unrewritten. This will not help for
1959-2011, which predates the web, but it is the first thing to try for any
later gap.

**4. Contemporary press.** *La Presse de Tunisie*, *L'Action* / *Le Renouveau*
(the party organ, under successive names) and *Al-Amal* published constituency
result lists in the days after each election. Useful as a cross-check on the JORT
and often easier to obtain. Turess (`turess.com`) aggregates Tunisian press but
its archive does not reach the single-party era.

**5. Secondary literature.** Useful for the frame and for elite biography, not
for rosters. Camau and Geisser on the Bourguiba and Ben Ali regimes; Hibou on the
RCD's organisation; Martin's *Histoire de la Tunisie contemporaine* for
1881-1956, which is the ultimate source behind the 1956 roster used here.

## Coding rules

Rows produced by archival work must follow the same rules as the collected data.

**Persons.** Mint no identifiers by hand. Add a staging document
(`data/raw/staging_<source>.json`) in the shape defined by
`src/parliamentarians_tn/collect/base.py` and let `build.py` assign `person_id`
values and attempt cross-source matching. This matters: a deputy who sat in 1989
and again in 2011 must resolve to *one* person, and only the builder's matching
logic — with its review file — can do that safely.

**Names.** Record the Arabic form exactly as the source gives it, including the
definite article where present. Do not normalise, do not correct spelling, and do
not romanise by hand: `ids.romanize_arabic` handles the fallback and the codebook
records which rows were machine-romanised. Where the source itself supplies a
French spelling (the JORT often does), record it as `name_lat` — a
source-supplied romanisation always outranks a generated one.

**Dates.** Use the date the source states, at the precision the source states.
If only a year is known, write `YYYY-01-01` and set the companion precision
column to `year`. **Never interpolate a plausible day.** An empty date in this
dataset means "not established"; a padded date with a precision flag means
"known to the year". Those are different claims and must stay different.

**Entry and exit.** `entry_mode` is `elected` for a member returned at a general
election, `elected_byelection` for a by-election, `replacement_list` for a
list-successor, `appointed` for the presidentially appointed third of the Chamber
of Advisors. Where the JORT records a vacancy but not its cause, `exit_mode` is
`unknown` — not `resignation`, which is a guess.

**Party.** For 1959-2011 nearly every member belonged to the ruling party under
its then name. Use the identifier for the name in force at the time:
`PTY-NEODESTOUR` to 1964, `PTY-PSD` to 1988, `PTY-RCD` after. The succession
links are in `parties.csv`, so an analyst can treat the lineage as one
organisation or three; do not pre-decide that by collapsing the identifiers.

**Opposition deputies from 1994.** The compensatory seats introduced in 1994
admitted opposition members (19 of 163 in 1994, rising to 53 of 214 in 2009).
Code their party accurately — `PTY-MDS`, `PTY-PUP`, `PTY-UDU`, `PTY-ETTAJDID` and
others — and record on the mandate whether the seat was won in a constituency or
allocated nationally. That distinction is the whole institutional point of the
mechanism and is what makes the period usable for work on authoritarian
power-sharing.

**Provenance.** Every row needs a source. Add a row to `sources.csv` for the
archival source used, with its holding institution, and cite the JORT issue
number and date in the staging record's `source_url` or note field. A row without
a traceable citation cannot be defended in review and should not be added.

## Verification owed on the 1956 assembly

The 98-member roster is present but comes from Arabic Wikipedia. Before it is
used as evidence:

1. Check each name and constituency against the JORT proclamation of the results
   of 25 March 1956.
2. Resolve the article's internal contradiction over the replacement of Salah
   Bel Aiech — the roster table and the by-election list disagree, and the
   collector flags this rather than resolving it.
3. Establish which of the ten members who vacated seats did so by appointment as
   governor or délégué and which by death. The article gives the aggregate (six
   governors, one délégué, two deaths — which accounts for nine of ten) but
   attributes none of them individually.
4. Confirm the date Bourguiba handed the chair to Jallouli Fares. The dataset
   records 15 April 1956 as an explicit approximation.
5. Code occupations per member. The article gives only chamber-level counts,
   which are stored as an assembly attribute; the individual-level data would
   make the founding elite's social composition directly comparable to the
   post-2011 chambers, which is one of the more interesting things this dataset
   could support.

## Priority order

If effort is limited, this is the order that buys the most:

1. **~~ARP-2014~~ — done.** Recovered from Internet Archive captures of Al
   Bawsala's 2014 observatory; see `SOURCES.md`. Its committee pages were *not*
   recovered and remain the cheapest remaining win: the same CDX-plus-raw-capture
   method should work on the archived committee pages under `/2014/`. The
   archived roster links `/2014/assemblee/commissions`, `/2014/assemblee/bureau`,
   `/2014/votes` and `/2014/lois`, so the captures are known to exist; the
   attempt is open because `web.archive.org` was unreachable from the
   environment it was last tried in (connection reset on every request, while
   `archive.org` itself answered), not because the pages were checked and found
   missing. Anyone with working Archive access should be able to close it.
2. **ADV-2005, the Chamber of Advisors** — and this one may not need archival
   work at all. It sits in the dataset with 112 seats and zero members, listed
   until now as having no source. But its own site, `chambredesconseillers.tn`,
   was captured by the Internet Archive before it went dead: the availability
   API confirms a capture of `/fr/index.php?id=145` from 21 August 2010
   returning 200. Nobody has read it. If those pages carry a member list, this
   is a web-scraping job of the same shape as ARP-2014, not a JORT search, and
   it closes an entire chamber. It is blocked by the same unreachable
   `web.archive.org` as item 1, so one working Archive session could settle
   both.
3. **COD-2009 and COD-2004.** The last two chambers of the Ben Ali period, with
   substantial documented opposition contingents, immediately adjacent to the
   2011 rupture. This is what makes elite continuity across the revolution
   measurable — currently impossible.
4. **COD-1994 and COD-1999.** The introduction and consolidation of compensatory
   opposition seats.
5. **1956 verification**, per above.
6. **The single-party chambers 1959-1989.** Highest archival cost, and the
   membership is least variable, so the lowest marginal return — but necessary
   for any claim about the founding elite's persistence across the whole period.
