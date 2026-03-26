"""TDD RED: bioRxiv utils — 6 pytest tests for API, parsing, CSV."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from utils import (
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


# --- Test 1: retry succeeds on 3rd attempt ---

def test_get_api_response_retries():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = b"ok"
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    from urllib.error import URLError

    call_count = 0

    def side_effect(req, timeout=30):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise URLError("transient")
        return mock_resp

    with patch("utils.urlopen", side_effect=side_effect), \
         patch("utils.time.sleep"):
        result = get_api_response("https://api.biorxiv.org/test", max_retries=3)

    assert result == b"ok"
    assert call_count == 3


# --- Test 2: raises RuntimeError after max retries ---

def test_get_api_response_raises_after_max():
    from urllib.error import URLError

    with patch("utils.urlopen", side_effect=URLError("fail")), \
         patch("utils.time.sleep"):
        with pytest.raises(RuntimeError):
            get_api_response("https://api.biorxiv.org/test", max_retries=3)


# --- Test 3: parse_biorxiv_json groups by ISO week ---

def test_parse_biorxiv_json():
    result = parse_biorxiv_json(FIXTURE_JSON)

    assert isinstance(result, dict)
    # 2024-01-15 and 2024-01-16 are both ISO week 3
    assert 3 in result
    assert len(result[3]) == 2
    # Each row: [Date, ISOWeek, DOI, Version, Category, Title, Authors]
    first = result[3][0]
    assert first[0] == "2024-01-15"
    assert first[1] == 3
    assert first[2] == "10.1101/2024.01.15.1234"


# --- Test 4: needs_pagination returns True when total > count ---

def test_pagination_detection():
    messages_needs_more = [{"total": 150, "count": 100}]
    messages_complete = [{"total": 50, "count": 100}]

    assert needs_pagination(messages_needs_more) is True
    assert needs_pagination(messages_complete) is False


# --- Test 5: write_file creates CSV with header + rows ---

def test_write_file_creates_csv(tmp_path):
    header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    rows = [
        ["2024-01-15", 3, "10.1101/2024.01.15.1234", "1", "neuroscience", "Test Paper", "Smith J"],
    ]

    write_file(rows, "3", str(tmp_path), header)

    out_file = tmp_path / "3.csv"
    assert out_file.exists()
    content = out_file.read_text(encoding="UTF8")
    assert "Date" in content
    assert "ISOWeek" in content
    assert "2024-01-15" in content


# --- Test 6: build_date_range returns (today-DAYS, today) ---

def test_date_range_construction():
    days = 7
    start, end = build_date_range(days)

    today = date.today()
    expected_start = (today - timedelta(days=days)).isoformat()
    expected_end = today.isoformat()

    assert start == expected_start
    assert end == expected_end
    # Format: YYYY-MM-DD
    assert len(start) == 10
    assert start[4] == "-"
