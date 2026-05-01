"""Build processed datasets from the manually collected SRDI policy workbook."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS_START = pd.Timestamp("2020-01-01")
ANALYSIS_END = pd.Timestamp("2025-12-31")
SRDI_KEYWORD = "专精特新"
CENTRAL_SOURCE_LABEL = "国家"
XINJIANG_SOURCE_LABELS = {"新疆维吾尔自治区", "新疆生产建设兵团"}

RAW_COLUMNS = {
	"序号": "source_row_number",
	"所属省份": "source_label_original",
	"地区名称": "region_name",
	"发文日期": "publish_date",
	"关键词数量清单": "keyword_count_metadata",
	"关键词总数量": "keyword_count_raw",
	"标题": "title",
	"文号": "document_number",
	"发文机构": "agency",
	"原文链接": "source_url",
	"摘要": "abstract",
}

PROCESSED_POLICY_COLUMNS = [
	"policy_id",
	"province",
	"source_label_original",
	"jurisdiction_type",
	"region_name",
	"publish_date",
	"publish_year",
	"keyword_hit",
	"keyword_count",
	"keyword_count_raw",
	"title",
	"document_number",
	"agency",
	"source_url",
	"abstract",
	"title_contains_srdi",
	"abstract_contains_srdi",
	"title_or_abstract_contains_srdi",
	"in_analysis_window",
	"review_status",
]

INTENSITY_COLUMNS = [
	"province",
	"publish_year",
	"srdi_policy_count",
	"log_srdi_policy_count_plus1",
	"total_keyword_count",
	"avg_keyword_count",
	"title_contains_srdi_count",
	"abstract_contains_srdi_count",
	"title_or_abstract_contains_srdi_count",
	"missing_agency_count",
	"unique_agency_count",
]


def stable_policy_id(source_url: object) -> str:
	"""Create a stable short ID from the source URL."""
	text = "" if pd.isna(source_url) else str(source_url).strip()
	digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
	return f"manual_srdi_{digest}"


def normalize_province(source_label: object) -> str:
	"""Map source labels to final analysis units."""
	label = "" if pd.isna(source_label) else str(source_label).strip()
	if label == CENTRAL_SOURCE_LABEL:
		return "central"
	if label in XINJIANG_SOURCE_LABELS:
		return "新疆"
	return label


def normalize_manual_policy_workbook(raw: pd.DataFrame) -> pd.DataFrame:
	"""Standardize raw workbook columns and derived flags."""
	missing_columns = sorted(set(RAW_COLUMNS) - set(raw.columns))
	if missing_columns:
		raise ValueError(f"manual SRDI workbook missing columns: {missing_columns}")

	records = raw.rename(columns=RAW_COLUMNS).copy()
	for column in RAW_COLUMNS.values():
		if column in records:
			records[column] = records[column].fillna("").astype(str).str.strip()

	records["publish_date_parsed"] = pd.to_datetime(records["publish_date"], errors="coerce")
	records["publish_date"] = records["publish_date_parsed"].dt.date.astype("string")
	records["publish_year"] = records["publish_date_parsed"].dt.year.astype("Int64")
	records["in_analysis_window"] = records["publish_date_parsed"].between(
		ANALYSIS_START,
		ANALYSIS_END,
		inclusive="both",
	)
	records["province"] = records["source_label_original"].map(normalize_province)
	records["jurisdiction_type"] = records["province"].eq("central").map({True: "central", False: "local"})
	records["keyword_hit"] = SRDI_KEYWORD
	records["keyword_count"] = pd.to_numeric(records["keyword_count_raw"], errors="coerce").astype("Int64")
	records["policy_id"] = records["source_url"].map(stable_policy_id)
	records["title_contains_srdi"] = records["title"].str.contains(SRDI_KEYWORD, regex=False)
	records["abstract_contains_srdi"] = records["abstract"].str.contains(SRDI_KEYWORD, regex=False)
	records["title_or_abstract_contains_srdi"] = records["title_contains_srdi"] | records["abstract_contains_srdi"]
	records["review_status"] = "accepted"
	return records


def build_manual_policy_records_v0(raw: pd.DataFrame) -> pd.DataFrame:
	"""Build analysis-window processed policy records from the manual workbook."""
	records = normalize_manual_policy_workbook(raw)
	processed = records.loc[records["in_analysis_window"]].copy()
	return processed[PROCESSED_POLICY_COLUMNS].reset_index(drop=True)


def build_province_year_intensity_v0(processed: pd.DataFrame) -> pd.DataFrame:
	"""Build a balanced province-year SRDI policy-intensity table."""
	local = processed.loc[processed["jurisdiction_type"].eq("local")].copy()
	provinces = sorted(local["province"].dropna().unique())
	years = list(range(ANALYSIS_START.year, ANALYSIS_END.year + 1))
	base = pd.MultiIndex.from_product([provinces, years], names=["province", "publish_year"]).to_frame(index=False)

	aggregated = (
		local.groupby(["province", "publish_year"], dropna=False)
		.agg(
			srdi_policy_count=("policy_id", "size"),
			total_keyword_count=("keyword_count", "sum"),
			avg_keyword_count=("keyword_count", "mean"),
			title_contains_srdi_count=("title_contains_srdi", "sum"),
			abstract_contains_srdi_count=("abstract_contains_srdi", "sum"),
			title_or_abstract_contains_srdi_count=("title_or_abstract_contains_srdi", "sum"),
			missing_agency_count=("agency", lambda values: int(values.fillna("").str.strip().eq("").sum())),
			unique_agency_count=("agency", lambda values: int(values.fillna("").str.strip().replace("", pd.NA).dropna().nunique())),
		)
		.reset_index()
	)
	intensity = base.merge(aggregated, on=["province", "publish_year"], how="left")
	count_columns = [
		"srdi_policy_count",
		"total_keyword_count",
		"title_contains_srdi_count",
		"abstract_contains_srdi_count",
		"title_or_abstract_contains_srdi_count",
		"missing_agency_count",
		"unique_agency_count",
	]
	intensity[count_columns] = intensity[count_columns].fillna(0).astype("int64")
	intensity["avg_keyword_count"] = intensity["avg_keyword_count"].fillna(0.0)
	intensity["log_srdi_policy_count_plus1"] = np.log(intensity["srdi_policy_count"] + 1)
	return intensity[INTENSITY_COLUMNS].reset_index(drop=True)


def build_manual_processed_quality_report(
	raw: pd.DataFrame,
	processed: pd.DataFrame,
	intensity: pd.DataFrame,
) -> pd.DataFrame:
	"""Create a long-form QA report for manual SRDI processed v0."""
	normalized = normalize_manual_policy_workbook(raw)
	in_window = normalized["in_analysis_window"]
	xinjiang_mask = normalized["source_label_original"].isin(XINJIANG_SOURCE_LABELS)
	rows = [
		("source_records", len(normalized), "Rows in the manual workbook."),
		("processed_records", len(processed), "Rows retained in 2020-2025 processed v0."),
		("excluded_outside_analysis_window", int((~in_window).sum()), "Rows outside 2020-2025; currently 2026 records."),
		("missing_publish_dates", int(normalized["publish_date_parsed"].isna().sum()), "Rows with unparseable publication date."),
		("missing_source_urls", int(normalized["source_url"].eq("").sum()), "Rows without source URL."),
		("duplicate_source_urls", int(processed.duplicated("source_url").sum()), "Duplicate URLs in processed v0."),
		("missing_titles", int(processed["title"].eq("").sum()), "Rows without title in processed v0."),
		("missing_agency", int(processed["agency"].eq("").sum()), "Rows without agency in processed v0."),
		("missing_document_number", int(processed["document_number"].eq("").sum()), "Rows without document number in processed v0."),
		("missing_abstract", int(processed["abstract"].eq("").sum()), "Rows without abstract in processed v0."),
		("central_records", int(processed["jurisdiction_type"].eq("central").sum()), "Central records retained in processed v0."),
		("local_records", int(processed["jurisdiction_type"].eq("local").sum()), "Local records retained in processed v0."),
		("local_province_units", int(processed.loc[processed["jurisdiction_type"].eq("local"), "province"].nunique()), "Local province units after Xinjiang merge."),
		("intensity_records", len(intensity), "Balanced province-year rows."),
		("xinjiang_original_records", int(xinjiang_mask.sum()), "Rows from the two original Xinjiang source labels before date filtering."),
		("xinjiang_processed_records", int(processed["province"].eq("新疆").sum()), "Rows mapped to province=新疆 in processed v0."),
		("title_contains_srdi", int(processed["title_contains_srdi"].sum()), "Processed rows whose title contains 专精特新."),
		("abstract_contains_srdi", int(processed["abstract_contains_srdi"].sum()), "Processed rows whose abstract contains 专精特新."),
		("title_or_abstract_contains_srdi", int(processed["title_or_abstract_contains_srdi"].sum()), "Processed rows whose title or abstract contains 专精特新."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def write_manual_processed_v0(
	workbook_input: Path,
	processed_output: Path,
	intensity_output: Path,
	quality_output: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	"""Read the manual workbook and write processed records, intensity, and QA."""
	raw = pd.read_excel(workbook_input, sheet_name="tableData", dtype=str)
	processed = build_manual_policy_records_v0(raw)
	intensity = build_province_year_intensity_v0(processed)
	quality_report = build_manual_processed_quality_report(raw, processed, intensity)

	processed_output.parent.mkdir(parents=True, exist_ok=True)
	intensity_output.parent.mkdir(parents=True, exist_ok=True)
	quality_output.parent.mkdir(parents=True, exist_ok=True)
	processed.to_csv(processed_output, index=False)
	intensity.to_csv(intensity_output, index=False)
	quality_report.to_csv(quality_output, index=False)
	return processed, intensity, quality_report
