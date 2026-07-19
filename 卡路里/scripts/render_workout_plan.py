#!/usr/bin/env python3
"""健身计划 HTML 渲染器

职责定位（2026-07-18 复盘）：
- 本 HTML = 训练前看今天练什么（"今天该做哪些动作、几组、几kg"）
- 训练复盘 = 走独立 CLI：`/卡路里 复盘今日`，由 exercise_review 动态算
- 本 HTML 不嵌入任何复盘数据（避免写死假数据，如完成率 0%）
- include_review 默认 False；要开复盘 section 必须显式传 --review

历史教训：
- 518e651 / c8915a3 曾在 HTML 顶部手写"今日复盘"模块，完成率硬编码 0%
- 卡路里技能 SKILL.md 强制规定 1 已重新解读为"卡路里复盘联动"，
  不适用于训练计划 HTML（这是两个独立职责）
"""

import json
import sys
from pathlib import Path
from db import find_db_path, get_db, init_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)

# ── 部位色板（v2 · 7 色 · 第一性原理 2026-07-20 重构）──
# 设计原则:
#   1. 6 大解剖部位 + 1 训练模式 = 7 个标签(完整 MECE)
#   2. 色相距离 ≥ 30°, 色盲友好(避开红绿并列)
#   3. 按 push/pull/legs 分组排列, 冷暖搭配
#   4. WCAG 对比度: 文字 vs 浅背景 ≥ 4.5:1
PART_COLORS = {
    # Push 类 (暖色, 力量感)
    "胸": "#c2410c",  # 砖红 - 推的中心
    "肩": "#a16207",  # 深金 - 推的上方 (黄系拉开跟红的距离)
    "臂": "#4338ca",  # 紫蓝 - 推的末端 (冷色跳出)
    # Pull 类 (冷色, 伸展感)
    "背": "#047857",  # 翠绿 - 拉的中心
    "腿": "#0891b2",  # 青    - 下肢 (介于绿蓝)
    "腹": "#7c3aed",  # 深紫  - 核心 (紫系避开腿青)
    # 训练模式
    "有氧": "#6b7280",  # 冷灰 - 心肺 (中性, 跟所有色系不撞)
}

def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def render(output_path=None, target_week=None, include_review=False):
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

    # ── review (可选，默认关闭) ──
    # 训练计划 HTML 职责 = 训练前看今天练什么，不含复盘
    # 训练复盘请用独立 CLI：`/卡路里 复盘今日`
    review_data = None
    if include_review:
        try:
            from analysis.exercise import exercise_review
            from datetime import date
            today_str = date.today().strftime('%Y-%m-%d')
            review_data = exercise_review(today_str, today_str, silent=True)
        except Exception as e:
            print(f"⚠️ 复盘 section 渲染失败: {e}")
            review_data = None

    # ── 渲染 ──
    html = _render_html(config, weeks_data, total_weeks, target_week, review_data)

    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
        return output_path
    # 默认输出到技能目录
    default_path = SKILL_DIR / '健身计划.html'
    default_path.write_text(html, encoding='utf-8')
    return str(default_path)


def _render_html(config, weeks_data, total_weeks, target_week, review_data=None):
    week_nums = sorted(weeks_data.keys())

    # 简版 CSS（复用参考模板核心样式）
    css = '''
:root{--bg:#fbfbfd;--card:#fff;--ink:#1d1d1f;--ink2:#6e6e73;--ink3:#86868b;--line:#d2d2d7;--lineS:#e8e8ed;--accent:#0071e3;--shadow:0 1px 2px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.04)}
*{margin:0;padding:0;box-sizing:border-box}
html,body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","PingFang SC",sans-serif;background:var(--bg);color:var(--ink);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
.app{max-width:900px;margin:0 auto;padding:32px 20px 60px}
.header h1{font-size:32px;font-weight:600;letter-spacing:-.02em;margin-bottom:4px}
.header p{color:var(--ink2);font-size:14px;margin-bottom:24px}
.tabs{display:flex;gap:2px;margin-bottom:20px;border-bottom:1px solid var(--lineS);overflow-x:auto;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}
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
.day-tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px;scrollbar-width:none}.day-tabs::-webkit-scrollbar{display:none}
.day-tab{background:var(--card);border:1px solid var(--lineS);padding:6px 12px;font-family:inherit;font-size:12.5px;font-weight:500;color:var(--ink2);cursor:pointer;border-radius:8px;transition:all .15s}
.day-tab:hover{border-color:var(--accent);color:var(--ink)}
.day-tab.active{background:var(--ink);border-color:var(--ink);color:#fff}
.review-section{background:#fff;border:1px solid var(--lineS);border-radius:16px;padding:22px 26px;margin-bottom:20px;box-shadow:var(--shadow)}
.review-section h2{font-size:18px;font-weight:600;margin-bottom:14px}
.review-stat{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}
.stat-label{font-size:11px;color:var(--ink3);text-transform:uppercase;letter-spacing:.06em;font-weight:500}
.stat-value{font-size:32px;font-weight:600;color:var(--accent);line-height:1}
.review-detail{color:var(--ink2);font-size:13px;margin-bottom:10px;line-height:1.6}
.review-detail p{margin-bottom:3px}
.review-detail strong{color:var(--ink);font-weight:500}
.anomalies{list-style:none;padding:0;margin-top:8px}
.anomalies li{padding:5px 0;color:var(--ink2);font-size:13px}
.no-review{color:var(--ink3);font-style:italic;font-size:13px}
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

    # 复盘 section（仅在 --review 显式开启时渲染；默认不渲染）
    # 设计原则：训练计划 HTML = 训练前看今天练什么；复盘走独立 CLI `/卡路里 复盘今日`
    if review_data:
        from datetime import date
        today_str = date.today().strftime('%Y-%m-%d')
        today_review = review_data.get(today_str) or next(iter(review_data.values()), None)
        if today_review:
            rate = today_review.get('completion_rate')
            sessions = today_review.get('sessions', [])
            plan_sets = today_review.get('plan_total_sets', 0)
            actual_sets = today_review.get('actual_total_sets', 0)
            anomalies = today_review.get('anomalies', [])
            note = today_review.get('note')
            html_parts.append('<div class="review-section">')
            html_parts.append(f'<h2>📋 今日复盘 · {today_str}</h2>')
            if rate is not None:
                html_parts.append('<div class="review-stat">')
                html_parts.append('<span class="stat-label">完成率</span>')
                html_parts.append(f'<span class="stat-value">{rate:.0f}%</span>')
                html_parts.append('</div>')
            html_parts.append('<div class="review-detail">')
            if sessions:
                sessions_filtered = [s for s in sessions if s]  # 过滤空字符串,避免 " / 上午·臂" 双斜杠
                if sessions_filtered:
                    html_parts.append(f'<p><strong>训练:</strong> {" / ".join(sessions_filtered)}</p>')
            if plan_sets or actual_sets:
                html_parts.append(f'<p><strong>组数:</strong> 计划 {plan_sets} · 实做 {actual_sets}</p>')
            if note:
                html_parts.append(f'<p><strong>备注:</strong> {note}</p>')
            html_parts.append('</div>')
            if anomalies:
                html_parts.append('<ul class="anomalies">')
                for a in anomalies:
                    html_parts.append(f'<li>{a}</li>')
                html_parts.append('</ul>')
            html_parts.append('</div>')
        else:
            html_parts.append('<div class="review-section"><h2>📋 今日复盘</h2><p class="no-review">暂无复盘数据</p></div>')
    # 如果 include_review=False（默认），不渲染任何复盘 section（设计原则：复盘走独立 CLI）

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

        # Day tabs
        html_parts.append(f'<div class="day-tabs" id="dayTabs_w{wn}">')
        for dow in range(1, 8):
            day_label = ['','周一','周二','周三','周四','周五','周六','周日'][dow]
            active = ' active' if dow == 1 else ''
            html_parts.append(f'<button class="day-tab{active}" data-day="d{w_idx}_{dow}">{day_label}</button>')
        html_parts.append('</div>')

        for dow in range(1, 8):
            sessions = _day_sessions.get(dow, [])
            day_label = ['','周一','周二','周三','周四','周五','周六','周日'][dow]
            display = '' if dow == 1 else ' style="display:none"'

            html_parts.append(f'<div class="day-content" data-day="d{w_idx}_{dow}"{display}>')

            # 全天休息
            if len(sessions) == 1 and sessions[0].get('is_rest_day'):
                html_parts.append(f'<div class="session rest-day"><h3>{day_label} · 休息日</h3><p>主动恢复，不练力量</p></div>')
                html_parts.append('</div>'); continue

            # 渲染每个 session
            for sess in sessions:
                movements = sess['movements']
                html_parts.append('<div class="session">')
                html_parts.append('<div class="sess-head">')
                html_parts.append(f'<span class="sess-tag">{day_label}</span>')

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

            html_parts.append('</div>')  # /day-content

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
document.querySelectorAll('.day-tabs').forEach(dt=>{
  dt.querySelectorAll('.day-tab').forEach(t=>{
    t.onclick=function(){
      this.parentElement.querySelectorAll('.day-tab').forEach(b=>b.classList.remove('active'));
      this.classList.add('active');
      const week = this.closest('.week');
      week.querySelectorAll('.day-content').forEach(d=>{
        d.style.display = d.dataset.day === this.dataset.day ? '' : 'none';
      });
    };
  });
});
</script>''')

    html_parts.append('</div></body></html>')
    return '\n'.join(html_parts)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='渲染健身计划HTML')
    p.add_argument('-o','--output',help='输出文件路径')
    p.add_argument('-w','--week',type=int,help='聚焦第几周')
    p.add_argument('--review', action='store_true', help='打开复盘 section（默认关闭。复盘请用 `/卡路里 复盘今日` CLI）')
    args = p.parse_args()
    result = render(args.output, args.week, include_review=args.review)
    if isinstance(result, str) and not args.output:
        print(result)
    elif args.output:
        print(f'→ {result}')
