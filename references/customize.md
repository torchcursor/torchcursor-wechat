# 自定义手册

三种自定义路径，按"改动成本"从低到高排列。选哪种取决于你是临时试色，还是要固定一个栏目的视觉。

| 路径 | 做法 | 成本 | 适合 |
|---|---|---|---|
| A 改参数 | 命令行传参 | 一句话 | 临时试色、单篇特殊 |
| B 配置文件 | 写一份 JSON，长期复用 | 一次性 | 固定栏目调性（推荐） |
| C 新增风格 | 在 `generate.py` 的 `STYLES` 里加一条 | 一次性 | 需要与现有风格明显不同的骨架 |

参数优先级：**命令行 > 配置文件 > 内置默认值**。

---

## A. 可调参数清单

| 参数 | 说明 | 常用值 |
|---|---|---|
| `--style` | 风格（1.5.0 起仅 `cardnote`） | `cardnote` |
| `--bg` | 底纹模式 | `plain` / `ruled` / `grid` |
| `--accent` | 强调色（下划线、编号） | 默认 `#e0a43c` |
| `--brand-color` | 品牌词、链接词颜色 | 默认 `#4a5bc4` |
| `--bg-color` | 页面底色 | `#ffffff` / `#fafaf4` |
| `--bg-line` | 结构底纹线色 | `#e6e3d8` / `#e8eaec` / `#f4e2d6` |
| `--ink` | 金句卡 / 导语条底色 | `#1e1f21` / `#8f2313` |
| `--font-size` | 正文字号 px | 15 / 16 / 17 |
| `--line-height` | 正文行高 | 1.78 ~ 1.95（中文长文别低于 1.8） |
| `--title` | 覆盖标题（默认取文稿首个 `# 标题`） | — |
| `--eyebrow` | 头部卡片眉题（cardnote） | 栏目名 + 分隔号 + 品牌 |
| `--lead` | 头部卡片黑底导语条文案 | 一句话导语 |
| `--footer` | 头部卡片落款 | 账号名 · 定位 |
| `--card-img` | 头部卡片图片占位文案 | `[ 头图占位 ]` |
| `--no-card` | 不渲染头部卡片 | — |
| `--no-parts` | 不渲染编号分节，用普通二级标题 | — |
| `--plain-h2` | 分节标题不用两列表格（编号仍保留） | — |
| `--config` | JSON 配置文件 | — |
| `--out` | 输出目录 | 默认 `<文稿目录>/公众号HTML输出/` |
| `--check` | 生成后跑合规自检（CI 友好，失败返回 1） | — |

配色不是随便挑的：**强调色的明度要与正文形成清晰对比，但饱和度不能压过正文**。工业品/B 端内容优先单色强调，避免多色混用。

---

## B. 配置文件

复制 `examples/torchcursor.config.json` 改成自己的栏目配置：

```json
{
  "style": "cardnote",
  "bg": "plain",
  "accent": "#e0a43c",
  "brand_color": "#4a5bc4",
  "bg_color": "#fafaf4",
  "bg_line": "#e6e3d8",
  "ink": "#1e1f21",
  "font_size": 16,
  "line_height": 1.9,
  "parts": true,
  "card": {
    "eyebrow": "NOTES · 你的品牌",
    "lead": "一句话导语",
    "footer": "账号名 · 定位",
    "img": "[ 图片占位：头图 ]"
  }
}
```

用法：

```bash
python3 scripts/generate.py article.md --config my-column.json
```

单篇需要临时调整时，命令行覆盖即可：

```bash
python3 scripts/generate.py article.md --config my-column.json --bg ruled --font-size 17
```

---

## C. 新增风格

1. 在 `references/styles.md` 追加一节，写清气质、适用、结构、色值、完整 CSS；
2. 在 `scripts/generate.py` 的 `STYLES` 字典里加同名字典，键保持一致：
   `name / en / desc / text / bg / muted / border / line / accent_fallback / brand_fallback / ink_fallback / marks / css`；
3. `marks` 必须包含 `hl`（强调）/ `red`（红字）/ `num`（编号）/ `brand`（品牌词）四键，
   不需要颜色区分时降级为加粗或纯文本，**不要删键**；
4. `css` 至少覆盖 `h2 / h3 / p / blockquote / callout / ul / ol / li / strong / em / code / pre / hr`；
5. 生成样张验证：

```bash
python3 scripts/generate.py examples/sample-article.md --style all --bg plain --check
```

### 骨架元素速查

```
h2 h3 p blockquote callout ul ol li strong em code pre hr
```

`callout` 由 `> !文字` 触发，渲染为 `<p>`；`em` 由 `==文字==` 触发。

---

## D. 与 `dbs-wechat-html` 的关系

本工具的排版规则来源与 `dbs-wechat-html`（15 种欧美媒体风格）一致：逐元素行内样式、禁 `<style>`/class/伪元素、首个 H1 只进 `<title>`、段末中文句号去掉。

区别：
- `dbs-wechat-html` 提供的是**欧美媒体范式**（WIRED / Stripe / FT / Apple 一路）；
- 本工具提供的是**中文公众号原生打法**（头部信息卡片 + 编号分节 + 强调下划线 + 纸感底纹），并额外提供**画面底纹 PNG 生成**与 `--check` 自检。

两个可以并存：欧美范式适合科技、工具类；本工具适合观点长文、B 端、专栏。
