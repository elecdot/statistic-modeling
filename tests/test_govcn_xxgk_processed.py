from pathlib import Path

import pandas as pd

from statistic_modeling.policy_text_crawler.config import load_source_config
from statistic_modeling.policy_text_crawler.govcn_xxgk_pipeline import (
	aggregate_candidate_provenance,
	filter_candidates_to_target_window,
	filter_records_to_target_window,
)
from statistic_modeling.policy_text_crawler.govcn_xxgk_processed import (
	build_processed_quality_report,
	build_processed_v0,
)


ROOT = Path(__file__).resolve().parents[1]


def test_processed_v0_applies_manual_review_rule() -> None:
	details = pd.read_csv(ROOT / "data" / "interim" / "govcn_xxgk_all_policy_detail_records.csv")
	processed = build_processed_v0(details)
	quality_report = build_processed_quality_report(details, processed).set_index("metric")

	assert len(processed) == 719
	assert set(processed["parse_status"]) == {"success"}
	assert set(processed["review_status"]) == {"accepted"}
	assert processed["source_url"].is_unique
	assert processed["text_hash"].is_unique
	assert (processed["text_len"] < 200).sum() == 11
	assert "official_subject_categories" in processed
	assert "inline_attachment_titles" not in processed
	assert quality_report.loc["excluded_detail_failed", "value"] == 1
	assert quality_report.loc["rows_with_official_subject_categories", "value"] == 719
	assert "rows_with_inline_attachment_titles" not in quality_report.index


def test_target_date_window_flags_out_of_scope_rows() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	details = pd.DataFrame(
		[
			{"publish_date": "2026-04-21", "parse_status": "success", "review_status": "accepted"},
			{"publish_date": "2025-09-04", "parse_status": "success", "review_status": "accepted"},
		],
	)

	filtered = filter_records_to_target_window(details, config)

	assert filtered["in_target_date_window"].tolist() == [False, True]
	assert filtered.loc[0, "parse_status"] == "skipped_out_of_scope"
	assert filtered.loc[0, "review_status"] == "needs_review"


def test_candidate_window_filter_and_provenance_aggregation() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	candidates = pd.DataFrame(
		[
			{
				"candidate_id": "a",
				"query_batch_id": "batch_a",
				"keyword_hit": "专精特新",
				"publish_time": "2024-01-01",
				"source_url": "https://www.gov.cn/a.htm",
				"raw_json_path": "a.json",
			},
			{
				"candidate_id": "b",
				"query_batch_id": "batch_b",
				"keyword_hit": "小巨人",
				"publish_time": None,
				"cwrq": "2024-01-01",
				"source_url": "https://www.gov.cn/a.htm",
				"raw_json_path": "b.json",
			},
			{
				"candidate_id": "c",
				"query_batch_id": "batch_c",
				"keyword_hit": "中小企业",
				"publish_time": "2019-01-01",
				"source_url": "https://www.gov.cn/c.htm",
				"raw_json_path": "c.json",
			},
		],
	)

	in_window = filter_candidates_to_target_window(candidates, config)
	aggregated = aggregate_candidate_provenance(in_window)

	assert len(aggregated) == 1
	assert aggregated.loc[0, "keyword_hit"] == "专精特新;小巨人"
	assert aggregated.loc[0, "query_batch_id"] == "batch_a;batch_b"
