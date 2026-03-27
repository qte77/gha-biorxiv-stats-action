"""TDD RED: bioRxiv utils — 6 pytest tests for API, parsing, CSV."""

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from src.utils import (
    build_date_range,
    get_api_response,
    needs_pagination,
    parse_biorxiv_json,
    write_file,
)

# --- Fixtures ---

FIXTURE_JSON = json.dumps({
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
}).encode()


def test_get_api_response_retries():
    """Retry succeeds on 3rd attempt."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"ok"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    call_count = 0

    def side_effect(req, timeout=30):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise URLError("transient")
        return mock_resp

    with patch("src.utils.urlopen", side_effect=side_effect), \
         patch("src.utils.time.sleep"):
        result = get_api_response("https://api.biorxiv.org/test", max_retries=3)

    assert result == b"ok"
    assert call_count == 3


def test_get_api_response_raises_after_max():
    """Raises RuntimeError after max retries exhausted."""
    with patch("src.utils.urlopen", side_effect=URLError("fail")), \
         patch("src.utils.time.sleep"):
        with pytest.raises(RuntimeError):
            get_api_response("https://api.biorxiv.org/test", max_retries=3)


def test_parse_biorxiv_json():
    """Groups papers by ISO week number."""
    result = parse_biorxiv_json(FIXTURE_JSON)
    assert isinstance(result, dict)
    assert 3 in result
    assert len(result[3]) == 2
    first = result[3][0]
    assert first[0] == "2024-01-15"
    assert first[1] == 3
    assert first[2] == "10.1101/2024.01.15.1234"


def test_pagination_detection():
    """Detects when total > count means more pages."""
    assert needs_pagination([{"total": 150, "count": 100}]) is True
    assert needs_pagination([{"total": 50, "count": 100}]) is False


def test_write_file_creates_csv(tmp_path):
    """Creates CSV with header and data rows."""
    header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    rows = [["2024-01-15", 3, "10.1101/2024.01.15.1234", "1", "neuroscience", "Test Paper", "Smith J"]]
    write_file(rows, "3", str(tmp_path), header)
    out_file = tmp_path / "3.csv"
    assert out_file.exists()
    content = out_file.read_text(encoding="UTF8")
    assert "Date" in content
    assert "2024-01-15" in content


def test_date_range_construction():
    """Returns (today-DAYS, today) as ISO date strings."""
    start, end = build_date_range(7)
    today = date.today()
    assert start == (today - timedelta(days=7)).isoformat()
    assert end == today.isoformat()
    assert len(start) == 10
