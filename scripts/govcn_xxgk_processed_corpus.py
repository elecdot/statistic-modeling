"""Build processed gov.cn XXGK policy-text corpus artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from statistic_modeling.policy_text_crawler.config import find_workspace_root
from statistic_modeling.policy_text_crawler.govcn_xxgk_processed import write_processed_v0


def main() -> None:
	parser = argparse.ArgumentParser(description="Build the gov.cn XXGK processed all-policy corpus v0.")
	parser.add_argument(
		"--details-input",
		type=Path,
		default=Path("data/interim/govcn_xxgk_all_policy_detail_records.csv"),
		help="Interim all-policy detail records CSV.",
	)
	parser.add_argument(
		"--processed-output",
		type=Path,
		default=Path("data/processed/govcn_xxgk_all_policy_text_corpus_v0.csv"),
		help="Processed corpus v0 CSV output path.",
	)
	parser.add_argument(
		"--quality-output",
		type=Path,
		default=Path("outputs/govcn_xxgk_all_processed_v0_quality_report.csv"),
		help="Processed corpus v0 QA report output path.",
	)
	args = parser.parse_args()

	workspace_root = find_workspace_root()
	details_input = workspace_root / args.details_input if not args.details_input.is_absolute() else args.details_input
	processed_output = workspace_root / args.processed_output if not args.processed_output.is_absolute() else args.processed_output
	quality_output = workspace_root / args.quality_output if not args.quality_output.is_absolute() else args.quality_output

	processed, quality_report = write_processed_v0(details_input, processed_output, quality_output)
	print(f"wrote {len(processed)} rows to {processed_output}")
	print(f"wrote {len(quality_report)} rows to {quality_output}")


if __name__ == "__main__":
	main()
