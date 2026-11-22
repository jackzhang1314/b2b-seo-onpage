# 研究记录接口（由 Codex 生成）

用户提供链接/文件和任务即可，不填此结构。先按[研究流程](research-workflow.md)实际研究，再把 `research` 对象加到 `plan.json`，使用原来的 `onpage.py check-plan`。无需新增命令或联网 Python 依赖。

完整页 `focus.scope=full_page` 缺 `research` 会拒绝；声明使用客户行业词库时必须有可读原件。确实缺词库时可走有实际证据的独立研究路径。局部/旧接口兼容，但明确 `research_status=not_checked`，不能表示完整研究完成。研究字段可保留更多实际观察，脚本不限制额外属性。

## 最小字段

| 字段 | 要求 |
| --- | --- |
| target_url / keyword / market / language | 与 plan、页面证据完全一致 |
| evidence_class | observed 或 simulation；合成数据始终 simulation |
| sources | 实际本地证据登记，见下文；先从用户链接读取/下载后生成 |
| library | source_refs、source_kinds、coverage。声明竞品排名来源时记录 competitors 与 rank_cutoff=30 |
| keyword_decisions | 本页候选词取舍；有用户词库时先评估库内原词 |
| serp | query=主词、source、actual_market、actual_language、coverage、results；可加 samples/features/设备/日期 |
| competitor_coverage | coverage；可附选取范围、数量和理由 |
| competitor_pages | 每个实际阅读/尝试阅读的页面及具体对照 |
| brief | page_role 与 focus 同值、audience、intent、angle、modules |
| limitations | 已知研究限制的字符串数组；不要把“以后不保证排名”这类通用话当数据缺口 |

`coverage` 只接受 complete/partial/unknown/unavailable。完整性声明必须来自实际核验；来源表的文件存在和哈希只能固定证据，不能验证声明的真实性。

## 来源与引用

sources 每项含 `id`（唯一、不含 #）、`kind`（library/page_plan/keyword_group/serp/competitor/business/site/gsc）、`path`（绝对路径或相对 plan 的路径）、`source`（实际来源说明）和 `collected_at`（ISO 日期/时间）。页面规划和分组可来自同一 Excel，分别登记实际工作表及行引用。脚本读取来源文件并计算 SHA256，导出路径归一为绝对路径。

有本站查询导出时可用 `kind=gsc`。登记实际 `page_url`、`start_date`、`end_date`（YYYY-MM-DD）和 `filters`（如 US、Web、全部设备）。同一文件有多页时可指向同一文件的不同记录，引用写到所属行。若 Google 选定的规范页与当前编辑网址不同，`page_url` 保留报表中的原网址，`canonical_ref` 引用本任务中证明两者对应的 site 来源，例如 URL 检查结果。脚本核对所声明的地址、日期和来源类型。编辑者仍须核对原始导出的筛选及行内容。

引用写 `source-id#具体行/段/截图位置`；至少引用已登记来源。脚本核 source-id 存在和来源类型，**不自动验证行号/引文内容**；Codex 必须对照原文件。词库至少登记合并/归一化表与可追溯来源关系，不能只创建一个空壳“已完成研究”说明文件。

客户已整理的行业词库使用 `source_kinds=["customer_curated"]`，coverage 描述收到并读取的版本及范围。若有实际种子扩展或竞品排名原件，可追加 `seed_expansion` 或 `competitor_rankings`。只有竞品排名分支需要登记实际独立域名和自然排名上限 30，少于 20 家会记为研究缺口。清洗口径、原始行数、去重数和多条来源关系可作为附加字段保留。

独立研究将 library 填为 `{"coverage":"unavailable","unavailable_reason":"说明查找过的项目资料和实际缺项"}`。结合 site/business 资料，使用引用外部实访的 web 候选，或有本页查询证据且适合本页的 gsc 候选。后者在缺同行或 SERP 时仍可交有限改稿，在各自的 coverage 和 limitations 记录实际缺项。普通实测仍标 partial，模拟仍标 simulation。如确实读了用户词库但本品类零命中，保留 library 来源，写 `no_match_reason` 说明范围；不用构造库内关键词。

## 候选词、SERP 与页面对照

keyword_decisions 每项：

```json
{"keyword":"1 tonne mini excavator","origin":"library","decision":"include","reason":"示例：待实际验证与主词的产品实体、购买任务和SERP相容","module_ids":["selection"],"evidence_refs":["library-normalized#row=12","serp-primary#observation=2"]}
```

origin 可用 library、planning、web、editorial 或 gsc。词库及分组皆有的原词沿用 library，在 evidence_refs 同时引原词行、组成员行和规划页。仅见于规划或分组表的词使用 planning，引用 page_plan 或 keyword_group。可附实际 `keyword_id`、`planned_page_id`、`group_ids` 和 `group_labels`（实际组号、组名数组）及 `planned_role`（客户原角色）。分组及角色需要规划来源。`keyword-selection` 和 `keyword-placement` 阅读表均保留这些字段。原归属有冲突时保留各行引用，使用 review 说明冲突。

来自本站 GSC 的查询用 `origin=gsc`，引用对应的 gsc 来源，可在 `metrics.gsc` 保留实际点击和展现。decision 沿用 include/other_page/exclude/review，include 指向已有简报模块。每个规范词保留一条判断和所有适用来源。focus 的每个辅助词必须被研究 include，主词有冲突时保留原词并说明缺口。other_page 可附 target_url 或 target_page_role。metrics 可存实际 volume/KD/intent/CPC、数据库和日期，未知指标留空。

serp.results 每项含 `position`（实际自然位置 1–10，不能为布尔值）、`url`、`page_type`、`evidence_refs`（至少一个 serp 来源）。同位置不能重复；同 URL 多位置保留。搜索样本不知位置时放 `samples`，同字段但不填 position，不能猜序号。展示标题用 `title`，进入结果表；SERP 的 `features`、`format_assessment` 等附加观察原样保留在可复用 serp-brief.json，必须分清观察与推断；SERP 页面采集时间在来源登记中。广告/PAA 不计入自然前十。

competitor_pages 每项含 `url`、`read_state`（read/partial/failed）、`selection_reason`、`observed_strengths`、`page_gap`、`recommendation`、`evidence_refs`。跳转时 `requested_url` 记录SERP地址，`url` 记录实际最终地址，两者均导出；只有有实际读取依据的跳转才可关联。read/partial 必须引用 competitor 文件；failed 记录读取失败及未知，不猜优点。没有读过任何 SERP 代表页、读失败或覆盖有限会标 partial。通常读 3–5 个有代表性的页面；脚本不拿固定篇数代替研究判断。可附原始 Title/H 结构、模块、事实、业务依据、优先级等。

brief.modules 每项为 `id`、`heading`、`task`、`evidence_refs`。task 写清保留/新增/改进、模块回答的问题、必要事实及内链任务；angle 说明本页差异及依据。企业事实仍用 plan.claims / fact_gaps 管理，研究引用不会自动赋予公开使用许可。候选词通过 module_ids 连接到模块；正文改稿通过 keyword_placement 连接到实际表达。

为商业页选 B 端属性词时，按[品类选词流程](category-modifier-research.md)把实际查询短语记入上述 keyword_decisions。reason 写明买家任务、企业条件与本页去向，evidence_refs 指向本项目的词库、市场观察及业务依据。brief.angle 说明最终用词或保留原题的理由。仅在内置词表看到的写法属于 editorial 构想，后续查到的实际证据按来源登记。

产品＋属性词的 Google 查询应各自登记查询词、市场、日期、来源及发现的域名；在对应的 serp 类型来源文件保留这些分查询记录。主词的 serp.results 和 samples 仅收主词那次查询的结果。另一个查询命中的 URL 或站内导航找到的页面，均可按 competitor_pages 登记实访：selection_reason 中标明发现路径与页型，observed_strengths 记录真实 Title、属性所在位置与采购含义，recommendation 说明对同页型的借鉴。外站词频可按独立域名和已读页型说明，不用页面重复出现次数推断搜索量。

## 输出与状态

- `research.json`：原始研究判断及归一来源路径；`research-sources.json`：来源哈希与时间。
- `keyword-selection.csv/.xlsx`、`serp-results.csv/.xlsx`、`competitor-comparison.csv/.xlsx`：选词取舍、实际搜索结果和竞品对照。未定排名样本的位置保持空值。选词、SERP、竞品对照、改稿与关键词安排表逐行带 page_url、primary_keyword、target_market、content_language、research_evidence_class 和 research_status，单独转发表格也保留模拟与市场语境。
- `page-brief.md`：受众、意图、差异、模块任务、模块选词及缺口；`onpage-review.md` 链接到它。
- `run.json`：research_status、research_gaps 与源文件哈希。`documented` 表示必需记录/引用已登记且未声明覆盖缺口，不表示自动核实了 Top 20、前十真实性或研究质量。`partial` 明确缺口；`simulation` 始终标模拟，仍保留 research_gaps。

局部改稿完成、完整研究、可公开文案、已保存/已上线及效果分别验收。不得通过省略 focus 或改成 metadata 来掩盖本次实际是完整页任务。
