# B2B On-page SEO Skill

从目标关键词和页面开始，结合行业词库、目标市场 SERP 与竞品内容，完成页面简报、Title、描述、H 标签、正文和内链改稿。需要修改 WordPress 页面时，与已有 WordPress Build Harness 配合完成保存和回读。

**本目录为本地候选版 v2.7.0-rc.1。** 现有页面可附本页的 Search Console 查询导出。Codex 先保留已吸引目标买家的用词，再从行业词库与同行具体页面核对值得补充的采购条件，交付一个 SEO 标题和有实际答案的段落。新页可以直接提供架构、词库和业务资料。[关键词布局方法与示例](skills/b2b-seo-onpage/references/query-placement.md)

在这个候选目录中可以直接说：“请使用本目录的 `skills/b2b-seo-onpage` 优化【网址】。词库、页面和已有数据在【目录】。告诉我哪些买家用语应该保留，哪些采购问题还没有回答，并给我可替换的标题与正文。”

## 安装公开稳定版 v2.6.0

把下面这段发给 Codex 即可安装固定版本。

```text
请使用 $skill-installer 从这个固定版本安装 B2B On-page SEO Skill。
https://github.com/jackzhang1314/b2b-seo-onpage/tree/v2.6.0/skills/b2b-seo-onpage
已有相同版本且内容一致就复用。升级时先备份同名旧版和本地定制，保留较新版本。
安装后核对 Skill 版本和文件完整性，并告诉我怎么开始。
```

离线安装可下载 ZIP，将解压目录交给 Codex，要求它按包内的 `RELEASE.json` 核对完整性，安装整个 `skills/b2b-seo-onpage` 目录。[下载 v2.6.0 ZIP](https://github.com/jackzhang1314/b2b-seo-onpage/releases/download/v2.6.0/b2b-seo-onpage-2.6.0.zip) · [下载 SHA-256 校验文件](https://github.com/jackzhang1314/b2b-seo-onpage/releases/download/v2.6.0/b2b-seo-onpage-2.6.0.zip.sha256)

也可以使用本机 `skill-installer` 的命令行脚本，将下面的脚本路径换成本机实际路径。

```sh
python3 /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo jackzhang1314/b2b-seo-onpage --ref v2.6.0 --path skills/b2b-seo-onpage
```

宿主刷新技能列表后即可使用，必要时打开新会话。处理脚本使用 Python 3.11+ 标准库。关键词工具账号和站点权限沿用你的环境，实际修改 WordPress 时再接入该站已有的 Build Harness。

## 第一次使用，提供什么

**已有页面：目标关键词＋URL/稿件就能启动。尚未建页：先给关键词和目标市场。** Codex 会识别或建议页型；已确认的页型和主词会沿用。

以下资料有助于确定市场、采购词和可发布的企业事实。已有的直接复用。

- **行业词库位置**：CSV、表格链接，或原始导出文件夹；不用自己合并、去重或改列名。
- **目标国家和内容语言**，例如美国、英文。
- **真实业务资料**：企业角色、产品/型号范围、规格、可公开的能力与采购条件；已有架构或页面简报一并复用。
- **补查工具入口（可选）**：已有网页版关键词工具，或已导出的研究数据。

行业词库按两部分整理：①用户 Top 20 竞争对手各自自然排名位置 **1–30** 的关键词及排名 URL；②产品核心种子词的扩展词。不是每个竞品只取30个词。Codex保留来源与排名关系，同一个词的搜索量不会跨文件相加；缺失的竞品或来源会明确列出。

## 可直接复制的调用

```text
使用 $b2b-seo-onpage。
目标关键词：mini excavator manufacturer。
页面：【URL或稿件路径；没建页就写尚未建页】。
市场和语言：美国、英文。
行业词库或原始导出文件夹：【链接或路径】。
公司及产品资料：【链接或路径】。
已有网页版关键词工具：【入口；没有可省略】。

请识别页面类型，核对主词与真实业务是否适合；
整理词库，筛选适合本页的词组，分析目标市场SERP和代表竞品页面，
形成页面简报，再交Title、描述、标题结构和实际正文改稿。
说明选词与排除理由、竞品优点如何采用、关键词位置和资料缺口。
这次先交改稿，已有内容合适可以保留。
```

上面的关键词是示例。贸易商不能仅因关键词带 `manufacturer` 就写成自有工厂；美国市场也不等于美国制造。

只改标题时，可以直接说：

```text
使用 $b2b-seo-onpage。
页面：【URL或稿件】；已选主词：【关键词】。
行业词库：【文件或目录】。市场和语言：【例如美国、英文】。
先从词库找这个品类的采购用词，再用几组“产品＋可能的属性词”去 Google 找同行独立站。
看看同行在首页、集合页和详情页各用什么词。结合我们能接的订单，只给这页一个推荐 Title、description 和依据。
```

已有架构时，给架构输出目录、index.html 或 Markdown 简报即可。Codex 会复用这页的主词、章节词、筛选词、模板模块及资料缺口。有词库先查词库，没有架构就独立研究本页；缺少客户词库时仍可依据实页和业务资料给出改稿，注明研究覆盖。

## 给已有页面布局关键词

可以直接说“用 $b2b-seo-onpage。架构、行业词库和公司资料在这个文件夹，目标页面是这个 URL。请尽量把相容的采购属性自然组合进一个 SEO Title，给出 H1、H2/H3 和实际段落。已有归属的主词沿用；没有架构就自行研究这一页。” 查看[架构交接和 H 标签实例](skills/b2b-seo-onpage/references/architecture-to-page.md)以及[五种页型的标题示例](skills/b2b-seo-onpage/references/title-and-snippet.md)。

例如，一家按买家设计印刷、接受批量订单的邮寄盒厂家，可以把集合页的 SEO 标题写为 `Custom Printed Mailer Box Manufacturer for Bulk Orders`。H1 用 `Custom Printed Mailer Boxes` 点明类目。H2 `Planning a Bulk Mailer Box Order` 说明询价需要哪些资料，下面的 H3 `Artwork and Box Dimensions` 给出图稿和尺寸要求。

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

完整任务先看 `onpage-review.md`。`page-brief.md` 说明这一页为什么这样写；选词、SERP、竞品对照、改稿和关键词安排表保留依据。用户会拿到实际可替换的文案，缺证主张放在正文之外。

首页、类目页和详情页会先从你的词库提取相关的完整查询和 B 端属性，再核当地搜索结果与企业事实。比如库里同时有 `custom printed mailer boxes` 和 `stock mailer boxes in bulk`，做按图印刷的一页应优先验证前者，批发标准现货箱的一页应优先验证后者。内置词表帮助识别漏项与补查。已有标题准确时可以原样保留。可查看[品类调研方法](skills/b2b-seo-onpage/references/category-modifier-research.md)和[跨行业采购用词表](skills/b2b-seo-onpage/references/b2b-buying-modifiers.csv)。

如果要求实际修改本地文件或 CMS，请在同一请求中说明目标与修改范围。改稿、保存、前台回读、Google展示和流量/询盘效果分别说明。

## 网页版关键词工具

需要补查时，可通过 Computer Use 使用用户提供且获准自动操作的工具入口，包括实际可用的 Keyword Magic、关键词概览和 SERP 功能；不固定官方域名，也不要求 MCP。登录、验证码或权限问题由用户完成；平台明示禁止自动化时，改由用户手动导出，后续本地分析继续。

只取得可见样本就说明样本范围。通用搜索或未验证地域的结果不会冒充完整美国Google前十。账号、密码和会话信息不写进交付或公开包。

## 版本与验证范围

v2.7.0-rc.1 用同一份模拟客户资料与 v2.6.0 做了离线改稿对照。两版都保留了有效查询并补清了起订条件。候选版增加了可回读的 GSC 来源、查询归属与日期检查，已在命令行验证。实际搜索表现需要已收录页面的后续数据。

v2.6.0 接收站点架构交付，按页型组合多个采购属性，给出 H 标签与正文的对应位置。两个线上 WordPress 演示站的首页、一级类目、二级类目、型号详情和文章共五张原页完成了字段修改、公网 Title 和相关 H 标签回读，以及原内容恢复。另经该站 Harness 创建了一篇采购资料草稿并核实保存状态。站点保持 noindex。本次验证说明内容可以通过这些站点的实际编辑链路更新，搜索成效需另有数据。

v2.5.0 引入 14 组、273 个英文候选表达。221 个附有原页对应表达，52 个为编辑提出的检索种子。品类研究从你的行业词库开始，再用 Google 找同行、按页型读实际页面。安装文件和验证范围见 [RELEASE.json](RELEASE.json)。

v2.4.0 确立了 WordPress Harness 协作方式，当时完成了 24 项 On-page 回归、类型、代码及文档链接检查。v2.3.0 演练过公开安装和资料引导。此前版本的标题、摘要及竞品分析方法继续沿用。[方法来源与取舍](skills/b2b-seo-onpage/references/upstream.md)

后续安装优先使用固定版本，发布记录见 [Releases](https://github.com/jackzhang1314/b2b-seo-onpage/releases)。
