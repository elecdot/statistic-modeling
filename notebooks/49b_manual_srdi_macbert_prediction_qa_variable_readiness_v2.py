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
# # Manual SRDI MacBERT Prediction QA and Variable Readiness v2
#
# This notebook checks whether the 2019-2024 v2 MacBERT full-corpus prediction
# outputs are ready to feed the next policy-text variable-selection step.
#
# Scope:
#
# - input: completed v2 MacBERT row-level predictions and province-year
#   intensity table;
# - comparison baseline: v2 full-text dictionary province-year features;
# - checks: prediction completeness, panel balance, full-text fallback audit,
#   year/province probability distributions, dictionary alignment, boundary
#   samples, and variable-readiness decisions;
# - stop point: no final DID-ready panel, no enterprise merge, no DID estimate.

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

CLASSIFIED_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v2.csv"
MACBERT_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v2.csv"
DICTIONARY_ROW_FEATURES_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v2.csv"
DICTIONARY_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v2.csv"
PREDICTION_QUALITY_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v2.csv"
PREDICTION_PROBABILITY_SUMMARY_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v2.csv"
TRAINING_METRICS_PATH = ROOT / "outputs" / "manual_srdi_macbert_multilabel_metrics_v1.csv"

QA_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_qa_summary_v2.csv"
PROBABILITY_BY_YEAR_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_probability_by_year_v2.csv"
PROBABILITY_BY_PROVINCE_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_probability_by_province_v2.csv"
TOOL_STRUCTURE_BY_YEAR_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_tool_structure_by_year_v2.csv"
DICTIONARY_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_dictionary_comparison_v2.csv"
PROVINCE_YEAR_OUTLIERS_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_province_year_outliers_v2.csv"
BOUNDARY_SAMPLES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_boundary_samples_v2.csv"
VARIABLE_CANDIDATES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_variable_candidates_v2.csv"
VARIABLE_READINESS_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_variable_readiness_decision_v2.csv"
INTERPRETATION_NOTES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_prediction_interpretation_notes_v2.csv"

PROBABILITY_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_probability_by_year_v2.png"
TOOL_INTENSITY_BY_YEAR_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_tool_intensity_by_year_v2.png"
DICTIONARY_ALIGNMENT_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_dictionary_alignment_v2.png"
OTHER_SHARE_BY_PROVINCE_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_other_share_by_province_v2.png"

YEARS = list(range(2019, 2025))
TOOL_LABELS = ["supply", "demand", "environment"]
PROBABILITY_COLUMNS = ["p_supply", "p_demand", "p_environment", "p_other"]
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


def bool_series(series: pd.Series) -> pd.Series:
	"""Read bool-like CSV columns robustly."""
	if series.dtype == bool:
		return series
	return series.astype(str).str.lower().isin({"true", "1", "yes"})


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save a Matplotlib figure with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


def status_from_bool(condition: bool) -> str:
	"""Return a compact pass/fail status string for QA tables."""
	return "pass" if condition else "fail"


def robust_zscore(series: pd.Series) -> pd.Series:
	"""Compute a median/MAD z-score for outlier screening."""
	median = series.median()
	mad = (series - median).abs().median()
	if mad == 0 or pd.isna(mad):
		std = series.std(ddof=0)
		if std == 0 or pd.isna(std):
			return pd.Series(np.zeros(len(series)), index=series.index)
		return (series - series.mean()) / std
	return 0.6745 * (series - median) / mad


# %% [markdown]
# ## 1. Load Inputs and Structural Checks
#
# The expected v2 policy-side frame is 3989 row-level predictions and a balanced
# 31 local province x 2019-2024 province-year table.

# %%
classified = pd.read_csv(CLASSIFIED_PATH)
macbert_intensity = pd.read_csv(MACBERT_INTENSITY_PATH)
dictionary_rows = pd.read_csv(DICTIONARY_ROW_FEATURES_PATH)
dictionary_intensity = pd.read_csv(DICTIONARY_INTENSITY_PATH)
prediction_quality = pd.read_csv(PREDICTION_QUALITY_PATH).set_index("metric")
prediction_probability_summary = pd.read_csv(PREDICTION_PROBABILITY_SUMMARY_PATH)
training_metrics = pd.read_csv(TRAINING_METRICS_PATH)

for column in ["full_text_missing", "full_text_fallback_for_model", "needs_jurisdiction_review"]:
	if column in classified:
		classified[column] = bool_series(classified[column])

for column in ["has_supply_tool", "has_demand_tool", "has_environment_tool", "has_any_policy_tool"]:
	if column in dictionary_rows:
		dictionary_rows[column] = bool_series(dictionary_rows[column])

load_checks = pd.DataFrame(
	[
		{"artifact": "macbert_classified_rows_v2", "rows": len(classified), "columns": classified.shape[1]},
		{"artifact": "macbert_province_year_intensity_v2", "rows": len(macbert_intensity), "columns": macbert_intensity.shape[1]},
		{"artifact": "dictionary_row_features_v2", "rows": len(dictionary_rows), "columns": dictionary_rows.shape[1]},
		{"artifact": "dictionary_province_year_intensity_v2", "rows": len(dictionary_intensity), "columns": dictionary_intensity.shape[1]},
		{"artifact": "prediction_quality_report_v2", "rows": len(prediction_quality), "columns": prediction_quality.shape[1]},
		{"artifact": "training_metrics_v1_checkpoint", "rows": len(training_metrics), "columns": training_metrics.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Basic Prediction QA

# %%
probabilities_in_range = bool(classified[PROBABILITY_COLUMNS].apply(lambda series: series.between(0, 1).all()).all())
panel_is_balanced = (
	len(macbert_intensity) == 186
	and macbert_intensity["province"].nunique() == 31
	and set(macbert_intensity["publish_year"]) == set(YEARS)
	and macbert_intensity[["province", "publish_year"]].duplicated().sum() == 0
	and "central" not in set(macbert_intensity["province"])
)
test_metrics = training_metrics.loc[training_metrics["split"].eq("test")].iloc[0]

fallback_rows = int(classified["model_text_source"].eq("title_metadata_fallback").sum())
missing_full_text_rows = int(classified["full_text_missing"].sum())
jurisdiction_review_rows = int(classified["needs_jurisdiction_review"].sum())
other_label_share = float(classified["other_label"].mean())
valid_tool_policy_share = float(classified["valid_tool_policy"].mean())

qa_summary = pd.DataFrame(
	[
		{"metric": "classified_rows", "value": len(classified), "note": "Expected 3989 for v2."},
		{"metric": "policy_id_unique", "value": bool(classified["policy_id"].is_unique), "note": "Must be true before variable selection."},
		{"metric": "probabilities_in_range", "value": probabilities_in_range, "note": "All p_* values should be in [0, 1]."},
		{"metric": "year_set", "value": ";".join(map(str, sorted(classified["publish_year"].unique()))), "note": "Expected 2019-2024."},
		{"metric": "central_rows", "value": int(classified["jurisdiction_type"].eq("central").sum()), "note": "Retained in row-level predictions."},
		{"metric": "local_rows", "value": int(classified["jurisdiction_type"].eq("local").sum()), "note": "Used for province-year aggregation."},
		{"metric": "province_year_rows", "value": len(macbert_intensity), "note": "Expected 186."},
		{"metric": "province_units", "value": int(macbert_intensity["province"].nunique()), "note": "Expected 31 local province units."},
		{"metric": "panel_is_balanced_31x6", "value": panel_is_balanced, "note": "Balanced 2019-2024 local province panel."},
		{"metric": "missing_full_text_rows", "value": missing_full_text_rows, "note": "Retained and audited, not dropped."},
		{"metric": "model_text_fallback_rows", "value": fallback_rows, "note": "Rows predicted using title/metadata fallback."},
		{"metric": "jurisdiction_review_candidate_rows", "value": jurisdiction_review_rows, "note": "Should be zero before variable selection."},
		{"metric": "valid_tool_policy_rows", "value": int(classified["valid_tool_policy"].sum()), "note": "Rows retained by hard-label filter."},
		{"metric": "valid_tool_policy_share", "value": valid_tool_policy_share, "note": "Audit share, not a target threshold."},
		{"metric": "other_label_rows", "value": int(classified["other_label"].sum()), "note": "Boundary/exclusion rows."},
		{"metric": "other_label_share", "value": other_label_share, "note": "Used for exclusion audit."},
		{"metric": "test_micro_f1", "value": float(test_metrics["micro_f1"]), "note": "Held-out round-1 test metric from v1 checkpoint."},
		{"metric": "test_macro_f1", "value": float(test_metrics["macro_f1"]), "note": "Held-out round-1 test metric from v1 checkpoint."},
		{"metric": "test_samples_jaccard", "value": float(test_metrics["samples_jaccard"]), "note": "Held-out round-1 test metric from v1 checkpoint."},
	]
)
qa_summary.to_csv(QA_SUMMARY_OUTPUT, index=False)
qa_summary

# %% [markdown]
# ## 3. Probability Distribution by Year and Province
#
# These descriptive tables support paper-facing checks on whether the 2019
# supplement or any province drives abnormal prediction patterns.

# %%
probability_by_year = (
	classified.groupby("publish_year")
	.agg(
		policy_records=("policy_id", "size"),
		local_records=("jurisdiction_type", lambda series: int(series.eq("local").sum())),
		central_records=("jurisdiction_type", lambda series: int(series.eq("central").sum())),
		avg_p_supply=("p_supply", "mean"),
		avg_p_demand=("p_demand", "mean"),
		avg_p_environment=("p_environment", "mean"),
		avg_p_other=("p_other", "mean"),
		supply_label_share=("supply_label", "mean"),
		demand_label_share=("demand_label", "mean"),
		environment_label_share=("environment_label", "mean"),
		other_label_share=("other_label", "mean"),
		valid_tool_policy_share=("valid_tool_policy", "mean"),
		model_text_fallback_rows=("model_text_source", lambda series: int(series.eq("title_metadata_fallback").sum())),
	)
	.reset_index()
)
probability_by_year.to_csv(PROBABILITY_BY_YEAR_OUTPUT, index=False)
probability_by_year

# %%
probability_by_province = (
	classified.loc[classified["jurisdiction_type"].eq("local")]
	.groupby("province")
	.agg(
		policy_records=("policy_id", "size"),
		avg_p_supply=("p_supply", "mean"),
		avg_p_demand=("p_demand", "mean"),
		avg_p_environment=("p_environment", "mean"),
		avg_p_other=("p_other", "mean"),
		supply_label_share=("supply_label", "mean"),
		demand_label_share=("demand_label", "mean"),
		environment_label_share=("environment_label", "mean"),
		other_label_share=("other_label", "mean"),
		valid_tool_policy_share=("valid_tool_policy", "mean"),
		model_text_fallback_rows=("model_text_source", lambda series: int(series.eq("title_metadata_fallback").sum())),
	)
	.reset_index()
	.sort_values(["avg_p_other", "policy_records"], ascending=[False, False])
)
probability_by_province.to_csv(PROBABILITY_BY_PROVINCE_OUTPUT, index=False)
probability_by_province.head(10)

# %%
fig, ax = plt.subplots(figsize=(7.2, 4.2))
for column, label in [
	("avg_p_supply", "Supply"),
	("avg_p_demand", "Demand"),
	("avg_p_environment", "Environment"),
	("avg_p_other", "Other"),
]:
	ax.plot(probability_by_year["publish_year"], probability_by_year[column], marker="o", label=label)
ax.set_xlabel("Year")
ax.set_ylabel("Average predicted probability")
ax.set_xticks(YEARS)
ax.set_ylim(0, 1)
ax.legend(frameon=False, ncols=2)
save_figure(fig, PROBABILITY_BY_YEAR_FIG)
fig

fig, ax = plt.subplots(figsize=(7.8, 5.0))
plot_data = probability_by_province.sort_values("other_label_share", ascending=True).tail(12)
ax.barh(plot_data["province"].map(PROVINCE_EN).fillna(plot_data["province"]), plot_data["other_label_share"], color="#6b7280")
ax.set_xlabel("Other-label share")
ax.set_ylabel("")
ax.set_xlim(0, max(0.12, plot_data["other_label_share"].max() * 1.15))
save_figure(fig, OTHER_SHARE_BY_PROVINCE_FIG)
fig

# %% [markdown]
# ## 4. Province-Year Tool Structure and Dictionary Alignment
#
# MacBERT probability sums are the main candidate variables because they retain
# continuous model information. Dictionary counts remain transparent robustness
# candidates.

# %%
tool_structure_by_year = (
	macbert_intensity.groupby("publish_year")
	.agg(
		srdi_policy_count=("srdi_policy_count", "sum"),
		valid_tool_policy_count=("valid_tool_policy_count", "sum"),
		other_label_policy_count=("other_label_policy_count", "sum"),
		sum_p_supply=("sum_p_supply", "sum"),
		sum_p_demand=("sum_p_demand", "sum"),
		sum_p_environment=("sum_p_environment", "sum"),
		sum_p_other=("sum_p_other", "sum"),
		supply_label_policy_count=("supply_label_policy_count", "sum"),
		demand_label_policy_count=("demand_label_policy_count", "sum"),
		environment_label_policy_count=("environment_label_policy_count", "sum"),
	)
	.reset_index()
)
total_tool_sum = tool_structure_by_year[["sum_p_supply", "sum_p_demand", "sum_p_environment"]].sum(axis=1)
for category in TOOL_LABELS:
	tool_structure_by_year[f"{category}_probability_share"] = np.where(
		total_tool_sum.gt(0),
		tool_structure_by_year[f"sum_p_{category}"] / total_tool_sum,
		0.0,
	)
tool_structure_by_year["valid_tool_policy_share"] = np.where(
	tool_structure_by_year["srdi_policy_count"].gt(0),
	tool_structure_by_year["valid_tool_policy_count"] / tool_structure_by_year["srdi_policy_count"],
	0.0,
)
tool_structure_by_year["other_label_policy_share"] = np.where(
	tool_structure_by_year["srdi_policy_count"].gt(0),
	tool_structure_by_year["other_label_policy_count"] / tool_structure_by_year["srdi_policy_count"],
	0.0,
)
tool_structure_by_year.to_csv(TOOL_STRUCTURE_BY_YEAR_OUTPUT, index=False)
tool_structure_by_year

# %%
fig, ax = plt.subplots(figsize=(7.4, 4.4))
bottom = np.zeros(len(tool_structure_by_year))
colors = {"supply": "#2563eb", "demand": "#059669", "environment": "#d97706"}
labels = {"supply": "Supply", "demand": "Demand", "environment": "Environment"}
for category in TOOL_LABELS:
	values = tool_structure_by_year[f"sum_p_{category}"].to_numpy()
	ax.bar(tool_structure_by_year["publish_year"], values, bottom=bottom, label=labels[category], color=colors[category])
	bottom += values
ax.set_xlabel("Year")
ax.set_ylabel("Summed MacBERT probability")
ax.set_xticks(YEARS)
ax.legend(frameon=False, ncols=3)
save_figure(fig, TOOL_INTENSITY_BY_YEAR_FIG)
fig

# %%
comparison = macbert_intensity.merge(
	dictionary_intensity,
	on=["province", "publish_year", "srdi_policy_count", "log_srdi_policy_count_plus1"],
	how="inner",
	validate="one_to_one",
	suffixes=("_macbert", "_dictionary"),
)

correlation_rows = []
for category in TOOL_LABELS:
	pairs = [
		(f"sum_p_{category}", f"{category}_tool_policy_count", "raw_sum_vs_dictionary_count"),
		(f"filtered_sum_p_{category}", f"{category}_tool_policy_count", "filtered_sum_vs_dictionary_count"),
		(f"{category}_probability_share", f"{category}_tool_policy_share", "raw_share_vs_dictionary_share"),
		(f"filtered_{category}_probability_share", f"{category}_tool_policy_share", "filtered_share_vs_dictionary_share"),
		(f"{category}_label_policy_count", f"{category}_tool_policy_count", "hard_label_count_vs_dictionary_count"),
	]
	for macbert_column, dictionary_column, comparison_type in pairs:
		correlation_rows.append(
			{
				"category": category,
				"comparison_type": comparison_type,
				"macbert_column": macbert_column,
				"dictionary_column": dictionary_column,
				"pearson_corr": comparison[[macbert_column, dictionary_column]].corr().iloc[0, 1],
				"spearman_corr": comparison[[macbert_column, dictionary_column]].corr(method="spearman").iloc[0, 1],
				"rows": len(comparison),
			}
		)

dictionary_comparison = pd.DataFrame(correlation_rows)
dictionary_comparison.to_csv(DICTIONARY_COMPARISON_OUTPUT, index=False)
dictionary_comparison

# %%
fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=False)
for ax, category in zip(axes, TOOL_LABELS, strict=True):
	ax.scatter(
		comparison[f"{category}_tool_policy_count"],
		comparison[f"sum_p_{category}"],
		s=18,
		alpha=0.72,
		color=colors[category],
	)
	ax.set_title(labels[category])
	ax.set_xlabel("Dictionary count")
	ax.set_ylabel("MacBERT probability sum")
save_figure(fig, DICTIONARY_ALIGNMENT_FIG)
fig

# %% [markdown]
# ## 5. Province-Year Outliers and Boundary Samples
#
# Outlier rows are diagnostic aids for variable selection. They are not removed
# automatically.

# %%
outlier_base = macbert_intensity.copy()
for column in [
	"srdi_policy_count",
	"sum_p_supply",
	"sum_p_demand",
	"sum_p_environment",
	"sum_p_other",
	"valid_tool_policy_share",
]:
	outlier_base[f"{column}_robust_z"] = robust_zscore(outlier_base[column])

outlier_mask = pd.Series(False, index=outlier_base.index)
for column in [
	"srdi_policy_count_robust_z",
	"sum_p_supply_robust_z",
	"sum_p_demand_robust_z",
	"sum_p_environment_robust_z",
	"sum_p_other_robust_z",
]:
	outlier_mask = outlier_mask | outlier_base[column].abs().ge(3)
outlier_mask = outlier_mask | outlier_base["valid_tool_policy_share_robust_z"].abs().ge(3)

province_year_outliers = (
	outlier_base.loc[outlier_mask]
	.sort_values(
		[
			"srdi_policy_count_robust_z",
			"sum_p_supply_robust_z",
			"sum_p_demand_robust_z",
			"sum_p_environment_robust_z",
		],
		ascending=False,
	)
	.reset_index(drop=True)
)
province_year_outliers.to_csv(PROVINCE_YEAR_OUTLIERS_OUTPUT, index=False)
province_year_outliers.head(20)

# %%
dictionary_flags = dictionary_rows[
	[
		"policy_id",
		"has_supply_tool",
		"has_demand_tool",
		"has_environment_tool",
		"supply_matched_terms",
		"demand_matched_terms",
		"environment_matched_terms",
	]
].copy()

boundary_base = classified.merge(dictionary_flags, on="policy_id", how="left", validate="one_to_one")


def take_boundary(frame: pd.DataFrame, reason: str, n: int = 30) -> pd.DataFrame:
	"""Take compact boundary-review rows from a pre-sorted frame."""
	output = frame.head(n).copy()
	output.insert(0, "review_reason", reason)
	return output


fallback_boundary = boundary_base.loc[boundary_base["model_text_source"].eq("title_metadata_fallback")]
boundary_samples = pd.concat(
	[
		take_boundary(boundary_base.sort_values("p_other", ascending=False), "highest_p_other"),
		take_boundary(
			boundary_base.loc[boundary_base["max_tool_prob"].between(0.35, 0.65)].sort_values("max_tool_prob"),
			"low_confidence_tool_boundary",
		),
		take_boundary(
			boundary_base.loc[boundary_base[["p_supply", "p_demand", "p_environment"]].ge(0.70).all(axis=1)].sort_values(
				"tool_probability_sum", ascending=False
			),
			"all_three_tools_high",
		),
		take_boundary(
			boundary_base.loc[boundary_base["p_demand"].between(0.45, 0.55)].sort_values("p_demand"),
			"demand_near_threshold",
		),
		take_boundary(
			boundary_base.loc[
				(boundary_base["supply_label"].ne(boundary_base["has_supply_tool"].astype(int)))
				| (boundary_base["demand_label"].ne(boundary_base["has_demand_tool"].astype(int)))
				| (boundary_base["environment_label"].ne(boundary_base["has_environment_tool"].astype(int)))
			].sort_values("p_other", ascending=False),
			"macbert_dictionary_conflict",
		),
		take_boundary(fallback_boundary, "title_metadata_fallback", n=10),
	],
	ignore_index=True,
)

boundary_columns = [
	"review_reason",
	"policy_id",
	"province",
	"source_label_original",
	"jurisdiction_type",
	"publish_year",
	"title",
	"agency",
	"source_url",
	"model_text_source",
	"full_text_missing",
	"p_supply",
	"p_demand",
	"p_environment",
	"p_other",
	"supply_label",
	"demand_label",
	"environment_label",
	"other_label",
	"valid_tool_policy",
	"has_supply_tool",
	"has_demand_tool",
	"has_environment_tool",
	"supply_matched_terms",
	"demand_matched_terms",
	"environment_matched_terms",
]
boundary_samples = boundary_samples[boundary_columns]
boundary_samples.to_csv(BOUNDARY_SAMPLES_OUTPUT, index=False)
boundary_samples.groupby("review_reason").size().reset_index(name="records")

# %% [markdown]
# ## 6. Variable Candidates and Readiness Decision
#
# This section defines candidate roles only. The next notebook should decide the
# final selected variable table and DID-ready policy-side panel.

# %%
variable_rows = [
	{
		"variable": "srdi_policy_count",
		"source_table": "province_year_srdi_macbert_tool_intensity_v2",
		"source_column": "srdi_policy_count",
		"candidate_role": "main_control_or_volume_moderator",
		"recommended_next_step": "carry_forward",
		"definition": "Number of local SRDI-related policy records in a province-year.",
	},
	{
		"variable": "srdi_policy_count_log",
		"source_table": "province_year_srdi_macbert_tool_intensity_v2",
		"source_column": "log_srdi_policy_count_plus1",
		"candidate_role": "scaled_volume_robustness",
		"recommended_next_step": "carry_forward",
		"definition": "Log of SRDI policy count plus one.",
	},
]
for category in TOOL_LABELS:
	variable_rows.extend(
		[
			{
				"variable": f"srdi_{category}_intensity",
				"source_table": "province_year_srdi_macbert_tool_intensity_v2",
				"source_column": f"sum_p_{category}",
				"candidate_role": "main_policy_tool_intensity",
				"recommended_next_step": "main_candidate",
				"definition": f"Province-year sum of MacBERT {category} probabilities.",
			},
			{
				"variable": f"srdi_{category}_intensity_filtered",
				"source_table": "province_year_srdi_macbert_tool_intensity_v2",
				"source_column": f"filtered_sum_p_{category}",
				"candidate_role": "robustness_filtered_probability",
				"recommended_next_step": "robustness_candidate",
				"definition": f"Province-year sum of MacBERT {category} probabilities after excluding hard other rows.",
			},
			{
				"variable": f"srdi_{category}_hard_label_count",
				"source_table": "province_year_srdi_macbert_tool_intensity_v2",
				"source_column": f"{category}_label_policy_count",
				"candidate_role": "robustness_hard_label_count",
				"recommended_next_step": "robustness_candidate",
				"definition": f"Count of policies with MacBERT hard {category} label.",
			},
			{
				"variable": f"dict_{category}_policy_count",
				"source_table": "province_year_srdi_text_features_fulltext_v2",
				"source_column": f"{category}_tool_policy_count",
				"candidate_role": "robustness_dictionary_count",
				"recommended_next_step": "robustness_candidate",
				"definition": f"Transparent full-text dictionary count for {category} tool terms.",
			},
		]
	)
variable_rows.extend(
	[
		{
			"variable": "srdi_valid_tool_policy_share",
			"source_table": "province_year_srdi_macbert_tool_intensity_v2",
			"source_column": "valid_tool_policy_share",
			"candidate_role": "audit_filter_share",
			"recommended_next_step": "audit_only",
			"definition": "Share of policies retained as valid tool policies after hard-label audit rules.",
		},
		{
			"variable": "srdi_other_exclusion_count",
			"source_table": "province_year_srdi_macbert_tool_intensity_v2",
			"source_column": "other_label_policy_count",
			"candidate_role": "audit_boundary_count",
			"recommended_next_step": "audit_only",
			"definition": "Count of hard other/boundary rows.",
		},
	]
)
variable_candidates = pd.DataFrame(variable_rows)
variable_candidates.to_csv(VARIABLE_CANDIDATES_OUTPUT, index=False)
variable_candidates

# %%
raw_dictionary_corr = dictionary_comparison.loc[
	dictionary_comparison["comparison_type"].eq("raw_sum_vs_dictionary_count")
].copy()
min_raw_spearman = float(raw_dictionary_corr["spearman_corr"].min())

readiness_rows = [
	{
		"check": "artifact_completeness",
		"status": status_from_bool(len(classified) == 3989 and len(macbert_intensity) == 186),
		"evidence": f"classified={len(classified)}, province_year={len(macbert_intensity)}",
		"decision_implication": "Required before variable selection.",
	},
	{
		"check": "panel_balance",
		"status": status_from_bool(panel_is_balanced),
		"evidence": f"years={list(map(int, sorted(macbert_intensity['publish_year'].unique())))}; provinces={macbert_intensity['province'].nunique()}",
		"decision_implication": "Required for a 31 province x 2019-2024 policy-side panel.",
	},
	{
		"check": "probability_validity",
		"status": status_from_bool(probabilities_in_range),
		"evidence": f"probabilities_in_range={probabilities_in_range}",
		"decision_implication": "Required for probability-sum intensity variables.",
	},
	{
		"check": "fallback_and_jurisdiction_audit",
		"status": status_from_bool(fallback_rows == 1 and jurisdiction_review_rows == 0),
		"evidence": f"fallback_rows={fallback_rows}; jurisdiction_review_candidate_rows={jurisdiction_review_rows}",
		"decision_implication": "The lone missing-full-text row should remain audited, not dropped.",
	},
	{
		"check": "other_exclusion_rate",
		"status": "pass" if other_label_share <= 0.10 else "needs_review",
		"evidence": f"other_label_share={other_label_share:.3f}",
		"decision_implication": "`other` remains an audit/filter variable, not a substantive policy-tool dimension.",
	},
	{
		"check": "heldout_model_quality",
		"status": "pass" if float(test_metrics["macro_f1"]) >= 0.70 else "needs_review",
		"evidence": f"test_micro_f1={test_metrics['micro_f1']:.3f}; test_macro_f1={test_metrics['macro_f1']:.3f}",
		"decision_implication": "Supports using the frozen v1 checkpoint for v2 policy-side variables.",
	},
	{
		"check": "dictionary_alignment",
		"status": "pass" if min_raw_spearman >= 0.50 else "needs_review",
		"evidence": f"min raw-sum vs dictionary-count Spearman correlation={min_raw_spearman:.3f}",
		"decision_implication": "Dictionary features can be retained as robustness variables.",
	},
	{
		"check": "current_decision",
		"status": "ready_for_variable_selection_v2",
		"evidence": "Use MacBERT probability sums as main candidates; keep filtered sums, hard labels, dictionary counts, and audit shares for robustness/audit.",
		"decision_implication": "Proceed to v2 policy-text variable selection, then final policy-side panel.",
	},
]
readiness_decision = pd.DataFrame(readiness_rows)
readiness_decision.to_csv(VARIABLE_READINESS_OUTPUT, index=False)
readiness_decision

# %% [markdown]
# ## 7. Paper-Facing Interpretation Notes

# %%
interpretation_notes = pd.DataFrame(
	[
		{
			"topic": "v2_window",
			"note": "The v2 MacBERT prediction universe covers 2019-2024, aligning the policy-side panel with the DID analysis window.",
			"evidence": f"row-level years={';'.join(map(str, sorted(classified['publish_year'].unique())))}; province-year rows={len(macbert_intensity)}.",
		},
		{
			"topic": "model_reuse",
			"note": "The v2 path reuses the frozen v1 MacBERT checkpoint, so changes come from the corrected corpus window and 2019 supplement rather than retraining.",
			"evidence": f"test macro-F1 from checkpoint QA={float(test_metrics['macro_f1']):.3f}.",
		},
		{
			"topic": "fallback_audit",
			"note": "The one missing-full-text row is retained and marked through model_text_source, preserving row-level auditability.",
			"evidence": f"missing_full_text_rows={missing_full_text_rows}; model_text_fallback_rows={fallback_rows}.",
		},
		{
			"topic": "main_variable_candidates",
			"note": "Continuous MacBERT probability sums are the preferred main policy-tool intensity candidates because they combine policy count and model-estimated tool content.",
			"evidence": "Candidate variables: srdi_supply_intensity, srdi_demand_intensity, srdi_environment_intensity.",
		},
		{
			"topic": "robustness_variables",
			"note": "Filtered probability sums, hard-label counts, and transparent dictionary counts should be carried as robustness candidates.",
			"evidence": f"dictionary raw-sum alignment minimum Spearman correlation={min_raw_spearman:.3f}.",
		},
		{
			"topic": "scope_boundary",
			"note": "This notebook stops before final policy-side DID-ready panel construction and contains no enterprise data or DID estimates.",
			"evidence": "Next step is variable selection and policy-side panel assembly only.",
		},
	]
)
interpretation_notes.to_csv(INTERPRETATION_NOTES_OUTPUT, index=False)
interpretation_notes

# %% [markdown]
# ## 8. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "qa_summary", "path": QA_SUMMARY_OUTPUT, "exists": QA_SUMMARY_OUTPUT.exists()},
		{"artifact": "probability_by_year", "path": PROBABILITY_BY_YEAR_OUTPUT, "exists": PROBABILITY_BY_YEAR_OUTPUT.exists()},
		{"artifact": "probability_by_province", "path": PROBABILITY_BY_PROVINCE_OUTPUT, "exists": PROBABILITY_BY_PROVINCE_OUTPUT.exists()},
		{"artifact": "tool_structure_by_year", "path": TOOL_STRUCTURE_BY_YEAR_OUTPUT, "exists": TOOL_STRUCTURE_BY_YEAR_OUTPUT.exists()},
		{"artifact": "dictionary_comparison", "path": DICTIONARY_COMPARISON_OUTPUT, "exists": DICTIONARY_COMPARISON_OUTPUT.exists()},
		{"artifact": "province_year_outliers", "path": PROVINCE_YEAR_OUTLIERS_OUTPUT, "exists": PROVINCE_YEAR_OUTLIERS_OUTPUT.exists()},
		{"artifact": "boundary_samples", "path": BOUNDARY_SAMPLES_OUTPUT, "exists": BOUNDARY_SAMPLES_OUTPUT.exists()},
		{"artifact": "variable_candidates", "path": VARIABLE_CANDIDATES_OUTPUT, "exists": VARIABLE_CANDIDATES_OUTPUT.exists()},
		{"artifact": "variable_readiness", "path": VARIABLE_READINESS_OUTPUT, "exists": VARIABLE_READINESS_OUTPUT.exists()},
		{"artifact": "interpretation_notes", "path": INTERPRETATION_NOTES_OUTPUT, "exists": INTERPRETATION_NOTES_OUTPUT.exists()},
		{"artifact": "probability_by_year_figure", "path": PROBABILITY_BY_YEAR_FIG, "exists": PROBABILITY_BY_YEAR_FIG.exists()},
		{"artifact": "tool_intensity_by_year_figure", "path": TOOL_INTENSITY_BY_YEAR_FIG, "exists": TOOL_INTENSITY_BY_YEAR_FIG.exists()},
		{"artifact": "dictionary_alignment_figure", "path": DICTIONARY_ALIGNMENT_FIG, "exists": DICTIONARY_ALIGNMENT_FIG.exists()},
		{"artifact": "other_share_by_province_figure", "path": OTHER_SHARE_BY_PROVINCE_FIG, "exists": OTHER_SHARE_BY_PROVINCE_FIG.exists()},
	]
)
output_checklist
