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
# # Manual SRDI Full-Text Keyword Quality
#
# This notebook audits the full-text v1 dictionary terms used for
# supply/demand/environment policy-tool proxies.
#
# Motivation:
#
# - full-text v1 nearly eliminates no-hit records;
# - supply and environment shares approach the any-tool share;
# - demand share rises sharply relative to v0;
# - several terms hit more than 80% of policy records.
#
# The goal is not to delete keywords automatically. The goal is to document how
# the dictionary should be interpreted in the paper: full-text keyword features
# are strong aggregate policy-intensity proxies, but broad high-coverage terms
# should not be read as precise row-level labels.

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

ROW_FEATURES_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_text_features_fulltext_v1.csv"
DICT_COVERAGE_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_fulltext_v1.csv"
V0_DICT_COVERAGE_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_coverage_v0.csv"
TEXT_MEASURE_RECOMMENDATION_PATH = ROOT / "outputs" / "manual_srdi_text_measure_recommendation_v1.csv"

SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_summary_v1.csv"
TERM_FLAGS_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_term_flags_v1.csv"
CATEGORY_OVERLAP_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_category_overlap_v1.csv"
CATEGORY_COMPARISON_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_category_comparison_v1.csv"
INTERPRETATION_OUTPUT = OUTPUT_DIR / "manual_srdi_fulltext_keyword_quality_interpretation_notes_v1.csv"

COVERAGE_BAND_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_coverage_bands_v1.png"
CATEGORY_SHARE_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_category_shares_v1.png"
OVERLAP_FIG = OUTPUT_DIR / "manual_srdi_fig_fulltext_keyword_overlap_v1.png"

TOOL_CATEGORIES = ["supply", "demand", "environment"]
SATURATED_THRESHOLD = 0.80
HIGH_THRESHOLD = 0.50
MODERATE_THRESHOLD = 0.25
LOW_THRESHOLD = 0.05
FIG_DPI = 300

BROAD_MEANING_TERMS = {
	"财政",
	"研发",
	"创新",
	"人才",
	"培训",
	"服务平台",
	"公共服务",
	"载体",
	"空间",
	"采购",
	"供需",
	"对接",
	"场景",
	"银行",
	"保险",
	"基金",
	"标准",
	"认定",
	"评价",
	"产业链",
	"供应链",
	"数字化",
	"融资",
	"贷款",
}

SHORT_TERM_REVIEW_LENGTH = 2


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


def coverage_band(share: float) -> str:
	"""Assign a coverage band used for interpretation diagnostics."""
	if share >= SATURATED_THRESHOLD:
		return "saturated_gte_80pct"
	if share >= HIGH_THRESHOLD:
		return "high_50_80pct"
	if share >= MODERATE_THRESHOLD:
		return "moderate_25_50pct"
	if share >= LOW_THRESHOLD:
		return "low_5_25pct"
	return "rare_lt_5pct"


# %% [markdown]
# ## 1. Load Inputs

# %%
row_features = pd.read_csv(ROW_FEATURES_PATH)
dictionary = pd.read_csv(DICT_COVERAGE_PATH)
dictionary_v0 = pd.read_csv(V0_DICT_COVERAGE_PATH)
recommendation = pd.read_csv(TEXT_MEASURE_RECOMMENDATION_PATH)

for column in ["has_supply_tool", "has_demand_tool", "has_environment_tool", "has_any_policy_tool"]:
	row_features[column] = bool_series(row_features[column])

load_checks = pd.DataFrame(
	[
		{"artifact": "fulltext_row_features", "rows": len(row_features), "columns": row_features.shape[1]},
		{"artifact": "fulltext_dictionary_coverage", "rows": len(dictionary), "columns": dictionary.shape[1]},
		{"artifact": "v0_dictionary_coverage", "rows": len(dictionary_v0), "columns": dictionary_v0.shape[1]},
		{"artifact": "text_measure_recommendation", "rows": len(recommendation), "columns": recommendation.shape[1]},
	]
)
load_checks

# %% [markdown]
# ## 2. Category-Level Saturation
#
# Supply and environment are almost universal in full-text v1. This is not a
# processing error. It reflects that full policy texts frequently discuss
# innovation, finance, standards, platforms, services, and institutional
# arrangements even when the title/abstract is narrower.

# %%
category_rows = []
for category in TOOL_CATEGORIES:
	indicator = f"has_{category}_tool"
	category_rows.append(
		{
			"category": category,
			"records_hit": int(row_features[indicator].sum()),
			"record_hit_share": float(row_features[indicator].mean()),
			"mean_hit_count": float(row_features[f"{category}_tool_hit_count"].mean()),
			"median_hit_count": float(row_features[f"{category}_tool_hit_count"].median()),
			"max_hit_count": int(row_features[f"{category}_tool_hit_count"].max()),
		}
	)
category_rows.append(
	{
		"category": "any_tool",
		"records_hit": int(row_features["has_any_policy_tool"].sum()),
		"record_hit_share": float(row_features["has_any_policy_tool"].mean()),
		"mean_hit_count": pd.NA,
		"median_hit_count": pd.NA,
		"max_hit_count": pd.NA,
	}
)
category_comparison = pd.DataFrame(category_rows)
category_comparison["distance_from_any_share"] = (
	category_comparison.loc[category_comparison["category"].eq("any_tool"), "record_hit_share"].item()
	- category_comparison["record_hit_share"]
)
category_comparison.to_csv(CATEGORY_COMPARISON_OUTPUT, index=False)
category_comparison

# %% [markdown]
# ## 3. Term-Level Quality Flags
#
# Term flags are interpretation flags, not deletion rules.

# %%
term_flags = dictionary.merge(
	dictionary_v0[["category", "term", "record_hit_share", "records_hit"]].rename(
		columns={"record_hit_share": "record_hit_share_v0", "records_hit": "records_hit_v0"}
	),
	on=["category", "term"],
	how="left",
	validate="one_to_one",
)
term_flags["coverage_band"] = term_flags["record_hit_share"].map(coverage_band)
term_flags["term_length"] = term_flags["term"].str.len()
term_flags["is_broad_meaning_term"] = term_flags["term"].isin(BROAD_MEANING_TERMS)
term_flags["is_short_term"] = term_flags["term_length"] <= SHORT_TERM_REVIEW_LENGTH
term_flags["is_saturated"] = term_flags["record_hit_share"] >= SATURATED_THRESHOLD
term_flags["is_high_coverage"] = term_flags["record_hit_share"] >= HIGH_THRESHOLD
term_flags["became_high_coverage_from_v0"] = (
	(term_flags["record_hit_share_v0"] < MODERATE_THRESHOLD)
	& (term_flags["record_hit_share"] >= MODERATE_THRESHOLD)
)
term_flags["share_delta_from_v0"] = term_flags["record_hit_share"] - term_flags["record_hit_share_v0"]


def interpretation_role(row: pd.Series) -> str:
	"""Assign a compact interpretation role for paper drafting."""
	if row["is_saturated"] or (row["is_high_coverage"] and row["is_broad_meaning_term"]):
		return "broad_intensity_signal"
	if row["record_hit_share"] >= MODERATE_THRESHOLD:
		return "common_tool_signal"
	if row["record_hit_share"] < LOW_THRESHOLD:
		return "rare_specific_signal"
	return "specific_tool_signal"


term_flags["interpretation_role"] = term_flags.apply(interpretation_role, axis=1)
term_flags["review_note"] = np.select(
	[
		term_flags["is_saturated"],
		term_flags["is_high_coverage"] & term_flags["is_broad_meaning_term"],
		term_flags["is_short_term"] & term_flags["is_broad_meaning_term"],
		term_flags["record_hit_share"] < LOW_THRESHOLD,
	],
	[
		"Very high full-text coverage; use mainly as aggregate intensity evidence.",
		"High-coverage broad term; avoid row-level label interpretation.",
		"Short broad term; inspect examples before qualitative claims.",
		"Rare term; useful as specific signal but contributes little to aggregate coverage.",
	],
	default="No special concern beyond standard dictionary-proxy interpretation.",
)
term_flags = term_flags.sort_values(["record_hit_share", "records_hit"], ascending=[False, False])
term_flags.to_csv(TERM_FLAGS_OUTPUT, index=False)
term_flags.head(20)

# %% [markdown]
# ## 4. Coverage-Band Summary

# %%
coverage_band_summary = (
	term_flags.groupby(["category", "coverage_band"])
	.size()
	.reset_index(name="terms")
)
coverage_band_summary["coverage_band"] = pd.Categorical(
	coverage_band_summary["coverage_band"],
	categories=["saturated_gte_80pct", "high_50_80pct", "moderate_25_50pct", "low_5_25pct", "rare_lt_5pct"],
	ordered=True,
)
coverage_band_summary = coverage_band_summary.sort_values(["category", "coverage_band"]).reset_index(drop=True)

summary = pd.DataFrame(
	[
		{"metric": "dictionary_terms", "value": len(term_flags), "note": "Total full-text dictionary terms."},
		{"metric": "saturated_terms_gte_80pct", "value": int(term_flags["is_saturated"].sum()), "note": "Terms hitting at least 80% of records."},
		{"metric": "high_coverage_terms_gte_50pct", "value": int(term_flags["is_high_coverage"].sum()), "note": "Terms hitting at least 50% of records."},
		{"metric": "moderate_plus_terms_gte_25pct", "value": int((term_flags["record_hit_share"] >= MODERATE_THRESHOLD).sum()), "note": "Terms hitting at least 25% of records."},
		{"metric": "rare_terms_lt_5pct", "value": int((term_flags["record_hit_share"] < LOW_THRESHOLD).sum()), "note": "Terms hitting fewer than 5% of records."},
		{"metric": "broad_meaning_terms", "value": int(term_flags["is_broad_meaning_term"].sum()), "note": "Terms flagged as broad by manual rule."},
		{"metric": "broad_intensity_signal_terms", "value": int(term_flags["interpretation_role"].eq("broad_intensity_signal").sum()), "note": "Terms best interpreted as aggregate intensity signals."},
		{"metric": "rare_specific_signal_terms", "value": int(term_flags["interpretation_role"].eq("rare_specific_signal").sum()), "note": "Rare but specific terms."},
	]
)
summary.to_csv(SUMMARY_OUTPUT, index=False)
summary

# %% [markdown]
# ## 5. Category Overlap
#
# Full-text category overlap is central to interpretation. If most records hit
# all three categories, category dummies are less informative than counts,
# shares, and relative intensity measures.

# %%
overlap_rows = []
overlap_definitions = {
	"any_tool": row_features["has_any_policy_tool"],
	"supply": row_features["has_supply_tool"],
	"demand": row_features["has_demand_tool"],
	"environment": row_features["has_environment_tool"],
	"supply_and_environment": row_features["has_supply_tool"] & row_features["has_environment_tool"],
	"supply_and_demand": row_features["has_supply_tool"] & row_features["has_demand_tool"],
	"demand_and_environment": row_features["has_demand_tool"] & row_features["has_environment_tool"],
	"all_three_categories": row_features["has_supply_tool"] & row_features["has_demand_tool"] & row_features["has_environment_tool"],
	"only_supply": row_features["has_supply_tool"] & ~row_features["has_demand_tool"] & ~row_features["has_environment_tool"],
	"only_demand": ~row_features["has_supply_tool"] & row_features["has_demand_tool"] & ~row_features["has_environment_tool"],
	"only_environment": ~row_features["has_supply_tool"] & ~row_features["has_demand_tool"] & row_features["has_environment_tool"],
	"no_tool": ~row_features["has_any_policy_tool"],
}
for group_name, mask in overlap_definitions.items():
	overlap_rows.append(
		{
			"group": group_name,
			"records": int(mask.sum()),
			"record_share": float(mask.mean()),
		}
	)
category_overlap = pd.DataFrame(overlap_rows)
category_overlap.to_csv(CATEGORY_OVERLAP_OUTPUT, index=False)
category_overlap

# %% [markdown]
# ## 6. Interpretation Notes

# %%
interpretation_notes = pd.DataFrame(
	[
		{
			"topic": "why_supply_environment_near_any",
			"finding": "Supply and environment full-text shares are close to the any-tool share.",
			"interpretation": "Full policy texts commonly contain general innovation, funding, platform, finance, standards, recognition, and ecosystem language. These are real policy-language signals but broad at row level.",
			"paper_wording": "Supply-side and environmental terms should be interpreted as aggregate policy-intensity proxies rather than mutually exclusive document labels.",
		},
		{
			"topic": "why_demand_rises",
			"finding": "Demand-side share rises sharply under full-text matching.",
			"interpretation": "Demand expressions such as market expansion, matching, scenarios, demonstration, export, exhibitions, and procurement are often in implementation clauses rather than titles or abstracts.",
			"paper_wording": "The full-text measure improves recall for demand-side tools, especially where demand support appears in implementation details.",
		},
		{
			"topic": "very_high_coverage_terms",
			"finding": "Some terms reach or exceed 80% record coverage.",
			"interpretation": "Terms such as innovation or standards may represent policy orientation rather than narrow instruments.",
			"paper_wording": "High-coverage terms are retained to capture policy-language intensity, but the analysis should emphasize province-year aggregates and avoid term-level causal claims.",
		},
		{
			"topic": "modeling_implication",
			"finding": "Category dummies are saturated; counts and shares carry more usable variation.",
			"interpretation": "For DID handoff, use province-year counts, hit counts, shares, and possibly relative composition measures instead of row-level binary labels.",
			"paper_wording": "The text-mining variables enter the empirical design as province-year policy-intensity and policy-orientation proxies.",
		},
	]
)
interpretation_notes.to_csv(INTERPRETATION_OUTPUT, index=False)
interpretation_notes

# %% [markdown]
# ## 7. Figures

# %%
band_order = ["saturated_gte_80pct", "high_50_80pct", "moderate_25_50pct", "low_5_25pct", "rare_lt_5pct"]
band_plot = (
	coverage_band_summary.pivot(index="category", columns="coverage_band", values="terms")
	.reindex(index=TOOL_CATEGORIES)
	.reindex(columns=band_order)
	.fillna(0)
)
fig, ax = plt.subplots(figsize=(9, 5))
bottom = np.zeros(len(band_plot.index))
colors = ["#9b3f3f", "#d0903f", "#4777b2", "#5f9f6e", "#8a8f98"]
for color, band in zip(colors, band_order, strict=True):
	values = band_plot[band].to_numpy()
	ax.bar(band_plot.index, values, bottom=bottom, label=band.replace("_", " "), color=color)
	bottom += values
ax.set_title("Full-Text Dictionary Terms by Coverage Band")
ax.set_xlabel("Tool category")
ax.set_ylabel("Dictionary terms")
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.25)
save_figure(fig, COVERAGE_BAND_FIG)
fig

# %%
fig, ax = plt.subplots(figsize=(7, 4.5))
plot_category = category_comparison.sort_values("record_hit_share", ascending=False)
ax.bar(plot_category["category"], plot_category["record_hit_share"], color=["#333333", "#4777b2", "#5f9f6e", "#d0903f"])
ax.set_title("Full-Text Category Hit Shares")
ax.set_xlabel("Category")
ax.set_ylabel("Share of policy records")
ax.set_ylim(0, 1.05)
ax.grid(axis="y", alpha=0.25)
save_figure(fig, CATEGORY_SHARE_FIG)
fig

# %%
plot_overlap = category_overlap.loc[
	category_overlap["group"].isin(["all_three_categories", "supply_and_environment", "supply_and_demand", "demand_and_environment", "no_tool"])
].sort_values("record_share", ascending=True)
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.barh(plot_overlap["group"].str.replace("_", " "), plot_overlap["record_share"], color="#4777b2")
ax.set_title("Full-Text Tool Category Overlap")
ax.set_xlabel("Share of policy records")
ax.set_ylabel("Overlap group")
ax.set_xlim(0, 1.05)
ax.grid(axis="x", alpha=0.25)
save_figure(fig, OVERLAP_FIG)
fig

# %% [markdown]
# ## 8. Output Checks

# %%
output_checks = pd.DataFrame(
	[
		{"check": "dictionary_terms", "value": len(term_flags), "expected": 85},
		{"check": "saturated_terms", "value": int(term_flags["is_saturated"].sum()), "expected": 2},
		{"check": "moderate_plus_terms", "value": int((term_flags["record_hit_share"] >= MODERATE_THRESHOLD).sum()), "expected": 41},
		{"check": "any_tool_share", "value": category_comparison.loc[category_comparison["category"].eq("any_tool"), "record_hit_share"].item(), "expected": "near 1"},
		{"check": "no_tool_records", "value": int(category_overlap.loc[category_overlap["group"].eq("no_tool"), "records"].item()), "expected": 2},
	]
)
output_checks
