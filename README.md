# B2B On-page SEO Skill

从目标关键词和页面开始，结合行业词库、目标市场 SERP 与竞品内容，完成页面简报、Title、描述、H 标签、正文和内链改稿。需要修改 WordPress 页面时，与已有 WordPress Build Harness 配合完成保存和回读。

**版本：v2.4.0。** 本仓库只提供 `b2b-seo-onpage`，可以独立安装，无需先安装整套 B2B SEO Skills 或 SEMrush MCP。适用于企业首页、产品类目、型号详情、文章、能力和应用页面。SEO研究与改稿可独立使用；WordPress实施复用本机已有Build Harness及该站项目。

## 安装

把下面这段发给 Codex：

```text
请使用 $skill-installer 安装 B2B On-page SEO Skill。
仓库：https://github.com/jackzhang1314/b2b-seo-onpage
固定版本：v2.4.0
目录：skills/b2b-seo-onpage

先核对已有同名Skill；相同版本且内容一致则复用。
需要更新时先保留旧版和本地定制，不覆盖其他Skills，不降级较新版本。
安装后检查版本、参考文件和脚本是否完整，并告诉我如何调用。
```

安装完成后从下一轮对话使用；若当前宿主尚未刷新技能列表，打开新会话。需要离线文件时下载 [v2.4.0 ZIP](https://github.com/jackzhang1314/b2b-seo-onpage/releases/download/v2.4.0/b2b-seo-onpage-2.4.0.zip)，将解压目录交给 Codex 安装。不要只复制 `SKILL.md`，须保留整个 `skills/b2b-seo-onpage` 文件夹。

给熟悉命令行的用户：使用本机 `skill-installer` 提供的脚本执行：

```sh
python3 /path/to/skill-installer/scripts/install-skill-from-github.py \
  --repo jackzhang1314/b2b-seo-onpage \
  --ref v2.4.0 \
  --path skills/b2b-seo-onpage
```

`/path/to/skill-installer` 替换成本机实际目录。处理脚本需要 Python 3.11+，运行依赖仅为标准库。浏览器、文件访问和网站后台能力使用当前 Codex 环境已有工具，不随本 Skill 安装获得。

## 第一次使用，提供什么

**已有页面：目标关键词＋URL/稿件就能启动。尚未建页：先给关键词和目标市场。** Codex 会识别或建议页型；已确认的页型和主词会沿用。

完整优化还需要：

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
只优化Title与description，交一个推荐版本及依据；适合保留的部分请保留。
```

局部任务复用已有资料，不必重做整个行业研究。完整任务缺词库时，先交页面现状和意图/页型初判，并引导补充资料，不宣称完整研究已经完成。

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

也可以从Harness开始：“用WordPress Build Harness继续这个网站，本页SEO研究与改稿使用已安装的 `$b2b-seo-onpage`，然后在刚才约定的目标完成修改和回读。”已有Content/Design负责人继续持有站点任务，SEO Skill提供研究和文案，不让流程重新开始。

## 会交付什么

完整任务先看 `onpage-review.md`。`page-brief.md` 说明这一页为什么这样写；选词、SERP、竞品对照、改稿和关键词安排表保留依据。用户会拿到实际可替换的文案，缺证主张放在正文之外。

标题按页面任务选择主题与可兑现的点击理由，保留型号和真实范围。长度预览帮助判断表达，不以60字符、关键词密度、固定字数或SEO总分作为通过标准。已经准确的标题可以保留。

如果要求实际修改本地文件或 CMS，请在同一请求中说明目标与修改范围。改稿、保存、前台回读、Google展示和流量/询盘效果分别说明。

## 网页版关键词工具

需要补查时，可通过 Computer Use 使用用户提供且获准自动操作的工具入口，包括实际可用的 Keyword Magic、关键词概览和 SERP 功能；不固定官方域名，也不要求 MCP。登录、验证码或权限问题由用户完成；平台明示禁止自动化时，改由用户手动导出，后续本地分析继续。

只取得可见样本就说明样本范围。通用搜索或未验证地域的结果不会冒充完整美国Google前十。账号、密码和会话信息不写进交付或公开包。

## 版本与验证范围

本独立版含12个运行文件；来源标识和文件摘要见 [RELEASE.json](RELEASE.json)。不包含其他SEO Skills、Harness源码、客户资料、研究记录或测试夹具。

2.4.0已通过24项On-page回归、两个脚本的严格类型检查、lint、Skill格式及文档链接检查。协作说明对照Harness 2.39.24、分发修订19的实际接口编写。完整WordPress端到端实测尚未完成，不宣称本版已通过完整CMS实施验收。2.3.0的公开安装与资料引导已单独演练；此前9个离线合成场景及35项语义核对属于2.3.0基础版本。这些检查均不证明真实客户排名或询盘增长。

更新说明：2.4明确SEO研究与WordPress实施的分工、字段映射、实际写入和回读；研究与改稿数据接口不变。2.3的按页型写Title/摘要、竞品内容取舍及效果解释继续保留。方法来源及取舍见 [references/upstream.md](skills/b2b-seo-onpage/references/upstream.md)。

后续安装优先使用固定版本，发布记录见 [Releases](https://github.com/jackzhang1314/b2b-seo-onpage/releases)。
