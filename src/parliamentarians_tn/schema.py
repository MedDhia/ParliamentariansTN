"""Single source of truth for the ParliamentariansTN relational schema.

Every processed table is declared here as a :class:`Table`. The build step, the
validator, the codebook generator and the network derivation all read these
declarations, so a column added here propagates everywhere instead of drifting
between code and documentation.

Design commitments
------------------
1. *Person / mandate separation.* A parliamentarian is one row in ``persons``
   however many times they are returned to parliament. Each term is a row in
   ``mandates``. This is what makes elite-circulation and re-election analysis
   possible, and it is the single most common modelling error in legislator
   datasets.
2. *Spells, not snapshots.* Party, bloc, committee and career attachments are
   stored as dated spells with ``start_date`` / ``end_date``. A deputy who
   defects mid-term produces two bloc rows, not one overwritten value. Bloc
   switching is therefore recoverable rather than lost.
3. *Explicit missingness.* An empty cell means "not recorded by any source we
   consulted". It never means zero, and never means "false". Date precision is
   carried in a companion ``*_precision`` column so that a birth year known only
   to the year is not silently treated as 1 January.
4. *Cell-level provenance.* ``provenance`` records which source supplied which
   field of which record, so any value in the dataset can be traced to a URL and
   a retrieval date. This is what lets the dataset be cited in peer review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str  # "string" | "integer" | "number" | "date" | "boolean" | "enum"
    description: str
    required: bool = False
    unique: bool = False
    enum: tuple[str, ...] | None = None
    references: str | None = None  # "table.column"
    example: str = ""


@dataclass(frozen=True)
class Table:
    name: str
    unit: str
    description: str
    columns: Sequence[Column]
    primary_key: tuple[str, ...] = ()
    notes: str = ""

    @property
    def column_names(self) -> list[str]:
        return [c.name for c in self.columns]

    def column(self, name: str) -> Column:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name} has no column {name!r}")


# --------------------------------------------------------------------------
# Controlled vocabularies
# --------------------------------------------------------------------------

DATE_PRECISION = ("day", "month", "year", "decade", "unknown")

ASSEMBLY_TYPE = (
    "constituent",  # 1956-59 ANC; 2011-14 NCA
    "ordinary_lower",  # National Assembly / Chamber of Deputies / ARP
    "ordinary_upper",  # Chamber of Advisors 2005-2011
    "regional",  # National Council of Regions and Districts 2023-
)

REGIME_PERIOD = (
    "protectorate_transition",  # 1956-1957, monarchy formally standing
    "bourguiba",  # 1957-1987
    "ben_ali",  # 1987-2011
    "transition",  # 2011-2014
    "second_republic",  # 2014-2021
    "exceptional_measures",  # 2021-2022, post 25 July
    "third_republic",  # 2022-
)

ENTRY_MODE = (
    "elected",
    "elected_byelection",
    "replacement_list",  # next candidate on the electoral list
    "appointed",
    "ex_officio",
    "unknown",
)

EXIT_MODE = (
    "end_of_term",
    "death",
    "resignation",
    "revocation",  # withdrawal of mandate
    "dissolution",  # assembly dissolved or frozen
    "became_minister",
    "elected_president",
    "still_serving",
    "unknown",
)

PARTY_FAMILY = (
    "destourian",  # Neo-Destour / PSD / RCD and successors
    "islamist",
    "left",
    "social_democratic",
    "liberal",
    "arab_nationalist",
    "national_conservative",
    "independent",
    "other",
    "unknown",
)

# The 2011-14 Constituent Assembly ran two parallel committee systems — six
# constituent committees drafting the constitution and a set of legislative
# committees handling ordinary business — and the distinction is substantive,
# so it is carried in the type rather than flattened into "standing".
COMMITTEE_TYPE = (
    "standing",
    "legislative",
    "constituent",
    "special",
    "inquiry",
    "joint",
    "unknown",
)

COMMITTEE_ROLE = ("chair", "vice_chair", "rapporteur", "assistant_rapporteur", "member", "unknown")

OFFICE = (
    "speaker",
    "first_vice_speaker",
    "vice_speaker",
    "bureau_member",
    "bloc_chair",
    "unknown",
)

# Sector of a pre- or post-parliamentary role. This is the backbone of the
# elite-circulation layer the dataset prioritises.
CAREER_SECTOR = (
    "state_executive",  # minister, governor, senior civil service
    "state_administration",
    "party",
    "trade_union",
    "business",
    "professional_association",
    "civil_society",
    "military",
    "security",
    "judiciary",
    "academia",
    "education",
    "health",
    "media",
    "religious",
    "local_government",
    "international_organisation",
    "diaspora_association",
    "other",
    "unknown",
)

GENDER = ("female", "male", "other", "unknown")

CONFIDENCE = ("high", "medium", "low")


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

PERSONS = Table(
    name="persons",
    unit="One row per natural person who has held a parliamentary mandate.",
    primary_key=("person_id",),
    description=(
        "The person registry. Identity is deliberately thin: names, sex, vital "
        "dates, origin. Everything time-varying lives in the spell tables so "
        "that a person's record does not have to be rewritten when their "
        "affiliation changes."
    ),
    notes=(
        "Names are stored in both Arabic script and Latin script because no "
        "single romanisation is authoritative in Tunisian practice: the ARP, "
        "Al Bawsala and the electoral commission romanise the same name "
        "differently. Matching across sources uses the normalised Arabic form "
        "(see ids.normalize_arabic) with the Latin form as a fallback."
    ),
    columns=[
        Column("person_id", "string", "Stable dataset identifier, format TNP-00000.", required=True, unique=True, example="TNP-00042"),
        Column("name_ar", "string", "Full name in Arabic script as given by the most authoritative source.", example="إبراهيم بودربالة"),
        Column("name_lat", "string", "Full name in Latin script.", example="Brahim Bouderbela"),
        Column("given_name_ar", "string", "Given name, Arabic script."),
        Column("family_name_ar", "string", "Family name, Arabic script."),
        Column("given_name_lat", "string", "Given name, Latin script."),
        Column("family_name_lat", "string", "Family name, Latin script."),
        Column("name_normalised", "string", "Diacritic- and orthography-normalised Arabic key used for cross-source matching.", example="ابراهيم بودربالة"),
        Column("gender", "enum", "Sex as recorded by the source. Sources record a binary; 'unknown' where absent.", enum=GENDER),
        Column("birth_date", "date", "Date of birth, ISO 8601. Partial dates are padded and flagged in birth_date_precision."),
        Column("birth_date_precision", "enum", "Granularity actually known for birth_date.", enum=DATE_PRECISION),
        Column("birth_place_ar", "string", "Locality of birth as written by the source, Arabic script."),
        Column("birth_governorate_id", "string", "Governorate of birth.", references="governorates.governorate_id"),
        Column("death_date", "date", "Date of death where applicable."),
        Column("death_date_precision", "enum", "Granularity of death_date.", enum=DATE_PRECISION),
        Column("marital_status", "string", "Marital status as reported (free text, source wording preserved)."),
        Column("n_children", "integer", "Number of children where reported."),
        Column("languages", "string", "Semicolon-separated languages claimed in the official biography.", example="ar;fr;en"),
        Column("education_raw", "string", "Education as written by the source, untranslated."),
        Column("education_level", "string", "Coded highest attainment; see docs/CODEBOOK.md."),
        Column("occupation_raw", "string", "Pre-parliamentary occupation as written by the source."),
        Column("occupation_sector", "enum", "Coded sector of the principal pre-parliamentary occupation.", enum=CAREER_SECTOR),
        Column("biography_ar", "string", "Official biographical text, Arabic, verbatim. Long free text."),
        Column("wikidata_qid", "string", "Wikidata item, where a match was verified.", example="Q3576068"),
        Column("first_mandate_start", "date", "Derived: start of earliest mandate."),
        Column("n_mandates", "integer", "Derived: number of distinct mandates held."),
    ],
)

ASSEMBLIES = Table(
    name="assemblies",
    unit="One row per parliamentary chamber-term (a legislature).",
    primary_key=("assembly_id",),
    description=(
        "The institutional frame, complete from the 1956 Constituent Assembly "
        "to the present. This table is hand-curated from constitutional and "
        "electoral-law sources rather than scraped, and it is what makes the "
        "dataset a time series rather than a set of disconnected snapshots."
    ),
    notes=(
        "Chamber-terms are the unit, not chambers. The 2019 ARP therefore ends "
        "in 2021 de facto (frozen by presidential decree) while its nominal "
        "term ran to 2024; both dates are recorded, because the distinction is "
        "the object of study for work on democratic breakdown."
    ),
    columns=[
        Column("assembly_id", "string", "Stable identifier.", required=True, unique=True, example="ARP-2023"),
        Column("name_ar", "string", "Official name, Arabic.", required=True),
        Column("name_fr", "string", "Official name, French."),
        Column("name_en", "string", "Conventional English name."),
        Column("type", "enum", "Chamber type.", enum=ASSEMBLY_TYPE, required=True),
        Column("ordinal", "integer", "Sequence number within the dataset, 1 = 1956 Constituent Assembly."),
        Column("start_date", "date", "First sitting. Empty where the date is not established (see notes)."),
        Column("end_date", "date", "Last sitting in fact. Empty if still sitting."),
        Column("nominal_end_date", "date", "End of term as provided in law, where it differs from end_date."),
        Column("seats_nominal", "integer", "Seats provided for by law."),
        Column("seats_filled", "integer", "Seats actually filled at opening, where known."),
        Column("seats_women", "integer", "Seats held by women at opening, where known."),
        Column("electoral_system", "string", "Formula used to return the chamber."),
        Column("suffrage", "string", "Franchise rules of note."),
        Column("regime_period", "enum", "Regime period in which the chamber sat.", enum=REGIME_PERIOD),
        Column("termination_mode", "string", "How the chamber ended: normal expiry, dissolution, freezing, supersession."),
        Column("speaker_person_id", "string", "Presiding officer, where identified.", references="persons.person_id"),
        Column("legal_basis", "string", "Constitution or decree establishing the chamber."),
        Column("coverage_status", "string", "Person-level coverage in this dataset: full, partial, frame_only."),
        Column("notes", "string", "Analyst notes, including known contested facts."),
    ],
)

MANDATES = Table(
    name="mandates",
    unit="One row per person per assembly per continuous spell of service.",
    primary_key=("mandate_id",),
    description=(
        "The core event table. A person returned in three legislatures has "
        "three rows; a person who replaces a resigning deputy mid-term has a "
        "row whose start_date is the replacement date, not the assembly's."
    ),
    columns=[
        Column("mandate_id", "string", "Stable identifier.", required=True, unique=True, example="TNM-00713"),
        Column("person_id", "string", "Holder of the mandate.", required=True, references="persons.person_id"),
        Column("assembly_id", "string", "Chamber-term served in.", required=True, references="assemblies.assembly_id"),
        Column("start_date", "date", "Start of this spell of service."),
        Column("end_date", "date", "End of this spell. Empty where still serving."),
        Column("entry_mode", "enum", "How the seat was obtained.", enum=ENTRY_MODE),
        Column("exit_mode", "enum", "How the mandate ended.", enum=EXIT_MODE),
        Column("constituency_id", "string", "Seat's constituency.", references="constituencies.constituency_id"),
        Column("governorate_id", "string", "Governorate of the constituency (denormalised for convenience).", references="governorates.governorate_id"),
        Column("electoral_list_ar", "string", "Name of the list on which the person was returned, Arabic."),
        Column("electoral_list_lat", "string", "Name of the list, Latin script."),
        Column("party_id_at_election", "string", "Party sponsoring the list, where applicable.", references="parties.party_id"),
        Column("seat_number", "string", "Seat or file number used by the chamber."),
        Column("is_diaspora_seat", "boolean", "True where the constituency is an out-of-country constituency."),
        Column("election_date", "date", "Date of the election returning this mandate."),
        Column("source_ids", "string", "Semicolon-separated source_id list.", references="sources.source_id"),
    ],
)

GOVERNORATES = Table(
    name="governorates",
    unit="One row per governorate.",
    primary_key=("governorate_id",),
    description=(
        "Tunisia's 24 governorates plus out-of-country groupings, with the "
        "regional aggregations used in the literature on interior/coastal "
        "inequality. Provides the geographic homophily dimension."
    ),
    columns=[
        Column("governorate_id", "string", "Identifier.", required=True, unique=True, example="TN-31"),
        Column("name_ar", "string", "Name, Arabic.", required=True),
        Column("name_lat", "string", "Name, Latin script."),
        Column("name_fr", "string", "Name, French."),
        Column("iso_3166_2", "string", "ISO 3166-2:TN code where one exists."),
        Column("region", "string", "Statistical region (Grand Tunis, North East, North West, Centre East, Centre West, South East, South West, abroad)."),
        Column("littoral", "boolean", "Coastal governorate, per the coastal/interior cleavage."),
        Column("created_year", "integer", "Year the governorate was created, for historical comparability."),
    ],
)

CONSTITUENCIES = Table(
    name="constituencies",
    unit="One row per constituency per assembly.",
    primary_key=("constituency_id",),
    description=(
        "Constituency boundaries and magnitudes change between elections, so "
        "constituencies are scoped to an assembly rather than treated as "
        "permanent units."
    ),
    columns=[
        Column("constituency_id", "string", "Identifier.", required=True, unique=True),
        Column("assembly_id", "string", "Assembly this delimitation applies to.", required=True, references="assemblies.assembly_id"),
        Column("name_ar", "string", "Name, Arabic.", required=True),
        Column("name_lat", "string", "Name, Latin script."),
        Column("governorate_id", "string", "Containing governorate, empty for out-of-country seats.", references="governorates.governorate_id"),
        Column("is_abroad", "boolean", "Out-of-country constituency."),
        Column("magnitude", "integer", "Number of seats returned."),
    ],
)

PARTIES = Table(
    name="parties",
    unit="One row per political party.",
    primary_key=("party_id",),
    description=(
        "Party register spanning the single-party era and the post-2011 "
        "multiparty period, with successor links so that the "
        "Neo-Destour / PSD / RCD lineage can be followed as one organisation "
        "or three, at the analyst's choice."
    ),
    columns=[
        Column("party_id", "string", "Identifier.", required=True, unique=True, example="PTY-RCD"),
        Column("name_ar", "string", "Name, Arabic.", required=True),
        Column("name_fr", "string", "Name, French."),
        Column("name_en", "string", "Name, English."),
        Column("abbrev", "string", "Common abbreviation.", example="RCD"),
        Column("family", "enum", "Ideological family.", enum=PARTY_FAMILY),
        Column("founded_date", "date", "Foundation date."),
        Column("dissolved_date", "date", "Dissolution date."),
        Column("predecessor_party_id", "string", "Organisational predecessor.", references="parties.party_id"),
        Column("wikidata_qid", "string", "Wikidata item."),
        Column("notes", "string", "Analyst notes."),
    ],
)

PARTY_AFFILIATIONS = Table(
    name="party_affiliations",
    unit="One row per person per party per spell.",
    primary_key=("affiliation_id",),
    description=(
        "Party membership as dated spells, independent of parliamentary "
        "service, so that pre-parliamentary and post-parliamentary membership "
        "is representable."
    ),
    columns=[
        Column("affiliation_id", "string", "Identifier.", required=True, unique=True),
        Column("person_id", "string", "Member.", required=True, references="persons.person_id"),
        Column("party_id", "string", "Party.", required=True, references="parties.party_id"),
        Column("start_date", "date", "Start of membership spell."),
        Column("end_date", "date", "End of membership spell."),
        Column("role", "string", "Role held in the party, e.g. political bureau member."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

BLOCS = Table(
    name="blocs",
    unit="One row per parliamentary bloc per assembly.",
    primary_key=("bloc_id",),
    description=(
        "Parliamentary blocs (kutla) are the operative unit of legislative "
        "behaviour after 2011 and are not identical to parties: blocs form, "
        "split and dissolve within a term."
    ),
    columns=[
        Column("bloc_id", "string", "Identifier.", required=True, unique=True),
        Column("assembly_id", "string", "Assembly in which the bloc existed.", required=True, references="assemblies.assembly_id"),
        Column("name_ar", "string", "Name, Arabic.", required=True),
        Column("name_lat", "string", "Name, Latin script."),
        Column("party_id", "string", "Dominant party, where the bloc is a party bloc.", references="parties.party_id"),
        Column("formed_date", "date", "Date the bloc was constituted."),
        Column("dissolved_date", "date", "Date the bloc ceased to exist."),
        Column("notes", "string", "Analyst notes."),
    ],
)

BLOC_MEMBERSHIPS = Table(
    name="bloc_memberships",
    unit="One row per person per bloc per spell.",
    primary_key=("bloc_membership_id",),
    description=(
        "Dated bloc membership. Consecutive rows for one person within one "
        "assembly are the defection record: this table is the primary input to "
        "analyses of bloc switching and parliamentary fragmentation."
    ),
    columns=[
        Column("bloc_membership_id", "string", "Identifier.", required=True, unique=True),
        Column("person_id", "string", "Member.", required=True, references="persons.person_id"),
        Column("bloc_id", "string", "Bloc.", required=True, references="blocs.bloc_id"),
        Column("assembly_id", "string", "Assembly.", required=True, references="assemblies.assembly_id"),
        Column("start_date", "date", "Start of membership."),
        Column("end_date", "date", "End of membership."),
        Column("role", "enum", "Role in the bloc.", enum=OFFICE),
        Column("is_founding_member", "boolean", "Member at the bloc's constitution."),
        Column(
            "dates_bracketed",
            "boolean",
            "True where the spell's boundaries were derived by comparing dated "
            "observations rather than read from a published date. The change "
            "occurred somewhere in the interval ending at start_date, not "
            "necessarily on it. Applies to the 2014-2019 chamber, whose bloc "
            "history is reconstructed from monthly web captures.",
        ),
        Column("notes", "string", "Analyst notes, including the bracketing interval where relevant."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

COMMITTEES = Table(
    name="committees",
    unit="One row per committee per assembly.",
    primary_key=("committee_id",),
    description="Standing and special committees, scoped to an assembly.",
    columns=[
        Column("committee_id", "string", "Identifier.", required=True, unique=True),
        Column("assembly_id", "string", "Assembly.", required=True, references="assemblies.assembly_id"),
        Column("name_ar", "string", "Name, Arabic.", required=True),
        Column("name_lat", "string", "Name, Latin script."),
        Column("name_en", "string", "Name, English."),
        Column("type", "enum", "Committee type.", enum=COMMITTEE_TYPE),
        Column("policy_domain", "string", "Coarse policy domain for cross-term comparison."),
        Column("seats", "integer", "Nominal membership size."),
    ],
)

COMMITTEE_MEMBERSHIPS = Table(
    name="committee_memberships",
    unit="One row per person per committee per spell.",
    primary_key=("committee_membership_id",),
    description=(
        "The bipartite person-committee structure. Projected to a "
        "person-person network this is the standard measure of legislative "
        "co-work in the literature."
    ),
    columns=[
        Column("committee_membership_id", "string", "Identifier.", required=True, unique=True),
        Column("person_id", "string", "Member.", required=True, references="persons.person_id"),
        Column("committee_id", "string", "Committee.", required=True, references="committees.committee_id"),
        Column("assembly_id", "string", "Assembly.", required=True, references="assemblies.assembly_id"),
        Column("role", "enum", "Role on the committee.", enum=COMMITTEE_ROLE),
        Column("start_date", "date", "Start of service."),
        Column("end_date", "date", "End of service."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

OFFICES = Table(
    name="offices",
    unit="One row per person per parliamentary office per spell.",
    primary_key=("office_id",),
    description="Bureau and presiding offices of the chamber.",
    columns=[
        Column("office_id", "string", "Identifier.", required=True, unique=True),
        Column("person_id", "string", "Office holder.", required=True, references="persons.person_id"),
        Column("assembly_id", "string", "Assembly.", required=True, references="assemblies.assembly_id"),
        Column("office", "enum", "Office held.", enum=OFFICE),
        Column("office_label_ar", "string", "Office title as given by the source."),
        Column("start_date", "date", "Start of tenure."),
        Column("end_date", "date", "End of tenure."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

CAREERS = Table(
    name="careers",
    unit="One row per person per extra-parliamentary role.",
    primary_key=("career_id",),
    description=(
        "Non-parliamentary positions before, during and after a mandate. This "
        "is the elite-circulation layer: it supports revolving-door analysis, "
        "co-affiliation networks through shared organisations, and tests of "
        "whether parliamentary recruitment draws on the state, the party, the "
        "union movement or business."
    ),
    notes=(
        "Rows are extracted from official biographies, which are unstructured "
        "and self-reported. ``extraction_method`` distinguishes a role parsed "
        "by rule from one coded by a human reader, and ``confidence`` should be "
        "consulted before using this table for inference."
    ),
    columns=[
        Column("career_id", "string", "Identifier.", required=True, unique=True),
        Column("person_id", "string", "Person.", required=True, references="persons.person_id"),
        Column("seq", "integer", "Ordering within the person's career, where known."),
        Column("role_raw", "string", "Role title as written by the source."),
        Column("role_en", "string", "English gloss of the role."),
        Column("organisation_raw", "string", "Organisation as written by the source."),
        Column("organisation_id", "string", "Normalised organisation key, for co-affiliation networks."),
        Column("sector", "enum", "Coded sector.", enum=CAREER_SECTOR),
        Column("is_ministerial", "boolean", "Role is a cabinet post."),
        Column("start_date", "date", "Start of role."),
        Column("end_date", "date", "End of role."),
        Column("date_precision", "enum", "Granularity of the dates.", enum=DATE_PRECISION),
        Column("relative_to_mandate", "string", "before, during, after, or unknown."),
        Column("extraction_method", "string", "rule, manual, or source_structured."),
        Column("confidence", "enum", "Analyst confidence in the row.", enum=CONFIDENCE),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

PARTICIPATION = Table(
    name="participation",
    unit="One row per person per assembly.",
    primary_key=("person_id", "assembly_id"),
    description=(
        "Behavioural indicators published by the chamber or by Al Bawsala. "
        "Available only for the terms where an observatory operated, so these "
        "columns are structurally missing for the single-party era."
    ),
    notes=(
        "Rates are proportions in [0, 1], not percentages. Denominators differ "
        "across sources and terms; ``*_denominator`` columns preserve them so "
        "that rates are not compared across incommensurable bases."
    ),
    columns=[
        Column("person_id", "string", "Person.", required=True, references="persons.person_id"),
        Column("assembly_id", "string", "Assembly.", required=True, references="assemblies.assembly_id"),
        Column("plenary_attendance_rate", "number", "Share of plenary sittings attended."),
        Column("plenary_denominator", "integer", "Number of plenary sittings in the base."),
        Column("committee_attendance_rate", "number", "Share of committee meetings attended."),
        Column("committee_denominator", "integer", "Number of committee meetings in the base."),
        Column("vote_participation_rate", "number", "Share of recorded votes in which the member voted."),
        Column("vote_denominator", "integer", "Number of recorded votes in the base."),
        Column("vote_discipline_rate", "number", "Share of votes cast with the member's bloc."),
        Column("n_written_questions", "integer", "Written questions submitted."),
        Column("n_oral_questions", "integer", "Oral questions submitted."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

PERSON_XREF = Table(
    name="person_xref",
    unit="One row per person per external identifier.",
    primary_key=("person_id", "source_id", "source_key"),
    description=(
        "Crosswalk from dataset person_id to every upstream identifier. This "
        "is what makes collection idempotent: a re-run resolves an upstream "
        "record to the same person_id instead of minting a duplicate. It also "
        "lets other researchers join their own scraped data to this dataset."
    ),
    columns=[
        Column("person_id", "string", "Dataset person.", required=True, references="persons.person_id"),
        Column("source_id", "string", "Source system.", required=True, references="sources.source_id"),
        Column("source_key", "string", "Primary key within that source.", required=True, example="742"),
        Column("source_url", "string", "Resolvable URL for the upstream record."),
        Column("match_method", "string", "How the link was made: source_id, exact_name, normalised_name, manual."),
        Column("match_confidence", "enum", "Confidence in the linkage.", enum=CONFIDENCE),
    ],
)

SOURCES = Table(
    name="sources",
    unit="One row per data source.",
    primary_key=("source_id",),
    description="Source register, with access conditions and coverage.",
    columns=[
        Column("source_id", "string", "Identifier.", required=True, unique=True, example="ARP_ODOO"),
        Column("name", "string", "Human-readable name.", required=True),
        Column("publisher", "string", "Publishing body."),
        Column("url", "string", "Entry-point URL."),
        Column("access_method", "string", "How the data is obtained."),
        Column("coverage", "string", "Assemblies and variables covered."),
        Column("language", "string", "Language(s) of the source."),
        Column("licence", "string", "Licence or terms, where stated."),
        Column("first_retrieved", "date", "First retrieval date."),
        Column("last_retrieved", "date", "Most recent retrieval date."),
        Column("reliability_notes", "string", "Known errors and cautions."),
    ],
)

PROVENANCE = Table(
    name="provenance",
    unit="One row per (table, record, field) that a source supplied.",
    primary_key=("table_name", "record_id", "field_name", "source_id"),
    description=(
        "Cell-level provenance. Kept as a long table so that a single field can "
        "carry several corroborating or conflicting sources, and so that "
        "disagreement between sources is data rather than a silent overwrite."
    ),
    columns=[
        Column("table_name", "string", "Target table.", required=True),
        Column("record_id", "string", "Primary key of the target record.", required=True),
        Column("field_name", "string", "Target column.", required=True),
        Column("source_id", "string", "Supplying source.", required=True, references="sources.source_id"),
        Column("value_hash", "string", "Short hash of the supplied value, to detect upstream revision."),
        Column("retrieved_at", "date", "Retrieval date."),
        Column("confidence", "enum", "Confidence in this value.", enum=CONFIDENCE),
    ],
)


# ---------------------------------------------------------------------------
# Recorded divisions
# ---------------------------------------------------------------------------

VOTE_POSITION = ("pour", "contre", "abstenu", "absent")

VOTES = Table(
    name="votes",
    unit="One row per recorded division.",
    primary_key=("vote_id",),
    description=(
        "Divisions on which a chamber's members are individually recorded. The "
        "title is the source's own description of what was voted on and is not "
        "normalised into bill identifiers, because the same instrument appears "
        "under several descriptions across procedural stages."
    ),
    columns=[
        Column("vote_id", "string", "Identifier.", required=True, unique=True),
        Column("assembly_id", "string", "Chamber.", required=True,
               references="assemblies.assembly_id"),
        Column("vote_date", "date", "Date of the division."),
        Column("title", "string", "The source's description of the division."),
        Column("source_url", "string", "Page the division was read from."),
        Column("n_recorded", "integer", "Members with a recorded position."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

VOTE_POSITIONS = Table(
    name="vote_positions",
    unit="One row per member per division.",
    primary_key=("vote_id", "person_id"),
    description=(
        "How each member is recorded on each division. A member missing from a "
        "division has no row rather than a row reading 'absent': members who "
        "joined late or left early are simply not listed, and inventing an "
        "absence for them would be a different claim from the one the source "
        "makes. Note that 'absent' as published conflates being away with being "
        "present and not voting; the source does not separate them."
    ),
    columns=[
        Column("vote_id", "string", "Division.", required=True, references="votes.vote_id"),
        Column("person_id", "string", "Member.", required=True,
               references="persons.person_id"),
        Column("assembly_id", "string", "Chamber.", required=True,
               references="assemblies.assembly_id"),
        Column("position", "enum", "Recorded position.", required=True,
               enum=VOTE_POSITION),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

PARTY_SWITCHES = Table(
    name="party_switches",
    unit="One row per member per recorded change of party within a term.",
    primary_key=("person_id", "assembly_id", "party_from_id", "party_to_id"),
    description=(
        "The party a member was elected on against the party they ended the term "
        "in. Undated by construction: the source publishes the pair, not the "
        "moment, so a row establishes that a move happened and not when. Members "
        "who kept their party have no row, which is why the absence of a row "
        "here means 'did not move', unlike missingness elsewhere in the dataset."
    ),
    columns=[
        Column("person_id", "string", "Member.", required=True,
               references="persons.person_id"),
        Column("assembly_id", "string", "Chamber.", required=True,
               references="assemblies.assembly_id"),
        Column("party_from_id", "string", "Party of election.", required=True,
               references="parties.party_id"),
        Column("party_to_id", "string", "Party at end of term.", required=True,
               references="parties.party_id"),
        Column("party_from_name", "string", "Party of election, as published."),
        Column("party_to_name", "string", "Party at end of term, as published."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

# ---------------------------------------------------------------------------
# Constitutional amendments
# ---------------------------------------------------------------------------

AMENDMENTS = Table(
    name="amendments",
    unit="One row per tabled amendment.",
    primary_key=("amendment_id",),
    description=(
        "Amendments tabled to the text of the constitution during the 2011-2014 "
        "drafting. Sponsorship is collective, so the sponsors are a separate "
        "table rather than a column."
    ),
    columns=[
        Column("amendment_id", "string", "Identifier.", required=True, unique=True),
        Column("assembly_id", "string", "Chamber.", required=True,
               references="assemblies.assembly_id"),
        Column("target_label", "string", "Article or section amended, as published."),
        Column("target_url", "string", "Source link to the article amended."),
        Column("text", "string", "The amendment's wording, as published."),
        Column("n_sponsors", "integer", "Number of members who tabled it."),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)

AMENDMENT_SPONSORSHIPS = Table(
    name="amendment_sponsorships",
    unit="One row per member per amendment they tabled.",
    primary_key=("amendment_id", "person_id"),
    description=(
        "Who tabled which amendment. This is a chosen tie rather than an "
        "assigned one, which makes it the constituent assembly's counterpart to "
        "the written-question co-signatures recorded for the 2023 chamber."
    ),
    columns=[
        Column("amendment_id", "string", "Amendment.", required=True,
               references="amendments.amendment_id"),
        Column("person_id", "string", "Sponsor.", required=True,
               references="persons.person_id"),
        Column("assembly_id", "string", "Chamber.", required=True,
               references="assemblies.assembly_id"),
        Column("source_ids", "string", "Provenance.", references="sources.source_id"),
    ],
)


TABLES: tuple[Table, ...] = (
    ASSEMBLIES,
    GOVERNORATES,
    CONSTITUENCIES,
    PARTIES,
    PERSONS,
    MANDATES,
    PARTY_AFFILIATIONS,
    BLOCS,
    BLOC_MEMBERSHIPS,
    COMMITTEES,
    COMMITTEE_MEMBERSHIPS,
    OFFICES,
    CAREERS,
    PARTICIPATION,
    VOTES,
    VOTE_POSITIONS,
    PARTY_SWITCHES,
    AMENDMENTS,
    AMENDMENT_SPONSORSHIPS,
    PERSON_XREF,
    SOURCES,
    PROVENANCE,
)

BY_NAME = {t.name: t for t in TABLES}


def table(name: str) -> Table:
    return BY_NAME[name]
