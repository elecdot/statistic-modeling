import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "manual_srdi_train_macbert_multilabel.py"

spec = importlib.util.spec_from_file_location("manual_srdi_train_macbert_multilabel", SCRIPT_PATH)
assert spec is not None
training = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = training
spec.loader.exec_module(training)


def test_compute_pos_weight_and_multilabel_metrics() -> None:
	y_true = np.asarray(
		[
			[1, 0, 1, 0],
			[0, 1, 1, 0],
			[0, 0, 0, 1],
		],
		dtype=np.float32,
	)
	y_prob = np.asarray(
		[
			[0.9, 0.1, 0.8, 0.1],
			[0.2, 0.7, 0.6, 0.1],
			[0.1, 0.1, 0.2, 0.8],
		],
		dtype=np.float32,
	)

	pos_weight = training.compute_pos_weight(y_true)
	metrics = training.compute_multilabel_metrics(y_true, y_prob)

	assert pos_weight.tolist() == [2.0, 2.0, 0.5, 2.0]
	assert metrics["micro_f1"] == 1.0
	assert metrics["macro_f1"] == 1.0
	assert training.hard_other_rule(y_prob).tolist()[-1] == [0, 0, 0, 1]


def test_macbert_training_dry_run_validates_jsonl_splits(tmp_path: Path) -> None:
	data_dir = tmp_path / "data"
	output_dir = tmp_path / "model"
	metrics_output = tmp_path / "metrics.csv"
	predictions_output = tmp_path / "predictions.csv"
	quality_output = tmp_path / "quality.csv"
	log_output = tmp_path / "train.log"
	data_dir.mkdir()
	rows = {
		"train": [
			{
				"doc_id": "doc_1",
				"sample_pool": "supply-like",
				"province": "北京",
				"year": 2024,
				"title": "支持专精特新企业",
				"source_url": "https://example.com/doc_1",
				"model_text": "标题：支持专精特新企业\n正文：给予资金奖励。",
				"labels": [1, 0, 0, 0],
				"soft_labels": [0.9, 0.1, 0.2, 0.0],
			}
		],
		"validation": [
			{
				"doc_id": "doc_2",
				"sample_pool": "demand-like",
				"province": "上海",
				"year": 2024,
				"title": "推广应用",
				"source_url": "https://example.com/doc_2",
				"model_text": "标题：推广应用\n正文：开展供需对接。",
				"labels": [0, 1, 0, 0],
				"soft_labels": [0.1, 0.8, 0.2, 0.0],
			}
		],
		"test": [
			{
				"doc_id": "doc_3",
				"sample_pool": "other-like",
				"province": "广东",
				"year": 2024,
				"title": "名单公示",
				"source_url": "https://example.com/doc_3",
				"model_text": "标题：名单公示\n正文：现予以公示。",
				"labels": [0, 0, 0, 1],
				"soft_labels": [0.0, 0.0, 0.1, 0.8],
			}
		],
	}
	for split, split_rows in rows.items():
		with (data_dir / f"{split}.jsonl").open("w", encoding="utf-8") as handle:
			for row in split_rows:
				handle.write(json.dumps(row, ensure_ascii=False) + "\n")

	args = argparse.Namespace(
		data_dir=data_dir,
		output_dir=output_dir,
		metrics_output=metrics_output,
			test_predictions_output=predictions_output,
			quality_output=quality_output,
			log_output=log_output,
			checkpoint_dir=None,
			model_name="hfl/chinese-macbert-base",
		max_length=512,
		epochs=1,
		batch_size=1,
		eval_batch_size=1,
		learning_rate=2e-5,
		weight_decay=0.01,
		warmup_ratio=0.1,
		seed=42,
		device="cpu",
		use_soft_labels=False,
		limit_train=None,
			limit_validation=None,
		limit_test=None,
		resume=False,
		show_download_progress=False,
		dry_run=True,
	)

	training.run_training(args)
	quality = pd.read_csv(quality_output).set_index("metric")

	assert quality.loc["train_rows", "value"] == "1"
	assert quality.loc["validation_rows", "value"] == "1"
	assert quality.loc["test_rows", "value"] == "1"
	assert quality.loc["dry_run", "value"] == "True"
	assert log_output.exists()
	assert not output_dir.exists()
	assert not metrics_output.exists()
	assert not predictions_output.exists()
