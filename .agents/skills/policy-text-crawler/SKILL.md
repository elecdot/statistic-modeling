---
name: policy-text-crawler
description: Build compliant, reproducible crawlers for Chinese public policy text collection in the SRDI/Little-Giant research project. Use when Codex needs to plan, prototype, validate, or implement policy text crawlers; inspect government policy websites; create source maps; design policy-text schemas; parse HTML/API/PDF/Word policy sources; or turn exploratory crawler notebooks into production code. Always use a Jupytext percent-format notebook during the preparation and judgment phase before writing formal crawler code.
---

# Policy Text Crawler

## Core Rule

Before implementing formal crawler code, first create or update a Jupytext percent-format Python notebook. Use the `jupytext-notebooks` skill for notebook pairing, editing, validation, and sync.

The notebook is the judgment surface for the user. It should make crawler decisions inspectable before automation is locked in:

- source scope and search keywords
- output schema and unit of observation
- website structure and pagination rules
- API, static HTML, attachment, or browser-automation feasibility
- sample records and parsing results
- compliance risks and crawl-rate assumptions
- unresolved decisions that require user judgment

Do not jump directly to a "mega crawler." Government websites vary too much. Prefer a semi-automated, site-specific pipeline that becomes more automated only after sample-based evidence is stable.

If source eligibility, sample inclusion rules, parser feasibility, or compliance status is unclear, continue notebook exploration instead of writing production crawler code.

## Preparation Workflow

1. Read the project `README.md`, relevant directory-level `README.md` files, and existing notebooks or crawler code.
2. Create or update a notebook under `notebooks/`, paired as `ipynb,py:percent`. Prefer names like `policy_text_crawler_<source_or_province>.py`.
3. In the percent-format `.py` notebook, document the research-facing data requirement before code:
   - target population and jurisdiction scope
   - policy keywords, such as `专精特新`, `小巨人`, `中小企业`
   - unit of observation: policy document, notice, guideline, interpretation, attachment, or clause
   - minimum required fields for downstream text mining and DID analysis
4. Build a source map before broad crawling. Start with priority provinces or central platforms, then expand.
5. Run small feasibility probes only. Fetch a few list pages, detail pages, and attachments with polite delays and timeouts.
6. Record evidence in notebook tables so the user can decide whether the source is usable.
7. Only after the notebook makes the crawler strategy clear, implement importable code or scripts.

## Notebook Requirements

Use readable markdown and small code cells. The notebook must include:

- goal, scope, source map, and output schema
- minimal HTTP/API/parser/attachment probes with evidence tables
- a decision log with `source`, `chosen_method`, `evidence`, `unresolved_risk`, `user_decision_needed`, and `ready_for_implementation`
- quality checks for empty text, short text, missing date, duplicate URL/title, keyword match, and province mismatch

Keep the notebook suitable for user review. Avoid hiding key assumptions in transient variables or long unannotated cells.

Use notebooks for feasibility judgment and user review. Once crawler logic stabilizes, move reusable production logic into `src/` and keep notebooks as thin demonstrations, audits, or decision records.

## Formal Implementation

After notebook decisions are stable, implement code using layered modules rather than one large script:

```text
Fetcher      request pages and download files
Parser       extract structured fields from source-specific HTML/API/documents
Cleaner      normalize conservative text fields
Storage      archive raw data and write interim/processed datasets
Validator    produce quality reports and failure records
```

Prefer site-specific parsers over a universal parser. Place reusable package code under `src/statistic_modeling/`, command or one-off entry points under `scripts/`, source configuration under `configs/`, and exploratory judgment work under `notebooks/`.

Use configuration files for source websites when multiple provinces or websites are involved. Include comments or docstrings for non-obvious selectors, API parameters, retry behavior, and data-quality assumptions. If dependencies are missing, add them with the project's `uv` conventions; in sandboxed runs use a workspace-safe cache such as `UV_CACHE_DIR=/tmp/uv-cache`.

## Quality Gate

Before expanding beyond pilot crawling, produce a notebook or report answering:

1. Can the source be requested compliantly and reproducibly?
2. Are title, date, agency, body, and attachments parseable?
3. Is the body HTML, API data, PDF, Word, or mixed?
4. Are records actually policy documents rather than news or publicity?
5. Are duplicates controlled by URL, title/date, and text hash?
6. Are missing dates, empty bodies, short bodies, and attachment failures quantified?
7. Are raw artifacts stored and linked from structured records?
8. Is the schema sufficient for policy text mining and staggered DID analysis?

If these are not clear, continue notebook exploration instead of writing or expanding production code.

## References

- Read `references/constraints.md` when deciding sample inclusion, crawling strategy, compliance boundaries, or go/no-go criteria.
- Read `references/schema.md` when designing fields, storage layout, parser outputs, and quality reports.
- Read `references/notebook-template.md` when creating a new crawler feasibility notebook or standardizing an existing one.
