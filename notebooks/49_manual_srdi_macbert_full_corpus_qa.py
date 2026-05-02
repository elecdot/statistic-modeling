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
# # Manual SRDI MacBERT Full-Corpus QA
#
# This notebook checks whether the MacBERT full-corpus prediction outputs are
# ready to become the main policy-tool intensity inputs for downstream DID.
#
# It does not train or predict a model. It reads the completed full-corpus
# prediction artifacts, compares them with the full-text dictionary feature
# baseline, samples boundary records for audit, and writes compact QA tables
# under `outputs/`.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

CLASSIFIED_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v1.csv"
MACBERT_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v1.csv"
DICTIONARY_ROW_FEATURES_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv"
DICTIONARY_INTENSITY_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv"
PREDICTION_QUALITY_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v1.csv"
PREDICTION_PROBABILITY_SUMMARY_PATH = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v1.csv"
TRAINING_METRICS_PATH = ROOT / "outputs" / "manual_srdi_macbert_multilabel_metrics_v1.csv"

QA_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_qa_summary_v1.csv"
PROBABILITY_BY_YEAR_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_probability_by_year_v1.csv"
PROBABILITY_BY_PROVINCE_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_probability_by_province_v1.csv"
DICTIONARY_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_dictionary_comparison_v1.csv"
BOUNDARY_SAMPLES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_boundary_samples_v1.csv"
DECISION_TABLE_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_full_corpus_decision_table_v1.csv"

YEARS = list(range(2020, 2026))
TOOL_LABELS = ["supply", "demand", "environment"]
PROBABILITY_COLUMNS = ["p_supply", "p_demand", "p_environment", "p_other"]

# %% [markdown]
# ## 1. Load Inputs
#
# Expected shape:
#
# - row-level MacBERT predictions: 4475 records;
# - province-year MacBERT intensity: 31 local province units x 6 years = 186
#   rows;
# - full-text dictionary features: retained as a transparent robustness
#   baseline, not as final labels.

# %%
classified = pd.read_csv(CLASSIFIED_PATH)
macbert_intensity = pd.read_csv(MACBERT_INTENSITY_PATH)
dictionary_rows = pd.read_csv(DICTIONARY_ROW_FEATURES_PATH)
dictionary_intensity = pd.read_csv(DICTIONARY_INTENSITY_PATH)
prediction_quality = pd.read_csv(PREDICTION_QUALITY_PATH).set_index("metric")
prediction_probability_summary = pd.read_csv(PREDICTION_PROBABILITY_SUMMARY_PATH)
training_metrics = pd.read_csv(TRAINING_METRICS_PATH)

load_checks = pd.DataFrame(
	[
		{"artifact": "macbert_classified_rows", "rows": len(classified), "columns": classified.shape[1]},
		{"artifact": "macbert_province_year_intensity", "rows": len(macbert_intensity), "columns": macbert_intensity.shape[1]},
		{"artifact": "dictionary_row_features", "rows": len(dictionary_rows), "columns": dictionary_rows.shape[1]},
		{"artifact": "dictionary_province_year_intensity", "rows": len(dictionary_intensity), "columns": dictionary_intensity.shape[1]},
		{"artifact": "prediction_quality_report", "rows": len(prediction_quality), "columns": prediction_quality.shape[1]},
		{"artifact": "training_metrics", "rows": len(training_metrics), "columns": training_metrics.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Basic Acceptance Checks

# %%
probabilities_in_range = bool(classified[PROBABILITY_COLUMNS].apply(lambda series: series.between(0, 1).all()).all())
panel_is_balanced = (
	len(macbert_intensity) == 186
	and macbert_intensity["province"].nunique() == 31
	and set(macbert_intensity["publish_year"]) == set(YEARS)
)

test_metrics = training_metrics.loc[training_metrics["split"].eq("test")].iloc[0]
qa_summary = pd.DataFrame(
	[
		{"metric": "classified_rows", "value": len(classified), "note": "Expected 4475."},
		{"metric": "policy_id_unique", "value": bool(classified["policy_id"].is_unique), "note": "Must be true before DID merge."},
		{"metric": "probabilities_in_range", "value": probabilities_in_range, "note": "All p_* values should be in [0, 1]."},
		{"metric": "central_rows", "value": int(classified["jurisdiction_type"].eq("central").sum()), "note": "Retained in row-level predictions."},
		{"metric": "local_rows", "value": int(classified["jurisdiction_type"].eq("local").sum()), "note": "Used for province-year aggregation."},
		{"metric": "province_year_rows", "value": len(macbert_intensity), "note": "Expected 186."},
		{"metric": "province_units", "value": int(macbert_intensity["province"].nunique()), "note": "Expected 31 local province units."},
		{"metric": "panel_is_balanced_31x6", "value": panel_is_balanced, "note": "Balanced 2020-2025 local province panel."},
		{"metric": "valid_tool_policy_rows", "value": int(classified["valid_tool_policy"].sum()), "note": "Rows retained by hard-label filter."},
		{"metric": "valid_tool_policy_share", "value": float(classified["valid_tool_policy"].mean()), "note": "Audit share, not a target threshold."},
		{"metric": "other_label_rows", "value": int(classified["other_label"].sum()), "note": "Boundary/exclusion rows."},
		{"metric": "other_label_share", "value": float(classified["other_label"].mean()), "note": "Used for exclusion audit."},
		{"metric": "test_micro_f1", "value": float(test_metrics["micro_f1"]), "note": "Held-out round-1 test metric."},
		{"metric": "test_macro_f1", "value": float(test_metrics["macro_f1"]), "note": "Held-out round-1 test metric."},
		{"metric": "test_samples_jaccard", "value": float(test_metrics["samples_jaccard"]), "note": "Held-out round-1 test metric."},
	]
)
qa_summary.to_csv(QA_SUMMARY_OUTPUT, index=False)
qa_summary

# %% [markdown]
# ## 3. Probability Distribution By Year And Province
#
# These tables are used to inspect whether any year or province has abnormal
# probability concentration before entering DID.

# %%
probability_by_year = (
	classified.groupby("publish_year")
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
	)
	.reset_index()
	.sort_values(["avg_p_other", "policy_records"], ascending=[False, False])
)
probability_by_province.to_csv(PROBABILITY_BY_PROVINCE_OUTPUT, index=False)
probability_by_province.head(10)

# %% [markdown]
# ## 4. MacBERT vs Full-Text Dictionary Baseline
#
# The dictionary features remain useful as transparent robustness proxies. This
# section checks whether province-year MacBERT intensity broadly agrees with the
# full-text dictionary direction.

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
	]
	for macbert_column, dictionary_column, comparison_type in pairs:
		correlation_rows.append(
			{
				"category": category,
				"comparison_type": comparison_type,
				"macbert_column": macbert_column,
				"dictionary_column": dictionary_column,
				"pearson_corr": comparison[[macbert_column, dictionary_column]].corr().iloc[0, 1],
				"rows": len(comparison),
			}
		)

dictionary_comparison = pd.DataFrame(correlation_rows)
dictionary_comparison.to_csv(DICTIONARY_COMPARISON_OUTPUT, index=False)
dictionary_comparison

# %% [markdown]
# ## 5. Boundary Samples For Manual Audit
#
# These are review aids only. They are not round-2 sample files.

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

for column in ["has_supply_tool", "has_demand_tool", "has_environment_tool"]:
	dictionary_flags[column] = dictionary_flags[column].astype(str).str.lower().isin({"true", "1", "yes"})

boundary_base = classified.merge(dictionary_flags, on="policy_id", how="left", validate="one_to_one")

def take_boundary(frame: pd.DataFrame, reason: str, n: int = 30) -> pd.DataFrame:
	output = frame.head(n).copy()
	output.insert(0, "review_reason", reason)
	return output


boundary_samples = pd.concat(
	[
		take_boundary(boundary_base.sort_values("p_other", ascending=False), "highest_p_other"),
		take_boundary(
			boundary_base.loc[boundary_base["max_tool_prob"].between(0.35, 0.65)].sort_values("max_tool_prob"),
			"low_confidence_tool_boundary",
		),
		take_boundary(
			boundary_base.loc[
				boundary_base[["p_supply", "p_demand", "p_environment"]].ge(0.70).all(axis=1)
			].sort_values("tool_probability_sum", ascending=False),
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
	],
	ignore_index=True,
)

boundary_columns = [
	"review_reason",
	"policy_id",
	"province",
	"jurisdiction_type",
	"publish_year",
	"title",
	"agency",
	"source_url",
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
# ## 6. DID Readiness Decision

# %%
min_dictionary_corr = dictionary_comparison.loc[
	dictionary_comparison["comparison_type"].eq("raw_sum_vs_dictionary_count"), "pearson_corr"
].min()

decision_rows = [
	{
		"check": "artifact_completeness",
		"status": "pass" if len(classified) == 4475 and len(macbert_intensity) == 186 else "fail",
		"evidence": f"classified={len(classified)}, province_year={len(macbert_intensity)}",
		"decision_implication": "Required before any DID merge.",
	},
	{
		"check": "probability_validity",
		"status": "pass" if probabilities_in_range else "fail",
		"evidence": f"probabilities_in_range={probabilities_in_range}",
		"decision_implication": "Required for probability-intensity variables.",
	},
	{
		"check": "heldout_model_quality",
		"status": "pass" if float(test_metrics["macro_f1"]) >= 0.70 else "needs_review",
		"evidence": f"test_micro_f1={test_metrics['micro_f1']:.3f}; test_macro_f1={test_metrics['macro_f1']:.3f}",
		"decision_implication": "Supports using round-1 MacBERT v1 for first DID variables.",
	},
	{
		"check": "other_exclusion_rate",
		"status": "pass" if classified["other_label"].mean() <= 0.10 else "needs_review",
		"evidence": f"other_label_share={classified['other_label'].mean():.3f}",
		"decision_implication": "`other` remains an audit/filter variable, not a main intensity dimension.",
	},
	{
		"check": "dictionary_alignment",
		"status": "pass" if min_dictionary_corr >= 0.50 else "needs_review",
		"evidence": f"min raw-sum vs dictionary-count correlation={min_dictionary_corr:.3f}",
		"decision_implication": "Full-text dictionary features can be retained as robustness checks.",
	},
	{
		"check": "current_decision",
		"status": "ready_for_did_v1",
		"evidence": "Use MacBERT probability sums/averages as main policy-tool intensity variables.",
		"decision_implication": "Round-2 labeling is optional after manual review of boundary samples.",
	},
]
decision_table = pd.DataFrame(decision_rows)
decision_table.to_csv(DECISION_TABLE_OUTPUT, index=False)
decision_table

# %% [markdown]
# ## 7. Output Checklist

# %%
output_checklist = pd.DataFrame(
	[
		{"artifact": "qa_summary", "path": QA_SUMMARY_OUTPUT, "exists": QA_SUMMARY_OUTPUT.exists()},
		{"artifact": "probability_by_year", "path": PROBABILITY_BY_YEAR_OUTPUT, "exists": PROBABILITY_BY_YEAR_OUTPUT.exists()},
		{"artifact": "probability_by_province", "path": PROBABILITY_BY_PROVINCE_OUTPUT, "exists": PROBABILITY_BY_PROVINCE_OUTPUT.exists()},
		{"artifact": "dictionary_comparison", "path": DICTIONARY_COMPARISON_OUTPUT, "exists": DICTIONARY_COMPARISON_OUTPUT.exists()},
		{"artifact": "boundary_samples", "path": BOUNDARY_SAMPLES_OUTPUT, "exists": BOUNDARY_SAMPLES_OUTPUT.exists()},
		{"artifact": "decision_table", "path": DECISION_TABLE_OUTPUT, "exists": DECISION_TABLE_OUTPUT.exists()},
	]
)
output_checklist
