# -*- coding: utf-8 -*-
"""把实施 map 10 个 issue（JSON）渲染成 HTML 汇总页。"""
import json
import html
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent  # skill-levelup/（JSON 所在）


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    in_list = False
    for line in lines:
        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3 class='md-h'>{html.escape(line[2:])}</h3>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3 class='md-h'>{html.escape(line[3:])}</h3>")
        elif line.strip().startswith("- "):
            if not in_list:
                out.append("<ul class='md-ul'>")
                in_list = True
            out.append(f"<li>{html.escape(line.strip()[2:])}</li>")
        elif line.strip().startswith("| "):
            continue  # 表格简化跳过
        elif line.strip().startswith("<!--"):
            continue
        elif line.strip() == "":
            if in_list:
                out.append("</ul>")
                in_list = False
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p class='md-p'>{html.escape(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def load_issues(f: str):
    text = Path(BASE / f).read_text(encoding="utf-8-sig")
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        # PowerShell 数组按行输出：每行一个 JSON 对象
        out = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out


def main():
    issues = []
    for f in ["_issue224.json", "_issues225-233.json"]:
        issues.extend(load_issues(f))
    issues.sort(key=lambda x: x["n"])

    cards = []
    for it in issues:
        cards.append(f"""
        <div class="issue">
          <div class="issue-head">
            <span class="no">#{it['n']}</span>
            <span class="title">{html.escape(it['t'])}</span>
          </div>
          <div class="body">{md_to_html(it['b'])}</div>
          <div class="link"><a href="{html.escape(it['u'])}" target="_blank">{html.escape(it['u'])}</a></div>
        </div>""")

    page = f"""<!DOCTYPE html>
<html lang="zh-Hans">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>实施 MAP 全部 ISSUE · 作息管家</title>
<style>
  :root {{ --bg:#f5f5f7; --card:#fff; --line:#e5e5ea; --text:#1d1d1f; --text2:#515154; --muted:#86868b; --accent:#0071e3; --accent-soft:rgba(0,113,227,.08); --ok:#34c759; --ok-soft:rgba(52,199,89,.12); }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--text); font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','PingFang SC','Microsoft YaHei',sans-serif; font-size:14px; line-height:1.6; -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:48px 20px 80px; }}
  header {{ margin-bottom:26px; }}
  .kicker {{ display:inline-flex; align-items:center; gap:8px; font-size:12px; font-weight:600; letter-spacing:.04em; color:var(--ok); background:var(--ok-soft); padding:5px 14px; border-radius:999px; }}
  h1 {{ font-size:28px; font-weight:700; letter-spacing:-0.01em; margin:14px 0 6px; }}
  .sub {{ color:var(--text2); font-size:14px; }}
  .issue {{ background:var(--card); border-radius:18px; padding:20px 24px; margin-bottom:16px; box-shadow:0 1px 0 rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.05); }}
  .issue-head {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; border-bottom:1px solid var(--line); padding-bottom:10px; }}
  .no {{ flex:none; font-size:13px; font-weight:700; color:var(--accent); background:var(--accent-soft); padding:3px 10px; border-radius:999px; }}
  .title {{ font-size:16px; font-weight:700; }}
  .md-h {{ font-size:14px; font-weight:700; margin:12px 0 6px; color:var(--text); }}
  .md-p {{ font-size:13px; color:var(--text2); margin:4px 0; }}
  .md-ul {{ margin:4px 0 8px 6px; padding-left:20px; }}
  .md-ul li {{ font-size:13px; color:var(--text2); margin:3px 0; }}
  .link {{ margin-top:10px; font-size:11.5px; }}
  .link a {{ color:var(--accent); text-decoration:none; }}
  footer {{ margin-top:30px; text-align:center; color:var(--muted); font-size:12.5px; }}
  @media (max-width:640px) {{ h1 {{ font-size:24px; }} .wrap {{ padding:32px 14px 56px; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="kicker">实施 MAP · 全部 ISSUE</span>
    <h1>10 个 issue（#224-#233）</h1>
    <p class="sub">实施 map #224 + 9 张子票。GitHub 实时源见各 issue 链接。</p>
  </header>
  {''.join(cards)}
  <footer>实施 map · 2026-08-09 · 生成于本地镜像</footer>
</div>
</body>
</html>"""
    out = BASE / "实施map-全部issue.html"
    out.write_text(page, encoding="utf-8")
    print(f"✅ {out}")


if __name__ == "__main__":
    main()
