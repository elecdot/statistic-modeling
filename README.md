# Statistic Modeling

Research workflow for policy text collection and analysis. Maybe panel construction later.

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

- [ ] Define a reusable XXGK search configuration before expanding collection.
  Start from the current central-government probe in
  `notebooks/20_central_gov_xxgk_explore.py`. Record each query as data, not as
  one-off notebook edits: keyword, title/full-text search, fuzzy/precise match,
  sort order, page size, max pages, and research reason.
- [ ] Probe full-text search before expanding title-search pages.
  Current title search finds `中小企业` candidates but not `专精特新` or `小巨人`.
  The next central-government probe should test `fieldName=""`,
  `isPreciseSearch=0`, and `sortField="publish_time"` for those keywords.
- [ ] Decide the safe scope for no-keyword collection.
  A blank `searchWord` can be used to request a general policy list, but it
  should first be tested on a small page range and reviewed through
  `pager.total`, `pager.pageCount`, duplicates, and detail-parse quality before
  any broader collection.
- [ ] Register collection configuration before formal collection.
  Add a small YAML/TOML/CSV config under `configs/` for XXGK query batches, and
  document the config fields before running more than pilot pages.
- [ ] Upgrade `data/source-manifest.csv` only after the next source batch.
  Current notes already record notebook provenance. If more sources are added,
  plan explicit fields such as `generated_by`, `upstream_files`,
  `collection_status`, and `review_status` instead of continuing to overload
  `notes`.
- [ ] Promote crawler logic out of notebooks only after the search strategy is stable.
  Once full-text search, pagination, detail parsing, and quality checks are
  reliable, move reusable fetch/parse/storage logic into `src/` or `scripts/`
  and keep notebooks as demonstrations and audit records.

## Documentations

- `docs/data-dictionary.md` -- Data field definitions (high priority required)
