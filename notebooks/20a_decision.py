# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
# ---

# %%

# %% [markdown]
# # Final Decision
#
# This notebook records the final crawling scheme of gov.cn/xxgk
#
# ```text
# Define data requirements
#   |
# Design the output schema
#   |
# Map data sources
#   |
# Condense exploratory steps into a crawling report
#   |   (skip separate Inspect website structure / Choose strategy / Feasibility script sections)
#   |
# Construct the URL queue
#   |
# Fetch detail pages and attachments
#   |
# Parse structured fields
#   |
# Clean policy text
#   |
# Deduplicate and run quality checks
#   |
# Store raw and structured data
#   |
# Use the corpus for text classification and statistical modeling
# ```

# %%
from __future__ import annotations

import pandas as pd

# %% [markdown]
# ## 1. Define Data Requirements
#
# This step fixes the research contract before implementation. The crawler should serve the SRDI/Little-Giant
# policy-text corpus, not just collect whatever the website can return.
#
# Current decision boundary:
#
# - Decide the data requirement and minimum schema for the central `gov.cn/zhengce/xxgk` crawler.
# - Do not decide pagination range, final crawling strategy, production code structure, or province-level expansion yet.
# - Do not fetch network data in this notebook step.

# %%
research_requirements = pd.DataFrame(
	[
		{
			"item": "jurisdiction",
			"decision": "central",
			"reason": "This notebook decides the central gov.cn/xxgk source first; province-level sources are a later workflow.",
		},
		{
			"item": "source_site",
			"decision": "gov.cn/zhengce/xxgk",
			"reason": "The source is the central government policy information disclosure page explored in notebook 20.",
		},
		{
			"item": "purpose",
			"decision": "Build a policy-text corpus for SRDI/Little-Giant policy intensity and text classification.",
			"reason": "Downstream work needs auditable policy text, metadata, and keyword/context signals.",
		},
		{
			"item": "primary_unit",
			"decision": "One policy document detail page.",
			"reason": "Detail pages carry the title, date, source URL, body text, and possible attachments needed for analysis.",
		},
		{
			"item": "secondary_artifacts",
			"decision": "List JSON, detail HTML, and attachments when present.",
			"reason": "Raw artifacts preserve auditability and allow parser improvements without repeated live requests.",
		},
	],
)
research_requirements

# %%
keyword_requirements = pd.DataFrame(
	[
		{
			"keyword": "专精特新",
			"use": "Core SRDI policy keyword",
			"default_collection": True,
			"note": "Title search may miss records; full-text probing is expected in a later step.",
		},
		{
			"keyword": "小巨人",
			"use": "Core Little-Giant recognition keyword",
			"default_collection": True,
			"note": "Title search may miss records; full-text probing is expected in a later step.",
		},
		{
			"keyword": "中小企业",
			"use": "Broader SME support-policy keyword",
			"default_collection": True,
			"note": "Useful for central support policies that materially affect SRDI firms.",
		},
		{
			"keyword": "",
			"use": "General policy list probe",
			"default_collection": False,
			"note": "Allowed for small feasibility checks only; not the default full collection route.",
		},
	],
)
keyword_requirements

# %%
candidate_document_types = pd.DataFrame(
	[
		{
			"document_type": "policy_document",
			"include_by_default": True,
			"examples": "通知, 意见, 办法, 规划, 方案, 公告",
			"review_note": "Primary unit for text mining and policy-intensity measurement.",
		},
		{
			"document_type": "attachment_page",
			"include_by_default": True,
			"examples": "Detail page whose main policy body is in PDF/Word attachments",
			"review_note": "Keep raw attachment URLs and mark attachment extraction status.",
		},
		{
			"document_type": "interpretation_or_news",
			"include_by_default": False,
			"examples": "政策解读, 新闻稿, 图片新闻",
			"review_note": "Mark as needs_review unless the research口径 explicitly includes it.",
		},
		{
			"document_type": "notice_or_publicity_list",
			"include_by_default": False,
			"examples": "申报通知, 公示名单, 批次公告",
			"review_note": "Potentially important for Little-Giant recognition, but needs a separate inclusion rule.",
		},
	],
)
candidate_document_types

# %% [markdown]
# ## 2. Design the Output Schema
#
# The schema below is the crawler contract for later implementation. It keeps raw and clean text separate, records
# source artifacts, and uses explicit status fields so failures are auditable instead of silently dropped.

# %%
output_schema = pd.DataFrame(
	[
		{"field": "policy_id", "required": True, "description": "Stable ID derived later from source URL or content hash."},
		{"field": "province", "required": True, "description": "Jurisdiction label; `central` for gov.cn/xxgk."},
		{"field": "title", "required": True, "description": "Policy title from list JSON or detail HTML."},
		{"field": "publish_date", "required": True, "description": "Publication date normalized to date-like text."},
		{"field": "agency", "required": False, "description": "Issuing agency when parseable or inferable."},
		{"field": "source_site", "required": True, "description": "Source site label, e.g. `gov.cn/zhengce/xxgk`."},
		{"field": "source_url", "required": True, "description": "Canonical public detail-page URL."},
		{"field": "keyword_hit", "required": False, "description": "Keyword or query that produced the candidate record."},
		{"field": "document_type", "required": True, "description": "Policy/document category used for inclusion review."},
		{"field": "text_raw", "required": True, "description": "Raw extracted body text before cleaning."},
		{"field": "text_clean", "required": False, "description": "Conservatively cleaned text for text mining."},
		{"field": "attachment_urls", "required": False, "description": "List of PDF/Word/other attachment URLs."},
		{"field": "raw_json_path", "required": False, "description": "Archived list JSON path when the record came from a list response."},
		{"field": "raw_html_path", "required": False, "description": "Archived detail HTML path."},
		{"field": "parse_status", "required": True, "description": "Parser status; see status values below."},
		{"field": "review_status", "required": True, "description": "Human/research review status; see status values below."},
		{"field": "error", "required": False, "description": "Error or review note when parsing is partial or failed."},
		{"field": "crawl_time", "required": True, "description": "Collection timestamp for reproducibility."},
		{"field": "text_hash", "required": False, "description": "Hash for exact duplicate detection after text extraction."},
	],
)
output_schema

# %%
status_values = pd.DataFrame(
	[
		{"status_field": "parse_status", "value": "success", "meaning": "List/detail/attachment parsing succeeded for required fields."},
		{"status_field": "parse_status", "value": "partial", "meaning": "Some useful fields parsed, but one or more important fields are missing."},
		{"status_field": "parse_status", "value": "list_failed", "meaning": "List JSON request or list parsing failed."},
		{"status_field": "parse_status", "value": "detail_failed", "meaning": "Detail HTML request or detail parsing failed."},
		{"status_field": "parse_status", "value": "attachment_failed", "meaning": "Attachment download or extraction failed."},
		{"status_field": "parse_status", "value": "skipped_access_restricted", "meaning": "Source required access that should not be bypassed."},
		{"status_field": "parse_status", "value": "skipped_out_of_scope", "meaning": "Record was found but excluded by research scope."},
		{"status_field": "review_status", "value": "accepted", "meaning": "Record fits the research口径."},
		{"status_field": "review_status", "value": "needs_review", "meaning": "Record is ambiguous and needs human/research judgment."},
		{"status_field": "review_status", "value": "rejected", "meaning": "Record should not enter the final corpus."},
	],
)
status_values

# %%
open_decisions = pd.DataFrame(
	[
		{
			"decision": "pagination_range",
			"status": "not_decided_in_step_1",
			"next_step": "Map sources and inspect list pagination before setting max_pages.",
		},
		{
			"decision": "final_crawling_strategy",
			"status": "not_decided_in_step_1",
			"next_step": "Compare title search, full-text search, and no-keyword probes.",
		},
		{
			"decision": "production_code_structure",
			"status": "not_decided_in_step_1",
			"next_step": "Only promote to src/scripts after crawler decisions are stable.",
		},
		{
			"decision": "province_level_expansion",
			"status": "out_of_scope_for_this_notebook_step",
			"next_step": "Open a separate province/source-map workflow after central gov.cn is decided.",
		},
	],
)
open_decisions

# %% [markdown]
# ## Next TODO
#
# Completed by section 3 below: `Map data sources`.

# %% [markdown]
# ## 3. Map Data Sources
#
# This step maps source surfaces before choosing a crawler strategy. A "source surface" is any stable place where the
# crawler can discover or retrieve policy records: a public page, a browser-facing JSON endpoint, a sitemap, a manual
# seed list, or already archived raw artifacts.
#
# This section still does not fetch network data. It only records the source map implied by notebook 20 and the current
# project artifacts.

# %%
source_map = pd.DataFrame(
	[
		{
			"source_surface": "XXGK landing page",
			"url_or_origin": "https://www.gov.cn/zhengce/xxgk",
			"role": "Entry page and source of page-script constants.",
			"method_candidate": "static_html",
			"current_evidence": "Archived as data/raw/html/gov_cn_zhengce_xxgk.html.",
			"crawler_decision_status": "usable_for_source_discovery",
			"risk_note": "Low technical risk; page itself does not contain the full searchable policy list.",
		},
		{
			"source_surface": "XXGK list JSON gateway",
			"url_or_origin": "https://sousuoht.www.gov.cn/athena/forward/486B5ABFBAD0FF5743F5E82E007EF04DDD6388E7989E9EC9CC7B84917AC81A5F",
			"role": "Search/list candidate policies by query configuration.",
			"method_candidate": "browser_facing_json",
			"current_evidence": "Archived first-page keyword JSON under data/raw/json/central_gov_xxgk_list_*.json.",
			"crawler_decision_status": "needs_configuration_probe",
			"risk_note": "Uses page-observed AJAX gateway; keep bounded, low-frequency, cached, and auditable.",
		},
		{
			"source_surface": "Public policy detail pages",
			"url_or_origin": "gov.cn/zhengce/content/... URLs from list JSON or manual seed",
			"role": "Primary unit of observation and source for title/date/body/attachments.",
			"method_candidate": "detail_html",
			"current_evidence": "Three archived detail HTML samples parsed successfully in notebook 20.",
			"crawler_decision_status": "usable_for_detail_fetch_and_parse",
			"risk_note": "Selectors need more samples before production implementation.",
		},
		{
			"source_surface": "Sitemaps",
			"url_or_origin": "https://www.gov.cn/baidu.xml and related sitemap files listed in robots.txt",
			"role": "Alternative public URL discovery path for policy detail pages.",
			"method_candidate": "sitemap_url_discovery",
			"current_evidence": "Mentioned by robots.txt; not yet probed in this decision notebook.",
			"crawler_decision_status": "candidate_alternative",
			"risk_note": "Likely lower compliance risk than AJAX search but may require broader URL filtering.",
		},
		{
			"source_surface": "Manual seed URLs",
			"url_or_origin": "Human-reviewed gov.cn policy detail URLs",
			"role": "Fallback or validation seed when search/list recall is uncertain.",
			"method_candidate": "manual_seed_then_detail_parse",
			"current_evidence": "Not yet created for XXGK; compatible with the detail parser path.",
			"crawler_decision_status": "fallback_candidate",
			"risk_note": "High transparency but lower recall unless seed construction is documented carefully.",
		},
	],
)
source_map

# %%
artifact_map = pd.DataFrame(
	[
		{
			"artifact_group": "landing_page_html",
			"path_pattern": "data/raw/html/gov_cn_zhengce_xxgk.html",
			"upstream_surface": "XXGK landing page",
			"expected_use": "Audit page structure and page-script constants.",
			"exists_in_current_project": True,
		},
		{
			"artifact_group": "list_json",
			"path_pattern": "data/raw/json/central_gov_xxgk_list_*.json",
			"upstream_surface": "XXGK list JSON gateway",
			"expected_use": "Rebuild candidate policy rows and inspect query response shape.",
			"exists_in_current_project": True,
		},
		{
			"artifact_group": "detail_html",
			"path_pattern": "data/raw/html/central_gov_xxgk_detail_*.html",
			"upstream_surface": "Public policy detail pages",
			"expected_use": "Re-run parsers without repeated live requests.",
			"exists_in_current_project": True,
		},
		{
			"artifact_group": "candidate_table",
			"path_pattern": "data/interim/central_gov_xxgk_sirdi_candidates.csv",
			"upstream_surface": "List JSON normalized by notebook 20",
			"expected_use": "Candidate queue input for detail-page sampling and later URL queue design.",
			"exists_in_current_project": True,
		},
		{
			"artifact_group": "detail_probe_table",
			"path_pattern": "data/interim/central_gov_xxgk_sirdi_detail_probe.csv",
			"upstream_surface": "Candidate table plus detail HTML",
			"expected_use": "Evidence for detail parser feasibility and schema adequacy.",
			"exists_in_current_project": True,
		},
	],
)
artifact_map

# %%
source_map_decisions = pd.DataFrame(
	[
		{
			"decision": "primary_list_discovery_surface",
			"current_choice": "XXGK list JSON gateway for pilot configuration probes",
			"why": "It directly represents the browser search UI and already produced usable candidate rows.",
			"remaining_check": "Compare title search, full-text search, and blank-keyword probes before broad use.",
		},
		{
			"decision": "primary_detail_surface",
			"current_choice": "Public gov.cn policy detail HTML pages",
			"why": "They are the intended unit of observation and can be archived and parsed.",
			"remaining_check": "Test more document templates and attachment cases.",
		},
		{
			"decision": "alternative_discovery_surface",
			"current_choice": "Sitemap or manual seed URL discovery",
			"why": "These provide lower-risk fallbacks if AJAX search recall or compliance becomes questionable.",
			"remaining_check": "Probe sitemap coverage and define manual seed documentation rules if needed.",
		},
	],
)
source_map_decisions

# %% [markdown]
# ## 4. Condensed Crawling Report
#
# This report replaces three exploratory sections that are already sufficiently informed by notebook 20:
#
# - `Inspect website structure`
# - `Choose a crawling strategy`
# - `Write a small feasibility script`
#
# The goal is not to repeat exploration. The goal is to state the crawler design clearly enough that the next step can
# construct a URL queue and then implement fetch/parse/storage modules.

# %%
skipped_exploration_steps = pd.DataFrame(
	[
		{
			"skipped_step": "Inspect website structure",
			"why_skipped": "Notebook 20 already inspected the landing page, page-script constants, list JSON shape, and detail-page samples.",
			"evidence_to_reuse": "Archived HTML/JSON artifacts plus the source map above.",
		},
		{
			"skipped_step": "Choose a crawling strategy",
			"why_skipped": "The current strategy is clear enough for a central-source pilot: configured list JSON discovery plus public detail-page parsing.",
			"evidence_to_reuse": "List JSON produced candidate rows; detail HTML samples parsed successfully.",
		},
		{
			"skipped_step": "Write a small feasibility script",
			"why_skipped": "Notebook 20 already acts as the feasibility script. Repeating it here would create duplicate crawler logic.",
			"evidence_to_reuse": "Use notebook 20 as evidence, then implement reusable crawler code later.",
		},
	],
)
skipped_exploration_steps

# %%
crawling_report = pd.DataFrame(
	[
		{
			"area": "Discovery",
			"decision": "Use the XXGK list JSON gateway for configured pilot URL discovery.",
			"implementation_note": "Queries must be config-driven: keyword, title/full-text, fuzzy/precise, sort, page_size, max_pages.",
			"risk_control": "Keep low-frequency requests, archive raw JSON, and retain sitemap/manual-seed alternatives.",
		},
		{
			"area": "Detail fetch",
			"decision": "Fetch public gov.cn policy detail pages discovered from list JSON or fallback seed URLs.",
			"implementation_note": "Archive raw detail HTML before parsing; support cached re-parse without network.",
			"risk_control": "Use bounded retries/timeouts; do not bypass access restrictions.",
		},
		{
			"area": "Parsing",
			"decision": "Parse title, publish date, agency, body text, attachment URLs, and source metadata into the schema above.",
			"implementation_note": "Treat attachment-heavy, interpretation/news, and publicity-list pages as review-sensitive types.",
			"risk_control": "Emit explicit parse_status/review_status instead of dropping failures.",
		},
		{
			"area": "Storage",
			"decision": "Store raw artifacts first, then structured interim tables, then processed corpus outputs.",
			"implementation_note": "Use raw JSON/HTML paths and stable IDs to link structured records back to artifacts.",
			"risk_control": "Never overwrite successful structured outputs with empty frames when live requests fail.",
		},
		{
			"area": "Quality",
			"decision": "Gate expansion on missing-field, duplicate, short-text, attachment, and needs-review reports.",
			"implementation_note": "Run quality checks after each pilot batch and before increasing max_pages.",
			"risk_control": "Stop expansion when parser failures or ambiguous document types are not explained.",
		},
	],
)
crawling_report

# %%
recommended_query_pilots = pd.DataFrame(
	[
		{
			"pilot": "title_sme_baseline",
			"keyword": "中小企业",
			"fieldName": "maintitle",
			"isPreciseSearch": 0,
			"sortField": "publish_time",
			"purpose": "Maintain known-good baseline from notebook 20.",
			"max_pages_initial": 1,
		},
		{
			"pilot": "fulltext_srdi",
			"keyword": "专精特新",
			"fieldName": "",
			"isPreciseSearch": 0,
			"sortField": "publish_time",
			"purpose": "Test recall for SRDI-specific policy text missed by title search.",
			"max_pages_initial": 1,
		},
		{
			"pilot": "fulltext_little_giant",
			"keyword": "小巨人",
			"fieldName": "",
			"isPreciseSearch": 0,
			"sortField": "publish_time",
			"purpose": "Test recall for Little-Giant recognition/support text missed by title search.",
			"max_pages_initial": 1,
		},
		{
			"pilot": "blank_recent_policy_probe",
			"keyword": "",
			"fieldName": "",
			"isPreciseSearch": 0,
			"sortField": "publish_time",
			"purpose": "Inspect general policy-list shape and pagination; not a default full collection.",
			"max_pages_initial": 1,
		},
	],
)
recommended_query_pilots

# %%
implementation_blocks = pd.DataFrame(
	[
		{
			"block": "Config",
			"responsibility": "Define query batches and source metadata.",
			"future_location": "configs/",
		},
		{
			"block": "Fetcher",
			"responsibility": "Request list JSON, detail HTML, and attachments with bounded retries and cache checks.",
			"future_location": "src/statistic_modeling/ or scripts/",
		},
		{
			"block": "Parser",
			"responsibility": "Normalize list rows and extract detail fields from HTML/attachments.",
			"future_location": "src/statistic_modeling/",
		},
		{
			"block": "Storage",
			"responsibility": "Archive raw artifacts and write structured interim/processed outputs.",
			"future_location": "src/statistic_modeling/",
		},
		{
			"block": "Validator",
			"responsibility": "Report missing dates, empty/short text, duplicate URLs/title-date pairs, attachment failures, and needs-review records.",
			"future_location": "src/statistic_modeling/ or notebooks/",
		},
	],
)
implementation_blocks

# %%
go_no_go = pd.DataFrame(
	[
		{
			"criterion": "Data requirement defined",
			"status": "ready",
			"note": "Central gov.cn/xxgk, SRDI/Little-Giant policy text corpus, detail page as primary unit.",
		},
		{
			"criterion": "Output schema defined",
			"status": "ready",
			"note": "Minimum fields and status values are defined above.",
		},
		{
			"criterion": "Source map defined",
			"status": "ready",
			"note": "Primary and fallback source surfaces are listed.",
		},
		{
			"criterion": "Query pilot plan",
			"status": "ready_for_next_step",
			"note": "Recommended pilots are specified; they should be converted into URL queue construction inputs.",
		},
		{
			"criterion": "Formal crawler implementation",
			"status": "not_ready_yet",
			"note": "Implement after URL queue design and quality gates are accepted.",
		},
	],
)
go_no_go

# %% [markdown]
# ## Next TODO
#
# Next step: `Construct the URL queue`.
#
# The next increment should turn `recommended_query_pilots` into a concrete queue contract: query-batch IDs, page
# ranges, raw JSON filenames, candidate URL IDs, deduplication keys, and stop conditions. It should still avoid broad
# crawling until the queue contract is reviewed.

# %% [markdown]
# ## 5. Construct the URL Queue
#
# The crawler should not directly loop over ad hoc keywords and pages. It should first build explicit queue tables.
# This makes every planned request reviewable before it is sent and gives downstream records stable IDs.
#
# This section defines the queue contract only. It does not call the network and does not write queue files.

# %%
query_batch_contract = pd.DataFrame(
	[
		{
			"field": "query_batch_id",
			"required": True,
			"description": "Stable ID for one list-query configuration, e.g. `govcn_xxgk_fulltext_srdi_time_p01`.",
		},
		{
			"field": "source_site",
			"required": True,
			"description": "Source label, fixed to `gov.cn/zhengce/xxgk` for this central-source queue.",
		},
		{
			"field": "keyword",
			"required": True,
			"description": "Search word. Empty string is allowed only for a bounded general-list probe.",
		},
		{
			"field": "search_position",
			"required": True,
			"description": "`title` maps to `fieldName=maintitle`; `fulltext` maps to `fieldName=`.",
		},
		{
			"field": "match_mode",
			"required": True,
			"description": "`fuzzy` maps to `isPreciseSearch=0`; `precise` maps to `isPreciseSearch=1`.",
		},
		{
			"field": "sort_by",
			"required": True,
			"description": "`time` maps to `sortField=publish_time`; `relevance` maps to an empty sort field.",
		},
		{
			"field": "page_size",
			"required": True,
			"description": "Number of list rows per request. Start with 10 for pilot review.",
		},
		{
			"field": "max_pages",
			"required": True,
			"description": "Maximum list pages to request for this batch. Start with 1 until quality checks pass.",
		},
		{
			"field": "purpose",
			"required": True,
			"description": "Research reason for this query batch.",
		},
		{
			"field": "enabled",
			"required": True,
			"description": "Boolean switch so risky or unresolved batches can remain documented but inactive.",
		},
	],
)
query_batch_contract

# %%
query_batches = pd.DataFrame(
	[
		{
			"query_batch_id": "govcn_xxgk_title_sme_time_pilot",
			"source_site": "gov.cn/zhengce/xxgk",
			"keyword": "中小企业",
			"search_position": "title",
			"match_mode": "fuzzy",
			"sort_by": "time",
			"page_size": 10,
			"max_pages": 1,
			"purpose": "Known-good baseline from notebook 20.",
			"enabled": True,
		},
		{
			"query_batch_id": "govcn_xxgk_fulltext_srdi_time_pilot",
			"source_site": "gov.cn/zhengce/xxgk",
			"keyword": "专精特新",
			"search_position": "fulltext",
			"match_mode": "fuzzy",
			"sort_by": "time",
			"page_size": 10,
			"max_pages": 1,
			"purpose": "Recover SRDI-specific records missed by title search.",
			"enabled": True,
		},
		{
			"query_batch_id": "govcn_xxgk_fulltext_little_giant_time_pilot",
			"source_site": "gov.cn/zhengce/xxgk",
			"keyword": "小巨人",
			"search_position": "fulltext",
			"match_mode": "fuzzy",
			"sort_by": "time",
			"page_size": 10,
			"max_pages": 1,
			"purpose": "Recover Little-Giant records missed by title search.",
			"enabled": True,
		},
		{
			"query_batch_id": "govcn_xxgk_blank_recent_time_probe",
			"source_site": "gov.cn/zhengce/xxgk",
			"keyword": "",
			"search_position": "fulltext",
			"match_mode": "fuzzy",
			"sort_by": "time",
			"page_size": 10,
			"max_pages": 1,
			"purpose": "Inspect general list shape and recent-policy pagination; not default corpus collection.",
			"enabled": False,
		},
	],
)
query_batches

# %%
list_page_queue_contract = pd.DataFrame(
	[
		{"field": "list_request_id", "required": True, "description": "Stable ID for one list JSON request."},
		{"field": "query_batch_id", "required": True, "description": "Foreign key to `query_batches`."},
		{"field": "page_no", "required": True, "description": "1-based list page number."},
		{"field": "request_payload", "required": True, "description": "Serializable JSON payload derived from the batch config."},
		{"field": "raw_json_path", "required": True, "description": "Planned archive path for the raw list response."},
		{"field": "request_status", "required": True, "description": "`pending`, `success`, `failed`, or `skipped`."},
		{"field": "stop_reason", "required": False, "description": "Reason not to request further pages, if known."},
	],
)
list_page_queue_contract

# %%
list_page_queue_example = pd.DataFrame(
	[
		{
			"list_request_id": f"{row.query_batch_id}_page_001",
			"query_batch_id": row.query_batch_id,
			"page_no": 1,
			"request_payload": {
				"keyword": row.keyword,
				"search_position": row.search_position,
				"match_mode": row.match_mode,
				"sort_by": row.sort_by,
				"page_size": row.page_size,
				"page_no": 1,
			},
			"raw_json_path": f"data/raw/json/{row.query_batch_id}_page_001.json",
			"request_status": "pending" if row.enabled else "skipped",
			"stop_reason": "" if row.enabled else "Batch documented but not enabled for pilot run.",
		}
		for row in query_batches.itertuples(index=False)
	],
)
list_page_queue_example

# %%
candidate_url_queue_contract = pd.DataFrame(
	[
		{"field": "candidate_id", "required": True, "description": "Stable candidate URL ID, preferably hash-based or source-url based."},
		{"field": "source_url", "required": True, "description": "Public gov.cn detail URL discovered from list JSON or manual seed."},
		{"field": "query_batch_id", "required": True, "description": "Query batch that first discovered the URL."},
		{"field": "list_request_id", "required": False, "description": "List request that first discovered the URL."},
		{"field": "title", "required": False, "description": "Candidate title from list JSON before detail parsing."},
		{"field": "publish_time", "required": False, "description": "Candidate publication timestamp from list JSON."},
		{"field": "dedupe_key", "required": True, "description": "Normalized source URL; later combine with title/date/text hash if needed."},
		{"field": "detail_status", "required": True, "description": "`pending`, `success`, `failed`, or `skipped`."},
		{"field": "raw_html_path", "required": True, "description": "Planned archive path for the public detail HTML."},
	],
)
candidate_url_queue_contract

# %%
queue_stop_conditions = pd.DataFrame(
	[
		{
			"condition": "empty_list",
			"applies_to": "list_page_queue",
			"action": "Stop that query batch after confirming the response is valid and not a request failure.",
		},
		{
			"condition": "page_no_reaches_max_pages",
			"applies_to": "list_page_queue",
			"action": "Stop even if pager reports more pages; expansion requires review.",
		},
		{
			"condition": "duplicate_url_rate_high",
			"applies_to": "candidate_url_queue",
			"action": "Pause expansion and inspect dedupe keys before requesting more detail pages.",
		},
		{
			"condition": "detail_parse_failures_unexplained",
			"applies_to": "candidate_url_queue",
			"action": "Stop detail expansion until parser selectors or document-type rules are updated.",
		},
		{
			"condition": "access_restricted_or_captcha",
			"applies_to": "any_request",
			"action": "Mark skipped_access_restricted; do not bypass the restriction.",
		},
	],
)
queue_stop_conditions

# %%
queue_acceptance_checks = pd.DataFrame(
	[
		{
			"check": "Every enabled query batch has at least one planned list request.",
			"status": "designed",
		},
		{
			"check": "Every list request has a deterministic raw_json_path.",
			"status": "designed",
		},
		{
			"check": "Candidate URLs dedupe on normalized source_url before detail fetching.",
			"status": "designed",
		},
		{
			"check": "Blank-keyword batch is documented but disabled by default.",
			"status": "designed",
		},
		{
			"check": "Expansion beyond page 1 requires review of quality and stop conditions.",
			"status": "designed",
		},
	],
)
queue_acceptance_checks

# %% [markdown]
# ## Next TODO
#
# Next step: `Fetch detail pages and attachments`.
#
# The next increment should decide the fetch contract for list JSON, detail HTML, and attachments: cache-first behavior,
# retry limits, timeout values, raw artifact paths, and status handling. It should still avoid broad collection until
# the queue contract above is accepted.

# %% [markdown]
# ## 6. Crawler Workflow and Parser Design
#
# This section combines two workflow steps:
#
# - `Fetch detail pages and attachments`
# - `Parse structured fields`
#
# The goal is to define how the future crawler should move records through fetch, archive, parse, and status handling.
# This is still a design section: no HTTP requests are sent and no parser implementation is created here.

# %%
crawler_workflow = pd.DataFrame(
	[
		{
			"stage": "1_config",
			"input": "Reviewed query batch table",
			"action": "Load enabled query batches and construct list-page queue.",
			"output": "List request queue with deterministic raw_json_path values.",
			"status_written": "request_status=pending",
		},
		{
			"stage": "2_list_fetch",
			"input": "One pending list request",
			"action": "Request or reload list JSON using cache-first behavior.",
			"output": "Archived raw list JSON and normalized candidate rows.",
			"status_written": "list parse_status success/list_failed",
		},
		{
			"stage": "3_url_queue",
			"input": "Candidate rows from list JSON",
			"action": "Normalize source URLs, build dedupe keys, and create detail-page queue.",
			"output": "Deduplicated candidate URL queue.",
			"status_written": "detail_status=pending/skipped",
		},
		{
			"stage": "4_detail_fetch",
			"input": "One pending public detail URL",
			"action": "Fetch or reload public HTML, then archive raw HTML before parsing.",
			"output": "Raw detail HTML path.",
			"status_written": "detail fetch success/detail_failed/skipped_access_restricted",
		},
		{
			"stage": "5_attachment_fetch",
			"input": "Attachment URLs discovered on detail page",
			"action": "Optionally fetch PDF/Word attachments with the same cache-first and bounded-retry rules.",
			"output": "Raw attachment paths and attachment extraction status.",
			"status_written": "attachment success/attachment_failed/not_present",
		},
		{
			"stage": "6_parse",
			"input": "Raw list JSON, raw detail HTML, and optional attachments",
			"action": "Extract structured fields into the output schema.",
			"output": "One normalized policy record per accepted candidate URL.",
			"status_written": "parse_status and review_status",
		},
	],
)
crawler_workflow

# %%
fetch_contract = pd.DataFrame(
	[
		{
			"target": "list_json",
			"cache_rule": "Use existing raw_json_path if present unless explicit refresh is requested.",
			"timeout_seconds": 30,
			"retry_policy": "At most one retry in pilot mode.",
			"failure_status": "list_failed",
			"artifact_path_rule": "data/raw/json/{list_request_id}.json",
		},
		{
			"target": "detail_html",
			"cache_rule": "Use existing raw_html_path if present before live fetch.",
			"timeout_seconds": 30,
			"retry_policy": "At most one retry in pilot mode.",
			"failure_status": "detail_failed",
			"artifact_path_rule": "data/raw/html/{candidate_id}.html",
		},
		{
			"target": "attachment_file",
			"cache_rule": "Use existing raw_file_path if present; do not fetch unsupported or access-restricted files.",
			"timeout_seconds": 30,
			"retry_policy": "At most one retry in pilot mode; skip large or restricted files.",
			"failure_status": "attachment_failed",
			"artifact_path_rule": "data/raw/{extension}/{candidate_id}_{attachment_index}.{extension}",
		},
	],
)
fetch_contract

# %%
parser_contract = pd.DataFrame(
	[
		{
			"field_group": "identity",
			"fields": "policy_id, source_site, source_url, province",
			"source_priority": "candidate queue, list JSON, detail final URL",
			"failure_behavior": "If source_url is missing, mark detail_failed and do not accept record.",
		},
		{
			"field_group": "bibliographic_metadata",
			"fields": "title, publish_date, agency, document_type",
			"source_priority": "detail HTML first, then list JSON fallback, then rule-based inference.",
			"failure_behavior": "Missing title/date sets parse_status=partial and review_status=needs_review.",
		},
		{
			"field_group": "text",
			"fields": "text_raw, text_clean, text_hash",
			"source_priority": "detail body selectors, full-page fallback, attachment extraction if needed.",
			"failure_behavior": "Empty or very short text sets parse_status=partial/detail_failed depending on available metadata.",
		},
		{
			"field_group": "attachments",
			"fields": "attachment_urls, raw_file_path, attachment_text",
			"source_priority": "detail HTML links that look like PDF/Word/Excel/archive attachments.",
			"failure_behavior": "Attachment extraction failure does not drop the record; mark attachment_failed or partial.",
		},
		{
			"field_group": "audit",
			"fields": "raw_json_path, raw_html_path, crawl_time, error, review_status",
			"source_priority": "fetcher/storage layer and parser exceptions.",
			"failure_behavior": "Never silently drop failures; write status and error/review note.",
		},
	],
)
parser_contract

# %%
document_type_rules = pd.DataFrame(
	[
		{
			"rule": "policy_document_by_title",
			"condition": "Title contains terms such as 通知, 意见, 办法, 规划, 方案, 公告.",
			"document_type": "policy_document",
			"review_status": "accepted",
		},
		{
			"rule": "attachment_page",
			"condition": "HTML has little body text but contains policy-like PDF/Word attachment links.",
			"document_type": "attachment_page",
			"review_status": "needs_review",
		},
		{
			"rule": "interpretation_or_news",
			"condition": "Title or page metadata indicates 解读, 新闻, 图片, 答记者问, or similar publicity content.",
			"document_type": "interpretation_or_news",
			"review_status": "needs_review",
		},
		{
			"rule": "notice_or_publicity_list",
			"condition": "Title indicates 申报通知, 名单, 公示, 批次, or recognition result list.",
			"document_type": "notice_or_publicity_list",
			"review_status": "needs_review",
		},
	],
)
document_type_rules

# %%
status_transition_design = pd.DataFrame(
	[
		{
			"event": "list response saved and parsed",
			"parse_status": "success",
			"review_status": "not_applicable_at_list_stage",
			"next_action": "Create candidate URL rows.",
		},
		{
			"event": "list request fails or JSON shape is invalid",
			"parse_status": "list_failed",
			"review_status": "needs_review",
			"next_action": "Do not create candidates from this request; inspect error.",
		},
		{
			"event": "detail HTML saved and required fields parsed",
			"parse_status": "success",
			"review_status": "accepted or needs_review based on document_type",
			"next_action": "Send record to quality checks.",
		},
		{
			"event": "detail HTML saved but body/date/agency incomplete",
			"parse_status": "partial",
			"review_status": "needs_review",
			"next_action": "Keep record with error/review note; do not drop.",
		},
		{
			"event": "detail page is access restricted",
			"parse_status": "skipped_access_restricted",
			"review_status": "rejected",
			"next_action": "Do not bypass access controls.",
		},
		{
			"event": "attachment extraction fails but detail body is usable",
			"parse_status": "partial",
			"review_status": "needs_review",
			"next_action": "Keep text and attachment URL; report attachment failure.",
		},
	],
)
status_transition_design

# %%
workflow_acceptance_checks = pd.DataFrame(
	[
		{
			"check": "Fetcher is cache-first and can reparse archived JSON/HTML without network.",
			"required_before_implementation": True,
		},
		{
			"check": "Raw artifacts are written before parser-derived structured rows.",
			"required_before_implementation": True,
		},
		{
			"check": "Parser returns a normalized record even when status is partial or failed.",
			"required_before_implementation": True,
		},
		{
			"check": "Attachment failures are explicit and do not silently remove the parent record.",
			"required_before_implementation": True,
		},
		{
			"check": "Access restrictions are marked skipped_access_restricted and are not bypassed.",
			"required_before_implementation": True,
		},
	],
)
workflow_acceptance_checks

# %% [markdown]
# ## Next TODO
#
# Next step: `Clean policy text; deduplicate and run quality checks`.
#
# The next increment should define conservative text-cleaning rules, exact duplicate keys, title/date duplicate checks,
# text-hash checks, and the quality report that gates expansion beyond pilot pages.

# %% [markdown]
# ## 7. Clean Policy Text, Deduplicate, and Run Quality Checks
#
# The crawler should preserve raw text and produce a conservative clean text field. Cleaning must not erase evidence
# needed for policy-instrument classification or later audit. Deduplication and quality checks should gate any expansion
# beyond pilot pages.

# %%
text_cleaning_rules = pd.DataFrame(
	[
		{
			"rule_id": "preserve_raw_text",
			"input_field": "text_raw",
			"output_field": "text_raw",
			"rule": "Never overwrite raw extracted body text.",
			"risk_if_wrong": "Cannot audit parser behavior or revise cleaning rules later.",
		},
		{
			"rule_id": "normalize_whitespace",
			"input_field": "text_raw",
			"output_field": "text_clean",
			"rule": "Collapse repeated whitespace while preserving paragraph-like sentence order.",
			"risk_if_wrong": "Over-cleaning can damage Chinese policy clauses and numbered sections.",
		},
		{
			"rule_id": "remove_page_chrome",
			"input_field": "text_raw",
			"output_field": "text_clean",
			"rule": "Remove obvious page chrome such as share buttons, QR prompts, and navigation residue when safely identifiable.",
			"risk_if_wrong": "Aggressive removal may delete legitimate policy text.",
		},
		{
			"rule_id": "keep_policy_markers",
			"input_field": "text_raw",
			"output_field": "text_clean",
			"rule": "Keep document numbers, dates, issuing agencies, article numbers, and attachment references.",
			"risk_if_wrong": "Policy type, time, and instrument classification signals may be lost.",
		},
		{
			"rule_id": "no_semantic_rewrite",
			"input_field": "text_raw",
			"output_field": "text_clean",
			"rule": "Do not summarize, translate, rewrite, or infer missing text during cleaning.",
			"risk_if_wrong": "The corpus would no longer be a source-faithful policy text dataset.",
		},
	],
)
text_cleaning_rules

# %%
dedupe_design = pd.DataFrame(
	[
		{
			"dedupe_level": "source_url",
			"key": "normalized source_url",
			"purpose": "Avoid fetching and parsing the same public detail URL repeatedly.",
			"action": "Keep first discovery and record later query batches as additional provenance.",
		},
		{
			"dedupe_level": "title_date",
			"key": "normalized title + publish_date",
			"purpose": "Catch reposts or URL variants of the same policy.",
			"action": "Mark duplicates as needs_review before dropping anything.",
		},
		{
			"dedupe_level": "text_hash",
			"key": "hash(text_clean or text_raw)",
			"purpose": "Detect exact duplicate body text after parsing.",
			"action": "Use as a strong duplicate signal, but preserve raw records until review.",
		},
		{
			"dedupe_level": "attachment_url",
			"key": "normalized attachment URL",
			"purpose": "Avoid repeated downloads of identical attachments.",
			"action": "Fetch once and link multiple records to the same raw attachment path if needed.",
		},
	],
)
dedupe_design

# %%
quality_report_contract = pd.DataFrame(
	[
		{
			"metric": "total_candidate_records",
			"source": "candidate URL queue",
			"action_threshold": "Always report.",
			"why_it_matters": "Defines the denominator for parser and review rates.",
		},
		{
			"metric": "successfully_parsed_records",
			"source": "parse_status",
			"action_threshold": "Must be high enough before expanding pages.",
			"why_it_matters": "Low success means crawler should improve parsers before scaling.",
		},
		{
			"metric": "missing_publish_date",
			"source": "publish_date",
			"action_threshold": "Any non-trivial count requires parser review.",
			"why_it_matters": "Year/date are required for policy intensity and panel alignment.",
		},
		{
			"metric": "empty_or_short_text",
			"source": "text_raw/text_clean length",
			"action_threshold": "Stop expansion if unexplained by attachment pages or document type.",
			"why_it_matters": "Text mining cannot use records with no substantive policy text.",
		},
		{
			"metric": "duplicate_source_urls",
			"source": "source_url dedupe key",
			"action_threshold": "Review if duplicate rate is high within a query batch.",
			"why_it_matters": "High duplication indicates query overlap or queue construction issues.",
		},
		{
			"metric": "duplicate_title_date_pairs",
			"source": "title + publish_date",
			"action_threshold": "Mark for review before removing.",
			"why_it_matters": "Potential reposts or same policy across multiple pages.",
		},
		{
			"metric": "attachment_failures",
			"source": "attachment parse/fetch status",
			"action_threshold": "Review before accepting attachment-heavy batches.",
			"why_it_matters": "Some policy bodies may live only in attachments.",
		},
		{
			"metric": "needs_review_records",
			"source": "review_status",
			"action_threshold": "Do not scale while unresolved review cases dominate.",
			"why_it_matters": "Ambiguous document types can distort policy-intensity measures.",
		},
	],
)
quality_report_contract

# %%
expansion_gate = pd.DataFrame(
	[
		{
			"gate": "pilot_batch_complete",
			"pass_condition": "All enabled query batches have list JSON archived or an explicit failure status.",
			"if_fail": "Do not add pages; inspect fetcher/status handling.",
		},
		{
			"gate": "detail_parse_quality",
			"pass_condition": "Representative detail pages parse title, publish_date, source_url, and body or attachment references.",
			"if_fail": "Improve detail parser or document-type rules first.",
		},
		{
			"gate": "duplicate_control",
			"pass_condition": "URL and title/date duplicates are quantified and explainable.",
			"if_fail": "Fix queue dedupe before requesting more pages.",
		},
		{
			"gate": "review_burden",
			"pass_condition": "`needs_review` cases are understood and have clear review categories.",
			"if_fail": "Clarify inclusion rules before scaling.",
		},
		{
			"gate": "compliance_and_rate_limit",
			"pass_condition": "Request limits, cache behavior, and access-restriction handling are documented.",
			"if_fail": "Do not expand collection.",
		},
	],
)
expansion_gate

# %%
storage_outputs = pd.DataFrame(
	[
		{
			"output_layer": "raw",
			"planned_artifacts": "list JSON, detail HTML, attachments",
			"purpose": "Source-faithful audit and parser re-runs.",
		},
		{
			"output_layer": "interim",
			"planned_artifacts": "candidate URL queue, parsed detail records, quality report",
			"purpose": "Reviewable crawler outputs before corpus construction.",
		},
		{
			"output_layer": "processed",
			"planned_artifacts": "clean policy-text corpus and policy-strength features",
			"purpose": "Downstream text classification and statistical modeling.",
		},
	],
)
storage_outputs

# %% [markdown]
# ## Next TODO
#
# Next step: `Store raw and structured data; use the corpus for text classification and statistical modeling`.
#
# The next increment should close the crawler-design notebook by specifying final storage conventions, configuration
# files to create before implementation, and the go/no-go checklist for moving reusable code into `src/` or `scripts/`.

# %% [markdown]
# ## 8. Store Raw and Structured Data; Connect to Modeling
#
# This final design section closes the crawler workflow. It defines what files the future implementation should write,
# what configuration should exist before running it, and what conditions must be met before moving from notebook design
# to reusable crawler code.

# %%
storage_conventions = pd.DataFrame(
	[
		{
			"layer": "raw",
			"path_pattern": "data/raw/json/{source_id}_{query_batch_id}_page_{page_no:03d}.json",
			"content": "Unmodified list JSON response.",
			"producer": "Fetcher",
			"consumer": "Parser and audit review.",
		},
		{
			"layer": "raw",
			"path_pattern": "data/raw/html/{candidate_id}.html",
			"content": "Unmodified public detail-page HTML.",
			"producer": "Fetcher",
			"consumer": "Parser and audit review.",
		},
		{
			"layer": "raw",
			"path_pattern": "data/raw/{extension}/{candidate_id}_{attachment_index}.{extension}",
			"content": "Downloaded attachment file when present and allowed.",
			"producer": "Fetcher",
			"consumer": "Attachment parser and audit review.",
		},
		{
			"layer": "interim",
			"path_pattern": "data/interim/{source_id}_candidate_url_queue.csv",
			"content": "Deduplicated candidate detail URLs with query provenance.",
			"producer": "Queue builder",
			"consumer": "Detail fetcher.",
		},
		{
			"layer": "interim",
			"path_pattern": "data/interim/{source_id}_policy_detail_records.parquet",
			"content": "Parsed records with status fields and raw artifact paths.",
			"producer": "Parser",
			"consumer": "Validator and review.",
		},
		{
			"layer": "interim",
			"path_pattern": "outputs/{source_id}_quality_report.csv",
			"content": "Quality metrics that gate expansion.",
			"producer": "Validator",
			"consumer": "Researcher/agent decision review.",
		},
		{
			"layer": "processed",
			"path_pattern": "data/processed/policy_texts_clean.parquet",
			"content": "Accepted clean policy-text corpus for text classification.",
			"producer": "Cleaner/reviewer",
			"consumer": "Text classification and policy-intensity construction.",
		},
	],
)
storage_conventions

# %%
configuration_files_to_create = pd.DataFrame(
	[
		{
			"config_file": "configs/govcn_xxgk_sources.toml",
			"purpose": "Source constants, endpoints, source_id, rate-limit policy, and compliance notes.",
			"required_before_code": True,
		},
		{
			"config_file": "configs/govcn_xxgk_query_batches.csv",
			"purpose": "Reviewed query batches: keyword, search_position, match_mode, sort_by, page_size, max_pages, enabled.",
			"required_before_code": True,
		},
		{
			"config_file": "configs/policy_text_schema.toml",
			"purpose": "Shared output fields, status values, and required-field policy.",
			"required_before_code": False,
		},
		{
			"config_file": "configs/document_type_rules.toml",
			"purpose": "Reviewable document-type rules for policy documents, attachments, news/interpretations, and notices/lists.",
			"required_before_code": False,
		},
	],
)
configuration_files_to_create

# %%
modeling_handoff = pd.DataFrame(
	[
		{
			"downstream_task": "text_classification",
			"required_crawler_fields": "policy_id, title, text_clean, document_type, keyword_hit, source_url",
			"handoff_note": "Classify policy tools and SRDI relevance only on accepted or explicitly reviewed records.",
		},
		{
			"downstream_task": "policy_intensity_by_year",
			"required_crawler_fields": "province, publish_date, agency, document_type, text_clean, policy_id",
			"handoff_note": "Central records should be labeled `province=central`; province-level intensity needs a separate source workflow.",
		},
		{
			"downstream_task": "audit_and_reproducibility",
			"required_crawler_fields": "source_url, raw_json_path, raw_html_path, raw_file_path, crawl_time, text_hash",
			"handoff_note": "Every structured record must link back to raw artifacts or carry an explicit failure/skip status.",
		},
		{
			"downstream_task": "manual_review",
			"required_crawler_fields": "review_status, error, document_type, title, source_url",
			"handoff_note": "Records marked needs_review should be resolved before final corpus export.",
		},
	],
)
modeling_handoff

# %%
implementation_go_no_go = pd.DataFrame(
	[
		{
			"gate": "crawler_contract_complete",
			"status": "ready",
			"evidence": "This notebook defines requirements, schema, source map, queue contract, workflow, parsing, cleaning, and storage.",
		},
		{
			"gate": "configuration_files_exist",
			"status": "not_ready",
			"evidence": "Configs are specified above but not yet created.",
		},
		{
			"gate": "pilot_query_results_reviewed",
			"status": "not_ready",
			"evidence": "Notebook 20 provides baseline evidence; full-text and blank-keyword pilot batches still need review.",
		},
		{
			"gate": "quality_report_accepted",
			"status": "not_ready",
			"evidence": "Quality report contract is defined, but no formal pilot quality report has been accepted.",
		},
		{
			"gate": "ready_to_move_to_src_or_scripts",
			"status": "not_ready",
			"evidence": "Create configs and run/review pilot queue before production crawler implementation.",
		},
	],
)
implementation_go_no_go

# %%
final_decision_log = pd.DataFrame(
	[
		{
			"decision": "central_govcn_xxgk_crawler_design",
			"chosen_direction": "Proceed to config-backed pilot crawler design, not broad crawling.",
			"evidence": "Existing notebook 20 proves list JSON and detail HTML feasibility for a small sample; this notebook defines the crawler contract.",
			"unresolved_risk": "Full-text recall, blank-keyword list behavior, attachment extraction, and quality thresholds still need pilot review.",
			"user_decision_needed": "Approve creation of configs and a small config-backed pilot implementation.",
			"ready_for_implementation": False,
		},
	],
)
final_decision_log

# %% [markdown]
# ## Final TODO
#
# Before implementing reusable crawler code, create the source/query configuration files and run a small reviewed pilot:
#
# 1. Create `configs/govcn_xxgk_sources.toml`.
# 2. Create `configs/govcn_xxgk_query_batches.csv`.
# 3. Run only enabled pilot batches.
# 4. Produce and review the quality report.
# 5. Move reusable fetch/parse/storage/validator code into `src/` or `scripts/` only after the pilot is accepted.
