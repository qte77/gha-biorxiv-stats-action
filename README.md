# gha-rxiv-stats-action

Logs a weekly CSV feed of papers submitted to [bioRxiv](https://www.biorxiv.org/)
and [medRxiv](https://www.medrxiv.org/) for selected categories. Cron
cadence is set by the calling workflow.

![Version](https://img.shields.io/badge/version-0.1.0-8A2BE2)
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
3. Fetches paper stats from the bioRxiv/medRxiv API for the configured categories and date range
4. Writes results to CSV files in the output directory
5. Opens a PR with the updated data (auto-merges via squash)

## Usage

```yaml
- uses: qte77/gha-rxiv-feed-action@v0
  with:
    OUT_DIR: "./data"
    DAYS: "1"
    CATEGORIES: "neuroscience"
    SERVER: "biorxiv"
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

<details>
<summary>Multi-server matrix (biorxiv + medrxiv)</summary>

```yaml
strategy:
  max-parallel: 1   # serialize to avoid concurrent auto-PR merges
  matrix:
    include:
      - server: biorxiv
        categories: "bioinformatics,microbiology"
      - server: medrxiv
        categories: "infectious diseases,genetic and genomic medicine"
steps:
  - uses: qte77/gha-rxiv-feed-action@v0
    with:
      OUT_DIR: "./data/${{ matrix.server }}"
      SERVER: ${{ matrix.server }}
      CATEGORIES: ${{ matrix.categories }}
      TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

</details>

## Inputs

| Name | Required | Default | Description |
| ---- | -------- | ------- | ----------- |
| `OUT_DIR` | No | `./data` | Directory to write CSV output files. Convention: `./data/<server>` so multiple servers can coexist when using a matrix. |
| `DAYS` | No | `1` | Number of days back to fetch. |
| `CATEGORIES` | No | _(empty)_ | Comma-separated categories to keep (case-insensitive). Empty keeps all. Filter applied client-side. See [`docs/categories.md`](docs/categories.md) for per-server taxonomies. |
| `SERVER` | No | `biorxiv` | API server: `biorxiv` or `medrxiv`. Same `/details/` endpoint, different `server` path segment. |
| `TOKEN` | No | `${{ github.token }}` | GitHub token for pushing changes. |

## API

Data sourced from:

- bioRxiv: `https://api.biorxiv.org/details/biorxiv/{date1}/{date2}/{cursor}/json`
- medRxiv: `https://api.biorxiv.org/details/medrxiv/{date1}/{date2}/{cursor}/json`

Both share the same CSHL endpoint, distinguished by the `{server}`
path segment.

## License

Apache-2.0 — see [LICENSE](LICENSE).
