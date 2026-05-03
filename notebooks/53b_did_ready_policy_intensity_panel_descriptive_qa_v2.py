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
# # DID-Ready Policy Intensity Panel Descriptive QA v2
#
# This notebook produces final descriptive and quality-analysis artifacts for
# the v2 policy-side DID-ready panel.
#
# Scope:
#
# - input: `manual_srdi_did_policy_intensity_panel_v2.csv`;
# - corrected window: 2019-2024;
# - policy-side panel only;
# - descriptive statistics, annual trends, province rankings, regional grouping
#   readiness, correlation diagnostics, outlier audit, and final handoff notes;
# - no enterprise data loading;
# - no DID regression;
# - no heterogeneity effect estimates.

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

PANEL_PATH = ROOT / "data" / "processed" / "manual_srdi_did_policy_intensity_panel_v2.csv"
PANEL_QA_PATH = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_quality_report_v2.csv"
VARIABLE_MAP_PATH = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_variable_map_v2.csv"

DESC_STATS_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_desc_stats_v2.csv"
YEAR_TREND_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_year_trend_v2.csv"
PROVINCE_RANKING_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_province_ranking_v2.csv"
REGION_TEMPLATE_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_region_group_template_v2.csv"
REGION_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_region_summary_v2.csv"
CORRELATION_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_correlations_v2.csv"
STRUCTURE_CORRELATION_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_structure_correlations_v2.csv"
OUTLIER_AUDIT_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_outlier_audit_v2.csv"
FINAL_QA_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_final_qa_v2.csv"
HANDOFF_NOTES_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_handoff_notes_v2.csv"

YEAR_TREND_FIG = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_fig_year_trend_v2.png"
PROVINCE_RANKING_FIG = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_fig_province_ranking_v2.png"
REGION_STRUCTURE_FIG = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_fig_region_structure_v2.png"
CORRELATION_FIG = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_fig_correlations_v2.png"
STRUCTURE_CORRELATION_FIG = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_fig_structure_correlations_v2.png"

YEARS = list(range(2019, 2025))
MAIN_VARIABLES = [
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
]
BASELINE_VARIABLES = [
	"srdi_policy_count",
	"srdi_policy_count_log",
]
ROBUSTNESS_VARIABLES = [
	"srdi_supply_intensity_filtered",
	"srdi_demand_intensity_filtered",
	"srdi_environment_intensity_filtered",
	"srdi_supply_hard_label_count",
	"srdi_demand_hard_label_count",
	"srdi_environment_hard_label_count",
	"srdi_supply_high_confidence_count",
	"srdi_demand_high_confidence_count",
	"srdi_environment_high_confidence_count",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
]
AUDIT_VARIABLES = [
	"srdi_valid_tool_policy_share",
	"srdi_other_exclusion_count",
	"audit_fallback_full_text_for_model_count",
	"audit_jurisdiction_review_candidate_count",
]
SUMMARY_VARIABLES = (
	BASELINE_VARIABLES
	+ MAIN_VARIABLES
	+ ["srdi_total_tool_intensity"]
	+ ROBUSTNESS_VARIABLES
	+ AUDIT_VARIABLES
)
CORRELATION_VARIABLES = [
	"srdi_policy_count",
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
	"srdi_total_tool_intensity",
	"srdi_supply_intensity_filtered",
	"srdi_demand_intensity_filtered",
	"srdi_environment_intensity_filtered",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
]
STRUCTURE_CORRELATION_VARIABLES = [
	"srdi_supply_probability_share",
	"srdi_demand_probability_share",
	"srdi_environment_probability_share",
	"srdi_supply_probability_share_filtered",
	"srdi_demand_probability_share_filtered",
	"srdi_environment_probability_share_filtered",
	"dict_supply_policy_share",
	"dict_demand_policy_share",
	"dict_environment_policy_share",
	"srdi_valid_tool_policy_share",
	"srdi_other_avg_probability",
]
OUTLIER_VARIABLES = [
	"srdi_policy_count",
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
	"srdi_total_tool_intensity",
	"srdi_other_exclusion_count",
]

REGION_GROUP = {
	"北京": "east",
	"天津": "east",
	"河北": "east",
	"上海": "east",
	"江苏": "east",
	"浙江": "east",
	"福建": "east",
	"山东": "east",
	"广东": "east",
	"海南": "east",
	"山西": "central",
	"安徽": "central",
	"江西": "central",
	"河南": "central",
	"湖北": "central",
	"湖南": "central",
	"内蒙古": "west",
	"广西": "west",
	"重庆": "west",
	"四川": "west",
	"贵州": "west",
	"云南": "west",
	"西藏": "west",
	"陕西": "west",
	"甘肃": "west",
	"青海": "west",
	"宁夏": "west",
	"新疆": "west",
	"辽宁": "northeast",
	"吉林": "northeast",
	"黑龙江": "northeast",
}
MUNICIPALITIES = {"北京", "天津", "上海", "重庆"}
PROVINCE_EN = {
	"上海": "Shanghai",
	"云南": "Yunnan",
	"内蒙古": "Inner Mongolia",
	"北京": "Beijing",
	"吉林": "Jilin",
	"四川": "Sichuan",
	"天津": "Tianjin",
	"宁夏": "Ningxia",
	"安徽": "Anhui",
	"山东": "Shandong",
	"山西": "Shanxi",
	"广东": "Guangdong",
	"广西": "Guangxi",
	"新疆": "Xinjiang",
	"江苏": "Jiangsu",
	"江西": "Jiangxi",
	"河北": "Hebei",
	"河南": "Henan",
	"浙江": "Zhejiang",
	"海南": "Hainan",
	"湖北": "Hubei",
	"湖南": "Hunan",
	"甘肃": "Gansu",
	"福建": "Fujian",
	"西藏": "Tibet",
	"贵州": "Guizhou",
	"辽宁": "Liaoning",
	"重庆": "Chongqing",
	"陕西": "Shaanxi",
	"青海": "Qinghai",
	"黑龙江": "Heilongjiang",
}
FIG_DPI = 300


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save a Matplotlib figure with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


def robust_zscore(series: pd.Series) -> pd.Series:
	"""Compute a median/MAD z-score for outlier audit."""
	median = series.median()
	mad = (series - median).abs().median()
	if mad == 0 or pd.isna(mad):
		std = series.std(ddof=0)
		if std == 0 or pd.isna(std):
			return pd.Series(np.zeros(len(series)), index=series.index)
		return (series - series.mean()) / std
	return 0.6745 * (series - median) / mad


# %% [markdown]
# ## 1. Load Final Panel and QA Inputs

# %%
panel = pd.read_csv(PANEL_PATH)
panel_qa = pd.read_csv(PANEL_QA_PATH).set_index("metric")
variable_map = pd.read_csv(VARIABLE_MAP_PATH)

if len(panel) != 186:
	raise ValueError(f"unexpected v2 panel rows: {len(panel)}")
if panel["did_province_key"].nunique() != 31:
	raise ValueError("v2 panel must contain 31 local province units")
if set(panel["did_year"]) != set(YEARS):
	raise ValueError(f"unexpected v2 years: {sorted(panel['did_year'].unique())}")
if panel[["did_province_key", "did_year"]].duplicated().sum() != 0:
	raise ValueError("v2 panel has duplicated did_province_key/did_year rows")
if "central" in set(panel["did_province_key"]):
	raise ValueError("v2 panel must exclude central")
if panel_qa.loc["year_set", "status"] != "pass":
	raise ValueError("v2 panel QA did not pass year_set")

load_checks = pd.DataFrame(
	[
		{"artifact": "did_policy_panel_v2", "path": PANEL_PATH, "rows": len(panel), "columns": panel.shape[1]},
		{"artifact": "panel_quality_report_v2", "path": PANEL_QA_PATH, "rows": len(panel_qa), "columns": panel_qa.shape[1]},
		{"artifact": "variable_map_v2", "path": VARIABLE_MAP_PATH, "rows": len(variable_map), "columns": variable_map.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Descriptive Statistics

# %%
desc_rows = []
role_map = variable_map.set_index("variable")["role"].to_dict()
did_use_map = variable_map.set_index("variable")["did_use"].to_dict()
for variable in SUMMARY_VARIABLES:
	series = panel[variable]
	desc_rows.append(
		{
			"variable": variable,
			"role": role_map.get(variable, ""),
			"did_use": did_use_map.get(variable, ""),
			"non_missing_count": int(series.notna().sum()),
			"missing_count": int(series.isna().sum()),
			"mean": float(series.mean()),
			"std": float(series.std(ddof=0)),
			"min": float(series.min()),
			"p25": float(series.quantile(0.25)),
			"median": float(series.median()),
			"p75": float(series.quantile(0.75)),
			"max": float(series.max()),
			"zero_count": int(series.eq(0).sum()),
		}
	)
desc_stats = pd.DataFrame(desc_rows)
desc_stats.to_csv(DESC_STATS_OUTPUT, index=False)
desc_stats

# %% [markdown]
# ## 3. Annual Trends

# %%
year_trend = (
	panel.groupby("did_year")
	.agg(
		province_units=("did_province_key", "nunique"),
		srdi_policy_count=("srdi_policy_count", "sum"),
		srdi_supply_intensity=("srdi_supply_intensity", "sum"),
		srdi_demand_intensity=("srdi_demand_intensity", "sum"),
		srdi_environment_intensity=("srdi_environment_intensity", "sum"),
		srdi_total_tool_intensity=("srdi_total_tool_intensity", "sum"),
		srdi_other_exclusion_count=("srdi_other_exclusion_count", "sum"),
		avg_valid_tool_policy_share=("srdi_valid_tool_policy_share", "mean"),
		fallback_full_text_rows=("audit_fallback_full_text_for_model_count", "sum"),
		jurisdiction_review_candidate_rows=("audit_jurisdiction_review_candidate_count", "sum"),
	)
	.reset_index()
)
total_tool = year_trend[MAIN_VARIABLES].sum(axis=1)
for variable in MAIN_VARIABLES:
	share_name = variable.replace("_intensity", "_share")
	year_trend[share_name] = np.where(total_tool.gt(0), year_trend[variable] / total_tool, 0.0)
year_trend.to_csv(YEAR_TREND_OUTPUT, index=False)
year_trend

# %%
fig, ax = plt.subplots(figsize=(7.4, 4.2))
ax.plot(year_trend["did_year"], year_trend["srdi_supply_intensity"], marker="o", label="Supply")
ax.plot(year_trend["did_year"], year_trend["srdi_demand_intensity"], marker="o", label="Demand")
ax.plot(year_trend["did_year"], year_trend["srdi_environment_intensity"], marker="o", label="Environment")
ax.set_xlabel("Year")
ax.set_ylabel("Summed MacBERT probability")
ax.set_xticks(YEARS)
ax.legend(frameon=False, ncols=3)
save_figure(fig, YEAR_TREND_FIG)

# %% [markdown]
# ## 4. Province Rankings

# %%
province_ranking = (
	panel.groupby("did_province_key")
	.agg(
		policy_province=("policy_province", "first"),
		srdi_policy_count=("srdi_policy_count", "sum"),
		srdi_supply_intensity=("srdi_supply_intensity", "sum"),
		srdi_demand_intensity=("srdi_demand_intensity", "sum"),
		srdi_environment_intensity=("srdi_environment_intensity", "sum"),
		srdi_total_tool_intensity=("srdi_total_tool_intensity", "sum"),
		srdi_other_exclusion_count=("srdi_other_exclusion_count", "sum"),
		fallback_full_text_rows=("audit_fallback_full_text_for_model_count", "sum"),
		jurisdiction_review_candidate_rows=("audit_jurisdiction_review_candidate_count", "sum"),
	)
	.reset_index()
)
province_ranking["rank_total_tool_intensity"] = province_ranking["srdi_total_tool_intensity"].rank(
	method="dense", ascending=False
).astype(int)
province_ranking["rank_policy_count"] = province_ranking["srdi_policy_count"].rank(method="dense", ascending=False).astype(int)
province_ranking = province_ranking.sort_values(["rank_total_tool_intensity", "did_province_key"])
province_ranking.to_csv(PROVINCE_RANKING_OUTPUT, index=False)
province_ranking.head(10)

# %%
fig, ax = plt.subplots(figsize=(7.4, 5.6))
plot_data = province_ranking.sort_values("srdi_total_tool_intensity", ascending=True).tail(15)
ax.barh(plot_data["did_province_key"].map(PROVINCE_EN), plot_data["srdi_total_tool_intensity"], color="#2563eb")
ax.set_xlabel("Total policy-tool intensity")
ax.set_ylabel("")
save_figure(fig, PROVINCE_RANKING_FIG)

# %% [markdown]
# ## 5. Regional Grouping Readiness
#
# This is a policy-side grouping template for later heterogeneity analysis. It
# does not estimate heterogeneous treatment effects.

# %%
province_totals = province_ranking[["did_province_key", "srdi_total_tool_intensity", "srdi_policy_count"]].copy()
province_totals["intensity_tertile"] = pd.qcut(
	province_totals["srdi_total_tool_intensity"].rank(method="first"),
	q=3,
	labels=["low_policy_intensity", "middle_policy_intensity", "high_policy_intensity"],
)
region_template = province_totals.assign(
	region_group=province_totals["did_province_key"].map(REGION_GROUP),
	is_municipality=province_totals["did_province_key"].isin(MUNICIPALITIES),
).sort_values(["region_group", "did_province_key"])
if region_template["region_group"].isna().any():
	raise ValueError("region template has unmapped provinces")
region_template.to_csv(REGION_TEMPLATE_OUTPUT, index=False)
region_template

# %%
panel_with_region = panel.merge(
	region_template[["did_province_key", "region_group", "is_municipality", "intensity_tertile"]],
	on="did_province_key",
	how="left",
	validate="many_to_one",
)
region_summary = (
	panel_with_region.groupby(["region_group", "did_year"])
	.agg(
		province_units=("did_province_key", "nunique"),
		srdi_policy_count=("srdi_policy_count", "sum"),
		srdi_supply_intensity=("srdi_supply_intensity", "sum"),
		srdi_demand_intensity=("srdi_demand_intensity", "sum"),
		srdi_environment_intensity=("srdi_environment_intensity", "sum"),
		srdi_total_tool_intensity=("srdi_total_tool_intensity", "sum"),
	)
	.reset_index()
)
region_summary.to_csv(REGION_SUMMARY_OUTPUT, index=False)
region_summary.head()

# %%
fig, ax = plt.subplots(figsize=(7.6, 4.4))
region_total = (
	panel_with_region.groupby("region_group")[MAIN_VARIABLES]
	.sum()
	.reindex(["east", "central", "west", "northeast"])
	.reset_index()
)
bottom = np.zeros(len(region_total))
colors = {
	"srdi_supply_intensity": "#2563eb",
	"srdi_demand_intensity": "#059669",
	"srdi_environment_intensity": "#d97706",
}
labels = {
	"srdi_supply_intensity": "Supply",
	"srdi_demand_intensity": "Demand",
	"srdi_environment_intensity": "Environment",
}
for variable in MAIN_VARIABLES:
	values = region_total[variable].to_numpy()
	ax.bar(region_total["region_group"], values, bottom=bottom, color=colors[variable], label=labels[variable])
	bottom += values
ax.set_xlabel("Region group")
ax.set_ylabel("Summed MacBERT probability")
ax.legend(frameon=False, ncols=3)
save_figure(fig, REGION_STRUCTURE_FIG)

# %% [markdown]
# ## 6. Correlation Diagnostics
#
# The first heatmap uses total policy-count and probability-sum variables. It is
# expected to show very high positive correlations because these measures are
# strongly volume-driven. The second heatmap uses structure and average
# variables, which is more informative for policy-tool composition.

# %%
corr = panel[CORRELATION_VARIABLES].corr()
correlation_rows = []
for left in CORRELATION_VARIABLES:
	for right in CORRELATION_VARIABLES:
		correlation_rows.append(
			{
				"left_variable": left,
				"right_variable": right,
				"pearson_corr": float(corr.loc[left, right]),
			}
		)
correlations = pd.DataFrame(correlation_rows)
correlations.to_csv(CORRELATION_OUTPUT, index=False)
correlations.head()

# %%
fig, ax = plt.subplots(figsize=(7.0, 6.2))
image = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")
ax.set_xticks(range(len(CORRELATION_VARIABLES)))
ax.set_yticks(range(len(CORRELATION_VARIABLES)))
short_labels = [
	"count",
	"supply",
	"demand",
	"env",
	"total",
	"supply_f",
	"demand_f",
	"env_f",
	"dict_s",
	"dict_d",
	"dict_e",
]
ax.set_xticklabels(short_labels, rotation=45, ha="right")
ax.set_yticklabels(short_labels)
fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
save_figure(fig, CORRELATION_FIG)
fig

# %%
structure_corr = panel[STRUCTURE_CORRELATION_VARIABLES].corr()
structure_correlation_rows = []
for left in STRUCTURE_CORRELATION_VARIABLES:
	for right in STRUCTURE_CORRELATION_VARIABLES:
		structure_correlation_rows.append(
			{
				"left_variable": left,
				"right_variable": right,
				"pearson_corr": float(structure_corr.loc[left, right]),
			}
		)
structure_correlations = pd.DataFrame(structure_correlation_rows)
structure_correlations.to_csv(STRUCTURE_CORRELATION_OUTPUT, index=False)
structure_correlations.head()

# %%
fig, ax = plt.subplots(figsize=(7.4, 6.4))
image = ax.imshow(structure_corr, vmin=-1, vmax=1, cmap="coolwarm")
ax.set_xticks(range(len(STRUCTURE_CORRELATION_VARIABLES)))
ax.set_yticks(range(len(STRUCTURE_CORRELATION_VARIABLES)))
structure_short_labels = [
	"supply_sh",
	"demand_sh",
	"env_sh",
	"supply_f_sh",
	"demand_f_sh",
	"env_f_sh",
	"dict_s_sh",
	"dict_d_sh",
	"dict_e_sh",
	"valid_sh",
	"other_avg",
]
ax.set_xticklabels(structure_short_labels, rotation=45, ha="right")
ax.set_yticklabels(structure_short_labels)
fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
save_figure(fig, STRUCTURE_CORRELATION_FIG)
fig

# %% [markdown]
# ## 7. Outlier Audit
#
# Outlier candidates are diagnostic rows only. They are not removed or winsorized
# in the policy-side handoff table.

# %%
outlier_audit = panel[
	[
		"policy_panel_id",
		"did_province_key",
		"did_year",
		"policy_province",
		*OUTLIER_VARIABLES,
	]
].copy()
robust_z_columns = []
for variable in OUTLIER_VARIABLES:
	column = f"{variable}_robust_z"
	outlier_audit[column] = robust_zscore(outlier_audit[variable])
	robust_z_columns.append(column)
outlier_audit["max_abs_robust_z"] = outlier_audit[robust_z_columns].abs().max(axis=1)
outlier_audit["outlier_candidate"] = outlier_audit["max_abs_robust_z"].ge(3.0)
outlier_audit = outlier_audit.sort_values(["outlier_candidate", "max_abs_robust_z"], ascending=[False, False])
outlier_audit.to_csv(OUTLIER_AUDIT_OUTPUT, index=False)
outlier_audit.head(15)

# %% [markdown]
# ## 8. Final QA and Handoff Notes

# %%
final_qa = pd.DataFrame(
	[
		{
			"check": "balanced_panel",
			"status": "pass" if len(panel) == 186 and panel["did_province_key"].nunique() == 31 else "fail",
			"evidence": f"rows={len(panel)}; provinces={panel['did_province_key'].nunique()}",
			"blocking": True,
		},
		{
			"check": "correct_window",
			"status": "pass" if set(panel["did_year"]) == set(YEARS) else "fail",
			"evidence": ";".join(map(str, sorted(panel["did_year"].unique()))),
			"blocking": True,
		},
		{
			"check": "main_variables_complete",
			"status": "pass" if panel[MAIN_VARIABLES].isna().sum().sum() == 0 else "fail",
			"evidence": f"missing={int(panel[MAIN_VARIABLES].isna().sum().sum())}",
			"blocking": True,
		},
		{
			"check": "fallback_audit_retained",
			"status": "pass" if int(panel["audit_fallback_full_text_for_model_count"].sum()) == 1 else "needs_review",
			"evidence": f"fallback_rows={int(panel['audit_fallback_full_text_for_model_count'].sum())}",
			"blocking": False,
		},
		{
			"check": "jurisdiction_audit_clear",
			"status": "pass" if int(panel["audit_jurisdiction_review_candidate_count"].sum()) == 0 else "fail",
			"evidence": f"jurisdiction_review_candidate_rows={int(panel['audit_jurisdiction_review_candidate_count'].sum())}",
			"blocking": True,
		},
		{
			"check": "heterogeneity_readiness_not_effect",
			"status": "ready",
			"evidence": str(REGION_TEMPLATE_OUTPUT.relative_to(ROOT)),
			"blocking": False,
		},
	]
)
final_qa.to_csv(FINAL_QA_OUTPUT, index=False)
final_qa

# %%
handoff_notes = pd.DataFrame(
	[
		{
			"topic": "final_panel_scope",
			"note": "The v2 final policy-side panel is complete for 31 local provinces over 2019-2024.",
			"evidence": f"rows={len(panel)}; years={';'.join(map(str, YEARS))}.",
		},
		{
			"topic": "merge_keys",
			"note": "Use did_province_key and did_year for downstream enterprise-panel merging after province-name confirmation.",
			"evidence": "policy_panel_id is unique and did_province_key/did_year has no duplicates.",
		},
		{
			"topic": "main_variables",
			"note": "Use continuous MacBERT probability sums as main policy-tool moderators.",
			"evidence": ";".join(MAIN_VARIABLES),
		},
		{
			"topic": "robustness_variables",
			"note": "Filtered sums, hard-label counts, high-confidence counts, and dictionary measures are retained for robustness checks.",
			"evidence": str(VARIABLE_MAP_PATH.relative_to(ROOT)),
		},
		{
			"topic": "heterogeneity_readiness",
			"note": "Region and intensity grouping outputs are templates for later heterogeneity analysis, not treatment-effect results.",
			"evidence": str(REGION_TEMPLATE_OUTPUT.relative_to(ROOT)),
		},
		{
			"topic": "scope_boundary",
			"note": "This repo stage stops at the policy-side panel; enterprise merge and DID regressions remain downstream tasks.",
			"evidence": "No enterprise data are loaded in this notebook.",
		},
	]
)
handoff_notes.to_csv(HANDOFF_NOTES_OUTPUT, index=False)
handoff_notes

# %% [markdown]
# ## 9. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "desc_stats", "path": DESC_STATS_OUTPUT, "rows": len(desc_stats), "exists": DESC_STATS_OUTPUT.exists()},
		{"artifact": "year_trend", "path": YEAR_TREND_OUTPUT, "rows": len(year_trend), "exists": YEAR_TREND_OUTPUT.exists()},
		{"artifact": "province_ranking", "path": PROVINCE_RANKING_OUTPUT, "rows": len(province_ranking), "exists": PROVINCE_RANKING_OUTPUT.exists()},
		{"artifact": "region_template", "path": REGION_TEMPLATE_OUTPUT, "rows": len(region_template), "exists": REGION_TEMPLATE_OUTPUT.exists()},
		{"artifact": "region_summary", "path": REGION_SUMMARY_OUTPUT, "rows": len(region_summary), "exists": REGION_SUMMARY_OUTPUT.exists()},
		{"artifact": "correlations", "path": CORRELATION_OUTPUT, "rows": len(correlations), "exists": CORRELATION_OUTPUT.exists()},
		{"artifact": "structure_correlations", "path": STRUCTURE_CORRELATION_OUTPUT, "rows": len(structure_correlations), "exists": STRUCTURE_CORRELATION_OUTPUT.exists()},
		{"artifact": "outlier_audit", "path": OUTLIER_AUDIT_OUTPUT, "rows": len(outlier_audit), "exists": OUTLIER_AUDIT_OUTPUT.exists()},
		{"artifact": "final_qa", "path": FINAL_QA_OUTPUT, "rows": len(final_qa), "exists": FINAL_QA_OUTPUT.exists()},
		{"artifact": "handoff_notes", "path": HANDOFF_NOTES_OUTPUT, "rows": len(handoff_notes), "exists": HANDOFF_NOTES_OUTPUT.exists()},
		{"artifact": "year_trend_figure", "path": YEAR_TREND_FIG, "exists": YEAR_TREND_FIG.exists()},
		{"artifact": "province_ranking_figure", "path": PROVINCE_RANKING_FIG, "exists": PROVINCE_RANKING_FIG.exists()},
		{"artifact": "region_structure_figure", "path": REGION_STRUCTURE_FIG, "exists": REGION_STRUCTURE_FIG.exists()},
		{"artifact": "correlation_figure", "path": CORRELATION_FIG, "exists": CORRELATION_FIG.exists()},
		{"artifact": "structure_correlation_figure", "path": STRUCTURE_CORRELATION_FIG, "exists": STRUCTURE_CORRELATION_FIG.exists()},
	]
)
output_checklist
