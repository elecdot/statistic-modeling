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


def test_manual_srdi_label_rule_keywords_and_round1_sample_are_consistent() -> None:
	rules = pd.read_csv(ROOT / "configs" / "manual_srdi_label_rule_keywords_v1.csv")
	label_docs = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_label_docs_v1.csv")
	sampling_frame = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_label_sampling_frame_v1.csv")
	round1_sample = pd.read_csv(ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_sample_round1_v1.csv")
	pool_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_label_sampling_pool_summary_v1.csv")
	manifest = pd.read_csv(ROOT / "data" / "source-manifest.csv")

	assert len(rules) == 106
	assert set(rules["rule_role"]) == {"recall", "discriminative", "other_signal"}
	assert set(rules["category"]) == {"supply", "demand", "environment", "other"}
	assert {"broad", "medium", "specific"}.issuperset(set(rules["specificity"]))

	assert len(label_docs) == 4475
	assert len(sampling_frame) == 4475
	assert len(round1_sample) == 800
	assert round1_sample["doc_id"].is_unique
	assert label_docs["doc_id"].is_unique
	assert set(round1_sample["year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert label_docs[["province", "year", "title", "clean_text"]].notna().all().all()
	assert label_docs["clean_text"].str.strip().ne("").all()

	assert round1_sample["sample_pool"].value_counts().to_dict() == {
		"demand-like": 200,
		"other-like": 200,
		"supply-like": 200,
		"environment-like": 200,
	}
	assert round1_sample.loc[round1_sample["sample_pool"].eq("other-like"), "other_signal_hit_count"].gt(0).all()
	assert round1_sample.loc[round1_sample["sample_pool"].eq("other-like"), "pool_other_like_priority"].sum() == 200
	assert pool_summary.loc[pool_summary["pool"].eq("demand-like"), "is_sufficient"].item()
	assert pool_summary.loc[pool_summary["pool"].eq("other-like"), "is_sufficient"].item()
	assert "手工收集_专精特新DeepSeek首轮样本v1" in set(manifest["source_name"])


def test_manual_srdi_macbert_training_data_outputs_are_consistent() -> None:
	dataset = pd.read_csv(ROOT / "data" / "processed" / "manual_policy_srdi_macbert_training_dataset_v1.csv")
	quality = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_training_data_quality_report_v1.csv").set_index("metric")
	split_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_training_split_summary_v1.csv").set_index("split")
	label_balance = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_training_label_balance_v1.csv")
	pos_weight = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_training_pos_weight_v1.csv").set_index("label")

	assert len(dataset) == 800
	assert dataset["doc_id"].is_unique
	assert dataset["split"].value_counts().to_dict() == {"train": 557, "test": 123, "validation": 120}
	assert dataset["model_text"].fillna("").str.strip().ne("").all()
	assert set(dataset["sample_pool"].value_counts().to_dict().values()) == {200}

	assert quality.loc["successful_label_rows", "value"] == 800
	assert quality.loc["missing_model_text", "value"] == 0
	assert split_summary.loc["train", "records"] == 557
	assert split_summary.loc["validation", "records"] == 120
	assert split_summary.loc["test", "records"] == 123
	assert set(label_balance["label"]) == {"supply", "demand", "environment", "other"}
	assert pos_weight.loc["other", "pos_weight"] > pos_weight.loc["demand", "pos_weight"]
	assert pos_weight.loc["environment", "pos_weight"] < 1

	for split_name, expected_rows in {"train": 557, "validation": 120, "test": 123}.items():
		path = ROOT / "data" / "processed" / "manual_policy_srdi_macbert_training_v1" / f"{split_name}.jsonl"
		rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
		assert len(rows) == expected_rows


def test_manual_srdi_macbert_full_corpus_qa_outputs_are_consistent() -> None:
	qa_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_qa_summary_v1.csv").set_index("metric")
	by_year = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_by_year_v1.csv")
	by_province = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_probability_by_province_v1.csv")
	dictionary_comparison = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_dictionary_comparison_v1.csv")
	boundary_samples = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_boundary_samples_v1.csv")
	decision = pd.read_csv(ROOT / "outputs" / "manual_srdi_macbert_full_corpus_decision_table_v1.csv").set_index("check")

	assert int(qa_summary.loc["classified_rows", "value"]) == 4475
	assert int(qa_summary.loc["province_year_rows", "value"]) == 186
	assert qa_summary.loc["panel_is_balanced_31x6", "value"] == "True"
	assert set(by_year["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert len(by_province) == 31
	assert set(dictionary_comparison["category"]) == {"supply", "demand", "environment"}
	assert len(boundary_samples) >= 100
	assert {
		"highest_p_other",
		"low_confidence_tool_boundary",
		"all_three_tools_high",
		"demand_near_threshold",
		"macbert_dictionary_conflict",
	}.issubset(set(boundary_samples["review_reason"]))
	assert decision.loc["current_decision", "status"] == "ready_for_did_v1"


def test_manual_srdi_policy_intensity_variable_selection_outputs_are_consistent() -> None:
	did_variables = pd.read_csv(ROOT / "data" / "processed" / "province_year_srdi_policy_text_variables_v1.csv")
	variable_selection = pd.read_csv(ROOT / "outputs" / "manual_srdi_policy_intensity_variable_selection_v1.csv")
	correlations = pd.read_csv(ROOT / "outputs" / "manual_srdi_policy_intensity_variable_correlations_v1.csv")
	decision = pd.read_csv(ROOT / "outputs" / "manual_srdi_policy_intensity_variable_decision_v1.csv").set_index(
		"decision_area"
	)

	main_variables = {
		"srdi_supply_intensity",
		"srdi_demand_intensity",
		"srdi_environment_intensity",
	}
	required_columns = {
		"province",
		"publish_year",
		"srdi_policy_count",
		"srdi_policy_count_log",
		"srdi_total_tool_intensity",
		"srdi_valid_tool_policy_share",
		"srdi_other_exclusion_count",
		"dict_supply_policy_count",
		"dict_demand_policy_count",
		"dict_environment_policy_count",
	} | main_variables

	assert len(did_variables) == 186
	assert did_variables["province"].nunique() == 31
	assert set(did_variables["publish_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert did_variables[["province", "publish_year"]].duplicated().sum() == 0
	assert required_columns.issubset(did_variables.columns)
	assert (did_variables[list(main_variables)] >= 0).all().all()

	selected_main = set(variable_selection.loc[variable_selection["recommended_use"].eq("main"), "variable"])
	assert selected_main == main_variables
	assert len(correlations) == 55
	assert decision.loc["main_policy_tool_variables", "variables"] == (
		"srdi_supply_intensity;srdi_demand_intensity;srdi_environment_intensity"
	)
	assert "ready for panel merge" in decision.loc["did_handoff_status", "decision"]


def test_manual_srdi_did_policy_intensity_handoff_outputs_are_consistent() -> None:
	handoff_qa = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_handoff_qa_v1.csv")
	variable_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_variable_summary_v1.csv")
	province_crosswalk = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_province_crosswalk_template_v1.csv")
	boundary_summary = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_boundary_review_summary_v1.csv")
	handoff_decision = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_handoff_decision_v1.csv").set_index(
		"decision_area"
	)

	blocking_checks = handoff_qa.loc[handoff_qa["blocking_for_did_merge"]]
	assert not blocking_checks.empty
	assert blocking_checks["status"].eq("pass").all()
	assert "boundary_samples_require_review" in set(handoff_qa["check"])

	assert len(province_crosswalk) == 31
	assert province_crosswalk["present_in_policy_variables"].all()
	assert province_crosswalk["did_merge_key_recommended"].is_unique
	assert "新疆" in set(province_crosswalk["did_merge_key_recommended"])

	assert {
		"srdi_supply_intensity",
		"srdi_demand_intensity",
		"srdi_environment_intensity",
		"srdi_policy_count",
	}.issubset(set(variable_summary["variable"]))
	assert variable_summary["missing_count"].eq(0).all()
	assert len(boundary_summary) == 5
	assert boundary_summary["records"].sum() == 150
	assert handoff_decision.loc["policy_side_handoff_status", "decision"] == "ready_for_first_did_merge"


def test_manual_srdi_did_ready_policy_intensity_panel_is_consistent() -> None:
	panel = pd.read_csv(ROOT / "data" / "processed" / "manual_srdi_did_policy_intensity_panel_v1.csv")
	quality = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_panel_quality_report_v1.csv").set_index(
		"metric"
	)
	variable_map = pd.read_csv(ROOT / "outputs" / "manual_srdi_did_policy_intensity_panel_variable_map_v1.csv")

	main_variables = {
		"srdi_supply_intensity",
		"srdi_demand_intensity",
		"srdi_environment_intensity",
	}
	merge_keys = {"did_province_key", "did_year"}

	assert len(panel) == 186
	assert panel["did_province_key"].nunique() == 31
	assert set(panel["did_year"]) == {2020, 2021, 2022, 2023, 2024, 2025}
	assert panel["policy_panel_id"].is_unique
	assert panel[list(merge_keys)].duplicated().sum() == 0
	assert main_variables.issubset(panel.columns)
	assert panel[list(main_variables)].notna().all().all()
	assert (panel[list(main_variables)] >= 0).all().all()
	assert {f"{variable}_z" for variable in main_variables}.issubset(panel.columns)
	assert panel["needs_firm_panel_confirmation"].all()
	assert "新疆" in set(panel["did_province_key"])

	assert quality.loc["panel_rows", "status"] == "pass"
	assert quality.loc["main_variable_missing_values", "value"] == "0"
	assert quality.loc["firm_panel_confirmation_required", "status"] == "needs_external_data"
	assert merge_keys.issubset(set(variable_map["variable"]))
	assert main_variables.issubset(set(variable_map.loc[variable_map["did_use"].eq("main_moderator"), "variable"]))
