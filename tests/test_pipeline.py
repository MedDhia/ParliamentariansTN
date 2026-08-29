"""Unit tests for the parts of the pipeline where a silent bug would be costly.

The emphasis is on the logic that is easy to get wrong and hard to notice:
Arabic name normalisation, biography parsing, temporal overlap in network
projection, and the guards that stopped real bugs during development. Each test
that corresponds to a bug found in the data names it.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from parliamentarians_tn import build as build_mod  # noqa: E402
from parliamentarians_tn import schema  # noqa: E402
from parliamentarians_tn.collect import (  # noqa: E402
    arp_odoo,
    chambre_conseillers,
    marsad_anc,
    marsad_arp2014,
    marsad_majles,
)
from parliamentarians_tn.ids import (  # noqa: E402
    IdRegistry,
    arabic_match_key,
    deterministic_id,
    latin_match_key,
    normalize_arabic,
    normalize_latin,
    romanize_arabic,
)
from parliamentarians_tn.networks import _overlaps, _project  # noqa: E402


# ---------------------------------------------------------------------------
# Arabic normalisation
# ---------------------------------------------------------------------------

class TestArabicNormalisation:
    def test_folds_alif_variants(self):
        assert normalize_arabic("أحمد") == normalize_arabic("احمد")
        assert normalize_arabic("إبراهيم") == normalize_arabic("ابراهيم")

    def test_drops_definite_article(self):
        # The ARP writes الحامدي, other sources write حامدي.
        assert normalize_arabic("الحامدي") == normalize_arabic("حامدي")

    def test_folds_ta_marbuta_and_alif_maqsura(self):
        assert normalize_arabic("فاطمة") == normalize_arabic("فاطمه")
        assert normalize_arabic("مصطفى") == normalize_arabic("مصطفي")

    def test_strips_diacritics(self):
        assert normalize_arabic("مُحَمَّد") == normalize_arabic("محمد")

    def test_match_key_is_word_order_invariant(self):
        # Sources disagree on family-name-first vs given-name-first.
        assert arabic_match_key("إبراهيم بودربالة") == arabic_match_key("بودربالة إبراهيم")

    def test_match_key_ignores_nasab_particles(self):
        assert arabic_match_key("محمد بن علي") == arabic_match_key("محمد علي")

    def test_empty_input_is_empty_not_error(self):
        assert normalize_arabic(None) == ""
        assert arabic_match_key("") == ""

    def test_distinct_names_do_not_collide(self):
        assert arabic_match_key("محمد الغنوشي") != arabic_match_key("راشد الغنوشي")


class TestLatinNormalisation:
    def test_folds_common_romanisation_variants(self):
        # Bouderbela / Buderbela: the ou/u alternation is the commonest split.
        assert normalize_latin("Bouderbela") == normalize_latin("Buderbela")

    def test_folds_accents_and_punctuation(self):
        assert normalize_latin("Béji Caïd-Essebsi") == normalize_latin("Beji Caid Essebsi")

    def test_match_key_is_word_order_invariant(self):
        assert latin_match_key("Brahim Bouderbela") == latin_match_key("Bouderbela Brahim")

    def test_distinct_names_do_not_collide(self):
        assert latin_match_key("Rached Ghannouchi") != latin_match_key("Mohamed Ghannouchi")


class TestRomanisation:
    def test_produces_latin_output(self):
        out = romanize_arabic("محمد")
        assert out and out.isascii()

    def test_empty_input(self):
        assert romanize_arabic("") == ""


# ---------------------------------------------------------------------------
# ID minting
# ---------------------------------------------------------------------------

class TestIdRegistry:
    def test_same_upstream_key_returns_same_id(self):
        reg = IdRegistry("TNP")
        first = reg.mint("ARP_ODOO", "742")
        assert reg.mint("ARP_ODOO", "742") == first

    def test_different_keys_get_different_ids(self):
        reg = IdRegistry("TNP")
        assert reg.mint("ARP_ODOO", "742") != reg.mint("ARP_ODOO", "743")

    def test_same_key_in_different_sources_is_distinct(self):
        reg = IdRegistry("TNP")
        assert reg.mint("ARP_ODOO", "1") != reg.mint("MARSAD_ANC", "1")

    def test_alias_maps_upstream_key_onto_existing_person(self):
        reg = IdRegistry("TNP")
        pid = reg.mint("MARSAD_ANC", "abc")
        reg.alias("MARSAD_MAJLES", "xyz", pid)
        assert reg.get("MARSAD_MAJLES", "xyz") == pid

    def test_counter_resumes_from_existing_ids(self):
        reg = IdRegistry("TNP", existing={"S::1": "TNP-00007"})
        assert reg.mint("S", "2") == "TNP-00008"

    def test_deterministic_id_is_stable_and_distinct(self):
        a = deterministic_id("CMT", "ARP-2019", "finance")
        assert a == deterministic_id("CMT", "ARP-2019", "finance")
        assert a != deterministic_id("CMT", "ARP-2023", "finance")


# ---------------------------------------------------------------------------
# Biography parsing (marsad ANC)
# ---------------------------------------------------------------------------

class TestBirthParsing:
    def test_full_date_with_place_and_governorate(self):
        out = marsad_anc.parse_birth(
            "Né le 02 Novembre 1975, à Sidi Khlif dans le gouvernorat de Sidi Bouzid, "
            "c'est là qu'il entame sa scolarité."
        )
        assert out["birth_date"] == "1975-11-02"
        assert out["birth_date_precision"] == "day"
        assert out["birth_place_ar"] == "Sidi Khlif"
        assert out["birth_governorate_name"] == "Sidi Bouzid"

    def test_footnote_glued_to_year_is_handled(self):
        # Regression: profiles pasted from Wikipedia read "né le 1er mai 19561".
        # The original pattern failed to match and fell through to an unrelated
        # later date, giving one member a birth year of 1998 and an apparent age
        # of 13 at election.
        out = marsad_anc.parse_birth(
            "Khemaïs Ksila, né le 1er mai 19561, est un homme politique tunisien. "
            "Il est emprisonné ... le 22 février 1998 ..."
        )
        assert out["birth_date"] == "1956-05-01"

    def test_year_only_gets_year_precision(self):
        out = marsad_anc.parse_birth("Né en 1965 à Kébili.")
        assert out["birth_date"] == "1965-01-01"
        assert out["birth_date_precision"] == "year"

    def test_implausible_year_is_rejected_not_published(self):
        assert marsad_anc.parse_birth("Né le 3 mars 2005 à Tunis.") == {}
        assert marsad_anc.parse_birth("Né en 1830 à Tunis.") == {}

    def test_no_birth_information(self):
        assert marsad_anc.parse_birth("Avocat au barreau de Tunis.") == {}


class TestGenderInference:
    def test_feminine_participle(self):
        assert marsad_anc.parse_gender("Née le 3 mars 1970 à Sfax.") == "female"

    def test_masculine_participle(self):
        assert marsad_anc.parse_gender("Né le 3 mars 1970 à Sfax.") == "male"

    def test_marital_participle_fallback(self):
        assert marsad_anc.parse_gender("Mariée et mère de deux enfants.") == "female"
        assert marsad_anc.parse_gender("Marié et père de deux enfants.") == "male"

    def test_pronoun_fallback(self):
        assert marsad_anc.parse_gender("Elle enseigne le droit. Elle milite.") == "female"

    def test_unknown_when_no_signal(self):
        assert marsad_anc.parse_gender("Avocat.") == "unknown"

    def test_never_infers_from_name_alone(self):
        # A bare name must not produce a sex: inference is from grammatical
        # agreement in the source's prose only.
        assert marsad_anc.parse_gender("Fatma Ben Ali") == "unknown"


class TestPersonalParsing:
    def test_marital_children_and_languages(self):
        out = marsad_anc.parse_personal(
            "Marié et père de deux enfants, il maîtrise la langue arabe et française."
        )
        assert out["marital_status"] == "marié"
        assert out["n_children"] == "2"
        assert "ar" in out["languages"] and "fr" in out["languages"]

    def test_no_personal_details(self):
        assert marsad_anc.parse_personal("Ingénieur agronome.") == {}


class TestCommitteeParsing:
    def test_parses_name_type_and_role_triples(self):
        markup = (
            "<div>لجنة الحقوق والحريات</div><div>لجنة تأسيسية</div>"
            "<div>المقرر المساعد الأول</div>"
        )
        rows = marsad_anc.parse_committees(markup)
        assert len(rows) == 1
        assert rows[0]["type"] == "constituent"
        assert rows[0]["role"] == "assistant_rapporteur"

    def test_legislative_and_special_types(self):
        markup = (
            "<div>لجنة المالية</div><div>لجنة تشريعية</div><div>عضو</div>"
            "<div>لجنة التوافقات</div><div>لجنة خاصة</div><div>رئيس</div>"
        )
        rows = marsad_anc.parse_committees(markup)
        assert [r["type"] for r in rows] == ["legislative", "special"]
        assert [r["role"] for r in rows] == ["member", "chair"]

    def test_empty_page_yields_nothing(self):
        assert marsad_anc.parse_committees("<div></div>") == []


# ---------------------------------------------------------------------------
# Arabic date parsing (marsad majles)
# ---------------------------------------------------------------------------

class TestArabicDates:
    @pytest.mark.parametrize("text,expected", [
        ("19 ديسمبر 2019", "2019-12-19"),
        ("1 جانفي 2020", "2020-01-01"),
        ("5 جويلية 2021", "2021-07-05"),
        ("3 أوت 2020", "2020-08-03"),
        ("7 فيفري 2020", "2020-02-07"),
    ])
    def test_tunisian_and_standard_month_names(self, text, expected):
        assert marsad_majles.parse_arabic_date(text) == expected

    def test_unparseable_returns_empty(self):
        assert marsad_majles.parse_arabic_date("اليوم") == ""
        assert marsad_majles.parse_arabic_date("") == ""


# ---------------------------------------------------------------------------
# ARP-2014 recovery from web captures
# ---------------------------------------------------------------------------

CARD = (
    '<a href="/2014/elus/Noureddine_Bhiri" class="depute"\n'
    '  data-nom="نور الدين البحيري"\n'
    '  data-bloc="حركة النهضة"\n'
    '  data-groupe_id="Mouvement_Ennahdha"\n'
    '  data-liste="حركة النهضة"\n'
    '  data-region="بن عروس"\n'
    '  data-sexe="رجال"\n'
    '  data-age="57"\n'
    '  data-profession="محامي"\n'
    '  data-siege="11">\n'
)


class TestArp2014Roster:
    def test_parses_card_attributes(self):
        rows = marsad_arp2014.parse_roster(CARD)
        assert list(rows) == ["Noureddine_Bhiri"]
        card = rows["Noureddine_Bhiri"]
        assert card["nom"] == "نور الدين البحيري"
        assert card["bloc"] == "حركة النهضة"
        assert card["region"] == "بن عروس"
        assert card["sexe"] == "رجال"
        assert card["siege"] == "11"

    def test_slug_is_a_source_supplied_romanisation(self):
        assert marsad_arp2014._slug_to_latin("Noureddine_Bhiri") == "Noureddine Bhiri"
        assert marsad_arp2014._slug_to_latin("Imed_Ouled_Jebril") == "Imed Ouled Jebril"

    def test_empty_markup_yields_nothing(self):
        assert marsad_arp2014.parse_roster("<html></html>") == {}


class TestArp2014BlocSpells:
    def _obs(self, *pairs):
        """(date, bloc) -> observation list for a single member."""
        return [
            (date, {"X": {"bloc": bloc, "groupe_id": bloc}})
            for date, bloc in pairs
        ]

    def test_stable_membership_is_one_spell_from_first_sitting(self):
        spells = marsad_arp2014.build_bloc_spells(
            self._obs(("2015-01-12", "A"), ("2016-01-08", "A"))
        )["X"]
        assert len(spells) == 1
        assert spells[0]["start_date"] == marsad_arp2014.FIRST_SITTING
        assert spells[0]["end_date"] == marsad_arp2014.TERM_END
        # never observed changing, so its dates are not bracketed
        assert spells[0]["dates_bracketed"] is False

    def test_a_change_closes_one_spell_and_opens_another(self):
        spells = marsad_arp2014.build_bloc_spells(
            self._obs(("2015-01-12", "A"), ("2016-01-08", "A"), ("2016-02-08", "B"))
        )["X"]
        assert [s["name_ar"] for s in spells] == ["A", "B"]
        # The spells tile without a gap: the outgoing one is closed where the
        # incoming one starts. Ending it at the last observation instead would
        # leave the member in no bloc for the length of the capture gap, which is
        # a false claim rather than a cautious one — with real captures nine
        # months wide it removed a quarter of the chamber from the panel.
        assert spells[0]["end_date"] == "2016-02-08"
        assert spells[1]["start_date"] == "2016-02-08"
        # The genuine uncertainty — the change happened somewhere in the interval
        # between the two observations — is carried by the bracketing fields.
        assert spells[0]["end_date_earliest"] == "2016-01-08"
        assert spells[1]["start_date_earliest"] == "2016-01-08"
        assert spells[0]["dates_bracketed"] is True
        assert spells[1]["dates_bracketed"] is True

    def test_spells_tile_without_gaps(self):
        """No month may fall between one spell ending and the next beginning."""
        spells = marsad_arp2014.build_bloc_spells(
            self._obs(("2015-01-12", "A"), ("2017-12-30", "A"), ("2018-10-12", "B"))
        )["X"]
        assert spells[0]["end_date"] == spells[1]["start_date"]

    def test_a_replacement_is_not_dated_to_the_first_sitting(self):
        """A member first seen mid-term joined mid-term.

        Dating their opening spell to the chamber's first sitting would credit
        them with years they did not serve, and would push the reconstructed
        chamber above its seat count in the opening month.
        """
        obs = [
            ("2015-01-12", {"A": {"bloc": "P", "groupe_id": "P"}}),
            ("2017-05-04", {"A": {"bloc": "P", "groupe_id": "P"},
                            "B": {"bloc": "P", "groupe_id": "P"}}),
        ]
        spells = marsad_arp2014.build_bloc_spells(obs)
        assert spells["A"][0]["start_date"] == marsad_arp2014.FIRST_SITTING
        assert spells["A"][0]["dates_bracketed"] is False
        assert spells["B"][0]["start_date"] == "2017-05-04"
        assert spells["B"][0]["dates_bracketed"] is True

    def test_a_member_who_stops_appearing_is_not_kept_to_the_end_of_term(self):
        obs = [
            ("2015-01-12", {"A": {"bloc": "P", "groupe_id": "P"},
                            "B": {"bloc": "P", "groupe_id": "P"}}),
            ("2017-05-04", {"A": {"bloc": "P", "groupe_id": "P"}}),
        ]
        spells = marsad_arp2014.build_bloc_spells(obs)
        assert spells["A"][-1]["end_date"] == marsad_arp2014.TERM_END
        assert spells["B"][-1]["end_date"] == "2015-01-12"

    def test_returning_to_a_previous_bloc_is_a_third_spell(self):
        spells = marsad_arp2014.build_bloc_spells(
            self._obs(("2015-01-12", "A"), ("2016-02-08", "B"), ("2017-05-04", "A"))
        )["X"]
        assert [s["name_ar"] for s in spells] == ["A", "B", "A"]

    def test_final_spell_is_closed_at_end_of_term(self):
        spells = marsad_arp2014.build_bloc_spells(
            self._obs(("2015-01-12", "A"), ("2016-02-08", "B"))
        )["X"]
        assert spells[-1]["end_date"] == marsad_arp2014.TERM_END

    def test_member_absent_from_early_captures_still_gets_a_spell(self):
        obs = [
            ("2015-01-12", {"A": {"bloc": "P", "groupe_id": "P"}}),
            ("2016-01-08", {"A": {"bloc": "P", "groupe_id": "P"},
                            "B": {"bloc": "Q", "groupe_id": "Q"}}),
        ]
        spells = marsad_arp2014.build_bloc_spells(obs)
        assert "B" in spells and len(spells["B"]) == 1

    def test_missing_bloc_attribute_is_skipped_not_recorded_as_blank(self):
        obs = [("2015-01-12", {"X": {"bloc": "", "groupe_id": ""}})]
        assert marsad_arp2014.build_bloc_spells(obs).get("X", []) == []


# ---------------------------------------------------------------------------
# Network projection
# ---------------------------------------------------------------------------

class TestOverlap:
    def test_disjoint_spells_do_not_overlap(self):
        ok, _, _ = _overlaps("2019-01-01", "2020-01-01", "2020-06-01", "2021-01-01")
        assert not ok

    def test_intersecting_spells_overlap(self):
        ok, start, _ = _overlaps("2019-01-01", "2021-01-01", "2020-01-01", "2022-01-01")
        assert ok and start == "2020-01-01"

    def test_open_ended_spells_overlap(self):
        ok, _, _ = _overlaps("2019-01-01", "", "2023-01-01", "")
        assert ok


class TestProjection:
    def _rows(self):
        return [
            {"person_id": "P1", "assembly_id": "A", "g": "G1",
             "start_date": "2020-01-01", "end_date": ""},
            {"person_id": "P2", "assembly_id": "A", "g": "G1",
             "start_date": "2020-01-01", "end_date": ""},
            {"person_id": "P3", "assembly_id": "A", "g": "G1",
             "start_date": "2019-01-01", "end_date": "2019-06-01"},
            # same group name, different chamber
            {"person_id": "P4", "assembly_id": "B", "g": "G1",
             "start_date": "2020-01-01", "end_date": ""},
        ]

    def test_edges_never_cross_assemblies(self):
        edges = _project("test", self._rows(), "g", {})
        pairs = {(e["source"], e["target"]) for e in edges}
        assert ("P1", "P4") not in pairs
        assert ("P2", "P4") not in pairs

    def test_non_overlapping_spells_produce_no_edge(self):
        edges = _project("test", self._rows(), "g", {})
        pairs = {(e["source"], e["target"]) for e in edges}
        assert ("P1", "P3") not in pairs
        assert ("P1", "P2") in pairs

    def test_newman_weight_discounts_large_groups(self):
        small = [
            {"person_id": f"S{i}", "assembly_id": "A", "g": "G",
             "start_date": "2020-01-01", "end_date": ""} for i in range(2)
        ]
        big = [
            {"person_id": f"B{i}", "assembly_id": "A", "g": "G",
             "start_date": "2020-01-01", "end_date": ""} for i in range(11)
        ]
        s_edge = _project("t", small, "g", {})[0]
        b_edge = _project("t", big, "g", {})[0]
        assert s_edge["weight_newman"] == pytest.approx(1.0)
        assert b_edge["weight_newman"] == pytest.approx(0.1)
        assert s_edge["weight"] == b_edge["weight"] == 1

    def test_shared_groups_accumulate_weight(self):
        rows = []
        for g in ("G1", "G2", "G3"):
            for p in ("P1", "P2"):
                rows.append({"person_id": p, "assembly_id": "A", "g": g,
                             "start_date": "2020-01-01", "end_date": ""})
        edges = _project("t", rows, "g", {})
        assert len(edges) == 1
        assert edges[0]["weight"] == 3
        assert edges[0]["shared_count"] == 3

    def test_singleton_group_produces_no_edge(self):
        rows = [{"person_id": "P1", "assembly_id": "A", "g": "G",
                 "start_date": "", "end_date": ""}]
        assert _project("t", rows, "g", {}) == []

    def test_missing_dates_are_flagged_assumed(self):
        rows = [
            {"person_id": "P1", "assembly_id": "A", "g": "G", "start_date": "", "end_date": ""},
            {"person_id": "P2", "assembly_id": "A", "g": "G", "start_date": "", "end_date": ""},
        ]
        assert _project("t", rows, "g", {})[0]["dates_assumed"] == "true"


# ---------------------------------------------------------------------------
# Schema integrity
# ---------------------------------------------------------------------------

class TestSchema:
    def test_table_names_unique(self):
        names = [t.name for t in schema.TABLES]
        assert len(names) == len(set(names))

    def test_column_names_unique_within_table(self):
        for tbl in schema.TABLES:
            assert len(tbl.column_names) == len(set(tbl.column_names)), tbl.name

    def test_primary_keys_exist_as_columns(self):
        for tbl in schema.TABLES:
            for key in tbl.primary_key:
                assert key in tbl.column_names, f"{tbl.name}.{key}"

    def test_references_point_at_real_tables_and_columns(self):
        for tbl in schema.TABLES:
            for col in tbl.columns:
                if not col.references:
                    continue
                target_table, target_col = col.references.split(".")
                assert target_table in schema.BY_NAME, col.references
                assert target_col in schema.BY_NAME[target_table].column_names, col.references

    def test_enum_columns_declare_a_vocabulary(self):
        for tbl in schema.TABLES:
            for col in tbl.columns:
                if col.dtype == "enum":
                    assert col.enum, f"{tbl.name}.{col.name} is enum with no vocabulary"

    def test_every_column_documented(self):
        for tbl in schema.TABLES:
            for col in tbl.columns:
                assert col.description.strip(), f"{tbl.name}.{col.name}"


class TestMarsadActivityParsing:
    """The NCA activity pages that an earlier version of the collector missed.

    The member's position on a division is carried in a CSS class, not in text,
    so a text-node walk silently returns nothing — which is exactly how 374,000
    recorded positions went unnoticed. These tests pin the markup contract.
    """

    VOTE_HTML = """
    <div class="vote-day"><div class="vote-date float">25 sept. 2014</div>
    <a href="/fr/vote/542d274612bdaa35e4bc6f9e" class="vote-article">
    <span class="float right-10 voted-absent"></span>
    Vote sur le projet de loi N&#176;64/2014</a>
    <div class="vote-day"><div class="vote-date float">3 janv. 2013</div>
    <a href="/fr/vote/542d242f12bdaa35e4bc6f9d" class="vote-article">
    <span class="float right-10 voted-pour"></span>
    Vote sur l'article 5</a>
    """

    def test_position_comes_from_the_css_class(self):
        rows = marsad_anc.parse_votes(self.VOTE_HTML)
        assert [r["position"] for r in rows] == ["absent", "pour"]

    def test_division_identity_and_dates(self):
        rows = marsad_anc.parse_votes(self.VOTE_HTML)
        assert rows[0]["vote_source_key"] == "542d274612bdaa35e4bc6f9e"
        assert rows[0]["date"] == "2014-09-25"
        assert rows[1]["date"] == "2013-01-03"
        assert "N°64/2014" in rows[0]["title"]

    def test_abbreviated_french_months(self):
        assert marsad_anc.parse_french_date("25 sept. 2014") == "2014-09-25"
        assert marsad_anc.parse_french_date("1 août 2013") == "2013-08-01"
        assert marsad_anc.parse_french_date("not a date") == ""

    AMENDMENT_HTML = """
    <p class="grey">Amendement sur <a href="/fr/constitution/3/article/0">Préambule</a>
    Soumis par <a href="#" class="show-deps" data-id="52c6a05412bdaa7f9b90f3c7">2 élus</a></p>
    <p id="52c6a05412bdaa7f9b90f3c7" class="deps small grey">
    <a href="/fr/deputes/4f4fbcf3bd8cb561570000ba">Mourad Amdouni</a>,
    <a href="/fr/deputes/4f4fbcf3bd8cb56157000001">Ibrahim Hamdi</a></p>
    <p style="text-align: justify;">Ajout de la lutte contre le colonialisme.</p>
    """

    def test_amendment_sponsors_and_text(self):
        rows = marsad_anc.parse_amendments(self.AMENDMENT_HTML)
        assert len(rows) == 1
        assert rows[0]["sponsor_source_keys"] == [
            "4f4fbcf3bd8cb561570000ba", "4f4fbcf3bd8cb56157000001"]
        assert rows[0]["target_label"] == "Préambule"
        # The wording, not the sponsor list that precedes it — the bug this
        # test exists for.
        assert rows[0]["text"] == "Ajout de la lutte contre le colonialisme."
        assert "Mourad" not in rows[0]["text"]

    MERCATO_HTML = """
    <script>var deps = {"a": "A"}, click = false,
    mercato_map = {"Ennahdha": {"then": 89, "now": 89, "partis": {}},
    "CPR": {"then": 29, "now": 0, "partis": {"CPR": ["x1"], "Wafa": ["x2", "x3"]}}};
    </script>
    """

    def test_mercato_yields_from_to_pairs(self):
        moves = marsad_anc.parse_mercato(self.MERCATO_HTML)
        assert {(m["deputy_source_key"], m["party_to"]) for m in moves} == {
            ("x1", "CPR"), ("x2", "Wafa"), ("x3", "Wafa")}
        # A member listed under their own party of election did not move; the
        # builder drops those rather than recording a switch to nowhere.
        assert [m for m in moves if m["party_from"] == m["party_to"]]

    def test_empty_activity_pages_are_recognised(self):
        assert marsad_anc._is_empty_page("<p>Aucune question pour le moment</p>")
        assert marsad_anc._is_empty_page("<p>Aucune publication pour l'instant</p>")
        assert not marsad_anc._is_empty_page(self.AMENDMENT_HTML)

    def test_position_codes_round_trip(self):
        from parliamentarians_tn.build import MARSAD_VOTE_CODES
        for position, code in marsad_anc.POSITION_CODES.items():
            assert MARSAD_VOTE_CODES[code] == position
        # "-" must never decode to a position: it means the division was not on
        # that member's page, which is not the same as being absent from it.
        assert "-" not in MARSAD_VOTE_CODES


class TestMajlesMemberStatistics:
    """ARP-2019 attendance, which the collector previously read only as a rate.

    The member page is the only place the *denominators* appear — how many
    sittings there were to attend. Without them the rates cannot be checked,
    which is why the dataset carried an attendance rate and an empty
    plenary_denominator for every member of this chamber.
    """

    HTML = """
    <a title="Présence en plénières : 87 / 112"><svg></svg></a>
    <a title="Présence en commissions permanentes : 37 / 80"><svg></svg></a>
    <a title="Participation aux votes : 121 / 335"><svg></svg></a>
    <span title="Absence justifiée : 6 / 25">Absence justifiée <b class="ml-1">5.36%</b></span>
    <span>Discipline de vote <b class="ml-1">28.06%</b></span>
    """

    def test_rates_are_recomputed_from_counts(self):
        stats = marsad_majles.parse_member_statistics(self.HTML)
        assert stats["plenary_attendance_rate"] == "0.7768"
        assert stats["plenary_denominator"] == "112"
        assert stats["vote_participation_rate"] == "0.3612"
        assert stats["vote_denominator"] == "335"
        assert stats["committee_attendance_rate"] == "0.4625"

    def test_discipline_is_stored_as_a_proportion(self):
        stats = marsad_majles.parse_member_statistics(self.HTML)
        assert stats["vote_discipline_rate"] == "0.2806"

    def test_unrecognised_measures_are_ignored(self):
        # "Absence justifiée" also matches the title pattern but is not one of
        # the measures the participation table holds; it must not leak in.
        stats = marsad_majles.parse_member_statistics(self.HTML)
        assert not any("justif" in k for k in stats)

    def test_zero_denominator_does_not_divide(self):
        assert marsad_majles.parse_member_statistics(
            '<a title="Participation aux votes : 0 / 0"></a>') == {}


class TestVoteAgreementLayer:
    """The derived vote-agreement dyads, which behave unlike every other layer.

    Checked against the committed file rather than by re-deriving: the point is
    that what ships obeys the contract the network guide states.
    """

    @staticmethod
    def _rows():
        path = ROOT / "data" / "networks" / "edges_vote_agreement.csv"
        if not path.exists():
            pytest.skip("run `make networks` first")
        with path.open(encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_weight_is_a_rate_not_a_count(self):
        # Every other layer's weight counts events. This one is a proportion,
        # and weight_newman is empty because there is no group size to correct.
        for row in self._rows():
            assert 0.0 <= float(row["weight"]) <= 1.0
            assert row["weight_newman"] == ""

    def test_pairs_are_ordered_and_unique(self):
        seen = set()
        for row in self._rows():
            assert row["source"] < row["target"], "dyads must be canonically ordered"
            key = (row["source"], row["target"])
            assert key not in seen, f"duplicate dyad {key}"
            seen.add(key)

    def test_thinly_scored_pairs_are_dropped_not_scored(self):
        # A pair scored on five divisions would take values on a coarse grid and
        # read as signal. The builder drops them; nothing below the floor ships.
        assert all(int(r["shared_count"]) >= 30 for r in self._rows())

    def test_layer_and_assembly_are_consistent(self):
        rows = self._rows()
        assert {r["layer"] for r in rows} == {"vote_agreement"}
        # Only one chamber has a roll-call record, so only one can appear here.
        assert {r["assembly_id"] for r in rows} == {"NCA-2011"}


class TestOdooRoleMapping:
    """arp.tn role titles, which all contain the word "president".

    Both maps are matched longest-key-first, and these are the strings the
    source actually uses — taken from the cached `arp.mandat.fonction` and
    `arp.deputegroupe` responses, not invented. Two bugs lived here: the
    assessors fell through to the four-character key and were coded `speaker`
    in a chamber with one, and bloc roles were mapped with the *chamber's*
    vocabulary, making every bloc chair a `speaker`.
    """

    ASSESSORS = [
        "نائب مساعد للرئيس مكلّف بشؤون التشريع",
        "نائب مساعد للرئيس مكلّف بالتصرف العام",
        "نائب مساعد للرئيس مُكلّف بالعلاقة مع المجلس الوطني للجهات والأقاليم",
    ]

    def _office(self, label):
        return arp_odoo._map_role(label, arp_odoo.OFFICE_MAP, default="unknown")

    def _bloc(self, label):
        return arp_odoo._map_role(label, arp_odoo.BLOC_ROLE_MAP, default="unknown")

    def test_assessors_are_bureau_members_not_speakers(self):
        for label in self.ASSESSORS:
            assert self._office(label) == "bureau_member", label

    def test_the_chamber_has_exactly_one_speaker_title(self):
        assert self._office("رئيس مجلس نواب الشعب") == "speaker"
        assert self._office("نائب رئيس مجلس نواب الشعب") == "vice_speaker"

    def test_a_bloc_head_is_a_bloc_chair_not_a_speaker(self):
        assert self._bloc("رئيس") == "bloc_chair"
        assert self._bloc("Président") == "bloc_chair"
        assert self._bloc("نائب رئيس") == "bloc_vice_chair"
        assert self._bloc("عضو") == "unknown"

    def test_both_maps_emit_only_declared_vocabulary(self):
        for mapping in (arp_odoo.OFFICE_MAP, arp_odoo.BLOC_ROLE_MAP):
            assert set(mapping.values()) <= set(schema.OFFICE)

    def test_the_non_attached_representative_is_not_forced_into_a_role(self):
        # "Representative of the non-attached in the conference of presidents"
        # is not a bureau post and the vocabulary has no slot for it. `unknown`
        # is the honest answer; guessing `bureau_member` would assert a fact.
        label = "ممثّل عن النواب غير المنتمين إلى كتل في ندوة الرؤساء"
        assert self._office(label) == "unknown"
        assert self._bloc(label) == "unknown"


class TestMajlesBureau:
    """ARP-2019 presiding officers, the chamber's only office data.

    The enum has to come from the *individual* title rather than the section
    heading, because "Vice-présiendent(e)s" covers both vice-presidencies and
    only each holder's own title carries the ordinal that separates them.
    """

    def _card(self, slug, dates, name, role):
        return f"""
        <a href="/ar/person/{slug}" class="text-center">
          <div class="info-popup"><span>Bloc X</span>
            <span><img class="popup-icon" src="/icons/calendar.svg">{dates}</span>
          </div>
          <div class="person-name h6">{name}</div>
          <div class="person-bloc txt-red">{role}</div>
        </a>"""

    def test_ordinal_separates_the_two_vice_speakers(self):
        markup = (self._card("a", "13 نوفمبر 2019 - اليوم", "A", "Première vice-présidente")
                  + self._card("b", "14 نوفمبر 2019 - اليوم", "B", "Deuxième vice-président"))
        parsed = marsad_majles.parse_bureau(markup)
        assert marsad_majles._office_code(parsed["a"]["role"]) == "first_vice_speaker"
        assert marsad_majles._office_code(parsed["b"]["role"]) == "vice_speaker"

    def test_assessors_are_bureau_members_not_speakers(self):
        # Their titles all contain "Président" as the person they assist, so a
        # naive substring test on "président" would make ten of them speakers.
        role = "L’assesseur auprès du Président chargé de la législation"
        assert marsad_majles._office_code(role) == "bureau_member"

    def test_dates_are_parsed_and_the_open_end_stays_empty(self):
        parsed = marsad_majles.parse_bureau(
            self._card("a", "20 أكتوبر 2020 - اليوم", "A", "الرئيس"))
        assert parsed["a"]["start_date"] == "2020-10-20"
        # "اليوم" means still serving when the site froze in 2021 — not today,
        # and not the March 2022 dissolution. Neither may be invented here.
        assert parsed["a"]["end_date"] == ""


# ---------------------------------------------------------------------------
# The Chamber of Advisors, 2005-2011
# ---------------------------------------------------------------------------

ADV_GOV_FR = """
<div id="texte">
<table><tbody>
 <tr><td class="CelTab1" colspan="2">La Manouba</td></tr>
 <tr><td class="CelTab2">Abdelwahed Trabelsi</td><td class="CelTab2">Salem Ben Amor</td></tr>
</tbody></table>
<table><tbody>
 <tr><td class="CelTab1" colspan="2">Zaghouan</td></tr>
 <tr><td class="CelTab2">Salah Ben Haj Hessine</td></tr>
</tbody></table>
</div>
<div id="end"></div>
"""

ADV_GOV_AR = """
<div id="content">
<table><tbody>
 <tr><td class="CelTab1" colspan="2">زغوان</td></tr>
 <tr><td class="CelTab2">صالح بن الحاج حسين</td></tr>
</tbody></table>
<table><tbody>
 <tr><td class="CelTab1" colspan="2">منوبة</td></tr>
 <tr><td class="CelTab2">سالم بن عمر</td><td class="CelTab2">عبد الواحد الطرابلسي</td></tr>
</tbody></table>
</div>
<div id="end"></div>
"""

ADV_APPOINTEES = """
<div id="texte"><table><tbody>
 <tr><td class="CelTab2">1</td><td class="CelTab2">Abdallah Kallel</td>
     <td class="CelTab2">15</td><td class="CelTab2">Chedli Klibi</td></tr>
 <tr><td class="CelTab2">2</td><td class="CelTab2"></td>
     <td class="CelTab2">16</td><td class="CelTab2">Sadok Ben Jemâa</td></tr>
</tbody></table></div>
<div id="end"></div>
"""

ADV_COMMITTEE = """
<div id="texte"><table><tbody>
 <tr><td class="CelTab1">Liste des membres de la Commission des finances</td>
     <td class="CelTab1">Liste des membres de la Commission de l’immunité</td></tr>
 <tr><td class="CelTab2"><div>Mohamed Sahraoui - Pr&eacute;sident de la Commission<br />
        Mongi Cherif - Rapporteur de la Commission<br />
        Salah Ben Haj Hessine - Rapporteur-adjoint<br />
        Abdelwahed Trabelsi</div></td>
     <td class="CelTab2"><div>Salem Ben Amor - Pr&eacute;sident de la Commission<br />
        - Rapporteur de la Commission<br />
        Mohamed Nejib Hamadi- Rapporteur-adjoint</div></td></tr>
</tbody></table></div>
<div id="end"></div>
"""


class TestAdvGovernorateJoin:
    """The two language versions list governorates in different orders."""

    def test_headings_resolve_to_governorate_ids(self):
        latin = chambre_conseillers.parse_governorates(ADV_GOV_FR, arabic=False)
        arabic = chambre_conseillers.parse_governorates(ADV_GOV_AR, arabic=True)
        assert set(latin) == set(arabic)
        # Manouba is TN-14, Zaghouan TN-22 — and note the pages disagree on order,
        # which is exactly why the join cannot be positional.
        assert latin["TN-14"] == ["Abdelwahed Trabelsi", "Salem Ben Amor"]
        assert arabic["TN-14"] == ["سالم بن عمر", "عبد الواحد الطرابلسي"]

    def test_pair_assignment_undoes_the_reversal(self):
        latin = chambre_conseillers.parse_governorates(ADV_GOV_FR, arabic=False)
        arabic = chambre_conseillers.parse_governorates(ADV_GOV_AR, arabic=True)
        pairs = dict(chambre_conseillers._assign_pair(
            arabic["TN-14"], latin["TN-14"], "TN-14"))
        assert pairs["سالم بن عمر"] == "Salem Ben Amor"

    def test_single_member_governorate_needs_no_decision(self):
        latin = chambre_conseillers.parse_governorates(ADV_GOV_FR, arabic=False)
        arabic = chambre_conseillers.parse_governorates(ADV_GOV_AR, arabic=True)
        assert len(chambre_conseillers._assign_pair(
            arabic["TN-22"], latin["TN-22"], "TN-22")) == 1

    def test_size_disagreement_raises(self):
        with pytest.raises(ValueError):
            chambre_conseillers._assign_pair(["أ"], ["A", "B"], "somewhere")

    def test_unknown_heading_raises_rather_than_dropping_a_governorate(self):
        with pytest.raises(ValueError):
            chambre_conseillers.parse_governorates(
                '<div id="texte"><table><tbody>'
                '<tr><td class="CelTab1">Atlantis</td></tr>'
                '<tr><td class="CelTab2">Someone</td></tr>'
                "</tbody></table></div><div id=\"end\"></div>",
                arabic=False,
            )


class TestAdvAppointees:
    def test_slot_numbers_are_the_join_key(self):
        slots = chambre_conseillers.parse_appointees(
            chambre_conseillers._content(ADV_APPOINTEES))
        assert slots[1] == "Abdallah Kallel"
        assert slots[15] == "Chedli Klibi"

    def test_an_empty_cell_is_a_vacancy_not_a_missing_row(self):
        """A blank name beside a live number is a seat the chamber did not fill."""
        slots = chambre_conseillers.parse_appointees(
            chambre_conseillers._content(ADV_APPOINTEES))
        assert 2 in slots
        assert slots[2] == ""


class TestAdvCommittees:
    def test_members_and_roles(self):
        lists = chambre_conseillers.parse_committee_lists(
            chambre_conseillers._content(ADV_COMMITTEE))
        assert len(lists) == 2
        name, members = lists[0]
        assert "Commission des finances" in name
        assert [chambre_conseillers._committee_role(r) for _n, r in members] == [
            "chair", "rapporteur", "assistant_rapporteur", "member"]

    def test_a_titled_row_with_no_name_is_not_a_member(self):
        """The source prints a rapporteur's title with no name beside it."""
        _name, members = chambre_conseillers.parse_committee_lists(
            chambre_conseillers._content(ADV_COMMITTEE))[1]
        assert ("", "Rapporteur de la Commission") in members

    def test_missing_space_before_the_dash_still_splits(self):
        assert chambre_conseillers._split_member(
            "Mohamed Nejib Hamadi- Rapporteur-adjoint") == (
                "Mohamed Nejib Hamadi", "Rapporteur-adjoint")

    def test_a_bare_name_has_no_role(self):
        assert chambre_conseillers._split_member("Abdelwahed Trabelsi") == (
            "Abdelwahed Trabelsi", "")

    def test_assistant_rapporteur_does_not_resolve_as_rapporteur(self):
        assert chambre_conseillers._committee_role("Rapporteur-adjoint") == (
            "assistant_rapporteur")


class TestAdvMemberResolution:
    """Committee pages spell a dozen names differently from the roster pages."""

    def _roster(self):
        names = [("ع", "Essia Dekhili"), ("ع", "Jamel Eddine Khemakhem"),
                 ("ع", "Mohamed Jalel Rouissi"), ("ع", "Slaheddine Chaâben"),
                 ("ع", "Hayet Aouani")]
        seats = {}
        for name_ar, name_lat in names:
            seat = chambre_conseillers.Seat(name_ar, name_lat, "appointed")
            seats[seat.source_key] = seat
        return seats

    @pytest.mark.parametrize("spelling,expected", [
        ("Essia Dekhili", "Essia_Dekhili"),          # exact
        ("Essia Dekhil", "Essia_Dekhili"),           # truncated
        ("Jameleddine Khemakhem", "Jamel_Eddine_Khemakhem"),
        ("Jalel Rouissi", "Mohamed_Jalel_Rouissi"),  # dropped given name
        ("Saleheddine Chaâbane", "Slaheddine_Cha_ben"),
        ("Hayet Laouani", "Hayet_Aouani"),
    ])
    def test_variants_resolve_into_the_roster(self, spelling, expected):
        assert chambre_conseillers._resolve_member(spelling, self._roster()) == expected

    def test_a_role_label_that_leaked_through_resolves_to_nobody(self):
        """A parse slip must not invent a member; it must return nothing."""
        assert chambre_conseillers._resolve_member(
            "Rapporteur de la Commission", self._roster()) == ""


class TestAdvVersionObservation:
    def _seat(self, name):
        return chambre_conseillers.Seat("ع", name, "appointed")

    def test_a_member_on_every_state_is_neither_arrival_nor_departure(self):
        seats = {}
        for index, date in enumerate(["2010-04-12", "2011-09-01"]):
            seen = {s.source_key: s for s in [self._seat("A")]}
            chambre_conseillers._observe(seats, seen, date, date, index == 0, "appointed")
        assert seats["A"].first_absent == ""
        assert seats["A"].late_arrival is False

    def test_a_member_who_stops_appearing_is_bracketed(self):
        seats = {}
        chambre_conseillers._observe(
            seats, {s.source_key: s for s in [self._seat("A"), self._seat("B")]},
            "2010-04-12", "2010-08-21", True, "appointed")
        chambre_conseillers._observe(
            seats, {s.source_key: s for s in [self._seat("A")]},
            "2011-09-01", "2011-09-01", False, "appointed")
        assert seats["B"].last_seen == "2010-08-21"
        assert seats["B"].first_absent == "2011-09-01"
        end, exit_mode, note = chambre_conseillers._mandate_notes(seats["B"])
        # The interval contains the dissolution, so no end date is asserted.
        assert end == ""
        assert exit_mode == "unknown"
        assert "2010-08-21" in note and "2011-09-01" in note

    def test_a_member_of_another_page_is_not_recorded_as_having_left(self):
        """Absence is only ever read off the page a seat belongs to."""
        seats = {}
        chambre_conseillers._observe(
            seats, {s.source_key: s for s in [self._seat("A")]},
            "2010-04-12", "2010-08-21", True, "appointed")
        other = chambre_conseillers.Seat("ع", "B", "governorate")
        chambre_conseillers._observe(
            seats, {other.source_key: other}, "2011-09-01", "2011-09-01", True, "governorate")
        assert seats["A"].first_absent == ""

    def test_a_late_arrival_keeps_the_dissolution_as_its_end(self):
        seats = {}
        chambre_conseillers._observe(
            seats, {s.source_key: s for s in [self._seat("A")]},
            "2010-04-12", "2010-08-21", True, "appointed")
        chambre_conseillers._observe(
            seats, {s.source_key: s for s in [self._seat("A"), self._seat("B")]},
            "2011-09-01", "2011-09-01", False, "appointed")
        assert seats["B"].late_arrival is True
        end, exit_mode, note = chambre_conseillers._mandate_notes(seats["B"])
        assert end == chambre_conseillers.DISSOLUTION
        assert exit_mode == "dissolution"
        assert "bracketed" in note


class TestAdvStructuralJoinGuard:
    def test_corresponding_pages_pass(self):
        pairs = [("محمد الصحراوي", "Mohamed Sahraoui"),
                 ("مبروك البحري", "Mabrouk Bahri")]
        assert chambre_conseillers._check_similarity(pairs, "test") > 0.3

    def test_a_shifted_join_raises_instead_of_mislabelling(self):
        pairs = [("محمد الصحراوي", "Mabrouk Bahri"),
                 ("مبروك البحري", "Joseph Roger Bismuth")]
        with pytest.raises(ValueError):
            chambre_conseillers._check_similarity(pairs, "test")


# ---------------------------------------------------------------------------
# ARP-2014 committees and bureau, across three site layouts
# ---------------------------------------------------------------------------

COMMITTEE_2015 = """
<h4>لجنة التشريع العام</h4>
<a href="/2014/elus/Slim_Besbes" class="membre">
  <span class="elu-fonction floati">الرئيس</span>
  <span class="elu-nom">سليم بسباس</span><br>
  <span class="elu-liste">حركة النهضة</span>
</a>
<a href="/2014/elus/Olfa_Soukri" class="membre">
  <span class="elu-fonction floati">المقرر</span>
  <span class="elu-nom">ألفة السكري</span>
</a>
"""

COMMITTEE_2016 = """
<h1 class="col-5">لجنة التشريع العام</h1>
<a href="/2014/elus/Chaker_Ayadi" data-bloc="حركة نداء تونس" data-region="جندوبة">
  <div class="elu-nom">شاكر عيادي</div>
  <div class="elu-fonction">رئيس اللجنة</div>
</a>
<a href="/2014/elus/Latifa_Habachi" data-bloc="حركة النهضة" data-region="منوبة">
  <div class="elu-nom">لطيفة الحباشي</div>
  <div class="elu-fonction">نائبة رئيس اللجنة</div>
</a>
<a href="/2014/elus/Sana_Mersni" data-bloc="حركة النهضة" data-region="جندوبة">
  <div class="elu-nom">سناء مرسني</div>
  <div class="elu-fonction">مقررة مساعدة أولى</div>
</a>
"""

COMMITTEE_2019 = """
<h1>لجنة التشريع العام</h1>
<a href="/2014/elus/Karim_Helali" class="link-elu">
  <h6 class="card-title mb-1">كريم الهلالي</h6>
  <span class="p-0 d-block text-primary font-weight-normal h6">رئيس</span>
</a>
"""

# A wound-up committee: no sitting members, only a list of who resigned.
COMMITTEE_DISSOLVED = """
<h4>اللجنة الخاصة المكلفة بالماليّة</h4>
<h4>أعضاء مستقيلين</h4>
<div><a class="black" href="/2014/elus/Tarek_Fetiti">طارق فتيتي</a></div>
<div><a class="black" href="/2014/elus/Olfa_Soukri">ألفة السكري</a></div>
"""

BUREAU_2019 = """
<h5 class="card-header">الرئيس</h5>
<a href="/2014/elus/Mohamed_Ennaceur" class="link-elu">
  <h6 class="card-title mb-1">محمد الناصر</h6>
  <span class="p-0 d-block text-primary"><i class="fal fa-briefcase"></i> الرئيس</span>
  <span class="p-0 d-block"><i class="fal fa-calendar-alt"></i> 04 ديسمبر 2015 - 25 جويلية 2019</span>
</a>
<a href="/2014/elus/Abdelfattah_Mourou" class="link-elu">
  <h6 class="card-title mb-1">عبد الفتاح مورو</h6>
  <span class="p-0 d-block text-primary"><i class="fal fa-briefcase"></i> النائب الأوّل لرئيس المجلس</span>
  <span class="p-0 d-block"><i class="fal fa-calendar-alt"></i> 04 ديسمبر 2014 - الآن</span>
</a>
<a href="/2014/elus/Faycel_Khelifa" class="link-elu">
  <h6 class="card-title mb-1">فيصل خليفة</h6>
  <span class="p-0 d-block text-primary"><i class="fal fa-briefcase"></i> مساعد الرئيس المكلف بالإعلام والاتصال</span>
  <span class="p-0 d-block"><i class="fal fa-calendar-alt"></i> 19 أكتوبر 2018 - الآن</span>
</a>
"""


class TestArp2014CommitteeLayouts:
    """The site was redesigned twice mid-term; all three layouts must parse."""

    @pytest.mark.parametrize("markup,slug", [
        (COMMITTEE_2015, "Slim_Besbes"),
        (COMMITTEE_2016, "Chaker_Ayadi"),
        (COMMITTEE_2019, "Karim_Helali"),
    ])
    def test_each_layout_yields_its_chair(self, markup, slug):
        name, members = marsad_arp2014.parse_committee_page(markup)
        assert name == "لجنة التشريع العام"
        assert (slug, "chair") in members

    def test_resigned_members_are_not_current_members(self):
        """A wound-up committee still links its former members."""
        _name, members = marsad_arp2014.parse_committee_page(COMMITTEE_DISSOLVED)
        assert members == []


class TestArp2014RoleClassification:
    """39 spellings of 5 roles; classification is by token, and order matters."""

    @pytest.mark.parametrize("label,expected", [
        ("رئيس اللجنة", "chair"),
        ("رئيسة اللجنة", "chair"),
        ("الرئيس", "chair"),
        ("نائب رئيس اللجنة", "vice_chair"),
        ("نائبة رئيسة اللجنة", "vice_chair"),
        ("مقرر اللجنة", "rapporteur"),
        ("مقرّرة", "rapporteur"),
        ("مقرر مساعد أول", "assistant_rapporteur"),
        ("مقررة مساعدة ثانية", "assistant_rapporteur"),
        ("مساعد مقرر ثاني", "assistant_rapporteur"),
        ("عضو", "member"),
        ("عضوة", "member"),
    ])
    def test_labels(self, label, expected):
        assert marsad_arp2014._classify(
            label, marsad_arp2014.COMMITTEE_ROLE_TOKENS, "member") == expected

    def test_a_vice_chair_is_not_read_as_a_chair(self):
        """'نائب رئيس اللجنة' contains 'رئيس'; the order of the tests is the fix."""
        assert marsad_arp2014._classify(
            "نائب رئيس اللجنة", marsad_arp2014.COMMITTEE_ROLE_TOKENS, "member") != "chair"

    def test_an_assistant_rapporteur_is_not_read_as_a_rapporteur(self):
        assert marsad_arp2014._classify(
            "مقرر مساعد أول", marsad_arp2014.COMMITTEE_ROLE_TOKENS, "member") != "rapporteur"

    def test_the_shadda_does_not_change_the_answer(self):
        assert marsad_arp2014._classify(
            "مقرّر", marsad_arp2014.COMMITTEE_ROLE_TOKENS, "member") == (
                marsad_arp2014._classify(
                    "مقرر", marsad_arp2014.COMMITTEE_ROLE_TOKENS, "member"))


class TestArp2014Bureau:
    def test_offices_and_portfolios(self):
        rows = marsad_arp2014.parse_bureau_page(BUREAU_2019)
        offices = {slug: office for slug, office, _t, _d in rows}
        assert offices["Mohamed_Ennaceur"] == "speaker"
        assert offices["Abdelfattah_Mourou"] == "first_vice_speaker"
        # An assistant to the speaker holds a portfolio and sits on the bureau.
        assert offices["Faycel_Khelifa"] == "bureau_member"

    def test_the_portfolio_label_is_kept_verbatim(self):
        rows = {slug: title for slug, _o, title, _d in
                marsad_arp2014.parse_bureau_page(BUREAU_2019)}
        assert rows["Faycel_Khelifa"] == "مساعد الرئيس المكلف بالإعلام والاتصال"

    def test_published_dates_are_parsed(self):
        dates = {slug: d for slug, _o, _t, d in
                 marsad_arp2014.parse_bureau_page(BUREAU_2019)}
        assert marsad_arp2014.parse_arabic_date(
            dates["Mohamed_Ennaceur"].split(" - ")[0]) == "2015-12-04"
        assert marsad_arp2014.parse_arabic_date(
            dates["Mohamed_Ennaceur"].split(" - ")[1]) == "2019-07-25"

    def test_still_serving_is_recognised_rather_than_parsed_as_a_date(self):
        assert marsad_arp2014.parse_arabic_date("الآن") == ""
        assert any(tok in "04 ديسمبر 2014 - الآن"
                   for tok in marsad_arp2014.STILL_SERVING)


class TestArp2014CommitteeSpells:
    def _obs(self, *pairs):
        """(date, [slugs]) -> observation list."""
        return [(date, {slug: "member" for slug in slugs}) for date, slugs in pairs]

    def test_present_throughout_is_one_unbracketed_spell(self):
        spells = marsad_arp2014.build_committee_spells(
            self._obs(("2015-03-07", ["A"]), ("2019-08-23", ["A"])))["A"]
        assert len(spells) == 1
        assert spells[0]["start_date"] == marsad_arp2014.FIRST_SITTING
        assert spells[0]["end_date"] == marsad_arp2014.TERM_END
        assert spells[0]["dates_bracketed"] is False

    def test_a_late_joiner_starts_when_first_seen_not_at_the_first_sitting(self):
        spells = marsad_arp2014.build_committee_spells(
            self._obs(("2015-03-07", ["A"]), ("2017-05-25", ["A", "B"])))["B"]
        assert spells[0]["start_date"] == "2017-05-25"
        assert spells[0]["dates_bracketed"] is True

    def test_someone_who_leaves_does_not_serve_to_the_end_of_the_term(self):
        spells = marsad_arp2014.build_committee_spells(
            self._obs(("2015-03-07", ["A", "B"]), ("2017-05-25", ["A"]),
                      ("2019-08-23", ["A"])))["B"]
        assert len(spells) == 1
        assert spells[0]["end_date"] != marsad_arp2014.TERM_END
        assert spells[0]["last_observed"] == "2015-03-07"

    def test_leaving_and_returning_is_two_spells_not_one(self):
        spells = marsad_arp2014.build_committee_spells(
            self._obs(("2015-03-07", ["A"]), ("2017-05-25", []),
                      ("2019-08-23", ["A"])))["A"]
        assert len(spells) == 2

    def test_a_promotion_does_not_split_the_spell(self):
        observations = [("2015-03-07", {"A": "member"}), ("2017-05-25", {"A": "chair"})]
        spells = marsad_arp2014.build_committee_spells(observations)["A"]
        assert len(spells) == 1
        assert spells[0]["role"] == "chair"


class TestNameOnlyMergeDistance:
    """A shared name is the weakest evidence here, and it decays with time."""

    def _builder(self, years):
        b = object.__new__(build_mod.Builder)
        b.assemblies = {a: {"start_date": f"{y}-01-01", "end_date": ""}
                        for a, y in years.items()}
        b.person_fields = {"P": {}}
        b.rejected_merges = []
        return b

    def test_a_plausible_gap_still_merges(self):
        """Rachid Sfar sat in the 1986 chamber and the 2005 upper house."""
        b = self._builder({"COD-1986": 1986, "ADV-2005": 2005})
        assert b._too_far_apart("P", "COD-1986", "ADV-2005") is False

    def test_an_implausible_gap_is_refused(self):
        """Two men called الطيب السحباني beats one serving 1956 to 2005."""
        b = self._builder({"ANC-1956": 1956, "ADV-2005": 2005})
        assert b._too_far_apart("P", "ANC-1956", "ADV-2005") is True

    def test_the_refusal_is_recorded_not_silent(self):
        b = self._builder({"ANC-1956": 1956, "ADV-2005": 2005})
        b._too_far_apart("P", "ANC-1956", "ADV-2005")
        assert b.rejected_merges[0]["years_apart"] == 49

    def test_a_birth_date_settles_it_on_evidence_instead(self):
        b = self._builder({"ANC-1956": 1956, "ADV-2005": 2005})
        b.person_fields["P"]["birth_date"] = (0, "1930-01-01")
        assert b._too_far_apart("P", "ANC-1956", "ADV-2005") is False

    def test_an_undated_chamber_does_not_trigger_the_rule(self):
        """The rule needs two dates; without them it must not guess."""
        b = self._builder({"ADV-2005": 2005})
        b.assemblies["MYSTERY"] = {"start_date": "", "end_date": ""}
        assert b._too_far_apart("P", "MYSTERY", "ADV-2005") is False


class TestStagedConstituencyMerge:
    """Staged constituency rows must enrich the derived ones, never pre-empt them."""

    def _builder(self):
        b = object.__new__(build_mod.Builder)
        b.constituencies = {}
        b.gov_by_name = {"تونس": "TN-11"}
        return b

    def test_a_staged_row_fills_a_blank_field(self):
        b = self._builder()
        cid = b.resolve_constituency("تونس", "Tunis", "ADV-2005", "تونس", False)
        for field, value in [("magnitude", "2")]:
            if not b.constituencies[cid].get(field):
                b.constituencies[cid][field] = value
        assert b.constituencies[cid]["magnitude"] == "2"

    def test_resolution_still_derives_a_governorate_after_a_row_exists(self):
        """The regression this guards.

        `resolve_constituency` only derives a governorate for a constituency it
        is *creating*. Seeding the table from staged rows before the records are
        read therefore stops that derivation running at all, and silently strips
        `governorate_id` from every mandate in the chamber — which is why the
        merge happens after ingest, not before.
        """
        b = self._builder()
        cid = b.resolve_constituency("تونس", "Tunis", "ARP-2023", "تونس", False)
        assert b.constituencies[cid]["governorate_id"] == "TN-11"

    def test_a_preseeded_blank_row_would_have_lost_the_governorate(self):
        """States the failure mode explicitly, so the ordering cannot drift back."""
        b = self._builder()
        cid = build_mod.deterministic_id("TNC", "ARP-2023", b._norm_place("تونس"))
        b.constituencies[cid] = {
            "constituency_id": cid, "assembly_id": "ARP-2023", "name_ar": "تونس",
            "name_lat": "", "governorate_id": "", "is_abroad": "false", "magnitude": "2",
        }
        b.resolve_constituency("تونس", "Tunis", "ARP-2023", "تونس", False)
        assert b.constituencies[cid]["governorate_id"] == ""
