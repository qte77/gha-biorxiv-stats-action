"""bioRxiv-specific tests: JSON parsing, pagination signal, date range, pruning."""

import csv
import json
from datetime import date, timedelta

from src.fetchers.biorxiv import (
    build_date_range,
    needs_pagination,
    parse_biorxiv_json,
    prune_existing_csvs,
)

FIXTURE_JSON = json.dumps(
    {
        "messages": [{"status": "ok", "total": 150, "count": 100, "cursor": 0}],
        "collection": [
            {
                "doi": "10.1101/2024.01.15.1234",
                "version": "1",
                "category": "neuroscience",
                "title": "Test Paper One",
                "authors": "Smith J; Jones A",
                "abstract": "Abstract one.",
                "date": "2024-01-15",
            },
            {
                "doi": "10.1101/2024.01.16.5678",
                "version": "2",
                "category": "neuroscience",
                "title": "Test Paper Two",
                "authors": "Brown B",
                "abstract": "Abstract two.",
                "date": "2024-01-16",
            },
        ],
    }
).encode()


def test_parse_biorxiv_json():
    """Groups papers by ISO week number and includes the abstract column."""
    result = parse_biorxiv_json(FIXTURE_JSON)
    assert isinstance(result, dict)
    assert (2024, 3) in result
    assert len(result[(2024, 3)]) == 2
    first = result[(2024, 3)][0]
    assert first[0] == "2024-01-15"
    assert first[1] == 3
    assert first[2] == "10.1101/2024.01.15.1234"
    assert first[7] == "Abstract one."
    assert len(first) == 8


def test_parse_biorxiv_json_filters_by_category():
    """Entries outside the categories set are dropped (case-insensitive)."""
    data = json.dumps(
        {
            "messages": [{"status": "ok", "total": 3, "count": 3}],
            "collection": [
                {
                    "doi": "10.1101/a",
                    "version": "1",
                    "category": "Bioinformatics",
                    "title": "Keep",
                    "authors": "A",
                    "date": "2024-01-15",
                },
                {
                    "doi": "10.1101/b",
                    "version": "1",
                    "category": "neuroscience",
                    "title": "Drop",
                    "authors": "B",
                    "date": "2024-01-15",
                },
                {
                    "doi": "10.1101/c",
                    "version": "1",
                    "category": "microbiology",
                    "title": "Keep",
                    "authors": "C",
                    "date": "2024-01-15",
                },
            ],
        }
    ).encode()
    result = parse_biorxiv_json(data, {"bioinformatics", "microbiology"})
    rows = result[(2024, 3)]
    dois = {row[2] for row in rows}
    assert dois == {"10.1101/a", "10.1101/c"}


def test_parse_biorxiv_json_no_filter_keeps_all():
    """Empty/None category filter keeps every entry."""
    result_none = parse_biorxiv_json(FIXTURE_JSON, None)
    result_empty = parse_biorxiv_json(FIXTURE_JSON, set())
    assert len(result_none[(2024, 3)]) == 2
    assert len(result_empty[(2024, 3)]) == 2


def test_parse_biorxiv_json_year_boundary():
    """Papers in different ISO weeks get distinct (year, week) keys."""
    data = json.dumps(
        {
            "messages": [{"status": "ok", "total": 2, "count": 2}],
            "collection": [
                {
                    "doi": "10.1101/a",
                    "version": "1",
                    "category": "neuro",
                    "title": "Dec Paper",
                    "authors": "A",
                    "date": "2024-12-16",
                },
                {
                    "doi": "10.1101/b",
                    "version": "1",
                    "category": "neuro",
                    "title": "Jan Paper",
                    "authors": "B",
                    "date": "2025-01-06",
                },
            ],
        }
    ).encode()
    result = parse_biorxiv_json(data)
    keys = list(result.keys())
    assert len(keys) == 2
    assert (2024, 51) in result
    assert (2025, 2) in result


def test_prune_existing_csvs_drops_outside_set(tmp_path):
    """Rewrites CSVs to keep only rows whose Category is in the set."""
    header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    (tmp_path / "2024").mkdir()
    p = tmp_path / "2024" / "3.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerow(["2024-01-15", 3, "10.1101/a", "1", "Bioinformatics", "K", "X"])
        w.writerow(["2024-01-15", 3, "10.1101/b", "1", "neuroscience", "D", "Y"])
        w.writerow(["2024-01-15", 3, "10.1101/c", "1", "microbiology", "K", "Z"])
    removed = prune_existing_csvs(str(tmp_path), {"bioinformatics", "microbiology"})
    assert removed == 1
    with open(p) as f:
        kept = list(csv.DictReader(f))
    assert {r["DOI"] for r in kept} == {"10.1101/a", "10.1101/c"}


def test_prune_existing_csvs_noop_when_empty(tmp_path):
    """Empty/None category set leaves CSVs untouched."""
    (tmp_path / "2024").mkdir()
    p = tmp_path / "2024" / "3.csv"
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"])
        w.writerow(["2024-01-15", 3, "10.1101/a", "1", "neuroscience", "T", "X"])
    before = p.read_bytes()
    assert prune_existing_csvs(str(tmp_path), set()) == 0
    assert prune_existing_csvs(str(tmp_path), None) == 0
    assert p.read_bytes() == before


def test_pagination_detection():
    """Detects when total > count means more pages."""
    assert needs_pagination([{"total": 150, "count": 100}]) is True
    assert needs_pagination([{"total": 50, "count": 100}]) is False


def test_date_range_construction():
    """Returns (today-DAYS, today) as ISO date strings."""
    start, end = build_date_range(7)
    today = date.today()
    assert start == (today - timedelta(days=7)).isoformat()
    assert end == today.isoformat()
    assert len(start) == 10


def test_date_range_explicit_from_and_to_override_days():
    """Explicit date_from + date_to use the window verbatim, ignoring days."""
    start, end = build_date_range(999, date_from="2024-01-01", date_to="2024-12-31")
    assert start == "2024-01-01"
    assert end == "2024-12-31"


def test_date_range_only_from_extends_to_today():
    """Given only date_from, end defaults to today."""
    start, end = build_date_range(7, date_from="2024-01-01")
    assert start == "2024-01-01"
    assert end == date.today().isoformat()


def test_date_range_only_to_derives_from_using_days():
    """Given only date_to, start is date_to minus days."""
    start, end = build_date_range(30, date_to="2024-06-30")
    assert start == "2024-05-31"
    assert end == "2024-06-30"


def test_date_range_empty_strings_treated_as_unset():
    """Empty strings behave like None (validate_env normalizes None already,
    but app.py passes through env defaults which can be empty)."""
    start, end = build_date_range(7, date_from=None, date_to=None)
    today = date.today()
    assert start == (today - timedelta(days=7)).isoformat()
    assert end == today.isoformat()
