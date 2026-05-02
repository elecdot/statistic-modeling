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
# # DID-Ready Policy Intensity Panel
#
# This notebook builds the final policy-side panel for downstream DID merging.
#
# Scope:
#
# - policy data only;
# - no enterprise panel loading;
# - no DID regression;
# - one row per local province-year;
# - stable merge keys plus selected policy-intensity variables.
#
# Output:
#
# - `data/processed/manual_srdi_did_policy_intensity_panel_v1.csv`
#
# This table is the handoff artifact for later firm-year panel construction.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

POLICY_VARIABLES_PATH = ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v1.csv"
PROVINCE_CROSSWALK_PATH = ROOT / "outputs" / "manual_srdi_did_policy_intensity_province_crosswalk_template_v1.csv"

DID_PANEL_OUTPUT = ROOT / "data" / "processed" / "manual_srdi_did_policy_intensity_panel_v1.csv"
VARIABLE_MAP_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_variable_map_v1.csv"
QA_OUTPUT = OUTPUT_DIR / "manual_srdi_did_policy_intensity_panel_quality_report_v1.csv"

YEARS = list(range(2020, 2026))
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
	"srdi_supply_hard_label_count",
	"srdi_demand_hard_label_count",
	"srdi_environment_hard_label_count",
	"dict_supply_policy_count",
	"dict_demand_policy_count",
	"dict_environment_policy_count",
]
AUDIT_VARIABLES = [
	"srdi_valid_tool_policy_count",
	"srdi_valid_tool_policy_share",
	"srdi_other_exclusion_count",
]
PANEL_VARIABLES = (
	BASELINE_VARIABLES
	+ MAIN_VARIABLES
	+ ["srdi_total_tool_intensity"]
	+ STRUCTURE_VARIABLES
	+ ROBUSTNESS_VARIABLES
	+ ["srdi_total_tool_intensity_filtered"]
	+ AUDIT_VARIABLES
)
Z_SCORE_VARIABLES = BASELINE_VARIABLES + MAIN_VARIABLES + ["srdi_total_tool_intensity"]

# %% [markdown]
# ## 1. Load Inputs

# %%
policy_vars = pd.read_csv(POLICY_VARIABLES_PATH)
crosswalk = pd.read_csv(PROVINCE_CROSSWALK_PATH)

load_checks = pd.DataFrame(
	[
		{"artifact": "policy_variables", "path": POLICY_VARIABLES_PATH, "rows": len(policy_vars), "columns": policy_vars.shape[1]},
		{"artifact": "province_crosswalk", "path": PROVINCE_CROSSWALK_PATH, "rows": len(crosswalk), "columns": crosswalk.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Build Stable DID Merge Panel
#
# `did_province_key` is the recommended policy-side province key for downstream
# firm-panel merging. It uses short province names such as `广东`, `北京`, and
# `新疆`. The later enterprise-panel notebook should confirm that the firm data
# uses the same province spelling before merging.

# %%
required_columns = ["province", "publish_year"] + PANEL_VARIABLES
missing_columns = sorted(set(required_columns) - set(policy_vars.columns))
if missing_columns:
	raise ValueError(f"Missing required policy variable columns: {missing_columns}")

panel = policy_vars[required_columns].copy().rename(columns={"province": "policy_province"})
panel = panel.merge(
	crosswalk[
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
panel["policy_data_version"] = "manual_srdi_did_policy_intensity_panel_v1"

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
# ## 3. Add Standardized Variables
#
# Raw probability-sum intensities remain the main variables. Standardized
# versions are added only as convenience variables for later interaction models
# and coefficient-scale comparison.

# %%
for column in Z_SCORE_VARIABLES:
	std = panel[column].std(ddof=0)
	if std == 0:
		panel[f"{column}_z"] = 0.0
	else:
		panel[f"{column}_z"] = (panel[column] - panel[column].mean()) / std

panel.to_csv(DID_PANEL_OUTPUT, index=False)
panel.head()

# %% [markdown]
# ## 4. Variable Map

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
		"description": "Policy publication year, 2020-2025.",
		"did_use": "join_key",
	},
	{
		"variable": "policy_province",
		"role": "audit_key",
		"source": "policy variables",
		"description": "Canonical policy-side province label before short-name conversion.",
		"did_use": "audit",
	},
]

for variable in BASELINE_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "baseline_policy_volume",
			"source": "province_year_srdi_policy_text_variables_v1",
			"description": "Policy-count baseline or log-count baseline.",
			"did_use": "control_or_moderator",
		}
	)

for variable in MAIN_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "main_policy_tool_intensity",
			"source": "province_year_srdi_policy_text_variables_v1",
			"description": "MacBERT probability-sum policy-tool intensity.",
			"did_use": "main_moderator",
		}
	)

for variable in STRUCTURE_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "policy_tool_structure",
			"source": "province_year_srdi_policy_text_variables_v1",
			"description": "Relative probability share among supply, demand, and environment tools.",
			"did_use": "mechanism_or_heterogeneity",
		}
	)

for variable in ROBUSTNESS_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "robustness",
			"source": "province_year_srdi_policy_text_variables_v1",
			"description": "Filtered probability, hard-label, or dictionary robustness measure.",
			"did_use": "robustness",
		}
	)

for variable in AUDIT_VARIABLES:
	variable_rows.append(
		{
			"variable": variable,
			"role": "audit",
			"source": "province_year_srdi_policy_text_variables_v1",
			"description": "Valid-tool and other-label audit measure.",
			"did_use": "qa_or_sensitivity",
		}
	)

for variable in [f"{column}_z" for column in Z_SCORE_VARIABLES]:
	variable_rows.append(
		{
			"variable": variable,
			"role": "standardized_convenience",
			"source": "constructed from raw variable",
			"description": "Panel-wide z-score for coefficient scale comparison.",
			"did_use": "optional_scaled_model",
		}
	)

variable_map = pd.DataFrame(variable_rows)
variable_map.to_csv(VARIABLE_MAP_OUTPUT, index=False)
variable_map

# %% [markdown]
# ## 5. QA Report

# %%
expected_rows = 31 * len(YEARS)
qa_rows = [
	{
		"metric": "panel_rows",
		"value": len(panel),
		"expected": expected_rows,
		"status": "pass" if len(panel) == expected_rows else "fail",
		"note": "31 province units x 2020-2025.",
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
		"note": "Analysis window lower bound.",
	},
	{
		"metric": "year_max",
		"value": int(panel["did_year"].max()),
		"expected": max(YEARS),
		"status": "pass" if int(panel["did_year"].max()) == max(YEARS) else "fail",
		"note": "Analysis window upper bound.",
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
# ## 6. Handoff Decision
#
# The policy-side panel is ready. The only remaining dependency is external to
# this session: inspect the downstream enterprise panel province field and
# confirm it matches `did_province_key`.

# %%
blocking_failures = qa_report.loc[qa_report["status"].eq("fail")]
handoff_status = "ready_for_enterprise_panel_merge" if blocking_failures.empty else "blocked_before_enterprise_panel_merge"
pd.DataFrame(
	[
		{
			"decision": handoff_status,
			"policy_panel": DID_PANEL_OUTPUT.relative_to(ROOT),
			"merge_keys": "did_province_key;did_year",
			"main_variables": ";".join(MAIN_VARIABLES),
			"remaining_external_check": "Confirm enterprise panel province labels match did_province_key.",
		}
	]
)
