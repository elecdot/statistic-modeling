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
# # DID-Ready Policy Intensity Panel v2
#
# This notebook builds the final v2 policy-side panel for downstream DID
# merging.
#
# Scope:
#
# - policy data only;
# - corrected analysis window: 2019-2024;
# - one row per local province-year;
# - no enterprise panel loading;
# - no DID regression;
# - stable merge keys, selected policy-intensity variables, robustness fields,
#   audit fields, variable map, and QA report.
#
# Output:
#
# - `data/processed/manual_srdi_did_policy_intensity_panel_v2.csv`
#
# This table is the v2 policy-side handoff artifact. It is not an enterprise
# panel and does not contain treatment, outcome, or regression results.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

POLICY_VARIABLES_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v2.csv"
VARIABLE_DECISION_PATH = ROOT / "outputs" / "manual_srdi_policy_intensity_variable_decision_v2.csv"
BOUNDARY_SAMPLE_PATH = ROOT / "outputs" / "manual_srdi_macbert_prediction_boundary_samples_v2.csv"

DID_PANEL_OUTPUT = ROOT / "data" / "processed" / "manual_srdi_did_policy_intensity_panel_v2.csv"
PROVINCE_CROSSWALK_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_province_crosswalk_template_v2.csv"
VARIABLE_MAP_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_variable_map_v2.csv"
QA_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_quality_report_v2.csv"
DECISION_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_decision_v2.csv"

YEARS = list(range(2019, 2025))
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
STRUCTURE_VARIABLES = [
	"srdi_supply_probability_share",
	"srdi_demand_probability_share",
	"srdi_environment_probability_share",
]
ROBUSTNESS_VARIABLES = [
	"srdi_supply_intensity_filtered",
	"srdi_demand_intensity_filtered",
	"srdi_environment_intensity_filtered",
	"srdi_total_tool_intensity_filtered",
	"srdi_supply_probability_share_filtered",
	"srdi_demand_probability_share_filtered",
	"srdi_environment_probability_share_filtered",
	"srdi_supply_hard_label_count",
	"srdi_demand_hard_label_count",
	"srdi_environment_hard_label_count",
	"srdi_total_hard_label_count",
	"srdi_supply_high_confidence_count",
	"srdi_demand_high_confidence_count",
	"srdi_environment_high_confidence_count",
	"srdi_total_high_confidence_count",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
	"dict_any_tool_policy_count",
	"dict_supply_policy_share",
	"dict_demand_policy_share",
	"dict_environment_policy_share",
	"dict_any_tool_policy_share",
	"dict_avg_tool_category_count",
]
AUDIT_VARIABLES = [
	"srdi_macbert_policy_records",
	"srdi_valid_tool_policy_count",
	"srdi_valid_tool_policy_share",
	"srdi_other_exclusion_count",
	"srdi_other_probability_sum",
	"srdi_other_avg_probability",
	"audit_missing_full_text_count",
	"audit_fallback_full_text_for_model_count",
	"audit_full_text_missing_policy_count",
	"audit_full_text_fallback_policy_count",
	"audit_missing_agency_count",
	"audit_unique_agency_count",
	"audit_jurisdiction_review_candidate_count",
	"audit_avg_full_text_len",
	"audit_avg_text_surface_len",
]
PANEL_VARIABLES = (
	BASELINE_VARIABLES
	+ MAIN_VARIABLES
	+ ["srdi_total_tool_intensity"]
	+ STRUCTURE_VARIABLES
	+ ROBUSTNESS_VARIABLES
	+ AUDIT_VARIABLES
)
Z_SCORE_VARIABLES = BASELINE_VARIABLES + MAIN_VARIABLES + ["srdi_total_tool_intensity"]

# %% [markdown]
# ## 1. Load Inputs

# %%
policy_vars = pd.read_csv(POLICY_VARIABLES_PATH)
variable_decision = pd.read_csv(VARIABLE_DECISION_PATH)
boundary_samples = pd.read_csv(BOUNDARY_SAMPLE_PATH)

load_checks = pd.DataFrame(
	[
		{"artifact": "policy_text_variables_v2", "path": POLICY_VARIABLES_PATH, "rows": len(policy_vars), "columns": policy_vars.shape[1]},
		{"artifact": "variable_decision_v2", "path": VARIABLE_DECISION_PATH, "rows": len(variable_decision), "columns": variable_decision.shape[1]},
		{"artifact": "boundary_samples_v2", "path": BOUNDARY_SAMPLE_PATH, "rows": len(boundary_samples), "columns": boundary_samples.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Build v2 Province Crosswalk
#
# `did_province_key` uses the short policy-side province key, such as `广东`,
# `北京`, and `新疆`. The downstream enterprise panel must still confirm that
# its province field uses the same spelling before merging.

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
province_crosswalk.head()

# %% [markdown]
# ## 3. Build Stable DID Merge Panel

# %%
required_columns = ["province", "publish_year"] + PANEL_VARIABLES
missing_columns = sorted(set(required_columns) - set(policy_vars.columns))
if missing_columns:
	raise ValueError(f"Missing required v2 policy variable columns: {missing_columns}")

expected_index = pd.MultiIndex.from_product([EXPECTED_PROVINCES, YEARS], names=["province", "publish_year"])
actual_index = pd.MultiIndex.from_frame(policy_vars[["province", "publish_year"]])
missing_index = expected_index.difference(actual_index)
extra_index = actual_index.difference(expected_index)
if len(missing_index) or len(extra_index):
	raise ValueError(f"v2 policy variables are not the expected 31 x 2019-2024 panel: missing={len(missing_index)}, extra={len(extra_index)}")

panel = policy_vars[required_columns].copy().rename(columns={"province": "policy_province"})
panel = panel.merge(
	province_crosswalk[
		[
			"policy_province",
			"province_short_name",
			"did_merge_key_recommended",
			"needs_firm_panel_confirmation",
		]
	],
	on="policy_province",
	how="left",
	validate="many_to_one",
)
panel = panel.rename(
	columns={
		"province_short_name": "province_short",
		"did_merge_key_recommended": "did_province_key",
		"publish_year": "did_year",
	}
)
panel["policy_panel_id"] = panel["did_province_key"] + "_" + panel["did_year"].astype(str)
panel["policy_data_version"] = "manual_srdi_did_policy_intensity_panel_v2"

front_columns = [
	"policy_panel_id",
	"did_province_key",
	"did_year",
	"policy_province",
	"province_short",
	"needs_firm_panel_confirmation",
	"policy_data_version",
]
panel = panel[front_columns + PANEL_VARIABLES]
panel = panel.sort_values(["did_province_key", "did_year"]).reset_index(drop=True)
panel.head()

# %% [markdown]
# ## 4. Add Standardized Convenience Variables
#
# Raw probability-sum variables remain the main policy-tool variables.
# Standardized versions are convenience variables for coefficient-scale
# comparison and interaction models.

# %%
for column in Z_SCORE_VARIABLES:
	std = panel[column].std(ddof=0)
	panel[f"{column}_z"] = 0.0 if std == 0 else (panel[column] - panel[column].mean()) / std

panel.to_csv(DID_PANEL_OUTPUT, index=False)
panel.head()

# %% [markdown]
# ## 5. Variable Map

# %%
variable_rows = [
	{
		"variable": "policy_panel_id",
		"role": "identifier",
		"source": "constructed",
		"description": "Stable province-year policy-side row ID: did_province_key + year.",
		"did_use": "merge_audit",
	},
	{
		"variable": "did_province_key",
		"role": "merge_key",
		"source": "province crosswalk",
		"description": "Recommended province key for merging with the enterprise panel.",
		"did_use": "join_key",
	},
	{
		"variable": "did_year",
		"role": "merge_key",
		"source": "publish_year",
		"description": "Policy publication year, 2019-2024.",
		"did_use": "join_key",
	},
	{
		"variable": "policy_province",
		"role": "audit_key",
		"source": "policy variables",
		"description": "Canonical policy-side province label before short-name conversion.",
		"did_use": "audit",
	},
	{
		"variable": "policy_data_version",
		"role": "version",
		"source": "constructed",
		"description": "Policy-side panel version identifier.",
		"did_use": "merge_audit",
	},
]

for variable in BASELINE_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "baseline_policy_volume",
			"source": "province_year_srdi_policy_text_variables_v2",
			"description": "Policy-count baseline or log-count baseline.",
			"did_use": "control_or_moderator",
		}
	)

for variable in MAIN_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "main_policy_tool_intensity",
			"source": "province_year_srdi_policy_text_variables_v2",
			"description": "MacBERT probability-sum policy-tool intensity.",
			"did_use": "main_moderator",
		}
	)

for variable in STRUCTURE_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "policy_tool_structure",
			"source": "province_year_srdi_policy_text_variables_v2",
			"description": "Relative probability share among supply, demand, and environment tools.",
			"did_use": "mechanism_or_heterogeneity",
		}
	)

for variable in ROBUSTNESS_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "robustness",
			"source": "province_year_srdi_policy_text_variables_v2",
			"description": "Filtered probability, hard-label, high-confidence, or dictionary robustness measure.",
			"did_use": "robustness",
		}
	)

for variable in AUDIT_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "audit",
			"source": "province_year_srdi_policy_text_variables_v2",
			"description": "Data-quality, fallback, boundary-label, or text-coverage audit measure.",
			"did_use": "qa_or_sensitivity",
		}
	)

for variable in [f"{column}_z" for column in Z_SCORE_VARIABLES]:
	variable_rows.append(
		{
			"variable": variable,
			"role": "standardized_convenience",
			"source": "constructed from raw variable",
			"description": "Panel-wide z-score for coefficient-scale comparison.",
			"did_use": "optional_scaled_model",
		}
	)

variable_map = pd.DataFrame(variable_rows)
variable_map.to_csv(VARIABLE_MAP_OUTPUT, index=False)
variable_map.head()

# %% [markdown]
# ## 6. QA Report

# %%
expected_rows = len(EXPECTED_PROVINCES) * len(YEARS)
qa_rows = [
	{
		"metric": "panel_rows",
		"value": len(panel),
		"expected": expected_rows,
		"status": "pass" if len(panel) == expected_rows else "fail",
		"note": "31 local province units x 2019-2024.",
	},
	{
		"metric": "province_units",
		"value": panel["did_province_key"].nunique(),
		"expected": 31,
		"status": "pass" if panel["did_province_key"].nunique() == 31 else "fail",
		"note": "Local province units only; central excluded.",
	},
	{
		"metric": "year_min",
		"value": int(panel["did_year"].min()),
		"expected": min(YEARS),
		"status": "pass" if int(panel["did_year"].min()) == min(YEARS) else "fail",
		"note": "Corrected analysis-window lower bound.",
	},
	{
		"metric": "year_max",
		"value": int(panel["did_year"].max()),
		"expected": max(YEARS),
		"status": "pass" if int(panel["did_year"].max()) == max(YEARS) else "fail",
		"note": "Corrected analysis-window upper bound.",
	},
	{
		"metric": "year_set",
		"value": ";".join(map(str, sorted(panel["did_year"].unique()))),
		"expected": ";".join(map(str, YEARS)),
		"status": "pass" if set(panel["did_year"]) == set(YEARS) else "fail",
		"note": "Must be 2019-2024, not 2020-2025.",
	},
	{
		"metric": "policy_panel_id_unique",
		"value": panel["policy_panel_id"].is_unique,
		"expected": True,
		"status": "pass" if panel["policy_panel_id"].is_unique else "fail",
		"note": "Required for unambiguous province-year merge.",
	},
	{
		"metric": "did_keys_unique",
		"value": int(panel[["did_province_key", "did_year"]].duplicated().sum()),
		"expected": 0,
		"status": "pass" if panel[["did_province_key", "did_year"]].duplicated().sum() == 0 else "fail",
		"note": "No duplicate merge keys.",
	},
	{
		"metric": "main_variable_missing_values",
		"value": int(panel[MAIN_VARIABLES].isna().sum().sum()),
		"expected": 0,
		"status": "pass" if panel[MAIN_VARIABLES].isna().sum().sum() == 0 else "fail",
		"note": "Main moderators must be complete.",
	},
	{
		"metric": "main_variable_negative_values",
		"value": int((panel[MAIN_VARIABLES] < 0).sum().sum()),
		"expected": 0,
		"status": "pass" if (panel[MAIN_VARIABLES] < 0).sum().sum() == 0 else "fail",
		"note": "Probability-sum intensities cannot be negative.",
	},
	{
		"metric": "fallback_full_text_rows",
		"value": int(panel["audit_fallback_full_text_for_model_count"].sum()),
		"expected": 1,
		"status": "pass" if int(panel["audit_fallback_full_text_for_model_count"].sum()) == 1 else "needs_review",
		"note": "The single v2 missing-full-text fallback row remains retained and auditable.",
	},
	{
		"metric": "jurisdiction_review_candidate_rows",
		"value": int(panel["audit_jurisdiction_review_candidate_count"].sum()),
		"expected": 0,
		"status": "pass" if int(panel["audit_jurisdiction_review_candidate_count"].sum()) == 0 else "fail",
		"note": "Reviewed v2 overrides should leave no unresolved jurisdiction candidates.",
	},
	{
		"metric": "central_in_panel",
		"value": "central" in set(panel["did_province_key"]),
		"expected": False,
		"status": "pass" if "central" not in set(panel["did_province_key"]) else "fail",
		"note": "Central policies are retained row-level upstream but excluded from province-year variation.",
	},
	{
		"metric": "firm_panel_confirmation_required",
		"value": bool(panel["needs_firm_panel_confirmation"].all()),
		"expected": True,
		"status": "needs_external_data",
		"note": "Confirm did_province_key against enterprise panel before final merge.",
	},
]
qa_report = pd.DataFrame(qa_rows)
qa_report.to_csv(QA_OUTPUT, index=False)
qa_report

# %% [markdown]
# ## 7. Handoff Decision

# %%
blocking_failures = qa_report.loc[qa_report["status"].eq("fail")]
panel_status = "ready_for_enterprise_panel_merge" if blocking_failures.empty else "blocked_before_enterprise_panel_merge"

decision = pd.DataFrame(
	[
		{
			"decision_area": "policy_side_panel_status",
			"decision": panel_status,
			"evidence": "All blocking policy-side checks pass." if blocking_failures.empty else "; ".join(blocking_failures["metric"]),
			"next_action": "Load enterprise panel, inspect province-name field, and join on did_province_key/did_year after confirming crosswalk.",
		},
		{
			"decision_area": "analysis_window",
			"decision": "Use 2019-2024.",
			"evidence": ";".join(map(str, YEARS)),
			"next_action": "Do not use the old 2020-2025 v1 panel for the corrected DID policy-side window.",
		},
		{
			"decision_area": "main_did_policy_variables",
			"decision": "Use MacBERT probability-sum variables as main policy-tool moderators.",
			"evidence": ";".join(MAIN_VARIABLES),
			"next_action": "Merge these variables into the firm-year panel and interact with treatment status as required by the downstream DID design.",
		},
		{
			"decision_area": "robustness_and_audit",
			"decision": "Retain filtered sums, hard-label counts, high-confidence counts, dictionary variables, fallback audit, and jurisdiction audit fields.",
			"evidence": str(VARIABLE_MAP_OUTPUT.relative_to(ROOT)),
			"next_action": "Use robustness variables for sensitivity checks; keep audit variables out of main substantive interpretation.",
		},
		{
			"decision_area": "province_name_crosswalk",
			"decision": "Use did_province_key as recommended merge key, pending firm-panel confirmation.",
			"evidence": str(PROVINCE_CROSSWALK_OUTPUT.relative_to(ROOT)),
			"next_action": "Compare this template with the enterprise panel province labels before final merge.",
		},
	]
)
decision.to_csv(DECISION_OUTPUT, index=False)
decision

# %% [markdown]
# ## 8. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "did_panel_v2", "path": DID_PANEL_OUTPUT, "rows": len(panel), "exists": DID_PANEL_OUTPUT.exists()},
		{"artifact": "province_crosswalk_v2", "path": PROVINCE_CROSSWALK_OUTPUT, "rows": len(province_crosswalk), "exists": PROVINCE_CROSSWALK_OUTPUT.exists()},
		{"artifact": "variable_map_v2", "path": VARIABLE_MAP_OUTPUT, "rows": len(variable_map), "exists": VARIABLE_MAP_OUTPUT.exists()},
		{"artifact": "qa_report_v2", "path": QA_OUTPUT, "rows": len(qa_report), "exists": QA_OUTPUT.exists()},
		{"artifact": "decision_v2", "path": DECISION_OUTPUT, "rows": len(decision), "exists": DECISION_OUTPUT.exists()},
	]
)
output_checklist
