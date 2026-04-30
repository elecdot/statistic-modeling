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
from __future__ import annotations

from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
DETAILS_PATH = ROOT / "data" / "interim" / "govcn_xxgk_all_policy_detail_records.csv"
QUALITY_PATH = ROOT / "outputs" / "govcn_xxgk_all_quality_report.csv"

EXPECTED_DETAIL_ROWS = 720
TARGET_START = "2020-01-01"
TARGET_END = "2025-12-31"
SHORT_TEXT_THRESHOLD = 200
OFFICIAL_SUBJECT_SEPARATOR = "\\"


def extract_official_subject_categories_from_html(html: str) -> list[str]:
	"""Extract gov.cn's official non-exclusive subject categories from detail HTML."""
	soup = BeautifulSoup(html, "html.parser")
	category_node = soup.select_one(".zcwj_ztfl")
	if category_node is None:
		for label in soup.find_all(string=lambda value: value and "主题分类" in value):
			cell = label.find_parent("td")
			next_cell = cell.find_next_sibling("td") if cell else None
			if next_cell:
				category_node = next_cell
				break
	if category_node is None:
		return []
	raw_value = " ".join(category_node.get_text(" ", strip=True).split())
	return [part.strip() for part in raw_value.split(OFFICIAL_SUBJECT_SEPARATOR) if part.strip()]

# %% [markdown]
# # gov.cn XXGK Central Corpus QA
#
# This notebook starts the processing exploration after the central
# `gov.cn/zhengce/xxgk` crawler has produced the 2020-2025 all-policy corpus.
#
# Goal:
#
# - inspect whether the crawler output is ready to become a stable processed
#   policy-text corpus;
# - identify records that need review before text mining;
# - define a conservative processed-corpus v0 field set without writing files.

# %% [markdown]
# ## 1. Load Current Corpus Artifacts
#
# The all-policy detail table is the current unit of review. Each row should be
# one deduplicated public policy detail page.

# %%
details = pd.read_csv(DETAILS_PATH)
quality = pd.read_csv(QUALITY_PATH)

details["publish_date_parsed"] = pd.to_datetime(details["publish_date"], errors="coerce")
details["text_len"] = details["text_clean"].fillna("").str.len()
details["has_text"] = details["text_len"] > 0
details["is_short_text"] = details["text_len"] < SHORT_TEXT_THRESHOLD
details["has_attachment"] = details["attachment_urls"].fillna("").str.len() > 2

artifact_overview = pd.DataFrame(
	[
		{"check": "detail_rows", "value": len(details), "expected_or_note": EXPECTED_DETAIL_ROWS},
		{"check": "unique_source_urls", "value": details["source_url"].nunique(), "expected_or_note": len(details)},
		{"check": "date_min", "value": details["publish_date_parsed"].min().date(), "expected_or_note": TARGET_START},
		{"check": "date_max", "value": details["publish_date_parsed"].max().date(), "expected_or_note": TARGET_END},
		{"check": "crawler_quality_rows", "value": len(quality), "expected_or_note": 1},
	],
)
artifact_overview

# %% [markdown]
# ## 2. Corpus Quality Snapshot
#
# These tables turn crawler status columns into review queues. They should be
# inspected before deciding which records are accepted into `data/processed/`.

# %%
status_breakdown = (
	details.groupby(["parse_status", "review_status", "document_type"], dropna=False)
	.size()
	.reset_index(name="records")
	.sort_values("records", ascending=False)
)
status_breakdown

# %%
qa_summary = pd.DataFrame(
	[
		{"metric": "detail_records", "value": len(details), "interpretation": "Current all-policy detail rows."},
		{"metric": "success_details", "value": int((details["parse_status"] == "success").sum()), "interpretation": "Rows with extracted detail text."},
		{"metric": "detail_failed", "value": int((details["parse_status"] == "detail_failed").sum()), "interpretation": "Rows retained for retry or manual review."},
		{"metric": "needs_review", "value": int((details["review_status"] == "needs_review").sum()), "interpretation": "Rows not automatically accepted."},
		{"metric": "short_text_lt_200", "value": int(details["is_short_text"].sum()), "interpretation": "Likely attachment pages, notices, or parser edge cases."},
		{"metric": "missing_publish_date", "value": int(details["publish_date_parsed"].isna().sum()), "interpretation": "Rows without parseable publication date."},
		{"metric": "duplicate_source_url", "value": int(details.duplicated("source_url").sum()), "interpretation": "Should remain 0 after crawler deduplication."},
		{"metric": "duplicate_text_hash", "value": int(details["text_hash"].duplicated().sum()), "interpretation": "Should remain 0 except failed rows with blank hashes."},
		{"metric": "outside_target_window", "value": int((~details["in_target_date_window"].fillna(False)).sum()), "interpretation": "Should remain 0 for processed v0."},
	],
)
qa_summary

# %% [markdown]
# ## 3. Review Queue
#
# The review queue is deterministic and intentionally small enough to inspect
# manually. It prioritizes failed rows, short rows, missing dates, and rows
# already marked `needs_review`.

# %%
review_candidates = details.assign(
	review_reason=lambda df: [
		";".join(
			reason
			for reason, triggered in [
				("detail_failed", row.parse_status == "detail_failed"),
				("needs_review", row.review_status == "needs_review"),
				("short_text", row.is_short_text),
				("missing_date", pd.isna(row.publish_date_parsed)),
				("outside_window", not bool(row.in_target_date_window)),
			]
			if triggered
		)
		for row in df.itertuples(index=False)
	],
)

review_queue = (
	review_candidates.loc[review_candidates["review_reason"] != ""]
	.assign(
		severity=lambda df: df["review_reason"].str.contains("detail_failed").astype(int) * 100
		+ df["review_reason"].str.contains("missing_date").astype(int) * 50
		+ df["review_reason"].str.contains("short_text").astype(int) * 10
	)
	.sort_values(["severity", "publish_date_parsed", "title"], ascending=[False, False, True])
	[
		[
			"policy_id",
			"title",
			"publish_date",
			"agency",
			"document_type",
			"parse_status",
			"review_status",
			"text_len",
			"review_reason",
			"source_url",
			"error",
		]
	]
	.reset_index(drop=True)
)
review_queue.head(30)

# %%
review_reason_summary = (
	review_queue["review_reason"]
	.str.get_dummies(sep=";")
	.sum()
	.rename_axis("review_reason")
	.reset_index(name="records")
	.sort_values("records", ascending=False)
)
review_reason_summary

# %% [markdown]
# ## 4. Official Subject Category Probe
#
# gov.cn detail pages can include a self-labeled `主题分类` field. The official
# value is non-exclusive and split with `\`, for example
# `城乡建设、环境保护\其他`.
#
# Project field name decision:
#
# - use `official_subject_categories`;
# - keep the official Chinese labels as a list of category strings;
# - do not reuse this field as the later province-level policy-tool
#   classification, because local policy sources may not provide the same
#   taxonomy.

# %%
subject_probe_rows = []
for row in details.itertuples(index=False):
	raw_html_path = getattr(row, "raw_html_path")
	path = Path(raw_html_path) if isinstance(raw_html_path, str) and raw_html_path else None
	if path and path.exists():
		categories = extract_official_subject_categories_from_html(path.read_text(encoding="utf-8"))
	else:
		categories = []
	subject_probe_rows.append(
		{
			"policy_id": row.policy_id,
			"title": row.title,
			"source_url": row.source_url,
			"raw_html_path": raw_html_path,
			"official_subject_categories": categories,
			"official_subject_category_count": len(categories),
		},
	)

subject_probe = pd.DataFrame(subject_probe_rows)
subject_probe_summary = pd.DataFrame(
	[
		{"metric": "detail_records", "value": len(subject_probe), "note": "All all-policy detail rows."},
		{
			"metric": "with_official_subject_categories",
			"value": int((subject_probe["official_subject_category_count"] > 0).sum()),
			"note": "Rows whose archived HTML exposes 主题分类.",
		},
		{
			"metric": "missing_official_subject_categories",
			"value": int((subject_probe["official_subject_category_count"] == 0).sum()),
			"note": "Includes failed rows or detail templates without this metadata block.",
		},
	]
)
subject_probe_summary

# %%
official_subject_category_counts = (
	subject_probe.explode("official_subject_categories")
	.dropna(subset=["official_subject_categories"])
	.groupby("official_subject_categories")
	.size()
	.rename_axis("official_subject_category")
	.reset_index(name="records")
	.sort_values(["records", "official_subject_category"], ascending=[False, True])
	.reset_index(drop=True)
)
official_subject_category_counts

# %%
subject_probe.loc[
	subject_probe["official_subject_category_count"] > 1,
	["title", "official_subject_categories", "source_url"],
].head(10)

# %% [markdown]
# ## 5. Manual Review Decisions
#
# Manual review completed on 2026-04-30:
#
# - the single `detail_failed` row is a timeout and can be dropped from
#   processed v0;
# - all short-text rows were inspected and the captured text is correct. They
#   should be accepted into processed v0, not treated as parser exceptions.

# %%
manual_review_decisions = pd.DataFrame(
	[
		{
			"condition": "parse_status == 'detail_failed'",
			"records": int((details["parse_status"] == "detail_failed").sum()),
			"manual_decision": "exclude_from_processed_v0",
			"reason": "The retained timeout row has no text. It remains in interim audit data but is not useful for text mining.",
		},
		{
			"condition": "parse_status == 'success' and text_len < 200",
			"records": int(((details["parse_status"] == "success") & details["is_short_text"]).sum()),
			"manual_decision": "accept_into_processed_v0",
			"reason": "Manual review confirmed the short texts were correctly captured and are not exceptions.",
		},
	],
)
manual_review_decisions

# %%
details_reviewed = details.copy()
details_reviewed["manual_review_status"] = details_reviewed["review_status"]
details_reviewed["manual_exclusion_reason"] = ""

timeout_mask = details_reviewed["parse_status"] == "detail_failed"
short_success_mask = (details_reviewed["parse_status"] == "success") & details_reviewed["is_short_text"]

details_reviewed.loc[timeout_mask, "manual_review_status"] = "rejected"
details_reviewed.loc[timeout_mask, "manual_exclusion_reason"] = "timeout_no_text_drop_from_processed_v0"
details_reviewed.loc[short_success_mask, "manual_review_status"] = "accepted"

manual_review_summary = (
	details_reviewed.groupby(["parse_status", "review_status", "manual_review_status"], dropna=False)
	.size()
	.reset_index(name="records")
	.sort_values("records", ascending=False)
)
manual_review_summary

# %% [markdown]
# ## 6. Processed Corpus v0 Contract Draft
#
# This is a proposed stable field set for the next step. The preview below does
# not write any file. It shows what an accepted processed output would look like
# after applying the manual review decisions above.

# %%
processed_schema = pd.DataFrame(
	[
		{"field": "policy_id", "source": "detail_records.policy_id", "purpose": "Stable record identifier."},
		{"field": "province", "source": "detail_records.province", "purpose": "Fixed to central for this corpus."},
		{"field": "title", "source": "detail_records.title", "purpose": "Policy title for search and classification."},
		{"field": "publish_date", "source": "detail_records.publish_date", "purpose": "Date for year and event-time features."},
		{"field": "publish_year", "source": "derived from publish_date", "purpose": "Panel merge and year-level summaries."},
		{"field": "agency", "source": "detail_records.agency", "purpose": "Issuing body metadata."},
		{"field": "source_site", "source": "detail_records.source_site", "purpose": "Corpus provenance."},
		{"field": "source_url", "source": "detail_records.source_url", "purpose": "Audit link and deduplication key."},
		{"field": "official_subject_categories", "source": "detail HTML 主题分类", "purpose": "Official gov.cn non-exclusive subject categories, preserved as Chinese labels."},
		{"field": "document_type", "source": "detail_records.document_type", "purpose": "Coarse type control for policy text mining."},
		{"field": "text_clean", "source": "detail_records.text_clean", "purpose": "Main text input for downstream NLP."},
		{"field": "text_len", "source": "derived from text_clean", "purpose": "Quality filter and descriptive statistics."},
		{"field": "text_hash", "source": "detail_records.text_hash", "purpose": "Text duplicate control."},
		{"field": "attachment_urls", "source": "detail_records.attachment_urls", "purpose": "Attachment audit and future parsing queue."},
		{"field": "raw_json_path", "source": "detail_records.raw_json_path", "purpose": "Raw list JSON provenance."},
		{"field": "raw_html_path", "source": "detail_records.raw_html_path", "purpose": "Raw detail HTML provenance."},
		{"field": "parse_status", "source": "detail_records.parse_status", "purpose": "Parser outcome retained for audit."},
		{"field": "review_status", "source": "manual_review_status", "purpose": "Final acceptance state after manual review."},
	],
)
processed_schema

# %%
processed_v0_preview = (
	details_reviewed.loc[
		(details["parse_status"] == "success")
		& (details_reviewed["manual_review_status"] == "accepted")
		& details["in_target_date_window"].fillna(False)
		& details["has_text"]
	]
	.drop(columns=["official_subject_categories"], errors="ignore")
	.merge(subject_probe[["policy_id", "official_subject_categories"]], on="policy_id", how="left")
	.assign(publish_year=lambda df: df["publish_date_parsed"].dt.year.astype("Int64"))
	.assign(review_status=lambda df: df["manual_review_status"])
	[
		[
			"policy_id",
			"province",
			"title",
			"publish_date",
			"publish_year",
			"agency",
			"source_site",
			"source_url",
			"official_subject_categories",
			"document_type",
			"text_clean",
			"text_len",
			"text_hash",
			"attachment_urls",
			"raw_json_path",
			"raw_html_path",
			"parse_status",
			"review_status",
		]
	]
	.reset_index(drop=True)
)

processed_v0_overview = pd.DataFrame(
	[
		{"item": "processed_v0_preview_rows", "value": len(processed_v0_preview), "note": "Rows accepted after manual review decisions."},
		{"item": "excluded_timeout_or_failure", "value": len(details) - len(processed_v0_preview), "note": "Rows excluded from processed v0."},
		{"item": "min_publish_year", "value": int(processed_v0_preview["publish_year"].min()), "note": "Expected 2020."},
		{"item": "max_publish_year", "value": int(processed_v0_preview["publish_year"].max()), "note": "Expected 2025."},
	]
)
processed_v0_overview

# %%
processed_v0_preview.head(10)

# %% [markdown]
# ## 7. Decisions For Next Step
#
# The key review decisions are now resolved. The next notebook or script can
# write a processed v0 artifact using the rule below.

# %%
open_decisions = pd.DataFrame(
	[
		{
			"decision": "processed_v0_acceptance_rule",
			"recommended_default": "Include parse_status=success, manual_review_status=accepted, in_target_date_window=True, non-empty text.",
			"why_it_matters": "Includes manually accepted short texts and excludes the timeout row.",
		},
		{
			"decision": "short_text_policy",
			"recommended_default": "Accept all currently reviewed short-text rows into v0.",
			"why_it_matters": "Manual review confirmed these are correctly captured short policies or notices.",
		},
		{
			"decision": "failed_detail_policy",
			"recommended_default": "Do not include the retained detail_failed row in processed v0.",
			"why_it_matters": "The failed row has no text and should remain an audit/retry item.",
		},
		{
			"decision": "attachment_policy",
			"recommended_default": "Keep attachment URLs as provenance; parse attachments in a later explicit pass.",
			"why_it_matters": "Attachment parsing needs separate PDF/Word handling and quality checks.",
		},
		{
			"decision": "official_subject_categories_policy",
			"recommended_default": "Include official_subject_categories in crawler detail outputs and processed v0 when gov.cn HTML provides 主题分类.",
			"why_it_matters": "The field preserves source-provided topical metadata without forcing it onto future local-government corpora.",
		},
		{
			"decision": "next_output_path",
			"recommended_default": "data/processed/govcn_xxgk_all_policy_text_corpus_v0.csv",
			"why_it_matters": "Processed outputs need stable versioned names before downstream text mining.",
		},
	],
)
open_decisions
