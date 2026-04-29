# Policy Text Crawler Constraints

## Research Boundaries

Do not silently decide contested sample rules. Surface these choices in the notebook decision log:

- whether to include policy interpretations, news articles, application notices, award/publicity lists, implementation plans, or subsidy guidelines
- whether attachments are primary policy text or supporting material
- whether reposted central/provincial documents count for the publishing jurisdiction or the issuing jurisdiction
- whether municipal documents are in scope for a province-level policy-intensity measure
- whether a page is relevant because it contains an SRDI keyword or because it materially supports SRDI enterprises

When uncertain, mark records as `needs_review` and explain the ambiguity. The agent may recommend a rule, but the notebook should make it easy for the user to accept or revise the research口径.

## Strategy Selection

Choose the simplest defensible method that works:

1. Public JSON API from Network panel.
2. Static HTML with `requests` or `httpx` plus BeautifulSoup.
3. Attachment parsing for PDF/Word policy bodies.
4. Playwright only when JavaScript execution is genuinely required.
5. Manual URL curation plus automated detail parsing for inconsistent websites.

Avoid a universal crawler unless repeated evidence shows the same structure across sources. For Chinese government policy websites, site-specific parsers plus a shared output schema are usually more robust.

## Compliance Rules

Use conservative collection behavior:

- respect `robots.txt`, website terms, and explicit access restrictions
- use timeouts, bounded retries, and polite low-frequency requests
- do not use high concurrency against government websites
- do not bypass login, captchas, paywalls, signatures, encrypted parameters, or access controls
- do not impersonate a real user account or use private credentials unless the user explicitly provides and authorizes them
- preserve source URLs and collection timestamps
- minimize repeat requests by archiving raw HTML/files and rerunning parsers locally

If a source is access-restricted, record the status as `skipped_access_restricted` or similar. Prefer an alternative official source or manual collection over technical circumvention.

## Notebook Go/No-Go Criteria

Before formal implementation, the notebook should show:

- the source can be requested compliantly and reproducibly
- the selected method has evidence from at least a small sample
- title, date, source URL, body text, and attachments are parseable or failure modes are documented
- ambiguous document types are identified for user judgment
- raw artifacts can be archived
- quality checks quantify missing text, missing dates, short text, duplicates, and attachment failures
- the output schema is adequate for policy text mining and staggered DID analysis

If these criteria are not met, continue notebook exploration instead of expanding crawler code.
