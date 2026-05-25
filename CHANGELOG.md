<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

## [Unreleased]

### Added

- **`workflow_dispatch.inputs` for ad-hoc backfill** in the reference
  `update-rxiv-feed.yaml` workflow: `date_from`, `date_to`, `server`.
  Enables `gh workflow run ... -f date_from=YYYY-MM-DD -f server=biorxiv`
  without editing the workflow file. Defaults are empty so cron
  behaviour is unchanged.

### Fixed

- **bioRxiv title and abstract now scrubbed of `\n`/`\r`** like arXiv
  already was. CSVs were always RFC-4180 valid (csv.writer quotes
  embedded newlines), but viewers that aren't CSV-aware (`cat`,
  `wc -l`, GitHub raw blob) treated each embedded newline as a row
  boundary and fragmented the display. New helper
  `scrub_newlines()` in `src/fetchers/common.py` is now the single
  source of truth used by both fetchers.

### Added

- **Abstract column on every CSV row** for arXiv, bioRxiv, and medRxiv;
  arXiv rows additionally include `Authors`. Both fields are already
  returned by the existing API calls — zero extra requests. arXiv schema
  grows 7 → 9 cols (`[Published, ISOWeek, Updated, ID, Version, Title,
  Categories, Authors, Abstract]`); bio/med grows 7 → 8 cols (trailing
  `Abstract`). Dedup keys and existing column indices unchanged.
  Pre-existing CSVs keep their narrower schema; loader and prune
  tolerate mixed widths (#116).
- **`DATE_FROM`/`DATE_TO` honored on the bioRxiv/medRxiv path.**
  Previously declared as "arXiv only" — now overrides the rolling
  `DAYS` window for bio/med too. Enables wide-window backfill
  dispatches. `filter_new_rows` still dedupes, so this fills gaps in
  coverage; rewriting narrow-schema rows requires clearing the data
  dir first (#118).
- `scripts/enum_medrxiv_categories.py` — one-off helper to re-enumerate
  the medRxiv category taxonomy by paginating the `/details/medrxiv/`
  API until convergence (#115).

### Changed

- **medRxiv category list flipped from "sampled, 29" to "canonical, 51"**
  in `docs/categories.md`. Re-enumerated over a 2.4-year window
  (41,446 papers); convergence after a 500-page streak with no new
  category. Adds 22 categories including emergency medicine, oncology
  subspecialties (orthopedics, otolaryngology), and palliative
  medicine. API returns lowercase ASCII; client-side matching is
  already case-insensitive (#115).
- **Workflow matrix in `.github/workflows/update-rxiv-feed.yaml` now
  driven by repo variables.** `vars.ARXIV_TOPICS`,
  `vars.BIORXIV_CATEGORIES`, `vars.MEDRXIV_CATEGORIES` override the
  inline defaults when set (mirrors the existing `vars.DAYS` pattern).
  Defaults preserved exactly — upstream behavior unchanged when vars
  unset. Forks can broaden categories without source-level divergence
  by setting Settings → Variables (#117).

---

## [0.2.1] - 2026-05-24

### Changed

- **Floating major-version tag `v0` removed.** Consumers must pin a
  specific tag (`@v0.2.1`) or commit SHA. Aligns with the SHA-pinning
  posture (no mutable refs in `uses:`). README usage examples updated
  to `@v0.2.1`.
- Composite action `action.yaml` steps pinned to full-length commit SHAs
  to match the workflow-files policy (consistency with #74 and
  defense-in-depth against upstream tag rewrites). Surfaced by a
  downstream consumer fork whose repo enforces
  `sha_pinning_required: true`. Supersedes #112.
- `github/codeql-action/{init,autobuild,analyze}` bumped 4.35.4 →
  4.35.5 (SHA `9e0d7b8`). Supersedes #108.

### Fixed

- arxiv probe call in `_arxiv_paginate` no longer crashes the job when
  `export.arxiv.org` is transiently unavailable. The probe now matches
  the per-page error-handling pattern: log and early-exit with an empty
  result so the matrix job completes and the next scheduled run
  self-heals. Triggered by run #26009245522.

### Added

- Historical arxiv data migrated from `qte77/gha-arxiv-stats-action`
  (renamed to `gha-arxiv-stats-action-legacy` and archived after the
  fold-in) under `data/arxiv/`: 6 files in `2024/` (legacy 6-column schema:
  `Published,Weekday,Updated,ID,Version,Title`) and 10 files in
  `2026/` (current 7-column schema with `Categories`). Schema drift is
  harmless — the dedup key `(ID, Version)` is at the same indices
  `(3, 4)` in both, and weekly CSVs aren't re-appended after the week
  closes. Closes #72.
- arxiv row added to `.github/workflows/update-rxiv-feed.yaml` matrix.
  Weekly cron now fetches arxiv + biorxiv + medrxiv. Action invocation
  passes `TOPICS: ${{ matrix.topics }}`; bio/med rows leave it empty,
  arxiv row sets the default CS/AI cluster.

---

## [0.2.0] - 2026-05-15

### Added

- `SERVER=arxiv` dispatch in `src/app.py` exposing arXiv as a first-class
  fetcher alongside bioRxiv/medRxiv. Closes #72.
- New action inputs `TOPICS`, `INCLUDE_CITATIONS`, `SEMANTIC_SCHOLAR_API_KEY`,
  `MAX_AGE_DAYS`, `DATE_FROM`, `DATE_TO`, `PAGE_SIZE`, `MAX_PAGES` —
  arxiv-specific; ignored for bioRxiv/medRxiv runs.

### Changed

- **BREAKING**: `SERVER` default flipped from `biorxiv` to `arxiv`.
  Consumers omitting `SERVER` in their workflow will silently switch
  from bioRxiv to arXiv. Pin `@v0.1.0` to keep the bioRxiv default.
- **BREAKING**: `OUT_DIR` default flipped from `./data` to `./data/arxiv`.
- `src/app.py` rewritten: side-effect-free at module level (all env
  reading + filesystem + network moved into `main()` / `_run_*`
  helpers). Imports use `src.fetchers.*` / `src.validation` so the same
  module works in pytest and at runtime; `action.yaml` PYTHONPATH
  adjusted to `${{ github.action_path }}` (was `.../src`).
- README usage example now leads with arxiv (no explicit inputs needed);
  bioRxiv/medRxiv moved into separate subsections.
- `docs/categories.md` reordered arxiv-first with the canonical arXiv
  taxonomy (20 top-level groups) and `TOPICS` default rationale.

### Security

### Renamed

- HTTP URL validation hardened in `src/utils.py`: scheme is parsed
  (not prefix-matched), userinfo (`user:pass@host`) is rejected to
  prevent URL-confusion attacks, fragments are rejected (defensive
  against URL-construction bugs), non-443 ports are rejected as an
  SSRF guard, and the hostname is checked against an allowlist of
  three API hosts (`api.biorxiv.org`, `export.arxiv.org`,
  `api.semanticscholar.org`). New `_validate_url()` replaces
  `_ensure_https()`. Covered by 7 new pytest tests (#88).

### Renamed

- Repo `gha-biorxiv-stats-action` → `gha-rxiv-stats-action` to reflect
  multi-server scope (bioRxiv + medRxiv today; chemRxiv, psyArXiv,
  arXiv pending — see #69, #70, #72). GitHub auto-redirects old URLs;
  in-repo references (README badges, Usage, action.yaml `name`)
  updated (#78).

### Added

- Client-side `CATEGORIES` filter in `parse_biorxiv_json` (the
  bioRxiv `/details/` API has no server-side category filter, so the
  prior `?category=` URL query was a silent no-op) (#76).
- `prune_existing_csvs()` rewrites historical CSVs on each run so
  rows outside the current category set are dropped retroactively (#76).
- `docs/categories.md` documenting per-server taxonomies (bioRxiv
  canonical 25, medRxiv sampled 29; chemRxiv and psyArXiv tracked as
  separate fetcher work in #69 and #70) (#76).
- README inline `strategy.matrix` example for fetching biorxiv +
  medrxiv with a single workflow (#77).
- `lychee.toml` project-local config with accept codes `[200, 202, 204,
  301, 401, 403, 429]` and the workflow-badge URL exclude pattern;
  prerequisite for the multi-fetcher work in #72 (#87).
- `src/fetchers/arxiv.py` arxiv Atom XML parser (`parse_arxiv_url`,
  `build_date_query`, `extract_categories`, `get_parsed_output`,
  `get_total_results`, `encode_feedparser_dict`) — ported from
  `qte77/gha-arxiv-stats-action` per #72. Not yet wired into the
  action; PR B4 will add the `SERVER=arxiv` dispatch (#TBD-B3).
- `src/fetchers/arxiv_citations.py` Semantic Scholar enrichment for
  arxiv papers, rate-limited to 1 RPS, opt-in via `INCLUDE_CITATIONS`
  (#TBD-B3).
- `src/validation.py` env-var validator covering `OUT_DIR` (path
  traversal), `SERVER` (allowlist of biorxiv/medrxiv/arxiv),
  `INCLUDE_CITATIONS` (bool string), integer vars
  (`DAYS`/`MAX_AGE_DAYS`/`PAGE_SIZE`/`MAX_PAGES`), date vars
  (`DATE_FROM`/`DATE_TO`), and the `TOPICS`-required-when-`SERVER=arxiv`
  conditional. Adapted (not verbatim) from `gha-arxiv-stats-action` —
  the source validated stale env vars unused by the actual app
  (#TBD-B3).
- `feedparser>=6.0.12` runtime dep added to `pyproject.toml` (#TBD-B3).

### Changed

- All workflow actions pinned to full-length commit SHAs:
  `actions/checkout` → `de0fac2` (v6.0.2),
  `astral-sh/setup-uv` → `37802ad` (v7.6.0),
  `github/codeql-action/*` → `e46ed2c` (v4.35.3),
  `callowayproject/bump-my-version` → `e6ecdc3` (1.3.0) (#74).
- Expanded `.gitignore` (Python, IDE, secrets, Claude per-user, OS
  patterns) (#75).
- README inputs table cross-links `CATEGORIES` to
  `docs/categories.md` and notes the `./data/<server>` convention for
  multi-server use (#77).
- README tagline updated to mention bioRxiv + medRxiv; API section
  lists both URLs (#78).
- Ruff lint config tightened to parity with `gha-arxiv-stats-action`:
  added rule sets `S` (flake8-bandit) and `C90` (mccabe) with
  `max-complexity = 10`, and ignored `S101` only in `tests/**`. Bumped
  dev dep to `ruff>=0.15.10`. Prerequisite for #72 (#87).
- HTTP client in `src/utils.py:get_api_response` migrated from
  `urllib.request.urlopen` to `requests`. The retry loop now catches
  `requests.RequestException` (strict superset of the prior `URLError`
  catch), preserving retry/backoff semantics. Unifies the HTTP stack
  with `gha-arxiv-stats-action` ahead of folding it in per #72 (#88).
- `src/utils.py` split into `src/fetchers/biorxiv.py` (parse, pagination,
  date range, prune) and `src/fetchers/common.py` (HTTP + URL validator +
  shared dedup/IO) to prepare for the arxiv merge (#72). Shared dedup
  functions gain a `dedup_cols` keyword (default `(2, 3)` for biorxiv
  `(DOI, Version)`; arxiv will pass `(3, 4)` for `(ID, Version)`).
  `src/utils.py` and `tests/test_utils.py` deleted; tests redistributed
  to `tests/fetchers/test_{biorxiv,common}.py` with patch paths updated.
  No behaviour change. 25 → 27 tests (#TBD-B2).

### Removed

- `.lycheeignore` — content moved into `lychee.toml` `exclude` array
  to prevent drift between two configs (#87).
- `# noqa: S310` and `# nosec B310` suppressions in `src/utils.py` —
  both rules are urllib-specific and no longer apply after the
  `requests` migration (#88).

### Fixed

- `Lint MD and Links` workflow no longer fails at startup with
  `issues: write` permission missing for the reusable workflow's
  nested `notify` job (#73).
- Replace `assert resp.status == 200` in `src/utils.py` (S101 in
  `src/`) with explicit `if resp.status != 200: raise URLError(...)`.
  Retry/backoff semantics preserved — the existing `except URLError`
  clause already catches it (#87).

---

## [0.1.0] - 2026-03-29

---

### Added

- HTTPS validation for API server URLs (#10)
- Test and lint CI workflow (#12)

### Changed

- Rename `app/` to `src/` for standard project layout (#10)
- Migrate to `uv` package manager, DRY workflow (#12)
- Migrate license to Apache-2.0 (#13)
- Bump `actions/checkout` from 4 to 6 (#2)
- Bump `actions/setup-python` from 5 to 6 (#3)
- Bump `callowayproject/bump-my-version` from 1.2.7 to 1.3.0 (#4)

### Fixed

- Use temp file for tree entries to avoid argument list overflow (#5)
- Cast biorxiv API total/count to int for pagination (#6)
- Reduce default DAYS to 1, increase timeout, clear category (#7)
- Defensive `.get()` in `needs_pagination` for missing keys (#8)
- Update workflow `APP_DIR` from `app/` to `src/` (#11)

## [0.0.0] - 2026-03-26

### Added

- Composite `action.yaml` with inputs (OUT_DIR, DAYS, CATEGORIES, SERVER, PY_VER, TOKEN) and branding
- biorxiv API integration (`https://api.biorxiv.org/details/{server}/{date1}/{date2}/{cursor}/json`)
- 6 pytest tests for API fetch, parsing, and CSV output

---
