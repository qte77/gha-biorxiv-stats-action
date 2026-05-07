"""Utility functions for bioRxiv / medRxiv stats action."""

import csv
import json
import os
import time
from datetime import date, timedelta
from os import makedirs
from os.path import dirname, exists
from urllib.error import URLError
from urllib.request import Request, urlopen


def _ensure_https(url: str) -> None:
    """Reject non-HTTPS URLs to prevent file:/ and custom scheme access."""
    if not url.lower().startswith("https://"):
        raise ValueError(f"Only HTTPS URLs are allowed, got: {url[:50]}")


def get_api_response(url: str, max_retries: int = 3, backoff_base: float = 2.0) -> bytes:
    """Fetch URL with retry/backoff. Raises RuntimeError after max_retries."""
    _ensure_https(url)
    req = Request(url)
    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=120) as resp:  # noqa: S310  # nosec B310
                assert resp.status == 200, f"bioRxiv API returned non-200: {resp.status}"
                return resp.read()
        except (URLError, AssertionError):
            if attempt < max_retries - 1:
                time.sleep(backoff_base**attempt)
            else:
                raise RuntimeError(
                    f"bioRxiv API failed after {max_retries} attempts: {url}"
                ) from None


def parse_biorxiv_json(data: bytes, categories: set | None = None) -> dict:
    """Parse bioRxiv JSON bytes, return dict keyed by (year, week) tuple.

    Each value is a list of rows:
    [Date, ISOWeek, DOI, Version, Category, Title, Authors]

    If ``categories`` is a non-empty set, entries whose category is not in the
    set are discarded (case-insensitive match on the bioRxiv category string).
    """
    payload = json.loads(data)
    out: dict = {}
    cat_filter = {c.strip().lower() for c in categories} if categories else None
    for entry in payload.get("collection", []):
        cat = entry.get("category", "")
        if cat_filter and cat.strip().lower() not in cat_filter:
            continue
        pub_date = entry["date"]  # YYYY-MM-DD
        iso = date.fromisoformat(pub_date).isocalendar()
        key = (iso[0], iso[1])  # (year, week)
        if key not in out:
            out[key] = []
        out[key].append(
            [
                pub_date,
                iso[1],
                entry.get("doi", ""),
                entry.get("version", ""),
                cat,
                entry.get("title", ""),
                entry.get("authors", ""),
            ]
        )
    return out


def needs_pagination(messages: list) -> bool:
    """Return True when the API total exceeds the current page count."""
    if not messages:
        return False
    msg = messages[0]
    total = int(msg.get("total", 0))
    count = int(msg.get("count", 0))
    return total > count


def build_date_range(days: int) -> tuple:
    """Return (start_date, end_date) as YYYY-MM-DD strings.

    end_date is today; start_date is today minus `days`.
    """
    today = date.today()
    start = today - timedelta(days=days)
    return start.isoformat(), today.isoformat()


def _load_existing_ids(out_file):
    """Load set of (doi, version) from existing CSV for dedup."""
    existing = set()
    if exists(out_file):
        with open(out_file, newline="", encoding="UTF8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if len(row) >= 4:
                    existing.add((row[2], str(row[3])))
    return existing


def load_all_existing_ids(data_dir):
    """Load all (doi, version) pairs from CSVs in data_dir/YYYY/ subdirs."""
    existing = set()
    if not exists(data_dir):
        return existing
    for entry in os.listdir(data_dir):
        subdir = os.path.join(data_dir, entry)
        if not os.path.isdir(subdir) or not entry.isdigit():
            continue
        for fname in os.listdir(subdir):
            if fname.endswith(".csv"):
                existing.update(_load_existing_ids(os.path.join(subdir, fname)))
    return existing


def prune_existing_csvs(data_dir: str, categories: set | None) -> int:
    """Rewrite each CSV in data_dir/YYYY/ keeping only rows whose Category is
    in the set (case-insensitive). Returns total rows removed. No-op when
    categories is empty/None.
    """
    if not categories or not exists(data_dir):
        return 0
    cat_filter = {c.strip().lower() for c in categories}
    removed = 0
    for entry in os.listdir(data_dir):
        subdir = os.path.join(data_dir, entry)
        if not os.path.isdir(subdir) or not entry.isdigit():
            continue
        for fname in os.listdir(subdir):
            if not fname.endswith(".csv"):
                continue
            path = os.path.join(subdir, fname)
            with open(path, newline="", encoding="UTF8") as f:
                rows = list(csv.reader(f))
            if not rows:
                continue
            header, *body = rows
            kept = [r for r in body if len(r) >= 5 and r[4].strip().lower() in cat_filter]
            if len(kept) != len(body):
                removed += len(body) - len(kept)
                with open(path, "w", newline="", encoding="UTF8") as f:
                    w = csv.writer(f)
                    w.writerow(header)
                    w.writerows(kept)
    return removed


def filter_new_rows(rows, existing_ids):
    """Filter out rows whose (doi, version) is already known."""
    return [row for row in rows if (row[2], str(row[3])) not in existing_ids]


def write_file(content, file_name, out_dir=".", header=None):
    """Write rows to a CSV file, creating header on first write."""
    out_file = f"{out_dir}/{file_name}.csv"
    fopen_kw = {"file": out_file, "newline": "", "encoding": "UTF8"}
    if not exists(out_file):
        makedirs(dirname(out_file) if dirname(out_file) else out_dir, exist_ok=True)
        with open(mode="w+", **fopen_kw) as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
    existing = _load_existing_ids(out_file)
    new_rows = [row for row in content if (row[2], str(row[3])) not in existing]
    if new_rows:
        with open(mode="a+", **fopen_kw) as f:
            writer = csv.writer(f)
            for row in new_rows:
                writer.writerow(row)
