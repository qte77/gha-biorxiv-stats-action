"""Migrate every CSV under ``<data_root>/<server>/<year>/*.csv`` to the
current canonical header for that server.

Driven by the same headers the action writes today (kept in lockstep
with ``src/app.py`` ``_BIORXIV_HEADER`` / ``_ARXIV_HEADER``). Delegates
the rewrite to ``src.fetchers.common.upgrade_csv_header`` so the strict
prefix-safety rule applies uniformly — legacy files with renamed columns
(e.g. arXiv 2024's ``Weekday`` vs current ``ISOWeek``) are left alone.

Idempotent. Safe to re-run.

Usage:
    python scripts/migrate_csv_schema.py [data_root]   # default: data
"""

import sys
from pathlib import Path

from src.fetchers.common import upgrade_csv_header

_BIORXIV = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors", "Abstract"]
_ARXIV = [
    "Published",
    "ISOWeek",
    "Updated",
    "ID",
    "Version",
    "Title",
    "Categories",
    "Authors",
    "Abstract",
]
_HEADERS = {"biorxiv": _BIORXIV, "medrxiv": _BIORXIV, "arxiv": _ARXIV}


def main(data_root: str = "data") -> int:
    """Return the number of CSV files actually upgraded."""
    root = Path(data_root)
    if not root.is_dir():
        print(f"data root not found: {root}", file=sys.stderr)
        return 0
    upgraded = 0
    for server_dir in sorted(root.iterdir()):
        if not server_dir.is_dir() or server_dir.name not in _HEADERS:
            continue
        header = _HEADERS[server_dir.name]
        for year_dir in sorted(server_dir.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            for csv_path in sorted(year_dir.glob("*.csv")):
                if upgrade_csv_header(str(csv_path), header):
                    upgraded += 1
                    print(f"upgraded {csv_path}")
    print(f"upgraded {upgraded} CSV file(s) under {root}", file=sys.stderr)
    return upgraded


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1] if len(sys.argv) > 1 else "data") >= 0 else 1)
