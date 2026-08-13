#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_diet_review.py — 饮食复盘 HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 饮食复盘（本周）/ 饮食复盘（本月）/ 饮食复盘（最近 90 天）/ 饮食复盘（今年）/ 饮食复盘（自定义时间）
对应模板: templates/diet_review.html

呈现数据: 总热量/日均/总蛋白/日均 + 趋势 + 高频 TOP5 + 一句话
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '饮食复盘'
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'diet_review.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _resolve_range(rtype, start, end):
    """按复盘类型解析起止日期"""
    today = date.today()
    if rtype == 'week':
        s = today - timedelta(days=today.weekday())
        return s.isoformat(), today.isoformat()
    if rtype == 'month':
        return today.replace(day=1).isoformat(), today.isoformat()
    if rtype == 'quarter':
        return (today - timedelta(days=89)).isoformat(), today.isoformat()
    if rtype == 'year':
        return today.replace(month=1, day=1).isoformat(), today.isoformat()
    if rtype == 'range' and start and end:
        return start, end
    return (today - timedelta(days=6)).isoformat(), today.isoformat()


def build_data(start, end):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('''
        SELECT date, food_name, SUM(calories), SUM(protein), COUNT(*)
        FROM food_log WHERE date BETWEEN ? AND ? AND food_name != '💧水'
        GROUP BY date, food_name ORDER BY date
    ''', (start, end))
    rows = cur.fetchall()
    conn.close()

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    by_day = {}
    freq = {}
    for d, food, cal, pro, cnt in rows:
        cal = cal or 0; pro = pro or 0
        by_day[d] = by_day.get(d, [0, 0])
        by_day[d][0] += cal; by_day[d][1] += pro
        freq[food] = freq.get(food, 0) + cnt

    total_cal = round(sum(v[0] for v in by_day.values()), 1)
    total_pro = round(sum(v[1] for v in by_day.values()), 1)
    avg_cal = round(total_cal / max(1, days), 1)
    avg_pro = round(total_pro / max(1, days), 1)

    top5 = sorted(freq.items(), key=lambda x: -x[1])[:5]
    top5 = [{'food': f, 'count': c} for f, c in top5]

    daily = [{'date': d, 'cal': round(v[0], 1), 'pro': round(v[1], 1)}
             for d, v in sorted(by_day.items())]
    # #44 审查(趋势完整窗口):无记录天 0 值占位(模板渲染空柱)
    _full = []
    _d = date.fromisoformat(start)
    _end_d = date.fromisoformat(end)
    from datetime import timedelta as _td
    while _d <= _end_d:
        _iso = _d.isoformat()
        _full.append({'date': _iso, 'cal': next((x['cal'] for x in daily if x['date'] == _iso), 0),
                      'pro': next((x['pro'] for x in daily if x['date'] == _iso), 0)})
        _d += _td(days=1)
    daily = _full

    # 一句话(基于数据)
    if not by_day:
        one_line = '该时间段没有饮食记录'
    else:
        _data_days = sum(1 for d in daily if d['cal'] > 0)
        trend = ('数据不足(仅 ' + str(_data_days) + ' 天有记录)' if _data_days < 3 else
                 ('上升' if daily[-1]['cal'] > daily[0]['cal'] * 1.1 else
                  '下降' if daily[-1]['cal'] < daily[0]['cal'] * 0.9 else '平稳'))
        one_line = (f'{days} 天内日均 {avg_cal} 卡,总蛋白 {total_pro}g;'
                    f'趋势{trend};高频食物 {top5[0]["food"]}({top5[0]["count"]} 次)' if top5 else
                    f'{days} 天内日均 {avg_cal} 卡,总蛋白 {total_pro}g,趋势{trend}')

    return {
        'status': 'ok',
        'data': {
            'summary': {'days': days, 'total_cal': total_cal, 'avg_cal': avg_cal,
                        'total_pro': total_pro, 'avg_pro': avg_pro, 'one_line': one_line},
            'top5': top5,
            'daily': daily,
            'meta': {'start': start, 'end': end, 'today': today_iso()},
        },
        'message': f'饮食复盘 {start} ~ {end}',
    }


def today_iso():
    return date.today().isoformat()


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染饮食复盘 HTML(结果型)')
    p.add_argument('--type', choices=['week', 'month', 'quarter', 'year', 'range'], default='week')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    s, e = _resolve_range(args.type, args.start, args.end)
    try:
        data = build_data(s, e)
        if args.chain:
            data['data']['meta']['chain'] = args.chain
        html = render_html(data)
    except Exception as ex:
        print(f'❌ 渲染失败: {ex}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'饮食复盘_{args.type}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {s} ~ {e} | 总热量 {sm["total_cal"]} 卡 | 日均 {sm["avg_cal"]} 卡')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
