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
# # Manual SRDI Classified-Record TF-IDF Interpretability v2
#
# This notebook adds an interpretability and quality-audit layer on top of the
# completed 2019-2024 v2 MacBERT classified policy records.
#
# Scope:
#
# - input: v2 row-level MacBERT classified records and v2 full-text policy
#   corpus;
# - method: dependency-light domain-phrase TF-IDF using the reviewed SRDI
#   policy-tool keyword lists as vocabulary;
# - outputs: label-level TF-IDF terms, overlap audit, representative documents,
#   interpretation notes, and paper-facing figures;
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

LABEL_SUMMARY_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_label_summary_v2.csv"
TOP_TERMS_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_top_terms_v2.csv"
OVERLAP_AUDIT_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_overlap_audit_v2.csv"
REPRESENTATIVE_DOCS_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_representative_docs_v2.csv"
INTERPRETATION_NOTES_OUTPUT = OUTPUT_DIR / "manual_srdi_macbert_tfidf_interpretation_notes_v2.csv"

TOP_TERMS_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_tfidf_top_terms_v2.png"
HEATMAP_FIG = OUTPUT_DIR / "manual_srdi_macbert_fig_tfidf_label_heatmap_v2.png"

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
FIG_DPI = 300

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


def save_figure(fig: plt.Figure, path: Path) -> None:
	"""Save a Matplotlib figure with consistent paper-draft settings."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fig.tight_layout()
	fig.savefig(path, dpi=FIG_DPI, bbox_inches="tight")
	plt.close(fig)


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
	"""Build a reviewed domain-phrase vocabulary for TF-IDF interpretation."""
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
	"""Return the analysis sample mask for one label."""
	if label == "other":
		return bool_series(frame["other_label"]) | (
			frame["p_other"].ge(HIGH_CONFIDENCE_THRESHOLD["other"]) & frame["max_tool_prob"].lt(0.4)
		)
	return frame[LABEL_PROBABILITY[label]].ge(HIGH_CONFIDENCE_THRESHOLD[label])


# %% [markdown]
# ## 1. Load Inputs and Build the Analysis Surface
#
# The classified prediction table contains probabilities and audit fields, while
# the processed corpus retains the full text. We merge them by `policy_id`.

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
		{"metric": "central_rows", "value": int(records["jurisdiction_type"].eq("central").sum()), "note": "Retained for row-level interpretability."},
		{"metric": "local_rows", "value": int(records["jurisdiction_type"].eq("local").sum()), "note": "Policy-side aggregation source."},
	]
)
load_summary

# %% [markdown]
# ## 2. Domain-Phrase Vocabulary
#
# The project environment intentionally avoids adding new segmentation
# dependencies here. Instead, this notebook builds a reviewed domain-phrase
# vocabulary from the existing SRDI label-rule and full-text dictionary files,
# then computes TF-IDF over those phrases. This makes the output interpretable
# and aligned with the policy-tool taxonomy, while avoiding a new variable
# construction path.

# %%
vocabulary = build_vocabulary(label_rules, dictionary)
term_pattern = re.compile("|".join(re.escape(term) for term in vocabulary["term"]))

vocab_summary = pd.DataFrame(
	[
		{"metric": "vocabulary_terms", "value": len(vocabulary), "note": "Reviewed domain phrases after stop-term filtering."},
		{"metric": "vocabulary_sources", "value": ";".join(sorted(set(";".join(vocabulary["sources"]).split(";")))), "note": "Sources used to build the vocabulary."},
		{"metric": "tool_categories", "value": ";".join(sorted(set(";".join(vocabulary["source_categories"]).split(";")))), "note": "Source categories represented in the vocabulary."},
	]
)
vocab_summary

# %% [markdown]
# ## 3. Compute TF-IDF Scores
#
# TF-IDF is computed at the row-document level. The analysis sample for supply,
# demand, and environment uses high-confidence records (`p >= 0.75`). The
# `other` analysis sample uses the hard `other_label` rule plus high-`p_other`
# low-tool-probability records. Multi-label documents may enter more than one
# substantive tool category.

# %%
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

label_summary_rows = []
top_term_frames = []
for label, mask in label_masks.items():
	label_indices = np.where(mask.to_numpy())[0]
	non_label_indices = np.where(~mask.to_numpy())[0]
	label_tfidf = tfidf[label_indices] if len(label_indices) else np.empty((0, len(terms)))
	non_label_tfidf = tfidf[non_label_indices] if len(non_label_indices) else np.empty((0, len(terms)))
	label_mean = label_tfidf.mean(axis=0) if len(label_indices) else np.zeros(len(terms))
	non_label_mean = non_label_tfidf.mean(axis=0) if len(non_label_indices) else np.zeros(len(terms))
	label_doc_frequency = (counts[label_indices] > 0).sum(axis=0) if len(label_indices) else np.zeros(len(terms))
	label_doc_share = label_doc_frequency / max(len(label_indices), 1)
	global_doc_share = doc_frequency / n_docs
	lift = label_mean - non_label_mean
	share_lift = label_doc_share - global_doc_share
	score = label_mean + np.maximum(lift, 0) + np.maximum(share_lift, 0)

	label_summary_rows.append(
		{
			"label": label,
			"label_name": LABEL_NAME[label],
			"analysis_rule": (
				"p_label >= 0.75"
				if label in TOOL_LABELS
				else "hard other_label or p_other >= 0.60 with max_tool_prob < 0.40"
			),
			"high_confidence_doc_count": int(len(label_indices)),
			"high_confidence_doc_share": float(len(label_indices) / n_docs),
			"mean_label_probability": float(records.loc[mask, LABEL_PROBABILITY[label]].mean()) if len(label_indices) else 0.0,
			"mean_max_tool_probability": float(records.loc[mask, "max_tool_prob"].mean()) if len(label_indices) else 0.0,
			"mean_domain_terms_per_doc": float(counts[label_indices].sum(axis=1).mean()) if len(label_indices) else 0.0,
			"documents_with_any_domain_term_share": float((counts[label_indices].sum(axis=1) > 0).mean()) if len(label_indices) else 0.0,
		}
	)

	label_terms = pd.DataFrame(
		{
			"label": label,
			"label_name": LABEL_NAME[label],
			"term": terms,
			"rank_score": score,
			"mean_tfidf": label_mean,
			"non_label_mean_tfidf": non_label_mean,
			"tfidf_lift": lift,
			"label_doc_count": label_doc_frequency.astype(int),
			"label_doc_share": label_doc_share,
			"global_doc_count": doc_frequency.astype(int),
			"global_doc_share": global_doc_share,
			"doc_share_lift": share_lift,
		}
	).merge(vocabulary, on="term", how="left")
	label_terms = label_terms.sort_values(["rank_score", "mean_tfidf", "label_doc_share"], ascending=False)
	label_terms["rank"] = np.arange(1, len(label_terms) + 1)
	top_term_frames.append(label_terms.head(30))

label_summary = pd.DataFrame(label_summary_rows)
top_terms = pd.concat(top_term_frames, ignore_index=True)

label_summary.to_csv(LABEL_SUMMARY_OUTPUT, index=False)
top_terms.to_csv(TOP_TERMS_OUTPUT, index=False)

label_summary

# %% [markdown]
# ## 4. Overlap Audit and Representative Documents
#
# Some terms should appear across multiple categories because policy files often
# contain mixed tools. This overlap table is an interpretability aid: it flags
# terms that are not category-exclusive and should not be overinterpreted.

# %%
overlap_audit = (
	top_terms.loc[top_terms["rank"].le(20)]
	.groupby("term", as_index=False)
	.agg(
		label_count=("label", "nunique"),
		labels=("label", lambda values: ";".join(sorted(set(values)))),
		best_rank=("rank", "min"),
		max_mean_tfidf=("mean_tfidf", "max"),
		source_categories=("source_categories", "first"),
	)
	.query("label_count >= 2")
	.sort_values(["label_count", "best_rank", "term"], ascending=[False, True, True])
)
overlap_audit.to_csv(OVERLAP_AUDIT_OUTPUT, index=False)

representative_rows = []
top_terms_by_label = {
	label: top_terms.loc[top_terms["label"].eq(label)].head(12)["term"].tolist()
	for label in LABELS
}
for label, mask in label_masks.items():
	candidate = records.loc[mask].copy()
	if candidate.empty:
		continue
	candidate_terms = top_terms_by_label[label]
	candidate["top_tfidf_term_hits"] = candidate["analysis_text"].map(
		lambda text: ";".join([term for term in candidate_terms if term in text])
	)
	candidate["top_tfidf_term_hit_count"] = candidate["top_tfidf_term_hits"].map(
		lambda value: 0 if not value else len(value.split(";"))
	)
	candidate = candidate.sort_values(
		[LABEL_PROBABILITY[label], "top_tfidf_term_hit_count", "full_text_len"],
		ascending=[False, False, False],
	).head(15)
	for _, row in candidate.iterrows():
		excerpt_source = row["full_text"] if row["full_text"] else row["title"]
		representative_rows.append(
			{
				"label": label,
				"label_name": LABEL_NAME[label],
				"policy_id": row["policy_id"],
				"province": row["province"],
				"jurisdiction_type": row["jurisdiction_type"],
				"publish_year": row["publish_year"],
				"title": row["title"],
				"p_supply": row["p_supply"],
				"p_demand": row["p_demand"],
				"p_environment": row["p_environment"],
				"p_other": row["p_other"],
				"top_tfidf_term_hits": row["top_tfidf_term_hits"],
				"top_tfidf_term_hit_count": row["top_tfidf_term_hit_count"],
				"text_excerpt": str(excerpt_source)[:180],
			}
		)

representative_docs = pd.DataFrame(representative_rows)
representative_docs.to_csv(REPRESENTATIVE_DOCS_OUTPUT, index=False)

overlap_audit.head(20)

# %% [markdown]
# ## 5. Figures

# %%
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
axes = axes.flatten()
for ax, label in zip(axes, LABELS, strict=True):
	plot_data = top_terms.loc[top_terms["label"].eq(label)].head(12).sort_values("mean_tfidf")
	ax.barh(plot_data["term"], plot_data["mean_tfidf"], color="#4C78A8")
	ax.set_title(f"{LABEL_NAME[label]} top TF-IDF phrases")
	ax.set_xlabel("Mean TF-IDF")
	ax.tick_params(axis="y", labelsize=9)
save_figure(fig, TOP_TERMS_FIG)
display(fig)

heatmap_terms = (
	top_terms.loc[top_terms["rank"].le(8), ["label", "term"]]
	.drop_duplicates()
	.groupby("label")
	.head(8)["term"]
	.drop_duplicates()
	.tolist()
)
heatmap_rows = []
for term in heatmap_terms:
	term_idx = term_to_idx[term]
	row = {"term": term}
	for label, mask in label_masks.items():
		indices = np.where(mask.to_numpy())[0]
		row[label] = float(tfidf[indices, term_idx].mean()) if len(indices) else 0.0
	heatmap_rows.append(row)

heatmap = pd.DataFrame(heatmap_rows).set_index("term")
fig, ax = plt.subplots(figsize=(8, max(6, 0.28 * len(heatmap))))
matrix = heatmap[LABELS].to_numpy()
im = ax.imshow(matrix, aspect="auto", cmap="YlGnBu")
ax.set_xticks(np.arange(len(LABELS)))
ax.set_xticklabels([LABEL_NAME[label] for label in LABELS], rotation=20, ha="right")
ax.set_yticks(np.arange(len(heatmap.index)))
ax.set_yticklabels(heatmap.index)
ax.set_title("Mean TF-IDF of top interpretive phrases by label")
for row_idx in range(matrix.shape[0]):
	for col_idx in range(matrix.shape[1]):
		ax.text(col_idx, row_idx, f"{matrix[row_idx, col_idx]:.2f}", ha="center", va="center", fontsize=7)
fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
save_figure(fig, HEATMAP_FIG)

display(fig)
print(TOP_TERMS_FIG, HEATMAP_FIG)

# %% [markdown]
# ## 6. Interpretation Notes

# %%
notes = pd.DataFrame(
	[
		{
			"topic": "analysis_scope",
			"note": "TF-IDF is used only for classified-record interpretability and quality audit. It is not a new DID policy-intensity variable path.",
		},
		{
			"topic": "vocabulary_scope",
			"note": f"The vocabulary contains {len(vocabulary)} reviewed domain phrases from the label-rule and full-text dictionary files after removing common SRDI identity terms.",
		},
		{
			"topic": "label_samples",
			"note": "Supply, demand, and environment TF-IDF summaries use p_label >= 0.75 high-confidence documents; other uses hard other labels or high p_other with low max tool probability.",
		},
		{
			"topic": "multi_label_policy",
			"note": "A document may enter more than one substantive tool label because policy files can contain multiple instruments.",
		},
		{
			"topic": "overlap_interpretation",
			"note": "Terms appearing across multiple label top lists should be interpreted as mixed-policy language, not as category-exclusive evidence.",
		},
		{
			"topic": "paper_use",
			"note": "Use the top-term and heatmap figures as appendix or methods-QA evidence that the MacBERT labels align with recognizable policy-tool phrases.",
		},
	]
)
notes.to_csv(INTERPRETATION_NOTES_OUTPUT, index=False)

notes

# %% [markdown]
# ## 7. Output Inventory

# %%
output_inventory = pd.DataFrame(
	[
		{"path": str(LABEL_SUMMARY_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": LABEL_SUMMARY_OUTPUT.exists()},
		{"path": str(TOP_TERMS_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": TOP_TERMS_OUTPUT.exists()},
		{"path": str(OVERLAP_AUDIT_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": OVERLAP_AUDIT_OUTPUT.exists()},
		{"path": str(REPRESENTATIVE_DOCS_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": REPRESENTATIVE_DOCS_OUTPUT.exists()},
		{"path": str(INTERPRETATION_NOTES_OUTPUT.relative_to(ROOT)), "kind": "table", "exists": INTERPRETATION_NOTES_OUTPUT.exists()},
		{"path": str(TOP_TERMS_FIG.relative_to(ROOT)), "kind": "figure", "exists": TOP_TERMS_FIG.exists()},
		{"path": str(HEATMAP_FIG.relative_to(ROOT)), "kind": "figure", "exists": HEATMAP_FIG.exists()},
	]
)
output_inventory
