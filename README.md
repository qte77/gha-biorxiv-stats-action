# gha-biorxiv-stats-action

Logs daily stats of papers submitted to [biorxiv.org](https://www.biorxiv.org/).

![Version](https://img.shields.io/badge/version-0.0.0-8A2BE2)
[![Update biorxiv.org stats](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/write-biorxiv-stats.yml/badge.svg)](https://github.com/qte77/gha-biorxiv-stats-action/actions/workflows/write-biorxiv-stats.yml)

## Usage

```yaml
- uses: qte77/gha-biorxiv-stats-action@v0
  with:
    OUT_DIR: './data'
    DAYS: '1'
    CATEGORIES: 'neuroscience'
    SERVER: 'biorxiv'
    PY_VER: '3.10'
    TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `OUT_DIR` | Output directory for CSV files | `./data` |
| `DAYS` | Number of days to fetch | `1` |
| `CATEGORIES` | Comma-separated biorxiv categories | `neuroscience` |
| `SERVER` | API server (`biorxiv` or `medrxiv`) | `biorxiv` |
| `PY_VER` | Python version | `3.10` |
| `TOKEN` | GitHub token for signed commits | `${{ github.token }}` |

## API

Data sourced from `https://api.biorxiv.org/details/{server}/{date1}/{date2}/{cursor}/json`.

## License

BSD 3-Clause — see [LICENSE](LICENSE).
