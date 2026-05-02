import argparse
import importlib.util
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


def test_deepseek_round1_dry_run_writes_expected_outputs(tmp_path: Path) -> None:
	input_path = tmp_path / "round1_sample.csv"
	labels_output = tmp_path / "labels.csv"
	quality_output = tmp_path / "quality.csv"
	raw_dir = tmp_path / "raw"
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
		resume=False,
		dry_run=True,
		fail_fast=False,
	)
	labels, quality = labeling.run_labeling(args)

	assert len(labels) == 1
	assert labels.loc[0, "label_status"] == "dry_run"
	assert labels.loc[0, "doc_id"] == "doc_1"
	assert labels.loc[0, "sample_pool"] == "supply-like"
	assert labels_output.exists()
	assert quality_output.exists()
	assert not list(raw_dir.glob("*.json"))
	assert quality.set_index("metric").loc["dry_run_records", "value"] == 1
