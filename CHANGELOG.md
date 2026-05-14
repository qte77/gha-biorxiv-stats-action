<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

## [Unreleased]

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

### Removed

- `.lycheeignore` — content moved into `lychee.toml` `exclude` array
  to prevent drift between two configs (#87).

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
