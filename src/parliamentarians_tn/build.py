"""Assemble the analysis-ready tables from staged collector output.

This is where the dataset is actually made. Collectors produce one staging
document per source; this module merges them, resolves people and organisations
to stable identifiers, and writes the relational CSVs in ``data/processed``.

The hard problem it solves is person identity. A deputy who sat in the 2011
Constituent Assembly and returned in 2019 appears in two unconnected sources
with two different upstream keys and two different romanisations of the same
Arabic name. If those are not merged, every re-election, every career, and every
elite-circulation measure is wrong — and the error is invisible, because the
dataset still looks well formed. So matching is done explicitly, its method is
recorded per link in ``person_xref``, and every cross-source merge is written to
``data/processed/_match_review.csv`` for human audit.

Matching is deliberately conservative. Two records merge only when their
normalised Arabic name keys agree, and where both sources supply a Latin name
those must agree too. Tunisian naming makes homonyms common, so a name match
inside a single chamber is never treated as the same person: two members of one
assembly with the same name are two people until a human says otherwise.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any, Iterable

from . import schema
from .collect.base import all_staging
from .ids import (
    IdRegistry,
    arabic_match_key,
    deterministic_id,
    latin_match_key,
    normalize_arabic,
    romanize_arabic,
    value_hash,
)
from .io import PROCESSED, REFERENCE, log, read_table, write_rows, write_table
from .reference import PRESIDING_OFFICERS_PRE2011

# Which source wins when two disagree about the same field. The chamber's own
# register outranks civic monitors, which outrank an encyclopaedia.
SOURCE_PRIORITY = [
    "ARP_ODOO",
    "MARSAD_MAJLES",
    "MARSAD_ANC",
    "WIKI_AR_ANC1956",
    "REFERENCE",
]


def _priority(source_id: str) -> int:
    try:
        return SOURCE_PRIORITY.index(source_id)
    except ValueError:
        return len(SOURCE_PRIORITY)


class Builder:
    def __init__(self) -> None:
        self.assemblies = {r["assembly_id"]: r for r in read_table("assemblies", REFERENCE)}
        self.governorates = list(read_table("governorates", REFERENCE))
        self.parties_ref = list(read_table("parties", REFERENCE))

        # Governorate lookup by every name form we know, normalised.
        self.gov_by_name: dict[str, str] = {}
        for g in self.governorates:
            for field in ("name_ar", "name_lat", "name_fr"):
                if g.get(field):
                    self.gov_by_name[self._norm_place(g[field])] = g["governorate_id"]

        self.party_by_name: dict[str, str] = {}
        for p in self.parties_ref:
            for field in ("name_ar", "name_fr", "name_en", "abbrev"):
                if p.get(field):
                    self.party_by_name[self._norm_place(p[field])] = p["party_id"]

        self.persons = IdRegistry("TNP")
        self.person_fields: dict[str, dict[str, tuple[int, str]]] = defaultdict(dict)
        self.xref: list[dict[str, Any]] = []
        self.match_review: list[dict[str, Any]] = []
        self.provenance: list[dict[str, Any]] = []

        # match indices: key -> [(person_id, assembly_id, source_id, name)]
        self.by_ar_key: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
        self.by_lat_key: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)

        self.mandates: list[dict[str, Any]] = []
        self.constituencies: dict[str, dict[str, Any]] = {}
        self.parties: dict[str, dict[str, Any]] = {p["party_id"]: dict(p) for p in self.parties_ref}
        self.blocs: dict[str, dict[str, Any]] = {}
        self.bloc_memberships: list[dict[str, Any]] = []
        self.committees: dict[str, dict[str, Any]] = {}
        self.committee_memberships: list[dict[str, Any]] = []
        self.offices: list[dict[str, Any]] = []
        self.careers: list[dict[str, Any]] = []
        self.party_affiliations: list[dict[str, Any]] = []
        self.participation: dict[tuple[str, str], dict[str, Any]] = {}
        self.sources: dict[str, dict[str, Any]] = {}

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _norm_place(name: str) -> str:
        """Normalise a place or organisation name for lookup."""
        n = normalize_arabic(name)
        if n:
            return n
        return " ".join(str(name).lower().replace("-", " ").replace("é", "e").split())

    def _record_provenance(self, table: str, record_id: str, field: str,
                           source_id: str, value: Any, retrieved: str) -> None:
        self.provenance.append({
            "table_name": table,
            "record_id": record_id,
            "field_name": field,
            "source_id": source_id,
            "value_hash": value_hash(value),
            "retrieved_at": retrieved,
            "confidence": "high" if source_id == "ARP_ODOO" else "medium",
        })

    def _set_person_field(self, person_id: str, field: str, value: Any, source_id: str) -> None:
        """Fill a person field, keeping the highest-priority non-empty value."""
        if value in (None, "", False):
            return
        prio = _priority(source_id)
        current = self.person_fields[person_id].get(field)
        if current is None or prio < current[0]:
            self.person_fields[person_id][field] = (prio, str(value))

    # -- entity resolution ------------------------------------------------
    def resolve_person(self, rec: dict[str, Any], source_id: str, assembly_id: str) -> str:
        """Return the person_id for a staged record, matching across sources."""
        existing = self.persons.get(source_id, rec["source_key"])
        if existing:
            return existing

        name_ar = rec.get("name_ar") or ""
        name_lat = rec.get("name_lat") or ""
        ar_key = arabic_match_key(name_ar)
        lat_key = latin_match_key(name_lat)

        candidate: tuple[str, str] | None = None  # (person_id, method)
        if ar_key:
            for pid, a_id, s_id, nm in self.by_ar_key.get(ar_key, []):
                # Never merge two members of the same chamber on a name alone.
                if a_id == assembly_id:
                    continue
                # If both sides have a Latin name, require it to agree too.
                other_lat = self.person_fields[pid].get("name_lat")
                if lat_key and other_lat:
                    if latin_match_key(other_lat[1]) != lat_key:
                        continue
                    candidate = (pid, "normalised_name_ar+lat")
                else:
                    candidate = (pid, "normalised_name_ar")
                break
        if candidate is None and lat_key:
            for pid, a_id, s_id, nm in self.by_lat_key.get(lat_key, []):
                if a_id == assembly_id:
                    continue
                candidate = (pid, "normalised_name_lat")
                break

        if candidate:
            person_id, method = candidate
            self.persons.alias(source_id, rec["source_key"], person_id)
            self.match_review.append({
                "person_id": person_id,
                "matched_source": source_id,
                "matched_source_key": rec["source_key"],
                "matched_name_ar": name_ar,
                "matched_name_lat": name_lat,
                "assembly_id": assembly_id,
                "method": method,
                "confidence": "high" if "lat" in method and "ar" in method else "medium",
                "action_required": "confirm this is the same person",
            })
        else:
            person_id = self.persons.mint(source_id, rec["source_key"])
            method = "source_id"

        if ar_key:
            self.by_ar_key[ar_key].append((person_id, assembly_id, source_id, name_ar))
        if lat_key:
            self.by_lat_key[lat_key].append((person_id, assembly_id, source_id, name_lat))

        self.xref.append({
            "person_id": person_id,
            "source_id": source_id,
            "source_key": rec["source_key"],
            "source_url": rec.get("source_url", ""),
            "match_method": method,
            "match_confidence": (
                "high" if method == "source_id"
                else "high" if method == "normalised_name_ar+lat"
                else "medium"
            ),
        })
        return person_id

    def resolve_governorate(self, name: str) -> str:
        if not name:
            return ""
        key = self._norm_place(name)
        if key in self.gov_by_name:
            return self.gov_by_name[key]
        # Out-of-country constituencies name a country or city, not a governorate.
        if any(tok in name for tok in ("خارج", "الخارج", "فرنسا", "إيطاليا", "ألمانيا", "أمريكا")):
            return "TN-99"
        return ""

    def resolve_constituency(self, name_ar: str, name_lat: str, assembly_id: str,
                             governorate_name: str, is_abroad: bool) -> str:
        if not (name_ar or name_lat):
            return ""
        cid = deterministic_id("TNC", assembly_id, self._norm_place(name_ar or name_lat))
        if cid not in self.constituencies:
            gov = self.resolve_governorate(governorate_name) or self.resolve_governorate(name_ar)
            self.constituencies[cid] = {
                "constituency_id": cid,
                "assembly_id": assembly_id,
                "name_ar": name_ar,
                "name_lat": name_lat,
                "governorate_id": gov,
                "is_abroad": "true" if (is_abroad or gov == "TN-99") else "false",
                "magnitude": "",
            }
        elif name_lat and not self.constituencies[cid].get("name_lat"):
            self.constituencies[cid]["name_lat"] = name_lat
        return cid

    def resolve_party(self, name_ar: str, name_lat: str = "") -> str:
        if not (name_ar or name_lat):
            return ""
        for candidate in (name_ar, name_lat):
            if candidate:
                key = self._norm_place(candidate)
                if key in self.party_by_name:
                    return self.party_by_name[key]
        pid = deterministic_id("PTY", self._norm_place(name_ar or name_lat))
        if pid not in self.parties:
            self.parties[pid] = {
                "party_id": pid,
                "name_ar": name_ar,
                "name_fr": name_lat,
                "name_en": "",
                "abbrev": "",
                # Not in the curated register: family is genuinely unknown, and
                # saying so is better than guessing an ideological family.
                "family": "unknown",
                "founded_date": "",
                "dissolved_date": "",
                "predecessor_party_id": "",
                "wikidata_qid": "",
                "notes": "Minted from source data; not in the curated party register.",
            }
            for candidate in (name_ar, name_lat):
                if candidate:
                    self.party_by_name.setdefault(self._norm_place(candidate), pid)
        return pid

    def resolve_bloc(self, spell: dict[str, Any], assembly_id: str) -> str:
        name_ar = spell.get("name_ar", "")
        name_lat = spell.get("name_lat", "")
        key = spell.get("source_key") or name_ar or name_lat
        bid = deterministic_id("BLC", assembly_id, self._norm_place(str(key)))
        if bid not in self.blocs:
            self.blocs[bid] = {
                "bloc_id": bid,
                "assembly_id": assembly_id,
                "name_ar": name_ar,
                "name_lat": name_lat,
                "party_id": self.resolve_party(name_ar, name_lat),
                "formed_date": spell.get("start_date", ""),
                "dissolved_date": "",
                "notes": spell.get("notes", ""),
            }
        return bid

    def resolve_committee(self, spell: dict[str, Any], assembly_id: str) -> str:
        name_ar = spell.get("name_ar", "")
        name_lat = spell.get("name_lat", "")
        key = spell.get("source_key") or name_ar
        cid = deterministic_id("CMT", assembly_id, self._norm_place(str(key)))
        if cid not in self.committees:
            self.committees[cid] = {
                "committee_id": cid,
                "assembly_id": assembly_id,
                "name_ar": name_ar,
                "name_lat": name_lat,
                "name_en": "",
                "type": spell.get("type") or "standing",
                "policy_domain": spell.get("category_ar", ""),
                "seats": "",
            }
        return cid

    # -- ingest -----------------------------------------------------------
    def ingest(self, doc: dict[str, Any]) -> None:
        source_id = doc["source_id"]
        retrieved = doc.get("retrieved_at", "")
        default_assembly = doc["assembly_id"]
        self.sources[source_id] = doc["source"]
        log(f"  ingesting {source_id}: {len(doc['records'])} records -> {default_assembly}")

        for rec in doc["records"]:
            assembly_id = rec.get("assembly_id") or default_assembly
            person_id = self.resolve_person(rec, source_id, assembly_id)

            # -- person attributes ---------------------------------------
            simple_fields = [
                "name_ar", "name_lat", "given_name_ar", "family_name_ar",
                "given_name_lat", "family_name_lat", "gender", "birth_date",
                "birth_date_precision", "birth_place_ar", "death_date",
                "death_date_precision", "marital_status", "n_children",
                "languages", "education_raw", "education_level", "occupation_raw",
                "occupation_sector", "biography_ar", "wikidata_qid",
            ]
            for field in simple_fields:
                val = rec.get(field)
                if val:
                    self._set_person_field(person_id, field, val, source_id)
                    if field in (rec.get("authoritative_fields") or []):
                        self._record_provenance("persons", person_id, field, source_id, val, retrieved)

            # Sources name the governorate explicitly only occasionally
            # ("dans le gouvernorat de Sidi Bouzid"). Where they give only a
            # locality, fall back to matching it against the governorate names:
            # many Tunisian governorates are named after their capital, so a
            # birthplace of "Monastir" identifies the governorate. Localities
            # that are not governorate capitals simply stay unresolved.
            gov = (
                self.resolve_governorate(rec.get("birth_governorate_name", ""))
                or self.resolve_governorate(rec.get("birth_place_ar", ""))
            )
            if gov:
                self._set_person_field(person_id, "birth_governorate_id", gov, source_id)

            # -- mandate --------------------------------------------------
            m = rec.get("mandate") or {}
            if m:
                constituency_id = self.resolve_constituency(
                    m.get("constituency_name_ar", ""),
                    m.get("constituency_name_lat", ""),
                    assembly_id,
                    m.get("governorate_name_ar", ""),
                    bool(m.get("is_diaspora_seat")),
                )
                gov_id = ""
                if constituency_id:
                    gov_id = self.constituencies[constituency_id].get("governorate_id", "")
                mandate_id = deterministic_id("TNM", person_id, assembly_id, m.get("start_date", ""))
                self.mandates.append({
                    "mandate_id": mandate_id,
                    "person_id": person_id,
                    "assembly_id": assembly_id,
                    "start_date": m.get("start_date", ""),
                    "end_date": m.get("end_date", ""),
                    "entry_mode": m.get("entry_mode", "unknown"),
                    "exit_mode": m.get("exit_mode", "unknown"),
                    "constituency_id": constituency_id,
                    "governorate_id": gov_id,
                    "electoral_list_ar": m.get("electoral_list_ar", ""),
                    "electoral_list_lat": m.get("electoral_list_lat", ""),
                    "party_id_at_election": self.resolve_party(
                        m.get("party_name_ar", ""), m.get("party_name_lat", "")
                    ),
                    "seat_number": m.get("seat_number", ""),
                    "is_diaspora_seat": "true" if m.get("is_diaspora_seat") else "false",
                    "election_date": m.get("election_date", ""),
                    "source_ids": source_id,
                })
                self._record_provenance("mandates", mandate_id, "assembly_id", source_id,
                                        assembly_id, retrieved)

            # -- spells ---------------------------------------------------
            for spell in rec.get("blocs") or []:
                bloc_id = self.resolve_bloc(spell, assembly_id)
                self.bloc_memberships.append({
                    "bloc_membership_id": deterministic_id(
                        "BLM", person_id, bloc_id, spell.get("start_date", "")),
                    "person_id": person_id,
                    "bloc_id": bloc_id,
                    "assembly_id": assembly_id,
                    "start_date": spell.get("start_date", ""),
                    "end_date": spell.get("end_date", ""),
                    "role": spell.get("role") or "unknown",
                    "is_founding_member": "",
                    "source_ids": source_id,
                })

            for spell in rec.get("committees") or []:
                committee_id = self.resolve_committee(spell, assembly_id)
                self.committee_memberships.append({
                    "committee_membership_id": deterministic_id(
                        "CMM", person_id, committee_id, spell.get("start_date", "")),
                    "person_id": person_id,
                    "committee_id": committee_id,
                    "assembly_id": assembly_id,
                    "role": spell.get("role") or "member",
                    "start_date": spell.get("start_date", ""),
                    "end_date": spell.get("end_date", ""),
                    "source_ids": source_id,
                })

            for spell in rec.get("offices") or []:
                self.offices.append({
                    "office_id": deterministic_id(
                        "OFC", person_id, assembly_id, spell.get("office", ""),
                        spell.get("start_date", "")),
                    "person_id": person_id,
                    "assembly_id": assembly_id,
                    "office": spell.get("office") or "unknown",
                    "office_label_ar": spell.get("office_label_ar", ""),
                    "start_date": spell.get("start_date", ""),
                    "end_date": spell.get("end_date", ""),
                    "source_ids": source_id,
                })

            for i, spell in enumerate(rec.get("careers") or [], start=1):
                self.careers.append({
                    "career_id": deterministic_id(
                        "CAR", person_id, str(i), spell.get("role_raw", "")),
                    "person_id": person_id,
                    "seq": i,
                    "role_raw": spell.get("role_raw", ""),
                    "role_en": spell.get("role_en", ""),
                    "organisation_raw": spell.get("organisation_raw", ""),
                    "organisation_id": (
                        deterministic_id("ORG", self._norm_place(spell["organisation_raw"]))
                        if spell.get("organisation_raw") else ""
                    ),
                    "sector": spell.get("sector") or "unknown",
                    "is_ministerial": "true" if spell.get("is_ministerial") else "",
                    "start_date": spell.get("start_date", ""),
                    "end_date": spell.get("end_date", ""),
                    "date_precision": spell.get("date_precision", "unknown"),
                    "relative_to_mandate": spell.get("relative_to_mandate", "unknown"),
                    "extraction_method": spell.get("extraction_method", "source_structured"),
                    "confidence": spell.get("confidence", "medium"),
                    "source_ids": source_id,
                })

            for spell in rec.get("party_affiliations") or []:
                party_id = self.resolve_party(spell.get("name_ar", ""), spell.get("name_lat", ""))
                if not party_id:
                    continue
                self.party_affiliations.append({
                    "affiliation_id": deterministic_id(
                        "AFF", person_id, party_id, spell.get("start_date", "")),
                    "person_id": person_id,
                    "party_id": party_id,
                    "start_date": spell.get("start_date", ""),
                    "end_date": spell.get("end_date", ""),
                    "role": spell.get("role", ""),
                    "source_ids": source_id,
                })

            part = rec.get("participation") or {}
            if part:
                key = (person_id, assembly_id)
                row = self.participation.setdefault(key, {
                    "person_id": person_id,
                    "assembly_id": assembly_id,
                    "plenary_attendance_rate": "",
                    "plenary_denominator": "",
                    "committee_attendance_rate": "",
                    "committee_denominator": "",
                    "vote_participation_rate": "",
                    "vote_denominator": "",
                    "vote_discipline_rate": "",
                    "n_written_questions": "",
                    "n_oral_questions": "",
                    "source_ids": source_id,
                })
                for field in ("plenary_attendance_rate", "committee_attendance_rate",
                              "vote_participation_rate", "vote_discipline_rate",
                              "n_written_questions", "n_oral_questions"):
                    if part.get(field) not in (None, ""):
                        row[field] = part[field]

    # -- pre-2011 presiding officers --------------------------------------
    def add_presiding_officers(self) -> None:
        """Seed persons and offices for the eight speakers of 1959-2011.

        These are the only individuals recoverable for the single-party era
        without archival work. They get an office spell, and a mandate in every
        chamber their tenure overlapped — holding the chair entails holding a
        seat — with entry_mode 'unknown' because the source does not say how
        they were returned.
        """
        source_id = "REFERENCE"
        self.sources[source_id] = {
            "source_id": source_id,
            "name": "Curated institutional frame and pre-2011 presiding officers",
            "publisher": "This repository",
            "url": "",
            "access_method": "Hand-curated in src/parliamentarians_tn/reference.py",
            "coverage": "All 19 chamber-terms 1956-present; governorates; party register; speakers 1959-2011",
            "language": "ar; fr; en",
            "licence": "MIT (as the repository)",
            "first_retrieved": "",
            "last_retrieved": "",
            "reliability_notes": (
                "Compiled from constitutional texts, electoral laws and the "
                "historiography, with seat counts cross-checked against reported "
                "election results. Rows carrying unverified values say so in `notes`."
            ),
        }
        lower = [
            a for a in self.assemblies.values()
            if a["type"] == "ordinary_lower" and a["start_date"] and a["start_date"] < "2011"
        ]
        for name_ar, name_lat, y0, y1, note in PRESIDING_OFFICERS_PRE2011:
            rec = {"source_key": f"speaker-{name_lat}", "name_ar": name_ar, "name_lat": name_lat}
            # Tenures are known to the year only, and a speaker's last year is
            # always the next speaker's first year, so a boundary-inclusive
            # overlap would credit each speaker with the chamber their successor
            # actually presided over. Strict inequalities on the year avoid that:
            # a chamber counts only if it opened before the tenure's final year
            # and closed after its first.
            def _overlaps(a: dict[str, str]) -> bool:
                start_year = int(a["start_date"][:4])
                end_year = int(a["end_date"][:4]) if a["end_date"] else 9999
                return start_year < y1 and end_year > y0

            overlapping = sorted(
                (a for a in lower if _overlaps(a)),
                key=lambda a: a["start_date"],
            )
            home = overlapping[0]["assembly_id"] if overlapping else "NA-1959"
            person_id = self.resolve_person(rec, source_id, home)
            self._set_person_field(person_id, "name_ar", name_ar, source_id)
            self._set_person_field(person_id, "name_lat", name_lat, source_id)

            self.offices.append({
                "office_id": deterministic_id("OFC", person_id, "speaker", str(y0)),
                "person_id": person_id,
                "assembly_id": home,
                "office": "speaker",
                "office_label_ar": "رئيس مجلس النواب",
                "start_date": f"{y0}-01-01",
                "end_date": f"{y1}-12-31",
                "source_ids": source_id,
            })
            for a in overlapping:
                mandate_id = deterministic_id("TNM", person_id, a["assembly_id"], a["start_date"])
                self.mandates.append({
                    "mandate_id": mandate_id,
                    "person_id": person_id,
                    "assembly_id": a["assembly_id"],
                    "start_date": a["start_date"],
                    "end_date": a["end_date"],
                    "entry_mode": "unknown",
                    "exit_mode": "unknown",
                    "constituency_id": "",
                    "governorate_id": "",
                    "electoral_list_ar": "",
                    "electoral_list_lat": "",
                    "party_id_at_election": (
                        "PTY-PSD" if a["start_date"] < "1988" else "PTY-RCD"
                    ),
                    "seat_number": "",
                    "is_diaspora_seat": "false",
                    "election_date": "",
                    "source_ids": source_id,
                })
        log(f"  added {len(PRESIDING_OFFICERS_PRE2011)} pre-2011 presiding officers")

    # -- output -----------------------------------------------------------
    def person_rows(self) -> list[dict[str, Any]]:
        mandates_by_person: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in self.mandates:
            mandates_by_person[m["person_id"]].append(m)

        rows = []
        for person_id in sorted({x["person_id"] for x in self.xref}):
            fields = {k: v[1] for k, v in self.person_fields[person_id].items()}
            name_ar = fields.get("name_ar", "")
            name_lat = fields.get("name_lat", "")
            if not name_lat and name_ar:
                # Machine romanisation, flagged as such in the codebook.
                name_lat = romanize_arabic(name_ar)
            mine = mandates_by_person.get(person_id, [])
            starts = sorted(m["start_date"] for m in mine if m["start_date"])
            row = {c.name: "" for c in schema.PERSONS.columns}
            row.update({
                "person_id": person_id,
                "name_ar": name_ar,
                "name_lat": name_lat,
                "name_normalised": normalize_arabic(name_ar),
                "first_mandate_start": starts[0] if starts else "",
                "n_mandates": len({m["assembly_id"] for m in mine}),
            })
            for key, val in fields.items():
                if key in row:
                    row[key] = val
            rows.append(row)
        return rows

    def write_all(self) -> None:
        write_table(schema.ASSEMBLIES, list(self.assemblies.values()))
        write_table(schema.GOVERNORATES, self.governorates)
        write_table(schema.CONSTITUENCIES, sorted(
            self.constituencies.values(), key=lambda r: (r["assembly_id"], r["name_ar"])))
        write_table(schema.PARTIES, sorted(self.parties.values(), key=lambda r: r["party_id"]))
        write_table(schema.PERSONS, self.person_rows())
        write_table(schema.MANDATES, sorted(
            self.mandates, key=lambda r: (r["assembly_id"], r["person_id"])))
        write_table(schema.PARTY_AFFILIATIONS, self.party_affiliations)
        write_table(schema.BLOCS, sorted(self.blocs.values(), key=lambda r: r["bloc_id"]))
        write_table(schema.BLOC_MEMBERSHIPS, self.bloc_memberships)
        write_table(schema.COMMITTEES, sorted(
            self.committees.values(), key=lambda r: r["committee_id"]))
        write_table(schema.COMMITTEE_MEMBERSHIPS, self.committee_memberships)
        write_table(schema.OFFICES, self.offices)
        write_table(schema.CAREERS, self.careers)
        write_table(schema.PARTICIPATION, list(self.participation.values()))
        write_table(schema.PERSON_XREF, sorted(
            self.xref, key=lambda r: (r["person_id"], r["source_id"])))
        write_table(schema.SOURCES, [self.sources[k] for k in sorted(self.sources)])
        write_table(schema.PROVENANCE, self.provenance)

        if self.match_review:
            write_rows(
                PROCESSED / "_match_review.csv",
                list(self.match_review[0].keys()),
                self.match_review,
            )
        log(f"cross-source person merges needing review: {len(self.match_review)}")


def build() -> Builder:
    docs = all_staging()
    if not docs:
        raise SystemExit(
            "no staging documents found in data/raw. Run the collectors first "
            "(see `make collect` or python -m parliamentarians_tn.collect.<source>)."
        )
    b = Builder()
    # Ingest in source-priority order so that the authoritative naming of a
    # person is established before a weaker source tries to match against it.
    docs.sort(key=lambda d: _priority(d["source_id"]))
    for doc in docs:
        b.ingest(doc)
    b.add_presiding_officers()
    b.write_all()
    return b


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    b = build()
    log(f"built {len(b.person_rows())} persons, {len(b.mandates)} mandates")


if __name__ == "__main__":
    main()
