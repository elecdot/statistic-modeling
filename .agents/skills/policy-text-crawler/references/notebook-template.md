# Policy Text Crawler Notebook Template

Use this as a compact Jupytext percent-format skeleton for crawler feasibility notebooks. Use the `jupytext-notebooks` skill for pairing, syncing, validation, and percent-format rules.

```python
# %% [markdown]
# # Policy Text Crawler Feasibility: <source_or_province>
#
# Purpose: decide whether this source can support compliant, reproducible policy text collection for SRDI/Little-Giant research.

# %% [markdown]
# ## Goal and Scope
#
# - Jurisdiction:
# - Source site:
# - Time span:
# - Keywords:
# - Candidate document types:
# - Explicitly out of scope:

# %%
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# %% [markdown]
# ## Source Map

# %%
source_map = pd.DataFrame(
    [
        {
            "source": "",
            "base_url": "",
            "search_url": "",
            "keyword": "",
            "note": "",
        }
    ]
)
source_map

# %% [markdown]
# ## Output Schema
#
# Use `references/schema.md` from the policy-text-crawler skill for canonical fields and status values.

# %%
required_fields = [
    "province",
    "year",
    "policy_title",
    "policy_body",
    "policy_type",
    "source_url",
]
required_fields

# %% [markdown]
# ## Feasibility Probes
#
# Record only small, polite probes. Do not expand crawling here.

# %%
probe_results = pd.DataFrame(
    columns=[
        "source",
        "url",
        "method",
        "status_code",
        "encoding",
        "content_preview",
        "risk_note",
    ]
)
probe_results

# %% [markdown]
# ## Parser Probes
#
# Test selectors, JSON paths, or attachment extraction on a small sample.

# %%
parser_results = pd.DataFrame(
    columns=[
        "source",
        "sample_url",
        "title_ok",
        "date_ok",
        "body_ok",
        "attachments_ok",
        "parse_status",
        "note",
    ]
)
parser_results

# %% [markdown]
# ## Quality Checks

# %%
quality_checks = pd.DataFrame(
    columns=[
        "check",
        "count",
        "example",
        "action_needed",
    ]
)
quality_checks

# %% [markdown]
# ## Decision Log

# %%
decision_log = pd.DataFrame(
    [
        {
            "source": "",
            "chosen_method": "",
            "evidence": "",
            "unresolved_risk": "",
            "user_decision_needed": "",
            "ready_for_implementation": False,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
)
decision_log

# %% [markdown]
# ## Go / No-Go Result
#
# State whether formal crawler implementation is ready. If not ready, list the next notebook investigation steps.
```
