# Manual SRDI Paper Draft Notes

本文档用于阶段性论文起草和研究思路梳理。它把当前已经完成的
手工 SRDI 政策数据、full-text 文本挖掘、描述性材料和标注准备工作
转写为论文可继续扩展的方法叙事。本文档不是任务板；活动工作入口仍以
项目根目录 `README.md#Open Loops` 为准。

## 1. 研究主线

本项目的核心问题是：专精特新“小巨人”认定是否促进企业创新，以及
地方支持政策强度和政策工具结构是否会影响该政策效果。企业层面的
因果识别由后续 staggered DID 完成，本文档对应的是政策文本层的
数据构造和变量准备。

政策文本部分承担两项功能：

1. 构造省份-年份层面的专精特新政策强度变量，用于与企业面板和 DID
   处理效应进行衔接。
2. 从政策文本中提取供给型、需求型、环境型工具倾向，用于刻画地方
   政策支持结构，并进一步检验不同政策工具是否具有不同的创新促进作用。

当前研究路线已经从“大范围继续扩展 crawler”转为“基于人工收集的
专精特新政策全量表进行稳定数据处理和文本挖掘”。这一转向的原因是：
论文阶段需要可控、可审计、覆盖中央和省级来源的政策样本，而不是继续
消耗时间在多来源 crawler 可行性上。

## 2. 数据来源与样本口径

当前主数据来源为：

- metadata workbook:
  `data/interim/manual_policy_all_keyword_srdi.xlsx`;
- full-text workbook:
  `data/interim/manual_policy_all_keyword_srdi_with_full_text.xlsx`.

样本为中央及省级来源中 metadata 包含“专精特新”的政策记录。主分析窗口
固定为 2020-2025 年。处理时排除 2026 年记录，保留 2020 年 1 月 1 日至
2025 年 12 月 31 日的政策。

当前 full-text processed 表为
`data/processed/manual_policy_srdi_policy_records_fulltext_v1.csv`，共
4475 条记录。其中地方政策 4266 条，中央政策 209 条。中央政策保留在
行级政策表和文本描述中，但不进入省份-年份差异强度表。省份层面将
`新疆维吾尔自治区` 与 `新疆生产建设兵团` 合并为 `新疆`，并保留
`source_label_original` 用于审计。

地方政策强度表为
`data/processed/province_year_srdi_policy_intensity_v0.csv`，覆盖 31 个
省级单位和 2020-2025 年 6 个年份，形成 186 个省份-年份观测。

论文中可以这样表述样本构造：

> 本文基于手工收集的中央及省级“专精特新”相关政策记录构建政策文本
> 数据集。样本覆盖 2020-2025 年，政策记录的检索和纳入以“专精特新”
> 关键词为核心。为与企业层面的地区面板衔接，本文将地方政策聚合到
> 省份-年份层面，并将新疆维吾尔自治区与新疆生产建设兵团统一记为
> “新疆”。中央政策用于总体政策文本描述和中央-地方对比，但不进入
> 地方省份差异强度的计算。

## 3. 政策强度变量的第一层构造

当前已经稳定落盘的 DID-facing 政策强度变量来自
`data/processed/province_year_srdi_policy_intensity_v0.csv`。该表以地方
省份-年份为观测单位，排除 `central`。核心变量包括：

- `srdi_policy_count`: 当年该省份专精特新相关政策数量；
- `log_srdi_policy_count_plus1`: `log(count + 1)` 形式的平滑强度；
- `total_keyword_count`: 关键词命中次数合计；
- `avg_keyword_count`: 平均关键词命中次数；
- `unique_agency_count`: 发文机构覆盖数量；
- `missing_agency_count`: 发文机构缺失记录数量。

这一层变量的优势是透明、稳定、与面板模型衔接简单。它可以作为论文中
最基础的地方政策支持强度指标。文本挖掘和后续模型标注则用于构造
第二层政策工具结构变量。

论文中可以这样表述：

> 本文首先以省份-年份内“专精特新”相关政策数量衡量地方政策支持强度，
> 并构造 `log(count + 1)` 作为主强度指标。该指标反映地方政府围绕
> 专精特新企业出台政策的活跃程度。中央政策由于不构成省份间差异，
> 不纳入该强度指标，但在文本描述和中央-地方政策特征比较中保留。

## 4. 从 Title/Abstract 到 Full-Text 的方法转向

早期 v0 文本挖掘使用 `title + abstract` 作为文本表面。该路径具有较强的
可解释性和较低噪声，但召回不足。基于人工抽查和词典修订，v0 词典从
53 项扩展到 85 项后，未命中记录由 352 条降至 271 条。

随后加入 full-text v1 路径。v1 保持相同样本窗口、省份标准化和 85 项
词典，只将文本表面从 `title + abstract` 替换为 `title + full_text`。
full-text v1 的关键诊断为：

- processed records: 4475;
- missing full text: 0;
- row-level full-text features: 4475;
- province-year full-text features: 186;
- no-tool-hit records: 2;
- zero-coverage dictionary terms: 0;
- terms matching at least 25% of records: 41.

v0/v1 比较显示，full text 几乎消除了 no-hit 问题，但也使宽泛政策词在
全文中高度饱和。因此，当前结论是：full-text v1 更适合作为主轴，
但其结果应解释为聚合层面的政策文本强度代理，而不是逐条政策的最终
人工分类标签。v0 可以作为稳健性或方法比较路径。

论文中可以这样表述：

> 为避免仅依赖标题和摘要造成政策工具漏检，本文进一步引入政策全文。
> 与标题-摘要版本相比，全文匹配显著提高了政策工具相关词项的召回率，
> 但也使部分宽泛词项覆盖率上升。因此，本文不将全文词典命中解释为
> 逐条政策的最终类别标签，而主要将其作为省份-年份层面政策工具倾向和
> 政策文本强度的可解释代理变量。

## 5. 政策工具词典与解释边界

当前词典围绕三类政策工具构造：

- `supply`: 资金、补贴、培训、服务平台、技术改造、人才、空间和要素
  支持等供给型工具；
- `demand`: 政府采购、展会、市场开拓、示范应用、应用场景、供需对接、
  出口和外部市场等需求型工具；
- `environment`: 融资、贷款、担保、知识产权、标准、认定评价、上市、
  营商环境和服务机制等环境型工具。

词典采用透明 substring matching，而不是分词模型或监督分类器。这样做的
优点是可审计、易复核、便于论文解释；限制是短词和宽泛词可能在全文中
具有较高覆盖率。

full-text 关键词质量检查显示：

- dictionary terms: 85;
- saturated terms, matching at least 80% of records: 2;
- high-coverage terms, matching at least 50% of records: 15;
- moderate-or-higher terms, matching at least 25% of records: 41;
- broad-intensity signal terms: 15.

类别层面，full-text 词典下 `supply` 与 `environment` 接近 any-tool 命中，
`demand` 也大幅上升。这说明在政策全文中，创新、平台、资金、服务、
融资、认定、标准、供需对接、场景和市场开拓等表达通常会共同出现。
因此，当前词典更适合用于：

1. 解释性描述；
2. 聚合强度代理；
3. 标注抽样和冲突诊断；
4. 后续 DeepSeek/MacBERT 标签体系的辅助规则。

它不应被包装为最终的人工政策工具分类器。

论文中可以这样表述：

> 本文首先构建透明的政策工具关键词词典，用于描述政策文本中供给、
> 需求和环境型工具的出现情况。由于政策全文中不同工具表述常共同出现，
> 且部分词项具有较宽语义，本文将词典结果定位为可解释的文本强度代理和
> 标注辅助规则，而非最终的排他式政策工具分类。

## 6. 描述性材料的论文用途

当前已经生成了两套描述性材料：title/abstract v0 和 full-text v1。
论文主轴建议使用 full-text v1 描述性输出，v0 作为补充说明或稳健性比较。

full-text descriptive notebook 为
`notebooks/44_manual_srdi_fulltext_descriptive_analysis.py`。它生成的材料包括：

- 年度 SRDI 政策数量趋势；
- 省份政策数量分布；
- full-text 工具类别命中比例；
- 省份-年份政策强度热力表；
- 省级工具结构；
- 中央 vs 地方政策特征对比；
- no-hit 记录说明；
- 高覆盖词项解释表。

这些材料在论文中的角色可以分为三层：

1. 数据覆盖说明：说明政策样本在年份和省份上的分布。
2. 政策活跃度描述：展示不同省份和年份的政策数量差异。
3. 政策工具结构描述：展示供给、需求、环境型工具倾向在时间和地区上的
   差异，但避免将其解释为最终分类结果。

可进入论文的图表包括：

- annual policy count trend;
- province policy count distribution;
- tool-category shares by year;
- province-year policy intensity heatmap;
- central-local comparison;
- high-coverage keyword table or appendix table.

## 7. 标注与模型路线

按照 `docs/label-intensity-construct-plan.md`，下一阶段的目标不是继续优化
关键词词典，而是引入 DeepSeek/MacBERT 多标签流程。

当前已经完成进入标注阶段前的数据准备：

- label docs:
  `data/processed/manual_policy_srdi_label_docs_v1.csv`, 4475 records;
- sampling frame:
  `data/processed/manual_policy_srdi_label_sampling_frame_v1.csv`, 4475 records;
- round-1 DeepSeek sample:
  `data/interim/manual_policy_srdi_deepseek_sample_round1_v1.csv`, 800 records;
- sample pools:
  `supply-like`, `demand-like`, `environment-like`, `other-like`, each 200 records.

DeepSeek round-1 labeling command is
`scripts/manual_srdi_deepseek_round1_label.py`. It is designed as an auditable
labeling step: prompts are generated from the prepared sample, raw API responses
are cached, parsed JSON labels are written separately, and a run quality report
records success, failure, and sample-pool counts.

在这一设计中，最终输出不再是互斥类别，而是四个概率：

- `p_supply`;
- `p_demand`;
- `p_environment`;
- `p_other`.

前三类允许同时为高概率；`other` 用于识别纯程序性文本、公示、名单、新闻、
政策解读、非实质政策工具文本或其他不适合进入政策工具分析的记录。

方法路线可以写为：

> 本文在词典诊断的基础上进一步构建多标签标注样本。首先利用关键词规则
> 形成供给型、需求型、环境型和其他类的分层候选池，并从四类候选池中
> 各抽取 200 篇政策形成 800 篇 round-1 标注样本。随后使用大语言模型
> 生成多标签银标，并以 MacBERT 训练政策文本多标签分类模型，最终对全量
> 政策输出供给、需求、环境和其他四类概率。

## 8. 与 DID 层的衔接

政策文本变量最终需要进入企业层面的 staggered DID 设计。当前可形成两类
省份-年份政策变量。

第一类是数量型政策强度：

- `srdi_policy_count`;
- `log_srdi_policy_count_plus1`;
- `total_keyword_count`;
- `unique_agency_count`.

第二类是文本工具结构变量，当前 full-text 词典版本可以先作为描述性和
稳健性变量，后续 DeepSeek/MacBERT 概率版本更适合作为主模型变量：

- supply policy intensity;
- demand policy intensity;
- environment policy intensity;
- other or low-substance share;
- average tool probability or category-specific policy share.

在 DID 模型中，这些变量可以作为省份-年份层面的调节变量或异质性分组变量。
例如，可以检验小巨人认定对企业创新的影响是否在政策强度更高、需求侧工具
更强或环境型支持更充分的省份-年份中更大。

论文中可以这样表述：

> 在因果识别部分，本文将省份-年份政策文本变量与企业面板匹配，用于检验
> 地方政策支持环境是否调节专精特新认定对企业创新的影响。基础政策强度由
> 政策数量衡量，政策工具结构由文本模型输出的供给、需求和环境型工具概率
> 聚合得到。

## 9. 可写入论文的方法结构

论文方法部分可以按以下顺序展开。

### 9.1 政策文本数据构建

说明数据来源、关键词收集原则、中央与地方来源、时间窗口、省份标准化、
新疆合并规则、中央政策处理规则，以及最终行级记录和省份-年份记录数。

### 9.2 政策强度变量

先给出政策数量强度变量，作为最透明的基础指标。说明为什么中央政策不进入
省份差异强度。

### 9.3 文本预处理与 full-text 选择

说明 v0 title/abstract 和 v1 full-text 比较，解释为什么主轴采用 full-text。
同时说明 full-text 可能带来高覆盖宽泛词，因此后续不把词典作为最终分类器。

### 9.4 词典诊断与规则抽样

说明词典从 53 项修订到 85 项、no-hit 抽检和修订效果。进一步说明词典现在
主要用于召回、抽样、诊断和解释。

### 9.5 多标签标注与模型预测

说明 DeepSeek round-1 样本、四类 pool、MacBERT 多标签模型和最终概率输出。
强调 supply/demand/environment 非互斥。

### 9.6 政策文本变量进入 DID

说明如何将行级政策概率聚合为省份-年份政策工具强度，并与企业面板合并。

## 10. 写作边界

当前已经可以稳定写入论文的内容：

- 手工政策数据来源和样本口径；
- 2020-2025 分析窗口；
- 4475 条行级政策记录；
- 31 个地方省份 x 6 年的平衡政策强度表；
- 新疆合并规则；
- 中央政策保留但不进入省份强度；
- full-text v1 作为主文本路径；
- 词典作为透明文本强度代理和标注辅助规则；
- round-1 标注样本已经构建完成。

当前写作中需要谨慎处理的内容：

- 不应声称词典命中就是最终人工分类；
- 不应把 supply、demand、environment 解释为互斥类别；
- 不应把 full-text 高频宽泛词解释为精确工具识别；
- 在 DeepSeek/MacBERT 完成前，不应声称已经得到最终
  `p_supply/p_demand/p_environment/p_other`;
- 在 DID panel 合并完成前，不应声称政策强度变量已经进入最终因果模型。
