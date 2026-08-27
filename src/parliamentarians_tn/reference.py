"""Hand-curated reference data: the institutional frame, geography and parties.

Unlike the collectors, nothing here is scraped. These are the facts that make
the scraped person-level data interpretable as a time series, and they are
curated from constitutional texts, electoral laws and the historiography rather
than from any single website. Keeping them in code rather than in a loose CSV
means every value carries a comment where it is contested, and the whole frame
is reviewable in a diff.

Verification status is stated honestly per row. Seat counts for 1959-2009 were
checked against the party-level results reported for each election; note that
the 1964 and 1969 chambers had 101 seats, not the 90 frequently repeated from
the 1959 figure. Dates for the Chamber of Advisors could not be verified and are
left empty rather than guessed — an empty date in this dataset means "not
established", never "unknown but probably around then".

Run ``python -m parliamentarians_tn.reference`` to (re)write data/reference/.
"""

from __future__ import annotations

from .io import REFERENCE, log, write_table
from .schema import ASSEMBLIES, GOVERNORATES, PARTIES

# ---------------------------------------------------------------------------
# Assemblies: the institutional frame, 1956 to the present
# ---------------------------------------------------------------------------
#
# `end_date` is the last day the chamber actually functioned; `nominal_end_date`
# is the expiry provided in law where the two differ. The 2019 ARP is the case
# that makes this distinction necessary and is precisely the object of study for
# work on democratic breakdown, so both are recorded.
#
# For chambers before 2011, `start_date` holds the election date: the first
# sitting has not been verified against the Journal Officiel, and the notes say
# so on every affected row.

_UNVERIFIED_SITTING = (
    "start_date is the election date; the first-sitting date has not been "
    "verified against the Journal Officiel de la République Tunisienne."
)

ASSEMBLY_ROWS: list[dict[str, object]] = [
    {
        "assembly_id": "ANC-1956",
        "name_ar": "المجلس القومي التأسيسي",
        "name_fr": "Assemblée nationale constituante",
        "name_en": "National Constituent Assembly",
        "type": "constituent",
        "ordinal": 1,
        "start_date": "1956-04-08",
        "end_date": "1959-06-01",
        "nominal_end_date": "",
        "seats_nominal": 98,
        "seats_filled": 98,
        "seats_women": 0,
        "electoral_system": "Closed-list plurality (bloc vote) in multi-member constituencies; the Front National list won all seats",
        "suffrage": "Men only; women were enfranchised in 1957 and first voted in the 1959 elections",
        "regime_period": "protectorate_transition",
        "termination_mode": "Superseded: dissolved on promulgation of the Constitution of 1 June 1959",
        "speaker_person_id": "",
        "legal_basis": "Beylical decree of 1955 convening a constituent assembly",
        "coverage_status": "full",
        "notes": (
            "Elected 25 March 1956, five days after independence; opened 8 April 1956. "
            "Voted to abolish the monarchy and proclaim the Republic on 25 July 1957. "
            "Ten seats were refilled at a by-election on 26 August 1956 after six "
            "members were appointed governors, one a délégué, and two died. "
            "seats_women is 0 because women were not enfranchised until 1957 and "
            "first stood in 1959; this follows from the franchise rather than from a "
            "counted roster. "
            "Full roster available but from a tertiary source; see docs/SOURCES.md."
        ),
    },
    {
        "assembly_id": "NA-1959",
        "name_ar": "مجلس الأمة",
        "name_fr": "Assemblée nationale",
        "name_en": "National Assembly",
        "type": "ordinary_lower",
        "ordinal": 2,
        "start_date": "1959-11-08",
        "end_date": "1964-11-08",
        "nominal_end_date": "",
        "seats_nominal": 90,
        "seats_filled": 90,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); Neo-Destour won all 90 seats",
        "suffrage": "Universal adult suffrage; women voting in a legislative election for the first time",
        "regime_period": "bourguiba",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1 June 1959",
        "coverage_status": "frame_only",
        "notes": f"First legislature under the 1959 Constitution. {_UNVERIFIED_SITTING}",
    },
    {
        "assembly_id": "NA-1964",
        "name_ar": "مجلس الأمة",
        "name_fr": "Assemblée nationale",
        "name_en": "National Assembly",
        "type": "ordinary_lower",
        "ordinal": 3,
        "start_date": "1964-11-08",
        "end_date": "1969-11-02",
        "nominal_end_date": "",
        "seats_nominal": 101,
        "seats_filled": 101,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); the Socialist Destourian Party won all 101 seats",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": (
            "The Neo-Destour renamed itself the Parti socialiste destourien at its 1964 "
            "Bizerte congress. Seat count verified as 101; the figure of 90 often "
            f"reported for this chamber is carried over from 1959. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "NA-1969",
        "name_ar": "مجلس الأمة",
        "name_fr": "Assemblée nationale",
        "name_en": "National Assembly",
        "type": "ordinary_lower",
        "ordinal": 4,
        "start_date": "1969-11-02",
        "end_date": "1974-11-03",
        "nominal_end_date": "",
        "seats_nominal": 101,
        "seats_filled": 101,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); single-party return",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": _UNVERIFIED_SITTING,
    },
    {
        "assembly_id": "NA-1974",
        "name_ar": "مجلس الأمة",
        "name_fr": "Assemblée nationale",
        "name_en": "National Assembly",
        "type": "ordinary_lower",
        "ordinal": 5,
        "start_date": "1974-11-03",
        "end_date": "1979-11-04",
        "nominal_end_date": "",
        "seats_nominal": 112,
        "seats_filled": 112,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); single-party return",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959; Bourguiba proclaimed President for life in 1975",
        "coverage_status": "frame_only",
        "notes": _UNVERIFIED_SITTING,
    },
    {
        "assembly_id": "NA-1979",
        "name_ar": "مجلس الأمة",
        "name_fr": "Assemblée nationale",
        "name_en": "National Assembly",
        "type": "ordinary_lower",
        "ordinal": 6,
        "start_date": "1979-11-04",
        "end_date": "1981-11-01",
        "nominal_end_date": "1984-11-04",
        "seats_nominal": 121,
        "seats_filled": 121,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); single-party return",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Early renewal: elections held in 1981, three years into the term",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": (
            "Cut short by the early election of 1 November 1981, the first contested "
            f"by legalised opposition parties. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-1981",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 7,
        "start_date": "1981-11-01",
        "end_date": "1986-11-02",
        "nominal_end_date": "",
        "seats_nominal": 136,
        "seats_filled": 136,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); the PSD-led National Front took all 136 seats",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": (
            "The chamber was renamed Chamber of Deputies (مجلس النواب) in 1981, "
            f"replacing National Assembly (مجلس الأمة). {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-1986",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 8,
        "start_date": "1986-11-02",
        "end_date": "1989-04-02",
        "nominal_end_date": "1991-11-02",
        "seats_nominal": 125,
        "seats_filled": 125,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); opposition boycott left all 125 seats to the PSD",
        "suffrage": "Universal adult suffrage",
        "regime_period": "bourguiba",
        "termination_mode": "Early renewal after the change of regime of 7 November 1987",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": (
            "Sat across the removal of Bourguiba by Ben Ali on 7 November 1987, so this "
            "chamber-term spans two regime periods; regime_period records its period of "
            f"election. Cut short by the early election of 2 April 1989. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-1989",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 9,
        "start_date": "1989-04-02",
        "end_date": "1994-03-20",
        "nominal_end_date": "",
        "seats_nominal": 141,
        "seats_filled": 141,
        "seats_women": "",
        "electoral_system": "Closed-list plurality (bloc vote); the RCD took all 141 seats",
        "suffrage": "Universal adult suffrage",
        "regime_period": "ben_ali",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": (
            "First election under Ben Ali; the PSD had been renamed Rassemblement "
            "constitutionnel démocratique (RCD) in 1988. Independent lists associated "
            f"with the Islamist tendency polled strongly but won no seats. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-1994",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 10,
        "start_date": "1994-03-20",
        "end_date": "1999-10-24",
        "nominal_end_date": "",
        "seats_nominal": 163,
        "seats_filled": 163,
        "seats_women": "",
        "electoral_system": "144 seats by bloc vote plus 19 seats distributed nationally to losing opposition lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "ben_ali",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959; 1993 amendment of the electoral code",
        "coverage_status": "frame_only",
        "notes": (
            "The compensatory mechanism introduced here admitted opposition deputies to "
            "the chamber for the first time (19 of 163 seats). It is the institutional "
            "origin of the 'tolerated opposition' that the literature treats as "
            f"authoritarian power-sharing. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-1999",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 11,
        "start_date": "1999-10-24",
        "end_date": "2004-10-24",
        "nominal_end_date": "",
        "seats_nominal": 182,
        "seats_filled": 182,
        "seats_women": "",
        "electoral_system": "148 seats by bloc vote plus 34 compensatory seats for opposition lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "ben_ali",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959",
        "coverage_status": "frame_only",
        "notes": _UNVERIFIED_SITTING,
    },
    {
        "assembly_id": "COD-2004",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 12,
        "start_date": "2004-10-24",
        "end_date": "2009-10-25",
        "nominal_end_date": "",
        "seats_nominal": 189,
        "seats_filled": 189,
        "seats_women": "",
        "electoral_system": "152 seats by bloc vote plus 37 compensatory seats for opposition lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "ben_ali",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959 as amended in 2002",
        "coverage_status": "frame_only",
        "notes": (
            "First lower chamber to sit alongside the Chamber of Advisors, created by the "
            f"constitutional amendment approved in the referendum of 26 May 2002. {_UNVERIFIED_SITTING}"
        ),
    },
    {
        "assembly_id": "COD-2009",
        "name_ar": "مجلس النواب",
        "name_fr": "Chambre des députés",
        "name_en": "Chamber of Deputies",
        "type": "ordinary_lower",
        "ordinal": 13,
        "start_date": "2009-10-25",
        "end_date": "2011-03-23",
        "nominal_end_date": "2014-10-25",
        "seats_nominal": 214,
        "seats_filled": 214,
        "seats_women": "",
        "electoral_system": "161 seats by bloc vote plus 53 compensatory seats for opposition lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "ben_ali",
        "termination_mode": "Dissolved after the revolution of 14 January 2011",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 1959 as amended",
        "coverage_status": "frame_only",
        "notes": (
            "The last chamber of the Ben Ali period. It ceased to function after Ben Ali "
            "left the country on 14 January 2011 and was dissolved in the course of the "
            "March 2011 decree-laws that suspended the 1959 Constitution. The precise "
            "dissolution instrument and date require verification against the JORT; "
            "2011-03-23 is recorded provisionally."
        ),
    },
    {
        "assembly_id": "ADV-2005",
        "name_ar": "مجلس المستشارين",
        "name_fr": "Chambre des conseillers",
        "name_en": "Chamber of Advisors",
        "type": "ordinary_upper",
        "ordinal": "",
        "start_date": "",
        "end_date": "2011-03-23",
        "nominal_end_date": "",
        "seats_nominal": 112,
        "seats_filled": "",
        "seats_women": "",
        "electoral_system": "Mixed: two-thirds elected indirectly by local councillors and professional bodies, one-third appointed by the President",
        "suffrage": "Indirect; no direct popular vote",
        "regime_period": "ben_ali",
        "termination_mode": "Dissolved after the revolution of 14 January 2011",
        "speaker_person_id": "",
        "legal_basis": "Constitutional amendment approved by referendum on 26 May 2002",
        "coverage_status": "frame_only",
        "notes": (
            "Tunisia's only upper house before 2023. Sat 2005-2011 in parallel with the "
            "Chamber of Deputies. start_date is left EMPTY because the date of its first "
            "sitting could not be verified; it is not unknown-but-approximately-2005, it "
            "is simply not established here. Membership was reported as 112 at creation "
            "and 126 after the 2008 partial renewal; both figures require verification. "
            "No person-level data is included for this chamber."
        ),
    },
    {
        "assembly_id": "NCA-2011",
        "name_ar": "المجلس الوطني التأسيسي",
        "name_fr": "Assemblée nationale constituante",
        "name_en": "National Constituent Assembly",
        "type": "constituent",
        "ordinal": 14,
        "start_date": "2011-11-22",
        "end_date": "2014-12-01",
        "nominal_end_date": "",
        "seats_nominal": 217,
        "seats_filled": 217,
        "seats_women": 65,
        "electoral_system": "Closed-list proportional representation with largest remainder (Hare quota) in 33 constituencies, six of them out-of-country; vertical parity required on lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "transition",
        "termination_mode": "Superseded: handed over to the ARP on 2 December 2014 after adopting the Constitution of 27 January 2014",
        "speaker_person_id": "",
        "legal_basis": "Decree-Law 2011-35 of 10 May 2011; Constituent Law 2011-6 of 16 December 2011",
        "coverage_status": "full",
        "notes": (
            "Elected 23 October 2011 in Tunisia's first free election. Ennahdha took 89 "
            "seats, CPR 29, Aridha Chaabia 26, Ettakatol 20. seats_women is the figure "
            "usually reported for the assembly as returned and should be recomputed from "
            "the mandates table for any published claim."
        ),
    },
    {
        "assembly_id": "ARP-2014",
        "name_ar": "مجلس نواب الشعب",
        "name_fr": "Assemblée des représentants du peuple",
        "name_en": "Assembly of the Representatives of the People",
        "type": "ordinary_lower",
        "ordinal": 15,
        "start_date": "2014-12-02",
        "end_date": "2019-10-05",
        "nominal_end_date": "",
        "seats_nominal": 217,
        "seats_filled": 217,
        "seats_women": "",
        "electoral_system": "Closed-list proportional representation with largest remainder in 33 constituencies, six out-of-country; vertical parity required",
        "suffrage": "Universal adult suffrage",
        "regime_period": "second_republic",
        "termination_mode": "Normal expiry",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 27 January 2014",
        "coverage_status": "full",
        "notes": (
            "Elected 26 October 2014: Nidaa Tounes 86 seats, Ennahdha 69. Dates follow "
            "the chamber's own mandate record; its successor first sat on 13 November 2019. "
            "Recovered from Internet Archive captures of Al Bawsala's 2014 observatory "
            "(majles.marsad.tn/2014), which the live site no longer serves. Because ~29 "
            "monthly captures survive, this is the ONE chamber for which bloc switching "
            "is directly observable: 108 of 246 members changed bloc during the term, "
            "tracking the split of Nidaa Tounes and the formation of Machrouu Tounes."
        ),
    },
    {
        "assembly_id": "ARP-2019",
        "name_ar": "مجلس نواب الشعب",
        "name_fr": "Assemblée des représentants du peuple",
        "name_en": "Assembly of the Representatives of the People",
        "type": "ordinary_lower",
        "ordinal": 16,
        "start_date": "2019-11-13",
        "end_date": "2021-07-25",
        "nominal_end_date": "2024-11-13",
        "seats_nominal": 217,
        "seats_filled": 217,
        "seats_women": "",
        "electoral_system": "Closed-list proportional representation with largest remainder in 33 constituencies, six out-of-country",
        "suffrage": "Universal adult suffrage",
        "regime_period": "second_republic",
        "termination_mode": "Frozen by Presidential Decree 2021-117 of 25 July 2021; formally dissolved on 30 March 2022",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 27 January 2014",
        "coverage_status": "full",
        "notes": (
            "The chamber whose suspension ended the Second Republic. end_date is the date "
            "its powers were frozen; nominal_end_date is the five-year expiry that never "
            "arrived; the formal dissolution followed on 30 March 2022. Analyses of "
            "democratic breakdown should use end_date, not nominal_end_date, as the point "
            "of institutional death."
        ),
    },
    {
        "assembly_id": "ARP-2023",
        "name_ar": "مجلس نواب الشعب",
        "name_fr": "Assemblée des représentants du peuple",
        "name_en": "Assembly of the Representatives of the People",
        "type": "ordinary_lower",
        "ordinal": 17,
        "start_date": "2023-03-13",
        "end_date": "",
        "nominal_end_date": "2027-03-12",
        "seats_nominal": 161,
        "seats_filled": "",
        "seats_women": "",
        "electoral_system": "Two-round majoritarian in 161 single-member constituencies; candidates stand as individuals, not on party lists",
        "suffrage": "Universal adult suffrage",
        "regime_period": "third_republic",
        "termination_mode": "",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 25 July 2022; Decree-Law 2022-55 amending the electoral law",
        "coverage_status": "full",
        "notes": (
            "Elected 17 December 2022 (first round) and 29 January 2023 (second round) on "
            "a turnout of about 11 per cent. The shift from closed-list PR to single-member "
            "districts with individual candidacies is the central institutional change of "
            "the Third Republic and breaks comparability of party-level measures with "
            "2011-2019: there are no party lists to code."
        ),
    },
    {
        "assembly_id": "CNRD-2023",
        "name_ar": "المجلس الوطني للجهات والأقاليم",
        "name_fr": "Conseil national des régions et des districts",
        "name_en": "National Council of Regions and Districts",
        "type": "regional",
        "ordinal": "",
        "start_date": "2024-04-19",
        "end_date": "",
        "nominal_end_date": "",
        "seats_nominal": 77,
        "seats_filled": "",
        "seats_women": "",
        "electoral_system": "Indirect: members drawn by lot from elected local and regional councils",
        "suffrage": "Indirect; no direct popular vote",
        "regime_period": "third_republic",
        "termination_mode": "",
        "speaker_person_id": "",
        "legal_basis": "Constitution of 25 July 2022 (in force from 25 July 2022)",
        "coverage_status": "frame_only",
        "notes": (
            "The second chamber of the Third Republic, restoring bicameralism after "
            "twelve years. Constituted following the local elections of December 2023; "
            "elected its presiding officers on 19 April 2024, which is recorded as "
            "start_date. Imed Derbali was elected president. No person-level data is "
            "included yet: the council does not publish a machine-readable roster and it "
            "is not covered by either Al Bawsala observatory."
        ),
    },
]


# ---------------------------------------------------------------------------
# Governorates
# ---------------------------------------------------------------------------
#
# `region` uses the seven statistical regions of the Institut National de la
# Statistique, which is the aggregation the literature on interior/coastal
# inequality uses. `littoral` marks governorates with a Mediterranean coastline
# — the operationalisation of the coastal/interior cleavage that structures
# Tunisian politics and, on the standard argument, the 2011 revolution.
#
# `created_year` is left empty throughout. Several governorates were created or
# split in the 1970s-2000s (Ariana and Ben Arous in 1983, Manouba in 2000), but
# the dates could not be verified here and a wrong value would silently corrupt
# any analysis of pre-reform constituencies.

_GOV = [
    # (id, ar, lat, fr, region, littoral)
    ("TN-11", "تونس", "Tunis", "Tunis", "Grand Tunis", True),
    ("TN-12", "أريانة", "Ariana", "Ariana", "Grand Tunis", True),
    ("TN-13", "بن عروس", "Ben Arous", "Ben Arous", "Grand Tunis", True),
    ("TN-14", "منوبة", "Manouba", "La Manouba", "Grand Tunis", False),
    ("TN-21", "نابل", "Nabeul", "Nabeul", "North East", True),
    ("TN-22", "زغوان", "Zaghouan", "Zaghouan", "North East", False),
    ("TN-23", "بنزرت", "Bizerte", "Bizerte", "North East", True),
    ("TN-31", "باجة", "Beja", "Béja", "North West", True),
    ("TN-32", "جندوبة", "Jendouba", "Jendouba", "North West", True),
    ("TN-33", "الكاف", "Kef", "Le Kef", "North West", False),
    ("TN-34", "سليانة", "Siliana", "Siliana", "North West", False),
    ("TN-41", "القيروان", "Kairouan", "Kairouan", "Centre West", False),
    ("TN-42", "القصرين", "Kasserine", "Kasserine", "Centre West", False),
    ("TN-43", "سيدي بوزيد", "Sidi Bouzid", "Sidi Bouzid", "Centre West", False),
    ("TN-51", "سوسة", "Sousse", "Sousse", "Centre East", True),
    ("TN-52", "المنستير", "Monastir", "Monastir", "Centre East", True),
    ("TN-53", "المهدية", "Mahdia", "Mahdia", "Centre East", True),
    ("TN-61", "صفاقس", "Sfax", "Sfax", "Centre East", True),
    ("TN-71", "قفصة", "Gafsa", "Gafsa", "South West", False),
    ("TN-72", "توزر", "Tozeur", "Tozeur", "South West", False),
    ("TN-73", "قبلي", "Kebili", "Kébili", "South West", False),
    ("TN-81", "قابس", "Gabes", "Gabès", "South East", True),
    ("TN-82", "مدنين", "Medenine", "Médenine", "South East", True),
    ("TN-83", "تطاوين", "Tataouine", "Tataouine", "South East", False),
    # Out-of-country seats have existed since 2011 and are grouped here so that
    # a diaspora mandate is not silently assigned to a domestic governorate.
    ("TN-99", "خارج تونس", "Abroad", "Étranger", "abroad", False),
]

GOVERNORATE_ROWS = [
    {
        "governorate_id": gid,
        "name_ar": ar,
        "name_lat": lat,
        "name_fr": fr,
        "iso_3166_2": gid if gid != "TN-99" else "",
        "region": region,
        "littoral": "true" if littoral else "false",
        "created_year": "",
    }
    for gid, ar, lat, fr, region, littoral in _GOV
]


# ---------------------------------------------------------------------------
# Parties
# ---------------------------------------------------------------------------
#
# A seed register, not an exhaustive one. build.py mints additional parties from
# whatever names the collectors encounter, with family "unknown"; the point of
# this table is to fix the identity and ideological family of the organisations
# that matter for the long run, and above all to record the
# Neo-Destour -> PSD -> RCD succession explicitly. Whether that lineage is one
# organisation or three is a substantive question, so the dataset gives the
# analyst the links and does not decide it.

_PARTIES = [
    # (id, ar, fr, en, abbrev, family, founded, dissolved, predecessor)
    ("PTY-NEODESTOUR", "الحزب الحر الدستوري الجديد", "Néo-Destour", "Neo-Destour Party",
     "Neo-Destour", "destourian", "1934-03-02", "1964-10-22", ""),
    ("PTY-PSD", "الحزب الاشتراكي الدستوري", "Parti socialiste destourien",
     "Socialist Destourian Party", "PSD", "destourian", "1964-10-22", "1988-02-27",
     "PTY-NEODESTOUR"),
    ("PTY-RCD", "التجمع الدستوري الديمقراطي", "Rassemblement constitutionnel démocratique",
     "Democratic Constitutional Rally", "RCD", "destourian", "1988-02-27", "2011-03-09",
     "PTY-PSD"),
    ("PTY-CPT", "الحزب الشيوعي التونسي", "Parti communiste tunisien",
     "Tunisian Communist Party", "PCT", "left", "1920-01-01", "1993-04-23", ""),
    ("PTY-ETTAJDID", "حركة التجديد", "Mouvement Ettajdid", "Ettajdid Movement",
     "Ettajdid", "left", "1993-04-23", "2012-04-01", "PTY-CPT"),
    ("PTY-MDS", "حركة الديمقراطيين الاشتراكيين", "Mouvement des démocrates socialistes",
     "Movement of Socialist Democrats", "MDS", "social_democratic", "1978-06-10", "", ""),
    ("PTY-PUP", "حزب الوحدة الشعبية", "Parti de l'unité populaire",
     "Popular Unity Party", "PUP", "left", "1981-01-01", "", ""),
    ("PTY-UDU", "الاتحاد الديمقراطي الوحدوي", "Union démocratique unioniste",
     "Unionist Democratic Union", "UDU", "arab_nationalist", "1988-01-01", "", ""),
    ("PTY-ENNAHDHA", "حركة النهضة", "Mouvement Ennahdha", "Ennahdha Movement",
     "Ennahdha", "islamist", "1981-06-06", "", ""),
    ("PTY-CPR", "المؤتمر من أجل الجمهورية", "Congrès pour la République",
     "Congress for the Republic", "CPR", "social_democratic", "2001-07-25", "", ""),
    ("PTY-ETTAKATOL", "التكتل الديمقراطي من أجل العمل والحريات",
     "Forum démocratique pour le travail et les libertés",
     "Democratic Forum for Labour and Liberties", "Ettakatol", "social_democratic",
     "1994-04-09", "", ""),
    ("PTY-ARIDHA", "العريضة الشعبية", "Pétition populaire", "Popular Petition",
     "Aridha Chaabia", "other", "2011-01-01", "", ""),
    ("PTY-NIDAA", "نداء تونس", "Nidaa Tounes", "Nidaa Tounes", "Nidaa",
     "national_conservative", "2012-06-16", "", ""),
    ("PTY-JOMHOURI", "الحزب الجمهوري", "Parti républicain", "Republican Party",
     "Al Joumhouri", "liberal", "2012-04-09", "", ""),
    ("PTY-MACHROU", "حركة مشروع تونس", "Machrouû Tounes", "Machrouu Tounes",
     "Machrouu", "social_democratic", "2016-03-20", "", "PTY-NIDAA"),
    ("PTY-TAHYA", "تحيا تونس", "Tahya Tounes", "Tahya Tounes", "Tahya",
     "liberal", "2019-01-27", "", ""),
    ("PTY-QALB", "قلب تونس", "Qalb Tounes", "Heart of Tunisia", "Qalb Tounes",
     "liberal", "2019-06-01", "", ""),
    ("PTY-PDL", "الحزب الدستوري الحر", "Parti destourien libre",
     "Free Destourian Party", "PDL", "destourian", "2013-01-01", "", ""),
    ("PTY-KARAMA", "ائتلاف الكرامة", "Coalition Al Karama", "Al Karama Coalition",
     "Al Karama", "islamist", "2019-01-01", "", ""),
    ("PTY-ECHAAB", "حركة الشعب", "Mouvement du peuple", "People's Movement",
     "Echaab", "arab_nationalist", "2011-01-01", "", ""),
    ("PTY-INDEPENDENT", "مستقل", "Indépendant", "Independent", "Ind.",
     "independent", "", "", ""),
]

PARTY_ROWS = [
    {
        "party_id": pid,
        "name_ar": ar,
        "name_fr": fr,
        "name_en": en,
        "abbrev": abbrev,
        "family": family,
        "founded_date": founded,
        "dissolved_date": dissolved,
        "predecessor_party_id": pred,
        "wikidata_qid": "",
        "notes": "",
    }
    for pid, ar, fr, en, abbrev, family, founded, dissolved, pred in _PARTIES
]


# ---------------------------------------------------------------------------
# Presiding officers of the pre-2011 chambers
# ---------------------------------------------------------------------------
#
# The only person-level data recoverable for 1959-2011 without archival work.
# Eight men presided over the chamber across fifty-two years, several of whom
# also served as prime minister or head of state — Fouad Mebazaa became interim
# President in January 2011 by virtue of holding this office. Tenures are given
# to the year only, which is what the source supports; date_precision is
# therefore "year" and the dates are written as 1 January / 31 December.
#
# These rows are loaded by build.py as persons with an `offices` spell, NOT as
# mandates: the specific legislature each served in is derivable from the
# assemblies table by date overlap, but the source does not state it.

PRESIDING_OFFICERS_PRE2011 = [
    # (name_ar, name_lat, start_year, end_year, note)
    ("الجلولي فارس", "Jallouli Fares", 1959, 1964,
     "Also presided over the 1956 Constituent Assembly from April 1956."),
    ("الصادق المقدم", "Sadok Mokaddem", 1964, 1981, "Previously foreign minister."),
    ("محمود المسعدي", "Mahmoud Messadi", 1981, 1987,
     "Writer and former education minister; architect of post-independence schooling."),
    ("رشيد صفر", "Rachid Sfar", 1987, 1988, "Prime minister 1986-1987."),
    ("صلاح الدين بالي", "Salah Eddine Baly", 1988, 1990, ""),
    ("الباجي قائد السبسي", "Beji Caid Essebsi", 1990, 1991,
     "Later prime minister in 2011 and President of the Republic 2014-2019."),
    ("الحبيب بولعراس", "Habib Boularès", 1991, 1997,
     "Writer and former minister; briefly prime minister in 1990."),
    ("فؤاد المبزع", "Fouad Mebazaa", 1997, 2011,
     "Became interim President of the Republic on 15 January 2011 under the "
     "constitutional provision vesting succession in the speaker."),
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def write_reference() -> None:
    write_table(ASSEMBLIES, ASSEMBLY_ROWS, REFERENCE)
    write_table(GOVERNORATES, GOVERNORATE_ROWS, REFERENCE)
    write_table(PARTIES, PARTY_ROWS, REFERENCE)
    log(f"reference frame: {len(ASSEMBLY_ROWS)} assemblies, "
        f"{len(GOVERNORATE_ROWS)} governorates, {len(PARTY_ROWS)} parties, "
        f"{len(PRESIDING_OFFICERS_PRE2011)} pre-2011 presiding officers")


if __name__ == "__main__":
    write_reference()
