# Data Dictionary

## Quick Lookup

Use this section as the entry point before reading the full field dictionary.
Search the listed file or section name in this document to jump to the detailed
schema.

| Need | Start Here | Purpose |
| --- | --- | --- |
| Current main upstream manual SRDI workbook | `data/interim/manual_policy_all_keyword_srdi.xlsx` | Metadata-only manual collection with title and abstract. |
| Current main full-text manual SRDI workbook | `data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx` | Same record universe with collected full policy text. |
| 2019 supplementary full-text SRDI workbook | `data/interim/manual_policy_all_keyword_srdi_2019_supplementary.xlsx` | Supplementary 2019 policy full-text records for the v2 corpus rebuild. |
| Manual SRDI jurisdiction corrections v1 | `configs/manual_srdi_jurisdiction_overrides_v1.csv` | Reviewed corrections for the original 2020-2025 v0/v1 paths. |
| Manual SRDI jurisdiction corrections v2 | `configs/manual_srdi_jurisdiction_overrides_v2.csv` | v1 corrections plus reviewed 2019 supplement decisions for the 2019-2024 v2 corpus. |
| v2 row-level full-text policy corpus | `data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv` | 2019-2024 policy-side corpus for the next v2 text-mining chain. |
| v2 base province-year policy count table | `data/processed/province_year_srdi_policy_intensity_v2.csv` | Balanced 31 province x 2019-2024 local policy-count table. |
| v2 row-level full-text dictionary features | `data/processed/manual_policy_srdi_text_features_fulltext_v2.csv` | 2019-2024 title + full-text dictionary features using the frozen v1 codebook. |
| v2 province-year full-text dictionary features | `data/processed/province_year_srdi_text_features_fulltext_v2.csv` | Balanced 31 province x 2019-2024 aggregate dictionary-feature table. |
| Main row-level full-text policy corpus | `data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv` | Preferred 2020-2025 processed policy records for text mining. |
| Baseline row-level title/abstract corpus | `data/processed/manual_policy_srdi_policy_records_v0.csv` | Earlier processed corpus retained for robustness and comparison. |
| DID-facing policy-count intensity table | `data/processed/province_year_srdi_policy_intensity_v0.csv` | Balanced province-year policy count and keyword intensity candidate. |
| Main full-text policy-tool features | `data/processed/manual_policy_srdi_text_features_fulltext_v1.csv` | Row-level title + full-text dictionary features. |
| Main province-year full-text features | `data/processed/province_year_srdi_text_features_fulltext_v1.csv` | Province-year aggregate full-text policy-tool intensity proxies. |
| Baseline title/abstract text features | `data/processed/manual_policy_srdi_text_features_v0.csv` | Row-level title + abstract dictionary features. |
| Baseline province-year text features | `data/processed/province_year_srdi_text_features_v0.csv` | Province-year aggregate title/abstract text features. |
| Policy-tool dictionary and review artifacts | `outputs/manual_policy_srdi_tool_dictionary_v0.csv` | Dictionary terms plus coverage and no-hit review outputs. |
| DeepSeek label-rule sampling inputs | `Manual SRDI Label-Rule Preparation v1` | Label docs, sampling frame, keyword rules, and round-1 sample. |
| DeepSeek round-1 labels | `Manual SRDI DeepSeek Round-1 Labels v1` | Parsed multi-label silver labels and run QA after live API labeling. |
| MacBERT training data | `Manual SRDI MacBERT Training Data v1` | Deterministic train/validation/test dataset derived from DeepSeek round-1 labels. |
| MacBERT full-corpus predictions | `Manual SRDI MacBERT Full-Corpus Prediction v1` | Row-level probabilities and hard labels for the 4,475 full-text policy records. |
| DID-facing MacBERT tool intensity | `data/processed/province_year_srdi_macbert_tool_intensity_v1.csv` | Balanced province-year policy-tool probability intensity table. |
| DID-ready selected policy-text variables | `data/processed/province_year_srdi_policy_text_variables_v1.csv` | Selected main, robustness, and audit variables for downstream staggered DID. |
| Final policy-side DID panel | `data/processed/manual_srdi_did_policy_intensity_panel_v1.csv` | Merge-ready province-year policy intensity panel with `did_province_key` and `did_year`. |
| Central gov.cn crawler outputs | `gov.cn XXGK Candidate Queues`; `gov.cn XXGK Detail Records` | Central-government list and detail crawler schemas. |
| Central gov.cn processed corpus | `gov.cn XXGK Processed All-Policy Corpus v0` | Analysis-ready central-government all-policy text corpus. |
| Quality reports | `outputs/*quality_report.csv`; `gov.cn XXGK Quality Reports` | Run checks, record counts, exclusions, and warning metrics. |

Current analysis default before the v2 rebuild remains the full-text v1 manual
SRDI path. The v2 corpus and base count table are the new 2019-2024 inputs for
the next policy-text mining chain, but v2 dictionary, MacBERT, variable
selection, and final DID-ready outputs have not yet been rebuilt.

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

### `configs/manual_srdi_jurisdiction_overrides_v1.csv`

Reviewed correction table for records where the collection source label refers
to a reposting website, but the policy title and source evidence indicate a
different policy jurisdiction. These corrections are applied by
`scripts/manual_srdi_processed_corpus.py` and
`scripts/manual_srdi_fulltext_processed_corpus.py`.

| Item | Value |
| --- | --- |
| Data layer | `configs` |
| Observation unit | One reviewed policy jurisdiction correction |
| Current shape | 15 rows x 7 columns |
| Main use | Ensure `province` represents the policy jurisdiction used in DID-facing province-year variables |

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID derived from `source_url`. |
| `source_url` | string / URL | Original collected source URL. |
| `source_label_original` | string | Original `所属省份` value from the workbook. |
| `corrected_province` | string | Reviewed policy jurisdiction to use in processed outputs. |
| `correction_status` | string | Expected `corrected` for reviewed correction rows. |
| `correction_reason` | string | Reason for correction, such as source-site reposting. |
| `evidence` | string | Human-readable evidence, usually title-prefix jurisdiction evidence. |

### `configs/manual_srdi_jurisdiction_overrides_v2.csv`

Reviewed correction table used by
`scripts/manual_srdi_fulltext_processed_corpus_v2.py`. It carries forward the
15 v1 corrections and adds six 2019 supplement decisions: five corrected
reposted central or out-of-province policies, plus one 安徽 row reviewed and kept
as original because the document is a local recommendation notice referencing a
central program.

| Item | Value |
| --- | --- |
| Data layer | `configs` |
| Observation unit | One reviewed policy jurisdiction decision |
| Current shape | 21 rows x 7 columns |
| Main use | Ensure v2 `province` reflects reviewed policy jurisdiction before 2019-2024 aggregation |

The field schema matches `manual_srdi_jurisdiction_overrides_v1.csv`. In v2,
`correction_status` can be `corrected` or `reviewed_original`; reviewed-original
rows are kept in their source jurisdiction and excluded from unresolved
jurisdiction-review candidates.

### `data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`

Full-text version of the manual SRDI keyword workbook. It keeps the same record
universe as `manual_policy_all_keyword_srdi.xlsx`, but replaces the collected
`摘要` field with `原文` so the formal text-mining path can use title + full
policy text.

| Item | Value |
| --- | --- |
| Data layer | `interim` |
| File format | Excel workbook (`.xlsx`) |
| Sheet | `tableData` |
| Observation unit | One manually collected policy record |
| Current shape | 4642 rows x 11 columns |
| Date coverage in file | 2020-01-02 through 2026-04-30 |
| Current 2020-2025 window count | 4475 rows |
| Main use | Full-text policy-tool dictionary features and v0/v1 method comparison |

Field meanings match `manual_policy_all_keyword_srdi.xlsx`, except:

| Field | Type | Description |
| --- | --- | --- |
| `原文` | string | Collected full policy text. The current workbook has no missing full text; 2020-2025 records have median full-text length of 5359 Chinese characters. |

### `data/interim/manual_policy_all_keyword_srdi_2019_supplementary.xlsx`

Supplementary full-text workbook for 2019 SRDI keyword policy records. This file
is used only by the v2 full-text corpus path and does not alter v1 artifacts.

| Item | Value |
| --- | --- |
| Data layer | `interim` |
| File format | Excel workbook (`.xlsx`) |
| Sheet | `tableData` |
| Observation unit | One manually collected policy record |
| Current shape | 190 rows x 9 columns |
| Date coverage in file | 2019-01-02 through 2019-12-31 |
| Main use | Add 2019 policy records to the v2 2019-2024 policy-side corpus |
| Quality report | `outputs/manual_policy_srdi_2019_supplement_quality_report_v2.csv` |

Field meanings match `manual_policy_all_keyword_srdi_with_full_text.xlsx`,
except:

| Field | Type | Description |
| --- | --- | --- |
| `原文文本` | string | Collected full policy text, standardized to `full_text` in v2. One 2019 row is retained with empty full text and `full_text_missing=True`. |

The 2019 supplement does not contain workbook keyword-count metadata. The v2
processor derives `keyword_count` from literal `专精特新` occurrences in title
plus full text and records `keyword_count_source=derived_from_text`.

### `data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv`

Processed full-text policy-record table for the 2019-2024 v2 policy-side corpus.
It stacks 2019 records from
`data/interim/manual_policy_all_keyword_srdi_2019_supplementary.xlsx` with
2020-2024 records from
`data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`. It applies
`configs/manual_srdi_jurisdiction_overrides_v2.csv`, which resolves the initial
2019 jurisdiction candidates before aggregation.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One manually collected SRDI-related policy record |
| Current shape | 3989 rows x 35 columns |
| Date scope | 2019-2024 |
| Source URL uniqueness | Unique `source_url` |
| Policy ID uniqueness | Unique `policy_id` |
| Generator | `scripts/manual_srdi_fulltext_processed_corpus_v2.py` |
| Quality report | `outputs/manual_policy_srdi_processed_fulltext_v2_quality_report.csv` |

Additional v2 audit fields:

| Field | Type | Description |
| --- | --- | --- |
| `source_workbook` | string | Source Excel workbook name for row-level provenance. |
| `source_schema_version` | string | `current_fulltext_workbook_v1` or `supplement_2019_fulltext_v1`. |
| `keyword_count_source` | string | `workbook_metadata` for current workbook rows, `derived_from_text` for 2019 supplement rows. |
| `full_text_missing` | boolean | Whether the standardized `full_text` field is empty. Empty rows are retained. |
| `full_text_fallback_for_model` | boolean | Marks rows where later model-input code should construct fallback text from metadata and title. |
| `needs_jurisdiction_review` | boolean | Whether the 2019 supplement row is an audit candidate for reposted central or out-of-province policies. |
| `jurisdiction_review_reason` | string | Audit-only reason, such as central-ministry terms or a title prefix suggesting another province. |
| `jurisdiction_review_suggested_province` | string | Audit-only suggested jurisdiction for later manual review. |
| `jurisdiction_review_evidence` | string | Matched terms or title-prefix evidence. |

### `data/processed/province_year_srdi_policy_intensity_v2.csv`

Balanced local province-year policy-count panel derived from
`manual_policy_srdi_policy_records_fulltext_v2.csv`. This is a foundation table
for later v2 text-mining aggregation, not a final DID-ready panel.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province-year |
| Current shape | 186 rows x 14 columns |
| Date scope | 2019-2024 |
| Province units | 31 local province units; `central` excluded |
| Generator | `scripts/manual_srdi_fulltext_processed_corpus_v2.py` |
| Quality report | `outputs/manual_policy_srdi_processed_fulltext_v2_quality_report.csv` |

Core fields include `srdi_policy_count`, keyword-count summaries, full-text
missing/fallback counts, agency missingness, unique agency count, and
`jurisdiction_review_candidate_count`.

### `data/processed/manual_policy_srdi_text_features_fulltext_v2.csv`

Row-level full-text dictionary feature table for the rebuilt 2019-2024 v2
corpus. It is generated by
`notebooks/42b_manual_srdi_fulltext_text_mining_v2.py` from
`data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv`.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One processed manual SRDI policy record |
| Current shape | 3989 rows x 43 columns |
| Text surface | `title` + `full_text` |
| Method | Substring dictionary using frozen full-text v1 85-term codebook |
| Generator | `notebooks/42b_manual_srdi_fulltext_text_mining_v2.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_fulltext_v2_quality_report.csv` |

The feature columns match the v1 full-text dictionary logic and add v2 audit
fields such as `source_workbook`, `source_schema_version`,
`keyword_count_source`, `full_text_missing`, `full_text_fallback_for_model`, and
`needs_jurisdiction_review`.

### `data/processed/province_year_srdi_text_features_fulltext_v2.csv`

Province-year aggregate full-text dictionary feature table for the v2 corpus.
It joins dictionary aggregates from
`data/processed/manual_policy_srdi_text_features_fulltext_v2.csv` to
`data/processed/province_year_srdi_policy_intensity_v2.csv`.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province unit-year |
| Current shape | 186 rows x 31 columns |
| Geographic units | 31 local province units |
| Date scope | 2019-2024 |
| Excludes | `central` records |
| Generator | `notebooks/42b_manual_srdi_fulltext_text_mining_v2.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_fulltext_v2_quality_report.csv` |

Core aggregate fields include the v2 policy-count base, full-text
missing/fallback counts, SRDI/Little-Giant/SME hit counts, supply/demand/
environment dictionary policy counts and shares, `any_tool_policy_count`, and
`avg_tool_category_count`. This is a policy-side text-feature table, not a final
DID-ready panel.

### `data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv`

Processed full-text policy-record table derived from
`data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`. It keeps the
same 2020-2025 window and province normalization as v0, but stores `full_text`
instead of the shorter abstract text. The `province` field represents the
reviewed policy jurisdiction, not necessarily the reposting source site.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One manually collected SRDI-related policy record |
| Current shape | 4475 rows x 25 columns |
| Date scope | 2020-2025 |
| Source URL uniqueness | Unique `source_url` |
| Generator | `scripts/manual_srdi_fulltext_processed_corpus.py` |
| Quality report | `outputs/manual_policy_srdi_processed_fulltext_v1_quality_report.csv` |

Additional or changed fields relative to
`manual_policy_srdi_policy_records_v0.csv`:

| Field | Type | Description |
| --- | --- | --- |
| `full_text` | string | Collected full policy text. |
| `full_text_len` | integer | Character length of `full_text`. |
| `full_text_contains_srdi` | boolean | Whether `full_text` contains `专精特新`. |
| `title_or_full_text_contains_srdi` | boolean | Whether either title or full text contains `专精特新`. |

### `data/processed/manual_policy_srdi_policy_records_v0.csv`

Processed policy-record table derived from
`data/interim/manual_policy_all_keyword_srdi.xlsx`. This is the first stable
record-level input for the manual SRDI policy-mining path.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One manually collected SRDI-related policy record |
| Current shape | 4475 rows x 24 columns |
| Date scope | 2020-2025 |
| Source URL uniqueness | Unique `source_url` |
| Generator | `scripts/manual_srdi_processed_corpus.py` |
| Quality report | `outputs/manual_policy_srdi_processed_v0_quality_report.csv` |

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable ID derived from `source_url`. |
| `province` | string / category | Reviewed analysis unit. `国家` is mapped to `central`; `新疆维吾尔自治区` and `新疆生产建设兵团` are mapped to `新疆`; reviewed reposted out-of-jurisdiction policies use the corrected policy jurisdiction from `configs/manual_srdi_jurisdiction_overrides_v1.csv`. |
| `province_before_correction` | string / category | Province value before applying reviewed jurisdiction overrides. |
| `province_correction_status` | string | `original` or `corrected`. |
| `province_correction_reason` | string | Reason for a reviewed correction, if any. |
| `province_correction_evidence` | string | Human-readable evidence used for the province correction. |
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

### `data/processed/manual_policy_srdi_text_features_v0.csv`

Row-level text-mining features built from
`data/processed/manual_policy_srdi_policy_records_v0.csv` in
`notebooks/40_manual_srdi_text_mining.py`. This v0 feature table uses title and
abstract text only. The policy-tool categories are transparent dictionary
features and require review before being interpreted as final manual policy
instrument labels.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One processed manual SRDI policy record |
| Current shape | 4475 rows x 31 columns |
| Text surface | `title` + `abstract` |
| Method | Substring dictionary |
| Generator | `notebooks/40_manual_srdi_text_mining.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_v0_quality_report.csv` |

Key fields:

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID inherited from processed manual records. |
| `province` | string / category | `central` or local province unit; Xinjiang source labels are merged into `新疆`. |
| `publish_year` | integer | Publication year. |
| `title_len` | integer | Character length of title. |
| `abstract_len` | integer | Character length of abstract. |
| `text_surface_len` | integer | Character length of title plus abstract separator. |
| `srdi_hit_count` | integer | Count of `专精特新` hits in title + abstract. |
| `little_giant_hit_count` | integer | Count of `小巨人` hits in title + abstract. |
| `sme_hit_count` | integer | Count of `中小企业` hits in title + abstract. |
| `supply_tool_hit_count` | integer | Count of supply-side dictionary term hits. |
| `has_supply_tool` | boolean | Whether any supply-side dictionary term appears. |
| `supply_matched_terms` | string | Semicolon-separated matched supply-side terms. |
| `demand_tool_hit_count` | integer | Count of demand-side dictionary term hits. |
| `has_demand_tool` | boolean | Whether any demand-side dictionary term appears. |
| `demand_matched_terms` | string | Semicolon-separated matched demand-side terms. |
| `environment_tool_hit_count` | integer | Count of environment-side dictionary term hits. |
| `has_environment_tool` | boolean | Whether any environment-side dictionary term appears. |
| `environment_matched_terms` | string | Semicolon-separated matched environment-side terms. |
| `policy_tool_category_count` | integer | Number of policy-tool categories hit by the row. |
| `has_any_policy_tool` | boolean | Whether any v0 tool category is hit. |
| `policy_tool_mix` | string | Semicolon-separated category mix among `supply`, `demand`, and `environment`. |

### `data/processed/province_year_srdi_text_features_v0.csv`

Province-year aggregate text feature table. It joins
`data/processed/province_year_srdi_policy_intensity_v0.csv` with aggregates
from `data/processed/manual_policy_srdi_text_features_v0.csv`.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province unit-year |
| Current shape | 186 rows x 24 columns |
| Geographic units | 31 local province units |
| Date scope | 2020-2025 |
| Excludes | `central` records |
| Generator | `notebooks/40_manual_srdi_text_mining.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_v0_quality_report.csv` |

Additional text-feature fields beyond
`province_year_srdi_policy_intensity_v0.csv`:

| Field | Type | Description |
| --- | --- | --- |
| `text_feature_policy_records` | integer | Number of local policy rows used for text features in the province-year. |
| `avg_text_surface_len` | float | Average title + abstract length. |
| `total_srdi_hit_count` | integer | Total `专精特新` hits. |
| `total_little_giant_hit_count` | integer | Total `小巨人` hits. |
| `total_sme_hit_count` | integer | Total `中小企业` hits. |
| `supply_tool_policy_count` | integer | Count of policies with supply-side dictionary hits. |
| `demand_tool_policy_count` | integer | Count of policies with demand-side dictionary hits. |
| `environment_tool_policy_count` | integer | Count of policies with environment-side dictionary hits. |
| `any_tool_policy_count` | integer | Count of policies with at least one v0 tool-category hit. |
| `avg_tool_category_count` | float | Average number of v0 tool categories hit by policies in the province-year. |
| `supply_tool_policy_share` | float | `supply_tool_policy_count / srdi_policy_count`, zero when no policies. |
| `demand_tool_policy_share` | float | `demand_tool_policy_count / srdi_policy_count`, zero when no policies. |
| `environment_tool_policy_share` | float | `environment_tool_policy_count / srdi_policy_count`, zero when no policies. |

### `outputs/manual_policy_srdi_tool_dictionary_v0.csv`

Dictionary codebook used by `notebooks/40_manual_srdi_text_mining.py`.

| Field | Type | Description |
| --- | --- | --- |
| `category` | string | One of `supply`, `demand`, or `environment`. |
| `term` | string | Chinese substring matched against title + abstract text. |

Related review artifacts:

- `outputs/manual_policy_srdi_tool_dictionary_coverage_v0.csv`: term-level
  `records_hit` and `total_hits` counts. Current revised dictionary has 85
  terms and no zero-coverage dictionary terms.
- `outputs/manual_policy_srdi_dictionary_revision_effect_v0.csv`: before/after
  effect table for the manual no-hit review revision. The revision added 32
  dictionary terms, reduced no-hit records from 352 to 271, and increased
  demand-side matches most strongly.
- `outputs/manual_policy_srdi_keyword_quality_check_v0.csv`: term-level quality
  table with coverage share, term length, and review flags. Current check flags
  50 terms for low/high coverage, short length, or broad meaning; these flags
  are cautions for interpretation, not automatic exclusion rules.
- `outputs/manual_policy_srdi_no_tool_hit_records_v0.csv`: all 271 rows with no
  revised v0 supply/demand/environment dictionary hit, including title and
  abstract for manual review.
- `outputs/manual_policy_srdi_no_tool_hit_review_sample_v0.csv`: deterministic
  30-row review sample, 5 no-hit records per year.
- `outputs/manual_policy_srdi_no_tool_hit_summary_v0.csv`: no-hit counts by
  year and province.

### `data/processed/manual_policy_srdi_text_features_fulltext_v1.csv`

Row-level full-text feature table built from
`data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv` in
`notebooks/42_manual_srdi_fulltext_text_mining.py`. It applies the same
reviewed 85-term dictionary as v0 to title + full text.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One processed manual SRDI policy record |
| Current shape | 4475 rows x 31 columns |
| Text surface | `title` + `full_text` |
| Method | Substring dictionary |
| Generator | `notebooks/42_manual_srdi_fulltext_text_mining.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv` |

Key difference from v0:

- no-hit records fall from 271 to 2 because full text contains substantially
  more policy-tool language;
- high-coverage dictionary terms rise from 1 to 41, so full-text feature shares
  require more caution before causal interpretation.

### `data/processed/province_year_srdi_text_features_fulltext_v1.csv`

Province-year aggregate full-text feature table. It joins the same
`data/processed/province_year_srdi_policy_intensity_v0.csv` policy-count frame
with aggregates from
`data/processed/manual_policy_srdi_text_features_fulltext_v1.csv`.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province unit-year |
| Current shape | 186 rows x 26 columns |
| Geographic units | 31 local province units |
| Date scope | 2020-2025 |
| Excludes | `central` records |
| Generator | `notebooks/42_manual_srdi_fulltext_text_mining.py` |
| Quality report | `outputs/manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv` |

Additional fields beyond the v0 aggregate include `avg_full_text_len` and
`any_tool_policy_share`. Count and share variables use the full-text v1
dictionary surface.

### `outputs/manual_policy_srdi_text_mining_v0_quality_report.csv`

Long-form QA report for manual SRDI text-mining v0 outputs. Current key
metrics:

- `row_feature_records=4475`
- `province_year_feature_records=186`
- `policy_records_with_any_tool_hit=4204`
- `policy_records_without_tool_hit=271`
- `no_tool_hit_review_sample_records=30`
- `dictionary_terms=85`
- `zero_coverage_terms=0`
- `low_coverage_terms_lte_5_records=6`
- `high_coverage_terms_gte_25pct_records=1`
- `terms_with_review_flags=50`

### `outputs/manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv`

Long-form QA report for manual SRDI full-text v1 feature outputs. Current key
metrics:

- `row_feature_records=4475`
- `province_year_feature_records=186`
- `policy_records_with_any_tool_hit=4473`
- `policy_records_without_tool_hit=2`
- `dictionary_terms=85`
- `zero_coverage_terms=0`
- `low_coverage_terms_lte_5_records=1`
- `high_coverage_terms_gte_25pct_records=41`
- `terms_with_review_flags=54`

The sharp decline in no-hit rows indicates that full text improves policy-tool
coverage. The increase in high-coverage terms indicates that full-text features
should be interpreted as broad policy-tool intensity proxies rather than
precise row-level labels.

### `outputs/manual_policy_srdi_text_mining_fulltext_v2_quality_report.csv`

Long-form QA report for manual SRDI full-text v2 dictionary-feature outputs.
Current key metrics:

- `row_feature_records=3989`
- `province_year_feature_records=186`
- `policy_records_with_any_tool_hit=3986`
- `policy_records_without_tool_hit=3`
- `dictionary_terms=85`
- `zero_coverage_terms=0`
- `low_coverage_terms_lte_5_records=2`
- `high_coverage_terms_gte_25pct_records=41`
- `terms_with_review_flags=55`
- `full_text_missing_records=1`
- `jurisdiction_review_candidate_records=0`

The v2 dictionary path intentionally reuses the reviewed full-text v1 codebook
so differences from v1 reflect the 2019-2024 corpus rebuild and jurisdiction
review rather than a new dictionary口径.

### `outputs/manual_srdi_fulltext_desc_*_v2.csv`

Grouped v2 descriptive-analysis tables generated by
`notebooks/44b_manual_srdi_fulltext_descriptive_keyword_quality_v2.py`. These
tables are intended for paper drafting and pre-MacBERT QA, not as final DID
regression inputs.

Current headline metrics:

- year trend covers exactly 2019-2024 and sums to 3989 policy records;
- local province distribution covers 31 province units;
- source composition is 3799 current-workbook rows and 190 2019 supplement
  rows;
- 2019 supplement rows include one empty-full-text record and one no-tool-hit
  record;
- v2 no-tool-hit total is 3 records.

### `outputs/manual_srdi_fulltext_keyword_quality_*_v2.csv`

Grouped v2 keyword-quality tables generated by the same notebook. They document
coverage bands, v1-v2 coverage deltas, category overlap, category saturation,
and interpretation notes for the frozen full-text dictionary codebook.

Current headline metrics:

- `dictionary_terms=85`
- `saturated_terms_gte_80pct=2`
- `high_coverage_terms_gte_50pct=15`
- `moderate_plus_terms_gte_25pct=41`
- `broad_intensity_signal_terms=15`
- `all_three_categories=3506`
- `no_tool=3`

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

### Manual SRDI Label-Rule Preparation v1

Files:

- `configs/manual_srdi_label_rule_keywords_v1.csv`
- `data/processed/manual_policy_srdi_label_docs_v1.csv`
- `data/processed/manual_policy_srdi_label_sampling_frame_v1.csv`
- `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv`

These files prepare the full-text corpus for DeepSeek/MacBERT multi-label
classification. Keyword rules are sampling and diagnostic aids, not final
policy-tool labels.

| Item | Value |
| --- | --- |
| Data layer | `configs`, `processed`, `interim` |
| Generator | `notebooks/46_manual_srdi_label_rule_keywords.py` |
| Policy universe | Manual SRDI full-text records, 2020-2025 |
| Label docs shape | 4475 rows x 9 columns |
| Sampling frame shape | 4475 rows |
| Round-1 sample shape | 800 rows |
| Sample pools | 200 each: supply-like, demand-like, environment-like, other-like |

Rule keyword fields:

| Field | Type | Description |
| --- | --- | --- |
| `category` | string | `supply`, `demand`, `environment`, or `other`. |
| `term` | string | Literal Chinese substring rule. |
| `rule_role` | string | `recall`, `discriminative`, or `other_signal`. |
| `specificity` | string | `broad`, `medium`, or `specific`. |
| `keep_for_sampling` | boolean | Whether the term is used when forming sample pools. |
| `keep_for_interpretation` | boolean | Whether the term can be shown as an interpretation aid. |
| `needs_context` | boolean | Whether isolated hits should be interpreted only with context. |
| `notes` | string | Audit note for broad or boundary terms. |

Label docs fields:

| Field | Type | Description |
| --- | --- | --- |
| `doc_id` | string | Stable policy ID inherited from `policy_id`. |
| `province` | string | `central` or local province unit. |
| `year` | integer | Publication year. |
| `title` | string | Policy title. |
| `issuing_agency` | string | Issuing agency when available. |
| `publish_date` | date-like string | Publication date. |
| `source_url` | string / URL | Original policy URL. |
| `clean_text` | string | Full text used for labeling prompts. |
| `text_len` | integer | Full-text character length. |

Sampling frame and round-1 sample add pool flags and rule-hit audit fields,
including `pool_supply_like`, `pool_demand_like`,
`pool_environment_like`, `pool_other_like`, recall/discriminative hit counts,
other-signal hit counts, and matched-term strings. `sample_pool` in the
round-1 sample records the primary sampling source and is not a final label.

### Manual SRDI DeepSeek Round-1 Labels v1

Files generated by `scripts/manual_srdi_deepseek_round1_label.py` after the
live API run:

- `data/raw/json/manual_srdi_deepseek_round1_v1/*.json`
- `data/interim/manual_policy_srdi_deepseek_labels_round1_v1.csv`
- `outputs/manual_policy_srdi_deepseek_round1_quality_report_v1.csv`

The script reads `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv`
and sends each sampled policy to DeepSeek for document-level multi-label
annotation. Raw API responses are cached separately from the parsed labels so
failed or ambiguous records can be audited and retried.

| Item | Value |
| --- | --- |
| Data layer | `raw`, `interim`, `outputs` |
| Generator | `scripts/manual_srdi_deepseek_round1_label.py` |
| Input sample | `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv` |
| Expected live output shape | 800 rows |
| API secret handling | `DEEPSEEK_API_KEY` environment variable only |
| Main use | Silver labels for MacBERT multi-label training |

Parsed label fields:

| Field | Type | Description |
| --- | --- | --- |
| `doc_id` | string | Stable policy ID. |
| `sample_pool` | string | Sampling source: supply-like, demand-like, environment-like, or other-like. |
| `province` | string | `central` or local province unit. |
| `year` | integer | Publication year. |
| `title` | string | Policy title. |
| `issuing_agency` | string | Issuing agency passed to the model. |
| `publish_date` | date-like string | Publication date. |
| `source_url` | string / URL | Original policy URL. |
| `model` | string | DeepSeek model used for the label call. |
| `label_status` | string | `success`, `failed`, or `dry_run`. |
| `error` | string | API or parse error when `label_status=failed`. |
| `raw_response_path` | string | Cached raw API response path when available. |
| `text_len` | integer | Full original `clean_text` character length. |
| `prompt_text_chars` | integer | Number of text characters included in the prompt. |
| `labeled_at` | datetime string | UTC timestamp when the output row was written. |
| `p_supply` | float | DeepSeek probability for supply-side policy tools. |
| `supply_evidence` | JSON string | Evidence snippets or phrases supporting `p_supply`. |
| `p_demand` | float | DeepSeek probability for demand-side policy tools. |
| `demand_evidence` | JSON string | Evidence snippets or phrases supporting `p_demand`. |
| `p_environment` | float | DeepSeek probability for environmental policy tools. |
| `environment_evidence` | JSON string | Evidence snippets or phrases supporting `p_environment`. |
| `p_other` | float | DeepSeek probability that the record should be excluded from policy-tool analysis. |
| `other_reason` | string | Model explanation for `p_other`. |
| `has_substantive_policy_tool` | boolean | Whether the model identifies substantive support tools. |
| `is_srdi_related` | boolean | Whether the model judges the document as SRDI-related. |
| `summary_reason` | string | Short overall explanation. |
| `y_supply` | integer | First-pass binary label, `p_supply >= 0.5`. |
| `y_demand` | integer | First-pass binary label, `p_demand >= 0.5`. |
| `y_environment` | integer | First-pass binary label, `p_environment >= 0.5`. |
| `y_other` | integer | First-pass binary exclusion label, `p_other >= 0.6` and all tool probabilities below 0.4. |

### Manual SRDI MacBERT Training Data v1

Files generated by `notebooks/48_manual_srdi_macbert_training_data.py`:

- `data/processed/manual_policy_srdi_macbert_training_dataset_v1.csv`
- `data/processed/manual_policy_srdi_macbert_training_v1/train.jsonl`
- `data/processed/manual_policy_srdi_macbert_training_v1/validation.jsonl`
- `data/processed/manual_policy_srdi_macbert_training_v1/test.jsonl`
- `outputs/manual_srdi_macbert_training_data_quality_report_v1.csv`
- `outputs/manual_srdi_macbert_training_split_summary_v1.csv`
- `outputs/manual_srdi_macbert_training_label_balance_v1.csv`
- `outputs/manual_srdi_macbert_training_pos_weight_v1.csv`

These files convert the 800 successful DeepSeek round-1 silver labels into a
stable MacBERT training-data split. They do not train a model. The split is
deterministic and approximately stratified by `sample_pool` and binary label
pattern.

| Item | Value |
| --- | --- |
| Data layer | `processed`, `outputs` |
| Generator | `notebooks/48_manual_srdi_macbert_training_data.py` |
| Input labels | `data/interim/manual_policy_srdi_deepseek_labels_round1_v1.csv` |
| Input full text | `data/processed/manual_policy_srdi_label_docs_v1.csv` |
| Dataset shape | 800 rows x 27 columns |
| JSONL split sizes | train 557, validation 120, test 123 |
| Main use | Input data for the future MacBERT multi-label training script |

Core fields:

| Field | Type | Description |
| --- | --- | --- |
| `doc_id` | string | Stable policy ID. |
| `split` | string | `train`, `validation`, or `test`. |
| `sample_pool` | string | Original round-1 sampling pool. |
| `province` | string | `central` or local province unit. |
| `year` | integer | Publication year. |
| `title` | string | Policy title. |
| `issuing_agency` | string | Issuing agency passed to the model. |
| `publish_date` | date-like string | Publication date. |
| `source_url` | string / URL | Original policy URL. |
| `model_text` | string | Compact MacBERT input text: title, agency, province/year, front text, and keyword-context snippets. |
| `model_text_len` | integer | Character length of `model_text` before tokenizer truncation. |
| `source_text_hash` | string | Short hash of the full source `clean_text`. |
| `model_text_hash` | string | Short hash of the constructed `model_text`. |
| `labels` | JSON-like list | Binary label vector `[supply, demand, environment, other]`. JSONL files store this as an array. |
| `soft_labels` | JSON-like list | DeepSeek probability vector `[p_supply, p_demand, p_environment, p_other]`. JSONL files store this as an array. |
| `y_supply` | integer | Binary supply label. |
| `y_demand` | integer | Binary demand label. |
| `y_environment` | integer | Binary environment label. |
| `y_other` | integer | Binary other/exclusion label. |
| `p_supply` | float | DeepSeek supply probability. |
| `p_demand` | float | DeepSeek demand probability. |
| `p_environment` | float | DeepSeek environment probability. |
| `p_other` | float | DeepSeek other probability. |
| `has_substantive_policy_tool` | boolean | DeepSeek substantive-tool flag. |
| `is_srdi_related` | boolean | DeepSeek SRDI-related flag. |
| `summary_reason` | string | DeepSeek short explanation. |
| `raw_response_path` | string / path | Cached raw DeepSeek response path. |

### Manual SRDI MacBERT Full-Corpus Prediction v1

Files generated by `scripts/manual_srdi_macbert_predict_full_corpus.py`:

- `data/processed/manual_policy_srdi_policy_classified_fulltext_v1.csv`
- `data/processed/province_year_srdi_macbert_tool_intensity_v1.csv`
- `outputs/manual_srdi_macbert_full_corpus_prediction_quality_report_v1.csv`
- `outputs/manual_srdi_macbert_full_corpus_probability_summary_v1.csv`
- `outputs/manual_srdi_macbert_full_corpus_panel_coverage_v1.csv`

The script applies the trained MacBERT multi-label checkpoint to the full
manual SRDI full-text corpus. Row-level predictions retain central records, but
the province-year intensity table excludes `central` and uses the existing
31-province x 2020-2025 panel skeleton.

| Item | Value |
| --- | --- |
| Data layer | `processed`, `outputs` |
| Generator | `scripts/manual_srdi_macbert_predict_full_corpus.py` |
| Input corpus | `data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv` |
| Input model | `outputs/manual_srdi_macbert_multilabel_v1/` |
| Prediction shape | 4475 rows |
| Province-year shape | 186 rows |
| Main use | DID-facing policy-tool intensity and full-corpus prediction QA |

Row-level prediction fields:

| Field | Type | Description |
| --- | --- | --- |
| `policy_id` | string | Stable policy ID inherited from the full-text processed corpus. |
| `province` | string | `central` or local province unit after jurisdiction corrections. |
| `source_label_original` | string | Original manual collection source label. |
| `jurisdiction_type` | string | `central` or `local`. |
| `publish_date` | date-like string | Publication date. |
| `publish_year` | integer | Publication year, 2020-2025. |
| `title` | string | Policy title. |
| `agency` | string | Issuing agency when available. |
| `source_url` | string / URL | Original policy URL. |
| `full_text_len` | integer | Source full-text character length. |
| `p_supply` | float | MacBERT probability for supply-side policy tools. |
| `p_demand` | float | MacBERT probability for demand-side policy tools. |
| `p_environment` | float | MacBERT probability for environmental policy tools. |
| `p_other` | float | MacBERT probability that the row is an exclusion/boundary text. |
| `supply_label` | integer | Hard label, `p_supply >= 0.5`. |
| `demand_label` | integer | Hard label, `p_demand >= 0.5`. |
| `environment_label` | integer | Hard label, `p_environment >= 0.5`. |
| `other_label` | integer | Hard exclusion label, `p_other >= 0.6` and all tool probabilities below 0.4. |
| `max_tool_prob` | float | Maximum of `p_supply`, `p_demand`, and `p_environment`. |
| `tool_probability_sum` | float | Sum of the three tool probabilities. |
| `any_tool_label` | integer | Whether any of the three tool hard labels is positive. |
| `valid_tool_policy` | integer | `1` when `other_label=0` and at least one tool hard label is positive. |
| `model_text_hash` | string | Short hash of the compact model input used for prediction. |

Province-year intensity fields include the baseline `srdi_policy_count` and
`log_srdi_policy_count_plus1`, raw probability sums/averages for each label,
filtered probability sums/averages using `valid_tool_policy`, hard-label policy
counts, high-confidence policy counts at probability `>=0.75`, and tool
probability shares. Use probability sums or averages as the main continuous
intensity variables; hard-label counts are audit and robustness variables.

### Manual SRDI MacBERT Full-Corpus Prediction v2

Files generated by `scripts/manual_srdi_macbert_predict_full_corpus_v2.py`:

- `data/processed/manual_policy_srdi_policy_classified_fulltext_v2.csv`
- `data/processed/province_year_srdi_macbert_tool_intensity_v2.csv`
- `outputs/manual_srdi_macbert_full_corpus_prediction_quality_report_v2.csv`
- `outputs/manual_srdi_macbert_full_corpus_probability_summary_v2.csv`
- `outputs/manual_srdi_macbert_full_corpus_panel_coverage_v2.csv`
- `outputs/manual_srdi_macbert_full_corpus_prediction_v2.log`

The v2 wrapper applies the frozen v1 MacBERT multi-label checkpoint to the
reviewed 2019-2024 v2 full-text corpus. It keeps the v1 prediction artifacts
unchanged, retains central records at row level, and excludes `central` from the
balanced province-year intensity table. The single row with missing full text is
retained and marked with `model_text_source=title_metadata_fallback`; its model
input is constructed from title, issuing agency, province, and year metadata.

| Item | Value |
| --- | --- |
| Data layer | `processed`, `outputs` |
| Generator | `scripts/manual_srdi_macbert_predict_full_corpus_v2.py` |
| Input corpus | `data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv` |
| Input model | `outputs/manual_srdi_macbert_multilabel_v1/` |
| Prediction shape | 3989 rows |
| Province-year shape | 186 rows |
| Province-year coverage | 31 local province units x 2019-2024 |
| Main use | v2 policy-side text intensity preparation and full-corpus prediction QA |

v2 row-level predictions include the v1 fields plus corpus audit fields inherited
from the v2 full-text source, including `source_workbook`,
`source_schema_version`, `keyword_count_source`, `full_text_missing`,
`full_text_fallback_for_model`, `needs_jurisdiction_review`,
`province_before_correction`, `province_correction_status`,
`province_correction_reason`, `province_correction_evidence`, and
`model_text_source`.

Current v2 prediction QA:

| Metric | Value |
| --- | ---: |
| `input_rows` | 3989 |
| `prediction_rows` | 3989 |
| `central_rows` | 192 |
| `local_rows` | 3797 |
| `province_year_rows` | 186 |
| `province_units` | 31 |
| `year_min` | 2019 |
| `year_max` | 2024 |
| `empty_full_text_rows` | 1 |
| `model_text_fallback_rows` | 1 |
| `jurisdiction_review_candidate_rows` | 0 |
| `valid_tool_policy_rows` | 3469 |
| `other_exclusion_rows` | 232 |

The independent v2 prediction-QA and variable-readiness notebook
`notebooks/49b_manual_srdi_macbert_prediction_qa_variable_readiness_v2.py`
writes paper-facing diagnostics and the handoff decision for the next
variable-selection step:

- `outputs/manual_srdi_macbert_prediction_qa_summary_v2.csv`
- `outputs/manual_srdi_macbert_prediction_probability_by_year_v2.csv`
- `outputs/manual_srdi_macbert_prediction_probability_by_province_v2.csv`
- `outputs/manual_srdi_macbert_prediction_tool_structure_by_year_v2.csv`
- `outputs/manual_srdi_macbert_prediction_dictionary_comparison_v2.csv`
- `outputs/manual_srdi_macbert_prediction_province_year_outliers_v2.csv`
- `outputs/manual_srdi_macbert_prediction_boundary_samples_v2.csv`
- `outputs/manual_srdi_macbert_variable_candidates_v2.csv`
- `outputs/manual_srdi_macbert_variable_readiness_decision_v2.csv`
- `outputs/manual_srdi_macbert_prediction_interpretation_notes_v2.csv`

Current decision: `ready_for_variable_selection_v2`. This is a QA and
readiness handoff only; it does not create the final policy-side DID-ready
panel.

### Manual SRDI DID-Ready Policy-Text Variables v1

File generated by
`notebooks/50_manual_srdi_policy_intensity_variable_selection.py`:

- `data/processed/province_year_srdi_policy_text_variables_v1.csv`

This table fixes the policy-text variable口径 for downstream staggered DID. It
uses the MacBERT province-year intensity table as the main source and joins the
full-text dictionary province-year table for robustness variables. It excludes
`central` and remains balanced at 31 local province units x 2020-2025.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One province-year |
| Current shape | 186 rows x 30 columns |
| Generator | `notebooks/50_manual_srdi_policy_intensity_variable_selection.py` |
| Main upstream table | `data/processed/province_year_srdi_macbert_tool_intensity_v1.csv` |
| Robustness upstream table | `data/processed/province_year_srdi_text_features_fulltext_v1.csv` |
| Main use | DID-facing policy-text intensity variables |

| Field | Type | Description |
| --- | --- | --- |
| `province` | string | Local province unit. `central` is excluded. |
| `publish_year` | integer | Publication year, 2020-2025. |
| `srdi_policy_count` | integer | Number of SRDI-related policy records in the province-year. Use as a policy-volume control or alternative intensity measure. |
| `srdi_policy_count_log` | float | `log(srdi_policy_count + 1)`. |
| `srdi_supply_intensity` | float | Main supply-side policy-tool intensity, defined as the province-year sum of MacBERT `p_supply`. |
| `srdi_demand_intensity` | float | Main demand-side policy-tool intensity, defined as the province-year sum of MacBERT `p_demand`. |
| `srdi_environment_intensity` | float | Main environmental policy-tool intensity, defined as the province-year sum of MacBERT `p_environment`. |
| `srdi_total_tool_intensity` | float | Sum of the three main policy-tool intensity variables. Use as an auxiliary aggregate, not as a replacement for tool-specific variables. |
| `srdi_supply_avg_probability` | float | Average `p_supply` among policies in the province-year. |
| `srdi_demand_avg_probability` | float | Average `p_demand` among policies in the province-year. |
| `srdi_environment_avg_probability` | float | Average `p_environment` among policies in the province-year. |
| `srdi_supply_probability_share` | float | Supply probability share among the three tool probability sums. |
| `srdi_demand_probability_share` | float | Demand probability share among the three tool probability sums. |
| `srdi_environment_probability_share` | float | Environment probability share among the three tool probability sums. |
| `srdi_supply_intensity_filtered` | float | Supply probability sum after excluding hard `other` rows. Robustness variable. |
| `srdi_demand_intensity_filtered` | float | Demand probability sum after excluding hard `other` rows. Robustness variable. |
| `srdi_environment_intensity_filtered` | float | Environment probability sum after excluding hard `other` rows. Robustness variable. |
| `srdi_total_tool_intensity_filtered` | float | Sum of the three filtered probability-sum variables. |
| `srdi_supply_hard_label_count` | integer | Count of policies with MacBERT supply hard label. Robustness variable. |
| `srdi_demand_hard_label_count` | integer | Count of policies with MacBERT demand hard label. Robustness variable. |
| `srdi_environment_hard_label_count` | integer | Count of policies with MacBERT environment hard label. Robustness variable. |
| `dict_supply_policy_count` | integer | Full-text dictionary count of supply-hit policies. Transparent robustness proxy. |
| `dict_demand_policy_count` | integer | Full-text dictionary count of demand-hit policies. Transparent robustness proxy. |
| `dict_environment_policy_count` | integer | Full-text dictionary count of environment-hit policies. Transparent robustness proxy. |
| `dict_supply_policy_share` | float | Full-text dictionary supply-hit share. |
| `dict_demand_policy_share` | float | Full-text dictionary demand-hit share. |
| `dict_environment_policy_share` | float | Full-text dictionary environment-hit share. |
| `srdi_valid_tool_policy_count` | integer | Count of records retained as valid tool policies after hard-label audit rules. Audit variable. |
| `srdi_valid_tool_policy_share` | float | Share of records retained as valid tool policies. Audit variable. |
| `srdi_other_exclusion_count` | integer | Count of hard `other` rows. Audit variable, not a substantive policy tool. |

Decision artifacts:

- `outputs/manual_srdi_policy_intensity_variable_selection_v1.csv`
- `outputs/manual_srdi_policy_intensity_variable_correlations_v1.csv`
- `outputs/manual_srdi_policy_intensity_variable_decision_v1.csv`

### Manual SRDI Policy-Text Variables v2

File generated by
`notebooks/50b_manual_srdi_policy_intensity_variable_selection_v2.py`:

- `data/processed/province_year_srdi_policy_text_variables_v2.csv`

This table fixes the v2 policy-text variable口径 for the corrected 2019-2024
policy-side panel. It uses the v2 MacBERT province-year intensity table as the
main source and joins the v2 full-text dictionary province-year table for
robustness and audit variables. It excludes `central` and remains balanced at
31 local province units x 2019-2024. It does not add DID merge keys, z-scores,
enterprise data, or DID estimates.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One province-year |
| Current shape | 186 rows x 57 columns |
| Generator | `notebooks/50b_manual_srdi_policy_intensity_variable_selection_v2.py` |
| Main upstream table | `data/processed/province_year_srdi_macbert_tool_intensity_v2.csv` |
| Robustness upstream table | `data/processed/province_year_srdi_text_features_fulltext_v2.csv` |
| QA upstream table | `outputs/manual_srdi_macbert_variable_readiness_decision_v2.csv` |
| Main use | Input table for the final v2 policy-side panel construction |

Main variables:

| Field | Type | Description |
| --- | --- | --- |
| `province` | string | Local province unit. `central` is excluded. |
| `publish_year` | integer | Publication year, 2019-2024. |
| `srdi_policy_count` | integer | Number of local SRDI-related policies in the province-year. |
| `srdi_policy_count_log` | float | `log(srdi_policy_count + 1)`. |
| `srdi_supply_intensity` | float | Main supply-side policy-tool intensity, defined as the province-year sum of MacBERT `p_supply`. |
| `srdi_demand_intensity` | float | Main demand-side policy-tool intensity, defined as the province-year sum of MacBERT `p_demand`. |
| `srdi_environment_intensity` | float | Main environmental policy-tool intensity, defined as the province-year sum of MacBERT `p_environment`. |
| `srdi_total_tool_intensity` | float | Sum of the three main policy-tool intensity variables. Auxiliary aggregate only. |

Robustness variables include `srdi_*_intensity_filtered`,
`srdi_*_hard_label_count`, `srdi_*_high_confidence_count`,
`dict_*_policy_count`, and `dict_*_policy_share`. Audit-only variables include
`srdi_valid_tool_policy_share`, `srdi_other_exclusion_count`,
`audit_fallback_full_text_for_model_count`, and
`audit_jurisdiction_review_candidate_count`.

Decision artifacts:

- `outputs/manual_srdi_policy_intensity_variable_selection_v2.csv`
- `outputs/manual_srdi_policy_intensity_variable_correlations_v2.csv`
- `outputs/manual_srdi_policy_intensity_variable_summary_v2.csv`
- `outputs/manual_srdi_policy_intensity_variable_decision_v2.csv`

Current decision: the v2 policy-text variable table is ready for final
policy-side panel construction.

### Manual SRDI DID-Ready Policy Intensity Panel v1

File generated by `notebooks/52_did_ready_policy_intensity_panel.py`:

- `data/processed/manual_srdi_did_policy_intensity_panel_v1.csv`

This is the final policy-side handoff table for downstream enterprise-panel
construction. It does not contain enterprise records and does not run DID
models. It adds stable merge keys and standardized convenience variables to the
selected policy-text variables.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province-year |
| Current shape | 186 rows x 35 columns |
| Generator | `notebooks/52_did_ready_policy_intensity_panel.py` |
| Main upstream table | `data/processed/province_year_srdi_policy_text_variables_v1.csv` |
| Crosswalk upstream table | `outputs/manual_srdi_did_policy_intensity_province_crosswalk_template_v1.csv` |
| Main use | Policy-side merge input for staggered DID panel construction |

| Field | Type | Description |
| --- | --- | --- |
| `policy_panel_id` | string | Stable policy-side province-year ID, built as `did_province_key` + year. |
| `did_province_key` | string | Recommended short province key for later enterprise-panel merge, such as `广东`, `北京`, or `新疆`. Must be confirmed against the firm panel before final merge. |
| `did_year` | integer | Policy year, 2020-2025. |
| `policy_province` | string | Canonical policy-side province label before short-name conversion, such as `广东省` or `广西壮族自治区`. |
| `province_short` | string | Short province label used to construct `did_province_key`. |
| `needs_firm_panel_confirmation` | boolean | `True` until the downstream enterprise panel province field is inspected. |
| `policy_data_version` | string | Version marker, currently `manual_srdi_did_policy_intensity_panel_v1`. |
| `srdi_policy_count` | integer | Baseline province-year SRDI policy count. |
| `srdi_policy_count_log` | float | `log(srdi_policy_count + 1)`. |
| `srdi_supply_intensity` | float | Main supply-side MacBERT probability-sum intensity. |
| `srdi_demand_intensity` | float | Main demand-side MacBERT probability-sum intensity. |
| `srdi_environment_intensity` | float | Main environment-side MacBERT probability-sum intensity. |
| `srdi_total_tool_intensity` | float | Sum of the three main policy-tool intensities. |
| `srdi_supply_probability_share` | float | Supply probability share among the three policy tools. |
| `srdi_demand_probability_share` | float | Demand probability share among the three policy tools. |
| `srdi_environment_probability_share` | float | Environment probability share among the three policy tools. |
| `srdi_supply_intensity_filtered` | float | Supply probability sum after hard-`other` filtering. |
| `srdi_demand_intensity_filtered` | float | Demand probability sum after hard-`other` filtering. |
| `srdi_environment_intensity_filtered` | float | Environment probability sum after hard-`other` filtering. |
| `srdi_total_tool_intensity_filtered` | float | Sum of filtered supply, demand, and environment intensities. |
| `srdi_supply_hard_label_count` | integer | Count of policies with hard supply label. |
| `srdi_demand_hard_label_count` | integer | Count of policies with hard demand label. |
| `srdi_environment_hard_label_count` | integer | Count of policies with hard environment label. |
| `dict_supply_policy_count` | integer | Full-text dictionary supply-hit count. |
| `dict_demand_policy_count` | integer | Full-text dictionary demand-hit count. |
| `dict_environment_policy_count` | integer | Full-text dictionary environment-hit count. |
| `srdi_valid_tool_policy_count` | integer | Count of valid tool policies after hard-label audit rules. |
| `srdi_valid_tool_policy_share` | float | Share of valid tool policies after hard-label audit rules. |
| `srdi_other_exclusion_count` | integer | Count of hard `other` records. Audit variable only. |
| `*_z` | float | Panel-wide z-score versions of policy count, log count, three main tool intensities, and total tool intensity. These are convenience variables for coefficient-scale comparison. |

Companion outputs:

- `outputs/manual_srdi_did_policy_intensity_panel_quality_report_v1.csv`
- `outputs/manual_srdi_did_policy_intensity_panel_variable_map_v1.csv`

### Manual SRDI DID-Ready Policy Intensity Panel v2

File generated by `notebooks/52b_did_ready_policy_intensity_panel_v2.py`:

- `data/processed/manual_srdi_did_policy_intensity_panel_v2.csv`

This is the final v2 policy-side handoff table for downstream enterprise-panel
construction. It corrects the analysis window to 2019-2024, excludes `central`
from province-year variation, and adds stable merge keys, robustness variables,
audit variables, and z-score convenience variables. It does not contain
enterprise records and does not run DID models.

| Item | Value |
| --- | --- |
| Data layer | `processed` |
| Observation unit | One local province-year |
| Current shape | 186 rows x 61 columns |
| Generator | `notebooks/52b_did_ready_policy_intensity_panel_v2.py` |
| Main upstream table | `data/processed/province_year_srdi_policy_text_variables_v2.csv` |
| Main use | Corrected 2019-2024 policy-side merge input for staggered DID panel construction |

| Field | Type | Description |
| --- | --- | --- |
| `policy_panel_id` | string | Stable policy-side province-year ID, built as `did_province_key` + year. |
| `did_province_key` | string | Recommended short province key for later enterprise-panel merge, such as `广东`, `北京`, or `新疆`. Must be confirmed against the firm panel before final merge. |
| `did_year` | integer | Policy year, 2019-2024. |
| `policy_province` | string | Canonical policy-side province label before short-name conversion. |
| `province_short` | string | Short province label used to construct `did_province_key`. |
| `needs_firm_panel_confirmation` | boolean | `True` until the downstream enterprise panel province field is inspected. |
| `policy_data_version` | string | Version marker, currently `manual_srdi_did_policy_intensity_panel_v2`. |
| `srdi_supply_intensity` | float | Main supply-side MacBERT probability-sum intensity. |
| `srdi_demand_intensity` | float | Main demand-side MacBERT probability-sum intensity. |
| `srdi_environment_intensity` | float | Main environment-side MacBERT probability-sum intensity. |
| `srdi_*_intensity_filtered` | float | Robustness probability sums after hard-`other` filtering. |
| `srdi_*_hard_label_count` | integer | Robustness hard-label policy counts. |
| `srdi_*_high_confidence_count` | integer | Robustness counts for policy-tool probability at least 0.75. |
| `dict_*_policy_count`, `dict_*_policy_share` | numeric | Transparent full-text dictionary robustness variables. |
| `audit_fallback_full_text_for_model_count` | integer | Count of model-input fallback rows in the province-year. The v2 panel total is 1. |
| `audit_jurisdiction_review_candidate_count` | integer | Count of unresolved jurisdiction-review candidates in the province-year. The v2 panel total is 0. |
| `*_z` | float | Panel-wide z-score versions of policy count, log count, three main tool intensities, and total tool intensity. |

Companion outputs:

- `outputs/manual_srdi_did_policy_intensity_province_crosswalk_template_v2.csv`
- `outputs/manual_srdi_did_policy_intensity_panel_quality_report_v2.csv`
- `outputs/manual_srdi_did_policy_intensity_panel_variable_map_v2.csv`
- `outputs/manual_srdi_did_policy_intensity_panel_decision_v2.csv`

Current policy-side status: `ready_for_enterprise_panel_merge`, pending
external confirmation that the enterprise panel province labels match
`did_province_key`.
