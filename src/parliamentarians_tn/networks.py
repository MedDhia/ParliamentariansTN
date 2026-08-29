"""Derive network files from the relational tables.

The relational tables are the dataset; these files are a convenience layer for
network analysis. Two shapes are written for every relational layer:

* **Bipartite incidence lists** (``bipartite_person_*.csv``) — person-to-affiliation
  edges, unprojected. These are the honest representation, and researchers who
  care about projection choices (weighting by group size, Newman weighting,
  backboning) should start here rather than from a projection someone else made.
* **One-mode projections** (``edges_*.csv``) — person-to-person edges with a
  weight, for immediate use in igraph, networkx, Gephi or Cytoscape.

Three rules govern every projection here:

1. **Edges never cross assemblies.** Two deputies who sat on the finance
   committee in 2011 and 2023 respectively did not co-serve. Every projection is
   computed within a chamber-term, and ``assembly_id`` is carried on each edge so
   that a pooled analysis is a deliberate choice rather than an accident.
2. **Spells must overlap in time.** Where both memberships carry dates, an edge
   is created only if the intervals actually intersect: someone who left a
   committee in 2020 never sat with someone who joined in 2021. Where a source
   publishes no dates, membership is assumed to span the assembly, and the edge
   is flagged ``dates_assumed=true`` so this assumption can be filtered out.
3. **Group size is recorded, not hidden.** A 53-member bloc generates 1,378
   dyads and will dominate any unweighted centrality measure. Each edge carries
   the size of the group that produced it, and ``weight_newman`` gives the
   standard 1/(n-1) correction.

Run ``python -m parliamentarians_tn.networks`` after a build.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from itertools import combinations
from typing import Any, Iterable

from .io import NETWORKS, RAW, log, read_table, write_rows

EDGE_FIELDS = [
    "source", "target", "layer", "assembly_id", "weight", "weight_newman",
    "group_ids", "group_names", "group_size", "shared_count",
    "overlap_start", "overlap_end", "dates_assumed",
]


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> tuple[bool, str, str]:
    """Do two date intervals intersect? Empty bounds are treated as open.

    Returns (overlaps, overlap_start, overlap_end).
    """
    lo = max(a_start or "0000-00-00", b_start or "0000-00-00")
    hi_candidates = [x for x in (a_end, b_end) if x]
    hi = min(hi_candidates) if hi_candidates else ""
    if hi and lo > hi:
        return False, "", ""
    return True, ("" if lo == "0000-00-00" else lo), hi


def _project(
    layer: str,
    memberships: Iterable[dict[str, Any]],
    group_key: str,
    group_names: dict[str, str],
) -> list[dict[str, Any]]:
    """Project a bipartite membership list onto person-person edges.

    ``memberships`` rows need: person_id, assembly_id, the group key, and
    start_date/end_date.
    """
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in memberships:
        gid = row.get(group_key) or ""
        if not gid or not row.get("person_id"):
            continue
        by_group[(row.get("assembly_id", ""), gid)].append(row)

    # dyad -> accumulated evidence
    acc: dict[tuple[str, str, str], dict[str, Any]] = {}
    group_sizes: dict[tuple[str, str], int] = {k: len(v) for k, v in by_group.items()}

    for (assembly_id, gid), members in by_group.items():
        size = len(members)
        if size < 2:
            continue
        for a, b in combinations(sorted(members, key=lambda r: r["person_id"]), 2):
            if a["person_id"] == b["person_id"]:
                continue
            ok, ov_start, ov_end = _overlaps(
                a.get("start_date", ""), a.get("end_date", ""),
                b.get("start_date", ""), b.get("end_date", ""),
            )
            if not ok:
                continue
            assumed = not (a.get("start_date") and b.get("start_date"))
            key = (assembly_id, a["person_id"], b["person_id"])
            entry = acc.get(key)
            if entry is None:
                entry = acc[key] = {
                    "source": a["person_id"],
                    "target": b["person_id"],
                    "layer": layer,
                    "assembly_id": assembly_id,
                    "weight": 0,
                    "weight_newman": 0.0,
                    "group_ids": [],
                    "group_names": [],
                    "group_size": [],
                    "shared_count": 0,
                    "overlap_start": ov_start,
                    "overlap_end": ov_end,
                    "dates_assumed": assumed,
                }
            entry["weight"] += 1
            entry["shared_count"] += 1
            entry["group_ids"].append(gid)
            entry["group_names"].append(group_names.get(gid, ""))
            entry["group_size"].append(size)
            # Newman's correction: a tie formed inside a large group carries
            # less information than one formed inside a small group.
            entry["weight_newman"] += 1.0 / (size - 1)
            entry["dates_assumed"] = entry["dates_assumed"] or assumed
            if ov_start and (not entry["overlap_start"] or ov_start < entry["overlap_start"]):
                entry["overlap_start"] = ov_start

    rows = []
    for entry in acc.values():
        rows.append({
            **entry,
            "group_ids": ";".join(entry["group_ids"]),
            "group_names": ";".join(x for x in entry["group_names"] if x),
            "group_size": ";".join(str(x) for x in entry["group_size"]),
            "weight_newman": round(entry["weight_newman"], 6),
            "dates_assumed": "true" if entry["dates_assumed"] else "false",
        })
    rows.sort(key=lambda r: (r["assembly_id"], -r["weight"], r["source"], r["target"]))
    return rows


def build_nodes() -> list[dict[str, Any]]:
    """One row per person, with the attributes a network analyst needs to hand."""
    persons = read_table("persons")
    mandates = read_table("mandates")
    parties = {p["party_id"]: p for p in read_table("parties")}
    governorates = {g["governorate_id"]: g for g in read_table("governorates")}
    constituencies = {c["constituency_id"]: c for c in read_table("constituencies")}
    participation = {(p["person_id"], p["assembly_id"]): p for p in read_table("participation")}
    careers = defaultdict(list)
    for c in read_table("careers"):
        careers[c["person_id"]].append(c)

    by_person = defaultdict(list)
    for m in mandates:
        by_person[m["person_id"]].append(m)

    rows = []
    for p in persons:
        mine = sorted(by_person.get(p["person_id"], []), key=lambda m: m.get("start_date") or "")
        last = mine[-1] if mine else {}
        first = mine[0] if mine else {}
        gov_id = ""
        for m in reversed(mine):
            gov_id = m.get("governorate_id") or ""
            if gov_id:
                break
        gov = governorates.get(gov_id, {})
        party = parties.get(last.get("party_id_at_election", ""), {})
        part = participation.get((p["person_id"], last.get("assembly_id", "")), {})
        sectors = sorted({c["sector"] for c in careers.get(p["person_id"], []) if c["sector"]})
        rows.append({
            "person_id": p["person_id"],
            "name_ar": p["name_ar"],
            "name_lat": p["name_lat"],
            "gender": p["gender"],
            "birth_year": (p["birth_date"] or "")[:4],
            "birth_date_precision": p["birth_date_precision"],
            "birth_governorate_id": p["birth_governorate_id"],
            "n_mandates": p["n_mandates"],
            "first_assembly_id": first.get("assembly_id", ""),
            "last_assembly_id": last.get("assembly_id", ""),
            "first_mandate_start": p["first_mandate_start"],
            "constituency_id": last.get("constituency_id", ""),
            "constituency_name_ar": constituencies.get(last.get("constituency_id", ""), {}).get("name_ar", ""),
            "governorate_id": gov_id,
            "governorate_name_lat": gov.get("name_lat", ""),
            "region": gov.get("region", ""),
            "littoral": gov.get("littoral", ""),
            "party_id_last": last.get("party_id_at_election", ""),
            "party_family_last": party.get("family", ""),
            "occupation_raw": p["occupation_raw"],
            "career_sectors": ";".join(sectors),
            "vote_participation_rate": part.get("vote_participation_rate", ""),
            "plenary_attendance_rate": part.get("plenary_attendance_rate", ""),
            "n_written_questions": part.get("n_written_questions", ""),
        })
    rows.sort(key=lambda r: r["person_id"])
    return rows


def build_cosignature_edges() -> list[dict[str, Any]]:
    """Co-signature ties from jointly submitted written questions (ARP-2023).

    Read from the ARP staging document rather than the processed tables: the
    question corpus is behavioural data about documents, not about mandates, so
    it has no home in the relational schema. Upstream deputy keys are mapped
    through person_xref.
    """
    path = RAW / "staging_arp_odoo.json"
    if not path.exists():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    cosigs = (doc.get("assembly_updates") or {}).get("written_question_cosignatures") or []
    if not cosigs:
        return []

    key_to_person = {
        x["source_key"]: x["person_id"]
        for x in read_table("person_xref")
        if x["source_id"] == "ARP_ODOO"
    }

    acc: dict[tuple[str, str], dict[str, Any]] = {}
    unmapped = set()
    for q in cosigs:
        people = []
        for key in q.get("signer_source_keys", []):
            pid = key_to_person.get(str(key))
            if pid:
                people.append(pid)
            else:
                unmapped.add(str(key))
        for a, b in combinations(sorted(set(people)), 2):
            entry = acc.setdefault((a, b), {
                "source": a, "target": b, "layer": "written_question_cosignature",
                "assembly_id": "ARP-2023", "weight": 0, "weight_newman": 0.0,
                "group_ids": [], "group_names": "", "group_size": [],
                "shared_count": 0, "overlap_start": "", "overlap_end": "",
                "dates_assumed": "false",
            })
            entry["weight"] += 1
            entry["shared_count"] += 1
            entry["group_ids"].append(q["question_id"])
            entry["group_size"].append(len(people))
            entry["weight_newman"] += 1.0 / max(1, len(people) - 1)
            if q.get("date"):
                if not entry["overlap_start"] or q["date"] < entry["overlap_start"]:
                    entry["overlap_start"] = q["date"]
                if not entry["overlap_end"] or q["date"] > entry["overlap_end"]:
                    entry["overlap_end"] = q["date"]

    if unmapped:
        log(f"  cosignature: {len(unmapped)} signer key(s) not resolvable to a person "
            "(deputies who left the chamber are absent from the public roster)")

    rows = []
    for entry in acc.values():
        rows.append({
            **entry,
            "group_ids": ";".join(entry["group_ids"]),
            "group_size": ";".join(str(x) for x in entry["group_size"]),
            "weight_newman": round(entry["weight_newman"], 6),
        })
    rows.sort(key=lambda r: (-r["weight"], r["source"], r["target"]))
    return rows


def build_amendment_edges() -> list[dict[str, Any]]:
    """Co-sponsorship ties from constitutional amendments (NCA-2011).

    The constituent assembly's counterpart to the 2023 chamber's written-question
    co-signatures, and the more consequential of the two: these are the ties
    formed while drafting the constitution itself. Built from the processed
    tables rather than staging, because amendments *do* have a home in the
    schema.

    Newman-corrected as elsewhere: an amendment tabled by nineteen members
    manufactures 171 dyads, and counting those equally with a two-member
    amendment would let a handful of mass filings dominate every centrality.
    """
    sponsorships = list(read_table("amendment_sponsorships"))
    if not sponsorships:
        return []
    by_amendment: dict[str, list[str]] = defaultdict(list)
    assembly_of: dict[str, str] = {}
    for row in sponsorships:
        by_amendment[row["amendment_id"]].append(row["person_id"])
        assembly_of[row["amendment_id"]] = row["assembly_id"]

    acc: dict[tuple[str, str], dict[str, Any]] = {}
    for amendment_id, people in by_amendment.items():
        people = sorted(set(people))
        if len(people) < 2:
            continue
        for a, b in combinations(people, 2):
            entry = acc.setdefault((a, b), {
                "source": a, "target": b, "layer": "amendment_cosponsorship",
                "assembly_id": assembly_of[amendment_id], "weight": 0,
                "weight_newman": 0.0, "group_ids": [], "group_names": "",
                "group_size": [], "shared_count": 0, "overlap_start": "",
                "overlap_end": "", "dates_assumed": "false",
            })
            entry["weight"] += 1
            entry["shared_count"] += 1
            entry["group_ids"].append(amendment_id)
            entry["group_size"].append(len(people))
            entry["weight_newman"] += 1.0 / (len(people) - 1)

    out = []
    for entry in acc.values():
        out.append({
            **entry,
            "group_ids": ";".join(entry["group_ids"][:20]),
            "group_size": ";".join(str(s) for s in entry["group_size"][:20]),
            "weight_newman": round(entry["weight_newman"], 6),
        })
    return sorted(out, key=lambda r: (r["source"], r["target"]))


def build_vote_agreement_edges(
    min_cast: int = 40, min_minority: float = 0.025, min_shared: int = 30,
) -> list[dict[str, Any]]:
    """Agreement between every pair of members on contested divisions (NCA-2011).

    The only *revealed* tie layer in the dataset. Committee co-membership is
    assigned and co-sponsorship is chosen; this is neither — two members are
    tied to the degree that they voted the same way, whether or not they meant
    to be associated. That makes it the layer to use for polarisation, and the
    one to be most careful with, because a tie here is a correlation and not an
    act.

    ``weight`` is the share of jointly-cast divisions on which the pair voted
    the same way, on **contested divisions only**. Near-unanimous divisions are
    excluded first (the same filter figure 21 uses): agreement on a vote nobody
    opposed is agreement with the whole chamber, and leaving those in pushes
    every pair toward 0.84 and compresses the differences that matter. On the
    993 contested divisions the same measure spreads from 0.2 to 1.0.

    Abstention and absence are not agreement or disagreement — they are absence
    of a position — so a division counts for a pair only where *both* cast pour
    or contre. ``shared_count`` records how many divisions that was, and pairs
    below ``min_shared`` are dropped rather than scored on a handful of votes.

    Unlike every other layer here this one is near-complete: almost every pair
    of members has a value, so it is a weighted graph rather than a sparse one.
    Threshold it before running anything that assumes sparsity, and remember
    that the threshold is an analytical choice the file does not make for you.
    """
    positions: dict[str, dict[str, int]] = defaultdict(dict)
    assemblies: dict[str, str] = {}
    for row in read_table("vote_positions"):
        if row["position"] == "pour":
            positions[row["person_id"]][row["vote_id"]] = 1
        elif row["position"] == "contre":
            positions[row["person_id"]][row["vote_id"]] = -1
        else:
            continue
        assemblies[row["vote_id"]] = row["assembly_id"]
    if not positions:
        return []

    votes = sorted({v for p in positions.values() for v in p})
    index = {v: j for j, v in enumerate(votes)}
    people = sorted(positions)
    matrix = [[0] * len(votes) for _ in people]
    for i, person in enumerate(people):
        for vote_id, value in positions[person].items():
            matrix[i][index[vote_id]] = value

    # Contested divisions only. Done with plain loops so the network layer keeps
    # the pipeline's no-scientific-stack promise; it is 217 x 1,724 and runs in
    # about a second.
    keep = []
    for j in range(len(votes)):
        yes = sum(1 for i in range(len(people)) if matrix[i][j] == 1)
        no = sum(1 for i in range(len(people)) if matrix[i][j] == -1)
        cast = yes + no
        if cast >= min_cast and min(yes, no) / cast >= min_minority:
            keep.append(j)

    out: list[dict[str, Any]] = []
    for a in range(len(people)):
        row_a = matrix[a]
        for b in range(a + 1, len(people)):
            row_b = matrix[b]
            shared = agreed = 0
            for j in keep:
                va, vb = row_a[j], row_b[j]
                if va and vb:
                    shared += 1
                    agreed += va == vb
            if shared < min_shared:
                continue
            out.append({
                "source": people[a], "target": people[b],
                "layer": "vote_agreement",
                "assembly_id": assemblies[votes[keep[0]]] if keep else "",
                "weight": round(agreed / shared, 6),
                "weight_newman": "", "group_ids": "", "group_names": "",
                "group_size": "", "shared_count": shared,
                "overlap_start": "", "overlap_end": "", "dates_assumed": "false",
            })
    return sorted(out, key=lambda r: (r["source"], r["target"]))


def build_shared_constituency_edges() -> list[dict[str, Any]]:
    """Ties between members returned by the same constituency in the same chamber.

    Substantively this is a co-representation tie, and it only exists where
    constituencies are multi-member: under the 2011-2019 list system a
    constituency returned several deputies, whereas the 2023 chamber is
    single-member, so this layer is empty for ARP-2023 by construction, not by
    omission.
    """
    mandates = read_table("mandates")
    constituencies = {c["constituency_id"]: c for c in read_table("constituencies")}
    rows = [
        {
            "person_id": m["person_id"],
            "assembly_id": m["assembly_id"],
            "constituency_id": m["constituency_id"],
            "start_date": m.get("start_date", ""),
            "end_date": m.get("end_date", ""),
        }
        for m in mandates if m.get("constituency_id")
    ]
    names = {cid: c["name_ar"] for cid, c in constituencies.items()}
    return _project("shared_constituency", rows, "constituency_id", names)


def build_career_edges() -> list[dict[str, Any]]:
    """Ties between members who passed through the same organisation.

    This is the elite-circulation layer. It is built from the ``careers`` table,
    whose rows are extracted from narrative biographies, so edges here inherit
    that table's uncertainty: an organisation matched on a normalised name string
    may be two different bodies with similar names. Filter on the source
    ``careers.confidence`` column before drawing inferential conclusions.

    Note this layer is deliberately *not* restricted to a single assembly:
    sharing a trade union or a ministry twenty years apart is exactly the tie
    elite-circulation arguments are about. ``assembly_id`` is therefore empty.
    """
    careers = [c for c in read_table("careers") if c.get("organisation_id")]
    rows = [
        {
            "person_id": c["person_id"],
            "assembly_id": "",
            "organisation_id": c["organisation_id"],
            "start_date": c.get("start_date", ""),
            "end_date": c.get("end_date", ""),
        }
        for c in careers
    ]
    names = {c["organisation_id"]: c["organisation_raw"] for c in careers}
    return _project("shared_organisation", rows, "organisation_id", names)


def write_all() -> dict[str, int]:
    counts: dict[str, int] = {}

    nodes = build_nodes()
    write_rows(NETWORKS / "nodes.csv", list(nodes[0].keys()), nodes)
    counts["nodes"] = len(nodes)

    # -- bipartite incidence -------------------------------------------------
    committees = {c["committee_id"]: c for c in read_table("committees")}
    com_mem = read_table("committee_memberships")
    bip_com = [
        {
            "person_id": r["person_id"],
            "committee_id": r["committee_id"],
            "committee_name_ar": committees.get(r["committee_id"], {}).get("name_ar", ""),
            "committee_type": committees.get(r["committee_id"], {}).get("type", ""),
            "assembly_id": r["assembly_id"],
            "role": r["role"],
            "start_date": r.get("start_date", ""),
            "end_date": r.get("end_date", ""),
        }
        for r in com_mem
    ]
    write_rows(NETWORKS / "bipartite_person_committee.csv",
               list(bip_com[0].keys()) if bip_com else ["person_id", "committee_id"], bip_com)
    counts["bipartite_person_committee"] = len(bip_com)

    blocs = {b["bloc_id"]: b for b in read_table("blocs")}
    bloc_mem = read_table("bloc_memberships")
    bip_bloc = [
        {
            "person_id": r["person_id"],
            "bloc_id": r["bloc_id"],
            "bloc_name_ar": blocs.get(r["bloc_id"], {}).get("name_ar", ""),
            "assembly_id": r["assembly_id"],
            "role": r["role"],
            "start_date": r.get("start_date", ""),
            "end_date": r.get("end_date", ""),
        }
        for r in bloc_mem
    ]
    write_rows(NETWORKS / "bipartite_person_bloc.csv",
               list(bip_bloc[0].keys()) if bip_bloc else ["person_id", "bloc_id"], bip_bloc)
    counts["bipartite_person_bloc"] = len(bip_bloc)

    # -- projections ---------------------------------------------------------
    com_edges = _project(
        "committee_comembership", com_mem, "committee_id",
        {cid: c["name_ar"] for cid, c in committees.items()},
    )
    write_rows(NETWORKS / "edges_committee_comembership.csv", EDGE_FIELDS, com_edges)
    counts["edges_committee_comembership"] = len(com_edges)

    bloc_edges = _project(
        "bloc_comembership", bloc_mem, "bloc_id",
        {bid: b["name_ar"] for bid, b in blocs.items()},
    )
    write_rows(NETWORKS / "edges_bloc_comembership.csv", EDGE_FIELDS, bloc_edges)
    counts["edges_bloc_comembership"] = len(bloc_edges)

    circ_edges = build_shared_constituency_edges()
    write_rows(NETWORKS / "edges_shared_constituency.csv", EDGE_FIELDS, circ_edges)
    counts["edges_shared_constituency"] = len(circ_edges)

    career_edges = build_career_edges()
    write_rows(NETWORKS / "edges_shared_organisation.csv", EDGE_FIELDS, career_edges)
    counts["edges_shared_organisation"] = len(career_edges)

    cosig = build_cosignature_edges()
    write_rows(NETWORKS / "edges_question_cosignature.csv", EDGE_FIELDS, cosig)
    counts["edges_question_cosignature"] = len(cosig)

    amend = build_amendment_edges()
    write_rows(NETWORKS / "edges_amendment_cosponsorship.csv", EDGE_FIELDS, amend)
    counts["edges_amendment_cosponsorship"] = len(amend)

    agree = build_vote_agreement_edges()
    write_rows(NETWORKS / "edges_vote_agreement.csv", EDGE_FIELDS, agree)
    counts["edges_vote_agreement"] = len(agree)

    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args()
    counts = write_all()
    log("network files:")
    for name, n in counts.items():
        log(f"    {name:38s} {n:6d} rows")


if __name__ == "__main__":
    main()
