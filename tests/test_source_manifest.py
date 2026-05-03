from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_source_manifest_globs_do_not_mix_srdi_and_all_policy_cache() -> None:
	manifest = pd.read_csv(ROOT / "data" / "source-manifest.csv").fillna("")
	assert len(manifest) == 70
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
	assert "手工收集_专精特新辖区修正表v1" in set(manifest["source_name"])
	assert "手工收集_专精特新DeepSeek首轮样本v1" in set(manifest["source_name"])
	assert "手工收集_专精特新DeepSeek首轮标签v1" in set(manifest["source_name"])
	assert "手工收集_专精特新MacBERT训练数据v1" in set(manifest["source_name"])
	assert "手工收集_专精特新MacBERT全量预测v1" in set(manifest["source_name"])
	assert "手工收集_省份年份MacBERT政策工具强度v1" in set(manifest["source_name"])
	assert "手工收集_省份年份专精特新DID政策文本变量v1" in set(manifest["source_name"])
	assert "手工收集_专精特新DID政策强度面板v1" in set(manifest["source_name"])
	assert "手工收集_专精特新MacBERT全量预测v2" in set(manifest["source_name"])
	assert "手工收集_省份年份MacBERT政策工具强度v2" in set(manifest["source_name"])
	assert "手工收集_专精特新MacBERT全量预测QA v2" in set(manifest["source_name"])
	assert "手工收集_专精特新MacBERT变量准备QA v2" in set(manifest["source_name"])
	assert "手工收集_省份年份专精特新政策文本变量v2" in set(manifest["source_name"])
	assert "手工收集_专精特新政策文本变量口径QA v2" in set(manifest["source_name"])
	assert "手工收集_专精特新DID政策强度面板v2" in set(manifest["source_name"])
	assert "手工收集_专精特新DID政策强度面板QA v2" in set(manifest["source_name"])
	assert "手工收集_专精特新2019补充全文政策表" in set(manifest["source_name"])
	assert "手工收集_专精特新辖区修正表v2" in set(manifest["source_name"])
	assert "手工收集_全国专精特新全文政策记录v2" in set(manifest["source_name"])
	assert "手工收集_省份年份专精特新政策计数v2" in set(manifest["source_name"])
	assert "手工收集_专精特新2019辖区复核候选v2" in set(manifest["source_name"])
	assert "手工收集_专精特新全文文本特征v2" in set(manifest["source_name"])
	assert "手工收集_省份年份专精特新全文文本特征v2" in set(manifest["source_name"])
	assert "手工收集_专精特新全文描述分析v2" in set(manifest["source_name"])
	assert "手工收集_专精特新全文关键词质量分析v2" in set(manifest["source_name"])
