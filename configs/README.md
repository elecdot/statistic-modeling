# Configs

Configuration files for experiments, datasets, and pipelines live here.

## gov.cn XXGK Pilot

- `govcn_xxgk_sources.toml`: central-government XXGK source constants, public gateway parameters, request guardrails, artifact path conventions, and status values.
- `govcn_xxgk_query_batches.csv`: reviewed pilot query batches. Each row defines keyword, title/full-text search, fuzzy/precise mode, sort order, page size, max pages, and whether the batch is enabled.
- `govcn_xxgk_all_query_batches.csv`: blank-keyword all-policy query batch for the independent 2020-2025 central XXGK corpus.

The crawler entry point is `scripts/govcn_xxgk_crawler.py`. Its default `run` mode is cache-first and does not send network requests; live fetching requires `--fetch-live`.

## Manual SRDI Jurisdiction Overrides

- `manual_srdi_jurisdiction_overrides_v1.csv`: reviewed corrections used by the
  original 2020-2025 v0/v1 manual SRDI paths.
- `manual_srdi_jurisdiction_overrides_v2.csv`: v2 correction set for the
  2019-2024 full-text corpus. It carries the v1 reviewed corrections forward
  and adds 2019 supplement review decisions, including one reviewed-original
  安徽 row that mentions a central program but remains a local notice.
