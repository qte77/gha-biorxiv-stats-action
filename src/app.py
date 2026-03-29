"""Main entry point for bioRxiv / medRxiv stats action."""

import json
from os import getenv

from utils import (
    build_date_range,
    filter_new_rows,
    get_api_response,
    load_all_existing_ids,
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

existing_ids = load_all_existing_ids(OUT_DIR)
print(f"Loaded {len(existing_ids)} existing paper IDs from {OUT_DIR}")


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

    for (year, week), rows in all_weeks.items():
        new_rows = filter_new_rows(rows, existing_ids)
        if new_rows:
            year_dir = f"{OUT_DIR}/{year}"
            write_file(new_rows, str(week), year_dir, HEADER)
            existing_ids.update((row[2], str(row[3])) for row in new_rows)
            print(f"Wrote {year}/week {week}: {len(new_rows)} new papers")


if __name__ == "__main__":
    main()
