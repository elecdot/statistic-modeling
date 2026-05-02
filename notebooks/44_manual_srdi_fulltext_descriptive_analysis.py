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
# # Manual SRDI Full-Text Descriptive Analysis
#
# This notebook produces the main paper-facing descriptive materials for the
# full-text SRDI policy-mining path.
#
# Scope:
#
# - policy universe: manually collected central/provincial `专精特新` policy
#   records, 2020-2025;
# - main text measure: full-text v1 dictionary features from
#   `notebooks/42_manual_srdi_fulltext_text_mining.py`;
# - v0 title/abstract outputs remain available as robustness and method
#   comparison, but this notebook uses full text as the primary axis;
# - figures use English labels to avoid Chinese font-rendering problems;
# - CSV tables retain Chinese province and dictionary-term fields for audit.

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

POLICY_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv"
INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v0.csv"
TEXT_FEATURES_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv"
PROVINCE_YEAR_TEXT_FEATURES_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv"
DICTIONARY_COVERAGE_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv"

YEAR_TREND_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_year_trend.csv"
PROVINCE_DISTRIBUTION_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_province_distribution.csv"
TOOL_CATEGORY_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_category_summary.csv"
TOOL_SHARES_BY_YEAR_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_shares_by_year.csv"
HEATMAP_MATRIX_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_policy_intensity_heatmap_matrix.csv"
TOOL_SHARE_BY_PROVINCE_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_tool_share_by_province.csv"
CENTRAL_LOCAL_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_central_local_comparison.csv"
NO_HIT_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_no_hit_summary.csv"
HIGH_COVERAGE_TERMS_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_desc_high_coverage_terms.csv"

YEAR_TREND_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_year_trend.png"
PROVINCE_DISTRIBUTION_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_province_distribution.png"
TOOL_SHARES_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_tool_shares_by_year.png"
POLICY_INTENSITY_HEATMAP_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_policy_intensity_heatmap.png"
TOOL_SHARE_BY_PROVINCE_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_tool_share_by_province.png"
CENTRAL_LOCAL_COMPARISON_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_central_local_comparison.png"
NO_HIT_SHARE_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_no_hit_share_by_year.png"
HIGH_COVERAGE_TERMS_FIG = OUTPUT_DIR / "manual_srdi_fulltext_fig_high_coverage_terms.png"

YEARS = list(range(2020, 2026))
TOOL_CATEGORIES = ["supply", "demand", "environment"]
HIGH_COVERAGE_SHARE_THRESHOLD = 0.25

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

FIGSIZE_WIDE = (9, 5)
FIGSIZE_TALL = (9, 8)
FIG_DPI = 300


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


# %% [markdown]
# ## 1. Load Inputs
#
# Full-text records and full-text feature tables should use the same policy
# universe as v0: 4475 records and a balanced 31 x 6 local province-year panel.

# %%
records = pd.read_csv(POLICY_RECORDS_PATH)
intensity = pd.read_csv(INTENSITY_PATH)
text_features = pd.read_csv(TEXT_FEATURES_PATH)
province_year_text_features = pd.read_csv(PROVINCE_YEAR_TEXT_FEATURES_PATH)
dictionary_coverage = pd.read_csv(DICTIONARY_COVERAGE_PATH)

for column in ["has_supply_tool", "has_demand_tool", "has_environment_tool", "has_any_policy_tool"]:
	text_features[column] = bool_series(text_features[column])

load_checks = pd.DataFrame(
	[
		{"artifact": "fulltext_policy_records", "rows": len(records), "columns": records.shape[1]},
		{"artifact": "province_year_intensity", "rows": len(intensity), "columns": intensity.shape[1]},
		{"artifact": "fulltext_text_features", "rows": len(text_features), "columns": text_features.shape[1]},
		{"artifact": "province_year_fulltext_features", "rows": len(province_year_text_features), "columns": province_year_text_features.shape[1]},
		{"artifact": "fulltext_dictionary_coverage", "rows": len(dictionary_coverage), "columns": dictionary_coverage.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Annual SRDI Policy Count Trend

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
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
ax.plot(year_trend["publish_year"], year_trend["total_policy_count"], marker="o", linewidth=2, label="Total")
ax.plot(year_trend["publish_year"], year_trend["local"], marker="o", linewidth=2, label="Local")
ax.plot(year_trend["publish_year"], year_trend["central"], marker="o", linewidth=2, label="Central")
ax.set_title("Annual SRDI Policy Records, 2020-2025")
ax.set_xlabel("Year")
ax.set_ylabel("Policy records")
ax.set_xticks(YEARS)
ax.grid(axis="y", alpha=0.3)
ax.legend()
save_figure(fig, YEAR_TREND_FIG)
fig

# %% [markdown]
# ## 3. Province Policy Count Distribution

# %%
province_distribution = (
	records.loc[records["jurisdiction_type"] == "local"]
	.groupby("province")
	.agg(
		policy_count=("policy_id", "size"),
		total_keyword_count=("keyword_count", "sum"),
		avg_keyword_count=("keyword_count", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
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
fig, ax = plt.subplots(figsize=FIGSIZE_TALL)
ax.barh(plot_distribution["province_en"], plot_distribution["policy_count"], color="#4777b2")
ax.set_title("Local SRDI Policy Records by Province, 2020-2025")
ax.set_xlabel("Policy records")
ax.set_ylabel("Province")
ax.grid(axis="x", alpha=0.25)
save_figure(fig, PROVINCE_DISTRIBUTION_FIG)
fig

# %% [markdown]
# ## 4. Full-Text Tool Category Shares
#
# Full-text v1 uses overlapping dictionary categories. A policy can match more
# than one tool category.

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
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
for category, label in [("supply", "Supply"), ("demand", "Demand"), ("environment", "Environment"), ("any", "Any tool")]:
	ax.plot(tool_shares_by_year["publish_year"], tool_shares_by_year[f"{category}_tool_share"], marker="o", linewidth=2, label=label)
ax.set_title("Full-Text Dictionary Tool Hit Shares by Year")
ax.set_xlabel("Year")
ax.set_ylabel("Share of policy records")
ax.set_xticks(YEARS)
ax.set_ylim(0, 1.05)
ax.grid(axis="y", alpha=0.3)
ax.legend()
save_figure(fig, TOOL_SHARES_BY_YEAR_FIG)
fig

# %% [markdown]
# ## 5. Province-Year Policy Intensity Heatmap
#
# This heatmap remains count-based. It is the most direct visual bridge to the
# DID province-year data structure.

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
ax.set_title("Province-Year SRDI Policy Intensity")
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
# ## 6. Full-Text Tool Structure By Province

# %%
tool_share_by_province = (
	province_year_text_features.groupby("province")
	.agg(
		srdi_policy_count=("srdi_policy_count", "sum"),
		supply_tool_policy_count=("supply_tool_policy_count", "sum"),
		demand_tool_policy_count=("demand_tool_policy_count", "sum"),
		environment_tool_policy_count=("environment_tool_policy_count", "sum"),
		any_tool_policy_count=("any_tool_policy_count", "sum"),
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
ax.set_title("Full-Text Tool Shares: Top 15 Provinces by Policy Count")
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
# ## 7. Central vs Local Full-Text Feature Comparison

# %%
central_local_comparison = (
	text_features.groupby("jurisdiction_type")
	.agg(
		policy_records=("policy_id", "size"),
		avg_text_surface_len=("text_surface_len", "mean"),
		avg_full_text_len=("full_text_len", "mean"),
		avg_keyword_count=("keyword_count", "mean"),
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
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
x = np.arange(len(plot_cl.index))
width = 0.2
for offset, column in enumerate(plot_cl.columns):
	ax.bar(x + (offset - 1.5) * width, plot_cl[column], width=width, label=column.replace("_tool_share", "").replace("_", " ").title())
ax.set_title("Central vs Local Full-Text Dictionary Feature Shares")
ax.set_xlabel("Jurisdiction type")
ax.set_ylabel("Share of policy records")
ax.set_xticks(x)
ax.set_xticklabels([label.title() for label in plot_cl.index])
ax.set_ylim(0, 1.05)
ax.legend()
ax.grid(axis="y", alpha=0.25)
save_figure(fig, CENTRAL_LOCAL_COMPARISON_FIG)
fig

# %% [markdown]
# ## 8. Full-Text No-Hit Share
#
# Full-text v1 should almost eliminate no-hit rows. Remaining no-hit rows are
# review targets, not processing failures.

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
fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
ax.bar(no_hit_by_year["group_value"].astype(str), no_hit_by_year["no_tool_share"], color="#b25d4a")
ax.set_title("Full-Text No-Tool-Hit Share by Year")
ax.set_xlabel("Year")
ax.set_ylabel("Share of policy records")
ax.set_ylim(0, max(0.01, no_hit_by_year["no_tool_share"].max() * 1.3))
ax.grid(axis="y", alpha=0.25)
add_value_labels(ax, fmt="{:.3f}")
save_figure(fig, NO_HIT_SHARE_BY_YEAR_FIG)
fig

# %% [markdown]
# ## 9. High-Coverage Full-Text Terms
#
# Full text improves recall but broad terms can become highly saturated. The
# CSV keeps Chinese terms; the figure uses term indexes so it renders reliably
# without Chinese fonts.

# %%
high_coverage_terms = (
	dictionary_coverage.loc[dictionary_coverage["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD]
	.sort_values(["record_hit_share", "records_hit"], ascending=[False, False])
	.reset_index(drop=True)
)
high_coverage_terms["rank"] = high_coverage_terms.index + 1
high_coverage_terms.to_csv(HIGH_COVERAGE_TERMS_OUTPUT, index=False)
high_coverage_terms.head(20)

# %%
plot_terms = high_coverage_terms.head(20).sort_values("record_hit_share", ascending=True).copy()
plot_terms["plot_label"] = [
	f"{category} term {rank}"
	for rank, category in zip(plot_terms["rank"], plot_terms["category"], strict=True)
]
fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(plot_terms["plot_label"], plot_terms["record_hit_share"], color="#4777b2")
ax.set_title("Top Full-Text High-Coverage Terms")
ax.set_xlabel("Share of policy records hit")
ax.set_ylabel("Dictionary term index")
ax.grid(axis="x", alpha=0.25)
save_figure(fig, HIGH_COVERAGE_TERMS_FIG)
fig

# %% [markdown]
# ## 10. Output Checks

# %%
output_checks = pd.DataFrame(
	[
		{"check": "year_trend_years", "value": year_trend["publish_year"].tolist(), "expected": YEARS},
		{"check": "province_distribution_units", "value": len(province_distribution), "expected": 31},
		{"check": "heatmap_shape", "value": heatmap_matrix.shape, "expected": (31, 6)},
		{"check": "central_local_groups", "value": sorted(central_local_comparison["jurisdiction_type"].tolist()), "expected": ["central", "local"]},
		{"check": "fulltext_no_hit_total", "value": int(no_hit_by_year["no_tool_policy_count"].sum()), "expected": 2},
		{"check": "high_coverage_terms", "value": len(high_coverage_terms), "expected": 41},
	]
)
output_checks

# %% [markdown]
# ## 11. Reading Notes
#
# These descriptive outputs should be read as the main full-text policy-mining
# evidence for the paper draft. They show strong full-text coverage and clear
# province-year variation, while also documenting broad-term saturation through
# the high-coverage term table.
