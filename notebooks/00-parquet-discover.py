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
import pandas as pd

# %% [markdown]
# # What is `.parquet`
#
# `.parquet` is a columnar storage data. Optimize for large data manipulate, faster than row storage like `.csv` and `.excel` which is easy to read but break the spatial coherence through different meta-data.
#
# `.parquet` support features like *predicate pushdown* and *column pruning*

# %% [markdown]
# ## Read
#
# >[!tip] Do not read the whole table unless you are sure you need it

# %%
df = pd.read_parquet("../data/interim/policy_text_manifest.parquet")
print(df.head())

# %%
df = pd.read_parquet(
    "../data/interim/policy_text_manifest.parquet",
    columns=["policy_id", "title", "published_at"]
)
print(df)

# %% [markdown]
# ## Write

# %% [markdown]
# >[!warning] As type before writing.
# >This avoid pitfalls:
# >Leading zero is been drop (if its treated as int)

# %%
df["policy_id"] = df["policy_id"].astype(str)
df["published_at"] = pd.to_datetime(df["published_at"])
print(df.dtypes)

# %%
# In practice, pandas indexes are not often used in data science.
#df.to_parquet("xxx.parquet", index=False, engine="pyarrow")

# %%
# Partitioned Parquet Dataset
#df.to_parquet(
#   "../data/interim/",
#   partition_cols=["published_at"],
#   engine="pyarrow"
#)

# %% [markdown]
# This would result in:
# ```
# data/
#   published_at=2015/
#   published_at=2016/
#   ...
# ```

# %% [markdown]
# # Go Deeper
#
# ## Row Group
#
# Parquet store data per "row group" (e.g., typically 64MB per rq), which is benefit for parallel computing, spark system (save as node), fast batch manipulating:
# ```
# .parquet
#  ├─ Row Group 1 (1-64MB)
#  │   ├─ firm_id column chunk
#  │   ├─ year column chunk
#  │   └─ patent column chunk
#  ├─ Row Group 2 (65-128MB)
#  │   ├─ ...
#  ```
# Each rq has its own metadata (e.g., max/min). This allow a strategy called "predicate pushdown", i.e., fast search based on the metadata.
# Moreover, there are pages under each row group:
# ```
# Row Group
#   ├── Column Chunk
#        ├── Page 1
#        ├── Page 2
#        └── ...
# ```
# Each page is an independent **compression and encoding** (RLE / dictionary) unit.
# Parquet will chose which encoding is better for the row (e.g., dictionary encoding / run-length encoding).
# For instance, if "province" has only a few of duplicate value, then Parquet will use "dictionary encoding"
#
# >[!tip] Compare with "Partition", "Row Group" play a role on: precisely file-internal control, automatically optimize, IO computing friendly.

# %% [markdown]
# ### Work With Row Group
#
# **Inspect the row group**:

# %%
import pyarrow.parquet as pq

pq_file = pq.ParquetFile("../data/interim/policy_text_manifest.parquet")
print(pq_file.metadata)

# %%
for  i in range(pq_file.num_row_groups):
    print(pq_file.metadata.row_group(i))

# %% [markdown]
#
# **Split row group by sort first**:

# %%
df = df.sort_values(["published_at", "policy_id"], ascending=[False, False])
print(df.head())

# %% [markdown]
# Then we can write the sorted DataFrame to Parquet, which will maintain the order of rows within each partition.

# %%
# df.to_parquet(
#     "file.parquet",
#     engine="pyarrow",
#     row_group_size=100_000
# )
