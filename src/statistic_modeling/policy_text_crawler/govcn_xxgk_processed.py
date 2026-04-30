"""Build processed gov.cn XXGK policy-text corpora from crawler detail records."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

SHORT_TEXT_THRESHOLD = 200

PROCESSED_V0_COLUMNS = [
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


def parse_serialized_list(value: object) -> list[str]:
	"""Parse list-like CSV values written by pandas from crawler list fields."""
	if isinstance(value, list):
		return [str(item) for item in value if str(item)]
	if pd.isna(value) or value == "":
		return []
	if isinstance(value, str):
		try:
			parsed = ast.literal_eval(value)
		except (SyntaxError, ValueError):
			return [value] if value else []
		if isinstance(parsed, list):
			return [str(item) for item in parsed if str(item)]
	return []


def with_manual_review_decisions(details: pd.DataFrame) -> pd.DataFrame:
	"""Apply the reviewed v0 rule: drop timeout failures, accept valid short text."""
	reviewed = details.copy()
	reviewed["publish_date_parsed"] = pd.to_datetime(reviewed["publish_date"], errors="coerce")
	reviewed["text_len"] = reviewed["text_clean"].fillna("").str.len()
	reviewed["has_text"] = reviewed["text_len"] > 0
	reviewed["is_short_text"] = reviewed["text_len"] < SHORT_TEXT_THRESHOLD
	reviewed["manual_review_status"] = reviewed["review_status"]
	reviewed["manual_exclusion_reason"] = ""

	timeout_mask = reviewed["parse_status"] == "detail_failed"
	short_success_mask = (reviewed["parse_status"] == "success") & reviewed["is_short_text"]

	reviewed.loc[timeout_mask, "manual_review_status"] = "rejected"
	reviewed.loc[timeout_mask, "manual_exclusion_reason"] = "timeout_no_text_drop_from_processed_v0"
	reviewed.loc[short_success_mask, "manual_review_status"] = "accepted"
	return reviewed


def build_processed_v0(details: pd.DataFrame) -> pd.DataFrame:
	"""Build the accepted central all-policy processed corpus v0."""
	reviewed = with_manual_review_decisions(details)
	accepted = reviewed.loc[
		(reviewed["parse_status"] == "success")
		& (reviewed["manual_review_status"] == "accepted")
		& reviewed["in_target_date_window"].fillna(False)
		& reviewed["has_text"]
	].copy()
	accepted["publish_year"] = accepted["publish_date_parsed"].dt.year.astype("Int64")
	accepted["review_status"] = accepted["manual_review_status"]
	return accepted[PROCESSED_V0_COLUMNS].reset_index(drop=True)


def build_processed_quality_report(details: pd.DataFrame, processed: pd.DataFrame) -> pd.DataFrame:
	"""Create a long-form QA report for processed v0."""
	reviewed = with_manual_review_decisions(details)
	subject_values = [
		category
		for value in processed["official_subject_categories"]
		for category in parse_serialized_list(value)
	]
	attachment_url_rows = processed["attachment_urls"].fillna("[]").map(parse_serialized_list).map(bool)
	rows = [
		("source_detail_records", len(details), "Rows in interim all-policy detail records."),
		("processed_records", len(processed), "Rows accepted into processed v0."),
		("excluded_records", len(details) - len(processed), "Rows excluded from processed v0."),
		("excluded_detail_failed", int((reviewed["parse_status"] == "detail_failed").sum()), "Timeout/detail failures excluded from processed v0."),
		("short_text_accepted", int(((processed["parse_status"] == "success") & (processed["text_len"] < SHORT_TEXT_THRESHOLD)).sum()), "Manual review confirmed these short texts are valid captures."),
		("missing_publish_dates", int(processed["publish_date"].isna().sum()), "Processed rows without publication date."),
		("duplicate_source_urls", int(processed.duplicated("source_url").sum()), "Duplicate source URLs in processed v0."),
		("duplicate_text_hashes", int(processed.duplicated("text_hash").sum()), "Duplicate normalized text hashes in processed v0."),
		("min_publish_year", int(processed["publish_year"].min()), "Earliest publication year in processed v0."),
		("max_publish_year", int(processed["publish_year"].max()), "Latest publication year in processed v0."),
		("rows_with_official_subject_categories", int(processed["official_subject_categories"].fillna("[]").ne("[]").sum()), "Rows with gov.cn official subject categories."),
		("unique_official_subject_categories", len(set(subject_values)), "Distinct official subject category labels after splitting list values."),
		("rows_with_attachment_urls", int(attachment_url_rows.sum()), "Processed rows with downloadable attachment URLs."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def write_processed_v0(
	details_input: Path,
	processed_output: Path,
	quality_output: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
	"""Read interim detail records and write processed v0 plus QA report."""
	details = pd.read_csv(details_input)
	processed = build_processed_v0(details)
	quality_report = build_processed_quality_report(details, processed)

	processed_output.parent.mkdir(parents=True, exist_ok=True)
	quality_output.parent.mkdir(parents=True, exist_ok=True)
	processed.to_csv(processed_output, index=False)
	quality_report.to_csv(quality_output, index=False)
	return processed, quality_report
