"""Semantic Scholar citation enrichment tests."""

from unittest.mock import MagicMock, patch

import requests

import src.fetchers.arxiv_citations as citations_module
from src.fetchers.arxiv_citations import enrich_row, get_citations


def _make_response(data: dict):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def test_get_citations_success():
    """Returns correct dict when API responds with citation data."""
    payload = {"citationCount": 42, "referenceCount": 10, "influentialCitationCount": 5}
    citations_module._last_call = 0.0
    with patch("src.fetchers.arxiv_citations.requests.get", return_value=_make_response(payload)):
        result = get_citations("2406.04221")
    assert result == {"citation_count": 42, "reference_count": 10, "influential_count": 5}


def test_get_citations_not_found():
    """Returns zero-filled dict on HTTPError (graceful fallback)."""
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    citations_module._last_call = 0.0
    with patch("src.fetchers.arxiv_citations.requests.get", return_value=resp):
        result = get_citations("9999.99999")
    assert result == {"citation_count": 0, "reference_count": 0, "influential_count": 0}


def test_get_citations_respects_rate_limit():
    """Calls time.sleep between successive requests to respect 1 RPS limit."""
    payload = {"citationCount": 1, "referenceCount": 0, "influentialCitationCount": 0}
    citations_module._last_call = 0.0

    with (
        patch("src.fetchers.arxiv_citations.requests.get", return_value=_make_response(payload)),
        patch("src.fetchers.arxiv_citations.time") as mock_time,
    ):
        mock_time.time.return_value = 0.0
        get_citations("2406.00001")
        mock_time.time.return_value = 0.5
        get_citations("2406.00002")

    mock_time.sleep.assert_called()


def test_enrich_row():
    """Appends citation columns to a CSV row."""
    row = ["2024-06-06T16:20:07Z", 23, "2024-06-07T10:00:00Z", "2406.04221", 1, "'A Title'"]
    citations = {"citation_count": 42, "reference_count": 10, "influential_count": 5}
    result = enrich_row(row, citations)
    assert result == row + [42, 10, 5]
    assert len(result) == len(row) + 3
