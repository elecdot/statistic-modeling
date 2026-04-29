"""Parsers for gov.cn XXGK list JSON and detail HTML."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from statistic_modeling.policy_text_crawler.config import QueryBatch, SourceConfig

DETAIL_SELECTORS = [".pages_content", ".article", ".content", ".TRS_Editor", "#UCAP-CONTENT", "article"]
ATTACHMENT_RE = re.compile(r"\.(pdf|doc|docx|xls|xlsx|wps|zip)(?:$|[?#])", flags=re.IGNORECASE)
DATE_RE = re.compile(r"(?:发布时间|发布日期|成文日期)[:：\s]*([0-9]{4}[-年][0-9]{1,2}[-月][0-9]{1,2})")


def clean_text(value: str | None) -> str:
	return " ".join(str(value or "").split())


def clean_html_text(value: str | None) -> str:
	return clean_text(BeautifulSoup(value or "", "html.parser").get_text("", strip=True))


def normalize_policy_title(title: str) -> str:
	title = clean_text(title.replace("_中国政府网", ""))
	return title.split("_", 1)[0] if "_" in title else title


def infer_agency_from_title(title: str) -> str | None:
	if title.startswith("国务院办公厅"):
		return "国务院办公厅"
	if title.startswith("国务院"):
		return "国务院"
	return None


def infer_agency_from_candidate(title: str, fwzh: str | None) -> str | None:
	if agency := infer_agency_from_title(title):
		return agency
	if str(fwzh or "").startswith("国令"):
		return "国务院"
	return None


def infer_document_type(title: str, attachment_urls: list[str]) -> str:
	if any(word in title for word in ["通知", "意见", "办法", "规划", "方案", "公告", "通告"]):
		return "policy_document"
	if attachment_urls:
		return "attachment_page"
	return "needs_review"


def make_policy_id(source_id: str, source_url: str) -> str:
	digest = hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:16]
	return f"{source_id}_{digest}"


def text_hash(text: str) -> str:
	return hashlib.sha256(clean_text(text).encode("utf-8")).hexdigest()


def parse_list_candidates(
	response_payload: dict,
	*,
	config: SourceConfig,
	batch: QueryBatch,
	raw_json_path: Path,
) -> list[dict]:
	"""Normalize candidate detail URLs from one list JSON response."""
	result_data = response_payload.get("result", {}).get("data", {})
	pager = result_data.get("pager", {})
	page_no = pager.get("pageNo", 1)
	records = []
	for item in result_data.get("list", []) or []:
		source_url = urljoin(config.landing_url + "/", item.get("pub_url", ""))
		title = clean_html_text(item.get("maintitle", ""))
		records.append(
			{
				"candidate_id": make_policy_id(config.source_id, source_url),
				"query_batch_id": batch.query_batch_id,
				"province": config.jurisdiction,
				"source_site": config.source_site,
				"title": title,
				"fwzh": clean_text(item.get("fwzh", "")),
				"cwrq": item.get("cwrq"),
				"publish_time": item.get("publish_time"),
				"source_url": source_url,
				"keyword_hit": batch.keyword,
				"category_id": 1100,
				"page_no": page_no,
				"list_total": pager.get("total"),
				"list_page_count": pager.get("pageCount"),
				"list_page_size": pager.get("pageSize"),
				"parse_status": "success",
				"raw_json_path": str(raw_json_path),
			},
		)
	return records


def parse_detail_html(
	html: str,
	*,
	config: SourceConfig,
	candidate: dict,
	final_url: str | None = None,
	raw_html_path: Path | None = None,
) -> dict:
	"""Parse one public policy detail HTML page into the crawler output schema."""
	url = final_url or candidate["source_url"]
	title_hint = candidate.get("title") or ""
	fwzh = candidate.get("fwzh")
	candidate_date = str(candidate.get("publish_time") or candidate.get("cwrq") or "").split(" ")[0] or None
	soup = BeautifulSoup(html, "html.parser")

	title = ""
	if soup.select_one("h1"):
		title = normalize_policy_title(soup.select_one("h1").get_text(" ", strip=True))
	if not title and soup.title:
		title = normalize_policy_title(soup.title.get_text(" ", strip=True))
	if not title:
		title = title_hint

	agency = ""
	for label in ["source", "ContentSource"]:
		meta = soup.find("meta", attrs={"name": label})
		if meta and meta.get("content"):
			agency = clean_text(meta["content"])
			break

	body_text = ""
	for selector in DETAIL_SELECTORS:
		body = soup.select_one(selector)
		if body:
			body_text = clean_text(body.get_text(" ", strip=True))
			if len(body_text) >= 80:
				break
	if not body_text:
		body_text = clean_text(soup.get_text(" ", strip=True))

	date_match = DATE_RE.search(body_text)
	attachment_urls: list[str] = []
	for anchor in soup.select("a[href]"):
		href = anchor.get("href", "")
		anchor_text = clean_text(anchor.get_text(" ", strip=True))
		if ATTACHMENT_RE.search(href) or "附件" in anchor_text:
			attachment_urls.append(urljoin(url, href))

	parse_status = "success" if len(body_text) >= 80 else "partial"
	review_status = "needs_review" if len(body_text) < 200 else "accepted"
	crawl_time = datetime.now(UTC).isoformat()
	return {
		"policy_id": candidate.get("candidate_id") or make_policy_id(config.source_id, url),
		"province": config.jurisdiction,
		"title": title,
		"publish_date": date_match.group(1).replace("年", "-").replace("月", "-").replace("日", "") if date_match else candidate_date,
		"agency": infer_agency_from_candidate(title, fwzh) or agency or infer_agency_from_candidate(title_hint, fwzh),
		"source_site": config.source_site,
		"source_url": url,
		"query_batch_id": candidate.get("query_batch_id"),
		"keyword_hit": candidate.get("keyword_hit") or candidate.get("keyword"),
		"document_type": infer_document_type(title, attachment_urls),
		"text_raw": body_text,
		"text_clean": clean_text(body_text),
		"attachment_urls": attachment_urls,
		"raw_json_path": candidate.get("raw_json_path"),
		"raw_html_path": str(raw_html_path) if raw_html_path else None,
		"parse_status": parse_status,
		"review_status": review_status,
		"error": None,
		"crawl_time": crawl_time,
		"text_hash": text_hash(body_text) if body_text else None,
	}
