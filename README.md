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
- [ ] Run DeepSeek round-1 labeling on
  `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv`, following
  `docs/label-intensity-construct-plan.md`.
- [ ] Link `province_year_srdi_policy_intensity_v0.csv` to the downstream
  staggered-DID panel and finalize province-name compatibility.

## Documentations

- `docs/govcn-xxgk-dev-notes.md` -- gov.cn XXGK development notes, milestone history, current artifact snapshot, and stage decisions.
- `docs/manual-srdi-policy-mining-notes.md` -- manual SRDI policy mining milestone and paper-drafting notes.
- `docs/govcn-xxgk-crawler.md` -- gov.cn XXGK crawler operation, mechanism, outputs, and demo checks.
- `docs/source-manifest-guide.md` -- Data registration rules for `data/source-manifest.csv`.
- `docs/data-dictionary.md` -- Data field definitions for registered datasets.
