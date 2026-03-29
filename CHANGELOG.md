<!-- markdownlint-disable MD024 no-duplicate-heading -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**Types of changes**: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`

## [Unreleased]

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
