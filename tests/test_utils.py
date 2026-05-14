"""TDD RED: bioRxiv utils — pytest tests for API, parsing, CSV."""

import csv
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.utils import (
    _validate_url,
    build_date_range,
    filter_new_rows,
    get_api_response,
    load_all_existing_ids,
    needs_pagination,
    parse_biorxiv_json,
    prune_existing_csvs,
    write_file,
)

# --- Fixtures ---

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
                "date": "2024-01-15",
            },
            {
                "doi": "10.1101/2024.01.16.5678",
                "version": "2",
                "category": "neuroscience",
                "title": "Test Paper Two",
                "authors": "Brown B",
                "date": "2024-01-16",
            },
        ],
    }
).encode()


def _make_response(data: bytes = b"ok"):
    """Create a mock requests.Response with successful raise_for_status."""
    resp = MagicMock()
    resp.content = data
    resp.raise_for_status = MagicMock()
    return resp


def test_get_api_response_retries():
    """Fails 2x with ConnectionError then succeeds — returns data on 3rd call."""
    resp = _make_response(b"ok")
    side_effects = [
        requests.ConnectionError("transient"),
        requests.ConnectionError("transient"),
        resp,
    ]
    with (
        patch("src.utils.requests.get", side_effect=side_effects) as mock_get,
        patch("src.utils.time.sleep"),
    ):
        result = get_api_response("https://api.biorxiv.org/test", max_retries=3)
    assert result == b"ok"
    assert mock_get.call_count == 3


def test_get_api_response_raises_after_max():
    """Raises RuntimeError after max retries exhausted."""
    with (
        patch("src.utils.requests.get", side_effect=requests.ConnectionError("fail")),
        patch("src.utils.time.sleep"),
    ):
        with pytest.raises(RuntimeError):
            get_api_response("https://api.biorxiv.org/test", max_retries=3)


@pytest.mark.parametrize(
    "host",
    ["api.biorxiv.org", "export.arxiv.org", "api.semanticscholar.org"],
)
def test_validate_url_accepts_allowlisted_hosts(host: str) -> None:
    """All three allowlisted API hosts pass validation."""
    _validate_url(f"https://{host}/some/path")


@pytest.mark.parametrize(
    "url",
    [
        "http://api.biorxiv.org/x",
        "file:///etc/passwd",
        "gopher://api.biorxiv.org/x",
        "ftp://api.biorxiv.org/x",
    ],
)
def test_validate_url_rejects_non_https(url: str) -> None:
    """Any scheme other than https raises ValueError."""
    with pytest.raises(ValueError, match="HTTPS"):
        _validate_url(url)


def test_validate_url_rejects_userinfo() -> None:
    """URLs with user:pass@host are rejected to prevent URL-confusion attacks."""
    with pytest.raises(ValueError, match="[Uu]serinfo"):
        _validate_url("https://user:pass@api.biorxiv.org/x")


def test_validate_url_rejects_fragment() -> None:
    """URLs with a fragment are rejected (defensive against construction bugs)."""
    with pytest.raises(ValueError, match="[Ff]ragment"):
        _validate_url("https://api.biorxiv.org/x#frag")


def test_validate_url_rejects_unknown_host() -> None:
    """Hosts outside the API allowlist are rejected."""
    with pytest.raises(ValueError, match="[Hh]ost"):
        _validate_url("https://evil.example.com/x")


def test_validate_url_rejects_non_default_port() -> None:
    """Non-443 ports are rejected (block SSRF to internal services)."""
    with pytest.raises(ValueError, match="port"):
        _validate_url("https://api.biorxiv.org:8080/x")


def test_parse_biorxiv_json():
    """Groups papers by ISO week number."""
    result = parse_biorxiv_json(FIXTURE_JSON)
    assert isinstance(result, dict)
    assert (2024, 3) in result
    assert len(result[(2024, 3)]) == 2
    first = result[(2024, 3)][0]
    assert first[0] == "2024-01-15"
    assert first[1] == 3
    assert first[2] == "10.1101/2024.01.15.1234"


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


def test_write_file_creates_csv(tmp_path):
    """Creates CSV with header and data rows."""
    header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    rows = [
        ["2024-01-15", 3, "10.1101/2024.01.15.1234", "1", "neuroscience", "Test Paper", "Smith J"]
    ]
    year_dir = str(tmp_path / "2024")
    write_file(rows, "3", year_dir, header)
    out_file = tmp_path / "2024" / "3.csv"
    assert out_file.exists()
    content = out_file.read_text(encoding="UTF8")
    assert "Date" in content
    assert "2024-01-15" in content


def test_dedup_filters_existing_rows(tmp_path):
    """filter_new_rows removes rows with known DOI+version."""
    existing = {("10.1101/known.1", "1")}
    rows = [
        ["2024-01-15", 3, "10.1101/known.1", "1", "neuro", "Known", "A"],
        ["2024-01-16", 3, "10.1101/new.1", "1", "neuro", "New", "B"],
    ]
    result = filter_new_rows(rows, existing)
    assert len(result) == 1
    assert result[0][2] == "10.1101/new.1"


def test_write_file_no_duplicates(tmp_path):
    """Writing same rows twice doesn't duplicate."""
    header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    rows = [["2024-01-15", 3, "10.1101/2024.01.15.1234", "1", "neuro", "Paper", "Smith"]]
    year_dir = str(tmp_path / "2024")
    write_file(rows, "3", year_dir, header)
    write_file(rows, "3", year_dir, header)  # write again
    content = (tmp_path / "2024" / "3.csv").read_text(encoding="UTF8")
    lines = [line for line in content.strip().split("\n") if line]
    assert len(lines) == 2  # header + 1 data row, no duplicate


def test_load_all_existing_ids_walks_year_dirs(tmp_path):
    """load_all_existing_ids finds IDs across year subdirectories."""
    # Create 2024/3.csv
    (tmp_path / "2024").mkdir()
    with open(tmp_path / "2024" / "3.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ISOWeek", "DOI", "Version", "Cat", "Title", "Authors"])
        w.writerow(["2024-01-15", 3, "10.1101/a", "1", "neuro", "A", "X"])
    # Create 2025/1.csv
    (tmp_path / "2025").mkdir()
    with open(tmp_path / "2025" / "1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ISOWeek", "DOI", "Version", "Cat", "Title", "Authors"])
        w.writerow(["2025-01-06", 1, "10.1101/b", "2", "neuro", "B", "Y"])
    ids = load_all_existing_ids(str(tmp_path))
    assert ("10.1101/a", "1") in ids
    assert ("10.1101/b", "2") in ids
    assert len(ids) == 2


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
    assert (2024, 51) in result  # Dec 16 = ISO week 51 of 2024
    assert (2025, 2) in result  # Jan 6 = ISO week 2 of 2025


def test_date_range_construction():
    """Returns (today-DAYS, today) as ISO date strings."""
    start, end = build_date_range(7)
    today = date.today()
    assert start == (today - timedelta(days=7)).isoformat()
    assert end == today.isoformat()
    assert len(start) == 10
