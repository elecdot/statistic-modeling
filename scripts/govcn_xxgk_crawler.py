"""Command-line entry point for the gov.cn XXGK pilot crawler."""

from __future__ import annotations

import argparse
from pathlib import Path

from statistic_modeling.policy_text_crawler.config import find_workspace_root, load_query_batches, load_source_config
from statistic_modeling.policy_text_crawler.govcn_xxgk_pipeline import (
	aggregate_candidate_provenance,
	build_list_page_queue,
	collect_list_candidates_from_cache,
	fetch_and_parse_detail_records_live,
	fetch_list_candidates_live,
	filter_candidates_to_target_window,
	filter_records_to_target_window,
	parse_detail_records_from_cache,
	quality_summary,
	select_detail_candidates,
)


def _default_paths(workspace_root: Path) -> tuple[Path, Path]:
	return workspace_root / "configs" / "govcn_xxgk_sources.toml", workspace_root / "configs" / "govcn_xxgk_query_batches.csv"


def main() -> None:
	parser = argparse.ArgumentParser(description="Build or run the gov.cn XXGK pilot crawler.")
	parser.add_argument("--source-config", type=Path, help="Path to govcn_xxgk_sources.toml.")
	parser.add_argument("--query-batches", type=Path, help="Path to govcn_xxgk_query_batches.csv.")
	parser.add_argument("--include-disabled", action="store_true", help="Include disabled query batches in queue output.")
	subparsers = parser.add_subparsers(dest="command", required=True)

	queue_parser = subparsers.add_parser("queue", help="Build the reviewed list-request queue without fetching.")
	queue_parser.add_argument("--output", type=Path, help="Optional CSV output path.")

	run_parser = subparsers.add_parser("run", help="Run cache-first parsing, or live fetching with --fetch-live.")
	run_parser.add_argument("--fetch-live", action="store_true", help="Send live requests and archive raw artifacts.")
	run_parser.add_argument("--max-pages-override", type=int, help="Temporary live-run page cap override for reviewed probes.")
	run_parser.add_argument("--candidates-output", type=Path, default=Path("data/interim/govcn_xxgk_candidate_url_queue.csv"))
	run_parser.add_argument("--details-output", type=Path, default=Path("data/interim/govcn_xxgk_policy_detail_records.csv"))
	run_parser.add_argument("--quality-output", type=Path, default=Path("outputs/govcn_xxgk_quality_report.csv"))
	run_parser.add_argument("--keep-out-of-window", action="store_true", help="Keep rows outside the configured target date window.")
	run_parser.add_argument(
		"--max-details-per-batch",
		type=int,
		default=3,
		help="Pilot detail-page cap per query batch. Use -1 to parse/fetch all candidates.",
	)

	args = parser.parse_args()
	workspace_root = find_workspace_root()
	default_source_config, default_query_batches = _default_paths(workspace_root)
	config = load_source_config(args.source_config or default_source_config)
	batches = load_query_batches(args.query_batches or default_query_batches, enabled_only=not args.include_disabled)

	if args.command == "queue":
		queue = build_list_page_queue(config, batches)
		if args.output:
			output = workspace_root / args.output if not args.output.is_absolute() else args.output
			output.parent.mkdir(parents=True, exist_ok=True)
			queue.to_csv(output, index=False)
			print(f"wrote {len(queue)} queue rows to {output}")
		else:
			print(queue.to_csv(index=False), end="")
		return

	if args.fetch_live:
		candidates = fetch_list_candidates_live(workspace_root, config, batches, max_pages_override=args.max_pages_override)
		in_window_candidates = filter_candidates_to_target_window(candidates, config)
		detail_candidates = aggregate_candidate_provenance(
			select_detail_candidates(
				in_window_candidates,
				max_per_batch=None if args.max_details_per_batch < 0 else args.max_details_per_batch,
			),
		)
		details = fetch_and_parse_detail_records_live(workspace_root, config, detail_candidates)
	else:
		candidates = collect_list_candidates_from_cache(workspace_root, config, batches)
		in_window_candidates = filter_candidates_to_target_window(candidates, config)
		detail_candidates = aggregate_candidate_provenance(
			select_detail_candidates(
				in_window_candidates,
				max_per_batch=None if args.max_details_per_batch < 0 else args.max_details_per_batch,
			),
		)
		details = parse_detail_records_from_cache(workspace_root, config, detail_candidates)

	details = filter_records_to_target_window(details, config)
	if not args.keep_out_of_window and "in_target_date_window" in details:
		details = details[details["in_target_date_window"]].reset_index(drop=True)

	for frame, output in [
		(candidates, args.candidates_output),
		(details, args.details_output),
		(quality_summary(candidates, details), args.quality_output),
	]:
		output_path = workspace_root / output if not output.is_absolute() else output
		output_path.parent.mkdir(parents=True, exist_ok=True)
		frame.to_csv(output_path, index=False)
		print(f"wrote {len(frame)} rows to {output_path}")


if __name__ == "__main__":
	main()
