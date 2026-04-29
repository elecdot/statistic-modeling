import json
from pathlib import Path

import pandas as pd

from statistic_modeling.policy_text_crawler.config import load_query_batches, load_source_config
from statistic_modeling.policy_text_crawler.govcn_xxgk_gateway import build_list_payload
from statistic_modeling.policy_text_crawler.govcn_xxgk_parser import parse_detail_html, parse_list_candidates
from statistic_modeling.policy_text_crawler.govcn_xxgk_pipeline import (
	aggregate_candidate_provenance,
	build_list_page_queue,
	filter_candidates_to_target_window,
	filter_records_to_target_window,
	list_page_stop_reason,
	load_cached_list_payload,
	select_detail_candidates,
)


ROOT = Path(__file__).resolve().parents[1]


def test_config_and_query_batches_load() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batches = load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv", enabled_only=False)

	assert config.source_id == "govcn_xxgk"
	assert len(batches) == 4
	assert [batch.enabled for batch in batches].count(True) == 3


def test_queue_and_payload_mapping() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batches = load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")

	queue = build_list_page_queue(config, batches)
	assert len(queue) == sum(batch.max_pages for batch in batches)

	srdi_batch = next(batch for batch in batches if batch.keyword == "专精特新")
	payload = build_list_payload(config, srdi_batch, code="CODE", page_no=1)
	assert payload["searchFields"] == [{"fieldName": "", "searchWord": "专精特新"}]
	assert payload["isPreciseSearch"] == 0
	assert payload["sorts"] == [{"sortField": "publish_time", "sortOrder": "DESC"}]


def test_parse_cached_list_json_and_detail_html() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batch = next(
		batch
		for batch in load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")
		if batch.keyword == "中小企业"
	)
	raw_json_path = ROOT / "data" / "raw" / "json" / "central_gov_xxgk_list_中小企业.json"
	payload = json.loads(raw_json_path.read_text(encoding="utf-8"))
	candidates = parse_list_candidates(payload, config=config, batch=batch, raw_json_path=raw_json_path)

	assert len(candidates) == 10
	assert candidates[0]["source_url"].startswith("https://www.gov.cn/")
	assert candidates[0]["list_total"] is not None
	assert candidates[0]["list_page_count"] is not None
	assert len(select_detail_candidates(pd.DataFrame(candidates), max_per_batch=3)) == 3

	raw_html_path = ROOT / "data" / "raw" / "html" / "central_gov_xxgk_detail_https_www_gov_cn_zhengce_content_202503_content_7015401_htm.html"
	record = parse_detail_html(
		raw_html_path.read_text(encoding="utf-8"),
		config=config,
		candidate=candidates[0],
		raw_html_path=raw_html_path,
	)
	assert record["parse_status"] in {"success", "partial"}
	assert record["source_site"] == "gov.cn/zhengce/xxgk"
	assert record["text_hash"]


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
				"publish_time": "2024-01-01",
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


def test_legacy_cache_fallback_is_first_page_only() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batch = next(
		batch
		for batch in load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")
		if batch.keyword == "中小企业"
	)

	assert load_cached_list_payload(ROOT, config, batch, 1) is not None
	assert load_cached_list_payload(ROOT, config, batch, 50) is None


def test_list_pagination_stop_reason_uses_pager_and_date_window() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batch = next(
		batch
		for batch in load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")
		if batch.keyword == "中小企业"
	)
	payload = {
		"result": {
			"data": {
				"pager": {"pageNo": 2, "pageCount": 5, "total": 50, "pageSize": 10},
				"list": [{"publish_time": "2019-12-31"}, {"publish_time": "2020-01-01"}],
			},
		},
	}
	assert list_page_stop_reason(payload, config, batch) == "page_crossed_target_start_date"

	payload["result"]["data"]["pager"]["pageNo"] = 5
	payload["result"]["data"]["list"] = [{"publish_time": "2021-01-01"}]
	assert list_page_stop_reason(payload, config, batch) == "reached_page_count"
