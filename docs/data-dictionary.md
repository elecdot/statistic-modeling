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
