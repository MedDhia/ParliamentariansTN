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

from ..ids import normalize_arabic
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
    baseline_date = observations[0][0] if observations else ""

    for capture_date, roster in observations:
        for slug, attrs in roster.items():
            bloc = attrs.get("bloc", "")
            if not bloc:
                continue
            current = spells[slug][-1] if spells.get(slug) else None
            if current is None:
                # A member present in the FIRST capture was seated at the start of
                # the term, so their opening bloc is dated to the first sitting —
                # blocs were constituted then. A member who first appears in a
                # later capture is a mid-term replacement, and dating their bloc
                # membership to the first sitting would credit them with up to
                # four years they did not serve (and would push the chamber's
                # reconstructed size above its seat count in the opening month).
                joined_at_start = capture_date == baseline_date
                spells[slug].append({
                    "name_ar": bloc,
                    "groupe_id": attrs.get("groupe_id", ""),
                    "start_date": FIRST_SITTING if joined_at_start else capture_date,
                    "start_date_earliest": FIRST_SITTING if joined_at_start
                    else last_seen_date.get(slug, capture_date),
                    "first_observed": capture_date,
                    "last_observed": capture_date,
                    "end_date": "",
                    # A replacement's true arrival lies somewhere between the
                    # previous capture and this one, so the boundary is bracketed.
                    "dates_bracketed": not joined_at_start,
                })
            elif current["name_ar"] != bloc:
                previous_observation = last_seen_date.get(slug, current["last_observed"])
                # Close the outgoing spell where the incoming one starts, so a
                # member's spells tile their service without gaps. Ending it at
                # the last *observation* instead would leave the member in no
                # bloc at all for the length of the capture gap — up to nine
                # months here — which is a false claim, not a cautious one. The
                # genuine uncertainty is that the change happened somewhere in
                # (previous_observation, capture_date]; that interval is recorded
                # in end_date_earliest / start_date_earliest and flagged
                # dates_bracketed.
                current["end_date"] = capture_date
                current["end_date_earliest"] = previous_observation
                current["dates_bracketed"] = True
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

    # Close each member's final spell. Only a member still present in the LAST
    # capture served to the end of the term; one who stops appearing was
    # replaced, and closing their spell at the term's end would keep them in the
    # chamber for years after they left (and push the reconstructed chamber above
    # its seat count in the closing months).
    final_date = observations[-1][0] if observations else ""
    for slug, member_spells in spells.items():
        if not member_spells or member_spells[-1]["end_date"]:
            continue
        last_spell = member_spells[-1]
        served_to_end = last_seen_date.get(slug) == final_date
        last_spell["end_date"] = TERM_END if served_to_end else last_spell["last_observed"]
        if not served_to_end:
            last_spell["dates_bracketed"] = True
    return spells


# ---------------------------------------------------------------------------
# Committees and the bureau
#
# The roster page was only ever half of what this observatory published. The
# committee pages under /2014/assemblee/commissions/<id> and the bureau page
# carry the chamber's internal organisation, and they were the one part of this
# recovery left open when the roster landed. They are worth the second pass for
# a specific reason: committee co-membership is the standard measure of
# legislative co-work, and this dataset otherwise has it for 2011-14 and 2019-
# but not for the term in between — exactly the term whose coalition broke up.
#
# Two complications, both handled below.
#
# **The site was redesigned mid-term.** Captures up to about 2017 use a compact
# layout (``<a class="membre">`` wrapping ``elu-fonction`` / ``elu-nom``); later
# ones use Bootstrap cards (``<a class="link-elu">`` wrapping a ``card-title``).
# Both are parsed; a capture that yields nothing under either is skipped rather
# than silently treated as an empty committee, which would read as every member
# having left at once.
#
# **The /2014/ paths outlived the chamber.** Captures from 2020 return the
# *2019* chamber's committees under the same URLs — spot-checked and confirmed:
# a 2020 capture of the general-legislation committee lists members elected in
# 2019. Anything captured after the term ended is therefore discarded, which is
# a stricter window than the roster pass needed.
# ---------------------------------------------------------------------------

COMMISSIONS_INDEX = "https://majles.marsad.tn/2014/assemblee/commissions"
BUREAU_URL = "https://majles.marsad.tn/2014/assemblee/bureau"
COMMITTEE_ID_RE = re.compile(r"/2014/assemblee/commissions/([0-9a-f]{24})/?$")

# Every member of a committee or of the bureau is an anchor to that person's own
# page, in all three layouts the site went through. What changes between layouts
# is what sits *inside* the anchor, so one block regex plus tolerant extraction
# beats three parsers:
#
#   2015      <a href="/2014/elus/X" class="membre">
#                <span class="elu-fonction">الرئيس</span>
#                <span class="elu-nom">…</span>
#   2015-17   <a href="/2014/elus/X" data-bloc="…" data-region="…">
#                <div class="elu-nom">…</div>
#                <div class="elu-fonction">رئيس اللجنة</div>
#   2019      <a href="/2014/elus/X" class="link-elu">
#                <h6 class="card-title mb-1">…</h6>
#                <span class="p-0 d-block text-primary …">رئيس</span>
ELU_BLOCK_RE = re.compile(
    r'<a\s+(?:class="[^"]*"\s+)?href="/2014/elus/([^"?]+)"[^>]*>(.*?)</a>', re.S)
# A wound-up committee's page still links its former members, as bare anchors
# with neither a name element nor a role. Requiring a name element is what keeps
# "أعضاء مستقيلين" — resigned members — from being read as current membership.
NAME_MARKER_RE = re.compile(r"elu-nom|card-title")
ROLE_RE = re.compile(
    r'class="elu-fonction[^"]*"\s*>(.*?)</(?:span|div)>'
    r'|<span class="p-0 d-block text-primary[^"]*">(.*?)</span>', re.S)
HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]>", re.S)
# The 2019 bureau page prints each spell as "04 ديسمبر 2015 - 25 جويلية 2019".
BUREAU_DATES_RE = re.compile(r"fa-calendar-alt[^>]*></i>\s*([^<]+)</span>", re.S)

# Committee roles are classified by token rather than by table lookup: the
# corpus spells them 39 different ways across 3,172 labels — masculine and
# feminine ("مقرر" / "مقررة"), with and without the definite article, with and
# without the shadda, with and without "اللجنة", and "first"/"second" assistant
# rapporteurs written four ways each. Enumerating that is a losing game; the
# distinguishing token is not.
#
# Order is the whole algorithm. "مساعد مقرر ثاني" is an assistant rapporteur and
# contains "مقرر"; "نائب رئيس اللجنة" is a vice-chair and contains "رئيس". Each
# test therefore has to run before the one whose token it also contains.
COMMITTEE_ROLE_TOKENS = (
    (("مساعد", "مساعدة"), "assistant_rapporteur"),
    (("نائب", "نائبة"), "vice_chair"),
    (("مقرر", "مقررة"), "rapporteur"),
    (("رئيس", "رئيسة"), "chair"),
    (("عضو", "عضوة"), "member"),
)

# Bureau titles. "مساعد الرئيس المكلف بالإعلام والاتصال" — assistant to the
# speaker for media — is a portfolio, and every holder of one sits on the
# bureau, so they all map to `bureau_member` with the portfolio kept verbatim in
# `office_label_ar`. That label is worth keeping: it is the only place in this
# dataset where a chamber's internal division of labour is named.
OFFICE_ROLE_TOKENS = (
    (("مساعد", "مساعدة"), "bureau_member"),
    (("النائب الاول", "النائبة الاولى", "النائب الأول", "النائبة الأولى"),
     "first_vice_speaker"),
    (("نائب", "نائبة"), "vice_speaker"),
    (("رئيس", "رئيسة"), "speaker"),
)

# Committees created for one job rather than standing ones. The index page files
# these under "اللجان المؤقتة"; the distinction is substantive enough to keep.
SPECIAL_COMMITTEE_TOKENS = ("الخاصة", "المؤقتة", "التحقيق")

ARABIC_MONTHS = {
    "جانفي": 1, "فيفري": 2, "مارس": 3, "أفريل": 4, "ماي": 5, "جوان": 6,
    "جويلية": 7, "أوت": 8, "سبتمبر": 9, "أكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
    "يناير": 1, "فبراير": 2, "إبريل": 4, "أبريل": 4, "مايو": 5, "يونيو": 6,
    "يوليو": 7, "أغسطس": 8,
}
# What the site prints instead of an end date for someone still in post.
STILL_SERVING = ("الآن", "اليوم")


def _strip_tags(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


def _classify(label: str, tokens: tuple, default: str) -> str:
    """Map a role label to a code by the first distinguishing token it carries."""
    folded = normalize_arabic(label)
    for candidates, code in tokens:
        if any(normalize_arabic(c) in folded for c in candidates):
            return code
    return default


def _parse_member_blocks(markup: str) -> list[tuple[str, str, str]]:
    """Return ``[(slug, role label, whole anchor)]`` for every member anchor."""
    out = []
    for match in ELU_BLOCK_RE.finditer(markup):
        blob = match.group(2)
        if not NAME_MARKER_RE.search(blob):
            continue
        role = ROLE_RE.search(blob)
        label = _strip_tags(role.group(1) or role.group(2) or "") if role else ""
        out.append((html.unescape(match.group(1)).strip(), label, blob))
    return out


def parse_committee_page(markup: str) -> tuple[str, list[tuple[str, str]]]:
    """Return ``(committee name, [(member slug, role)])`` from any of the layouts."""
    members = [
        (slug, _classify(label, COMMITTEE_ROLE_TOKENS, "member"))
        for slug, label, _blob in _parse_member_blocks(markup)
    ]
    name = ""
    for heading in HEADING_RE.findall(markup):
        text = _strip_tags(heading)
        if text and "لجنة" in text:
            name = text
            break
    return name, members


def parse_bureau_page(markup: str) -> list[tuple[str, str, str, str]]:
    """Return ``[(slug, office, printed title, printed date range)]``.

    The later layout prints an explicit date range beside each member, which is
    better than anything capture-diffing can produce: these office spells carry
    the chamber's own dates rather than a bracket between crawls.
    """
    out = []
    for slug, label, blob in _parse_member_blocks(markup):
        dates = BUREAU_DATES_RE.search(blob)
        out.append((slug, _classify(label, OFFICE_ROLE_TOKENS, "bureau_member"),
                    label, _strip_tags(dates.group(1)) if dates else ""))
    return out


def parse_arabic_date(text: str) -> str:
    """``04 ديسمبر 2015`` -> ``2015-12-04``; anything else -> ``""``."""
    match = re.search(r"(\d{1,2})\s+(\S+)\s+(\d{4})", text.strip())
    if not match:
        return ""
    day, month_name, year = match.groups()
    month = ARABIC_MONTHS.get(month_name.strip())
    if not month:
        return ""
    return f"{year}-{month:02d}-{int(day):02d}"


# At most this many captures are read per committee. Twenty-five committees
# times every monthly capture would be seven hundred fetches for resolution the
# data cannot carry anyway — a membership change is located to the gap between
# captures either way. Twelve evenly spaced captures put that gap at roughly a
# quarter across the term, with enough slack that the handful of captures which
# yield nothing (a wound-up committee showing only its resigned members) do not
# leave a committee with two usable observations four years apart.
MAX_COMMITTEE_CAPTURES = 12


def _sample(values: list[str], limit: int) -> list[str]:
    """Take ``limit`` evenly spaced items, always keeping the first and last."""
    if len(values) <= limit:
        return values
    step = (len(values) - 1) / (limit - 1)
    picked = {values[min(int(round(i * step)), len(values) - 1)] for i in range(limit)}
    picked.update({values[0], values[-1]})
    return sorted(picked)


def list_committee_captures(fetcher: Fetcher) -> dict[str, list[str]]:
    """Return ``committee id -> [capture timestamps]``, within the term only."""
    payload = fetcher.get_json(
        CDX,
        slug="cdx_commissions",
        params={
            "url": "majles.marsad.tn/2014/assemblee/commissions*",
            "output": "json",
            "filter": "statuscode:200",
            "limit": "8000",
        },
    )
    if not payload or len(payload) < 2:
        raise RuntimeError("no Wayback captures found for the 2014 committee pages")
    header = payload[0]
    ti, ui, li = header.index("timestamp"), header.index("original"), header.index("length")
    per_month: dict[tuple[str, str], tuple[str, int]] = {}
    for row in payload[1:]:
        url = row[ui]
        if "?" in url:
            # Session-scoped variants of the same page; the bare URL is enough.
            continue
        match = COMMITTEE_ID_RE.search(url)
        if not match:
            continue
        ts, length = row[ti], int(row[li] or 0)
        # Captures after the term ended show the NEXT chamber's committees under
        # these same paths, verified by spot check. They are not this chamber.
        if ts[:8] > TERM_END.replace("-", ""):
            continue
        key = (match.group(1), ts[:6])
        if key not in per_month or length > per_month[key][1]:
            per_month[key] = (ts, length)
    out: dict[str, list[str]] = defaultdict(list)
    for (cid, _month), (ts, _length) in sorted(per_month.items()):
        out[cid].append(ts)
    return {cid: _sample(sorted(stamps), MAX_COMMITTEE_CAPTURES)
            for cid, stamps in sorted(out.items())}


def build_committee_spells(
    observations: list[tuple[str, dict[str, str]]],
) -> dict[str, list[dict[str, Any]]]:
    """Turn a committee's capture series into dated membership spells.

    ``observations`` is [(capture_date, {member slug: role})] in date order.
    A member observed across a contiguous run of captures gets one spell. A
    member who drops out and returns gets two, which is the honest reading: the
    site showed them off the committee in between.
    """
    spells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not observations:
        return spells
    last_date = observations[-1][0]
    previous: dict[str, str] = {}
    for index, (capture_date, roster) in enumerate(observations):
        for slug, role in roster.items():
            current = spells[slug][-1] if spells.get(slug) else None
            if current is not None and not current["closed"]:
                current["last_observed"] = capture_date
                current["role"] = role  # a member promoted to chair keeps one spell
                continue
            spells[slug].append({
                "role": role,
                "first_observed": capture_date,
                "last_observed": capture_date,
                "start_bracketed_from": previous.get(slug, ""),
                "closed": False,
                "from_first_capture": index == 0,
            })
        for slug, member_spells in spells.items():
            if slug in roster or not member_spells or member_spells[-1]["closed"]:
                continue
            member_spells[-1]["closed"] = True
            member_spells[-1]["end_bracketed_to"] = capture_date
        previous = {slug: capture_date for slug in roster}
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slug, member_spells in spells.items():
        for spell in member_spells:
            served_from_start = spell["from_first_capture"]
            served_to_end = not spell["closed"] and spell["last_observed"] == last_date
            spell["start_date"] = FIRST_SITTING if served_from_start else spell["first_observed"]
            spell["end_date"] = TERM_END if served_to_end else (
                spell.get("end_bracketed_to") or spell["last_observed"])
            spell["dates_bracketed"] = not (served_from_start and served_to_end)
            out[slug].append(spell)
    return out


def collect_committees(fetcher: Fetcher) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Committee membership for every member, as dated spells."""
    captures = list_committee_captures(fetcher)
    log(f"  {len(captures)} committees, "
        f"{sum(len(v) for v in captures.values())} captures to read")
    by_member: dict[str, list[dict[str, Any]]] = defaultdict(list)
    summary: dict[str, Any] = {"committees": [], "n_unparsed_captures": 0}
    for cid, stamps in captures.items():
        observations: list[tuple[str, dict[str, str]]] = []
        name = ""
        for ts in stamps:
            markup = fetcher.get_text(
                WAYBACK.format(timestamp=ts, url=f"{COMMISSIONS_INDEX}/{cid}"),
                slug=f"commission_{cid}_{ts}",
            )
            page_name, members = parse_committee_page(markup)
            if not members:
                # A redirect, an error page, or a layout this parser does not
                # know. Treating it as an empty committee would read as the
                # whole membership resigning on that date.
                summary["n_unparsed_captures"] += 1
                continue
            name = name or page_name
            observations.append((_timestamp_to_date(ts), dict(members)))
        if not observations or not name:
            continue
        kind = "special" if any(tok in name for tok in SPECIAL_COMMITTEE_TOKENS) else "standing"
        spells = build_committee_spells(observations)
        for slug, member_spells in spells.items():
            for spell in member_spells:
                by_member[slug].append({
                    "source_key": cid,
                    "name_ar": name,
                    "type": kind,
                    "role": spell["role"],
                    "start_date": spell["start_date"],
                    "end_date": spell["end_date"],
                    "dates_bracketed": spell["dates_bracketed"],
                    "notes": (
                        f"observed on this committee on captures from "
                        f"{spell['first_observed']} to {spell['last_observed']}, "
                        f"out of {len(observations)} readable captures of its page; "
                        f"the recorded span {spell['start_date']}..{spell['end_date']} "
                        "is the outer bound, since each boundary falls in a gap "
                        "between captures rather than on a known date"
                    ) if spell["dates_bracketed"] else "",
                })
        summary["committees"].append({
            "committee_id": cid,
            "name_ar": name,
            "type": kind,
            "captures": len(observations),
            "distinct_members": len(spells),
            "first_capture": observations[0][0],
            "last_capture": observations[-1][0],
        })
    return by_member, summary


def collect_bureau(fetcher: Fetcher) -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Bureau membership, with the chamber's own dates where the page gives them."""
    payload = fetcher.get_json(
        CDX,
        slug="cdx_bureau",
        params={"url": "majles.marsad.tn/2014/assemblee/bureau", "output": "json",
                "filter": "statuscode:200", "limit": "300"},
    )
    header = payload[0]
    ti, li = header.index("timestamp"), header.index("length")
    stamps = [row[ti] for row in sorted(payload[1:], key=lambda r: -int(r[li] or 0))
              if row[ti][:8] <= TERM_END.replace("-", "")]
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    n_read = 0
    for ts in stamps[:4]:
        markup = fetcher.get_text(
            WAYBACK.format(timestamp=ts, url=BUREAU_URL), slug=f"bureau_{ts}")
        rows = parse_bureau_page(markup)
        if not rows:
            continue
        n_read += 1
        for slug, office, title, printed in rows:
            if (slug, office, title) in seen:
                continue
            seen.add((slug, office, title))
            start, _, end = printed.partition(" - ")
            out[slug].append({
                "office": office,
                "office_label_ar": title,
                "start_date": parse_arabic_date(start),
                # The page writes "الآن" for someone still in post at the time of
                # the capture. Every capture read here predates the end of the
                # term, and a chamber office cannot outlive its chamber, so the
                # term's end is the correct close — a published date, not a guess.
                "end_date": (TERM_END if any(tok in end for tok in STILL_SERVING)
                             else parse_arabic_date(end)),
            })
    return out, n_read


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
    committee_spells, committee_summary = collect_committees(fetcher)
    bureau_spells, n_bureau_captures = collect_bureau(fetcher)
    log(f"  {sum(len(v) for v in committee_spells.values())} committee spells across "
        f"{len(committee_summary['committees'])} committees; "
        f"{sum(len(v) for v in bureau_spells.values())} bureau seats")

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
            committees=committee_spells.get(slug, []),
            offices=bureau_spells.get(slug, []),
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
                "profession, constituency, electoral list, seat number, bloc "
                "membership as dated spells derived from ~35 monthly captures, "
                "committee membership with roles from the archived committee "
                "pages, and the bureau with the chamber's own dates"
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
            "captures_used": list(timestamps),
            "n_captures": len(observations),
            "n_bloc_switchers": n_switchers,
            "baseline_capture": baseline_date,
            "committees": committee_summary["committees"],
            "n_unparsed_committee_captures": committee_summary["n_unparsed_captures"],
            "n_bureau_captures_read": n_bureau_captures,
        },
        notes=(
            f"{len(records)} members from {len(observations)} Internet Archive "
            f"captures; {n_switchers} members changed bloc during the term. "
            f"{sum(len(v) for v in committee_spells.values())} committee spells "
            f"across {len(committee_summary['committees'])} committees and "
            f"{sum(len(v) for v in bureau_spells.values())} bureau seats. "
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
