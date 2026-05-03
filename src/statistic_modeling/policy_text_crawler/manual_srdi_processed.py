"""Build processed datasets from the manually collected SRDI policy workbook."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS_START = pd.Timestamp("2020-01-01")
ANALYSIS_END = pd.Timestamp("2025-12-31")
ANALYSIS_V2_START = pd.Timestamp("2019-01-01")
ANALYSIS_V2_END = pd.Timestamp("2024-12-31")
SRDI_KEYWORD = "专精特新"
CENTRAL_SOURCE_LABEL = "国家"
XINJIANG_SOURCE_LABELS = {"新疆维吾尔自治区", "新疆生产建设兵团"}
CURRENT_FULLTEXT_SOURCE_SCHEMA_V2 = "current_fulltext_workbook_v1"
SUPPLEMENT_2019_SOURCE_SCHEMA_V2 = "supplement_2019_fulltext_v1"
JURISDICTION_OVERRIDES_COLUMNS = [
	"policy_id",
	"source_url",
	"source_label_original",
	"corrected_province",
	"correction_status",
	"correction_reason",
	"evidence",
]

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

FULLTEXT_RAW_COLUMNS = {
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
	"原文": "full_text",
}

SUPPLEMENT_2019_RAW_COLUMNS = {
	"序号": "source_row_number",
	"所属省份": "source_label_original",
	"地区名称": "region_name",
	"发文日期": "publish_date",
	"标题": "title",
	"文号": "document_number",
	"发文机构": "agency",
	"原文链接": "source_url",
	"原文文本": "full_text",
}

PROCESSED_POLICY_COLUMNS = [
	"policy_id",
	"province",
	"province_before_correction",
	"province_correction_status",
	"province_correction_reason",
	"province_correction_evidence",
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

PROCESSED_FULLTEXT_POLICY_COLUMNS = [
	"policy_id",
	"province",
	"province_before_correction",
	"province_correction_status",
	"province_correction_reason",
	"province_correction_evidence",
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
	"full_text",
	"full_text_len",
	"title_contains_srdi",
	"full_text_contains_srdi",
	"title_or_full_text_contains_srdi",
	"in_analysis_window",
	"review_status",
]

PROCESSED_FULLTEXT_POLICY_COLUMNS_V2 = [
	"policy_id",
	"province",
	"province_before_correction",
	"province_correction_status",
	"province_correction_reason",
	"province_correction_evidence",
	"source_label_original",
	"jurisdiction_type",
	"region_name",
	"publish_date",
	"publish_year",
	"keyword_hit",
	"keyword_count",
	"keyword_count_raw",
	"keyword_count_metadata",
	"keyword_count_source",
	"title",
	"document_number",
	"agency",
	"source_url",
	"full_text",
	"full_text_len",
	"full_text_missing",
	"full_text_fallback_for_model",
	"title_contains_srdi",
	"full_text_contains_srdi",
	"title_or_full_text_contains_srdi",
	"in_analysis_window",
	"review_status",
	"source_workbook",
	"source_schema_version",
	"needs_jurisdiction_review",
	"jurisdiction_review_reason",
	"jurisdiction_review_suggested_province",
	"jurisdiction_review_evidence",
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

INTENSITY_COLUMNS_V2 = [
	"province",
	"publish_year",
	"srdi_policy_count",
	"log_srdi_policy_count_plus1",
	"total_keyword_count",
	"avg_keyword_count",
	"title_contains_srdi_count",
	"full_text_contains_srdi_count",
	"title_or_full_text_contains_srdi_count",
	"missing_full_text_count",
	"fallback_full_text_for_model_count",
	"missing_agency_count",
	"unique_agency_count",
	"jurisdiction_review_candidate_count",
]

JURISDICTION_REVIEW_CANDIDATE_COLUMNS_V2 = [
	"policy_id",
	"source_workbook",
	"source_schema_version",
	"source_label_original",
	"province_before_correction",
	"province",
	"publish_date",
	"publish_year",
	"title",
	"agency",
	"source_url",
	"jurisdiction_review_reason",
	"jurisdiction_review_suggested_province",
	"jurisdiction_review_evidence",
]

PROVINCE_TITLE_PREFIXES = [
	("内蒙古自治区", "内蒙古自治区"),
	("广西壮族自治区", "广西壮族自治区"),
	("西藏自治区", "西藏自治区"),
	("宁夏回族自治区", "宁夏回族自治区"),
	("新疆生产建设兵团", "新疆"),
	("新疆维吾尔自治区", "新疆"),
	("黑龙江省", "黑龙江省"),
	("北京市", "北京市"),
	("天津市", "天津市"),
	("上海市", "上海市"),
	("重庆市", "重庆市"),
	("河北省", "河北省"),
	("山西省", "山西省"),
	("辽宁省", "辽宁省"),
	("吉林省", "吉林省"),
	("江苏省", "江苏省"),
	("浙江省", "浙江省"),
	("安徽省", "安徽省"),
	("福建省", "福建省"),
	("江西省", "江西省"),
	("山东省", "山东省"),
	("河南省", "河南省"),
	("湖北省", "湖北省"),
	("湖南省", "湖南省"),
	("广东省", "广东省"),
	("海南省", "海南省"),
	("四川省", "四川省"),
	("贵州省", "贵州省"),
	("云南省", "云南省"),
	("陕西省", "陕西省"),
	("甘肃省", "甘肃省"),
	("青海省", "青海省"),
	("内蒙古", "内蒙古自治区"),
	("广西", "广西壮族自治区"),
	("西藏", "西藏自治区"),
	("宁夏", "宁夏回族自治区"),
	("新疆", "新疆"),
	("黑龙江", "黑龙江省"),
	("北京", "北京市"),
	("天津", "天津市"),
	("上海", "上海市"),
	("重庆", "重庆市"),
	("河北", "河北省"),
	("山西", "山西省"),
	("辽宁", "辽宁省"),
	("吉林", "吉林省"),
	("江苏", "江苏省"),
	("浙江", "浙江省"),
	("安徽", "安徽省"),
	("福建", "福建省"),
	("江西", "江西省"),
	("山东", "山东省"),
	("河南", "河南省"),
	("湖北", "湖北省"),
	("湖南", "湖南省"),
	("广东", "广东省"),
	("海南", "海南省"),
	("四川", "四川省"),
	("贵州", "贵州省"),
	("云南", "云南省"),
	("陕西", "陕西省"),
	("甘肃", "甘肃省"),
	("青海", "青海省"),
]

CENTRAL_JURISDICTION_REVIEW_TERMS = [
	"国务院",
	"工业和信息化部",
	"财政部",
	"国家发展改革委",
	"国家知识产权局",
	"商务部",
	"科技部",
	"教育部",
	"中国人民银行",
	"国家市场监督管理总局",
	"市场监管总局",
	"国家广播电视总局",
	"国家体育总局",
	"国家标准化管理委员会",
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


def load_jurisdiction_overrides(path: Path | None) -> pd.DataFrame:
	"""Load auditable province overrides for reposted out-of-jurisdiction policies."""
	if path is None or not path.exists():
		return pd.DataFrame(columns=JURISDICTION_OVERRIDES_COLUMNS)
	overrides = pd.read_csv(path, dtype=str).fillna("")
	missing_columns = sorted(set(JURISDICTION_OVERRIDES_COLUMNS) - set(overrides.columns))
	if missing_columns:
		raise ValueError(f"manual SRDI jurisdiction overrides missing columns: {missing_columns}")
	overrides = overrides[JURISDICTION_OVERRIDES_COLUMNS].copy()
	if overrides["policy_id"].duplicated().any():
		duplicates = overrides.loc[overrides["policy_id"].duplicated(), "policy_id"].head(5).tolist()
		raise ValueError(f"manual SRDI jurisdiction overrides contain duplicate policy_id values: {duplicates}")
	return overrides


def apply_jurisdiction_overrides(records: pd.DataFrame, overrides: pd.DataFrame | None = None) -> pd.DataFrame:
	"""Apply reviewed province corrections while preserving source labels for audit."""
	records = records.copy()
	records["province_before_correction"] = records["province"]
	records["province_correction_status"] = "original"
	records["province_correction_reason"] = ""
	records["province_correction_evidence"] = ""

	if overrides is None or overrides.empty:
		return records

	override_lookup = overrides.set_index("policy_id")
	matched = records["policy_id"].isin(override_lookup.index)
	if not matched.any():
		return records

	for policy_id, override in override_lookup.iterrows():
		row_mask = records["policy_id"].eq(policy_id)
		if not row_mask.any():
			continue
		corrected_province = normalize_province(override["corrected_province"])
		records.loc[row_mask, "province"] = corrected_province
		records.loc[row_mask, "province_correction_status"] = override["correction_status"] or "corrected"
		records.loc[row_mask, "province_correction_reason"] = override["correction_reason"]
		records.loc[row_mask, "province_correction_evidence"] = override["evidence"]

	records["jurisdiction_type"] = records["province"].eq("central").map({True: "central", False: "local"})
	return records


def normalize_manual_policy_workbook(
	raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
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
	records = apply_jurisdiction_overrides(records, jurisdiction_overrides)
	records["title_contains_srdi"] = records["title"].str.contains(SRDI_KEYWORD, regex=False)
	records["abstract_contains_srdi"] = records["abstract"].str.contains(SRDI_KEYWORD, regex=False)
	records["title_or_abstract_contains_srdi"] = records["title_contains_srdi"] | records["abstract_contains_srdi"]
	records["review_status"] = "accepted"
	return records


def normalize_manual_fulltext_policy_workbook(
	raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Standardize the full-text manual workbook and derived audit flags."""
	missing_columns = sorted(set(FULLTEXT_RAW_COLUMNS) - set(raw.columns))
	if missing_columns:
		raise ValueError(f"manual SRDI full-text workbook missing columns: {missing_columns}")

	records = raw.rename(columns=FULLTEXT_RAW_COLUMNS).copy()
	for column in FULLTEXT_RAW_COLUMNS.values():
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
	records = apply_jurisdiction_overrides(records, jurisdiction_overrides)
	records["full_text_len"] = records["full_text"].str.len()
	records["title_contains_srdi"] = records["title"].str.contains(SRDI_KEYWORD, regex=False)
	records["full_text_contains_srdi"] = records["full_text"].str.contains(SRDI_KEYWORD, regex=False)
	records["title_or_full_text_contains_srdi"] = records["title_contains_srdi"] | records["full_text_contains_srdi"]
	records["review_status"] = "accepted"
	return records


def count_srdi_keyword(text: object) -> int:
	"""Count literal SRDI keyword occurrences in a text surface."""
	value = "" if pd.isna(text) else str(text)
	return value.count(SRDI_KEYWORD)


def derive_srdi_keyword_count(title: object, full_text: object) -> int:
	"""Derive the SRDI keyword count when workbook metadata is unavailable."""
	text_surface = f"{'' if pd.isna(title) else str(title)}\n{'' if pd.isna(full_text) else str(full_text)}"
	return count_srdi_keyword(text_surface)


def _clean_v2_text_columns(records: pd.DataFrame) -> pd.DataFrame:
	"""Trim v2 text-like columns after source-schema normalization."""
	records = records.copy()
	for column in [
		"source_row_number",
		"source_label_original",
		"region_name",
		"publish_date",
		"keyword_count_metadata",
		"keyword_count_raw",
		"title",
		"document_number",
		"agency",
		"source_url",
		"full_text",
		"source_workbook",
		"source_schema_version",
	]:
		if column in records:
			records[column] = records[column].fillna("").astype(str).str.strip()
	return records


def _standardize_current_fulltext_for_v2(raw: pd.DataFrame, source_workbook: str) -> pd.DataFrame:
	"""Normalize the current full-text workbook before applying the v2 window."""
	missing_columns = sorted(set(FULLTEXT_RAW_COLUMNS) - set(raw.columns))
	if missing_columns:
		raise ValueError(f"manual SRDI current full-text workbook missing columns: {missing_columns}")

	records = raw.rename(columns=FULLTEXT_RAW_COLUMNS).copy()
	records["source_workbook"] = source_workbook
	records["source_schema_version"] = CURRENT_FULLTEXT_SOURCE_SCHEMA_V2
	records = _clean_v2_text_columns(records)
	records["keyword_count"] = pd.to_numeric(records["keyword_count_raw"], errors="coerce").astype("Int64")
	derived_keyword_count = records.apply(
		lambda row: derive_srdi_keyword_count(row["title"], row["full_text"]),
		axis=1,
	)
	needs_derived_count = records["keyword_count"].isna()
	records.loc[needs_derived_count, "keyword_count"] = derived_keyword_count.loc[needs_derived_count].astype("Int64")
	records["keyword_count_source"] = needs_derived_count.map({True: "derived_from_text", False: "workbook_metadata"})
	return records


def _standardize_2019_supplement_for_v2(raw: pd.DataFrame, source_workbook: str) -> pd.DataFrame:
	"""Normalize the 2019 supplementary full-text workbook to the v2 schema."""
	missing_columns = sorted(set(SUPPLEMENT_2019_RAW_COLUMNS) - set(raw.columns))
	if missing_columns:
		raise ValueError(f"manual SRDI 2019 supplementary workbook missing columns: {missing_columns}")

	records = raw.rename(columns=SUPPLEMENT_2019_RAW_COLUMNS).copy()
	records["keyword_count_metadata"] = ""
	records["keyword_count_raw"] = ""
	records["source_workbook"] = source_workbook
	records["source_schema_version"] = SUPPLEMENT_2019_SOURCE_SCHEMA_V2
	records = _clean_v2_text_columns(records)
	records["keyword_count"] = records.apply(
		lambda row: derive_srdi_keyword_count(row["title"], row["full_text"]),
		axis=1,
	).astype("Int64")
	records["keyword_count_source"] = "derived_from_text"
	return records


def infer_title_prefix_province(title: object) -> str:
	"""Infer a province from a leading title prefix for audit-only review."""
	text = "" if pd.isna(title) else str(title).strip()
	for prefix, province in PROVINCE_TITLE_PREFIXES:
		if text.startswith(prefix):
			return normalize_province(province)
	return ""


def infer_central_review_terms(title: object, agency: object) -> str:
	"""Return central-agency terms that make a local-source record review-worthy."""
	text = f"{'' if pd.isna(title) else str(title)}\n{'' if pd.isna(agency) else str(agency)}"
	matched = [term for term in CENTRAL_JURISDICTION_REVIEW_TERMS if term in text]
	return ";".join(matched)


def add_v2_jurisdiction_review_flags(records: pd.DataFrame) -> pd.DataFrame:
	"""Flag 2019 supplement rows that may use source site rather than policy jurisdiction."""
	records = records.copy()
	reasons: list[str] = []
	suggestions: list[str] = []
	evidence_values: list[str] = []
	for _, row in records.iterrows():
		row_reasons: list[str] = []
		row_suggestions: list[str] = []
		row_evidence: list[str] = []
		is_2019_supplement = row.get("source_schema_version", "") == SUPPLEMENT_2019_SOURCE_SCHEMA_V2
		is_local = row.get("jurisdiction_type", "") == "local"
		is_unreviewed_original = row.get("province_correction_status", "") == "original"
		if is_2019_supplement and is_local and is_unreviewed_original:
			title_prefix_province = infer_title_prefix_province(row.get("title", ""))
			if title_prefix_province and title_prefix_province != row.get("province", ""):
				row_reasons.append("title_prefix_suggests_other_jurisdiction")
				row_suggestions.append(title_prefix_province)
				row_evidence.append(f"title_prefix={title_prefix_province}")

			central_terms = infer_central_review_terms(row.get("title", ""), row.get("agency", ""))
			if central_terms:
				row_reasons.append("local_source_mentions_central_ministry")
				row_suggestions.append("central")
				row_evidence.append(f"central_terms={central_terms}")

		reasons.append(";".join(row_reasons))
		suggestions.append(";".join(dict.fromkeys(row_suggestions)))
		evidence_values.append(";".join(row_evidence))

	records["jurisdiction_review_reason"] = reasons
	records["jurisdiction_review_suggested_province"] = suggestions
	records["jurisdiction_review_evidence"] = evidence_values
	records["needs_jurisdiction_review"] = records["jurisdiction_review_reason"].ne("")
	return records


def normalize_manual_fulltext_policy_workbooks_v2(
	current_fulltext_raw: pd.DataFrame,
	supplement_2019_raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
	current_source_workbook: str = "manual_policy_all_keyword_srdi_with_full_text.xlsx",
	supplement_source_workbook: str = "manual_policy_all_keyword_srdi_2019_supplementary.xlsx",
) -> pd.DataFrame:
	"""Build a combined full-text v2 source table before date-window filtering."""
	current_records = _standardize_current_fulltext_for_v2(current_fulltext_raw, current_source_workbook)
	supplement_records = _standardize_2019_supplement_for_v2(supplement_2019_raw, supplement_source_workbook)
	records = pd.concat([current_records, supplement_records], ignore_index=True, sort=False)

	records["publish_date_parsed"] = pd.to_datetime(records["publish_date"], errors="coerce")
	records["publish_date"] = records["publish_date_parsed"].dt.date.astype("string")
	records["publish_year"] = records["publish_date_parsed"].dt.year.astype("Int64")
	current_window = (
		records["source_schema_version"].eq(CURRENT_FULLTEXT_SOURCE_SCHEMA_V2)
		& records["publish_date_parsed"].between(
			pd.Timestamp("2020-01-01"),
			ANALYSIS_V2_END,
			inclusive="both",
		)
	)
	supplement_window = (
		records["source_schema_version"].eq(SUPPLEMENT_2019_SOURCE_SCHEMA_V2)
		& records["publish_date_parsed"].between(
			ANALYSIS_V2_START,
			pd.Timestamp("2019-12-31"),
			inclusive="both",
		)
	)
	records["in_analysis_window"] = current_window | supplement_window
	records["province"] = records["source_label_original"].map(normalize_province)
	records["jurisdiction_type"] = records["province"].eq("central").map({True: "central", False: "local"})
	records["keyword_hit"] = SRDI_KEYWORD
	records["policy_id"] = records["source_url"].map(stable_policy_id)
	records = apply_jurisdiction_overrides(records, jurisdiction_overrides)
	records["full_text_len"] = records["full_text"].fillna("").astype(str).str.len()
	records["full_text_missing"] = records["full_text"].fillna("").astype(str).str.strip().eq("")
	records["full_text_fallback_for_model"] = records["full_text_missing"]
	records["title_contains_srdi"] = records["title"].str.contains(SRDI_KEYWORD, regex=False)
	records["full_text_contains_srdi"] = records["full_text"].str.contains(SRDI_KEYWORD, regex=False)
	records["title_or_full_text_contains_srdi"] = records["title_contains_srdi"] | records["full_text_contains_srdi"]
	records["review_status"] = "accepted"
	records = add_v2_jurisdiction_review_flags(records)
	return records


def build_manual_fulltext_policy_records_v2(
	current_fulltext_raw: pd.DataFrame,
	supplement_2019_raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
	current_source_workbook: str = "manual_policy_all_keyword_srdi_with_full_text.xlsx",
	supplement_source_workbook: str = "manual_policy_all_keyword_srdi_2019_supplementary.xlsx",
) -> pd.DataFrame:
	"""Build v2 full-text policy records for the 2019-2024 policy-side corpus."""
	records = normalize_manual_fulltext_policy_workbooks_v2(
		current_fulltext_raw,
		supplement_2019_raw,
		jurisdiction_overrides,
		current_source_workbook,
		supplement_source_workbook,
	)
	processed = records.loc[records["in_analysis_window"]].copy()
	return processed[PROCESSED_FULLTEXT_POLICY_COLUMNS_V2].reset_index(drop=True)


def build_manual_policy_records_v0(
	raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Build analysis-window processed policy records from the manual workbook."""
	records = normalize_manual_policy_workbook(raw, jurisdiction_overrides)
	processed = records.loc[records["in_analysis_window"]].copy()
	return processed[PROCESSED_POLICY_COLUMNS].reset_index(drop=True)


def build_manual_fulltext_policy_records_v1(
	raw: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Build analysis-window full-text policy records from the manual workbook."""
	records = normalize_manual_fulltext_policy_workbook(raw, jurisdiction_overrides)
	processed = records.loc[records["in_analysis_window"]].copy()
	return processed[PROCESSED_FULLTEXT_POLICY_COLUMNS].reset_index(drop=True)


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


def build_province_year_intensity_v2(processed: pd.DataFrame) -> pd.DataFrame:
	"""Build a balanced 2019-2024 province-year SRDI full-text v2 count table."""
	local = processed.loc[processed["jurisdiction_type"].eq("local")].copy()
	provinces = sorted(local["province"].dropna().unique())
	years = list(range(ANALYSIS_V2_START.year, ANALYSIS_V2_END.year + 1))
	base = pd.MultiIndex.from_product([provinces, years], names=["province", "publish_year"]).to_frame(index=False)

	aggregated = (
		local.groupby(["province", "publish_year"], dropna=False)
		.agg(
			srdi_policy_count=("policy_id", "size"),
			total_keyword_count=("keyword_count", "sum"),
			avg_keyword_count=("keyword_count", "mean"),
			title_contains_srdi_count=("title_contains_srdi", "sum"),
			full_text_contains_srdi_count=("full_text_contains_srdi", "sum"),
			title_or_full_text_contains_srdi_count=("title_or_full_text_contains_srdi", "sum"),
			missing_full_text_count=("full_text_missing", "sum"),
			fallback_full_text_for_model_count=("full_text_fallback_for_model", "sum"),
			missing_agency_count=("agency", lambda values: int(values.fillna("").str.strip().eq("").sum())),
			unique_agency_count=("agency", lambda values: int(values.fillna("").str.strip().replace("", pd.NA).dropna().nunique())),
			jurisdiction_review_candidate_count=("needs_jurisdiction_review", "sum"),
		)
		.reset_index()
	)
	intensity = base.merge(aggregated, on=["province", "publish_year"], how="left")
	count_columns = [
		"srdi_policy_count",
		"total_keyword_count",
		"title_contains_srdi_count",
		"full_text_contains_srdi_count",
		"title_or_full_text_contains_srdi_count",
		"missing_full_text_count",
		"fallback_full_text_for_model_count",
		"missing_agency_count",
		"unique_agency_count",
		"jurisdiction_review_candidate_count",
	]
	intensity[count_columns] = intensity[count_columns].fillna(0).astype("int64")
	intensity["avg_keyword_count"] = intensity["avg_keyword_count"].fillna(0.0)
	intensity["log_srdi_policy_count_plus1"] = np.log(intensity["srdi_policy_count"] + 1)
	return intensity[INTENSITY_COLUMNS_V2].reset_index(drop=True)


def build_v2_jurisdiction_review_candidates(processed: pd.DataFrame) -> pd.DataFrame:
	"""Return 2019 supplement records that need policy-jurisdiction review."""
	candidates = processed.loc[processed["needs_jurisdiction_review"]].copy()
	if candidates.empty:
		return pd.DataFrame(columns=JURISDICTION_REVIEW_CANDIDATE_COLUMNS_V2)
	return candidates[JURISDICTION_REVIEW_CANDIDATE_COLUMNS_V2].sort_values(
		["publish_year", "source_label_original", "title"],
		ignore_index=True,
	)


def build_manual_processed_quality_report(
	raw: pd.DataFrame,
	processed: pd.DataFrame,
	intensity: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Create a long-form QA report for manual SRDI processed v0."""
	normalized = normalize_manual_policy_workbook(raw, jurisdiction_overrides)
	in_window = normalized["in_analysis_window"]
	xinjiang_mask = normalized["source_label_original"].isin(XINJIANG_SOURCE_LABELS)
	corrected = processed["province_correction_status"].eq("corrected")
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
		("province_corrected_records", int(corrected.sum()), "Rows with reviewed source-label jurisdiction corrections."),
		("title_contains_srdi", int(processed["title_contains_srdi"].sum()), "Processed rows whose title contains 专精特新."),
		("abstract_contains_srdi", int(processed["abstract_contains_srdi"].sum()), "Processed rows whose abstract contains 专精特新."),
		("title_or_abstract_contains_srdi", int(processed["title_or_abstract_contains_srdi"].sum()), "Processed rows whose title or abstract contains 专精特新."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def build_manual_fulltext_processed_quality_report(
	raw: pd.DataFrame,
	processed: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Create a long-form QA report for manual SRDI full-text processed v1."""
	normalized = normalize_manual_fulltext_policy_workbook(raw, jurisdiction_overrides)
	in_window = normalized["in_analysis_window"]
	xinjiang_mask = normalized["source_label_original"].isin(XINJIANG_SOURCE_LABELS)
	corrected = processed["province_correction_status"].eq("corrected")
	rows = [
		("source_records", len(normalized), "Rows in the full-text manual workbook."),
		("processed_records", len(processed), "Rows retained in 2020-2025 processed full-text v1."),
		("excluded_outside_analysis_window", int((~in_window).sum()), "Rows outside 2020-2025; currently 2026 records."),
		("missing_publish_dates", int(normalized["publish_date_parsed"].isna().sum()), "Rows with unparseable publication date."),
		("missing_source_urls", int(normalized["source_url"].eq("").sum()), "Rows without source URL."),
		("duplicate_source_urls", int(processed.duplicated("source_url").sum()), "Duplicate URLs in processed full-text v1."),
		("missing_titles", int(processed["title"].eq("").sum()), "Rows without title in processed full-text v1."),
		("missing_agency", int(processed["agency"].eq("").sum()), "Rows without agency in processed full-text v1."),
		("missing_document_number", int(processed["document_number"].eq("").sum()), "Rows without document number in processed full-text v1."),
		("missing_full_text", int(processed["full_text"].eq("").sum()), "Rows without full text in processed full-text v1."),
		("central_records", int(processed["jurisdiction_type"].eq("central").sum()), "Central records retained in processed full-text v1."),
		("local_records", int(processed["jurisdiction_type"].eq("local").sum()), "Local records retained in processed full-text v1."),
		("local_province_units", int(processed.loc[processed["jurisdiction_type"].eq("local"), "province"].nunique()), "Local province units after Xinjiang merge."),
		("xinjiang_original_records", int(xinjiang_mask.sum()), "Rows from the two original Xinjiang source labels before date filtering."),
		("xinjiang_processed_records", int(processed["province"].eq("新疆").sum()), "Rows mapped to province=新疆 in processed full-text v1."),
		("province_corrected_records", int(corrected.sum()), "Rows with reviewed source-label jurisdiction corrections."),
		("title_contains_srdi", int(processed["title_contains_srdi"].sum()), "Processed rows whose title contains 专精特新."),
		("full_text_contains_srdi", int(processed["full_text_contains_srdi"].sum()), "Processed rows whose full text contains 专精特新."),
		("title_or_full_text_contains_srdi", int(processed["title_or_full_text_contains_srdi"].sum()), "Processed rows whose title or full text contains 专精特新."),
		("min_full_text_len", int(processed["full_text_len"].min()), "Minimum full-text character length."),
		("median_full_text_len", float(processed["full_text_len"].median()), "Median full-text character length."),
		("max_full_text_len", int(processed["full_text_len"].max()), "Maximum full-text character length."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def build_manual_fulltext_processed_quality_report_v2(
	current_fulltext_raw: pd.DataFrame,
	supplement_2019_raw: pd.DataFrame,
	processed: pd.DataFrame,
	intensity: pd.DataFrame,
	jurisdiction_candidates: pd.DataFrame,
	jurisdiction_overrides: pd.DataFrame | None = None,
) -> pd.DataFrame:
	"""Create a long-form QA report for the 2019-2024 full-text v2 corpus."""
	normalized = normalize_manual_fulltext_policy_workbooks_v2(
		current_fulltext_raw,
		supplement_2019_raw,
		jurisdiction_overrides,
	)
	in_window = normalized["in_analysis_window"]
	corrected = processed["province_correction_status"].eq("corrected")
	reviewed_original = processed["province_correction_status"].eq("reviewed_original")
	missing_full_text_policy_ids = ";".join(processed.loc[processed["full_text_missing"], "policy_id"].tolist())
	rows = [
		("analysis_window", "2019-01-01 through 2024-12-31", "Policy-side v2 analysis window."),
		("current_fulltext_source_records", len(current_fulltext_raw), "Rows in the current full-text workbook."),
		("supplement_2019_source_records", len(supplement_2019_raw), "Rows in the 2019 supplementary workbook."),
		("combined_source_records", len(normalized), "Rows after stacking current full-text and 2019 supplement sources."),
		("processed_records", len(processed), "Rows retained in 2019-2024 processed full-text v2."),
		("processed_2019_records", int(processed["publish_year"].eq(2019).sum()), "Rows retained from the 2019 supplement."),
		("processed_2020_2024_records", int(processed["publish_year"].between(2020, 2024).sum()), "Rows retained from current full-text workbook years 2020-2024."),
		("excluded_outside_analysis_window", int((~in_window).sum()), "Rows outside 2019-2024, mainly current workbook 2025-2026 records."),
		("excluded_2025_records", int(normalized["publish_year"].eq(2025).sum()), "Rows dated 2025 and excluded from v2."),
		("excluded_2026_records", int(normalized["publish_year"].eq(2026).sum()), "Rows dated 2026 and excluded from v2."),
		("missing_publish_dates", int(normalized["publish_date_parsed"].isna().sum()), "Rows with unparseable publication date."),
		("missing_source_urls", int(normalized["source_url"].eq("").sum()), "Rows without source URL."),
		("duplicate_source_urls", int(processed.duplicated("source_url").sum()), "Duplicate URLs in processed full-text v2."),
		("duplicate_policy_ids", int(processed.duplicated("policy_id").sum()), "Duplicate policy IDs in processed full-text v2."),
		("missing_titles", int(processed["title"].eq("").sum()), "Rows without title in processed full-text v2."),
		("missing_agency", int(processed["agency"].eq("").sum()), "Rows without agency in processed full-text v2."),
		("missing_document_number", int(processed["document_number"].eq("").sum()), "Rows without document number in processed full-text v2."),
		("missing_full_text", int(processed["full_text_missing"].sum()), "Rows without full text; retained with model-input fallback flag."),
		("missing_full_text_policy_ids", missing_full_text_policy_ids, "Policy IDs for rows without full text."),
		("full_text_fallback_for_model_rows", int(processed["full_text_fallback_for_model"].sum()), "Rows that later model-input code should build from metadata/title fallback."),
		("central_records", int(processed["jurisdiction_type"].eq("central").sum()), "Central records retained in row-level processed full-text v2."),
		("local_records", int(processed["jurisdiction_type"].eq("local").sum()), "Local records retained in row-level processed full-text v2."),
		("local_province_units", int(processed.loc[processed["jurisdiction_type"].eq("local"), "province"].nunique()), "Local province units after Xinjiang merge."),
		("intensity_records", len(intensity), "Balanced local province-year rows for 2019-2024."),
		("keyword_count_workbook_metadata_records", int(processed["keyword_count_source"].eq("workbook_metadata").sum()), "Rows using workbook keyword count metadata."),
		("keyword_count_derived_from_text_records", int(processed["keyword_count_source"].eq("derived_from_text").sum()), "Rows using derived title/full-text keyword counts."),
		("province_corrected_records", int(corrected.sum()), "Rows with reviewed source-label jurisdiction corrections applied."),
		("province_reviewed_original_records", int(reviewed_original.sum()), "Rows reviewed and kept in their original source-label jurisdiction."),
		("jurisdiction_review_candidate_records", len(jurisdiction_candidates), "2019 supplement rows flagged for jurisdiction review before final paper freeze."),
		("title_contains_srdi", int(processed["title_contains_srdi"].sum()), "Processed rows whose title contains 专精特新."),
		("full_text_contains_srdi", int(processed["full_text_contains_srdi"].sum()), "Processed rows whose full text contains 专精特新."),
		("title_or_full_text_contains_srdi", int(processed["title_or_full_text_contains_srdi"].sum()), "Processed rows whose title or full text contains 专精特新."),
		("min_full_text_len", int(processed["full_text_len"].min()), "Minimum full-text character length."),
		("median_full_text_len", float(processed["full_text_len"].median()), "Median full-text character length."),
		("max_full_text_len", int(processed["full_text_len"].max()), "Maximum full-text character length."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def build_2019_supplement_quality_report_v2(
	supplement_2019_raw: pd.DataFrame,
	processed: pd.DataFrame,
	jurisdiction_candidates: pd.DataFrame,
) -> pd.DataFrame:
	"""Create source-specific QA for the 2019 supplementary workbook."""
	supplement = processed.loc[processed["source_schema_version"].eq(SUPPLEMENT_2019_SOURCE_SCHEMA_V2)].copy()
	raw_dates = pd.to_datetime(supplement_2019_raw["发文日期"], errors="coerce")
	missing_full_text_policy_ids = ";".join(supplement.loc[supplement["full_text_missing"], "policy_id"].tolist())
	rows = [
		("source_records", len(supplement_2019_raw), "Rows in the 2019 supplementary workbook."),
		("processed_records", len(supplement), "2019 supplement rows retained in the v2 analysis window."),
		("date_min", raw_dates.min().date().isoformat() if raw_dates.notna().any() else "", "Minimum source publication date."),
		("date_max", raw_dates.max().date().isoformat() if raw_dates.notna().any() else "", "Maximum source publication date."),
		("missing_publish_dates", int(raw_dates.isna().sum()), "Rows with unparseable publication date."),
		("source_url_unique", bool(supplement_2019_raw["原文链接"].is_unique), "Whether 2019 source URLs are unique."),
		("duplicate_source_urls", int(supplement_2019_raw["原文链接"].duplicated().sum()), "Duplicate source URLs in the 2019 source workbook."),
		("duplicate_titles", int(supplement_2019_raw["标题"].duplicated().sum()), "Duplicate policy titles in the 2019 source workbook."),
		("missing_full_text", int(supplement["full_text_missing"].sum()), "2019 rows without full text."),
		("missing_full_text_policy_ids", missing_full_text_policy_ids, "2019 policy IDs for rows without full text."),
		("short_full_text_lt_100", int(supplement["full_text_len"].lt(100).sum()), "2019 rows with full-text length below 100 characters."),
		("short_full_text_lt_300", int(supplement["full_text_len"].lt(300).sum()), "2019 rows with full-text length below 300 characters."),
		("central_records", int(supplement["jurisdiction_type"].eq("central").sum()), "2019 central records."),
		("local_records", int(supplement["jurisdiction_type"].eq("local").sum()), "2019 local-source records."),
		("source_label_units", int(supplement["source_label_original"].nunique()), "Original 2019 source-label units."),
		("title_contains_srdi", int(supplement["title_contains_srdi"].sum()), "2019 rows whose title contains 专精特新."),
		("full_text_contains_srdi", int(supplement["full_text_contains_srdi"].sum()), "2019 rows whose full text contains 专精特新."),
		("title_or_full_text_contains_srdi", int(supplement["title_or_full_text_contains_srdi"].sum()), "2019 rows whose title or full text contains 专精特新."),
		("keyword_count_derived_from_text_records", int(supplement["keyword_count_source"].eq("derived_from_text").sum()), "2019 rows with keyword_count derived from title/full text."),
		("jurisdiction_review_candidate_records", len(jurisdiction_candidates), "2019 rows flagged for later jurisdiction review."),
	]
	return pd.DataFrame(rows, columns=["metric", "value", "note"])


def write_manual_processed_v0(
	workbook_input: Path,
	processed_output: Path,
	intensity_output: Path,
	quality_output: Path,
	jurisdiction_overrides_input: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	"""Read the manual workbook and write processed records, intensity, and QA."""
	raw = pd.read_excel(workbook_input, sheet_name="tableData", dtype=str)
	jurisdiction_overrides = load_jurisdiction_overrides(jurisdiction_overrides_input)
	processed = build_manual_policy_records_v0(raw, jurisdiction_overrides)
	intensity = build_province_year_intensity_v0(processed)
	quality_report = build_manual_processed_quality_report(raw, processed, intensity, jurisdiction_overrides)

	processed_output.parent.mkdir(parents=True, exist_ok=True)
	intensity_output.parent.mkdir(parents=True, exist_ok=True)
	quality_output.parent.mkdir(parents=True, exist_ok=True)
	processed.to_csv(processed_output, index=False)
	intensity.to_csv(intensity_output, index=False)
	quality_report.to_csv(quality_output, index=False)
	return processed, intensity, quality_report


def write_manual_fulltext_processed_v1(
	workbook_input: Path,
	processed_output: Path,
	quality_output: Path,
	jurisdiction_overrides_input: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
	"""Read the full-text workbook and write processed records plus QA."""
	raw = pd.read_excel(workbook_input, sheet_name="tableData", dtype=str)
	jurisdiction_overrides = load_jurisdiction_overrides(jurisdiction_overrides_input)
	processed = build_manual_fulltext_policy_records_v1(raw, jurisdiction_overrides)
	quality_report = build_manual_fulltext_processed_quality_report(raw, processed, jurisdiction_overrides)

	processed_output.parent.mkdir(parents=True, exist_ok=True)
	quality_output.parent.mkdir(parents=True, exist_ok=True)
	processed.to_csv(processed_output, index=False)
	quality_report.to_csv(quality_output, index=False)
	return processed, quality_report


def write_manual_fulltext_processed_v2(
	current_workbook_input: Path,
	supplement_2019_input: Path,
	processed_output: Path,
	intensity_output: Path,
	quality_output: Path,
	supplement_quality_output: Path,
	jurisdiction_candidates_output: Path,
	jurisdiction_overrides_input: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
	"""Read v2 full-text sources and write the 2019-2024 corpus, count panel, and QA."""
	current_raw = pd.read_excel(current_workbook_input, sheet_name="tableData", dtype=str)
	supplement_2019_raw = pd.read_excel(supplement_2019_input, sheet_name="tableData", dtype=str)
	jurisdiction_overrides = load_jurisdiction_overrides(jurisdiction_overrides_input)
	processed = build_manual_fulltext_policy_records_v2(
		current_raw,
		supplement_2019_raw,
		jurisdiction_overrides,
		current_workbook_input.name,
		supplement_2019_input.name,
	)
	if processed.duplicated("source_url").any():
		duplicates = processed.loc[processed.duplicated("source_url"), "source_url"].head(10).tolist()
		raise ValueError(f"manual SRDI full-text v2 contains duplicate source_url values: {duplicates}")
	if processed.duplicated("policy_id").any():
		duplicates = processed.loc[processed.duplicated("policy_id"), "policy_id"].head(10).tolist()
		raise ValueError(f"manual SRDI full-text v2 contains duplicate policy_id values: {duplicates}")

	intensity = build_province_year_intensity_v2(processed)
	jurisdiction_candidates = build_v2_jurisdiction_review_candidates(processed)
	quality_report = build_manual_fulltext_processed_quality_report_v2(
		current_raw,
		supplement_2019_raw,
		processed,
		intensity,
		jurisdiction_candidates,
		jurisdiction_overrides,
	)
	supplement_quality_report = build_2019_supplement_quality_report_v2(
		supplement_2019_raw,
		processed,
		jurisdiction_candidates,
	)

	for path, frame in [
		(processed_output, processed),
		(intensity_output, intensity),
		(quality_output, quality_report),
		(supplement_quality_output, supplement_quality_report),
		(jurisdiction_candidates_output, jurisdiction_candidates),
	]:
		path.parent.mkdir(parents=True, exist_ok=True)
		frame.to_csv(path, index=False)
	return processed, intensity, quality_report, supplement_quality_report, jurisdiction_candidates
