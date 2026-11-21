# 从架构与词库确定一页的关键词位置

先找当前网站已经确认的架构。可接收用户给的目录、HTML、Markdown、表格或单页链接。确认产品、站点、语言、页型、上级和实际 URL。项目中的 `docs/CURRENT.md`、内容简报、旧网址映射和客户确认意见有助于区分原规划与已上线版本。

## 已有架构怎样接

核对过的上游是 [b2b-seo-site-architecture v0.4.1 输出说明](https://github.com/jackzhang1314/b2b-seo-site-architecture/blob/bb52b6894887ca72ba72490fad50641d9ccdec76/skills/b2b-seo-site-architecture/references/output-contract.md)。按实际收到的版本及文件取用。

| 手头资料 | 提取与使用 |
| --- | --- |
| 完整交付目录 | 在 `pages.csv` 找首页、类目、详情等核心页，在 `content-plan.csv` 找文章。读本行 ID、父级、路径、主词、页型、模板变体、职责、独有内容和待证事实。按同一 ID 查 `keyword-decisions.csv`，回到用户词库核完整查询、来源行、市场和排名 URL。 |
| 模块与字段资料 | `design-briefs.md`、`design-modules.csv`、`design-fields.csv` 和 `product-attributes.csv` 给出模块任务、变体、字段和筛选条件。用实际页面核实哪些模块已经上线、字段值是否有事实依据。 |
| HTML 或 Markdown | 从 `index.html` 的对应页面或文章条目，以及收到的规划、设计交接或研究笔记中，摘取明确写出的路径、主题、主辅词、上级、模块和证据状态；注明文件、标题或页面锚点。仅有架构图时可确认层级，关键词归属缺失的部分再查词库和实页。 |
| 仅有计划 JSON | 读取 `architecture-plan.json` 的 project、pages、decisions、templates。按 ID 关联；关键词只有 ID 时到所给词表取对应原词。记录来源与缺口。 |

完整表格可选用 `onpage.py architecture-page --source <架构目录> --url <规划URL> --out <新目录>`。输出的 `architecture-page.json` 只取一页及其词项，保留原表的数据行序号、架构 mode 和研究覆盖。文章同样可用此命令。URL 不同而已有可靠的旧新映射时，用 `--page-id <架构ID>` 读取规划，并在本页简报记录为何对应线上 URL。出现多个匹配先核身份。只有文档也可直接阅读，不要求重新导出表格。

保留已确认主词和页面职责。上游 `state=proposed/conditional`、`mode=simulation`、`research_complete=false` 或缺企业事实时，把相应状态带进本页。架构能说明计划由谁承接某个词；当前企业能否接单须有本企业依据。

## 从分配到标题、H 标签和正文

一个页面可以承接多条采购查询。先看每条在上游的去向，再决定表达。

- `page` 是整页主题候选，本页已定主词优先；核它适合在 Title 和主内容 H1 怎样出现。
- `section` 回答本页一个实际问题。用该问题拟 H2，下面写买家需要的答案、规格、比较或采购条件。H3 展开所属 H2 的一项细节。
- `filter` 先落实为真实可用的规格、选项、参数或筛选。只有页面确实解释这一选项，且它属于采购问题时才升为标题。
- 归属兄弟页、子类或型号的词以实际链接衔接。`defer/exclude` 保留原决定；有新的采购证据时，把修订意见交给用户。

先把本页现有的 HTML Title、H1、H2/H3 和对应正文排在一起，标明每个 H3 属于哪一个 H2。分别查看导航、产品卡片与页尾；有些主题将页面 H1 放在 `main` 之前。为重要词写出库内原词和来源、实际采用的表达、Title/H1/H2/H3/正文/参数/其他页、所属模块、内容依据。拟好的 H 标题必须让后面一段能作答。把词挪到 H2 时，同时交可替换的标题及需要增补的正文。原本准确的标题直接保留。

例如一个已确认生产定制包装的厂家，二级类目承接 `custom printed mailer boxes`，支持批量订单。可拟 Title 为 `Custom Printed Mailer Boxes for Bulk Orders`，H1 为 `Custom Printed Mailer Boxes`。H2 `Printing Options for Branded Mailer Boxes` 下面展示实际支持的印刷方案。另一 H2 `Planning a Bulk Mailer Box Order` 下面解释采购方应提供什么，其 H3 `Artwork and Box Dimensions` 给出文件与尺寸要求。某一箱型独有的内衬规格应留给具体款式。这里的语句示范落点，客户资料决定可采用的部分。

## 没有架构或行业词库时

没有架构就直接做这一页。读用户 URL、面包屑、导航、同级与子页、小范围竞品实页、业务资料和已有行业词库。确定这页服务的买家、上级与相邻页各负责什么，再拟主词、可组合的采购词和模块。新页先核最接近的现有页面、预期父级和模板，避免为同一采购需求重复建页。

没有可读的用户词库时，复用已获授权的本站 GSC/询价用语（如有）、实际产品名与规格、同行页面和目标市场查询，自行补查候选。记录本页研究来源与未取得的资料，继续给具体标题、大纲和改稿。通用搜索保留其真实来源。用户后来提供词库时，再按完整原词与排名 URL 对照。详见[研究记录接口](research-contract.md)。
