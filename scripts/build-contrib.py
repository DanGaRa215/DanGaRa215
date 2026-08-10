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

    # 草のマスが1つも無い = ユーザー名の誤りやサービス側の異常。壊れた図を配ってしまうので止める。
    cells = len(re.findall(r"<rect\b", inner))
    if cells < 300:
        raise RuntimeError(f"草のマスが {cells} 個しかない。生成を中止")

    w = cw + PAD_X * 2
    h = ch + PAD_TOP + PAD_BOTTOM

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{USER} contribution calendar">
  <title>{USER} contribution calendar</title>
  <desc>{cells} cells from {SRC}</desc>

  <defs>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="#FF9FD3"/>
      <stop offset="50%"  stop-color="#D6117E"/>
      <stop offset="100%" stop-color="#FF9FD3"/>
    </linearGradient>
  </defs>

  <!-- 白のカード。草の空セルが #eeeeee、ラベルが #767676 なので、
       ダークテーマでも読めるよう下地は白のまま置く -->
  <rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="14"
        fill="#FFFFFF" stroke="#FF5FB5" stroke-width="3"/>

  <!-- 見出しと、下端のアクセントライン -->
  <text x="{PAD_X}" y="30" font-family="'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
        font-size="13" font-weight="700" fill="#D6117E" letter-spacing="2.4">CONTRIBUTIONS</text>
  <rect x="{PAD_X}" y="{h - 17}" width="{cw}" height="2.5" rx="1.25" fill="url(#edge)"/>

  <!-- 四隅のピンクの飾り -->
  <g stroke="#D6117E" stroke-width="3" stroke-linecap="round" fill="none">
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
