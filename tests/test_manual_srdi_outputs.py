from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_manual_srdi_text_mining_outputs_are_consistent() -> None:
	row_features = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_text_features_v0.csv")
	province_year_features = pd.read_csv(ROOT / "data" / "processed" / "province_year_srdi_text_features_v0.csv")
	quality_report = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_text_mining_v0_quality_report.csv").set_index("metric")
	dictionary = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_v0.csv")
	dictionary_coverage = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_v0.csv")
	revision_effect = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_dictionary_revision_effect_v0.csv").set_index("metric")
	keyword_quality = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_keyword_quality_check_v0.csv")
	no_hit_records = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_v0.csv")
	no_hit_sample = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_review_sample_v0.csv")

	assert len(row_features) == 4475
	assert len(province_year_features) == 186
	assert row_features["policy_id"].is_unique
	assert province_year_features["province"].nunique() == 31
	assert set(province_year_features["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert {"supply", "demand", "environment"} == set(dictionary["category"])
	assert len(dictionary_coverage) == 85
	assert (dictionary_coverage["records_hit"] > 0).all()
	assert revision_effect.loc["policy_records_without_tool_hit", "delta"] == -81
	assert len(keyword_quality) == 85
	assert keyword_quality["needs_review"].sum() == 50
	assert len(no_hit_records) == 271
	assert len(no_hit_sample) == 30
	assert quality_report.loc["row_feature_records", "value"] == 4475
	assert quality_report.loc["province_year_feature_records", "value"] == 186
	assert quality_report.loc["no_tool_hit_review_sample_records", "value"] == 30
	assert quality_report.loc["zero_coverage_terms", "value"] == 0


def test_manual_srdi_fulltext_outputs_are_consistent() -> None:
	processed = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv")
	row_features = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv")
	province_year_features = pd.read_csv(ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv")
	processed_quality = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_processed_fulltext_v1_quality_report.csv").set_index("metric")
	text_quality = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_text_mining_fulltext_v1_quality_report.csv").set_index("metric")
	dictionary = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_fulltext_v1.csv")
	dictionary_coverage = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv")
	no_hit_records = pd.read_csv(ROOT / "outputs" / "manual_policy_srdi_no_tool_hit_records_fulltext_v1.csv")

	assert len(processed) == 4475
	assert len(row_features) == 4475
	assert len(province_year_features) == 186
	assert processed["source_url"].is_unique
	assert row_features["policy_id"].is_unique
	assert processed["full_text"].fillna("").str.strip().ne("").all()
	assert processed_quality.loc["missing_full_text", "value"] == 0
	assert processed_quality.loc["full_text_contains_srdi", "value"] == 4475
	assert set(dictionary["category"]) == {"supply", "demand", "environment"}
	assert len(dictionary_coverage) == 85
	assert (dictionary_coverage["records_hit"] > 0).all()
	assert len(no_hit_records) == 2
	assert text_quality.loc["row_feature_records", "value"] == 4475
	assert text_quality.loc["province_year_feature_records", "value"] == 186
	assert text_quality.loc["policy_records_without_tool_hit", "value"] == 2
	assert text_quality.loc["high_coverage_terms_gte_25pct_records", "value"] == 41


def test_manual_srdi_text_measure_comparison_outputs_are_consistent() -> None:
	summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_text_measure_comparison_summary_v1.csv").set_index("metric")
	row_transitions = pd.read_csv(ROOT / "outputs" / "manual_srdi_text_measure_row_transitions_v1.csv")
	correlations = pd.read_csv(ROOT / "outputs" / "manual_srdi_text_measure_province_year_correlations_v1.csv")
	high_coverage_terms = pd.read_csv(ROOT / "outputs" / "manual_srdi_text_measure_fulltext_high_coverage_terms_v1.csv")
	recommendation = pd.read_csv(ROOT / "outputs" / "manual_srdi_text_measure_recommendation_v1.csv")

	assert summary.loc["policy_records_compared", "value"] == 4475
	assert summary.loc["v0_no_tool_hit_records", "value"] == 271
	assert summary.loc["v1_no_tool_hit_records", "value"] == 2
	assert summary.loc["v0_no_hit_recovered_by_v1", "value"] == 269
	assert len(row_transitions) == 16
	assert set(correlations["variable"]) == {
		"supply_tool_policy_count",
		"demand_tool_policy_count",
		"environment_tool_policy_count",
		"supply_tool_policy_share",
		"demand_tool_policy_share",
		"environment_tool_policy_share",
		"avg_tool_category_count",
	}
	assert len(high_coverage_terms) == 41
	assert recommendation.loc[recommendation["decision_area"].eq("main_text_measure"), "recommendation"].str.contains("full-text v1").item()


def test_manual_srdi_fulltext_descriptive_outputs_are_consistent() -> None:
	year_trend = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_year_trend.csv")
	province_distribution = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_province_distribution.csv")
	tool_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_tool_category_summary.csv")
	tool_shares_by_year = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_tool_shares_by_year.csv")
	heatmap_matrix = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_policy_intensity_heatmap_matrix.csv", index_col=0)
	tool_share_by_province = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_tool_share_by_province.csv")
	central_local = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_central_local_comparison.csv")
	no_hit_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_no_hit_summary.csv")
	high_coverage_terms = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_desc_high_coverage_terms.csv")

	assert year_trend["publish_year"].tolist() == [2020, 2021, 2022, 2023, 2024, 2025]
	assert len(province_distribution) == 31
	assert set(tool_summary["tool_category"]) == {"supply", "demand", "environment", "any_tool"}
	assert len(tool_shares_by_year) == 6
	assert heatmap_matrix.shape == (31, 6)
	assert len(tool_share_by_province) == 31
	assert sorted(central_local["jurisdiction_type"].tolist()) == ["central", "local"]
	assert no_hit_summary.loc[no_hit_summary["summary_type"].eq("year"), "no_tool_policy_count"].sum() == 2
	assert len(high_coverage_terms) == 41


def test_manual_srdi_fulltext_keyword_quality_outputs_are_consistent() -> None:
	summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_summary_v1.csv").set_index("metric")
	term_flags = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_term_flags_v1.csv")
	category_overlap = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_category_overlap_v1.csv").set_index("group")
	category_comparison = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_category_comparison_v1.csv").set_index("category")
	interpretation_notes = pd.read_csv(ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_interpretation_notes_v1.csv")

	assert summary.loc["dictionary_terms", "value"] == 85
	assert summary.loc["saturated_terms_gte_80pct", "value"] == 2
	assert summary.loc["high_coverage_terms_gte_50pct", "value"] == 15
	assert summary.loc["moderate_plus_terms_gte_25pct", "value"] == 41
	assert len(term_flags) == 85
	assert term_flags["interpretation_role"].eq("broad_intensity_signal").sum() == 15
	assert category_overlap.loc["no_tool", "records"] == 2
	assert category_overlap.loc["all_three_categories", "records"] == 3924
	assert category_comparison.loc["supply", "record_hit_share"] > 0.99
	assert category_comparison.loc["environment", "record_hit_share"] > 0.98
	assert category_comparison.loc["demand", "record_hit_share"] > 0.88
	assert set(interpretation_notes["topic"]) == {
		"why_supply_environment_near_any",
		"why_demand_rises",
		"very_high_coverage_terms",
		"modeling_implication",
	}
