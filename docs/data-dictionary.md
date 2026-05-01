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

### `data/interim/manual_policy_all_keyword_srdi.xlsx`

Manual keyword-policy workbook collected as a time-constrained replacement for
continuing broad crawler expansion. It covers central and local policy sources
whose metadata contains the keyword `专精特新`. This workbook is the current
primary upstream table for the next text-processing and policy-mining stage.

| Item | Value |
| --- | --- |
| Data layer | `interim` |
| File format | Excel workbook (`.xlsx`) |
| Sheet | `tableData` |
| Observation unit | One manually collected policy record |
| Current shape | 4642 rows x 11 columns |
| Geographic coverage | `国家` plus 32 local source labels; Xinjiang is split into `新疆维吾尔自治区` and `新疆生产建设兵团` |
| Date coverage in file | 2020-01-02 through 2026-04-30 |
| Current 2020-2025 window count | 4475 rows |
| Quality report | `outputs/manual_policy_all_keyword_srdi_quality_report.csv` |
| Coverage table | `outputs/manual_policy_all_keyword_srdi_province_year_counts.csv` |
| Main use | Policy-text mining and downstream policy-intensity construction for SRDI-related policies |

| Field | Type | Description |
| --- | --- | --- |
| `序号` | string / integer-like | Row number from the manual collection workbook. |
| `所属省份` | string / category | Source jurisdiction label, including `国家` for central policies. |
| `地区名称` | string | More specific region or source-side area name when available. |
| `发文日期` | date-like string | Publication date. Dates parse cleanly in the current workbook. |
| `关键词数量清单` | string / JSON-like | Keyword count metadata. All current rows contain `专精特新`. |
| `关键词总数量` | integer-like string | Total keyword hit count retained from collection metadata. |
| `标题` | string | Policy title. Duplicate titles can occur across jurisdictions or reposts, so do not treat title alone as a stable ID. |
| `文号` | string | Document number when available. Missingness is expected for many local pages. |
| `发文机构` | string | Issuing agency when available. Missingness must be handled before modeling. |
| `原文链接` | string / URL | Original source URL. Current inspect found no missing or duplicate URLs. |
| `摘要` | string | Source-side or collected abstract text. Most rows contain the visible `专精特新` keyword hit here. |

Initial inspect notes:

- `原文链接` has no missing values and no duplicates in the current workbook.
- `发文日期` has no missing or unparseable values.
- 167 records are dated 2026. If the analysis window remains 2020-2025, filter
  those rows before constructing paper tables or DID-facing policy intensity.
- 20 records do not show `专精特新` in `标题` or `摘要`, but their
  `关键词数量清单` still records a `专精特新` hit. Treat them as metadata-backed
  keyword matches until source text is rechecked.

### `data/processed/manual_policy_srdi_policy_records_v0.csv`

Processed policy-record table derived from
`data/interim/manual_policy_all_keyword_srdi.xlsx`. This is the first stable
record-level input for the manual SRDI policy-mining path.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One manually collected SRDI-related policy record |
| Current shape | 4475 rows x 20 columns |
| Date scope | 2020-2025 |
| Source URL uniqueness | Unique `source_url` |
| Generator | `scripts/manual_srdi_processed_corpus.py` |
| Quality report | `outputs/manual_policy_srdi_processed_v0_quality_report.csv` |

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable ID derived from `source_url`. |
| `province` | string / category | Analysis unit. `国家` is mapped to `central`; `新疆维吾尔自治区` and `新疆生产建设兵团` are mapped to `新疆`. |
| `source_label_original` | string | Original `所属省份` value from the workbook. Use this to audit province normalization. |
| `jurisdiction_type` | string / category | `central` or `local`. |
| `region_name` | string | Original `地区名称`. |
| `publish_date` | date-like string | Publication date. |
| `publish_year` | integer | Year derived from `publish_date`. |
| `keyword_hit` | string | Fixed to `专精特新` for this processed v0. |
| `keyword_count` | integer | Numeric keyword hit count parsed from `关键词总数量`. |
| `keyword_count_raw` | string | Original keyword hit count value. |
| `title` | string | Policy title. |
| `document_number` | string | Policy document number when available. |
| `agency` | string | Issuing agency when available. |
| `source_url` | string / URL | Original source URL; unique in processed v0. |
| `abstract` | string | Collected abstract text. |
| `title_contains_srdi` | boolean | Whether `title` contains `专精特新`. |
| `abstract_contains_srdi` | boolean | Whether `abstract` contains `专精特新`. |
| `title_or_abstract_contains_srdi` | boolean | Whether either title or abstract contains `专精特新`. |
| `in_analysis_window` | boolean | Always `True` in this output; retained for audit. |
| `review_status` | string | Current processed v0 status; expected `accepted`. |

### `data/processed/province_year_srdi_policy_intensity_v0.csv`

Balanced province-year policy-intensity table derived from
`data/processed/manual_policy_srdi_policy_records_v0.csv`. It is designed as a
direct candidate input for DID-side province-year policy-intensity construction.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province unit-year |
| Current shape | 186 rows x 11 columns |
| Date scope | 2020-2025 |
| Geographic units | 31 local province units; the two Xinjiang source labels are merged into `新疆` |
| Excludes | `central` records |
| Generator | `scripts/manual_srdi_processed_corpus.py` |
| Quality report | `outputs/manual_policy_srdi_processed_v0_quality_report.csv` |

| Field | Type | Description |
| --- | --- | --- |
| `province` | string / category | Local province unit used for policy-intensity analysis. |
| `publish_year` | integer | Calendar year. |
| `srdi_policy_count` | integer | Count of SRDI keyword policy records in the province-year. |
| `log_srdi_policy_count_plus1` | float | Natural log of `srdi_policy_count + 1`. |
| `total_keyword_count` | integer | Sum of `keyword_count` across records in the province-year. |
| `avg_keyword_count` | float | Mean keyword hit count across records in the province-year; zero for no-policy rows. |
| `title_contains_srdi_count` | integer | Count of records whose title contains `专精特新`. |
| `abstract_contains_srdi_count` | integer | Count of records whose abstract contains `专精特新`. |
| `title_or_abstract_contains_srdi_count` | integer | Count of records with a visible title or abstract keyword hit. |
| `missing_agency_count` | integer | Count of records without `agency`. |
| `unique_agency_count` | integer | Distinct non-empty agency count in the province-year. |

### `outputs/manual_policy_srdi_processed_v0_quality_report.csv`

Long-form quality report for the manual SRDI processed v0 outputs. Key metrics:

- `processed_records=4475`
- `excluded_outside_analysis_window=167`
- `local_province_units=31`
- `intensity_records=186`
- `xinjiang_processed_records=47`

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
| Current shape | 28 rows x 23 columns | 720 rows x 23 columns |
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
| `official_subject_categories` | string / serialized list | Source-provided gov.cn `主题分类` labels. Values are non-exclusive official Chinese categories split from the detail page's `\`-separated field. This taxonomy is specific to gov.cn and should not be assumed for local-government sources. |
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

### gov.cn XXGK Processed All-Policy Corpus v0

File:

- `data/processed/govcn_xxgk_all_policy_text_corpus_v0.csv`

This is the first analysis-ready central-government XXGK text corpus. It is
derived from the all-policy detail records after manual QA in
`notebooks/30_central_gov_xxgk_corpus_qa.py`.

Inclusion rule:

- include rows with `parse_status=success`, accepted manual review, in-window
  publication date, and non-empty text;
- include all reviewed short-text rows because manual review confirmed the text
  was correctly captured;
- exclude the one retained timeout / `detail_failed` row.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One accepted central gov.cn XXGK policy detail page |
| Current shape | 719 rows x 18 columns |
| Date scope | 2020-2025 |
| URL uniqueness | Unique `source_url` |
| Generator | `scripts/govcn_xxgk_processed_corpus.py` |
| Quality report | `outputs/govcn_xxgk_all_processed_v0_quality_report.csv` |

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID derived from `source_url`. |
| `province` | string | Fixed to `central`. |
| `title` | string | Parsed policy title. |
| `publish_date` | date-like string | Publication date. |
| `publish_year` | integer | Year derived from `publish_date`. |
| `agency` | string | Parsed or inferred issuing agency. |
| `source_site` | string | Fixed to `gov.cn/zhengce/xxgk`. |
| `source_url` | string / URL | Public policy detail page URL. |
| `official_subject_categories` | string / serialized list | Source-provided gov.cn `主题分类` labels. |
| `document_type` | string | Coarse parser label retained from detail records. |
| `text_clean` | string | Main cleaned text for downstream NLP and policy-text mining. |
| `text_len` | integer | Character length of `text_clean`. |
| `text_hash` | string | SHA-256 hash of normalized text. |
| `attachment_urls` | string / serialized list | Downloadable attachment URLs found on the page. |
| `raw_json_path` | string / path | Upstream raw list JSON artifact path. |
| `raw_html_path` | string / path | Archived raw detail HTML path. |
| `parse_status` | string | Retained parser status; expected `success` in processed v0. |
| `review_status` | string | Final review status after manual QA; expected `accepted` in processed v0. |

### gov.cn XXGK Processed v0 Quality Report

File:

- `outputs/govcn_xxgk_all_processed_v0_quality_report.csv`

The processed v0 report is a long-form metric table with columns
`metric`, `value`, and `note`. Current key values: 720 source detail records,
719 processed records, 1 excluded timeout/detail failure, 11 accepted short-text
records, 0 duplicate URLs, 0 duplicate text hashes, and 719 rows with official
subject categories.
