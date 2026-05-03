# Scripts

One-off or reusable research scripts live here.

## gov.cn XXGK

`govcn_xxgk_crawler.py` is the command entry point for the central gov.cn XXGK
crawler. Prefer the `just` recipes at the repository root:

```bash
just govcn-xxgk-cache-pilot
just govcn-xxgk-live-full
just govcn-xxgk-all-probe
just govcn-xxgk-all-full
just govcn-xxgk-processed-v0
```

See `docs/govcn-xxgk-crawler.md` before changing query configs or running broad
live collection.

`govcn_xxgk_processed_corpus.py` builds the reviewed processed all-policy
corpus v0 from cached interim detail records. It does not send network requests.

## Manual SRDI Workbook

`manual_srdi_processed_corpus.py` builds processed policy records and a
province-year policy-intensity table from
`data/interim/manual_policy_all_keyword_srdi.xlsx`. It applies reviewed
jurisdiction corrections from `configs/manual_srdi_jurisdiction_overrides_v1.csv`
so `province` represents the policy jurisdiction rather than only the reposting
source site. Prefer:

```bash
just manual-srdi-processed-v0
```

This command does not send network requests.

`manual_srdi_fulltext_processed_corpus.py` builds the full-text v1 processed
policy records from
`data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`, using the
same jurisdiction correction config. Prefer:

```bash
just manual-srdi-fulltext-processed-v1
```

This keeps the title/abstract v0 artifacts intact and writes independent
full-text v1 outputs.

`manual_srdi_fulltext_processed_corpus_v2.py` builds the 2019-2024 full-text v2
corpus by stacking the current full-text workbook's 2020-2024 records with the
2019 supplementary workbook at
`data/interim/manual_policy_all_keyword_srdi_2019_supplementary.xlsx`. It keeps
v1 outputs intact, writes a v2 row-level corpus, a balanced province-year
policy-count table, QA reports, and a 2019 jurisdiction-review candidate table.
The default jurisdiction correction config is
`configs/manual_srdi_jurisdiction_overrides_v2.csv`, which preserves the
reviewed v1 corrections and adds the 2019 supplement review decisions.
Prefer:

```bash
just manual-srdi-fulltext-processed-v2
```

This command does not run notebooks, MacBERT prediction, or downstream DID
construction.

`manual_srdi_deepseek_round1_label.py` labels the deterministic 800-record
round-1 sample with a DeepSeek-compatible chat API and writes cached raw
responses plus parsed multi-label outputs. It reads the API key only from
`DEEPSEEK_API_KEY`.

Validate the prompt and output plumbing without network calls:

```bash
just manual-srdi-deepseek-round1-dry-run
```

Run the live round-1 labeling only after exporting the key in the shell:

```bash
export DEEPSEEK_API_KEY="..."
just manual-srdi-deepseek-round1
```

The live recipe uses `--resume --workers 3 --max-retries 2`. Raw responses are
cached by `doc_id`, so interrupted runs can be resumed without repeating
completed requests. If the API returns frequent 429 or timeout errors, lower
parallelism:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_deepseek_round1_label.py --resume --workers 2
```

Progress and error details are written to
`outputs/manual_policy_srdi_deepseek_round1_run_log_v1.log` as well as the
console.

When cached responses are parsed with `--resume`, the parser reads
`message.content` first. If a DeepSeek response has empty `message.content` but
contains the requested JSON object in `reasoning_content`, the script uses that
as a conservative fallback without modifying the raw cache file.

`manual_srdi_train_macbert_multilabel.py` trains the first MacBERT multi-label
classifier from the JSONL split prepared by
`notebooks/48_manual_srdi_macbert_training_data.py`.

Validate inputs without loading the model:

```bash
just manual-srdi-macbert-train-dry-run
```

The live training command uses the project-declared `torch` and `transformers`
dependencies and requires access to download `hfl/chinese-macbert-base` unless
it is already cached:

```bash
just manual-srdi-macbert-train
```

The live recipe passes `--resume`. At each completed epoch, the script writes a
checkpoint under `outputs/manual_srdi_macbert_multilabel_v1/checkpoints/` and
updates the metrics CSV. If training is interrupted, rerun the same command; it
continues from the latest completed epoch rather than starting from scratch.
Progress and failures are logged to
`outputs/manual_srdi_macbert_multilabel_train_v1.log`.

Hugging Face download progress bars and advisory model-loading messages are
suppressed by default so run logs stay readable. Pass `--show-download-progress`
when debugging model downloads. For remote checkpoints, the script requests
PyTorch weights to avoid the non-fatal safetensors auto-conversion thread that
can emit repository-discussion 403 messages for this checkpoint. Safetensors-only
local checkpoints remain supported for smoke tests.

The script writes the model checkpoint to
`outputs/manual_srdi_macbert_multilabel_v1/`, validation/test metrics to
`outputs/manual_srdi_macbert_multilabel_metrics_v1.csv`, test predictions to
`outputs/manual_srdi_macbert_multilabel_test_predictions_v1.csv`, and run QA to
`outputs/manual_srdi_macbert_multilabel_quality_report_v1.csv`.

`manual_srdi_macbert_predict_full_corpus.py` applies the trained checkpoint to
all 4,475 full-text policy records and aggregates policy-tool probabilities to a
balanced province-year table:

```bash
just manual-srdi-macbert-predict-full
```

The script uses the same model-text construction and hard-label thresholds as
the training workflow. It writes row-level predictions to
`data/processed/manual_policy_srdi_policy_classified_fulltext_v1.csv`,
province-year tool intensity to
`data/processed/province_year_srdi_macbert_tool_intensity_v1.csv`, and prediction
QA tables under `outputs/manual_srdi_macbert_full_corpus_*_v1.csv`.

`manual_srdi_macbert_predict_full_corpus_v2.py` applies the same trained v1
checkpoint to the reviewed 2019-2024 v2 full-text corpus:

```bash
just manual-srdi-macbert-predict-full-v2
```

The v2 entry point writes row-level predictions to
`data/processed/manual_policy_srdi_policy_classified_fulltext_v2.csv`,
province-year tool intensity to
`data/processed/province_year_srdi_macbert_tool_intensity_v2.csv`, and prediction
QA tables under `outputs/manual_srdi_macbert_full_corpus_*_v2.csv`. It keeps v1
outputs intact and uses title/agency/province/year fallback for the single
retained v2 row with empty full text.
