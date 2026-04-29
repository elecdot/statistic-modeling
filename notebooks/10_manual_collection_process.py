# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.1
#   kernelspec:
#     display_name: statistic-modeling (3.11.14)
#     language: python
#     name: python3
# ---

# %%
from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

DATA_DIR = Path("data") if Path("data").exists() else Path("../data")
target = DATA_DIR / "interim" / "labeled_policy_text_manual_collection.xlsx"

target

# %% [markdown]
#

# %%
# Read with no header first, then promote row 0 to column names.
df_raw = pd.read_excel(target, header=None)
headers = df_raw.iloc[0].astype("string").str.strip().tolist()
df = df_raw.iloc[1:].copy()
df.columns = headers

from urllib.parse import urlsplit, urlunsplit

required_cols = ["province", "source_url"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise KeyError(f"Missing required columns: {missing}")

# 手动调整这个值：保留 source_url 从左到右的前几段
# 例如 3 表示保留 a/b/c，4 表示保留 a/b/c/d
keep_segments = 0

def truncate_source_url(url: str, keep_segments: int = keep_segments) -> str:
    if pd.isna(url):
        return pd.NA
    text = str(url).strip().strip("/")
    if not text:
        return pd.NA
    parsed = urlsplit(text)
    if parsed.scheme and parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if keep_segments <= 0:
            return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        truncated_path = "/".join(parts[:keep_segments])
        if truncated_path:
            truncated_path = "/" + truncated_path
        return urlunsplit((parsed.scheme, parsed.netloc, truncated_path, "", ""))
    parts = [part for part in text.split("/") if part]
    if keep_segments <= 0:
        return pd.NA
    return "/".join(parts[:keep_segments]) if len(parts) >= keep_segments else "/".join(parts)

subset = df[required_cols].copy()
for col in required_cols:
    subset[col] = subset[col].astype("string").str.strip()

subset = subset.dropna(subset=required_cols)
subset = subset[(subset["province"] != "") & (subset["source_url"] != "")].copy()
subset["source_url"] = subset["source_url"].map(truncate_source_url)
subset = subset.dropna(subset=["source_url"])
subset = subset[subset["source_url"] != ""]

result = (
    subset.groupby(["province", "source_url"], dropna=False)
    .size()
    .reset_index(name="count")
    .sort_values(["province", "count", "source_url"], ascending=[True, False, True], ignore_index=True)
)

result
result.to_csv(DATA_DIR / "tmp" / "province_source_url_counts.csv", index=False)


# %%
