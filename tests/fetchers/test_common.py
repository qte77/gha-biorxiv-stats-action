"""Shared fetcher tests: HTTP retry, URL validator, dedup/IO with dedup_cols."""

import csv
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.fetchers.common import (
    _validate_url,
    filter_new_rows,
    get_api_response,
    load_all_existing_ids,
    write_file,
)


def _make_response(data: bytes = b"ok"):
    """Create a mock requests.Response with successful raise_for_status."""
    resp = MagicMock()
    resp.content = data
    resp.raise_for_status = MagicMock()
    return resp


# --- HTTP retry ---


def test_get_api_response_retries():
    """Fails 2x with ConnectionError then succeeds — returns data on 3rd call."""
    resp = _make_response(b"ok")
    side_effects = [
        requests.ConnectionError("transient"),
        requests.ConnectionError("transient"),
        resp,
    ]
    with (
        patch("src.fetchers.common.requests.get", side_effect=side_effects) as mock_get,
        patch("src.fetchers.common.time.sleep"),
    ):
        result = get_api_response("https://api.biorxiv.org/test", max_retries=3)
    assert result == b"ok"
    assert mock_get.call_count == 3


def test_get_api_response_raises_after_max():
    """Raises RuntimeError after max retries exhausted."""
    with (
        patch(
            "src.fetchers.common.requests.get",
            side_effect=requests.ConnectionError("fail"),
        ),
        patch("src.fetchers.common.time.sleep"),
    ):
        with pytest.raises(RuntimeError):
            get_api_response("https://api.biorxiv.org/test", max_retries=3)


# --- URL validator ---


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


# --- Dedup/IO (biorxiv schema by default) ---


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


def test_dedup_filters_existing_rows():
    """filter_new_rows removes rows with known DOI+version (biorxiv default)."""
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
    write_file(rows, "3", year_dir, header)
    content = (tmp_path / "2024" / "3.csv").read_text(encoding="UTF8")
    lines = [line for line in content.strip().split("\n") if line]
    assert len(lines) == 2


def test_load_all_existing_ids_walks_year_dirs(tmp_path):
    """load_all_existing_ids finds IDs across year subdirectories."""
    (tmp_path / "2024").mkdir()
    with open(tmp_path / "2024" / "3.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ISOWeek", "DOI", "Version", "Cat", "Title", "Authors"])
        w.writerow(["2024-01-15", 3, "10.1101/a", "1", "neuro", "A", "X"])
    (tmp_path / "2025").mkdir()
    with open(tmp_path / "2025" / "1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "ISOWeek", "DOI", "Version", "Cat", "Title", "Authors"])
        w.writerow(["2025-01-06", 1, "10.1101/b", "2", "neuro", "B", "Y"])
    ids = load_all_existing_ids(str(tmp_path))
    assert ("10.1101/a", "1") in ids
    assert ("10.1101/b", "2") in ids
    assert len(ids) == 2


# --- dedup_cols parametrize: proves schema-agnostic dedup ---


@pytest.mark.parametrize(
    ("dedup_cols", "header", "row_keep", "row_dup"),
    [
        (
            (2, 3),  # biorxiv: (DOI, Version)
            ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"],
            ["2024-01-15", 3, "10.1101/a", "1", "neuro", "A", "X"],
            ["2024-01-15", 3, "10.1101/a", "1", "neuro", "Dup", "Y"],
        ),
        (
            (3, 4),  # arxiv: (ID, Version) — Published/ISOWeek/Updated come first
            ["Published", "ISOWeek", "Updated", "ID", "Version", "Title", "Categories"],
            ["2026-03-23T17:00:00Z", 13, "2026-03-23T17:00:00Z", "2603.00001", "1", "'T'", "cs"],
            ["2026-03-23T17:00:00Z", 13, "2026-03-23T17:00:00Z", "2603.00001", "1", "'D'", "cs"],
        ),
    ],
)
def test_dedup_cols_parametrize(tmp_path, dedup_cols, header, row_keep, row_dup):
    """write_file/load_all_existing_ids/filter_new_rows respect dedup_cols.

    Default (2, 3) covers biorxiv (DOI, Version). Arxiv schema uses (3, 4)
    (ID, Version). Both paths must dedupe correctly without sharing keys.
    """
    year_dir = str(tmp_path / "2026")
    write_file([row_keep], "13", year_dir, header, dedup_cols=dedup_cols)
    write_file([row_dup], "13", year_dir, header, dedup_cols=dedup_cols)
    out_file = tmp_path / "2026" / "13.csv"
    with open(out_file) as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2  # header + 1 data row (dup filtered)

    ids = load_all_existing_ids(str(tmp_path), dedup_cols=dedup_cols)
    expected_key = (row_keep[dedup_cols[0]], str(row_keep[dedup_cols[1]]))
    assert expected_key in ids

    new = filter_new_rows(
        [row_keep, ["2026-03-24T00:00:00Z", 13, "u", "fresh", "1", "x", "y"]],
        ids,
        dedup_cols=dedup_cols,
    )
    assert len(new) == 1
