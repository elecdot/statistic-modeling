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
# # Manual SRDI Label Rule Keywords v1
#
# This notebook turns the exploratory full-text dictionary into a rule system
# for DeepSeek/MacBERT labeling preparation.
#
# It does not call DeepSeek, does not train MacBERT, and does not treat keyword
# hits as final labels. The outputs are used for stratified sampling, audit, and
# later model-diagnosis only.

# %%
from __future__ import annotations

from pathlib import Path

import pandas as pd

# %%
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()

FULLTEXT_RECORDS_PATH = ROOT / "data" / "processed" / "manual_policy_srdi_policy_records_fulltext_v1.csv"
TERM_FLAGS_PATH = ROOT / "outputs" / "manual_srdi_fulltext_keyword_quality_term_flags_v1.csv"

RULE_KEYWORDS_OUTPUT = ROOT / "configs" / "manual_srdi_label_rule_keywords_v1.csv"
LABEL_DOCS_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_label_docs_v1.csv"
SAMPLING_FRAME_OUTPUT = ROOT / "data" / "processed" / "manual_policy_srdi_label_sampling_frame_v1.csv"
ROUND1_SAMPLE_OUTPUT = ROOT / "data" / "interim" / "manual_policy_srdi_deepseek_sample_round1_v1.csv"

RULE_COVERAGE_OUTPUT = ROOT / "outputs" / "manual_srdi_label_rule_keyword_coverage_v1.csv"
POOL_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_label_sampling_pool_summary_v1.csv"
SAMPLE_SUMMARY_OUTPUT = ROOT / "outputs" / "manual_srdi_label_sample_round1_summary_v1.csv"
RULE_NOTES_OUTPUT = ROOT / "outputs" / "manual_srdi_label_rule_keyword_notes_v1.csv"

RANDOM_STATE = 42
TARGET_PER_POOL = 200
YEARS = list(range(2020, 2026))
VALID_CATEGORIES = {"supply", "demand", "environment", "other"}
VALID_RULE_ROLES = {"recall", "discriminative", "other_signal"}
VALID_SPECIFICITY = {"broad", "medium", "specific"}


def rule(
	category: str,
	term: str,
	rule_role: str,
	specificity: str,
	keep_for_sampling: bool = True,
	keep_for_interpretation: bool = True,
	needs_context: bool = False,
	notes: str = "",
) -> dict[str, object]:
	"""Create one auditable label-rule keyword row."""
	return {
		"category": category,
		"term": term,
		"rule_role": rule_role,
		"specificity": specificity,
		"keep_for_sampling": keep_for_sampling,
		"keep_for_interpretation": keep_for_interpretation,
		"needs_context": needs_context,
		"notes": notes,
	}


def count_hits(text: str, terms: list[str]) -> int:
	"""Count literal substring hits over a term list."""
	return sum(str(text).count(term) for term in terms)


def matched_terms(text: str, terms: list[str]) -> str:
	"""Return semicolon-separated terms present in text."""
	return ";".join(term for term in terms if term in str(text))


def sample_from_pool(
	frame: pd.DataFrame,
	pool_name: str,
	mask: pd.Series,
	taken_doc_ids: set[str],
	target_n: int,
	priority_mask: pd.Series | None = None,
) -> pd.DataFrame:
	"""Draw a deterministic without-replacement sample for one pool."""
	available = frame.loc[mask & ~frame["doc_id"].isin(taken_doc_ids)].copy()
	parts = []

	if priority_mask is not None:
		priority = available.loc[priority_mask.loc[available.index]].copy()
		take_n = min(target_n, len(priority))
		if take_n:
			parts.append(priority.sample(n=take_n, random_state=RANDOM_STATE))

	remaining_n = target_n - sum(len(part) for part in parts)
	if remaining_n > 0:
		used = set(pd.concat(parts)["doc_id"]) if parts else set()
		remainder = available.loc[~available["doc_id"].isin(used)].copy()
		take_n = min(remaining_n, len(remainder))
		if take_n:
			parts.append(remainder.sample(n=take_n, random_state=RANDOM_STATE + len(taken_doc_ids)))

	if not parts:
		return pd.DataFrame(columns=[*frame.columns, "sample_pool"])

	sample = pd.concat(parts, ignore_index=True)
	sample["sample_pool"] = pool_name
	return sample


# %% [markdown]
# ## 1. Build Rule Keyword Table
#
# Broad full-text terms are retained as `recall` rules. More specific policy
# instruments are assigned to `discriminative`. Procedural/no-substance signals
# are assigned to `other_signal`.

# %%
rules = [
	# Supply recall / broad intensity terms.
	rule("supply", "创新", "recall", "broad", keep_for_interpretation=False, needs_context=True, notes="Very high coverage; aggregate intensity only."),
	rule("supply", "财政", "recall", "broad", keep_for_interpretation=False, needs_context=True, notes="Broad fiscal language."),
	rule("supply", "研发", "recall", "broad", needs_context=True, notes="Broad R&D orientation."),
	rule("supply", "人才", "recall", "broad", needs_context=True, notes="Broad talent orientation."),
	rule("supply", "培训", "recall", "broad", needs_context=True, notes="Broad training/service signal."),
	rule("supply", "服务平台", "recall", "broad", needs_context=True, notes="Broad service-platform language."),
	rule("supply", "公共服务", "recall", "broad", needs_context=True, notes="Broad public-service language."),
	rule("supply", "数字化", "recall", "broad", needs_context=True, notes="Broad digitalization support."),
	# Supply discriminative terms.
	rule("supply", "奖励", "discriminative", "medium"),
	rule("supply", "补贴", "discriminative", "medium"),
	rule("supply", "补助", "discriminative", "medium"),
	rule("supply", "奖补", "discriminative", "medium"),
	rule("supply", "专项资金", "discriminative", "specific"),
	rule("supply", "资金支持", "discriminative", "specific"),
	rule("supply", "财政支持", "discriminative", "specific"),
	rule("supply", "研发补助", "discriminative", "specific"),
	rule("supply", "技术改造", "discriminative", "specific"),
	rule("supply", "设备更新", "discriminative", "specific"),
	rule("supply", "职业技能", "discriminative", "specific"),
	rule("supply", "技能提升", "discriminative", "specific"),
	rule("supply", "见习岗位", "discriminative", "specific"),
	rule("supply", "节能诊断", "discriminative", "specific"),
	rule("supply", "诊断服务", "discriminative", "specific"),
	rule("supply", "出海服务", "discriminative", "specific"),
	rule("supply", "孵化", "discriminative", "medium"),
	rule("supply", "智造空间", "discriminative", "specific"),
	rule("supply", "创新平台", "discriminative", "medium"),
	rule("supply", "基础设施", "discriminative", "medium"),
	rule("supply", "要素保障", "discriminative", "specific"),
	# Demand recall / broad terms.
	rule("demand", "采购", "recall", "broad", needs_context=True, notes="Broad procurement language; government procurement is more specific."),
	rule("demand", "对接", "recall", "broad", needs_context=True, notes="High full-text coverage; context required."),
	rule("demand", "场景", "recall", "broad", needs_context=True, notes="Can mean application scenarios or general scenes."),
	rule("demand", "推广应用", "recall", "medium", needs_context=True),
	rule("demand", "市场", "recall", "broad", needs_context=True),
	# Demand discriminative terms.
	rule("demand", "政府采购", "discriminative", "specific"),
	rule("demand", "首台套", "discriminative", "specific"),
	rule("demand", "首批次", "discriminative", "specific"),
	rule("demand", "首版次", "discriminative", "specific"),
	rule("demand", "示范应用", "discriminative", "specific"),
	rule("demand", "应用场景", "discriminative", "specific"),
	rule("demand", "供需对接", "discriminative", "specific"),
	rule("demand", "市场开拓", "discriminative", "specific"),
	rule("demand", "产品推广", "discriminative", "specific"),
	rule("demand", "展会", "discriminative", "medium"),
	rule("demand", "参展", "discriminative", "medium"),
	rule("demand", "展览会", "discriminative", "specific"),
	rule("demand", "博览会", "discriminative", "specific"),
	rule("demand", "广交会", "discriminative", "specific"),
	rule("demand", "展位", "discriminative", "specific"),
	rule("demand", "走出去", "discriminative", "medium"),
	rule("demand", "外贸", "discriminative", "medium"),
	rule("demand", "出口", "discriminative", "medium"),
	rule("demand", "国际市场", "discriminative", "specific"),
	rule("demand", "产业链对接", "discriminative", "specific"),
	# Environment recall / broad terms.
	rule("environment", "融资", "recall", "broad", needs_context=True),
	rule("environment", "贷款", "recall", "broad", needs_context=True),
	rule("environment", "标准", "recall", "broad", keep_for_interpretation=False, needs_context=True, notes="Very high coverage; aggregate intensity only."),
	rule("environment", "认定", "recall", "broad", needs_context=True),
	rule("environment", "评价", "recall", "broad", needs_context=True),
	rule("environment", "产业链", "recall", "broad", needs_context=True),
	rule("environment", "供应链", "recall", "broad", needs_context=True),
	rule("environment", "银行", "recall", "broad", needs_context=True),
	rule("environment", "保险", "recall", "broad", needs_context=True),
	rule("environment", "基金", "recall", "broad", needs_context=True),
	# Environment discriminative terms.
	rule("environment", "融资担保", "discriminative", "specific"),
	rule("environment", "担保", "discriminative", "medium"),
	rule("environment", "贴息", "discriminative", "specific"),
	rule("environment", "贷款贴息", "discriminative", "specific"),
	rule("environment", "税收优惠", "discriminative", "specific"),
	rule("environment", "税收", "discriminative", "medium"),
	rule("environment", "减税", "discriminative", "specific"),
	rule("environment", "降费", "discriminative", "specific"),
	rule("environment", "知识产权保护", "discriminative", "specific"),
	rule("environment", "知识产权", "discriminative", "medium"),
	rule("environment", "上市培育", "discriminative", "specific"),
	rule("environment", "上市", "discriminative", "medium"),
	rule("environment", "挂牌", "discriminative", "medium"),
	rule("environment", "营商环境", "discriminative", "specific"),
	rule("environment", "服务机制", "discriminative", "specific"),
	rule("environment", "信用", "discriminative", "medium"),
	rule("environment", "科技金融", "discriminative", "specific"),
	rule("environment", "绿色金融", "discriminative", "specific"),
	rule("environment", "绿贷", "discriminative", "specific"),
	rule("environment", "银企", "discriminative", "specific"),
	rule("environment", "风险减量", "discriminative", "specific"),
	rule("environment", "梯度培育", "discriminative", "specific"),
	rule("environment", "培育库", "discriminative", "specific"),
	rule("environment", "法规制度", "discriminative", "specific"),
	rule("environment", "标准制定", "discriminative", "specific"),
	rule("environment", "认定评价", "discriminative", "specific"),
	# Other/procedural signals.
	rule("other", "申报", "other_signal", "medium", keep_for_interpretation=False, needs_context=True, notes="Procedural signal, not final other label."),
	rule("other", "通知", "other_signal", "broad", keep_for_interpretation=False, needs_context=True),
	rule("other", "公示", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "名单", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "公布", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "转发", "other_signal", "specific", keep_for_interpretation=False, needs_context=True),
	rule("other", "会议", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "座谈", "other_signal", "specific", keep_for_interpretation=False, needs_context=True),
	rule("other", "解读", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "新闻", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "工作动态", "other_signal", "specific", keep_for_interpretation=False, needs_context=True),
	rule("other", "评审", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "复核", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "遴选", "other_signal", "specific", keep_for_interpretation=False, needs_context=True),
	rule("other", "推荐", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
	rule("other", "通告", "other_signal", "medium", keep_for_interpretation=False, needs_context=True),
]
rule_keywords = pd.DataFrame(rules).drop_duplicates(["category", "term", "rule_role"]).reset_index(drop=True)

assert set(rule_keywords["category"]).issubset(VALID_CATEGORIES)
assert set(rule_keywords["rule_role"]).issubset(VALID_RULE_ROLES)
assert set(rule_keywords["specificity"]).issubset(VALID_SPECIFICITY)

RULE_KEYWORDS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
rule_keywords.to_csv(RULE_KEYWORDS_OUTPUT, index=False)
rule_keywords.head(12)

# %% [markdown]
# ## 2. Build Label Docs

# %%
records = pd.read_csv(FULLTEXT_RECORDS_PATH)
term_flags = pd.read_csv(TERM_FLAGS_PATH)

label_docs = (
	records.rename(
		columns={
			"policy_id": "doc_id",
			"publish_year": "year",
			"agency": "issuing_agency",
			"full_text": "clean_text",
			"full_text_len": "text_len",
		}
	)[["doc_id", "province", "year", "title", "issuing_agency", "publish_date", "source_url", "clean_text", "text_len"]]
	.copy()
)
label_docs["issuing_agency"] = label_docs["issuing_agency"].fillna("")
label_docs["clean_text"] = label_docs["clean_text"].fillna("").astype(str).str.strip()

LABEL_DOCS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
label_docs.to_csv(LABEL_DOCS_OUTPUT, index=False)
label_docs.head()

# %% [markdown]
# ## 3. Build Sampling Frame

# %%
text_surface = (label_docs["title"].fillna("") + "\n" + label_docs["clean_text"].fillna("")).astype(str)
title_surface = label_docs["title"].fillna("").astype(str)

sampling_frame = label_docs.copy()
for category in ["supply", "demand", "environment"]:
	for role in ["recall", "discriminative"]:
		terms = rule_keywords.loc[
			(rule_keywords["category"].eq(category))
			& (rule_keywords["rule_role"].eq(role))
			& (rule_keywords["keep_for_sampling"].astype(bool)),
			"term",
		].tolist()
		prefix = f"{category}_{role}"
		sampling_frame[f"{prefix}_hit_count"] = text_surface.map(lambda text, terms=terms: count_hits(text, terms))
		sampling_frame[f"{prefix}_matched_terms"] = text_surface.map(lambda text, terms=terms: matched_terms(text, terms))

other_terms = rule_keywords.loc[rule_keywords["rule_role"].eq("other_signal"), "term"].tolist()
sampling_frame["other_signal_hit_count"] = text_surface.map(lambda text: count_hits(text, other_terms))
sampling_frame["other_signal_matched_terms"] = text_surface.map(lambda text: matched_terms(text, other_terms))
sampling_frame["title_other_signal_hit_count"] = title_surface.map(lambda text: count_hits(text, other_terms))
sampling_frame["title_other_signal_matched_terms"] = title_surface.map(lambda text: matched_terms(text, other_terms))

sampling_frame["pool_supply_like"] = (sampling_frame["supply_discriminative_hit_count"] > 0) | (sampling_frame["supply_recall_hit_count"] >= 2)
sampling_frame["pool_demand_like"] = (sampling_frame["demand_discriminative_hit_count"] > 0) | (sampling_frame["demand_recall_hit_count"] > 0)
sampling_frame["pool_environment_like"] = (sampling_frame["environment_discriminative_hit_count"] > 0) | (sampling_frame["environment_recall_hit_count"] >= 2)
sampling_frame["pool_other_like_priority"] = (
	(sampling_frame["title_other_signal_hit_count"] > 0)
	& ~(
		(sampling_frame["supply_discriminative_hit_count"] > 0)
		& (sampling_frame["demand_discriminative_hit_count"] > 0)
		& (sampling_frame["environment_discriminative_hit_count"] > 0)
	)
)
sampling_frame["pool_other_like"] = sampling_frame["other_signal_hit_count"] > 0
sampling_frame["all_three_discriminative_hit"] = (
	(sampling_frame["supply_discriminative_hit_count"] > 0)
	& (sampling_frame["demand_discriminative_hit_count"] > 0)
	& (sampling_frame["environment_discriminative_hit_count"] > 0)
)

SAMPLING_FRAME_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
sampling_frame.to_csv(SAMPLING_FRAME_OUTPUT, index=False)
sampling_frame.head()

# %% [markdown]
# ## 4. Draw Round-1 Sample
#
# Demand and other-like pools are sampled first because they are the important
# boundary pools for the next model-labeling phase.

# %%
taken_doc_ids: set[str] = set()
sample_parts = []
pool_specs = [
	("demand-like", sampling_frame["pool_demand_like"], None),
	("other-like", sampling_frame["pool_other_like"], sampling_frame["pool_other_like_priority"]),
	("supply-like", sampling_frame["pool_supply_like"], None),
	("environment-like", sampling_frame["pool_environment_like"], None),
]
for pool_name, mask, priority in pool_specs:
	part = sample_from_pool(
		sampling_frame,
		pool_name=pool_name,
		mask=mask,
		taken_doc_ids=taken_doc_ids,
		target_n=TARGET_PER_POOL,
		priority_mask=priority,
	)
	taken_doc_ids.update(part["doc_id"].tolist())
	sample_parts.append(part)

round1_sample = pd.concat(sample_parts, ignore_index=True)
round1_sample = round1_sample[
	[
		"doc_id",
		"sample_pool",
		"province",
		"year",
		"title",
		"issuing_agency",
		"publish_date",
		"source_url",
		"clean_text",
		"text_len",
		"pool_supply_like",
		"pool_demand_like",
		"pool_environment_like",
		"pool_other_like",
		"pool_other_like_priority",
		"supply_recall_hit_count",
		"supply_discriminative_hit_count",
		"demand_recall_hit_count",
		"demand_discriminative_hit_count",
		"environment_recall_hit_count",
		"environment_discriminative_hit_count",
		"other_signal_hit_count",
		"title_other_signal_hit_count",
		"supply_discriminative_matched_terms",
		"demand_discriminative_matched_terms",
		"environment_discriminative_matched_terms",
		"other_signal_matched_terms",
	]
].copy()

ROUND1_SAMPLE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
round1_sample.to_csv(ROUND1_SAMPLE_OUTPUT, index=False)
round1_sample["sample_pool"].value_counts()

# %% [markdown]
# ## 5. QA Outputs

# %%
coverage_rows = []
for _, row in rule_keywords.iterrows():
	term = row["term"]
	coverage_rows.append(
		{
			**row.to_dict(),
			"records_hit": int(text_surface.map(lambda text, term=term: term in text).sum()),
			"record_hit_share": float(text_surface.map(lambda text, term=term: term in text).mean()),
			"title_records_hit": int(title_surface.map(lambda text, term=term: term in text).sum()),
			"title_record_hit_share": float(title_surface.map(lambda text, term=term: term in text).mean()),
		}
	)
rule_coverage = pd.DataFrame(coverage_rows)
rule_coverage.to_csv(RULE_COVERAGE_OUTPUT, index=False)

pool_summary_rows = []
for pool_name, column in [
	("supply-like", "pool_supply_like"),
	("demand-like", "pool_demand_like"),
	("environment-like", "pool_environment_like"),
	("other-like", "pool_other_like"),
	("other-like-priority", "pool_other_like_priority"),
]:
	mask = sampling_frame[column]
	pool_summary_rows.append(
		{
			"pool": pool_name,
			"candidate_records": int(mask.sum()),
			"candidate_share": float(mask.mean()),
			"sample_records": int(round1_sample["sample_pool"].eq(pool_name).sum())
			if pool_name != "other-like-priority"
			else int(round1_sample.loc[round1_sample["sample_pool"].eq("other-like"), "pool_other_like_priority"].sum()),
			"target_records": TARGET_PER_POOL if pool_name != "other-like-priority" else pd.NA,
			"is_sufficient": bool(mask.sum() >= TARGET_PER_POOL) if pool_name != "other-like-priority" else bool(mask.sum() > 0),
		}
	)
pool_summary = pd.DataFrame(pool_summary_rows)
pool_summary.to_csv(POOL_SUMMARY_OUTPUT, index=False)

sample_year_summary = (
	round1_sample.groupby(["sample_pool", "year"])
	.size()
	.reset_index(name="records")
	.assign(summary_type="sample_pool_year")
	.rename(columns={"sample_pool": "group_1", "year": "group_2"})
)
sample_province_summary = (
	round1_sample.groupby(["sample_pool", "province"])
	.size()
	.reset_index(name="records")
	.assign(summary_type="sample_pool_province")
	.rename(columns={"sample_pool": "group_1", "province": "group_2"})
)
sample_pool_summary = (
	round1_sample.groupby("sample_pool")
	.size()
	.reset_index(name="records")
	.assign(summary_type="sample_pool", group_2="")
	.rename(columns={"sample_pool": "group_1"})
)
sample_summary = pd.concat(
	[
		sample_pool_summary[["summary_type", "group_1", "group_2", "records"]],
		sample_year_summary[["summary_type", "group_1", "group_2", "records"]],
		sample_province_summary[["summary_type", "group_1", "group_2", "records"]],
	],
	ignore_index=True,
)
sample_summary.to_csv(SAMPLE_SUMMARY_OUTPUT, index=False)

rule_notes = pd.DataFrame(
	[
		{
			"topic": "keyword_role_change",
			"note": "Keywords are now sampling and diagnostic rules, not final policy-tool labels.",
		},
		{
			"topic": "recall_terms",
			"note": "Broad high-coverage terms are retained for candidate recall but require context before interpretation.",
		},
		{
			"topic": "discriminative_terms",
			"note": "Specific policy-tool terms are used to construct supply/demand/environment-like sampling pools.",
		},
		{
			"topic": "other_signal_terms",
			"note": "Procedural terms define other-like boundary samples but are not final other labels.",
		},
		{
			"topic": "round1_sample",
			"note": "Round-1 sample is deterministic, without replacement, and balanced at 200 records per pool.",
		},
	]
)
rule_notes.to_csv(RULE_NOTES_OUTPUT, index=False)

pool_summary

# %%
sample_summary.head(20)

# %% [markdown]
# ## 6. Output Checks

# %%
output_checks = pd.DataFrame(
	[
		{"check": "rule_keywords_nonempty", "value": len(rule_keywords), "expected": "> 0"},
		{"check": "label_docs_records", "value": len(label_docs), "expected": 4475},
		{"check": "sampling_frame_records", "value": len(sampling_frame), "expected": 4475},
		{"check": "round1_sample_records", "value": len(round1_sample), "expected": 800},
		{"check": "round1_doc_id_unique", "value": round1_sample["doc_id"].is_unique, "expected": True},
		{"check": "sample_pool_counts", "value": round1_sample["sample_pool"].value_counts().to_dict(), "expected": "200 each"},
		{"check": "year_coverage", "value": sorted(round1_sample["year"].unique().tolist()), "expected": YEARS},
		{"check": "other_like_priority_records_in_sample", "value": int(round1_sample.loc[round1_sample["sample_pool"].eq("other-like"), "pool_other_like_priority"].sum()), "expected": "> 0"},
	]
)
output_checks
