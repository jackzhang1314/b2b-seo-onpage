# 研究记录接口（由 Codex 生成）

用户提供链接/文件和任务即可，不填此结构。先按[研究流程](research-workflow.md)实际研究，再把 `research` 对象加到 `plan.json`，使用原来的 `onpage.py check-plan`。无需新增命令或联网 Python 依赖。

完整页 `focus.scope=full_page` 缺 `research` 会拒绝；声明使用客户行业词库时必须有可读原件。确实缺词库时可走有实际证据的独立研究路径。局部/旧接口兼容，但明确 `research_status=not_checked`，不能表示完整研究完成。研究字段可保留更多实际观察，脚本不限制额外属性。

## 最小字段

| 字段 | 要求 |
| --- | --- |
| target_url / keyword / market / language | 与 plan、页面证据完全一致 |
| evidence_class | observed 或 simulation；合成数据始终 simulation |
| sources | 实际本地证据登记，见下文；先从用户链接读取/下载后生成 |
| library | source_refs、source_kinds、coverage，记录竞品清单和导出范围。可给 expected_competitors、rank_cutoff、scope_note |
| keyword_decisions | 本页候选词取舍；有用户词库时先评估库内原词 |
| serp | coverage 和 queries 数组。旧版单查询也可直接读取 |
| competitor_coverage | coverage；可附选取范围、数量和理由 |
| competitor_pages | 每个实际阅读/尝试阅读的页面及具体对照 |
| brief | page_role 与 focus 同值、audience、intent、angle、modules |
| limitations | 已知研究限制的字符串数组；不要把“以后不保证排名”这类通用话当数据缺口 |

`coverage` 只接受 complete/partial/unknown/unavailable。完整性声明必须来自实际核验；来源表的文件存在和哈希只能固定证据，不能验证声明的真实性。

## 来源与引用

sources 每项含 `id`（唯一、不含 #）、`kind`（library/page_plan/keyword_group/serp/competitor/business/site/gsc）、`path`（绝对路径或相对 plan 的路径）、`source`（实际来源说明）和 `collected_at`（ISO 日期/时间）。页面规划和分组可来自同一 Excel，分别登记实际工作表及行引用。脚本读取来源文件并计算 SHA256，导出路径归一为绝对路径。

有本站查询导出时可用 `kind=gsc`。登记实际 `page_url`、`start_date`、`end_date`（YYYY-MM-DD）和 `filters`（如 US、Web、全部设备）。同一文件有多页时可指向同一文件的不同记录，引用写到所属行。若 Google 选定的规范页与当前编辑网址不同，`page_url` 保留报表中的原网址，`canonical_ref` 引用本任务中证明两者对应的 site 来源，例如 URL 检查结果。脚本核对所声明的地址、日期和来源类型。编辑者仍须核对原始导出的筛选及行内容。

引用写 `source-id#具体行/段/截图位置`；至少引用已登记来源。脚本核 source-id 存在和来源类型，**不自动验证行号/引文内容**；Codex 必须对照原文件。词库至少登记合并/归一化表与可追溯来源关系，不能只创建一个空壳“已完成研究”说明文件。

客户整理版可用 `customer_curated`，产品总词用 `product_terms`，工具拓展用 `seed_expansion`，竞品原始排名用 `competitor_rankings`。`competitors` 写实际收到的域名。有明确的客户清单可另给 `expected_competitors`，缺哪些就报哪些。`rank_cutoff` 仅在已知时填实际最后排名（正整数），全量或多来源区间可用 `scope_note` 写原始导出范围。按市场、日期和工具留原始记录。

独立研究将 library 填为 `{"coverage":"unavailable","unavailable_reason":"说明查找过的项目资料和实际缺项"}`。结合 site/business 资料，使用引用外部实访的 web 候选，或有本页查询证据且适合本页的 gsc 候选。后者在缺同行或 SERP 时仍可交有限改稿，在各自的 coverage 和 limitations 记录实际缺项。普通实测仍标 partial，模拟仍标 simulation。如确实读了用户词库但本品类零命中，保留 library 来源，写 `no_match_reason` 说明范围；不用构造库内关键词。

## 候选词、SERP 与页面对照

keyword_decisions 每项：

```json
{"keyword":"1 tonne mini excavator","origin":"library","decision":"include","reason":"示例：待实际验证与主词的产品实体、购买任务和SERP相容","module_ids":["selection"],"evidence_refs":["library-normalized#row=12","serp-primary#observation=2"]}
```

origin 可用 library、planning、web、editorial 或 gsc。词库及分组皆有的原词沿用 library，在 evidence_refs 同时引原词行、组成员行和规划页。仅见于规划或分组表的词使用 planning，引用 page_plan 或 keyword_group。可附实际 `keyword_id`、`planned_page_id`、`group_ids` 和 `group_labels`（实际组号、组名数组）及 `planned_role`（客户原角色）。分组及角色需要规划来源。`keyword-selection` 和 `keyword-placement` 阅读表均保留这些字段。原归属有冲突时保留各行引用，使用 review 说明冲突。

来自本站 GSC 的查询用 `origin=gsc`，引用对应的 gsc 来源，可在 `metrics.gsc` 保留实际点击和展现。decision 沿用 include/other_page/exclude/review，include 指向已有简报模块。每个规范词保留一条判断和所有适用来源。focus 的每个辅助词必须被研究 include，主词有冲突时保留原词并说明缺口。other_page 可附 target_url 或 target_page_role。metrics 可存实际 volume/KD/intent/CPC、数据库和日期，未知指标留空。

每次 B 端查询一条快照。新记录写 `serp={coverage, queries:[...]}`。每条含 `query, source, actual_market, actual_language, coverage, position_kind, results`，可加 `samples, collected_at`。`position_kind=google_organic` 用于可证实的 Google 自然名次，`provider_order` 表示搜索服务顺序，`unverified` 用于无名次样本。每条 results 记录 `position, url, title, page_type, evidence_refs`，原始位置可大于十，同一查询快照内须唯一。无可靠序号放入 samples 并省略 position。可用 `screening=skip, screening_reason=零售商` 记录筛除，其他值为 candidate/unreviewed。传统单查询结构仍可读。

例如 `phone case factory` 原始第 13 位命中首页时，结果行仍写该首页。另一个查询可以有自己的第 13 位。筛查深度和正式同行数分别说明。

新格式的 `competitor_pages` 只收已经核实资格的外贸 B2B 独立站页面。每项用 `company, site_type, business_evidence, page_type, discovery_source, discovery_url, url, read_state, selection_reason, observed_strengths, page_gap, recommendation, evidence_refs`。`site_type` 为 export_b2b_independent 或 mixed_b2b_page，后者仅指混营站的企业业务页。`discovery_source` 为 search、architecture 或 customer；search 的 discovery_url 必须来自实际搜索记录。`requested_url` 只在 HTTP 跳转有依据时填，`url` 是实际阅读地址。从搜索命中域名转到另一个域名时，用 `discovery_relation_ref` 引用可核实两者关系的同行来源。

read/partial 引用 competitor 原页资料。read 记录 `seo_title, h1, subtitle, subtitle_tag` 四个字符串及有序 `h2` 字符串数组。实读确无该项用“未见”，标题层级没有正文 H2 用空数组，记录实际用途。未读全用 partial/failed，说明哪些位置未核。多页属于同一企业时沿用同一个 company 名。旧版无资格记录的实访按 legacy_unclassified 保留。

brief.modules 每项为 `id`、`heading`、`task`、`evidence_refs`。task 写清保留/新增/改进、模块回答的问题、必要事实及内链任务；angle 说明本页差异及依据。企业事实仍用 plan.claims / fact_gaps 管理，研究引用不会自动赋予公开使用许可。候选词通过 module_ids 连接到模块；正文改稿通过 keyword_placement 连接到实际表达。

为商业页选 B 端属性词时，按[品类选词流程](category-modifier-research.md)把实际查询短语记入上述 keyword_decisions。reason 写明买家任务、企业条件与本页去向，evidence_refs 指向本项目的词库、市场观察及业务依据。brief.angle 说明最终用词或保留原题的理由。仅在内置词表看到的写法属于 editorial 构想，后续查到的实际证据按来源登记。

完整页交付时把 `architecture-page` 的清单交给 `check-plan --architecture-page`。`keyword_decisions` 对原分组以及新发现的每个候选给出去向。可给 `intent_group` 让同意图的多个词共用一个名称。调整原有归属须有 `ownership_override_ref` 引用经确认的 page_plan 或 keyword_group 来源。保留的词也需要实际文案落点。规划页尚无 URL 时用 `focus.planned_page_id` 绑定。已改址时同时用 `focus.page_url_mapping_ref` 引用 page_plan 中的新旧映射。已有主词发生变更时，以 `focus.primary_override_ref` 引用已确认的规划或分组决定。

## 输出与状态

- `research.json`：原始研究判断及归一来源路径；`research-sources.json`：来源哈希与时间。
- `keyword-selection.csv/.xlsx`、`serp-results.csv/.xlsx`、`competitor-comparison.csv/.xlsx`：选词取舍、实际搜索结果和竞品对照。未定排名样本的位置保持空值。选词、SERP、竞品对照、改稿与关键词安排表逐行带 page_url、primary_keyword、target_market、content_language、research_evidence_class 和 research_status，单独转发表格也保留模拟与市场语境。
- `page-brief.md`：受众、意图、差异、模块任务、模块选词及缺口；`onpage-review.md` 链接到它。
- `run.json` 记录来源、实际缺口、状态和本页的词库核对计数。`keyword-coverage.csv/.xlsx` 给出原行、实际表达、归属、位置及文案状态。`planned_with_text` 和 `added_with_text` 含待确认稿，`placed_planned_terms` 和 `added_placed_terms` 只数原页已有或可用文案。后者分为 `already_in_copy` 与 `new_copy_terms`。`draft_added_intents` 与 `added_intents` 分别按两种口径去重；缺少判断所需的意图归组时留空。`simulation` 表示模拟，`documented` 表示已登记和通过结构核对。

局部改稿完成、完整研究、可公开文案、已保存/已上线及效果分别验收。不得通过省略 focus 或改成 metadata 来掩盖本次实际是完整页任务。
