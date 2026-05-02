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
# # DID Policy-Intensity Handoff
#
# This notebook checks whether the selected manual SRDI policy-text variables
# are ready to be merged into the downstream staggered-DID enterprise panel.
#
# It does not load enterprise data and does not run DID regressions. Its job is
# to freeze the policy-side handoff contract:
#
# - one row per local province-year;
# - 31 province units x 2020-2025;
# - main MacBERT probability-sum policy-tool variables present and non-missing;
# - province-name crosswalk template available for the firm panel merge;
# - boundary-sample review remains explicit before final paper freeze.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

POLICY_VARIABLES_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v1.csv"
VARIABLE_DECISION_PATH = ROOT / "outputs" / "manual_srdi_policy_intensity_variable_decision_v1.csv"
BOUNDARY_SAMPLE_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_boundary_samples_v1.csv"

QA_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_handoff_qa_v1.csv"
VARIABLE_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_variable_summary_v1.csv"
PROVINCE_CROSSWALK_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_province_crosswalk_template_v1.csv"
BOUNDARY_REVIEW_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_boundary_review_summary_v1.csv"
HANDOFF_DECISION_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_handoff_decision_v1.csv"

YEARS = list(range(2020, 2026))
EXPECTED_PROVINCES = [
	"上海市",
	"云南省",
	"内蒙古自治区",
	"北京市",
	"吉林省",
	"四川省",
	"天津市",
	"宁夏回族自治区",
	"安徽省",
	"山东省",
	"山西省",
	"广东省",
	"广西壮族自治区",
	"新疆",
	"江苏省",
	"江西省",
	"河北省",
	"河南省",
	"浙江省",
	"海南省",
	"湖北省",
	"湖南省",
	"甘肃省",
	"福建省",
	"西藏自治区",
	"贵州省",
	"辽宁省",
	"重庆市",
	"陕西省",
	"青海省",
	"黑龙江省",
]

PROVINCE_SHORT_NAME = {
	"上海市": "上海",
	"云南省": "云南",
	"内蒙古自治区": "内蒙古",
	"北京市": "北京",
	"吉林省": "吉林",
	"四川省": "四川",
	"天津市": "天津",
	"宁夏回族自治区": "宁夏",
	"安徽省": "安徽",
	"山东省": "山东",
	"山西省": "山西",
	"广东省": "广东",
	"广西壮族自治区": "广西",
	"新疆": "新疆",
	"江苏省": "江苏",
	"江西省": "江西",
	"河北省": "河北",
	"河南省": "河南",
	"浙江省": "浙江",
	"海南省": "海南",
	"湖北省": "湖北",
	"湖南省": "湖南",
	"甘肃省": "甘肃",
	"福建省": "福建",
	"西藏自治区": "西藏",
	"贵州省": "贵州",
	"辽宁省": "辽宁",
	"重庆市": "重庆",
	"陕西省": "陕西",
	"青海省": "青海",
	"黑龙江省": "黑龙江",
}

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
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
]
AUDIT_VARIABLES = [
	"srdi_valid_tool_policy_share",
	"srdi_other_exclusion_count",
]

# %% [markdown]
# ## 1. Load Policy-Side Handoff Inputs

# %%
policy_vars = pd.read_csv(POLICY_VARIABLES_PATH)
variable_decision = pd.read_csv(VARIABLE_DECISION_PATH)
boundary_samples = pd.read_csv(BOUNDARY_SAMPLE_PATH)

load_checks = pd.DataFrame(
	[
		{"artifact": "policy_text_variables", "path": POLICY_VARIABLES_PATH, "rows": len(policy_vars), "columns": policy_vars.shape[1]},
		{"artifact": "variable_decision", "path": VARIABLE_DECISION_PATH, "rows": len(variable_decision), "columns": variable_decision.shape[1]},
		{"artifact": "boundary_samples", "path": BOUNDARY_SAMPLE_PATH, "rows": len(boundary_samples), "columns": boundary_samples.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Province-Year Panel Checks
#
# The policy-side table must be a balanced local province-year panel before it
# is merged into a firm-year DID panel.

# %%
expected_index = pd.MultiIndex.from_product([EXPECTED_PROVINCES, YEARS], names=["province", "publish_year"])
actual_index = pd.MultiIndex.from_frame(policy_vars[["province", "publish_year"]])
missing_index = expected_index.difference(actual_index)
extra_index = actual_index.difference(expected_index)

panel_checks = {
	"rows": len(policy_vars),
	"expected_rows": len(EXPECTED_PROVINCES) * len(YEARS),
	"province_units": policy_vars["province"].nunique(),
	"expected_province_units": len(EXPECTED_PROVINCES),
	"year_min": int(policy_vars["publish_year"].min()),
	"year_max": int(policy_vars["publish_year"].max()),
	"duplicate_province_year_rows": int(policy_vars[["province", "publish_year"]].duplicated().sum()),
	"missing_expected_province_year_rows": len(missing_index),
	"extra_province_year_rows": len(extra_index),
}
panel_checks_df = pd.DataFrame([{"metric": key, "value": value} for key, value in panel_checks.items()])
panel_checks_df

# %% [markdown]
# ## 3. Variable Completeness And Distribution Checks

# %%
handoff_variables = BASELINE_VARIABLES + MAIN_VARIABLES + ROBUSTNESS_VARIABLES + AUDIT_VARIABLES
missing_columns = sorted(set(handoff_variables) - set(policy_vars.columns))
negative_value_columns = [
	column
	for column in handoff_variables
	if column in policy_vars.columns and pd.api.types.is_numeric_dtype(policy_vars[column]) and (policy_vars[column] < 0).any()
]

variable_summary = policy_vars[handoff_variables].describe().T.reset_index(names="variable")
variable_summary["missing_count"] = [int(policy_vars[column].isna().sum()) for column in handoff_variables]
variable_summary["variable_role"] = variable_summary["variable"].map(
	{
		**{column: "baseline" for column in BASELINE_VARIABLES},
		**{column: "main" for column in MAIN_VARIABLES},
		**{column: "robustness" for column in ROBUSTNESS_VARIABLES},
		**{column: "audit" for column in AUDIT_VARIABLES},
	}
)
variable_summary.to_csv(VARIABLE_SUMMARY_OUTPUT, index=False)
variable_summary

# %% [markdown]
# ## 4. Province-Name Crosswalk Template
#
# The downstream enterprise panel may use short province names such as `广东`
# instead of policy-side labels such as `广东省`. This template is not yet the
# final firm-data crosswalk; it is the policy-side canonical mapping to review
# when the firm panel arrives.

# %%
province_crosswalk = pd.DataFrame(
	[
		{
			"policy_province": province,
			"province_short_name": PROVINCE_SHORT_NAME[province],
			"did_merge_key_recommended": PROVINCE_SHORT_NAME[province],
			"needs_firm_panel_confirmation": True,
			"note": "Confirm this key against the enterprise panel province field before merging.",
		}
		for province in EXPECTED_PROVINCES
	]
)
province_crosswalk["present_in_policy_variables"] = province_crosswalk["policy_province"].isin(policy_vars["province"])
province_crosswalk.to_csv(PROVINCE_CROSSWALK_OUTPUT, index=False)
province_crosswalk

# %% [markdown]
# ## 5. Boundary-Sample Review Status
#
# Boundary samples should be reviewed before final paper freeze. This does not
# block the first DID merge, but it should remain visible because it affects how
# confidently we discuss demand-threshold and `other` boundary cases.

# %%
boundary_review_summary = (
	boundary_samples.groupby("review_reason", dropna=False)
	.agg(
		records=("policy_id", "count"),
		avg_p_supply=("p_supply", "mean"),
		avg_p_demand=("p_demand", "mean"),
		avg_p_environment=("p_environment", "mean"),
		avg_p_other=("p_other", "mean"),
	)
	.reset_index()
	.sort_values(["records", "review_reason"], ascending=[False, True])
)
boundary_review_summary.to_csv(BOUNDARY_REVIEW_SUMMARY_OUTPUT, index=False)
boundary_review_summary

# %% [markdown]
# ## 6. Handoff QA And Decision

# %%
qa_rows = [
	{
		"check": "balanced_panel_31x6",
		"status": "pass" if panel_checks["rows"] == panel_checks["expected_rows"] and panel_checks["missing_expected_province_year_rows"] == 0 else "fail",
		"evidence": f"{panel_checks['rows']} rows; {panel_checks['province_units']} provinces; years {panel_checks['year_min']}-{panel_checks['year_max']}",
		"blocking_for_did_merge": True,
	},
	{
		"check": "unique_province_year_key",
		"status": "pass" if panel_checks["duplicate_province_year_rows"] == 0 else "fail",
		"evidence": f"{panel_checks['duplicate_province_year_rows']} duplicated province-year rows",
		"blocking_for_did_merge": True,
	},
	{
		"check": "main_variables_present",
		"status": "pass" if not missing_columns else "fail",
		"evidence": "missing columns: " + ";".join(missing_columns) if missing_columns else "all handoff variables present",
		"blocking_for_did_merge": True,
	},
	{
		"check": "main_variables_non_missing",
		"status": "pass" if policy_vars[MAIN_VARIABLES].isna().sum().sum() == 0 else "fail",
		"evidence": f"{int(policy_vars[MAIN_VARIABLES].isna().sum().sum())} missing values in main variables",
		"blocking_for_did_merge": True,
	},
	{
		"check": "no_negative_policy_variables",
		"status": "pass" if not negative_value_columns else "fail",
		"evidence": "negative columns: " + ";".join(negative_value_columns) if negative_value_columns else "no negative values in numeric handoff variables",
		"blocking_for_did_merge": True,
	},
	{
		"check": "province_crosswalk_template_ready",
		"status": "pass" if province_crosswalk["present_in_policy_variables"].all() else "fail",
		"evidence": f"{int(province_crosswalk['present_in_policy_variables'].sum())} policy provinces represented in template",
		"blocking_for_did_merge": False,
	},
	{
		"check": "boundary_samples_require_review",
		"status": "needs_review",
		"evidence": f"{len(boundary_samples)} boundary rows grouped into {boundary_samples['review_reason'].nunique()} review reasons",
		"blocking_for_did_merge": False,
	},
]
handoff_qa = pd.DataFrame(qa_rows)
handoff_qa.to_csv(QA_OUTPUT, index=False)
handoff_qa

# %%
blocking_failures = handoff_qa.loc[handoff_qa["blocking_for_did_merge"] & handoff_qa["status"].eq("fail")]
handoff_status = "ready_for_first_did_merge" if blocking_failures.empty else "blocked_before_did_merge"

handoff_decision = pd.DataFrame(
	[
		{
			"decision_area": "policy_side_handoff_status",
			"decision": handoff_status,
			"evidence": "All blocking policy-side checks pass." if blocking_failures.empty else "; ".join(blocking_failures["check"]),
			"next_action": "Load enterprise panel, inspect province-name field, and join on province/year after confirming crosswalk.",
		},
		{
			"decision_area": "main_did_policy_variables",
			"decision": "Use MacBERT probability-sum variables as main policy-tool moderators.",
			"evidence": ";".join(MAIN_VARIABLES),
			"next_action": "Merge these variables into firm-year panel and interact with LittleGiant treatment status.",
		},
		{
			"decision_area": "province_name_crosswalk",
			"decision": "Use province_short_name as recommended merge key, pending firm-panel confirmation.",
			"evidence": str(PROVINCE_CROSSWALK_OUTPUT.relative_to(ROOT)),
			"next_action": "Compare this template with the enterprise panel province labels before final merge.",
		},
		{
			"decision_area": "boundary_review",
			"decision": "Boundary review is not blocking for first merge but remains required before final paper freeze.",
			"evidence": str(BOUNDARY_REVIEW_SUMMARY_OUTPUT.relative_to(ROOT)),
			"next_action": "Review high p_other, demand-threshold, and MacBERT/dictionary conflict samples.",
		},
	]
)
handoff_decision.to_csv(HANDOFF_DECISION_OUTPUT, index=False)
handoff_decision

# %% [markdown]
# ## 7. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "handoff_qa", "path": QA_OUTPUT, "rows": len(handoff_qa), "exists": QA_OUTPUT.exists()},
		{"artifact": "variable_summary", "path": VARIABLE_SUMMARY_OUTPUT, "rows": len(variable_summary), "exists": VARIABLE_SUMMARY_OUTPUT.exists()},
		{"artifact": "province_crosswalk_template", "path": PROVINCE_CROSSWALK_OUTPUT, "rows": len(province_crosswalk), "exists": PROVINCE_CROSSWALK_OUTPUT.exists()},
		{"artifact": "boundary_review_summary", "path": BOUNDARY_REVIEW_SUMMARY_OUTPUT, "rows": len(boundary_review_summary), "exists": BOUNDARY_REVIEW_SUMMARY_OUTPUT.exists()},
		{"artifact": "handoff_decision", "path": HANDOFF_DECISION_OUTPUT, "rows": len(handoff_decision), "exists": HANDOFF_DECISION_OUTPUT.exists()},
	]
)
output_checklist
