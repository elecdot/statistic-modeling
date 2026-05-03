"""Build the v2 manual SRDI full-text corpus for the 2019-2024 policy window."""

from __future__ import annotations

import argparse
from pathlib import Path

from statistic_modeling.policy_text_crawler.config import find_workspace_root
from statistic_modeling.policy_text_crawler.manual_srdi_processed import write_manual_fulltext_processed_v2


def resolve_workspace_path(workspace_root: Path, path: Path) -> Path:
	"""Resolve repository-relative CLI paths against the workspace root."""
	return workspace_root / path if not path.is_absolute() else path


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--current-workbook-input",
		type=Path,
		default=Path("data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx"),
		help="Current manual SRDI full-text workbook covering 2020 onward.",
	)
	parser.add_argument(
		"--supplement-2019-input",
		type=Path,
		default=Path("data/interim/manual_policy_all_keyword_srdi_2019_supplementary.xlsx"),
		help="Supplementary 2019 manual SRDI full-text workbook.",
	)
	parser.add_argument(
		"--processed-output",
		type=Path,
		default=Path("data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv"),
		help="Processed 2019-2024 manual SRDI full-text v2 corpus output path.",
	)
	parser.add_argument(
		"--intensity-output",
		type=Path,
		default=Path("data/processed/province_year_srdi_policy_intensity_v2.csv"),
		help="Balanced 2019-2024 province-year SRDI policy-count v2 output path.",
	)
	parser.add_argument(
		"--quality-output",
		type=Path,
		default=Path("outputs/manual_policy_srdi_processed_fulltext_v2_quality_report.csv"),
		help="Processed full-text v2 QA report output path.",
	)
	parser.add_argument(
		"--supplement-quality-output",
		type=Path,
		default=Path("outputs/manual_policy_srdi_2019_supplement_quality_report_v2.csv"),
		help="2019 supplementary workbook QA report output path.",
	)
	parser.add_argument(
		"--jurisdiction-candidates-output",
		type=Path,
		default=Path("outputs/manual_policy_srdi_v2_jurisdiction_review_candidates.csv"),
		help="2019 rows needing later jurisdiction review.",
	)
	parser.add_argument(
		"--jurisdiction-overrides",
		type=Path,
		default=Path("configs/manual_srdi_jurisdiction_overrides_v2.csv"),
		help="Reviewed source-label jurisdiction correction CSV for the v2 corpus.",
	)
	args = parser.parse_args()

	workspace_root = find_workspace_root()
	processed, intensity, quality, supplement_quality, jurisdiction_candidates = write_manual_fulltext_processed_v2(
		resolve_workspace_path(workspace_root, args.current_workbook_input),
		resolve_workspace_path(workspace_root, args.supplement_2019_input),
		resolve_workspace_path(workspace_root, args.processed_output),
		resolve_workspace_path(workspace_root, args.intensity_output),
		resolve_workspace_path(workspace_root, args.quality_output),
		resolve_workspace_path(workspace_root, args.supplement_quality_output),
		resolve_workspace_path(workspace_root, args.jurisdiction_candidates_output),
		resolve_workspace_path(workspace_root, args.jurisdiction_overrides),
	)
	print(f"wrote {len(processed)} rows to {resolve_workspace_path(workspace_root, args.processed_output)}")
	print(f"wrote {len(intensity)} rows to {resolve_workspace_path(workspace_root, args.intensity_output)}")
	print(f"wrote {len(quality)} rows to {resolve_workspace_path(workspace_root, args.quality_output)}")
	print(
		f"wrote {len(supplement_quality)} rows to "
		f"{resolve_workspace_path(workspace_root, args.supplement_quality_output)}"
	)
	print(
		f"wrote {len(jurisdiction_candidates)} rows to "
		f"{resolve_workspace_path(workspace_root, args.jurisdiction_candidates_output)}"
	)


if __name__ == "__main__":
	main()
