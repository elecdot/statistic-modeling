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
# # Manual SRDI Full-Text Mining v2
#
# This notebook builds the transparent full-text dictionary features for the
# rebuilt 2019-2024 v2 policy corpus.
#
# Scope:
#
# - source table: `data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv`;
# - base province-year count frame: `data/processed/province_year_srdi_policy_intensity_v2.csv`;
# - text surface: title + full text;
# - method: reuse the reviewed full-text v1 supply/demand/environment dictionary;
# - outputs: row-level v2 full-text features, province-year v2 aggregate
#   full-text features, dictionary coverage, keyword-quality checks, no-hit
#   review tables, and QA.
#
# This step does not run MacBERT, variable selection, final DID panel
# construction, enterprise-panel merging, or DID estimation.

# %%
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
POLICY_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v2.csv"
INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v2.csv"
FROZEN_DICTIONARY_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_fulltext_v1.csv"

ROW_FEATURES_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v2.csv"
PROVINCE_YEAR_FEATURES_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v2.csv"
QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_text_mining_fulltext_v2_quality_report.csv"
DICTIONARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_fulltext_v2.csv"
DICTIONARY_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v2.csv"
KEYWORD_QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_keyword_quality_check_fulltext_v2.csv"
NO_TOOL_HIT_RECORDS_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_fulltext_v2.csv"
NO_TOOL_HIT_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_summary_fulltext_v2.csv"

SRDI_KEYWORDS = {
	"srdi": "专精特新",
	"little_giant": "小巨人",
	"sme": "中小企业",
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
EXPECTED_YEARS = set(range(2019, 2025))
EXPECTED_LOCAL_PROVINCES = 31
EXPECTED_PROVINCE_YEAR_ROWS = 186

# %% [markdown]
# ## 1. Load v2 Corpus and Frozen Dictionary
#
# The v2 text-mining path reuses the reviewed full-text v1 dictionary. This
# keeps the codebook stable while changing only the policy window and corpus.

# %%
records = pd.read_csv(POLICY_RECORDS_PATH)
intensity = pd.read_csv(INTENSITY_PATH)
frozen_dictionary = pd.read_csv(FROZEN_DICTIONARY_PATH)

if set(records["publish_year"].unique()) != EXPECTED_YEARS:
	raise ValueError(f"unexpected v2 record years: {sorted(records['publish_year'].unique())}")
if len(intensity) != EXPECTED_PROVINCE_YEAR_ROWS:
	raise ValueError(f"unexpected v2 province-year rows: {len(intensity)}")
if intensity["province"].nunique() != EXPECTED_LOCAL_PROVINCES:
	raise ValueError(f"unexpected v2 local province count: {intensity['province'].nunique()}")
if "central" in set(intensity["province"]):
	raise ValueError("v2 province-year text features must exclude central")
if records["policy_id"].duplicated().any():
	raise ValueError("v2 policy records contain duplicate policy_id values")
if records["source_url"].duplicated().any():
	raise ValueError("v2 policy records contain duplicate source_url values")

dictionary_categories = ["supply", "demand", "environment"]
if set(frozen_dictionary["category"]) != set(dictionary_categories):
	raise ValueError("frozen full-text dictionary must contain supply, demand, and environment categories")
policy_tool_dictionary = {
	category: frozen_dictionary.loc[frozen_dictionary["category"].eq(category), "term"].dropna().astype(str).tolist()
	for category in dictionary_categories
}

records["text_surface"] = records[["title", "full_text"]].fillna("").agg("。".join, axis=1)
records["title_len"] = records["title"].fillna("").str.len()
records["full_text_len"] = records["full_text"].fillna("").str.len()
records["text_surface_len"] = records["text_surface"].str.len()

load_overview = pd.DataFrame(
	[
		{"metric": "policy_records", "value": len(records), "note": "Processed manual SRDI full-text v2 records."},
		{"metric": "unique_source_urls", "value": records["source_url"].nunique(), "note": "Should match policy_records."},
		{"metric": "province_units_in_records", "value": records["province"].nunique(), "note": "Includes central."},
		{"metric": "local_intensity_rows", "value": len(intensity), "note": "31 province units x 6 years."},
		{"metric": "min_publish_year", "value": records["publish_year"].min(), "note": "Analysis window lower bound."},
		{"metric": "max_publish_year", "value": records["publish_year"].max(), "note": "Analysis window upper bound."},
		{"metric": "dictionary_terms", "value": len(frozen_dictionary), "note": "Frozen full-text v1 dictionary terms reused in v2."},
		{"metric": "missing_full_text", "value": int(records["full_text_missing"].sum()), "note": "Rows retained with empty full text."},
	],
)
load_overview

# %% [markdown]
# ## 2. Dictionary Feature Construction
#
# Counting uses literal substring matches. The method remains transparent and
# auditable, and it is intentionally not a row-level manual policy-tool label.

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

for category, keywords in policy_tool_dictionary.items():
	feature_rows[f"{category}_tool_hit_count"] = feature_rows["text_surface"].map(lambda text, kws=keywords: count_keyword_hits(text, kws))
	feature_rows[f"has_{category}_tool"] = feature_rows[f"{category}_tool_hit_count"] > 0
	feature_rows[f"{category}_matched_terms"] = feature_rows["text_surface"].map(lambda text, kws=keywords: matched_keywords(text, kws))

tool_indicator_columns = [f"has_{category}_tool" for category in policy_tool_dictionary]
feature_rows["policy_tool_category_count"] = feature_rows[tool_indicator_columns].sum(axis=1)
feature_rows["has_any_policy_tool"] = feature_rows["policy_tool_category_count"] > 0
feature_rows["policy_tool_mix"] = feature_rows.apply(
	lambda row: ";".join(category for category in policy_tool_dictionary if row[f"has_{category}_tool"]),
	axis=1,
)

row_feature_columns = [
	"policy_id",
	"province",
	"province_before_correction",
	"province_correction_status",
	"province_correction_reason",
	"province_correction_evidence",
	"source_label_original",
	"jurisdiction_type",
	"region_name",
	"publish_date",
	"publish_year",
	"keyword_count",
	"keyword_count_source",
	"source_workbook",
	"source_schema_version",
	"full_text_missing",
	"full_text_fallback_for_model",
	"needs_jurisdiction_review",
	"title",
	"document_number",
	"agency",
	"source_url",
	"title_len",
	"full_text_len",
	"text_surface_len",
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
# ## 3. Province-Year v2 Aggregation
#
# Central records remain in the row-level features for audit, but province-year
# aggregates use only local records and merge back onto the balanced v2
# policy-count frame.

# %%
local_features = row_features.loc[row_features["jurisdiction_type"] == "local"].copy()
province_year_features = (
	local_features.groupby(["province", "publish_year"], dropna=False)
	.agg(
		text_feature_policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
		full_text_missing_policy_count=("full_text_missing", "sum"),
		full_text_fallback_policy_count=("full_text_fallback_for_model", "sum"),
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
	"full_text_missing_policy_count",
	"full_text_fallback_policy_count",
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
province_year_features["avg_full_text_len"] = province_year_features["avg_full_text_len"].fillna(0.0)
province_year_features["avg_tool_category_count"] = province_year_features["avg_tool_category_count"].fillna(0.0)
for category in dictionary_categories:
	province_year_features[f"{category}_tool_policy_share"] = (
		province_year_features[f"{category}_tool_policy_count"]
		/ province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
	).fillna(0.0)
province_year_features["any_tool_policy_share"] = (
	province_year_features["any_tool_policy_count"]
	/ province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
).fillna(0.0)
province_year_features.head()

# %% [markdown]
# ## 4. QA and Review Artifacts
#
# The no-hit and keyword-quality outputs preserve the same review surfaces as
# v1, with v2 provenance fields added where useful.

# %%
dictionary_rows = [
	{
		"category": category,
		"term": term,
		"records_hit": int(feature_rows["text_surface"].map(lambda text, t=term: t in text).sum()),
		"total_hits": int(feature_rows["text_surface"].map(lambda text, t=term: count_keyword_hits(text, [t])).sum()),
	}
	for category, terms in policy_tool_dictionary.items()
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
		full_text_excerpt=lambda frame: frame["full_text"].fillna("").str.slice(0, 800),
		review_status="needs_dictionary_review",
		review_reason="no_fulltext_v2_policy_tool_dictionary_hit",
	)
	[
		[
			"policy_id",
			"province",
			"source_label_original",
			"jurisdiction_type",
			"publish_date",
			"publish_year",
			"source_workbook",
			"source_schema_version",
			"full_text_missing",
			"title",
			"agency",
			"source_url",
			"full_text_excerpt",
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

no_tool_hit_year_summary = no_tool_hit_records.groupby("publish_year").size().reset_index(name="no_tool_hit_records")
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

quality_report = pd.DataFrame(
	[
		{"metric": "row_feature_records", "value": len(row_features), "note": "Rows in row-level full-text v2 feature table."},
		{"metric": "province_year_feature_records", "value": len(province_year_features), "note": "Rows in province-year full-text v2 feature table."},
		{"metric": "policy_records_with_any_tool_hit", "value": int(row_features["has_any_policy_tool"].sum()), "note": "Rows hitting at least one policy-tool dictionary category."},
		{"metric": "policy_records_without_tool_hit", "value": int((~row_features["has_any_policy_tool"]).sum()), "note": "Rows with no full-text v2 policy-tool dictionary hit."},
		{"metric": "supply_tool_policy_records", "value": int(row_features["has_supply_tool"].sum()), "note": "Rows with supply-side dictionary hit."},
		{"metric": "demand_tool_policy_records", "value": int(row_features["has_demand_tool"].sum()), "note": "Rows with demand-side dictionary hit."},
		{"metric": "environment_tool_policy_records", "value": int(row_features["has_environment_tool"].sum()), "note": "Rows with environment-side dictionary hit."},
		{"metric": "central_policy_records", "value": int((row_features["jurisdiction_type"] == "central").sum()), "note": "Central rows in row-level full-text v2 features."},
		{"metric": "local_policy_records", "value": int((row_features["jurisdiction_type"] == "local").sum()), "note": "Local rows in row-level full-text v2 features."},
		{"metric": "source_current_fulltext_records", "value": int(row_features["source_schema_version"].eq("current_fulltext_workbook_v1").sum()), "note": "Rows from current full-text workbook."},
		{"metric": "source_2019_supplement_records", "value": int(row_features["source_schema_version"].eq("supplement_2019_fulltext_v1").sum()), "note": "Rows from 2019 supplementary workbook."},
		{"metric": "full_text_missing_records", "value": int(row_features["full_text_missing"].sum()), "note": "Rows with empty full text retained in v2."},
		{"metric": "full_text_fallback_for_model_records", "value": int(row_features["full_text_fallback_for_model"].sum()), "note": "Rows marked for later model-input fallback construction."},
		{"metric": "jurisdiction_review_candidate_records", "value": int(row_features["needs_jurisdiction_review"].sum()), "note": "Unresolved v2 jurisdiction review rows entering text mining."},
		{"metric": "dictionary_terms", "value": len(dictionary_table), "note": "Total dictionary terms across all categories; frozen full-text v1 codebook."},
		{"metric": "zero_coverage_terms", "value": int((keyword_quality_table["records_hit"] == 0).sum()), "note": "Dictionary terms with no title/full-text hit."},
		{"metric": "low_coverage_terms_lte_5_records", "value": int((keyword_quality_table["records_hit"] <= LOW_COVERAGE_TERM_THRESHOLD).sum()), "note": "Terms with at most 5 matching records."},
		{"metric": "high_coverage_terms_gte_25pct_records", "value": int((keyword_quality_table["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD).sum()), "note": "Terms matching at least 25% of records; review for broad meaning."},
		{"metric": "terms_with_review_flags", "value": int(keyword_quality_table["needs_review"].sum()), "note": "Terms flagged for low/high coverage, short length, or broad meaning."},
		{"metric": "province_units", "value": province_year_features["province"].nunique(), "note": "Local province units in aggregate features."},
		{"metric": "year_min", "value": int(province_year_features["publish_year"].min()), "note": "Minimum year in aggregate features."},
		{"metric": "year_max", "value": int(province_year_features["publish_year"].max()), "note": "Maximum year in aggregate features."},
		{"metric": "median_full_text_len", "value": float(row_features["full_text_len"].median()), "note": "Median full-text character length."},
		{"metric": "max_full_text_len", "value": int(row_features["full_text_len"].max()), "note": "Maximum full-text character length."},
	],
)

for path in [
	ROW_FEATURES_OUTPUT,
	PROVINCE_YEAR_FEATURES_OUTPUT,
	QUALITY_OUTPUT,
	DICTIONARY_OUTPUT,
	DICTIONARY_COVERAGE_OUTPUT,
	KEYWORD_QUALITY_OUTPUT,
	NO_TOOL_HIT_RECORDS_OUTPUT,
	NO_TOOL_HIT_SUMMARY_OUTPUT,
]:
	path.parent.mkdir(parents=True, exist_ok=True)

row_features.to_csv(ROW_FEATURES_OUTPUT, index=False)
province_year_features.to_csv(PROVINCE_YEAR_FEATURES_OUTPUT, index=False)
quality_report.to_csv(QUALITY_OUTPUT, index=False)
frozen_dictionary[["category", "term"]].to_csv(DICTIONARY_OUTPUT, index=False)
dictionary_table.to_csv(DICTIONARY_COVERAGE_OUTPUT, index=False)
keyword_quality_table.to_csv(KEYWORD_QUALITY_OUTPUT, index=False)
no_tool_hit_records.to_csv(NO_TOOL_HIT_RECORDS_OUTPUT, index=False)
no_tool_hit_summary.to_csv(NO_TOOL_HIT_SUMMARY_OUTPUT, index=False)

quality_report

# %% [markdown]
# ## 5. Interpretation Notes
#
# - v2 reuses the reviewed v1 dictionary so coverage changes are attributable to
#   the 2019-2024 corpus, not codebook drift.
# - The row with empty full text remains in the row-level feature table. Its
#   dictionary signal comes from the title surface only.
# - Dictionary features are broad text-intensity proxies and should not be
#   interpreted as final manual labels.
# - This notebook stops at policy-side dictionary features; MacBERT, variable
#   selection, and final DID panel construction remain separate v2 tasks.

# %%
dictionary_table.sort_values(["category", "records_hit", "term"], ascending=[True, False, True])

# %%
keyword_quality_table.sort_values(["needs_review", "records_hit"], ascending=[False, False])

# %%
no_tool_hit_summary.head(20)

# %%
