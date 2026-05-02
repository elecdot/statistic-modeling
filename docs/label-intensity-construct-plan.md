DeepSeek 官方文档显示其 Chat API 可用 OpenAI-compatible 调用方式，`base_url` 为 `https://api.deepseek.com`，当前模型名包括 `deepseek-v4-flash` 与 `deepseek-v4-pro`；同时 Chat Completions 支持 `response_format={"type":"json_object"}` 的 JSON 输出模式。([DeepSeek API Docs][1]) MacBERT 这里使用 `hfl/chinese-macbert-base`，其模型卡说明 MacBERT 是基于 BERT 架构改进的中文预训练模型，并建议使用 BERT 相关函数加载。([Hugging Face][2]) 多标签训练采用 `BCEWithLogitsLoss`，它把 Sigmoid 与 BCELoss 合在一个损失函数里，比手动 `sigmoid + BCELoss` 数值更稳定，并支持 `pos_weight` 处理类别不平衡。([PyTorch 文档][3])

---

# 政策文本多标签分类设计书

## 1. 任务定义

### 1.1 输入

输入为已经采集并清洗后的政策文件数据，每一行是一篇政策文件：

```text
doc_id
province
year
title
issuing_agency
publish_date
source_url
clean_text
```

本文不再做条款级分类，而是以**整篇政策文件**为分析单位。

---

## 1.2 输出

每篇政策输出四个独立概率：

```text
p_supply       ∈ [0, 1]
p_demand       ∈ [0, 1]
p_environment  ∈ [0, 1]
p_other        ∈ [0, 1]
```

注意：这四个概率**不要求相加为 1**。

含义如下：

| 输出              | 含义                                              |
| --------------- | ----------------------------------------------- |
| `p_supply`      | 该政策是否包含供给型政策工具                                  |
| `p_demand`      | 该政策是否包含需求型政策工具                                  |
| `p_environment` | 该政策是否包含环境型政策工具                                  |
| `p_other`       | 该文本是否不应进入政策工具分析，例如纯通知、公示、新闻、非专精特新相关文本、无实质政策工具文本 |

前三类可以同时为高概率；`other` 是排除类，原则上如果 `p_other` 很高，前三类应较低。

---

## 1.3 标签定义

### 供给型 `supply`

政府直接提供资源。

典型内容：

```text
资金奖励、财政补贴、研发补助、技术改造补助、人才支持、培训服务、公共服务平台、基础设施、创新平台、数字化改造支持
```

### 需求型 `demand`

政府创造、扩大或引导市场需求。

典型内容：

```text
政府采购、首台套推广、示范应用、应用场景开放、供需对接、展会推广、市场开拓、产品推广、产业链对接
```

### 环境型 `environment`

政府改善制度环境、金融环境、知识产权环境、营商环境。

典型内容：

```text
税收优惠、融资担保、贷款贴息、上市培育、知识产权保护、标准制定、认定评价、信用体系、营商环境、法规制度、服务机制
```

注意：**金融支持、贷款、担保、上市培育通常归 environment，不归 supply**。除非文本明确写财政直接奖励、补助、拨款。

### 其他类 `other`

文本不适合进入政策工具分析。

典型情况：

```text
非专精特新相关文本
新闻报道
会议动态
名单公示
申报通知
转发通知
政策解读
只有程序性安排，没有实质扶持措施
正文缺失或网页噪声严重
```

边界规则：

```text
如果标题像通知，但正文包含明确扶持措施，不应直接判为 other。
如果只是“组织申报”“名单公示”“转发通知”，且没有实质扶持工具，则判为 other。
```

---

# 2. 总体流程

```text
4475 篇政策文件
  ↓
关键词预分层抽样
  ↓
抽取 800 篇送 DeepSeek V4 标注
  ↓
得到多标签银标训练集
  ↓
训练 MacBERT 多标签分类模型
  ↓
MacBERT 对 4475 篇全量预测
  ↓
筛选低置信度 / 边界样本
  ↓
再抽 200–400 篇送 DeepSeek V4 补标
  ↓
合并训练集，二次训练 MacBERT
  ↓
最终对 4475 篇输出四个概率
  ↓
输出 policy_classified_full.csv
```

推荐标注量：

```text
最低可行：800 篇
推荐稳定版：1000–1200 篇
不建议低于：600 篇
```

---

# 3. 抽样策略

不要随机抽样。先用关键词做预分层，保证四个维度都有训练样本。

## 3.1 候选池规则

```python
SUPPLY_KWS = [
    "奖励", "补贴", "补助", "专项资金", "财政支持", "资金支持",
    "人才", "培训", "公共服务平台", "服务平台", "技术改造", "研发补助",
]

DEMAND_KWS = [
    "政府采购", "采购", "首台套", "示范应用", "推广应用", "供需对接",
    "市场开拓", "展会", "应用场景", "产品推广",
]

ENVIRONMENT_KWS = [
    "融资", "贷款", "担保", "贴息", "税收", "知识产权", "标准",
    "认定", "评价", "上市", "营商环境", "服务机制", "信用",
]

OTHER_KWS = [
    "申报", "通知", "公示", "名单", "公布", "转发", "会议",
    "座谈", "解读", "新闻", "工作动态",
]
```

第一轮建议：

```text
supply-like       200 篇
demand-like       200 篇
environment-like  200 篇
other-like        200 篇
合计              800 篇
```

第二轮从模型预测结果中抽：

```text
p 值接近阈值的样本
p_other 高但前三类也不低的样本
demand 边界样本
规则命中类别与模型预测概率冲突的样本
```

---

# 4. DeepSeek 标注输出格式

DeepSeek 不输出单标签，而输出四个独立概率与证据。

目标 JSON：

```json
{
  "p_supply": 0.0,
  "supply_evidence": [],
  "p_demand": 0.0,
  "demand_evidence": [],
  "p_environment": 0.0,
  "environment_evidence": [],
  "p_other": 0.0,
  "other_reason": "",
  "has_substantive_policy_tool": true,
  "is_srdi_related": true,
  "summary_reason": ""
}
```

训练时可把概率转成二值标签：

```python
y_supply = int(p_supply >= 0.5)
y_demand = int(p_demand >= 0.5)
y_environment = int(p_environment >= 0.5)
y_other = int(p_other >= 0.6 and max(p_supply, p_demand, p_environment) < 0.4)
```

也可以直接把 DeepSeek 概率作为 soft label 训练。第一版建议先用二值标签，流程更稳。

---

# 5. 代码示例一：调用 DeepSeek V4 抽样标注

文件：`scripts/label_with_deepseek.py`

运行前准备：

```bash
pip install openai pandas tqdm python-dotenv
```

环境变量：

```bash
export DEEPSEEK_API_KEY="你的 API Key"
```

代码：

```python
import os
import re
import json
import time
import hashlib
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from openai import OpenAI


INPUT_CSV = "data/policies_clean.csv"
OUTPUT_JSONL = "data/deepseek_labels_round1.jsonl"
SAMPLE_CSV = "data/deepseek_sample_round1.csv"

MODEL_NAME = "deepseek-v4-pro"

LABEL_COLUMNS = [
    "p_supply",
    "p_demand",
    "p_environment",
    "p_other",
]


client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)


def normalize_text(text: str, max_chars: int = 16000) -> str:
    """
    控制输入长度，避免成本过高。
    第一版可以截断；后续可以替换为更精细的 doc_card。
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", "\n", text).strip()
    return text[:max_chars]


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def build_system_prompt() -> str:
    return """
你是政策文本分类专家。你的任务是对中文政策文件进行多标签政策工具判断。
必须输出严格 JSON，不要输出 Markdown，不要输出解释性正文。
""".strip()


def build_user_prompt(row: pd.Series) -> str:
    title = str(row.get("title", ""))
    province = str(row.get("province", ""))
    year = str(row.get("year", ""))
    issuing_agency = str(row.get("issuing_agency", ""))
    text = normalize_text(str(row.get("clean_text", "")))

    return f"""
请对以下“整篇政策文件”进行多标签政策工具判断。

你需要分别判断该文件是否包含以下四类内容：

1. supply：供给型政策工具。政府直接提供资源，包括资金奖励、财政补贴、人才支持、技术服务、研发补助、公共服务平台、基础设施等。
2. demand：需求型政策工具。政府创造或引导市场需求，包括政府采购、示范应用、首台套推广、供需对接、市场开拓、展会推广、应用场景开放等。
3. environment：环境型政策工具。政府改善制度环境或发展环境，包括税收优惠、融资担保、贷款贴息、知识产权、标准制定、认定评价、营商环境、上市培育、法规制度等。
4. other：非有效政策工具文本。包括非专精特新相关文本、新闻报道、名单公示、纯申报通知、转发通知、会议动态、政策解读、正文缺失、没有实质扶持措施的文本。

判断规则：
- supply、demand、environment 可以同时为高概率。
- other 表示该文本整体不应进入政策工具分析。
- 如果文本包含任一实质性 supply / demand / environment 政策工具，则 other 应为低概率。
- 对每一类分别给出 0-1 概率。
- 每个概率必须独立判断，不要求四个概率相加为 1。
- 必须给出支持判断的原文证据。
- 必须输出 JSON。

输出 JSON 格式如下：
{{
  "p_supply": 0.0,
  "supply_evidence": ["..."],
  "p_demand": 0.0,
  "demand_evidence": ["..."],
  "p_environment": 0.0,
  "environment_evidence": ["..."],
  "p_other": 0.0,
  "other_reason": "...",
  "has_substantive_policy_tool": true,
  "is_srdi_related": true,
  "summary_reason": "..."
}}

政策元数据：
标题：{title}
省份：{province}
年份：{year}
发文机关：{issuing_agency}

政策正文：
{text}
""".strip()


def call_deepseek(row: pd.Series, max_retries: int = 3) -> dict:
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(row)},
    ]

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
                max_tokens=2048,
            )
            content = response.choices[0].message.content

            if not content or not content.strip():
                raise ValueError("Empty response content")

            data = json.loads(content)

            for col in LABEL_COLUMNS:
                if col not in data:
                    raise ValueError(f"Missing field: {col}")
                data[col] = float(data[col])
                data[col] = max(0.0, min(1.0, data[col]))

            return data

        except Exception as e:
            last_error = e
            time.sleep(2 ** attempt)

    raise RuntimeError(f"DeepSeek call failed after retries: {last_error}")


def make_rule_pools(df: pd.DataFrame) -> pd.DataFrame:
    supply_kws = ["奖励", "补贴", "补助", "专项资金", "财政支持", "人才", "培训", "平台", "技术改造", "研发"]
    demand_kws = ["政府采购", "采购", "首台套", "示范应用", "推广应用", "供需对接", "市场开拓", "展会", "应用场景"]
    env_kws = ["融资", "贷款", "担保", "贴息", "税收", "知识产权", "标准", "认定", "评价", "上市", "营商环境"]
    other_kws = ["申报", "通知", "公示", "名单", "公布", "转发", "会议", "座谈", "解读", "新闻"]

    text = (df["title"].fillna("") + "\n" + df["clean_text"].fillna("")).astype(str)

    def hit_any(s: str, kws: list[str]) -> bool:
        return any(kw in s for kw in kws)

    df = df.copy()
    df["pool_supply"] = text.apply(lambda s: hit_any(s, supply_kws))
    df["pool_demand"] = text.apply(lambda s: hit_any(s, demand_kws))
    df["pool_environment"] = text.apply(lambda s: hit_any(s, env_kws))
    df["pool_other"] = text.apply(lambda s: hit_any(s, other_kws))
    return df


def stratified_sample(df: pd.DataFrame, n_each: int = 200, seed: int = 42) -> pd.DataFrame:
    df = make_rule_pools(df)

    sampled_ids = set()
    parts = []

    pool_defs = [
        ("supply", "pool_supply"),
        ("demand", "pool_demand"),
        ("environment", "pool_environment"),
        ("other", "pool_other"),
    ]

    for pool_name, col in pool_defs:
        candidates = df[df[col] & ~df["doc_id"].isin(sampled_ids)]
        take_n = min(n_each, len(candidates))
        part = candidates.sample(n=take_n, random_state=seed)
        part = part.copy()
        part["sample_pool"] = pool_name
        sampled_ids.update(part["doc_id"].tolist())
        parts.append(part)

    sample_df = pd.concat(parts, ignore_index=True)
    return sample_df


def load_done_ids(output_jsonl: str) -> set:
    path = Path(output_jsonl)
    if not path.exists():
        return set()

    done = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                done.add(str(obj["doc_id"]))
    return done


def main():
    df = pd.read_csv(INPUT_CSV)
    df["doc_id"] = df["doc_id"].astype(str)

    if Path(SAMPLE_CSV).exists():
        sample_df = pd.read_csv(SAMPLE_CSV)
        sample_df["doc_id"] = sample_df["doc_id"].astype(str)
    else:
        sample_df = stratified_sample(df, n_each=200)
        Path(SAMPLE_CSV).parent.mkdir(parents=True, exist_ok=True)
        sample_df.to_csv(SAMPLE_CSV, index=False, encoding="utf-8-sig")

    done_ids = load_done_ids(OUTPUT_JSONL)
    Path(OUTPUT_JSONL).parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSONL, "a", encoding="utf-8") as fout:
        for _, row in tqdm(sample_df.iterrows(), total=len(sample_df)):
            doc_id = str(row["doc_id"])
            if doc_id in done_ids:
                continue

            result = call_deepseek(row)

            record = {
                "doc_id": doc_id,
                "title": row.get("title", ""),
                "province": row.get("province", ""),
                "year": row.get("year", ""),
                "sample_pool": row.get("sample_pool", ""),
                "text_hash": text_hash(str(row.get("clean_text", ""))),
                **result,
            }

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            fout.flush()


if __name__ == "__main__":
    main()
```

输出文件：

```text
data/deepseek_labels_round1.jsonl
```

---

# 6. 代码示例二：构造 MacBERT 训练集

文件：`scripts/build_multilabel_dataset.py`

```python
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


POLICIES_CSV = "data/policies_clean.csv"
LABELS_JSONL = "data/deepseek_labels_round1.jsonl"
OUTPUT_DIR = Path("data/macbert_multilabel")


def load_jsonl(path: str) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def make_model_input(row: pd.Series, max_front_chars: int = 1200, max_keyword_chars: int = 1200) -> str:
    """
    MacBERT 不能直接吃超长全文。
    第一版输入 = 标题 + 机关 + 年份 + 正文前部 + 关键词附近片段。
    """
    title = str(row.get("title", ""))
    agency = str(row.get("issuing_agency", ""))
    year = str(row.get("year", ""))
    text = str(row.get("clean_text", ""))

    front = text[:max_front_chars]

    keywords = [
        "奖励", "补贴", "补助", "专项资金", "政府采购", "示范应用", "供需对接",
        "融资", "贷款", "担保", "贴息", "税收", "知识产权", "标准", "营商环境",
        "申报", "公示", "名单", "转发", "会议"
    ]

    snippets = []
    for kw in keywords:
        idx = text.find(kw)
        if idx != -1:
            start = max(0, idx - 120)
            end = min(len(text), idx + 260)
            snippets.append(text[start:end])

    keyword_context = "\n".join(snippets)
    keyword_context = keyword_context[:max_keyword_chars]

    return f"""
标题：{title}
发文机关：{agency}
年份：{year}

正文前部：
{front}

关键词附近内容：
{keyword_context}
""".strip()


def binarize(row: pd.Series) -> list[int]:
    p_supply = float(row["p_supply"])
    p_demand = float(row["p_demand"])
    p_environment = float(row["p_environment"])
    p_other = float(row["p_other"])

    y_supply = int(p_supply >= 0.50)
    y_demand = int(p_demand >= 0.50)
    y_environment = int(p_environment >= 0.50)

    # other 是排除类，阈值应更严格
    y_other = int(
        p_other >= 0.60
        and max(p_supply, p_demand, p_environment) < 0.40
    )

    return [y_supply, y_demand, y_environment, y_other]


def main():
    policies = pd.read_csv(POLICIES_CSV)
    policies["doc_id"] = policies["doc_id"].astype(str)

    labels = load_jsonl(LABELS_JSONL)
    labels["doc_id"] = labels["doc_id"].astype(str)

    df = labels.merge(
        policies,
        on="doc_id",
        how="left",
        suffixes=("_label", ""),
    )

    df["text"] = df.apply(make_model_input, axis=1)
    df["labels"] = df.apply(binarize, axis=1)

    # 可选：去掉全 0 样本，但这里不建议，因为 all-zero 对学习“无明显工具”有价值
    # df = df[df["labels"].apply(lambda x: sum(x) > 0)]

    train_df, temp_df = train_test_split(
        df,
        test_size=0.30,
        random_state=42,
        shuffle=True,
    )

    valid_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        random_state=42,
        shuffle=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    keep_cols = ["doc_id", "text", "labels", "p_supply", "p_demand", "p_environment", "p_other"]
    train_df[keep_cols].to_json(OUTPUT_DIR / "train.jsonl", orient="records", lines=True, force_ascii=False)
    valid_df[keep_cols].to_json(OUTPUT_DIR / "valid.jsonl", orient="records", lines=True, force_ascii=False)
    test_df[keep_cols].to_json(OUTPUT_DIR / "test.jsonl", orient="records", lines=True, force_ascii=False)

    print("Saved:")
    print(OUTPUT_DIR / "train.jsonl", len(train_df))
    print(OUTPUT_DIR / "valid.jsonl", len(valid_df))
    print(OUTPUT_DIR / "test.jsonl", len(test_df))


if __name__ == "__main__":
    main()
```

---

# 7. 代码示例三：微调 MacBERT 多标签模型

文件：`scripts/train_macbert_multilabel.py`

安装依赖：

```bash
pip install torch transformers datasets scikit-learn numpy
```

Hugging Face 的 `Trainer` 是一个完整的 PyTorch 训练与评估循环，可配合 `TrainingArguments` 管理训练参数；这里我们用自定义 Trainer 覆盖损失函数，以便加入 `pos_weight`。([Hugging Face][4]) scikit-learn 的 `f1_score` 支持 multilabel 任务，并可使用 `micro`、`macro`、`samples` 等平均方式。([Scikit-learn][5])

```python
import json
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch import nn
from datasets import load_dataset
from sklearn.metrics import f1_score, precision_score, recall_score
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding,
)


MODEL_NAME = "hfl/chinese-macbert-base"
DATA_DIR = "data/macbert_multilabel"
OUTPUT_DIR = "outputs/macbert-policy-multilabel"

LABEL_NAMES = ["supply", "demand", "environment", "other"]
NUM_LABELS = len(LABEL_NAMES)


def compute_pos_weight(train_labels: np.ndarray) -> torch.Tensor:
    """
    pos_weight = negative_count / positive_count
    用于缓解某些标签正例过少的问题，尤其 demand。
    """
    pos = train_labels.sum(axis=0)
    neg = train_labels.shape[0] - pos
    pos = np.clip(pos, 1, None)
    pos_weight = neg / pos
    return torch.tensor(pos_weight, dtype=torch.float)


class WeightedMultiLabelTrainer(Trainer):
    def __init__(self, *args, pos_weight: Optional[torch.Tensor] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.pos_weight = pos_weight

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        labels = inputs.pop("labels").float()
        outputs = model(**inputs)
        logits = outputs.logits

        if self.pos_weight is not None:
            pos_weight = self.pos_weight.to(logits.device)
            loss_fct = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
        else:
            loss_fct = nn.BCEWithLogitsLoss()

        loss = loss_fct(logits, labels)
        return (loss, outputs) if return_outputs else loss


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = sigmoid(logits)

    # 第一版统一阈值 0.5；后续可按 valid set 为每个标签调阈值
    preds = (probs >= 0.5).astype(int)
    labels = labels.astype(int)

    metrics = {
        "micro_f1": f1_score(labels, preds, average="micro", zero_division=0),
        "macro_f1": f1_score(labels, preds, average="macro", zero_division=0),
        "samples_f1": f1_score(labels, preds, average="samples", zero_division=0),
        "micro_precision": precision_score(labels, preds, average="micro", zero_division=0),
        "micro_recall": recall_score(labels, preds, average="micro", zero_division=0),
    }

    per_label_f1 = f1_score(labels, preds, average=None, zero_division=0)
    per_label_precision = precision_score(labels, preds, average=None, zero_division=0)
    per_label_recall = recall_score(labels, preds, average=None, zero_division=0)

    for i, name in enumerate(LABEL_NAMES):
        metrics[f"{name}_f1"] = per_label_f1[i]
        metrics[f"{name}_precision"] = per_label_precision[i]
        metrics[f"{name}_recall"] = per_label_recall[i]

    return metrics


def main():
    dataset = load_dataset(
        "json",
        data_files={
            "train": f"{DATA_DIR}/train.jsonl",
            "validation": f"{DATA_DIR}/valid.jsonl",
            "test": f"{DATA_DIR}/test.jsonl",
        },
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def preprocess(batch):
        tokenized = tokenizer(
            batch["text"],
            truncation=True,
            max_length=512,
        )
        tokenized["labels"] = batch["labels"]
        return tokenized

    dataset = dataset.map(preprocess, batched=True)

    train_labels = np.array(dataset["train"]["labels"])
    pos_weight = compute_pos_weight(train_labels)
    print("pos_weight:", dict(zip(LABEL_NAMES, pos_weight.tolist())))

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label={i: name for i, name in enumerate(LABEL_NAMES)},
        label2id={name: i for i, name in enumerate(LABEL_NAMES)},
        problem_type="multi_label_classification",
    )

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        gradient_accumulation_steps=2,
        num_train_epochs=5,
        weight_decay=0.01,
        warmup_ratio=0.1,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_steps=20,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = WeightedMultiLabelTrainer(
        model=model,
        args=args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
        pos_weight=pos_weight,
    )

    trainer.train()

    print("Validation metrics:")
    print(trainer.evaluate(dataset["validation"]))

    print("Test metrics:")
    print(trainer.evaluate(dataset["test"]))

    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)


if __name__ == "__main__":
    main()
```

---

# 8. 代码示例四：全量预测 4475 篇政策

文件：`scripts/predict_all_policies.py`

```python
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification


MODEL_DIR = "outputs/macbert-policy-multilabel"
INPUT_CSV = "data/policies_clean.csv"
OUTPUT_CSV = "data/policy_classified_full.csv"

LABEL_NAMES = ["supply", "demand", "environment", "other"]


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def make_model_input(row: pd.Series, max_front_chars: int = 1200, max_keyword_chars: int = 1200) -> str:
    title = str(row.get("title", ""))
    agency = str(row.get("issuing_agency", ""))
    year = str(row.get("year", ""))
    text = str(row.get("clean_text", ""))

    front = text[:max_front_chars]

    keywords = [
        "奖励", "补贴", "补助", "专项资金", "政府采购", "示范应用", "供需对接",
        "融资", "贷款", "担保", "贴息", "税收", "知识产权", "标准", "营商环境",
        "申报", "公示", "名单", "转发", "会议"
    ]

    snippets = []
    for kw in keywords:
        idx = text.find(kw)
        if idx != -1:
            start = max(0, idx - 120)
            end = min(len(text), idx + 260)
            snippets.append(text[start:end])

    keyword_context = "\n".join(snippets)[:max_keyword_chars]

    return f"""
标题：{title}
发文机关：{agency}
年份：{year}

正文前部：
{front}

关键词附近内容：
{keyword_context}
""".strip()


def labels_from_probs(p_supply, p_demand, p_environment, p_other):
    supply_label = int(p_supply >= 0.50)
    demand_label = int(p_demand >= 0.50)
    environment_label = int(p_environment >= 0.50)

    other_label = int(
        p_other >= 0.60
        and max(p_supply, p_demand, p_environment) < 0.40
    )

    is_valid_policy_tool = int(
        max(p_supply, p_demand, p_environment) >= 0.50
        and other_label == 0
    )

    return supply_label, demand_label, environment_label, other_label, is_valid_policy_tool


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.to(device)
    model.eval()

    df = pd.read_csv(INPUT_CSV)
    outputs = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        text = make_model_input(row)

        encoded = tokenizer(
            text,
            truncation=True,
            max_length=512,
            padding=False,
            return_tensors="pt",
        )

        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            logits = model(**encoded).logits.detach().cpu().numpy()[0]

        probs = sigmoid(logits)
        p_supply, p_demand, p_environment, p_other = probs.tolist()

        (
            supply_label,
            demand_label,
            environment_label,
            other_label,
            is_valid_policy_tool,
        ) = labels_from_probs(p_supply, p_demand, p_environment, p_other)

        max_tool_prob = max(p_supply, p_demand, p_environment)

        outputs.append({
            "doc_id": row.get("doc_id", ""),
            "province": row.get("province", ""),
            "year": row.get("year", ""),
            "title": row.get("title", ""),
            "issuing_agency": row.get("issuing_agency", ""),
            "publish_date": row.get("publish_date", ""),
            "source_url": row.get("source_url", ""),

            "p_supply": p_supply,
            "p_demand": p_demand,
            "p_environment": p_environment,
            "p_other": p_other,

            "supply_label": supply_label,
            "demand_label": demand_label,
            "environment_label": environment_label,
            "other_label": other_label,
            "is_valid_policy_tool": is_valid_policy_tool,

            "max_tool_prob": max_tool_prob,
            "model_version": MODEL_DIR,
        })

    out_df = pd.DataFrame(outputs)
    Path(OUTPUT_CSV).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved to {OUTPUT_CSV}")
    print(out_df[["p_supply", "p_demand", "p_environment", "p_other"]].describe())


if __name__ == "__main__":
    main()
```

---

# 9. 二轮补标策略

第一次训练后，从 `policy_classified_full.csv` 中筛样本：

```python
import pandas as pd

df = pd.read_csv("data/policy_classified_full.csv")

# 边界样本：模型不确定
uncertain = df[
    (
        df[["p_supply", "p_demand", "p_environment", "p_other"]].max(axis=1).between(0.35, 0.65)
    )
]

# other 冲突：p_other 高，但政策工具概率也高
other_conflict = df[
    (df["p_other"] >= 0.50)
    & (df[["p_supply", "p_demand", "p_environment"]].max(axis=1) >= 0.40)
]

# demand 边界：需求型往往稀缺，需额外补样
demand_boundary = df[
    df["p_demand"].between(0.30, 0.70)
]

sample2 = pd.concat([
    uncertain.sample(min(120, len(uncertain)), random_state=42),
    other_conflict.sample(min(100, len(other_conflict)), random_state=42),
    demand_boundary.sample(min(120, len(demand_boundary)), random_state=42),
]).drop_duplicates("doc_id")

sample2.to_csv("data/deepseek_sample_round2.csv", index=False, encoding="utf-8-sig")
```

然后复用 `label_with_deepseek.py`，把输入 sample 改为 round2 文件即可。

---

# 10. 最终输出表设计

## 10.1 全量表：`policy_classified_full.csv`

```text
doc_id
province
year
title
issuing_agency
publish_date
source_url

p_supply
p_demand
p_environment
p_other

supply_label
demand_label
environment_label
other_label
is_valid_policy_tool

max_tool_prob
model_version
```

## 10.2 有效政策工具表：`policy_tool_valid.csv`

```python
import pandas as pd

df = pd.read_csv("data/policy_classified_full.csv")

valid = df[df["is_valid_policy_tool"] == 1].copy()

valid.to_csv(
    "data/policy_tool_valid.csv",
    index=False,
    encoding="utf-8-sig",
)
```

后续构建政策强度时，推荐直接使用概率聚合：

```text
SupplyIntensity_{province, year}      = Σ p_supply
DemandIntensity_{province, year}      = Σ p_demand
EnvironmentIntensity_{province, year} = Σ p_environment
```

而不是只用二值标签计数。

---

# 11. 方法章节推荐表述

可以直接改写进论文：

```text
本文以整篇政策文件为分析单位，构建面向专精特新政策文本的多标签政策工具分类任务。不同于互斥式单标签分类，本文允许同一政策文件同时包含供给型、需求型和环境型政策工具，并额外设置 other 维度，用于识别非专精特新相关文本、程序性通知、公示公告、新闻动态以及不包含实质性政策工具的文件。

考虑到人工标注成本较高，本文采用 DeepSeek V4 对抽样政策文件进行结构化标注，要求其分别输出供给型、需求型、环境型和 other 四个维度的概率、原文证据和判断理由，形成 DeepSeek-assisted silver labels。随后，本文使用 hfl/chinese-macbert-base 作为基础模型，将政策文件标题、发文机关、年份、正文前部及政策关键词附近片段拼接为模型输入，并采用多标签学习方式进行微调。模型输出层使用 sigmoid 激活函数，损失函数采用 BCEWithLogitsLoss，以同时学习四个独立标签的判别概率。

为降低抽样标注不足带来的边界误差，本文采用两轮标注策略：第一轮基于关键词预分层抽取样本，保证供给型、需求型、环境型和 other 类候选样本均被覆盖；第二轮从 MacBERT 初次预测结果中选取低置信度、需求型边界和 other 冲突样本，再交由 DeepSeek V4 补充标注。最终，本文使用二次训练后的 MacBERT 模型对 4475 篇政策文件进行全量预测，并输出每篇政策在四个维度上的概率。后续政策强度测度中，本文剔除 other 概率较高的无效文本，并以省份—年份为单位聚合供给型、需求型和环境型概率，构建政策工具强度指标。
```

---

# 12. 最终执行清单

```text
1. 准备 data/policies_clean.csv
2. 运行 scripts/label_with_deepseek.py，抽样 800 篇并标注
3. 运行 scripts/build_multilabel_dataset.py，生成 train / valid / test
4. 运行 scripts/train_macbert_multilabel.py，训练第一版 MacBERT
5. 运行 scripts/predict_all_policies.py，预测 4475 篇
6. 从预测结果中抽取 200–400 篇边界样本
7. 再次调用 DeepSeek 标注 round2
8. 合并 round1 + round2 标签
9. 重建训练集并二次训练 MacBERT
10. 最终预测 4475 篇，输出 policy_classified_full.csv
11. 剔除 other 高概率文本，输出 policy_tool_valid.csv
12. 用 Σp_supply / Σp_demand / Σp_environment 构建省份—年份政策工具强度
```

[1]: https://api-docs.deepseek.com/?utm_source=chatgpt.com "Your First API Call | DeepSeek API Docs"
[2]: https://huggingface.co/hfl/chinese-macbert-base?utm_source=chatgpt.com "hfl/chinese-macbert-base · Hugging Face"
[3]: https://docs.pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html?highlight=all&utm_source=chatgpt.com "BCEWithLogitsLoss — PyTorch 2.10 documentation"
[4]: https://huggingface.co/docs/transformers/main_classes/trainer?utm_source=chatgpt.com "Trainer · Hugging Face"
[5]: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.f1_score.html?highlight=f1&utm_source=chatgpt.com "f1_score — scikit-learn 1.7.1 documentation"
