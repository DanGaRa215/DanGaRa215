#!/usr/bin/env python3
"""GitHub の緑のコントリビューションカレンダーをピンクの枠に収めた SVG を生成する。

ghchart.rshah.org が返す SVG は <rect> と <text> のフラットな並びなので、
その中身をそのまま自作フレームの中に <g> で取り込む。
出力は外部参照を一切持たない自己完結SVGになるため、
GitHub が <img> として描画してもそのまま表示でき、
ghchart が落ちても README は壊れない。
"""

import re
import sys
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "DanGaRa215"
OUT = sys.argv[2] if len(sys.argv) > 2 else "assets/contrib.svg"

SRC = f"https://ghchart.rshah.org/{USER}"

PAD_X = 26      # 草の左右の余白
PAD_TOP = 44    # 見出し行のぶん上を広めに取る
PAD_BOTTOM = 26

# ghchart が inline style で持つ色 -> CSS 変数
COLOR_VARS = {
    "fill:#eeeeee": "--c0",   # 空セル
    "fill:#c6e48b": "--c1",
    "fill:#7bc96f": "--c2",
    "fill:#239a3b": "--c3",
    "fill:#196127": "--c4",
    "fill:#767676": "--lbl",  # 月・曜日ラベル
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": f"{USER}-profile-readme"})
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status != 200:
            raise RuntimeError(f"{url} returned HTTP {r.status}")
        return r.read().decode("utf-8")


def main() -> int:
    raw = fetch(SRC)

    m = re.search(r"<svg\b[^>]*>", raw)
    if not m:
        raise RuntimeError("ghchart のレスポンスに <svg> が見つからない")
    open_tag = m.group(0)

    def dim(name: str) -> int:
        d = re.search(rf'{name}="(\d+(?:\.\d+)?)"', open_tag)
        if not d:
            raise RuntimeError(f"<svg> に {name} 属性がない")
        return round(float(d.group(1)))

    cw, ch = dim("width"), dim("height")

    inner = raw[m.end():]
    inner = inner[: inner.rindex("</svg>")].strip()

    # ghchart は色を inline style で持つ。inline style は外部ルールより強いので
    # クラスでは上書きできない。色リテラルを CSS 変数に置き換えることで、
    # prefers-color-scheme でライト/ダークを切り替えられるようにする。
    for literal, var in COLOR_VARS.items():
        if literal not in inner:
            raise RuntimeError(f"ghchart の配色が変わっている: {literal} が見つからない")
        inner = inner.replace(literal, f"fill:var({var})")

    # 草のマスが1つも無い = ユーザー名の誤りやサービス側の異常。壊れた図を配ってしまうので止める。
    cells = len(re.findall(r"<rect\b", inner))
    if cells < 300:
        raise RuntimeError(f"草のマスが {cells} 個しかない。生成を中止")

    w = cw + PAD_X * 2
    h = ch + PAD_TOP + PAD_BOTTOM

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{USER} contribution calendar">
  <title>{USER} contribution calendar</title>
  <desc>{cells} cells from {SRC}</desc>

  <style>
    /* ライト時は GitHub 従来の緑階調そのまま。ダーク時は GitHub のダークテーマと同じ緑に差し替える。
       閲覧者の OS/ブラウザの配色設定に追従する */
    svg {{
      --c0: #eeeeee; --c1: #c6e48b; --c2: #7bc96f; --c3: #239a3b; --c4: #196127;
      --lbl: #767676; --head: #D6117E;
    }}
    @media (prefers-color-scheme: dark) {{
      svg {{
        --c0: #161b22; --c1: #0e4429; --c2: #006d32; --c3: #26a641; --c4: #39d353;
        --lbl: #8b949e; --head: #FF6EC7;
      }}
    }}
  </style>

  <!-- 背景は塗らない。ページの地色（ダークなら黒、ライトなら白）がそのまま透ける -->
  <rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="14"
        fill="none" stroke="#FF5FB5" stroke-width="3"/>

  <text x="{PAD_X}" y="30" font-family="'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
        font-size="13" font-weight="700" fill="var(--head)" letter-spacing="2.4">CONTRIBUTIONS</text>

  <!-- 四隅のピンクの飾り -->
  <g stroke="var(--head)" stroke-width="3" stroke-linecap="round" fill="none">
    <path d="M14 {PAD_TOP - 8} L14 20 Q14 14 20 14 L44 14"/>
    <path d="M{w - 44} 14 L{w - 20} 14 Q{w - 14} 14 {w - 14} 20 L{w - 14} {PAD_TOP - 8}"/>
    <path d="M14 {h - PAD_BOTTOM + 4} L14 {h - 20} Q14 {h - 14} 20 {h - 14} L44 {h - 14}"/>
    <path d="M{w - 44} {h - 14} L{w - 20} {h - 14} Q{w - 14} {h - 14} {w - 14} {h - 20} L{w - 14} {h - PAD_BOTTOM + 4}"/>
  </g>

  <!-- ghchart から取り込んだ緑の草。色は GitHub 純正の階調そのまま -->
  <g transform="translate({PAD_X}, {PAD_TOP})">
{inner}
  </g>
</svg>
"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"wrote {OUT}  ({w}x{h}, {cells} cells from {SRC})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
