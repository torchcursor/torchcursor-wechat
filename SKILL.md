---
name: torchcursor-wechat
description: Convert Markdown into WeChat Official Account (公众号) ready-to-paste HTML that keeps its layout after pasting — inline-only styles, no <style>/class/id/pseudo-elements, card-and-notecard layouts, numbered sections, highlight underlines, page-tint backgrounds and ruled/grid paper backgrounds; ships a zero-dependency CLI plus a single-file browser studio with one-click style/background buttons. Use when the user wants 公众号排版, 微信排版, Markdown 转微信 HTML, 把文章做成可粘贴到公众号后台的格式, 排版控制台, or needs HTML that survives the WeChat editor's sanitizer (微信公众号粘贴兼容 / 草稿箱 / 排版美化).
license: MIT
metadata:
  version: "1.6.0"
  author: TorchCursor (火把光标)
  language: zh-CN / en
  dependencies: Python 3.8+ (standard library only); studio.html needs no runtime
agent_created: true
---

# torchcursor-wechat · 微信公众号 Markdown 排版

把一个 Markdown 文稿转成**在浏览器全选复制、粘贴进微信公众号后台后仍然保持排版**的 HTML。

本技能只做排版，不改观点、不做内容诊断、不润色文案。

## 核心原则（先读这几条，否则做出来的东西在微信里会散架）

1. **浏览器复制不会带走 `<head><style>`**。所以可见样式必须逐元素写在 `style` 属性上，不能依赖 class、id、伪元素或父级继承。
2. **公众号后台会二次清洗 HTML/CSS**。禁用 `<style>`、class、id、`:before/:after`、外链资源、JS、hover、`position:fixed`、渐变、阴影、`background-image`。能用单色、边框、留白表达的，就用它们表达。
3. **正文不重复标题**。文稿首个 `# 一级标题` 只写入 `<title>` 与文件名，不进入正文；否则发布后会出现两个连续标题。
4. **全文底色用「牺牲壳」双层包裹 + 逐块防断裂**。实测（2026-09-11 三轮真机）机制：粘贴时编辑器**只丢弃最外层那一个容器**，第二层及更深的 section 连同样式原样保留（头部卡片的底色就是这么活下来的）。所以最外层放不带样式的牺牲壳 `<section>`，真正的底色层放第二层；`--page-bg none` 可关闭包裹。
5. **每个内容块都自带底色，间距一律用 padding 不用 margin**。实测（2026-09-11 第四轮真机）：底色层进微信后会被摊到每个文字块上，块与块之间的 **margin 不属于任何块、会露白**；margin 不吃背景，padding 吃。生成器用 `blockify` 把垂直 margin 折半转成 padding 并给每个块补底色，保证全文无白缝。
6. **布局一律不用表格**。微信编辑器会把粘贴进来的表格转成自己的表格组件：出现边框、列宽错乱（实测：标题、图片全被框上方框）。图文并排用图片 `float:right` 固定像素宽 + 文字绕排（float 和 px 宽度粘贴都保留；清洗也只是退化为上下堆叠）；分节标题用纯段落堆叠。图片占位不带任何边框（虚线框粘过去会被当成小方框）。

**为什么要自己写解析器和渲染器，而不是手写 HTML**：微信清洗规则是硬约束，靠人工每次注意必然出错；把规则写进代码 + 自检脚本，才能保证每次产出都合规。本技能自带 `scripts/generate.py`（零第三方依赖）与 `--check` 自检。

## 两种用法：命令行，或点按钮

| 用法 | 入口 | 适合 |
|---|---|---|
| 命令行 | `scripts/generate.py` | AI/脚本调用、批量生成、固定栏目配置 |
| **可视化控制台** | `studio.html`（单文件、零依赖、双击即开） | 人在调样式：点按钮换底色/字号，右侧实时预览，一键复制 |

控制台与命令行是**同一套规则的两种实现**（同一份风格 token、同一套 Markdown 规则），渲染结果逐字节一致，由 `scripts/check_sync.py` 在 CI 里锁死。改风格必须同时改两处，否则 CI 会红。

## 何时使用

- 用户要把写好的一篇文章 / 口播稿 / 长文做成公众号可粘贴的 HTML
- 用户抱怨"排版粘贴到公众号就乱了""样式丢了""底色没了"
- 用户要一条固定栏目视觉（标题卡片、编号分节、强调下划线、全文底色）
- 用户要**点按钮**调排版而不是记命令 → 直接用 `studio.html`

## 快速开始

```bash
# 默认即卡片笔记风格（唯一风格）
python3 scripts/generate.py article.md

# 全文底色：默认 auto（双层牺牲壳包裹，随粘贴保留）
python3 scripts/generate.py article.md

# 关闭包裹（白底直出）
python3 scripts/generate.py article.md --page-bg none

# 头部卡片真图（先传公众号素材库拿 mmbiz 链接）
python3 scripts/generate.py article.md --card-img-url "https://mmbiz.qpic.cn/....jpg"

# 用配置文件固定栏目调性（推荐长期使用）
python3 scripts/generate.py article.md --config torchcursor.config.json

# 生成后跑微信粘贴合规自检
python3 scripts/generate.py article.md --check
```

可视化控制台：直接双击 `studio.html`（或拖进浏览器），无需 Python、无需联网。

输出默认写到文稿同级的 `公众号HTML输出/`。生成后告诉用户：打开 HTML → `Cmd+A` 全选 → `Cmd+C` 复制 → 粘贴到公众号后台编辑器 → 用后台预览检查手机端。

## 唯一风格：卡片笔记（cardnote）

暖米白底 + 头部方框卡片（圆角图片位）+ 编号分节 + 橙色下划线强调。
1.5.0 起为**唯一风格**（David 决定砍掉 graphite/forge，聚焦一套视觉）；底纹（横线纸/方格纸/PNG 底图）全部移除。

排版参数（2026-09-12 David 定稿）：正文 80% 黑 `#333333`、标题 90% 黑 `#262626` 字重 700、
重点标注（下划线/加粗/红字）100% 黑、每个块左右内边距 ≥15px（不贴边）。

完整 CSS 设计源见 `references/styles.md`。

## 背景：必须分三层理解

这是最容易做错的一点，也是本技能区别于普通"Markdown 转 HTML"工具的地方：

| 层 | 做法 | 能否粘贴带入 | 说明 |
|---|---|---|---|
| **全文底色** | 牺牲壳双层包裹（底色在第二层 section）+ 每块单独补底色 | 能（真机已验证，持续复核） | 编辑器粘贴时只丢最外层容器；第二层底色随头部卡片一同存活。`--page-bg none` 关闭 |

**不要试图做底纹**：横线纸/方格纸底纹和 PNG 底图（1.4.0 及以前的功能）已按 David 决定移除——背景图一定被清洗，后台也没有背景上传入口。**不要把 `background-image` 当作可靠的粘贴手段**——它一定被清洗。也不要把样式写在最外层容器上——最外层容器会被丢弃（所以底色必须放在第二层）。

**哪些彩色背景能保留**：第二层及更深的元素背景都可以——全文底色层、头部卡片、黑底导语条、金句卡、引用块。

细节与已知回落项见 `references/wechat-limits.md`。

## 参数速查

| 参数 | 说明 |
|---|---|
| `--style` | 默认 `cardnote`（唯一风格） |
| `--page-bg` | 全文底色：`auto`（默认，取风格底色）/ `#色值` / `none`（不包裹）。双层牺牲壳包裹，随粘贴保留 |
| `--accent` `--brand-color` `--bg-color` `--ink` | 强调色 / 品牌词色 / 页面底色 / 金句卡底色 |
| `--font-size` `--line-height` | 正文字号（默认 16）、行高（默认 1.9） |
| `--eyebrow` `--lead` `--footer` | 头部卡片眉题 / 黑底导语条 / 落款 |
| `--card-img-url` | 头部卡片真图 URL（公众号素材库地址）：固定 132px 宽右浮动、圆角 + 细修饰边框，任何原图尺寸都渲染成同样大小的缩略图；留空回落固定 132×88 占位盒（删文字边框不掉） |
| `--card-img` | 头部卡片图片占位文案（无 URL 时显示） |
| `--title` `--no-card` `--no-parts` `--plain-h2` | 覆盖标题 / 关头部卡片 / 关编号分节 / 分节不用表格 |
| `--config` `--out` `--check` | JSON 配置、输出目录、合规自检 |

CLI 优先于配置文件，配置文件优先于内置默认值。完整参数手册与新增风格的方法见 `references/customize.md`。

## Markdown 支持

| 写法 | 结果 |
|---|---|
| 首个 `# 标题` | 只进 `<title>`，不进正文 |
| `## 标题` | 分节；开启 `parts` 时自动编号 `01/02/03…` 并渲染为段落堆叠分节头（不用表格） |
| `### 标题` | 三级标题 |
| `**粗体**` / `` `代码` `` | 加粗 / 行内代码 |
| `==文字==` | 关键强调（cardnote 为橙黄粗下划线） |
| `<u>` `<r>` `<l>` `<n>` | 高级行内标记：强调 / 红字 / 品牌词 / 编号 |
| `> 引用` | 引用块 |
| `> !文字` | 金句卡（深色底白字） |
| `*图注*`（独占一行） | 居中灰色图注 |
| `![说明](https://...)` | 链接为 http(s) 时渲染**真图**：圆角 `<img>`（12px）嵌在带底色的 section 里。链接用公众号素材库地址（mmbiz.qpic.cn/...），粘贴后图片自带圆角、坐在全文底色上 |
| `![说明](描述)` | 链接非 URL 时为图片位置占位（不内嵌图片） |
| `- 列表` / `1. 列表` | 无序 / 有序列表 |
| `\| 表格 \|` | 转成列表输出（微信对表格兼容差） |
| `---` | 分隔线 |

**分段规则（1.4.0 起）**：每个非空行就是一个段落——不做「空行才分段」的 Markdown 标准合并（真实写作场景里单换行就是想分段，合并会让粘贴后整篇变成一大块）。

段落末尾的中文句号会被去掉（中文排版惯例，避免行尾孤点）。

**给文稿加重点（写稿时就标好，工具负责渲染）**：`==文字==` 橙色下划线、`**文字**` 加粗、`<r>文字</r>` 红字、`<l>文字</l>` 品牌色。每段挑 1 处关键短语标下划线或加粗即可，不要满屏强调。

## 交付前必须自检

```bash
python3 scripts/generate.py article.md --check
```

自检覆盖：`<style>` / class / id / 伪元素 / JS / 外链 / 正文一级标题 / 样式重复声明 / 可见元素缺 inline style / 字面转义残留。有任何一项不通过就不要交付。

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| 粘贴后文字有底色但段落间隙是白色 | 底色层进了但块间 margin 露白（margin 不吃背景）。1.3.0 起 `blockify` 已把 margin 转 padding 并逐块补底色；用 1.3.0+ 重新生成 |
| 粘贴后全文底色丢成白色 | 检查粘贴内容是否是双层包裹（外层牺牲壳 + 内层底色层）。1.2.0 起默认双层包裹；若确认包裹仍在仍丢底色，说明微信清洗规则变了——用 `--page-bg none` 退回白底方案，并把现象记录进 `references/wechat-limits.md` |
| 粘贴后标题/图片出现小方框 | 旧版本用表格做布局会触发此问题（微信把表格转成带边框的表格组件）；用 1.2.0+（无表格布局）重新生成 |
| 粘贴后连正文都变纯文字了 | 内容被 `<div>` 包住了——编辑器白名单没有 `div`，整段会被吞。本技能一律用 `<section>`，不要手改成 `div` |
| 出现两个标题 | 文稿里的首个一级标题被渲染进了正文；确认用的是本技能的生成器 |
| 头部卡片图片塌小/位置不对 | 用 1.6.0+：图片固定 132px 右浮动，不依赖父容器百分比宽度（1.5.x 的分栏百分比宽度会被微信洗掉）。真图务必填素材库 mmbiz 链接，编辑器里手动插图控制不了圆角和位置 |
| 分节编号不对 | 标题已自带编号时（`## 01 标题`）沿用原编号，否则按顺序自动编号 |
| 控制台改了风格但 CI 报红 | `studio.html` 与 `generate.py` 的风格表漂移了；跑 `python3 scripts/check_sync.py` 看差异字段 |

## 参考文件

- `studio.html` — 可视化控制台（单文件、零依赖、双击即开），点按钮调底色/字号/头部卡片并一键复制
- `scripts/generate.py` — 命令行生成器（含 `--check` 合规自检）
- `scripts/check_sync.py` — 校验 `generate.py` 与 `studio.html` 是否漂移（CI 必跑）
- `scripts/test_studio.js` — 控制台真机验证（jsdom 模拟点按钮，需要 `npm i jsdom`）
- `references/install.md` — 安装到 Codex / Claude Code / Cursor / Copilot / WorkBuddy / 豆包 等客户端
- `references/styles.md` — 三种风格的完整 CSS 设计源
- `references/customize.md` — 参数手册、配置文件、新增风格的方法
- `references/wechat-limits.md` — 微信粘贴红线、背景三层真相、已知回落项

## 致谢与边界

排版范式参考中文公众号常见的「卡片笔记」范式（头部信息卡片 + 编号分节 + 强调下划线），只借鉴排版结构，不包含任何第三方品牌资产（logo、专有图、品牌色不作为内置默认）。生成的 HTML 不含外链与远程资源。
