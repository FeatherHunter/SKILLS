#!/usr/bin/env python3
"""健身计划 HTML 渲染器：从 DB 读取 → 生成 Apple 风格训练计划页面"""

import json
import sys
from pathlib import Path
from db import find_db_path, get_db, init_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)

# ── 部位色板 ──
PART_COLORS = {
    "胸": "#c2410c", "背": "#047857", "肩": "#b45309",
    "臂": "#4338ca", "腹": "#0e7490", "腿": "#be123c",
}

def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def render(output_path=None, target_week=None):
    """主渲染函数"""
    conn = _get_db()
    c = conn.cursor()

    # ── config ──
    c.execute('SELECT title, version, description, total_weeks, start_date FROM workout_plan_config')
    cfg = c.fetchone()
    if not cfg:
        return "尚未制定健身计划。"
    config = dict(zip(['title','version','desc','total_weeks','start_date'], cfg))

    # ── plans ──
    c.execute('''
        SELECT week_number, day_of_week, session_index, session_label,
               time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans ORDER BY week_number, day_of_week, session_index
    ''')
    rows = c.fetchall()
    conn.close()

    weeks_data = {}
    for r in rows:
        wn, dow, si, label, ts, te, rest, total_sets, movements = r
        weeks_data.setdefault(wn, []).append({
            'day_of_week': dow, 'session_index': si, 'label': label,
            'time_start': ts, 'time_end': te, 'is_rest_day': rest,
            'total_sets': total_sets, 'movements': json.loads(movements) if movements else [],
        })

    total_weeks = config['total_weeks']

    # ── 渲染 ──
    html = _render_html(config, weeks_data, total_weeks, target_week)

    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
        return output_path
    return html


def _render_html(config, weeks_data, total_weeks, target_week):
    week_nums = sorted(weeks_data.keys())

    # 简版 CSS（复用参考模板核心样式）
    css = '''
:root{--bg:#fbfbfd;--card:#fff;--ink:#1d1d1f;--ink2:#6e6e73;--ink3:#86868b;--line:#d2d2d7;--lineS:#e8e8ed;--accent:#0071e3;--shadow:0 1px 2px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.04)}
*{margin:0;padding:0;box-sizing:border-box}
html,body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC",sans-serif;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.app{max-width:900px;margin:0 auto;padding:32px 20px 60px}
.header h1{font-size:32px;font-weight:600;letter-spacing:-.02em;margin-bottom:4px}
.header p{color:var(--ink2);font-size:14px;margin-bottom:24px}
.tabs{display:flex;gap:2px;margin-bottom:20px;border-bottom:1px solid var(--lineS);overflow-x:auto}
.tab{flex-shrink:0;background:none;border:none;padding:10px 18px;font-family:inherit;font-size:14px;font-weight:500;color:var(--ink2);cursor:pointer;position:relative;border-radius:6px 6px 0 0}
.tab:hover{color:var(--ink);background:rgba(0,113,227,.06)}
.tab.active{color:var(--accent)}
.tab.active::after{content:"";position:absolute;left:12px;right:12px;bottom:-1px;height:2px;background:var(--accent);border-radius:1px}
.week{display:none;animation:fade .2s ease}
.week.active{display:block}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.session{background:var(--card);border:1px solid var(--lineS);border-radius:16px;padding:22px 26px;margin-bottom:14px;box-shadow:var(--shadow)}
.sess-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--lineS);flex-wrap:wrap}
.sess-tag{font-family:"SF Mono",monospace;font-size:11px;color:var(--ink3);background:var(--bg);padding:3px 8px;border-radius:5px}
.sess-name{font-size:17px;font-weight:600}
.sess-time{font-size:12px;color:var(--ink3);margin-left:auto}
.rest-day{padding:40px;text-align:center;color:var(--ink3)}
.rest-day h3{font-size:20px;color:var(--ink);margin-bottom:8px}
table{width:100%;border-collapse:collapse}
th{text-align:left;font-weight:500;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);padding:8px 12px 8px 0;border-bottom:1px solid var(--lineS)}
td{padding:12px 10px 12px 0;border-bottom:1px solid var(--lineS);font-size:13px;color:var(--ink2);vertical-align:top}
tr:last-child td{border-bottom:none}
td:first-child{font-weight:500;color:var(--ink);min-width:160px}
td .sub{font-size:11px;color:var(--ink3);display:block;margin-top:2px}
.part-tag{display:inline-block;font-size:10.5px;padding:2px 6px;border-radius:4px;font-weight:600}
@media(max-width:640px){.app{padding:20px 12px 48px}.session{padding:16px 14px}.header h1{font-size:26px}td{padding:10px 4px;font-size:12px}td:first-child{min-width:120px}}
'''
    # 构建 HTML
    html_parts = [
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<title>{config["title"]}</title><style>{css}</style></head>',
        '<body><div class="app">',
        f'<div class="header"><h1>{config["title"]}</h1>',
        f'<p>{config["desc"] or ""} · {total_weeks} 周循环 · 起始 {config["start_date"]}</p></div>',
    ]

    # 周 Tab
    html_parts.append('<div class="tabs" id="weekTabs">')
    for i, wn in enumerate(week_nums):
        active = ' active' if (target_week and wn == target_week) or (not target_week and i == 0) else ''
        html_parts.append(f'<button class="tab{active}" data-wk="{wn}">第 {wn} 周</button>')
    html_parts.append('</div>')

    # 每周内容
    for w_idx, wn in enumerate(week_nums):
        active_cls = ' active' if (target_week and wn == target_week) or (not target_week and w_idx == 0) else ''
        html_parts.append(f'<div class="week{active_cls}" data-wk="{wn}">')

        days = weeks_data.get(wn, [])
        # 按 day_of_week 分组
        from itertools import groupby
        days_sorted = sorted(days, key=lambda d: d['day_of_week'])
        _day_sessions = {}
        for d in days_sorted:
            _day_sessions.setdefault(d['day_of_week'], []).append(d)

        for dow in range(1, 8):
            sessions = _day_sessions.get(dow, [])
            if not sessions:
                continue

            day_label = ['','周一','周二','周三','周四','周五','周六','周日'][dow]

            # 检查是否全天休息
            if len(sessions) == 1 and sessions[0].get('is_rest_day'):
                html_parts.append(f'<div class="session rest-day"><h3>{day_label} · 休息日</h3><p>主动恢复，不练力量</p></div>')
                continue

            # 渲染每个 session
            for sess in sessions:
                movements = sess['movements']
                html_parts.append('<div class="session">')
                html_parts.append('<div class="sess-head">')
                html_parts.append(f'<span class="sess-tag">{day_label}</span>')

                # 时间 → 时段标识
                ts = sess.get('time_start', '')
                te = sess.get('time_end', '')
                time_str = f'{ts}-{te}' if ts and te else ''
                html_parts.append(f'<span class="sess-name">{sess["label"]}</span>')
                if time_str:
                    html_parts.append(f'<span class="sess-time">{time_str}</span>')
                if sess.get('total_sets'):
                    html_parts.append(f'<span class="sess-time"> 共 {sess["total_sets"]} 组</span>')
                html_parts.append('</div>')

                # 动作表格
                if movements:
                    html_parts.append('<table><thead><tr><th>动作</th><th>部位</th><th>组数 × 次数</th><th>重量</th><th>休息</th></tr></thead><tbody>')
                    for m in movements:
                        name = m.get('name','')
                        part = m.get('part','')
                        mtype = m.get('type','')
                        note = m.get('note','')
                        rest = m.get('rest','')
                        sets_list = m.get('sets',[])
                        nsets = len(sets_list)
                        reps = sets_list[0].get('reps','?') if sets_list else '?'
                        weight = sets_list[0].get('weight','?') if sets_list else '?'
                        unit = sets_list[0].get('unit','kg') if sets_list else 'kg'

                        color = PART_COLORS.get(part, '#6e6e73')
                        wt = f'{weight} {unit}' if unit != '自重' else '自重'

                        html_parts.append('<tr>')
                        html_parts.append(f'<td><strong>{name}</strong><span class="sub">{note or ""}{" · "+mtype if mtype else ""}</span></td>')
                        html_parts.append(f'<td><span class="part-tag" style="background:{color}20;color:{color}">{part}</span></td>')
                        html_parts.append(f'<td><strong>{nsets}</strong> × {reps}</td>')
                        html_parts.append(f'<td><strong>{wt}</strong></td>')
                        html_parts.append(f'<td>{rest}</td>')
                        html_parts.append('</tr>')
                    html_parts.append('</tbody></table>')
                else:
                    html_parts.append('<p style="color:var(--ink3);padding:12px 0">暂无动作</p>')

                html_parts.append('</div>')  # /session

        html_parts.append('</div>')  # /week

    # Tab 切换 JS
    html_parts.append('''<script>
document.querySelectorAll('#weekTabs .tab').forEach(t=>{
  t.onclick=function(){
    document.querySelectorAll('#weekTabs .tab').forEach(b=>b.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.week').forEach(w=>{
      w.classList.toggle('active', w.dataset.wk === this.dataset.wk);
    });
  };
});
</script>''')

    html_parts.append('</div></body></html>')
    return '\n'.join(html_parts)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='渲染健身计划HTML')
    p.add_argument('-o','--output',help='输出文件路径')
    p.add_argument('-w','--week',type=int,help='聚焦第几周')
    args = p.parse_args()
    result = render(args.output, args.week)
    if isinstance(result, str) and not args.output:
        print(result)
    elif args.output:
        print(f'→ {result}')
