#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_summary.py — 运动报表 HTML(看类 17 场景一体 · v1.0)

对应 SKILL.md 唤醒词(17 个):
  - 看今日运动/看昨日运动            → --mode records --today/--yesterday
  - 看本周/上周/本月/上月运动         → --mode summary --week/--last-week/--month/--last-month
  - 看最近 7/30/60 天运动             → --mode summary --days 7/30/60
  - 看最近 180/365 天运动(降采样)     → --mode summary --days 180/365 --downsample 3/week
  - 看某段时间运动                    → --mode summary --from <F> --to <T>
  - 看运动记录（有备注）              → --mode records --has-note
  - 看运动记录（按力量筛选）          → --mode records --category 力量
  - 看运动记录（按有氧筛选）          → --mode records --category 有氧
对应模板: templates/exercise_summary.html

2026-08-02 · ticket #5 运动 · R3 --chain 强制 + R5 <场景名>_结果_TS.html
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_summary.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from exercise_tracker import resolve_window  # noqa

_CAT_LABELS = {'力量': 'strength', '有氧': 'cardio', '柔韧': 'flex', '日常': 'daily'}


def _scene_name(args) -> str:
    """由参数推断场景名(2026-08-02 · R5 命名)"""
    if getattr(args, 'has_note', False):
        return '看运动记录（有备注）'
    if args.category == '力量':
        return '看运动记录（按力量筛选）'
    if args.category == '有氧':
        return '看运动记录（按有氧筛选）'
    if args.window == 'today':
        return '看今日运动'
    if args.window == 'yesterday':
        return '看昨日运动'
    if args.window == 'week':
        return '看本周运动'
    if args.window == 'last-week':
        return '看上周运动'
    if args.window == 'month':
        return '看本月运动'
    if args.window == 'last-month':
        return '看上月运动'
    if args.days:
        return {7: '看最近 7 天运动', 30: '看最近 30 天运动',
                60: '看最近 60 天运动', 180: '看最近 180 天运动',
                365: '看最近 365 天运动'}.get(args.days, '看最近 30 天运动')
    return '看某段时间运动'


def _goal_cal() -> int | None:
    """读每日运动目标(卡),未设返回 None(2026-08-02 · ticket #5)"""
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT exercise_goal FROM daily_goal WHERE id = 1").fetchone()
        return row[0] if row and row[0] else None
    finally:
        conn.close()


def _fetch(conn, start, end, category=None, has_note=False, etype=None):
    """查询运动记录(全字段,2026-08-02 扩展:note/距离/心率/reps/重量/组号)"""
    cur = conn.cursor()
    conds, params = ['date BETWEEN ? AND ?', 'COALESCE(is_deleted, 0) = 0'], [start, end]
    if category:
        conds.append('category = ?')
        params.append(category)
    if has_note:
        conds.append("note IS NOT NULL AND note != ''")
    if etype:
        conds.append('exercise_type LIKE ?')
        params.append(f'%{etype}%')
    cur.execute(f'''
        SELECT date, time, exercise_type, category, calories_burned AS calorie,
               duration_minutes AS minutes, COALESCE(set_index, 0) AS sets,
               note, distance_km, avg_heart_rate, max_heart_rate, reps, load_kg, steps
        FROM exercise_log
        WHERE {' AND '.join(conds)}
        ORDER BY date DESC, time DESC
    ''', params)
    items = []
    for (d, t, et, cat, cal, mins, sets, note, dist, ahr, mhr, reps, load, steps) in cur.fetchall():
        items.append({'date': d, 'time': t, 'exercise_type': et,
                      'category': _CAT_LABELS.get(cat, 'daily'), 'calorie': cal,
                      'minutes': mins, 'sets': sets, 'note': note,
                      'distance_km': dist, 'avg_heart_rate': ahr, 'max_heart_rate': mhr,
                      'reps': reps, 'load_kg': load, 'steps': steps})
    return items


def _pace(distance_km, minutes):
    """配速 = 分钟/km(距离缺失返回 None)"""
    if distance_km and minutes:
        return round(minutes / distance_km, 1)
    return None


def _downsample(items, mode):
    """降采样:mode=None 每天一行;3 = 每 3 天合并;week = 按 ISO 周合并

    返回 [{label, calorie, minutes, active_days}]
    """
    if not items:
        return []
    by_day = {}
    for i in items:
        d = i['date']
        if d not in by_day:
            by_day[d] = {'calorie': 0, 'minutes': 0, 'count': 0}
        by_day[d]['calorie'] += (i.get('calorie') or 0)
        by_day[d]['minutes'] += (i.get('minutes') or 0)
        by_day[d]['count'] += 1
    days = sorted(by_day)

    if mode is None:
        return [{'label': d, **by_day[d], 'active': True} for d in days]

    if mode == '3':
        buckets, cur, idx = [], [], 0
        for d in days:
            cur.append(d)
            if len(cur) == 3:
                buckets.append(cur)
                cur = []
        if cur:
            buckets.append(cur)
        out = []
        for b in buckets:
            cal = sum(by_day[x]['calorie'] for x in b)
            mins = sum(by_day[x]['minutes'] for x in b)
            act = sum(1 for x in b if by_day[x]['count'])
            out.append({'label': f'{b[0]}~{b[-1]}', 'calorie': cal, 'minutes': mins,
                        'active': act > 0, 'active_days': act})
        return out

    # week:按 ISO 周(周一开头)
    out, week_map = [], {}
    from datetime import datetime as _dt
    for d in days:
        iso = _dt.fromisoformat(d).isocalendar()
        key = f'{iso[0]}-W{iso[1]}'
        if key not in week_map:
            week_map[key] = {'calorie': 0, 'minutes': 0, 'count': 0, 'label': key}
        wk = week_map[key]
        wk['calorie'] += by_day[d]['calorie']
        wk['minutes'] += by_day[d]['minutes']
        wk['count'] += by_day[d]['count']
    for wk in week_map.values():
        out.append({'label': wk['label'], 'calorie': wk['calorie'], 'minutes': wk['minutes'],
                    'active': wk['count'] > 0, 'active_days': wk['count']})
    return out


def build_data(start, end, mode='records', category=None, has_note=False,
               etype=None, downsample=None):
    """构建报表数据(mode: records/summary;category/has_note 过滤;downsample 降采样)"""
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    items = _fetch(conn, start, end, category=category, has_note=has_note, etype=etype)
    conn.close()

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    goal = _goal_cal()
    total_cal = round(sum((i.get('calorie') or 0) for i in items), 1)
    total_min = sum((i.get('minutes') or 0) for i in items)
    active_days = len(set(i['date'] for i in items))

    # vs 目标(如有)
    goal_info = None
    if goal and mode == 'records':
        pct = round(total_cal / goal * 100) if goal else 0
        goal_info = {'goal': goal, 'actual': round(total_cal), 'pct': pct,
                     'gap': round(goal - total_cal), 'achieved': total_cal >= goal}

    if mode == 'records':
        if category == '力量':
            table_header = ("<tr><th>日期</th><th>动作</th><th class='num'>组号</th>"
                            "<th class='num'>重量</th><th class='num'>次数</th>"
                            "<th class='num'>热量</th></tr>")
            table_title = '力量训练记录'
        elif category == '有氧':
            table_header = ("<tr><th>日期</th><th>类型</th><th class='num'>时长</th>"
                            "<th class='num'>距离</th><th class='num'>配速</th>"
                            "<th class='num'>热量</th></tr>")
            table_title = '有氧运动记录'
        elif has_note:
            table_header = ("<tr><th>日期</th><th>类型</th><th class='num'>时长</th>"
                            "<th class='num'>热量</th><th>备注</th></tr>")
            table_title = '带备注的运动记录'
        else:
            table_header = ("<tr><th>日期</th><th>时间</th><th>类型</th>"
                            "<th class='num'>时长</th><th class='num'>热量</th>"
                            "<th class='num'>组数</th></tr>")
            table_title = '运动记录'
        subtitle = f'{start} ~ {end} · {len(items)} 条记录 · {active_days} 天运动'
        summary = {
            'subtitle': subtitle,
            'k1': {'label': '记录数', 'value': str(len(items)), 'extra': f'{active_days} 天运动'},
            'k2': {'label': '总热量', 'value': f'{total_cal:,.1f}',
                   'extra': f'日均 {round(total_cal / max(1, days))}'},
            'k3': {'label': '总时长', 'value': f'{total_min} 分钟',
                   'extra': f'平均 {round(total_min / max(1, len(items)), 1)} 分/次'},
            'k4': {'label': '目标对比', 'value': goal_info and f'{goal_info["pct"]}%' or '未设目标',
                   'extra': goal_info and f'vs {goal_info["goal"]} 卡 · 差 {goal_info["gap"]} 卡' or ''},
            'table_header': table_header,
            'table_title': table_title,
        }
    else:
        rows = _downsample(items, downsample)
        table_header = ("<tr><th>日期</th><th class='num'>热量</th><th class='num'>时长</th>"
                        "<th class='num'>运动</th></tr>")
        subtitle = f'{start} ~ {end} · {active_days}/{days} 天运动'
        summary = {
            'subtitle': subtitle,
            'k1': {'label': '运动天数', 'value': str(active_days), 'extra': f'占 {days} 天的 {round(active_days / max(1, days) * 100)}%'},
            'k2': {'label': '总热量', 'value': f'{total_cal:,.1f}', 'extra': f'日均 {round(total_cal / max(1, days))}'},
            'k3': {'label': '总时长', 'value': f'{total_min} 分钟', 'extra': f'平均 {round(total_min / max(1, active_days))} 分/天'},
            'k4': {'label': '目标对比', 'value': goal_info and f'{goal_info["pct"]}%' or '未设目标',
                   'extra': goal_info and f'vs {goal_info["goal"]} 卡 · 差 {goal_info["gap"]} 卡' or ''},
            'table_header': table_header,
            'table_title': '运动汇总',
        }

    return {
        'status': 'ok',
        'data': {
            'summary': summary,
            'items': items,
            'rows': rows if mode == 'summary' else [],
            'mode': mode,
            'goal': goal_info,
            'meta': {'start': start, 'end': end, 'days': days,
                     'today': date.today().isoformat()},
        },
        'message': f'已生成运动报表({mode}, {len(items)} 条)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动报表 HTML(看类 17 场景一体)')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--today', action='store_true')
    g.add_argument('--yesterday', action='store_true')
    g.add_argument('--week', action='store_true')
    g.add_argument('--last-week', action='store_true', dest='last_week')
    g.add_argument('--month', action='store_true')
    g.add_argument('--last-month', action='store_true', dest='last_month')
    p.add_argument('--days', type=int)
    p.add_argument('--from', dest='from_date')
    p.add_argument('--to', dest='to_date')
    p.add_argument('--mode', choices=['records', 'summary'], default='records')
    p.add_argument('--category', choices=['有氧', '力量', '柔韧', '日常'])
    p.add_argument('--has-note', action='store_true', dest='has_note')
    p.add_argument('--type')
    p.add_argument('--downsample', choices=['3', 'week'])
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    # ⭐ 思考链强制(R3 · 同 render_crud_view/render_exercise_receipt)
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读DB→3.渲染报表"', file=sys.stderr)
        return 2

    window = None
    for w, flag in (('today', args.today), ('yesterday', args.yesterday),
                    ('week', args.week), ('last-week', args.last_week),
                    ('month', args.month), ('last-month', args.last_month)):
        if flag:
            window = w
            break
    args.window = window

    s, e = resolve_window(window, days=args.days, from_date=args.from_date, to_date=args.to_date)
    scene = _scene_name(args)
    mode = 'records' if (args.mode == 'records' or args.has_note or args.category) else 'summary'
    try:
        data = build_data(s, e, mode=mode, category=args.category,
                          has_note=args.has_note, etype=args.type,
                          downsample=args.downsample)
        data['data']['meta']['chain'] = args.chain.strip()
        data['data']['meta']['wake_word'] = scene
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(
            _quote_arg(a) for a in argv)
        data['data']['meta']['source'] = 'exercise_log (只读报表)'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    n = len(data['data']['items'])
    print(f'✅ {out_path}')
    print(f'   场景: {scene} | 范围: {s} ~ {e} | {n} 条 | 窗口: {window or "自定义"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
