"""Train a MacBERT multi-label classifier for manual SRDI policy tools.

The script consumes the deterministic JSONL split prepared by
``notebooks/48_manual_srdi_macbert_training_data.py`` and trains a four-label
classifier for supply, demand, environment, and other. It intentionally keeps
the training loop explicit instead of hiding the workflow behind notebooks, so
metrics, predictions, checkpoints, and failure modes are easy to audit.

Install-time note: the command requires ``torch`` and ``transformers``. They are
imported lazily so repository tests can still run in lightweight environments.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATA_DIR = ROOT / "data" / "processed" / "manual_policy_srdi_macbert_training_v1"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "manual_srdi_macbert_multilabel_v1"
DEFAULT_METRICS_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_multilabel_metrics_v1.csv"
DEFAULT_TEST_PREDICTIONS_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_multilabel_test_predictions_v1.csv"
DEFAULT_QUALITY_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_multilabel_quality_report_v1.csv"
DEFAULT_LOG_OUTPUT = ROOT / "outputs" / "manual_srdi_macbert_multilabel_train_v1.log"
DEFAULT_MODEL_NAME = "hfl/chinese-macbert-base"

LABEL_NAMES = ["supply", "demand", "environment", "other"]
NUM_LABELS = len(LABEL_NAMES)


@dataclass(frozen=True)
class TrainingDeps:
	"""Lazy imports required only for actual model training."""

	torch: Any
	AutoTokenizer: Any
	AutoModelForSequenceClassification: Any


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
	parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
	parser.add_argument("--metrics-output", type=Path, default=DEFAULT_METRICS_OUTPUT)
	parser.add_argument("--test-predictions-output", type=Path, default=DEFAULT_TEST_PREDICTIONS_OUTPUT)
	parser.add_argument("--quality-output", type=Path, default=DEFAULT_QUALITY_OUTPUT)
	parser.add_argument("--log-output", type=Path, default=DEFAULT_LOG_OUTPUT)
	parser.add_argument("--checkpoint-dir", type=Path, default=None, help="Defaults to OUTPUT_DIR/checkpoints.")
	parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
	parser.add_argument("--max-length", type=int, default=512)
	parser.add_argument("--epochs", type=int, default=5)
	parser.add_argument("--batch-size", type=int, default=8)
	parser.add_argument("--eval-batch-size", type=int, default=16)
	parser.add_argument("--learning-rate", type=float, default=2e-5)
	parser.add_argument("--weight-decay", type=float, default=0.01)
	parser.add_argument("--warmup-ratio", type=float, default=0.10)
	parser.add_argument("--seed", type=int, default=42)
	parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
	parser.add_argument("--use-soft-labels", action="store_true", help="Train against DeepSeek probabilities instead of binary labels.")
	parser.add_argument("--limit-train", type=int, default=None, help="Optional cap for smoke runs.")
	parser.add_argument("--limit-validation", type=int, default=None, help="Optional cap for smoke runs.")
	parser.add_argument("--limit-test", type=int, default=None, help="Optional cap for smoke runs.")
	parser.add_argument("--resume", action="store_true", help="Resume from the latest epoch checkpoint if present.")
	parser.add_argument("--show-download-progress", action="store_true", help="Show Hugging Face download progress bars and advisory model-loading logs for debugging.")
	parser.add_argument("--dry-run", action="store_true", help="Validate data and write QA only; do not load model or train.")
	return parser.parse_args()


def setup_logging(log_output: Path) -> logging.Logger:
	"""Write training progress to both console and a persistent log file."""
	log_output.parent.mkdir(parents=True, exist_ok=True)
	logger = logging.getLogger("manual_srdi_macbert_training")
	logger.setLevel(logging.INFO)
	logger.handlers.clear()
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
	console_handler = logging.StreamHandler()
	console_handler.setFormatter(formatter)
	file_handler = logging.FileHandler(log_output, encoding="utf-8")
	file_handler.setFormatter(formatter)
	logger.addHandler(console_handler)
	logger.addHandler(file_handler)
	return logger


def configure_model_loading_noise(*, quiet: bool) -> None:
	"""Keep third-party model-loading chatter out of research run logs by default."""
	if quiet:
		os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
		os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
		os.environ["TRANSFORMERS_VERBOSITY"] = "error"
		try:
			from huggingface_hub.utils import disable_progress_bars

			disable_progress_bars()
		except Exception:
			# Progress-bar suppression is best-effort and must not block training.
			pass


def require_training_deps(*, quiet: bool = True) -> TrainingDeps:
	try:
		import torch
		from transformers import AutoModelForSequenceClassification, AutoTokenizer
		from transformers.utils import logging as transformers_logging
	except ModuleNotFoundError as exc:
		raise RuntimeError(
			"MacBERT training requires torch and transformers. Install them with "
			"`UV_CACHE_DIR=/tmp/uv-cache UV_HTTP_TIMEOUT=300 uv add torch transformers` "
			"or an equivalent project-approved dependency command."
		) from exc
	if quiet:
		transformers_logging.set_verbosity_error()
	return TrainingDeps(
		torch=torch,
		AutoTokenizer=AutoTokenizer,
		AutoModelForSequenceClassification=AutoModelForSequenceClassification,
	)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
	rows: list[dict[str, Any]] = []
	with path.open("r", encoding="utf-8") as handle:
		for line in handle:
			if line.strip():
				rows.append(json.loads(line))
	return rows


def load_split(data_dir: Path, split: str, limit: int | None = None) -> list[dict[str, Any]]:
	path = data_dir / f"{split}.jsonl"
	rows = read_jsonl(path)
	if limit is not None:
		rows = rows[:limit]
	return rows


def validate_rows(rows: Iterable[dict[str, Any]], split: str) -> None:
	seen: set[str] = set()
	for row in rows:
		doc_id = str(row.get("doc_id", ""))
		if not doc_id:
			raise ValueError(f"{split} row is missing doc_id")
		if doc_id in seen:
			raise ValueError(f"{split} has duplicate doc_id: {doc_id}")
		seen.add(doc_id)
		if not str(row.get("model_text", "")).strip():
			raise ValueError(f"{split} row has empty model_text: {doc_id}")
		labels = row.get("labels")
		soft_labels = row.get("soft_labels")
		if not isinstance(labels, list) or len(labels) != NUM_LABELS:
			raise ValueError(f"{split} row has invalid labels: {doc_id}")
		if not isinstance(soft_labels, list) or len(soft_labels) != NUM_LABELS:
			raise ValueError(f"{split} row has invalid soft_labels: {doc_id}")


def label_matrix(rows: list[dict[str, Any]], *, use_soft_labels: bool = False) -> np.ndarray:
	field = "soft_labels" if use_soft_labels else "labels"
	return np.asarray([row[field] for row in rows], dtype=np.float32)


def compute_pos_weight(train_labels: np.ndarray) -> np.ndarray:
	positive = train_labels.sum(axis=0)
	negative = train_labels.shape[0] - positive
	positive = np.clip(positive, 1.0, None)
	return negative / positive


def sigmoid(logits: np.ndarray) -> np.ndarray:
	return 1.0 / (1.0 + np.exp(-logits))


def hard_other_rule(probabilities: np.ndarray) -> np.ndarray:
	"""Apply the project's stricter binary rule for the exclusion label."""
	binary = (probabilities >= 0.5).astype(int)
	tool_max = probabilities[:, :3].max(axis=1)
	binary[:, 3] = ((probabilities[:, 3] >= 0.6) & (tool_max < 0.4)).astype(int)
	return binary


def compute_multilabel_metrics(
	y_true: np.ndarray,
	y_prob: np.ndarray,
	*,
	threshold: float = 0.5,
) -> dict[str, float]:
	"""Compute dependency-light multilabel metrics for validation/test checks."""
	y_pred = (y_prob >= threshold).astype(int)
	y_pred[:, 3] = hard_other_rule(y_prob)[:, 3]
	y_true = y_true.astype(int)

	true_positive = (y_true & y_pred).sum(axis=0)
	false_positive = ((1 - y_true) & y_pred).sum(axis=0)
	false_negative = (y_true & (1 - y_pred)).sum(axis=0)

	precision = true_positive / np.clip(true_positive + false_positive, 1, None)
	recall = true_positive / np.clip(true_positive + false_negative, 1, None)
	f1 = 2 * precision * recall / np.clip(precision + recall, 1e-12, None)

	micro_tp = true_positive.sum()
	micro_fp = false_positive.sum()
	micro_fn = false_negative.sum()
	micro_precision = micro_tp / max(micro_tp + micro_fp, 1)
	micro_recall = micro_tp / max(micro_tp + micro_fn, 1)
	micro_f1 = 2 * micro_precision * micro_recall / max(micro_precision + micro_recall, 1e-12)

	row_overlap = (y_true & y_pred).sum(axis=1)
	row_union = ((y_true | y_pred).sum(axis=1)).clip(min=1)
	samples_jaccard = float(np.mean(row_overlap / row_union))

	metrics: dict[str, float] = {
		"micro_precision": float(micro_precision),
		"micro_recall": float(micro_recall),
		"micro_f1": float(micro_f1),
		"macro_precision": float(np.mean(precision)),
		"macro_recall": float(np.mean(recall)),
		"macro_f1": float(np.mean(f1)),
		"samples_jaccard": samples_jaccard,
	}
	for idx, label_name in enumerate(LABEL_NAMES):
		metrics[f"{label_name}_precision"] = float(precision[idx])
		metrics[f"{label_name}_recall"] = float(recall[idx])
		metrics[f"{label_name}_f1"] = float(f1[idx])
	return metrics


class PolicyTextDataset:
	"""Tiny torch Dataset wrapper around JSONL records."""

	def __init__(self, rows: list[dict[str, Any]], *, use_soft_labels: bool, torch_module: Any) -> None:
		self.rows = rows
		self.use_soft_labels = use_soft_labels
		self.torch = torch_module

	def __len__(self) -> int:
		return len(self.rows)

	def __getitem__(self, index: int) -> dict[str, Any]:
		row = self.rows[index]
		return {
			"doc_id": row["doc_id"],
			"text": row["model_text"],
			"labels": self.torch.tensor(row["soft_labels" if self.use_soft_labels else "labels"], dtype=self.torch.float32),
		}


def make_collate_fn(tokenizer: Any, torch_module: Any, max_length: int):
	def collate(batch: list[dict[str, Any]]) -> dict[str, Any]:
		encoded = tokenizer(
			[item["text"] for item in batch],
			truncation=True,
			padding=True,
			max_length=max_length,
			return_tensors="pt",
		)
		encoded["labels"] = torch_module.stack([item["labels"] for item in batch])
		return encoded

	return collate


def select_device(torch_module: Any, requested: str) -> Any:
	if requested == "cuda":
		return torch_module.device("cuda")
	if requested == "cpu":
		return torch_module.device("cpu")
	return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")


def train_one_epoch(
	*,
	model: Any,
	loader: Any,
	optimizer: Any,
	scheduler: Any,
	loss_fn: Any,
	device: Any,
) -> float:
	model.train()
	total_loss = 0.0
	for batch in loader:
		labels = batch.pop("labels").to(device)
		batch = {key: value.to(device) for key, value in batch.items()}
		outputs = model(**batch)
		loss = loss_fn(outputs.logits, labels)
		loss.backward()
		optimizer.step()
		scheduler.step()
		optimizer.zero_grad(set_to_none=True)
		total_loss += float(loss.detach().cpu().item())
	return total_loss / max(len(loader), 1)


def predict(
	*,
	model: Any,
	loader: Any,
	device: Any,
	torch_module: Any,
) -> np.ndarray:
	model.eval()
	probabilities: list[np.ndarray] = []
	with torch_module.no_grad():
		for batch in loader:
			batch.pop("labels", None)
			batch = {key: value.to(device) for key, value in batch.items()}
			logits = model(**batch).logits.detach().cpu().numpy()
			probabilities.append(sigmoid(logits))
	return np.vstack(probabilities) if probabilities else np.empty((0, NUM_LABELS), dtype=np.float32)


def flatten_metrics(metrics_by_split_epoch: list[dict[str, Any]]) -> pd.DataFrame:
	return pd.DataFrame(metrics_by_split_epoch)


def resolved_checkpoint_dir(args: argparse.Namespace) -> Path:
	return args.checkpoint_dir if args.checkpoint_dir is not None else args.output_dir / "checkpoints"


def checkpoint_path(checkpoint_dir: Path, epoch: int) -> Path:
	return checkpoint_dir / f"epoch_{epoch:03d}.pt"


def latest_checkpoint_path(checkpoint_dir: Path) -> Path | None:
	checkpoints = sorted(checkpoint_dir.glob("epoch_*.pt"))
	return checkpoints[-1] if checkpoints else None


def should_use_safetensors(model_name: str) -> bool:
	"""Prefer PyTorch weights for remote checkpoints, but support safetensors-only local fixtures."""
	model_path = Path(model_name)
	if not model_path.is_dir():
		return False
	has_pytorch_weights = any(model_path.glob("pytorch_model*.bin"))
	has_safetensors = any(model_path.glob("*.safetensors"))
	return has_safetensors and not has_pytorch_weights


def save_checkpoint(
	*,
	torch_module: Any,
	checkpoint_dir: Path,
	epoch: int,
	model: Any,
	optimizer: Any,
	scheduler: Any,
	best_epoch: int | None,
	best_validation_macro_f1: float,
	best_state: dict[str, Any] | None,
	metrics_rows: list[dict[str, Any]],
) -> Path:
	"""Persist epoch-boundary training state so interrupted runs can resume."""
	checkpoint_dir.mkdir(parents=True, exist_ok=True)
	path = checkpoint_path(checkpoint_dir, epoch)
	payload = {
		"epoch": epoch,
		"model_state_dict": model.state_dict(),
		"optimizer_state_dict": optimizer.state_dict(),
		"scheduler_state_dict": scheduler.state_dict(),
		"best_epoch": best_epoch,
		"best_validation_macro_f1": best_validation_macro_f1,
		"best_state": best_state,
		"metrics_rows": metrics_rows,
	}
	torch_module.save(payload, path)
	return path


def load_checkpoint(
	*,
	torch_module: Any,
	path: Path,
	model: Any,
	optimizer: Any,
	scheduler: Any,
	device: Any,
) -> dict[str, Any]:
	"""Load a checkpoint produced by ``save_checkpoint``."""
	payload = torch_module.load(path, map_location=device)
	model.load_state_dict(payload["model_state_dict"])
	optimizer.load_state_dict(payload["optimizer_state_dict"])
	scheduler.load_state_dict(payload["scheduler_state_dict"])
	return payload


def write_predictions(rows: list[dict[str, Any]], probabilities: np.ndarray, path: Path) -> None:
	binary = hard_other_rule(probabilities)
	output_rows = []
	for row, probs, labels in zip(rows, probabilities, binary, strict=True):
		output_rows.append(
			{
				"doc_id": row["doc_id"],
				"sample_pool": row.get("sample_pool", ""),
				"province": row.get("province", ""),
				"year": row.get("year", ""),
				"title": row.get("title", ""),
				"p_supply": probs[0],
				"p_demand": probs[1],
				"p_environment": probs[2],
				"p_other": probs[3],
				"supply_label": labels[0],
				"demand_label": labels[1],
				"environment_label": labels[2],
				"other_label": labels[3],
				"source_url": row.get("source_url", ""),
			}
		)
	path.parent.mkdir(parents=True, exist_ok=True)
	pd.DataFrame(output_rows).to_csv(path, index=False)


def build_quality_report(
	*,
	args: argparse.Namespace,
	train_rows: list[dict[str, Any]],
	validation_rows: list[dict[str, Any]],
	test_rows: list[dict[str, Any]],
	best_epoch: int | None,
	best_validation_macro_f1: float | None,
	device: str,
	dry_run: bool,
) -> pd.DataFrame:
	return pd.DataFrame(
		[
			{"metric": "train_rows", "value": len(train_rows), "note": "Training split rows."},
			{"metric": "validation_rows", "value": len(validation_rows), "note": "Validation split rows."},
			{"metric": "test_rows", "value": len(test_rows), "note": "Test split rows."},
			{"metric": "model_name", "value": args.model_name, "note": "Base model requested."},
			{"metric": "epochs", "value": args.epochs, "note": "Configured max epochs."},
			{"metric": "batch_size", "value": args.batch_size, "note": "Training batch size."},
			{"metric": "max_length", "value": args.max_length, "note": "Tokenizer truncation length."},
			{"metric": "use_soft_labels", "value": args.use_soft_labels, "note": "Whether soft DeepSeek probabilities were used as training targets."},
			{"metric": "device", "value": device, "note": "Resolved training device."},
			{"metric": "dry_run", "value": dry_run, "note": "True means no model was loaded or trained."},
			{"metric": "best_epoch", "value": "" if best_epoch is None else best_epoch, "note": "Epoch with best validation macro_f1."},
			{"metric": "best_validation_macro_f1", "value": "" if best_validation_macro_f1 is None else best_validation_macro_f1, "note": "Best validation macro F1 observed."},
		]
	)


def run_training(args: argparse.Namespace) -> None:
	logger = setup_logging(args.log_output)
	quiet_model_loading = not args.show_download_progress
	configure_model_loading_noise(quiet=quiet_model_loading)
	logger.info("Starting MacBERT training run")
	train_rows = load_split(args.data_dir, "train", args.limit_train)
	validation_rows = load_split(args.data_dir, "validation", args.limit_validation)
	test_rows = load_split(args.data_dir, "test", args.limit_test)
	for split, rows in [("train", train_rows), ("validation", validation_rows), ("test", test_rows)]:
		validate_rows(rows, split)
	logger.info("Loaded splits train=%s validation=%s test=%s", len(train_rows), len(validation_rows), len(test_rows))

	if args.dry_run:
		args.quality_output.parent.mkdir(parents=True, exist_ok=True)
		build_quality_report(
			args=args,
			train_rows=train_rows,
			validation_rows=validation_rows,
			test_rows=test_rows,
			best_epoch=None,
			best_validation_macro_f1=None,
			device="not_resolved",
			dry_run=True,
		).to_csv(args.quality_output, index=False)
		logger.info("Dry run OK. Wrote quality report: %s", args.quality_output)
		return

	deps = require_training_deps(quiet=quiet_model_loading)
	torch = deps.torch
	random.seed(args.seed)
	np.random.seed(args.seed)
	torch.manual_seed(args.seed)
	if torch.cuda.is_available():
		torch.cuda.manual_seed_all(args.seed)

	device = select_device(torch, args.device)
	tokenizer = deps.AutoTokenizer.from_pretrained(args.model_name)
	model = deps.AutoModelForSequenceClassification.from_pretrained(
		args.model_name,
		num_labels=NUM_LABELS,
		id2label={idx: name for idx, name in enumerate(LABEL_NAMES)},
		label2id={name: idx for idx, name in enumerate(LABEL_NAMES)},
		problem_type="multi_label_classification",
		use_safetensors=should_use_safetensors(args.model_name),
	)
	model.to(device)

	train_dataset = PolicyTextDataset(train_rows, use_soft_labels=args.use_soft_labels, torch_module=torch)
	validation_dataset = PolicyTextDataset(validation_rows, use_soft_labels=False, torch_module=torch)
	test_dataset = PolicyTextDataset(test_rows, use_soft_labels=False, torch_module=torch)
	collate_fn = make_collate_fn(tokenizer, torch, args.max_length)
	train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)
	validation_loader = torch.utils.data.DataLoader(validation_dataset, batch_size=args.eval_batch_size, shuffle=False, collate_fn=collate_fn)
	test_loader = torch.utils.data.DataLoader(test_dataset, batch_size=args.eval_batch_size, shuffle=False, collate_fn=collate_fn)

	pos_weight = torch.tensor(compute_pos_weight(label_matrix(train_rows)), dtype=torch.float32, device=device)
	loss_fn = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)
	optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay)
	total_steps = max(len(train_loader) * args.epochs, 1)
	warmup_steps = int(total_steps * args.warmup_ratio)

	def lr_lambda(step: int) -> float:
		if warmup_steps and step < warmup_steps:
			return max(step / max(warmup_steps, 1), 1e-8)
		remaining = total_steps - step
		decay_steps = max(total_steps - warmup_steps, 1)
		return max(remaining / decay_steps, 0.0)

	scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

	checkpoint_dir = resolved_checkpoint_dir(args)
	metrics_rows: list[dict[str, Any]] = []
	best_state = None
	best_epoch = None
	best_validation_macro_f1 = -1.0
	start_epoch = 1
	if args.resume:
		latest_checkpoint = latest_checkpoint_path(checkpoint_dir)
		if latest_checkpoint is not None:
			payload = load_checkpoint(torch_module=torch, path=latest_checkpoint, model=model, optimizer=optimizer, scheduler=scheduler, device=device)
			start_epoch = int(payload["epoch"]) + 1
			best_epoch = payload.get("best_epoch")
			best_validation_macro_f1 = float(payload.get("best_validation_macro_f1", -1.0))
			best_state = payload.get("best_state")
			metrics_rows = list(payload.get("metrics_rows", []))
			logger.info("Resumed from checkpoint=%s next_epoch=%s", latest_checkpoint, start_epoch)
		else:
			logger.info("Resume requested but no checkpoint found under %s; starting from epoch 1", checkpoint_dir)

	started = time.perf_counter()
	try:
		for epoch in range(start_epoch, args.epochs + 1):
			epoch_started = time.perf_counter()
			train_loss = train_one_epoch(
				model=model,
				loader=train_loader,
				optimizer=optimizer,
				scheduler=scheduler,
				loss_fn=loss_fn,
				device=device,
			)
			validation_probabilities = predict(model=model, loader=validation_loader, device=device, torch_module=torch)
			validation_metrics = compute_multilabel_metrics(label_matrix(validation_rows), validation_probabilities)
			metrics_rows.append({"epoch": epoch, "split": "validation", "train_loss": train_loss, **validation_metrics})
			args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
			flatten_metrics(metrics_rows).to_csv(args.metrics_output, index=False)
			logger.info(
				"epoch=%s/%s train_loss=%.4f validation_macro_f1=%.4f elapsed_seconds=%.2f",
				epoch,
				args.epochs,
				train_loss,
				validation_metrics["macro_f1"],
				time.perf_counter() - epoch_started,
			)
			if validation_metrics["macro_f1"] > best_validation_macro_f1:
				best_validation_macro_f1 = validation_metrics["macro_f1"]
				best_epoch = epoch
				best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
			checkpoint = save_checkpoint(
				torch_module=torch,
				checkpoint_dir=checkpoint_dir,
				epoch=epoch,
				model=model,
				optimizer=optimizer,
				scheduler=scheduler,
				best_epoch=best_epoch,
				best_validation_macro_f1=best_validation_macro_f1,
				best_state=best_state,
				metrics_rows=metrics_rows,
			)
			logger.info("Saved checkpoint: %s", checkpoint)
	except KeyboardInterrupt:
		logger.warning("Training interrupted. Resume with `just manual-srdi-macbert-train` or pass --resume explicitly.")
		raise
	except Exception:
		logger.exception("Training failed before completion")
		raise

	if best_state is not None:
		model.load_state_dict(best_state)

	test_probabilities = predict(model=model, loader=test_loader, device=device, torch_module=torch)
	test_metrics = compute_multilabel_metrics(label_matrix(test_rows), test_probabilities)
	metrics_rows.append({"epoch": best_epoch, "split": "test", "train_loss": "", **test_metrics})

	args.output_dir.mkdir(parents=True, exist_ok=True)
	model.save_pretrained(args.output_dir)
	tokenizer.save_pretrained(args.output_dir)

	args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
	flatten_metrics(metrics_rows).to_csv(args.metrics_output, index=False)
	write_predictions(test_rows, test_probabilities, args.test_predictions_output)
	build_quality_report(
		args=args,
		train_rows=train_rows,
		validation_rows=validation_rows,
		test_rows=test_rows,
		best_epoch=best_epoch,
		best_validation_macro_f1=best_validation_macro_f1,
		device=str(device),
		dry_run=False,
	).assign(elapsed_seconds=round(time.perf_counter() - started, 2)).to_csv(args.quality_output, index=False)
	logger.info("Wrote model: %s", args.output_dir)
	logger.info("Wrote metrics: %s", args.metrics_output)
	logger.info("Wrote test predictions: %s", args.test_predictions_output)
	logger.info("Wrote quality report: %s", args.quality_output)


def main() -> None:
	run_training(parse_args())


if __name__ == "__main__":
	main()
