"""Display-only English glosses for Arabic labels.

**These are not data.** The Arabic strings in ``data/processed`` are
authoritative; everything here exists solely so a chart axis can be read, and so
that no figure has to render Arabic (matplotlib has no shaping or bidi — see
``_style.label``). Glosses are short by design: an axis tick is not the place for
a party's full registered name.

Where a bloc's Arabic name is already accompanied by a Latin form in the data —
Al Bawsala's own French naming, carried through for NCA-2011 and ARP-2014 — the
gloss here is a *shortened* version of the same thing, not an independent
translation.

Anything unglossed falls back to the table's ``name_lat`` and, failing that,
raises. That is deliberate: a silently untranslated label is a figure defect.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Parliamentary blocs
# ---------------------------------------------------------------------------
# Keyed on the exact Arabic string in blocs.name_ar. The trailing "(2019)" /
# "(2020)" in the 2019 chamber's names is Marsad's bloc-year suffix, not part of
# the bloc's name, so it is dropped from the display form.

BLOC_GLOSS: dict[str, str] = {
    # --- NCA 2011-2014 -----------------------------------------------------
    "كتلة حركة النهضة": "Ennahdha",
    "غير المنتمين إلى كتل": "No bloc",
    "الكتلة الديمقراطية": "Democratic Bloc",
    "كتلة المؤتمر من أجل الجمهورية": "CPR",
    "الإنتقال الديمقراطي": "Democratic Transition",
    "كتلة حزب التكتل": "Ettakatol",
    "كتلة الوفاء للثورة": "Loyalty to the Revolution",
    "التحالف الديمقراطي": "Democratic Alliance",

    # --- ARP 2014-2019 -----------------------------------------------------
    "حركة نداء تونس": "Nidaa Tounes",
    "حركة النهضة": "Ennahdha",
    "غير المنتمين": "No bloc",
    "الائتلاف الوطني": "National Coalition",
    "الكتلة الحرّة": "Al Horra",
    "كتلة الحرّة لحركة مشروع تونس": "Al Horra (Machrouu Tounes)",
    "الإتحاد الوطني الحر": "UPL",
    "الجبهة الشعبية": "Popular Front",
    "كتلة الولاء للوطن": "Loyalty to the Nation",
    "الكتلة الإجتماعية الديمقراطية": "Social Democratic Bloc",
    "الكتلة الوطنية": "National Bloc",
    "آفاق تونس": "Afek Tounes",
    "آفاق تونس ونداء التونسيين بالخارج": "Afek Tounes + diaspora",
    "آفاق تونس والحركة الوطنية ونداء التونسيين بالخارج": "Afek Tounes + national movement",

    # --- ARP 2019-2021 -----------------------------------------------------
    "كتلة حركة النهضة (2019)": "Ennahdha",
    "الكتلة الديمقراطية (2019)": "Democratic Bloc",
    "كتلة حزب قلب تونس (2019)": "Qalb Tounes",
    "مستقل": "Independent",
    "كتلة ائتلاف الكرامة (2019)": "Al Karama",
    "كتلة الاصلاح (2019)": "Reform Bloc",
    "كتلة الحزب الدستوري الحر (2019)": "PDL",
    "كتلة تحيا تونس (2019)": "Tahya Tounes",
    "الكتلة الوطنية (2020)": "National Bloc",

    # --- ARP 2023- ---------------------------------------------------------
    "كتلة الأمانة والعمل": "Al Amana wal Amal",
    "كتلة صوت الجمهورية": "Voice of the Republic",
    "كتلة الوطنية المستقلة": "Independent National",
    "كتلة لينتصر الشعب": "Li-Yantasir al-Shaab",
    "كتلة الأحرار": "Al Ahrar",
    "كتلة الخط الوطني السيادي": "Sovereignist National Line",
}


# ---------------------------------------------------------------------------
# Professions (ARP-2014, the only chamber with near-complete occupation data)
# ---------------------------------------------------------------------------
# Marsad's own occupational categories. Glossed to the shortest form that keeps
# the distinction the category is making — "senior civil servant" and
# "civil servant" are separate categories upstream and stay separate here.

PROFESSION_GLOSS: dict[str, str] = {
    "محامي": "Lawyer",
    "أستاذ تعليم ثانوي": "Secondary teacher",
    "مدير مؤسسة": "Company director",
    "أستاذ جامعي": "University professor",
    "موظف بالقطاع الخاص": "Private-sector employee",
    "طبيب": "Doctor",
    "إطار سامي بالوظيفة العمومية": "Senior civil servant",
    "متقاعد": "Retired",
    "معلّم تعليم أساسي": "Primary teacher",
    "موظف عمومي": "Civil servant",
    "إطار سامي بالقطاع الخاص": "Senior private-sector manager",
    "باحث جامعي": "Academic researcher",
    "طالب": "Student",
    "غير مصنف": "Unclassified",
    "مهندس": "Engineer",
    "إطار بالوظيفة العمومية": "Public-sector manager",
    "إطار سامي بالقطاع البنكي": "Senior banking manager",
    "ممثل جمعياتي": "Civil-society representative",
    "صحافي": "Journalist",
    "فلاح": "Farmer",
    "محاسب": "Accountant",
    "رجل أعمال": "Businessman",
    "أستاذ": "Teacher",
    "إمام": "Imam",
}


# ---------------------------------------------------------------------------
# Chambers
# ---------------------------------------------------------------------------
# Short display labels. The assembly_id is already ASCII and is used as the tick
# in most figures; these are for the few places a fuller name reads better.

ASSEMBLY_SHORT: dict[str, str] = {
    "ANC-1956": "Constituent 1956",
    "NA-1959": "Nat. Assembly 1959",
    "NA-1964": "Nat. Assembly 1964",
    "NA-1969": "Nat. Assembly 1969",
    "NA-1974": "Nat. Assembly 1974",
    "NA-1979": "Nat. Assembly 1979",
    "COD-1981": "Deputies 1981",
    "COD-1986": "Deputies 1986",
    "COD-1989": "Deputies 1989",
    "COD-1994": "Deputies 1994",
    "COD-1999": "Deputies 1999",
    "COD-2004": "Deputies 2004",
    "COD-2009": "Deputies 2009",
    "ADV-2005": "Advisors 2005",
    "NCA-2011": "Constituent 2011",
    "ARP-2014": "ARP 2014",
    "ARP-2019": "ARP 2019",
    "ARP-2023": "ARP 2023",
    "CNRD-2023": "Regions 2023",
}

REGIME_SHORT: dict[str, str] = {
    "protectorate_transition": "Independence",
    "bourguiba": "Bourguiba",
    "ben_ali": "Ben Ali",
    "transition": "Transition",
    "second_republic": "Second Republic",
    "exceptional_measures": "Exceptional measures",
    "third_republic": "Third Republic",
}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

_ARABIC_RANGE = re.compile(r"[؀-ۿ]")


def _shorten(text: str, limit: int = 34) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1].rstrip(" ,") + "…"


def _is_latin(text: str) -> bool:
    """True when the string carries no Arabic and so is safe to draw as-is."""
    return not _ARABIC_RANGE.search(str(text))


def _strip_stray_arabic(text: str) -> str:
    """Drop stray Arabic characters from a string that is otherwise Latin.

    Upstream records occasionally carry a lone Arabic mark glued to a French
    name — one ARP-2023 committee's French label begins with a kasra (U+0650),
    presumably a keyboard slip when the record was typed. Rendering that would
    trip the Arabic guard for a string that is, in substance, French.

    Only applied when what remains is still mostly Latin letters; a genuinely
    Arabic string is left alone so the guard still fires on it. The raw value in
    the data is untouched — this is display cleanup, not a correction.
    """
    text = str(text)
    if _is_latin(text):
        return text
    cleaned = _ARABIC_RANGE.sub("", text).strip()
    latin_letters = sum(1 for ch in cleaned if ch.isalpha() and ch.isascii())
    if latin_letters >= 4 and latin_letters >= 0.5 * len(cleaned):
        return cleaned
    return text


def bloc(name_ar: str, name_lat: str = "", limit: int = 34) -> str:
    """English display label for a bloc, falling back to the data's Latin name."""
    gloss = BLOC_GLOSS.get(" ".join(str(name_ar).split()))
    if gloss:
        return gloss
    if name_lat:
        return _shorten(_strip_stray_arabic(name_lat), limit)
    raise KeyError(
        f"no gloss for bloc {name_ar!r} and no name_lat in the data; "
        "add it to figures/_labels.py BLOC_GLOSS"
    )


def profession(name_ar: str, limit: int = 30) -> str:
    """English display label for an occupation category.

    Free-text entries — a handful of ARP-2014 rows carry a whole French CV
    paragraph in the profession field — are bucketed rather than glossed.
    """
    key = " ".join(str(name_ar).split())
    gloss = PROFESSION_GLOSS.get(key)
    if gloss:
        return gloss
    # Latin free text: keep it, shortened. Anything else is unglossed Arabic,
    # which is bucketed rather than drawn broken.
    if _is_latin(key):
        return _shorten(key, limit)
    return "Other / unclassified"


def committee(name_ar: str, name_lat: str = "", name_en: str = "",
              limit: int = 40) -> str:
    for candidate in (name_en, name_lat):
        if candidate:
            text = _shorten(_strip_stray_arabic(candidate), limit)
            # Some of the chamber's French labels were typed lowercase and some
            # capitalised; on one chart the mixture reads as an error. Leading
            # character only, as for person_name.
            return text[0].upper() + text[1:] if text else text
    raise KeyError(
        f"no Latin name for committee {name_ar!r}; add a gloss in figures/_labels.py"
    )


_COMMITTEE_PREFIX = re.compile(
    r"^(?:la\s+)?commissions?\s+(?:de\s+la\s+|de\s+l['’]|de\s+|du\s+|des\s+|d['’])?",
    re.IGNORECASE,
)


def committee_short(name_ar: str, name_lat: str = "", name_en: str = "",
                    limit: int = 26) -> str:
    """Committee label with the boilerplate prefix removed.

    Every French committee name begins "Commission de la …", so truncating from
    the left spends the whole budget on the part they all share and cuts off the
    only word that tells them apart — "Commission de la sant…" and "Commission de
    la Plan…" differ in characters 18 onward. Dropping the prefix puts the policy
    domain first, which is what a rim label has room for.
    """
    full = committee(name_ar, name_lat, name_en, limit=200)
    stripped = _COMMITTEE_PREFIX.sub("", full).strip(" ,")
    if not stripped:
        stripped = full
    stripped = stripped[0].upper() + stripped[1:] if stripped else stripped
    return _shorten(stripped, limit)


def person_name(name_lat: str) -> str:
    """Display form of a Latin-script personal name.

    Only the leading character is touched, and only when it is a lowercase
    letter: a few upstream records were typed as "dhafer Sghiri", which reads as
    a rendering bug when it lands on a chart. Nothing else is normalised —
    title-casing the whole string would mangle the nasab particles ("Ben Ali",
    "Bel Aiech") that carry meaning. The value in ``data/processed`` is untouched;
    this is display cleanup, not a correction.
    """
    text = str(name_lat).strip()
    if text and text[0].islower():
        return text[0].upper() + text[1:]
    return text


def assembly(assembly_id: str) -> str:
    return ASSEMBLY_SHORT.get(assembly_id, assembly_id)


def regime(period: str) -> str:
    return REGIME_SHORT.get(period, period or "unknown")


def assembly_wrapped(assembly_id: str) -> str:
    """Two-line chamber label, for a dense horizontal tick row.

    Preferred over rotating the tick labels: rotation costs legibility and, in a
    tight-bbox render, pushes the labels into whatever sits below the axes.
    """
    text = assembly(assembly_id)
    if " " not in text:
        return text
    head, _, tail = text.rpartition(" ")
    return f"{head}\n{tail}"
