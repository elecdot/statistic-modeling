import argparse
import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "manual_srdi_deepseek_round1_label.py"

spec = importlib.util.spec_from_file_location("manual_srdi_deepseek_round1_label", SCRIPT_PATH)
assert spec is not None
labeling = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(labeling)


def test_parse_model_content_tolerates_fenced_json() -> None:
	content = """```json
	{
	  "p_supply": 0.7,
	  "supply_evidence": ["资金奖励"],
	  "p_demand": 0.2,
	  "demand_evidence": [],
	  "p_environment": 0.8,
	  "environment_evidence": ["融资担保"],
	  "p_other": 0.1,
	  "other_reason": "",
	  "has_substantive_policy_tool": true,
	  "is_srdi_related": true,
	  "summary_reason": "含有财政与金融支持。"
	}
	```"""

	parsed = labeling.normalize_label_payload(labeling.parse_model_content(content))

	assert parsed["p_supply"] == 0.7
	assert parsed["p_environment"] == 0.8
	assert parsed["supply_evidence"] == ["资金奖励"]
	assert parsed["has_substantive_policy_tool"] is True
	assert labeling.derive_binary_labels(parsed) == {
		"y_supply": 1,
		"y_demand": 0,
		"y_environment": 1,
		"y_other": 0,
	}


def test_extract_message_content_falls_back_to_reasoning_content() -> None:
	api_response = {
		"choices": [
			{
				"message": {
					"content": "",
					"reasoning_content": """模型推理省略。
					```json
					{
					  "p_supply": 0.45,
					  "supply_evidence": ["特设岗位"],
					  "p_demand": 0.0,
					  "demand_evidence": [],
					  "p_environment": 0.9,
					  "environment_evidence": ["职称评审绿色通道"],
					  "p_other": 0.0,
					  "other_reason": "",
					  "has_substantive_policy_tool": true,
					  "is_srdi_related": true,
					  "summary_reason": "人才评价制度优化。"
					}
					```""",
				}
			}
		]
	}

	content = labeling.extract_message_content(api_response)
	parsed = labeling.normalize_label_payload(labeling.parse_model_content(content))

	assert parsed["p_supply"] == 0.45
	assert parsed["p_environment"] == 0.9
	assert parsed["summary_reason"] == "人才评价制度优化。"


def test_deepseek_round1_dry_run_writes_expected_outputs(tmp_path: Path) -> None:
	input_path = tmp_path / "round1_sample.csv"
	labels_output = tmp_path / "labels.csv"
	quality_output = tmp_path / "quality.csv"
	raw_dir = tmp_path / "raw"
	log_output = tmp_path / "run.log"
	pd.DataFrame(
		[
			{
				"doc_id": "doc_1",
				"province": "北京",
				"year": 2024,
				"title": "关于支持专精特新企业发展的政策",
				"issuing_agency": "北京市经济和信息化局",
				"publish_date": "2024-01-01",
				"source_url": "https://example.com/doc_1",
				"clean_text": "对专精特新企业给予资金奖励和融资服务。",
				"sample_pool": "supply-like",
			},
			{
				"doc_id": "doc_2",
				"province": "上海",
				"year": 2025,
				"title": "专精特新企业名单公示",
				"issuing_agency": "上海市经济和信息化委员会",
				"publish_date": "2025-01-01",
				"source_url": "https://example.com/doc_2",
				"clean_text": "现将专精特新企业名单予以公示。",
				"sample_pool": "other-like",
			},
		]
	).to_csv(input_path, index=False)

	args = argparse.Namespace(
		input=input_path,
		raw_output_dir=raw_dir,
		labels_output=labels_output,
		quality_output=quality_output,
		model="deepseek-v4-flash",
		base_url="https://api.deepseek.com",
		limit=1,
		max_text_chars=100,
		sleep_seconds=0,
		timeout_seconds=1,
		workers=2,
		max_retries=0,
		retry_sleep_seconds=0,
		progress_interval=1,
		log_output=log_output,
		resume=False,
		dry_run=True,
		fail_fast=False,
	)
	labels, quality = labeling.run_labeling(args)

	assert len(labels) == 1
	assert labels.loc[0, "label_status"] == "dry_run"
	assert labels.loc[0, "doc_id"] == "doc_1"
	assert labels.loc[0, "sample_pool"] == "supply-like"
	assert labels["doc_id"].is_unique
	assert labels_output.exists()
	assert quality_output.exists()
	assert log_output.exists()
	assert not list(raw_dir.glob("*.json"))
	assert quality.set_index("metric").loc["dry_run_records", "value"] == 1
	assert "progress done=1/1" in log_output.read_text(encoding="utf-8")


def test_deepseek_round1_resume_uses_cached_raw_json_without_api_call(tmp_path: Path, monkeypatch) -> None:
	input_path = tmp_path / "round1_sample.csv"
	labels_output = tmp_path / "labels.csv"
	quality_output = tmp_path / "quality.csv"
	raw_dir = tmp_path / "raw"
	log_output = tmp_path / "run.log"
	raw_dir.mkdir()
	pd.DataFrame(
		[
			{
				"doc_id": "doc_1",
				"province": "北京",
				"year": 2024,
				"title": "关于支持专精特新企业发展的政策",
				"issuing_agency": "北京市经济和信息化局",
				"publish_date": "2024-01-01",
				"source_url": "https://example.com/doc_1",
				"clean_text": "对专精特新企业给予资金奖励和融资服务。",
				"sample_pool": "supply-like",
			}
		]
	).to_csv(input_path, index=False)
	cached_payload = {
		"doc_id": "doc_1",
		"api_response": {
			"choices": [
				{
					"message": {
						"content": json.dumps(
							{
								"p_supply": 0.8,
								"supply_evidence": ["资金奖励"],
								"p_demand": 0.1,
								"demand_evidence": [],
								"p_environment": 0.7,
								"environment_evidence": ["融资服务"],
								"p_other": 0.0,
								"other_reason": "",
								"has_substantive_policy_tool": True,
								"is_srdi_related": True,
								"summary_reason": "含有供给和环境型支持。",
							},
							ensure_ascii=False,
						)
					}
				}
			]
		},
	}
	(raw_dir / "doc_1.json").write_text(json.dumps(cached_payload, ensure_ascii=False), encoding="utf-8")

	def fail_if_called(**kwargs):
		raise AssertionError("API should not be called for cached resume rows")

	monkeypatch.setattr(labeling, "post_chat_completion", fail_if_called)
	args = argparse.Namespace(
		input=input_path,
		raw_output_dir=raw_dir,
		labels_output=labels_output,
		quality_output=quality_output,
		model="deepseek-v4-flash",
		base_url="https://api.deepseek.com",
		limit=None,
		max_text_chars=100,
		sleep_seconds=0,
		timeout_seconds=1,
		workers=2,
		max_retries=0,
		retry_sleep_seconds=0,
		progress_interval=1,
		log_output=log_output,
		resume=True,
		dry_run=False,
		fail_fast=False,
	)
	labels, quality = labeling.run_labeling(args)

	assert len(labels) == 1
	assert labels.loc[0, "label_status"] == "success"
	assert labels.loc[0, "p_supply"] == 0.8
	assert labels.loc[0, "raw_response_path"] == str(raw_dir / "doc_1.json")
	assert quality.set_index("metric").loc["success_records", "value"] == 1
	assert "source=cache" in log_output.read_text(encoding="utf-8")


def test_deepseek_round1_failure_is_recorded_without_stopping(tmp_path: Path, monkeypatch) -> None:
	input_path = tmp_path / "round1_sample.csv"
	labels_output = tmp_path / "labels.csv"
	quality_output = tmp_path / "quality.csv"
	raw_dir = tmp_path / "raw"
	log_output = tmp_path / "run.log"
	pd.DataFrame(
		[
			{
				"doc_id": "doc_1",
				"province": "北京",
				"year": 2024,
				"title": "关于支持专精特新企业发展的政策",
				"issuing_agency": "北京市经济和信息化局",
				"publish_date": "2024-01-01",
				"source_url": "https://example.com/doc_1",
				"clean_text": "对专精特新企业给予资金奖励和融资服务。",
				"sample_pool": "supply-like",
			},
			{
				"doc_id": "doc_2",
				"province": "上海",
				"year": 2025,
				"title": "专精特新企业名单公示",
				"issuing_agency": "上海市经济和信息化委员会",
				"publish_date": "2025-01-01",
				"source_url": "https://example.com/doc_2",
				"clean_text": "现将专精特新企业名单予以公示。",
				"sample_pool": "other-like",
			},
		]
	).to_csv(input_path, index=False)

	def raise_error(**kwargs):
		raise RuntimeError("simulated API failure")

	monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
	monkeypatch.setattr(labeling, "post_chat_completion", raise_error)
	args = argparse.Namespace(
		input=input_path,
		raw_output_dir=raw_dir,
		labels_output=labels_output,
		quality_output=quality_output,
		model="deepseek-v4-flash",
		base_url="https://api.deepseek.com",
		limit=None,
		max_text_chars=100,
		sleep_seconds=0,
		timeout_seconds=1,
		workers=2,
		max_retries=0,
		retry_sleep_seconds=0,
		progress_interval=1,
		log_output=log_output,
		resume=False,
		dry_run=False,
		fail_fast=False,
	)
	labels, quality = labeling.run_labeling(args)

	assert len(labels) == 2
	assert labels["doc_id"].tolist() == ["doc_1", "doc_2"]
	assert labels["label_status"].eq("failed").all()
	assert labels["error"].str.contains("simulated API failure").all()
	assert quality.set_index("metric").loc["failed_records", "value"] == 2
	assert "status=failed" in log_output.read_text(encoding="utf-8")
