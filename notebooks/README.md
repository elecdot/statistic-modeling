# Notebooks

Exploratory and decision notebooks live here.

Keep committed notebooks small and clear when possible.

Crawler decisions should be documented while website reconnaissance
in paired Jupytext notebooks before being promoted into reusable scripts
or package code.

## Manual SRDI v2

- `42b_manual_srdi_fulltext_text_mining_v2.py`: builds the 2019-2024 v2
  transparent full-text dictionary features from
  `manual_policy_srdi_policy_records_fulltext_v2.csv` and the frozen v1
  full-text dictionary. It stops before MacBERT, variable selection, final DID
  panel construction, or enterprise-panel work.
- `44b_manual_srdi_fulltext_descriptive_keyword_quality_v2.py`: builds v2
  descriptive and keyword-quality analysis artifacts from the v2 corpus and
  dictionary features, including source composition, empty full-text handling,
  no-hit diagnostics, category overlap, and term coverage.
- `49b_manual_srdi_macbert_prediction_qa_variable_readiness_v2.py`: checks the
  completed 2019-2024 v2 MacBERT predictions against structural QA, prediction
  distributions, dictionary alignment, boundary samples, and variable-readiness
  decisions. It stops before final policy-side panel construction.
- `50b_manual_srdi_policy_intensity_variable_selection_v2.py`: selects the
  2019-2024 v2 policy-text variables from MacBERT probability sums, filtered
  sums, hard-label counts, high-confidence counts, dictionary robustness
  variables, and audit fields. It writes the variable table used by the later
  final policy-side panel step, but does not add DID merge keys or z-scores.
- `52b_did_ready_policy_intensity_panel_v2.py`: builds the final 2019-2024 v2
  policy-side DID-ready panel with `did_province_key`, `did_year`,
  `policy_panel_id`, selected main/robustness/audit variables, z-score
  convenience variables, province crosswalk, variable map, QA report, and
  handoff decision. It does not load enterprise data or run DID regressions.
- `53b_did_ready_policy_intensity_panel_descriptive_qa_v2.py`: builds final v2
  policy-side descriptive and QA artifacts for paper/data handoff, including
  summary statistics, year trends, province rankings, region grouping
  readiness, correlations, outlier audit, figures, and final handoff notes. It
  does not estimate heterogeneity effects.
