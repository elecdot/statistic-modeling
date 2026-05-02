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

# %% [markdown]
# # Manual SRDI Text Measure Comparison
#
# This notebook compares the v0 title/abstract dictionary features with the
# full-text v1 dictionary features. It does not revise the dictionary and does
# not change any processed data.
#
# Purpose:
#
# - quantify how much full text changes policy-tool coverage;
# - check whether province-year aggregates are stable enough for DID handoff;
# - identify broad full-text terms that need cautious interpretation;
# - produce a compact recommendation table for choosing the paper-facing text
#   measure.
#
# Interpretation rule:
#
# - v0 = title + abstract baseline;
# - v1 = title + full text candidate main measure;
# - both are transparent dictionary proxy variables, not final human labels.

# %%
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# %matplotlib inline

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

ROW_V0_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_v0.csv"
ROW_V1_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv"
PY_V0_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_v0.csv"
PY_V1_PATH = ROOT / "data" / "processed" / "province_year_srdi_text_features_fulltext_v1.csv"
DICT_V0_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_v0.csv"
DICT_V1_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv"

SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_comparison_summary_v1.csv"
ROW_TRANSITION_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_row_transitions_v1.csv"
PY_CORRELATION_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_province_year_correlations_v1.csv"
PY_DELTA_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_province_year_deltas_v1.csv"
TERM_DELTA_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_term_coverage_delta_v1.csv"
HIGH_COVERAGE_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_fulltext_high_coverage_terms_v1.csv"
RECOMMENDATION_OUTPUT = OUTPUT_DIR / "manual_srdi_text_measure_recommendation_v1.csv"

NO_HIT_FIG = OUTPUT_DIR / "manual_srdi_fig_text_measure_no_hit_comparison_v1.png"
TOOL_SHARE_FIG = OUTPUT_DIR / "manual_srdi_fig_text_measure_tool_share_comparison_v1.png"
CORRELATION_FIG = OUTPUT_DIR / "manual_srdi_fig_text_measure_province_year_correlation_v1.png"
HIGH_COVERAGE_FIG = OUTPUT_DIR / "manual_srdi_fig_text_measure_high_coverage_terms_v1.png"

TOOL_CATEGORIES = ["supply", "demand", "environment"]
SHARE_COLUMNS = [f"{category}_tool_policy_share" for category in TOOL_CATEGORIES]
COUNT_COLUMNS = [f"{category}_tool_policy_count" for category in TOOL_CATEGORIES]
HIGH_COVERAGE_SHARE_THRESHOLD = 0.25
FIG_DPI = 300


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save figures with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


def bool_series(series: pd.Series) -> pd.Series:
	"""Read bool-like CSV columns robustly."""
	if series.dtype == bool:
		return series
	return series.astype(str).str.lower().isin({"true", "1", "yes"})


# %% [markdown]
# ## 1. Load Inputs
#
# The v0 and v1 row-level tables share `policy_id`, so row-level transitions
# can be audited directly. Province-year tables share the same balanced 31 x 6
# panel.

# %%
row_v0 = pd.read_csv(ROW_V0_PATH)
row_v1 = pd.read_csv(ROW_V1_PATH)
py_v0 = pd.read_csv(PY_V0_PATH)
py_v1 = pd.read_csv(PY_V1_PATH)
dict_v0 = pd.read_csv(DICT_V0_PATH)
dict_v1 = pd.read_csv(DICT_V1_PATH)

for frame in [row_v0, row_v1]:
	for column in ["has_any_policy_tool", "has_supply_tool", "has_demand_tool", "has_environment_tool"]:
		frame[column] = bool_series(frame[column])

load_checks = pd.DataFrame(
	[
		{"artifact": "row_v0", "rows": len(row_v0), "columns": row_v0.shape[1]},
		{"artifact": "row_v1", "rows": len(row_v1), "columns": row_v1.shape[1]},
		{"artifact": "province_year_v0", "rows": len(py_v0), "columns": py_v0.shape[1]},
		{"artifact": "province_year_v1", "rows": len(py_v1), "columns": py_v1.shape[1]},
		{"artifact": "dictionary_v0", "rows": len(dict_v0), "columns": dict_v0.shape[1]},
		{"artifact": "dictionary_v1", "rows": len(dict_v1), "columns": dict_v1.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Row-Level Coverage Transitions
#
# The main row-level question is whether full text recovers previously no-hit
# policies, and whether category-specific hits become nearly universal.

# %%
row_compare_columns = [
	"policy_id",
	"province",
	"jurisdiction_type",
	"publish_year",
	"title",
	"has_any_policy_tool",
	"has_supply_tool",
	"has_demand_tool",
	"has_environment_tool",
	"policy_tool_category_count",
]
row_compare = row_v0[row_compare_columns].merge(
	row_v1[row_compare_columns + ["full_text_len"]],
	on=["policy_id", "province", "jurisdiction_type", "publish_year", "title"],
	how="inner",
	suffixes=("_v0", "_v1"),
	validate="one_to_one",
)

transition_rows = []
for category in ["any", *TOOL_CATEGORIES]:
	v0_column = "has_any_policy_tool_v0" if category == "any" else f"has_{category}_tool_v0"
	v1_column = "has_any_policy_tool_v1" if category == "any" else f"has_{category}_tool_v1"
	crosstab = pd.crosstab(row_compare[v0_column], row_compare[v1_column])
	for v0_value in [False, True]:
		for v1_value in [False, True]:
			transition_rows.append(
				{
					"category": category,
					"v0_hit": v0_value,
					"v1_hit": v1_value,
					"records": int(crosstab.loc[v0_value, v1_value]) if v0_value in crosstab.index and v1_value in crosstab.columns else 0,
				}
			)
row_transitions = pd.DataFrame(transition_rows)
row_transitions.to_csv(ROW_TRANSITION_OUTPUT, index=False)
row_transitions

# %%
coverage_summary_rows = []
for label, frame in [("v0_title_abstract", row_v0), ("v1_full_text", row_v1)]:
	coverage_summary_rows.append(
		{
			"measure": label,
			"metric": "any_tool_hit_records",
			"value": int(frame["has_any_policy_tool"].sum()),
			"share": float(frame["has_any_policy_tool"].mean()),
		}
	)
	coverage_summary_rows.append(
		{
			"measure": label,
			"metric": "no_tool_hit_records",
			"value": int((~frame["has_any_policy_tool"]).sum()),
			"share": float((~frame["has_any_policy_tool"]).mean()),
		}
	)
	for category in TOOL_CATEGORIES:
		column = f"has_{category}_tool"
		coverage_summary_rows.append(
			{
				"measure": label,
				"metric": f"{category}_tool_hit_records",
				"value": int(frame[column].sum()),
				"share": float(frame[column].mean()),
			}
		)
coverage_summary = pd.DataFrame(coverage_summary_rows)

recovered_no_hit = row_compare.loc[~row_compare["has_any_policy_tool_v0"] & row_compare["has_any_policy_tool_v1"]]
still_no_hit = row_compare.loc[~row_compare["has_any_policy_tool_v0"] & ~row_compare["has_any_policy_tool_v1"]]

summary = pd.DataFrame(
	[
		{"metric": "policy_records_compared", "value": len(row_compare), "note": "Matched policy_id rows in v0 and full-text v1."},
		{"metric": "v0_no_tool_hit_records", "value": int((~row_compare["has_any_policy_tool_v0"]).sum()), "note": "No supply/demand/environment hit in title + abstract."},
		{"metric": "v1_no_tool_hit_records", "value": int((~row_compare["has_any_policy_tool_v1"]).sum()), "note": "No supply/demand/environment hit in title + full text."},
		{"metric": "v0_no_hit_recovered_by_v1", "value": len(recovered_no_hit), "note": "Rows missed by v0 but hit by full-text v1."},
		{"metric": "still_no_hit_after_v1", "value": len(still_no_hit), "note": "Rows missed by both v0 and full-text v1."},
	]
)
summary.to_csv(SUMMARY_OUTPUT, index=False)
summary

# %% [markdown]
# ## 3. Province-Year Stability
#
# For DID handoff, row-level recovery is less important than whether
# province-year aggregates remain stable. This section compares count and share
# variables across the balanced 31 x 6 province-year panel.

# %%
py_compare = py_v0.merge(
	py_v1,
	on=["province", "publish_year"],
	how="inner",
	suffixes=("_v0", "_v1"),
	validate="one_to_one",
)

correlation_rows = []
for column in [*COUNT_COLUMNS, *SHARE_COLUMNS, "avg_tool_category_count"]:
	v0_column = f"{column}_v0"
	v1_column = f"{column}_v1"
	correlation_rows.append(
		{
			"variable": column,
			"pearson_corr": py_compare[[v0_column, v1_column]].corr().iloc[0, 1],
			"spearman_corr": py_compare[[v0_column, v1_column]].rank().corr().iloc[0, 1],
			"v0_mean": py_compare[v0_column].mean(),
			"v1_mean": py_compare[v1_column].mean(),
			"mean_delta_v1_minus_v0": (py_compare[v1_column] - py_compare[v0_column]).mean(),
			"max_abs_delta": (py_compare[v1_column] - py_compare[v0_column]).abs().max(),
		}
	)
province_year_correlations = pd.DataFrame(correlation_rows)
province_year_correlations.to_csv(PY_CORRELATION_OUTPUT, index=False)
province_year_correlations

# %%
delta_columns = ["province", "publish_year", "srdi_policy_count_v0"]
province_year_deltas = py_compare[delta_columns].rename(columns={"srdi_policy_count_v0": "srdi_policy_count"}).copy()
for column in [*COUNT_COLUMNS, *SHARE_COLUMNS, "avg_tool_category_count"]:
	province_year_deltas[f"{column}_v0"] = py_compare[f"{column}_v0"]
	province_year_deltas[f"{column}_v1"] = py_compare[f"{column}_v1"]
	province_year_deltas[f"{column}_delta"] = py_compare[f"{column}_v1"] - py_compare[f"{column}_v0"]
province_year_deltas.to_csv(PY_DELTA_OUTPUT, index=False)
province_year_deltas.head()

# %% [markdown]
# ## 4. Term-Level Coverage Change
#
# Full text should improve recall, but broad terms can become too common. Terms
# crossing the 25% record-hit threshold are flagged for cautious interpretation.

# %%
term_delta = dict_v0.merge(
	dict_v1,
	on=["category", "term"],
	how="inner",
	suffixes=("_v0", "_v1"),
	validate="one_to_one",
)
term_delta["records_hit_delta"] = term_delta["records_hit_v1"] - term_delta["records_hit_v0"]
term_delta["record_hit_share_delta"] = term_delta["record_hit_share_v1"] - term_delta["record_hit_share_v0"]
term_delta["became_high_coverage_in_v1"] = (
	(term_delta["record_hit_share_v0"] < HIGH_COVERAGE_SHARE_THRESHOLD)
	& (term_delta["record_hit_share_v1"] >= HIGH_COVERAGE_SHARE_THRESHOLD)
)
term_delta["high_coverage_in_v1"] = term_delta["record_hit_share_v1"] >= HIGH_COVERAGE_SHARE_THRESHOLD
term_delta = term_delta.sort_values(["record_hit_share_v1", "records_hit_delta"], ascending=[False, False])
term_delta.to_csv(TERM_DELTA_OUTPUT, index=False)

high_coverage_terms = term_delta.loc[term_delta["high_coverage_in_v1"]].copy()
high_coverage_terms.to_csv(HIGH_COVERAGE_OUTPUT, index=False)
high_coverage_terms.head(20)

# %% [markdown]
# ## 5. Recommendation Table
#
# The recommendation separates measurement choice from causal interpretation.
# Full text is stronger as a main aggregate proxy, while v0 remains useful as a
# robustness benchmark because it is less exposed to broad-term saturation.

# %%
v0_no_hit = int((~row_compare["has_any_policy_tool_v0"]).sum())
v1_no_hit = int((~row_compare["has_any_policy_tool_v1"]).sum())
high_coverage_v0 = int((dict_v0["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD).sum())
high_coverage_v1 = int((dict_v1["record_hit_share"] >= HIGH_COVERAGE_SHARE_THRESHOLD).sum())
min_share_corr = province_year_correlations.loc[
	province_year_correlations["variable"].isin(SHARE_COLUMNS),
	"pearson_corr",
].min()

recommendation = pd.DataFrame(
	[
		{
			"decision_area": "main_text_measure",
			"recommendation": "Use full-text v1 for the main province-year text-intensity proxy.",
			"evidence": f"Full-text v1 reduces no-hit records from {v0_no_hit} to {v1_no_hit}.",
			"caution": "Do not interpret row-level dictionary hits as manual labels.",
		},
		{
			"decision_area": "robustness_measure",
			"recommendation": "Retain title/abstract v0 as a robustness and method-comparison measure.",
			"evidence": "v0 is less exposed to broad full-text terms and is already documented.",
			"caution": "v0 has lower recall and leaves more no-hit records.",
		},
		{
			"decision_area": "broad_term_interpretation",
			"recommendation": "Interpret full-text tool variables as aggregate intensity proxies.",
			"evidence": f"High-coverage terms increase from {high_coverage_v0} to {high_coverage_v1}.",
			"caution": "Avoid narrative claims based on individual broad terms without examples.",
		},
		{
			"decision_area": "did_handoff",
			"recommendation": "Build DID candidates from v1 count/share variables and keep v0 alternatives.",
			"evidence": f"Minimum Pearson correlation among v0/v1 tool shares is {min_share_corr:.3f}.",
			"caution": "Check multicollinearity before entering multiple tool shares together.",
		},
	]
)
recommendation.to_csv(RECOMMENDATION_OUTPUT, index=False)
recommendation

# %% [markdown]
# ## 6. Figures

# %%
no_hit_plot = coverage_summary.loc[coverage_summary["metric"].eq("no_tool_hit_records")].copy()
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(no_hit_plot["measure"], no_hit_plot["value"], color=["#8a8f98", "#4777b2"])
ax.set_title("No-Tool-Hit Records: v0 vs Full-Text v1")
ax.set_xlabel("Text measure")
ax.set_ylabel("Policy records")
ax.grid(axis="y", alpha=0.25)
for patch in ax.patches:
	ax.annotate(f"{patch.get_height():.0f}", (patch.get_x() + patch.get_width() / 2, patch.get_height()), ha="center", va="bottom", fontsize=9)
save_figure(fig, NO_HIT_FIG)
fig

# %%
tool_share_plot = coverage_summary.loc[coverage_summary["metric"].str.endswith("_tool_hit_records")].copy()
tool_share_plot["category"] = tool_share_plot["metric"].str.replace("_tool_hit_records", "", regex=False)
tool_share_wide = tool_share_plot.pivot(index="category", columns="measure", values="share").reindex(TOOL_CATEGORIES)

fig, ax = plt.subplots(figsize=(7, 4.5))
x = np.arange(len(tool_share_wide.index))
width = 0.35
ax.bar(x - width / 2, tool_share_wide["v0_title_abstract"], width, label="v0 title/abstract", color="#8a8f98")
ax.bar(x + width / 2, tool_share_wide["v1_full_text"], width, label="v1 full text", color="#4777b2")
ax.set_title("Policy-Tool Hit Shares by Text Measure")
ax.set_xlabel("Tool category")
ax.set_ylabel("Share of policy records")
ax.set_xticks(x)
ax.set_xticklabels(["Supply", "Demand", "Environment"])
ax.set_ylim(0, 1.05)
ax.grid(axis="y", alpha=0.25)
ax.legend()
save_figure(fig, TOOL_SHARE_FIG)
fig

# %%
fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
for ax, category in zip(axes, TOOL_CATEGORIES, strict=True):
	v0_col = f"{category}_tool_policy_share_v0"
	v1_col = f"{category}_tool_policy_share_v1"
	ax.scatter(py_compare[v0_col], py_compare[v1_col], alpha=0.7, s=22, color="#4777b2")
	ax.plot([0, 1], [0, 1], color="#444444", linestyle="--", linewidth=1)
	ax.set_title(category.capitalize())
	ax.set_xlabel("v0 share")
	ax.grid(alpha=0.25)
axes[0].set_ylabel("v1 share")
fig.suptitle("Province-Year Tool Shares: v0 vs Full-Text v1", y=1.03)
save_figure(fig, CORRELATION_FIG)
fig

# %%
plot_high_terms = high_coverage_terms.head(20).sort_values("record_hit_share_v1", ascending=True).copy()
plot_high_terms["plot_label"] = [
	f"{category} term {rank}"
	for rank, category in enumerate(plot_high_terms["category"], start=1)
]
fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(plot_high_terms["plot_label"], plot_high_terms["record_hit_share_v1"], color="#4777b2")
ax.set_title("Top Full-Text High-Coverage Dictionary Terms")
ax.set_xlabel("Share of policy records hit")
ax.set_ylabel("Dictionary term index")
ax.grid(axis="x", alpha=0.25)
save_figure(fig, HIGH_COVERAGE_FIG)
fig

# %% [markdown]
# ## 7. Reading Notes
#
# Full-text v1 is the better candidate for main paper-facing text intensity
# because it nearly eliminates no-hit rows. The cost is broader coverage:
# full-text dictionary hits are closer to aggregate policy-language intensity
# than precise document-level policy-tool labels.
#
# A reasonable next step is to build the DID handoff table from full-text v1
# province-year count/share variables, while retaining v0 title/abstract
# variables as robustness alternatives.
