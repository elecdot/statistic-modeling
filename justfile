set shell := ["bash", "-c"]

ruff:
    UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .

test:
    UV_CACHE_DIR=/tmp/uv-cache uv run pytest

nbsync:
    UV_CACHE_DIR=/tmp/uv-cache uv run jupytext --sync notebooks/*.ipynb

# Print the reviewed gov.cn XXGK list-request queue without fetching.
govcn-xxgk-queue:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py queue

# Run the gov.cn XXGK pilot in cache-first mode. This does not send network requests.
govcn-xxgk-cache-pilot:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py run

# Run the reviewed gov.cn XXGK live collection for the configured 2025-2020 scope.
govcn-xxgk-live-full:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py run --fetch-live --max-details-per-batch -1

# Probe the central all-policy XXGK corpus with blank keyword and isolated outputs.
govcn-xxgk-all-probe:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py --query-batches configs/govcn_xxgk_all_query_batches.csv run --fetch-live --max-pages-override 5 --candidates-output data/interim/govcn_xxgk_all_candidate_url_queue.csv --details-output data/interim/govcn_xxgk_all_policy_detail_records.csv --quality-output outputs/govcn_xxgk_all_quality_report.csv

# Run the central all-policy XXGK corpus for the configured 2020-2025 scope.
govcn-xxgk-all-full:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_crawler.py --query-batches configs/govcn_xxgk_all_query_batches.csv run --fetch-live --max-details-per-batch -1 --candidates-output data/interim/govcn_xxgk_all_candidate_url_queue.csv --details-output data/interim/govcn_xxgk_all_policy_detail_records.csv --quality-output outputs/govcn_xxgk_all_quality_report.csv

# Build the reviewed central all-policy processed text corpus v0.
govcn-xxgk-processed-v0:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/govcn_xxgk_processed_corpus.py

# Build processed records and province-year intensity from the manual SRDI workbook.
manual-srdi-processed-v0:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_processed_corpus.py

# Build processed records from the manual SRDI workbook with full text.
manual-srdi-fulltext-processed-v1:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_fulltext_processed_corpus.py

# Build the 2019-2024 v2 full-text corpus and province-year policy-count panel.
manual-srdi-fulltext-processed-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_fulltext_processed_corpus_v2.py

# Build 2019-2024 v2 full-text dictionary features from the frozen v1 codebook.
manual-srdi-fulltext-text-mining-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python notebooks/42b_manual_srdi_fulltext_text_mining_v2.py

# Build 2019-2024 v2 full-text descriptive and keyword-quality artifacts.
manual-srdi-fulltext-desc-keyword-quality-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python notebooks/44b_manual_srdi_fulltext_descriptive_keyword_quality_v2.py

# Validate DeepSeek round-1 labeling prompts and outputs without API calls.
manual-srdi-deepseek-round1-dry-run:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_deepseek_round1_label.py --dry-run --limit 3 --labels-output /tmp/manual_policy_srdi_deepseek_labels_round1_dry_run.csv --quality-output /tmp/manual_policy_srdi_deepseek_round1_dry_run_quality_report.csv --raw-output-dir /tmp/manual_srdi_deepseek_round1_dry_run

# Run DeepSeek round-1 labeling. Requires DEEPSEEK_API_KEY in the shell.
manual-srdi-deepseek-round1:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_deepseek_round1_label.py --resume --workers 3 --max-retries 2

# Validate MacBERT training inputs without loading a model.
manual-srdi-macbert-train-dry-run:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_train_macbert_multilabel.py --dry-run

# Train the first MacBERT multi-label classifier. Requires torch, transformers, and model download access.
manual-srdi-macbert-train:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_train_macbert_multilabel.py --resume

# Predict policy-tool probabilities for the full manual SRDI full-text corpus.
manual-srdi-macbert-predict-full:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_macbert_predict_full_corpus.py

# Predict policy-tool probabilities for the 2019-2024 v2 full-text corpus.
manual-srdi-macbert-predict-full-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/manual_srdi_macbert_predict_full_corpus_v2.py

# Build 2019-2024 v2 MacBERT prediction QA and variable-readiness artifacts.
manual-srdi-macbert-qa-variable-readiness-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python notebooks/49b_manual_srdi_macbert_prediction_qa_variable_readiness_v2.py

# Select 2019-2024 v2 policy-text variables for the final policy-side panel step.
manual-srdi-policy-text-variable-selection-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python notebooks/50b_manual_srdi_policy_intensity_variable_selection_v2.py

# Build the final 2019-2024 v2 policy-side DID-ready panel.
manual-srdi-did-ready-policy-panel-v2:
    UV_CACHE_DIR=/tmp/uv-cache uv run python notebooks/52b_did_ready_policy_intensity_panel_v2.py
