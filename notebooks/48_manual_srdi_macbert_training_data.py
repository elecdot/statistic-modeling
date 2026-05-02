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
# # Manual SRDI MacBERT Training-Data Preparation
#
# This notebook turns the completed DeepSeek round-1 silver labels into a
# deterministic MacBERT-ready multi-label training dataset.
#
# Scope:
#
# - no model download;
# - no MacBERT training;
# - no API calls;
# - no relabeling.
#
# Outputs include train/validation/test JSONL files, an audit CSV with all 800
# training rows, label-balance diagnostics, `pos_weight` values for
# `BCEWithLogitsLoss`, and a compact readiness report.

# %%
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

LABEL_DOCS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_label_docs_v1.csv"
LABELS_PATH = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_labels_round1_v1.csv"
RULE_KEYWORDS_PATH = ROOT / "configs" / "manual_srdi_label_rule_keywords_v1.csv"

DATASET_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_macbert_training_dataset_v1.csv"
JSONL_DIR = ROOT / "data" / "processed" / "manual_policy_srdi_macbert_training_v1"
TRAIN_JSONL = JSONL_DIR / "train.jsonl"
VALID_JSONL = JSONL_DIR / "validation.jsonl"
TEST_JSONL = JSONL_DIR / "test.jsonl"

QUALITY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_training_data_quality_report_v1.csv"
SPLIT_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_training_split_summary_v1.csv"
LABEL_BALANCE_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_training_label_balance_v1.csv"
POS_WEIGHT_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_training_pos_weight_v1.csv"

LABEL_COLUMNS = ["y_supply", "y_demand", "y_environment", "y_other"]
PROBABILITY_COLUMNS = ["p_supply", "p_demand", "p_environment", "p_other"]
LABEL_NAMES = ["supply", "demand", "environment", "other"]
SPLIT_RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}
RANDOM_STATE = 42
FRONT_CHARS = 1200
KEYWORD_CONTEXT_CHARS = 1200
KEYWORD_CONTEXT_WINDOW_LEFT = 120
KEYWORD_CONTEXT_WINDOW_RIGHT = 260

# %% [markdown]
# ## 1. Load Completed Silver Labels

# %%
label_docs = pd.read_csv(LABEL_DOCS_PATH)
labels = pd.read_csv(LABELS_PATH)
rule_keywords = pd.read_csv(RULE_KEYWORDS_PATH)

label_docs.shape, labels.shape, rule_keywords.shape

# %%
if not labels["label_status"].eq("success").all():
	failed = labels.loc[labels["label_status"].ne("success"), ["doc_id", "label_status", "error"]]
	raise ValueError(f"MacBERT training data requires all DeepSeek labels to be success:\n{failed.to_string()}")

if labels["doc_id"].duplicated().any():
	raise ValueError("DeepSeek labels contain duplicate doc_id values.")

if label_docs["doc_id"].duplicated().any():
	raise ValueError("Label docs contain duplicate doc_id values.")

# %% [markdown]
# ## 2. Build MacBERT Model Input Text
#
# Full policy texts can be longer than MacBERT's practical input length. This
# notebook prepares a compact, reproducible input string:
#
# - title, agency, year, province metadata;
# - front section of the full text;
# - contexts around label-rule keywords.
#
# Token-level truncation still belongs to the future training script.

# %%
def stable_hash(value: str, length: int = 16) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def normalize_text(value: Any) -> str:
	text = "" if pd.isna(value) else str(value)
	text = re.sub(r"\s+", "\n", text)
	return text.strip()


def get_context_terms(rule_frame: pd.DataFrame) -> list[str]:
	terms = (
		rule_frame.loc[rule_frame["keep_for_sampling"].astype(str).str.lower().eq("true"), "term"]
		.dropna()
		.astype(str)
		.str.strip()
	)
	return sorted({term for term in terms if term}, key=lambda item: (-len(item), item))


CONTEXT_TERMS = get_context_terms(rule_keywords)
len(CONTEXT_TERMS), CONTEXT_TERMS[:10]

# %%
def collect_keyword_context(text: str, terms: list[str]) -> str:
	seen_spans: list[tuple[int, int]] = []
	snippets: list[str] = []
	for term in terms:
		index = text.find(term)
		if index < 0:
			continue
		start = max(0, index - KEYWORD_CONTEXT_WINDOW_LEFT)
		end = min(len(text), index + len(term) + KEYWORD_CONTEXT_WINDOW_RIGHT)
		if any(max(start, old_start) < min(end, old_end) for old_start, old_end in seen_spans):
			continue
		seen_spans.append((start, end))
		snippet = text[start:end].strip()
		if snippet:
			snippets.append(snippet)
		if len("\n".join(snippets)) >= KEYWORD_CONTEXT_CHARS:
			break
	return "\n".join(snippets)[:KEYWORD_CONTEXT_CHARS]


def make_model_text(row: pd.Series) -> str:
	text = normalize_text(row["clean_text"])
	front = text[:FRONT_CHARS]
	keyword_context = collect_keyword_context(text, CONTEXT_TERMS)
	parts = [
		f"标题：{normalize_text(row['title'])}",
		f"发文机关：{normalize_text(row['issuing_agency'])}",
		f"省份：{normalize_text(row['province'])}",
		f"年份：{int(row['year'])}",
		"",
		"正文前部：",
		front,
	]
	if keyword_context:
		parts.extend(["", "关键词附近内容：", keyword_context])
	return "\n".join(parts).strip()


# %% [markdown]
# ## 3. Merge Labels With Documents

# %%
dataset = labels.merge(
	label_docs[["doc_id", "clean_text"]],
	on="doc_id",
	how="left",
	validate="one_to_one",
)

if dataset["clean_text"].isna().any():
	missing = dataset.loc[dataset["clean_text"].isna(), "doc_id"].head(10).tolist()
	raise ValueError(f"Missing clean_text for labeled docs: {missing}")

for column in LABEL_COLUMNS:
	dataset[column] = dataset[column].astype(int)

dataset["labels"] = dataset[LABEL_COLUMNS].astype(int).values.tolist()
dataset["soft_labels"] = dataset[PROBABILITY_COLUMNS].astype(float).values.tolist()
dataset["label_pattern"] = dataset[LABEL_COLUMNS].astype(str).agg("".join, axis=1)
dataset["stratify_key"] = dataset["sample_pool"].astype(str) + "|" + dataset["label_pattern"]
dataset["model_text"] = dataset.apply(make_model_text, axis=1)
dataset["model_text_len"] = dataset["model_text"].str.len()
dataset["source_text_hash"] = dataset["clean_text"].map(lambda value: stable_hash(normalize_text(value)))
dataset["model_text_hash"] = dataset["model_text"].map(stable_hash)

dataset[["doc_id", "sample_pool", "label_pattern", "model_text_len"]].head()

# %% [markdown]
# ## 4. Deterministic Stratified Split
#
# The split is deterministic and grouped by `sample_pool + label pattern` when
# possible. Tiny groups are still split by hash order, so the result is stable
# without adding scikit-learn as a dependency.

# %%
def split_group(group: pd.DataFrame) -> pd.Series:
	ordered = group.sort_values("_split_hash").copy()
	n = len(ordered)
	train_n = round(n * SPLIT_RATIOS["train"])
	valid_n = round(n * SPLIT_RATIOS["validation"])
	if train_n + valid_n > n:
		valid_n = max(0, n - train_n)
	test_n = n - train_n - valid_n
	if n >= 3 and test_n == 0:
		if valid_n > 1:
			valid_n -= 1
		elif train_n > 1:
			train_n -= 1
		test_n = 1
	assigned = ["train"] * train_n + ["validation"] * valid_n + ["test"] * test_n
	return pd.Series(assigned, index=ordered.index, dtype="string")


dataset["_split_hash"] = dataset["doc_id"].map(lambda value: stable_hash(f"{RANDOM_STATE}:{value}", length=32))
split_series = dataset.groupby("stratify_key", group_keys=False).apply(split_group)
dataset["split"] = split_series.reindex(dataset.index).astype(str)
dataset = dataset.drop(columns=["_split_hash"])

dataset["split"].value_counts().sort_index()

# %% [markdown]
# ## 5. QA Tables

# %%
label_balance_rows = []
for split_name in ["all", "train", "validation", "test"]:
	frame = dataset if split_name == "all" else dataset.loc[dataset["split"].eq(split_name)]
	for label_name, column in zip(LABEL_NAMES, LABEL_COLUMNS, strict=True):
		positive = int(frame[column].sum())
		total = int(len(frame))
		negative = total - positive
		label_balance_rows.append(
			{
				"split": split_name,
				"label": label_name,
				"records": total,
				"positive_records": positive,
				"negative_records": negative,
				"positive_share": positive / total if total else 0.0,
			}
		)
label_balance = pd.DataFrame(label_balance_rows)

train_frame = dataset.loc[dataset["split"].eq("train")]
pos_weight_rows = []
for label_name, column in zip(LABEL_NAMES, LABEL_COLUMNS, strict=True):
	positive = int(train_frame[column].sum())
	negative = int(len(train_frame) - positive)
	pos_weight_rows.append(
		{
			"label": label_name,
			"train_positive_records": positive,
			"train_negative_records": negative,
			"pos_weight": negative / max(positive, 1),
			"note": "Use as BCEWithLogitsLoss(pos_weight=...) candidate; review after validation metrics.",
		}
	)
pos_weight = pd.DataFrame(pos_weight_rows)

split_summary = (
	dataset.groupby(["split", "sample_pool"], dropna=False)
	.size()
	.unstack(fill_value=0)
	.reset_index()
)
split_summary["records"] = split_summary.drop(columns=["split"]).sum(axis=1)
for split_name in ["train", "validation", "test"]:
	if split_name not in set(split_summary["split"]):
		raise ValueError(f"Missing split: {split_name}")

quality_rows = [
	{"metric": "input_label_rows", "value": len(labels), "note": "DeepSeek round-1 parsed label rows."},
	{"metric": "successful_label_rows", "value": int(labels["label_status"].eq("success").sum()), "note": "Rows available for training-data preparation."},
	{"metric": "training_dataset_rows", "value": len(dataset), "note": "Rows written to the MacBERT training dataset."},
	{"metric": "unique_doc_ids", "value": dataset["doc_id"].nunique(), "note": "Should equal training_dataset_rows."},
	{"metric": "train_rows", "value": int(dataset["split"].eq("train").sum()), "note": "Deterministic split size."},
	{"metric": "validation_rows", "value": int(dataset["split"].eq("validation").sum()), "note": "Deterministic split size."},
	{"metric": "test_rows", "value": int(dataset["split"].eq("test").sum()), "note": "Deterministic split size."},
	{"metric": "missing_model_text", "value": int(dataset["model_text"].str.len().eq(0).sum()), "note": "Should be zero."},
	{"metric": "min_model_text_len", "value": int(dataset["model_text_len"].min()), "note": "Shortest constructed model input."},
	{"metric": "max_model_text_len", "value": int(dataset["model_text_len"].max()), "note": "Longest constructed model input before tokenizer truncation."},
	{"metric": "random_state", "value": RANDOM_STATE, "note": "Used for deterministic hash split."},
]
quality_report = pd.DataFrame(quality_rows)

label_balance, pos_weight, split_summary, quality_report

# %% [markdown]
# ## 6. Write MacBERT Training Artifacts

# %%
training_columns = [
	"doc_id",
	"split",
	"sample_pool",
	"province",
	"year",
	"title",
	"issuing_agency",
	"publish_date",
	"source_url",
	"model_text",
	"model_text_len",
	"source_text_hash",
	"model_text_hash",
	"labels",
	"soft_labels",
	*LABEL_COLUMNS,
	*PROBABILITY_COLUMNS,
	"has_substantive_policy_tool",
	"is_srdi_related",
	"summary_reason",
	"raw_response_path",
]

for path in [
	DATASET_OUTPUT,
	TRAIN_JSONL,
	VALID_JSONL,
	TEST_JSONL,
	QUALITY_OUTPUT,
	SPLIT_SUMMARY_OUTPUT,
	LABEL_BALANCE_OUTPUT,
	POS_WEIGHT_OUTPUT,
]:
	path.parent.mkdir(parents=True, exist_ok=True)

dataset[training_columns].to_csv(DATASET_OUTPUT, index=False)
label_balance.to_csv(LABEL_BALANCE_OUTPUT, index=False)
pos_weight.to_csv(POS_WEIGHT_OUTPUT, index=False)
split_summary.to_csv(SPLIT_SUMMARY_OUTPUT, index=False)
quality_report.to_csv(QUALITY_OUTPUT, index=False)


def write_jsonl(frame: pd.DataFrame, path: Path) -> None:
	with path.open("w", encoding="utf-8") as handle:
		for record in frame[training_columns].to_dict(orient="records"):
			handle.write(json.dumps(record, ensure_ascii=False) + "\n")


write_jsonl(dataset.loc[dataset["split"].eq("train")], TRAIN_JSONL)
write_jsonl(dataset.loc[dataset["split"].eq("validation")], VALID_JSONL)
write_jsonl(dataset.loc[dataset["split"].eq("test")], TEST_JSONL)

DATASET_OUTPUT, TRAIN_JSONL, VALID_JSONL, TEST_JSONL

# %% [markdown]
# ## 7. Readiness Conclusion
#
# The DeepSeek round-1 labels are now converted into deterministic MacBERT
# training-data artifacts. The next implementation step is the actual MacBERT
# training script, which should read the JSONL split files, tokenize
# `model_text`, train a four-label classifier, and report validation/test
# metrics before predicting the full 4,475-document corpus.
