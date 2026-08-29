# Codebook

Generated from `src/parliamentarians_tn/schema.py` and the built data on 2026-08-29. Do not edit by hand — run `make codebook` instead.

## Reading this codebook

**An empty cell means the value was not recorded by any source we consulted.** It never means zero, never means false, and never means the attribute does not apply. Coverage varies enormously across the seventy years the dataset spans, so a column that is 95 per cent complete for the sitting chamber may be empty for the single-party era; the fill rates below are computed over all rows and should be read alongside `docs/COVERAGE.md`, which breaks completeness down by chamber.

Dates are ISO 8601. Where a date is known only to the year, it is stored as 1 January of that year and the companion `*_precision` column records `year`; treating such a value as a known day is a mistake the precision column exists to prevent.

Rates are proportions in [0, 1], not percentages. Denominators differ across sources and terms, so rates should not be compared across chambers without checking `sources.csv` for how each was computed.

## Tables

| Table | Unit of observation | Rows |
| --- | --- | --- |
| [`assemblies`](#assemblies) | One row per parliamentary chamber-term (a legislature). | 19 |
| [`governorates`](#governorates) | One row per governorate. | 25 |
| [`constituencies`](#constituencies) | One row per constituency per assembly. | 260 |
| [`parties`](#parties) | One row per political party. | 70 |
| [`persons`](#persons) | One row per natural person who has held a parliamentary mandate. | 856 |
| [`mandates`](#mandates) | One row per person per assembly per continuous spell of service. | 959 |
| [`party_affiliations`](#party_affiliations) | One row per person per party per spell. | 217 |
| [`blocs`](#blocs) | One row per parliamentary bloc per assembly. | 40 |
| [`bloc_memberships`](#bloc_memberships) | One row per person per bloc per spell. | 1,116 |
| [`committees`](#committees) | One row per committee per assembly. | 54 |
| [`committee_memberships`](#committee_memberships) | One row per person per committee per spell. | 1,129 |
| [`offices`](#offices) | One row per person per parliamentary office per spell. | 60 |
| [`careers`](#careers) | One row per person per extra-parliamentary role. | 171 |
| [`participation`](#participation) | One row per person per assembly. | 583 |
| [`votes`](#votes) | One row per recorded division. | 1,724 |
| [`vote_positions`](#vote_positions) | One row per member per division. | 370,922 |
| [`party_switches`](#party_switches) | One row per member per recorded change of party within a term. | 105 |
| [`amendments`](#amendments) | One row per tabled amendment. | 251 |
| [`amendment_sponsorships`](#amendment_sponsorships) | One row per member per amendment they tabled. | 3,646 |
| [`person_xref`](#person_xref) | One row per person per external identifier. | 950 |
| [`sources`](#sources) | One row per data source. | 6 |
| [`provenance`](#provenance) | One row per (table, record, field) that a source supplied. | 5,039 |

## `assemblies`

**Unit of observation.** One row per parliamentary chamber-term (a legislature).

The institutional frame, complete from the 1956 Constituent Assembly to the present. This table is hand-curated from constitutional and electoral-law sources rather than scraped, and it is what makes the dataset a time series rather than a set of disconnected snapshots.

**Primary key.** `assembly_id`

**Notes.** Chamber-terms are the unit, not chambers. The 2019 ARP therefore ends in 2021 de facto (frozen by presidential decree) while its nominal term ran to 2024; both dates are recorded, because the distinction is the object of study for work on democratic breakdown.

**Rows.** 19

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `assembly_id` | string | 19 (100%) | *(required, unique)* Stable identifier. Example: `ARP-2023`. |
| `name_ar` | string | 19 (100%) | *(required)* Official name, Arabic. |
| `name_fr` | string | 19 (100%) | Official name, French. |
| `name_en` | string | 19 (100%) | Conventional English name. |
| `type` | enum | 19 (100%) | *(required)* Chamber type. One of: `constituent`, `ordinary_lower`, `ordinary_upper`, `regional`. |
| `ordinal` | integer | 17 (89%) | Sequence number within the dataset, 1 = 1956 Constituent Assembly. |
| `start_date` | date | 18 (95%) | First sitting. Empty where the date is not established (see notes). |
| `end_date` | date | 17 (89%) | Last sitting in fact. Empty if still sitting. |
| `nominal_end_date` | date | 5 (26%) | End of term as provided in law, where it differs from end_date. |
| `seats_nominal` | integer | 19 (100%) | Seats provided for by law. |
| `seats_filled` | integer | 16 (84%) | Seats actually filled at opening, where known. |
| `seats_women` | integer | 2 (11%) | Seats held by women at opening, where known. |
| `electoral_system` | string | 19 (100%) | Formula used to return the chamber. |
| `suffrage` | string | 19 (100%) | Franchise rules of note. |
| `regime_period` | enum | 19 (100%) | Regime period in which the chamber sat. One of: `protectorate_transition`, `bourguiba`, `ben_ali`, `transition`, `second_republic`, `exceptional_measures`, `third_republic`. |
| `termination_mode` | string | 17 (89%) | How the chamber ended: normal expiry, dissolution, freezing, supersession. |
| `speaker_person_id` | string → `persons.person_id` | 0 (0%) | Presiding officer, where identified. |
| `legal_basis` | string | 19 (100%) | Constitution or decree establishing the chamber. |
| `coverage_status` | string | 19 (100%) | Person-level coverage in this dataset: full, partial, frame_only. |
| `notes` | string | 19 (100%) | Analyst notes, including known contested facts. |

<details><summary>Distribution of <code>type</code></summary>

| Value | n |
| --- | --- |
| `ordinary_lower` | 15 |
| `constituent` | 2 |
| `ordinary_upper` | 1 |
| `regional` | 1 |

</details>

<details><summary>Distribution of <code>regime_period</code></summary>

| Value | n |
| --- | --- |
| `bourguiba` | 7 |
| `ben_ali` | 6 |
| `second_republic` | 2 |
| `third_republic` | 2 |
| `protectorate_transition` | 1 |
| `transition` | 1 |

</details>

## `governorates`

**Unit of observation.** One row per governorate.

Tunisia's 24 governorates plus out-of-country groupings, with the regional aggregations used in the literature on interior/coastal inequality. Provides the geographic homophily dimension.

**Primary key.** `governorate_id`

**Rows.** 25

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `governorate_id` | string | 25 (100%) | *(required, unique)* Identifier. Example: `TN-31`. |
| `name_ar` | string | 25 (100%) | *(required)* Name, Arabic. |
| `name_lat` | string | 25 (100%) | Name, Latin script. |
| `name_fr` | string | 25 (100%) | Name, French. |
| `iso_3166_2` | string | 24 (96%) | ISO 3166-2:TN code where one exists. |
| `region` | string | 25 (100%) | Statistical region (Grand Tunis, North East, North West, Centre East, Centre West, South East, South West, abroad). |
| `littoral` | boolean | 25 (100%) | Coastal governorate, per the coastal/interior cleavage. |
| `created_year` | integer | 0 (0%) | Year the governorate was created, for historical comparability. |

## `constituencies`

**Unit of observation.** One row per constituency per assembly.

Constituency boundaries and magnitudes change between elections, so constituencies are scoped to an assembly rather than treated as permanent units.

**Primary key.** `constituency_id`

**Rows.** 260

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `constituency_id` | string | 260 (100%) | *(required, unique)* Identifier. |
| `assembly_id` | string → `assemblies.assembly_id` | 260 (100%) | *(required)* Assembly this delimitation applies to. |
| `name_ar` | string | 260 (100%) | *(required)* Name, Arabic. |
| `name_lat` | string | 33 (13%) | Name, Latin script. |
| `governorate_id` | string → `governorates.governorate_id` | 231 (89%) | Containing governorate, empty for out-of-country seats. |
| `is_abroad` | boolean | 260 (100%) | Out-of-country constituency. |
| `magnitude` | integer | 0 (0%) | Number of seats returned. |

## `parties`

**Unit of observation.** One row per political party.

Party register spanning the single-party era and the post-2011 multiparty period, with successor links so that the Neo-Destour / PSD / RCD lineage can be followed as one organisation or three, at the analyst's choice.

**Primary key.** `party_id`

**Rows.** 70

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `party_id` | string | 70 (100%) | *(required, unique)* Identifier. Example: `PTY-RCD`. |
| `name_ar` | string | 70 (100%) | *(required)* Name, Arabic. |
| `name_fr` | string | 55 (79%) | Name, French. |
| `name_en` | string | 21 (30%) | Name, English. |
| `abbrev` | string | 21 (30%) | Common abbreviation. Example: `RCD`. |
| `family` | enum | 70 (100%) | Ideological family. One of: `destourian`, `islamist`, `left`, `social_democratic`, `liberal`, `arab_nationalist`, `national_conservative`, `independent`, `other`, `unknown`. |
| `founded_date` | date | 20 (29%) | Foundation date. |
| `dissolved_date` | date | 5 (7%) | Dissolution date. |
| `predecessor_party_id` | string → `parties.party_id` | 4 (6%) | Organisational predecessor. |
| `wikidata_qid` | string | 0 (0%) | Wikidata item. |
| `notes` | string | 49 (70%) | Analyst notes. |

<details><summary>Distribution of <code>family</code></summary>

| Value | n |
| --- | --- |
| `unknown` | 49 |
| `social_democratic` | 4 |
| `destourian` | 4 |
| `left` | 3 |
| `liberal` | 3 |
| `arab_nationalist` | 2 |
| `islamist` | 2 |
| `other` | 1 |
| `independent` | 1 |
| `national_conservative` | 1 |

</details>

## `persons`

**Unit of observation.** One row per natural person who has held a parliamentary mandate.

The person registry. Identity is deliberately thin: names, sex, vital dates, origin. Everything time-varying lives in the spell tables so that a person's record does not have to be rewritten when their affiliation changes.

**Primary key.** `person_id`

**Notes.** Names are stored in both Arabic script and Latin script because no single romanisation is authoritative in Tunisian practice: the ARP, Al Bawsala and the electoral commission romanise the same name differently. Matching across sources uses the normalised Arabic form (see ids.normalize_arabic) with the Latin form as a fallback.

**Rows.** 856

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `person_id` | string | 856 (100%) | *(required, unique)* Stable dataset identifier, format TNP-00000. Example: `TNP-00042`. |
| `name_ar` | string | 856 (100%) | Full name in Arabic script as given by the most authoritative source. Example: `إبراهيم بودربالة`. |
| `name_lat` | string | 856 (100%) | Full name in Latin script. Example: `Brahim Bouderbela`. |
| `given_name_ar` | string | 155 (18%) | Given name, Arabic script. |
| `family_name_ar` | string | 154 (18%) | Family name, Arabic script. |
| `given_name_lat` | string | 155 (18%) | Given name, Latin script. |
| `family_name_lat` | string | 155 (18%) | Family name, Latin script. |
| `name_normalised` | string | 856 (100%) | Diacritic- and orthography-normalised Arabic key used for cross-source matching. Example: `ابراهيم بودربالة`. |
| `gender` | enum | 742 (87%) | Sex as recorded by the source. Sources record a binary; 'unknown' where absent. One of: `female`, `male`, `other`, `unknown`. |
| `birth_date` | date | 158 (18%) | Date of birth, ISO 8601. Partial dates are padded and flagged in birth_date_precision. |
| `birth_date_precision` | enum | 158 (18%) | Granularity actually known for birth_date. One of: `day`, `month`, `year`, `decade`, `unknown`. |
| `birth_place_ar` | string | 114 (13%) | Locality of birth as written by the source, Arabic script. |
| `birth_governorate_id` | string → `governorates.governorate_id` | 68 (8%) | Governorate of birth. |
| `death_date` | date | 3 (0%) | Date of death where applicable. |
| `death_date_precision` | enum | 3 (0%) | Granularity of death_date. One of: `day`, `month`, `year`, `decade`, `unknown`. |
| `marital_status` | string | 62 (7%) | Marital status as reported (free text, source wording preserved). |
| `n_children` | integer | 37 (4%) | Number of children where reported. |
| `languages` | string | 47 (5%) | Semicolon-separated languages claimed in the official biography. Example: `ar;fr;en`. |
| `education_raw` | string | 217 (25%) | Education as written by the source, untranslated. |
| `education_level` | string | 0 (0%) | Coded highest attainment; see docs/CODEBOOK.md. |
| `occupation_raw` | string | 227 (27%) | Pre-parliamentary occupation as written by the source. |
| `occupation_sector` | enum | 0 (0%) | Coded sector of the principal pre-parliamentary occupation. One of: `state_executive`, `state_administration`, `party`, `trade_union`, `business`, `professional_association`, `civil_society`, `military`, `security`, `judiciary`, `academia`, `education`, `health`, `media`, `religious`, `local_government`, `international_organisation`, `diaspora_association`, `other`, `unknown`. |
| `biography_ar` | string | 222 (26%) | Official biographical text, Arabic, verbatim. Long free text. |
| `wikidata_qid` | string | 0 (0%) | Wikidata item, where a match was verified. Example: `Q3576068`. |
| `first_mandate_start` | date | 856 (100%) | Derived: start of earliest mandate. |
| `n_mandates` | integer | 856 (100%) | Derived: number of distinct mandates held. |

<details><summary>Distribution of <code>gender</code></summary>

| Value | n |
| --- | --- |
| `male` | 535 |
| `female` | 203 |
| `unknown` | 4 |

</details>

<details><summary>Distribution of <code>birth_date_precision</code></summary>

| Value | n |
| --- | --- |
| `day` | 149 |
| `year` | 9 |

</details>

<details><summary>Distribution of <code>death_date_precision</code></summary>

| Value | n |
| --- | --- |
| `day` | 3 |

</details>

## `mandates`

**Unit of observation.** One row per person per assembly per continuous spell of service.

The core event table. A person returned in three legislatures has three rows; a person who replaces a resigning deputy mid-term has a row whose start_date is the replacement date, not the assembly's.

**Primary key.** `mandate_id`

**Rows.** 959

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `mandate_id` | string | 959 (100%) | *(required, unique)* Stable identifier. Example: `TNM-00713`. |
| `person_id` | string → `persons.person_id` | 959 (100%) | *(required)* Holder of the mandate. |
| `assembly_id` | string → `assemblies.assembly_id` | 959 (100%) | *(required)* Chamber-term served in. |
| `start_date` | date | 959 (100%) | Start of this spell of service. |
| `end_date` | date | 807 (84%) | End of this spell. Empty where still serving. |
| `entry_mode` | enum | 959 (100%) | How the seat was obtained. One of: `elected`, `elected_byelection`, `replacement_list`, `appointed`, `ex_officio`, `unknown`. |
| `exit_mode` | enum | 959 (100%) | How the mandate ended. One of: `end_of_term`, `death`, `resignation`, `revocation`, `dissolution`, `became_minister`, `elected_president`, `still_serving`, `unknown`. |
| `constituency_id` | string → `constituencies.constituency_id` | 932 (97%) | Seat's constituency. |
| `governorate_id` | string → `governorates.governorate_id` | 788 (82%) | Governorate of the constituency (denormalised for convenience). |
| `electoral_list_ar` | string | 787 (82%) | Name of the list on which the person was returned, Arabic. |
| `electoral_list_lat` | string | 325 (34%) | Name of the list, Latin script. |
| `party_id_at_election` | string → `parties.party_id` | 342 (36%) | Party sponsoring the list, where applicable. |
| `seat_number` | string | 401 (42%) | Seat or file number used by the chamber. |
| `is_diaspora_seat` | boolean | 959 (100%) | True where the constituency is an out-of-country constituency. |
| `election_date` | date | 942 (98%) | Date of the election returning this mandate. |
| `source_ids` | string → `sources.source_id` | 959 (100%) | Semicolon-separated source_id list. |

<details><summary>Distribution of <code>entry_mode</code></summary>

| Value | n |
| --- | --- |
| `elected` | 903 |
| `replacement_list` | 29 |
| `unknown` | 17 |
| `elected_byelection` | 10 |

</details>

<details><summary>Distribution of <code>exit_mode</code></summary>

| Value | n |
| --- | --- |
| `end_of_term` | 534 |
| `dissolution` | 216 |
| `still_serving` | 152 |
| `unknown` | 54 |
| `death` | 3 |

</details>

## `party_affiliations`

**Unit of observation.** One row per person per party per spell.

Party membership as dated spells, independent of parliamentary service, so that pre-parliamentary and post-parliamentary membership is representable.

**Primary key.** `affiliation_id`

**Rows.** 217

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `affiliation_id` | string | 217 (100%) | *(required, unique)* Identifier. |
| `person_id` | string → `persons.person_id` | 217 (100%) | *(required)* Member. |
| `party_id` | string → `parties.party_id` | 217 (100%) | *(required)* Party. |
| `start_date` | date | 0 (0%) | Start of membership spell. |
| `end_date` | date | 0 (0%) | End of membership spell. |
| `role` | string | 0 (0%) | Role held in the party, e.g. political bureau member. |
| `source_ids` | string → `sources.source_id` | 217 (100%) | Provenance. |

## `blocs`

**Unit of observation.** One row per parliamentary bloc per assembly.

Parliamentary blocs (kutla) are the operative unit of legislative behaviour after 2011 and are not identical to parties: blocs form, split and dissolve within a term.

**Primary key.** `bloc_id`

**Rows.** 40

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `bloc_id` | string | 40 (100%) | *(required, unique)* Identifier. |
| `assembly_id` | string → `assemblies.assembly_id` | 40 (100%) | *(required)* Assembly in which the bloc existed. |
| `name_ar` | string | 40 (100%) | *(required)* Name, Arabic. |
| `name_lat` | string | 24 (60%) | Name, Latin script. |
| `party_id` | string → `parties.party_id` | 40 (100%) | Dominant party, where the bloc is a party bloc. |
| `formed_date` | date | 40 (100%) | Date the bloc was constituted. |
| `dissolved_date` | date | 0 (0%) | Date the bloc ceased to exist. |
| `notes` | string | 16 (40%) | Analyst notes. |

## `bloc_memberships`

**Unit of observation.** One row per person per bloc per spell.

Dated bloc membership. Consecutive rows for one person within one assembly are the defection record: this table is the primary input to analyses of bloc switching and parliamentary fragmentation.

**Primary key.** `bloc_membership_id`

**Rows.** 1,116

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `bloc_membership_id` | string | 1,116 (100%) | *(required, unique)* Identifier. |
| `person_id` | string → `persons.person_id` | 1,116 (100%) | *(required)* Member. |
| `bloc_id` | string → `blocs.bloc_id` | 1,116 (100%) | *(required)* Bloc. |
| `assembly_id` | string → `assemblies.assembly_id` | 1,116 (100%) | *(required)* Assembly. |
| `start_date` | date | 1,116 (100%) | Start of membership. |
| `end_date` | date | 748 (67%) | End of membership. |
| `role` | enum | 1,116 (100%) | Role in the bloc. One of: `speaker`, `first_vice_speaker`, `vice_speaker`, `bureau_member`, `bloc_chair`, `bloc_vice_chair`, `unknown`. |
| `is_founding_member` | boolean | 0 (0%) | Member at the bloc's constitution. |
| `dates_bracketed` | boolean | 478 (43%) | True where the spell's boundaries were derived by comparing dated observations rather than read from a published date. The change occurred somewhere in the interval ending at start_date, not necessarily on it. Applies to the 2014-2019 chamber, whose bloc history is reconstructed from monthly web captures. |
| `notes` | string | 478 (43%) | Analyst notes, including the bracketing interval where relevant. |
| `source_ids` | string → `sources.source_id` | 1,116 (100%) | Provenance. |

<details><summary>Distribution of <code>role</code></summary>

| Value | n |
| --- | --- |
| `unknown` | 1,092 |
| `bloc_vice_chair` | 12 |
| `bloc_chair` | 12 |

</details>

## `committees`

**Unit of observation.** One row per committee per assembly.

Standing and special committees, scoped to an assembly.

**Primary key.** `committee_id`

**Rows.** 54

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `committee_id` | string | 54 (100%) | *(required, unique)* Identifier. |
| `assembly_id` | string → `assemblies.assembly_id` | 54 (100%) | *(required)* Assembly. |
| `name_ar` | string | 54 (100%) | *(required)* Name, Arabic. |
| `name_lat` | string | 13 (24%) | Name, Latin script. |
| `name_en` | string | 0 (0%) | Name, English. |
| `type` | enum | 54 (100%) | Committee type. One of: `standing`, `legislative`, `constituent`, `special`, `inquiry`, `joint`, `unknown`. |
| `policy_domain` | string | 11 (20%) | Coarse policy domain for cross-term comparison. |
| `seats` | integer | 0 (0%) | Nominal membership size. |

<details><summary>Distribution of <code>type</code></summary>

| Value | n |
| --- | --- |
| `standing` | 31 |
| `legislative` | 8 |
| `special` | 7 |
| `constituent` | 6 |
| `joint` | 1 |
| `inquiry` | 1 |

</details>

## `committee_memberships`

**Unit of observation.** One row per person per committee per spell.

The bipartite person-committee structure. Projected to a person-person network this is the standard measure of legislative co-work in the literature.

**Primary key.** `committee_membership_id`

**Rows.** 1,129

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `committee_membership_id` | string | 1,129 (100%) | *(required, unique)* Identifier. |
| `person_id` | string → `persons.person_id` | 1,129 (100%) | *(required)* Member. |
| `committee_id` | string → `committees.committee_id` | 1,129 (100%) | *(required)* Committee. |
| `assembly_id` | string → `assemblies.assembly_id` | 1,129 (100%) | *(required)* Assembly. |
| `role` | enum | 1,129 (100%) | Role on the committee. One of: `chair`, `vice_chair`, `rapporteur`, `assistant_rapporteur`, `member`, `unknown`. |
| `start_date` | date | 1,129 (100%) | Start of service. |
| `end_date` | date | 635 (56%) | End of service. |
| `source_ids` | string → `sources.source_id` | 1,129 (100%) | Provenance. |

<details><summary>Distribution of <code>role</code></summary>

| Value | n |
| --- | --- |
| `member` | 846 |
| `chair` | 82 |
| `rapporteur` | 77 |
| `vice_chair` | 66 |
| `assistant_rapporteur` | 58 |

</details>

## `offices`

**Unit of observation.** One row per person per parliamentary office per spell.

Bureau and presiding offices of the chamber.

**Primary key.** `office_id`

**Rows.** 60

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `office_id` | string | 60 (100%) | *(required, unique)* Identifier. |
| `person_id` | string → `persons.person_id` | 60 (100%) | *(required)* Office holder. |
| `assembly_id` | string → `assemblies.assembly_id` | 60 (100%) | *(required)* Assembly. |
| `office` | enum | 60 (100%) | Office held. One of: `speaker`, `first_vice_speaker`, `vice_speaker`, `bureau_member`, `bloc_chair`, `bloc_vice_chair`, `unknown`. |
| `office_label_ar` | string | 60 (100%) | Office title as given by the source. |
| `start_date` | date | 60 (100%) | Start of tenure. |
| `end_date` | date | 32 (53%) | End of tenure. |
| `source_ids` | string → `sources.source_id` | 60 (100%) | Provenance. |

<details><summary>Distribution of <code>office</code></summary>

| Value | n |
| --- | --- |
| `bureau_member` | 39 |
| `speaker` | 12 |
| `unknown` | 5 |
| `vice_speaker` | 3 |
| `first_vice_speaker` | 1 |

</details>

## `careers`

**Unit of observation.** One row per person per extra-parliamentary role.

Non-parliamentary positions before, during and after a mandate. This is the elite-circulation layer: it supports revolving-door analysis, co-affiliation networks through shared organisations, and tests of whether parliamentary recruitment draws on the state, the party, the union movement or business.

**Primary key.** `career_id`

**Notes.** Rows are extracted from official biographies, which are unstructured and self-reported. ``extraction_method`` distinguishes a role parsed by rule from one coded by a human reader, and ``confidence`` should be consulted before using this table for inference.

**Rows.** 171

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `career_id` | string | 171 (100%) | *(required, unique)* Identifier. |
| `person_id` | string → `persons.person_id` | 171 (100%) | *(required)* Person. |
| `seq` | integer | 171 (100%) | Ordering within the person's career, where known. |
| `role_raw` | string | 171 (100%) | Role title as written by the source. |
| `role_en` | string | 0 (0%) | English gloss of the role. |
| `organisation_raw` | string | 18 (11%) | Organisation as written by the source. |
| `organisation_id` | string | 18 (11%) | Normalised organisation key, for co-affiliation networks. |
| `sector` | enum | 171 (100%) | Coded sector. One of: `state_executive`, `state_administration`, `party`, `trade_union`, `business`, `professional_association`, `civil_society`, `military`, `security`, `judiciary`, `academia`, `education`, `health`, `media`, `religious`, `local_government`, `international_organisation`, `diaspora_association`, `other`, `unknown`. |
| `is_ministerial` | boolean | 0 (0%) | Role is a cabinet post. |
| `start_date` | date | 0 (0%) | Start of role. |
| `end_date` | date | 0 (0%) | End of role. |
| `date_precision` | enum | 171 (100%) | Granularity of the dates. One of: `day`, `month`, `year`, `decade`, `unknown`. |
| `relative_to_mandate` | string | 171 (100%) | before, during, after, or unknown. |
| `extraction_method` | string | 171 (100%) | rule, manual, or source_structured. |
| `confidence` | enum | 171 (100%) | Analyst confidence in the row. One of: `high`, `medium`, `low`. |
| `source_ids` | string → `sources.source_id` | 171 (100%) | Provenance. |

<details><summary>Distribution of <code>sector</code></summary>

| Value | n |
| --- | --- |
| `education` | 46 |
| `judiciary` | 36 |
| `academia` | 23 |
| `party` | 16 |
| `trade_union` | 13 |
| `other` | 9 |
| `state_executive` | 8 |
| `health` | 7 |
| `business` | 3 |
| `military` | 3 |
| `religious` | 2 |
| `state_administration` | 2 |
| `media` | 2 |
| `civil_society` | 1 |

</details>

<details><summary>Distribution of <code>date_precision</code></summary>

| Value | n |
| --- | --- |
| `unknown` | 171 |

</details>

<details><summary>Distribution of <code>confidence</code></summary>

| Value | n |
| --- | --- |
| `medium` | 168 |
| `low` | 3 |

</details>

## `participation`

**Unit of observation.** One row per person per assembly.

Behavioural indicators published by the chamber or by Al Bawsala. Available only for the terms where an observatory operated, so these columns are structurally missing for the single-party era.

**Primary key.** `person_id, assembly_id`

**Notes.** Rates are proportions in [0, 1], not percentages. Denominators differ across sources and terms; ``*_denominator`` columns preserve them so that rates are not compared across incommensurable bases.

**Rows.** 583

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `person_id` | string → `persons.person_id` | 583 (100%) | *(required)* Person. |
| `assembly_id` | string → `assemblies.assembly_id` | 583 (100%) | *(required)* Assembly. |
| `plenary_attendance_rate` | number | 216 (37%) | Share of plenary sittings attended. |
| `plenary_denominator` | integer | 216 (37%) | Number of plenary sittings in the base. |
| `committee_attendance_rate` | number | 203 (35%) | Share of committee meetings attended. |
| `committee_denominator` | integer | 203 (35%) | Number of committee meetings in the base. |
| `vote_participation_rate` | number | 429 (74%) | Share of recorded votes in which the member voted. |
| `vote_denominator` | integer | 216 (37%) | Number of recorded votes in the base. |
| `vote_discipline_rate` | number | 207 (36%) | Share of votes cast with the member's bloc. |
| `n_written_questions` | integer | 154 (26%) | Written questions submitted. |
| `n_oral_questions` | integer | 0 (0%) | Oral questions submitted. |
| `source_ids` | string → `sources.source_id` | 583 (100%) | Provenance. |

## `votes`

**Unit of observation.** One row per recorded division.

Divisions on which a chamber's members are individually recorded. The title is the source's own description of what was voted on and is not normalised into bill identifiers, because the same instrument appears under several descriptions across procedural stages.

**Primary key.** `vote_id`

**Rows.** 1,724

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `vote_id` | string | 1,724 (100%) | *(required, unique)* Identifier. |
| `assembly_id` | string → `assemblies.assembly_id` | 1,724 (100%) | *(required)* Chamber. |
| `vote_date` | date | 1,724 (100%) | Date of the division. |
| `title` | string | 1,724 (100%) | The source's description of the division. |
| `source_url` | string | 0 (0%) | Page the division was read from. |
| `n_recorded` | integer | 1,724 (100%) | Members with a recorded position. |
| `source_ids` | string → `sources.source_id` | 1,724 (100%) | Provenance. |

## `vote_positions`

**Unit of observation.** One row per member per division.

How each member is recorded on each division. A member missing from a division has no row rather than a row reading 'absent': members who joined late or left early are simply not listed, and inventing an absence for them would be a different claim from the one the source makes. Note that 'absent' as published conflates being away with being present and not voting; the source does not separate them.

**Primary key.** `vote_id, person_id`

**Rows.** 370,922

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `vote_id` | string → `votes.vote_id` | 370,922 (100%) | *(required)* Division. |
| `person_id` | string → `persons.person_id` | 370,922 (100%) | *(required)* Member. |
| `assembly_id` | string → `assemblies.assembly_id` | 370,922 (100%) | *(required)* Chamber. |
| `position` | enum | 370,922 (100%) | *(required)* Recorded position. One of: `pour`, `contre`, `abstenu`, `absent`. |
| `source_ids` | string → `sources.source_id` | 370,922 (100%) | Provenance. |

<details><summary>Distribution of <code>position</code></summary>

| Value | n |
| --- | --- |
| `pour` | 187,239 |
| `absent` | 129,240 |
| `contre` | 35,654 |
| `abstenu` | 18,789 |

</details>

## `party_switches`

**Unit of observation.** One row per member per recorded change of party within a term.

The party a member was elected on against the party they ended the term in. Undated by construction: the source publishes the pair, not the moment, so a row establishes that a move happened and not when. Members who kept their party have no row, which is why the absence of a row here means 'did not move', unlike missingness elsewhere in the dataset.

The two id columns are empty where the published party name does not resolve to the curated register. That is deliberate. The source names parties in French only, and the near-misses are treacherous: 'Parti communiste des ouvriers de Tunisie' and 'Parti communiste tunisien' are different parties, so a fuzzy match would silently merge two organisations. The verbatim names are always present, and crosswalking them is left to a human who can tell those two apart.

**Primary key.** `person_id, assembly_id, party_from_name, party_to_name`

**Rows.** 105

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `person_id` | string → `persons.person_id` | 105 (100%) | *(required)* Member. |
| `assembly_id` | string → `assemblies.assembly_id` | 105 (100%) | *(required)* Chamber. |
| `party_from_id` | string → `parties.party_id` | 40 (38%) | Party of election; empty where the published name does not resolve to the curated register. |
| `party_to_id` | string → `parties.party_id` | 98 (93%) | Party at end of term; empty where the published name does not resolve to the curated register. |
| `party_from_name` | string | 105 (100%) | Party of election, as published. |
| `party_to_name` | string | 105 (100%) | Party at end of term, as published. |
| `source_ids` | string → `sources.source_id` | 105 (100%) | Provenance. |

## `amendments`

**Unit of observation.** One row per tabled amendment.

Amendments tabled to the text of the constitution during the 2011-2014 drafting. Sponsorship is collective, so the sponsors are a separate table rather than a column.

**Primary key.** `amendment_id`

**Rows.** 251

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `amendment_id` | string | 251 (100%) | *(required, unique)* Identifier. |
| `assembly_id` | string → `assemblies.assembly_id` | 251 (100%) | *(required)* Chamber. |
| `target_label` | string | 251 (100%) | Article or section amended, as published. |
| `target_url` | string | 251 (100%) | Source link to the article amended. |
| `text` | string | 251 (100%) | The amendment's wording, as published. |
| `n_sponsors` | integer | 251 (100%) | Number of members who tabled it. |
| `source_ids` | string → `sources.source_id` | 251 (100%) | Provenance. |

## `amendment_sponsorships`

**Unit of observation.** One row per member per amendment they tabled.

Who tabled which amendment. This is a chosen tie rather than an assigned one, which makes it the constituent assembly's counterpart to the written-question co-signatures recorded for the 2023 chamber.

**Primary key.** `amendment_id, person_id`

**Rows.** 3,646

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `amendment_id` | string → `amendments.amendment_id` | 3,646 (100%) | *(required)* Amendment. |
| `person_id` | string → `persons.person_id` | 3,646 (100%) | *(required)* Sponsor. |
| `assembly_id` | string → `assemblies.assembly_id` | 3,646 (100%) | *(required)* Chamber. |
| `source_ids` | string → `sources.source_id` | 3,646 (100%) | Provenance. |

## `person_xref`

**Unit of observation.** One row per person per external identifier.

Crosswalk from dataset person_id to every upstream identifier. This is what makes collection idempotent: a re-run resolves an upstream record to the same person_id instead of minting a duplicate. It also lets other researchers join their own scraped data to this dataset.

**Primary key.** `person_id, source_id, source_key`

**Rows.** 950

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `person_id` | string → `persons.person_id` | 950 (100%) | *(required)* Dataset person. |
| `source_id` | string → `sources.source_id` | 950 (100%) | *(required)* Source system. |
| `source_key` | string | 950 (100%) | *(required)* Primary key within that source. Example: `742`. |
| `source_url` | string | 942 (99%) | Resolvable URL for the upstream record. |
| `match_method` | string | 950 (100%) | How the link was made: source_id, exact_name, normalised_name, manual. |
| `match_confidence` | enum | 950 (100%) | Confidence in the linkage. One of: `high`, `medium`, `low`. |

<details><summary>Distribution of <code>match_confidence</code></summary>

| Value | n |
| --- | --- |
| `high` | 942 |
| `medium` | 8 |

</details>

## `sources`

**Unit of observation.** One row per data source.

Source register, with access conditions and coverage.

**Primary key.** `source_id`

**Rows.** 6

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `source_id` | string | 6 (100%) | *(required, unique)* Identifier. Example: `ARP_ODOO`. |
| `name` | string | 6 (100%) | *(required)* Human-readable name. |
| `publisher` | string | 6 (100%) | Publishing body. |
| `url` | string | 5 (83%) | Entry-point URL. |
| `access_method` | string | 6 (100%) | How the data is obtained. |
| `coverage` | string | 6 (100%) | Assemblies and variables covered. |
| `language` | string | 6 (100%) | Language(s) of the source. |
| `licence` | string | 6 (100%) | Licence or terms, where stated. |
| `first_retrieved` | date | 5 (83%) | First retrieval date. |
| `last_retrieved` | date | 5 (83%) | Most recent retrieval date. |
| `reliability_notes` | string | 6 (100%) | Known errors and cautions. |

## `provenance`

**Unit of observation.** One row per (table, record, field) that a source supplied.

Cell-level provenance. Kept as a long table so that a single field can carry several corroborating or conflicting sources, and so that disagreement between sources is data rather than a silent overwrite.

**Primary key.** `table_name, record_id, field_name, source_id`

**Rows.** 5,039

| Variable | Type | Non-empty | Description |
| --- | --- | --- | --- |
| `table_name` | string | 5,039 (100%) | *(required)* Target table. |
| `record_id` | string | 5,039 (100%) | *(required)* Primary key of the target record. |
| `field_name` | string | 5,039 (100%) | *(required)* Target column. |
| `source_id` | string → `sources.source_id` | 5,039 (100%) | *(required)* Supplying source. |
| `value_hash` | string | 5,039 (100%) | Short hash of the supplied value, to detect upstream revision. |
| `retrieved_at` | date | 5,039 (100%) | Retrieval date. |
| `confidence` | enum | 5,039 (100%) | Confidence in this value. One of: `high`, `medium`, `low`. |

<details><summary>Distribution of <code>confidence</code></summary>

| Value | n |
| --- | --- |
| `medium` | 3,800 |
| `high` | 1,239 |

</details>

