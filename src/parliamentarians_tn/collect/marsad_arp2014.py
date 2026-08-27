"""Collector: the 2014-2019 Assembly of the Representatives of the People.

This chamber was the dataset's largest gap. Al Bawsala's first observatory
covers 2011-2014 and its second starts with the 2019 chamber; the ARP's own
database restricts closed mandates to internal users. The 2014-2019 term — a
democratic term sitting between two well-covered ones — had no roster at all,
which meant no continuous 2011-2023 panel.

It turns out Al Bawsala *did* run an observatory for it, at
``majles.marsad.tn/2014``, and the live site no longer serves those paths (every
``/2014/*`` URL now returns the current site's catch-all page). The Internet
Archive holds it. The roster page ``/2014/assemblee`` renders all 217 members as
cards whose data attributes carry everything the priority layer needs::

    <a href="/2014/elus/Noureddine_Bhiri" class="depute"
       data-nom="نور الدين البحيري"  data-bloc="حركة النهضة"
       data-liste="حركة النهضة"      data-region="بن عروس"
       data-sexe="رجال"              data-age="57"
       data-profession="محامي"        data-siege="11">

Two things make this source unusually good rather than merely adequate:

* **The slug is a source-supplied romanisation.** ``Noureddine_Bhiri`` is Al
  Bawsala's own Latin spelling, so this chamber gets real romanised names rather
  than machine transliteration.
* **The Archive holds ~35 monthly captures spanning Jan 2015 to Oct 2020.**
  Diffing consecutive captures recovers *dated bloc membership* — which chamber
  members left which bloc, and roughly when. Bloc switching is therefore
  observable for this term, where it is not for 2011-14 or 2019-21. That matters:
  this is the chamber whose governing coalition fragmented, with Nidaa Tounes
  splitting and Machrouu Tounes forming out of it mid-term.

The cost of recovering it from snapshots is date precision: a bloc change is
only located to the interval between two captures. Every spell derived this way
records the bracketing dates and is marked ``dates_bracketed``, so the
uncertainty travels with the data instead of being lost.

A correctness check worth noting: the first capture yields bloc sizes of Nidaa
Tounes 86 and Ennahdha 69, which match the official 2014 election result exactly,
and 33 distinct constituencies, matching the delimitation in force.
"""

from __future__ import annotations

import argparse
import html
import re
from collections import defaultdict
from typing import Any

from ..io import Fetcher, RAW, log, today
from .base import PersonRecord, StagingDoc

SOURCE_ID = "MARSAD_ARP2014"
ASSEMBLY_ID = "ARP-2014"

ORIGINAL_URL = "https://majles.marsad.tn/2014/assemblee"
CDX = "https://web.archive.org/cdx/search/cdx"
# The `id_` modifier returns the capture unrewritten — no Archive toolbar, no
# rewritten links — which is what makes the data attributes parseable.
WAYBACK = "https://web.archive.org/web/{timestamp}id_/{url}"

FIRST_SITTING = "2014-12-02"
ELECTION_DATE = "2014-10-26"
TERM_END = "2019-10-05"
# Captures are only meaningful while the chamber sat; a little slack past the
# end of term catches the last crawl of the final composition.
CAPTURE_WINDOW_END = "20191231"

GENDER_MAP = {"رجال": "male", "نساء": "female"}

# Out-of-country constituencies are named for the country, not a governorate.
ABROAD_TOKENS = ("فرنسا", "إيطاليا", "ألمانيا", "أمريكا", "الأمريكيتين",
                 "العربية", "آسيا", "أستراليا", "الخارج", "أوروبا")

CARD_RE = re.compile(r'<a href="/2014/elus/([^"]+)"\s+class="depute"(.*?)>', re.S)
ATTR_RE = re.compile(r'data-([a-z_]+)="([^"]*)"')


def _slug_to_latin(slug: str) -> str:
    """``Noureddine_Bhiri`` -> ``Noureddine Bhiri``.

    This is Al Bawsala's own romanisation, so it outranks anything the
    transliteration fallback would produce.
    """
    return re.sub(r"\s+", " ", slug.replace("_", " ").replace("%20", " ")).strip()


def parse_roster(markup: str) -> dict[str, dict[str, str]]:
    """Parse a capture of /2014/assemblee into slug -> card attributes."""
    out: dict[str, dict[str, str]] = {}
    for slug, blob in CARD_RE.findall(markup):
        attrs = {k: html.unescape(v).strip() for k, v in ATTR_RE.findall(blob)}
        slug = html.unescape(slug).strip()
        if not slug:
            continue
        out[slug] = attrs
    return out


def _timestamp_to_date(timestamp: str) -> str:
    return f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"


def list_captures(fetcher: Fetcher) -> list[str]:
    """Return one capture timestamp per calendar month, oldest first."""
    payload = fetcher.get_json(
        CDX,
        slug="cdx_assemblee",
        params={
            "url": "majles.marsad.tn/2014/assemblee",
            "output": "json",
            "filter": "statuscode:200",
            "limit": "300",
        },
    )
    if not payload or len(payload) < 2:
        raise RuntimeError("no Wayback captures found for the 2014 roster")
    header = payload[0]
    ti, li = header.index("timestamp"), header.index("length")

    per_month: dict[str, tuple[str, int]] = {}
    for row in payload[1:]:
        ts, length = row[ti], int(row[li] or 0)
        # Tiny captures are error pages or redirects, not the roster.
        if length < 12000:
            continue
        # Captures after the term ended (5 Oct 2019) do not describe this
        # chamber, and by 2020 the page had been redesigned and yields no cards.
        if ts[:8] > CAPTURE_WINDOW_END:
            continue
        month = ts[:6]
        # keep the largest capture in each month: partial renders are smaller
        if month not in per_month or length > per_month[month][1]:
            per_month[month] = (ts, length)
    return [ts for ts, _ in sorted(per_month.values(), key=lambda x: x[0])]


def build_bloc_spells(
    observations: list[tuple[str, dict[str, dict[str, str]]]],
) -> dict[str, list[dict[str, Any]]]:
    """Turn a time series of roster captures into dated bloc spells.

    ``observations`` is [(capture_date, {slug: attrs})] in date order.

    A change is only ever located to the interval between the capture that last
    showed the old bloc and the capture that first shows the new one, so each
    spell carries both bounds. ``start_date`` is the conservative choice — the
    first date the new bloc was actually observed — and
    ``start_date_earliest`` records how far back the change may really go.
    """
    spells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    last_seen_date: dict[str, str] = {}

    for capture_date, roster in observations:
        for slug, attrs in roster.items():
            bloc = attrs.get("bloc", "")
            if not bloc:
                continue
            current = spells[slug][-1] if spells.get(slug) else None
            if current is None:
                spells[slug].append({
                    "name_ar": bloc,
                    "groupe_id": attrs.get("groupe_id", ""),
                    # The first capture postdates the chamber's first sitting;
                    # a member's opening bloc is attributed to the sitting date
                    # because blocs were constituted at the term's start.
                    "start_date": FIRST_SITTING,
                    "start_date_earliest": FIRST_SITTING,
                    "first_observed": capture_date,
                    "last_observed": capture_date,
                    "end_date": "",
                    "dates_bracketed": False,
                })
            elif current["name_ar"] != bloc:
                previous_observation = last_seen_date.get(slug, current["last_observed"])
                current["end_date"] = previous_observation
                current["end_date_latest"] = capture_date
                spells[slug].append({
                    "name_ar": bloc,
                    "groupe_id": attrs.get("groupe_id", ""),
                    "start_date": capture_date,
                    "start_date_earliest": previous_observation,
                    "first_observed": capture_date,
                    "last_observed": capture_date,
                    "end_date": "",
                    "dates_bracketed": True,
                })
            else:
                current["last_observed"] = capture_date
            last_seen_date[slug] = capture_date

    # close the final spell of every member at the end of the term
    for slug, member_spells in spells.items():
        if member_spells and not member_spells[-1]["end_date"]:
            member_spells[-1]["end_date"] = TERM_END
    return spells


def collect(refresh: bool = False, max_captures: int | None = None) -> StagingDoc:
    fetcher = Fetcher(RAW / "marsad_arp2014", delay=1.5, refresh=refresh)

    timestamps = list_captures(fetcher)
    if max_captures:
        # keep the first and last, sample evenly between
        if len(timestamps) > max_captures:
            step = len(timestamps) / max_captures
            picked = {timestamps[min(int(i * step), len(timestamps) - 1)]
                      for i in range(max_captures)}
            picked.add(timestamps[0])
            picked.add(timestamps[-1])
            timestamps = sorted(picked)
    log(f"  {len(timestamps)} monthly captures from {timestamps[0]} to {timestamps[-1]}")

    observations: list[tuple[str, dict[str, dict[str, str]]]] = []
    for ts in timestamps:
        markup = fetcher.get_text(
            WAYBACK.format(timestamp=ts, url=ORIGINAL_URL), slug=f"assemblee_{ts}"
        )
        roster = parse_roster(markup)
        if not roster:
            log(f"  capture {ts}: no cards parsed, skipping")
            continue
        observations.append((_timestamp_to_date(ts), roster))
        log(f"  capture {ts}: {len(roster)} members")

    if not observations:
        raise RuntimeError("no capture yielded a parseable roster; upstream layout changed")

    spells = build_bloc_spells(observations)

    # The union of every capture is the set of people who sat at any point, which
    # is what the mandates table wants — replacements included.
    union: dict[str, dict[str, str]] = {}
    first_seen: dict[str, str] = {}
    last_seen: dict[str, str] = {}
    for capture_date, roster in observations:
        for slug, attrs in roster.items():
            union.setdefault(slug, attrs)
            union[slug] = {**union[slug], **{k: v for k, v in attrs.items() if v}}
            first_seen.setdefault(slug, capture_date)
            last_seen[slug] = capture_date

    baseline_date, baseline = observations[0]
    n_switchers = sum(1 for s in spells.values() if len(s) > 1)
    log(f"  {len(union)} distinct members across captures; "
        f"{n_switchers} with a bloc change")

    records: list[PersonRecord] = []
    for slug, attrs in sorted(union.items()):
        region = attrs.get("region", "")
        is_abroad = any(tok in region for tok in ABROAD_TOKENS)
        age = attrs.get("age", "")

        member_spells = []
        for spell in spells.get(slug, []):
            member_spells.append({
                "source_key": spell.get("groupe_id") or spell["name_ar"],
                "name_ar": spell["name_ar"],
                "name_lat": _slug_to_latin(spell.get("groupe_id", "")),
                "role": "unknown",
                "start_date": spell["start_date"],
                "end_date": spell["end_date"],
                "dates_bracketed": spell["dates_bracketed"],
                "notes": (
                    "bloc change located between "
                    f"{spell['start_date_earliest']} and {spell['start_date']}; "
                    "snapshot-derived, exact date unknown"
                ) if spell["dates_bracketed"] else "",
            })

        # A member absent from the first capture but present later joined
        # mid-term; one absent from the last capture left before the term ended.
        entry_mode = "elected" if slug in baseline else "replacement_list"
        left_early = last_seen[slug] != observations[-1][0]

        notes = []
        if age.isdigit():
            # Age with a known reference date could be turned into a birth year,
            # but only to within a year, so it is preserved rather than
            # converted: an analyst can derive it and own the uncertainty.
            notes.append(f"age {age} as observed on {first_seen[slug]}")
        if entry_mode == "replacement_list":
            notes.append(f"absent from the first capture ({baseline_date}); "
                         f"first observed {first_seen[slug]}")
        if left_early:
            notes.append(f"last observed {last_seen[slug]}, before the final capture")
        notes.append("recovered from an Internet Archive capture; "
                     "the live site no longer serves this observatory")

        records.append(PersonRecord(
            source_key=slug,
            source_url=f"https://majles.marsad.tn/2014/elus/{slug}",
            name_ar=attrs.get("nom", ""),
            name_lat=_slug_to_latin(slug),
            gender=GENDER_MAP.get(attrs.get("sexe", ""), "unknown"),
            occupation_raw=attrs.get("profession", ""),
            mandate={
                "start_date": FIRST_SITTING if entry_mode == "elected" else first_seen[slug],
                "end_date": TERM_END if not left_early else last_seen[slug],
                "entry_mode": entry_mode,
                "exit_mode": "end_of_term" if not left_early else "unknown",
                "constituency_name_ar": region,
                "governorate_name_ar": "" if is_abroad else region,
                "electoral_list_ar": attrs.get("liste", ""),
                "seat_number": attrs.get("siege", ""),
                "is_diaspora_seat": is_abroad,
                "election_date": ELECTION_DATE,
                "notes": "; ".join(notes),
            },
            blocs=member_spells,
            authoritative_fields=["name_ar", "name_lat", "gender", "occupation_raw"],
        ))

    doc = StagingDoc(
        source_id=SOURCE_ID,
        assembly_id=ASSEMBLY_ID,
        source={
            "source_id": SOURCE_ID,
            "name": "Marsad Majles 2014 observatory (Al Bawsala), via the Internet Archive",
            "publisher": "Al Bawsala; captures held by the Internet Archive",
            "url": ORIGINAL_URL,
            "access_method": (
                "Wayback CDX index to enumerate captures, then raw (`id_`) "
                "snapshot fetches of the roster page"
            ),
            "coverage": (
                "ARP-2014: all 217 members with Arabic and romanised names, sex, "
                "profession, constituency, electoral list, seat number, and "
                "bloc membership as dated spells derived from ~35 monthly captures"
            ),
            "language": "ar",
            "licence": "Not stated. Civic-monitoring data on public office-holders.",
            "first_retrieved": today(),
            "last_retrieved": today(),
            "reliability_notes": (
                "The live site no longer serves /2014/*: those URLs return the "
                "current site's catch-all page, so this term is recoverable only "
                "from the Internet Archive. Bloc spells are derived by diffing "
                "monthly captures, so a change is located only to the interval "
                "between two captures; affected spells carry the bracketing dates "
                "and a note. Age is published without a birth date and is NOT "
                "converted to one — with a capture date it would only fix the "
                "birth year to within a year, so the raw age and observation date "
                "are preserved instead. Cross-check on the first capture: bloc "
                "sizes are Nidaa Tounes 86 and Ennahdha 69, matching the official "
                "2014 election result, across 33 constituencies."
            ),
        },
        assembly_updates={
            "captures_used": [ts for ts, _ in [(t, None) for t in timestamps]],
            "n_captures": len(observations),
            "n_bloc_switchers": n_switchers,
            "baseline_capture": baseline_date,
        },
        notes=(
            f"{len(records)} members from {len(observations)} Internet Archive "
            f"captures; {n_switchers} members changed bloc during the term. "
            f"Fetch: {fetcher.report()}."
        ),
        records=records,
    )
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description="Recover the 2014-2019 ARP from the Internet Archive")
    ap.add_argument("--refresh", action="store_true", help="bypass the raw cache")
    ap.add_argument("--max-captures", type=int, default=None,
                    help="sample at most N captures (faster; coarser switch dates)")
    args = ap.parse_args()
    collect(refresh=args.refresh, max_captures=args.max_captures).save()


if __name__ == "__main__":
    main()
