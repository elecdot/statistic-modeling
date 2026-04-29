# Policy Text Crawler Schema

## Canonical Record

Normalize every source to a common policy-text record. Recommended fields:

```text
policy_id
province
city
year
title
publish_date
agency
source_site
source_url
keyword_hit
document_type
text_raw
text_clean
attachment_urls
attachment_text
raw_html_path
raw_file_path
parse_status
review_status
error
crawl_time
text_hash
```

Minimum fields for this research project:

```text
province
year
policy_title
policy_body
policy_type
source_url
```

Keep `text_raw` and `text_clean` separate. Cleaning rules can affect policy-intensity measurement, so raw text must remain available for audit and reprocessing.

## Suggested Status Values

Use explicit status fields instead of dropping failures:

```text
parse_status:
  success
  partial
  list_failed
  detail_failed
  attachment_failed
  skipped_access_restricted
  skipped_out_of_scope

review_status:
  accepted
  needs_review
  rejected
```

Attach an `error` or `review_note` when a record is partial, failed, skipped, or ambiguous.

## Storage Layout

Use project conventions and keep raw artifacts reproducible:

```text
data/raw/html/
data/raw/pdf/
data/raw/docx/
data/interim/policy_list.csv
data/interim/policy_detail_raw.parquet
data/processed/policy_texts_clean.parquet
data/processed/province_year_policy_strength.parquet
outputs/
```

Prefer Parquet for analytical datasets, CSV for manually editable seed/source maps, and raw HTML/files for auditability.

## Parser Output Contract

Each parser should return a normalized dictionary even when fields are missing. A useful parser output includes:

```python
{
    "province": "...",
    "title": "...",
    "publish_date": "...",
    "agency": "...",
    "source_site": "...",
    "source_url": "...",
    "text_raw": "...",
    "attachment_urls": [],
    "raw_html_path": "...",
    "parse_status": "success",
    "error": None,
}
```

The caller should add crawl timestamps, hashes, file paths, and quality flags consistently.

## Quality Report

After pilot crawling, generate a compact quality report with counts for:

- total candidate records
- successfully parsed records
- partial and failed parses
- empty body text
- short body text
- missing publication dates
- duplicate source URLs
- duplicate title/date pairs
- duplicate or near-duplicate text hashes
- attachment download/extraction failures
- records marked `needs_review`

Use this report to decide whether to expand source coverage or return to notebook investigation.
