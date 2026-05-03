import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "manual_srdi_macbert_predict_full_corpus.py"
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("manual_srdi_macbert_predict_full_corpus", SCRIPT_PATH)
assert spec is not None
prediction = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = prediction
spec.loader.exec_module(prediction)


def test_full_prediction_hard_rule_and_panel_aggregation() -> None:
	classified = pd.DataFrame(
		{
			"policy_id": ["central_1", "local_1", "local_2"],
			"province": ["central", "北京", "北京"],
			"source_label_original": ["国家", "北京", "北京"],
			"jurisdiction_type": ["central", "local", "local"],
			"publish_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
			"publish_year": [2024, 2024, 2024],
			"title": ["central", "local one", "local two"],
			"agency": ["a", "b", "c"],
			"source_url": ["https://example.com/c", "https://example.com/1", "https://example.com/2"],
			"full_text_len": [100, 100, 100],
		}
	)
	probabilities = np.asarray(
		[
			[0.9, 0.2, 0.2, 0.1],
			[0.8, 0.7, 0.2, 0.1],
			[0.2, 0.2, 0.2, 0.8],
		],
		dtype=np.float32,
	)
	classified["model_text"] = ["a", "b", "c"]
	classified = prediction.add_prediction_columns(classified, probabilities)
	base_panel = pd.DataFrame(
		{
			"province": ["北京", "北京", "上海", "上海"],
			"publish_year": [2024, 2025, 2024, 2025],
			"srdi_policy_count": [2, 0, 0, 0],
			"log_srdi_policy_count_plus1": [1.0986, 0.0, 0.0, 0.0],
		}
	)

	intensity = prediction.build_intensity_table(classified, base_panel)

	assert len(intensity) == 4
	assert "central" not in set(intensity["province"])
	beijing_2024 = intensity.loc[intensity["province"].eq("北京") & intensity["publish_year"].eq(2024)].iloc[0]
	assert beijing_2024["macbert_policy_records"] == 2
	assert beijing_2024["valid_tool_policy_count"] == 1
	assert beijing_2024["sum_p_supply"] > beijing_2024["filtered_sum_p_supply"]
	assert beijing_2024["other_label_policy_count"] == 1
	assert intensity.loc[intensity["province"].eq("上海"), "macbert_policy_records"].sum() == 0


def test_v2_empty_full_text_fallback_builds_model_text() -> None:
	row = pd.Series(
		{
			"policy_id": "fallback_1",
			"province": "安徽省",
			"source_label_original": "安徽省",
			"jurisdiction_type": "local",
			"publish_date": "2019-02-22",
			"publish_year": 2019,
			"title": "关于做好工业和信息化部专精特新小巨人企业补充推荐工作的通知",
			"agency": "",
			"source_url": "https://example.com/fallback",
			"full_text": "",
			"full_text_len": 0,
		}
	)
	frame = pd.DataFrame([row])

	prediction.validate_input(frame, allow_empty_full_text_fallback=True)
	model_text = prediction.make_model_text(row, context_terms=["专精特新", "小巨人"])

	assert "标题：" in model_text
	assert "降级输入说明" in model_text
	assert "专精特新" in model_text


def test_empty_full_text_still_fails_without_fallback_flag() -> None:
	frame = pd.DataFrame(
		[
			{
				"policy_id": "fallback_1",
				"province": "安徽省",
				"source_label_original": "安徽省",
				"jurisdiction_type": "local",
				"publish_date": "2019-02-22",
				"publish_year": 2019,
				"title": "专精特新政策",
				"agency": "",
				"source_url": "https://example.com/fallback",
				"full_text": "",
				"full_text_len": 0,
			}
		]
	)

	try:
		prediction.validate_input(frame)
	except ValueError as error:
		assert "empty full_text" in str(error)
	else:
		raise AssertionError("empty full_text should fail when fallback is disabled")


def test_manual_srdi_macbert_full_prediction_outputs_are_consistent() -> None:
	classified_path = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v1.csv"
	intensity_path = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v1.csv"
	if not classified_path.exists() or not intensity_path.exists():
		return

	classified = pd.read_csv(classified_path)
	intensity = pd.read_csv(intensity_path)
	quality = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v1.csv").set_index("metric")
	probability_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v1.csv")
	panel_coverage = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_panel_coverage_v1.csv")

	assert len(classified) == 4475
	assert classified["policy_id"].is_unique
	assert len(intensity) == 186
	assert intensity["province"].nunique() == 31
	assert set(intensity["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert len(panel_coverage) == 186
	assert set(probability_summary["label"]) == {"supply", "demand", "environment", "other"}
	for column in ["p_supply", "p_demand", "p_environment", "p_other"]:
		assert classified[column].between(0, 1).all()
	assert {"supply_label", "demand_label", "environment_label", "other_label", "valid_tool_policy"}.issubset(classified.columns)
	assert int(quality.loc["prediction_rows", "value"]) == 4475
	assert int(quality.loc["province_year_rows", "value"]) == 186


def test_manual_srdi_macbert_full_prediction_v2_outputs_are_consistent() -> None:
	classified_path = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v2.csv"
	intensity_path = ROOT / "data" / "processed" / "province_year_srdi_macbert_tool_intensity_v2.csv"
	if not classified_path.exists() or not intensity_path.exists():
		return

	classified = pd.read_csv(classified_path)
	intensity = pd.read_csv(intensity_path)
	quality = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_prediction_quality_report_v2.csv").set_index("metric")
	probability_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_summary_v2.csv")
	panel_coverage = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_panel_coverage_v2.csv")

	assert len(classified) == 3989
	assert classified["policy_id"].is_unique
	assert len(intensity) == 186
	assert intensity["province"].nunique() == 31
	assert set(intensity["publish_year"]) == {2019, 2020, 2021, 2022, 2023, 2024}
	assert len(panel_coverage) == 186
	assert set(probability_summary["label"]) == {"supply", "demand", "environment", "other"}
	assert classified["model_text_source"].value_counts().to_dict()["title_metadata_fallback"] == 1
	assert classified["full_text_missing"].sum() == 1
	assert classified["needs_jurisdiction_review"].sum() == 0
	for column in ["p_supply", "p_demand", "p_environment", "p_other"]:
		assert classified[column].between(0, 1).all()
	assert {"supply_label", "demand_label", "environment_label", "other_label", "valid_tool_policy"}.issubset(classified.columns)
	assert int(quality.loc["prediction_rows", "value"]) == 3989
	assert int(quality.loc["province_year_rows", "value"]) == 186
	assert int(quality.loc["model_text_fallback_rows", "value"]) == 1
