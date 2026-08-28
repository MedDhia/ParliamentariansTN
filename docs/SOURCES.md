# Sources

Every value in this dataset comes from one of the sources below, and
`data/processed/provenance.csv` records which source supplied which field of
which record. This document explains what each source is, what it covers, how
it is accessed, how far it can be trusted, and — for the periods no source
covers — what was checked and found wanting.

## Summary

| ID | Source | Covers | Depth | Access |
| --- | --- | --- | --- | --- |
| `ARP_ODOO` | Assembly of the Representatives of the People, official site | ARP-2023 | Roster, bilingual names, sex, governorate, constituency, blocs, committees, offices, written questions | Odoo JSON-RPC, read-only |
| `MARSAD_MAJLES` | Marsad Majles (Al Bawsala) | ARP-2019 | Roster, sex, profession, district, list, bloc, dated committee spells, attendance and voting rates | HTML |
| `MARSAD_ARP2014` | Marsad Majles 2014 observatory, via the Internet Archive | ARP-2014 | Full roster, Arabic + romanised names, sex, profession, constituency, list, seat number, **bloc membership as dated spells** | Wayback CDX + raw captures |
| `MARSAD_ANC` | Marsad (Al Bawsala) | NCA-2011 | Narrative biographies (ar+fr), birth date and place, sex (inferred), marital status, languages, bloc, list, party, committees with roles, vote participation | HTML |
| `WIKI_AR_ANC1956` | Arabic Wikipedia | ANC-1956 | Full 98-member roster with constituencies, August 1956 by-elections, presiding officers, aggregate occupational profile | MediaWiki API |
| `REFERENCE` | This repository | All 19 chamber-terms | Institutional frame, geography, party register, 1959–2011 presiding officers | Hand-curated |

## `ARP_ODOO` — the chamber's own database

**What it is.** `arp.tn` runs on Odoo 12. Its public pages render themselves by
calling `/web/dataset/call_kw`, the standard Odoo JSON-RPC endpoint, and that
endpoint answers anonymous requests for the models the site displays. Reading it
directly returns structured records instead of scraped markup.

**Access boundary.** Only models the public site itself queries are read, as the
anonymous portal user, read-only. Odoo's access-control layer is left to do its
job and is not worked around: `ir.model`, `arp.motif` and `arp.competence` all
return `AccessError` and were not pursued. Nothing is retrieved that a visitor to
arp.tn is not already shown.

**Models used.** `arp.depute`, `arp.informations.politiques`, `arp.mandat`,
`arp.groupe`, `arp.deputegroupe`, `arp.commission`, `arp.deputecommission`,
`arp.mandat.fonction`, `arp.gouvernorat`, `arp.circonscription`,
`arp.question.ecrite`.

**Bilingual names.** Odoo stores translations per field, so the same record
yields `إبراهيم بودربالة` under `lang=ar_SY` and `Brahim Bouderbela` under
`lang=fr_FR`. Both are fetched. This is the best romanisation available anywhere
for these members because it is the chamber's own, and it is what makes
cross-source name matching tractable.

**Cautions.**

- The public projection is **scoped to the current mandate**. `arp.mandat` lists
  the 2011-14, 2014-19, 2019-24 and 2023-27 terms, but record rules filter
  membership rows for closed terms; queries for them return zero rows, not an
  error. This is why the chamber's own site cannot supply the ARP-2014 gap.
- **Biographical fields are mostly empty** in the public projection even though
  the columns exist (`birthday`, `biographie`, `experience`, `marital`). Do not
  read their emptiness as evidence about the members.
- `is_active` is a computed field guarded by an internal ACL; requesting it makes
  the whole `search_read` fail. Use `state`.
- The 2023-2027 mandate is mislabelled upstream in the default and French
  projections as *"Mandat Parlementaire 2028-2027"*. The Arabic label
  (`المدة النيابية 2023-2027`) is correct.
- Odoo returns `False` for every empty field regardless of declared type. The
  pipeline converts this to an empty string; naive ingestion produces the string
  `"False"` throughout.

## `MARSAD_MAJLES` — Al Bawsala's second observatory

**What it is.** `majles.marsad.tn`, covering the assembly elected in October
2019: the chamber frozen by Presidential Decree 2021-117 on 25 July 2021 and
dissolved on 30 March 2022.

**Why the roster is cheap to collect.** The roster page renders all 216 members
as cards whose `data-filter-*` attributes carry bloc, electoral list, district,
profession, age and sex, plus a vote-participation rate, an attendance rate, and
whether the member filed the statutory asset declaration. One request yields the
priority biographical layer for the whole chamber.

**Why the member pages are collected anyway.** The roster card gives a rounded
rate and nothing else. Each member's own page gives five measures *with their
denominators* — plenary attendance, standing-committee attendance,
special-committee attendance, vote participation and vote discipline — plus the
justified and unjustified absence split. The denominator is what makes a rate
checkable and comparable within the chamber: "87 of 112 sittings" supports
inference that "77.68%" alone does not. Rates here are recomputed from the
counts rather than read from the rendered percentage, so upstream rounding does
not propagate.

**Cautions.**

- The site has not been updated since 2021. That makes it a stable archive, and
  a citable one, but it reflects the chamber as of its suspension.
- **Bloc pages are attendance tables, not membership histories.** They list who
  belonged to each bloc but publish no joining or leaving dates, so bloc
  membership here is an end-of-term snapshot and **within-term switching is not
  recoverable**. For a chamber that fragmented continuously across its term this
  is a substantive limitation, not a cosmetic one.
- **Age is published without a reference date** and is therefore *not* converted
  into a birth date. It is preserved in the mandate note.
- Attendance and participation figures differ between the roster cards and the
  member pages. The member page is preferred because it states its denominator;
  where the two disagree the page's figure is the one recorded. Compare these
  rates within this term only — the denominators are this chamber's sitting and
  division counts and mean nothing against another chamber's.
- **"Absence justifiée" and "absence injustifiée" are published** as a further
  split of non-attendance. They are not carried into `participation`, which has
  no column for them; they are available on the cached member pages for anyone
  who wants to code them.
- Committee pages *do* publish joining and leaving dates, and those are used.

## `MARSAD_ARP2014` — the 2014-2019 chamber, from the Internet Archive

**What it is.** Al Bawsala ran a third observatory, at `majles.marsad.tn/2014`,
covering the assembly elected in October 2014. The live site no longer serves
those paths: every `/2014/*` URL now returns the current site's catch-all page,
which is why this term looked like it had no source at all. The Internet Archive
holds it.

**Why it matters.** This was the dataset's largest gap — a democratic term
between two well-documented ones, whose absence broke any continuous 2011-2023
panel. Recovering it takes the number of people traceable across more than one
chamber from 26 to 84.

**How it is collected.** The Wayback CDX index enumerates captures of
`/2014/assemblee`; each is fetched with the `id_` modifier, which returns the
capture unrewritten (no Archive toolbar, no rewritten links). Each of the 217
members renders as a card whose data attributes carry the whole priority layer:

```
<a href="/2014/elus/Noureddine_Bhiri" class="depute"
   data-nom="نور الدين البحيري"  data-bloc="حركة النهضة"
   data-liste="حركة النهضة"      data-region="بن عروس"
   data-sexe="رجال"              data-age="57"
   data-profession="محامي"        data-siege="11">
```

**Bloc switching.** Roughly 29 monthly captures survive from January 2015 to May
2019. Diffing consecutive captures reconstructs bloc membership as dated spells,
making this **the one chamber for which switching is directly observable**: 108
of 246 members changed bloc. The recovered sequences track the real history —
members leaving Nidaa Tounes for الكتلة الحرّة in early 2016 and then for the
Machrouu Tounes bloc in December 2016, and the National Coalition forming in
2017.

**Cross-checks.** The first capture gives bloc sizes of Nidaa Tounes 86 and
Ennahdha 69, matching the official 2014 election result exactly, across 33
constituencies, matching the delimitation then in force, with 19 out-of-country
seats.

**Cautions.**

- **Spell boundaries are bracketed, not published.** A change is located only to
  the interval between two captures. Affected rows carry
  `bloc_memberships.dates_bracketed = true` and a note giving the interval;
  `start_date` is the first date the new bloc was actually observed, which is the
  conservative choice. Do not treat these as exact dates.
- **Captures after May 2019 yield nothing.** The page was redesigned, so the
  collector stops there; the term ended in October 2019 in any case.
- **Age is published without a birth date and is not converted.** Even with a
  known capture date it would only fix the birth year to within a year, so the
  raw age and observation date are preserved in the mandate note instead.
- The roster is a snapshot series, so the 246 people recorded include the 217
  elected plus 29 who entered later; members absent from the final usable
  capture have `exit_mode = unknown` rather than an invented departure reason.
- Committee membership was **not** recovered: the archived captures of the
  committee pages were not part of this collection and remain an open lead.

## `MARSAD_ANC` — Al Bawsala's first observatory

**What it is.** `marsad.tn`, covering the 2011-2014 National Constituent
Assembly. It is the richest source for any Tunisian legislature, biographically
*and* behaviourally: narrative profiles for all 217 members in both Arabic and
French, plus bloc, electoral list, constituency, party, committee assignments
with roles, a vote-participation rate with the member's rank — and, on separate
sub-pages, the chamber's entire recorded voting record, the constitutional
amendments each member tabled, and their party of election against their party
at the end of the term.

**An earlier version of this collector took about a fifth of it.** Each profile
links five sub-pages; only `/commissions` was followed. `/votes`, `/amendements`,
`/questions` and `/transparence` were never opened, nor was the site-level
`/mercato`. What that left behind was not marginal: roughly 1,700 recorded
divisions per member. The gap was invisible from the inside — the collector ran
clean, the profile pages parsed, and nothing in the data said "there is a voting
record you have not looked at". It was found only by listing the outbound links
on a page already in the cache. The lesson is recorded in
[RECONSTRUCTION_PROTOCOL.md](RECONSTRUCTION_PROTOCOL.md): enumerate a source's
endpoints before declaring it exhausted, because a collector cannot report data
it never requested.

**Why the French pages are parsed.** The French profiles render dates in one
predictable form (`Né le 02 Novembre 1975, à Sidi Khlif dans le gouvernorat de
Sidi Bouzid`) where the Arabic profiles use several idioms. The Arabic text is
still stored verbatim as `biography_ar`.

**Cautions.**

- Compiled by an NGO partly from member questionnaires, so occupations and civic
  roles are **self-reported**.
- Bloc affiliation is a single snapshot; *bloc* switching within 2011-2014 is
  not recoverable and must not be inferred from its absence. *Party* switching
  is recoverable, from the `/mercato` diagram, which publishes each member's
  party of election against their party at the end of the term.
- **The party-switching rows are undated.** The source gives the from/to pair,
  not the moment, so a row says that a member moved and not when. They also
  cannot be chained: a member who moved twice appears once, as origin and
  destination.
- **"Absent" on a division conflates two things** — being away, and being
  present and not voting. The source does not separate them, so an abstention
  rate computed from these positions is a lower bound.
- Divisions missing from a member's page get no row at all rather than a row
  reading absent. Members who joined late or left early are simply not listed,
  and manufacturing an absence for them would assert something the source does
  not.
- Some profiles are pasted from Wikipedia and carry footnote markers glued to
  years (`né le 1er mai 19561`). The parser handles this, and rejects any birth
  year implying an age under 18 or over 90 at election — a guard added after one
  member was initially assigned a birth year of 1998.
- Career rows extracted from these narratives are rule-based, carry
  `extraction_method='rule'` and a confidence grade, and are a starting point
  for hand-coding rather than a finished career history.

## `WIKI_AR_ANC1956` — the founding assembly

**What it is.** The Arabic Wikipedia article on the 1956 Constituent Assembly,
which reproduces the complete 98-member roster by constituency, the ten
replacements made at the by-election of 26 August 1956, the presiding officers,
and the chamber's aggregate occupational composition.

**Why it is used despite being an encyclopaedia.** No institution publishes this
roster in machine-readable form, and the chamber's own successor holds nothing
before 2011. Without this source the dataset's anchor chamber — the body that
seated independent Tunisia's founding elite — would be an empty frame.

**Cautions.**

- Tertiary source. Names and constituencies derive from Martin (2003) and
  Ghorbal (2011) but are not individually footnoted. Every row needs JORT
  verification before being used as evidence; see
  `RECONSTRUCTION_PROTOCOL.md`.
- **The article contradicts itself.** The roster table annotates Salah Bel Aiech
  as replaced by Ahmed Amara, while the by-election list has Ahmed Amara
  replacing Sheikh Ali Ben Aissa Bouhjar and Bahri Barbouch replacing Bel Aiech.
  The dedicated by-election list is treated as authoritative because it is the
  more specific claim, and the collector reports the conflict rather than hiding
  it.
- Occupations are given only as **chamber-level counts** (19 farmers, 14 lawyers,
  11 merchants, and so on), never per member, so they are stored as an
  assembly-level attribute.
- The article does not say which members vacated their seats by appointment and
  which by death, so `exit_mode` is `unknown` for all ten.
- By-election successors inherit their predecessor's constituency. That is an
  inference, flagged in the mandate note.

## `REFERENCE` — the curated frame

Held in `src/parliamentarians_tn/reference.py` so that contested values carry a
comment and the whole frame is reviewable in a diff. Covers all nineteen
chamber-terms, the 24 governorates plus an out-of-country grouping, a seed party
register including the Neo-Destour → PSD → RCD succession, and the eight
presiding officers of 1959-2011.

Seat counts for 1959-2009 were cross-checked against reported party-level
election results. **The 1964 and 1969 chambers had 101 seats, not the 90 often
repeated from the 1959 figure.** For pre-2011 chambers `start_date` holds the
election date because first-sitting dates are not verified, and every affected
row says so in `notes`. The Chamber of Advisors has an **empty** `start_date`:
its first sitting could not be established, and an empty date here means "not
established", never "approximately then".

## Periods and layers no source covers

These were investigated and found unavailable, which is itself worth recording
so the next researcher does not repeat the search.

**1959-2011 rosters.** No machine-readable list of members exists for any of the
eleven chambers of the single-party era. Checked: the chamber's own Odoo database
(nothing before 2011); Al Bawsala (founded 2011); Wikidata, which holds 243
ARP members and 100 NCA members but only **five** people with the pre-2011
Chamber of Deputies position; Arabic Wikipedia, which has a members category for
1956 but none for later chambers. The route is archival — see
`RECONSTRUCTION_PROTOCOL.md`.

**Bloc switching in 2011-2014 and 2019-2021.** Switching is now observable for
the 2014-2019 chamber (from archived captures) and for the sitting chamber (from
`arp.tn`, which publishes appointment and departure dates), but not for the
Constituent Assembly or the 2019 chamber, whose sources publish end-of-term
snapshots. `marsad.tn/mercato` is a dedicated Al Bawsala page tracking bloc
movement in the Constituent Assembly — the Tunisian press's term for the
phenomenon — and archived captures of the 2019 roster may permit the same
snapshot-diffing approach used for 2014. Both are identified but not parsed.

**Roll-call votes.** `marsad.tn/deputes/<id>/votes` returns a large per-member
voting record for the Constituent Assembly, and `majles.marsad.tn` publishes
votes for 2019. Neither is collected here: the schema holds voting *rates* but
not individual vote choices, and adding a votes table is the single largest
available extension to this dataset.

**Chamber of Advisors (2005-2011) and CNRD (2023-).** Neither has a published
machine-readable roster; the CNRD is covered by neither observatory.

## Access ethics

All of this is public data about people acting in public office, published by the
institutions they serve in or by civic-monitoring organisations whose purpose is
to make it public. Collection is rate-limited (roughly one request per second),
identifies itself in the `User-Agent`, and caches every response in `data/raw`
so that re-running the pipeline does not re-hit upstream servers. Access-control
boundaries are respected rather than probed. Personal contact details that
appear in some upstream records — addresses, telephone numbers, private email —
are deliberately **not** carried into the published tables, even where the
upstream field is readable.
