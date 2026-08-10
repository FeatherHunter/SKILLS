#!/usr/bin/env python3
"""健身计划 HTML 渲染器(2026-08-02 重构:多模式 · ticket #6)

对应 SKILL.md 唤醒词:看完整计划 / 看本周计划 / 看下周计划 / 看上周计划 / 看指定周计划 / 看今天练什么 / 看某天练什么 / 看计划概览 / 看计划 vs 实际 / 看计划完成率 / 看未完成训练 / 看动作完成率

模式(--mode):
  full      全计划视图(原行为;--week N 可聚焦单周)
  week      单周视图(7 天表 + 完成度;--week N)
  today     看今天练什么(动作/组数/重量 + 实时完成进度,接 exercise_log)
  day       看某天练什么(指定日期;--start <YYYY-MM-DD>,默认今天;复用 today 组装逻辑 · #255)
  overview  看计划概览(KPI + 每周完成率列表)
  vs        看计划 vs 实际(完成度/偏差/动作级对比表;--start/--end)
  completion 看计划完成率(每周完成率折线)
  missed    看未完成训练(漏练日期 + 应练动作;--days N)
  movement  看动作完成率(动作 TOP 榜;--days N)

设计:
- 渲染器只做:读数据 → 序列化 → 注入 → 输出
- DOM 渲染交给 JS(CSS / JS / HTML 骨架都在稳定模板里)
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次(注入器校验)
"""
import argparse
import json
from datetime import date, timedelta
from html_paths import html_path
import sys
from pathlib import Path

from db import find_db_path, get_db, init_db  # noqa: E402 (供 _get_db 动态解析)

SKILL_DIR = Path(__file__).resolve().parent.parent
DB_FILENAME = "calorie_data.db"
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'workout_plan_view.html'


def _get_db():
    """动态解析 DB 路径(2026-08-02 ticket #6:与 render_goal_config 等一致,
    支持 SKILLS_DB_PATH 环境变量在测试中被 monkeypatch)"""
    from db import find_db_path, get_db, init_db
    db_path = find_db_path(SKILL_DIR, DB_FILENAME)
    if not db_path.exists():
        init_db(db_path)
    return get_db(db_path)


def _load_config(conn):
    c = conn.cursor()
    c.execute('SELECT title, version, description, total_weeks, start_date FROM workout_plan_config')
    row = c.fetchone()
    if not row:
        return None
    return {
        'title': row[0] or '健身计划',
        'version': row[1] or '',
        'description': row[2] or '',
        'total_weeks': row[3],
        'start_date': row[4] or '',
    }


def _load_week(conn, week_number):
    """读某一周所有天的 sessions(与 workout_plan.get_day_plan 同构)"""
    c = conn.cursor()
    c.execute('''
        SELECT week_number, day_of_week, session_index, session_label,
               time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans
        WHERE week_number = ?
        ORDER BY day_of_week, session_index
    ''', (week_number,))
    days_map = {}
    for r in c.fetchall():
        dow = r[1]
        days_map.setdefault(dow, []).append({
            'session_index': r[2],
            'session_label': r[3],
            'time_start': r[4] or '',
            'time_end': r[5] or '',
            'is_rest_day': bool(r[6]),
            'total_sets': r[7] or 0,
            'movements': json.loads(r[8]) if r[8] else [],
        })
    days = [{
        'day_of_week': dow,
        'day_label': ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][dow],
        'sessions': days_map[dow],
    } for dow in sorted(days_map)]
    return {'week_number': week_number, 'days': days}


def _calc_week_number(target_date, config):
    """target_date 对应的计划周次(与 workout_plan.calc_plan_week 同构)"""
    if not config:
        return None
    start = date.fromisoformat(config['start_date'])
    days_diff = (target_date - start).days
    if days_diff < 0:
        return None
    real_week = days_diff // 7 + 1
    return ((real_week - 1) % config['total_weeks']) + 1


def _week_completion(conn, week_number, config):
    """某周完成度:按天对比 exercise_log 实做组数 vs 计划组数"""
    start = date.fromisoformat(config['start_date'])
    total_plan = 0
    total_actual = 0
    plan_days = 0
    c = conn.cursor()
    for dow in range(1, 8):
        day_date = start + timedelta(days=(week_number - 1) * 7 + (dow - 1))
        c.execute('SELECT COALESCE(SUM(total_sets),0) FROM workout_plans WHERE week_number=? AND day_of_week=? AND is_rest_day=0', (week_number, dow))
        plan_sets = c.fetchone()[0]
        if plan_sets > 0:
            plan_days += 1
            total_plan += plan_sets
        c.execute('SELECT COUNT(*) FROM exercise_log WHERE date=?', (day_date.isoformat(),))
        total_actual += c.fetchone()[0]
    rate = (total_actual / total_plan * 100) if total_plan else None
    return {
        'week_number': week_number,
        'plan_sets': total_plan,
        'actual_sets': total_actual,
        'completion_rate': round(rate, 1) if rate is not None else None,
        'plan_days': plan_days,
    }


def build_full_data(conn, focus_week=None):
    """全计划视图(原 render_workout_plan 行为);focus_week 给定时只渲染该周"""
    config = _load_config(conn)
    if not config:
        return None
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_number FROM workout_plans ORDER BY week_number')
    week_numbers = [r[0] for r in c.fetchall()]
    if focus_week is not None and focus_week in week_numbers:
        week_numbers = [focus_week]
    weeks = [_load_week(conn, wn) for wn in week_numbers]
    # 2026-08-10 #252:full 模式返回当前周次(模板默认激活本周, 用户看全计划最关心当前)
    current_week = _calc_week_number(date.today(), config)
    return {'mode': 'full', 'config': config, 'weeks': weeks, 'current_week': current_week,
            'review': {'today': None}}


def build_week_data(conn, week_number):
    """单周视图:7 天表 + 完成度 + 一句话"""
    config = _load_config(conn)
    if not config:
        return None
    if week_number is None:
        week_number = _calc_week_number(date.today(), config) or 1
    week = _load_week(conn, week_number)
    completion = _week_completion(conn, week_number, config)
    return {
        'mode': 'week',
        'config': config,
        'weeks': [week],
        'focus_week': week_number,
        'completion': completion,
    }


def build_today_data(conn):
    """今日视图:动作/组数/重量 + 实时完成进度"""
    data = _build_day_data(conn, date.today())
    if data:
        data['mode'] = 'today'
    return data


def build_day_data(conn, target_date):
    """#255: 指定日期视图(复用 today 组装逻辑; 无日期默认今天)"""
    return _build_day_data(conn, target_date)


def _build_day_data(conn, target_date):
    """按日期组装训练日数据(2026-08-10 #255: today 与 day 共用)"""
    config = _load_config(conn)
    if not config:
        return None
    week_number = _calc_week_number(target_date, config)
    c = conn.cursor()
    if week_number is None:
        return {
            'mode': 'day',
            'config': config,
            'date': target_date.isoformat(),
            'unstarted': True,
            'start_date': config['start_date'],
            'sessions': [],
            'completion': None,
        }
    dow = target_date.isoweekday()
    c.execute('''
        SELECT session_index, session_label, time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans
        WHERE week_number=? AND day_of_week=? ORDER BY session_index
    ''', (week_number, dow))
    sessions = []
    for r in c.fetchall():
        movements = json.loads(r[6]) if r[6] else []
        # 每个动作的实时完成:exercise_log 中同动作名已做组数
        enriched = []
        total_done = 0
        total_plan = 0
        for m in movements:
            sets = m.get('sets') or []
            plan_sets = len(sets)
            total_plan += plan_sets
            done = 0
            if plan_sets:
                c.execute("SELECT COUNT(*) FROM exercise_log WHERE date=? AND exercise_type=?",
                          (target_date.isoformat(), m.get('name', '')))
                done = c.fetchone()[0]
                total_done += min(done, plan_sets)
            enriched.append({
                'name': m.get('name', ''),
                'part': m.get('part', ''),
                'sets': plan_sets,
                'sets_done': min(done, plan_sets),
                'reps': sets[0].get('reps') if sets else None,
                'weight': sets[0].get('weight') if sets else None,
                'unit': sets[0].get('unit', 'kg') if sets else 'kg',
            })
        sessions.append({
            'session_index': r[0],
            'session_label': r[1],
            'time_start': r[2] or '',
            'time_end': r[3] or '',
            'is_rest_day': bool(r[4]),
            'total_sets': r[5] or 0,
            'movements': enriched,
        })
    total_plan = sum(s['total_sets'] or 0 for s in sessions if not s['is_rest_day'])
    total_done = 0
    for s in sessions:
        if s['is_rest_day']:
            continue
        for m in s['movements']:
            total_done += m['sets_done']
    is_rest = all(s['is_rest_day'] for s in sessions) if sessions else False
    return {
        'mode': 'day',
        'config': config,
        'date': target_date.isoformat(),
        'plan_week': week_number,
        'is_rest': is_rest,
        'unstarted': False,
        'sessions': sessions,
        'completion': {
            'plan_sets': total_plan,
            'done_sets': total_done,
            'remaining_sets': max(total_plan - total_done, 0),
            'rate': round(total_done / total_plan * 100, 1) if total_plan else None,
        },
    }


def build_overview_data(conn):
    """概览视图:KPI(总周数/完成率/训练日/动作数)+ 每周完成率列表"""
    config = _load_config(conn)
    if not config:
        return None
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_number FROM workout_plans ORDER BY week_number')
    week_numbers = [r[0] for r in c.fetchall()]
    weekly_rates = [_week_completion(conn, wn, config) for wn in week_numbers]
    total_plan = sum(w['plan_sets'] for w in weekly_rates)
    total_actual = sum(w['actual_sets'] for w in weekly_rates)
    overall_rate = round(total_actual / total_plan * 100, 1) if total_plan else None
    training_days = sum(w['plan_days'] for w in weekly_rates)
    c.execute('SELECT COUNT(*) FROM workout_plans WHERE is_rest_day=0')
    total_sessions = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM (SELECT json_extract(json_each.value, '$.name') FROM workout_plans, json_each(workout_plans.movements))")
    total_movements = c.fetchone()[0]
    return {
        'mode': 'overview',
        'config': config,
        'kpi': {
            'total_weeks': config['total_weeks'],
            'overall_rate': overall_rate,
            'training_days': training_days,
            'total_sessions': total_sessions,
            'total_movements': total_movements,
        },
        'weekly_rates': weekly_rates,
    }


def build_vs_data(conn, start_date=None, end_date=None):
    """计划 vs 实际:完成度 + 偏差 + 动作级对比表"""
    config = _load_config(conn)
    if not config:
        return None
    end = date.fromisoformat(end_date) if end_date else date.today()
    if start_date is None:
        start = end - timedelta(days=6)
    else:
        start = date.fromisoformat(start_date)
    c = conn.cursor()
    plan_rows = {}
    actual_rows = {}
    cur = start
    while cur <= end:
        day_str = cur.isoformat()
        wn = _calc_week_number(cur, config)
        if wn:
            dow = cur.isoweekday()
            c.execute('''
                SELECT movements, total_sets FROM workout_plans
                WHERE week_number=? AND day_of_week=? AND is_rest_day=0
            ''', (wn, dow))
            for r in c.fetchall():
                for m in (json.loads(r[0]) if r[0] else []):
                    name = m.get('name', '?')
                    plan_rows[name] = plan_rows.get(name, 0) + len(m.get('sets') or [])
        c.execute("SELECT exercise_type, COUNT(*) FROM exercise_log WHERE date=? GROUP BY exercise_type", (day_str,))
        for r in c.fetchall():
            actual_rows[r[0]] = actual_rows.get(r[0], 0) + r[1]
        cur += timedelta(days=1)
    movement_rows = []
    all_names = sorted(set(plan_rows) | set(actual_rows))
    for name in all_names:
        plan_sets = plan_rows.get(name, 0)
        act_sets = actual_rows.get(name, 0)
        dev = ((act_sets - plan_sets) / plan_sets * 100) if plan_sets else None
        movement_rows.append({
            'movement': name,
            'plan_sets': plan_sets,
            'actual_sets': act_sets,
            'deviation_pct': round(dev, 1) if dev is not None else None,
        })
    total_plan = sum(r['plan_sets'] for r in movement_rows)
    total_actual = sum(r['actual_sets'] for r in movement_rows)
    rate = round(total_actual / total_plan * 100, 1) if total_plan else None
    return {
        'mode': 'vs',
        'config': config,
        'start_date': start.isoformat(),
        'end_date': end.isoformat(),
        'completion_rate': rate,
        'deviation': round((rate or 0) - 100, 1),
        'movement_rows': movement_rows,
    }


def build_completion_data(conn):
    """完成率趋势:每周完成率折线"""
    config = _load_config(conn)
    if not config:
        return None
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_number FROM workout_plans ORDER BY week_number')
    weekly = [_week_completion(conn, wn, config) for wn in [r[0] for r in c.fetchall()]]
    return {'mode': 'completion', 'config': config, 'weekly': weekly}


def build_missed_data(conn, days=28):
    """未完成训练:漏练日期 + 应练动作列表"""
    config = _load_config(conn)
    if not config:
        return None
    start = date.today() - timedelta(days=days - 1)
    c = conn.cursor()
    missed = []
    cur = start
    while cur <= date.today():
        day_str = cur.isoformat()
        wn = _calc_week_number(cur, config)
        if wn:
            dow = cur.isoweekday()
            c.execute('''
                SELECT total_sets, movements FROM workout_plans
                WHERE week_number=? AND day_of_week=? AND is_rest_day=0
            ''', (wn, dow))
            rows = c.fetchall()
            if rows:
                c.execute('SELECT COUNT(*) FROM exercise_log WHERE date=?', (day_str,))
                done = c.fetchone()[0]
                plan_sets = sum(r[0] or 0 for r in rows)
                if done < plan_sets:
                    movements = []
                    for r in rows:
                        for m in (json.loads(r[1]) if r[1] else []):
                            movements.append(m.get('name', '?'))
                    missed.append({
                        'date': day_str,
                        'plan_week': wn,
                        'dow_label': ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][dow],
                        'plan_sets': plan_sets,
                        'done_sets': done,
                        'movements': movements,
                    })
        cur += timedelta(days=1)
    return {'mode': 'missed', 'config': config, 'days': days, 'missed': missed}


def build_movement_data(conn, days=28):
    """动作完成率:动作 TOP 榜"""
    config = _load_config(conn)
    if not config:
        return None
    start = date.today() - timedelta(days=days - 1)
    c = conn.cursor()
    plan_map = {}
    cur = start
    while cur <= date.today():
        wn = _calc_week_number(cur, config)
        if wn:
            c.execute('''
                SELECT movements FROM workout_plans
                WHERE week_number=? AND day_of_week=? AND is_rest_day=0
            ''', (wn, cur.isoweekday()))
            for r in c.fetchall():
                for m in (json.loads(r[0]) if r[0] else []):
                    name = m.get('name', '?')
                    plan_map[name] = plan_map.get(name, 0) + len(m.get('sets') or [])
        cur += timedelta(days=1)
    c.execute('''
        SELECT exercise_type, COUNT(*) FROM exercise_log
        WHERE date >= ? GROUP BY exercise_type
    ''', (start.isoformat(),))
    actual_map = dict(c.fetchall())
    ranking = []
    for name in sorted(plan_map):
        plan_sets = plan_map[name]
        done = min(actual_map.get(name, 0), plan_sets)
        ranking.append({
            'movement': name,
            'plan_sets': plan_sets,
            'done_sets': done,
            'rate': round(done / plan_sets * 100, 1) if plan_sets else None,
        })
    ranking.sort(key=lambda r: (r['rate'] is not None, r['rate'] if r['rate'] is not None else -1), reverse=True)
    return {'mode': 'movement', 'config': config, 'days': days, 'ranking': ranking}


def _build_review_data(conn):
    """可选:拉今日复盘数据填充 review section"""
    try:
        from analysis.exercise import exercise_review
        today_str = date.today().strftime('%Y-%m-%d')
        raw = exercise_review(today_str, today_str, silent=True)
        if not raw:
            return {'today': None}
        today_review = raw.get(today_str) or next(iter(raw.values()), None)
        if not today_review:
            return {'today': None}
        return {
            'today': {
                'date': today_review.get('date') or today_str,
                'completion_rate': today_review.get('completion_rate'),
                'sessions': today_review.get('sessions') or [],
                'plan_total_sets': today_review.get('plan_total_sets', 0),
                'actual_total_sets': today_review.get('actual_total_sets', 0),
                'anomalies': today_review.get('anomalies') or [],
                'note': today_review.get('note'),
            }
        }
    except Exception as e:
        print(f"⚠️ 复盘 section 渲染失败: {e}", file=sys.stderr)
        return {'today': None}


def _render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(
            f"模板占位符数量异常: 期望 1 个,实际 {template.count(placeholder)} 个\n"
            f"路径: {TEMPLATE_PATH}"
        )
    payload_obj = {
        'status': 'ok',
        'data': data,
        'message': '健身计划 HTML 已生成',
    }
    payload = json.dumps(payload_obj, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def render(mode='full', week=None, start_date=None, end_date=None, days=None,
           include_review=False, output_path=None):
    """主渲染函数"""
    conn = _get_db()
    try:
        builders = {
            'full': lambda: build_full_data(conn, focus_week=week),
            'week': lambda: build_week_data(conn, week),
            'today': lambda: build_today_data(conn),
            'day': lambda: build_day_data(conn, date.fromisoformat(start_date) if start_date else date.today()),
            'overview': lambda: build_overview_data(conn),
            'vs': lambda: build_vs_data(conn, start_date, end_date),
            'completion': lambda: build_completion_data(conn),
            'missed': lambda: build_missed_data(conn, days or 28),
            'movement': lambda: build_movement_data(conn, days or 28),
        }
        if mode not in builders:
            raise ValueError(f'未知 mode: {mode}')
        data = builders[mode]()
    finally:
        conn.close()

    if data is None:
        return "尚未制定健身计划。"

    # 2026-08-10 #255:统一注入 meta(排障日志 + 底部数据源行依赖)
    scene_names_inner = {
        'full': '看完整计划', 'week': '看周计划', 'today': '看今天练什么', 'day': '看某天练什么',
        'overview': '看计划概览', 'vs': '看计划vs实际', 'completion': '看计划完成率',
        'missed': '看未完成训练', 'movement': '看动作完成率',
    }
    from render_crud_view import _quote_arg
    data['meta'] = {
        'generated_at': date.today().isoformat(),
        'wake_word': scene_names_inner.get(mode, '健身计划'),
        'source': 'workout_plans',
        'chain': '(未注入)',
        'render_cmd': 'python scripts/render_workout_plan.py ' + ' '.join(_quote_arg(a) for a in sys.argv[1:]),
    }

    if include_review:
        conn2 = _get_db()
        try:
            data['review'] = _build_review_data(conn2)
        finally:
            conn2.close()

    html = _render_html(data)
    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
        return output_path

    scene_names = {
        'full': '看完整计划', 'week': '看周计划', 'today': '看今天练什么', 'day': '看某天练什么',
        'overview': '看计划概览', 'vs': '看计划vs实际', 'completion': '看计划完成率',
        'missed': '看未完成训练', 'movement': '看动作完成率',
    }
    default_path = html_path(SKILL_DIR, scene_names.get(mode, '健身计划'))
    default_path.write_text(html, encoding='utf-8')
    return str(default_path)


def main():
    p = argparse.ArgumentParser(
        description='渲染健身计划 HTML(多模式 · 2026-08-02 ticket #6)'
    )
    p.add_argument('-m', '--mode', default='full',
                   choices=['full', 'week', 'today', 'day', 'overview', 'vs', 'completion', 'missed', 'movement'],
                   help='渲染模式(full=全计划 / week=单周 / today=今日 / day=指定日期 / overview=概览 / vs=对比 / completion=完成率 / missed=漏练 / movement=动作榜)')
    p.add_argument('-w', '--week', type=int, help='周次(week 模式必用;full 模式可聚焦)')
    p.add_argument('--start', help='开始日期 YYYY-MM-DD(vs 模式) 或指定日期(day 模式)')
    p.add_argument('--end', help='结束日期 YYYY-MM-DD(vs 模式)')
    p.add_argument('--days', type=int, help='回溯天数(missed/movement 默认 28)')
    p.add_argument('--review', action='store_true', help='打开复盘 section(full 模式)')
    p.add_argument('-o', '--output', help='输出文件路径')
    args = p.parse_args()

    result = render(args.mode, args.week, args.start, args.end, args.days,
                    include_review=args.review, output_path=args.output)
    if isinstance(result, str) and not args.output:
        print(result)
    elif args.output:
        print(f'→ {result}')


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()
