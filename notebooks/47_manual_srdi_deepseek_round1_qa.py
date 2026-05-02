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
# # Manual SRDI DeepSeek Round-1 QA
#
# This notebook checks whether the DeepSeek round-1 labeling artifacts are
# complete enough to enter the next MacBERT / label-modeling stage.
#
# It does not call DeepSeek and does not modify raw API cache files. It reads
# the completed raw JSON cache, parsed label CSV, run quality report, and the
# original round-1 sample, then writes compact QA tables under `outputs/`.

# %%
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

SAMPLE_PATH = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_sample_round1_v1.csv"
LABELS_PATH = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_labels_round1_v1.csv"
QUALITY_PATH = ROOT / "outputs" / "manual_policy_srdi_deepseek_round1_quality_report_v1.csv"
RAW_DIR = ROOT / "data" / "raw" / "json" / "manual_srdi_deepseek_round1_v1"
RUN_LOG_PATH = ROOT / "outputs" / "manual_policy_srdi_deepseek_round1_run_log_v1.log"

QA_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_qa_summary_v1.csv"
FAILED_RECORDS_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_failed_records_v1.csv"
LABEL_DISTRIBUTION_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_label_distribution_v1.csv"
POOL_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_pool_summary_v1.csv"
PROBABILITY_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_probability_summary_v1.csv"
READINESS_OUTPUT = ROOT / "outputs" / "manual_srdi_deepseek_round1_readiness_decision_v1.csv"

EXPECTED_RECORDS = 800
EXPECTED_POOLS = {"supply-like", "demand-like", "environment-like", "other-like"}
PROBABILITY_COLUMNS = ["p_supply", "p_demand", "p_environment", "p_other"]
BINARY_COLUMNS = ["y_supply", "y_demand", "y_environment", "y_other"]

# %% [markdown]
# ## 1. Load Artifacts

# %%
sample = pd.read_csv(SAMPLE_PATH)
labels = pd.read_csv(LABELS_PATH)
quality = pd.read_csv(QUALITY_PATH)
raw_paths = sorted(RAW_DIR.glob("*.json"))

sample.shape, labels.shape, quality.shape, len(raw_paths)

# %% [markdown]
# ## 2. Raw Cache Integrity
#
# The parsed label CSV is the main artifact for modeling. Raw cache integrity is
# still checked because `--resume` and future audits depend on these JSON files.

# %%
raw_checks = []
for raw_path in raw_paths:
	try:
		payload = json.loads(raw_path.read_text(encoding="utf-8"))
		api_response = payload.get("api_response", {})
		choices = api_response.get("choices") or []
		message = choices[0].get("message", {}) if choices else {}
		content = message.get("content", "")
		raw_checks.append(
			{
				"raw_file": raw_path.name,
				"doc_id": payload.get("doc_id", ""),
				"has_choices": bool(choices),
				"content_is_nonempty": bool(str(content).strip()),
				"has_reasoning_content": bool(str(message.get("reasoning_content", "")).strip()),
				"parse_status": "success",
				"error": "",
			}
		)
	except Exception as exc:
		raw_checks.append(
			{
				"raw_file": raw_path.name,
				"doc_id": "",
				"has_choices": False,
				"content_is_nonempty": False,
				"has_reasoning_content": False,
				"parse_status": "failed",
				"error": str(exc),
			}
		)

raw_check = pd.DataFrame(raw_checks)
raw_check_summary = {
	"raw_json_files": len(raw_check),
	"raw_json_parse_failures": int(raw_check["parse_status"].ne("success").sum()),
	"raw_json_without_choices": int((~raw_check["has_choices"]).sum()) if len(raw_check) else 0,
	"raw_json_empty_content": int((~raw_check["content_is_nonempty"]).sum()) if len(raw_check) else 0,
}
raw_check_summary

# %% [markdown]
# ## 3. Completeness And Failure Checks

# %%
merged = sample[["doc_id", "sample_pool", "province", "year", "title"]].merge(
	labels,
	on=["doc_id", "sample_pool", "province", "year", "title"],
	how="outer",
	indicator=True,
	suffixes=("_sample", "_label"),
)

failed_records = labels.loc[labels["label_status"].ne("success")].copy()
failed_record_columns = [
	"doc_id",
	"sample_pool",
	"province",
	"year",
	"title",
	"label_status",
	"error",
	"raw_response_path",
]
failed_records = failed_records[failed_record_columns].sort_values(["sample_pool", "province", "year", "doc_id"])

completeness = {
	"sample_records": len(sample),
	"label_records": len(labels),
	"unique_sample_doc_ids": sample["doc_id"].nunique(),
	"unique_label_doc_ids": labels["doc_id"].nunique(),
	"merge_left_only": int(merged["_merge"].eq("left_only").sum()),
	"merge_right_only": int(merged["_merge"].eq("right_only").sum()),
	"success_records": int(labels["label_status"].eq("success").sum()),
	"failed_records": int(labels["label_status"].eq("failed").sum()),
	"missing_probability_values": int(labels.loc[labels["label_status"].eq("success"), PROBABILITY_COLUMNS].isna().sum().sum()),
}
completeness

# %% [markdown]
# ## 4. Label And Probability Distribution

# %%
success = labels.loc[labels["label_status"].eq("success")].copy()

label_distribution = (
	success[BINARY_COLUMNS]
	.agg(["sum", "mean"])
	.T.rename(columns={"sum": "positive_records", "mean": "positive_share"})
	.reset_index(names="label")
)
label_distribution["positive_records"] = label_distribution["positive_records"].astype(int)

pool_summary = (
	labels.groupby(["sample_pool", "label_status"], dropna=False)
	.size()
	.unstack(fill_value=0)
	.reset_index()
)
for column in ["success", "failed"]:
	if column not in pool_summary:
		pool_summary[column] = 0
pool_summary["records"] = pool_summary[["success", "failed"]].sum(axis=1)
pool_summary["success_share"] = pool_summary["success"] / pool_summary["records"]

probability_summary = success[PROBABILITY_COLUMNS].agg(["count", "mean", "std", "min", "median", "max"]).T.reset_index(names="probability")
probability_summary

# %% [markdown]
# ## 5. Readiness Decision

# %%
conditions = [
	(
		"raw_cache_complete",
		len(raw_paths) == EXPECTED_RECORDS,
		f"Expected {EXPECTED_RECORDS} raw JSON files; found {len(raw_paths)}.",
	),
	(
		"labels_complete",
		len(labels) == EXPECTED_RECORDS and labels["doc_id"].nunique() == EXPECTED_RECORDS,
		f"Expected {EXPECTED_RECORDS} unique label rows; found rows={len(labels)}, unique_doc_ids={labels['doc_id'].nunique()}.",
	),
	(
		"sample_alignment_complete",
		merged["_merge"].eq("both").all(),
		f"Sample/label merge left_only={int(merged['_merge'].eq('left_only').sum())}, right_only={int(merged['_merge'].eq('right_only').sum())}.",
	),
	(
		"pool_balance_complete",
		set(labels["sample_pool"].unique()) == EXPECTED_POOLS and labels["sample_pool"].value_counts().eq(200).all(),
		f"Pool counts: {labels['sample_pool'].value_counts().sort_index().to_dict()}",
	),
	(
		"no_failed_labels",
		labels["label_status"].eq("success").all(),
		f"Failed label rows: {int(labels['label_status'].ne('success').sum())}.",
	),
	(
		"success_probabilities_complete",
		success[PROBABILITY_COLUMNS].notna().all().all(),
		"All success rows should have non-missing probabilities.",
	),
	(
		"raw_content_parseable",
		raw_check["parse_status"].eq("success").all() and raw_check["has_choices"].all(),
		f"Raw parse failures={int(raw_check['parse_status'].ne('success').sum())}; missing choices={int((~raw_check['has_choices']).sum())}.",
	),
]

readiness = pd.DataFrame(
	[
		{
			"check": name,
			"passed": bool(passed),
			"note": note,
		}
		for name, passed, note in conditions
	]
)
ready_for_macbert_training = bool(readiness["passed"].all())
ready_for_failed_label_repair = bool(
	not ready_for_macbert_training and readiness.loc[readiness["check"].ne("no_failed_labels"), "passed"].all()
)

decision = pd.DataFrame(
	[
		{
			"decision": "ready_for_macbert_training",
			"value": ready_for_macbert_training,
			"note": "Requires zero failed labels and complete sample/raw alignment.",
		},
		{
			"decision": "ready_for_failed_label_repair",
			"value": ready_for_failed_label_repair,
			"note": "True only when infrastructure artifacts are complete but at least one parsed label still failed.",
		},
		{
			"decision": "recommended_next_action",
			"value": "retry_failed_label_then_rerun_qa" if not ready_for_macbert_training else "enter_macbert_training_preparation",
			"note": "Use this value as the next workflow gate.",
		},
	]
)
readiness, decision

# %% [markdown]
# ## 6. Write QA Outputs

# %%
qa_summary = pd.DataFrame(
	[
		{"metric": key, "value": value, "note": ""}
		for key, value in {
			**raw_check_summary,
			**completeness,
			"sample_pools": ";".join(sorted(labels["sample_pool"].dropna().unique())),
			"ready_for_macbert_training": ready_for_macbert_training,
			"ready_for_failed_label_repair": ready_for_failed_label_repair,
		}.items()
	]
)

for path in [
	QA_SUMMARY_OUTPUT,
	FAILED_RECORDS_OUTPUT,
	LABEL_DISTRIBUTION_OUTPUT,
	POOL_SUMMARY_OUTPUT,
	PROBABILITY_SUMMARY_OUTPUT,
	READINESS_OUTPUT,
]:
	path.parent.mkdir(parents=True, exist_ok=True)

qa_summary.to_csv(QA_SUMMARY_OUTPUT, index=False)
failed_records.to_csv(FAILED_RECORDS_OUTPUT, index=False)
label_distribution.to_csv(LABEL_DISTRIBUTION_OUTPUT, index=False)
pool_summary.to_csv(POOL_SUMMARY_OUTPUT, index=False)
probability_summary.to_csv(PROBABILITY_SUMMARY_OUTPUT, index=False)
pd.concat([readiness.assign(table="check"), decision.assign(table="decision")], ignore_index=True).to_csv(
	READINESS_OUTPUT,
	index=False,
)

QA_SUMMARY_OUTPUT, FAILED_RECORDS_OUTPUT, READINESS_OUTPUT

# %% [markdown]
# ## 7. Notebook Conclusion
#
# The DeepSeek round-1 run now has a complete 800-row parsed label table and a
# complete 800-file raw cache. The sample is aligned with the original round-1
# frame and remains balanced across four sampling pools.
#
# One raw response, `manual_srdi_8d707795ae153f1b`, still has an empty
# `message.content`, but the requested JSON object is present in
# `reasoning_content`. The labeling parser now uses `message.content` first and
# falls back to `reasoning_content` when `content` is empty, so this row is
# parsed successfully without changing the raw cache or re-calling the API.
#
# Practical decision: round-1 labels are artifact-complete and can enter the
# next training-data preparation step under `docs/label-intensity-construct-plan.md`.
