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
from statistic_modeling.policy_text_crawler.govcn_xxgk_processed import (
	build_processed_quality_report,
	build_processed_v0,
)
from statistic_modeling.policy_text_crawler.manual_srdi_processed import (
	build_manual_policy_records_v0,
	build_manual_processed_quality_report,
	build_province_year_intensity_v0,
	stable_policy_id,
)


ROOT = Path(__file__).resolve().parents[1]


def test_config_and_query_batches_load() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batches = load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv", enabled_only=False)
	all_batches = load_query_batches(ROOT / "configs" / "govcn_xxgk_all_query_batches.csv", enabled_only=False)

	assert config.source_id == "govcn_xxgk"
	assert len(batches) == 4
	assert [batch.enabled for batch in batches].count(True) == 3
	assert len(all_batches) == 1
	assert all_batches[0].keyword == ""
	assert all_batches[0].max_pages == 1000


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

	all_batch = load_query_batches(ROOT / "configs" / "govcn_xxgk_all_query_batches.csv")[0]
	all_payload = build_list_payload(config, all_batch, code="CODE", page_no=1)
	assert all_payload["searchFields"] == [{"fieldName": "", "searchWord": ""}]
	assert all_payload["isPreciseSearch"] == 0
	assert all_payload["sorts"] == [{"sortField": "publish_time", "sortOrder": "DESC"}]


def test_all_policy_outputs_are_isolated_from_srdi_outputs() -> None:
	srdi_outputs = {
		"data/interim/govcn_xxgk_candidate_url_queue.csv",
		"data/interim/govcn_xxgk_policy_detail_records.csv",
		"outputs/govcn_xxgk_quality_report.csv",
	}
	all_outputs = {
		"data/interim/govcn_xxgk_all_candidate_url_queue.csv",
		"data/interim/govcn_xxgk_all_policy_detail_records.csv",
		"outputs/govcn_xxgk_all_quality_report.csv",
	}
	assert srdi_outputs.isdisjoint(all_outputs)


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


def test_parse_detail_html_extracts_official_subject_categories() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	candidate = {
		"candidate_id": "sample",
		"title": "sample",
		"source_url": "https://www.gov.cn/zhengce/content/2021-04/25/content_5601954.htm",
	}
	raw_html_path = (
		ROOT
		/ "data"
		/ "raw"
		/ "html"
		/ "central_gov_xxgk_detail_https_www_gov_cn_zhengce_content_2021_04_25_content_5601954_htm.html"
	)

	record = parse_detail_html(
		raw_html_path.read_text(encoding="utf-8"),
		config=config,
		candidate=candidate,
		raw_html_path=raw_html_path,
	)

	assert record["official_subject_categories"] == ["城乡建设、环境保护", "其他"]


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


def test_manual_srdi_processed_v0_standardizes_window_and_province_units() -> None:
	raw = pd.DataFrame(
		[
			{
				"序号": "1",
				"所属省份": "国家",
				"地区名称": "国家",
				"发文日期": "2025-01-01",
				"关键词数量清单": '{"专精特新": 2}',
				"关键词总数量": "2",
				"标题": "专精特新政策",
				"文号": "",
				"发文机构": "",
				"原文链接": "https://example.com/central",
				"摘要": "中央专精特新摘要",
			},
			{
				"序号": "2",
				"所属省份": "新疆维吾尔自治区",
				"地区名称": "新疆",
				"发文日期": "2024-01-01",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "地方政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/xj-region",
				"摘要": "摘要含专精特新",
			},
			{
				"序号": "3",
				"所属省份": "新疆生产建设兵团",
				"地区名称": "兵团",
				"发文日期": "2023-01-01",
				"关键词数量清单": '{"专精特新": 3}',
				"关键词总数量": "3",
				"标题": "兵团政策",
				"文号": "兵工信",
				"发文机构": "兵团工信局",
				"原文链接": "https://example.com/xj-bingtuan",
				"摘要": "专精特新摘要",
			},
			{
				"序号": "4",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2026-01-01",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "2026政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/out-of-window",
				"摘要": "专精特新摘要",
			},
		]
	)

	processed = build_manual_policy_records_v0(raw)

	assert len(processed) == 3
	assert processed.loc[processed["source_label_original"].eq("国家"), "province"].item() == "central"
	assert set(processed.loc[processed["source_label_original"].str.contains("新疆"), "province"]) == {"新疆"}
	assert set(processed["publish_year"]) == {2023, 2024, 2025}
	assert set(processed["review_status"]) == {"accepted"}
	assert processed.loc[processed["source_url"].eq("https://example.com/central"), "policy_id"].item() == stable_policy_id(
		"https://example.com/central"
	)


def test_manual_srdi_intensity_excludes_central_and_balances_years() -> None:
	raw = pd.read_excel(ROOT / "data" / "interim" / "manual_policy_all_keyword_srdi.xlsx", sheet_name="tableData", dtype=str)
	processed = build_manual_policy_records_v0(raw)
	intensity = build_province_year_intensity_v0(processed)
	quality_report = build_manual_processed_quality_report(raw, processed, intensity).set_index("metric")

	assert len(processed) == 4475
	assert processed["source_url"].is_unique
	assert "central" in set(processed["province"])
	assert processed.loc[processed["source_label_original"].isin(["新疆维吾尔自治区", "新疆生产建设兵团"]), "province"].eq("新疆").all()
	assert len(intensity) == 186
	assert set(intensity["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert intensity["province"].nunique() == 31
	assert "central" not in set(intensity["province"])
	assert "新疆" in set(intensity["province"])
	assert quality_report.loc["excluded_outside_analysis_window", "value"] == 167
	assert quality_report.loc["local_province_units", "value"] == 31


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


def test_source_manifest_globs_do_not_mix_srdi_and_all_policy_cache() -> None:
	manifest = pd.read_csv(ROOT / "data" / "source-manifest.csv").fillna("")
	assert len(manifest) == 27
	assert {
		"generated_by",
		"config_files",
		"upstream_files",
		"quality_report",
		"collection_status",
		"review_status",
		"record_count",
	}.issubset(manifest.columns)

	def resolve_grouped_globs(value: str) -> list[Path]:
		matches: list[Path] = []
		for pattern in value.split(";"):
			pattern = pattern.strip()
			if pattern:
				matches.extend((ROOT / "data").glob(pattern))
		return sorted(matches)

	srdi_json_row = manifest.loc[manifest["source_name"] == "政府信息公开平台_中国政府网_Crawler列表JSON"].iloc[0]
	all_json_row = manifest.loc[manifest["source_name"] == "政府信息公开平台_中国政府网_AllPolicy列表JSON"].iloc[0]

	srdi_matches = resolve_grouped_globs(srdi_json_row["local_file"])
	all_matches = resolve_grouped_globs(all_json_row["local_file"])

	assert srdi_matches
	assert len(all_matches) == 76
	assert all("govcn_xxgk_all" not in path.name for path in srdi_matches)
	assert all("govcn_xxgk_all" in path.name for path in all_matches)


def test_manual_srdi_text_mining_outputs_are_consistent() -> None:
	row_features = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_text_features_v0.csv")
	province_year_features = pd.read_csv(ROOT / "data" / "processed" / "province_year_srdi_text_features_v0.csv")
	quality_report = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_text_mining_v0_quality_report.csv").set_index("metric")
	dictionary = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_v0.csv")
	dictionary_coverage = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_v0.csv")
	revision_effect = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_dictionary_revision_effect_v0.csv").set_index("metric")
	keyword_quality = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_keyword_quality_check_v0.csv")
	no_hit_records = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_v0.csv")
	no_hit_sample = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_review_sample_v0.csv")

	assert len(row_features) == 4475
	assert len(province_year_features) == 186
	assert row_features["policy_id"].is_unique
	assert province_year_features["province"].nunique() == 31
	assert set(province_year_features["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert {"supply", "demand", "environment"} == set(dictionary["category"])
	assert len(dictionary_coverage) == 85
	assert (dictionary_coverage["records_hit"] > 0).all()
	assert revision_effect.loc["policy_records_without_tool_hit", "delta"] == -81
	assert len(keyword_quality) == 85
	assert keyword_quality["needs_review"].sum() == 50
	assert len(no_hit_records) == 271
	assert len(no_hit_sample) == 30
	assert quality_report.loc["row_feature_records", "value"] == 4475
	assert quality_report.loc["province_year_feature_records", "value"] == 186
	assert quality_report.loc["no_tool_hit_review_sample_records", "value"] == 30
	assert quality_report.loc["zero_coverage_terms", "value"] == 0


def test_legacy_cache_fallback_is_first_page_only() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	batch = next(
		batch
		for batch in load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")
		if batch.keyword == "中小企业"
	)

	assert load_cached_list_payload(ROOT, config, batch, 1) is not None
	assert load_cached_list_payload(ROOT, config, batch, 50) is None


def test_planned_cache_paths_remain_compatible_with_manifest_narrowing() -> None:
	config = load_source_config(ROOT / "configs" / "govcn_xxgk_sources.toml")
	srdi_batch = next(
		batch
		for batch in load_query_batches(ROOT / "configs" / "govcn_xxgk_query_batches.csv")
		if batch.query_batch_id == "govcn_xxgk_fulltext_srdi_time_pilot"
	)
	all_batch = load_query_batches(ROOT / "configs" / "govcn_xxgk_all_query_batches.csv")[0]

	assert load_cached_list_payload(ROOT, config, srdi_batch, 1) is not None
	assert load_cached_list_payload(ROOT, config, all_batch, 1) is not None


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
