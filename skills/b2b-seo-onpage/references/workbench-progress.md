# 让网站工作台显示真实进度

用户在架构工作台为页面打开「做 SEO」，Codex 即可接着工作。想优化全站，可以批量选择要优化的页面。已经上线的页面可单独安排 SEO。只选建页时，建站工具处理建页，On-page 继续保留该页的关键词归属供其他页面研究。

## 如何读取本轮页面

当前网站根目录 `AGENTS.md` 的 SEO 小节指向 `seo-project-index.json`，其中 `files.handoff` 是这版工作台的选择和进度。用户给定一个工作台目录或 `index.html` 时固定此版。从工作台浏览器链接进入时，核实其本地工作台目录与页面显示的版本编号，勿自动改选较新版本。自动发现优先选同站、同市场、同语言的采用版。没有采用版且只有一个符合条件的已勾选草案时可继续。

`site-queue` 从该版选择只输出 `seo_eligible=true` 的页。是否合格由架构工具根据「要求 SEO」及页面是否要建或已有可改记录判断。单独选择建页、SEO 暂缓和未明确排期的行留在 `run.json` 的范围说明中。跳过新建与优化现有页面可以分别表达。已有改稿或发布回执时先复核当前版本和现场，按实际需要续做。查资料可照常用 `architecture-page`，其中 `workbench_progress` 记下所选版本和页号。旧工作台只有建页选择、缺少独立 SEO 选择时，可以照常研究并处理用户单独点名的 URL。全新、尚未登记的 URL 也可单独优化，使用它自己的交付记录。

## 优化和保存的两个结果

- **工作台显示「已优化」。** 当拟稿通过对应范围的检查，且已保存并重新读到改稿和报告，On-page 用共享入口写回 `onpage/optimized`。完整页面仍按整页研究和覆盖流程验收，局部任务的摘要注明实际范围。未核实的商业标题、待核稿和失败运行保留本地资料。
- **工作台显示「已发布」。** WordPress Builder Harness 在指定站点保存了对应的已发布对象，独立回读该对象的同一版本；并从其正式 URL 再次抓到与核准稿一致的 Title、H1 及本次预期改动后，才能写回 `onpage/published`。草稿、预览、仅导出 HTML 和例题拟稿都不会满足此条件。隔离 WordPress 的实际发布回读仅属于该模拟项目。

下面是 Codex 在普通优化工作流中使用的命令。用户提供项目或工作台与目标范围即可。

```sh
python3 onpage.py site-queue --project-root PROJECT --out queue
python3 onpage.py architecture-page --source WORKBENCH --page-id PAGE_ID --out inputs
python3 onpage.py check-plan --architecture-page inputs/architecture-page.json \
  --plan plan.json --evidence before/page-evidence.json --require-b2b-headings \
  --sync-workbench --out draft
python3 onpage.py compare --architecture-page inputs/architecture-page.json \
  --plan plan.json --after after/page-evidence.json --reviewed-headings draft/commercial-headings.json \
  --cms-save cms-save.json --cms-readback cms-readback.json --require-b2b-headings \
  --sync-workbench --out verified
```

`cms-save.json` 和 `cms-readback.json` 可直接使用 Harness 的 `content-apply` 与单独 `read-content` 输出。保留同一对象的 ID、类型、正式链接、发布状态和保存版本。只把这些原始回执留在该站的私有项目目录；工作台登记的是实施证据的引用。其他现场适配器保留其真实回执，自动校验未识别时把实施结果保留待核。前台用独立获取的最新 HTML/DOM，`inspect --capture` 中记录实际最终 URL、抓取时间、来源和观测到的 `http_status: 200`。每个写回事件附 `workbench-proof.json`，可按路径和摘要核对页面稿、回读报告及两份 CMS 回执。

工作台共享命令位于同一台机器上架构 Skill 的 `scripts/workbench_progress.py`。On-page 检查写回前的当前选择与版本，只写 `onpage` 轨道。`--architecture-skill` 可以指定隔离测试用的架构安装目录。若写回暂时失败，稿件与回读结果已留在原目录。用 `workbench-sync` 加上同一 `--out`、`--architecture-page` 和 `--plan` 重试；发布还须传回原 `--after`、`--reviewed-headings` 及两份 CMS 回执。重复成功会复用稳定事件编号。工作台已换版时先重新取得该页的规划与选择。
