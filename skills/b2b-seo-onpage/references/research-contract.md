# 研究记录接口（由 Codex 生成）

用户提供链接/文件和任务即可，不填此结构。先按[研究流程](research-workflow.md)实际研究，再把 `research` 对象加到 `plan.json`，使用原来的 `onpage.py check-plan`。无需新增命令或联网 Python 依赖。

完整页 `focus.scope=full_page` 缺 `research` 会拒绝；研究里缺可读取的行业词库文件也会拒绝。局部/旧接口兼容，但明确 `research_status=not_checked`，不能表示完整研究完成。研究字段可保留更多实际观察，脚本不限制额外属性。

## 最小字段

| 字段 | 要求 |
| --- | --- |
| target_url / keyword / market / language | 与 plan、页面证据完全一致 |
| evidence_class | observed 或 simulation；合成数据始终 simulation |
| sources | 实际本地证据登记，见下文；先从用户链接读取/下载后生成 |
| library | source_refs、source_kinds、competitors、rank_cutoff=30、coverage |
| keyword_decisions | 本页候选词取舍，至少含行业词库候选 |
| serp | query=主词、source、actual_market、actual_language、coverage、results；可加 samples/features/设备/日期 |
| competitor_coverage | coverage；可附选取范围、数量和理由 |
| competitor_pages | 每个实际阅读/尝试阅读的页面及具体对照 |
| brief | page_role 与 focus 同值、audience、intent、angle、modules |
| limitations | 已知研究限制的字符串数组；不要把“以后不保证排名”这类通用话当数据缺口 |

`coverage` 只接受 complete/partial/unknown/unavailable。完整性声明必须来自实际核验；来源表的文件存在和哈希只能固定证据，不能验证声明的真实性。

## 来源与引用

sources 每项含 `id`（唯一、不含 #）、`kind`（library/serp/competitor/business/site）、`path`（绝对路径或相对 plan 的路径）、`source`（实际来源说明，不含凭据）、`collected_at`（ISO 日期/时间）。脚本读文件、拒绝空文件并计算 SHA256。导出中的来源路径归一为绝对路径，便于继续检查。

引用写 `source-id#具体行/段/截图位置`；至少引用已登记来源。脚本核 source-id 存在和来源类型，**不自动验证行号/引文内容**；Codex 必须对照原文件。词库至少登记合并/归一化表与可追溯来源关系，不能只创建一个空壳“已完成研究”说明文件。

library.source_kinds 是 seed_expansion 与 competitor_rankings 的实际来源集合；competitors 是实际覆盖的独立竞品域名。少于 20 家、缺一种来源或 coverage 非 complete 会标 partial。多个文件不等于多个竞品。rank_cutoff 是自然排名上限，不是关键词条数。清洗规则、原始行数、去重数量、关系表位置和未知来源可作为附加字段保留。

## 候选词、SERP 与页面对照

keyword_decisions 每项：

```json
{"keyword":"1 tonne mini excavator","origin":"library","decision":"include","reason":"示例：待实际验证与主词的产品实体、购买任务和SERP相容","module_ids":["selection"],"evidence_refs":["library-normalized#row=12","serp-primary#observation=2"]}
```

origin：library/web/editorial。decision：include/other_page/exclude/review。include 必须指向已存在 brief 模块；其他决定不能写本页 module_ids。一个规范词一条决定，多来源放在 evidence_refs，原始竞品/URL 关系仍保留在词库证据。focus 的每个辅助词必须被研究 include；主词有冲突时保持原词、标缺口。`other_page` 可附 `target_url` / `target_page_role`，导出到阅读表，不自动创建或改站。可用 `metrics` 对象保留实际 volume/KD/intent/CPC、数据库、时间和来源引用；未知指标留空，脚本只转存，不验证指标真实性或把不同观察相加。

serp.results 每项含 `position`（实际自然位置 1–10，不能为布尔值）、`url`、`page_type`、`evidence_refs`（至少一个 serp 来源）。同位置不能重复；同 URL 多位置保留。搜索样本不知位置时放 `samples`，同字段但不填 position，不能猜序号。展示标题用 `title`，进入结果表；SERP 的 `features`、`format_assessment` 等附加观察原样保留在可复用 serp-brief.json，必须分清观察与推断；SERP 页面采集时间在来源登记中。广告/PAA 不计入自然前十。

competitor_pages 每项含 `url`、`read_state`（read/partial/failed）、`selection_reason`、`observed_strengths`、`page_gap`、`recommendation`、`evidence_refs`。跳转时 `requested_url` 记录SERP地址，`url` 记录实际最终地址，两者均导出；只有有实际读取依据的跳转才可关联。read/partial 必须引用 competitor 文件；failed 记录读取失败及未知，不猜优点。没有读过任何 SERP 代表页、读失败或覆盖有限会标 partial。通常读 3–5 个有代表性的页面；脚本不拿固定篇数代替研究判断。可附原始 Title/H 结构、模块、事实、业务依据、优先级等。

brief.modules 每项为 `id`、`heading`、`task`、`evidence_refs`。task 写清保留/新增/改进、模块回答的问题、必要事实及内链任务；angle 说明本页差异及依据。企业事实仍用 plan.claims / fact_gaps 管理，研究引用不会自动赋予公开使用许可。候选词通过 module_ids 连接到模块；正文改稿通过 keyword_placement 连接到实际表达。

## 输出与状态

- `research.json`：原始研究判断及归一来源路径；`research-sources.json`：来源哈希与时间。
- `keyword-selection.csv/.xlsx`、`serp-results.csv/.xlsx`、`competitor-comparison.csv/.xlsx`：选词取舍、实际搜索结果和竞品对照。未定排名样本的位置保持空值。选词、SERP、竞品对照、改稿与关键词安排表逐行带 page_url、primary_keyword、target_market、content_language、research_evidence_class 和 research_status，单独转发表格也保留模拟与市场语境。
- `page-brief.md`：受众、意图、差异、模块任务、模块选词及缺口；`onpage-review.md` 链接到它。
- `run.json`：research_status、research_gaps 与源文件哈希。`documented` 表示必需记录/引用已登记且未声明覆盖缺口，不表示自动核实了 Top 20、前十真实性或研究质量。`partial` 明确缺口；`simulation` 始终标模拟，仍保留 research_gaps。

局部改稿完成、完整研究、可公开文案、已保存/已上线及效果分别验收。不得通过省略 focus 或改成 metadata 来掩盖本次实际是完整页任务。
