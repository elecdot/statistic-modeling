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
# # Manual SRDI Policy-Intensity Variable Selection v2
#
# This notebook fixes the v2 policy-text variable口径 for the corrected
# 2019-2024 policy-side panel.
#
# It reads the completed v2 MacBERT province-year intensity table, joins the v2
# full-text dictionary robustness features, checks the v2 MacBERT readiness
# decision, and writes a compact province-year policy-text variable table.
#
# Scope boundary: this notebook does not add DID merge keys, z-scores,
# enterprise data, or DID estimates. The final policy-side DID-ready panel is a
# later step.

# %%
from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

MACBERT_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v2.csv"
DICTIONARY_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v2.csv"
VARIABLE_CANDIDATES_PATH = ROOT / "outputs" / "manual_srdi_macbert_variable_candidates_v2.csv"
MACBERT_READINESS_PATH = ROOT / "outputs" / "manual_srdi_macbert_variable_readiness_decision_v2.csv"

POLICY_TEXT_VARIABLES_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v2.csv"
VARIABLE_SELECTION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_selection_v2.csv"
VARIABLE_CORRELATION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_correlations_v2.csv"
VARIABLE_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_summary_v2.csv"
VARIABLE_DECISION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_decision_v2.csv"

YEARS = list(range(2019, 2025))
TOOL_LABELS = ["supply", "demand", "environment"]

# %% [markdown]
# ## 1. Load Inputs and Gate on Readiness

# %%
macbert = pd.read_csv(MACBERT_INTENSITY_PATH)
dictionary = pd.read_csv(DICTIONARY_INTENSITY_PATH)
variable_candidates = pd.read_csv(VARIABLE_CANDIDATES_PATH)
readiness = pd.read_csv(MACBERT_READINESS_PATH).set_index("check")

required_readiness_checks = [
	"artifact_completeness",
	"panel_balance",
	"probability_validity",
	"fallback_and_jurisdiction_audit",
	"other_exclusion_rate",
	"heldout_model_quality",
	"dictionary_alignment",
]
failed_checks = readiness.loc[required_readiness_checks].query("status != 'pass'")
if not failed_checks.empty:
	raise ValueError(f"v2 MacBERT readiness checks are not all pass: {failed_checks.index.tolist()}")
if readiness.loc["current_decision", "status"] != "ready_for_variable_selection_v2":
	raise ValueError("v2 MacBERT readiness decision is not ready_for_variable_selection_v2")

load_checks = pd.DataFrame(
	[
		{"artifact": "macbert_tool_intensity_v2", "rows": len(macbert), "columns": macbert.shape[1]},
		{"artifact": "dictionary_fulltext_intensity_v2", "rows": len(dictionary), "columns": dictionary.shape[1]},
		{"artifact": "variable_candidates_v2", "rows": len(variable_candidates), "columns": variable_candidates.shape[1]},
		{"artifact": "macbert_readiness_v2", "rows": len(readiness), "columns": readiness.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Construct the v2 Policy-Text Variable Table
#
# Main variables:
#
# - `srdi_policy_count`: annual local SRDI-related policy count;
# - `srdi_policy_count_log`: `log(count + 1)`;
# - `srdi_supply_intensity`, `srdi_demand_intensity`,
#   `srdi_environment_intensity`: province-year sums of MacBERT probabilities.
#
# Robustness variables retain filtered probability sums, hard-label counts,
# high-confidence counts, and transparent dictionary counts/shares.

# %%
policy_variables = macbert[
	[
		"province",
		"publish_year",
		"srdi_policy_count",
		"log_srdi_policy_count_plus1",
		"macbert_policy_records",
		"valid_tool_policy_count",
		"valid_tool_policy_share",
		"other_label_policy_count",
		"sum_p_supply",
		"sum_p_demand",
		"sum_p_environment",
		"sum_p_other",
		"avg_p_supply",
		"avg_p_demand",
		"avg_p_environment",
		"avg_p_other",
		"supply_probability_share",
		"demand_probability_share",
		"environment_probability_share",
		"filtered_sum_p_supply",
		"filtered_sum_p_demand",
		"filtered_sum_p_environment",
		"filtered_sum_p_other",
		"filtered_supply_probability_share",
		"filtered_demand_probability_share",
		"filtered_environment_probability_share",
		"filtered_avg_p_supply",
		"filtered_avg_p_demand",
		"filtered_avg_p_environment",
		"supply_label_policy_count",
		"demand_label_policy_count",
		"environment_label_policy_count",
		"high_confidence_supply_policy_count",
		"high_confidence_demand_policy_count",
		"high_confidence_environment_policy_count",
	]
].copy()

policy_variables = policy_variables.rename(
	columns={
		"log_srdi_policy_count_plus1": "srdi_policy_count_log",
		"macbert_policy_records": "srdi_macbert_policy_records",
		"valid_tool_policy_count": "srdi_valid_tool_policy_count",
		"valid_tool_policy_share": "srdi_valid_tool_policy_share",
		"other_label_policy_count": "srdi_other_exclusion_count",
		"sum_p_supply": "srdi_supply_intensity",
		"sum_p_demand": "srdi_demand_intensity",
		"sum_p_environment": "srdi_environment_intensity",
		"sum_p_other": "srdi_other_probability_sum",
		"avg_p_supply": "srdi_supply_avg_probability",
		"avg_p_demand": "srdi_demand_avg_probability",
		"avg_p_environment": "srdi_environment_avg_probability",
		"avg_p_other": "srdi_other_avg_probability",
		"supply_probability_share": "srdi_supply_probability_share",
		"demand_probability_share": "srdi_demand_probability_share",
		"environment_probability_share": "srdi_environment_probability_share",
		"filtered_sum_p_supply": "srdi_supply_intensity_filtered",
		"filtered_sum_p_demand": "srdi_demand_intensity_filtered",
		"filtered_sum_p_environment": "srdi_environment_intensity_filtered",
		"filtered_sum_p_other": "srdi_other_probability_sum_filtered",
		"filtered_supply_probability_share": "srdi_supply_probability_share_filtered",
		"filtered_demand_probability_share": "srdi_demand_probability_share_filtered",
		"filtered_environment_probability_share": "srdi_environment_probability_share_filtered",
		"filtered_avg_p_supply": "srdi_supply_avg_probability_filtered",
		"filtered_avg_p_demand": "srdi_demand_avg_probability_filtered",
		"filtered_avg_p_environment": "srdi_environment_avg_probability_filtered",
		"supply_label_policy_count": "srdi_supply_hard_label_count",
		"demand_label_policy_count": "srdi_demand_hard_label_count",
		"environment_label_policy_count": "srdi_environment_hard_label_count",
		"high_confidence_supply_policy_count": "srdi_supply_high_confidence_count",
		"high_confidence_demand_policy_count": "srdi_demand_high_confidence_count",
		"high_confidence_environment_policy_count": "srdi_environment_high_confidence_count",
	}
)

policy_variables["srdi_total_tool_intensity"] = (
	policy_variables["srdi_supply_intensity"]
	+ policy_variables["srdi_demand_intensity"]
	+ policy_variables["srdi_environment_intensity"]
)
policy_variables["srdi_total_tool_intensity_filtered"] = (
	policy_variables["srdi_supply_intensity_filtered"]
	+ policy_variables["srdi_demand_intensity_filtered"]
	+ policy_variables["srdi_environment_intensity_filtered"]
)
policy_variables["srdi_total_hard_label_count"] = (
	policy_variables["srdi_supply_hard_label_count"]
	+ policy_variables["srdi_demand_hard_label_count"]
	+ policy_variables["srdi_environment_hard_label_count"]
)
policy_variables["srdi_total_high_confidence_count"] = (
	policy_variables["srdi_supply_high_confidence_count"]
	+ policy_variables["srdi_demand_high_confidence_count"]
	+ policy_variables["srdi_environment_high_confidence_count"]
)

dictionary_rename = dictionary[
	[
		"province",
		"publish_year",
		"supply_tool_policy_count",
		"demand_tool_policy_count",
		"environment_tool_policy_count",
		"any_tool_policy_count",
		"supply_tool_policy_share",
		"demand_tool_policy_share",
		"environment_tool_policy_share",
		"any_tool_policy_share",
		"missing_full_text_count",
		"fallback_full_text_for_model_count",
		"full_text_missing_policy_count",
		"full_text_fallback_policy_count",
		"missing_agency_count",
		"unique_agency_count",
		"jurisdiction_review_candidate_count",
		"avg_full_text_len",
		"avg_text_surface_len",
		"avg_tool_category_count",
	]
].rename(
	columns={
		"supply_tool_policy_count": "dict_supply_policy_count",
		"demand_tool_policy_count": "dict_demand_policy_count",
		"environment_tool_policy_count": "dict_environment_policy_count",
		"any_tool_policy_count": "dict_any_tool_policy_count",
		"supply_tool_policy_share": "dict_supply_policy_share",
		"demand_tool_policy_share": "dict_demand_policy_share",
		"environment_tool_policy_share": "dict_environment_policy_share",
		"any_tool_policy_share": "dict_any_tool_policy_share",
		"missing_full_text_count": "audit_missing_full_text_count",
		"fallback_full_text_for_model_count": "audit_fallback_full_text_for_model_count",
		"full_text_missing_policy_count": "audit_full_text_missing_policy_count",
		"full_text_fallback_policy_count": "audit_full_text_fallback_policy_count",
		"missing_agency_count": "audit_missing_agency_count",
		"unique_agency_count": "audit_unique_agency_count",
		"jurisdiction_review_candidate_count": "audit_jurisdiction_review_candidate_count",
		"avg_full_text_len": "audit_avg_full_text_len",
		"avg_text_surface_len": "audit_avg_text_surface_len",
		"avg_tool_category_count": "dict_avg_tool_category_count",
	}
)

policy_variables = policy_variables.merge(
	dictionary_rename,
	on=["province", "publish_year"],
	how="left",
	validate="one_to_one",
)
policy_variables = policy_variables.sort_values(["province", "publish_year"]).reset_index(drop=True)

if len(policy_variables) != 186:
	raise ValueError(f"unexpected v2 policy variable rows: {len(policy_variables)}")
if policy_variables["province"].nunique() != 31:
	raise ValueError("v2 policy variables must contain 31 local province units")
if set(policy_variables["publish_year"]) != set(YEARS):
	raise ValueError(f"unexpected v2 years: {sorted(policy_variables['publish_year'].unique())}")
if policy_variables[["province", "publish_year"]].duplicated().sum() != 0:
	raise ValueError("v2 policy variables contain duplicated province-year rows")
if "central" in set(policy_variables["province"]):
	raise ValueError("v2 province-year policy variables must exclude central")

required_nonnegative = [
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
if policy_variables[required_nonnegative].isna().any().any():
	raise ValueError("v2 policy variables contain missing required values")
if not policy_variables[required_nonnegative].ge(0).all().all():
	raise ValueError("v2 policy variables contain negative required values")

policy_variables.to_csv(POLICY_TEXT_VARIABLES_OUTPUT, index=False)
policy_variables.head()

# %% [markdown]
# ## 3. Variable Selection Table

# %%
variable_rows = [
	{
		"variable": "srdi_policy_count",
		"role": "baseline_policy_volume",
		"source_column": "srdi_policy_count",
		"recommended_use": "main_control_or_moderator",
		"definition": "Number of local SRDI-related policies in a province-year.",
		"paper_note": "Captures policy-volume intensity independent of policy-tool mix.",
	},
	{
		"variable": "srdi_policy_count_log",
		"role": "baseline_policy_volume",
		"source_column": "log_srdi_policy_count_plus1",
		"recommended_use": "robustness_or_scaled_version",
		"definition": "Log of SRDI policy count plus one.",
		"paper_note": "Use when count distribution is skewed.",
	},
	{
		"variable": "srdi_supply_intensity",
		"role": "main_policy_tool_intensity",
		"source_column": "sum_p_supply",
		"recommended_use": "main",
		"definition": "Province-year sum of MacBERT supply-side probabilities.",
		"paper_note": "Main supply-side policy-tool intensity.",
	},
	{
		"variable": "srdi_demand_intensity",
		"role": "main_policy_tool_intensity",
		"source_column": "sum_p_demand",
		"recommended_use": "main",
		"definition": "Province-year sum of MacBERT demand-side probabilities.",
		"paper_note": "Main demand-side policy-tool intensity; retain threshold and dictionary robustness because demand is the conceptually narrowest tool class.",
	},
	{
		"variable": "srdi_environment_intensity",
		"role": "main_policy_tool_intensity",
		"source_column": "sum_p_environment",
		"recommended_use": "main",
		"definition": "Province-year sum of MacBERT environment-side probabilities.",
		"paper_note": "Main environmental policy-tool intensity.",
	},
	{
		"variable": "srdi_total_tool_intensity",
		"role": "aggregate_policy_tool_intensity",
		"source_column": "sum_p_supply + sum_p_demand + sum_p_environment",
		"recommended_use": "summary_or_auxiliary",
		"definition": "Sum of the three MacBERT policy-tool probability intensities.",
		"paper_note": "Use as a descriptive aggregate or auxiliary robustness variable, not as a replacement for tool-specific variables.",
	},
]

for category in TOOL_LABELS:
	variable_rows.extend(
		[
			{
				"variable": f"srdi_{category}_intensity_filtered",
				"role": "robustness_filtered_probability",
				"source_column": f"filtered_sum_p_{category}",
				"recommended_use": "robustness",
				"definition": f"MacBERT {category} probability sum after excluding hard other rows.",
				"paper_note": "Checks sensitivity to excluding non-substantive or boundary texts.",
			},
			{
				"variable": f"srdi_{category}_hard_label_count",
				"role": "robustness_hard_label_count",
				"source_column": f"{category}_label_policy_count",
				"recommended_use": "robustness",
				"definition": f"Count of policies with MacBERT hard {category} label.",
				"paper_note": "Threshold-based alternative to continuous probability intensity.",
			},
			{
				"variable": f"srdi_{category}_high_confidence_count",
				"role": "robustness_high_confidence_count",
				"source_column": f"high_confidence_{category}_policy_count",
				"recommended_use": "robustness",
				"definition": f"Count of policies with MacBERT {category} probability at least 0.75.",
				"paper_note": "High-confidence threshold alternative for stricter policy-tool definitions.",
			},
			{
				"variable": f"dict_{category}_policy_count",
				"role": "robustness_dictionary_count",
				"source_column": f"{category}_tool_policy_count",
				"recommended_use": "robustness",
				"definition": f"Full-text dictionary count of policies with {category} keyword hits.",
				"paper_note": "Transparent dictionary baseline, not final row-level label.",
			},
			{
				"variable": f"dict_{category}_policy_share",
				"role": "robustness_dictionary_share",
				"source_column": f"{category}_tool_policy_share",
				"recommended_use": "robustness",
				"definition": f"Share of policies with full-text dictionary {category} keyword hits.",
				"paper_note": "Transparent share-based dictionary robustness variable.",
			},
		]
	)

variable_rows.extend(
	[
		{
			"variable": "srdi_valid_tool_policy_share",
			"role": "audit_filter_share",
			"source_column": "valid_tool_policy_share",
			"recommended_use": "audit",
			"definition": "Share of policies retained as substantive tool policies by hard-label filter.",
			"paper_note": "Use for QA, not as a main DID explanatory variable.",
		},
		{
			"variable": "srdi_other_exclusion_count",
			"role": "audit_exclusion_count",
			"source_column": "other_label_policy_count",
			"recommended_use": "audit",
			"definition": "Count of policies marked as other/exclusion by MacBERT hard rule.",
			"paper_note": "Use for data-quality discussion and boundary checks.",
		},
		{
			"variable": "audit_fallback_full_text_for_model_count",
			"role": "audit_fallback_count",
			"source_column": "fallback_full_text_for_model_count",
			"recommended_use": "audit",
			"definition": "Count of policies whose model input used title/metadata fallback.",
			"paper_note": "The v2 corpus has one fallback row; keep this visible in final handoff QA.",
		},
		{
			"variable": "audit_jurisdiction_review_candidate_count",
			"role": "audit_jurisdiction_count",
			"source_column": "jurisdiction_review_candidate_count",
			"recommended_use": "audit",
			"definition": "Count of policies still marked for jurisdiction review in the province-year.",
			"paper_note": "Should remain zero after reviewed v2 overrides.",
		},
	]
)

variable_selection = pd.DataFrame(variable_rows)
variable_selection.to_csv(VARIABLE_SELECTION_OUTPUT, index=False)
variable_selection

# %% [markdown]
# ## 4. Correlation and Redundancy Diagnostics
#
# Probability-sum variables are expected to correlate with policy volume. The
# final DID specification should therefore keep volume controls and use
# robustness variables to check threshold and dictionary alternatives.

# %%
selected_corr_columns = [
	"srdi_policy_count",
	"srdi_policy_count_log",
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
	"srdi_total_tool_intensity",
	"srdi_supply_intensity_filtered",
	"srdi_demand_intensity_filtered",
	"srdi_environment_intensity_filtered",
	"srdi_supply_hard_label_count",
	"srdi_demand_hard_label_count",
	"srdi_environment_hard_label_count",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
]

correlation_rows = []
for left, right in combinations(selected_corr_columns, 2):
	pearson_corr = policy_variables[[left, right]].corr().iloc[0, 1]
	spearman_corr = policy_variables[[left, right]].corr(method="spearman").iloc[0, 1]
	correlation_rows.append(
		{
			"left_variable": left,
			"right_variable": right,
			"pearson_corr": pearson_corr,
			"spearman_corr": spearman_corr,
			"abs_pearson_corr": abs(pearson_corr),
			"rows": len(policy_variables),
		}
	)
variable_correlations = pd.DataFrame(correlation_rows).sort_values("abs_pearson_corr", ascending=False)
variable_correlations.to_csv(VARIABLE_CORRELATION_OUTPUT, index=False)
variable_correlations.head(20)

# %% [markdown]
# ## 5. Variable Summary

# %%
summary_columns = [
	"srdi_policy_count",
	"srdi_policy_count_log",
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
	"srdi_total_tool_intensity",
	"srdi_supply_intensity_filtered",
	"srdi_demand_intensity_filtered",
	"srdi_environment_intensity_filtered",
	"srdi_valid_tool_policy_share",
	"srdi_other_exclusion_count",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
	"audit_fallback_full_text_for_model_count",
	"audit_jurisdiction_review_candidate_count",
]
summary_rows = []
for column in summary_columns:
	series = policy_variables[column]
	summary_rows.append(
		{
			"variable": column,
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
variable_summary = pd.DataFrame(summary_rows)
variable_summary.to_csv(VARIABLE_SUMMARY_OUTPUT, index=False)
variable_summary

# %% [markdown]
# ## 6. Final v2 Variable Decision

# %%
main_candidate_set = set(variable_candidates.loc[variable_candidates["recommended_next_step"].eq("main_candidate"), "variable"])
expected_main_variables = {
	"srdi_supply_intensity",
	"srdi_demand_intensity",
	"srdi_environment_intensity",
}
if main_candidate_set != expected_main_variables:
	raise ValueError(f"unexpected v2 main candidates: {sorted(main_candidate_set)}")

decision_rows = [
	{
		"decision_area": "main_policy_tool_variables",
		"decision": "Use continuous MacBERT probability-sum variables as the v2 main policy-tool intensity口径.",
		"variables": "srdi_supply_intensity;srdi_demand_intensity;srdi_environment_intensity",
		"rationale": "They preserve model confidence and policy volume, avoid arbitrary hard-threshold loss, and passed v2 prediction-readiness checks.",
	},
	{
		"decision_area": "baseline_policy_volume",
		"decision": "Keep SRDI policy count variables as volume controls or alternative intensity measures.",
		"variables": "srdi_policy_count;srdi_policy_count_log",
		"rationale": "They separate policy quantity from policy-tool composition.",
	},
	{
		"decision_area": "robustness_variables",
		"decision": "Use filtered probability sums, hard-label counts, high-confidence counts, dictionary counts, and dictionary shares for robustness checks.",
		"variables": "srdi_*_intensity_filtered;srdi_*_hard_label_count;srdi_*_high_confidence_count;dict_*_policy_count;dict_*_policy_share",
		"rationale": "They test sensitivity to other exclusion, thresholding, stricter confidence thresholds, and transparent keyword proxies.",
	},
	{
		"decision_area": "audit_variables",
		"decision": "Carry valid-tool share, other-exclusion count, fallback count, and jurisdiction-review count as audit-only variables.",
		"variables": "srdi_valid_tool_policy_share;srdi_other_exclusion_count;audit_fallback_full_text_for_model_count;audit_jurisdiction_review_candidate_count",
		"rationale": "These fields document data quality and model-boundary handling but should not be interpreted as substantive policy tools.",
	},
	{
		"decision_area": "v2_window",
		"decision": "Use the corrected 2019-2024 window.",
		"variables": "publish_year=2019;2020;2021;2022;2023;2024",
		"rationale": "The old 2020-2025 window is not the correct DID policy-side window.",
	},
	{
		"decision_area": "next_step",
		"decision": "The v2 policy-text variable table is ready for final policy-side panel construction.",
		"variables": "data/processed/province_year_srdi_policy_text_variables_v2.csv",
		"rationale": "The table is balanced at 31 local provinces x 2019-2024, excludes central policies from province-year variation, and preserves robustness/audit fields.",
	},
]
variable_decision = pd.DataFrame(decision_rows)
variable_decision.to_csv(VARIABLE_DECISION_OUTPUT, index=False)
variable_decision

# %% [markdown]
# ## 7. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "policy_text_variables_v2", "path": POLICY_TEXT_VARIABLES_OUTPUT, "rows": len(policy_variables), "exists": POLICY_TEXT_VARIABLES_OUTPUT.exists()},
		{"artifact": "variable_selection_v2", "path": VARIABLE_SELECTION_OUTPUT, "rows": len(variable_selection), "exists": VARIABLE_SELECTION_OUTPUT.exists()},
		{"artifact": "variable_correlations_v2", "path": VARIABLE_CORRELATION_OUTPUT, "rows": len(variable_correlations), "exists": VARIABLE_CORRELATION_OUTPUT.exists()},
		{"artifact": "variable_summary_v2", "path": VARIABLE_SUMMARY_OUTPUT, "rows": len(variable_summary), "exists": VARIABLE_SUMMARY_OUTPUT.exists()},
		{"artifact": "variable_decision_v2", "path": VARIABLE_DECISION_OUTPUT, "rows": len(variable_decision), "exists": VARIABLE_DECISION_OUTPUT.exists()},
	]
)
output_checklist
