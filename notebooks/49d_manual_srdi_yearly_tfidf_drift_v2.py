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
# # Manual SRDI Yearly TF-IDF Drift v2
#
# This notebook extends the classified-record TF-IDF interpretability layer to a
# year-by-year diagnostic. Its goal is to support paper-facing discussion of
# policy-language evolution and to audit whether the 2019 supplementary corpus
# behaves coherently within the 2019-2024 v2 window.
#
# Scope:
#
# - input: v2 MacBERT classified policy records and v2 full-text policy corpus;
# - method: reviewed domain-phrase TF-IDF by `publish_year x label`;
# - outputs: year-label summary, top terms, drift audit, and figures;
# - stop point: no new DID variables, no final policy-side panel mutation, no
#   enterprise merge, and no DID estimate.

# %%
from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# %matplotlib inline

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
OUTPUT_DIR = ROOT / "outputs"

CLASSIFIED_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_classified_fulltext_v2.csv"
CORPUS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v2.csv"
LABEL_RULE_PATH = ROOT / "configs" / "manual_srdi_label_rule_keywords_v1.csv"
DICTIONARY_PATH = ROOT / "outputs" / "manual_policy_srdi_tool_dictionary_fulltext_v2.csv"

YEAR_LABEL_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_year_label_summary_v2.csv"
TOP_TERMS_BY_YEAR_LABEL_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_top_terms_by_year_label_v2.csv"
YEARLY_DRIFT_AUDIT_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_yearly_drift_audit_v2.csv"
YEARLY_INTERPRETATION_NOTES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_yearly_interpretation_notes_v2.csv"

YEARLY_TOOL_TERMS_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_tfidf_yearly_tool_terms_v2.png"
YEARLY_DRIFT_HEATMAP_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_tfidf_yearly_drift_heatmap_v2.png"

YEARS = list(range(2019, 2025))
LABELS = ["supply", "demand", "environment", "other"]
TOOL_LABELS = ["supply", "demand", "environment"]
LABEL_PROBABILITY = {
	"supply": "p_supply",
	"demand": "p_demand",
	"environment": "p_environment",
	"other": "p_other",
}
LABEL_NAME = {
	"supply": "Supply",
	"demand": "Demand",
	"environment": "Environment",
	"other": "Other",
}
HIGH_CONFIDENCE_THRESHOLD = {
	"supply": 0.75,
	"demand": 0.75,
	"environment": 0.75,
	"other": 0.60,
}
SCOPE_FILTERS = {
	"all_records": None,
	"local_only": "local",
}
FIG_DPI = 300
TOP_N_TERMS = 15
MIN_INTERPRETABLE_DOCS = 10

CJK_FONT_PATHS = [
	Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
	Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
	Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
]

COMMON_STOP_TERMS = {
	"专精特新",
	"小巨人",
	"中小企业",
	"企业",
	"政策",
	"工作",
	"发展",
	"支持",
	"推进",
	"推动",
	"促进",
	"加强",
	"提升",
	"开展",
	"有关",
	"实施",
	"管理",
	"通知",
	"创新",
}

OTHER_AUDIT_TERMS = {
	"申报",
	"公示",
	"名单",
	"公布",
	"推荐",
	"复核",
	"转发",
	"解读",
	"会议",
	"工作动态",
	"组织申报",
	"名单公示",
	"申报通知",
	"入库培育",
}


def bool_series(series: pd.Series) -> pd.Series:
	"""Read bool-like CSV columns robustly."""
	if series.dtype == bool:
		return series
	return series.astype(str).str.lower().isin({"true", "1", "yes"})


def configure_plot_fonts() -> None:
	"""Use an available CJK font so Chinese TF-IDF terms render in figures."""
	for font_path in CJK_FONT_PATHS:
		if font_path.exists():
			font_manager.fontManager.addfont(str(font_path))
			font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
			plt.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
			plt.rcParams["font.family"] = "sans-serif"
			plt.rcParams["axes.unicode_minus"] = False
			return
	plt.rcParams["axes.unicode_minus"] = False


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save a Matplotlib figure with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


def normalize_text(value: object) -> str:
	"""Normalize text for dependency-light policy phrase matching."""
	if pd.isna(value):
		return ""
	text = str(value)
	text = re.sub(r"\s+", "", text)
	text = re.sub(r"[，。；：、“”‘’（）()《》【】\[\]{}<>！？!?,.;:：/\\|·\-—_+=*~`\"']", "", text)
	return text


def clean_term(value: object) -> str:
	"""Normalize one vocabulary term and drop unusable fragments."""
	term = normalize_text(value)
	if len(term) < 2:
		return ""
	if term in COMMON_STOP_TERMS:
		return ""
	return term


def build_vocabulary(label_rules: pd.DataFrame, dictionary: pd.DataFrame) -> pd.DataFrame:
	"""Build a reviewed domain-phrase vocabulary for yearly TF-IDF interpretation."""
	terms: list[dict[str, str]] = []

	for _, row in label_rules.iterrows():
		term = clean_term(row["term"])
		if not term:
			continue
		keep_for_interpretation = str(row.get("keep_for_interpretation", "")).lower() == "true"
		if keep_for_interpretation or row.get("category") == "other" or term in OTHER_AUDIT_TERMS:
			terms.append(
				{
					"term": term,
					"source_category": str(row.get("category", "")),
					"source": "label_rule",
					"specificity": str(row.get("specificity", "")),
					"rule_role": str(row.get("rule_role", "")),
				}
			)

	for _, row in dictionary.iterrows():
		term = clean_term(row["term"])
		if not term:
			continue
		terms.append(
			{
				"term": term,
				"source_category": str(row.get("category", "")),
				"source": "dictionary",
				"specificity": "",
				"rule_role": "",
			}
		)

	for term in OTHER_AUDIT_TERMS:
		cleaned = clean_term(term)
		if cleaned:
			terms.append(
				{
					"term": cleaned,
					"source_category": "other",
					"source": "manual_other_audit",
					"specificity": "audit",
					"rule_role": "boundary",
				}
			)

	vocabulary = pd.DataFrame(terms).drop_duplicates(["term", "source_category", "source"])
	term_summary = (
		vocabulary.groupby("term", as_index=False)
		.agg(
			source_categories=("source_category", lambda values: ";".join(sorted(set(filter(None, values))))),
			sources=("source", lambda values: ";".join(sorted(set(values)))),
			specificity=("specificity", lambda values: ";".join(sorted(set(filter(None, values))))),
			rule_role=("rule_role", lambda values: ";".join(sorted(set(filter(None, values))))),
		)
		.sort_values("term")
		.reset_index(drop=True)
	)
	term_summary["term_len"] = term_summary["term"].str.len()
	return term_summary.sort_values(["term_len", "term"], ascending=[False, True]).reset_index(drop=True)


def count_domain_terms(text: str, pattern: re.Pattern[str]) -> Counter[str]:
	"""Count reviewed domain phrases in one normalized policy text."""
	return Counter(pattern.findall(text))


def label_mask(frame: pd.DataFrame, label: str) -> pd.Series:
	"""Return the high-confidence analysis mask for one label."""
	if label == "other":
		return bool_series(frame["other_label"]) | (
			frame["p_other"].ge(HIGH_CONFIDENCE_THRESHOLD["other"]) & frame["max_tool_prob"].lt(0.4)
		)
	return frame[LABEL_PROBABILITY[label]].ge(HIGH_CONFIDENCE_THRESHOLD[label])


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
	"""Compute cosine similarity and return 0 when either vector is empty."""
	denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
	if denominator == 0:
		return 0.0
	return float(np.dot(left, right) / denominator)


def top_terms_from_vector(vector: np.ndarray, terms: list[str], top_n: int = 8) -> str:
	"""Return compact top-term text for drift-audit tables."""
	if not len(vector):
		return ""
	indices = np.argsort(vector)[::-1][:top_n]
	return ";".join(term for term_idx in indices if vector[term_idx] > 0 for term in [terms[term_idx]])


# %% [markdown]
# ## 1. Load Inputs and Build the Yearly Analysis Surface
#
# The row-level prediction table provides probabilities and label flags. The
# processed corpus provides full text and source audit fields. This notebook
# keeps both all-records and local-only scopes so that paper narrative can use
# local policy language while retaining a complete corpus audit.

# %%
configure_plot_fonts()

classified = pd.read_csv(CLASSIFIED_PATH)
corpus = pd.read_csv(CORPUS_PATH)
label_rules = pd.read_csv(LABEL_RULE_PATH)
dictionary = pd.read_csv(DICTIONARY_PATH)

for column in [
	"full_text_missing",
	"full_text_fallback_for_model",
	"needs_jurisdiction_review",
	"supply_label",
	"demand_label",
	"environment_label",
	"other_label",
	"any_tool_label",
	"valid_tool_policy",
]:
	if column in classified:
		classified[column] = bool_series(classified[column])
	if column in corpus:
		corpus[column] = bool_series(corpus[column])

text_columns = [
	"policy_id",
	"title",
	"agency",
	"full_text",
	"full_text_len",
	"full_text_missing",
	"full_text_fallback_for_model",
	"needs_jurisdiction_review",
]
records = classified.merge(
	corpus[text_columns],
	on="policy_id",
	how="left",
	suffixes=("", "_corpus"),
	validate="one_to_one",
)

records["full_text"] = records["full_text"].fillna("")
records["title"] = records["title"].fillna("")
records["agency"] = records["agency"].fillna("")
records["analysis_text"] = (
	records["title"].astype(str)
	+ records["title"].astype(str)
	+ records["agency"].astype(str)
	+ records["full_text"].astype(str)
).map(normalize_text)

load_summary = pd.DataFrame(
	[
		{"metric": "classified_rows", "value": len(classified), "note": "Expected 3989 for v2."},
		{"metric": "corpus_rows", "value": len(corpus), "note": "Expected 3989 for v2."},
		{"metric": "merged_rows", "value": len(records), "note": "One row per policy_id."},
		{"metric": "policy_id_unique", "value": bool(records["policy_id"].is_unique), "note": "Required for row-level TF-IDF."},
		{"metric": "year_set", "value": ";".join(map(str, sorted(records["publish_year"].unique()))), "note": "Expected 2019-2024."},
		{"metric": "central_rows", "value": int(records["jurisdiction_type"].eq("central").sum()), "note": "Retained in all-records audit."},
		{"metric": "local_rows", "value": int(records["jurisdiction_type"].eq("local").sum()), "note": "Preferred scope for paper narrative."},
	]
)
load_summary

# %% [markdown]
# ## 2. Reviewed Vocabulary and TF-IDF Matrix
#
# We use the same reviewed domain-phrase vocabulary as the classified-record
# interpretability notebook. This keeps the yearly drift audit aligned with the
# policy-tool taxonomy and avoids creating a separate unsupervised tokenization
# path.

# %%
vocabulary = build_vocabulary(label_rules, dictionary)
term_pattern = re.compile("|".join(re.escape(term) for term in vocabulary["term"]))

term_counts: list[Counter[str]] = [count_domain_terms(text, term_pattern) for text in records["analysis_text"]]
terms = vocabulary["term"].tolist()
n_docs = len(records)
counts = np.zeros((n_docs, len(terms)), dtype=np.float32)

term_to_idx = {term: idx for idx, term in enumerate(terms)}
for row_idx, counter in enumerate(term_counts):
	for term, count in counter.items():
		term_idx = term_to_idx.get(term)
		if term_idx is not None:
			counts[row_idx, term_idx] = count

tf = np.log1p(counts)
doc_frequency = (counts > 0).sum(axis=0)
idf = np.log((1 + n_docs) / (1 + doc_frequency)) + 1
tfidf = tf * idf

label_masks = {label: label_mask(records, label) for label in LABELS}

vocab_summary = pd.DataFrame(
	[
		{"metric": "vocabulary_terms", "value": len(vocabulary), "note": "Reviewed domain phrases after stop-term filtering."},
		{"metric": "records_with_any_domain_term", "value": int((counts.sum(axis=1) > 0).sum()), "note": "Rows with at least one reviewed phrase."},
		{"metric": "year_count", "value": records["publish_year"].nunique(), "note": "Expected 6."},
	]
)
vocab_summary

# %% [markdown]
# ## 3. Year-Label Summaries and Top Terms
#
# Each `scope x year x label` cell is summarized separately. Cells with fewer
# than 10 high-confidence records are retained but flagged as thin descriptive
# evidence.

# %%
summary_rows = []
top_term_frames = []
drift_vectors: dict[tuple[str, str, int], np.ndarray] = {}
label_baseline_vectors: dict[tuple[str, str], np.ndarray] = {}

for scope, jurisdiction_filter in SCOPE_FILTERS.items():
	scope_mask = pd.Series(True, index=records.index)
	if jurisdiction_filter is not None:
		scope_mask = records["jurisdiction_type"].eq(jurisdiction_filter)

	for label in LABELS:
		label_scope_mask = scope_mask & label_masks[label]
		label_indices = np.where(label_scope_mask.to_numpy())[0]
		label_baseline_vectors[(scope, label)] = (
			tfidf[label_indices].mean(axis=0) if len(label_indices) else np.zeros(len(terms))
		)

		for year in YEARS:
			cell_mask = label_scope_mask & records["publish_year"].eq(year)
			cell_indices = np.where(cell_mask.to_numpy())[0]
			non_cell_indices = np.where((scope_mask & ~cell_mask).to_numpy())[0]
			cell_tfidf = tfidf[cell_indices] if len(cell_indices) else np.empty((0, len(terms)))
			non_cell_tfidf = tfidf[non_cell_indices] if len(non_cell_indices) else np.empty((0, len(terms)))
			cell_mean = cell_tfidf.mean(axis=0) if len(cell_indices) else np.zeros(len(terms))
			non_cell_mean = non_cell_tfidf.mean(axis=0) if len(non_cell_indices) else np.zeros(len(terms))
			cell_doc_frequency = (counts[cell_indices] > 0).sum(axis=0) if len(cell_indices) else np.zeros(len(terms))
			cell_doc_share = cell_doc_frequency / max(len(cell_indices), 1)
			scope_doc_frequency = (counts[np.where(scope_mask.to_numpy())[0]] > 0).sum(axis=0)
			scope_doc_share = scope_doc_frequency / max(int(scope_mask.sum()), 1)
			lift = cell_mean - non_cell_mean
			share_lift = cell_doc_share - scope_doc_share
			score = cell_mean + np.maximum(lift, 0) + np.maximum(share_lift, 0)
			drift_vectors[(scope, label, year)] = cell_mean

			summary_rows.append(
				{
					"scope": scope,
					"publish_year": year,
					"label": label,
					"label_name": LABEL_NAME[label],
					"analysis_rule": (
						"p_label >= 0.75"
						if label in TOOL_LABELS
						else "hard other_label or p_other >= 0.60 with max_tool_prob < 0.40"
					),
					"high_confidence_doc_count": int(len(cell_indices)),
					"is_thin_cell": bool(len(cell_indices) < MIN_INTERPRETABLE_DOCS),
					"mean_label_probability": float(records.loc[cell_mask, LABEL_PROBABILITY[label]].mean()) if len(cell_indices) else 0.0,
					"mean_max_tool_probability": float(records.loc[cell_mask, "max_tool_prob"].mean()) if len(cell_indices) else 0.0,
					"mean_domain_terms_per_doc": float(counts[cell_indices].sum(axis=1).mean()) if len(cell_indices) else 0.0,
					"documents_with_any_domain_term_share": float((counts[cell_indices].sum(axis=1) > 0).mean()) if len(cell_indices) else 0.0,
				}
			)

			label_terms = pd.DataFrame(
				{
					"scope": scope,
					"publish_year": year,
					"label": label,
					"label_name": LABEL_NAME[label],
					"term": terms,
					"rank_score": score,
					"mean_tfidf": cell_mean,
					"non_cell_mean_tfidf": non_cell_mean,
					"tfidf_lift": lift,
					"label_year_doc_count": cell_doc_frequency.astype(int),
					"label_year_doc_share": cell_doc_share,
					"scope_doc_count": scope_doc_frequency.astype(int),
					"scope_doc_share": scope_doc_share,
					"doc_share_lift": share_lift,
					"high_confidence_doc_count": int(len(cell_indices)),
					"is_thin_cell": bool(len(cell_indices) < MIN_INTERPRETABLE_DOCS),
				}
			).merge(vocabulary, on="term", how="left")
			label_terms = label_terms.sort_values(["rank_score", "mean_tfidf", "label_year_doc_share"], ascending=False)
			label_terms["rank"] = np.arange(1, len(label_terms) + 1)
			top_term_frames.append(label_terms.head(TOP_N_TERMS))

year_label_summary = pd.DataFrame(summary_rows)
top_terms_by_year_label = pd.concat(top_term_frames, ignore_index=True)

year_label_summary.to_csv(YEAR_LABEL_SUMMARY_OUTPUT, index=False)
top_terms_by_year_label.to_csv(TOP_TERMS_BY_YEAR_LABEL_OUTPUT, index=False)

year_label_summary.head(12)

# %% [markdown]
# ## 4. Yearly Drift Audit
#
# The first diagnostic compares each year-label vector with the same label's
# all-year baseline. The second diagnostic compares adjacent years within the
# same label. Lower cosine similarity means stronger language drift.

# %%
drift_rows = []
for scope in SCOPE_FILTERS:
	for label in LABELS:
		baseline = label_baseline_vectors[(scope, label)]
		for year in YEARS:
			vector = drift_vectors[(scope, label, year)]
			cell = year_label_summary.loc[
				year_label_summary["scope"].eq(scope)
				& year_label_summary["label"].eq(label)
				& year_label_summary["publish_year"].eq(year)
			].iloc[0]
			cosine_to_baseline = cosine_similarity(vector, baseline)
			drift_rows.append(
				{
					"scope": scope,
					"comparison_type": "annual_to_label_all_years",
					"label": label,
					"label_name": LABEL_NAME[label],
					"publish_year": year,
					"comparison_year": "",
					"high_confidence_doc_count": int(cell["high_confidence_doc_count"]),
					"is_thin_cell": bool(cell["is_thin_cell"]),
					"cosine_similarity": cosine_to_baseline,
					"drift_distance": 1 - cosine_to_baseline,
					"top_terms": top_terms_from_vector(vector, terms),
					"comparison_top_terms": top_terms_from_vector(baseline, terms),
				}
			)

		for previous_year, current_year in zip(YEARS[:-1], YEARS[1:], strict=True):
			previous_vector = drift_vectors[(scope, label, previous_year)]
			current_vector = drift_vectors[(scope, label, current_year)]
			previous_cell = year_label_summary.loc[
				year_label_summary["scope"].eq(scope)
				& year_label_summary["label"].eq(label)
				& year_label_summary["publish_year"].eq(previous_year)
			].iloc[0]
			current_cell = year_label_summary.loc[
				year_label_summary["scope"].eq(scope)
				& year_label_summary["label"].eq(label)
				& year_label_summary["publish_year"].eq(current_year)
			].iloc[0]
			cosine_adjacent = cosine_similarity(current_vector, previous_vector)
			drift_rows.append(
				{
					"scope": scope,
					"comparison_type": "adjacent_year",
					"label": label,
					"label_name": LABEL_NAME[label],
					"publish_year": current_year,
					"comparison_year": previous_year,
					"high_confidence_doc_count": int(current_cell["high_confidence_doc_count"]),
					"is_thin_cell": bool(current_cell["is_thin_cell"] or previous_cell["is_thin_cell"]),
					"cosine_similarity": cosine_adjacent,
					"drift_distance": 1 - cosine_adjacent,
					"top_terms": top_terms_from_vector(current_vector, terms),
					"comparison_top_terms": top_terms_from_vector(previous_vector, terms),
				}
			)

yearly_drift_audit = pd.DataFrame(drift_rows)
yearly_drift_audit.to_csv(YEARLY_DRIFT_AUDIT_OUTPUT, index=False)

yearly_drift_audit.head(12)

# %% [markdown]
# ## 5. Figures

# %%
local_top = top_terms_by_year_label.loc[
	top_terms_by_year_label["scope"].eq("local_only")
	& top_terms_by_year_label["label"].isin(TOOL_LABELS)
	& top_terms_by_year_label["rank"].le(1)
].copy()
local_top["year_label"] = local_top["publish_year"].astype(str) + " " + local_top["label_name"]

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
for ax, label in zip(axes, TOOL_LABELS, strict=True):
	plot_data = local_top.loc[local_top["label"].eq(label)].sort_values("publish_year")
	ax.bar(plot_data["publish_year"].astype(str), plot_data["mean_tfidf"], color="#4C78A8")
	for idx, row in enumerate(plot_data.itertuples(index=False)):
		ax.text(idx, row.mean_tfidf, row.term, ha="center", va="bottom", fontsize=9)
	ax.set_title(f"Local {LABEL_NAME[label]}: annual top TF-IDF phrase")
	ax.set_ylabel("Mean TF-IDF")
	ax.set_ylim(0, max(plot_data["mean_tfidf"].max() * 1.25, 0.1))
axes[-1].set_xlabel("Publish year")
save_figure(fig, YEARLY_TOOL_TERMS_FIG)
display(fig)

drift_matrix_source = yearly_drift_audit.loc[
	yearly_drift_audit["scope"].eq("local_only")
	& yearly_drift_audit["comparison_type"].eq("annual_to_label_all_years")
].copy()
drift_matrix = (
	drift_matrix_source.pivot(index="label_name", columns="publish_year", values="drift_distance")
	.reindex([LABEL_NAME[label] for label in LABELS])
	.reindex(columns=YEARS)
)
fig, ax = plt.subplots(figsize=(9, 4.8))
matrix = drift_matrix.to_numpy()
im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
ax.set_xticks(np.arange(len(YEARS)))
ax.set_xticklabels(YEARS)
ax.set_yticks(np.arange(len(drift_matrix.index)))
ax.set_yticklabels(drift_matrix.index)
ax.set_title("Local yearly TF-IDF drift from each label's all-year language")
for row_idx in range(matrix.shape[0]):
	for col_idx in range(matrix.shape[1]):
		ax.text(col_idx, row_idx, f"{matrix[row_idx, col_idx]:.2f}", ha="center", va="center", fontsize=8)
fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="1 - cosine similarity")
save_figure(fig, YEARLY_DRIFT_HEATMAP_FIG)
display(fig)

YEARLY_TOOL_TERMS_FIG, YEARLY_DRIFT_HEATMAP_FIG

# %% [markdown]
# ## 6. Interpretation Notes

# %%
thin_cells = int(year_label_summary["is_thin_cell"].sum())
local_thin_cells = int(year_label_summary.loc[year_label_summary["scope"].eq("local_only"), "is_thin_cell"].sum())
notes = pd.DataFrame(
	[
		{
			"topic": "analysis_scope",
			"note": "Yearly TF-IDF is used only for policy-language evolution and quality audit. It is not a new DID policy-intensity variable path.",
		},
		{
			"topic": "vocabulary_scope",
			"note": f"The vocabulary contains {len(vocabulary)} reviewed domain phrases from the label-rule and full-text dictionary files after removing common SRDI identity terms.",
		},
		{
			"topic": "year_window",
			"note": "The analysis window is fixed to 2019-2024 and covers both all-records and local-only scopes.",
		},
		{
			"topic": "thin_cells",
			"note": f"Cells with fewer than {MIN_INTERPRETABLE_DOCS} high-confidence records are retained and flagged; {thin_cells} total cells and {local_thin_cells} local-only cells are thin.",
		},
		{
			"topic": "drift_interpretation",
			"note": "Drift distance is 1 minus cosine similarity between yearly mean TF-IDF vectors and label all-year baselines or adjacent-year vectors.",
		},
		{
			"topic": "paper_use",
			"note": "Use the local-only annual top-term figure and drift heatmap as appendix or methods-QA evidence for policy-language evolution and 2019-corpus continuity.",
		},
	]
)
notes.to_csv(YEARLY_INTERPRETATION_NOTES_OUTPUT, index=False)

notes

# %% [markdown]
# ## 7. Output Inventory

# %%
output_inventory = pd.DataFrame(
	[
		{"path": str(YEAR_LABEL_SUMMARY_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": YEAR_LABEL_SUMMARY_OUTPUT.exists()},
		{"path": str(TOP_TERMS_BY_YEAR_LABEL_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": TOP_TERMS_BY_YEAR_LABEL_OUTPUT.exists()},
		{"path": str(YEARLY_DRIFT_AUDIT_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": YEARLY_DRIFT_AUDIT_OUTPUT.exists()},
		{"path": str(YEARLY_INTERPRETATION_NOTES_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": YEARLY_INTERPRETATION_NOTES_OUTPUT.exists()},
		{"path": str(YEARLY_TOOL_TERMS_FIG.relative_to(ROOT)), "kind": "figure", "exists": YEARLY_TOOL_TERMS_FIG.exists()},
		{"path": str(YEARLY_DRIFT_HEATMAP_FIG.relative_to(ROOT)), "kind": "figure", "exists": YEARLY_DRIFT_HEATMAP_FIG.exists()},
	]
)
output_inventory
