# 从网站规划到上线页面

## 整站和单页怎样开始

| 用户交给 Codex 什么 | 会得到什么 |
| --- | --- |
| 当前网站项目，或已采用的架构工作台 | 从 `pages.csv` 和 `content-plan.csv` 取出这个站、市场和语言的全部规划页。从支持 SEO 勾选的工作台筛出已请求且可处理的页，在 `site-queue.csv` 记录每页的改稿、实际保存位置、前台链接和待处理原因。 |
| 一个已有或刚新增的 URL | 优先匹配该 URL 的规划行，复用它的词组和模块。有页面但尚未列入工作台时，读取真实产品、父类和相邻页的选词，用同站词库和可比同行提出本页主词。覆盖表注明归属为本次建议。 |

从网站项目运行 `site-queue --project-root <项目> --out <新目录>` 。也可给 `--source <工作台>/index.html` 或整个目录。HTML 是工作台入口，与它同目录的索引和表格提供逐行数据。工作台有多种市场、语言或真假数据时，按目标项目选定一份。自动发现读取网站 `AGENTS.md` 中同范围的采用版。只有一份匹配草案且已勾选时，可从那份草案继续；只勾建页时可查资料，SEO 队列为空。

当范围是整个现网站，Codex 用已有 Harness 读取站内已发布、可优化的公开页面与记录，把清单通过 `site-queue --site-inventory <实际页面.csv>` 与工作台对照。这张表由实施方生成，列为 `url,page_type,cms_record,status`，可加 `market,language,page_name`。页型取实际页面用途，记录写对象类型与 ID（例如 `page:24`）。清单只列对外页面，媒体附件、后台接口和内部搜索页不列入。规划行缺失的同站页面可单独具名优化，保留其他页的词组归属。启用独立 SEO 勾选时，整站执行仅纳入工作台已选择页。重复网址、同记录多网址或页型冲突标待核。已安排建页并要求 SEO 的页面可以先改稿，待实际页面建成后再回读发布结果。

每页运行 `architecture-page --project-root <项目> --page-id <编号> --out <页目录>` 。指定网址时用 `--url <URL>`。确认目标网址属于该站、但尚无规划行时，加 `--allow-unplanned`。先搜索已有清洗词库、逐词归属、可比页面、该 URL 的排名明细和 Top Pages。原始导出用来补缺或复查。Top Pages 的页面流量和逐词排名各自保留来源。全站复用同品类、市场和页型的同行观察，每一页单独核产品事实、承接范围和落点。

## 怎样给主词补上采购属性

保留上游已定的产品主词，检查它是否含采购表达，另外记下本页可采用的品类词形、供货方式和依据。例如主词是 `mini excavator`，先查 `mini excavator supplier` 和 `mini excavator manufacturer`。分别看目标市场里靠前、可比的约五家外贸 B2B 独立站，看产品页对型号、供货对象和订单方式怎样措辞。只要是找同行的线索，即使工具查不到搜索量也可以研究；把数值留空。实际查询、同行用语、企业资料分别回指来源。

首页、产品集合页、产品详情页的 **SEO Title 与主 H1 每处都要有本页品类和至少一项有企业依据的 B 端表达**。首页写主营范围，集合页写全系列成立的条件，详情页同时保留型号或具体款式。两处可用不同的自然说法。About Us 可以说明企业身份和依据，服务页写真实服务范围，文章围绕读者的问题组织。

| 虚构业务条件 | SEO Title | 主 H1 |
| --- | --- | --- |
| 工厂自产定制玻璃瓶，首页代表该业务 | Custom Glass Bottle Manufacturer · Example Glass | Custom Glass Bottles for Brands |
| 这组手机壳都可定制图案，接受批发订单 | Custom Phone Cases for Wholesale Orders | Custom Printed Phone Cases |
| 这款挖掘机只向经销商供货，企业是供应商 | EX20 Mini Excavator for Dealers · Example Equipment | EX20 Mini Excavator for Distributors |

每种说法都要覆盖该页的产品和订单。`custom` 表示定制，`customer` 表示客户。`bulk orders` 表示批量订货，规格表里的 `bulk density` 表示堆积密度。`factory automation` 指工厂自动化。通过同行导航或域名看到 Factory 可以启发检索，企业订单条款、产品目录、可核实的生产资料都可作为本方证据。只有本企业的适用证据才能支持“我方是制造商”。证据不足时先查产品目录、企业资料和订单条件，能证实企业供货就可选择 supplier 或真实交易方式。仍不能确认时，该页保留待核状态，整站继续处理其他页。

一个词已经把订单说清，就不用再串同义词；第二个词能说明另一项真实条件时可以加入。例如 `Custom Phone Cases for Wholesale Orders` 同时说明了可以定制、可以批量订货。其他条件可以在副标题、H2 和对应该节的正文说明。Google 的系统会理解相关词，并可能依据可见主标题等内容生成搜索结果的标题链接。团队使用双标题检查来表达企业能接什么订单。[搜索入门指南](https://developers.google.com/search/docs/fundamentals/seo-starter-guide) · [标题链接指南](https://developers.google.com/search/docs/appearance/title-link)

## 写到实际页面里

从工作台读出本页词组、模块、设计字段和该型号的产品属性。对照现有页面，把每个小节定为保留、重写、补充或待核。原先 AI 生成的描述泛泛时可以重写首屏与整段正文。例如“高品质手机壳”可换成买家如何选择材质、可印哪些位置、询价时提交什么文件。只有企业资料支持的部分才写入公开稿。保留现有有效产品关联、图片、表单、型号参数和已经有价值的查询。覆盖表指向最终稿里实际回答该需求的模块和原句。

沿用 `plan.json` 的 `focus.primary_keyword` 和 `claims`。在完整商业页稿中加以下片段。`claim_id` 指向本企业可公开且适用于该页的事实，例如可定制印刷、确实接受批发订单。批准状态沿用原资料。客户只提供内部模拟时，即使写出的标题很好，也仍要留在模拟交付中。

```json
{
  "commercial_headings": {
    "page_type": "category",
    "category_terms": ["phone case", "phone cases"],
    "modifiers": [
      {"phrase": "custom", "claim_id": "logo-printing"},
      {"phrase": "wholesale", "claim_id": "trade-orders"}
    ]
  }
}
```

`category_terms` 填真正的品类词形，勿填品牌、裸型号或包含采购词的整串标题。记录对应语言和实际表达。行业用语和其他语言可在 `modifiers` 中提供自然短语，同时用 `kind` 标记 `supplier_role`（供方身份）、`order_type`（接单方式）或 `trade_buyer`（企业客户），例如 `{"phrase":"for brands","kind":"trade_buyer","claim_id":"brand-orders"}`。检查结果记录实际词和依据，编辑负责判断该企业事实能否支持这句话。

```sh
python3 onpage.py check-plan --plan plan.json --evidence before/page-evidence.json \
  --architecture-page inputs/architecture-page.json --require-b2b-headings --out draft
python3 onpage.py compare --plan plan.json --after after/page-evidence.json \
  --architecture-page inputs/architecture-page.json --reviewed-headings draft/commercial-headings.json \
  --require-b2b-headings --out readback
```

两个命令分别检查改后拟稿和另行采集的页面。`commercial-headings.json` 列出原主词、里面已有的采购表达、两个位置的完整文本、采购词、事实编号和待核原因。整页的 `keyword-coverage.xlsx` 另有「SEO Title 与主 H1」工作表，可直接查看两个位置的最终文案和企业依据。声明 `commercial_headings` 后，未通过就以退出码 2 返回并保留报告。旧版计划加 `--require-b2b-headings` 同样执行严格检查。保留的旧 H1 和保留的 Title 也要检查。用户只要一个字段时尊重本次写入范围，并说明另一处的实况。

## 用 WordPress Builder Harness 实施

用户已指定项目、环境和实施范围时，在同一次任务继续调用该站的 `wordpress-builder`。Content 更新对应记录的 SEO 插件字段、H1 源字段、ACF 或正文并重新打开。新增单页内容优先使用已有模块，确有模板或字段绑定缺口再由 Design 处理。Delivery 读取同一环境的实际 URL，保存新的快照，再核标题、正文、原有产品和询价入口。按站点已有的写入授权推进整批，记录冲突、缺证和失败的具体页，继续完成可处理的页。[WordPress 实施流程](wordpress-harness-handoff.md)

正式工作台用[共享写回流程](workbench-progress.md)保存版本和页号对应的「已优化」与「已发布」事件。把每页的实际结果也写回本轮 `site-queue.csv`。`progress` 使用 `drafted`、`saved`、`verified` 或 `blocked`；`cms_record` 记录对象类型和 ID，后两列分别引用后台及前台回读。只有同一版本已保存并在目标环境读回，才标记 `verified`。线上首次建页按用户授权的范围处理。规划了但站上尚无记录且只授权优化现有页时，交出可用稿并记明原因。重试从已有队列继续，先检查原记录和上次回执，避免重复建页或覆盖刚发生的编辑。
