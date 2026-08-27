"""The staging contract shared by every collector.

Collectors do not write the final tables. They emit a *staging document* — one
JSON file per source — in the common shape defined here, and
:mod:`parliamentarians_tn.build` merges those documents, resolves entities to
stable IDs and writes the relational CSVs.

Keeping the split means a collector only has to understand its own upstream
quirks, while record linkage, ID minting and provenance live in exactly one
place. Adding a source is then a self-contained job: write a collector, emit
staging, and the rest of the pipeline absorbs it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..io import RAW, log, today


@dataclass
class PersonRecord:
    """One parliamentarian as seen by one source, for one assembly."""

    source_key: str  # primary key in the upstream system
    source_url: str = ""

    # -- identity -------------------------------------------------------
    name_ar: str = ""
    name_lat: str = ""
    given_name_ar: str = ""
    family_name_ar: str = ""
    given_name_lat: str = ""
    family_name_lat: str = ""
    gender: str = ""
    birth_date: str = ""
    birth_date_precision: str = ""
    birth_place_ar: str = ""
    birth_governorate_name: str = ""
    death_date: str = ""
    death_date_precision: str = ""
    marital_status: str = ""
    n_children: str = ""
    languages: str = ""
    education_raw: str = ""
    education_level: str = ""
    occupation_raw: str = ""
    occupation_sector: str = ""
    biography_ar: str = ""
    wikidata_qid: str = ""

    # -- mandate --------------------------------------------------------
    mandate: dict[str, Any] = field(default_factory=dict)

    # -- spells ---------------------------------------------------------
    blocs: list[dict[str, Any]] = field(default_factory=list)
    committees: list[dict[str, Any]] = field(default_factory=list)
    offices: list[dict[str, Any]] = field(default_factory=list)
    careers: list[dict[str, Any]] = field(default_factory=list)
    party_affiliations: list[dict[str, Any]] = field(default_factory=list)
    participation: dict[str, Any] = field(default_factory=dict)

    # -- provenance -----------------------------------------------------
    # Fields this source is authoritative for. build.py writes one provenance
    # row per (record, field) listed here. Collectors that leave this empty get
    # provenance inferred from the non-empty identity fields.
    authoritative_fields: list[str] = field(default_factory=list)

    def populated_person_fields(self) -> list[str]:
        skip = {"source_key", "source_url", "mandate", "blocs", "committees",
                "offices", "careers", "party_affiliations", "participation",
                "authoritative_fields"}
        return [k for k, v in asdict(self).items() if k not in skip and v]


@dataclass
class StagingDoc:
    """Everything one collector learned in one run."""

    source_id: str
    source: dict[str, Any]  # a row for the `sources` table
    assembly_id: str  # default assembly for records lacking their own
    records: list[PersonRecord] = field(default_factory=list)
    assembly_updates: dict[str, Any] = field(default_factory=dict)
    constituencies: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    retrieved_at: str = ""

    def path(self) -> Path:
        return RAW / f"staging_{self.source_id.lower()}.json"

    def save(self) -> Path:
        self.retrieved_at = self.retrieved_at or today()
        payload = {
            "source_id": self.source_id,
            "source": self.source,
            "assembly_id": self.assembly_id,
            "assembly_updates": self.assembly_updates,
            "constituencies": self.constituencies,
            "notes": self.notes,
            "retrieved_at": self.retrieved_at,
            "records": [asdict(r) for r in self.records],
        }
        p = self.path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"staged {len(self.records)} records -> {p.name}")
        return p


def load_staging(source_id: str) -> dict[str, Any] | None:
    p = RAW / f"staging_{source_id.lower()}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def all_staging() -> list[dict[str, Any]]:
    """Load every staging document present, in a deterministic order.

    Order matters: later documents may enrich a person first seen in an earlier
    one, and build.py treats earlier sources as having naming priority. The sort
    is by filename so the build is reproducible.
    """
    docs = []
    for p in sorted(RAW.glob("staging_*.json")):
        docs.append(json.loads(p.read_text(encoding="utf-8")))
    return docs
