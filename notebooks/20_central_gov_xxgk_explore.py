# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: statistic-modeling (3.11.14)
#     language: python
#     name: python3
# ---

# %%
import base64
import json
import re
import secrets
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import pandas as pd
from IPython.display import display


def find_workspace_root(start: Path | None = None) -> Path:
	current = (start or Path.cwd()).resolve()
	for candidate in [current, *current.parents]:
		if (candidate / "pyproject.toml").exists():
			return candidate
	raise FileNotFoundError("Could not locate the workspace root from the current directory.")


workspace_root = find_workspace_root()
source_url = "https://www.gov.cn/zhengce/xxgk"
output_path = workspace_root / "data" / "tmp"
raw_html_path = workspace_root / "data" / "raw" / "html"
raw_json_path = workspace_root / "data" / "raw" / "json"
interim_path = workspace_root / "data" / "interim"
output_path.mkdir(parents=True, exist_ok=True)
raw_html_path.mkdir(parents=True, exist_ok=True)
raw_json_path.mkdir(parents=True, exist_ok=True)
interim_path.mkdir(parents=True, exist_ok=True)

# %% [markdown]
# # Agent Handoff: Central Gov XXGK Policy Collection
#
# This notebook is the handoff surface for the China Government Network policy information disclosure page:
# `https://www.gov.cn/zhengce/xxgk`.
#
# What this notebook does:
#
# 1. Saves the public XXGK landing page HTML for audit.
# 2. Reads the page script to reproduce the same small AJAX list request that the browser uses.
# 3. Saves raw list JSON under `data/raw/json/`.
# 4. Converts list rows into `data/interim/central_gov_xxgk_sirdi_candidates.csv`.
# 5. Fetches a few public policy detail pages and saves raw HTML under `data/raw/html/`.
# 6. Converts detail pages into `data/interim/central_gov_xxgk_sirdi_detail_probe.csv`.
#
# Current default scope:
#
# - Keywords: `专精特新`, `小巨人`, `中小企业`
# - Search position: title (`maintitle`)
# - Match mode: fuzzy (`isPreciseSearch=0`)
# - Sort order: latest publication date first (`sortField=publish_time`, `DESC`)
# - Page scope: first page only, 10 list rows per keyword
# - Detail probe: at most 3 detail pages per keyword
#
# Current known result:
#
# - `中小企业` returns candidate rows under title search.
# - `专精特新` and `小巨人` return no rows under title search; the next technical probe should try full-text search
#   (`fieldName=""`) before increasing page count.
#
# Maintenance rules for future agents:
#
# - Do not rewrite this notebook into a production crawler until the sampling decisions are stable.
# - Do not clear existing CSVs when a live request fails. This notebook intentionally falls back to archived raw
#   JSON/HTML so a sandboxed run cannot destroy successful probe outputs.
# - Keep requests low-frequency and bounded. This method calls a browser-facing gateway endpoint, so any expansion
#   needs explicit crawl-rate and compliance review.
# - Edit the paired `.py:percent` file first, then sync the `.ipynb` with Jupytext.

# %% [markdown]
# # Discover https://www.gov.cn/zhengce/xxgk
#
# Goal: capture the source HTML for the central government policy information disclosure portal.
#
# Initial observation:
# 1. the page is reachable with a plain HTTP request;
# 2. the response is static HTML rather than a browser-only render;
# 3. the policy links expose a search function, but the URL stays stable when the list changes.
#
# Output artifact for this probe:
# - directory: `data/raw`
# - file: `data/raw/gov_cn_zhengce_xxgk.html`

# %%
html_path = output_path / "gov_cn_zhengce_xxgk.html"
archived_html_path = raw_html_path / "gov_cn_zhengce_xxgk.html"

try:
	request = Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
	with urlopen(request, timeout=30) as response:
		final_url = response.geturl()
		status_code = response.status
		content_type = response.headers.get_content_type()
		charset = response.headers.get_content_charset() or "utf-8"
		html_text = response.read().decode(charset, errors="replace")
	html_path.write_text(html_text, encoding="utf-8")
	archived_html_path.write_text(html_text, encoding="utf-8")
	fetch_error = None
except (HTTPError, URLError, TimeoutError, OSError) as exc:
	if not archived_html_path.exists():
		raise
	final_url = source_url
	status_code = None
	content_type = "text/html"
	html_path = archived_html_path
	html_text = archived_html_path.read_text(encoding="utf-8")
	fetch_error = repr(exc)

title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
page_title = title_match.group(1).strip() if title_match else ""

probe_result = {
	"source_url": source_url,
	"final_url": final_url,
	"status_code": status_code,
	"content_type": content_type,
	"chars": len(html_text),
	"title": page_title,
	"saved_to": str(html_path),
	"fetch_error": fetch_error,
}

probe_result

# %% [markdown]
# ## Inspect the Source HTML
#
# Observations:
# 1. Search function is written in JS script (entrypoint: `changeFilter`) at the bottom of the file (`<script>`). Bad news: This query list MAY NOT be static...
# 2. the provincial platform links start at line 2025. Header snippet:
# ```html
#         <!-- 地方部门平台链接-->
#         <div class="zfxxgknb conr_part">
#           <div class="part_box1 part_box">
#             <p class="pb_title">省（区、市）政府信息公开平台</p>
#             <div class="tab_box">
#               <table>
#                 <tbody>
#                 <tr class="jishu">
#                   <td><a href="http://www.beijing.gov.cn/gongkai/zfxxgk/" target="_blank">北 京</a></td>
#                   <td><a href="http://www.tj.gov.cn/zwgk/zfxxgkzl/gkzn/" target="_blank">天 津</a></td>
#                   <td><a href="https://www.hebei.gov.cn/columns/7b96ca20-882f-436c-9d13-7c91d82ccd55/index.html" target="_blank">河
#                     北</a></td>
#                   <td><a href="https://www.shanxi.gov.cn/zfxxgk/zfxxgkzl/zfxxgkzn/" target="_blank">山 西</a></td>
#                   <td><a href="http://www.nmg.gov.cn/zwgk/zfxxgk/zfxxgkml/?gk=3" target="_blank">内蒙古</a></td>
#                 </tr>
#                 <tr>
#                   <td><a href="http://www.ln.gov.cn/zwgkx/zfxxgk1/zfxxgkzn/" target="_blank">辽 宁</a></td>
#                   <td><a href="http://xxgk.jl.gov.cn/" target="_blank">吉 林</a></td>
#                   <td><a href="https://www.hlj.gov.cn/hlj/c108369/zfxxgk.shtml" target="_blank">黑龙江</a></td>
#                   <td><a href="http://www.shanghai.gov.cn/nw49255/index.html" target="_blank">上 海</a></td>
#                   <td><a href="http://www.jiangsu.gov.cn/col/col76552/index.html" target="_blank">江 苏</a></td>
#                 </tr>
# ```

# %% [markdown]
# ## Parse Static Link Tables
#
# Parse the provincial platform link table first.

# %%
html_path = output_path / "gov_cn_zhengce_xxgk.html"
soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")


def clean_text(value: str) -> str:
	return " ".join(value.split())


def clean_html_text(value: str) -> str:
	return clean_text(BeautifulSoup(value or "", "html.parser").get_text("", strip=True))


platform_rows = []
for section in soup.select("div.zfxxgknb.conr_part > div.part_box"):
	section_title_tag = section.select_one("p.pb_title")
	section_title = clean_text(section_title_tag.get_text(" ", strip=True)) if section_title_tag else ""
	if section_title != "省（区、市）政府信息公开平台":
		continue
	for row_index, row in enumerate(section.select("table tr"), start=1):
		for cell_index, cell in enumerate(row.select("td"), start=1):
			anchor = cell.select_one("a")
			platform_rows.append(
				{
					"section": section_title,
					"row_index": row_index,
					"cell_index": cell_index,
					"label": clean_text(anchor.get_text(" ", strip=True)) if anchor else clean_text(cell.get_text(" ", strip=True)),
					"url": anchor.get("href") if anchor and anchor.has_attr("href") else None,
					"target": anchor.get("target") if anchor and anchor.has_attr("target") else None,
				},
			)


platform_links_df = pd.DataFrame(platform_rows)
platform_section_summary = (
	platform_links_df.groupby("section", dropna=False)
	.size()
	.reset_index(name="link_count")
	.sort_values(["link_count", "section"], ascending=[False, True])
)

platform_missing_href_df = platform_links_df[platform_links_df["url"].isna()]

platform_section_summary

# %% [markdown]
# ### Show Each Link
#
# Display the extracted link text and URL for each static section.

# %%
link_display_columns = ["row_index", "cell_index", "label", "url", "target"]
link_display_df = platform_links_df.sort_values(
	["section", "row_index", "cell_index"],
	ascending=[True, True, True],
).reset_index(drop=True)

for section_name, section_df in link_display_df.groupby("section", sort=False):
	print(section_name)
	display(section_df[link_display_columns].reset_index(drop=True))


# %% [markdown]
# ## Policies list
#
# **Findings**:
#
# Origin HTML start at line:198:
# ```html
#         <!-- 政府信息公开指南 -->
#         <div class="xxgkzn conr_part current_conr_part" id="xxgkzn" style="display: block;">
# ```
#
# - Search results are not present in the static HTML: the page relies on client-side JavaScript (entry function `changeFilter`) to fetch and insert policy list items via XHR. The HTML saved from a single request does not contain policy entries, so static probing returns empty results.
# - The `changeFilter` function is present in the page scripts and the UI sets parameters such as `position`, `isPreciseSearch`, and `sort`. The actual AJAX endpoint and the full request format have not yet been reverse-engineered.
# - Common reasons a direct API request fails include: required headers (Referer/Cookie/User-Agent), dynamic tokens or parameters generated at runtime, and origin/rate restrictions on the endpoint.

# %% [markdown]
# ## Reverse Engineer the Policy List AJAX Interface
#
# The page script exposes enough constants to reproduce the list-query path without a browser:
#
# - `DOMAIN_ADDRESS`: `//sousuoht.www.gov.cn`
# - `siteId`: `8`
# - `viewId`: `30`
# - `thirdPartyCode`: `thirdparty_code_107`
# - code endpoint: `/athena/forward/DA2FE8C6CAD0EEBC5F97F7E3F3633A7188DAA40373EEA0E4024A081201F4D546`
# - list endpoint: `/athena/forward/486B5ABFBAD0FF5743F5E82E007EF04DDD6388E7989E9EC9CC7B84917AC81A5F`
#
# The request headers include an encrypted `athenaAppKey`. The helper below implements the minimum RSA
# PKCS#1 v1.5 public-key encryption needed to mimic the page's `JSEncrypt` call, without adding a notebook-only
# dependency.
#
# Query knobs exposed by the browser UI:
#
# - `SRDI_KEYWORDS`: search words. Use `[""]` for a no-keyword first-page policy list probe.
# - Title search: `searchFields=[{"fieldName": "maintitle", "searchWord": keyword}]`.
# - Full-text search: `searchFields=[{"fieldName": "", "searchWord": keyword}]`.
# - Fuzzy search: `isPreciseSearch=0`.
# - Precise search: `isPreciseSearch=1`.
# - Publication-date sort: `sorts=[{"sortField": "publish_time", "sortOrder": "DESC"}]`.
# - Relevance sort: `sorts=[{"sortField": "", "sortOrder": "DESC"}]`.

# %%
DOMAIN_ADDRESS = "https://sousuoht.www.gov.cn"
SITE_ID = 8
VIEW_ID = 30
THIRD_PARTY_CODE = "thirdparty_code_107"
ATHENA_APP_KEY = "a46884b2013e4d189f2a8e2d49a23525"
ATHENA_APP_NAME = "国网搜索"
PUBLIC_KEY = (
	"MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCSMhMJQ+XLI7oW0k9Bwufur4Ag40tcsrzT7WZf6Ao0O/hyY1gZtCSYFxkx"
	"IZUXjW46j27XSW8IDX1rTJoHaMxHCWsOpTi2W5stybGYZytsY5on8gd8AIaS1d52h9eaS2TFydtJJtE50xHmT0WmoyoinWCuV"
	"COkdCLhh9b9jSdeSQIDAQAB"
)
CODE_ENDPOINT = "/athena/forward/DA2FE8C6CAD0EEBC5F97F7E3F3633A7188DAA40373EEA0E4024A081201F4D546"
LIST_ENDPOINT = "/athena/forward/486B5ABFBAD0FF5743F5E82E007EF04DDD6388E7989E9EC9CC7B84917AC81A5F"
# Default search words for the SRDI policy-text probe. Keep this small until list/detail quality is stable.
SRDI_KEYWORDS = ["专精特新", "小巨人", "中小企业"]


def _read_der_length(data: bytes, offset: int) -> tuple[int, int]:
	first = data[offset]
	offset += 1
	if first < 0x80:
		return first, offset
	length_size = first & 0x7F
	length = int.from_bytes(data[offset : offset + length_size], "big")
	return length, offset + length_size


def _read_der_tlv(data: bytes, offset: int) -> tuple[int, bytes, int]:
	tag = data[offset]
	length, value_start = _read_der_length(data, offset + 1)
	value_end = value_start + length
	return tag, data[value_start:value_end], value_end


def parse_spki_rsa_public_key(public_key_base64: str) -> tuple[int, int]:
	"""Extract the RSA modulus and exponent from a SubjectPublicKeyInfo DER blob."""
	der = base64.b64decode(public_key_base64)
	tag, spki, _ = _read_der_tlv(der, 0)
	if tag != 0x30:
		raise ValueError("Expected SubjectPublicKeyInfo sequence.")

	offset = 0
	_, _, offset = _read_der_tlv(spki, offset)  # algorithm identifier
	bit_string_tag, bit_string, offset = _read_der_tlv(spki, offset)
	if bit_string_tag != 0x03 or not bit_string:
		raise ValueError("Expected RSA public key bit string.")

	rsa_key_der = bit_string[1:]  # first byte is the unused-bit count
	rsa_tag, rsa_sequence, _ = _read_der_tlv(rsa_key_der, 0)
	if rsa_tag != 0x30:
		raise ValueError("Expected RSA public key sequence.")

	offset = 0
	modulus_tag, modulus_bytes, offset = _read_der_tlv(rsa_sequence, offset)
	exponent_tag, exponent_bytes, offset = _read_der_tlv(rsa_sequence, offset)
	if modulus_tag != 0x02 or exponent_tag != 0x02:
		raise ValueError("Expected RSA integer fields.")
	return int.from_bytes(modulus_bytes, "big"), int.from_bytes(exponent_bytes, "big")


def rsa_encrypt_pkcs1_v15(message: str, public_key_base64: str) -> str:
	"""Match the browser-side JSEncrypt output shape closely enough for the gateway header."""
	modulus, exponent = parse_spki_rsa_public_key(public_key_base64)
	key_size = (modulus.bit_length() + 7) // 8
	message_bytes = message.encode("utf-8")
	padding_size = key_size - len(message_bytes) - 3
	if padding_size < 8:
		raise ValueError("Message is too long for this RSA key.")

	padding = bytearray()
	while len(padding) < padding_size:
		candidate = secrets.token_bytes(padding_size - len(padding))
		padding.extend(byte for byte in candidate if byte != 0)
	encoded = b"\x00\x02" + bytes(padding[:padding_size]) + b"\x00" + message_bytes
	encrypted_int = pow(int.from_bytes(encoded, "big"), exponent, modulus)
	return base64.b64encode(encrypted_int.to_bytes(key_size, "big")).decode("ascii")


def ajax_headers() -> dict[str, str]:
	"""Build browser-like headers for the XXGK gateway request.

	This mimics the public page's JavaScript call. It is not a private login token, but it is still a gateway
	interface rather than a plain static HTML URL, so keep usage bounded, low-frequency, and documented.
	"""
	return {
		"User-Agent": "Mozilla/5.0",
		"Referer": "https://www.gov.cn/zhengce/xxgk/",
		"Content-Type": "application/json;charset=utf-8",
		"athenaAppKey": quote(rsa_encrypt_pkcs1_v15(ATHENA_APP_KEY, PUBLIC_KEY), safe=""),
		"athenaAppName": quote(ATHENA_APP_NAME, safe=""),
	}


def request_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
	"""Request JSON from the gateway.

	`payload=None` sends a GET request for the temporary code. Passing a dictionary sends a POST request for list data.
	Some responses are JSON strings nested inside JSON, so this helper decodes that shape as well.
	"""
	data = None
	method = "GET"
	headers = ajax_headers()
	if payload is not None:
		data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		method = "POST"
	request = Request(url, data=data, headers=headers, method=method)
	with urlopen(request, timeout=timeout) as response:
		text = response.read().decode("utf-8", errors="replace")
	parsed = json.loads(text)
	return json.loads(parsed) if isinstance(parsed, str) else parsed


def save_json_artifact(name: str, payload: dict) -> Path:
	path = raw_json_path / name
	path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
	return path


def extract_candidate_records(response_payload: dict, keyword: str, artifact_path: Path) -> list[dict]:
	"""Normalize list records from either a live response or an archived raw JSON artifact.

	The resulting rows feed `central_gov_xxgk_sirdi_candidates.csv`. Keeping this separate from the live request
	allows later no-network runs to rebuild candidates from saved JSON without clearing successful data.
	"""
	result_data = response_payload.get("result", {}).get("data", {})
	records = []
	for item in result_data.get("list", []) or []:
		records.append(
			{
				"title": clean_html_text(item.get("maintitle", "")),
				"fwzh": clean_text(item.get("fwzh", "")),
				"cwrq": item.get("cwrq"),
				"publish_time": item.get("publish_time"),
				"source_url": urljoin(source_url + "/", item.get("pub_url", "")),
				"keyword": keyword,
				"category_id": 1100,
				"page_no": result_data.get("pager", {}).get("pageNo", 1),
				"parse_status": "success",
				"raw_json_path": str(artifact_path.relative_to(workspace_root)),
			},
		)
	return records


def get_category_ids(category: dict) -> list[int]:
	ids = []
	for child in category.get("children", []):
		ids.append(child["id"])
		ids.extend(get_category_ids(child))
	return ids


root_policy_category = {"id": 1100, "children": [{"id": item["id"], "children": []} for item in []]}
ajax_probe_constants = {
	"domain": DOMAIN_ADDRESS,
	"site_id": SITE_ID,
	"view_id": VIEW_ID,
	"third_party_code": THIRD_PARTY_CODE,
	"keywords": SRDI_KEYWORDS,
	"list_page_size": 10,
}

ajax_probe_constants

# %% [markdown]
# ### Probe the Gateway Code and List Query
#
# This cell is intentionally bounded: one code request plus one first-page list request for each SRDI keyword.
# Raw JSON responses are archived for auditability. If the gateway refuses the request, the failure is captured in
# `list_probe_summary_df` and the decision log below instead of being hidden.
#
# Output artifacts from this cell:
#
# - `data/raw/json/central_gov_xxgk_code_probe.json`: raw response for the temporary gateway code request.
# - `data/raw/json/central_gov_xxgk_list_*.json`: raw first-page list response for each keyword.
# - `data/interim/central_gov_xxgk_sirdi_candidates.csv`: normalized candidate policy rows.

# %%
code_code = None
code_probe_error = None
code_probe_response = {}

try:
	code_url = f"{DOMAIN_ADDRESS}{CODE_ENDPOINT}?thirdPartyName=hycloud&thirdPartyTenantId={SITE_ID}"
	code_probe_response = request_json(code_url)
	save_json_artifact("central_gov_xxgk_code_probe.json", code_probe_response)
	if code_probe_response.get("resultCode", {}).get("code") == 200:
		code_code = code_probe_response.get("result", {}).get("data")
except Exception as exc:
	code_probe_error = repr(exc)
	save_json_artifact("central_gov_xxgk_code_probe_error.json", {"error": code_probe_error})

list_probe_records = []
list_probe_errors = []
used_archived_list_records = False

for keyword in SRDI_KEYWORDS:
	if not code_code:
		list_probe_errors.append({"keyword": keyword, "error": code_probe_error or "codeCode was not returned"})
		continue

	payload = {
		"code": code_code,
		"thirdPartyCode": THIRD_PARTY_CODE,
		"thirdPartyTableId": VIEW_ID,
		"resultFields": ["pub_url", "maintitle", "fwzh", "cwrq", "publish_time"],
		"trackTotalHits": "true",
		# Browser UI mapping: title search uses `maintitle`; full-text search uses an empty field name.
		"searchFields": [{"fieldName": "maintitle", "searchWord": keyword}],
		# Browser UI mapping: 0 = fuzzy search; 1 = precise search.
		"isPreciseSearch": 0,
		# Browser UI mapping: `publish_time` = date sort; empty sortField = relevance sort.
		"sorts": [{"sortField": "publish_time", "sortOrder": "DESC"}],
		"childrenInfoIds": [],
		"pageSize": 10,
		"pageNo": 1,
	}
	try:
		response_payload = request_json(f"{DOMAIN_ADDRESS}{LIST_ENDPOINT}", payload=payload)
		artifact_path = save_json_artifact(f"central_gov_xxgk_list_{keyword}.json", response_payload)
		list_probe_records.extend(extract_candidate_records(response_payload, keyword, artifact_path))
		time.sleep(1)
	except Exception as exc:
		error = repr(exc)
		list_probe_errors.append({"keyword": keyword, "error": error})
		save_json_artifact(f"central_gov_xxgk_list_{keyword}_error.json", {"payload": payload, "error": error})

# If live probing fails in a later notebook run, recover from archived successful JSON instead of overwriting
# the candidate table with an empty frame. This keeps the audit trail and derived tables internally consistent.
if not list_probe_records:
	for keyword in SRDI_KEYWORDS:
		artifact_path = raw_json_path / f"central_gov_xxgk_list_{keyword}.json"
		if not artifact_path.exists():
			continue
		try:
			response_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
			archived_records = extract_candidate_records(response_payload, keyword, artifact_path)
			list_probe_records.extend(archived_records)
			used_archived_list_records = used_archived_list_records or bool(archived_records)
		except Exception as exc:
			list_probe_errors.append({"keyword": keyword, "error": f"archived JSON parse failed: {exc!r}"})

candidate_columns = ["title", "fwzh", "cwrq", "publish_time", "source_url", "keyword", "category_id", "page_no", "parse_status", "raw_json_path"]
candidates_df = pd.DataFrame(list_probe_records, columns=candidate_columns)
candidate_output_path = interim_path / "central_gov_xxgk_sirdi_candidates.csv"
candidates_df.to_csv(candidate_output_path, index=False)

list_probe_summary_df = pd.DataFrame(
	[
		{
			"code_returned": bool(code_code),
			"used_archived_list_records": used_archived_list_records,
			"candidate_records": len(candidates_df),
			"keywords_with_errors": len(list_probe_errors),
			"candidate_csv": str(candidate_output_path.relative_to(workspace_root)),
			"code_probe_error": code_probe_error,
		},
	],
)

display(list_probe_summary_df)
display(candidates_df.head(10))
if list_probe_errors:
	display(pd.DataFrame(list_probe_errors))

# %% [markdown]
# ## Detail Page Probe
#
# For each keyword, inspect at most three candidate detail pages. The goal is not full crawling; it is to decide
# whether title, date, agency, body text, and attachments can be parsed from representative pages.
#
# Output artifacts from this section:
#
# - `data/raw/html/central_gov_xxgk_detail_*.html`: archived public detail page HTML.
# - `data/interim/central_gov_xxgk_sirdi_detail_probe.csv`: normalized detail-page parse sample.

# %%
DETAIL_SELECTORS = [
	".pages_content",
	".article",
	".content",
	".TRS_Editor",
	"#UCAP-CONTENT",
	"article",
]
ATTACHMENT_RE = re.compile(r"\.(pdf|doc|docx|xls|xlsx|wps|zip)(?:$|[?#])", flags=re.IGNORECASE)
DATE_RE = re.compile(r"(?:发布时间|发布日期|成文日期)[:：\s]*([0-9]{4}[-年][0-9]{1,2}[-月][0-9]{1,2})")


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


def extract_detail_record(candidate: dict) -> dict:
	"""Fetch or reload one public detail page and normalize it to the shared policy-text shape.

	The first attempt fetches the public detail URL. If that fails, the function reuses archived HTML with the same
	URL-derived filename. This protects previous successful probes when the notebook is rerun in a no-network sandbox.
	"""
	url = candidate["source_url"]
	keyword = candidate["keyword"]
	candidate_title = candidate.get("title") or ""
	candidate_publish_date = str(candidate.get("publish_time") or candidate.get("cwrq") or "").split(" ")[0] or None
	candidate_fwzh = candidate.get("fwzh")
	record = {
		"province": "central",
		"source_site": "gov.cn/zhengce/xxgk",
		"policy_title": candidate_title or None,
		"title": candidate_title or None,
		"publish_date": candidate_publish_date,
		"agency": infer_agency_from_candidate(candidate_title, candidate_fwzh),
		"source_url": url,
		"keyword_hit": keyword,
		"document_type": None,
		"text_raw": "",
		"attachment_urls": [],
		"parse_status": "detail_failed",
		"review_status": "needs_review",
		"error": None,
		"raw_html_path": None,
	}
	try:
		try:
			request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": source_url})
			with urlopen(request, timeout=30) as response:
				final_url = response.geturl()
				charset = response.headers.get_content_charset() or "utf-8"
				html = response.read().decode(charset, errors="replace")

			safe_name = re.sub(r"[^A-Za-z0-9]+", "_", final_url).strip("_")[:120] or "detail"
			raw_detail_path = raw_html_path / f"central_gov_xxgk_detail_{safe_name}.html"
			raw_detail_path.write_text(html, encoding="utf-8")
		except Exception as fetch_exc:
			# Reuse archived detail HTML when a later notebook run has no network permission.
			candidate_urls = [url]
			if url.startswith("http://"):
				candidate_urls.append("https://" + url.removeprefix("http://"))
			cached_paths = []
			for candidate_url in candidate_urls:
				safe_name = re.sub(r"[^A-Za-z0-9]+", "_", candidate_url).strip("_")[:120] or "detail"
				cached_paths.append(raw_html_path / f"central_gov_xxgk_detail_{safe_name}.html")
			raw_detail_path = next((path for path in cached_paths if path.exists()), None)
			if raw_detail_path is None:
				raise fetch_exc
			final_url = url
			html = raw_detail_path.read_text(encoding="utf-8")

		detail_soup = BeautifulSoup(html, "html.parser")

		title = ""
		if detail_soup.select_one("h1"):
			title = normalize_policy_title(detail_soup.select_one("h1").get_text(" ", strip=True))
		if not title and detail_soup.title:
			title = normalize_policy_title(detail_soup.title.get_text(" ", strip=True))
		if not title:
			title = candidate_title

		agency = ""
		for label in ["source", "ContentSource"]:
			meta = detail_soup.find("meta", attrs={"name": label})
			if meta and meta.get("content"):
				agency = clean_text(meta["content"])
				break

		body_text = ""
		for selector in DETAIL_SELECTORS:
			body = detail_soup.select_one(selector)
			if body:
				body_text = clean_text(body.get_text(" ", strip=True))
				if len(body_text) >= 80:
					break
		if not body_text:
			body_text = clean_text(detail_soup.get_text(" ", strip=True))

		date_match = DATE_RE.search(body_text)
		attachment_urls = []
		for anchor in detail_soup.select("a[href]"):
			href = anchor.get("href", "")
			anchor_text = clean_text(anchor.get_text(" ", strip=True))
			if ATTACHMENT_RE.search(href) or "附件" in anchor_text:
				attachment_urls.append(urljoin(final_url, href))

		record.update(
			{
				"policy_title": title,
				"title": title,
				"publish_date": date_match.group(1).replace("年", "-").replace("月", "-").replace("日", "") if date_match else candidate_publish_date,
				"agency": infer_agency_from_candidate(title, candidate_fwzh) or agency or infer_agency_from_candidate(candidate_title, candidate_fwzh),
				"source_url": final_url,
				"document_type": infer_document_type(title, attachment_urls),
				"text_raw": body_text,
				"attachment_urls": attachment_urls,
				"parse_status": "success" if len(body_text) >= 80 else "partial",
				"review_status": "needs_review" if len(body_text) < 200 else "accepted",
				"raw_html_path": str(raw_detail_path.relative_to(workspace_root)),
			},
		)
	except Exception as exc:
		record["error"] = repr(exc)
	return record


detail_candidates_df = (
	candidates_df.drop_duplicates(["keyword", "source_url"])
	.groupby("keyword", group_keys=False)
	.head(3)
	if not candidates_df.empty
	else pd.DataFrame(columns=candidate_columns)
)

detail_records = []
for row in detail_candidates_df.to_dict("records"):
	detail_records.append(extract_detail_record(row))
	time.sleep(0.5)

detail_columns = [
	"province",
	"source_site",
	"policy_title",
	"title",
	"publish_date",
	"agency",
	"source_url",
	"keyword_hit",
	"document_type",
	"text_raw",
	"attachment_urls",
	"parse_status",
	"review_status",
	"error",
	"raw_html_path",
]
details_df = pd.DataFrame(detail_records, columns=detail_columns)
details_output_path = interim_path / "central_gov_xxgk_sirdi_detail_probe.csv"
details_df.to_csv(details_output_path, index=False)

display(details_df[["keyword_hit", "title", "publish_date", "agency", "document_type", "parse_status", "source_url", "error"]])

# %% [markdown]
# ## Quality Checks and Decision Log
#
# These checks are deliberately compact. They are meant to answer whether this source is ready for a formal crawler
# implementation, not to certify the full population of central-government policy documents.
#
# Maintenance notes:
#
# - If both live requests and archived artifacts are unavailable, stop and inspect the failure instead of treating an
#   empty CSV as a valid collection result.
# - Before increasing `pageSize` or adding more pages, inspect `pager.total`, `pager.pageCount`, duplicate URLs, and
#   detail parse quality.
# - For `专精特新` and `小巨人`, try full-text search (`fieldName=""`) before increasing title-search pages.
# - This method uses the page's internal AJAX gateway. Keep rate limits conservative and preserve raw artifacts so the
#   collection remains auditable.

# %%
quality_summary = {
	"total_candidate_records": len(candidates_df),
	"detail_pages_sampled": len(details_df),
	"successfully_parsed_details": int((details_df["parse_status"] == "success").sum()) if not details_df.empty else 0,
	"partial_or_failed_details": int(details_df["parse_status"].isin(["partial", "detail_failed"]).sum()) if not details_df.empty else 0,
	"empty_body_text": int((details_df["text_raw"].fillna("").str.len() == 0).sum()) if not details_df.empty else 0,
	"short_body_text_lt_200": int((details_df["text_raw"].fillna("").str.len() < 200).sum()) if not details_df.empty else 0,
	"missing_publication_dates": int(details_df["publish_date"].isna().sum()) if not details_df.empty else 0,
	"duplicate_source_urls": int(candidates_df.duplicated("source_url").sum()) if not candidates_df.empty else 0,
	"duplicate_title_date_pairs": int(candidates_df.duplicated(["title", "publish_time"]).sum()) if not candidates_df.empty else 0,
	"attachment_pages": int(details_df["attachment_urls"].apply(lambda value: len(value) > 0 if isinstance(value, list) else False).sum()) if not details_df.empty else 0,
	"attachment_failures": 0,
	"needs_review_records": int((details_df["review_status"] == "needs_review").sum()) if not details_df.empty else 0,
}
quality_summary_df = pd.DataFrame([quality_summary])
display(quality_summary_df)

ajax_ready = len(candidates_df) > 0
detail_ready = not details_df.empty and details_df["parse_status"].isin(["success", "partial"]).any()
decision_log_df = pd.DataFrame(
	[
		{
			"source": "gov.cn/zhengce/xxgk policy list AJAX",
			"chosen_method": "gateway_ajax_then_detail_html" if ajax_ready else "continue_notebook_probe_or_manual_url_seed",
			"evidence": (
				f"code_returned={bool(code_code)}; used_archived_list_records={used_archived_list_records}; candidates={len(candidates_df)}; "
				f"detail_pages_sampled={len(details_df)}; detail_ready={detail_ready}"
			),
			"unresolved_risk": (
				"Gateway headers may change because athenaAppKey is generated client-side; detail selectors need more samples."
				if ajax_ready
				else f"AJAX probe failed or returned no candidates: {code_probe_error or list_probe_errors}"
			),
			"user_decision_needed": (
				"Confirm whether central-government results alone are in scope for the policy-intensity corpus."
				if ajax_ready
				else "Decide whether to continue reverse engineering or use manually curated search-result URLs."
			),
			"ready_for_implementation": bool(ajax_ready and detail_ready),
		},
	],
)
display(decision_log_df)

# %%
