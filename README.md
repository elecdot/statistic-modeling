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

- [ ] Build the first text-mining feature notebook from
  `data/processed/govcn_xxgk_all_policy_text_corpus_v0.csv`.
  Start with keyword hits for `专精特新` / `小巨人` / `中小企业`, publication-year
  trends, official subject category cross-tabs, and text-length diagnostics.
- [ ] Decide how `official_subject_categories` should be used in modeling.
  It is a gov.cn-specific source taxonomy and should not be treated as a
  province-level policy-tool taxonomy without a separate mapping decision.
- [ ] Decide whether attachment context is needed. If it is, design it as a
  separate artifact rather than adding exploratory fields to the main processed
  corpus. NOTE: I prefer not.
- [ ] Define the province-level source expansion workflow. Start with a source
  map and feasibility notebook before adding provincial crawler code.
- [ ] Link central processed corpus outputs to downstream policy-intensity
  construction and staggered-DID panel requirements.

## Documentations

- `docs/govcn-xxgk-dev-notes.md` -- gov.cn XXGK development notes, milestone history, current artifact snapshot, and stage decisions.
- `docs/govcn-xxgk-crawler.md` -- gov.cn XXGK crawler operation, mechanism, outputs, and demo checks.
- `docs/source-manifest-guide.md` -- Data registration rules for `data/source-manifest.csv`.
- `docs/data-dictionary.md` -- Data field definitions for registered datasets.
