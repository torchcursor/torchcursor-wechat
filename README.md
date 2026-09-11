# torchcursor-wechat

**把 Markdown 转成「粘贴进微信公众号后台后排版还在」的 HTML。**

An Agent Skill + standalone CLI + a single-file browser studio that convert Markdown into WeChat Official Account—ready HTML. Styles are inlined per element so the layout survives the WeChat editor's HTML/CSS sanitizer.

```
Markdown  →  点按钮排版 / 一行命令  →  Cmd+A / Cmd+C  →  粘贴进公众号后台  →  手机端排版完好
```

零第三方依赖（Python 3.8+ 标准库），`studio.html` 连 Python 都不需要，全程不联网、不写入任何远程服务。

---

## 为什么需要它

微信公众号后台是一个很"挑剔"的编辑器：浏览器全选复制**不会带走 `<head><style>`**，后台还会**二次清洗** HTML 和 CSS。大多数 Markdown 转换器生成的 HTML 粘进微信后，标题层级、底色、强调全丢。

这个工具把"微信粘贴规则"写进了生成器和自检脚本：

- 所有可见样式**逐元素展开**到 `style` 属性，不依赖 class / id / 伪元素 / 父级继承
- 生成的 HTML **不含** `<style>`、class、id、`:before/:after`、`<script>`、外链资源、`@import`
- 全文底色由**外层 `<section>`** 承载，能跟着粘进去（写在 `<body>` 上必丢，用 `<div>` 包会被整段吞）
- 文稿首个 `# 标题` 只写入 `<title>`，**不进正文**——避免发布后出现两个标题
- 附带 `--check` 自检：任何一条红线不通过就不交付

## 快速开始

### 方式一：可视化控制台（点按钮）

直接**双击 `studio.html`**（或拖进浏览器）。无需 Python、无需联网、无需安装。

左边点按钮换风格 / 底纹 / 全文底色 / 配色 / 字号行高，右边手机宽度实时预览，点「复制到公众号」再去后台 `Cmd+V` 粘贴即可。

### 方式二：命令行

```bash
git clone https://github.com/torchcursor/torchcursor-wechat.git
cd torchcursor-wechat

python3 scripts/generate.py examples/sample-article.md --style all --config examples/torchcursor.config.json --check
```

打开 `examples/output/00_风格总览_plain.html` 比较风格，然后：

1. 在浏览器打开选定的 HTML
2. `Cmd+A` 全选，`Cmd+C` 复制
3. 粘贴进公众号后台编辑器
4. 用后台预览检查手机端效果

> 两条路是**同一套规则的两份实现**，渲染结果逐字节一致，由 `scripts/check_sync.py` 在 CI 中锁死。

## 三种风格

| style id | 名称 | 气质 | 适用 |
|---|---|---|---|
| `cardnote` | 卡片笔记 | 暖米白底、头部方框卡片、编号分节、下划线强调 | 观点长文、认知输出、系列专栏（默认） |
| `graphite` | 石墨工业 | 冷、硬、克制，无彩色 | 行业分析、深度判断、B 端内容 |
| `forge` | 熔炉橙 | 暖、有能量，单一强调色 | 观点输出、转化文、活动通知 |

## 背景：三层，别搞混

这是本工具和普通 Markdown 转 HTML 最大的差别。

编辑器底层是 ProseMirror，**白名单里有 `<section>`，没有 `<body>` 和 `<div>`**。这一条决定了所有背景规则：

| 层 | 实现 | 能否粘贴带入 | 怎么用 |
|---|---|---|---|
| **全文底色** | 整篇内容包在外层 `<section>` 里，由它带 `background-color` | **能** | 默认开启；`--page-bg auto/#色值/none` |
| **结构底纹** | 行内边框模拟：`ruled` 每段一条细底线（横线纸）；`grid` 分节区块带边框 + 内部段落底线（方格纸） | **能** | `--bg ruled` / `--bg grid` |
| **画面底纹** | 真正可平铺的底纹图 | **不能**，需后台手动设置 | `python3 scripts/make_bg_tile.py --pattern grid --theme cardnote` 生成 PNG，再去公众号后台「背景 → 自定义上传」 |

两个最常见的坑：

- **底色写在 `<body>` 上 = 白写**。body 不在复制范围内，粘过去必然变白底。
- **用 `<div>` 包内容 = 整段被吞**。div 不在白名单，连内容带背景一起消失，表现成"整篇样式全没了"。

本工具一律用 `<section>`，且外层只承载背景、不承载任何文字样式——即使平台丢弃外层容器，正文也不受影响。

**不要指望把 `background-image` 写进 HTML**：微信大概率清洗它。要真底纹就生成 PNG + 后台设置。

```bash
# 生成三种主题的方格 / 横线 / 点阵底纹（平铺图）
python3 scripts/make_bg_tile.py --pattern grid  --size 40 --all-themes --out assets
python3 scripts/make_bg_tile.py --pattern ruled --size 32 --all-themes --out assets
python3 scripts/make_bg_tile.py --pattern dots  --size 24 --theme cardnote --out assets
```

## 常用参数

```bash
# 自定义强调色 / 品牌词色 / 底色 / 线色
python3 scripts/generate.py article.md --accent "#c2410c" --brand-color "#1d4ed8" \
  --bg-color "#fafaf4" --bg-line "#e6e3d8"

# 头部卡片文案（cardnote 风格）
python3 scripts/generate.py article.md --eyebrow "NOTES · 你的品牌" \
  --lead "一句话导语" --footer "你的落款" --card-img "[ 头图占位 ]"

# 字号行高、关掉编号分节 / 头部卡片
python3 scripts/generate.py article.md --font-size 17 --line-height 1.95 --no-parts

# 用配置文件固定栏目调性
python3 scripts/generate.py article.md --config torchcursor.config.json
```

完整参数见 `references/customize.md`。

## 安装到各家 AI 客户端

`SKILL.md` 遵循 [Agent Skills 开放标准](https://github.com/anthropics/skills)——Claude Code、OpenAI Codex CLI、Cursor、GitHub Copilot、Gemini CLI、OpenCode、Roo Code、Windsurf、Trae 等 20+ 客户端都读同一份技能文件。

```bash
# 一句话装到项目（自动识别已安装的客户端）
npx add-skill torchcursor/torchcursor-wechat

# 装到全局，指定客户端
npx add-skill torchcursor/torchcursor-wechat -g -a codex
npx add-skill torchcursor/torchcursor-wechat -g -a claude-code

# 也可以直接把仓库地址丢给 AI，让它自己装
```

手动安装就是把目录放进对应技能目录（`~/.codex/skills/`、`~/.claude/skills/`、`~/.cursor/skills/`、`~/.workbuddy/skills/` …）。各客户端完整目录表、调用方式、以及**豆包能装到什么程度**，见 `references/install.md`。

```bash
# 例：装到 Claude Code 全局
cp -r torchcursor-wechat ~/.claude/skills/
# 例：装到某个项目（随仓库提交，团队共享）
mkdir -p .claude/skills && cp -r torchcursor-wechat .claude/skills/
```

## 目录结构

```
torchcursor-wechat/
├── SKILL.md                    # 技能入口（frontmatter: name / description）
├── studio.html                 # 可视化控制台：点按钮调样式 + 实时预览 + 一键复制
├── README.md
├── CHANGELOG.md
├── LICENSE                     # MIT
├── scripts/
│   ├── generate.py             # Markdown → 微信可粘贴 HTML
│   ├── make_bg_tile.py         # 生成可平铺底纹 PNG（手写 PNG 编码，零依赖）
│   ├── check_sync.py           # 校验 generate.py 与 studio.html 是否漂移（CI 必跑）
│   └── test_studio.js          # 控制台真机验证（jsdom 模拟点按钮）
├── references/
│   ├── install.md              # 安装到各家 AI 客户端
│   ├── styles.md               # 三种风格的完整 CSS 设计源
│   ├── customize.md            # 参数手册 / 配置文件 / 新增风格
│   └── wechat-limits.md        # 微信粘贴红线、背景三层真相、已知回落项
├── examples/
│   ├── sample-article.md
│   ├── torchcursor.config.json
│   └── output/                 # 生成样张（可直接对比）
└── assets/                     # 预生成的底纹 PNG
```

## Markdown 支持速查

| 写法 | 结果 |
|---|---|
| 首个 `# 标题` | 只进 `<title>`，不进正文 |
| `## 标题` | 分节，自动编号 `01/02/03…`（两列表格分节头） |
| `**粗体**` `` `代码` `` `==强调==` | 加粗 / 行内代码 / 关键强调 |
| `> 引用` / `> !金句` | 引用块 / 深色底白字金句卡 |
| `*图注*`（独占一行） | 居中灰色图注 |
| `![说明](路径)` | 图片占位（不内嵌图片） |
| `- 列表` `1. 列表` `---` | 列表 / 分隔线 |
| `<u>` `<r>` `<l>` `<n>` | 高级行内标记：强调 / 红字 / 品牌词 / 编号 |

## English

**torchcursor-wechat** turns Markdown into HTML that keeps its layout after being pasted into the WeChat Official Account (微信公众号) editor.

Why it exists: the WeChat editor strips `<head><style>` on copy and sanitizes the pasted HTML/CSS again. Generic Markdown-to-HTML tools lose headings, backgrounds and emphasis. This tool inlines every visible style per element, forbids `<style>` / class / id / pseudo-elements / external assets, drops the leading `# H1` from the body (so you don't get a duplicated title), and ships a `--check` linter for the paste-safety rules.

Three styles (`cardnote`, `graphite`, `forge`), three background modes (`plain`, `ruled`, `grid`), a page-tint carried by an outer `<section>` (the only element WeChat's ProseMirror whitelist accepts for backgrounds — put it on `<body>` and it is lost; put content in a `<div>` and the whole block gets swallowed), a JSON config for stable column branding, and a dependency-free PNG generator for real tiled paper textures you apply via the editor's own background setting.

Two front ends, one ruleset: a zero-dependency CLI (`scripts/generate.py`) and a single-file browser studio (`studio.html`, double-click to open, click buttons to restyle, live preview, one-click copy). A CI check (`scripts/check_sync.py`) asserts both render byte-identical output.

Requires Python 3.8+ for the CLI. No third-party packages, no network access. `studio.html` needs no runtime at all.

## License

MIT — see [LICENSE](LICENSE).

排版范式参考中文公众号常见的「卡片笔记」结构（信息卡片 + 编号分节 + 强调下划线），只借鉴排版结构，不包含第三方品牌资产。
