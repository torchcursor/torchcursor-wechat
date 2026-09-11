# Changelog

## 1.0.0 — 2026-09-11

首个版本。

**生成器 `scripts/generate.py`**
- 把 Markdown 转成可粘贴进微信公众号后台的 HTML；零第三方依赖（Python 3.8+ 标准库）
- 三种风格：`cardnote`（卡片笔记）、`graphite`（石墨工业）、`forge`（熔炉橙）
- 三种底纹模式：`plain`（纯色）、`ruled`（横线纸，段落底线）、`grid`（方格纸，分节区块边框 + 段落底线）
- 头部方框卡片（眉题 / 左标题右图 / 落款 / 黑底导语条），用表格实现图文并排
- 编号分节（`01` + `PART` / 标题 + `NOTES` 两列布局），支持 `## 01 标题` 沿用原编号
- 行内标记：`==强调==`、`**粗体**`、`` `代码` ``、`<u>/<r>/<l>/<n>`
- Markdown 支持：H1→标题元信息、H2/H3、引用、`> !金句`、`*图注*`、图片占位、列表、表格转列表、分隔线
- 参数化：强调色 / 品牌词色 / 底色 / 线色 / 金句底色 / 字号 / 行高 / 标题 / 卡片文案 / 编号开关
- JSON 配置文件（`--config`），优先级：命令行 > 配置 > 默认
- `--check` 微信粘贴合规自检（CI 友好，失败返回 1）

**底纹图 `scripts/make_bg_tile.py`**
- 生成可无缝平铺的底纹 PNG（方格 / 横线 / 点阵），手写 PNG 编码，不依赖 Pillow
- 内置三套主题配色，或自定义颜色与尺寸
- 用途：公众号后台「背景 → 自定义上传」设置全文背景（CSS 底纹会被后台清洗，只能这样落地）

**文档**
- `SKILL.md` 遵循 Agent Skills 开放标准（frontmatter `name` / `description`）
- `references/styles.md` 完整 CSS 设计源
- `references/customize.md` 参数手册与新增风格方法
- `references/wechat-limits.md` 微信粘贴红线、底纹真相、已知回落项
- `examples/` 示例文稿、配置文件与生成样张
