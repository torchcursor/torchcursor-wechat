#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
torchcursor-wechat · 底纹图生成器

背景：
  微信公众号后台会清洗 background-image，任何 CSS 画的底纹都带不进正文。
  真正能生效的"画面底纹"，是在公众号编辑器里给全文设置背景图（背景 → 自定义上传）。
  本脚本生成可以无缝平铺的底纹 PNG，供上传使用。

为什么手写 PNG 编码：不引入 Pillow 等依赖，任何装了 Python 3 的机器都能跑。

用法：
  python3 scripts/make_bg_tile.py --pattern grid   --size 40 --color "#e6e3d8" --bg "#fafaf4" --out assets/
  python3 scripts/make_bg_tile.py --pattern ruled  --size 32 --color "#e6e3d8" --bg "#fafaf4" --out assets/
  python3 scripts/make_bg_tile.py --pattern dots   --size 24 --color "#d8d4c8" --bg "#fafaf4" --out assets/
  python3 scripts/make_bg_tile.py --pattern grid --all-themes --out assets/     # 三种主题配色各来一套
"""
import argparse
import os
import struct
import zlib

THEMES = {
    "cardnote": {"bg": "#fafaf4", "line": "#e6e3d8"},
    "graphite": {"bg": "#ffffff", "line": "#e8eaec"},
    "forge":    {"bg": "#ffffff", "line": "#f4e2d6"},
}

PATTERNS = ("grid", "ruled", "dots")


def hex_rgb(value):
    v = value.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def write_png(path, width, height, rows):
    """rows: list[bytes]，每行 RGB 原始字节（长度 = width*3）。"""
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8bit truecolor
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def make_tile(pattern, size, line_rgb, bg_rgb):
    """返回 size×size 的 RGB 行数据；图案按瓦片边界闭合，可无缝平铺。"""
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            px = bg_rgb
            on_line = False
            if pattern == "grid":
                on_line = (x == 0 or y == 0)
            elif pattern == "ruled":
                on_line = (y == 0)
            elif pattern == "dots":
                on_line = (x == 0 and y == 0)
            row += bytes(line_rgb if on_line else px)
        rows.append(bytes(row))
    return rows


def main():
    ap = argparse.ArgumentParser(prog="make_bg_tile.py",
                                description="生成可平铺的公众号全文背景底纹 PNG（零依赖）")
    ap.add_argument("--pattern", choices=PATTERNS, default="grid")
    ap.add_argument("--size", type=int, default=40, help="瓦片边长 px（方格常用 40，横线常用 32）")
    ap.add_argument("--color", help="线条颜色，如 #e6e3d8")
    ap.add_argument("--bg", dest="bg", help="底色，如 #fafaf4；建议与正文底色一致")
    ap.add_argument("--theme", choices=list(THEMES), help="直接用主题配色（cardnote/graphite/forge）")
    ap.add_argument("--all-themes", action="store_true", help="三种主题配色各生成一套")
    ap.add_argument("--out", default="assets", help="输出目录（默认 assets/）")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    jobs = []
    if args.all_themes:
        for name, th in THEMES.items():
            jobs.append((name, th["line"], th["bg"]))
    elif args.theme:
        th = THEMES[args.theme]
        jobs.append((args.theme, args.color or th["line"], args.bg or th["bg"]))
    else:
        line = args.color or THEMES["cardnote"]["line"]
        bg = args.bg or THEMES["cardnote"]["bg"]
        jobs.append(("custom", line, bg))

    for name, line, bg in jobs:
        rows = make_tile(args.pattern, args.size, hex_rgb(line), hex_rgb(bg))
        fname = "bg-%s-%s-%d.png" % (args.pattern, name, args.size)
        path = os.path.join(args.out, fname)
        n = write_png(path, args.size, args.size, rows)
        print("生成 %s  %d×%d  %s on %s  %.1f KB" % (path, args.size, args.size, line, bg, n / 1024))
    print("\n用法：公众号后台 → 图文编辑 → 样式/背景 → 自定义上传背景图 → 选这张 PNG，"
          "平铺方式选「重复」。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
