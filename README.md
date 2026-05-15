# gha-rxiv-feed-action

Logs a weekly CSV feed of papers submitted to [arXiv](https://arxiv.org/),
[bioRxiv](https://www.biorxiv.org/), and [medRxiv](https://www.medrxiv.org/)
for selected categories. Cron cadence is set by the calling workflow.

![Version](https://img.shields.io/badge/version-0.2.0-8A2BE2)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Update rxiv feed](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/update-rxiv-feed.yaml/badge.svg)](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/update-rxiv-feed.yaml)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/gha-rxiv-feed-action/badge)](https://www.codefactor.io/repository/github/qte77/gha-rxiv-feed-action)
[![CodeQL](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/codeql.yml/badge.svg)](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/codeql.yml)
[![Dependabot](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/dependabot/dependabot-updates)
[![Ruff](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/ruff.yml/badge.svg)](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/ruff.yml)
[![Tests](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/test.yml/badge.svg)](https://github.com/qte77/gha-rxiv-feed-action/actions/workflows/test.yml)

## What it does

1. Checks out the calling repository
2. Sets up Python via uv
3. Fetches paper stats from the selected `SERVER` (arXiv by default; bioRxiv or medRxiv on request)
4. Writes results to CSV files in `./data/<server>/`
5. Opens a PR with the updated data (auto-merges via squash)

## Usage

Default: fetch the last week of arXiv submissions in CS/AI categories.

```yaml
- uses: qte77/gha-rxiv-feed-action@v0
  with:
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### arXiv with custom topics + citation enrichment

```yaml
- uses: qte77/gha-rxiv-feed-action@v0
  with:
    TOPICS: "cat:cs.CV+OR+cat:cs.LG"
    INCLUDE_CITATIONS: "true"
    SEMANTIC_SCHOLAR_API_KEY: ${{ secrets.SEMANTIC_SCHOLAR_KEY }}
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### bioRxiv / medRxiv

```yaml
- uses: qte77/gha-rxiv-feed-action@v0
  with:
    SERVER: "biorxiv"
    OUT_DIR: "./data/biorxiv"
    CATEGORIES: "neuroscience,bioinformatics"
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Multi-server matrix

```yaml
strategy:
  max-parallel: 1   # serialize to avoid concurrent auto-PR merges
  matrix:
    include:
      - server: arxiv
        topics: "cat:cs.CV+OR+cat:cs.LG"
      - server: biorxiv
        categories: "bioinformatics,microbiology"
      - server: medrxiv
        categories: "infectious diseases,genetic and genomic medicine"
steps:
  - uses: qte77/gha-rxiv-feed-action@v0
    with:
      OUT_DIR: "./data/${{ matrix.server }}"
      SERVER: ${{ matrix.server }}
      TOPICS: ${{ matrix.topics }}
      CATEGORIES: ${{ matrix.categories }}
      TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Name | Required | Default | Description |
| ---- | -------- | ------- | ----------- |
| `SERVER` | No | `arxiv` | API server: `arxiv`, `biorxiv`, or `medrxiv`. |
| `OUT_DIR` | No | `./data/arxiv` | Directory to write CSV output files. Convention: `./data/<server>` so multiple servers can coexist when using a matrix. |
| `TOPICS` | No | `cat:cs.CV+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.AI+OR+cat:cs.NE+OR+cat:cs.RO` | arXiv search_query (URL-encoded, OR-joined). See [`docs/categories.md`](docs/categories.md#arxiv). arXiv only. |
| `INCLUDE_CITATIONS` | No | `false` | Enrich arXiv rows with Semantic Scholar citation counts. arXiv only. |
| `SEMANTIC_SCHOLAR_API_KEY` | No | _(empty)_ | Optional Semantic Scholar API key for higher rate limits. arXiv only. |
| `MAX_AGE_DAYS` | No | `7` | Skip arXiv papers published more than N days ago. Ignored when `DATE_FROM` is set. arXiv only. |
| `DATE_FROM` | No | _(empty)_ | YYYY-MM-DD lower bound on arXiv `submittedDate`. arXiv only. |
| `DATE_TO` | No | _(empty)_ | YYYY-MM-DD upper bound on arXiv `submittedDate`. Empty = today. arXiv only. |
| `PAGE_SIZE` | No | `1000` | arXiv pagination page size. arXiv only. |
| `MAX_PAGES` | No | `5` | Cap on arXiv pagination pages per run. arXiv only. |
| `DAYS` | No | `1` | Number of days back to fetch. bioRxiv/medRxiv only. |
| `CATEGORIES` | No | _(empty)_ | Comma-separated bioRxiv/medRxiv categories to keep. See [`docs/categories.md`](docs/categories.md). bioRxiv/medRxiv only. |
| `TOKEN` | No | `${{ github.token }}` | GitHub token for pushing changes. |

## API

Data sourced from:

- arXiv: `https://export.arxiv.org/api/query?search_query={topics}&start={n}&max_results={k}&sortBy=submittedDate` (Atom XML)
- bioRxiv: `https://api.biorxiv.org/details/biorxiv/{date1}/{date2}/{cursor}/json`
- medRxiv: `https://api.biorxiv.org/details/medrxiv/{date1}/{date2}/{cursor}/json`

Outbound requests are locked to an allowlist of API hosts
(`api.biorxiv.org`, `export.arxiv.org`, `api.semanticscholar.org`) and
require HTTPS on port 443; non-allowlisted hosts raise `ValueError` at
the validator boundary. Extend `_ALLOWED_HOSTS` in
`src/fetchers/common.py` when adding a new fetcher.

## Data

`data/<server>/<year>/<isoweek>.csv` — one CSV per ISO week per server.
The action appends new rows on each run and dedupes by
`(DOI, Version)` for bioRxiv/medRxiv or `(ID, Version)` for arXiv.

`data/arxiv/` is pre-populated with 16 historical weekly CSVs migrated
from [`qte77/gha-arxiv-stats-action-legacy`](https://github.com/qte77/gha-arxiv-stats-action-legacy)
(formerly `gha-arxiv-stats-action`; archived after the fold-in) when
this action absorbed its scope (issue #72). The 6 files under
`data/arxiv/2024/` use a legacy 6-column schema
(`Published,Weekday,Updated,ID,Version,Title`); files from 2026 onward
use the current 7-column schema with a trailing `Categories` column.
The dedup key columns are at the same indices in both schemas, so the
mixed-schema state is safe; new writes go to current-week files only.

## License

Apache-2.0 — see [LICENSE](LICENSE).
