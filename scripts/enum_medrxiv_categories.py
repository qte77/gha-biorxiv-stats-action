"""Enumerate every distinct medRxiv category over a window.

One-off helper to keep `docs/categories.md` honest. medRxiv's category
taxonomy is not published in a canonical machine-readable form, so the
ground truth is whatever the `/details/medrxiv/` API has returned in
practice. Run periodically (e.g. annually) and diff the output against
the doc.

Usage:
    python scripts/enum_medrxiv_categories.py

Tune `START`/`END` for a wider/narrower window. Convergence stops the
scan once `CONVERGE_AFTER` consecutive pages add no new category; bump
it if you suspect long-tail categories are still being missed.
"""

import sys
import time

import requests

START = "2024-01-01"
END = "2026-05-24"
PAGE = 30
URL = "https://api.biorxiv.org/details/medrxiv/{start}/{end}/{cursor}/json"
CONVERGE_AFTER = 500


def fetch(cursor: int) -> dict:
    url = URL.format(start=START, end=END, cursor=cursor)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def main() -> int:
    cats: set[str] = set()
    cursor = 0
    streak = 0
    page_idx = 0
    first = fetch(cursor)
    total = int(first["messages"][0]["total"])
    print(f"total papers in window: {total}", file=sys.stderr)

    def absorb(payload: dict) -> int:
        before = len(cats)
        for e in payload.get("collection", []):
            c = (e.get("category") or "").strip()
            if c:
                cats.add(c)
        return len(cats) - before

    new = absorb(first)
    print(f"page {page_idx:>4} cursor {cursor:>6}: +{new} (total {len(cats)})", file=sys.stderr)
    cursor += PAGE
    page_idx += 1
    while cursor < total:
        try:
            payload = fetch(cursor)
        except Exception as exc:
            print(f"page {page_idx} cursor {cursor}: error {exc}", file=sys.stderr)
            time.sleep(2)
            continue
        new = absorb(payload)
        streak = 0 if new else streak + 1
        if new or page_idx % 50 == 0:
            print(
                f"page {page_idx:>4} cursor {cursor:>6}: +{new} "
                f"(total {len(cats)}, streak {streak})",
                file=sys.stderr,
            )
        if streak >= CONVERGE_AFTER:
            print(f"converged after {streak} pages with no new categories", file=sys.stderr)
            break
        cursor += PAGE
        page_idx += 1
        time.sleep(0.1)
    for c in sorted(cats, key=str.lower):
        print(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
