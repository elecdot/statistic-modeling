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
`data/interim/manual_policy_all_keyword_srdi.xlsx`. Prefer:

```bash
just manual-srdi-processed-v0
```

This command does not send network requests.

`manual_srdi_fulltext_processed_corpus.py` builds the full-text v1 processed
policy records from
`data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`. Prefer:

```bash
just manual-srdi-fulltext-processed-v1
```

This keeps the title/abstract v0 artifacts intact and writes independent
full-text v1 outputs.

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
