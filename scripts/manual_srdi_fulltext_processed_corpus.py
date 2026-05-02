"""Build processed manual SRDI full-text policy records."""

from __future__ import annotations

import argparse
from pathlib import Path

from statistic_modeling.policy_text_crawler.config import find_workspace_root
from statistic_modeling.policy_text_crawler.manual_srdi_processed import write_manual_fulltext_processed_v1


def main() -> None:
	parser = argparse.ArgumentParser(description="Build processed full-text v1 outputs from the manual SRDI workbook.")
	parser.add_argument(
		"--workbook-input",
		type=Path,
		default=Path("data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx"),
		help="Manual SRDI keyword policy workbook with full text.",
	)
	parser.add_argument(
		"--processed-output",
		type=Path,
		default=Path("data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv"),
		help="Processed manual SRDI full-text policy records v1 CSV output path.",
	)
	parser.add_argument(
		"--quality-output",
		type=Path,
		default=Path("outputs/manual_policy_srdi_processed_fulltext_v1_quality_report.csv"),
		help="Processed manual SRDI full-text v1 QA report output path.",
	)
	args = parser.parse_args()

	workspace_root = find_workspace_root()
	workbook_input = workspace_root / args.workbook_input if not args.workbook_input.is_absolute() else args.workbook_input
	processed_output = workspace_root / args.processed_output if not args.processed_output.is_absolute() else args.processed_output
	quality_output = workspace_root / args.quality_output if not args.quality_output.is_absolute() else args.quality_output

	processed, quality_report = write_manual_fulltext_processed_v1(
		workbook_input,
		processed_output,
		quality_output,
	)
	print(f"wrote {len(processed)} rows to {processed_output}")
	print(f"wrote {len(quality_report)} rows to {quality_output}")


if __name__ == "__main__":
	main()
