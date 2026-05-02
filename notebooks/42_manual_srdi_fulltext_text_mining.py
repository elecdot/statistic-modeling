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
# # Manual SRDI Full-Text Mining v1
#
# This notebook adds the full-text version of the manual SRDI policy-mining
# workflow. It intentionally does not overwrite the v0 title/abstract outputs.
#
# Scope:
#
# - source table: `data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv`;
# - text surface: title + full text;
# - method: the same transparent supply/demand/environment substring dictionary
#   used in v0;
# - outputs: row-level full-text features and province-year aggregate full-text
#   features.
#
# Interpretation:
#
# - v0 remains the title/abstract baseline;
# - v1 is the candidate paper-facing full-text measure;
# - dictionary hits are transparent text features, not final manual labels.

# %%
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
POLICY_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv"
INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v0.csv"
ROW_FEATURES_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv"
PROVINCE_YEAR_FEATURES_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv"
QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv"
DICTIONARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_fulltext_v1.csv"
DICTIONARY_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv"
KEYWORD_QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_keyword_quality_check_fulltext_v1.csv"
NO_TOOL_HIT_RECORDS_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_fulltext_v1.csv"
NO_TOOL_HIT_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_summary_fulltext_v1.csv"

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

# The v1 full-text run deliberately reuses the reviewed v0 dictionary so any
# difference comes from the text surface, not from changing the codebook.
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
# ## 1. Load Full-Text Records
#
# The processed full-text table keeps the same 2020-2025 scope and province
# normalization as v0. The province-year intensity base is reused from v0
# because the policy universe is the same; this notebook only changes text
# measurement.

# %%
records = pd.read_csv(POLICY_RECORDS_PATH)
intensity = pd.read_csv(INTENSITY_PATH)

records["text_surface"] = records[["title", "full_text"]].fillna("").agg("。".join, axis=1)
records["title_len"] = records["title"].fillna("").str.len()
records["full_text_len"] = records["full_text"].fillna("").str.len()
records["text_surface_len"] = records["text_surface"].str.len()

load_overview = pd.DataFrame(
	[
		{"metric": "policy_records", "value": len(records), "note": "Processed manual SRDI full-text records."},
		{"metric": "unique_source_urls", "value": records["source_url"].nunique(), "note": "Should match policy_records."},
		{"metric": "province_units_in_records", "value": records["province"].nunique(), "note": "Includes central."},
		{"metric": "local_intensity_rows", "value": len(intensity), "note": "31 province units x 6 years."},
		{"metric": "min_publish_year", "value": records["publish_year"].min(), "note": "Analysis window lower bound."},
		{"metric": "max_publish_year", "value": records["publish_year"].max(), "note": "Analysis window upper bound."},
		{"metric": "median_full_text_len", "value": records["full_text_len"].median(), "note": "Full text length diagnostic."},
	],
)
load_overview

# %% [markdown]
# ## 2. Full-Text Dictionary Features
#
# The feature builder is intentionally identical to v0 except for the text
# surface. Counting uses literal substring matches to keep the method auditable.

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
	"full_text_len",
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
# ## 3. Province-Year Full-Text Features
#
# The aggregate table keeps the same 31 x 6 local province-year frame as v0 and
# adds full-text dictionary counts and shares. Central records remain available
# in the row-level table but are excluded from the DID-facing province-year
# aggregate.

# %%
local_features = row_features.loc[row_features["jurisdiction_type"] == "local"].copy()
province_year_features = (
	local_features.groupby(["province", "publish_year"], dropna=False)
	.agg(
		text_feature_policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
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
province_year_features["avg_full_text_len"] = province_year_features["avg_full_text_len"].fillna(0.0)
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
province_year_features["any_tool_policy_share"] = (
	province_year_features["any_tool_policy_count"] / province_year_features["srdi_policy_count"].where(province_year_features["srdi_policy_count"] > 0)
).fillna(0.0)
province_year_features.head()

# %% [markdown]
# ## 4. Quality and Review Artifacts
#
# Full text should reduce no-hit records, but it can also increase broad-term
# hits. These outputs make that tradeoff inspectable before v1 is promoted to a
# paper-facing measure.

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
		full_text_excerpt=lambda frame: frame["full_text"].fillna("").str.slice(0, 800),
		review_status="needs_dictionary_review",
		review_reason="no_fulltext_v1_policy_tool_dictionary_hit",
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

quality_report = pd.DataFrame(
	[
		{"metric": "row_feature_records", "value": len(row_features), "note": "Rows in row-level full-text feature table."},
		{"metric": "province_year_feature_records", "value": len(province_year_features), "note": "Rows in province-year full-text feature table."},
		{"metric": "policy_records_with_any_tool_hit", "value": int(row_features["has_any_policy_tool"].sum()), "note": "Rows hitting at least one policy-tool dictionary category."},
		{"metric": "policy_records_without_tool_hit", "value": int((~row_features["has_any_policy_tool"]).sum()), "note": "Rows with no full-text v1 policy-tool dictionary hit."},
		{"metric": "supply_tool_policy_records", "value": int(row_features["has_supply_tool"].sum()), "note": "Rows with supply-side dictionary hit."},
		{"metric": "demand_tool_policy_records", "value": int(row_features["has_demand_tool"].sum()), "note": "Rows with demand-side dictionary hit."},
		{"metric": "environment_tool_policy_records", "value": int(row_features["has_environment_tool"].sum()), "note": "Rows with environment-side dictionary hit."},
		{"metric": "central_policy_records", "value": int((row_features["jurisdiction_type"] == "central").sum()), "note": "Central rows in row-level full-text features."},
		{"metric": "local_policy_records", "value": int((row_features["jurisdiction_type"] == "local").sum()), "note": "Local rows in row-level full-text features."},
		{"metric": "dictionary_terms", "value": len(dictionary_table), "note": "Total dictionary terms across all categories; same codebook as v0."},
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

ROW_FEATURES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
PROVINCE_YEAR_FEATURES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
QUALITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DICTIONARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
DICTIONARY_COVERAGE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
KEYWORD_QUALITY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NO_TOOL_HIT_RECORDS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
NO_TOOL_HIT_SUMMARY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

row_features.to_csv(ROW_FEATURES_OUTPUT, index=False)
province_year_features.to_csv(PROVINCE_YEAR_FEATURES_OUTPUT, index=False)
quality_report.to_csv(QUALITY_OUTPUT, index=False)
dictionary_table[["category", "term"]].to_csv(DICTIONARY_OUTPUT, index=False)
dictionary_table.to_csv(DICTIONARY_COVERAGE_OUTPUT, index=False)
keyword_quality_table.to_csv(KEYWORD_QUALITY_OUTPUT, index=False)
no_tool_hit_records.to_csv(NO_TOOL_HIT_RECORDS_OUTPUT, index=False)
no_tool_hit_summary.to_csv(NO_TOOL_HIT_SUMMARY_OUTPUT, index=False)

quality_report

# %% [markdown]
# ## 5. Interpretation Notes
#
# - Full-text v1 uses the same dictionary as v0, so coverage changes are caused
#   by the larger text surface.
# - Full-text hits are stronger evidence than title/abstract hits, but broad
#   terms such as `创新`, `服务`, `标准`, or `认定` still need cautious
#   interpretation.
# - Remaining no-hit rows are review targets, not processing failures.
# - The DID handoff should decide whether to use count variables, share
#   variables, or both, and should avoid treating dictionary shares as causal
#   mechanisms before model-side checks.

# %%
dictionary_table.sort_values(["category", "records_hit", "term"], ascending=[True, False, True])

# %%
keyword_quality_table.sort_values(["needs_review", "records_hit"], ascending=[False, False])

# %%
no_tool_hit_summary.head(20)

# %%
