"""Shared fetcher utilities: HTTP client, URL validator, dedup + CSV I/O.

Per-server fetchers (biorxiv.py, arxiv.py) import from this module. The
``dedup_cols`` keyword on the dedup/IO functions makes them schema-agnostic:
biorxiv passes ``(2, 3)`` (DOI, Version); arxiv will pass ``(3, 4)`` (ID,
Version). Defaults match the biorxiv schema for backwards compatibility.
"""

import csv
import os
import time
from os import makedirs
from os.path import dirname, exists
from urllib.parse import urlparse

import requests

# Hosts the action is permitted to fetch from. Extend this set when adding a
# new fetcher (e.g. chemrxiv, psyarxiv).
_ALLOWED_HOSTS = frozenset(
    {
        "api.biorxiv.org",
        "export.arxiv.org",
        "api.semanticscholar.org",
    }
)


def _validate_url(url: str) -> None:
    """Reject non-HTTPS URLs and hosts outside the API allowlist.

    Stricter than a scheme-prefix check: parses the URL and rejects
    userinfo (URL-confusion attacks), fragments (construction bugs),
    non-443 ports (SSRF guard), and hosts not in ``_ALLOWED_HOSTS``.
    """
    parts = urlparse(url)
    if parts.scheme != "https":
        raise ValueError(f"Only HTTPS URLs are allowed, got: {url[:80]}")
    if parts.username or parts.password:
        raise ValueError(f"Userinfo not allowed in URL: {url[:80]}")
    if parts.fragment:
        raise ValueError(f"Fragment not allowed in URL: {url[:80]}")
    if parts.port not in (None, 443):
        raise ValueError(f"Non-443 port not allowed: {url[:80]}")
    if parts.hostname not in _ALLOWED_HOSTS:
        raise ValueError(f"Host not in allowlist: {parts.hostname}")


def get_api_response(url: str, max_retries: int = 3, backoff_base: float = 2.0) -> bytes:
    """Fetch URL with retry/backoff. Raises RuntimeError after max_retries."""
    _validate_url(url)
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException:
            if attempt < max_retries - 1:
                time.sleep(backoff_base**attempt)
            else:
                raise RuntimeError(f"API failed after {max_retries} attempts: {url}") from None


def _load_existing_ids(out_file, dedup_cols: tuple[int, int] = (2, 3)):
    """Load set of (id, version) tuples from existing CSV for dedup.

    ``dedup_cols`` is a 2-tuple of column indices into each CSV row that
    together form the dedup key. Default ``(2, 3)`` matches biorxiv's
    ``[Date, ISOWeek, DOI, Version, ...]`` schema. Arxiv passes ``(3, 4)``
    for ``[Published, ISOWeek, Updated, ID, Version, ...]``.
    """
    existing = set()
    id_col, ver_col = dedup_cols
    min_len = max(id_col, ver_col) + 1
    if exists(out_file):
        with open(out_file, newline="", encoding="UTF8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= min_len:
                    existing.add((row[id_col], str(row[ver_col])))
    return existing


def load_all_existing_ids(data_dir, dedup_cols: tuple[int, int] = (2, 3)):
    """Load all dedup keys from CSVs in data_dir/YYYY/ subdirs."""
    existing = set()
    if not exists(data_dir):
        return existing
    for entry in os.listdir(data_dir):
        subdir = os.path.join(data_dir, entry)
        if not os.path.isdir(subdir) or not entry.isdigit():
            continue
        for fname in os.listdir(subdir):
            if fname.endswith(".csv"):
                existing.update(_load_existing_ids(os.path.join(subdir, fname), dedup_cols))
    return existing


def filter_new_rows(rows, existing_ids, dedup_cols: tuple[int, int] = (2, 3)):
    """Filter out rows whose dedup key is already in ``existing_ids``."""
    id_col, ver_col = dedup_cols
    return [row for row in rows if (row[id_col], str(row[ver_col])) not in existing_ids]


def write_file(
    content,
    file_name,
    out_dir=".",
    header=None,
    dedup_cols: tuple[int, int] = (2, 3),
):
    """Write rows to a CSV file, creating header on first write. Dedupes
    against existing rows on the ``dedup_cols`` key pair.
    """
    out_file = f"{out_dir}/{file_name}.csv"
    fopen_kw = {"file": out_file, "newline": "", "encoding": "UTF8"}
    if not exists(out_file):
        makedirs(dirname(out_file) if dirname(out_file) else out_dir, exist_ok=True)
        with open(mode="w+", **fopen_kw) as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
    existing = _load_existing_ids(out_file, dedup_cols)
    id_col, ver_col = dedup_cols
    new_rows = [row for row in content if (row[id_col], str(row[ver_col])) not in existing]
    if new_rows:
        with open(mode="a+", **fopen_kw) as f:
            writer = csv.writer(f)
            for row in new_rows:
                writer.writerow(row)
