# gha-biorxiv-stats-action

Logs daily stats of papers submitted to [biorxiv.org](https://www.biorxiv.org/).

![Version](https://img.shields.io/badge/version-0.1.0-8A2BE2)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![Update biorxiv.org stats](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/write-biorxiv-stats.yml/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/write-biorxiv-stats.yml)
[![CodeFactor](https://www.codefactor.io/repository/github/qte77/gha-biorxiv-stats-action/badge)](https://www.codefactor.io/repository/github/qte77/gha-biorxiv-stats-action)
[![CodeQL](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/codeql.yml/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/codeql.yml)
[![Dependabot](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/dependabot/dependabot-updates)
[![Ruff](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/ruff.yml/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/ruff.yml)
[![Tests](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/test.yml/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/test.yml)

## What it does

1. Checks out the calling repository
2. Sets up Python via uv
3. Fetches paper stats from the bioRxiv/medRxiv API for the configured categories and date range
4. Writes results to CSV files in the output directory
5. Opens a PR with the updated data (auto-merges via squash)

## Usage

```yaml
- uses: qte77/gha-biorxiv-stats-action@v0
  with:
    OUT_DIR: './data'
    DAYS: '1'
    CATEGORIES: 'neuroscience'
    SERVER: 'biorxiv'
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Name | Required | Default | Description |
|------|----------|---------|-------------|
| `OUT_DIR` | No | `./data` | Directory to write CSV output files |
| `DAYS` | No | `1` | Number of days back to fetch |
| `CATEGORIES` | No | _(empty)_ | bioRxiv category filter (e.g. neuroscience). Empty for all |
| `SERVER` | No | `biorxiv` | API server: `biorxiv` or `medrxiv` |
| `TOKEN` | No | `${{ github.token }}` | GitHub token for pushing changes |

## API

Data sourced from `https://api.biorxiv.org/details/{server}/{date1}/{date2}/{cursor}/json`.

## License

Apache-2.0 — see [LICENSE](LICENSE).
