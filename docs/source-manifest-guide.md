# Source Manifest Guide

`data/source-manifest.csv` is the project-level registry for local data
artifacts that should remain auditable. It is intentionally lightweight: it
tracks where data came from, where it lives locally, and which code or notebook
produced it.

## Required Columns

| Column | Description |
| --- | --- |
| `source_name` | Human-readable source or artifact group name. |
| `source_type` | Artifact type, such as `html`, `api-json`, `html-detail`, `interim-derived`, or `manual-collection`. |
| `url_or_origin` | External URL, API endpoint, upstream local artifact, or manual origin. |
| `access_date` | Collection or registration date. Current rows use `YYYY-M-D`. |
| `local_file` | Path under `data/`, without the leading `data/`. Globs are allowed for grouped raw artifacts. |
| `generated_by` | Script, notebook, or manual process that produced the artifact. |
| `config_files` | Config files used by the run, separated with `;` when there is more than one. |
| `upstream_files` | Local input artifacts used to derive this artifact, separated with `;` when there is more than one. |
| `quality_report` | Quality-report artifact linked to the dataset, when available. |
| `collection_status` | `raw`, `validated`, `partial`, `failed`, or `deprecated`. |
| `review_status` | `accepted`, `needs_review`, or `rejected`. |
| `record_count` | Row count for tabular artifacts. Leave empty for grouped raw file patterns. |
| `notes` | Short human-readable provenance note. Do not hide code/config/upstream links here when a dedicated column exists. |

## Registration Rules

- Register raw external inputs and important derived datasets.
- Use grouped rows for raw crawl artifacts when individual files are numerous.
- Do not register every detail HTML page separately.
- Put the code source in `generated_by`, for example `scripts/govcn_xxgk_crawler.py`.
- Put run configuration in `config_files`, for example `configs/govcn_xxgk_sources.toml;configs/govcn_xxgk_all_query_batches.csv`.
- Put local data dependencies in `upstream_files`.
- Keep `url_or_origin` for the external URL, API endpoint, manual origin, or a compact human-readable upstream description.
- Keep `local_file` relative to `data/`.
- Register a new row when the artifact's meaning or generation config changes.
- Use `collection_status=partial` and `review_status=needs_review` when the artifact is usable but has retained failures or review rows.

## Current XXGK Pattern

The gov.cn XXGK crawler uses three registration levels:

| Level | Example |
| --- | --- |
| Raw list JSON | `raw/json/govcn_xxgk_govcn_xxgk_all_*_page_*.json` |
| Candidate queue | `interim/govcn_xxgk_all_candidate_url_queue.csv` |
| Structured detail records | `interim/govcn_xxgk_all_policy_detail_records.csv` |

SRDI keyword outputs and all-policy outputs must stay registered separately
because they have different query semantics, config files, quality reports, and
downstream use.
