# Statistic Modeling

Research workflow for policy text collection and analysis. Maybe panel construction later.

## Stack

- Python >= 3.11
- uv for environment and dependency management
- just for integrate reusable instructions

## Structure

- `configs/`: experiment and pipeline configuration files.
- `data/`: local datasets and derived data artifacts.
- `docs/`: notes, reports, and project documentation.
- `notebooks/`: exploratory notebooks.
- `outputs/`: generated figures, tables, and run outputs.
- `scripts/`: one-off or reusable research scripts.
- `src/`: importable Python package code.

## Open Loops

- [x] Define a reusable XXGK search configuration before expanding collection.
  Start from the current central-government probe in
  `notebooks/20_central_gov_xxgk_explore.py`. Record each query as data, not as
  one-off notebook edits: keyword, title/full-text search, fuzzy/precise match,
  sort order, page size, max pages, and research reason.
- [x] Probe full-text search before expanding title-search pages.
  The live pilot confirmed `fieldName=""`, `isPreciseSearch=0`, and
  `sortField="publish_time"` return candidate rows for both `专精特新` and
  `小巨人`.
- [ ] Decide the safe scope for no-keyword collection.
  A blank `searchWord` can be used to request a general policy list, but it
  should first be tested on a small page range and reviewed through
  `pager.total`, `pager.pageCount`, duplicates, and detail-parse quality before
  any broader collection.
- [x] Register collection configuration before formal collection.
  Add a small YAML/TOML/CSV config under `configs/` for XXGK query batches, and
  document the config fields before running more than pilot pages.
- [ ] Upgrade `data/source-manifest.csv` only after the next source batch.
  Current notes already record notebook provenance. If more sources are added,
  plan explicit fields such as `generated_by`, `upstream_files`,
  `collection_status`, and `review_status` instead of continuing to overload
  `notes`.
- [ ] Promote crawler logic out of notebooks only after the search strategy is stable.
  A first cache-first gov.cn XXGK crawler skeleton now exists under
  `src/statistic_modeling/policy_text_crawler/` with the command entry point
  `scripts/govcn_xxgk_crawler.py`. Full-text pilot batches, `pager.total` /
  `pager.pageCount`, target-date filtering, detail parsing, and quality reports
  have been confirmed on bounded live runs. Before broad use, review final
  `max_pages` and rate-limit settings; keep notebooks as demonstrations and
  audit records.

## Current XXGK Collection Snapshot

- Source: `gov.cn/zhengce/xxgk`
- Scope: central-government policy detail pages from 2020-01-01 through 2025-12-31.
- Query batches: `中小企业` title search; `专精特新` full-text search; `小巨人` full-text search.
- Candidate queue: `data/interim/govcn_xxgk_candidate_url_queue.csv`
- Structured records: `data/interim/govcn_xxgk_policy_detail_records.csv`
- Quality report: `outputs/govcn_xxgk_quality_report.csv`
- Current full run: 50 candidate rows, 28 deduplicated in-window detail records, all 28 parsed successfully.
- Multi-keyword provenance is preserved in `keyword_hit` and `query_batch_id` with `;` separators.

## Documentations

- `docs/data-dictionary.md` -- Data field definitions (high priority required)
