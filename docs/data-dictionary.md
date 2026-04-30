# Data Dictionary

## Registered Datasets

### `data/interim/labeled_policy_text_manual_collection.xlsx`

Policy-text coding workbook for provincial support policies related to
"Specialized, Refined, Distinctive, and Innovative" enterprises. The file is an
intermediate manually collected and labeled source for policy text mining and
policy-intensity construction.

| Item | Value |
| --- | --- |
| Data layer | `interim` |
| File format | Excel workbook (`.xlsx`) |
| Sheet | `Sheet1` |
| Observation unit | One policy document |
| Current shape | 67 rows x 9 columns |
| Geographic coverage | 10 provinces/municipalities in current workbook |
| Main use | Policy instrument classification; province-year policy support intensity |
| Identifier candidates | `policy_title`, `source_url` |
| Date/timing field | `release_year` |

| Field | Original field | Type | Description |
| --- | --- | --- | --- |
| `province` | `省份` | string / category | Province or municipality associated with the policy document. |
| `policy_title` | `政策名称` | string | Full policy document title. Treat as text; currently unique in the workbook. |
| `release_year` | `发布年份` | string / year-like | Policy release year. Keep as string during import because at least one value contains an implementation-period note, e.g. `2019 （实施2019-2021）`. Extract a numeric year only in a cleaned derivative table. |
| `issuing_agency` | `发布机构` | string | Issuing agency or agencies for the policy document. |
| `source_url` | `文件链接` | string / URL | Source URL for the policy document. Treat as an identifier-like string. |
| `primary_policy_instrument_type` | `政策类型（主要）` | string / category | Manual primary policy-instrument classification, such as supply-side, demand-side, environmental, or mixed types. Review spelling variants before converting to controlled categories. |
| `policy_instrument_binary_code` | `类型编码（辅助） 第一位（供给型标记）：该政策包含供给型工具 ；第二位（需求型标记）：该政策同时包含需求型工具 ； 第三位（环境型标记）：该政策同时包含环境型工具； 第四位（专精特新配套标记）：该政策是专精特新专属配套政策` | string / four-character code | Auxiliary manual binary code. Position 1 marks supply-side tools; position 2 marks demand-side tools; position 3 marks environmental tools; position 4 marks whether the policy is a dedicated SRDI support policy. Keep as string to preserve leading zeros. |
| `classification_rationale` | `判断依据` | string | Manual rationale for the policy-type judgment. Useful for audit, label validation, and future coding-rule refinement. |
| `key_text_excerpt` | `正文关键摘录` | string | Key excerpt from the policy text supporting the manual classification. Useful for policy text mining features and qualitative validation. |

Notes:

- This is not yet an analysis-ready panel dataset.
- The workbook header row has been standardized to explanatory English
  `snake_case` field names. Original Chinese field names are retained in the
  dictionary above for provenance.
- Do not overwrite source values during cleaning. Write standardized derived
  outputs to `data/interim/` or `data/processed/`.
- Final derived variables should document how
  `primary_policy_instrument_type` and `policy_instrument_binary_code` are
  normalized into supply-side, demand-side, environmental, and SRDI
  dedicated-policy indicators.

### gov.cn XXGK Candidate Queues

Files:

- `data/interim/govcn_xxgk_candidate_url_queue.csv`
- `data/interim/govcn_xxgk_all_candidate_url_queue.csv`

Candidate queues are list-page outputs from `gov.cn/zhengce/xxgk`. They preserve
query provenance, page metadata, and raw JSON artifact paths before detail-page
parsing.

| Item | SRDI corpus | All-policy corpus |
| --- | --- | --- |
| Data layer | `interim` | `interim` |
| Observation unit | One list-row candidate URL | One list-row candidate URL |
| Current shape | 50 rows x 17 columns | 760 rows x 17 columns |
| Source | `gov.cn/zhengce/xxgk` | `gov.cn/zhengce/xxgk` |
| Query scope | `中小企业`, `专精特新`, `小巨人` | Blank keyword |
| Date scope | Boundary pages retained; details filtered to 2020-2025 | Boundary pages retained; details filtered to 2020-2025 |
| Generator | `scripts/govcn_xxgk_crawler.py` | `scripts/govcn_xxgk_crawler.py` |

| Field | Type | Description |
| --- | --- | --- |
| `candidate_id` | string | Stable candidate ID derived from `source_url`. |
| `query_batch_id` | string | Query batch that produced the candidate. |
| `province` | string | Fixed to `central`. |
| `source_site` | string | Fixed to `gov.cn/zhengce/xxgk`. |
| `title` | string | List-row title with HTML tags removed. |
| `fwzh` | string | Document number from list JSON when available. |
| `cwrq` | datetime-like string | Formulation date from list JSON when available. |
| `publish_time` | datetime-like string | Publication timestamp from list JSON. |
| `source_url` | string / URL | Public policy detail page URL. |
| `keyword_hit` | string | Query keyword. Blank for all-policy rows. |
| `category_id` | integer | Source-side category ID used by the XXGK list. |
| `page_no` | integer | List page number. |
| `list_total` | integer | `pager.total` from the list JSON response. |
| `list_page_count` | integer | `pager.pageCount` from the list JSON response. |
| `list_page_size` | integer | `pager.pageSize` from the list JSON response. |
| `parse_status` | string | List parse status; currently expected to be `success`. |
| `raw_json_path` | string / path | Archived raw list JSON path. |

### gov.cn XXGK Detail Records

Files:

- `data/interim/govcn_xxgk_policy_detail_records.csv`
- `data/interim/govcn_xxgk_all_policy_detail_records.csv`

Detail records are the main policy-text crawler outputs. They contain parsed
policy metadata, raw and cleaned text, provenance links, parser status, and
review status.

| Item | SRDI corpus | All-policy corpus |
| --- | --- | --- |
| Data layer | `interim` | `interim` |
| Observation unit | One deduplicated policy detail page | One deduplicated policy detail page |
| Current shape | 28 rows x 21 columns | 720 rows x 21 columns |
| Date scope | 2020-2025 | 2020-2025 |
| URL uniqueness | Unique `source_url` | Unique `source_url` |
| Generator | `scripts/govcn_xxgk_crawler.py` | `scripts/govcn_xxgk_crawler.py` |

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID derived from `source_url`. |
| `province` | string | Fixed to `central`. |
| `title` | string | Parsed policy title. |
| `publish_date` | date-like string | Parsed publication date. |
| `agency` | string | Parsed or inferred issuing agency. |
| `source_site` | string | Fixed to `gov.cn/zhengce/xxgk`. |
| `source_url` | string / URL | Public policy detail page URL; unique in each detail output. |
| `query_batch_id` | string | Query provenance. Multiple values are separated by `;`. |
| `keyword_hit` | string | Keyword provenance. Multiple values are separated by `;`; blank for all-policy rows. |
| `document_type` | string | Coarse parser label: `policy_document`, `attachment_page`, or `needs_review`. |
| `text_raw` | string | Extracted page text before conservative normalization. |
| `text_clean` | string | Conservatively normalized text for downstream processing. |
| `attachment_urls` | string / serialized list | Attachment URLs found on the detail page. |
| `raw_json_path` | string / path | Upstream raw list JSON artifact path. |
| `raw_html_path` | string / path | Archived raw detail HTML path. |
| `parse_status` | string | `success`, `partial`, `detail_failed`, or another configured parser status. |
| `review_status` | string | `accepted`, `needs_review`, or `rejected`. |
| `error` | string | Error message for failed rows. |
| `crawl_time` | datetime-like string | UTC timestamp for detail parsing/fetching. |
| `text_hash` | string | SHA-256 hash of normalized text. |
| `in_target_date_window` | boolean | Whether `publish_date` is within 2020-01-01 through 2025-12-31. |

Status interpretation:

- `parse_status=success`: parser extracted detail text.
- `parse_status=detail_failed`: detail page failed to fetch or parse; inspect
  `error` and retry or review manually.
- `review_status=needs_review`: record parsed but is short, unusual, or failed.
- `review_status=accepted`: record passed current automated checks.

### gov.cn XXGK Quality Reports

Files:

- `outputs/govcn_xxgk_quality_report.csv`
- `outputs/govcn_xxgk_all_quality_report.csv`

Quality reports are one-row summaries generated by the crawler. They are used as
run acceptance checks and should be reviewed before downstream text mining.

| Field | Type | Description |
| --- | --- | --- |
| `candidate_records` | integer | Number of candidate rows. |
| `detail_records` | integer | Number of detail rows. |
| `success_details` | integer | Detail rows with `parse_status=success`. |
| `partial_details` | integer | Detail rows with `parse_status=partial`. |
| `failed_details` | integer | Detail rows with `parse_status=detail_failed`. |
| `empty_body_text` | integer | Detail rows with empty `text_raw`. |
| `short_body_text_lt_200` | integer | Detail rows where `text_raw` is shorter than 200 characters. |
| `missing_publication_dates` | integer | Detail rows without `publish_date`. |
| `out_of_target_date_window` | integer | Detail rows outside 2020-2025. |
| `duplicate_source_urls` | integer | Duplicate URLs in candidate rows. |
| `duplicate_text_hashes` | integer | Duplicate `text_hash` values in detail rows. |
