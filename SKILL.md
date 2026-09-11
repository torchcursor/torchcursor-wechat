---
name: torchcursor-wechat
description: Convert Markdown into WeChat Official Account (公众号) ready-to-paste HTML that keeps its layout after pasting — inline-only styles, no <style>/class/id/pseudo-elements, card-and-notecard layouts, numbered sections, highlight underlines, and ruled/grid paper backgrounds. Use when the user wants 公众号排版, 微信排版, Markdown 转微信 HTML, 把文章做成可粘贴到公众号后台的格式, or needs HTML that survives the WeChat editor's sanitizer (微信公众号粘贴兼容 / 草稿箱 / 排版美化).
license: MIT
metadata:
  version: "1.0.0"
  author: TorchCursor (火把光标)
  language: zh-CN / en
  dependencies: Python 3.8+ (standard library only)
agent_created: true
---

# torchcursor-wechat · 微信公众号 Markdown 排版

把一个 Markdown 文稿转成**在浏览器全选复制、粘贴进微信公众号后台后仍然保持排版**的 HTML。

本技能只做排版，不改观点、不做内容诊断、不润色文案。

## 核心原则（先读这三条，否则做出来的东西在微信里会散架）

1. **浏览器复制不会带走 `<head><style>`**。所以可见样式必须逐元素写在 `style` 属性上，不能依赖 class、id、伪元素或父级继承。
2. **公众号后台会二次清洗 HTML/CSS**。禁用 `<style>`、class、id、`:before/:after`、外链资源、JS、hover、`position:fixed`、渐变、阴影、`background-image`。能用单色、边框、留白表达的，就用它们表达。
3. **正文不重复标题**。文稿首个 `# 一级标题` 只写入 `<title>` 与文件名，不进入正文；否则发布后会出现两个连续标题。

**为什么要自己写解析器和渲染器，而不是手写 HTML**：微信清洗规则是硬约束，靠人工每次注意必然出错；把规则写进代码 + 自检脚本，才能保证每次产出都合规。本技能自带 `scripts/generate.py`（零第三方依赖）与 `--check` 自检。

## 何时使用

- 用户要把写好的一篇文章 / 口播稿 / 长文做成公众号可粘贴的 HTML
- 用户抱怨"排版粘贴到公众号就乱了""样式丢了""底色没了"
- 用户要一条固定栏目视觉（标题卡片、编号分节、强调下划线、横线纸/方格纸底纹）
- 用户要批量生成多个风格让编辑挑选

## 快速开始

```bash
# 单风格
python3 scripts/generate.py article.md --style cardnote

# 全部风格 + 风格总览页
python3 scripts/generate.py article.md --style all --bg plain

# 横线纸 / 方格纸底纹
python3 scripts/generate.py article.md --style cardnote --bg ruled
python3 scripts/generate.py article.md --style cardnote --bg grid

# 用配置文件固定栏目调性（推荐长期使用）
python3 scripts/generate.py article.md --config torchcursor.config.json

# 生成后跑微信粘贴合规自检
python3 scripts/generate.py article.md --style all --check

# 生成可平铺的底纹 PNG（供公众号后台"全文背景"上传）
python3 scripts/make_bg_tile.py --pattern grid --size 40 --theme cardnote --out assets/
```

输出默认写到文稿同级的 `公众号HTML输出/`。生成后告诉用户：打开 HTML → `Cmd+A` 全选 → `Cmd+C` 复制 → 粘贴到公众号后台编辑器 → 用后台预览检查手机端。

## 三种风格

| style id | 名称 | 气质 | 适用 |
|---|---|---|---|
| `cardnote` | 卡片笔记 | 暖米白底 + 头部方框卡片 + 编号分节 + 下划线强调 | 观点长文、认知输出、系列专栏（默认） |
| `graphite` | 石墨工业 | 冷、硬、克制，无彩色 | 行业分析、深度判断、B 端内容 |
| `forge` | 熔炉橙 | 暖、有能量，单一强调色 | 观点输出、转化文、活动通知 |

完整 CSS 设计源见 `references/styles.md`。

## 底纹：必须分两层理解

这是最容易做错的一点，也是本技能区别于普通"Markdown 转 HTML"工具的地方：

| 层 | 做法 | 能否粘贴带入 | 说明 |
|---|---|---|---|
| **结构底纹** | 用行内边框模拟：`ruled` 每段一条细底线；`grid` 分节区块带边框 + 内部段落底线 | 能 | 微信只清洗背景图和复杂 CSS，边框保留 |
| **画面底纹** | 真正的方格/横线纸底图，用 `scripts/make_bg_tile.py` 生成可平铺 PNG | 不能 | 需在公众号编辑器「背景 → 自定义上传」手动设置 |

**不要把 `background-image` 写进生成的 HTML**——它一定会被清洗掉，视觉上等于没写，还给人"我做了底纹"的错觉。要真底纹就生成 PNG + 告诉用户去后台设置。

细节与已知回落项见 `references/wechat-limits.md`。

## 参数速查

| 参数 | 说明 |
|---|---|
| `--style` | `cardnote` / `graphite` / `forge` / `all` |
| `--bg` | `plain` / `ruled` / `grid` |
| `--accent` `--brand-color` `--bg-color` `--bg-line` `--ink` | 强调色 / 品牌词色 / 页面底色 / 底纹线色 / 金句卡底色 |
| `--font-size` `--line-height` | 正文字号（默认 16）、行高（默认 1.9） |
| `--eyebrow` `--lead` `--footer` `--card-img` | 头部卡片眉题 / 黑底导语条 / 落款 / 图片占位文案 |
| `--title` `--no-card` `--no-parts` `--plain-h2` | 覆盖标题 / 关头部卡片 / 关编号分节 / 分节不用表格 |
| `--config` `--out` `--check` | JSON 配置、输出目录、合规自检 |

CLI 优先于配置文件，配置文件优先于内置默认值。完整参数手册与新增风格的方法见 `references/customize.md`。

## Markdown 支持

| 写法 | 结果 |
|---|---|
| 首个 `# 标题` | 只进 `<title>`，不进正文 |
| `## 标题` | 分节；开启 `parts` 时自动编号 `01/02/03…` 并渲染为两列表格分节头 |
| `### 标题` | 三级标题 |
| `**粗体**` / `` `代码` `` | 加粗 / 行内代码 |
| `==文字==` | 关键强调（cardnote 为橙黄粗下划线） |
| `<u>` `<r>` `<l>` `<n>` | 高级行内标记：强调 / 红字 / 品牌词 / 编号 |
| `> 引用` | 引用块 |
| `> !文字` | 金句卡（深色底白字） |
| `*图注*`（独占一行） | 居中灰色图注 |
| `![说明](路径)` | 图片位置占位（不内嵌图片） |
| `- 列表` / `1. 列表` | 无序 / 有序列表 |
| `\| 表格 \|` | 转成列表输出（微信对表格兼容差） |
| `---` | 分隔线 |

段落末尾的中文句号会被去掉（中文排版惯例，避免行尾孤点）。

## 交付前必须自检

```bash
python3 scripts/generate.py article.md --style all --check
```

自检覆盖：`<style>` / class / id / 伪元素 / JS / 外链 / 正文一级标题 / 样式重复声明 / 可见元素缺 inline style / 字面转义残留。有任何一项不通过就不要交付。

## 常见问题

| 现象 | 原因与处理 |
|---|---|
| 粘贴后底色丢成白色 | 页面底色写在 `<body>` 上，后台会回落。要稳定就接受白底，或在后台「背景」里设全文背景色 |
| 底纹没出现 | 用的是画面底纹而非结构底纹；改用 `--bg ruled/grid`，或生成 PNG 去后台设置 |
| 出现两个标题 | 文稿里的首个一级标题被渲染进了正文；确认用的是本技能的生成器 |
| 头部卡片图片位置空着 | 图片是占位框，粘贴后在原位插入图片、删掉占位框 |
| 分节编号不对 | 标题已自带编号时（`## 01 标题`）沿用原编号，否则按顺序自动编号 |

## 参考文件

- `references/styles.md` — 三种风格的完整 CSS 设计源
- `references/customize.md` — 参数手册、配置文件、新增风格的方法
- `references/wechat-limits.md` — 微信粘贴红线、底纹真相、已知回落项

## 致谢与边界

排版范式参考中文公众号常见的「卡片笔记」范式（头部信息卡片 + 编号分节 + 强调下划线），只借鉴排版结构，不包含任何第三方品牌资产（logo、专有图、品牌色不作为内置默认）。生成的 HTML 不含外链与远程资源。
