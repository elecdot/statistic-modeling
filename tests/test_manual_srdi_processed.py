from pathlib import Path

import pandas as pd

from statistic_modeling.policy_text_crawler.manual_srdi_processed import (
	build_2019_supplement_quality_report_v2,
	build_manual_fulltext_policy_records_v1,
	build_manual_fulltext_policy_records_v2,
	build_manual_fulltext_processed_quality_report,
	build_manual_fulltext_processed_quality_report_v2,
	build_manual_policy_records_v0,
	build_manual_processed_quality_report,
	build_province_year_intensity_v0,
	build_province_year_intensity_v2,
	build_v2_jurisdiction_review_candidates,
	load_jurisdiction_overrides,
	stable_policy_id,
)


ROOT = Path(__file__).resolve().parents[1]


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


def test_manual_srdi_fulltext_processed_v1_standardizes_full_text_records() -> None:
	raw = pd.DataFrame(
		[
			{
				"序号": "1",
				"所属省份": "国家",
				"地区名称": "国家",
				"发文日期": "2025-01-01",
				"关键词数量清单": '{"专精特新": 2}',
				"关键词总数量": "2",
				"标题": "政策标题",
				"文号": "",
				"发文机构": "",
				"原文链接": "https://example.com/central-fulltext",
				"原文": "中央专精特新全文",
			},
			{
				"序号": "2",
				"所属省份": "新疆生产建设兵团",
				"地区名称": "兵团",
				"发文日期": "2024-01-01",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "兵团专精特新政策",
				"文号": "",
				"发文机构": "兵团工信局",
				"原文链接": "https://example.com/xj-fulltext",
				"原文": "政策全文",
			},
			{
				"序号": "3",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2026-01-01",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "2026政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/out-of-window-fulltext",
				"原文": "专精特新全文",
			},
		]
	)

	processed = build_manual_fulltext_policy_records_v1(raw)
	quality_report = build_manual_fulltext_processed_quality_report(raw, processed).set_index("metric")

	assert len(processed) == 2
	assert "full_text" in processed
	assert processed.loc[processed["source_label_original"].eq("国家"), "province"].item() == "central"
	assert processed.loc[processed["source_label_original"].eq("新疆生产建设兵团"), "province"].item() == "新疆"
	assert processed.loc[processed["source_url"].eq("https://example.com/central-fulltext"), "full_text_contains_srdi"].item()
	assert processed.loc[processed["source_url"].eq("https://example.com/xj-fulltext"), "title_or_full_text_contains_srdi"].item()
	assert quality_report.loc["excluded_outside_analysis_window", "value"] == 1
	assert quality_report.loc["missing_full_text", "value"] == 0


def test_manual_srdi_fulltext_v2_standardizes_2019_supplement_and_window() -> None:
	current_raw = pd.DataFrame(
		[
			{
				"序号": "1",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2024-01-01",
				"关键词数量清单": '{"专精特新": 2}',
				"关键词总数量": "2",
				"标题": "广东专精特新政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/current-2024",
				"原文": "支持专精特新企业。",
			},
			{
				"序号": "2",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2019-12-31",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "当前表2019政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/current-2019",
				"原文": "专精特新全文。",
			},
			{
				"序号": "3",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2025-01-01",
				"关键词数量清单": '{"专精特新": 1}',
				"关键词总数量": "1",
				"标题": "2025政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/current-2025",
				"原文": "专精特新全文。",
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
				"原文链接": "https://example.com/current-2026",
				"原文": "专精特新全文。",
			},
		]
	)
	supplement_raw = pd.DataFrame(
		[
			{
				"序号": "1",
				"所属省份": "国家",
				"地区名称": "国家",
				"发文日期": "2019-01-01",
				"标题": "中央专精特新政策",
				"文号": "",
				"发文机构": "工业和信息化部",
				"原文链接": "https://example.com/supplement-central-2019",
				"原文文本": "中央专精特新全文。",
			},
			{
				"序号": "2",
				"所属省份": "新疆生产建设兵团",
				"地区名称": "兵团",
				"发文日期": "2019-02-01",
				"标题": "兵团专精特新政策",
				"文号": "",
				"发文机构": "兵团工信局",
				"原文链接": "https://example.com/supplement-xj-2019",
				"原文文本": "",
			},
			{
				"序号": "3",
				"所属省份": "广东省",
				"地区名称": "广东",
				"发文日期": "2020-01-01",
				"标题": "补充表2020政策",
				"文号": "",
				"发文机构": "工信厅",
				"原文链接": "https://example.com/supplement-2020",
				"原文文本": "专精特新全文。",
			},
		]
	)

	processed = build_manual_fulltext_policy_records_v2(current_raw, supplement_raw)
	intensity = build_province_year_intensity_v2(processed)

	assert set(processed["publish_year"]) == {2019, 2024}
	assert "https://example.com/current-2019" not in set(processed["source_url"])
	assert "https://example.com/current-2025" not in set(processed["source_url"])
	assert "https://example.com/current-2026" not in set(processed["source_url"])
	assert "https://example.com/supplement-2020" not in set(processed["source_url"])
	assert processed.loc[processed["source_url"].eq("https://example.com/supplement-central-2019"), "province"].item() == "central"
	assert processed.loc[processed["source_url"].eq("https://example.com/supplement-xj-2019"), "province"].item() == "新疆"
	assert processed.loc[processed["source_url"].eq("https://example.com/supplement-xj-2019"), "full_text_missing"].item()
	assert processed.loc[
		processed["source_url"].eq("https://example.com/supplement-xj-2019"),
		"full_text_fallback_for_model",
	].item()
	assert set(processed.loc[processed["publish_year"].eq(2019), "keyword_count_source"]) == {"derived_from_text"}
	assert processed.loc[processed["source_url"].eq("https://example.com/current-2024"), "keyword_count_source"].item() == "workbook_metadata"
	assert processed["source_url"].is_unique
	assert processed["policy_id"].is_unique
	assert "central" not in set(intensity["province"])
	assert set(intensity["publish_year"]) == {2019, 2020, 2021, 2022, 2023, 2024}


def test_manual_srdi_intensity_excludes_central_and_balances_years() -> None:
	raw = pd.read_excel(ROOT / "data" / "interim" / "manual_policy_all_keyword_srdi.xlsx", sheet_name="tableData", dtype=str)
	overrides = load_jurisdiction_overrides(ROOT / "configs" / "manual_srdi_jurisdiction_overrides_v1.csv")
	processed = build_manual_policy_records_v0(raw, overrides)
	intensity = build_province_year_intensity_v0(processed)
	quality_report = build_manual_processed_quality_report(raw, processed, intensity, overrides).set_index("metric")

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
	assert quality_report.loc["province_corrected_records", "value"] == 15


def test_manual_srdi_fulltext_v2_real_corpus_and_quality_reports_are_consistent() -> None:
	current_raw = pd.read_excel(
		ROOT / "data" / "interim" / "manual_policy_all_keyword_srdi_with_full_text.xlsx",
		sheet_name="tableData",
		dtype=str,
	)
	supplement_raw = pd.read_excel(
		ROOT / "data" / "interim" / "manual_policy_all_keyword_srdi_2019_supplementary.xlsx",
		sheet_name="tableData",
		dtype=str,
	)
	overrides = load_jurisdiction_overrides(ROOT / "configs" / "manual_srdi_jurisdiction_overrides_v1.csv")
	processed = build_manual_fulltext_policy_records_v2(current_raw, supplement_raw, overrides)
	intensity = build_province_year_intensity_v2(processed)
	candidates = build_v2_jurisdiction_review_candidates(processed)
	quality = build_manual_fulltext_processed_quality_report_v2(
		current_raw,
		supplement_raw,
		processed,
		intensity,
		candidates,
		overrides,
	).set_index("metric")
	supplement_quality = build_2019_supplement_quality_report_v2(
		supplement_raw,
		processed,
		candidates,
	).set_index("metric")

	assert len(processed) == 3989
	assert processed["source_url"].is_unique
	assert processed["policy_id"].is_unique
	assert set(processed["publish_year"]) == {2019, 2020, 2021, 2022, 2023, 2024}
	assert processed["source_schema_version"].value_counts().to_dict() == {
		"current_fulltext_workbook_v1": 3799,
		"supplement_2019_fulltext_v1": 190,
	}
	assert processed.loc[processed["source_schema_version"].eq("supplement_2019_fulltext_v1"), "keyword_count_source"].eq(
		"derived_from_text"
	).all()
	assert processed["full_text_missing"].sum() == 1
	assert len(intensity) == 186
	assert intensity["province"].nunique() == 31
	assert set(intensity["publish_year"]) == {2019, 2020, 2021, 2022, 2023, 2024}
	assert "central" not in set(intensity["province"])
	assert len(candidates) > 0
	assert quality.loc["supplement_2019_source_records", "value"] == 190
	assert quality.loc["processed_records", "value"] == 3989
	assert quality.loc["excluded_2025_records", "value"] == 676
	assert quality.loc["excluded_2026_records", "value"] == 167
	assert quality.loc["missing_full_text", "value"] == 1
	assert quality.loc["intensity_records", "value"] == 186
	assert quality.loc["jurisdiction_review_candidate_records", "value"] == len(candidates)
	assert supplement_quality.loc["missing_full_text_policy_ids", "value"] == quality.loc["missing_full_text_policy_ids", "value"]


def test_manual_srdi_jurisdiction_overrides_correct_reposted_policy_records() -> None:
	overrides = load_jurisdiction_overrides(ROOT / "configs" / "manual_srdi_jurisdiction_overrides_v1.csv")
	fulltext = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv")
	label_docs = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_label_docs_v1.csv")
	round1_sample = pd.read_csv(ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_sample_round1_v1.csv")
	policy_id = "manual_srdi_947d656f3bdcf1ae"

	assert len(overrides) == 15
	assert fulltext.loc[fulltext["policy_id"].eq(policy_id), "province"].item() == "上海市"
	assert fulltext.loc[fulltext["policy_id"].eq(policy_id), "province_before_correction"].item() == "北京市"
	assert fulltext.loc[fulltext["policy_id"].eq(policy_id), "province_correction_status"].item() == "corrected"
	assert label_docs.loc[label_docs["doc_id"].eq(policy_id), "province"].item() == "上海市"
	assert round1_sample.loc[round1_sample["doc_id"].eq(policy_id), "province"].item() == "上海市"
