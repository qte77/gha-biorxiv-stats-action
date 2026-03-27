"""Main entry point for bioRxiv / medRxiv stats action."""

import json
from os import getenv

from utils import (
    build_date_range,
    get_api_response,
    needs_pagination,
    parse_biorxiv_json,
    write_file,
)

OUT_DIR = getenv("OUT_DIR", "./data")
DAYS = int(getenv("DAYS", "1"))
CATEGORIES = getenv("CATEGORIES", "")
SERVER = getenv("SERVER", "biorxiv")  # biorxiv or medrxiv

HEADER = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
PAGE_SIZE = 100
BASE_URL = f"https://api.biorxiv.org/details/{SERVER}"


def main() -> None:
    """Fetch, parse, and write bioRxiv stats as weekly CSV files."""
    start_date, end_date = build_date_range(DAYS)
    cursor = 0
    all_weeks: dict = {}

    while True:
        url = f"{BASE_URL}/{start_date}/{end_date}/{cursor}/json"
        if CATEGORIES:
            url = f"{url}?category={CATEGORIES}"

        data = get_api_response(url)
        payload = json.loads(data)
        messages = payload.get("messages", [])

        weekly = parse_biorxiv_json(data)
        for week, rows in weekly.items():
            all_weeks.setdefault(week, []).extend(rows)

        if not needs_pagination(messages):
            break
        cursor += PAGE_SIZE

    for week_num, rows in all_weeks.items():
        write_file(rows, str(week_num), OUT_DIR, HEADER)
        print(f"Wrote week {week_num}: {len(rows)} papers")


if __name__ == "__main__":
    main()
