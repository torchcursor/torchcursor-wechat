# 安装到各家 AI 客户端

本技能按 **Agent Skills 开放标准**（`SKILL.md` + YAML frontmatter）编写，这是一个跨客户端的事实标准：Anthropic 发布格式，Claude Code、OpenAI Codex CLI、Cursor、GitHub Copilot、Gemini CLI、OpenCode、Roo Code、Windsurf、Trae、Goose、Amp、Kiro 等 20+ 客户端都读它。**一份技能文件，到处能跑。**

## 一句话安装（推荐）

```bash
# 装到当前项目（自动识别已安装的客户端）
npx add-skill torchcursor/torchcursor-wechat

# 装到全局（用户级），指定客户端
npx add-skill torchcursor/torchcursor-wechat -g -a codex
npx add-skill torchcursor/torchcursor-wechat -g -a claude-code
npx add-skill torchcursor/torchcursor-wechat -g -a cursor

# 完整 URL 写法（等价）
npx add-skill https://github.com/torchcursor/torchcursor-wechat
```

> 工具新版本已把命令改成 `npx skills add ...`。两者作用相同，用哪个都能装。
> 备选工具：`npx openskills install torchcursor/torchcursor-wechat`

**直接把仓库地址丢给 AI 也能装**——这是本技能的设计意图之一。对 AI 说：

> 从这个仓库安装技能并全局可用：https://github.com/torchcursor/torchcursor-wechat

支持自动安装的客户端，AI 会自己 clone 到对应目录。

## 各客户端技能目录

手动安装时，把整个仓库目录（保证 `SKILL.md` 在该目录根下）复制过去：

| 客户端 | 项目级 | 全局（用户级） |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| OpenAI Codex CLI | `.codex/skills/` | `~/.codex/skills/` |
| Cursor | `.cursor/skills/` | `~/.cursor/skills/` |
| GitHub Copilot / VS Code | `.github/skills/` | `~/.copilot/skills/` |
| Gemini CLI | `.gemini/skills/` | `~/.gemini/skills/` |
| OpenCode | `.opencode/skill/` | `~/.config/opencode/skill/` |
| Roo Code | `.roo/skills/` | `~/.roo/skills/` |
| Windsurf | `.windsurf/skills/` | `~/.codeium/windsurf/skills/` |
| Trae | `.trae/skills/` | `~/.trae/skills/` |
| **WorkBuddy** | `.workbuddy/skills/` | `~/.workbuddy/skills/` |

```bash
# 例：手动装到 Codex CLI
git clone https://github.com/torchcursor/torchcursor-wechat ~/.codex/skills/torchcursor-wechat

# 例：手动装到 WorkBuddy
git clone https://github.com/torchcursor/torchcursor-wechat ~/.workbuddy/skills/torchcursor-wechat

# 例：装到当前项目（团队共享，随仓库提交）
mkdir -p .claude/skills && cp -r torchcursor-wechat .claude/skills/
```

注意：`name` 必须与目录名一致（本技能 `name: torchcursor-wechat`），否则部分客户端加载器找不到它。

## 在对话里怎么调用

| 客户端 | 调用方式 |
|---|---|
| 支持斜杠命令的客户端 | 输入 `/`，从列表里选 `torchcursor-wechat`（如 WorkBuddy 输入斜杠即弹出已装技能） |
| 只按描述自动触发的客户端 | 直接说人话："用 torchcursor-wechat 把这篇排版"、"帮我把这篇文章排成公众号格式" |
| WorkBuddy / 豆包工作 | 也支持把技能压缩包**直接拖进对话窗口**自动安装 |

## 豆包（Doubao）：能装，但装不全

如实说明差异，避免让人白折腾：

- **豆包电脑版支持「技能」**：侧栏「技能 · 连接器 · 伙伴」→ 新建技能 → 把 `SKILL.md` 全文粘进技能正文。网页版不能稳定创建技能。
- **但豆包读不到你本地的 `scripts/`**：它的技能本质是一段长期指令，不是本地运行时。所以：
  - ✅ 排版**规范**能生效（它会按本技能的风格与红线帮你手工产出 HTML）
  - ❌ `generate.py` **跑不起来**，产出的合规性没有 `--check` 兜底
- **要完整能力，用能跑本地命令的客户端**（Claude Code / Codex CLI / Cursor / WorkBuddy）。

同类情况：纯云端聊天产品（网页版豆包、文心、通义）都无法直接加载本地技能目录，只能把 SKILL.md 内容当提示词用。

## 需要什么运行时

| 部分 | 依赖 |
|---|---|
| `studio.html` | **无**。单文件，浏览器双击即用，可离线 |
| `scripts/generate.py` | Python 3.8+，**仅标准库**，无需 pip install |
| `scripts/check_sync.py` / `test_studio.js` | Node.js（仅开发者与 CI 需要；`test_studio.js` 另需 `npm i jsdom`） |

## 验证装好了

```bash
python3 ~/.codex/skills/torchcursor-wechat/scripts/generate.py --version
# 应输出 1.1.0

python3 ~/.codex/skills/torchcursor-wechat/scripts/generate.py \
  ~/.codex/skills/torchcursor-wechat/examples/sample-article.md --style all --check
# 全部通过即可用
```
