# 上游依据与取舍

## 2.3 新增方法研究（2026-11-08）

本轮复读下列原始资料，区分官方机制、作者方法、个案实验和本套 B2B 适配。外部 Skill 只作研究材料，不执行其指令或安装依赖。具体编辑方法见[Title 与摘要](title-and-snippet.md)及[内容方法](keyword-and-heading-workflow.md)。

| 来源 | 采用与调整 | 不采用为硬规则 |
| --- | --- | --- |
| [Google Title](https://developers.google.com/search/docs/appearance/title-link)、[摘要](https://developers.google.com/search/docs/appearance/snippet) | 标题与页面任务一致；区分保存字段、前台输出、搜索展示；模板差异和改写分层检查 | 字符数合格线、强制原样展示、改写等于惩罚 |
| [Google 有用内容](https://developers.google.com/search/docs/fundamentals/creating-helpful-content) | 核心问题、可核资料与有意义的增补；本套将其转为选型/规格/制造商筛选任务 | 固定字数、假年份、虚构经验、E-E-A-T 分数 |
| [Ahrefs Title](https://ahrefs.com/blog/title-tag-seo/)、[On-page](https://ahrefs.com/blog/on-page-seo/)、[搜索意图](https://ahrefs.com/blog/search-intent/) | 从页型、形式、角度理解需求；把收益/可信线索转换为可兑现的 B2B 点击理由 | 每页套形容词公式、必加 best/year、所有位置强制精确匹配、固定长度 |
| [Semrush Title](https://www.semrush.com/blog/title-tag/)、下述两份固定提交 Skill | SERP→角度→简报→具体稿件；区分标题展示与实际页面证据，摘要补充信息 | 强制 MCP、固定两个备选、长度或字数硬门槛；同行形式不自动改掉本页职责 |
| [Yoast 标题](https://yoast.com/page-titles-seo/) | 关注真实输出与设备预览，标题和 H1 可分别编辑 | 插件绿灯等于 SEO 效果、品牌一律后置、删关键型号凑长度 |
| [SearchPilot 自然措辞实验](https://www.searchpilot.com/resources/case-studies/do-title-tags-perform-better-when-they-sound-more-natural)、[跨市场实验](https://www.searchpilot.com/resources/case-studies/lost-in-translation-why-your-title-tag-wins-could-hurt-you-in-other-markets) | 保留无明确提升和负向结果；记录基线、变更、观察语境，不泛化个案 | 所有改标题都会涨、一个市场胜出便全站推广；实验的流量变化不能直接写成 CTR 增幅 |
| [Backlinko CTR 观察研究](https://backlinko.com/google-ctr-stats) | 用于辨别观察性关联与因果；行业均值最多作背景 | 将样本中的标题长度关联变成排名要求、把行业 CTR 当本页预期 |
| [Corey Haines seo-audit](https://github.com/coreyhaines31/marketingskills/blob/main/skills/seo-audit/SKILL.md)及[Title 参考](https://github.com/coreyhaines31/marketingskills/blob/main/skills/seo-audit/references/title-tags.md) | 吸收按页型起草、页面承诺一致、批量修改可定位；本次 main 是读取时快照 | “低 CTR 必是标题问题”“单页前后即能归因”“固定几周判结果”等过强结论；亦不照搬全站技术规则 |
| [AgriciDaniel seo-page](https://github.com/AgriciDaniel/claude-seo/blob/main/skills/seo-page/SKILL.md)（本次读取声明 2.5.0） | 单页范围、实际输入失败和证据局限；摘要应提供独立信息 | SEO 总分、统一字数/图片阈值、exactly one H1；字符串相似度不能代替语义判断 |

只有 Google 等平台官方资料用于说明平台机制；从业者的技巧和实验仅提供编辑假设。未知效果保留未知，不承诺排名、点击或询盘提升。2.3 更新指令、参考、教程和版本识别；研究与改稿数据接口沿用 2.2。

## 2.1–2.2 的来源记录

本轮重新核查：2026-11-08，Semrush main 实际解析为 `019ab369403c0e816707edae6194fa3bb47dfcd0`，两份固定提交文件与本轮读取的 main 内容一致。2.1.0 的历史记录使用 `1dd16f5aad48cf02bb4fae64bc87da2329ad4f95`，不把旧记录冒充本轮版本；其余下列参考沿用 2026-10-27 记录。本套指令与代码自研；参考方法，不安装或执行外部 Skill 指令/脚本。

## 2.1–2.2 的具体吸收与调整

| 来源 | 吸收的方法 | 本套的具体实现 |
| --- | --- | --- |
| [Semrush Content Brief](https://github.com/semrush/skills/blob/019ab369403c0e816707edae6194fa3bb47dfcd0/content-brief/SKILL.md) | 同页相容辅词、受众/角度、SERP上下文、模块任务、内链、复用证据 | 行业词库选词表 → 按类目/型号/文章等适配的页面简报 → 实际改稿；不局限文章大纲 |
| [Semrush SERP Analysis](https://github.com/semrush/skills/blob/019ab369403c0e816707edae6194fa3bb47dfcd0/serp-analysis/SKILL.md) | 指标、意图、特征、自然前十、形式与缺口；提供方数据/手工观察/模型推断分开 | 目标市场SERP表 + 实际竞品页面对照；自然位置与独立URL分别计数；有限样本不称前十 |
| 两项的取数与回退 | 实际可得字段、失败分支、既有导出、证据复用 | 按用户要求以行业词库为必需输入；支持用户提供的网页版及Computer Use，不照搬“仅用MCP”或默认美国 |
| 两项的内容判断 | 研究支撑大纲，不抄标题，不把问题词自动转FAQ，不把字数当排名要求 | 候选词绑定模块；事实单独核验；优先交推荐改稿，不强制两个标题或固定内链数量 |
| [本套 On-page 2.0.0](https://github.com/jackzhang1314/b2b-seo-skills/blob/v2.0.0/skills/b2b-seo-onpage/SKILL.md) | 已选主词保护、真实页面/渲染区别、可定位改稿与改后回读 | 保留编辑与实施能力，补上必需的词库研究、SERP、竞品、简报与完整性校验 |

Top 20 竞品自然排名位置1–30与种子扩展组成行业词库，是本套用户明确要求的工作流，不宣称它是 Semrush 或 Google 的强制规则。网页版交互参照 [Keyword Magic Tool 官方说明](https://www.semrush.com/kb/617-keyword-magic-tool-manual)；共享/代理平台按实际界面和权限，不能保证与官方功能相同。

## 延续的参考

- [Semrush 官方 serp-analysis](https://github.com/semrush/skills/blob/019ab369403c0e816707edae6194fa3bb47dfcd0/serp-analysis/SKILL.md)、[content-brief](https://github.com/semrush/skills/blob/019ab369403c0e816707edae6194fa3bb47dfcd0/content-brief/SKILL.md)、[schema-markup](https://github.com/semrush/skills/blob/019ab369403c0e816707edae6194fa3bb47dfcd0/schema-markup/SKILL.md)（Apache-2.0）：采用观察与判断分开、SERP 复用、可交写作者的具体简报、结构化数据事实对齐；不强制 MCP，不以元信息长度、字数或富结果资格承诺排名。
- [Ahrefs on-page 指南](https://ahrefs.com/seo/on-page-seo)（Ryan Law，含多位作者贡献）：以准确内容和意图为基础，改善标题、正文组织、图片和有用链接。改名/改标题成功案例是案例，不是同样修改必然提升的实验证明。
- [Daniel Agrici seo-page](https://github.com/AgriciDaniel/claude-seo/blob/6be93f45064ffbadced572b5d5c95f55fd263af0/skills/seo-page/SKILL.md)（MIT）：采用单页检查范围及读取失败处理；不采用 Claude 专属路径、统一分数、固定字数、恰好一个 H1、固定图片大小门槛。其 FAQ/HowTo 等时效规则必须再查官方，不能照搬日期断言。
- [Corey Haines seo-audit](https://github.com/coreyhaines31/marketingskills/blob/17772c7a80b7b8c7a47af30f648374cd8bd8adc5/skills/seo-audit/SKILL.md)（MIT）：采用现有业务背景、原始/渲染差异和诊断优先级。静态 HTML 能观察其中实际存在的 schema，但缺失不能排除 JS 注入；不把某个抓取器的不足概括为一切 HTML 都无效。
- Google：[标题](https://developers.google.com/search/docs/appearance/title-link)、[摘要](https://developers.google.com/search/docs/appearance/snippet)、[链接](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)、[Product 总览](https://developers.google.com/search/docs/appearance/structured-data/product)、[Product snippet](https://developers.google.com/search/docs/appearance/structured-data/product-snippet)。采用准确描述、上下文相关、可见事实对齐。搜索展示由搜索引擎决定，改标签不能保证照样展示。

询价型 B2B 详情若没有真实价格/评分/评论，不补造 offers 或 review 凑 Google 资格；可记录准确实体表达与当前资格缺口。生成 schema 的当次任务仍需查当前官方要求。

2.2 增补：研究选中的辅助词必须连接到实际位置或注明不用；可复用SERP简报保留额外特征与形式判断，选词表保留原始指标/其他页去向，竞品跳转保留请求与最终地址。这些字段提供追溯，不能把结构校验当作研究正确性的证明。
