# Data Dictionary

## Example Sample Asserts

>[!warning] This is just a place holder. Anything of this example are not stable

### `data/raw/sample_policies.parquet`

| Field | Type | Description |
| --- | --- | --- |
| `source_name` | string | Source identifier (`zjtx-announcements` in current implementation) |
| `source_type` | string | Source channel type (`public_api`) |
| `source_url` | string | API URL used to fetch announcement payload |
| `policy_id` | string | Announcement id from upstream payload (`id`) |
| `title` | string | Announcement title |
| `published_at` | datetime | Upstream release timestamp (`fbsj`) parsed to datetime |
| `body_html` | string | Raw HTML content from upstream payload (`nr`) |
| `body_text` | string | Normalized plain text extracted from `body_html` |
| `fetched_at` | datetime | Local capture timestamp when payload was fetched |
| `notes` | string | Initialization-stage provenance note |

###  `data/interim/clean_text_policy.parquet`

...
