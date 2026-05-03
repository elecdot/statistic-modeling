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
# # Manual SRDI Full-Text Descriptive and Keyword Quality v2
#
# This notebook produces paper-facing descriptive and quality-analysis artifacts
# for the rebuilt 2019-2024 v2 full-text policy corpus.
#
# Scope:
#
# - policy universe: manual SRDI full-text v2 records, 2019-2024;
# - text measure: transparent full-text dictionary features from
#   `notebooks/42b_manual_srdi_fulltext_text_mining_v2.py`;
# - quality checks: source-window composition, 2019 supplement contribution,
#   empty full-text handling, no-hit rows, category overlap, term coverage, and
#   v1/v2 dictionary-coverage deltas;
# - stop point: no MacBERT prediction, variable selection, final DID panel, or
#   enterprise-panel merge.

# %%
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# %matplotlib inline

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

POLICY_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v2.csv"
INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v2.csv"
TEXT_FEATURES_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v2.csv"
PROVINCE_YEAR_TEXT_FEATURES_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v2.csv"
DICTIONARY_COVERAGE_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v2.csv"
DICTIONARY_COVERAGE_V1_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv"
NO_HIT_RECORDS_PATH = ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_fulltext_v2.csv"

YEAR_TREND_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_year_trend_v2.csv"
PROVINCE_DISTRIBUTION_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_province_distribution_v2.csv"
TOOL_CATEGORY_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_category_summary_v2.csv"
TOOL_SHARES_BY_YEAR_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_shares_by_year_v2.csv"
HEATMAP_MATRIX_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_policy_intensity_heatmap_matrix_v2.csv"
TOOL_SHARE_BY_PROVINCE_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_share_by_province_v2.csv"
CENTRAL_LOCAL_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_central_local_comparison_v2.csv"
NO_HIT_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_no_hit_summary_v2.csv"
SOURCE_SCHEMA_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_source_schema_summary_v2.csv"
MISSING_FULL_TEXT_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_missing_full_text_records_v2.csv"
HIGH_COVERAGE_TERMS_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_high_coverage_terms_v2.csv"

KEYWORD_QUALITY_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_summary_v2.csv"
TERM_FLAGS_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_term_flags_v2.csv"
CATEGORY_OVERLAP_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_category_overlap_v2.csv"
CATEGORY_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_category_comparison_v2.csv"
INTERPRETATION_NOTES_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_interpretation_notes_v2.csv"

YEAR_TREND_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_year_trend_v2.png"
PROVINCE_DISTRIBUTION_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_province_distribution_v2.png"
TOOL_SHARES_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_tool_shares_by_year_v2.png"
POLICY_INTENSITY_HEATMAP_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_policy_intensity_heatmap_v2.png"
TOOL_SHARE_BY_PROVINCE_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_tool_share_by_province_v2.png"
CENTRAL_LOCAL_COMPARISON_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_central_local_comparison_v2.png"
NO_HIT_SHARE_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_no_hit_share_by_year_v2.png"
KEYWORD_COVERAGE_BAND_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_coverage_bands_v2.png"
KEYWORD_CATEGORY_SHARE_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_category_shares_v2.png"
KEYWORD_OVERLAP_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_overlap_v2.png"

YEARS = list(range(2019, 2025))
TOOL_CATEGORIES = ["supply", "demand", "environment"]
SATURATED_THRESHOLD = 0.80
HIGH_THRESHOLD = 0.50
MODERATE_THRESHOLD = 0.25
LOW_THRESHOLD = 0.05
FIG_DPI = 300

PROVINCE_EN = {
	"上海市": "Shanghai",
	"云南省": "Yunnan",
	"内蒙古自治区": "Inner Mongolia",
	"北京市": "Beijing",
	"吉林省": "Jilin",
	"四川省": "Sichuan",
	"天津市": "Tianjin",
	"宁夏回族自治区": "Ningxia",
	"安徽省": "Anhui",
	"山东省": "Shandong",
	"山西省": "Shanxi",
	"广东省": "Guangdong",
	"广西壮族自治区": "Guangxi",
	"新疆": "Xinjiang",
	"江苏省": "Jiangsu",
	"江西省": "Jiangxi",
	"河北省": "Hebei",
	"河南省": "Henan",
	"浙江省": "Zhejiang",
	"海南省": "Hainan",
	"湖北省": "Hubei",
	"湖南省": "Hunan",
	"甘肃省": "Gansu",
	"福建省": "Fujian",
	"西藏自治区": "Tibet",
	"贵州省": "Guizhou",
	"辽宁省": "Liaoning",
	"重庆市": "Chongqing",
	"陕西省": "Shaanxi",
	"青海省": "Qinghai",
	"黑龙江省": "Heilongjiang",
}

BROAD_MEANING_TERMS = {
	"财政",
	"研发",
	"创新",
	"人才",
	"培训",
	"服务平台",
	"公共服务",
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
	"数字化",
	"融资",
	"贷款",
}


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save a Matplotlib figure with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


def bool_series(series: pd.Series) -> pd.Series:
	"""Read bool-like CSV columns robustly."""
	if series.dtype == bool:
		return series
	return series.astype(str).str.lower().isin({"true", "1", "yes"})


def add_value_labels(ax: plt.Axes, fmt: str = "{:.0f}") -> None:
	"""Add compact labels above vertical bars."""
	for patch in ax.patches:
		height = patch.get_height()
		ax.annotate(
			fmt.format(height),
			(patch.get_x() + patch.get_width() / 2, height),
			ha="center",
			va="bottom",
			fontsize=8,
			xytext=(0, 2),
			textcoords="offset points",
		)


def coverage_band(share: float) -> str:
	"""Assign a coverage band used for interpretation diagnostics."""
	if share >= SATURATED_THRESHOLD:
		return "saturated_gte_80pct"
	if share >= HIGH_THRESHOLD:
		return "high_50_80pct"
	if share >= MODERATE_THRESHOLD:
		return "moderate_25_50pct"
	if share >= LOW_THRESHOLD:
		return "low_5_25pct"
	return "rare_lt_5pct"


# %% [markdown]
# ## 1. Load Inputs and Structural Checks

# %%
records = pd.read_csv(POLICY_RECORDS_PATH)
intensity = pd.read_csv(INTENSITY_PATH)
text_features = pd.read_csv(TEXT_FEATURES_PATH)
province_year_text_features = pd.read_csv(PROVINCE_YEAR_TEXT_FEATURES_PATH)
dictionary_coverage = pd.read_csv(DICTIONARY_COVERAGE_PATH)
dictionary_coverage_v1 = pd.read_csv(DICTIONARY_COVERAGE_V1_PATH)
no_hit_records = pd.read_csv(NO_HIT_RECORDS_PATH)

for frame in [records, text_features]:
	for column in ["full_text_missing", "full_text_fallback_for_model", "needs_jurisdiction_review"]:
		if column in frame:
			frame[column] = bool_series(frame[column])
for column in ["has_supply_tool", "has_demand_tool", "has_environment_tool", "has_any_policy_tool"]:
	text_features[column] = bool_series(text_features[column])

if sorted(records["publish_year"].unique()) != YEARS:
	raise ValueError(f"unexpected v2 record years: {sorted(records['publish_year'].unique())}")
if len(province_year_text_features) != 186:
	raise ValueError(f"unexpected province-year feature rows: {len(province_year_text_features)}")
if province_year_text_features["province"].nunique() != 31:
	raise ValueError("v2 province-year features must contain 31 local province units")
if "central" in set(province_year_text_features["province"]):
	raise ValueError("v2 province-year features must exclude central")

load_checks = pd.DataFrame(
	[
		{"artifact": "fulltext_policy_records_v2", "rows": len(records), "columns": records.shape[1]},
		{"artifact": "province_year_intensity_v2", "rows": len(intensity), "columns": intensity.shape[1]},
		{"artifact": "fulltext_text_features_v2", "rows": len(text_features), "columns": text_features.shape[1]},
		{"artifact": "province_year_fulltext_features_v2", "rows": len(province_year_text_features), "columns": province_year_text_features.shape[1]},
		{"artifact": "fulltext_dictionary_coverage_v2", "rows": len(dictionary_coverage), "columns": dictionary_coverage.shape[1]},
		{"artifact": "fulltext_no_hit_records_v2", "rows": len(no_hit_records), "columns": no_hit_records.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Annual Policy Trend and Source Composition

# %%
year_trend = (
	records.groupby(["publish_year", "jurisdiction_type"])
	.size()
	.unstack(fill_value=0)
	.reindex(YEARS, fill_value=0)
	.rename_axis("publish_year")
	.reset_index()
)
for column in ["central", "local"]:
	if column not in year_trend:
		year_trend[column] = 0
year_trend["total_policy_count"] = year_trend["central"] + year_trend["local"]
year_trend = year_trend[["publish_year", "total_policy_count", "central", "local"]]
year_trend.to_csv(YEAR_TREND_OUTPUT, index=False)
year_trend

# %%
source_schema_summary = (
	text_features.groupby("source_schema_version")
	.agg(
		policy_records=("policy_id", "size"),
		central_records=("jurisdiction_type", lambda values: int(values.eq("central").sum())),
		local_records=("jurisdiction_type", lambda values: int(values.eq("local").sum())),
		year_min=("publish_year", "min"),
		year_max=("publish_year", "max"),
		avg_full_text_len=("full_text_len", "mean"),
		full_text_missing_records=("full_text_missing", "sum"),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
		no_tool_policy_count=("has_any_policy_tool", lambda values: int((~values).sum())),
	)
	.reset_index()
)
source_schema_summary["any_tool_policy_share"] = source_schema_summary["any_tool_policy_count"] / source_schema_summary["policy_records"]
source_schema_summary.to_csv(SOURCE_SCHEMA_SUMMARY_OUTPUT, index=False)
source_schema_summary

# %%
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(year_trend["publish_year"], year_trend["total_policy_count"], marker="o", linewidth=2, label="Total")
ax.plot(year_trend["publish_year"], year_trend["local"], marker="o", linewidth=2, label="Local")
ax.plot(year_trend["publish_year"], year_trend["central"], marker="o", linewidth=2, label="Central")
ax.set_title("Annual SRDI Policy Records, 2019-2024")
ax.set_xlabel("Year")
ax.set_ylabel("Policy records")
ax.set_xticks(YEARS)
ax.grid(axis="y", alpha=0.3)
ax.legend()
save_figure(fig, YEAR_TREND_FIG)
fig

# %% [markdown]
# ## 3. Province Distribution and Province-Year Count Surface

# %%
province_distribution = (
	records.loc[records["jurisdiction_type"] == "local"]
	.groupby("province")
	.agg(
		policy_count=("policy_id", "size"),
		total_keyword_count=("keyword_count", "sum"),
		avg_keyword_count=("keyword_count", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
		full_text_missing_records=("full_text_missing", "sum"),
		first_year=("publish_year", "min"),
		last_year=("publish_year", "max"),
	)
	.reset_index()
)
province_distribution["province_en"] = province_distribution["province"].map(PROVINCE_EN)
province_distribution["policy_count_share"] = province_distribution["policy_count"] / province_distribution["policy_count"].sum()
province_distribution = province_distribution.sort_values(["policy_count", "province"], ascending=[False, True], ignore_index=True)
province_distribution["rank"] = province_distribution.index + 1
province_distribution.to_csv(PROVINCE_DISTRIBUTION_OUTPUT, index=False)
province_distribution.head(10)

# %%
plot_distribution = province_distribution.sort_values("policy_count", ascending=True)
fig, ax = plt.subplots(figsize=(9, 8))
ax.barh(plot_distribution["province_en"], plot_distribution["policy_count"], color="#4777b2")
ax.set_title("Local SRDI Policy Records by Province, 2019-2024")
ax.set_xlabel("Policy records")
ax.set_ylabel("Province")
ax.grid(axis="x", alpha=0.25)
save_figure(fig, PROVINCE_DISTRIBUTION_FIG)
fig

# %%
heatmap_matrix = (
	intensity.pivot(index="province", columns="publish_year", values="srdi_policy_count")
	.reindex(province_distribution.sort_values("policy_count", ascending=False)["province"])
	.reindex(columns=YEARS)
)
heatmap_matrix.to_csv(HEATMAP_MATRIX_OUTPUT)
heatmap_matrix.shape

# %%
heatmap_labels = [PROVINCE_EN.get(province, province) for province in heatmap_matrix.index]
fig, ax = plt.subplots(figsize=(8, 10))
image = ax.imshow(heatmap_matrix.to_numpy(), aspect="auto", cmap="Blues")
ax.set_title("Province-Year SRDI Policy Count, 2019-2024")
ax.set_xlabel("Year")
ax.set_ylabel("Province")
ax.set_xticks(np.arange(len(YEARS)))
ax.set_xticklabels(YEARS)
ax.set_yticks(np.arange(len(heatmap_labels)))
ax.set_yticklabels(heatmap_labels, fontsize=8)
cbar = fig.colorbar(image, ax=ax)
cbar.set_label("Policy records")
save_figure(fig, POLICY_INTENSITY_HEATMAP_FIG)
fig

# %% [markdown]
# ## 4. Tool Category Coverage and Shares

# %%
tool_rows = []
for category in TOOL_CATEGORIES:
	indicator = f"has_{category}_tool"
	tool_rows.append(
		{
			"tool_category": category,
			"policy_records_hit": int(text_features[indicator].sum()),
			"share_of_all_records": float(text_features[indicator].mean()),
			"local_records_hit": int(text_features.loc[text_features["jurisdiction_type"] == "local", indicator].sum()),
			"central_records_hit": int(text_features.loc[text_features["jurisdiction_type"] == "central", indicator].sum()),
		}
	)
tool_rows.append(
	{
		"tool_category": "any_tool",
		"policy_records_hit": int(text_features["has_any_policy_tool"].sum()),
		"share_of_all_records": float(text_features["has_any_policy_tool"].mean()),
		"local_records_hit": int(text_features.loc[text_features["jurisdiction_type"] == "local", "has_any_policy_tool"].sum()),
		"central_records_hit": int(text_features.loc[text_features["jurisdiction_type"] == "central", "has_any_policy_tool"].sum()),
	}
)
tool_category_summary = pd.DataFrame(tool_rows)
tool_category_summary.to_csv(TOOL_CATEGORY_SUMMARY_OUTPUT, index=False)
tool_category_summary

# %%
tool_shares_by_year = (
	text_features.groupby("publish_year")
	.agg(
		policy_records=("policy_id", "size"),
		supply_tool_policy_count=("has_supply_tool", "sum"),
		demand_tool_policy_count=("has_demand_tool", "sum"),
		environment_tool_policy_count=("has_environment_tool", "sum"),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
		avg_full_text_len=("full_text_len", "mean"),
		full_text_missing_records=("full_text_missing", "sum"),
	)
	.reindex(YEARS)
	.reset_index()
)
for category in ["supply", "demand", "environment", "any"]:
	tool_shares_by_year[f"{category}_tool_share"] = (
		tool_shares_by_year[f"{category}_tool_policy_count"] / tool_shares_by_year["policy_records"]
	)
tool_shares_by_year.to_csv(TOOL_SHARES_BY_YEAR_OUTPUT, index=False)
tool_shares_by_year

# %%
fig, ax = plt.subplots(figsize=(9, 5))
for category, label in [("supply", "Supply"), ("demand", "Demand"), ("environment", "Environment"), ("any", "Any tool")]:
	ax.plot(tool_shares_by_year["publish_year"], tool_shares_by_year[f"{category}_tool_share"], marker="o", linewidth=2, label=label)
ax.set_title("Full-Text Dictionary Tool Hit Shares by Year, v2")
ax.set_xlabel("Year")
ax.set_ylabel("Share of policy records")
ax.set_xticks(YEARS)
ax.set_ylim(0, 1.05)
ax.grid(axis="y", alpha=0.3)
ax.legend()
save_figure(fig, TOOL_SHARES_BY_YEAR_FIG)
fig

# %%
tool_share_by_province = (
	province_year_text_features.groupby("province")
	.agg(
		srdi_policy_count=("srdi_policy_count", "sum"),
		supply_tool_policy_count=("supply_tool_policy_count", "sum"),
		demand_tool_policy_count=("demand_tool_policy_count", "sum"),
		environment_tool_policy_count=("environment_tool_policy_count", "sum"),
		any_tool_policy_count=("any_tool_policy_count", "sum"),
		full_text_missing_policy_count=("full_text_missing_policy_count", "sum"),
		avg_full_text_len=("avg_full_text_len", "mean"),
	)
	.reset_index()
)
for category in ["supply", "demand", "environment", "any"]:
	tool_share_by_province[f"{category}_tool_share"] = (
		tool_share_by_province[f"{category}_tool_policy_count"] / tool_share_by_province["srdi_policy_count"].where(tool_share_by_province["srdi_policy_count"] > 0)
	).fillna(0.0)
tool_share_by_province["province_en"] = tool_share_by_province["province"].map(PROVINCE_EN)
tool_share_by_province = tool_share_by_province.sort_values(["srdi_policy_count", "province"], ascending=[False, True], ignore_index=True)
tool_share_by_province.to_csv(TOOL_SHARE_BY_PROVINCE_OUTPUT, index=False)
tool_share_by_province.head(10)

# %%
plot_tool_province = tool_share_by_province.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 7))
y = np.arange(len(plot_tool_province))
height = 0.24
for offset, (category, label, color) in enumerate(
	[
		("supply", "Supply", "#4777b2"),
		("demand", "Demand", "#d0903f"),
		("environment", "Environment", "#5f9f6e"),
	]
):
	ax.barh(y + (offset - 1) * height, plot_tool_province[f"{category}_tool_share"], height=height, label=label, color=color)
ax.set_title("Full-Text Tool Shares: Top 15 Provinces by Policy Count, v2")
ax.set_xlabel("Share of province policy records")
ax.set_ylabel("Province")
ax.set_yticks(y)
ax.set_yticklabels(plot_tool_province["province_en"])
ax.set_xlim(0, 1.05)
ax.grid(axis="x", alpha=0.25)
ax.legend()
save_figure(fig, TOOL_SHARE_BY_PROVINCE_FIG)
fig

# %% [markdown]
# ## 5. Central-Local Comparison, Empty Full Text, and No-Hit Rows

# %%
central_local_comparison = (
	text_features.groupby("jurisdiction_type")
	.agg(
		policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
		avg_keyword_count=("keyword_count", "mean"),
		full_text_missing_records=("full_text_missing", "sum"),
		supply_tool_policy_count=("has_supply_tool", "sum"),
		demand_tool_policy_count=("has_demand_tool", "sum"),
		environment_tool_policy_count=("has_environment_tool", "sum"),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
		no_tool_policy_count=("has_any_policy_tool", lambda values: int((~values).sum())),
	)
	.reset_index()
)
for column in ["supply", "demand", "environment", "any", "no"]:
	count_column = f"{column}_tool_policy_count" if column != "no" else "no_tool_policy_count"
	central_local_comparison[f"{column}_tool_share"] = central_local_comparison[count_column] / central_local_comparison["policy_records"]
central_local_comparison.to_csv(CENTRAL_LOCAL_COMPARISON_OUTPUT, index=False)
central_local_comparison

# %%
plot_cl = central_local_comparison.set_index("jurisdiction_type")[["supply_tool_share", "demand_tool_share", "environment_tool_share", "no_tool_share"]]
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(plot_cl.index))
width = 0.2
for offset, column in enumerate(plot_cl.columns):
	ax.bar(x + (offset - 1.5) * width, plot_cl[column], width=width, label=column.replace("_tool_share", "").replace("_", " ").title())
ax.set_title("Central vs Local Full-Text Dictionary Feature Shares, v2")
ax.set_xlabel("Jurisdiction type")
ax.set_ylabel("Share of policy records")
ax.set_xticks(x)
ax.set_xticklabels([label.title() for label in plot_cl.index])
ax.set_ylim(0, 1.05)
ax.legend()
ax.grid(axis="y", alpha=0.25)
save_figure(fig, CENTRAL_LOCAL_COMPARISON_FIG)
fig

# %%
missing_full_text_records = (
	text_features.loc[text_features["full_text_missing"]]
	[
		[
			"policy_id",
			"province",
			"source_label_original",
			"jurisdiction_type",
			"publish_date",
			"publish_year",
			"source_workbook",
			"title",
			"agency",
			"source_url",
			"has_any_policy_tool",
			"policy_tool_mix",
		]
	]
	.sort_values(["publish_year", "province", "title"], ignore_index=True)
)
missing_full_text_records.to_csv(MISSING_FULL_TEXT_OUTPUT, index=False)
missing_full_text_records

# %%
no_hit_by_year = (
	text_features.groupby("publish_year")
	.agg(
		policy_records=("policy_id", "size"),
		no_tool_policy_count=("has_any_policy_tool", lambda values: int((~values).sum())),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
	)
	.reindex(YEARS)
	.reset_index()
)
no_hit_by_year["no_tool_share"] = no_hit_by_year["no_tool_policy_count"] / no_hit_by_year["policy_records"]
no_hit_by_year["summary_type"] = "year"
no_hit_by_year = no_hit_by_year.rename(columns={"publish_year": "group_value"})

no_hit_by_jurisdiction = (
	text_features.groupby("jurisdiction_type")
	.agg(
		policy_records=("policy_id", "size"),
		no_tool_policy_count=("has_any_policy_tool", lambda values: int((~values).sum())),
		any_tool_policy_count=("has_any_policy_tool", "sum"),
	)
	.reset_index()
	.rename(columns={"jurisdiction_type": "group_value"})
)
no_hit_by_jurisdiction["no_tool_share"] = no_hit_by_jurisdiction["no_tool_policy_count"] / no_hit_by_jurisdiction["policy_records"]
no_hit_by_jurisdiction["summary_type"] = "jurisdiction_type"

no_hit_summary = pd.concat(
	[
		no_hit_by_year[["summary_type", "group_value", "policy_records", "no_tool_policy_count", "any_tool_policy_count", "no_tool_share"]],
		no_hit_by_jurisdiction[["summary_type", "group_value", "policy_records", "no_tool_policy_count", "any_tool_policy_count", "no_tool_share"]],
	],
	ignore_index=True,
)
no_hit_summary.to_csv(NO_HIT_SUMMARY_OUTPUT, index=False)
no_hit_summary

# %%
fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(no_hit_by_year["group_value"].astype(str), no_hit_by_year["no_tool_share"], color="#b25d4a")
ax.set_title("Full-Text No-Tool-Hit Share by Year, v2")
ax.set_xlabel("Year")
ax.set_ylabel("Share of policy records")
ax.set_ylim(0, max(0.01, no_hit_by_year["no_tool_share"].max() * 1.3))
ax.grid(axis="y", alpha=0.25)
add_value_labels(ax, fmt="{:.3f}")
save_figure(fig, NO_HIT_SHARE_BY_YEAR_FIG)
fig

# %% [markdown]
# ## 6. Keyword Coverage and Interpretation Quality

# %%
category_rows = []
for category in TOOL_CATEGORIES:
	indicator = f"has_{category}_tool"
	category_rows.append(
		{
			"category": category,
			"records_hit": int(text_features[indicator].sum()),
			"record_hit_share": float(text_features[indicator].mean()),
			"mean_hit_count": float(text_features[f"{category}_tool_hit_count"].mean()),
			"median_hit_count": float(text_features[f"{category}_tool_hit_count"].median()),
			"max_hit_count": int(text_features[f"{category}_tool_hit_count"].max()),
		}
	)
category_rows.append(
	{
		"category": "any_tool",
		"records_hit": int(text_features["has_any_policy_tool"].sum()),
		"record_hit_share": float(text_features["has_any_policy_tool"].mean()),
		"mean_hit_count": pd.NA,
		"median_hit_count": pd.NA,
		"max_hit_count": pd.NA,
	}
)
category_comparison = pd.DataFrame(category_rows)
category_comparison["distance_from_any_share"] = (
	category_comparison.loc[category_comparison["category"].eq("any_tool"), "record_hit_share"].item()
	- category_comparison["record_hit_share"]
)
category_comparison.to_csv(CATEGORY_COMPARISON_OUTPUT, index=False)
category_comparison

# %%
term_flags = dictionary_coverage.merge(
	dictionary_coverage_v1[["category", "term", "record_hit_share", "records_hit"]].rename(
		columns={"record_hit_share": "record_hit_share_v1", "records_hit": "records_hit_v1"}
	),
	on=["category", "term"],
	how="left",
	validate="one_to_one",
)
term_flags["coverage_band"] = term_flags["record_hit_share"].map(coverage_band)
term_flags["term_length"] = term_flags["term"].str.len()
term_flags["is_broad_meaning_term"] = term_flags["term"].isin(BROAD_MEANING_TERMS)
term_flags["is_short_term"] = term_flags["term_length"] <= 2
term_flags["is_saturated"] = term_flags["record_hit_share"] >= SATURATED_THRESHOLD
term_flags["is_high_coverage"] = term_flags["record_hit_share"] >= HIGH_THRESHOLD
term_flags["share_delta_from_v1"] = term_flags["record_hit_share"] - term_flags["record_hit_share_v1"]
term_flags["became_high_coverage_from_v1"] = (
	(term_flags["record_hit_share_v1"] < MODERATE_THRESHOLD)
	& (term_flags["record_hit_share"] >= MODERATE_THRESHOLD)
)


def interpretation_role(row: pd.Series) -> str:
	"""Assign a compact interpretation role for paper drafting."""
	if row["is_saturated"] or (row["is_high_coverage"] and row["is_broad_meaning_term"]):
		return "broad_intensity_signal"
	if row["record_hit_share"] >= MODERATE_THRESHOLD:
		return "common_tool_signal"
	if row["record_hit_share"] < LOW_THRESHOLD:
		return "rare_specific_signal"
	return "specific_tool_signal"


term_flags["interpretation_role"] = term_flags.apply(interpretation_role, axis=1)
term_flags["review_note"] = np.select(
	[
		term_flags["is_saturated"],
		term_flags["is_high_coverage"] & term_flags["is_broad_meaning_term"],
		term_flags["is_short_term"] & term_flags["is_broad_meaning_term"],
		term_flags["record_hit_share"] < LOW_THRESHOLD,
	],
	[
		"Very high full-text coverage; use mainly as aggregate intensity evidence.",
		"High-coverage broad term; avoid row-level label interpretation.",
		"Short broad term; inspect examples before qualitative claims.",
		"Rare term; useful as specific signal but contributes little to aggregate coverage.",
	],
	default="No special concern beyond standard dictionary-proxy interpretation.",
)
term_flags = term_flags.sort_values(["record_hit_share", "records_hit"], ascending=[False, False])
term_flags.to_csv(TERM_FLAGS_OUTPUT, index=False)
term_flags.head(20)

# %%
coverage_band_summary = (
	term_flags.groupby(["category", "coverage_band"])
	.size()
	.reset_index(name="terms")
)
coverage_band_summary["coverage_band"] = pd.Categorical(
	coverage_band_summary["coverage_band"],
	categories=["saturated_gte_80pct", "high_50_80pct", "moderate_25_50pct", "low_5_25pct", "rare_lt_5pct"],
	ordered=True,
)
coverage_band_summary = coverage_band_summary.sort_values(["category", "coverage_band"]).reset_index(drop=True)

keyword_quality_summary = pd.DataFrame(
	[
		{"metric": "dictionary_terms", "value": len(term_flags), "note": "Total full-text dictionary terms."},
		{"metric": "saturated_terms_gte_80pct", "value": int(term_flags["is_saturated"].sum()), "note": "Terms hitting at least 80% of records."},
		{"metric": "high_coverage_terms_gte_50pct", "value": int(term_flags["is_high_coverage"].sum()), "note": "Terms hitting at least 50% of records."},
		{"metric": "moderate_plus_terms_gte_25pct", "value": int((term_flags["record_hit_share"] >= MODERATE_THRESHOLD).sum()), "note": "Terms hitting at least 25% of records."},
		{"metric": "rare_terms_lt_5pct", "value": int((term_flags["record_hit_share"] < LOW_THRESHOLD).sum()), "note": "Terms hitting fewer than 5% of records."},
		{"metric": "broad_meaning_terms", "value": int(term_flags["is_broad_meaning_term"].sum()), "note": "Terms flagged as broad by manual rule."},
		{"metric": "broad_intensity_signal_terms", "value": int(term_flags["interpretation_role"].eq("broad_intensity_signal").sum()), "note": "Terms best interpreted as aggregate intensity signals."},
		{"metric": "rare_specific_signal_terms", "value": int(term_flags["interpretation_role"].eq("rare_specific_signal").sum()), "note": "Rare but specific terms."},
		{"metric": "terms_became_high_coverage_from_v1", "value": int(term_flags["became_high_coverage_from_v1"].sum()), "note": "Terms crossing the 25% threshold relative to full-text v1."},
		{"metric": "max_abs_share_delta_from_v1", "value": float(term_flags["share_delta_from_v1"].abs().max()), "note": "Largest absolute term coverage-share change from full-text v1."},
		{"metric": "no_tool_records", "value": len(no_hit_records), "note": "Rows with no supply/demand/environment dictionary hit."},
		{"metric": "missing_full_text_records", "value": int(text_features["full_text_missing"].sum()), "note": "Rows with empty full text retained in v2 features."},
	]
)
keyword_quality_summary.to_csv(KEYWORD_QUALITY_SUMMARY_OUTPUT, index=False)
keyword_quality_summary

# %%
overlap_definitions = {
	"any_tool": text_features["has_any_policy_tool"],
	"supply": text_features["has_supply_tool"],
	"demand": text_features["has_demand_tool"],
	"environment": text_features["has_environment_tool"],
	"supply_and_environment": text_features["has_supply_tool"] & text_features["has_environment_tool"],
	"supply_and_demand": text_features["has_supply_tool"] & text_features["has_demand_tool"],
	"demand_and_environment": text_features["has_demand_tool"] & text_features["has_environment_tool"],
	"all_three_categories": text_features["has_supply_tool"] & text_features["has_demand_tool"] & text_features["has_environment_tool"],
	"only_supply": text_features["has_supply_tool"] & ~text_features["has_demand_tool"] & ~text_features["has_environment_tool"],
	"only_demand": ~text_features["has_supply_tool"] & text_features["has_demand_tool"] & ~text_features["has_environment_tool"],
	"only_environment": ~text_features["has_supply_tool"] & ~text_features["has_demand_tool"] & text_features["has_environment_tool"],
	"no_tool": ~text_features["has_any_policy_tool"],
}
category_overlap = pd.DataFrame(
	[
		{"group": group_name, "records": int(mask.sum()), "record_share": float(mask.mean())}
		for group_name, mask in overlap_definitions.items()
	]
)
category_overlap.to_csv(CATEGORY_OVERLAP_OUTPUT, index=False)
category_overlap

# %%
high_coverage_terms = (
	dictionary_coverage.loc[dictionary_coverage["record_hit_share"] >= MODERATE_THRESHOLD]
	.sort_values(["record_hit_share", "records_hit"], ascending=[False, False])
	.reset_index(drop=True)
)
high_coverage_terms["rank"] = high_coverage_terms.index + 1
high_coverage_terms.to_csv(HIGH_COVERAGE_TERMS_OUTPUT, index=False)
high_coverage_terms.head(20)

# %% [markdown]
# ## 7. Keyword Quality Figures

# %%
band_pivot = (
	coverage_band_summary.pivot(index="category", columns="coverage_band", values="terms")
	.fillna(0)
	.reindex(index=TOOL_CATEGORIES)
)
fig, ax = plt.subplots(figsize=(9, 5))
bottom = np.zeros(len(band_pivot))
for band in band_pivot.columns:
	values = band_pivot[band].to_numpy()
	ax.bar(band_pivot.index, values, bottom=bottom, label=str(band))
	bottom += values
ax.set_title("Full-Text Dictionary Coverage Bands, v2")
ax.set_xlabel("Tool category")
ax.set_ylabel("Dictionary terms")
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.25)
save_figure(fig, KEYWORD_COVERAGE_BAND_FIG)
fig

# %%
fig, ax = plt.subplots(figsize=(8, 5))
plot_category = category_comparison.loc[category_comparison["category"].isin([*TOOL_CATEGORIES, "any_tool"])]
ax.bar(plot_category["category"], plot_category["record_hit_share"], color=["#4777b2", "#d0903f", "#5f9f6e", "#7c6fb0"])
ax.set_title("Full-Text Category Hit Shares, v2")
ax.set_xlabel("Category")
ax.set_ylabel("Share of policy records")
ax.set_ylim(0, 1.05)
ax.grid(axis="y", alpha=0.25)
add_value_labels(ax, fmt="{:.2f}")
save_figure(fig, KEYWORD_CATEGORY_SHARE_FIG)
fig

# %%
overlap_plot = category_overlap.loc[
	category_overlap["group"].isin(["supply", "demand", "environment", "all_three_categories", "no_tool"])
].copy()
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(overlap_plot["group"], overlap_plot["record_share"], color="#4777b2")
ax.set_title("Full-Text Category Overlap Diagnostics, v2")
ax.set_xlabel("Group")
ax.set_ylabel("Share of policy records")
ax.set_ylim(0, 1.05)
ax.tick_params(axis="x", rotation=20)
ax.grid(axis="y", alpha=0.25)
add_value_labels(ax, fmt="{:.2f}")
save_figure(fig, KEYWORD_OVERLAP_FIG)
fig

# %% [markdown]
# ## 8. Interpretation Notes

# %%
interpretation_notes = pd.DataFrame(
	[
		{
			"topic": "v2_window_change",
			"note": "The v2 descriptive window is 2019-2024; 2025 records are excluded and 2019 supplement records are included before text-feature analysis.",
			"paper_use": "Use v2 tables for the corrected DID policy-side time window; avoid mixing v1 2020-2025 descriptive counts into v2 analysis.",
		},
		{
			"topic": "dictionary_stability",
			"note": "The v2 dictionary path reuses the reviewed full-text v1 85-term codebook, so term-coverage changes come from the corpus/window rebuild rather than codebook changes.",
			"paper_use": "Report this as a口径-control choice before comparing v2 dictionary and later MacBERT outputs.",
		},
		{
			"topic": "no_hit_and_missing_full_text",
			"note": "The v2 full-text dictionary path has three no-hit records and one retained empty-full-text record; these are review diagnostics, not grounds for dropping records.",
			"paper_use": "Mention in data-quality notes or appendix to justify retaining the complete v2 policy-record universe.",
		},
		{
			"topic": "broad_term_saturation",
			"note": "High-coverage broad terms remain common in full text; dictionary variables are best read as aggregate policy-tool intensity proxies, not precise row-level labels.",
			"paper_use": "Use category shares and term-flag tables to motivate MacBERT probability intensity as the preferred later-stage text measure.",
		},
		{
			"topic": "macbert_readiness",
			"note": "The v2 corpus and dictionary features have balanced province-year coverage, zero unresolved jurisdiction candidates, and explicit fallback markers for empty full text.",
			"paper_use": "Proceed to v2 MacBERT prediction after implementing model-text fallback for the single empty-full-text record.",
		},
	]
)
interpretation_notes.to_csv(INTERPRETATION_NOTES_OUTPUT, index=False)
interpretation_notes

# %% [markdown]
# ## 9. Output Checks

# %%
output_checks = pd.DataFrame(
	[
		{"check": "year_trend_years", "value": year_trend["publish_year"].tolist(), "expected": YEARS},
		{"check": "province_distribution_units", "value": len(province_distribution), "expected": 31},
		{"check": "heatmap_shape", "value": heatmap_matrix.shape, "expected": (31, 6)},
		{"check": "central_local_groups", "value": sorted(central_local_comparison["jurisdiction_type"].tolist()), "expected": ["central", "local"]},
		{"check": "fulltext_no_hit_total", "value": int(no_hit_by_year["no_tool_policy_count"].sum()), "expected": 3},
		{"check": "high_coverage_terms", "value": len(high_coverage_terms), "expected": 41},
		{"check": "missing_full_text_records", "value": len(missing_full_text_records), "expected": 1},
		{"check": "source_schema_rows", "value": len(source_schema_summary), "expected": 2},
	]
)
output_checks

# %% [markdown]
# ## 10. Reading Notes
#
# These outputs are suitable for a v2 descriptive/quality-analysis subsection or
# appendix draft. They should still be updated after v2 MacBERT prediction if
# the paper table needs dictionary and model-based policy-intensity measures in
# one consolidated descriptive table.
