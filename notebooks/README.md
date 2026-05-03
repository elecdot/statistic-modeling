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
