"""Label the manual SRDI round-1 sample with DeepSeek-compatible chat API.

The script reads the deterministic round-1 sample prepared by
``notebooks/46_manual_srdi_label_rule_keywords.py`` and writes three artifacts:

- cached raw API responses under ``data/raw/json/``;
- parsed row-level multi-label outputs under ``data/interim/``;
- a compact run quality report under ``outputs/``.

The API key is read only from ``DEEPSEEK_API_KEY``. Do not put secrets in config
files, command arguments, notebooks, or committed docs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_sample_round1_v1.csv"
DEFAULT_RAW_DIR = ROOT / "data" / "raw" / "json" / "manual_srdi_deepseek_round1_v1"
DEFAULT_LABELS_OUTPUT = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_labels_round1_v1.csv"
DEFAULT_QUALITY_OUTPUT = ROOT / "outputs" / "manual_policy_srdi_deepseek_round1_quality_report_v1.csv"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_RANDOM_STATE = 42

REQUIRED_INPUT_COLUMNS = {
	"doc_id",
	"province",
	"year",
	"title",
	"issuing_agency",
	"publish_date",
	"source_url",
	"clean_text",
	"sample_pool",
}

PROBABILITY_FIELDS = ("p_supply", "p_demand", "p_environment", "p_other")
EVIDENCE_FIELDS = ("supply_evidence", "demand_evidence", "environment_evidence")


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
	parser.add_argument("--raw-output-dir", type=Path, default=DEFAULT_RAW_DIR)
	parser.add_argument("--labels-output", type=Path, default=DEFAULT_LABELS_OUTPUT)
	parser.add_argument("--quality-output", type=Path, default=DEFAULT_QUALITY_OUTPUT)
	parser.add_argument("--model", default=DEFAULT_MODEL)
	parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
	parser.add_argument("--limit", type=int, default=None, help="Optional first-N cap for pilot runs.")
	parser.add_argument("--max-text-chars", type=int, default=12000)
	parser.add_argument("--sleep-seconds", type=float, default=0.5)
	parser.add_argument("--timeout-seconds", type=float, default=90.0)
	parser.add_argument("--resume", action="store_true", help="Reuse cached raw JSON responses when present.")
	parser.add_argument("--dry-run", action="store_true", help="Validate prompts and outputs without API calls.")
	parser.add_argument("--fail-fast", action="store_true", help="Stop at the first API or parse failure.")
	return parser.parse_args()


def utc_now_iso() -> str:
	return datetime.now(UTC).replace(microsecond=0).isoformat()


def stable_text_hash(value: str) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def safe_doc_id(value: str) -> str:
	return re.sub(r"[^0-9A-Za-z_-]+", "_", str(value)).strip("_")[:120]


def validate_input_columns(frame: pd.DataFrame) -> None:
	missing = REQUIRED_INPUT_COLUMNS.difference(frame.columns)
	if missing:
		raise ValueError(f"Input sample is missing required columns: {sorted(missing)}")
	if frame["doc_id"].duplicated().any():
		dupes = frame.loc[frame["doc_id"].duplicated(), "doc_id"].head(5).tolist()
		raise ValueError(f"Input sample has duplicate doc_id values, e.g. {dupes}")


def build_system_prompt() -> str:
	return (
		"你是一名中国公共政策文本编码员。请以整篇政策文件为单位，"
		"判断文本是否包含供给型、需求型、环境型政策工具，以及是否应归为 other。"
		"四个概率相互独立，不要求相加为 1。必须只输出一个 JSON object，"
		"不要输出 Markdown、解释性前后缀或代码块。"
	)


def build_user_prompt(row: pd.Series, max_text_chars: int) -> str:
	text = str(row["clean_text"])
	truncated = text[:max_text_chars]
	truncation_note = ""
	if len(text) > max_text_chars:
		truncation_note = f"\n[注意：正文已从 {len(text)} 字截断到前 {max_text_chars} 字用于标注。]"

	return f"""请对以下政策文本进行多标签概率标注。

标签定义：
1. supply：政府直接提供资源，例如资金奖励、财政补贴、研发补助、技术改造补助、人才支持、培训服务、公共服务平台、基础设施、创新平台、数字化改造支持。
2. demand：政府创造、扩大或引导市场需求，例如政府采购、首台套推广、示范应用、应用场景开放、供需对接、展会推广、市场开拓、产品推广、产业链对接。
3. environment：政府改善制度、金融、知识产权、标准、认定评价、营商环境等外部环境。金融支持、贷款、担保、上市培育通常归 environment，不归 supply，除非文本明确写财政直接奖励、补助、拨款。
4. other：文本不适合进入政策工具分析，例如纯通知、公示、名单、新闻、解读、非专精特新相关文本、正文缺失、只有程序性安排且没有实质扶持措施。

边界规则：
- 如果标题像通知，但正文包含明确扶持措施，不要仅凭标题判为 other。
- 如果只是组织申报、名单公示、转发通知，且没有实质扶持工具，则 other 应较高。
- supply、demand、environment 可以同时较高；other 高时，前三类通常应较低。

请输出严格 JSON object，字段必须为：
{{
  "p_supply": 0.0,
  "supply_evidence": [],
  "p_demand": 0.0,
  "demand_evidence": [],
  "p_environment": 0.0,
  "environment_evidence": [],
  "p_other": 0.0,
  "other_reason": "",
  "has_substantive_policy_tool": true,
  "is_srdi_related": true,
  "summary_reason": ""
}}

政策元数据：
- doc_id: {row["doc_id"]}
- province: {row["province"]}
- year: {row["year"]}
- title: {row["title"]}
- issuing_agency: {row["issuing_agency"]}
- publish_date: {row["publish_date"]}
- source_url: {row["source_url"]}
- sampling_pool: {row["sample_pool"]}
{truncation_note}

政策正文：
{truncated}
"""


def build_chat_payload(row: pd.Series, *, model: str, max_text_chars: int) -> dict[str, Any]:
	return {
		"model": model,
		"temperature": 0,
		"response_format": {"type": "json_object"},
		"messages": [
			{"role": "system", "content": build_system_prompt()},
			{"role": "user", "content": build_user_prompt(row, max_text_chars=max_text_chars)},
		],
	}


def post_chat_completion(
	*,
	api_key: str,
	base_url: str,
	payload: dict[str, Any],
	timeout_seconds: float,
) -> dict[str, Any]:
	url = f"{base_url.rstrip('/')}/chat/completions"
	request = urllib.request.Request(
		url,
		data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
		headers={
			"Authorization": f"Bearer {api_key}",
			"Content-Type": "application/json",
		},
		method="POST",
	)
	try:
		with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
			body = response.read().decode("utf-8")
	except urllib.error.HTTPError as exc:
		error_body = exc.read().decode("utf-8", errors="replace")
		raise RuntimeError(f"DeepSeek HTTP {exc.code}: {error_body[:500]}") from exc
	except urllib.error.URLError as exc:
		raise RuntimeError(f"DeepSeek request failed: {exc}") from exc
	return json.loads(body)


def extract_message_content(api_response: dict[str, Any]) -> str:
	try:
		return str(api_response["choices"][0]["message"]["content"])
	except (KeyError, IndexError, TypeError) as exc:
		raise ValueError("API response does not contain choices[0].message.content") from exc


def parse_model_content(content: str) -> dict[str, Any]:
	"""Parse a JSON object from the model content, tolerating fenced output."""
	cleaned = content.strip()
	if cleaned.startswith("```"):
		cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
		cleaned = re.sub(r"\s*```$", "", cleaned)
	try:
		value = json.loads(cleaned)
	except json.JSONDecodeError:
		start = cleaned.find("{")
		end = cleaned.rfind("}")
		if start < 0 or end <= start:
			raise
		value = json.loads(cleaned[start : end + 1])
	if not isinstance(value, dict):
		raise ValueError("Model content JSON is not an object.")
	return value


def clamp_probability(value: Any) -> float:
	try:
		probability = float(value)
	except (TypeError, ValueError):
		probability = 0.0
	return max(0.0, min(1.0, probability))


def normalize_evidence(value: Any) -> list[str]:
	if value is None:
		return []
	if isinstance(value, list):
		return [str(item).strip() for item in value if str(item).strip()]
	if isinstance(value, str):
		return [value.strip()] if value.strip() else []
	return [str(value).strip()] if str(value).strip() else []


def normalize_label_payload(payload: dict[str, Any]) -> dict[str, Any]:
	normalized: dict[str, Any] = {
		field: clamp_probability(payload.get(field, 0.0)) for field in PROBABILITY_FIELDS
	}
	for field in EVIDENCE_FIELDS:
		normalized[field] = normalize_evidence(payload.get(field))
	normalized["other_reason"] = str(payload.get("other_reason", "") or "").strip()
	normalized["has_substantive_policy_tool"] = bool(payload.get("has_substantive_policy_tool", False))
	normalized["is_srdi_related"] = bool(payload.get("is_srdi_related", False))
	normalized["summary_reason"] = str(payload.get("summary_reason", "") or "").strip()
	return normalized


def derive_binary_labels(label: dict[str, Any]) -> dict[str, int]:
	max_tool_probability = max(label["p_supply"], label["p_demand"], label["p_environment"])
	return {
		"y_supply": int(label["p_supply"] >= 0.5),
		"y_demand": int(label["p_demand"] >= 0.5),
		"y_environment": int(label["p_environment"] >= 0.5),
		"y_other": int(label["p_other"] >= 0.6 and max_tool_probability < 0.4),
	}


def make_empty_label() -> dict[str, Any]:
	return {
		"p_supply": pd.NA,
		"supply_evidence": [],
		"p_demand": pd.NA,
		"demand_evidence": [],
		"p_environment": pd.NA,
		"environment_evidence": [],
		"p_other": pd.NA,
		"other_reason": "",
		"has_substantive_policy_tool": pd.NA,
		"is_srdi_related": pd.NA,
		"summary_reason": "",
	}


def raw_response_path(raw_output_dir: Path, doc_id: str) -> Path:
	return raw_output_dir / f"{safe_doc_id(doc_id)}.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
	return json.loads(path.read_text(encoding="utf-8"))


def build_output_row(
	row: pd.Series,
	*,
	label: dict[str, Any],
	status: str,
	model: str,
	raw_path: Path | None,
	error: str = "",
	max_text_chars: int,
) -> dict[str, Any]:
	output = {
		"doc_id": row["doc_id"],
		"sample_pool": row["sample_pool"],
		"province": row["province"],
		"year": row["year"],
		"title": row["title"],
		"issuing_agency": row["issuing_agency"],
		"publish_date": row["publish_date"],
		"source_url": row["source_url"],
		"model": model,
		"label_status": status,
		"error": error,
		"raw_response_path": str(raw_path.relative_to(ROOT)) if raw_path else "",
		"text_len": len(str(row["clean_text"])),
		"prompt_text_chars": min(len(str(row["clean_text"])), max_text_chars),
		"labeled_at": utc_now_iso(),
	}
	output.update(
		{
			"p_supply": label["p_supply"],
			"supply_evidence": json.dumps(label["supply_evidence"], ensure_ascii=False),
			"p_demand": label["p_demand"],
			"demand_evidence": json.dumps(label["demand_evidence"], ensure_ascii=False),
			"p_environment": label["p_environment"],
			"environment_evidence": json.dumps(label["environment_evidence"], ensure_ascii=False),
			"p_other": label["p_other"],
			"other_reason": label["other_reason"],
			"has_substantive_policy_tool": label["has_substantive_policy_tool"],
			"is_srdi_related": label["is_srdi_related"],
			"summary_reason": label["summary_reason"],
		}
	)
	output.update(derive_binary_labels(label) if status == "success" else {
		"y_supply": pd.NA,
		"y_demand": pd.NA,
		"y_environment": pd.NA,
		"y_other": pd.NA,
	})
	return output


def parse_cached_or_live_response(path: Path) -> dict[str, Any]:
	artifact = read_json(path)
	api_response = artifact.get("api_response", artifact)
	content = extract_message_content(api_response)
	return normalize_label_payload(parse_model_content(content))


def label_one_row(row: pd.Series, args: argparse.Namespace, api_key: str | None) -> dict[str, Any]:
	raw_path = raw_response_path(args.raw_output_dir, str(row["doc_id"]))
	if args.dry_run:
		return build_output_row(
			row,
			label=make_empty_label(),
			status="dry_run",
			model=args.model,
			raw_path=None,
			max_text_chars=args.max_text_chars,
		)

	try:
		if args.resume and raw_path.exists():
			label = parse_cached_or_live_response(raw_path)
			return build_output_row(
				row,
				label=label,
				status="success",
				model=args.model,
				raw_path=raw_path,
				max_text_chars=args.max_text_chars,
			)

		if not api_key:
			raise RuntimeError("DEEPSEEK_API_KEY is not set.")
		payload = build_chat_payload(row, model=args.model, max_text_chars=args.max_text_chars)
		api_response = post_chat_completion(
			api_key=api_key,
			base_url=args.base_url,
			payload=payload,
			timeout_seconds=args.timeout_seconds,
		)
		artifact = {
			"doc_id": row["doc_id"],
			"model": args.model,
			"base_url": args.base_url,
			"created_at": utc_now_iso(),
			"max_text_chars": args.max_text_chars,
			"clean_text_sha256": stable_text_hash(str(row["clean_text"])),
			"api_response": api_response,
		}
		write_json(raw_path, artifact)
		label = normalize_label_payload(parse_model_content(extract_message_content(api_response)))
		return build_output_row(
			row,
			label=label,
			status="success",
			model=args.model,
			raw_path=raw_path,
			max_text_chars=args.max_text_chars,
		)
	except Exception as exc:
		if args.fail_fast:
			raise
		return build_output_row(
			row,
			label=make_empty_label(),
			status="failed",
			model=args.model,
			raw_path=raw_path if raw_path.exists() else None,
			error=str(exc),
			max_text_chars=args.max_text_chars,
		)


def build_quality_report(labels: pd.DataFrame, *, input_records: int, requested_records: int) -> pd.DataFrame:
	rows: list[dict[str, Any]] = [
		{"metric": "input_records", "value": input_records, "note": "Rows in the round-1 sample input."},
		{"metric": "requested_records", "value": requested_records, "note": "Rows selected for this run after --limit."},
		{"metric": "output_records", "value": len(labels), "note": "Rows written to the labels output."},
		{
			"metric": "success_records",
			"value": int(labels["label_status"].eq("success").sum()),
			"note": "Rows with parsed DeepSeek labels.",
		},
		{
			"metric": "failed_records",
			"value": int(labels["label_status"].eq("failed").sum()),
			"note": "Rows that failed API or parse handling.",
		},
		{
			"metric": "dry_run_records",
			"value": int(labels["label_status"].eq("dry_run").sum()),
			"note": "Rows validated without API calls.",
		},
		{
			"metric": "unique_doc_ids",
			"value": int(labels["doc_id"].nunique()),
			"note": "Unique documents in the output labels.",
		},
	]
	for pool, count in labels["sample_pool"].value_counts().sort_index().items():
		rows.append(
			{
				"metric": f"sample_pool_{pool}_records",
				"value": int(count),
				"note": "Output rows by round-1 sample pool.",
			}
		)
	return pd.DataFrame(rows)


def run_labeling(args: argparse.Namespace) -> tuple[pd.DataFrame, pd.DataFrame]:
	sample = pd.read_csv(args.input)
	validate_input_columns(sample)
	selected = sample.head(args.limit) if args.limit is not None else sample
	api_key = None if args.dry_run else os.environ.get("DEEPSEEK_API_KEY")

	records: list[dict[str, Any]] = []
	for idx, row in selected.iterrows():
		records.append(label_one_row(row, args, api_key))
		if not args.dry_run and idx != selected.index[-1] and args.sleep_seconds > 0:
			time.sleep(args.sleep_seconds)

	labels = pd.DataFrame(records)
	quality = build_quality_report(labels, input_records=len(sample), requested_records=len(selected))

	args.labels_output.parent.mkdir(parents=True, exist_ok=True)
	args.quality_output.parent.mkdir(parents=True, exist_ok=True)
	labels.to_csv(args.labels_output, index=False)
	quality.to_csv(args.quality_output, index=False)
	return labels, quality


def main() -> None:
	args = parse_args()
	labels, quality = run_labeling(args)
	print(f"Wrote labels: {args.labels_output} ({len(labels)} rows)")
	print(f"Wrote quality report: {args.quality_output} ({len(quality)} rows)")
	print(labels["label_status"].value_counts().sort_index().to_dict())


if __name__ == "__main__":
	main()
