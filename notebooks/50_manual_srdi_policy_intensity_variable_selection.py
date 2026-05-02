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
# # Manual SRDI Policy-Intensity Variable Selection
#
# This notebook fixes the main policy-text variable口径 for downstream DID.
#
# It does not merge firm panel data. It selects and renames province-year SRDI
# policy-count and MacBERT policy-tool variables into a compact DID-ready table,
# while documenting robustness and audit alternatives.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

MACBERT_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v1.csv"
DICTIONARY_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv"
MACBERT_QA_DECISION_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_decision_table_v1.csv"

DID_READY_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v1.csv"
VARIABLE_SELECTION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_selection_v1.csv"
VARIABLE_CORRELATION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_correlations_v1.csv"
VARIABLE_DECISION_OUTPUT = OUTPUT_DIR / "manual_srdi_policy_intensity_variable_decision_v1.csv"

YEARS = list(range(2020, 2026))
TOOL_LABELS = ["supply", "demand", "environment"]

# %% [markdown]
# ## 1. Load Inputs

# %%
macbert = pd.read_csv(MACBERT_INTENSITY_PATH)
dictionary = pd.read_csv(DICTIONARY_INTENSITY_PATH)
qa_decision = pd.read_csv(MACBERT_QA_DECISION_PATH)

load_checks = pd.DataFrame(
	[
		{"artifact": "macbert_tool_intensity", "rows": len(macbert), "columns": macbert.shape[1]},
		{"artifact": "dictionary_fulltext_intensity", "rows": len(dictionary), "columns": dictionary.shape[1]},
		{"artifact": "macbert_qa_decision", "rows": len(qa_decision), "columns": qa_decision.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Construct DID-Ready Variable Table
#
# Main variables:
#
# - `srdi_policy_count`: annual SRDI-related policy record count;
# - `srdi_policy_count_log`: log count, already using `log(count + 1)`;
# - `srdi_supply_intensity`, `srdi_demand_intensity`,
#   `srdi_environment_intensity`: MacBERT probability sums.
#
# Rationale: probability sums capture both policy volume and model-estimated
# policy-tool content. A province-year with more policies and higher tool
# probabilities should have larger intensity.

# %%
did_ready = macbert[
	[
		"province",
		"publish_year",
		"srdi_policy_count",
		"log_srdi_policy_count_plus1",
		"valid_tool_policy_count",
		"valid_tool_policy_share",
		"sum_p_supply",
		"sum_p_demand",
		"sum_p_environment",
		"avg_p_supply",
		"avg_p_demand",
		"avg_p_environment",
		"supply_probability_share",
		"demand_probability_share",
		"environment_probability_share",
		"filtered_sum_p_supply",
		"filtered_sum_p_demand",
		"filtered_sum_p_environment",
		"supply_label_policy_count",
		"demand_label_policy_count",
		"environment_label_policy_count",
		"other_label_policy_count",
	]
].copy()

did_ready = did_ready.rename(
	columns={
		"log_srdi_policy_count_plus1": "srdi_policy_count_log",
		"valid_tool_policy_count": "srdi_valid_tool_policy_count",
		"valid_tool_policy_share": "srdi_valid_tool_policy_share",
		"sum_p_supply": "srdi_supply_intensity",
		"sum_p_demand": "srdi_demand_intensity",
		"sum_p_environment": "srdi_environment_intensity",
		"avg_p_supply": "srdi_supply_avg_probability",
		"avg_p_demand": "srdi_demand_avg_probability",
		"avg_p_environment": "srdi_environment_avg_probability",
		"supply_probability_share": "srdi_supply_probability_share",
		"demand_probability_share": "srdi_demand_probability_share",
		"environment_probability_share": "srdi_environment_probability_share",
		"filtered_sum_p_supply": "srdi_supply_intensity_filtered",
		"filtered_sum_p_demand": "srdi_demand_intensity_filtered",
		"filtered_sum_p_environment": "srdi_environment_intensity_filtered",
		"supply_label_policy_count": "srdi_supply_hard_label_count",
		"demand_label_policy_count": "srdi_demand_hard_label_count",
		"environment_label_policy_count": "srdi_environment_hard_label_count",
		"other_label_policy_count": "srdi_other_exclusion_count",
	}
)

did_ready["srdi_total_tool_intensity"] = (
	did_ready["srdi_supply_intensity"]
	+ did_ready["srdi_demand_intensity"]
	+ did_ready["srdi_environment_intensity"]
)
did_ready["srdi_total_tool_intensity_filtered"] = (
	did_ready["srdi_supply_intensity_filtered"]
	+ did_ready["srdi_demand_intensity_filtered"]
	+ did_ready["srdi_environment_intensity_filtered"]
)

dictionary_rename = dictionary[
	[
		"province",
		"publish_year",
		"supply_tool_policy_count",
		"demand_tool_policy_count",
		"environment_tool_policy_count",
		"supply_tool_policy_share",
		"demand_tool_policy_share",
		"environment_tool_policy_share",
	]
].rename(
	columns={
		"supply_tool_policy_count": "dict_supply_policy_count",
		"demand_tool_policy_count": "dict_demand_policy_count",
		"environment_tool_policy_count": "dict_environment_policy_count",
		"supply_tool_policy_share": "dict_supply_policy_share",
		"demand_tool_policy_share": "dict_demand_policy_share",
		"environment_tool_policy_share": "dict_environment_policy_share",
	}
)
did_ready = did_ready.merge(dictionary_rename, on=["province", "publish_year"], how="left", validate="one_to_one")
did_ready = did_ready.sort_values(["province", "publish_year"]).reset_index(drop=True)
assert len(did_ready) == 186
assert did_ready["province"].nunique() == 31
assert set(did_ready["publish_year"]) == set(YEARS)
assert did_ready[["province", "publish_year"]].duplicated().sum() == 0
did_ready.to_csv(DID_READY_OUTPUT, index=False)
did_ready.head()

# %% [markdown]
# ## 3. Variable Selection Table

# %%
variable_rows = [
	{
		"variable": "srdi_policy_count",
		"role": "baseline_policy_volume",
		"source_column": "srdi_policy_count",
		"recommended_use": "main_control_or_moderator",
		"definition": "Number of SRDI-related policies in a province-year.",
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
		"paper_note": "Main demand-side policy-tool intensity; interpret with threshold robustness because demand precision is lower than recall.",
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
		"paper_note": "Use when a single overall text-policy intensity variable is needed.",
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
				"variable": f"dict_{category}_policy_count",
				"role": "robustness_dictionary_count",
				"source_column": f"{category}_tool_policy_count",
				"recommended_use": "robustness",
				"definition": f"Full-text dictionary count of policies with {category} keyword hits.",
				"paper_note": "Transparent dictionary baseline, not final row-level label.",
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
	]
)

variable_selection = pd.DataFrame(variable_rows)
variable_selection.to_csv(VARIABLE_SELECTION_OUTPUT, index=False)
variable_selection

# %% [markdown]
# ## 4. Correlation And Redundancy Diagnostics
#
# The three tool variables are expected to be positively correlated with policy
# volume because they are probability sums. This diagnostic is kept to support
# the later DID specification choice: include policy volume controls and report
# robustness using hard labels, filtered sums, and dictionary proxies.

# %%
selected_corr_columns = [
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

corr = did_ready[selected_corr_columns].corr()
correlation_rows = []
for left in selected_corr_columns:
	for right in selected_corr_columns:
		if left < right:
			correlation_rows.append({"left_variable": left, "right_variable": right, "pearson_corr": corr.loc[left, right]})
variable_correlations = pd.DataFrame(correlation_rows).sort_values("pearson_corr", ascending=False)
variable_correlations.to_csv(VARIABLE_CORRELATION_OUTPUT, index=False)
variable_correlations.head(15)

# %% [markdown]
# ## 5. Final Variable Decision

# %%
decision_rows = [
	{
		"decision_area": "main_policy_tool_variables",
		"decision": "Use continuous MacBERT probability-sum variables as the main policy-tool intensity口径.",
		"variables": "srdi_supply_intensity;srdi_demand_intensity;srdi_environment_intensity",
		"rationale": "They preserve model confidence and policy volume, avoid arbitrary hard-threshold loss, and are validated by full-corpus QA.",
	},
	{
		"decision_area": "baseline_policy_volume",
		"decision": "Keep SRDI policy count variables as volume controls or alternative intensity measures.",
		"variables": "srdi_policy_count;srdi_policy_count_log",
		"rationale": "They separate policy quantity from policy-tool composition.",
	},
	{
		"decision_area": "robustness_variables",
		"decision": "Use filtered probability sums, hard-label counts, and dictionary counts for robustness checks.",
		"variables": "srdi_*_intensity_filtered;srdi_*_hard_label_count;dict_*_policy_count",
		"rationale": "They test sensitivity to other exclusion, thresholding, and transparent keyword proxies.",
	},
	{
		"decision_area": "excluded_from_main_interpretation",
		"decision": "`other` is an audit/filter label, not a policy-tool intensity dimension.",
		"variables": "srdi_other_exclusion_count;srdi_valid_tool_policy_share",
		"rationale": "The other label is a boundary/exclusion class with lower model F1 and should not be treated as a substantive policy tool.",
	},
	{
		"decision_area": "did_handoff_status",
		"decision": "The DID-ready table is ready for panel merge after province-name compatibility checks.",
		"variables": "data/processed/province_year_srdi_policy_text_variables_v1.csv",
		"rationale": "The table is balanced at 31 provinces x 2020-2025 and excludes central policies from province-year variation.",
	},
]
variable_decision = pd.DataFrame(decision_rows)
variable_decision.to_csv(VARIABLE_DECISION_OUTPUT, index=False)
variable_decision

# %% [markdown]
# ## 6. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "did_ready_variables", "path": DID_READY_OUTPUT, "rows": len(did_ready), "exists": DID_READY_OUTPUT.exists()},
		{"artifact": "variable_selection", "path": VARIABLE_SELECTION_OUTPUT, "rows": len(variable_selection), "exists": VARIABLE_SELECTION_OUTPUT.exists()},
		{"artifact": "variable_correlations", "path": VARIABLE_CORRELATION_OUTPUT, "rows": len(variable_correlations), "exists": VARIABLE_CORRELATION_OUTPUT.exists()},
		{"artifact": "variable_decision", "path": VARIABLE_DECISION_OUTPUT, "rows": len(variable_decision), "exists": VARIABLE_DECISION_OUTPUT.exists()},
	]
)
output_checklist
