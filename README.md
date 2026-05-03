# Statistic Modeling

Research workflow for policy text collection and analysis. Later stages will
connect these policy-text corpora to panel construction and causal modeling.

## Stack

- Python >= 3.11
- uv for environment and dependency management
- just for integrate reusable instructions

## Structure

- `configs/`: experiment and pipeline configuration files.
- `data/`: local datasets and derived data artifacts.
- `docs/`: notes, reports, and project documentation.
- `notebooks/`: exploratory notebooks.
- `outputs/`: generated figures, tables, and run outputs.
- `scripts/`: one-off or reusable research scripts.
- `src/`: importable Python package code.

## Open Loops

**Current Main Work**:
We manually collected policies whose metadata contains the keyword "专精特新"
from central and provincial sources. The current main path is now based on
`data/interim/manual_policy_all_keyword_srdi.xlsx`, not continued broad crawler
expansion.

- [x] Build processed v0 records from the manual workbook:
  `data/processed/manual_policy_srdi_policy_records_v0.csv`.
- [x] Build the DID-facing province-year policy-intensity candidate:
  `data/processed/province_year_srdi_policy_intensity_v0.csv`.
- [x] Build the first text-mining feature notebook from the manual processed
  records. Start with title/abstract keyword features, publication-year trends,
  province distribution, central/local comparison, and simple policy-tool
  dictionary checks.
- [x] Review the v0 policy-tool dictionary and inspect no-hit rows. A 30-record
  sample-driven revision is archived in
  `docs/manual-srdi-policy-mining-notes.md`.
- [x] Build paper-facing descriptive tables and figures in
  `notebooks/41_manual_srdi_descriptive_analysis.py`.
- [x] Add a full-text v1 mining path from
  `data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`, keeping the
  v0 title/abstract path as a baseline.
- [x] Compare v0 title/abstract and full-text v1 text measures in
  `notebooks/43_manual_srdi_text_measure_comparison.py`. Current evidence
  favors full-text v1 as the main aggregate text-intensity proxy, with v0 kept
  as robustness.
- [x] Build the main full-text descriptive analysis in
  `notebooks/44_manual_srdi_fulltext_descriptive_analysis.py`.
- [x] Audit full-text keyword quality and interpretation in
  `notebooks/45_manual_srdi_fulltext_keyword_quality.py`.
- [x] Convert keywords into label-rule sampling aids and build the round-1
  DeepSeek sample in `notebooks/46_manual_srdi_label_rule_keywords.py`.
- [x] Build the DeepSeek round-1 labeling command in
  `scripts/manual_srdi_deepseek_round1_label.py`; use dry-run first, then live
  run with `DEEPSEEK_API_KEY` exported in the shell.
- [x] Run the live DeepSeek round-1 labeling and review its artifact readiness
  in `notebooks/47_manual_srdi_deepseek_round1_qa.py`. The run produced 800
  label rows and 800 raw JSON cache files; the first QA pass identified one
  parser-level repair case.
- [x] Repair the single failed DeepSeek label via cached-response parsing
  fallback, then rerun round-1 QA. Current QA reports 800 successful labels,
  zero failed labels, and `enter_macbert_training_preparation`.
- [x] Prepare MacBERT training data in
  `notebooks/48_manual_srdi_macbert_training_data.py`: deterministic
  train/validation/test JSONL files, label-balance QA, and `pos_weight`
  candidates.
- [x] Implement the MacBERT training script in
  `scripts/manual_srdi_train_macbert_multilabel.py`, with dry-run validation,
  explicit PyTorch training loop, validation/test metrics, model checkpoint
  output, and test-set predictions.
- [x] Run the live MacBERT training command and review validation/test
  multi-label metrics. Current round-1 model is adequate for full-corpus
  prediction, with the three main tool labels performing substantially better
  than the boundary `other` label.
- [x] Predict the full 4,475-document full-text corpus and build the
  DID-facing MacBERT province-year tool-intensity table:
  `data/processed/province_year_srdi_macbert_tool_intensity_v1.csv`.
- [x] Review full-corpus MacBERT prediction distributions in
  `notebooks/49_manual_srdi_macbert_full_corpus_qa.py`. Current decision table
  marks the v1 outputs as `ready_for_did_v1`; round-2 labeling is optional after
  boundary-sample review.
- [x] Fix the main DID-facing policy-text variable口径 in
  `notebooks/50_manual_srdi_policy_intensity_variable_selection.py`. Main
  variables are continuous MacBERT probability sums:
  `srdi_supply_intensity`, `srdi_demand_intensity`, and
  `srdi_environment_intensity`; policy count, filtered sums, hard-label counts,
  and dictionary counts are retained as controls or robustness variables.
- [x] Build the policy-side DID handoff notebook in
  `notebooks/51_did_policy_intensity_handoff.py`. Current QA marks
  `province_year_srdi_policy_text_variables_v1.csv` as
  `ready_for_first_did_merge`, with a province-name crosswalk template ready for
  enterprise-panel confirmation.
- [x] Build the final policy-side DID-ready panel in
  `notebooks/52_did_ready_policy_intensity_panel.py`:
  `data/processed/manual_srdi_did_policy_intensity_panel_v1.csv`. This table
  carries stable merge keys `did_province_key` and `did_year`, main policy-tool
  moderators, robustness variables, audit variables, and z-score convenience
  variables.
- [ ] Review `outputs/manual_srdi_macbert_full_corpus_boundary_samples_v1.csv`
  before final paper freeze, mainly for demand-threshold and `other` boundary
  cases.

**v2 2019-2024 Rebuild**:
The v2 path corrects the policy-side analysis window from 2020-2025 to
2019-2024. The current repo scope remains policy-panel construction only; it
does not run enterprise-panel merges or DID regressions.

- [x] Build the reviewed v2 full-text corpus and policy-count panel:
  `data/processed/manual_policy_srdi_policy_records_fulltext_v2.csv` and
  `data/processed/province_year_srdi_policy_intensity_v2.csv`.
- [x] Build v2 full-text dictionary features and descriptive/keyword-quality
  diagnostics in `notebooks/42b_manual_srdi_fulltext_text_mining_v2.py` and
  `notebooks/44b_manual_srdi_fulltext_descriptive_keyword_quality_v2.py`.
- [x] Run v2 MacBERT full-corpus prediction and province-year aggregation:
  `data/processed/manual_policy_srdi_policy_classified_fulltext_v2.csv` and
  `data/processed/province_year_srdi_macbert_tool_intensity_v2.csv`.
- [x] Build independent v2 MacBERT prediction QA and variable-readiness
  diagnostics in
  `notebooks/49b_manual_srdi_macbert_prediction_qa_variable_readiness_v2.py`.
  Current decision is `ready_for_variable_selection_v2`.
- [x] Build the v2 policy-text variable-selection notebook in
  `notebooks/50b_manual_srdi_policy_intensity_variable_selection_v2.py`:
  `data/processed/province_year_srdi_policy_text_variables_v2.csv`. Main
  variables remain continuous MacBERT probability sums; filtered sums,
  hard-label counts, high-confidence counts, dictionary variables, and audit
  fields are retained for the final panel step.
- [x] Build the final v2 policy-side DID-ready panel in
  `notebooks/52b_did_ready_policy_intensity_panel_v2.py`:
  `data/processed/manual_srdi_did_policy_intensity_panel_v2.csv`. Current
  policy-side status is `ready_for_enterprise_panel_merge`, pending external
  confirmation that enterprise-panel province labels match `did_province_key`.
- [x] Build final v2 policy-side descriptive and QA artifacts in
  `notebooks/53b_did_ready_policy_intensity_panel_descriptive_qa_v2.py`,
  including summary statistics, annual trends, province rankings, region
  grouping readiness, correlations, outlier audit, figures, and handoff notes.
  Region grouping is a readiness artifact, not a heterogeneity-effect result.

## Documentations

- `docs/govcn-xxgk-dev-notes.md` -- gov.cn XXGK development notes, milestone history, current artifact snapshot, and stage decisions.
- `docs/manual-srdi-policy-mining-notes.md` -- manual SRDI policy mining milestone and paper-drafting notes.
- `docs/manual-srdi-paper-draft-notes.md` -- stage paper-drafting notes for the manual SRDI data, full-text text-mining path, descriptive materials, and label-rule preparation.
- `docs/research-design-and-variable-description.md` -- paper-section draft for research design, DID specification, policy-intensity construction, and variable definitions.
- `docs/label-intensity-construct-plan.md` -- multi-label classification design for policy tools (supply-side, demand-side, environmental), including task definition, model architecture, and evaluation methodology.
- `docs/govcn-xxgk-crawler.md` -- gov.cn XXGK crawler operation, mechanism, outputs, and demo checks.
- `docs/source-manifest-guide.md` -- Data registration rules for `data/source-manifest.csv`.
- `docs/data-dictionary.md` -- Data field definitions for registered datasets.
