"""Dispatch tests for src/app.py.

Tests `main()` only — the per-server logic is covered by fetcher tests.
Patches `_run_arxiv` / `_run_biorxiv` so the test never touches HTTP.
"""

from unittest.mock import patch

import pytest

from src.app import main


def test_main_dispatches_to_arxiv(monkeypatch):
    """SERVER=arxiv routes to _run_arxiv only."""
    monkeypatch.setenv("SERVER", "arxiv")
    monkeypatch.setenv("TOPICS", "cat:cs.AI")
    monkeypatch.setenv("OUT_DIR", "./data/arxiv-test")

    with (
        patch("src.app._run_arxiv", create=True) as mock_arxiv,
        patch("src.app._run_biorxiv", create=True) as mock_bio,
    ):
        main()

    mock_arxiv.assert_called_once()
    mock_bio.assert_not_called()


def test_main_dispatches_to_biorxiv(monkeypatch):
    """SERVER=biorxiv routes to _run_biorxiv only."""
    monkeypatch.setenv("SERVER", "biorxiv")
    monkeypatch.setenv("OUT_DIR", "./data/biorxiv-test")

    with (
        patch("src.app._run_arxiv", create=True) as mock_arxiv,
        patch("src.app._run_biorxiv", create=True) as mock_bio,
    ):
        main()

    mock_bio.assert_called_once()
    mock_arxiv.assert_not_called()


def test_main_raises_on_invalid_env(monkeypatch):
    """validate_env is called inside main; bad SERVER raises ValueError."""
    monkeypatch.setenv("SERVER", "chemrxiv")

    with (
        patch("src.app._run_arxiv", create=True),
        patch("src.app._run_biorxiv", create=True),
    ):
        with pytest.raises(ValueError, match="SERVER"):
            main()
