"""bioRxiv / medRxiv fetcher: JSON parsing, pagination signal, date range, pruning.

Same API endpoint (`api.biorxiv.org/details/{server}/...`) serves both servers
with a different `{server}` path segment. The functions here are server-agnostic
within the bio/med pair.
"""

import csv
import json
import os
from datetime import date, timedelta
from os.path import exists


def parse_biorxiv_json(data: bytes, categories: set | None = None) -> dict:
    """Parse bioRxiv JSON bytes, return dict keyed by (year, week) tuple.

    Each value is a list of rows:
    [Date, ISOWeek, DOI, Version, Category, Title, Authors, Abstract]

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
        key = (iso[0], iso[1])
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
                entry.get("abstract", ""),
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


def build_date_range(
    days: int,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple:
    """Return (start_date, end_date) as YYYY-MM-DD strings.

    Explicit ``date_from``/``date_to`` override the rolling ``days`` window
    (useful for backfill dispatches). When only one bound is given, the
    other is derived: missing ``date_to`` defaults to today; missing
    ``date_from`` is ``date_to`` minus ``days``.

    Both inputs must be ``YYYY-MM-DD`` when set; ``validate_env`` rejects
    malformed values before this is called.
    """
    if date_from:
        end = date_to or date.today().isoformat()
        return date_from, end
    if date_to:
        end_d = date.fromisoformat(date_to)
        return (end_d - timedelta(days=days)).isoformat(), date_to
    today = date.today()
    return (today - timedelta(days=days)).isoformat(), today.isoformat()


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
