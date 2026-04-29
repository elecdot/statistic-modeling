"""Pipeline orchestration for the gov.cn XXGK pilot crawler."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

from statistic_modeling.policy_text_crawler.config import QueryBatch, SourceConfig
from statistic_modeling.policy_text_crawler.govcn_xxgk_gateway import (
	build_code_url,
	build_list_payload,
	request_json,
)
from statistic_modeling.policy_text_crawler.govcn_xxgk_parser import parse_detail_html, parse_list_candidates


def build_list_page_queue(config: SourceConfig, batches: list[QueryBatch]) -> pd.DataFrame:
	"""Build the planned list-request queue without calling the network."""
	rows = []
	for batch in batches:
		for page_no in range(1, batch.max_pages + 1):
			rows.append(
				{
					"list_request_id": f"{batch.query_batch_id}_page_{page_no:03d}",
					"query_batch_id": batch.query_batch_id,
					"source_id": config.source_id,
					"source_site": config.source_site,
					"keyword": batch.keyword,
					"search_position": batch.search_position,
					"match_mode": batch.match_mode,
					"sort_by": batch.sort_by,
					"page_no": page_no,
					"page_size": batch.page_size,
					"raw_json_path": f"data/raw/json/{config.source_id}_{batch.query_batch_id}_page_{page_no:03d}.json",
					"request_status": "pending" if batch.enabled else "skipped",
					"stop_reason": "" if batch.enabled else "Batch documented but disabled.",
				},
			)
	return pd.DataFrame(rows)


def _publish_dates_from_list_payload(response_payload: dict) -> pd.Series:
	items = response_payload.get("result", {}).get("data", {}).get("list", []) or []
	return pd.to_datetime([item.get("publish_time") or item.get("cwrq") for item in items], errors="coerce")


def list_page_stop_reason(response_payload: dict, config: SourceConfig, batch: QueryBatch) -> str:
	"""Return the reason to stop pagination after this list page, or an empty string."""
	result_data = response_payload.get("result", {}).get("data", {})
	items = result_data.get("list", []) or []
	pager = result_data.get("pager", {})
	page_no = int(pager.get("pageNo") or 1)
	page_count = int(pager.get("pageCount") or page_no)
	if not items:
		return "empty_list"
	if config.pagination.get("stop_after_page_count", True) and page_no >= page_count:
		return "reached_page_count"
	if (
		config.pagination.get("stop_when_sorted_page_before_start_date", True)
		and batch.sort_by == "time"
		and batch.sort_field == "publish_time"
	):
		dates = _publish_dates_from_list_payload(response_payload).dropna()
		if not dates.empty:
			start_date = pd.Timestamp(config.target_scope["start_date"])
			if dates.min() < start_date:
				return "page_crossed_target_start_date"
	return ""


def planned_raw_json_path(workspace_root: Path, config: SourceConfig, batch: QueryBatch, page_no: int) -> Path:
	return workspace_root / "data" / "raw" / "json" / f"{config.source_id}_{batch.query_batch_id}_page_{page_no:03d}.json"


def legacy_raw_json_path(workspace_root: Path, batch: QueryBatch) -> Path:
	"""Support notebook-20 cached list artifacts while the crawler is being introduced."""
	return workspace_root / "data" / "raw" / "json" / f"central_gov_xxgk_list_{batch.keyword}.json"


def load_cached_list_payload(workspace_root: Path, config: SourceConfig, batch: QueryBatch, page_no: int) -> tuple[dict, Path] | None:
	paths = [planned_raw_json_path(workspace_root, config, batch, page_no)]
	if page_no == 1:
		paths.append(legacy_raw_json_path(workspace_root, batch))
	for path in paths:
		if path.exists():
			return json.loads(path.read_text(encoding="utf-8")), path
	return None


def collect_list_candidates_from_cache(
	workspace_root: Path,
	config: SourceConfig,
	batches: list[QueryBatch],
) -> pd.DataFrame:
	"""Parse available raw list JSON without sending requests."""
	records: list[dict] = []
	for batch in batches:
		for page_no in range(1, batch.max_pages + 1):
			cached = load_cached_list_payload(workspace_root, config, batch, page_no)
			if cached is None:
				continue
			payload, raw_path = cached
			records.extend(parse_list_candidates(payload, config=config, batch=batch, raw_json_path=raw_path))
	return pd.DataFrame(records)


def select_detail_candidates(candidates: pd.DataFrame, *, max_per_batch: int | None = 3) -> pd.DataFrame:
	"""Limit detail-page work to a reviewable pilot sample by default."""
	if candidates.empty or max_per_batch is None:
		return candidates
	if max_per_batch <= 0:
		return candidates.iloc[0:0].copy()
	return (
		candidates.drop_duplicates(["query_batch_id", "source_url"])
		.groupby("query_batch_id", group_keys=False)
		.head(max_per_batch)
		.reset_index(drop=True)
	)


def filter_candidates_to_target_window(candidates: pd.DataFrame, config: SourceConfig) -> pd.DataFrame:
	"""Keep only candidate rows whose list-level date is inside the target window."""
	if candidates.empty:
		return candidates
	scope = config.target_scope
	start_date = date.fromisoformat(scope["start_date"])
	end_date = date.fromisoformat(scope["end_date"])
	filtered = candidates.copy()
	publish_dates = pd.to_datetime(filtered.get("publish_time", filtered.get("cwrq")), errors="coerce").dt.date
	in_window = publish_dates.between(start_date, end_date)
	return filtered[in_window.fillna(False)].reset_index(drop=True)


def aggregate_candidate_provenance(candidates: pd.DataFrame) -> pd.DataFrame:
	"""Deduplicate detail URLs while preserving all keyword/query provenance."""
	if candidates.empty:
		return candidates

	def merge_unique(values: pd.Series) -> str:
		seen = []
		for value in values.dropna().astype(str):
			if value and value not in seen:
				seen.append(value)
		return ";".join(seen)

	rows = []
	for _, group in candidates.groupby("source_url", sort=False):
		record = group.iloc[0].to_dict()
		for column in ["keyword_hit", "query_batch_id", "raw_json_path", "candidate_id"]:
			if column in group:
				record[column] = merge_unique(group[column])
		rows.append(record)
	return pd.DataFrame(rows)


def filter_records_to_target_window(details: pd.DataFrame, config: SourceConfig) -> pd.DataFrame:
	"""Flag records outside the configured publication-date window.

	The source gateway is sorted by publication date but the current pilot does
	not depend on undocumented date-filter parameters. For full 2025-2020 runs,
	this explicit post-parse rule keeps the corpus boundary auditable.
	"""
	if details.empty:
		return details
	scope = config.target_scope
	start_date = date.fromisoformat(scope["start_date"])
	end_date = date.fromisoformat(scope["end_date"])
	filtered = details.copy()
	publish_dates = pd.to_datetime(filtered["publish_date"], errors="coerce").dt.date
	in_window = publish_dates.between(start_date, end_date)
	filtered["in_target_date_window"] = in_window.fillna(False)
	filtered.loc[~filtered["in_target_date_window"], "review_status"] = "needs_review"
	filtered.loc[~filtered["in_target_date_window"], "parse_status"] = "skipped_out_of_scope"
	return filtered


def fetch_list_candidates_live(
	workspace_root: Path,
	config: SourceConfig,
	batches: list[QueryBatch],
	*,
	max_pages_override: int | None = None,
) -> pd.DataFrame:
	"""Fetch enabled list batches live and archive raw JSON responses."""
	code_payload = request_json(config, build_code_url(config))
	code = code_payload.get("result", {}).get("data")
	if not code:
		raise RuntimeError(f"Gateway code request did not return a code: {code_payload!r}")

	records: list[dict] = []
	raw_dir = workspace_root / "data" / "raw" / "json"
	raw_dir.mkdir(parents=True, exist_ok=True)
	for batch in batches:
		max_pages = max_pages_override if max_pages_override is not None else batch.max_pages
		for page_no in range(1, max_pages + 1):
			payload = build_list_payload(config, batch, code=code, page_no=page_no)
			response_payload = request_json(config, config.list_url, payload=payload)
			raw_path = planned_raw_json_path(workspace_root, config, batch, page_no)
			raw_path.write_text(json.dumps(response_payload, ensure_ascii=False, indent=2), encoding="utf-8")
			records.extend(parse_list_candidates(response_payload, config=config, batch=batch, raw_json_path=raw_path))
			if list_page_stop_reason(response_payload, config, batch):
				break
			time.sleep(float(config.request_policy["min_delay_seconds"]))
	return pd.DataFrame(records)


def _safe_detail_name(url: str) -> str:
	safe_name = re.sub(r"[^A-Za-z0-9]+", "_", url).strip("_")[:120] or "detail"
	return f"central_gov_xxgk_detail_{safe_name}.html"


def _cached_detail_path(workspace_root: Path, source_url: str) -> Path | None:
	raw_dir = workspace_root / "data" / "raw" / "html"
	candidates = [source_url]
	if source_url.startswith("http://"):
		candidates.append("https://" + source_url.removeprefix("http://"))
	for url in candidates:
		path = raw_dir / _safe_detail_name(url)
		if path.exists():
			return path
	return None


def parse_detail_records_from_cache(workspace_root: Path, config: SourceConfig, candidates: pd.DataFrame) -> pd.DataFrame:
	"""Parse cached detail HTML for candidate URLs."""
	records = []
	for candidate in candidates.drop_duplicates("source_url").to_dict("records"):
		raw_path = _cached_detail_path(workspace_root, candidate["source_url"])
		if raw_path is None:
			record = {
				"policy_id": candidate.get("candidate_id"),
				"province": config.jurisdiction,
				"title": candidate.get("title"),
				"publish_date": str(candidate.get("publish_time") or candidate.get("cwrq") or "").split(" ")[0] or None,
				"agency": None,
				"source_site": config.source_site,
				"source_url": candidate["source_url"],
				"query_batch_id": candidate.get("query_batch_id"),
				"keyword_hit": candidate.get("keyword_hit"),
				"document_type": None,
				"text_raw": "",
				"text_clean": "",
				"attachment_urls": [],
				"raw_json_path": candidate.get("raw_json_path"),
				"raw_html_path": None,
				"parse_status": "detail_failed",
				"review_status": "needs_review",
				"error": "cached detail HTML not found",
				"crawl_time": None,
				"text_hash": None,
			}
		else:
			html = raw_path.read_text(encoding="utf-8")
			record = parse_detail_html(html, config=config, candidate=candidate, raw_html_path=raw_path)
		records.append(record)
	return pd.DataFrame(records)


def fetch_and_parse_detail_records_live(workspace_root: Path, config: SourceConfig, candidates: pd.DataFrame) -> pd.DataFrame:
	"""Fetch public detail pages live, archive raw HTML, and parse records."""
	raw_dir = workspace_root / "data" / "raw" / "html"
	raw_dir.mkdir(parents=True, exist_ok=True)
	records = []
	for candidate in candidates.drop_duplicates("source_url").to_dict("records"):
		request = Request(
			candidate["source_url"],
			headers={"User-Agent": config.request_policy["user_agent"], "Referer": config.landing_url},
		)
		try:
			with urlopen(request, timeout=int(config.request_policy["timeout_seconds"])) as response:
				final_url = response.geturl()
				charset = response.headers.get_content_charset() or "utf-8"
				html = response.read().decode(charset, errors="replace")
			raw_path = raw_dir / _safe_detail_name(final_url)
			raw_path.write_text(html, encoding="utf-8")
			record = parse_detail_html(html, config=config, candidate=candidate, final_url=final_url, raw_html_path=raw_path)
		except Exception as exc:
			record = {
				"policy_id": candidate.get("candidate_id"),
				"province": config.jurisdiction,
				"title": candidate.get("title"),
				"publish_date": str(candidate.get("publish_time") or candidate.get("cwrq") or "").split(" ")[0] or None,
				"agency": None,
				"source_site": config.source_site,
				"source_url": candidate["source_url"],
				"query_batch_id": candidate.get("query_batch_id"),
				"keyword_hit": candidate.get("keyword_hit"),
				"document_type": None,
				"text_raw": "",
				"text_clean": "",
				"attachment_urls": [],
				"raw_json_path": candidate.get("raw_json_path"),
				"raw_html_path": None,
				"parse_status": "detail_failed",
				"review_status": "needs_review",
				"error": repr(exc),
				"crawl_time": None,
				"text_hash": None,
			}
		records.append(record)
		time.sleep(float(config.request_policy["min_delay_seconds"]))
	return pd.DataFrame(records)


def quality_summary(candidates: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
	"""Summarize the checks that gate crawler expansion."""
	return pd.DataFrame(
		[
				{
					"candidate_records": len(candidates),
					"detail_records": len(details),
				"success_details": int((details.get("parse_status") == "success").sum()) if not details.empty else 0,
				"partial_details": int((details.get("parse_status") == "partial").sum()) if not details.empty else 0,
				"failed_details": int((details.get("parse_status") == "detail_failed").sum()) if not details.empty else 0,
				"empty_body_text": int((details.get("text_raw", pd.Series(dtype=str)).fillna("").str.len() == 0).sum()) if not details.empty else 0,
				"short_body_text_lt_200": int((details.get("text_raw", pd.Series(dtype=str)).fillna("").str.len() < 200).sum()) if not details.empty else 0,
					"missing_publication_dates": int(details.get("publish_date", pd.Series(dtype=str)).isna().sum()) if not details.empty else 0,
					"out_of_target_date_window": int((~details["in_target_date_window"]).sum()) if "in_target_date_window" in details else 0,
					"duplicate_source_urls": int(candidates.duplicated("source_url").sum()) if "source_url" in candidates else 0,
				"duplicate_text_hashes": int(details.duplicated("text_hash").sum()) if "text_hash" in details else 0,
			},
		],
	)
