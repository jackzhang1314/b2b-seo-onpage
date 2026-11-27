# 从架构与词库确定一页的关键词位置

先找当前网站已经确认的架构。可接收用户给的目录、HTML、Markdown、表格或单页链接。确认产品、站点、语言、页型、上级和实际 URL。项目中的 `docs/CURRENT.md`、内容简报、旧网址映射和客户确认意见有助于区分原规划与已上线版本。

## 客户给了页面规划、关键词分组表和几万行行业词库

先记下文件版本、工作表和实际列名。三份资料可以是三个文件，也可以在同一工作簿的不同标签页。页面规划决定这页负责什么，分组表说明哪些需求已分给它，总词库提供完整原词及已有依据。版本互相矛盾时优先采用能确认的客户决定。有争议的成员单列，其余照常写稿。

| 顺序 | 实际读取与判断 |
| --- | --- |
| 页面 → 分组 | 从页面编号、规划 URL 或已证实的新旧网址关系定位，再取这页绑定的所有组。对照同语言的上级和最相近同级页，保留已定主词、职责、章节及不应混入的主题。 |
| 分组 → 成员 | 展开各组的完整成员，保留组号/组名、关键词 ID、角色、原行和确认状态。一组跨页时用成员自己的归属。同页多个组可以分别回答选型、工艺、订货等问题。每个组的代表词只代表该组。 |
| 成员 → 行业词库 | 优先用共用关键词 ID、市场、语言找原词、来源和可得的排名 URL。没有共同 ID 时在同市场、同语言核对整句，保留型号、单位和限定词。多个候选留原行复核。词库里暂时找不到的分组词仍保留规划来源。 |
| 补充词 → 已有归属 | 本页分配读全后，再在总库按产品、同义说法和采购条件查漏。查新词在全站规划中是否已分给别页。属于别页时保留页面 ID 或 URL，以及本页有用的简述或链接。确属本页而尚未分配时标“建议补充”。分组与接单资料矛盾时写明原方案、证据和建议去向。 |
| 组与成员 → 页面文案 | 给组内每项需求一个去向。能被同一句、同段或同一张规格表满足的词可以共同指向那里。简报列本页主词及组名，安排表给出可见位置、实际表达及原表出处。按同一去重口径注明分配成员数、已处理数和余项原因。 |

例如规划将 P12 软壳夹克类目分为 G4“采购软壳夹克”和 G9“绣标选项”，尺码测量教程归 P28。应先从 G4 确认 P12 的品类用词，从 G9 选出实际支持的刺绣问题写入 H2 和正文。P28 的测量步骤留给教程，必要时在 P12 的尺码表旁给入口。若总库另有 `factory direct workwear`，先核首页是否已承接找厂需求，再核本类目是否直接接单。以上编号和事实均为示意。

### 表格读取

Excel、CSV 或可访问的在线表格按原格式交给 Codex。先检查工作表及表头，再用可用的表格工具或逐行读取按页筛选，保留原文件、表名和行号。几万行可以建立可复用索引或分批读取，按当前页展开完整成员及相关边界词。只拿到预览或抽样时注明实际覆盖。

标准 CSV 可用现有 `architecture-page` 接入三份资料。下面的页面编号、市场、语言和路径换成实际值。

```sh
python3 skills/b2b-seo-onpage/scripts/onpage.py architecture-page --source planning \
  --page-id P12 --keyword-map planning/keyword-page-map.csv --library data/keywords.csv \
  --market US --language en --out work/P12-input
```

页面计划沿用下文格式。分组映射每行一个成员，列为 `keyword_id, keyword, target_url, market, language`，可带 `owner_page_id`、`group_id` 或 `need_id`、角色与状态。只按编号分配时保留空的 `target_url` 列。词库列为 `keyword_id, keyword_original, market, language`。市场和语言沿用原表的值，有页面或项目范围时可省命令行选项。客户表头不同或分组关系在另一张工作表时，由 Codex 根据真实对应关系生成供读取的 CSV，保留原文件、原工作表、原始行号和分组列。两表没有共用 ID 时可留空。没有已确认的“组 → 页”关系时，只采用能确定归属的行。

结果在 `architecture-page.json` 的 `planning_inputs`。 原架构也给了逐词分配时，`architecture_ownership_review` 会列出与本页候选重叠的其他页、暂缓或排除记录。查看 `assigned_rows` 的成员、`library_matches` 的原词和 `ownership_review` 中的跨页或未分配记录。无共用 ID 的同市场整句命中列于 `exact_phrase_candidates`，同 ID 但原词不同列于 `id_phrase_review`，均由编辑对照原件后采用。`missing_library_ids` 列出未对上的编号。`map_rows_read` 和 `library_rows_read` 统计扫过的记录数，单页完成度按该页成员的实际去向计算。分组、角色、原有来源列与本次读取的 CSV 行号均保留。

### 用具体竞品 URL 在总库查漏

先按架构的产品范围和页型，从 `ranked-url-summary.csv` 或客户对标资料挑出合格的外贸 B2B 页。汇总表只用来找页面。逐词回查使用 `ranking-observations.csv` 或用户的原始导出，保留全部实际排名和原行。搜索命中首页、从导航找到集合页时，分别核各自地址。

```sh
python3 SKILL_DIR/scripts/onpage.py architecture-page --source ARCH --page-id P12 --keyword-map map.csv --library library.csv --rankings ranks.csv --peer-url https://supplier.example/collections/cases/ --library-term "phone covers" --market US --language en --out page-input
```

`--peer-url`、`--rankings` 和 `--library-term` 可重复。只传已经确认合格的实读页。搜索词片段使用与该产品相关的别称或具体修饰短语。若总词过宽就收窄组合；单复数或其他语言的叫法可分别加入。脚本按字词边界查找英文短语，语义相关性由编辑判断。没有已选同行时仍可读原分组。传了同行且未指定排名文件时，优先使用架构目录中的 `ranking-observations.csv`，其次使用带排名 URL 的归一化总库。

含排名明细的 CSV、分号 CSV 与制表符文件可直接读取（UTF-8 或带 BOM 的 UTF-16）。独立排名表可用 `Keyword`/`关键词`、`URL`/`排名 URL`、`Current URL` 与 `Current position`。对比期导出取当前 URL 和当前位置，旧列保留在原记录。遇到其他表头，先根据客户原件对应列名，再做归一化。排名明细也可只有 `keyword_id` 和 `url`，由同市场同语言词库还原原词。不同来源逐行保留排名、日期、指标和原文件位置。`--ranking-date YYYY-MM-DD` 可限定快照。原表整列缺市场或语言时，先由编辑核实文件级范围再使用本页参数，在结果中标记继承来源。若该列存在而行值缺失，则留待复核。URL 保留路径大小写、末尾斜杠及查询参数，不同地址的关系须有明确依据。

`architecture-page.json` 中 `keyword_inventory` 保留逐词规划、排名、全库命中及全站归属，也列零命中 URL 和无法还原的排名行。发起整页校验时传 `--architecture-page page-input/architecture-page.json`。给每个候选提交 `include / other_page / review / exclude` 的编辑判断，include 要接到具体文案位置。已归别页或有冲突的词要调整时，引用经确认的规划变更。新增同义词和新增意图分别计数。[研究字段](research-contract.md)

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
