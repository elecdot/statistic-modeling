"""Predict full-corpus SRDI policy-tool probabilities with the trained MacBERT model."""

from __future__ import annotations

import argparse
import hashlib
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from manual_srdi_train_macbert_multilabel import (
	LABEL_NAMES,
	configure_model_loading_noise,
	hard_other_rule,
	require_training_deps,
	select_device,
	should_use_safetensors,
	sigmoid,
	setup_logging,
)


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv"
DEFAULT_BASE_PANEL = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v0.csv"
DEFAULT_RULE_KEYWORDS = ROOT / "configs" / "manual_srdi_label_rule_keywords_v1.csv"
DEFAULT_MODEL_DIR = ROOT / "outputs" / "manual_srdi_macbert_multilabel_v1"
DEFAULT_CLASSIFIED_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v1.csv"
DEFAULT_INTENSITY_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v1.csv"
DEFAULT_QUALITY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v1.csv"
DEFAULT_PROBABILITY_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v1.csv"
DEFAULT_PANEL_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_panel_coverage_v1.csv"
DEFAULT_LOG_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_v1.log"

FRONT_CHARS = 1200
KEYWORD_CONTEXT_CHARS = 1200
KEYWORD_CONTEXT_WINDOW_LEFT = 120
KEYWORD_CONTEXT_WINDOW_RIGHT = 260
HIGH_CONFIDENCE_THRESHOLD = 0.75

CORE_COLUMNS = [
	"policy_id",
	"province",
	"source_label_original",
	"jurisdiction_type",
	"publish_date",
	"publish_year",
	"title",
	"agency",
	"source_url",
	"full_text_len",
]


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
	parser.add_argument("--base-panel", type=Path, default=DEFAULT_BASE_PANEL)
	parser.add_argument("--rule-keywords", type=Path, default=DEFAULT_RULE_KEYWORDS)
	parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
	parser.add_argument("--classified-output", type=Path, default=DEFAULT_CLASSIFIED_OUTPUT)
	parser.add_argument("--intensity-output", type=Path, default=DEFAULT_INTENSITY_OUTPUT)
	parser.add_argument("--quality-output", type=Path, default=DEFAULT_QUALITY_OUTPUT)
	parser.add_argument("--probability-summary-output", type=Path, default=DEFAULT_PROBABILITY_SUMMARY_OUTPUT)
	parser.add_argument("--panel-coverage-output", type=Path, default=DEFAULT_PANEL_COVERAGE_OUTPUT)
	parser.add_argument("--log-output", type=Path, default=DEFAULT_LOG_OUTPUT)
	parser.add_argument("--max-length", type=int, default=512)
	parser.add_argument("--batch-size", type=int, default=16)
	parser.add_argument("--progress-every-batches", type=int, default=25)
	parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
	parser.add_argument("--limit", type=int, default=None, help="Optional cap for local smoke runs.")
	parser.add_argument("--show-download-progress", action="store_true", help="Show Hugging Face progress and advisory logs for debugging.")
	parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write QA only; do not load model or predict.")
	return parser.parse_args()


def normalize_text(value: Any) -> str:
	text = "" if pd.isna(value) else str(value)
	text = re.sub(r"\s+", "\n", text)
	return text.strip()


def stable_hash(value: str, length: int = 16) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def get_context_terms(rule_keywords: pd.DataFrame) -> list[str]:
	terms = (
		rule_keywords.loc[rule_keywords["keep_for_sampling"].astype(str).str.lower().eq("true"), "term"]
		.dropna()
		.astype(str)
		.str.strip()
	)
	return sorted({term for term in terms if term}, key=lambda item: (-len(item), item))


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


def make_model_text(row: pd.Series, context_terms: list[str]) -> str:
	text = normalize_text(row["full_text"])
	front = text[:FRONT_CHARS]
	keyword_context = collect_keyword_context(text, context_terms)
	parts = [
		f"标题：{normalize_text(row['title'])}",
		f"发文机关：{normalize_text(row['agency'])}",
		f"省份：{normalize_text(row['province'])}",
		f"年份：{int(row['publish_year'])}",
		"",
		"正文前部：",
		front,
	]
	if keyword_context:
		parts.extend(["", "关键词附近内容：", keyword_context])
	return "\n".join(parts).strip()


def validate_input(frame: pd.DataFrame) -> None:
	missing_columns = [column for column in [*CORE_COLUMNS, "full_text"] if column not in frame.columns]
	if missing_columns:
		raise ValueError(f"Input corpus is missing columns: {missing_columns}")
	if frame["policy_id"].duplicated().any():
		duplicates = frame.loc[frame["policy_id"].duplicated(), "policy_id"].head(10).tolist()
		raise ValueError(f"Input corpus has duplicate policy_id values: {duplicates}")
	if frame["full_text"].fillna("").astype(str).str.strip().eq("").any():
		missing = frame.loc[frame["full_text"].fillna("").astype(str).str.strip().eq(""), "policy_id"].head(10).tolist()
		raise ValueError(f"Input corpus has empty full_text rows: {missing}")


def predict_probabilities(
	*,
	texts: list[str],
	model_dir: Path,
	max_length: int,
	batch_size: int,
	device_name: str,
	quiet_model_loading: bool,
	progress_every_batches: int,
	logger: Any,
) -> tuple[np.ndarray, str]:
	deps = require_training_deps(quiet=quiet_model_loading)
	torch = deps.torch
	device = select_device(torch, device_name)
	tokenizer = deps.AutoTokenizer.from_pretrained(model_dir)
	model = deps.AutoModelForSequenceClassification.from_pretrained(
		model_dir,
		use_safetensors=should_use_safetensors(str(model_dir)),
	)
	model.to(device)
	model.eval()

	probabilities: list[np.ndarray] = []
	total_batches = max((len(texts) + batch_size - 1) // batch_size, 1)
	started = time.perf_counter()
	with torch.no_grad():
		for batch_index, start in enumerate(range(0, len(texts), batch_size), start=1):
			batch_texts = texts[start : start + batch_size]
			encoded = tokenizer(
				batch_texts,
				truncation=True,
				padding=True,
				max_length=max_length,
				return_tensors="pt",
			)
			encoded = {key: value.to(device) for key, value in encoded.items()}
			logits = model(**encoded).logits.detach().cpu().numpy()
			probabilities.append(sigmoid(logits))
			if batch_index == 1 or batch_index == total_batches or batch_index % progress_every_batches == 0:
				done = min(start + batch_size, len(texts))
				elapsed = time.perf_counter() - started
				rate = done / max(elapsed, 1e-9)
				remaining = (len(texts) - done) / max(rate, 1e-9)
				logger.info(
					"predicted batch=%s/%s rows=%s/%s elapsed_seconds=%.1f eta_seconds=%.1f",
					batch_index,
					total_batches,
					done,
					len(texts),
					elapsed,
					remaining,
				)
	return np.vstack(probabilities), str(device)


def add_prediction_columns(frame: pd.DataFrame, probabilities: np.ndarray) -> pd.DataFrame:
	output = frame[CORE_COLUMNS].copy()
	for index, label in enumerate(LABEL_NAMES):
		output[f"p_{label}"] = probabilities[:, index]
	binary = hard_other_rule(probabilities)
	for index, label in enumerate(LABEL_NAMES):
		output[f"{label}_label"] = binary[:, index]
	output["max_tool_prob"] = output[["p_supply", "p_demand", "p_environment"]].max(axis=1)
	output["tool_probability_sum"] = output[["p_supply", "p_demand", "p_environment"]].sum(axis=1)
	output["any_tool_label"] = output[["supply_label", "demand_label", "environment_label"]].max(axis=1)
	output["valid_tool_policy"] = ((output["other_label"].eq(0)) & (output["any_tool_label"].eq(1))).astype(int)
	output["model_text_hash"] = frame["model_text"].map(stable_hash)
	return output


def summarize_probabilities(classified: pd.DataFrame) -> pd.DataFrame:
	rows: list[dict[str, Any]] = []
	for label in LABEL_NAMES:
		series = classified[f"p_{label}"]
		rows.append(
			{
				"label": label,
				"count": int(series.count()),
				"mean": float(series.mean()),
				"std": float(series.std(ddof=0)),
				"min": float(series.min()),
				"q25": float(series.quantile(0.25)),
				"median": float(series.median()),
				"q75": float(series.quantile(0.75)),
				"max": float(series.max()),
				"hard_label_count": int(classified[f"{label}_label"].sum()),
				"hard_label_share": float(classified[f"{label}_label"].mean()),
			}
		)
	return pd.DataFrame(rows)


def build_intensity_table(classified: pd.DataFrame, base_panel: pd.DataFrame) -> pd.DataFrame:
	local = classified.loc[classified["jurisdiction_type"].eq("local") & classified["province"].ne("central")].copy()
	local["publish_year"] = local["publish_year"].astype(int)
	for label in ["supply", "demand", "environment", "other"]:
		local[f"filtered_p_{label}"] = local[f"p_{label}"] * local["valid_tool_policy"]
		local[f"high_confidence_{label}_policy_count"] = (local[f"p_{label}"] >= HIGH_CONFIDENCE_THRESHOLD).astype(int)

	grouped = (
		local.groupby(["province", "publish_year"], as_index=False)
		.agg(
			macbert_policy_records=("policy_id", "size"),
			valid_tool_policy_count=("valid_tool_policy", "sum"),
			other_label_policy_count=("other_label", "sum"),
			sum_p_supply=("p_supply", "sum"),
			sum_p_demand=("p_demand", "sum"),
			sum_p_environment=("p_environment", "sum"),
			sum_p_other=("p_other", "sum"),
			avg_p_supply=("p_supply", "mean"),
			avg_p_demand=("p_demand", "mean"),
			avg_p_environment=("p_environment", "mean"),
			avg_p_other=("p_other", "mean"),
			filtered_sum_p_supply=("filtered_p_supply", "sum"),
			filtered_sum_p_demand=("filtered_p_demand", "sum"),
			filtered_sum_p_environment=("filtered_p_environment", "sum"),
			filtered_sum_p_other=("filtered_p_other", "sum"),
			supply_label_policy_count=("supply_label", "sum"),
			demand_label_policy_count=("demand_label", "sum"),
			environment_label_policy_count=("environment_label", "sum"),
			high_confidence_supply_policy_count=("high_confidence_supply_policy_count", "sum"),
			high_confidence_demand_policy_count=("high_confidence_demand_policy_count", "sum"),
			high_confidence_environment_policy_count=("high_confidence_environment_policy_count", "sum"),
		)
	)

	output = base_panel[["province", "publish_year", "srdi_policy_count", "log_srdi_policy_count_plus1"]].merge(
		grouped,
		on=["province", "publish_year"],
		how="left",
		validate="one_to_one",
	)
	count_columns = [column for column in output.columns if column.endswith("_count") or column.endswith("_records")]
	probability_columns = [column for column in output.columns if column.startswith("sum_") or column.startswith("avg_") or column.startswith("filtered_sum_")]
	output[count_columns + probability_columns] = output[count_columns + probability_columns].fillna(0)

	raw_tool_sum = output[["sum_p_supply", "sum_p_demand", "sum_p_environment"]].sum(axis=1).replace(0, np.nan)
	filtered_tool_sum = output[["filtered_sum_p_supply", "filtered_sum_p_demand", "filtered_sum_p_environment"]].sum(axis=1).replace(0, np.nan)
	for label in ["supply", "demand", "environment"]:
		output[f"{label}_probability_share"] = (output[f"sum_p_{label}"] / raw_tool_sum).fillna(0)
		output[f"filtered_{label}_probability_share"] = (output[f"filtered_sum_p_{label}"] / filtered_tool_sum).fillna(0)
		output[f"filtered_avg_p_{label}"] = (
			output[f"filtered_sum_p_{label}"] / output["valid_tool_policy_count"].replace(0, np.nan)
		).fillna(0)
	output["valid_tool_policy_share"] = (output["valid_tool_policy_count"] / output["macbert_policy_records"].replace(0, np.nan)).fillna(0)
	return output.sort_values(["province", "publish_year"]).reset_index(drop=True)


def build_panel_coverage(intensity: pd.DataFrame) -> pd.DataFrame:
	return intensity[
		[
			"province",
			"publish_year",
			"srdi_policy_count",
			"macbert_policy_records",
			"valid_tool_policy_count",
			"valid_tool_policy_share",
		]
	].copy()


def build_quality_report(
	*,
	args: argparse.Namespace,
	input_rows: int,
	classified: pd.DataFrame,
	intensity: pd.DataFrame,
	device: str,
	elapsed_seconds: float,
	dry_run: bool,
) -> pd.DataFrame:
	metrics = [
		("model_dir", str(args.model_dir), "Model checkpoint used for prediction."),
		("input_rows", input_rows, "Input full-text policy records."),
		("prediction_rows", len(classified), "Row-level prediction records."),
		("policy_id_unique", bool(classified["policy_id"].is_unique), "Whether policy_id is unique in predictions."),
		("central_rows", int(classified["jurisdiction_type"].eq("central").sum()), "Central records retained in row-level predictions."),
		("local_rows", int(classified["jurisdiction_type"].eq("local").sum()), "Local records used for province-year aggregation."),
		("province_year_rows", len(intensity), "Province-year intensity rows."),
		("province_units", int(intensity["province"].nunique()), "Local province units in intensity table."),
		("year_min", int(intensity["publish_year"].min()) if len(intensity) else "", "Minimum year in intensity table."),
		("year_max", int(intensity["publish_year"].max()) if len(intensity) else "", "Maximum year in intensity table."),
		("other_exclusion_rows", int(classified["other_label"].sum()), "Rows marked as other by the hard rule."),
		("valid_tool_policy_rows", int(classified["valid_tool_policy"].sum()), "Rows retained as valid tool policies by the hard rule."),
		("missing_title", int(classified["title"].isna().sum()), "Missing title count."),
		("missing_agency", int(classified["agency"].isna().sum()), "Missing agency count."),
		("device", device, "Resolved prediction device."),
		("dry_run", dry_run, "True means no model was loaded or predictions generated."),
		("elapsed_seconds", round(elapsed_seconds, 2), "Prediction script elapsed seconds."),
	]
	for label in LABEL_NAMES:
		metrics.append((f"{label}_label_rows", int(classified[f"{label}_label"].sum()), f"Hard-label positive rows for {label}."))
		metrics.append((f"{label}_label_share", float(classified[f"{label}_label"].mean()), f"Hard-label positive share for {label}."))
	return pd.DataFrame([{"metric": metric, "value": value, "note": note} for metric, value, note in metrics])


def run_prediction(args: argparse.Namespace) -> None:
	started = time.perf_counter()
	logger = setup_logging(args.log_output)
	quiet_model_loading = not args.show_download_progress
	configure_model_loading_noise(quiet=quiet_model_loading)
	logger.info("Starting MacBERT full-corpus prediction")

	corpus = pd.read_csv(args.input)
	if args.limit is not None:
		corpus = corpus.head(args.limit).copy()
	base_panel = pd.read_csv(args.base_panel)
	rule_keywords = pd.read_csv(args.rule_keywords)
	validate_input(corpus)
	context_terms = get_context_terms(rule_keywords)
	corpus = corpus.copy()
	corpus["model_text"] = corpus.apply(make_model_text, axis=1, context_terms=context_terms)
	logger.info("Prepared model texts rows=%s context_terms=%s", len(corpus), len(context_terms))

	if args.dry_run:
		empty_classified = corpus[CORE_COLUMNS].copy()
		for label in LABEL_NAMES:
			empty_classified[f"p_{label}"] = 0.0
			empty_classified[f"{label}_label"] = 0
		empty_classified["max_tool_prob"] = 0.0
		empty_classified["tool_probability_sum"] = 0.0
		empty_classified["any_tool_label"] = 0
		empty_classified["valid_tool_policy"] = 0
		intensity = build_intensity_table(empty_classified, base_panel)
		args.quality_output.parent.mkdir(parents=True, exist_ok=True)
		build_quality_report(
			args=args,
			input_rows=len(corpus),
			classified=empty_classified,
			intensity=intensity,
			device="not_resolved",
			elapsed_seconds=time.perf_counter() - started,
			dry_run=True,
		).to_csv(args.quality_output, index=False)
		logger.info("Dry run OK. Wrote quality report: %s", args.quality_output)
		return

	probabilities, device = predict_probabilities(
		texts=corpus["model_text"].tolist(),
		model_dir=args.model_dir,
		max_length=args.max_length,
		batch_size=args.batch_size,
		device_name=args.device,
		quiet_model_loading=quiet_model_loading,
		progress_every_batches=args.progress_every_batches,
		logger=logger,
	)
	classified = add_prediction_columns(corpus, probabilities)
	intensity = build_intensity_table(classified, base_panel)
	probability_summary = summarize_probabilities(classified)
	panel_coverage = build_panel_coverage(intensity)
	quality = build_quality_report(
		args=args,
		input_rows=len(corpus),
		classified=classified,
		intensity=intensity,
		device=device,
		elapsed_seconds=time.perf_counter() - started,
		dry_run=False,
	)

	for path, frame in [
		(args.classified_output, classified),
		(args.intensity_output, intensity),
		(args.probability_summary_output, probability_summary),
		(args.panel_coverage_output, panel_coverage),
		(args.quality_output, quality),
	]:
		path.parent.mkdir(parents=True, exist_ok=True)
		frame.to_csv(path, index=False)
		logger.info("Wrote %s rows to %s", len(frame), path)


def main() -> None:
	run_prediction(parse_args())


if __name__ == "__main__":
	main()
