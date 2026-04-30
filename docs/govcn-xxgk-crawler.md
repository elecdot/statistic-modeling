# gov.cn XXGK Crawler

This document is the handoff guide for the central-government policy crawler
for `gov.cn/zhengce/xxgk`. It explains what the crawler produces, how to run
it, and how to interpret its outputs.

## Product

The crawler builds two related corpora from the China Government Network
government information disclosure page:

| Corpus | Purpose | Query config | Main output |
| --- | --- | --- | --- |
| SRDI keyword corpus | Research-focused policy corpus for SRDI / Little-Giant text mining | `configs/govcn_xxgk_query_batches.csv` | `data/interim/govcn_xxgk_policy_detail_records.csv` |
| All-policy corpus | Central XXGK policy baseline corpus for 2020-2025 | `configs/govcn_xxgk_all_query_batches.csv` | `data/interim/govcn_xxgk_all_policy_detail_records.csv` |

Both corpora use the same parser schema and source guardrails. They are kept in
separate files so the all-policy corpus cannot overwrite the SRDI corpus.

Current collection snapshot:

| Corpus | Candidate rows | Detail rows | Parse status |
| --- | ---: | ---: | --- |
| SRDI keyword corpus | 50 | 28 | 28 success |
| All-policy corpus | 760 | 720 | 719 success, 1 detail_failed |

The single all-policy `detail_failed` row is retained for review rather than
silently dropped.

## How It Works

The crawler follows this pipeline:

1. Read source constants from `configs/govcn_xxgk_sources.toml`.
2. Read query batches from a CSV config `configs/govcn_xxgk_*.csv`.
3. Request the public page's browser-facing XXGK list gateway.
4. Archive raw list JSON under `data/raw/json/`.
5. Normalize list rows into a candidate URL queue under `data/interim/`.
6. Filter candidate detail URLs to the configured 2020-2025 window.
7. Fetch public detail HTML pages one at a time with conservative delays.
8. Archive raw HTML under `data/raw/html/`.
9. Parse detail pages into structured policy-text records.
10. Write a compact quality report under `outputs/`.

The list gateway is the same browser-facing AJAX gateway observed from the
public XXGK page. The crawler uses page-observed public constants only. It does
not use private credentials, login bypass, captcha bypass, or concurrent
requests.

## Query Semantics

The query CSV controls search behavior:

| Field | Meaning |
| --- | --- |
| `keyword` | Search word. Empty string means all-policy blank search. |
| `field_name` | `maintitle` means title search; empty string means full-text search. |
| `is_precise_search` | `0` is fuzzy search; `1` is precise search. |
| `sort_field` | `publish_time` means publication-date sorting. |
| `max_pages` | Safety cap. Actual runs stop earlier at `pageCount` or date boundary. |

For all-policy collection, the query is intentionally blank:

```csv
keyword="", field_name="", is_precise_search=0, sort_field="publish_time"
```

## Pagination And Date Window

The configured target window is:

```text
2020-01-01 <= publish_date <= 2025-12-31
```

The crawler requests list pages sorted by `publish_time DESC`. It stops list
pagination when either:

- the current page reaches `pager.pageCount`; or
- the oldest list-row `publish_time` on a page is earlier than `2020-01-01`.

The boundary page is archived and included in the candidate queue for audit, but
detail fetching only runs for candidates inside the target date window.

## Commands

Use the workspace-safe uv cache specified in `justfile`.

For normal use, prefer the `just` targets. They pin the intended config files
and output paths so SRDI and all-policy runs do not overwrite each other.

```bash
just govcn-xxgk-queue
just govcn-xxgk-cache-pilot
just govcn-xxgk-live-full
```

All-policy commands:

```bash
just govcn-xxgk-all-probe
just govcn-xxgk-all-full
```

The probe command limits list pages and detail pages. Use it after changing
query configuration or parser behavior. The full command uses the configured
pagination/date stop rules and writes only all-policy outputs.

Use the underlying CLI directly only for debugging or reviewed custom runs:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py \
  --source-config configs/govcn_xxgk_sources.toml \
  --query-batches configs/govcn_xxgk_all_query_batches.csv \
  run \
  --fetch-live \
  --max-pages-override 5 \
  --max-details-per-batch 3 \
  --candidates-output data/interim/govcn_xxgk_all_candidate_url_queue.csv \
  --details-output data/interim/govcn_xxgk_all_policy_detail_records.csv \
  --quality-output outputs/govcn_xxgk_all_quality_report.csv
```

Important flags:

| Flag | Use |
| --- | --- |
| `--source-config` | Selects source constants such as endpoint and target date window. |
| `--query-batches` | Selects SRDI or all-policy query semantics. |
| `--include-disabled` | Includes disabled query rows when printing the queue. |
| `run --fetch-live` | Sends live requests and archives raw JSON/HTML. Without it, the run is cache-first. |
| `run --max-pages-override N` | Temporary page cap for probes. |
| `run --max-details-per-batch N` | Temporary detail cap per batch. Use `-1` for all candidates. |
| `run --candidates-output PATH` | Overrides candidate queue output path. |
| `run --details-output PATH` | Overrides detail-record output path. |
| `run --quality-output PATH` | Overrides quality-report output path. |
| `run --keep-out-of-window` | Keeps detail records outside the configured date window for audit. |

## Demo Checks

After running the all-policy full command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python - <<'PY'
import pandas as pd

candidates = pd.read_csv("data/interim/govcn_xxgk_all_candidate_url_queue.csv")
details = pd.read_csv("data/interim/govcn_xxgk_all_policy_detail_records.csv")
quality = pd.read_csv("outputs/govcn_xxgk_all_quality_report.csv")

print("candidate rows:", len(candidates))
print("detail rows:", len(details))
print("date range:", details["publish_date"].min(), details["publish_date"].max())
print("source_url unique:", details["source_url"].is_unique)
print(quality.to_dict("records")[0])
PY
```

Expected current result:

```text
candidate rows: 760
detail rows: 720
date range: 2020-01-07 2025-12-31
source_url unique: True
```

## Outputs

Candidate queues:

| Field | Description |
| --- | --- |
| `candidate_id` | Stable ID derived from source URL. |
| `query_batch_id` | Query config row that found the URL. |
| `province` | Fixed to `central`. |
| `source_site` | Fixed to `gov.cn/zhengce/xxgk`. |
| `title` | List-row title with HTML tags removed. |
| `fwzh` | Document number from list JSON when available. |
| `cwrq` | Formulation date from list JSON when available. |
| `publish_time` | Publication timestamp from list JSON. |
| `source_url` | Public policy detail page URL. |
| `keyword_hit` | Query keyword. Blank for all-policy corpus. |
| `page_no` | List page number. |
| `list_total` | `pager.total` from list JSON. |
| `list_page_count` | `pager.pageCount` from list JSON. |
| `list_page_size` | `pager.pageSize` from list JSON. |
| `parse_status` | List parse status. |
| `raw_json_path` | Archived raw list JSON path. |

Detail records:

| Field | Description |
| --- | --- |
| `policy_id` | Stable policy identifier. |
| `province` | Fixed to `central`. |
| `title` | Parsed policy title. |
| `publish_date` | Parsed publication date. |
| `agency` | Parsed or inferred issuing agency. |
| `source_site` | Fixed to `gov.cn/zhengce/xxgk`. |
| `source_url` | Public policy detail page URL. |
| `query_batch_id` | Query provenance; multiple values are `;` separated. |
| `keyword_hit` | Keyword provenance; multiple values are `;` separated. |
| `document_type` | Coarse parser label: `policy_document`, `attachment_page`, or `needs_review`. |
| `text_raw` | Raw extracted page text. |
| `text_clean` | Conservatively normalized text. |
| `attachment_urls` | Attachment URLs found on the page. |
| `raw_json_path` | Upstream list JSON artifact path. |
| `raw_html_path` | Archived detail HTML path. |
| `parse_status` | Detail parse status. |
| `review_status` | `accepted`, `needs_review`, or `rejected`. |
| `error` | Error message for failed rows. |
| `crawl_time` | UTC timestamp for detail parsing/fetching. |
| `text_hash` | SHA-256 hash of normalized text. |
| `in_target_date_window` | Whether parsed date is inside 2020-2025. |

Quality reports:

| Field | Description |
| --- | --- |
| `candidate_records` | Number of candidate rows. |
| `detail_records` | Number of detail rows. |
| `success_details` | Detail rows parsed successfully. |
| `partial_details` | Detail rows parsed partially. |
| `failed_details` | Detail rows that failed. |
| `empty_body_text` | Detail rows with empty extracted text. |
| `short_body_text_lt_200` | Detail rows with text shorter than 200 characters. |
| `missing_publication_dates` | Detail rows without publication date. |
| `out_of_target_date_window` | Detail rows outside 2020-2025. |
| `duplicate_source_urls` | Duplicate URLs in candidate rows. |
| `duplicate_text_hashes` | Duplicate text hashes in detail rows. |

## Failure Handling

- Live list and detail artifacts are archived before parsing.
- Failed detail rows remain in the structured output with `parse_status=detail_failed`.
- Short but successfully parsed records are marked `review_status=needs_review`.
- The all-policy corpus currently has one timeout failure and eleven short-text
  review rows. They are expected review items, not crawler blockers.

## Development Checklist

Before changing crawler behavior:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/uv-cache uv run pytest
```

Before broad live collection:

```bash
just govcn-xxgk-all-probe
```

Check:

- candidate rows are non-empty;
- `publish_time` is descending;
- `pager.total` and `pager.pageCount` are populated;
- at least one detail row parses successfully.
