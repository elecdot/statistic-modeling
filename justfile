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
