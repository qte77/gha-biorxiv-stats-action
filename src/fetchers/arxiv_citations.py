"""Semantic Scholar citation enrichment for arxiv paper IDs."""

import time

import requests

API_BASE = "https://api.semanticscholar.org/graph/v1/paper"
FIELDS = "citationCount,referenceCount,influentialCitationCount"
_last_call = 0.0


def get_citations(arxiv_id: str) -> dict:
    """Fetch citation counts from Semantic Scholar.

    Rate limited to 1 RPS. Returns zero-filled dict on any error.
    """
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    url = f"{API_BASE}/ARXIV:{arxiv_id}?fields={FIELDS}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _last_call = time.time()
        return {
            "citation_count": data.get("citationCount", 0),
            "reference_count": data.get("referenceCount", 0),
            "influential_count": data.get("influentialCitationCount", 0),
        }
    except requests.RequestException:
        _last_call = time.time()
        return {"citation_count": 0, "reference_count": 0, "influential_count": 0}


def enrich_row(row: list, citations: dict) -> list:
    """Append citation_count, reference_count, influential_count to a CSV row."""
    return row + [
        citations["citation_count"],
        citations["reference_count"],
        citations["influential_count"],
    ]
