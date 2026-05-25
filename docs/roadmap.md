# Roadmap

Lightweight tracking of intent. Issues + the milestone view on GitHub
are the source of truth; this file is the narrative summary.

## Short-term (in flight)

- Land bioRxiv newline scrub + workflow_dispatch backfill inputs
  (this PR).
- Land `fix(action)`: guard the auto-commit step when `OUT_DIR`
  doesn't exist (#129) — prevents transient-API-failure cascades.
- Backfill arXiv historic weeks 11–19 with the new
  `Authors`+`Abstract` schema once #129 merges and the
  date-range path is in (a single `gh workflow run` with
  `date_from`/`date_to`).

## Medium-term

- **chemRxiv fetcher** — Cloudflare-fronted public API needs a
  verified UA to bypass the challenge page (issue #69).
- **psyArXiv fetcher** — OSF taxonomy is depth-1 with 234 nodes;
  needs a coarse-grouping decision before wiring (`docs/categories.md`).
- **Backfill orchestration helper** — small script that loops
  `gh workflow run` over a series of monthly windows for very long
  backfills (the arXiv API caps at ~50k results per query).

## Long-term

- **Incremental dedup at the API boundary** — bio/med pagination
  currently fetches every cursor and dedupes client-side; smarter
  cursor stops once `since_doi` is seen would save bandwidth on
  unchanged historic weeks.
- **Schema versioning column** — explicit `SchemaVersion` column on
  each row so downstream consumers can branch on row format instead
  of column-count sniffing.
- **`scripts/migrate_csv_schema.py` re-run hook** — automate the
  one-shot migration when the schema grows again, integrated into
  the release workflow.
