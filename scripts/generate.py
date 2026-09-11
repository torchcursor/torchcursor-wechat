#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torchcursor-wechat · 把 Markdown 转成可直接粘贴进微信公众号后台的 HTML。

为什么代码要写成这样（决定了所有实现细节）：
  浏览器 Cmd+A / Cmd+C 不会带走 <head><style>，公众号后台还会二次清洗 HTML 和 CSS。
  所以：可见样式必须逐元素展开到 style 属性；禁用 <style>、class、id、伪元素、
  外链资源、JS、hover、position:fixed；不使用只靠父级继承才成立的样式。
  表格在微信里是稳定的图文并排方案，因此用于头部卡片与编号分节。

全文底色为什么必须由外层 <section> 承载：
  公众号编辑器底层是 ProseMirror，白名单里有 <section>、没有 <body> 和 <div>。
  只写在 <body> 上的底色不在复制范围内，粘进去必然消失；用 <div> 包内容更糟——
  div 不在白名单里，连同背景会被整段吞掉，只剩文字。
  所以整篇内容统一包在一个外层 <section> 里，由它承载 background-color。
  这个外层只承载背景，不承载任何文字样式，因此即使被平台清洗掉也不影响正文可读性。

依赖：仅 Python 3.8+ 标准库。
"""
import argparse
import html as _html
import json
import os
import re
import sys

VERSION = "1.1.0"

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
        "text": "#262626",
        "bg": "#fafaf4",
        "muted": "#6a6b65",
        "border": "#c0c1bb",
        "line": "#e6e3d8",
        "accent_fallback": "#e0a43c",
        "brand_fallback": "#4a5bc4",
        "ink_fallback": "#1e1f21",
        "marks": {
            "hl": ('<em style="font-style:normal;font-weight:800;color:#111111;'
                   'border-bottom:3px solid {a};padding-bottom:1px;">{t}</em>'),
            "red": '<strong style="font-weight:800;color:#c00000;">{t}</strong>',
            "num": '<span style="color:{a};font-weight:800;">{t}</span>',
            "brand": '<span style="color:{b};font-weight:700;">{t}</span>',
        },
        "css": {
            "h2": "font-size:20px;line-height:1.5;font-weight:850;margin:46px 0 16px;color:#1a1a1a;",
            "h3": "font-size:17px;line-height:1.5;font-weight:800;margin:30px 0 10px;color:#1a1a1a;",
            "p": "margin:16px 0;line-height:1.9;",
            "blockquote": ("margin:26px 0;padding:16px 18px;border-left:4px solid #3a3a3a;"
                           "background-color:#f0eee8;color:#1f1f1f;font-weight:700;line-height:1.85;"),
            "callout": ("margin:26px 0;padding:16px 18px;background-color:{ink};"
                        "color:#ffffff;font-weight:700;line-height:1.9;"),
            "ul": "margin:14px 0;padding-left:21px;",
            "ol": "margin:14px 0;padding-left:21px;",
            "li": "margin:8px 0;line-height:1.9;",
            "strong": "font-weight:800;color:#111111;",
            "em": "font-style:normal;font-weight:800;color:#111111;border-bottom:3px solid {a};",
            "code": ("font-family:%s;background-color:#f0eee8;color:#1a1a1a;padding:2px 6px;"
                     "border-radius:3px;font-size:14px;" % MONO),
            "pre": ("font-family:%s;background-color:#f0eee8;color:#1a1a1a;padding:14px 16px;"
                    "font-size:14px;line-height:1.6;overflow:auto;" % MONO),
            "hr": "border:none;border-top:1px solid #ddd8cc;margin:36px 0;",
        },
    },
    # 石墨工业：无彩色系，靠字重与留白建立层级
    "graphite": {
        "name": "石墨工业",
        "en": "Graphite",
        "desc": "冷、硬、克制，无彩色。适合行业分析、深度判断、B 端内容。",
        "text": "#26282b",
        "bg": "#ffffff",
        "muted": "#6b7075",
        "border": "#dcdee0",
        "line": "#e8eaec",
        "accent_fallback": "#111315",
        "brand_fallback": "#111315",
        "ink_fallback": "#111315",
        "marks": {
            "hl": '<strong style="font-weight:850;color:#0d0f11;">{t}</strong>',
            "red": '<strong style="font-weight:850;color:#0d0f11;">{t}</strong>',
            "num": "{t}",
            "brand": '<strong style="font-weight:850;color:#0d0f11;">{t}</strong>',
        },
        "css": {
            "h2": ("font-size:19px;line-height:1.46;font-weight:800;margin:44px 0 16px;color:#111315;"
                   "padding:14px 0 2px 13px;border-left:5px solid #111315;border-top:1px solid #dcdee0;"),
            "h3": "font-size:17px;line-height:1.5;font-weight:750;margin:30px 0 10px;color:#33373b;",
            "p": "margin:13px 0;line-height:1.86;",
            "blockquote": ("margin:22px 0;padding:14px 16px;border-left:3px solid #6b7075;"
                           "background-color:#f4f5f6;color:#4a4f54;"),
            "callout": ("margin:22px 0;padding:14px 16px;border-left:3px solid #6b7075;"
                        "background-color:#f4f5f6;color:#111315;font-weight:800;"),
            "ul": "margin:13px 0;padding-left:21px;",
            "ol": "margin:13px 0;padding-left:21px;",
            "li": "margin:8px 0;line-height:1.86;",
            "strong": "font-weight:850;color:#0d0f11;",
            "em": "font-style:normal;background-color:#eceeef;padding:1px 3px;",
            "code": ("font-family:%s;background-color:#f0f1f2;color:#1a1d1f;padding:2px 6px;"
                     "border-radius:3px;font-size:14px;" % MONO),
            "pre": ("font-family:%s;background-color:#f0f1f2;color:#1a1d1f;padding:14px 16px;"
                    "font-size:14px;line-height:1.6;overflow:auto;" % MONO),
            "hr": "border:none;border-top:1px solid #dcdee0;margin:34px 0;",
        },
    },
    # 熔炉橙：橙红为唯一强调色，底色保持中性白
    "forge": {
        "name": "熔炉橙",
        "en": "Forge",
        "desc": "暖、有能量、有警示感，单一强调色。适合观点输出、转化文、活动通知。",
        "text": "#2a2724",
        "bg": "#ffffff",
        "muted": "#7a6a5e",
        "border": "#e7d8cb",
        "line": "#f0e4da",
        "accent_fallback": "#c2410c",
        "brand_fallback": "#9a3412",
        "ink_fallback": "#8f2313",
        "marks": {
            "hl": '<strong style="font-weight:850;color:{a};">{t}</strong>',
            "red": '<strong style="font-weight:850;color:{a};">{t}</strong>',
            "num": "{t}",
            "brand": '<strong style="font-weight:850;color:{b};">{t}</strong>',
        },
        "css": {
            "h2": ("font-size:19px;line-height:1.46;font-weight:800;margin:44px 0 16px;color:#1c1917;"
                   "padding:13px 14px;background-color:#fdf3ec;border-left:5px solid {a};"),
            "h3": ("font-size:17px;line-height:1.5;font-weight:800;margin:30px 0 10px;color:#9a3412;"
                   "padding-bottom:6px;border-bottom:1px dotted #e0c4b1;"),
            "p": "margin:13px 0;line-height:1.86;",
            "blockquote": ("margin:22px 0;padding:14px 16px;border-left:4px solid {a};"
                           "background-color:#fdf3ec;color:#5a3a28;"),
            "callout": "margin:22px 0;padding:14px 16px;background-color:#8f2313;color:#ffffff;font-weight:800;",
            "ul": "margin:13px 0;padding-left:21px;",
            "ol": "margin:13px 0;padding-left:21px;",
            "li": "margin:8px 0;line-height:1.86;",
            "strong": "font-weight:850;color:{a};",
            "em": "font-style:normal;color:#9a3412;background-color:#fdf3ec;padding:1px 3px;",
            "code": ("font-family:%s;background-color:#fdf3ec;color:#9a3412;padding:2px 6px;"
                     "border-radius:3px;font-size:14px;" % MONO),
            "pre": ("font-family:%s;background-color:#fdf3ec;color:#7c2d12;padding:14px 16px;"
                    "font-size:14px;line-height:1.6;overflow:auto;" % MONO),
            "hr": "border:none;height:2px;background-color:{a};margin:34px 0;width:56%;",
        },
    },
}

BG_MODES = {
    "plain": "纯色底（最稳，粘贴后不变形）",
    "ruled": "横线纸：每段一条细底线，模拟笔记本横线（行内边框，粘贴可保留）",
    "grid": "方格纸：分节区块带边框、内部段落带底线，模拟方格分栏（行内边框，粘贴可保留）",
}

DEFAULT_CARD = {
    "eyebrow": "NOTES",
    "lead": "",
    "footer": "",
    "img": "[ 图片占位 ]",
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
    """→ (title, blocks)。blocks 元素为 (kind, payload)。"""
    lines = md.replace("\r\n", "\n").split("\n")
    title, blocks, i = None, [], 0
    buf = []

    def flush_para():
        if buf:
            text = _strip_tail_period(" ".join(buf))
            if text:
                blocks.append(("p", text))
            buf.clear()

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            flush_para()
            i += 1
            continue

        if line == "---" or line == "***":
            flush_para()
            blocks.append(("hr", ""))
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            flush_para()
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
            flush_para()
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
            flush_para()
            blocks.append(("figcaption", m.group(1).strip()))
            i += 1
            continue

        if line.startswith("!["):
            flush_para()
            cap = re.match(r"^!\[(.*?)\]\((.*?)\)", line)
            blocks.append(("imgph", (cap.group(1) or cap.group(2) or "图片").strip()))
            i += 1
            continue

        if re.match(r"^([-*+])\s+", line):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^([-*+])\s+", lines[i].strip()):
                items.append(re.sub(r"^([-*+])\s+", "", lines[i].strip()))
                i += 1
            blocks.append(("ul", items))
            continue

        if re.match(r"^\d+[.)]\s+", line):
            flush_para()
            items = []
            while i < len(lines) and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                items.append(re.sub(r"^\d+[.)]\s+", "", lines[i].strip()))
                i += 1
            blocks.append(("ol", items))
            continue

        if line.startswith("|") and line.endswith("|"):
            flush_para()
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

        buf.append(line)
        i += 1

    flush_para()
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


def part_header(num, sec_title, s, accent, muted, tight=False):
    """编号分节：左列 01 + PART，右列标题 + NOTES（两列表格，微信稳定）。"""
    mt, mb = ("22px", "12px") if tight else ("48px", "18px")
    return [
        '  <table role="presentation" style="width:100%%;border-collapse:collapse;'
        'margin:%s 0 %s;">' % (mt, mb),
        '    <tbody><tr>',
        '      <td style="width:58px;vertical-align:top;padding:2px 0 0;">',
        '        <p style="font-family:%s;font-size:24px;line-height:1.2;font-weight:850;'
        'color:#1a1a1a;margin:0;">%s</p>' % (SANS, num),
        '        <p style="font-family:%s;font-size:10px;line-height:1.5;color:%s;'
        'letter-spacing:2px;margin:2px 0 0;">PART</p>' % (SANS, muted),
        '      </td>',
        '      <td style="vertical-align:middle;padding:0 0 0 10px;">',
        '        <p style="font-family:%s;font-size:21px;line-height:1.5;font-weight:850;'
        'color:#1a1a1a;margin:0;">%s</p>' % (SANS, sec_title),
        '        <p style="font-family:%s;font-size:10px;line-height:1.5;color:%s;'
        'letter-spacing:3px;margin:6px 0 0;">NOTES</p>' % (SANS, muted),
        '      </td>',
        '    </tr></tbody>',
        '  </table>',
    ]


def head_card(s, opts, accent, brand, muted, border):
    """头部方框卡片：眉题 → 左标题右图 → 落款 → 黑底导语条（贴边框内侧贴底）。"""
    ink = opts["ink"]
    card = opts["card"]
    title_txt = opts["title"] or opts["_title"] or "文章标题"
    title_html = inline(title_txt, s, accent, brand)
    p = []
    p.append('<section style="margin:0 0 26px;border:1px solid %s;border-radius:6px;'
             'background-color:%s;padding:0;">' % (border, opts.get("_page_bg") or s["bg"]))
    if card["eyebrow"]:
        p.append('  <p style="font-family:%s;font-size:11px;line-height:1.6;color:%s;'
                 'letter-spacing:3px;margin:0;padding:18px 18px 0;">%s</p>'
                 % (SANS, muted, _html.escape(card["eyebrow"])))
    p.append('  <table role="presentation" style="width:100%;border-collapse:collapse;">')
    p.append('    <tbody><tr>')
    p.append('      <td style="width:64%;vertical-align:middle;padding:16px 14px 0 18px;">')
    p.append('        <p style="font-family:%s;font-size:24px;line-height:1.45;font-weight:850;'
             'color:#1a1a1a;margin:0;">%s</p>' % (SANS, title_html))
    p.append('      </td>')
    p.append('      <td style="width:36%;vertical-align:middle;padding:16px 18px 0 0;">')
    p.append('        <p style="font-family:%s;font-size:12px;line-height:1.7;color:%s;'
             'border:1px dashed %s;border-radius:8px;padding:20px 8px;text-align:center;'
             'margin:0;">%s</p>' % (SANS, muted, border, _html.escape(card["img"])))
    p.append('      </td>')
    p.append('    </tr></tbody>')
    p.append('  </table>')
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

    if kind == "h2":
        if opts["parts"] and payload and not opts["prefer_plain_h2"]:
            m = re.match(r"^(\d+)\s*[.、|｜]?\s*(.*)$", payload)
            if m:
                num, sec = m.group(1), m.group(2)
            else:
                opts["_sec"] = opts.get("_sec", 0) + 1
                num, sec = "%02d" % opts["_sec"], payload
            return part_header(num, _html.escape(sec), s, accent, muted,
                               tight=(opts["bg"] == "grid"))
        return ['  <h2 style="%s">%s</h2>'
                % (_st(s, "h2", accent, brand, fs, lh), _html.escape(payload))]

    if kind == "h3":
        return ['  <h3 style="%s">%s</h3>'
                % (_st(s, "h3", accent, brand, fs, lh), _html.escape(payload))]

    if kind == "p":
        return ['  <p style="%s">%s</p>'
                % (_app(_st(s, "p", accent, brand, fs, lh), para_extra),
                   inline(payload, s, accent, brand))]

    if kind == "quote":
        return ['  <blockquote style="%s">%s</blockquote>'
                % (_st(s, "blockquote", accent, brand, fs, lh),
                   inline(payload, s, accent, brand))]

    if kind == "callout":
        return ['  <p style="%s">%s</p>'
                % (_st(s, "callout", accent, brand, fs, lh),
                   inline(payload, s, accent, brand))]

    if kind == "hr":
        return ['  <hr style="%s">' % _st(s, "hr", accent, brand, fs, lh)]

    if kind == "imgph":
        return [
            '  <p style="font-family:%s;font-size:12px;line-height:1.7;color:%s;'
            'border:1px dashed %s;border-radius:6px;padding:36px 10px;text-align:center;'
            'margin:28px 0 0;">[ 图片：%s ]</p>' % (SANS, muted, line, _html.escape(payload)),
        ]

    if kind == "figcaption":
        return ['  <p style="font-family:%s;font-size:11px;line-height:1.6;color:%s;'
                'letter-spacing:2px;text-align:center;margin:10px 0 28px;">%s</p>'
                % (SANS, muted, inline(payload, s, accent, brand))]

    if kind in ("ul", "ol"):
        tag = kind
        out = ['  <%s style="%s">' % (tag, _st(s, tag, accent, brand, fs, lh))]
        for item in payload:
            out.append('    <li style="%s">%s</li>'
                       % (_st(s, "li", accent, brand, fs, lh),
                          inline(item, s, accent, brand)))
        out.append('  </%s>' % tag)
        return out

    if kind == "li_flat":
        return ['  <p style="%s">%s</p>'
                % (_app(_st(s, "p", accent, brand, fs, lh), para_extra),
                   inline(payload, s, accent, brand))]

    return []


def render(style_id, s, blocks, opts):
    accent = opts["accent"] or s["accent_fallback"]
    brand = opts["brand_color"] or s["brand_fallback"]
    muted = s["muted"]
    border = s["border"]
    line = opts["bg_line"] or s["line"]
    opts["ink"] = opts["ink"] or s["ink_fallback"]

    s = dict(s)
    s["tokens"] = {"a": accent, "b": brand, "ink": opts["ink"]}

    para_extra = ""
    if opts["bg"] in ("ruled", "grid"):
        # 横线纸 / 方格纸都靠行内底边线模拟——微信会清洗 background-image，边框不会
        para_extra = "padding-bottom:12px;border-bottom:1px solid %s;" % line

    parts = ["<!doctype html>", '<html lang="zh-CN">', "<head>",
             '  <meta charset="utf-8">',
             '  <meta name="viewport" content="width=device-width, initial-scale=1">',
             "  <title>%s</title>" % _html.escape(opts["title"] or opts["_title"] or "微信公众号文章"),
             "</head>"]
    parts.append('<body style="max-width:740px;margin:0 auto;padding:28px 22px;'
                 'background-color:%s;font-family:%s;">' % (opts["bg_color"] or s["bg"], SANS))

    # 全文底色由外层 <section> 承载（body 上的底色不在复制范围内，粘不进公众号）
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
        wrap_style = "background-color:%s;" % page_bg
        if opts.get("page_bg_image"):
            wrap_style += ("background-image:url('%s');background-repeat:repeat;"
                           "background-position:top left;" % opts["page_bg_image"])
        parts.append('<section style="%s">' % wrap_style)
        wrap_open = True

    if opts["card"] and s.get("marks"):
        parts += head_card(s, opts, accent, brand, muted, border)
        opts["_sec"] = 0

    # 分组：分节区块（grid 模式按组套边框）
    groups, cur = [], []
    for kind, payload in blocks:
        if kind == "h2" and cur:
            groups.append(cur)
            cur = []
        cur.append((kind, payload))
    if cur:
        groups.append(cur)

    for group in groups:
        wrap = opts["bg"] == "grid"
        if wrap:
            parts.append('<section style="border:1px solid %s;border-radius:6px;'
                         'padding:2px 16px 14px;margin:26px 0;">' % line)
        for kind, payload in group:
            parts += render_block(kind, payload, s, opts, accent, brand, muted, line, para_extra)
        if wrap:
            parts.append('</section>')

    if wrap_open:
        parts.append('</section>')

    parts += ["</body>", "</html>", ""]
    return "\n".join(parts)


# ---------------------------------------------------------------- 自检

def self_check(text):
    problems = []
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
        if re.search(pat, text):
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
        "bg": "plain",
        "accent": "",
        "brand_color": "",
        "bg_color": "",
        "bg_line": "",
        "page_bg": "auto",
        "page_bg_image": "",
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

    for key in ("style", "bg", "accent", "brand_color", "bg_color", "bg_line", "ink",
                "page_bg", "page_bg_image", "font_size", "line_height", "title", "out"):
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
            or args.card_img is not None:
        card = dict(o["card"] or DEFAULT_CARD)
        if args.eyebrow is not None:
            card["eyebrow"] = args.eyebrow
        if args.lead is not None:
            card["lead"] = args.lead
        if args.footer is not None:
            card["footer"] = args.footer
        if args.card_img is not None:
            card["img"] = args.card_img
        o["card"] = card
    if o["card"] is None:
        o["card"] = dict(DEFAULT_CARD)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="generate.py",
        description="把 Markdown 转成可粘贴进微信公众号后台的 HTML（torchcursor-wechat v%s）" % VERSION)
    ap.add_argument("input", nargs="?", help="Markdown 文件路径；省略则从 stdin 读取")
    ap.add_argument("--style", choices=list(STYLES) + ["all"], help="风格，all 表示全部生成")
    ap.add_argument("--bg", choices=list(BG_MODES), help="底纹模式（默认 plain）")
    ap.add_argument("--accent", help="强调色，如 #e0a43c")
    ap.add_argument("--brand-color", dest="brand_color", help="品牌词颜色，如 #4a5bc4")
    ap.add_argument("--bg-color", dest="bg_color", help="页面底色，如 #fafaf4")
    ap.add_argument("--bg-line", dest="bg_line", help="底纹线色，如 #e6e3d8")
    ap.add_argument("--page-bg", dest="page_bg",
                    help="全文底色：auto（跟随风格/--bg-color）/ none / #色值。"
                         "由外层 <section> 承载，粘贴后能保留")
    ap.add_argument("--page-bg-image", dest="page_bg_image",
                    help="全文背景图 URL（可平铺）。注意：公众号可能清洗 background-image，"
                         "保底做法是用 make_bg_tile.py 出图后在后台「背景」里手动上传")
    ap.add_argument("--ink", help="金句卡/导语条底色，如 #1e1f21")
    ap.add_argument("--font-size", dest="font_size", type=int, help="正文字号 px（默认 16）")
    ap.add_argument("--line-height", dest="line_height", type=float, help="正文行高（默认 1.9）")
    ap.add_argument("--title", help="覆盖文章标题（默认取文稿首个 # 标题）")
    ap.add_argument("--eyebrow", help="头部卡片眉题")
    ap.add_argument("--lead", help="头部卡片黑底导语条文案")
    ap.add_argument("--footer", help="头部卡片落款")
    ap.add_argument("--card-img", dest="card_img", help="头部卡片图片占位文案")
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
        fname = "%s_%s_%s.html" % (stem, sid, opts["bg"])
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(text)
        if args.check:
            all_problems[fname] = self_check(text)
        results.append((sid, s, fname))
        print("生成 %s  %s（%s / %s）" % (fname, s["name"], sid, BG_MODES[opts["bg"]].split("：")[0]))

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
