# 风格库（CSS 设计源）

本文件是三种风格的**设计源**。CSS 只是源，不是最终产物——生成正式 HTML 时必须按
「微信粘贴兼容性」把每条规则展开到对应元素的 `style` 属性上，并删除 `<style>`、class、id、伪元素。

占位符含义：`{a}` 强调色（`--accent`）、`{b}` 品牌词色（`--brand-color`）、`{ink}` 金句卡底色（`--ink`）。
未指定时取风格自带的 fallback 值。

---

## 一、通用规则（所有风格共享）

1. 正文字号 16px、行高 1.86–1.9，中文长文不牺牲可读性。
2. 字体栈统一系统字体，不引外链字体：
   `-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif`
3. 单色 `background` 统一写 `background-color`。
4. 伪元素装饰改成边框或留白。
5. 不依赖父级继承：每个 `p`/`h2`/`h3`/`blockquote`/`li` 都自带 `font-family`、`font-size`、`line-height`、`color`。

---

## 二、cardnote · 卡片笔记

- 适用：观点长文、认知输出、系列专栏
- 结构（自上而下）：
  1. **头部方框卡片**（细边框 `#c0c1bb`、圆角 6px、**padding 归零**）内含：
     深灰眉题（大字距，11px / `letter-spacing:3px`）→ 左标题（24px / 850，品牌词用 `{b}`）+ 右侧圆角头图（表格两列布局）→ 落款小字（11px 灰）→ **黑底导语条**（`{ink}`，白字 14px，贴左右边框内侧、贴卡片底部，底部圆角 `0 0 5px 5px`）
  2. **编号分节**（两列表格）：左列 `01`（24px/850）+ 下方 `PART`（10px 灰，`letter-spacing:2px`）；右列节标题（21px/850）+ 下方 `NOTES`（10px 灰，`letter-spacing:3px`）
  3. **正文段落** 16px / 1.9 / `#262626`
  4. **关键强调** `==文字==`：加粗 + `border-bottom:3px solid {a}`（不是底色高亮）
  5. **引用块**：深灰左竖线 4px + 浅灰底 `#f0eee8`，块内加粗；局部红字 `#c00000`
  6. **金句卡** `> !文字`：`{ink}` 底 + 白字
- 底色 `#fafaf4`（中性微暖白）；辅助灰 `#6a6b65`；边框 `#c0c1bb`；底纹线 `#e6e3d8`；品牌蓝 `#4a5bc4`；强调橙 `#e0a43c`；墨色 `#1e1f21`

设计意图：暖米白降低长文的白底刺激，头部卡片一次性承载栏目标识，编号分节给长文可导航的骨架；
强调只用下划线，避免大面积色块干扰阅读节奏。

```css
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.9;color:#262626;max-width:740px;margin:0 auto;padding:28px 22px;background-color:#fafaf4;}
h2{font-size:20px;line-height:1.5;font-weight:850;margin:46px 0 16px;color:#1a1a1a;}
h3{font-size:17px;line-height:1.5;font-weight:800;margin:30px 0 10px;color:#1a1a1a;}
p{margin:16px 0;line-height:1.9;}
blockquote{margin:26px 0;padding:16px 18px;border-left:4px solid #3a3a3a;background-color:#f0eee8;color:#1f1f1f;font-weight:700;line-height:1.85;}
ul,ol{margin:14px 0;padding-left:21px;}
li{margin:8px 0;line-height:1.9;}
strong{font-weight:800;color:#111111;}
em{font-style:normal;font-weight:800;color:#111111;border-bottom:3px solid #e0a43c;}
code{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#f0eee8;color:#1a1a1a;padding:2px 6px;border-radius:3px;font-size:14px;}
pre{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#f0eee8;color:#1a1a1a;padding:14px 16px;font-size:14px;line-height:1.6;overflow:auto;}
hr{border:none;border-top:1px solid #ddd8cc;margin:36px 0;}
```

配套组件（生成时展开为行内样式）：

```css
头部卡片{border:1px solid #c0c1bb;border-radius:6px;background-color:#fafaf4;padding:0;}
头部卡片眉题{font-size:11px;line-height:1.6;color:#6a6b65;letter-spacing:3px;padding:18px 18px 0;}
头部卡片标题{font-size:24px;line-height:1.45;font-weight:850;color:#1a1a1a;}
头部卡片落款{font-size:11px;line-height:1.6;color:#6a6b65;letter-spacing:2px;padding:14px 18px 16px;}
黑底导语条{font-size:14px;line-height:1.8;font-weight:600;color:#ffffff;background-color:#1e1f21;padding:14px 18px;border-radius:0 0 5px 5px;}
编号分节{左列 01=24px/850 #1a1a1a + PART=10px #6a6b65 letter-spacing:2px；右列 标题=21px/850 + NOTES=10px #6a6b65 letter-spacing:3px}
金句卡{font-size:16px;line-height:1.9;font-weight:700;color:#ffffff;background-color:#1e1f21;padding:16px 18px;margin:26px 0;}
图注{font-size:11px;line-height:1.6;color:#6a6b65;letter-spacing:2px;text-align:center;}
```

---

## 三、graphite · 石墨工业

- 适用：行业分析、深度判断、B 端内容
- 设计意图：**无彩色系**，靠字重与留白建立层级。工业品场景里"不花哨"本身就是可信度信号。
- 分节标题：左侧 5px 实心竖线 + 上细线，不用色块
- 强调：加粗 + 浅灰底 `#eceeef`；底纹线 `#e8eaec`

```css
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.86;color:#26282b;max-width:740px;margin:0 auto;padding:24px 22px;background-color:#ffffff;}
h2{font-size:19px;line-height:1.46;font-weight:800;margin:44px 0 16px;color:#111315;padding:14px 0 2px 13px;border-left:5px solid #111315;border-top:1px solid #dcdee0;}
h3{font-size:17px;line-height:1.5;font-weight:750;margin:30px 0 10px;color:#33373b;}
p{margin:13px 0;line-height:1.86;}
blockquote{margin:22px 0;padding:14px 16px;border-left:3px solid #6b7075;background-color:#f4f5f6;color:#4a4f54;}
ul,ol{margin:13px 0;padding-left:21px;}
li{margin:8px 0;line-height:1.86;}
strong{font-weight:850;color:#0d0f11;}
em{font-style:normal;background-color:#eceeef;padding:1px 3px;}
code{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#f0f1f2;color:#1a1d1f;padding:2px 6px;border-radius:3px;font-size:14px;}
pre{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#f0f1f2;color:#1a1d1f;padding:14px 16px;font-size:14px;line-height:1.6;overflow:auto;}
hr{border:none;border-top:1px solid #dcdee0;margin:34px 0;}
```

---

## 四、forge · 熔炉橙

- 适用：观点输出、转化文、活动通知
- 设计意图：以橙红为**唯一**强调色（对应工业场景的炉火、警示、能量），底色保持中性白。
  强调色只出现在标题左边框、加粗字、分隔线上，全篇刻意克制，避免转化文变成促销海报。
- 强调色 `#c2410c`（可换品牌色）；浅底 `#fdf3ec`；深底 `#8f2313`；底纹线 `#f4e2d6`

```css
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.86;color:#2a2724;max-width:740px;margin:0 auto;padding:24px 22px;background-color:#ffffff;}
h2{font-size:19px;line-height:1.46;font-weight:800;margin:44px 0 16px;color:#1c1917;padding:13px 14px;background-color:#fdf3ec;border-left:5px solid #c2410c;}
h3{font-size:17px;line-height:1.5;font-weight:800;margin:30px 0 10px;color:#9a3412;padding-bottom:6px;border-bottom:1px dotted #e0c4b1;}
p{margin:13px 0;line-height:1.86;}
blockquote{margin:22px 0;padding:14px 16px;border-left:4px solid #c2410c;background-color:#fdf3ec;color:#5a3a28;}
ul,ol{margin:13px 0;padding-left:21px;}
li{margin:8px 0;line-height:1.86;}
strong{font-weight:850;color:#c2410c;}
em{font-style:normal;color:#9a3412;background-color:#fdf3ec;padding:1px 3px;}
code{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#fdf3ec;color:#9a3412;padding:2px 6px;border-radius:3px;font-size:14px;}
pre{font-family:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;background-color:#fdf3ec;color:#7c2d12;padding:14px 16px;font-size:14px;line-height:1.6;overflow:auto;}
hr{border:none;height:2px;background-color:#c2410c;margin:34px 0;width:56%;}
```

---

## 五、底纹配色（配合 `scripts/make_bg_tile.py`）

| 主题 | 底色 | 线色 | 建议尺寸 |
|---|---|---|---|
| cardnote | `#fafaf4` | `#e6e3d8` | 方格 40 / 横线 32 / 点阵 24 |
| graphite | `#ffffff` | `#e8eaec` | 同上 |
| forge | `#ffffff` | `#f4e2d6` | 同上 |

规则：**线色与底色的明度差控制在 5%–8%**。差太小看不见，差太大底纹会抢正文注意力——底纹的职责是衬托，不是表演。

---

## 六、新增风格

复制任一风格条目，改 `style id`、`name`、`desc`、颜色与字号参数，然后在 `scripts/generate.py` 的 `STYLES` 里加同名字典。骨架元素保持一致：

```
h2 h3 p blockquote callout ul ol li strong em code pre hr
```

`marks` 四类行内标记（`hl` / `red` / `num` / `brand`）必须齐全；若某风格不需要区分颜色，就让它们降级为加粗或纯文本——**不要删键**。
