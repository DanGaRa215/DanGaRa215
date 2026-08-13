#!/usr/bin/env python3
"""GitHub の緑のコントリビューションカレンダーをピンクの枠に収め、
流れ星が草を食べながら進むアニメーションを付けた SVG を生成する。

ghchart.rshah.org が返す SVG からマス目の座標とスコアを読み取り、
自前で描き直している（ghchart の中身をそのまま埋めると、マス単位で
アニメーションを当てられないため）。月・曜日のラベルだけは元の要素を流用する。

流れ星は Platane/snk の蛇と同じく行を往復する経路をたどり、
通過したマスがそのタイミングで消える。1周の最後にまとめて生え直す。

出力は外部参照を持たない自己完結SVGなので、GitHub が <img> として描画しても
そのまま表示でき、ghchart が落ちても README は壊れない。
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

DUR = 24                # 1周の秒数
TRAVEL = 0.90           # このぶんだけ移動に使い、残りで草を生え直す
EAT = 0.005             # 1マスが消えるまでの時間（周期に対する比）
REGROW = 0.95           # ここから生え直しを始める

# ghchart の色 -> スコア段階。CSS 変数に置き換えてテーマ切り替えできるようにする
SCORE_COLORS = {
    0: "var(--c0)",
    1: "var(--c1)",
    2: "var(--c2)",
    3: "var(--c3)",
    4: "var(--c4)",
}

CELL_RE = re.compile(
    r'<rect style="fill:(#[0-9a-f]{6})[^"]*"\s+data-score="(\d+)"\s+data-date="([\d-]+)"'
    r'\s+x="([\d.]+)"\s+y="([\d.]+)"\s+width="([\d.]+)"\s+height="([\d.]+)"'
)


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

    cells = CELL_RE.findall(raw)
    if len(cells) < 300:
        raise RuntimeError(f"マスが {len(cells)} 個しか取れない。ghchart の書式が変わった可能性")

    # (列, 行) -> (スコア, x, y)
    xs = sorted({float(c[3]) for c in cells})
    ys = sorted({float(c[4]) for c in cells})
    col_of = {x: i for i, x in enumerate(xs)}
    row_of = {y: i for i, y in enumerate(ys)}
    size = float(cells[0][5])

    grid = {}
    for _, score, date, x, y, _w, _h in cells:
        grid[(col_of[float(x)], row_of[float(y)])] = (int(score), float(x), float(y), date)

    n_col, n_row = len(xs), len(ys)

    # 行ごとに左右へ折り返す蛇行経路。全マスを等間隔でたどるので、
    # 経路上の距離と通過順が線形に対応する
    order = []
    for r in range(n_row):
        cols = range(n_col) if r % 2 == 0 else range(n_col - 1, -1, -1)
        for c in cols:
            order.append((c, r))
    steps = len(order)

    def center(col: int, row: int) -> tuple:
        return (xs[0] + col * (xs[1] - xs[0]) + size / 2,
                ys[0] + row * (ys[1] - ys[0]) + size / 2)

    path = "M " + " L ".join(f"{cx:.1f} {cy:.1f}" for cx, cy in (center(c, r) for c, r in order))

    # 月・曜日のラベルは元の要素をそのまま使う（色だけ変数化）
    labels = re.findall(r"<text\b.*?</text>", raw, re.S)
    labels = [t.replace("fill:#767676", "fill:var(--lbl)") for t in labels]

    w = cw + PAD_X * 2
    h = ch + PAD_TOP + PAD_BOTTOM

    empty, filled = [], []
    for i, (c, r) in enumerate(order):
        if (c, r) not in grid:
            continue
        score, x, y, date = grid[(c, r)]
        empty.append(
            f'<rect x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" rx="2" fill="var(--c0)"/>'
        )
        if score == 0:
            continue
        # この星が通過する瞬間に消え、周回の終わりに生え直す
        t = TRAVEL * i / (steps - 1)
        t2 = min(t + EAT, REGROW - 0.001)
        filled.append(
            f'<rect x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" rx="2" '
            f'fill="{SCORE_COLORS[score]}">'
            f'<animate attributeName="opacity" values="1;1;0;0;1" '
            f'keyTimes="0;{t:.4f};{t2:.4f};{REGROW};1" dur="{DUR}s" repeatCount="indefinite"/>'
            f"</rect>"
        )

    nl = "\n      "
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{USER} contribution calendar">
  <title>{USER} contribution calendar</title>
  <desc>{len(cells)} cells from {SRC}</desc>

  <style>
    /* ライト時は GitHub 従来の緑階調そのまま。ダーク時は GitHub のダークテーマと同じ緑に差し替える。
       閲覧者の OS/ブラウザの配色設定に追従する */
    svg {{
      --c0: #eeeeee; --c1: #c6e48b; --c2: #7bc96f; --c3: #239a3b; --c4: #196127;
      --lbl: #767676; --head: #D6117E; --star: #D6117E;
    }}
    @media (prefers-color-scheme: dark) {{
      svg {{
        --c0: #161b22; --c1: #0e4429; --c2: #006d32; --c3: #26a641; --c4: #39d353;
        --lbl: #8b949e; --head: #FF6EC7; --star: #FF6EC7;
      }}
    }}
  </style>

  <defs>
    <linearGradient id="trail" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="-34" y2="0">
      <stop offset="0%"   stop-color="#D6117E" stop-opacity="0.95"/>
      <stop offset="45%"  stop-color="#FF5FB5" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#FF9FD3" stop-opacity="0"/>
    </linearGradient>
  </defs>

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

  <g transform="translate({PAD_X}, {PAD_TOP})">
    <!-- 空のマス。食べられた後もここが残るので穴が空いて見えない -->
    <g>
      {nl.join(empty)}
    </g>

    <!-- 草。色は GitHub 純正の階調そのまま -->
    <g>
      {nl.join(filled)}
    </g>

    {nl.join(labels)}

    <!-- 流れ星。rotate="auto" で進行方向を向くので、折り返しても尾が必ず後ろに伸びる -->
    <g>
      <g transform="rotate(180)">
        <path d="M0 0 L-34 0" stroke="url(#trail)" stroke-width="3.4" stroke-linecap="round"/>
        <circle r="3.4" fill="var(--star)"/>
        <circle r="1.5" fill="#FFFFFF"/>
      </g>
      <animateMotion dur="{DUR}s" repeatCount="indefinite" rotate="auto"
                     calcMode="linear" keyPoints="0;1;1" keyTimes="0;{TRAVEL};1"
                     path="{path}"/>
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{TRAVEL};{TRAVEL + 0.02};1"
               dur="{DUR}s" repeatCount="indefinite"/>
    </g>
  </g>
</svg>
"""

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)

    lit = sum(1 for c in cells if int(c[1]) > 0)
    print(f"wrote {OUT}  ({w}x{h}, {len(cells)} cells / {lit} lit, {steps} steps, {DUR}s loop)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
