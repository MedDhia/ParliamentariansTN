"""Filesystem layout, CSV round-tripping, and a polite cached HTTP client."""

from __future__ import annotations

import csv
import json
import os
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import requests

from .schema import Table

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
REFERENCE = DATA / "reference"
PROCESSED = DATA / "processed"
NETWORKS = DATA / "networks"
DOCS = ROOT / "docs"

for _d in (RAW, REFERENCE, PROCESSED, NETWORKS):
    _d.mkdir(parents=True, exist_ok=True)


def today() -> str:
    return date.today().isoformat()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

CSV_KWARGS: dict[str, Any] = {"lineterminator": "\n", "quoting": csv.QUOTE_MINIMAL}


def _clean(value: Any) -> str:
    """Render a Python value as a CSV cell.

    Odoo returns ``False`` for every empty field regardless of declared type,
    which would otherwise litter the dataset with the string ``False`` in place
    of missing values. ``None``, ``False`` and empty containers all become the
    empty string; genuine booleans must be passed as the strings "true"/"false"
    by the caller, which the collectors do explicitly.
    """
    if value is None or value is False:
        return ""
    if value is True:
        return "true"
    if isinstance(value, (list, tuple)):
        return ";".join(_clean(v) for v in value if v not in (None, False, ""))
    if isinstance(value, float):
        # keep rates readable and stable across runs
        return f"{value:.6g}"
    s = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    # Excel and R both mis-parse embedded newlines in unquoted fields; the csv
    # module quotes them, but collapsing keeps single-line-per-row diffs sane.
    return " ".join(s.split()) if "\n" in s else s


def write_table(tbl: Table, rows: Iterable[Mapping[str, Any]], directory: Path | None = None) -> Path:
    """Write rows as CSV using the schema's column order.

    Unknown keys are a programming error and raise, rather than being silently
    dropped: a typo in a collector should fail loudly, not lose a variable.
    """
    directory = directory or PROCESSED
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{tbl.name}.csv"
    cols = tbl.column_names
    n = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="raise", **CSV_KWARGS)
        writer.writeheader()
        for row in rows:
            unknown = set(row) - set(cols)
            if unknown:
                raise KeyError(f"{tbl.name}: unknown column(s) {sorted(unknown)}")
            writer.writerow({c: _clean(row.get(c)) for c in cols})
            n += 1
    log(f"wrote {path.relative_to(ROOT)} ({n} rows)")
    return path


def read_table(name: str, directory: Path | None = None) -> list[dict[str, str]]:
    for d in ([directory] if directory else [PROCESSED, REFERENCE]):
        path = d / f"{name}.csv"
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as fh:
                return list(csv.DictReader(fh))
    return []


def write_rows(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="raise", **CSV_KWARGS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _clean(row.get(c)) for c in fieldnames})
            n += 1
    log(f"wrote {path.relative_to(ROOT)} ({n} rows)")
    return path


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

USER_AGENT = (
    "ParliamentariansTN/0.1 (academic dataset on Tunisian parliamentarians; "
    "contact via repository issues)"
)


class Fetcher:
    """Cached, rate-limited HTTP client.

    Every response is written to ``data/raw`` keyed by a caller-supplied slug.
    Re-runs read from that cache unless ``refresh=True``, which means the whole
    build is reproducible offline and upstream servers are hit once per object
    rather than once per run. The delay is deliberately conservative: these are
    small public-institution servers, not commercial APIs.
    """

    def __init__(self, cache_dir: Path, delay: float = 1.0, refresh: bool = False, timeout: int = 60):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.refresh = refresh
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last_request = 0.0
        self.n_fetched = 0
        self.n_cached = 0

    # -- cache ------------------------------------------------------------
    def _cache_path(self, slug: str, ext: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in slug)
        return self.cache_dir / f"{safe}.{ext}"

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_exc: Exception | None = None
        for attempt in range(4):
            self._throttle()
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                resp.raise_for_status()
                return resp
            except Exception as exc:  # noqa: BLE001 - retried below
                last_exc = exc
                backoff = (2 ** attempt) + random.uniform(0, 0.5)
                log(f"  retry {attempt + 1}/4 after {backoff:.1f}s: {url} ({exc})")
                time.sleep(backoff)
        raise RuntimeError(f"failed after 4 attempts: {url}") from last_exc

    # -- public API -------------------------------------------------------
    def get_text(self, url: str, slug: str, ext: str = "html",
                 encoding: str | None = None) -> str:
        """Fetch a text resource, caching it as UTF-8.

        ``encoding`` overrides the response's declared charset. It exists for
        servers that return HTML with no charset in the Content-Type header, in
        which case HTTP says to assume Latin-1 and the library dutifully does —
        turning a UTF-8 Arabic page into mojibake that is then cached, so the
        damage survives every later run. Passing the encoding the page's own
        meta tag declares fixes it at the point the bytes are decoded.
        """
        path = self._cache_path(slug, ext)
        if path.exists() and not self.refresh:
            self.n_cached += 1
            return path.read_text(encoding="utf-8")
        resp = self._request("GET", url)
        if encoding:
            resp.encoding = encoding
        path.write_text(resp.text, encoding="utf-8")
        self.n_fetched += 1
        return resp.text

    def get_json(self, url: str, slug: str, params: Mapping[str, Any] | None = None) -> Any:
        path = self._cache_path(slug, "json")
        if path.exists() and not self.refresh:
            self.n_cached += 1
            return json.loads(path.read_text(encoding="utf-8"))
        resp = self._request("GET", url, params=params)
        payload = resp.json()
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        self.n_fetched += 1
        return payload

    def post_json(
        self,
        url: str,
        slug: str,
        payload: Mapping[str, Any],
        cacheable: "Callable[[Any], bool] | None" = None,
    ) -> Any:
        """POST JSON, caching the response unless ``cacheable`` rejects it.

        JSON-RPC transports application errors inside a 200 response, so a
        denied Odoo call looks like a perfectly good HTTP result. Caching those
        would poison the raw cache: a later run replays the stored error instead
        of retrying the fixed request. ``cacheable`` lets the caller refuse to
        persist such payloads.
        """
        path = self._cache_path(slug, "json")
        if path.exists() and not self.refresh:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cacheable is None or cacheable(cached):
                self.n_cached += 1
                return cached
            path.unlink()  # stale/poisoned entry, re-fetch below
        resp = self._request("POST", url, json=payload, headers={"Content-Type": "application/json"})
        data = resp.json()
        if cacheable is None or cacheable(data):
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        self.n_fetched += 1
        return data

    def report(self) -> str:
        return f"{self.n_fetched} fetched, {self.n_cached} from cache"


def iter_batches(seq: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}
