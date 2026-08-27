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

**Why it is cheap to collect.** The roster page renders all 216 members as cards
whose `data-filter-*` attributes carry bloc, electoral list, district,
profession, age and sex, plus a vote-participation rate, an attendance rate, and
whether the member filed the statutory asset declaration. One request yields the
priority biographical layer for the whole chamber.

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
- Attendance and participation denominators differ between the roster cards and
  the individual profile pages, and are not published alongside the roster
  figures. Compare these rates within this term only.
- Committee pages *do* publish joining and leaving dates, and those are used.

## `MARSAD_ANC` — Al Bawsala's first observatory

**What it is.** `marsad.tn`, covering the 2011-2014 National Constituent
Assembly. It is the richest biographical source for any Tunisian legislature:
narrative profiles for all 217 members in both Arabic and French, plus bloc,
electoral list, constituency, party, committee assignments with roles, and a
vote-participation rate with the member's rank in the chamber.

**Why the French pages are parsed.** The French profiles render dates in one
predictable form (`Né le 02 Novembre 1975, à Sidi Khlif dans le gouvernorat de
Sidi Bouzid`) where the Arabic profiles use several idioms. The Arabic text is
still stored verbatim as `biography_ar`.

**Cautions.**

- Compiled by an NGO partly from member questionnaires, so occupations and civic
  roles are **self-reported**.
- Bloc affiliation is a single snapshot; switching within 2011-2014 is not
  recoverable from this source and must not be inferred from its absence.
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

**ARP-2014.** The most valuable remaining gap. Leads worth pursuing, none yet
successful: the Internet Archive's captures of `majles.marsad.tn` and of the
2014-2019 `arp.tn`; Al Bawsala's own published dataset of ARP deputies prepared
for *Cahiers de la Liberté*, referenced in secondary literature but not located
online; the Data4Tunisia portal (`data4tunisia.org`), whose AlBawsala
organisation page returned HTTP 403 to automated requests and should be checked
by hand; and a direct request to Al Bawsala, which is the most likely to work.

**Bloc switching before 2023.** `marsad.tn/mercato` is a dedicated Al Bawsala
page tracking party and bloc movement in the Constituent Assembly — its name is
the Tunisian press's term for the phenomenon. It was identified but not parsed,
and is the obvious next collector for anyone who needs within-term defection for
2011-2014.

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
