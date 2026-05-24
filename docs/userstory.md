# User stories

Seed list of who this action serves and what they need from it.
Expand as new consumers come online.

## Maintainer of a downstream paper-evaluation pipeline

> As a consumer of the CSV feed, I want each row to carry the abstract
> so my LLM-prefilter step doesn't have to make a second per-DOI API
> call for every paper.

Covered by: schema change in #116 (Abstract column on all three
servers; Authors added to arXiv).

## Fork operator wanting broader category coverage

> As the maintainer of a fork that needs wider topic/category sets
> than the upstream defaults, I want to override them per-repo
> without forking the workflow file (which would diverge on every
> upstream sync).

Covered by: `vars.ARXIV_TOPICS` / `vars.BIORXIV_CATEGORIES` /
`vars.MEDRXIV_CATEGORIES` introduced in #117.

## Fork operator needing to backfill historic weeks

> As the operator of a fork whose data dir was wiped or only covers
> recent weeks, I want to re-fetch a historic window in a single
> dispatch — for any of the three servers — without editing the
> workflow file.

Covered by: `DATE_FROM`/`DATE_TO` honored by bio/med fetcher
(unreleased) + `workflow_dispatch.inputs.date_from/date_to/server`
(this PR).

## Downstream consumer reading CSVs in plain text

> As someone scanning the raw `.csv` in `cat`, `less`, or GitHub's
> raw blob view, I want each logical paper to occupy exactly one
> line so row counts and visual scanning behave intuitively.

Covered by: `scrub_newlines()` in `src/fetchers/common.py` applied
to title + abstract in both fetchers (this PR).

## Author of a new fetcher (chemRxiv, psyArXiv, ...)

> As someone adding a new preprint server, I want to reuse the
> existing pagination, dedup, retry, URL allowlist, and CSV-write
> machinery without copy-pasting code.

Partially covered by: `src/fetchers/common.py` (HTTP, URL
validation, dedup, write). Adding a server still requires its own
`parse_*` and `build_date_*` per-format helpers. Tracked aspirationally
in `docs/roadmap.md`.
