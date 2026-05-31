# Competitive landscape

Public GitHub repos that share part of this stack's scope —
"arxiv → recurring digest" ingestion. None implement the full
producer + LLM-eval split, but they bracket the design space and
set the bar for adoption-side simplicity.

This doc is feed-side context; the eval-specific comparison
(LLM filter, structured extraction) is repeated only where it
clarifies why the producer/eval split is shaped the way it is.
For the eval-side roadmap see [`gha-rxiv-paper-eval/docs/design.md`](https://github.com/qte77/gha-rxiv-paper-eval/blob/main/docs/design.md).

## Surveyed repos

Surfaced via a GitHub issues search
(`https://github.com/search?q=lidar+3d+print+bim&type=issues`,
2026-05). The query is incidental — it just exposed bots that
auto-file paper listings as issues.

| Repo | ⭐ | Issues | Commits | State |
|---|---:|---:|---:|---|
| [`luohongk/Embodied-AI-Daily`](https://github.com/luohongk/Embodied-AI-Daily) | 261 | 715 | 689 | Active |
| [`DongZhouGu/arxiv-daily`](https://github.com/DongZhouGu/arxiv-daily) | 83 | 941 | 9 | Set-and-forget |
| [`LeeKyungwook/get-arxiv-noti`](https://github.com/LeeKyungwook/get-arxiv-noti) | 35 | 1.5k+ | 1 | Dormant fork |
| [`A-suozhang/GetArxivDaily`](https://github.com/A-suozhang/GetArxivDaily) | 6 | 211 | 0 | Code removed; issues remain |

Counts are point-in-time snapshots. Re-verify before quoting.

## Pattern + cadence

| Repo | Source | Filter | Output | Cadence |
|---|---|---|---|---|
| Embodied-AI-Daily | arxiv API | Topic-scoped keyword sets (VLN/VLA/SLAM/Gaussian Splatting) | Issue per digest, top-10 | Daily |
| arxiv-daily | Scrapes `arxiv.org/list/cs/new` (HTML, not API) | Keyword list in `config.py` | Issue per match | Scheduled |
| get-arxiv-noti | Unknown (README unreachable) | Keywords | Issue per match | Dormant |
| GetArxivDaily | Removed | Removed | Historical issues only | – |

## Capability matrix

`feed-action` covers the ingest + normalize + persist columns;
`paper-eval` covers the filter + extract columns. The competitors
fuse both halves into a single repo.

| Capability | Embodied-AI-Daily | arxiv-daily | get-arxiv-noti | feed-action | paper-eval |
|---|:-:|:-:|:-:|:-:|:-:|
| arxiv ingest | ✓ | ✓ HTML | ✓ | ✓ API | (consumes feed) |
| bioRxiv / medRxiv | – | – | – | ✓ | ✓ |
| Citation enrichment (S2) | – | – | – | ✓ | – |
| Persistent CSV layer | – | – | – | ✓ | ✓ (artifact) |
| Outbound URL allowlist | – | – | – | ✓ | ✓ |
| Keyword filter | ✓ | ✓ | ✓ | – | ✓ (category pre-filter) |
| LLM relevance filter | – | – | – | – | ✓ |
| Structured extraction (JSON schema) | – | – | – | – | ✓ |
| Reusable as action/workflow | – | – | – | ✓ composite | ✓ workflow_call |
| Documented local entrypoint | – | – | – | ✓ Makefile | ✓ `make smoke` |

## Where the producer differs

- **Multi-server.** No competitor covers biomed. Adding a new
  preprint server here is a per-format `parse_*` + `build_date_*`
  on top of the shared HTTP / dedup / write machinery; competitors
  would need a rewrite per server.
- **Persistent data layer.** Output is `data/<server>/<year>/<isoweek>.csv`
  on the consumer repo, not transient issue bodies. Downstream
  consumers (paper-eval, dashboards, ad-hoc analysis) read CSV;
  nothing has to scrape issue text.
- **Composite action.** Consumers `uses: qte77/gha-rxiv-feed-action@vX.Y.Z`
  in their own workflow. Competitors are forks: you copy the repo,
  edit its keyword config, then run it.
- **Outbound HTTP allowlist** (`api.biorxiv.org`, `export.arxiv.org`,
  `api.semanticscholar.org`). Defense-in-depth chokepoint not present
  in the competitor scripts.

## Where competitors win

- **Onboarding-surface footprint.** Embodied-AI-Daily ships one
  README + one Python script in one repo and reached 261⭐ on
  visibility alone. The unit a user discovers is a *named feed*
  (`"the Embodied-AI Daily"`). This stack is a *toolkit* — the
  user-facing surface is whatever consumer repo wires it up, which
  is harder to brand or discover.
- **Zero LLM dependency.** Keyword match has no Models quota /
  PAT considerations. Cheaper to operate; weaker as a filter.

## Implications for this repo

1. **Keep the producer/eval split.** The keyword-bot pattern is
   load-bearing on the competitors' simplicity but caps their
   filtering ceiling. The LLM relevance step + structured
   extraction in paper-eval are the moat; folding them back into a
   single-repo bot would copy the competitors' weakness.
2. **Consider a reference consumer repo** — a thin downstream that
   pins both this action and paper-eval to a tag and posts triage
   issues. Gives the stack a single-repo discovery surface
   comparable to `Embodied-AI-Daily` without merging the layers.
   Not in scope for this repo; tracked aspirationally.
3. **Don't import competitor data.** Their issues are downstream
   keyword digests of the same arxiv API this repo already calls.
   Scraping them would be a regression in schema fidelity.
