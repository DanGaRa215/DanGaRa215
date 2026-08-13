#!/usr/bin/env python3
"""各技術の実ロゴをピンクに着色し、右にラベルを置いたチップ列の SVG を生成する。

shields.io のバッジはロゴが白・地がベタ塗りで、ロゴそのものの形が読み取りにくく、
Skills の各カテゴリが同じ見た目の塊になってしまう。ここではロゴを線画のまま
ピンクで描き、ラベルを横に添える。

ロゴは simple-icons（1パスの 24x24 SVG）から取得し、path の d だけを取り出して
自前の SVG に埋め込む。結果は外部参照ゼロの自己完結SVGになる。

内容は変わらないので日次ワークフローには入れていない。
技術を足したり simple-icons を追随させたいときに手で実行する:

    python3 scripts/build-skills.py
"""

import os
import re
import sys
import urllib.error
import urllib.request

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "assets"

ICON_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg"

# (出力ファイル名, [(ラベル, simple-icons のスラッグ or None)])
# None は「その技術の実ロゴが simple-icons に無い」もの。
# 無関係なブランドのロゴを流用すると誤解を招くので、文字だけのチップにする。
CATEGORIES = [
    ("skills-languages", [
        ("Python", "python"),
        ("SQL", None),               # 言語であり製品ではないのでロゴは無い
    ]),
    ("skills-tools", [
        ("Git", "git"),
        ("GitHub", "github"),
        ("Jupyter", "jupyter"),
        ("Claude Code", "claude"),
        ("Cursor", "cursor"),
    ]),
    ("skills-focus", [
        ("機械学習", None),
        ("自然言語処理", None),
        ("データ可視化", None),
        ("レコメンドシステム", None),
    ]),
]

FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
FONT_SIZE = 14
ICON = 18          # ロゴの一辺
CHIP_H = 38
GAP = 10           # チップ同士の間隔
ROW_GAP = 10
PAD_L = 14         # チップ左端からロゴまで
PAD_R = 16         # ラベル右端からチップ右端まで
ICON_TEXT_GAP = 9
MAX_W = 860        # これを超えたら折り返す

# 14px のヒューマニスト系サンセリフのおおよその字送り（フォントサイズに対する比）。
# 実測できないので、切れるより余るほうを選んで広めに見積もっている。
NARROW = set("iIlj.,:;'|!")
WIDE = set("mMWw@")


def is_fullwidth(ch: str) -> bool:
    """CJK（かな・漢字・全角記号）はラテン文字のおよそ2倍の字送りになる"""
    o = ord(ch)
    return (
        0x3000 <= o <= 0x30FF      # 全角記号・ひらがな・カタカナ
        or 0x3400 <= o <= 0x9FFF   # 漢字
        or 0xFF00 <= o <= 0xFF60   # 全角英数記号
    )


def text_width(s: str) -> float:
    total = 0.0
    for ch in s:
        if is_fullwidth(ch):
            total += 1.02
        elif ch in NARROW:
            total += 0.34
        elif ch in WIDE:
            total += 0.88
        elif ch == " ":
            total += 0.30
        elif ch in "/-":
            total += 0.38
        elif ch.isdigit():
            total += 0.58
        elif ch.isupper():
            total += 0.70
        else:
            total += 0.57
    return total * FONT_SIZE + 2


def fetch_icon_path(slug: str) -> str:
    url = ICON_URL.format(slug=slug)
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-build"})
    with urllib.request.urlopen(req, timeout=30) as r:
        svg = r.read().decode("utf-8")
    m = re.search(r'<path\s+d="([^"]+)"', svg)
    if not m:
        raise RuntimeError(f"{slug}: path が取れない")
    if 'viewBox="0 0 24 24"' not in svg:
        raise RuntimeError(f"{slug}: viewBox が 24x24 でない。拡大率の前提が崩れる")
    return m.group(1)


STYLE = """  <style>
    svg {
      --ink: #D6117E;      /* ロゴとラベル */
      --edge: #FF9FD3;     /* チップの枠 */
    }
    @media (prefers-color-scheme: dark) {
      svg { --ink: #FF6EC7; --edge: #FF5FB5; }
    }
  </style>
"""


def build(name: str, items: list) -> str:
    chips = []
    for label, slug in items:
        d = fetch_icon_path(slug) if slug else None
        w = PAD_L + (ICON + ICON_TEXT_GAP if d else 2) + text_width(label) + PAD_R
        chips.append((label, d, w))

    # 横に並べ、MAX_W を超えたら折り返す
    rows, cur, cur_w = [], [], 0.0
    for chip in chips:
        add = chip[2] + (GAP if cur else 0)
        if cur and cur_w + add > MAX_W:
            rows.append(cur)
            cur, cur_w = [chip], chip[2]
        else:
            cur.append(chip)
            cur_w += add
    if cur:
        rows.append(cur)

    total_w = max(sum(c[2] for c in r) + GAP * (len(r) - 1) for r in rows)
    total_h = len(rows) * CHIP_H + (len(rows) - 1) * ROW_GAP

    labels = ", ".join(c[0] for c in chips)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.0f} {total_h}" '
        f'width="{total_w:.0f}" height="{total_h}" role="img" aria-label="{labels}">\n'
        f"  <title>{labels}</title>\n{STYLE}\n"
    ]

    y = 0
    for row in rows:
        x = 0.0
        for label, d, w in row:
            out.append(
                f'  <g transform="translate({x:.1f}, {y})">\n'
                f'    <rect x="0.75" y="0.75" width="{w - 1.5:.1f}" height="{CHIP_H - 1.5}" '
                f'rx="{(CHIP_H - 1.5) / 2:.1f}" fill="none" stroke="var(--edge)" stroke-width="1.5"/>\n'
            )
            tx = PAD_L
            if d:
                # simple-icons は 24x24 前提なので ICON/24 に縮める
                sc = ICON / 24
                oy = (CHIP_H - ICON) / 2
                out.append(
                    f'    <g transform="translate({PAD_L}, {oy}) scale({sc:.4f})">'
                    f'<path d="{d}" fill="var(--ink)"/></g>\n'
                )
                tx = PAD_L + ICON + ICON_TEXT_GAP
            out.append(
                f'    <text x="{tx}" y="{CHIP_H / 2 + 5:.0f}" font-family="{FONT}" '
                f'font-size="{FONT_SIZE}" font-weight="600" fill="var(--ink)">{label}</text>\n'
                f"  </g>\n"
            )
            x += w + GAP
        y += CHIP_H + ROW_GAP

    out.append("</svg>\n")
    return "".join(out)


def main() -> int:
    for name, items in CATEGORIES:
        svg = build(name, items)
        path = os.path.join(OUT_DIR, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        missing = [l for l, s in items if s is None]
        note = f"  (ロゴ無し: {', '.join(missing)})" if missing else ""
        print(f"wrote {path}  {len(items)} chips{note}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
