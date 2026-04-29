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
