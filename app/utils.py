"""Utility functions for bioRxiv / medRxiv stats action."""
import csv
import json
import time
from datetime import date, timedelta
from os import makedirs
from os.path import dirname, exists
from urllib.error import URLError
from urllib.request import Request, urlopen


def get_api_response(url: str, max_retries: int = 3, backoff_base: float = 2.0) -> bytes:
    """Fetch URL with retry/backoff. Raises RuntimeError after max_retries."""
    if not url.lower().startswith("https://"):
        raise ValueError("URL must use HTTPS")
    req = Request(url)
    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=120) as resp:
                assert resp.status == 200, \
                    f"bioRxiv API returned non-200: {resp.status}"
                return resp.read()
        except (URLError, AssertionError):
            if attempt < max_retries - 1:
                time.sleep(backoff_base ** attempt)
            else:
                raise RuntimeError(
                    f"bioRxiv API failed after {max_retries} attempts: {url}"
                ) from None


def parse_biorxiv_json(data: bytes) -> dict:
    """Parse bioRxiv JSON bytes, return dict keyed by ISO week number.

    Each value is a list of rows:
    [Date, ISOWeek, DOI, Version, Category, Title, Authors]
    """
    payload = json.loads(data)
    out: dict = {}
    for entry in payload.get("collection", []):
        pub_date = entry["date"]  # YYYY-MM-DD
        iso_week = date.fromisoformat(pub_date).isocalendar().week
        if iso_week not in out:
            out[iso_week] = []
        out[iso_week].append([
            pub_date,
            iso_week,
            entry.get("doi", ""),
            entry.get("version", ""),
            entry.get("category", ""),
            entry.get("title", ""),
            entry.get("authors", ""),
        ])
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


def write_file(
    content: list,
    file_name: str,
    out_dir: str = ".",
    header=None,
) -> None:
    """Write rows to a CSV file, creating header on first write."""
    out_file = f"{out_dir}/{file_name}.csv"
    fopen_kw = {"file": out_file, "newline": "", "encoding": "UTF8"}
    if not exists(out_file):
        makedirs(dirname(out_file) or out_dir, exist_ok=True)
        with open(mode="w+", **fopen_kw) as f:
            writer = csv.writer(f)
            if header:
                writer.writerow(header)
    with open(mode="a+", **fopen_kw) as f:
        writer = csv.writer(f)
        for row in content:
            writer.writerow(row)
