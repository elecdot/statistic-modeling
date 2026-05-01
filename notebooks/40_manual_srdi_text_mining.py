# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: statistic-modeling (3.11.14)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Manual SRDI Policy Text Mining v0
#
# This notebook starts the text-mining path after the project shifted from
# broad crawler expansion to the manually collected national/provincial SRDI
# policy workbook.
#
# Scope:
#
# - source table: `data/processed/manual_policy_srdi_policy_records_v0.csv`;
# - text surface: title + abstract only;
# - method: transparent keyword dictionary, no segmentation model;
# - outputs: row-level text features and province-year aggregate text features.
#
# This is intentionally a first-pass feature notebook. It should produce
# explainable variables for paper tables and DID linkage before any richer NLP
# model is considered.
#
# Manual review update:
#
# - A 30-record no-hit sample, 5 records per year, showed that about half of
#   no-hit records still had recognizable policy-tool meanings.
# - Supply-side misses mainly involved service provision, factor guarantees, and
#   spatial support, such as energy-saving diagnosis, overseas service,
#   vocational skills, internship posts, intelligent manufacturing spaces, and
#   electricity-use guarantees.
# - Demand-side misses involved concrete exhibition and external-market terms,
#   such as expo/fair names, Canton Fair booths, going global, and external
#   market expansion.
# - Environment-side misses involved financial service and institutional
#   environment terms, such as technology finance, green loans, bank-insurance
#   service, risk reduction, bank-enterprise relations, and policy delivery.

# %%
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
POLICY_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_v0.csv"
INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v0.csv"
ROW_FEATURES_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_v0.csv"
PROVINCE_YEAR_FEATURES_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_text_features_v0.csv"
QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_text_mining_v0_quality_report.csv"
DICTIONARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_v0.csv"
DICTIONARY_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_v0.csv"
DICTIONARY_REVISION_EFFECT_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_dictionary_revision_effect_v0.csv"
KEYWORD_QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_keyword_quality_check_v0.csv"
NO_TOOL_HIT_RECORDS_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_v0.csv"
NO_TOOL_HIT_SAMPLE_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_review_sample_v0.csv"
NO_TOOL_HIT_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_summary_v0.csv"

SRDI_KEYWORDS = {
	"srdi": "专精特新",
	"little_giant": "小巨人",
	"sme": "中小企业",
}
TEXT_COLUMNS = ["title", "abstract"]

PRE_REVIEW_DICTIONARY_METRICS = {
	"dictionary_terms": 53,
	"policy_records_with_any_tool_hit": 4123,
	"policy_records_without_tool_hit": 352,
	"supply_tool_policy_records": 3497,
	"demand_tool_policy_records": 874,
	"environment_tool_policy_records": 3123,
}

BROAD_MEANING_TERMS_FOR_REVIEW = {
	"财政",
	"研发",
	"创新",
	"人才",
	"培训",
	"服务平台",
	"载体",
	"空间",
	"采购",
	"供需",
	"对接",
	"场景",
	"银行",
	"保险",
	"基金",
	"标准",
	"认定",
	"评价",
	"产业链",
	"供应链",
}
LOW_COVERAGE_TERM_THRESHOLD = 5
HIGH_COVERAGE_SHARE_THRESHOLD = 0.25

POLICY_TOOL_DICTIONARY = {
	"supply": [
		"财政",
		"补贴",
		"补助",
		"奖励",
		"奖补",
		"专项资金",
		"资金支持",
		"研发",
		"创新",
		"技改",
		"技术改造",
		"设备更新",
		"人才",
		"培训",
		"职业技能",
		"技能提升",
		"见习岗位",
		"见习",
		"服务平台",
		"公共服务",
		"诊断服务",
		"节能诊断",
		"出海服务",
		"孵化",
		"载体",
		"空间",
		"智造空间",
		"数字化",
		"工业互联网",
		"用电",
		"要素保障",
	],
	"demand": [
		"政府采购",
		"采购",
		"首台套",
		"首批次",
		"首版次",
		"市场开拓",
		"展会",
		"参展",
		"展览会",
		"博览会",
		"广交会",
		"展位",
		"走出去",
		"外贸",
		"出口",
		"国际化",
		"国际市场",
		"跨境电子商务",
		"拓市场",
		"供需",
		"对接",
		"订单",
		"应用示范",
		"推广应用",
		"场景",
	],
	"environment": [
		"融资",
		"贷款",
		"信贷",
		"担保",
		"基金",
		"科技金融",
		"绿色金融",
		"绿贷",
		"银行",
		"保险",
		"银行保险",
		"银企",
		"风险减量",
		"上市",
		"挂牌",
		"税收",
		"减税",
		"降费",
		"营商环境",
		"政策直达",
		"直达快享",
		"知识产权",
		"标准",
		"认定",
		"评价",
		"梯度培育",
		"培育库",
		"产业链",
		"供应链",
	],
}

# %% [markdown]
# ## 1. Load Processed Records
#
# The processed policy table already encodes the project-level scope decisions:
# 2020-2025 only, central/local labels, and the Xinjiang merge rule.

# %%
records = pd.read_csv(POLICY_RECORDS_PATH)
intensity = pd.read_csv(INTENSITY_PATH)

records["text_surface"] = records[TEXT_COLUMNS].fillna("").agg("。".join, axis=1)
records["title_len"] = records["title"].fillna("").str.len()
records["abstract_len"] = records["abstract"].fillna("").str.len()
records["text_surface_len"] = records["text_surface"].str.len()

load_overview = pd.DataFrame(
	[
		{"metric": "policy_records", "value": len(records), "note": "Processed manual SRDI records."},
		{"metric": "unique_source_urls", "value": records["source_url"].nunique(), "note": "Should match policy_records."},
		{"metric": "province_units_in_records", "value": records["province"].nunique(), "note": "Includes central."},
		{"metric": "local_intensity_rows", "value": len(intensity), "note": "31 province units x 6 years."},
		{"metric": "min_publish_year", "value": records["publish_year"].min(), "note": "Analysis window lower bound."},
		{"metric": "max_publish_year", "value": records["publish_year"].max(), "note": "Analysis window upper bound."},
	],
)
load_overview

# %% [markdown]
# ## 2. Dictionary Feature Builder
#
# The v0 dictionary is deliberately explicit and small. It follows the common
# policy-tool split used in this project:
#
# - supply-side: direct funding, technology, talent, platforms, digitalization;
# - demand-side: procurement, market expansion, demonstration, matching;
# - environment-side: finance, taxation, standards, IP, recognition, ecosystem.
#
# A row can hit multiple categories. These are weak text-mining features, not
# final human-coded policy labels.

# %%
def count_keyword_hits(text: str, keywords: list[str]) -> int:
	"""Count substring hits for a transparent Chinese keyword dictionary."""
	return sum(len(re.findall(re.escape(keyword), text)) for keyword in keywords)


def matched_keywords(text: str, keywords: list[str]) -> str:
	"""Return semicolon-separated dictionary terms that occur at least once."""
	return ";".join(keyword for keyword in keywords if keyword in text)


feature_rows = records.copy()
for column_key, keyword in SRDI_KEYWORDS.items():
	feature_rows[f"{column_key}_hit_count"] = feature_rows["text_surface"].map(lambda text, kw=keyword: count_keyword_hits(text, [kw]))
	feature_rows[f"has_{column_key}"] = feature_rows[f"{column_key}_hit_count"] > 0

for category, keywords in POLICY_TOOL_DICTIONARY.items():
	feature_rows[f"{category}_tool_hit_count"] = feature_rows["text_surface"].map(lambda text, kws=keywords: count_keyword_hits(text, kws))
	feature_rows[f"has_{category}_tool"] = feature_rows[f"{category}_tool_hit_count"] > 0
	feature_rows[f"{category}_matched_terms"] = feature_rows["text_surface"].map(lambda text, kws=keywords: matched_keywords(text, kws))

tool_indicator_columns = [f"has_{category}_tool" for category in POLICY_TOOL_DICTIONARY]
feature_rows["policy_tool_category_count"] = feature_rows[tool_indicator_columns].sum(axis=1)
feature_rows["has_any_policy_tool"] = feature_rows["policy_tool_category_count"] > 0
feature_rows["policy_tool_mix"] = feature_rows.apply(
	lambda row: ";".join(category for category in POLICY_TOOL_DICTIONARY if row[f"has_{category}_tool"]),
	axis=1,
)

row_feature_columns = [
	"policy_id",
	"province",
	"source_label_original",
	"jurisdiction_type",
	"publish_date",
	"publish_year",
	"title",
	"agency",
	"source_url",
	"title_len",
	"abstract_len",
	"text_surface_len",
	"keyword_count",
	"srdi_hit_count",
	"has_srdi",
	"little_giant_hit_count",
	"has_little_giant",
	"sme_hit_count",
	"has_sme",
	"supply_tool_hit_count",
	"has_supply_tool",
	"supply_matched_terms",
	"demand_tool_hit_count",
	"has_demand_tool",
	"demand_matched_terms",
	"environment_tool_hit_count",
	"has_environment_tool",
	"environment_matched_terms",
	"policy_tool_category_count",
	"has_any_policy_tool",
	"policy_tool_mix",
]
row_features = feature_rows[row_feature_columns].copy()
row_features.head()

# %% [markdown]
# ## 3. Descriptive Tables
#
# These tables are early paper-facing diagnostics. They show whether the manual
# dataset has enough variation over year, province, and simple policy-tool
# categories to support later analysis.

# %%
year_tool_summary = (
	row_features.groupby("publish_year")
	.agg(
		policy_records=("policy_id", "size"),
		has_supply_tool=("has_supply_tool", "sum"),
		has_demand_tool=("has_demand_tool", "sum"),
		has_environment_tool=("has_environment_tool", "sum"),
		has_any_policy_tool=("has_any_policy_tool", "sum"),
		avg_tool_category_count=("policy_tool_category_count", "mean"),
	)
	.reset_index()
)
year_tool_summary

# %%
province_tool_summary = (
	row_features.loc[row_features["jurisdiction_type"] == "local"]
	.groupby("province")
	.agg(
		policy_records=("policy_id", "size"),
		has_supply_tool=("has_supply_tool", "sum"),
		has_demand_tool=("has_demand_tool", "sum"),
		has_environment_tool=("has_environment_tool", "sum"),
		has_any_policy_tool=("has_any_policy_tool", "sum"),
		avg_tool_category_count=("policy_tool_category_count", "mean"),
	)
	.reset_index()
	.sort_values(["policy_records", "province"], ascending=[False, True])
)
province_tool_summary.head(20)

# %%
central_local_summary = (
	row_features.groupby("jurisdiction_type")
	.agg(
		policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		has_supply_tool=("has_supply_tool", "sum"),
		has_demand_tool=("has_demand_tool", "sum"),
		has_environment_tool=("has_environment_tool", "sum"),
		has_any_policy_tool=("has_any_policy_tool", "sum"),
	)
	.reset_index()
)
central_local_summary

# %% [markdown]
# ## 4. Province-Year Text Features
#
# This table joins the policy-count intensity table with aggregate text-mining
# indicators. It remains a candidate table: the dictionary is transparent but
# not yet a validated hand-coded policy-tool taxonomy.

# %%
local_features = row_features.loc[row_features["jurisdiction_type"] == "local"].copy()
province_year_features = (
	local_features.groupby(["province", "publish_year"], dropna=False)
	.agg(
		text_feature_policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		total_srdi_hit_count=("srdi_hit_count", "sum"),
		total_little_giant_hit_count=("little_giant_hit_count", "sum"),
		total_sme_hit_count=("sme_hit_count", "sum"),
		supply_tool_policy_count=("has_supply_tool", "sum"),
		demand_tool_policy_count=("has_demand_tool", "sum"),
		environment_tool_policy_count=("has_environment_tool", "sum"),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
		avg_tool_category_count=("policy_tool_category_count", "mean"),
	)
	.reset_index()
)

province_year_features = intensity.merge(province_year_features, on=["province", "publish_year"], how="left")
feature_numeric_columns = [
	"text_feature_policy_records",
	"total_srdi_hit_count",
	"total_little_giant_hit_count",
	"total_sme_hit_count",
	"supply_tool_policy_count",
	"demand_tool_policy_count",
	"environment_tool_policy_count",
	"any_tool_policy_count",
]
province_year_features[feature_numeric_columns] = province_year_features[feature_numeric_columns].fillna(0).astype("int64")
province_year_features["avg_text_surface_len"] = province_year_features["avg_text_surface_len"].fillna(0.0)
province_year_features["avg_tool_category_count"] = province_year_features["avg_tool_category_count"].fillna(0.0)
province_year_features["supply_tool_policy_share"] = (
	province_year_features["supply_tool_policy_count"] / province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
).fillna(0.0)
province_year_features["demand_tool_policy_share"] = (
	province_year_features["demand_tool_policy_count"] / province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
).fillna(0.0)
province_year_features["environment_tool_policy_share"] = (
	province_year_features["environment_tool_policy_count"] / province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
).fillna(0.0)
province_year_features.head()

# %% [markdown]
# ## 5. Write v0 Artifacts
#
# These outputs are deterministic and can be regenerated by running this
# notebook. They are intentionally small CSVs so they can be inspected directly.

# %%
dictionary_rows = [
	{
		"category": category,
		"term": term,
		"records_hit": int(feature_rows["text_surface"].map(lambda text, t=term: t in text).sum()),
		"total_hits": int(feature_rows["text_surface"].map(lambda text, t=term: count_keyword_hits(text, [t])).sum()),
	}
	for category, terms in POLICY_TOOL_DICTIONARY.items()
	for term in terms
]
dictionary_table = pd.DataFrame(dictionary_rows)
dictionary_table["record_hit_share"] = dictionary_table["records_hit"] / len(feature_rows)


def keyword_review_flags(row: pd.Series) -> str:
	"""Create auditable review flags for dictionary terms."""
	flags = []
	if row["records_hit"] == 0:
		flags.append("zero_coverage")
	elif row["records_hit"] <= LOW_COVERAGE_TERM_THRESHOLD:
		flags.append("low_coverage")
	if row["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD:
		flags.append("high_coverage")
	if len(str(row["term"])) <= 2:
		flags.append("short_term")
	if row["term"] in BROAD_MEANING_TERMS_FOR_REVIEW:
		flags.append("broad_meaning_review")
	return ";".join(flags)


keyword_quality_table = dictionary_table.copy()
keyword_quality_table["term_length"] = keyword_quality_table["term"].str.len()
keyword_quality_table["review_flags"] = keyword_quality_table.apply(keyword_review_flags, axis=1)
keyword_quality_table["needs_review"] = keyword_quality_table["review_flags"].ne("")

no_tool_hit_records = (
	feature_rows.loc[~feature_rows["has_any_policy_tool"]]
	.assign(
		review_status="needs_dictionary_review",
		review_reason="no_v0_policy_tool_dictionary_hit",
	)
	[
		[
			"policy_id",
			"province",
			"source_label_original",
			"jurisdiction_type",
			"publish_date",
			"publish_year",
			"title",
			"agency",
			"source_url",
			"abstract",
			"text_surface_len",
			"srdi_hit_count",
			"little_giant_hit_count",
			"sme_hit_count",
			"review_status",
			"review_reason",
		]
	]
	.sort_values(["publish_year", "province", "title"], ignore_index=True)
)

no_tool_hit_sample = (
	no_tool_hit_records.groupby("publish_year", group_keys=False)
	.head(5)
	.reset_index(drop=True)
)

no_tool_hit_year_summary = (
	no_tool_hit_records.groupby("publish_year")
	.size()
	.reset_index(name="no_tool_hit_records")
)
no_tool_hit_province_summary = (
	no_tool_hit_records.groupby("province")
	.size()
	.reset_index(name="no_tool_hit_records")
	.sort_values(["no_tool_hit_records", "province"], ascending=[False, True])
)
no_tool_hit_summary = pd.concat(
	[
		no_tool_hit_year_summary.assign(summary_type="year").rename(columns={"publish_year": "group_value"}),
		no_tool_hit_province_summary.assign(summary_type="province").rename(columns={"province": "group_value"}),
	],
	ignore_index=True,
)

current_dictionary_metrics = {
	"dictionary_terms": len(dictionary_table),
	"policy_records_with_any_tool_hit": int(row_features["has_any_policy_tool"].sum()),
	"policy_records_without_tool_hit": int((~row_features["has_any_policy_tool"]).sum()),
	"supply_tool_policy_records": int(row_features["has_supply_tool"].sum()),
	"demand_tool_policy_records": int(row_features["has_demand_tool"].sum()),
	"environment_tool_policy_records": int(row_features["has_environment_tool"].sum()),
}
dictionary_revision_effect = pd.DataFrame(
	[
		{
			"metric": metric,
			"before_review_revision": before_value,
			"after_review_revision": current_dictionary_metrics[metric],
			"delta": current_dictionary_metrics[metric] - before_value,
			"relative_change": (current_dictionary_metrics[metric] - before_value) / before_value if before_value else pd.NA,
			"method_note": "Updated after manual review of a 30-record no-hit sample, 5 records per year.",
		}
		for metric, before_value in PRE_REVIEW_DICTIONARY_METRICS.items()
	]
)

quality_report = pd.DataFrame(
	[
		{"metric": "row_feature_records", "value": len(row_features), "note": "Rows in row-level text feature table."},
		{"metric": "province_year_feature_records", "value": len(province_year_features), "note": "Rows in province-year text feature table."},
		{"metric": "policy_records_with_any_tool_hit", "value": int(row_features["has_any_policy_tool"].sum()), "note": "Rows hitting at least one policy-tool dictionary category."},
		{"metric": "policy_records_without_tool_hit", "value": int((~row_features["has_any_policy_tool"]).sum()), "note": "Rows with no v0 policy-tool dictionary hit."},
		{"metric": "no_tool_hit_review_sample_records", "value": len(no_tool_hit_sample), "note": "Deterministic review sample: first 5 no-hit rows per year after sorting."},
		{"metric": "supply_tool_policy_records", "value": int(row_features["has_supply_tool"].sum()), "note": "Rows with supply-side dictionary hit."},
		{"metric": "demand_tool_policy_records", "value": int(row_features["has_demand_tool"].sum()), "note": "Rows with demand-side dictionary hit."},
		{"metric": "environment_tool_policy_records", "value": int(row_features["has_environment_tool"].sum()), "note": "Rows with environment-side dictionary hit."},
		{"metric": "central_policy_records", "value": int((row_features["jurisdiction_type"] == "central").sum()), "note": "Central rows in row-level text features."},
		{"metric": "local_policy_records", "value": int((row_features["jurisdiction_type"] == "local").sum()), "note": "Local rows in row-level text features."},
		{"metric": "dictionary_terms", "value": len(dictionary_table), "note": "Total v0 dictionary terms across all categories."},
		{"metric": "zero_coverage_terms", "value": int((keyword_quality_table["records_hit"] == 0).sum()), "note": "Dictionary terms with no title/abstract hit."},
		{"metric": "low_coverage_terms_lte_5_records", "value": int((keyword_quality_table["records_hit"] <= LOW_COVERAGE_TERM_THRESHOLD).sum()), "note": "Terms with at most 5 matching records."},
		{"metric": "high_coverage_terms_gte_25pct_records", "value": int((keyword_quality_table["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD).sum()), "note": "Terms matching at least 25% of records; review for broad meaning."},
		{"metric": "terms_with_review_flags", "value": int(keyword_quality_table["needs_review"].sum()), "note": "Terms flagged for low/high coverage, short length, or broad meaning."},
		{"metric": "province_units", "value": province_year_features["province"].nunique(), "note": "Local province units in aggregate features."},
		{"metric": "year_min", "value": int(province_year_features["publish_year"].min()), "note": "Minimum year in aggregate features."},
		{"metric": "year_max", "value": int(province_year_features["publish_year"].max()), "note": "Maximum year in aggregate features."},
	],
)

ROW_FEATURES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
PROVINCE_YEAR_FEATURES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
QUALITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DICTIONARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DICTIONARY_COVERAGE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DICTIONARY_REVISION_EFFECT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
KEYWORD_QUALITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NO_TOOL_HIT_RECORDS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NO_TOOL_HIT_SAMPLE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NO_TOOL_HIT_SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

row_features.to_csv(ROW_FEATURES_OUTPUT, index=False)
province_year_features.to_csv(PROVINCE_YEAR_FEATURES_OUTPUT, index=False)
quality_report.to_csv(QUALITY_OUTPUT, index=False)
dictionary_table[["category", "term"]].to_csv(DICTIONARY_OUTPUT, index=False)
dictionary_table.to_csv(DICTIONARY_COVERAGE_OUTPUT, index=False)
dictionary_revision_effect.to_csv(DICTIONARY_REVISION_EFFECT_OUTPUT, index=False)
keyword_quality_table.to_csv(KEYWORD_QUALITY_OUTPUT, index=False)
no_tool_hit_records.to_csv(NO_TOOL_HIT_RECORDS_OUTPUT, index=False)
no_tool_hit_sample.to_csv(NO_TOOL_HIT_SAMPLE_OUTPUT, index=False)
no_tool_hit_summary.to_csv(NO_TOOL_HIT_SUMMARY_OUTPUT, index=False)

quality_report

# %% [markdown]
# ## 6. Dictionary and No-Hit Review
#
# The following outputs support manual review of the v0 dictionary:
#
# - `manual_policy_srdi_tool_dictionary_coverage_v0.csv`: term-level hit
#   counts;
# - `manual_policy_srdi_dictionary_revision_effect_v0.csv`: before/after
#   effect of the manual no-hit review revision;
# - `manual_policy_srdi_keyword_quality_check_v0.csv`: term-level quality flags
#   for low/high coverage, short terms, and broad-meaning terms;
# - `manual_policy_srdi_no_tool_hit_records_v0.csv`: all remaining no-hit
#   records after the reviewed dictionary revision;
# - `manual_policy_srdi_no_tool_hit_review_sample_v0.csv`: deterministic
#   review rows, 5 per year;
# - `manual_policy_srdi_no_tool_hit_summary_v0.csv`: no-hit counts by year and
#   province.

# %%
dictionary_table.sort_values(["category", "records_hit", "term"], ascending=[True, False, True])

# %%
dictionary_revision_effect

# %%
keyword_quality_table.sort_values(["needs_review", "records_hit"], ascending=[False, False])

# %%
no_tool_hit_summary.head(20)

# %%
no_tool_hit_sample[["province", "publish_year", "title", "abstract", "source_url"]]

# %% [markdown]
# ## 7. Interpretation Notes
#
# - The v0 dictionary features are suitable for descriptive analysis and as
#   candidate covariates, not as final causal interpretation by themselves.
# - The reviewed dictionary revision reduced no-hit records from 352 to 271,
#   added terms grounded in a 30-record manual sample, and kept zero-coverage
#   terms at 0.
# - Terms with `review_flags` in
#   `manual_policy_srdi_keyword_quality_check_v0.csv` should be described as
#   broad dictionary indicators rather than precise human labels.
# - `province_year_srdi_text_features_v0.csv` keeps all policy-count intensity
#   columns, so DID-side code can choose count-only or text-augmented measures.
# - Rows with no dictionary hit are not errors; they often mention SRDI policy
#   context without using the first-pass instrument terms.
# - The next review step should inspect high-count provinces and a sample of
#   no-hit rows before treating the tool categories as paper-facing labels.
