# 证据与改稿接口

仅 Python 3.11+ 标准库。学员用自然语言；输入、解析和 JSON 由 Codex 完成。工具只读本地证据，网络/登录/页面保存由环境内可用工具负责，无固定平台或 MCP 依赖。

WordPress 页面保存走[Harness 协作流程](wordpress-harness-handoff.md)。本文件的 `plan.json` 是 SEO 改稿协议，不是 Harness REST `content-plan` 的输入；先查实际记录/字段，由对应实施方生成该适配器的请求，再把真实 WordPress 改后输出交回这里核对。

## 1. 页面证据

保存实际 HTML（UTF-8）和取数说明；浏览器 DOM、源 HTML、第三方 tool_raw_html、用户供稿是不同阶段，不互相冒充。

```sh
python3 SKILL_DIR/scripts/onpage.py inspect --html /绝对路径/page.html --url https://example.com/product/ --keyword "selected product" --market US --language en --collected-at "2026-10-27T12:00:00+08:00" --stage supplied_html --capture /绝对路径/capture.json --out /绝对路径/新证据目录
```

只有正文用 `--text /绝对路径/page.md --stage supplied_text`。`--capture` 可选，内容如：

```json
{"requested_url":"https://example.com/old/","final_url":"https://example.com/product/","source":"browser","retrieved_at":"2026-10-27T12:00:00+08:00","limitations":["未取得跳转链 HTTP 状态"]}
```

`--url` 必须与 capture 的最终 URL 一致。stage 可选 `source_html/tool_raw_html/browser_dom/supplied_html/supplied_text`。脚本不自动取数、不伪造 HTTP 状态或采集日期。

流式/动态站点的源 HTML head 可能不等于浏览器 head。实际用浏览器读取 document.head 后，可加 `--rendered-head /绝对路径/browser-head.json`。该文件含 target_url、collected_at、source_ref，以及 head 对象（title/description/canonical/robots/language，各为字符串数组）。只提供实际观察过的字段；空数组表示已检查但未见，未检查的字段省略并沿用原文件观察。脚本保留 source_head、逐字段来源、浏览器观察和哈希；两份时间与覆盖差异需人工说明。

产出 `page-evidence.json`、`observations.csv`、`extracted-text.txt`、`run.json`，保留输入哈希。HTML 的 head、标题层级、链接、图片属性与 JSON-LD 原文分别保存；提取正文含导航及可能隐藏文本，不等于可见正文。H1 数量只是观察；canonical 缺失等是待核，不自动打分。

## 2. Codex 写改稿并校验

```sh
python3 SKILL_DIR/scripts/onpage.py check-plan --evidence /绝对路径/证据目录/page-evidence.json --plan /绝对路径/plan.json --out /绝对路径/新改稿目录
```

`plan.json` 的局部改稿最小例子（不是完整研究）：

```json
{
  "target_url":"https://example.com/product/","keyword":"selected product","market":"US","language":"en",
  "intent_fit":"fit","intent_reason":"页面对应已选型号，可补充询价资料",
  "serp":{"source":"manual_browser","actual_scope":"目标美国；当前只取得通用搜索样本，未核定美国排名","collected_at":"2026-10-27T12:00:00+08:00","coverage":"方向参考，非 Google 前十","results":[]},
  "claims":[{"claim_id":"capacity","text":"该型号容量 500ml","source_ref":"product-spec.pdf#page=2","verification_state":"user_provided","public_use_state":"approved_public"}],
  "changes":[{"change_id":"intro","field":"body","before":"","after":"A 500ml bottle. Confirm the selected closure and order quantity when requesting a quote.","reason":"把选型信息和询价动作放在一起","priority":"P1","copy_state":"ready","apply_state":"proposed","claim_ids":["capacity"],"evidence_refs":["product-spec.pdf#page=2"]}],
  "fact_gaps":["当前交期未确认"]
}
```

上下文必须与证据相同。`intent_fit`：fit/mixed/mismatch/unknown。局部/旧接口的 `serp` 可省略，此时明确未校验完整研究链。`focus.scope=full_page` 必须提供 `research`，其中必须有已读取的行业词库文件；详见[研究接口](research-contract.md)。研究中的 SERP 作为整页报告来源；局部旧接口 results 每项有 url/page_type/evidence_ref，排名仅实际取得时记录，空结果配真实限制。

change field：title/description/h1/h2/h3/h4/h5/h6/body/link/image_alt/schema/other。priority：P1/P2/P3。copy_state：ready/blocked。导出只接受 proposed；不能把校验成功设为已改站。

title/description 的 before 与 head 证据匹配。H1–H6 要有 HTML 证据，before 按标签及原文定位；同文同级出现多次时必须给 `heading_index`（全部标题按序，从1开始），并核对原文和级别。可用 `after_tag` 调整级别；新增同级标题需要 `placement` 说明插入位置。正文替换的 before 要能在提取文本定位。link/image_alt/schema/other 仍由 Codex 核具体位置，脚本不做完整 DOM 校验。

只有正文/Markdown可写候选标签与标题大纲，但不能捏造 HTML 标签现状来通过校验；用可读稿件交付，并标明待真实页面回读。

claim verification_state：page_observed/user_provided/verified/unverified/contradicted。public_use_state：public_observed/approved_public/internal_only/pending。ready 引用未经确认、矛盾或内部主张会失败。**未登记的虚构主张不能被脚本穷尽检测**，Codex 仍需逐句审阅，数字/认证/承诺尤其要登记。

产出 onpage-review.md、page-changes.csv、claims.json、plan.json 和 run.json；有实际 SERP 才输出 serp-brief.json。修改后重新保存证据并检查实际改动；实现回执另记 before/after 哈希、授权范围、实际修改位置、预览/线上核验，不能用 proposal 文件充当发布凭证。

## 3. 页面目标与关键词安排

完整优化在原 plan 中增加以下字段，**并附研究接口定义的 `research`**；下面仅展示 focus/placement 部分。用户不用填写。`primary_keyword` 必须与已选 `keyword` 一致，辅助词不与主词重复。局部任务按实际 scope 使用；保留段落可引用原证据，不必制造改动。

```json
{
  "focus": {
    "primary_keyword": "mini excavators",
    "secondary_keywords": ["mini diggers"],
    "page_role": "category",
    "buyer_task": "Compare available machines and request specifications",
    "scope": "full_page",
    "selection_ref": "user-selected-keyword",
    "architecture_ref": "planning/pages.csv#P01",
    "preserve": ["Actual model identity and the confirmed category scope"]
  },
  "keyword_placement": [
    {"keyword":"mini excavators","role":"primary","location":"title","expression":"Mini Excavators","change_id":"title","reason":"Identify the selected product family"},
    {"keyword":"mini diggers","role":"secondary","location":"not_used","reason":"No suitable passage in this edit"}
  ]
}
```

`scope`：metadata/headings/section/full_page。可选 `architecture_ref`、`selection_ref` 只填写真实来源。`keyword_placement` 的 location 为 title/description/h1–h6/intro/body/link/image_alt/not_used。已修改位置给 `change_id`，表达必须实际出现在该条改稿中，位置与改稿字段对应；正文开头 intro 对应 body，位置仍需人工回读。

保留现有表达时给 `source_ref`（不再给 change_id），脚本核它在该类型的已保存证据中出现；引用真实性和实际视觉位置由 Codex 核实。`not_used` 只写原因，不给 expression/change_id/source_ref。允许自然近义词作为 expression，不要求精确重复 keyword，也不计算密度分数。完整页必须说明主词和每一个已选辅助词的位置或本次不用的理由；只在研究表里选中、没有安排到正文也没有解释不用的词会被拒绝。

输出增加 `page-focus.json`、`keyword-placement.csv/.xlsx`。标题更改的 `field` 是旧标签，`after_tag` 是改后标签。例如将第二个实际标题从 H2 改 H3：

```json
{"change_id":"spec-heading","field":"h2","heading_index":2,"before":"Specifications","after":"Dimensions and Access","after_tag":"h3","placement":"型号参数模块","reason":"本段是选型章节的子问题","priority":"P2","copy_state":"ready","claim_ids":[],"evidence_refs":["page-evidence.json#headings/1"]}
```

不需要修改时允许 `changes: []`、`review_outcome: "retain"`、非空 `retention_reason`；交保留理由和观察范围。不能同时声明 retain 又给修改。其余上下文/意图字段照常核验；空改动表不是已改站。

## 4. 改后快照比较

先用 inspect 保存本次真实取得的改后快照，再执行：

```sh
python3 SKILL_DIR/scripts/onpage.py compare --plan /绝对路径/已校验计划/plan.json --after /绝对路径/改后证据/page-evidence.json --out /绝对路径/新回读目录
```

输入上下文（URL、主词、市场、语言）必须一致；最终地址变化先核用途，再按真实目标重建证据，不能修改字段绕过不匹配。输出 `implementation-review.md` 和 `implementation-observations.csv/.xlsx`，记录 Title/描述/H标题的文字匹配及正文片段出现。图片、链接、schema 等仍要求实际元素核查。

`observed_in_snapshot` 只说明给定快照出现了文字，`not_observed_in_snapshot` 只说明该快照未见；渲染可见性、正确段落、重复元素、发布时间、Google采用与效果不由比较器证明。原 plan 的 apply_state 继续 proposed，实际实施证据在项目记录保存，不能让本地文件比较变成发布回执。

内部模拟的本地回读可增加 `--local-simulation`，仅接受 `research.evidence_class=simulation` 及 `supplied_html/supplied_text` 快照。此时可观察 blocked 文案，但输出保留原 copy_state，不能改变 internal_only 或公开使用许可；run.json 明示 local_simulation、deployment_verified=false。默认 compare 继续跳过 blocked。图片/链接仍需按实际元素另行核查。
