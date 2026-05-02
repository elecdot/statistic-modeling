# Tests

Pytest regression and artifact-consistency checks live here.

The tests are organized by workflow:

- `test_govcn_xxgk_crawler.py`: gov.cn XXGK configuration, request payloads, cached parsing, and pagination behavior.
- `test_govcn_xxgk_processed.py`: gov.cn XXGK processed-corpus filtering and provenance rules.
- `test_manual_srdi_processed.py`: manual SRDI workbook normalization and province-year intensity construction.
- `test_manual_srdi_outputs.py`: manual SRDI text-mining and notebook output consistency checks.
- `test_manual_srdi_deepseek_labeling.py`: DeepSeek round-1 labeling prompt, parsing, dry-run, and output-shape checks without API calls.
- `test_manual_srdi_macbert_training.py`: MacBERT training-data metrics and dry-run checks without loading a model.
- `test_manual_srdi_macbert_prediction.py`: MacBERT full-corpus prediction hard-label rules, panel aggregation, and generated-output checks.
- `test_source_manifest.py`: source manifest path and cache-isolation checks.

Use the workspace-safe uv cache when running tests in agent sandboxes:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests
```
