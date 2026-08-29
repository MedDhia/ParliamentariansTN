"""Collector: the sitting Assembly of the Representatives of the People, from arp.tn.

The chamber's own website runs on Odoo 12 and exposes the same JSON-RPC endpoint
its public front-end uses (``/web/dataset/call_kw``). Reading it directly gives
structured records instead of scraped HTML: deputies, their governorate and
constituency, their parliamentary bloc and committee memberships with
appointment and departure dates, and the bureau offices they hold.

Two things about this access deserve stating plainly, since they bear on
whether the dataset is reproducible and defensible:

* **Only public data is read.** The endpoint enforces Odoo's access-control
  layer as the anonymous portal user. Administrative models (``ir.model``,
  ``arp.motif``, ``arp.competence``) return ``AccessError`` and are not
  pursued. Every model queried here is one the chamber's own public pages
  query to render themselves, so nothing is retrieved that a visitor to
  arp.tn is not already shown.
* **The public projection is scoped to the current mandate.** ``arp.mandat``
  lists the 2011-14, 2014-19, 2019-24 and 2023-27 terms, but membership rows
  for the closed terms are filtered out by record rules. Requests for them
  return zero rows, which is why this collector covers ARP-2023 only and the
  earlier terms are sourced from Al Bawsala instead.

A further quirk worth knowing when reading the output: Odoo stores translations
per field, so the *same* record yields ``إبراهيم بودربالة`` under
``lang=ar_SY`` and ``Brahim Bouderbela`` under ``lang=fr_FR``. The collector
fetches both and merges them, which is where the dataset's bilingual name
columns come from — and it is the cleanest romanisation available anywhere for
these members, because it is the chamber's own.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from ..io import Fetcher, RAW, log, today
from .base import PersonRecord, StagingDoc

SOURCE_ID = "ARP_ODOO"
ENDPOINT = "https://www.arp.tn/web/dataset/call_kw"
SITE = "https://www.arp.tn"

# arp.mandat primary key -> dataset assembly_id.
MANDATE_TO_ASSEMBLY = {
    104: "NCA-2011",
    19: "ARP-2014",
    43: "ARP-2019",
    105: "ARP-2023",
}
CURRENT_MANDATE = 105
CURRENT_ASSEMBLY = "ARP-2023"

LANG_AR = "ar_SY"
LANG_FR = "fr_FR"

# Arabic role titles used in arp.fonction, mapped to the schema vocabulary.
ROLE_MAP = {
    "رئيس": "chair",
    "نائب رئيس": "vice_chair",
    "نائب الرئيس": "vice_chair",
    "مقرر": "rapporteur",
    "مساعد مقرر": "assistant_rapporteur",
    "مقرر مساعد": "assistant_rapporteur",
    "عضو": "member",
}

# Chamber offices, from arp.mandat.fonction. `_map_role` tries the longest key
# first, which is what keeps these apart: every title below contains "رئيس", so
# a shorter key would swallow the longer ones. "نائب مساعد للرئيس" — assistant
# deputy to the president, the chamber's assessors — is the case that made this
# explicit: without it, 29 of the 37 recorded tenures fell through to the
# four-character "رئيس" and were coded `speaker`, in a chamber that has one.
OFFICE_MAP = {
    "نائب مساعد للرئيس": "bureau_member",
    "رئيس": "speaker",
    "رئيس المجلس": "speaker",
    "النائب الأول لرئيس": "first_vice_speaker",
    "النائب الأول": "first_vice_speaker",
    "نائب رئيس": "vice_speaker",
    "نائب الرئيس": "vice_speaker",
    "عضو المكتب": "bureau_member",
}

# Roles *inside a bloc*, from arp.deputegroupe. A separate map from OFFICE_MAP,
# because the same word means different things in the two places: the head of a
# bloc is not the speaker of the chamber. Sharing the map coded 11 bloc chairs
# as `speaker` and 12 bloc vice-chairs as `vice_speaker`. `marsad_majles` has
# used bloc_chair for this since it was written; this brings arp.tn into line.
BLOC_ROLE_MAP = {
    "نائب رئيس": "bloc_vice_chair",
    "نائب الرئيس": "bloc_vice_chair",
    "رئيس": "bloc_chair",
    "الرئيس": "bloc_chair",
    "Président": "bloc_chair",
}

# arp.deputegroupe / arp.deputecommission `cause` -> mandates.exit_mode idiom.
CAUSE_MAP = {
    "deces": "death",
    "demission": "resignation",
    "fin_mandat": "end_of_term",
    "fin_groupe": "bloc_dissolved",
    "fin_commission": "committee_dissolved",
}


def _m2o_id(value: Any) -> str:
    """Odoo many2one is ``[id, display_name]`` or ``False``."""
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return ""


def _m2o_name(value: Any) -> str:
    if isinstance(value, (list, tuple)) and len(value) > 1 and value[1]:
        return str(value[1]).strip()
    return ""


def _clean_str(value: Any) -> str:
    """Odoo returns False for every empty field, whatever its declared type."""
    if value is False or value is None:
        return ""
    return str(value).strip()


def _date_only(value: Any) -> str:
    s = _clean_str(value)
    return s[:10] if s else ""


def _map_role(label: str, mapping: dict[str, str], default: str = "member") -> str:
    if not label:
        return default
    label = label.strip()
    for key, val in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        if key in label:
            return val
    return default


class OdooClient:
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    def call(self, model: str, method: str, args: list[Any], lang: str | None = None,
             slug: str | None = None) -> Any:
        kwargs: dict[str, Any] = {}
        if lang:
            kwargs["context"] = {"lang": lang}
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {"model": model, "method": method, "args": args, "kwargs": kwargs},
        }
        slug = slug or f"{model}_{method}_{lang or 'default'}"
        data = self.fetcher.post_json(
            ENDPOINT, slug=slug, payload=payload,
            cacheable=lambda d: isinstance(d, dict) and "error" not in d,
        )
        if "error" in data:
            err = data["error"].get("data", {})
            raise RuntimeError(
                f"{model}.{method} failed: {err.get('exception_type')} "
                f"{err.get('message', '')[:200]}"
            )
        return data["result"]

    def search_read(self, model: str, domain: list[Any], fields: list[str],
                    lang: str | None = None, limit: int = 0, slug: str | None = None) -> list[dict]:
        return self.call(model, "search_read", [domain, fields, 0, limit], lang=lang, slug=slug)


def collect(refresh: bool = False) -> StagingDoc:
    fetcher = Fetcher(RAW / "arp_odoo", delay=1.0, refresh=refresh)
    api = OdooClient(fetcher)

    # -- reference tables -------------------------------------------------
    gov_ar = api.search_read("arp.gouvernorat", [], ["name", "code_iso"], lang=LANG_AR, slug="gov_ar")
    gov_fr = api.search_read("arp.gouvernorat", [], ["name", "code_iso"], lang=LANG_FR, slug="gov_fr")
    gov_fr_by_id = {g["id"]: g for g in gov_fr}

    circ_ar = api.search_read("arp.circonscription", [], ["name", "id_gouvernorat"], lang=LANG_AR, slug="circ_ar")
    circ_fr = api.search_read("arp.circonscription", [], ["name", "id_gouvernorat"], lang=LANG_FR, slug="circ_fr")
    circ_fr_by_id = {c["id"]: c for c in circ_fr}

    mandates = api.search_read("arp.mandat", [], ["name", "date_debut", "date_fin"], slug="mandats")
    log(f"  arp.mandat: {[(m['id'], m['name']) for m in mandates]}")

    # -- deputies, in both scripts ---------------------------------------
    dep_fields = [
        "name", "nom", "prenom", "gender", "marital", "birthday", "date_deaths",
        "work_email", "facebook", "twitter", "site", "type_depute", "state",
        "experience", "biographie", "adresse", "city_perso",
    ]
    dep_ar = api.search_read("arp.depute", [], dep_fields, lang=LANG_AR, slug="depute_ar")
    dep_fr = api.search_read("arp.depute", [], dep_fields, lang=LANG_FR, slug="depute_fr")
    dep_fr_by_id = {d["id"]: d for d in dep_fr}
    log(f"  arp.depute: {len(dep_ar)} records")

    # -- mandate/seat information ----------------------------------------
    info_fields = [
        "depute_id", "mandat_id", "gouvernorat_id", "circonscription_id",
        "election", "siege_id", "sortie", "cause", "experience", "biographie",
        "note", "default_end_date",
    ]
    info_ar = api.search_read("arp.informations.politiques", [], info_fields, lang=LANG_AR, slug="info_ar")
    info_by_dep: dict[str, dict] = {}
    for row in info_ar:
        dep_id = _m2o_id(row.get("depute_id"))
        if dep_id:
            info_by_dep[dep_id] = row
    log(f"  arp.informations.politiques: {len(info_ar)} records")

    # -- blocs -------------------------------------------------------------
    grp_ar = api.search_read("arp.groupe", [], ["name", "id_mandat", "couleur", "dep_list_count"], lang=LANG_AR, slug="groupe_ar")
    grp_fr = api.search_read("arp.groupe", [], ["name", "id_mandat"], lang=LANG_FR, slug="groupe_fr")
    grp_fr_by_id = {g["id"]: g for g in grp_fr}
    grp_by_id = {g["id"]: g for g in grp_ar}

    # `is_active` is a computed field guarded by an ARP/User ACL and makes the
    # whole search_read fail; `state` carries the same live/ended flag and is
    # readable. Requesting no field list at all also errors, so fields are
    # always named explicitly.
    dg_fields = ["depute", "id_groupe", "id_fonction", "mandat_id",
                 "date_affectation", "date_demission", "cause", "state"]
    dep_grp = api.search_read("arp.deputegroupe", [], dg_fields, lang=LANG_AR, slug="deputegroupe_ar")
    log(f"  arp.groupe: {len(grp_ar)} blocs, arp.deputegroupe: {len(dep_grp)} memberships")

    # -- committees --------------------------------------------------------
    com_ar = api.search_read("arp.commission", [], ["name", "id_categorie", "mandat_id", "order"], lang=LANG_AR, slug="commission_ar")
    com_fr = api.search_read("arp.commission", [], ["name", "id_categorie", "mandat_id"], lang=LANG_FR, slug="commission_fr")
    com_fr_by_id = {c["id"]: c for c in com_fr}
    com_by_id = {c["id"]: c for c in com_ar}

    dc_fields = ["depute", "id_commission", "id_fonction", "id_categorie", "mandat_id",
                 "date_affectation", "date_demission", "cause", "state"]
    dep_com = api.search_read("arp.deputecommission", [], dc_fields, lang=LANG_AR, slug="deputecommission_ar")
    log(f"  arp.commission: {len(com_ar)} committees, arp.deputecommission: {len(dep_com)} memberships")

    # -- bureau offices ----------------------------------------------------
    fn_fields = ["depute_id", "fonction_id", "mandat_id", "date_deb", "date_fin", "cause", "order"]
    offices = api.search_read("arp.mandat.fonction", [], fn_fields, lang=LANG_AR, slug="mandatfonction_ar")
    log(f"  arp.mandat.fonction: {len(offices)} office tenures")

    # -- written questions: counts and co-signature ties -------------------
    # The signer set lives in the many2many `deputy_ids`; the many2one
    # `deputy_id` is populated for only a minority of records (2,604 of the
    # questions have it empty) and cannot be used alone. Because `deputy_ids`
    # is a list, a jointly signed question yields a co-signature tie — the only
    # behavioural relational layer available for the sitting chamber.
    questions_per_dep: dict[str, int] = defaultdict(int)
    cosignatures: list[dict[str, Any]] = []
    try:
        q_fields = ["deputy_id", "deputy_ids", "mandat", "date_question"]
        page, offset = 2000, 0
        questions: list[dict] = []
        while True:
            batch = api.call(
                "arp.question.ecrite", "search_read",
                [[], q_fields, offset, page], lang=LANG_AR,
                slug=f"questions_{offset}",
            )
            questions.extend(batch)
            if len(batch) < page:
                break
            offset += page
        for q in questions:
            signers = [str(i) for i in (q.get("deputy_ids") or [])]
            solo = _m2o_id(q.get("deputy_id"))
            if solo and solo not in signers:
                signers.append(solo)
            if not signers:
                continue
            for s in signers:
                questions_per_dep[s] += 1
            if len(signers) > 1:
                cosignatures.append({
                    "question_id": str(q["id"]),
                    "date": _date_only(q.get("date_question")),
                    "mandate_source_key": _m2o_id(q.get("mandat")),
                    "signer_source_keys": signers,
                })
        log(f"  written questions: {len(questions)} records, "
            f"{len(questions_per_dep)} deputies with >=1, "
            f"{len(cosignatures)} jointly signed")
    except Exception as exc:  # noqa: BLE001 - optional enrichment
        log(f"  written-question collection unavailable ({exc}); skipping")

    # -- index memberships by deputy --------------------------------------
    blocs_by_dep: dict[str, list[dict]] = defaultdict(list)
    for row in dep_grp:
        dep_id = _m2o_id(row.get("depute"))
        if not dep_id:
            continue
        gid = _m2o_id(row.get("id_groupe"))
        blocs_by_dep[dep_id].append({
            "source_key": f"grp:{gid}",
            "name_ar": _m2o_name(row.get("id_groupe")),
            "name_lat": _m2o_name(grp_fr_by_id.get(int(gid), {}).get("name")) if gid.isdigit() else "",
            "name_lat_raw": _clean_str(grp_fr_by_id.get(int(gid), {}).get("name")) if gid.isdigit() else "",
            "colour": _clean_str(grp_by_id.get(int(gid), {}).get("couleur")) if gid.isdigit() else "",
            "role": _map_role(_m2o_name(row.get("id_fonction")), BLOC_ROLE_MAP,
                              default="unknown"),
            "role_label_ar": _m2o_name(row.get("id_fonction")),
            "start_date": _date_only(row.get("date_affectation")),
            "end_date": _date_only(row.get("date_demission")),
            "end_cause": CAUSE_MAP.get(_clean_str(row.get("cause")), _clean_str(row.get("cause"))),
            "is_active": bool(row.get("state")),
        })

    committees_by_dep: dict[str, list[dict]] = defaultdict(list)
    for row in dep_com:
        dep_id = _m2o_id(row.get("depute"))
        if not dep_id:
            continue
        cid = _m2o_id(row.get("id_commission"))
        committees_by_dep[dep_id].append({
            "source_key": f"com:{cid}",
            "name_ar": _m2o_name(row.get("id_commission")),
            "name_lat": _clean_str(com_fr_by_id.get(int(cid), {}).get("name")) if cid.isdigit() else "",
            "category_ar": _m2o_name(row.get("id_categorie")),
            "role": _map_role(_m2o_name(row.get("id_fonction")), ROLE_MAP),
            "role_label_ar": _m2o_name(row.get("id_fonction")),
            "start_date": _date_only(row.get("date_affectation")),
            "end_date": _date_only(row.get("date_demission")),
            "end_cause": CAUSE_MAP.get(_clean_str(row.get("cause")), _clean_str(row.get("cause"))),
            "is_active": bool(row.get("state")),
        })

    offices_by_dep: dict[str, list[dict]] = defaultdict(list)
    for row in offices:
        dep_id = _m2o_id(row.get("depute_id"))
        if not dep_id:
            continue
        label = _m2o_name(row.get("fonction_id"))
        offices_by_dep[dep_id].append({
            "office": _map_role(label, OFFICE_MAP, default="unknown"),
            "office_label_ar": label,
            "start_date": _date_only(row.get("date_deb")),
            "end_date": _date_only(row.get("date_fin")),
        })

    # -- build records -----------------------------------------------------
    records: list[PersonRecord] = []
    constituencies: list[dict[str, Any]] = []
    seen_circ: set[str] = set()

    for dep in dep_ar:
        dep_id = str(dep["id"])
        fr = dep_fr_by_id.get(dep["id"], {})
        info = info_by_dep.get(dep_id, {})

        circ_id = _m2o_id(info.get("circonscription_id"))
        gov_id = _m2o_id(info.get("gouvernorat_id"))
        circ_name_ar = _m2o_name(info.get("circonscription_id"))
        gov_name_ar = _m2o_name(info.get("gouvernorat_id"))

        if circ_id and circ_id not in seen_circ:
            seen_circ.add(circ_id)
            fr_circ = circ_fr_by_id.get(int(circ_id), {}) if circ_id.isdigit() else {}
            constituencies.append({
                "source_key": circ_id,
                "name_ar": circ_name_ar,
                "name_lat": _clean_str(fr_circ.get("name")),
                "governorate_name_ar": gov_name_ar,
                "is_abroad": "خارج" in circ_name_ar or "الخارج" in gov_name_ar,
            })

        gender = _clean_str(dep.get("gender")).lower()
        if gender not in ("male", "female"):
            gender = "unknown"

        # `sortie` marks a member who has left; `state` distinguishes the
        # chamber's own status codes. Neither is a date, so an end date only
        # comes from date_deaths or default_end_date.
        left = bool(info.get("sortie"))
        death = _date_only(dep.get("date_deaths"))
        exit_mode = "still_serving"
        if death:
            exit_mode = "death"
        elif left:
            exit_mode = CAUSE_MAP.get(_clean_str(info.get("cause")), "unknown")

        rec = PersonRecord(
            source_key=dep_id,
            source_url=f"{SITE}/deputy/details/{dep_id}",
            name_ar=_clean_str(dep.get("name")),
            name_lat=_clean_str(fr.get("name")),
            given_name_ar=_clean_str(dep.get("prenom")),
            family_name_ar=_clean_str(dep.get("nom")),
            given_name_lat=_clean_str(fr.get("prenom")),
            family_name_lat=_clean_str(fr.get("nom")),
            gender=gender,
            birth_date=_date_only(dep.get("birthday")),
            birth_date_precision="day" if _date_only(dep.get("birthday")) else "",
            death_date=death,
            death_date_precision="day" if death else "",
            marital_status=_clean_str(dep.get("marital")),
            occupation_raw=_clean_str(dep.get("experience")) or _clean_str(info.get("experience")),
            biography_ar=_clean_str(dep.get("biographie")) or _clean_str(info.get("biographie")),
            mandate={
                "start_date": _date_only(info.get("election")) or "2023-03-13",
                "end_date": death,
                "entry_mode": "elected",
                "exit_mode": exit_mode,
                "constituency_name_ar": circ_name_ar,
                "constituency_source_key": circ_id,
                "governorate_name_ar": gov_name_ar,
                "seat_number": _m2o_name(info.get("siege_id")),
                "election_date": _date_only(info.get("election")),
                "is_diaspora_seat": "خارج" in circ_name_ar,
                "notes": _clean_str(info.get("note")),
            },
            blocs=blocs_by_dep.get(dep_id, []),
            committees=committees_by_dep.get(dep_id, []),
            offices=offices_by_dep.get(dep_id, []),
            participation=(
                {"n_written_questions": questions_per_dep[dep_id]}
                if dep_id in questions_per_dep else {}
            ),
            authoritative_fields=[
                "name_ar", "name_lat", "given_name_ar", "family_name_ar",
                "given_name_lat", "family_name_lat", "gender",
            ],
        )
        records.append(rec)

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=CURRENT_ASSEMBLY,
        source={
            "source_id": SOURCE_ID,
            "name": "Assembly of the Representatives of the People — official website backend",
            "publisher": "Assemblée des Représentants du Peuple (Tunisia)",
            "url": SITE,
            "access_method": "Odoo 12 JSON-RPC (/web/dataset/call_kw) as the anonymous portal user, read-only",
            "coverage": (
                "ARP-2023 only: full roster, bilingual names, sex, governorate, "
                "constituency, seat number, bloc and committee memberships with "
                "appointment/departure dates and roles, bureau offices, written-question counts"
            ),
            "language": "ar; fr",
            "licence": "Not stated. Public institutional data on public office-holders.",
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "Authoritative for the sitting chamber's composition. Biographical "
                "depth is thin in the public projection: birthday, marital status "
                "and biography are empty for most members even though the fields "
                "exist. Record rules restrict membership rows to the current "
                "mandate, so the 2011-14, 2014-19 and 2019-24 terms return zero "
                "rows and are covered from Al Bawsala instead. One mandate label "
                "is mistyped upstream as 'Mandat Parlementaire 2028-2027' for the "
                "2023-2027 term."
            ),
        },
        constituencies=constituencies,
        assembly_updates={
            "mandates_seen": {str(m["id"]): m["name"] for m in mandates},
            "governorates": [
                {
                    "source_key": str(g["id"]),
                    "name_ar": _clean_str(g.get("name")),
                    "name_fr": _clean_str(gov_fr_by_id.get(g["id"], {}).get("name")),
                    "iso_3166_2": _clean_str(g.get("code_iso")),
                }
                for g in gov_ar
            ],
            "blocs": [
                {
                    "source_key": str(g["id"]),
                    "name_ar": _clean_str(g.get("name")),
                    "name_lat": _clean_str(grp_fr_by_id.get(g["id"], {}).get("name")),
                    "colour": _clean_str(g.get("couleur")),
                    "n_members_reported": g.get("dep_list_count"),
                    "mandate_source_key": _m2o_id(g.get("id_mandat")),
                }
                for g in grp_ar
            ],
            "written_question_cosignatures": cosignatures,
            "committees": [
                {
                    "source_key": str(c["id"]),
                    "name_ar": _clean_str(c.get("name")),
                    "name_lat": _clean_str(com_fr_by_id.get(c["id"], {}).get("name")),
                    "category_ar": _m2o_name(c.get("id_categorie")),
                    "mandate_source_key": _m2o_id(c.get("mandat_id")),
                }
                for c in com_ar
            ],
        },
        notes=(
            f"{len(records)} deputies; {len(dep_grp)} bloc memberships; "
            f"{len(dep_com)} committee memberships; {len(offices)} office tenures. "
            f"Fetch: {fetcher.report()}."
        ),
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect the sitting ARP from arp.tn")
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    args = ap.parse_args()
    collect(refresh=args.refresh).save()


if __name__ == "__main__":
    main()
