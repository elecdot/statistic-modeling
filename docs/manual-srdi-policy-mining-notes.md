# Manual SRDI Policy Mining Notes

This document records the current milestone for the manually collected SRDI
policy dataset and text-mining path. It is a method and paper drafting record,
not the active task board. Active work items stay only in the project README.

## Milestone Summary

The project shifted from continuing broad crawler expansion to using a manually
collected policy workbook:

- source workbook: `data/interim/manual_policy_all_keyword_srdi.xlsx`;
- collection scope: central and provincial policy records whose metadata
  contains `专精特新`;
- analysis window: 2020-2025;
- main purpose: build policy-intensity and text-feature variables that can be
  linked to the downstream staggered-DID panel and described in the paper.

This path is now the main working route for SRDI policy text mining. The earlier
gov.cn XXGK crawler remains documented and reusable, but it is not the primary
data source for the current paper workflow.

## Sample Definition

The processed manual policy records are stored in
`data/processed/manual_policy_srdi_policy_records_v0.csv`.

The current sample rules are:

- keep records dated from 2020-01-01 through 2025-12-31;
- exclude 2026 records from the main analysis window;
- map `国家` to `province=central`;
- map `新疆维吾尔自治区` and `新疆生产建设兵团` to `province=新疆`;
- preserve the original source label in `source_label_original`;
- keep central records in the row-level policy table;
- exclude central records from province-year intensity tables.

The processed row-level table contains 4475 records. The province-year
intensity table, `data/processed/province_year_srdi_policy_intensity_v0.csv`,
contains 186 rows, corresponding to 31 local province units across 2020-2025.

## Artifact Chain

The current manual SRDI pipeline is:

1. Manual workbook:
   `data/interim/manual_policy_all_keyword_srdi.xlsx`
2. Processed policy records:
   `data/processed/manual_policy_srdi_policy_records_v0.csv`
3. Province-year policy intensity:
   `data/processed/province_year_srdi_policy_intensity_v0.csv`
4. Row-level title/abstract text features:
   `data/processed/manual_policy_srdi_text_features_v0.csv`
5. Province-year text features:
   `data/processed/province_year_srdi_text_features_v0.csv`
6. Dictionary and QA artifacts:
   `outputs/manual_policy_srdi_tool_dictionary_v0.csv`,
   `outputs/manual_policy_srdi_tool_dictionary_coverage_v0.csv`,
   `outputs/manual_policy_srdi_dictionary_revision_effect_v0.csv`,
   `outputs/manual_policy_srdi_keyword_quality_check_v0.csv`, and
   `outputs/manual_policy_srdi_text_mining_v0_quality_report.csv`.

The processing script for the record-level and intensity tables is
`scripts/manual_srdi_processed_corpus.py`. The text-mining notebook is
`notebooks/40_manual_srdi_text_mining.py`.

The full-text v1 branch was added after the v0 milestone:

1. Full-text manual workbook:
   `data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`
2. Processed full-text records:
   `data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv`
3. Row-level full-text text features:
   `data/processed/manual_policy_srdi_text_features_fulltext_v1.csv`
4. Province-year full-text text features:
   `data/processed/province_year_srdi_text_features_fulltext_v1.csv`
5. Full-text QA artifacts:
   `outputs/manual_policy_srdi_processed_fulltext_v1_quality_report.csv` and
   `outputs/manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv`.

The full-text processing script is
`scripts/manual_srdi_fulltext_processed_corpus.py`. The full-text text-mining
notebook is `notebooks/42_manual_srdi_fulltext_text_mining.py`.

## Text-Mining Method

The v0 text-mining surface is `title + abstract`. The v1 text-mining surface is
`title + full_text`. Both versions use the same transparent substring
dictionary rather than a segmentation model or supervised classifier.

The dictionary has three policy-tool categories:

- `supply`: direct resources, services, skills, platforms, technology,
  spatial support, factor guarantees, and related supply-side supports;
- `demand`: procurement, exhibitions, market expansion, demonstration,
  matching, exports, and external-market terms;
- `environment`: finance, taxation, standards, intellectual property,
  recognition, evaluation, industry-chain ecosystem, and institutional
  environment terms.

Rows can match multiple categories. These features should be described as
dictionary indicators. They are not final manual policy-tool classification
labels.

## Dictionary Review And Revision

An initial no-hit inspection showed that the first dictionary missed several
clear policy-tool expressions. A 30-record no-hit sample, with 5 records per
year, found that about half of sampled no-hit records still had identifiable
policy-tool meaning.

Typical missed expressions were:

- supply-side: energy-saving diagnosis services, overseas services,
  vocational-skills support, internship posts, intelligent manufacturing
  spaces, electricity-use guarantees, and other service/factor supports;
- demand-side: exhibitions, expos, Canton Fair booths, going global, export and
  external-market expansion;
- environment-side: technology finance, green loans, bank-insurance services,
  risk reduction, bank-enterprise relations, and direct policy delivery.

The dictionary was revised based on these sample findings. The measured effect
is recorded in `outputs/manual_policy_srdi_dictionary_revision_effect_v0.csv`:

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Dictionary terms | 53 | 85 | +32 |
| Records with any tool hit | 4123 | 4204 | +81 |
| Records without tool hit | 352 | 271 | -81 |
| Supply-side hit records | 3497 | 3562 | +65 |
| Demand-side hit records | 874 | 1093 | +219 |
| Environment-side hit records | 3123 | 3179 | +56 |

The main gain came from demand-side coverage, especially concrete exhibition,
export, external-market, and going-global expressions.

## Keyword Quality Check

The keyword quality check is stored in
`outputs/manual_policy_srdi_keyword_quality_check_v0.csv`.

Current quality results:

- dictionary terms: 85;
- zero-coverage terms: 0;
- low-coverage terms, with at most 5 matching records: 6;
- high-coverage terms, matching at least 25% of records: 1;
- terms with any review flag: 50.

Review flags are interpretation cautions. They are not automatic deletion
rules.

Important interpretation cautions:

- `创新` is the only high-coverage term. It should be interpreted as a broad
  innovation-orientation signal, not as a precise policy instrument.
- Short terms such as `财政`, `研发`, `融资`, `认定`, `标准`, and `银行` can be
  useful in aggregate but should not be over-interpreted individually.
- Broad-meaning terms such as `产业链`, `供应链`, `认定`, and `评价` should be
  reported as dictionary-feature components rather than manual labels.

The current dictionary has no zero-coverage terms after revision.

## Full-Text V1 Update

The full-text v1 run keeps the same 2020-2025 sample window, province
normalization, and reviewed 85-term dictionary. The only intended measurement
change is the text surface: `title + full_text` replaces `title + abstract`.

Key full-text v1 diagnostics:

- processed full-text records: 4475;
- missing full text: 0;
- median full-text length: 5359 Chinese characters;
- maximum full-text length: 316503 Chinese characters;
- policy records with any tool hit: 4473;
- policy records without tool hit: 2;
- zero-coverage dictionary terms: 0;
- high-coverage terms, matching at least 25% of records: 41;
- terms with review flags: 54.

The main methodological implication is that full text almost eliminates no-hit
records, but it also makes broad dictionary terms much more common. Therefore,
full-text variables should be framed as policy-tool intensity proxies and
interpreted at aggregate levels, especially province-year aggregates, rather
than as precise row-level labels.

## V0 And V1 Measure Comparison

The v0/v1 comparison notebook is
`notebooks/43_manual_srdi_text_measure_comparison.py`.

Current comparison results:

- matched policy records: 4475;
- v0 no-tool-hit records: 271;
- v1 no-tool-hit records: 2;
- v0 no-hit rows recovered by v1: 269;
- still no-hit after v1: 2;
- high-coverage terms: 1 in v0 and 41 in full-text v1;
- minimum Pearson correlation among v0/v1 province-year tool shares: 0.280.

The comparison supports using full-text v1 as the main aggregate text-intensity
measure because it greatly improves recall. It also supports keeping v0 as a
robustness or method-comparison measure because full-text terms can become
broad and highly saturated. In paper language, v1 should be presented as an
aggregate text-intensity proxy rather than a precise row-level instrument label.

## Full-Text Descriptive Analysis

The full-text descriptive notebook is
`notebooks/44_manual_srdi_fulltext_descriptive_analysis.py`.

It produces the main paper-facing descriptive tables and figures under the
full-text v1 axis, including annual policy counts, province distribution,
full-text tool shares by year, province-year policy-intensity heatmap,
province-level tool structure, central/local comparison, no-hit summary, and
high-coverage dictionary terms.

Current descriptive diagnostics:

- annual trend covers 2020-2025;
- local province distribution covers 31 province units;
- province-year policy-intensity matrix is 31 x 6;
- full-text no-hit records total 2;
- high-coverage full-text dictionary terms total 41.

## Full-Text Keyword Quality Interpretation

The full-text keyword quality notebook is
`notebooks/45_manual_srdi_fulltext_keyword_quality.py`.

Current keyword-quality diagnostics:

- dictionary terms: 85;
- saturated terms, hitting at least 80% of records: 2;
- high-coverage terms, hitting at least 50% of records: 15;
- moderate-or-higher terms, hitting at least 25% of records: 41;
- rare terms, hitting fewer than 5% of records: 15;
- broad-meaning terms flagged by rule: 24;
- broad-intensity signal terms: 15;
- no-tool records: 2.

Category-level diagnostics:

- any-tool hit share: 0.9996;
- supply hit share: 0.9937;
- environment hit share: 0.9853;
- demand hit share: 0.8851;
- all-three-category hit share: 0.8769.

These results explain why supply and environment nearly coincide with the
any-tool indicator, and why demand rises sharply under full-text matching. In
full policy text, broad innovation, funding, platform, financial, standard,
recognition, ecosystem, matching, scenario, export, and procurement language
often appears in implementation clauses even when titles and abstracts are
narrower.

The paper-facing interpretation should therefore emphasize province-year
aggregate intensity and orientation proxies. It should avoid claiming that a
single row-level hit is a final manual label or that supply, demand, and
environment are mutually exclusive full-text classifications.

## Label-Rule Sampling Preparation

The label-rule preparation notebook is
`notebooks/46_manual_srdi_label_rule_keywords.py`.

This step changes the role of keywords. The full-text dictionary is no longer
treated as a candidate final classifier. Instead, keywords are used as:

- recall rules for broad candidate discovery;
- discriminative rules for supply/demand/environment-like sampling pools;
- other-signal rules for procedural or low-substance boundary samples;
- diagnostics for later DeepSeek/MacBERT prediction conflicts.

Current label-rule outputs:

- rule keyword config:
  `configs/manual_srdi_label_rule_keywords_v1.csv`;
- label document table:
  `data/processed/manual_policy_srdi_label_docs_v1.csv`;
- sampling frame:
  `data/processed/manual_policy_srdi_label_sampling_frame_v1.csv`;
- round-1 DeepSeek sample:
  `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv`.

Current preparation diagnostics:

- label docs: 4475 records;
- sampling frame: 4475 records;
- round-1 sample: 800 records;
- sample pools: 200 records each for supply-like, demand-like,
  environment-like, and other-like;
- sampling is deterministic, without replacement, and uses `random_state=42`.

The next modeling stage should call DeepSeek on the round-1 sample and produce
probabilistic multi-label outputs. The rule pools should not be interpreted as
the final labels.

## Paper Drafting Notes

Potential data-source wording:

> 本文基于手工收集的中央及省级“专精特新”相关政策记录构建政策文本数据集。样本覆盖 2020-2025 年，保留中央政策用于文本描述，并将地方政策聚合为省份-年份层面的政策强度指标。其中，新疆维吾尔自治区与新疆生产建设兵团在省份层面合并为“新疆”。

Potential policy-intensity wording:

> 省份-年份政策强度首先以当年包含“专精特新”关键词的地方政策数量衡量，并进一步构造 `log(count + 1)`、关键词命中次数、机构覆盖等辅助指标。中央政策不进入省份差异强度计算。

Potential text-mining wording:

> 在文本挖掘部分，本文使用政策标题与正文构造可解释的词典特征，并保留标题与摘要版本作为方法基准。词典围绕供给型、需求型和环境型政策工具展开，采用中文短语的直接匹配方式。该方法强调可复核性与解释性，不将词典命中直接等同于人工政策工具分类。

Potential dictionary-revision wording:

> 为降低漏检，本文对初始词典的 no-hit 样本进行了人工抽检。抽检样本按年份分层，每年 5 条，共 30 条。人工复核发现，部分未命中记录仍包含明确的服务供给、市场拓展、金融服务与制度环境等政策工具含义。因此，本文据此补充相关关键词。修订后，词典规模由 53 项增至 85 项，未命中记录由 352 条降至 271 条。

Potential limitation wording:

> 需要说明的是，全文词典匹配虽然显著降低了未命中比例，但部分词项具有较宽语义，并且在全文中覆盖率较高。因此，相关变量更适合作为省份-年份政策文本强度和政策工具倾向的可解释代理变量，而不宜理解为逐条政策的最终人工分类结果。
