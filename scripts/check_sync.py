#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_sync.py · 保证两套实现不漂移

studio.html（浏览器控制台，JS）和 scripts/generate.py（命令行，Python）是同一套规则的两份实现：
风格 token、Markdown 解析规则、HTML 渲染结果必须一致。否则用户在控制台里看到的排版，
和 AI 用命令行生成的排版会不一样——这是最难排查的一类问题，所以放进 CI 拦住。

做两层校验：
  1. 风格 token 逐项比对（名称、色值、每条 CSS 规则字符串），差异精确到字段；
  2. 用同一篇文章、同一组参数分别渲染，比对最终 HTML 是否一致（需要本机有 node，没有则跳过）。

退出码：0 全部一致；1 存在漂移。
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import generate  # noqa: E402  同目录，直接复用权威定义

STUDIO = os.path.join(ROOT, "studio.html")
SAMPLE = os.path.join(ROOT, "examples", "sample-article.md")

TOKEN_KEYS = ["name", "text", "bg", "muted", "border", "line",
              "accent_fallback", "brand_fallback", "ink_fallback"]
JS_KEYS = ["name", "text", "bg", "muted", "border", "line", "accent", "brand", "ink"]

CUT_MARK = "/* ---------------------------------------------------------------- 状态 */"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def js_engine():
    """从 studio.html 抽出纯渲染部分（状态/UI 之前的部分）。"""
    src = read(STUDIO)
    m = re.search(r"<script>(.*)</script>", src, re.S)
    if not m:
        raise SystemExit("studio.html 里找不到 <script> 块")
    body = m.group(1)
    if CUT_MARK not in body:
        raise SystemExit("studio.html 的脚本结构变了：找不到状态区切分标记 %r" % CUT_MARK)
    return body.split(CUT_MARK)[0]


def js_styles(engine):
    """把 JS 里的 STYLES 表当表达式求值，拿到真实对象（避免用正则解析 JS）。"""
    node = shutil.which("node")
    if not node:
        return None
    m = re.search(r"var STYLES = (\{.*?\n\});", engine, re.S)
    if not m:
        raise SystemExit("studio.html 里找不到 STYLES 定义")
    code = ("var SANS=%s, MONO=%s;\nvar STYLES = %s;\n"
            "process.stdout.write(JSON.stringify(STYLES));"
            % (json.dumps(generate.SANS), json.dumps(generate.MONO), m.group(1)))
    out = subprocess.run([node, "-e", code], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("求值 studio.html 的 STYLES 失败：\n%s" % out.stderr)
    return json.loads(out.stdout)


def norm(html):
    """归一化：只比结构，不比缩进和换行。"""
    return re.sub(r"\s+", " ", html).strip()


def compare_tokens():
    problems = []
    js = js_styles(js_engine())
    if js is None:
        print("  ! 本机没有 node，跳过风格 token 逐项比对（CI 环境会执行）")
        return problems

    py_ids, js_ids = set(generate.STYLES), set(js)
    if py_ids != js_ids:
        problems.append("风格集合不一致：generate.py=%s studio.html=%s"
                        % (sorted(py_ids), sorted(js_ids)))
        return problems

    for sid in sorted(py_ids):
        p, j = generate.STYLES[sid], js[sid]
        for pk, jk in zip(TOKEN_KEYS, JS_KEYS):
            if p.get(pk) != j.get(jk):
                problems.append("[%s] %s 不一致：generate.py=%r studio.html=%r"
                                % (sid, jk, p.get(pk), j.get(jk)))
        pc, jc = set(p.get("css", {})), set(j.get("css", {}))
        if pc != jc:
            problems.append("[%s] CSS 规则集合不一致：仅 py=%s 仅 js=%s"
                            % (sid, sorted(pc - jc), sorted(jc - pc)))
        for key in sorted(pc & jc):
            a = norm(p["css"][key].format(a="#A", b="#B", ink="#K"))
            b = norm(j["css"][key].replace("{a}", "#A").replace("{b}", "#B")
                     .replace("{ink}", "#K"))
            if a != b:
                problems.append("[%s] css.%s 不一致：\n      py: %s\n      js: %s"
                                % (sid, key, a, b))
        for key in ("hl", "red", "num", "brand"):
            a = norm(p["marks"][key].format(t="X", a="#A", b="#B", ink="#K"))
            b = norm(j["marks"][key].replace("{t}", "X").replace("{a}", "#A")
                     .replace("{b}", "#B").replace("{ink}", "#K"))
            if a != b:
                problems.append("[%s] marks.%s 不一致：\n      py: %s\n      js: %s"
                                % (sid, key, a, b))
    return problems


def compare_render():
    """同一篇文章 + 同一组参数，两边渲染结果必须一致。"""
    problems = []
    node = shutil.which("node")
    if not node:
        print("  ! 本机没有 node，跳过渲染结果比对（CI 环境会执行）")
        return problems

    md = read(SAMPLE)
    engine = js_engine()
    driver = """
var UI_T = {md: %s, styleId: "cardnote", bg: "plain", pageBg: "#fafaf4",
  accent: "", brandColor: "", ink: "", bgLine: "#e6e3d8",
  fontSize: 16, lineHeight: 1.9, parts: true, card: true, plainH2: false,
  eyebrow: "NOTES", lead: "", footer: ""};
process.stdout.write(articleHTML(UI_T));
""" % json.dumps(md)

    out = subprocess.run([node, "-e", engine + driver], capture_output=True, text=True)
    if out.returncode != 0:
        problems.append("studio.html 渲染失败：\n%s" % out.stderr.strip()[:800])
        return problems
    js_html = out.stdout

    title, blocks = generate.parse_markdown(md)
    s = generate.STYLES["cardnote"]
    opts = {
        "bg": "plain", "accent": "", "brand_color": "", "bg_color": "",
        "bg_line": "", "page_bg": "auto", "page_bg_image": "", "ink": "",
        "font_size": 16, "line_height": 1.9, "parts": True, "card": generate.DEFAULT_CARD,
        "title": "", "_title": title, "prefer_plain_h2": False, "_sec": 0,
    }
    py_html = generate.render("cardnote", s, blocks, opts)
    start = py_html.find('<section style="background-color:')
    end = py_html.rfind("</section>") + len("</section>")
    py_inner = py_html[start:end]

    if norm(py_inner) != norm(js_html):
        a, b = norm(py_inner), norm(js_html)
        i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
        problems.append("渲染结果不一致（首个差异在第 %d 字符）：\n"
                        "      py: ...%s\n      js: ...%s"
                        % (i, a[max(0, i - 70):i + 90], b[max(0, i - 70):i + 90]))
    return problems


def main():
    print("torchcursor-wechat · 两套实现同步校验")
    problems = []
    print("\n[1/2] 风格 token 逐项比对")
    p1 = compare_tokens()
    print("  ✓ 一致" if not p1 else "  ✗ 发现 %d 处不一致" % len(p1))
    problems += p1
    print("\n[2/2] 渲染结果比对（cardnote / plain）")
    p2 = compare_render()
    print("  ✓ 一致" if not p2 else "  ✗ 发现 %d 处不一致" % len(p2))
    problems += p2

    if problems:
        print("\n同步校验未通过：")
        for p in problems:
            print("  - %s" % p)
        print("\n提示：改风格必须同时改 scripts/generate.py 的 STYLES 与 studio.html 的 STYLES。")
        return 1
    print("\n结论：generate.py 与 studio.html 完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
