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
- [ ] Review the v0 policy-tool dictionary in
  `outputs/manual_policy_srdi_tool_dictionary_v0.csv` and inspect no-hit rows
  before treating supply/demand/environment features as paper-facing labels.
- [ ] Decide whether title/abstract-only evidence is enough for the paper's
  text-mining claims, or whether selected full-text retrieval is needed.
- [ ] Link `province_year_srdi_policy_intensity_v0.csv` to the downstream
  staggered-DID panel and finalize province-name compatibility.

## Documentations

- `docs/govcn-xxgk-dev-notes.md` -- gov.cn XXGK development notes, milestone history, current artifact snapshot, and stage decisions.
- `docs/govcn-xxgk-crawler.md` -- gov.cn XXGK crawler operation, mechanism, outputs, and demo checks.
- `docs/source-manifest-guide.md` -- Data registration rules for `data/source-manifest.csv`.
- `docs/data-dictionary.md` -- Data field definitions for registered datasets.
