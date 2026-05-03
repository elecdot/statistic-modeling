"""Predict v2 SRDI policy-tool probabilities with the trained MacBERT model."""

from __future__ import annotations

import argparse
from pathlib import Path

from manual_srdi_macbert_predict_full_corpus import (
	DEFAULT_MODEL_DIR,
	DEFAULT_RULE_KEYWORDS,
	ROOT,
	run_prediction,
)

DEFAULT_INPUT = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v2.csv"
DEFAULT_BASE_PANEL = ROOT / "data" / "processed" / "province_year_srdi_policy_intensity_v2.csv"
DEFAULT_CLASSIFIED_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v2.csv"
DEFAULT_INTENSITY_OUTPUT = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v2.csv"
DEFAULT_QUALITY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v2.csv"
DEFAULT_PROBABILITY_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v2.csv"
DEFAULT_PANEL_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_panel_coverage_v2.csv"
DEFAULT_LOG_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_v2.log"


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
	parser.add_argument(
		"--no-empty-full-text-fallback",
		action="store_true",
		help="Fail instead of using title/metadata fallback for the retained empty-full-text v2 row.",
	)
	args = parser.parse_args()
	args.allow_empty_full_text_fallback = not args.no_empty_full_text_fallback
	return args


def main() -> None:
	run_prediction(parse_args())


if __name__ == "__main__":
	main()
