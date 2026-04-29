# Configs

Configuration files for experiments, datasets, and pipelines live here.

## gov.cn XXGK Pilot

- `govcn_xxgk_sources.toml`: central-government XXGK source constants, public gateway parameters, request guardrails, artifact path conventions, and status values.
- `govcn_xxgk_query_batches.csv`: reviewed pilot query batches. Each row defines keyword, title/full-text search, fuzzy/precise mode, sort order, page size, max pages, and whether the batch is enabled.

The crawler entry point is `scripts/govcn_xxgk_crawler.py`. Its default `run` mode is cache-first and does not send network requests; live fetching requires `--fetch-live`.
