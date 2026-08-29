"""Unit tests for the parts of the pipeline where a silent bug would be costly.

The emphasis is on the logic that is easy to get wrong and hard to notice:
Arabic name normalisation, biography parsing, temporal overlap in network
projection, and the guards that stopped real bugs during development. Each test
that corresponds to a bug found in the data names it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from parliamentarians_tn import schema  # noqa: E402
from parliamentarians_tn.collect import (  # noqa: E402
    arp_odoo,
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
