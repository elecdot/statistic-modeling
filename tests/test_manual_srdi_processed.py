from pathlib import Path

import pandas as pd

from statistic_modeling.policy_text_crawler.manual_srdi_processed import (
	build_manual_fulltext_policy_records_v1,
	build_manual_fulltext_processed_quality_report,
	build_manual_policy_records_v0,
	build_manual_processed_quality_report,
	build_province_year_intensity_v0,
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
