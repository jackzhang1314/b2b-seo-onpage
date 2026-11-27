# B2B On-page SEO Skill

**把架构工作台里规划好的每一页，做成能接企业订单的实际页面。** 指定整站或一个 URL，Codex 复用架构 Skill 清洗过的词库、页面分组、竞品具体 URL 的排名明细和页面模块。整站任务还可对照 WordPress 的公开页面清单，找出已上线、尚无规划行的页面。它检查哪些词漏了、哪些旧文要重写，再把关键词落实到标题、首屏与各小节。对已获准维护的 WordPress 站点，可在同一任务里更新正式站并回读。

## 两种上课可直接用的调用

```text
使用 $b2b-seo-onpage，按这个网站已采用的架构工作台优化整站。用 WordPress Builder Harness 更新已上线页面，并逐页回读。
```

```text
使用 $b2b-seo-onpage，结合这个项目的工作台，只优化【页面 URL】。用 WordPress Builder Harness 保存并回读这页。
```

首页、产品集合页和详情页的 SEO Title 和主 H1 **每处都要有本页品类和至少一个合适的 B 端属性词**。已有主词继续沿用。比如工厂能定制玻璃瓶，可选 `custom glass bottle manufacturer`；仅做批发，就用真实的 `wholesale` 或 `supplier`。Semrush / Ahrefs 查不到组合量时，仍可按真实交易方式研究和采用，搜索量留空。详情页还会保留型号。完整改稿的覆盖表可直接翻到「SEO Title 与主 H1」查看两处实际文案和企业依据。可以直接要求“只交稿”，也可以指定已经新增、尚未进入工作台的 URL。[整站、单页和双标题示例](skills/b2b-seo-onpage/references/commercial-page-workflow.md)

v2.9.0 从客户确认的页面规划和分组取全本页成员，再按合格外贸 B2B 同行的具体 URL 反查排名词，补查产品加采购属性的搜索表达。整页交付给出 SEO Title、H1、可见副标题、H2 和各小节的正文。打开最终稿与覆盖表，就能从一个采购词找到实际回答它的那句话。[上游规划与客户词库](skills/b2b-seo-onpage/references/architecture-to-page.md)

已有页面还可以附上该 URL 的 Google Search Console 查询导出，保留确实带来相关展现或点击的买家用语。新页从已有架构、词库和产品资料开始。[关键词布局方法与示例](skills/b2b-seo-onpage/references/query-placement.md)

v2.10.0 支持从客户网站根目录 AGENTS.md 找回已有行业词库、竞品 Top Pages、逐词排名与架构工作台。在该项目打开新会话，告诉 Codex 页号或 URL 即可。[项目入口与单页读取](skills/b2b-seo-onpage/references/architecture-to-page.md)

## 安装 v2.11.0

把下面这段发给 Codex 即可安装固定版本。

```text
请使用 $skill-installer 从这个固定版本安装 B2B On-page SEO Skill。
https://github.com/jackzhang1314/b2b-seo-onpage/tree/v2.11.0/skills/b2b-seo-onpage
已有相同版本且内容一致就复用。升级时先备份同名旧版和本地定制，保留较新版本。
安装后核对 Skill 版本和文件完整性，并告诉我怎么开始。
```

离线安装可下载 ZIP，将解压目录交给 Codex，要求它按包内的 `RELEASE.json` 核对完整性，安装整个 `skills/b2b-seo-onpage` 目录。[下载 v2.11.0 ZIP](https://github.com/jackzhang1314/b2b-seo-onpage/releases/download/v2.11.0/b2b-seo-onpage-2.11.0.zip) · [下载 SHA-256 校验文件](https://github.com/jackzhang1314/b2b-seo-onpage/releases/download/v2.11.0/b2b-seo-onpage-2.11.0.zip.sha256)

也可以使用本机 `skill-installer` 的命令行脚本，将下面的脚本路径换成本机实际路径。

```sh
python3 /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo jackzhang1314/b2b-seo-onpage --ref v2.11.0 --path skills/b2b-seo-onpage
```

宿主刷新技能列表后即可使用，必要时打开新会话。处理脚本使用 Python 3.11+ 标准库。关键词工具账号和站点权限沿用你的环境，实际修改 WordPress 时再接入该站已有的 Build Harness。

## 第一次使用，提供什么

**已有架构工作台时，给网站项目或包含配套表格的工作台目录即可。** 想改哪一页就给 URL，想做全站就说整站优化。只有原始资料时，也可直接给页面规划、分组和行业词库。 三份资料可以分布在多个 Excel、CSV、在线表格，或同一工作簿的几个标签页。尚未上线的页面可给规划 URL 或编号。只有关键词和页面稿时，也可以先做这页。

以下资料有助于确定市场、采购词和可发布的企业事实。已有的直接复用。

- **行业词库**提供完整采购短语、关键词编号及已有来源。客户整理好的版本可以直接给，保留原表头。
- **网站页面规划**提供页面编号、规划 URL、上级、页面职责及已定主词。
- **关键词分组规划表**提供已分配的词组、成员词、角色和目标页。有些表用页面编号关联，有些用组号或 URL，Codex 会按实际列对照。
- **目标国家和内容语言**，例如美国、英文。
- **真实业务资料**：企业角色、产品/型号范围、规格、可公开的能力与采购条件；已有架构或页面简报一并复用。
- **补查工具入口（可选）**：已有网页版关键词工具，或已导出的研究数据。

可以直接提供含关键词和排名 URL 的竞品导出，以及 Semrush、Ahrefs 扩展词。保留各自国家库、日期和原始范围。几千到几万行都按页筛选，同一词在多家同行出现时保留多条来源。

## 可直接复制的调用

```text
使用 $b2b-seo-onpage。
目标页是【页面编号或 URL】，目标市场和语言是【美国、英文】。
行业词库在【文件】，网站页面规划在【文件】，关键词分组表在【文件或工作表】。
企业及产品资料在【目录】。

先找出已经分给这页的主词、词组和全部成员，再回查行业词库里的完整采购短语。
用“本页产品＋B 端属性词”找做相同业务的外贸 B2B 独立站。用同行实际集合页或详情页 URL 回查排名表，
把新找到的词和原组一起安排进 SEO Title、H1、Subtitle、H2 及相应正文。标明哪些沿用规划，
哪些建议补充，哪些应留给其他页面。这次只交改稿。
```

例如，软壳夹克类目可以同时接“软壳夹克”和“绣标选项”两组。若“怎样测量工装尺码”已经分给指南页，类目可保留尺码表并链接指南，测量教程仍由指南页承接。

只改标题时，可以直接说：

```text
使用 $b2b-seo-onpage。
页面：【URL或稿件】；已选主词：【关键词】。
行业词库：【文件或目录】。市场和语言：【例如美国、英文】。
从词库的完整查询里看买家想下什么订单，再去 Google 找同市场、同页型的同行页面。
对照本站上级和同级页，结合我们确实能接的订单，只给这页一个推荐 Title 和一句理由。
```

已有架构时，给架构输出目录、index.html 或 Markdown 简报即可。Codex 会复用这页的主词、章节词、筛选词、模板模块及资料缺口。有词库先查词库，没有架构就独立研究本页；缺少客户词库时仍可依据实页和业务资料给出改稿，注明研究覆盖。

## 怎样选同行、查漏词

例如搜 `phone case factory`，靠前的结果可能是品牌名带 Factory 的零售店。跳过这些结果，向后查或换搜 `private label phone case manufacturer`，直到找到经营同类业务、能核实海外企业供货的独立站。搜索命中工厂首页时，再去它真正的手机壳批发集合页读 Title、H1、副标题和正文 H2，用集合页自己的 URL 回查排名表。

打开 `page-copy.md` 看按阅读顺序排好的页面稿。再在 `keyword-coverage.xlsx` 搜任意一个词，就能看到它来自客户原分配、总库及排名补查，还是独立研究，以及实际模块、最终原句、回答和可用状态。上游有模块与字段表时，同一工作簿另有一张“上游模块与字段”表，逐项列出落点和缺口。[同行筛选方法](skills/b2b-seo-onpage/references/category-modifier-research.md)

以 `private label phone case manufacturer` 为例，首屏“我们为品牌生产手机壳”回答谁生产，包装小节“壳体可以印你的标志，包装可以用你的品牌”回答贴牌怎样交付。两个必需条件都找到对应原句后，才按各段实际公开状态计入可用或待确认稿。被替换的旧 H1、材料小节里的印标词，以及只有小标题的需求，都能在校验或覆盖状态中识别。[记录格式与示例](skills/b2b-seo-onpage/references/research-contract.md)

## 给已有页面布局关键词

可以直接说：“用 `$b2b-seo-onpage` 优化【页面】。词库和公司资料在【目录】。先给一个标题，告诉我为什么用它。再把买家看到标题后最关心的问题写成 H2 和可直接替换的正文。已有架构和写得准确的段落请沿用。” [架构交接](skills/b2b-seo-onpage/references/architecture-to-page.md) · [按页型拟标题](skills/b2b-seo-onpage/references/title-and-snippet.md)

以工装为例，`custom workwear manufacturer` 关心谁能定制生产，`factory direct workwear` 关心能否向生产方直接下单，`wholesale blank workwear` 关心能否按批发条件买到未加标的服装。先保留整条查询和可得的排名 URL，再判断哪些条件能在同一张订单上成立。[采购短语与订单示例](skills/b2b-seo-onpage/references/category-modifier-research.md)

假设软壳夹克与保暖夹克各有一个类目，企业资料确认所有软壳款可在左胸或袖部绣标，报价需图稿、位置和分尺码数量。软壳页可以这样交稿。

| 位置 | 示例改稿 |
| --- | --- |
| SEO Title | Custom Softshell Work Jackets with Embroidered Logos |
| 选词理由 | “Softshell” 让买家认出系列，“Embroidered Logos” 说明整个系列可以怎样定制。 |
| H1 | Custom Softshell Work Jackets |
| H2 | Where Can We Embroider Your Logo? |
| 紧接 H2 的正文 | Choose the left chest or sleeve for your embroidered logo. To request a quote, send your logo file, preferred placement and the quantity you need in each size. |

如果只有 SJ-08 可绣标，就把刺绣说明放在该型号旁，类目的标题只承诺整个系列共有的条件。原有尺码表可以直接保留。

## 配合 WordPress Build Harness 使用

On-page负责判断“应该怎样改、为什么”；Harness负责找到该站真实的编辑位置、实施与验收。Codex在同一个任务里衔接，你不需要手动在几个Skill之间搬运文案。

- `wordpress-builder` 从该站项目入口确认页面、当前环境和修改范围。
- `wordpress-content` 修改已有正文、ACF及实际单页SEO值；遇到模板、H标签结构或新字段问题才转 `wordpress-design`。
- `wordpress-delivery` 核对目标站保存结果、后台重开和实际页面；环境缺失时由 `wordpress-setup` 补齐后继续原任务。

已有Harness网站可这样说：

```text
使用 $b2b-seo-onpage，配合本机 WordPress Build Harness 优化这一个页面。
网站项目：【本地项目目录】；目标页面：【URL】。
目标关键词：【关键词】；市场和语言：【例如美国、英文】。
行业词库与企业资料：【链接或文件夹】。

请完成研究和改稿，并把确认可用的内容落实到这个项目的本地WordPress页面，
保持现有设计，保存后检查后台和前台，最后给我查看地址和修改说明。
```

上例授权本地实施。只要文案时改成“这次只交改稿”；需要线上修改时说明线上目标和范围。Codex会沿用同一任务已有授权。已有模板不一定读取主编辑器，所以会先核实际字段；单页优化不会默认重置全站SEO、开放索引、重新建站或覆盖数据库。详细分工见[WordPress协作与实施](skills/b2b-seo-onpage/references/wordpress-harness-handoff.md)。

已上线的网站可以这样说：“用 `$b2b-seo-onpage` 和这个项目的 WordPress Build Harness，更新【原网址】的 SEO 标题、采购指南 H2 和对应段落。词库和企业资料在【目录】。改完请读回 WordPress 字段和该网址实际显示的内容。” 如果要新增文章，可以指定“在【站点项目】把【选题】保存成草稿，给我后台编辑链接”。

也可以从Harness开始：“用WordPress Build Harness继续这个网站，本页SEO研究与改稿使用已安装的 `$b2b-seo-onpage`，然后在刚才约定的目标完成修改和回读。”已有Content/Design负责人继续持有站点任务，SEO Skill提供研究和文案，不让流程重新开始。

## 会交付什么

只改 Title 时会拿到一个标题和一句理由，也要 description 时直接说明。整页改稿先给推荐标题、H1、相关 H2/H3 及可直接使用的正文，再说明最影响决定的一项取舍。读完整报告可从 `onpage-review.md` 开始，`page-brief.md` 和选词、SERP、竞品及关键词安排表保留详细依据。

首页、类目页和详情页会先从你的词库提取相关的完整查询和 B 端属性，再核当地搜索结果与企业事实。比如库里同时有 `custom printed mailer boxes` 和 `stock mailer boxes in bulk`，做按图印刷的一页应优先验证前者，批发标准现货箱的一页应优先验证后者。内置词表帮助识别漏项与补查。已有标题准确时可以原样保留。可查看[品类调研方法](skills/b2b-seo-onpage/references/category-modifier-research.md)和[跨行业采购用词表](skills/b2b-seo-onpage/references/b2b-buying-modifiers.csv)。

如果要求实际修改本地文件或 CMS，请在同一请求中说明目标与修改范围。改稿、保存、前台回读、Google展示和流量/询盘效果分别说明。

## 网页版关键词工具

需要补查时，可通过 Computer Use 使用用户提供且获准自动操作的工具入口，包括实际可用的 Keyword Magic、关键词概览和 SERP 功能；不固定官方域名，也不要求 MCP。登录、验证码或权限问题由用户完成；平台明示禁止自动化时，改由用户手动导出，后续本地分析继续。

报告保留搜索服务的实际返回顺序。仅在核到目标地区 Google 自然排名时才标记为 Google 名次。账号、密码和会话信息留在授权环境内。

## 版本与验证范围

v2.11.0 新增整站工作清单和同站新增 URL 入口。首页、集合页、详情页分别校验实际 SEO Title 与主 H1 中的品类和有公开依据的采购表达，前台回读可逐字对照已核准稿。旧 AI 页面可按上游模块重写。测试和公开发布范围见 [版本清单](RELEASE.json)。

v2.9.0 将改后的最终段落、上游模块和字段接入逐词验收。手机壳集合页用模拟客户资料及已保存的同行实页完成回放，覆盖旧 H1、错放小节、复合词的两处答案、公开状态和相邻现货页归属。验证范围见 [RELEASE.json](RELEASE.json)。

v2.8.1 将首屏副标题 `subtitle` 补入完整改稿字段清单，示例、命令和使用说明可以逐项对照。[改稿字段及用法](skills/b2b-seo-onpage/references/data-and-commands.md)

v2.8.0 用一张模拟的品牌定制手机壳集合页，从原始规划、分组和排名明细走到实际改稿。原分配的 3 个词都有文案；从分组外采用了 2 个词，共新增 1 个采购意图。现货词归现货集合页，选购词归指南。样稿开头保留原 H1，列出建议 Title、副标题和 H2，逐项注明可用或待确认。

本版通过 23 项自动回归，并用 5 万行词库和 10 万行排名明细验证按页取词。另用挖掘机、手机壳、CNC 加工三个公开网站的页面 HTML 核对标题和副标题提取。搜索观察记录的是实际检索来源；模拟客户的排名与获客效果需要真实项目数据另行评估。[验证记录](RELEASE.json)

v2.7.0 将客户的页面规划、分组表和行业词库接到单页改稿。选词和布局表可回查原组、规划角色与来源。新版加入完整采购短语解读、相邻页标题比较和采购答案写作，并纳入候选版已有的按 URL 引用 Search Console 查询功能。本次正式版按要求未运行测试。

v2.7.0-rc.1 用同一份模拟客户资料与 v2.6.0 做了离线改稿对照。两版都保留了有效查询并补清了起订条件。候选版增加了可回读的 GSC 来源、查询归属与日期检查，已在命令行验证。实际搜索表现需要已收录页面的后续数据。

v2.6.0 接收站点架构交付，按页型组合多个采购属性，给出 H 标签与正文的对应位置。两个线上 WordPress 演示站的首页、一级类目、二级类目、型号详情和文章共五张原页完成了字段修改、公网 Title 和相关 H 标签回读，以及原内容恢复。另经该站 Harness 创建了一篇采购资料草稿并核实保存状态。站点保持 noindex。本次验证说明内容可以通过这些站点的实际编辑链路更新，搜索成效需另有数据。

v2.5.0 引入 14 组、273 个英文候选表达。221 个附有原页对应表达，52 个为编辑提出的检索种子。品类研究从你的行业词库开始，再用 Google 找同行、按页型读实际页面。安装文件和验证范围见 [RELEASE.json](RELEASE.json)。

v2.4.0 确立了 WordPress Harness 协作方式，当时完成了 24 项 On-page 回归、类型、代码及文档链接检查。v2.3.0 演练过公开安装和资料引导。此前版本的标题、摘要及竞品分析方法继续沿用。[方法来源与取舍](skills/b2b-seo-onpage/references/upstream.md)

后续安装优先使用固定版本，发布记录见 [Releases](https://github.com/jackzhang1314/b2b-seo-onpage/releases)。
