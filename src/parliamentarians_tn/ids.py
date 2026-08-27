"""Identity resolution: Arabic name normalisation, romanisation and ID minting.

Cross-source record linkage is the hard problem in this dataset. The same
deputy appears as ``إبراهيم بودربالة`` on arp.tn, as ``Brahim Bouderbela`` in the
French projection of the same record, and could plausibly appear as
``Ibrahim Bouderbala`` in a third source. Three orthographic facts about
Tunisian name data drive the normalisation below:

* Alif forms (أ إ آ ا) are used interchangeably in official records.
* The definite article is written both attached (``بودربالة``) and detached
  (``بو دربالة``), and the ``ال`` prefix is inconsistently present on family
  names (``الحامدي`` / ``حامدي``).
* Ta marbuta (ة) and ha (ه) are interchanged word-finally, as are ya (ي) and
  alif maqsura (ى).

Normalisation folds all of these so that the same person collapses to one key.
It is deliberately aggressive: it is used for *candidate generation*, and a
match is only accepted when a source identifier agrees or a human confirms.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

# ---------------------------------------------------------------------------
# Arabic normalisation
# ---------------------------------------------------------------------------

_ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")

_CHAR_FOLD = {
    # alif variants -> bare alif
    "أ": "ا",  # أ
    "إ": "ا",  # إ
    "آ": "ا",  # آ
    "ٱ": "ا",  # ٱ
    # ya / alif maqsura
    "ى": "ي",  # ى -> ي
    # ta marbuta -> ha
    "ة": "ه",  # ة -> ه
    # hamza on waw/ya
    "ؤ": "و",  # ؤ -> و
    "ئ": "ي",  # ئ -> ي
}

# Family-name prefixes that sources attach or detach inconsistently.
_DETACHABLE_PREFIXES = ("بن", "بو", "ابن", "اولاد", "ولد", "عبد")


def strip_arabic_diacritics(text: str) -> str:
    return _ARABIC_DIACRITICS.sub("", text)


def normalize_arabic(text: str | None) -> str:
    """Fold an Arabic name to a comparison key.

    Returns the empty string for falsy input so that callers can treat a
    missing name and an unnormalisable name identically.
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = strip_arabic_diacritics(s)
    s = "".join(_CHAR_FOLD.get(ch, ch) for ch in s)
    # drop the definite article wherever it begins a token
    s = re.sub(r"(?<![\w])ال(?=[؀-ۿ])", "", s)
    # collapse punctuation and whitespace
    s = re.sub(r"[^؀-ۿ\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def arabic_match_key(text: str | None) -> str:
    """A stricter key: normalised, prefix-folded, token-sorted.

    Token sorting absorbs given-name/family-name order differences, which vary
    between the ARP register (family first) and Al Bawsala (given first).
    """
    norm = normalize_arabic(text)
    if not norm:
        return ""
    tokens = [t for t in norm.split() if t not in _DETACHABLE_PREFIXES]
    tokens = [t for t in tokens if len(t) > 1]
    return " ".join(sorted(tokens))


# ---------------------------------------------------------------------------
# Latin normalisation
# ---------------------------------------------------------------------------

_LATIN_FOLD = str.maketrans(
    {"'": "", "’": "", "`": "", "-": " ", "_": " ", ".": " "}
)


def normalize_latin(text: str | None) -> str:
    """Fold a romanised name: strip accents, punctuation, case and doubles."""
    if not text:
        return ""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.translate(_LATIN_FOLD).lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    # common romanisation variants for the same Arabic phoneme
    s = re.sub(r"\bben\b", "ben", s)
    s = s.replace("ou", "u").replace("kh", "k").replace("ch", "sh")
    s = re.sub(r"(.)\1+", r"\1", s)  # collapse doubled letters
    s = re.sub(r"\s+", " ", s).strip()
    return s


def latin_match_key(text: str | None) -> str:
    norm = normalize_latin(text)
    if not norm:
        return ""
    return " ".join(sorted(t for t in norm.split() if len(t) > 1))


# ---------------------------------------------------------------------------
# Light romanisation for names that arrive only in Arabic
# ---------------------------------------------------------------------------

_TRANSLIT = {
    "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s",
    "ض": "d", "ط": "t", "ظ": "z", "ع": "a", "غ": "gh", "ف": "f", "ق": "q",
    "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y",
    "ء": "", "ة": "a", "ى": "a", "ـ": "",
}


def romanize_arabic(text: str | None) -> str:
    """Deterministic fallback romanisation.

    Used only to populate ``name_lat`` when no source supplies a Latin form.
    It is a transliteration aid, not a scholarly transcription: the codebook
    records which rows were machine-romanised so they are never mistaken for
    an official spelling.
    """
    if not text:
        return ""
    s = strip_arabic_diacritics(unicodedata.normalize("NFKC", str(text)))
    out = []
    for token in s.split():
        chars = "".join(_TRANSLIT.get(ch, ch if ch.isalnum() else "") for ch in token)
        chars = re.sub(r"(.)\1+", r"\1", chars)
        if chars:
            out.append(chars.capitalize())
    return " ".join(out)


# ---------------------------------------------------------------------------
# ID minting
# ---------------------------------------------------------------------------


def _fmt(prefix: str, n: int, width: int = 5) -> str:
    return f"{prefix}-{n:0{width}d}"


class IdRegistry:
    """Mints stable dataset IDs and remembers upstream keys.

    The registry is persisted (see :mod:`parliamentarians_tn.build`) so that
    ``person_id`` values are stable across collection runs and across releases.
    Once TNP-00042 refers to a person, it always refers to that person; IDs are
    never reused even if a record is later withdrawn.
    """

    def __init__(self, prefix: str, existing: dict[str, str] | None = None, width: int = 5):
        self.prefix = prefix
        self.width = width
        # upstream composite key -> dataset id
        self._by_key: dict[str, str] = dict(existing or {})
        used = [v for v in self._by_key.values()]
        self._counter = 0
        for v in used:
            try:
                self._counter = max(self._counter, int(v.rsplit("-", 1)[1]))
            except (IndexError, ValueError):
                continue

    @staticmethod
    def key(source_id: str, source_key: str) -> str:
        return f"{source_id}::{source_key}"

    def get(self, source_id: str, source_key: str) -> str | None:
        return self._by_key.get(self.key(source_id, source_key))

    def mint(self, source_id: str, source_key: str) -> str:
        """Return the existing ID for this upstream key, or create one."""
        k = self.key(source_id, source_key)
        if k in self._by_key:
            return self._by_key[k]
        self._counter += 1
        new_id = _fmt(self.prefix, self._counter, self.width)
        self._by_key[k] = new_id
        return new_id

    def alias(self, source_id: str, source_key: str, dataset_id: str) -> None:
        """Record that an upstream key resolves to an already-known entity."""
        self._by_key[self.key(source_id, source_key)] = dataset_id

    def items(self) -> list[tuple[str, str]]:
        return sorted(self._by_key.items())

    def __len__(self) -> int:
        return len(self._by_key)


def deterministic_id(prefix: str, *parts: str, width: int = 12) -> str:
    """A content-addressed ID for rows with no upstream primary key.

    Spell rows (a committee membership, a bloc membership) frequently have no
    identifier upstream. Hashing their natural key keeps them stable across
    re-runs without needing a persisted counter.
    """
    payload = "|".join(str(p or "") for p in parts)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:width]
    return f"{prefix}-{digest}"


def value_hash(value: object) -> str:
    return hashlib.sha1(str(value).encode("utf-8")).hexdigest()[:12]
