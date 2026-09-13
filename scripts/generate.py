#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torchcursor-wechat · 把 Markdown 转成可直接粘贴进微信公众号后台的 HTML。

为什么代码要写成这样（决定了所有实现细节）：
  浏览器 Cmd+A / Cmd+C 不会带走 <head><style>，公众号后台还会二次清洗 HTML 和 CSS。
  所以：可见样式必须逐元素展开到 style 属性；禁用 <style>、class、id、伪元素、
  外链资源、JS、hover、position:fixed；不使用只靠父级继承才成立的样式。
  表格在微信里会被转成带边框的表格组件，因此全文禁用 <table>；
  图文并排用 display:inline-block 的并列 <section>（被清洗时优雅退化为堆叠）。

全文底色为什么用「牺牲壳」双层包裹（v1.2.0）：
  公众号编辑器底层是 ProseMirror，白名单里有 <section>、没有 <body> 和 <div>，
  body 上的底色不在复制范围内；div 不在白名单里会连背景整段吞掉。
  实测（2026-09-11 三轮真机验证）得出机制：粘贴时编辑器只丢弃/解包**最外层那一个**
  容器，位于第二层及更深的 section 连同样式会原样保留（1.1.1 里头部卡片的底色
  就是这么活下来的，1.1.0 里被丢弃的只是最外层那一个包裹）。
  所以：最外层放一个不带任何样式的牺牲壳 <section>，真正的底色层放在第二层——
  牺牲壳被吃掉后，底色层升为顶层节点，与头部卡片同级，底色得以保留。
  布局禁用 <table>：微信会把粘贴进来的表格转成自带边框的表格组件（实测标题、
  图片全被框上方框），左右分栏改用 display:inline-block 的并列 <section>——
  即使 display 被清洗也只是退化为上下堆叠，绝不会出现边框。

依赖：仅 Python 3.8+ 标准库。
"""
import argparse
import html as _html
import json
import os
import re
import sys

VERSION = "1.6.1"

SANS = ("-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
        "'Hiragino Sans GB','Microsoft YaHei',sans-serif")
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

# ---------------------------------------------------------------- 风格定义

STYLES = {
    # 卡片笔记：暖米白 + 头部方框卡片（含黑底导语条）+ 编号分节 + 下划线强调
    "cardnote": {
        "name": "卡片笔记",
        "en": "Notecard",
        "desc": "暖米白底、头部卡片、编号分节、下划线强调。适合观点长文、认知输出。",
        "text": "#333333",
        "bg": "#fafaf4",
        "muted": "#6a6b65",
        "border": "#c0c1bb",
        "line": "#e6e3d8",
        "accent_fallback": "#e0a43c",
        "brand_fallback": "#4a5bc4",
        "ink_fallback": "#1e1f21",
        "marks": {
            "hl": ('<em style="font-style:normal;font-weight:800;color:#000000;'
                   'border-bottom:3px solid {a};padding-bottom:1px;">{t}</em>'),
            "red": '<strong style="font-weight:800;color:#c00000;">{t}</strong>',
            "num": '<span style="color:{a};font-weight:800;">{t}</span>',
            "brand": '<span style="color:{b};font-weight:700;">{t}</span>',
        },
        "css": {
            "h2": "font-size:20px;line-height:1.5;font-weight:700;margin:46px 0 16px;color:#262626;",
            "h3": "font-size:17px;line-height:1.5;font-weight:700;margin:30px 0 10px;color:#262626;",
            "p": "margin:16px 0;line-height:1.9;",
            "blockquote": ("margin:26px 0;padding:16px 18px;border-left:4px solid #3a3a3a;"
                           "background-color:#f0eee8;color:#404040;font-weight:700;line-height:1.85;"),
            "callout": ("margin:26px 0;padding:16px 18px;background-color:{ink};"
                        "color:#ffffff;font-weight:700;line-height:1.9;"),
            "ul": "margin:14px 0;padding-left:21px;",
            "ol": "margin:14px 0;padding-left:21px;",
            "li": "margin:8px 0;line-height:1.9;",
            "strong": "font-weight:800;color:#000000;",
            "em": "font-style:normal;font-weight:800;color:#000000;border-bottom:3px solid {a};",
            "code": ("font-family:%s;background-color:#f0eee8;color:#1a1a1a;padding:2px 6px;"
                     "border-radius:3px;font-size:14px;" % MONO),
            "pre": ("font-family:%s;background-color:#f0eee8;color:#1a1a1a;padding:14px 16px;"
                    "font-size:14px;line-height:1.6;overflow:auto;" % MONO),
            "hr": "border:none;border-top:1px solid #ddd8cc;margin:36px 0;",
        },
    },
}

DEFAULT_CARD = {
    "eyebrow": "NOTES",
    "lead": "",
    "footer": "",
    "img": "[ 图片占位 ]",
    "img_url": "",
}

# ---------------------------------------------------------------- Markdown 解析

MARKER_RE = re.compile(r"<(u|r|l|n)>(.*?)</\1>", re.S)


def _strip_tail_period(text):
    return re.sub(r"。$", "", text.strip())


def inline(text, s, accent, brand):
    """行内标记 → 行内样式 HTML。先抽出自定义标记，转义，再回填，避免被 HTML 转义破坏。"""
    hold = {}

    def stash(m):
        key = "\x00%d\x00" % len(hold)
        kind = {"u": "hl", "r": "red", "n": "num", "l": "brand"}[m.group(1)]
        hold[key] = s["marks"][kind].format(t=_html.escape(m.group(2).strip()),
                                            **s["tokens"])
        return key

    text = MARKER_RE.sub(stash, text)

    def stash_eq(m):
        key = "\x00%d\x00" % len(hold)
        hold[key] = s["marks"]["hl"].format(t=_html.escape(m.group(1).strip()),
                                            **s["tokens"])
        return key

    text = re.sub(r"==(.+?)==", stash_eq, text)

    out = _html.escape(text)

    # **粗体** / `代码`
    out = re.sub(r"\*\*(.+?)\*\*",
                 lambda m: '<strong style="%s">%s</strong>'
                           % (s["css"]["strong"].format(**s["tokens"]), m.group(1)),
                 out)
    out = re.sub(r"`([^`]+)`",
                 lambda m: '<code style="%s">%s</code>'
                           % (s["css"]["code"].format(**s["tokens"]), m.group(1)),
                 out)

    for key, val in hold.items():
        out = out.replace(key, val)
    return out


def parse_markdown(md):
    """→ (title, blocks)。blocks 元素为 (kind, payload)。

    分段规则（2026-09-12 按 David 实测反馈调整）：**每个非空行就是一个段落**，
    不做「空行才分段」的 Markdown 标准合并——真实写作场景里单换行就是想分段，
    合并成一段会让粘贴后整篇变成一大块。
    """
    lines = md.replace("\r\n", "\n").split("\n")
    title, blocks, i = None, [], 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            i += 1
            continue

        if line == "---" or line == "***":
            blocks.append(("hr", ""))
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level, text = len(m.group(1)), m.group(2).strip()
            if level == 1 and title is None:
                title = text                      # 首个 H1 → <title>，不进正文
            elif level == 2:
                blocks.append(("h2", text))
            elif level == 3:
                blocks.append(("h3", text))
            else:
                blocks.append(("h3", text))
            i += 1
            continue

        if line.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip().lstrip(">").strip())
                i += 1
            text = " ".join(q for q in quote if q)
            if text.startswith("!"):                 # > !文字  → 金句卡
                blocks.append(("callout", text.lstrip("!").strip()))
            else:
                blocks.append(("quote", text))
            continue

        m = re.match(r"^\*([^*].*?)\*$", line)       # *图注文字* → 居中灰色图注
        if m:
            blocks.append(("figcaption", m.group(1).strip()))
            i += 1
            continue

        if line.startswith("!["):
            cap = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", line)
            if cap and cap.group(2).strip().lower().startswith(("http://", "https://")):
                blocks.append(("img", (cap.group(1).strip(), cap.group(2).strip())))
            else:
                blocks.append(("imgph", (cap.group(1) if cap else "") or "图片"))
            i += 1
            continue

        if re.match(r"^([-*+])\s+", line):
            items = []
            while i < len(lines) and re.match(r"^([-*+])\s+", lines[i].strip()):
                items.append(re.sub(r"^([-*+])\s+", "", lines[i].strip()))
                i += 1
            blocks.append(("ul", items))
            continue

        if re.match(r"^\d+[.)]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+[.)]\s+", "", lines[i].strip()))
                i += 1
            blocks.append(("ol", items))
            continue

        if line.startswith("|") and line.endswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            # 表格在微信里兼容性差，按列表输出（与 dbs-wechat-html 规则一致）
            head = rows[0] if rows else []
            for row in rows[1:]:
                pairs = " ｜ ".join(
                    "%s：%s" % (head[k] if k < len(head) else "", v)
                    for k, v in enumerate(row) if v)
                blocks.append(("li_flat", pairs))
            continue

        text = _strip_tail_period(line)
        if text:
            blocks.append(("p", text))
        i += 1

    return title, blocks


# ---------------------------------------------------------------- HTML 渲染

def _st(s, tag, accent, brand, font_size, line_height):
    """补齐基础样式；元素自身已声明的属性不重复写入（避免 style 里出现重复声明）。"""
    defined = s["css"].get(tag, "").format(**s["tokens"])
    names = {d.split(":")[0].strip() for d in defined.split(";") if ":" in d}
    base = ""
    if "font-family" not in names:
        base += "font-family:%s;" % SANS
    if "font-size" not in names and font_size:
        base += "font-size:%spx;" % font_size
    if "line-height" not in names and line_height:
        base += "line-height:%s;" % line_height
    if "color" not in names:
        base += "color:%s;" % s["text"]
    return base + defined


def _app(style, extra):
    return (style.rstrip(";") + ";" + extra) if extra else style


def _px_half(v):
    """'46px' → 23，'0' → 0。非 px 值按 0 处理（本项目 margin 全是 px 或 0）。"""
    v = v.strip()
    m = re.fullmatch(r"([\d.]+)px", v)
    return int(round(float(m.group(1)) / 2)) if m else 0


def _px_int(v):
    v = v.strip()
    m = re.fullmatch(r"([\d.]+)px", v)
    return int(round(float(m.group(1)))) if m else 0


def blockify(style, bg):
    """全文底色防断裂（v1.3.0 核心）。

    真机实测：底色层进微信后会被摊到每个文字块上，但块与块之间的 margin
    （外边距）不属于任何块——间隙露白。margin 不吃元素背景，padding 吃。
    所以：把垂直 margin 折半转成 padding（折半是因为相邻块的 padding 会
    相加，而原来的 margin 会塌缩），并给没有自己底色的块补上全文底色。
    已有 background-color 的元素（引用块/金句卡）保留原色。

    v1.5.0：所有块强制左右内边距 ≥15px（David 实测反馈：正文贴边太满）。
    微信可能剥掉底色层 wrapper 的 padding，所以左右留白直接写在每个块上，
    保证任何情况下文字离底色边界至少一个字的距离。
    """
    SIDE = 15                          # 左右内边距下限（px），约一个字宽
    has_bg = "background-color" in style
    margin, padding = None, None
    keep = []
    for d in style.split(";"):
        d = d.strip()
        if not d:
            continue
        k, _, v = d.partition(":")
        k, v = k.strip(), v.strip()
        if k == "margin":
            margin = v
        elif k == "padding":
            padding = v
        else:
            keep.append("%s:%s" % (k, v))
    mt = mb = 0
    if margin:
        t = margin.split()
        if len(t) == 1:                       # 上下左右
            mt = mb = _px_half(t[0])
        elif len(t) == 2:                     # 上下 | 左右
            mt = mb = _px_half(t[0])
        elif len(t) == 3:                     # 上 | 左右 | 下
            mt, mb = _px_half(t[0]), _px_half(t[2])
        else:                                 # 上 右 下 左
            mt, mb = _px_half(t[0]), _px_half(t[2])
    pt = pb = pl = pr = 0
    if padding:
        t = padding.split()
        if len(t) == 1:
            pt = pb = pl = pr = _px_int(t[0])
        elif len(t) == 2:
            pt = pb = _px_int(t[0])
            pl = pr = _px_int(t[1])
        elif len(t) == 3:
            pt, pl, pb = _px_int(t[0]), _px_int(t[1]), _px_int(t[2])
        else:
            pt, pr, pb, pl = (_px_int(x) for x in t[:4])
    out = ["margin:0",
           "padding:%dpx %dpx %dpx %dpx" % (mt + pt, max(pr, SIDE), mb + pb, max(pl, SIDE))]
    if not has_bg:
        out.append("background-color:%s" % bg)
    out += keep
    return ";".join(out) + ";"


def part_header(num, sec_title, s, accent, muted, bg, tight=False):
    """编号分节：编号行 + 标题行 + NOTES 行，纯段落堆叠。

    不用表格布局：微信编辑器会把粘贴进来的表格转成自己的表格组件，
    出现边框、列宽错乱（实测 2026-09-11：编号和标题被拉开很远、带边框）。
    普通 <p> 是微信处理得最稳的元素，堆叠布局牺牲左右两列观感换取粘贴保真。
    每行经 blockify 处理：margin 折半转 padding + 补全文底色（防间隙露白）。
    """
    mt, mb = ("22px", "12px") if tight else ("48px", "18px")
    return [
        '  <p style="%s">%s&nbsp;<span style="font-size:10px;'
        'font-weight:600;color:%s;letter-spacing:2px;">PART</span></p>'
        % (blockify('font-family:%s;font-size:24px;line-height:1.2;font-weight:700;'
                    'color:#262626;margin:%s 0 0;' % (SANS, mt), bg),
           num, muted),
        '  <p style="%s">%s</p>'
        % (blockify('font-family:%s;font-size:21px;line-height:1.5;font-weight:700;'
                    'color:#262626;margin:8px 0 0;' % SANS, bg), sec_title),
        '  <p style="%s">NOTES</p>'
        % (blockify('font-family:%s;font-size:10px;line-height:1.5;color:%s;'
                    'letter-spacing:3px;margin:4px 0 %s;' % (SANS, muted, mb), bg),),
    ]


def _card_visual(card, border, muted):
    """头部卡片右侧图片（v1.6.1 按 David 真机反馈第三次调整）：

    v1.6.0 用 float:right 让文字绕排——真机实测微信编辑器不认文字绕排：
    图片被当独立块，标题被挤到图下面。改回 inline-block 双分栏（第三方编辑器
    通用做法，微信粘贴认），图片继续用固定像素宽（v1.6.0 已修的塌小根因：
    百分比宽度会被洗掉）：
    - 固定 160px 宽，任何尺寸原图都渲染成同样大小的圆角缩略图；
    - 圆角 8px（David 反馈 12px 太圆）；真图 height:auto 保比例；
    - 占位框固定 160x96 空盒，删光文字盒子仍在。
    """
    url = (card.get("img_url") or "").strip()
    common = ('display:inline-block;width:160px;max-width:100%%;border-radius:8px;'
              'border:1px solid %s;box-sizing:border-box;vertical-align:middle;'
              % border)
    if url:
        return ('<img src="%s" alt="" style="%sheight:auto;">'
                % (_html.escape(url, quote=True), common))
    return ('<span style="%sheight:96px;line-height:96px;text-align:center;'
            'font-family:%s;font-size:12px;color:%s;">%s</span>'
            % (common, SANS, muted, _html.escape(card.get("img") or "[ 图片占位 ]")))


def head_card(s, opts, accent, brand, muted, border):
    """头部方框卡片：眉题 → 左标题 62% + 右图 38% 双分栏（垂直居中）→ 落款 → 黑底导语条。

    布局不用 <table>（微信转成带边框表格组件）；v1.6.0 试过 float:right 文字绕排，
    真机实测微信不认（图片变独立块、标题被挤到图下面），v1.6.1 改回 inline-block
    双分栏——第三方编辑器（135/壹伴）的图文并排全是这个结构，微信粘贴认。
    图片在分栏里用固定像素宽（v1.5.x 塌小的根因是图片 width:100% 依赖分栏百分比
    宽度，不是分栏本身）。两个分栏必须写在同一行（不能有换行空白），否则
    62%+38% 加上空白节点会被挤到两行。
    """
    ink = opts["ink"]
    card = opts["card"]
    title_txt = opts["title"] or opts["_title"] or "文章标题"
    title_html = inline(title_txt, s, accent, brand)
    p = []
    p.append('<section style="margin:0;border:1px solid %s;border-radius:6px;'
             'background-color:%s;padding:0;">' % (border, opts.get("_page_bg") or s["bg"]))
    if card["eyebrow"]:
        p.append('  <p style="font-family:%s;font-size:11px;line-height:1.6;color:%s;'
                 'letter-spacing:3px;margin:0;padding:18px 18px 0;">%s</p>'
                 % (SANS, muted, _html.escape(card["eyebrow"])))
    p.append(
        '  <section style="margin:0;padding:16px 18px 0;">'
        '<section style="display:inline-block;width:62%%;vertical-align:middle;">'
        '<p style="font-family:%s;font-size:24px;line-height:1.45;font-weight:700;'
        'color:#262626;margin:0;padding-right:8px;">%s</p></section>'
        '<section style="display:inline-block;width:38%%;vertical-align:middle;'
        'text-align:right;">%s</section></section>'
        % (SANS, title_html, _card_visual(card, border, muted)))
    if card["footer"]:
        p.append('  <p style="font-family:%s;font-size:11px;line-height:1.6;color:%s;'
                 'letter-spacing:2px;margin:0;padding:14px 18px 16px;">%s</p>'
                 % (SANS, muted, _html.escape(card["footer"])))
    if card["lead"]:
        lead_html = inline(card["lead"], s, accent, brand)
        p.append('  <p style="font-family:%s;font-size:14px;line-height:1.8;font-weight:600;'
                 'color:#ffffff;background-color:%s;margin:0;padding:14px 18px;'
                 'border-radius:0 0 5px 5px;">%s</p>' % (SANS, ink, lead_html))
    p.append('</section>')
    return p


def render_block(kind, payload, s, opts, accent, brand, muted, line, para_extra):
    fs, lh = opts["font_size"], opts["line_height"]
    bg = opts["_page_bg"]          # 全文底色，blockify 给每个块补上（防间隙露白）

    if kind == "h2":
        if opts["parts"] and payload and not opts["prefer_plain_h2"]:
            m = re.match(r"^(\d+)\s*[.、|｜]?\s*(.*)$", payload)
            if m:
                num, sec = m.group(1), m.group(2)
            else:
                opts["_sec"] = opts.get("_sec", 0) + 1
                num, sec = "%02d" % opts["_sec"], payload
            return part_header(num, _html.escape(sec), s, accent, muted, bg)
        return ['  <h2 style="%s">%s</h2>'
                % (blockify(_st(s, "h2", accent, brand, fs, lh), bg),
                   _html.escape(payload))]

    if kind == "h3":
        return ['  <h3 style="%s">%s</h3>'
                % (blockify(_st(s, "h3", accent, brand, fs, lh), bg),
                   _html.escape(payload))]

    if kind == "p":
        return ['  <p style="%s">%s</p>'
                % (blockify(_app(_st(s, "p", accent, brand, fs, lh), para_extra), bg),
                   inline(payload, s, accent, brand))]

    if kind == "quote":
        return ['  <blockquote style="%s">%s</blockquote>'
                % (blockify(_st(s, "blockquote", accent, brand, fs, lh), bg),
                   inline(payload, s, accent, brand))]

    if kind == "callout":
        return ['  <p style="%s">%s</p>'
                % (blockify(_st(s, "callout", accent, brand, fs, lh), bg),
                   inline(payload, s, accent, brand))]

    if kind == "hr":
        return ['  <hr style="%s">' % blockify(_st(s, "hr", accent, brand, fs, lh), bg)]

    if kind == "img":
        # 真图：圆角 <img> 直接嵌进底色 section（图片 URL 用公众号素材库地址，
        # 粘贴时图片自带圆角、坐在全文底色上，不再是一块突兀的白）。
        # max-width 而非 width:100%（md2wechat 同款写法）：百分比 width 被微信
        # 洗掉时图片塌小，max-width 洗掉也只是回落自然尺寸，不会变小。
        alt, url = payload
        return [
            '  <section style="%s">'
            '<img src="%s" alt="%s" style="display:block;max-width:100%%;'
            'height:auto;border-radius:12px;">'
            '</section>'
            % (blockify('margin:24px 0;', bg),
               _html.escape(url, quote=True), _html.escape(alt)),
        ]

    if kind == "imgph":
        # 图片占位不带边框：参考成品里图片是没有框的，虚线框粘过去会被当成小方框
        return [
            '  <p style="%s">[ 图片：%s ]</p>'
            % (blockify('font-family:%s;font-size:12px;line-height:1.7;color:%s;'
                        'text-align:center;margin:28px 0;' % (SANS, muted), bg),
               _html.escape(payload)),
        ]

    if kind == "figcaption":
        return ['  <p style="%s">%s</p>'
                % (blockify('font-family:%s;font-size:11px;line-height:1.6;color:%s;'
                            'letter-spacing:2px;text-align:center;margin:10px 0 28px;'
                            % (SANS, muted), bg),
                   inline(payload, s, accent, brand))]

    if kind in ("ul", "ol"):
        tag = kind
        out = ['  <%s style="%s">' % (tag, blockify(_st(s, tag, accent, brand, fs, lh), bg))]
        for item in payload:
            out.append('    <li style="%s">%s</li>'
                       % (_st(s, "li", accent, brand, fs, lh),
                          inline(item, s, accent, brand)))
        out.append('  </%s>' % tag)
        return out

    if kind == "li_flat":
        return ['  <p style="%s">%s</p>'
                % (blockify(_app(_st(s, "p", accent, brand, fs, lh), para_extra), bg),
                   inline(payload, s, accent, brand))]

    return []


def render(style_id, s, blocks, opts):
    accent = opts["accent"] or s["accent_fallback"]
    brand = opts["brand_color"] or s["brand_fallback"]
    muted = s["muted"]
    border = s["border"]
    line = s["line"]
    opts["ink"] = opts["ink"] or s["ink_fallback"]

    s = dict(s)
    s["tokens"] = {"a": accent, "b": brand, "ink": opts["ink"]}

    parts = ["<!doctype html>", '<html lang="zh-CN">', "<head>",
             '  <meta charset="utf-8">',
             '  <meta name="viewport" content="width=device-width, initial-scale=1">',
             "  <title>%s</title>" % _html.escape(opts["title"] or opts["_title"] or "微信公众号文章"),
             "</head>"]
    parts.append('<body style="max-width:740px;margin:0 auto;padding:28px 22px;'
                 'background-color:%s;font-family:%s;">' % (opts["bg_color"] or s["bg"], SANS))

    # 全文底色：双层「牺牲壳」包裹（v1.2.0）。
    # 实测机制：粘贴时编辑器只丢弃最外层那一个容器；第二层及更深的 section
    # 连同样式原样保留（头部卡片的底色就是这么活下来的）。
    # 所以最外层放不带样式的牺牲壳，真正的底色层放第二层——壳被吃掉后，
    # 底色层升为顶层节点，底色得以保留。--page-bg none 可关闭包裹。
    page_bg = opts.get("page_bg", "auto")
    if page_bg == "auto":
        page_bg = opts["bg_color"] or s["bg"]
    if not page_bg or str(page_bg).lower() == "none":
        opts["_page_bg"] = s["bg"]          # 不包裹，但卡片仍需要一个有效底色
        page_bg = ""
    else:
        opts["_page_bg"] = page_bg
    wrap_open = False
    if page_bg:
        wrap_style = "background-color:%s;padding:24px 16px;" % page_bg
        parts.append("<section>")              # 牺牲壳：粘贴时会被编辑器丢弃
        parts.append("<section style=\"%s\">" % wrap_style)
        wrap_open = True

    if opts["card"] and s.get("marks"):
        parts += head_card(s, opts, accent, brand, muted, border)
        opts["_sec"] = 0

    for kind, payload in blocks:
        parts += render_block(kind, payload, s, opts, accent, brand, muted, line, "")

    if wrap_open:
        parts.append('</section>')
        parts.append('</section>')

    parts += ["</body>", "</html>", ""]
    return "\n".join(parts)


# ---------------------------------------------------------------- 自检

def self_check(text):
    problems = []
    # <img src> 的 URL 是刻意保留的：只允许公众号素材库图（mmbiz.qpic.cn，微信自家域，
    # 粘贴后正常显示）。其余外链（script/css/@import）仍然违规。
    text_noimg = re.sub(r"<img[^>]*>", "", text)
    img_tags = re.findall(r"<img[^>]*>", text)
    for tag in img_tags:
        if re.search(r'src="https?://', tag) and not re.search(r'src="https?://mmbiz\.qpic\.cn/', tag):
            problems.append("img 引用了非素材库图片（粘贴可能被拦截），请先用公众号素材库转存")
    for pat, label in [
        (r"<style", "<style> 标签"),
        (r'class\s*=', "class 选择器"),
        (r'\sid\s*=', "id 选择器"),
        (r":before|:after", "伪元素"),
        (r"<script", "JavaScript"),
        (r"https?://|@import", "外部资源"),
        (r"<h1[ >]", "正文一级标题（会与后台标题重复）"),
        (r"\\n", "字面 \\n 文本"),
        (r"%%", "字面 %% 文本"),
        (r":\s*;", "空的 CSS 声明（形如 background-color:;）"),
    ]:
        if re.search(pat, text_noimg):
            problems.append("含 %s" % label)

    for m in re.finditer(r'style="([^"]*)"', text):
        props = [d.split(":")[0].strip() for d in m.group(1).split(";") if ":" in d]
        dup = {p for p in props if props.count(p) > 1}
        if dup:
            problems.append("样式重复声明：%s" % ",".join(sorted(dup)))

    for tag in ["p", "h2", "h3", "blockquote", "li"]:
        for m in re.finditer(r"<%s([^>]*)>" % tag, text):
            attrs = m.group(1)
            if attrs.strip().endswith("/"):
                continue
            if 'style="' not in attrs:
                problems.append("<%s> 缺少 inline style" % tag)
                break
    return problems


# ---------------------------------------------------------------- CLI

def load_config(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_opts(args):
    o = {
        "style": "cardnote",
        "accent": "",
        "brand_color": "",
        "bg_color": "",
        "page_bg": "auto",
        "ink": "",
        "font_size": 16,
        "line_height": 1.9,
        "parts": True,
        "card": None,
        "title": "",
        "out": "",
        "prefer_plain_h2": False,
    }
    if args.config:
        cfg = load_config(args.config)
        for key in list(o):
            if key in cfg:
                o[key] = cfg[key]
        o["card"] = dict(DEFAULT_CARD, **(cfg.get("card") or {}))

    for key in ("style", "accent", "brand_color", "bg_color", "ink",
                "page_bg", "font_size", "line_height", "title", "out"):
        val = getattr(args, key, None)
        if val not in (None, ""):
            o[key] = val
    if getattr(args, "no_parts", False):
        o["parts"] = False
    if getattr(args, "no_card", False):
        o["card"] = False
    if getattr(args, "plain_h2", False):
        o["prefer_plain_h2"] = True
    if args.eyebrow is not None or args.lead is not None or args.footer is not None \
            or args.card_img is not None or args.card_img_url is not None:
        card = dict(o["card"] or DEFAULT_CARD)
        if args.eyebrow is not None:
            card["eyebrow"] = args.eyebrow
        if args.lead is not None:
            card["lead"] = args.lead
        if args.footer is not None:
            card["footer"] = args.footer
        if args.card_img is not None:
            card["img"] = args.card_img
        if args.card_img_url is not None:
            card["img_url"] = args.card_img_url
        o["card"] = card
    if o["card"] is None:
        o["card"] = dict(DEFAULT_CARD)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="generate.py",
        description="把 Markdown 转成可粘贴进微信公众号后台的 HTML（torchcursor-wechat v%s）" % VERSION)
    ap.add_argument("input", nargs="?", help="Markdown 文件路径；省略则从 stdin 读取")
    ap.add_argument("--style", choices=list(STYLES) + ["all"], default="cardnote",
                    help="风格（默认 cardnote 卡片笔记）")
    ap.add_argument("--accent", help="强调色，如 #e0a43c")
    ap.add_argument("--brand-color", dest="brand_color", help="品牌词颜色，如 #4a5bc4")
    ap.add_argument("--bg-color", dest="bg_color", help="页面底色，如 #fafaf4")
    ap.add_argument("--page-bg", dest="page_bg",
                    help="全文底色：auto（默认，取风格底色）/ #色值 / none（不包裹）。"
                         "v1.2.0 起用双层牺牲壳包裹：外层空壳被编辑器丢弃，"
                         "第二层底色保留（机制依据 2026-09-11 三轮真机实测）")
    ap.add_argument("--ink", help="金句卡/导语条底色，如 #1e1f21")
    ap.add_argument("--font-size", dest="font_size", type=int, help="正文字号 px（默认 16）")
    ap.add_argument("--line-height", dest="line_height", type=float, help="正文行高（默认 1.9）")
    ap.add_argument("--title", help="覆盖文章标题（默认取文稿首个 # 标题）")
    ap.add_argument("--eyebrow", help="头部卡片眉题")
    ap.add_argument("--lead", help="头部卡片黑底导语条文案")
    ap.add_argument("--footer", help="头部卡片落款")
    ap.add_argument("--card-img", dest="card_img", help="头部卡片图片占位文案")
    ap.add_argument("--card-img-url", dest="card_img_url",
                    help="头部卡片真实图片 URL（建议公众号素材库地址 mmbiz.qpic.cn/...）。"
                         "给了 URL 就渲染真图（圆角+细边框），忽略 --card-img 占位文案")
    ap.add_argument("--no-card", action="store_true", help="不渲染头部卡片")
    ap.add_argument("--no-parts", action="store_true", help="不渲染编号分节，用普通二级标题")
    ap.add_argument("--plain-h2", action="store_true", help="分节标题不用表格两列布局")
    ap.add_argument("--config", help="JSON 配置文件路径")
    ap.add_argument("--out", help="输出目录（默认：输入文件同级的 公众号HTML输出/）")
    ap.add_argument("--check", action="store_true", help="生成后跑微信粘贴合规自检")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            md = f.read()
        stem = os.path.splitext(os.path.basename(args.input))[0]
        base_dir = os.path.dirname(os.path.abspath(args.input))
    else:
        md = sys.stdin.read()
        stem, base_dir = "公众号文章", os.getcwd()

    title, blocks = parse_markdown(md)
    opts = build_opts(args)
    opts["_title"] = title or stem
    out_dir = opts["out"] or os.path.join(base_dir, "公众号HTML输出")
    os.makedirs(out_dir, exist_ok=True)

    style_ids = list(STYLES) if opts["style"] == "all" else [opts["style"]]
    results, all_problems = [], {}

    for sid in style_ids:
        s = STYLES[sid]
        o = dict(opts)
        o["card"] = opts["card"] if sid == "cardnote" else False
        o["_sec"] = 0
        text = render(sid, s, blocks, o)
        fname = "%s_%s.html" % (stem, sid)
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        if args.check:
            all_problems[fname] = self_check(text)
        results.append((sid, s, fname))
        print("生成 %s  %s" % (fname, s["name"]))

    if len(results) > 1:
        cards = "\n".join(
            '<div class="card"><h3>%s <code>%s</code></h3><p>%s</p>'
            '<a href="%s" target="_blank">打开样张 →</a></div>'
            % (s["name"], sid, s["desc"], fname) for sid, s, fname in results)
        idx = ("<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
               "<title>torchcursor-wechat · 风格总览</title><style>"
               "body{font-family:-apple-system,'PingFang SC',sans-serif;max-width:760px;"
               "margin:0 auto;padding:40px 24px;background:#f7f7f8;color:#222}"
               "h1{font-size:22px;margin:0 0 8px}.sub{color:#777;font-size:14px;margin:0 0 28px}"
               ".card{background:#fff;border:1px solid #e3e3e6;border-radius:10px;padding:18px 20px;"
               "margin-bottom:14px}.card h3{margin:0 0 8px;font-size:17px}"
               ".card code{background:#f1f1f3;padding:2px 6px;border-radius:4px;font-size:13px;"
               "color:#444;font-weight:400}.card p{margin:0 0 10px;color:#666;font-size:14px}"
               ".card a{color:#111;font-weight:600;text-decoration:none;border-bottom:1px solid #111;"
               "font-size:14px}</style></head><body>"
               "<h1>torchcursor-wechat · 风格总览</h1>"
               "<p class=\"sub\">底纹 %s ｜ 打开后 Cmd+A 全选 → Cmd+C → 粘贴到公众号后台</p>%s"
               "</body></html>\n") % (opts["bg"], cards)
        with open(os.path.join(out_dir, "00_风格总览_%s.html" % opts["bg"]), "w",
                  encoding="utf-8") as f:
            f.write(idx)
        print("生成 00_风格总览_%s.html" % opts["bg"])

    if args.check:
        print("\n微信粘贴合规自检：")
        bad = 0
        for fname, probs in all_problems.items():
            if probs:
                bad += 1
                print("  ✗ %s" % fname)
                for p in probs[:6]:
                    print("      - %s" % p)
            else:
                print("  ✓ %s" % fname)
        print("  结论：%s" % ("全部通过" if not bad else "%d 个文件有问题" % bad))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
