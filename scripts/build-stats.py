#!/usr/bin/env python3
"""GitHub GraphQL API から統計を取り、ピンク配色のカード2枚を生成する。

github-readme-stats の公開インスタンスが長期停止したため、外部サービスに依存せず
自前で描画する。出力は外部参照を持たない自己完結SVGで、配色はピンクと白のみ。

  assets/stats.svg  統計カード
  assets/langs.svg  使用言語カード

環境変数 GITHUB_TOKEN が必要（Actions では secrets.GITHUB_TOKEN、
ローカルでは `GITHUB_TOKEN=$(gh auth token)` で渡す）。
"""

import json
import os
import sys
import urllib.error
import urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "DanGaRa215"
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else "assets"

TOKEN = os.environ.get("GITHUB_TOKEN")

# 言語バーの色。ピンク階調のみ。実際の値は CSS 変数側でテーマごとに定義する
LANG_COLORS = [f"var(--l{i})" for i in range(1, 6)]

# 背景は塗らず、ページの地色を透かす。文字色だけ閲覧者の配色設定に追従させる。
# ダーク側は「最も使われている言語が最も明るい」ように順序を反転している。
STYLE = """  <style>
    svg {
      --head: #D6117E; --text: #B8005E; --value: #D6117E;
      --stripe: #FFF0F7; --track: #FFF0F7; --dot: #FF5FB5;
      --l1: #B8005E; --l2: #D6117E; --l3: #FF6EC7; --l4: #FF9FD3; --l5: #FFCFE7;
    }
    @media (prefers-color-scheme: dark) {
      svg {
        --head: #FF6EC7; --text: #FF9FD3; --value: #FF6EC7;
        --stripe: rgba(255, 95, 181, 0.10); --track: rgba(255, 95, 181, 0.12); --dot: #FF6EC7;
        --l1: #FFCFE7; --l2: #FF9FD3; --l3: #FF6EC7; --l4: #FF5FB5; --l5: #D6117E;
      }
    }
  </style>
"""

CARD_W = 420
CARD_H = 210
PAD = 24

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { totalCommitContributions }
    pullRequests(states: MERGED) { totalCount }
    openIssues: issues(states: OPEN) { totalCount }
    closedIssues: issues(states: CLOSED) { totalCount }
    repositoriesContributedTo(
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
    ) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN が設定されていない")
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USER}-profile-readme",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        raise RuntimeError(f"GraphQL error: {payload['errors']}")
    return payload["data"]


FONT = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"


def card_open(title: str, label: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CARD_W} {CARD_H}" width="{CARD_W}" height="{CARD_H}" role="img" aria-label="{esc(label)}">
  <title>{esc(label)}</title>
{STYLE}
  <rect x="1.5" y="1.5" width="{CARD_W - 3}" height="{CARD_H - 3}" rx="14"
        fill="none" stroke="#FF5FB5" stroke-width="3"/>
  <g stroke="var(--head)" stroke-width="3" stroke-linecap="round" fill="none">
    <path d="M14 34 L14 20 Q14 14 20 14 L40 14"/>
    <path d="M{CARD_W - 40} 14 L{CARD_W - 20} 14 Q{CARD_W - 14} 14 {CARD_W - 14} 20 L{CARD_W - 14} 34"/>
    <path d="M14 {CARD_H - 34} L14 {CARD_H - 20} Q14 {CARD_H - 14} 20 {CARD_H - 14} L40 {CARD_H - 14}"/>
    <path d="M{CARD_W - 40} {CARD_H - 14} L{CARD_W - 20} {CARD_H - 14} Q{CARD_W - 14} {CARD_H - 14} {CARD_W - 14} {CARD_H - 20} L{CARD_W - 14} {CARD_H - 34}"/>
  </g>
  <text x="{PAD}" y="34" font-family="{FONT}" font-size="13" font-weight="700"
        fill="var(--head)" letter-spacing="2.4">{esc(title)}</text>
"""


def build_stats(d: dict) -> str:
    u = d["user"]
    repos = u["repositories"]["nodes"]
    rows = [
        ("Total Stars", sum(n["stargazerCount"] for n in repos)),
        ("Commits (last year)", u["contributionsCollection"]["totalCommitContributions"]),
        ("Pull Requests (merged)", u["pullRequests"]["totalCount"]),
        ("Issues", u["openIssues"]["totalCount"] + u["closedIssues"]["totalCount"]),
        ("Contributed to", u["repositoriesContributedTo"]["totalCount"]),
        ("Followers", u["followers"]["totalCount"]),
    ]

    parts = [card_open("GITHUB STATS", f"{USER} GitHub stats")]
    y = 62
    for i, (name, value) in enumerate(rows):
        # 行を1本おきに淡いピンクで塗り、数字を追いやすくする
        if i % 2 == 0:
            parts.append(
                f'  <rect x="{PAD - 8}" y="{y - 13}" width="{CARD_W - (PAD - 8) * 2}" '
                f'height="22" rx="5" fill="var(--stripe)"/>\n'
            )
        parts.append(
            f'  <circle cx="{PAD + 3}" cy="{y - 4}" r="3" fill="var(--dot)"/>\n'
            f'  <text x="{PAD + 14}" y="{y}" font-family="{FONT}" font-size="13" '
            f'fill="var(--text)">{esc(name)}</text>\n'
            f'  <text x="{CARD_W - PAD}" y="{y}" font-family="{FONT}" font-size="14" '
            f'font-weight="700" fill="var(--value)" text-anchor="end">{value}</text>\n'
        )
        y += 24

    parts.append("</svg>\n")
    return "".join(parts)


def build_langs(d: dict) -> str:
    sizes: dict[str, int] = {}
    for n in d["user"]["repositories"]["nodes"]:
        for e in n["languages"]["edges"]:
            sizes[e["node"]["name"]] = sizes.get(e["node"]["name"], 0) + e["size"]

    if not sizes:
        raise RuntimeError("言語データが空。生成を中止")

    total = sum(sizes.values())
    top = sorted(sizes.items(), key=lambda kv: -kv[1])[: len(LANG_COLORS)]

    parts = [card_open("TOP LANGUAGES", f"{USER} top languages")]

    # 積み上げ横バー。角丸クリップで両端を丸める
    bar_x, bar_y, bar_w, bar_h = PAD, 54, CARD_W - PAD * 2, 12
    parts.append(
        f'  <defs><clipPath id="barClip">'
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6"/>'
        f"</clipPath></defs>\n"
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6" fill="var(--track)"/>\n'
        f'  <g clip-path="url(#barClip)">\n'
    )
    x = float(bar_x)
    for (name, size), color in zip(top, LANG_COLORS):
        seg = bar_w * size / total
        parts.append(
            f'    <rect x="{x:.2f}" y="{bar_y}" width="{seg:.2f}" height="{bar_h}" fill="{color}"/>\n'
        )
        x += seg
    parts.append("  </g>\n")

    y = 96
    for (name, size), color in zip(top, LANG_COLORS):
        pct = size / total * 100
        parts.append(
            # 最も薄い #FFCFE7 は白地だと輪郭が消えるので、全スウォッチに枠線を入れる
            f'  <rect x="{PAD}" y="{y - 9}" width="10" height="10" rx="2.5" fill="{color}"'
            f' stroke="#FF5FB5" stroke-width="0.8"/>\n'
            f'  <text x="{PAD + 18}" y="{y}" font-family="{FONT}" font-size="13" '
            f'fill="var(--text)">{esc(name)}</text>\n'
            f'  <text x="{CARD_W - PAD}" y="{y}" font-family="{FONT}" font-size="13" '
            f'font-weight="700" fill="var(--value)" text-anchor="end">{pct:.1f}%</text>\n'
        )
        y += 22

    parts.append("</svg>\n")
    return "".join(parts)


def main() -> int:
    data = graphql(QUERY, {"login": USER})

    for filename, content in (
        ("stats.svg", build_stats(data)),
        ("langs.svg", build_langs(data)),
    ):
        path = os.path.join(OUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"wrote {path} ({len(content)} bytes)")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (urllib.error.URLError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
