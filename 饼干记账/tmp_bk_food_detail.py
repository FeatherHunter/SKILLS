# -*- coding: utf-8 -*-
"""
按日聚合 8/11-8/14 饼干记账的食物记录,生成 HTML 比对表
- 含每笔金额/分类/账户/店铺/备注
- 让用户对照估算克数和热量
"""
import json, subprocess, sys

r = subprocess.run(
    ['python', 'scripts/query/cli.py', 'list',
     '--from', '2026-08-11', '--to', '2026-08-14',
     '--type', 'expense', '--json'],
    capture_output=True, text=True, encoding='utf-8'
)
data = json.loads(r.stdout)
recs = data['data']['records']

food_cats = ['餐饮', '居家/食品', '居家/菜市场']
food = [x for x in recs if any(x['category'].startswith(c) for c in food_cats)]

# 按日分组
by_day = {}
for r in food:
    day = r['time'][:10]
    by_day.setdefault(day, []).append(r)

# 生成 HTML
from datetime import datetime
html_rows = []
total_records = 0
total_amount = 0
for day in sorted(by_day.keys()):
    items = by_day[day]
    total_records += len(items)
    day_total = sum(abs(x['amount']) for x in items)
    total_amount += day_total
    rows_html = ''
    for r in items:
        rows_html += f"""<tr>
          <td>{r['time'][11:19]}</td>
          <td class="cat">{r['category']}</td>
          <td>{r.get('account','')}</td>
          <td class="amt">¥{abs(r['amount']):.2f}</td>
          <td class="note">{r['note']}</td>
        </tr>"""
    html_rows.append(f"""
    <section class="day">
      <h2>{day} · {len(items)} 笔 · 合计 ¥{day_total:.2f}</h2>
      <table>
        <thead><tr><th>时间</th><th>分类</th><th>账户</th><th>金额</th><th>备注</th></tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </section>""")

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>8/11-8/14 食物账单汇总 · 饼干记账</title>
<style>
  :root{{--bg:#f5f5f7;--card:#fff;--line:#e5e5ea;--fg:#1d1d1f;--fg2:#6e6e73;--blue:#007aff;--green:#34c759;--orange:#ff9500;--shadow:0 1px 3px rgba(0,0,0,.04),0 4px 16px rgba(0,0,0,.05);}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--fg);line-height:1.6;padding:0 0 80px;}}
  .wrap{{max-width:780px;margin:0 auto;padding:24px 16px;}}
  h1{{font-size:27px;font-weight:700;letter-spacing:-.02em;}}
  .summary{{display:flex;gap:12px;margin:18px 0;flex-wrap:wrap;}}
  .stat{{flex:1;min-width:120px;background:var(--card);border-radius:14px;box-shadow:var(--shadow);padding:14px 16px;}}
  .stat-label{{font-size:12px;color:var(--fg2);font-weight:600;}}
  .stat-val{{font-size:22px;font-weight:700;margin-top:4px;color:var(--blue);}}
  .day{{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:16px 18px;margin-bottom:14px;}}
  .day h2{{font-size:18px;font-weight:700;margin-bottom:12px;padding-bottom:8px;border-bottom:1px solid var(--line);}}
  table{{width:100%;border-collapse:collapse;font-size:13px;}}
  th{{text-align:left;color:var(--fg2);font-weight:600;padding:6px 4px;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;}}
  td{{padding:8px 4px;border-top:1px solid var(--line);vertical-align:top;}}
  .cat{{color:var(--fg2);font-size:12px;}}
  .amt{{font-weight:700;color:var(--orange);font-variant-numeric:tabular-nums;text-align:right;}}
  .note{{font-size:13px;}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <p class="eyebrow" style="font-size:12px;color:var(--fg2);font-weight:600;letter-spacing:.06em;">2026-08-11 ~ 2026-08-14 · 食物类支出</p>
    <h1>饼干记账 · 食物账单汇总</h1>
    <p style="color:var(--fg2);margin-top:6px;font-size:13px;">用于比对卡路里 · 估算克数/热量后逐日补录</p>
  </header>

  <div class="summary">
    <div class="stat"><div class="stat-label">总笔数</div><div class="stat-val">{total_records}</div></div>
    <div class="stat"><div class="stat-label">总金额</div><div class="stat-val">¥{total_amount:.2f}</div></div>
    <div class="stat"><div class="stat-label">覆盖天数</div><div class="stat-val">{len(by_day)}</div></div>
  </div>

  {''.join(html_rows)}

  <p style="margin-top:24px;font-size:12px;color:var(--fg2);">💡 用途:逐日比对 → 估计每笔实际吃了多少克 → 我用脚本查库匹配食物 → 生成卡路里补录确认页。</p>
</div>
</body>
</html>"""

with open(r"C:\Users\辰辰洋洋\.minimax\workspace\食物账单_8.11-8.14_比对.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"生成完成: {total_records} 笔 · ¥{total_amount:.2f} · {len(by_day)} 天")