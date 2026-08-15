#!/usr/bin/env python3
"""健身计划 HTML 渲染器(2026-08-02 重构:多模式 · ticket #6)

对应 SKILL.md 唤醒词:看完整计划 / 看本周计划 / 看下周计划 / 看上周计划 / 看指定周计划 / 看今天练什么 / 看某天练什么 / 看计划概览 / 看计划 vs 实际 / 看计划完成率 / 看未完成训练 / 看动作完成率 / 看某动作安排

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
  action    看某动作安排(按动作反查计划;--name <动作>,子串匹配 + 下次练习日 · #256)

设计:
- 渲染器只做:读数据 → 序列化 → 注入 → 输出
- DOM 渲染交给 JS(CSS / JS / HTML 骨架都在稳定模板里)
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次(注入器校验)
"""

from _base_render import envelope, inject_base, write_html  # noqa: E402
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

# === 场景名映射（#323） ===
# 10 个 mode 各自的 command_cn / wake_word / scene_id（Base 管线 scene.snapshot 元数据）
# 渲染器必须按 mode 填正确的 scene 名，否则复制数据头部永远是「看训练计划」
_SCENE_NAMES = {
    'full': '看完整计划',
    'week': '看周计划',
    'today': '看今天练什么',
    'day': '看某天练什么',
    'overview': '看计划概览',
    'vs': '看计划vs实际',
    'completion': '看计划完成率',
    'missed': '看未完成训练',
    'movement': '看动作完成率',
    'action': '看某动作安排',
}


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


def build_overview_data(conn, today=None):
    """概览视图:KPI(总周数/完成率/训练日/动作数)+ 周期剩余进度(#258)+ 每周完成率列表

    #258 周期剩余进度:按 config.start_date + total_weeks 计算
      - current_week: 当前处于周期第几周(线性真实周次,循环计划第 5 次 = 第 5 周)
      - remaining_weeks: 剩余完整周数(不含当前周)
      - remaining_training_days: 剩余周数 × 每周训练日数(基于计划实际非休息日)
      - period_status: active / unstarted / finished
      - today 参数可注入(测试固定日期,参考 #249 参考实现模式)
    """
    if today is None:
        today = date.today()
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
    # ---- #258 周期剩余进度 ----
    total_weeks = config['total_weeks']
    start = date.fromisoformat(config['start_date']) if config['start_date'] else None
    period = _period_progress(today, start, total_weeks, conn)
    return {
        'mode': 'overview',
        'config': config,
        'kpi': {
            'total_weeks': total_weeks,
            'overall_rate': overall_rate,
            'training_days': training_days,
            'total_sessions': total_sessions,
            'total_movements': total_movements,
            # #258 新增
            'current_week': period['current_week'],
            'remaining_weeks': period['remaining_weeks'],
            'remaining_training_days': period['remaining_training_days'],
            'period_status': period['status'],
            'period_start': config['start_date'],
            'period_end': period['end_date'],
        },
        'weekly_rates': weekly_rates,
    }


def _period_progress(today, start, total_weeks, conn):
    """周期剩余进度计算(线性真实周次,不取模)

    status:
      - unstarted: today < start_date
      - finished:  已过 start_date + total_weeks×7 天
      - active:    其余

    remaining_training_days(2026-08-11 #258 用户拍板 B · 精确到天):
      从「明天」起逐日数到周期结束,每天按循环周次映射回计划
      (real_week → plan_week = ((real_week-1)%total_weeks)+1, 查该周该天是否非休息日)。
      比「剩余完整周 × 每周训练日」更精确——用户改过某周训练结构时也能数对。
    """
    empty = {
        'status': 'unstarted', 'current_week': 0, 'remaining_weeks': total_weeks,
        'remaining_training_days': 0, 'end_date': '',
    }
    if not start or not total_weeks:
        return empty
    c = conn.cursor()
    # 计划内全部非休息日 (week_number, day_of_week) 集合
    c.execute('SELECT week_number, day_of_week FROM workout_plans WHERE is_rest_day=0')
    train_days = {(r[0], r[1]) for r in c.fetchall()}
    end_date = start + timedelta(days=total_weeks * 7 - 1)

    def _count_remaining(from_day):
        """from_day 起(含)到 end_date 之间的计划训练日数"""
        count = 0
        d = from_day
        while d <= end_date:
            real_week = ((d - start).days // 7) + 1
            plan_week = ((real_week - 1) % total_weeks) + 1
            if (plan_week, d.isoweekday()) in train_days:
                count += 1
            d += timedelta(days=1)
        return count

    if today < start:
        return {
            'status': 'unstarted', 'current_week': 0,
            'remaining_weeks': total_weeks,
            'remaining_training_days': _count_remaining(start),
            'end_date': end_date.isoformat(),
        }
    real_week = ((today - start).days // 7) + 1
    if real_week > total_weeks:
        return {
            'status': 'finished', 'current_week': total_weeks,
            'remaining_weeks': 0, 'remaining_training_days': 0,
            'end_date': end_date.isoformat(),
        }
    remaining_weeks = total_weeks - real_week
    return {
        'status': 'active', 'current_week': real_week,
        'remaining_weeks': remaining_weeks,
        'remaining_training_days': _count_remaining(today + timedelta(days=1)),
        'end_date': end_date.isoformat(),
    }


def build_vs_data(conn, start_date=None, end_date=None):
    """计划 vs 实际:完成度 + 偏差 + 动作级对比表(2026-08-10 #255: 入参已为 date 对象)"""
    config = _load_config(conn)
    if not config:
        return None
    end = end_date or date.today()
    if start_date is None:
        start = end - timedelta(days=6)
    else:
        start = start_date
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


def build_action_data(conn, name=None):
    """#256: 按动作反查计划(动作名 → 全部出现位置/频率/下次练习日)

    匹配策略: 先精确后子串(用户说「卧推」匹配计划「杠铃卧推」);无匹配 → 模糊候选(含任一关键字)
    下次练习日: 循环计划语义,从今天起按 (week, dow) 循环找最近一次"""
    config = _load_config(conn)
    if not config:
        return None
    if not name or not str(name).strip():
        return {'mode': 'action', 'config': config, 'query': '', 'error': '缺少动作名'}
    q = str(name).strip()
    c = conn.cursor()
    c.execute('''SELECT week_number, day_of_week, session_index, session_label, time_start, time_end, movements
                 FROM workout_plans WHERE is_rest_day=0 ORDER BY week_number, day_of_week, session_index''')
    positions = []
    all_names = set()
    for r in c.fetchall():
        for m in (json.loads(r[6]) if r[6] else []):
            mname = m.get('name', '')
            all_names.add(mname)
            sets = m.get('sets') or []
            nsets = len(sets)
            reps = sets[0].get('reps') if sets else None
            weight = sets[0].get('weight') if sets else None
            unit = sets[0].get('unit', 'kg') if sets else 'kg'
            part = m.get('part', '')
            hit = (mname == q) or (q in mname) or (mname in q)
            if hit:
                positions.append({
                    'week': r[0], 'day_of_week': r[1],
                    'dow_label': ['', '周一', '周二', '周三', '周四', '周五', '周六', '周日'][r[1]],
                    'session_label': r[3] or '', 'time': f"{r[4] or ''}-{r[5] or ''}",
                    'name': mname, 'part': part,
                    'sets': nsets, 'reps': reps, 'weight': weight, 'unit': unit,
                })
    if not positions:
        # 无匹配 → 模糊候选(含任一关键字)
        candidates = sorted(n for n in all_names if any(ch in n for ch in q))
        return {'mode': 'action', 'config': config, 'query': q,
                'positions': [], 'candidates': candidates[:6], 'error': f'计划中无「{q}」'}
    # 频率汇总: 按 (week, dow) 去重算每周出现次数(循环计划每周相同 → 每周 1 次)
    weekly_days = {(p['week'], p['day_of_week']) for p in positions}
    weeks_with = sorted({w for w, _ in weekly_days})
    # 下次练习日(从今天起,循环语义)
    today = date.today()
    next_date = None
    next_week = None
    for offset in range(0, 90):  # 最多看 90 天
        d = today + timedelta(days=offset)
        wn = _calc_week_number(d, config)
        if wn and (wn, d.isoweekday()) in weekly_days:
            next_date = d.isoformat()
            next_week = wn
            break
    total_sets = sum(p['sets'] for p in positions)
    parts = sorted({p['part'] for p in positions if p['part']})
    weights = [p['weight'] for p in positions if p['weight'] is not None]
    return {
        'mode': 'action', 'config': config, 'query': q,
        'positions': positions,
        'summary': {
            'weeks_with': len(weeks_with),
            'times_per_week': len(weekly_days) // len(weeks_with) if weeks_with else 0,
            'total_sets': total_sets,
            'parts': parts,
            'weight_min': min(weights) if weights else None,
            'weight_max': max(weights) if weights else None,
        },
        'next_date': next_date, 'next_week': next_week,
    }


# === Per-mode snapshot builders（#323 · scene.snapshot 注入） ===
# 任务：为 Base 管线 scene.snapshot 提供人类可读的全中文明细（旧 doCopy 等价物）
# 通用规则：
#   summary: 概览行(2-8 行)  · sections: [{heading, rows: [...]}]（按周/天/动作分组）
#   数据空时 summary 友好占位 + sections=[]，不要抛错
#   全中文人类可读，无 JSON 裸结构（与 buildDataText 契约一致）
# 设计：每个 mode 独立函数，便于扩展（#326 用户要求的「整体分析」如需新模式直接加）

def _fmt_rate(rate):
    """完成率: 0.0/None/数字 统一为人类可读字符串"""
    if rate is None:
        return '—'
    return f"{rate}%"


def _fmt_session_time(s):
    """训练段时间: '07:00-08:00' / 空段空串"""
    t1 = s.get('time_start') or ''
    t2 = s.get('time_end') or ''
    if t1 or t2:
        return f"{t1}-{t2}"
    return ''


def _fmt_movement_line(m):
    """动作行(全中文人类可读):
      '深蹲 · 腿 · 10次×50kg · 0/1 组'
    缺字段时省略对应段(空 part 就不显示 '· 腿')

    兼容两种数据形态(#323 对抗式审查发现):
      形态 1 (full/week/overview 等,来自 _load_week):
        m = {name, part, sets: [{reps, weight, unit}, ...]}
      形态 2 (today/day,来自 _build_day_data):
        m = {name, part, sets: N, sets_done, reps, weight, unit}
    形态 1 提取 sets[0].reps/weight,形态 2 直接读顶层字段。
    """
    name = m.get('name') or '?'
    part = f" · {m['part']}" if m.get('part') else ''
    sets_raw = m.get('sets')
    if isinstance(sets_raw, list) and sets_raw and not isinstance(m.get('reps'), (int, float)):
        # 形态 1: sets 是 list of {reps, weight, unit}
        s0 = sets_raw[0] or {}
        reps = s0.get('reps')
        weight = s0.get('weight')
        unit = s0.get('unit') or m.get('unit') or 'kg'
        sets_count = len(sets_raw)
        done = m.get('sets_done')
    else:
        # 形态 2: sets 是 int(组数), reps/weight 在顶层
        reps = m.get('reps')
        weight = m.get('weight')
        unit = m.get('unit') or 'kg'
        sets_count = sets_raw or 0
        done = m.get('sets_done')
    if reps is not None and weight is not None:
        sr = f" · {reps}次×{weight}{unit}"
    elif reps is not None:
        sr = f" · {reps}次"
    elif weight is not None:
        sr = f" · {weight}{unit}"
    else:
        sr = ''
    if sets_count and done is not None:
        progress = f" · {done}/{sets_count} 组"
    elif sets_count:
        progress = f" · {sets_count} 组"
    else:
        progress = ''
    return f"{name}{part}{sr}{progress}"


def _snapshot_full(data):
    """全计划: 标题 + 总周数/起始日 + 逐周逐天逐训练段的动作明细"""
    cfg = data.get('config') or {}
    title = cfg.get('title') or '健身计划'
    version = cfg.get('version') or ''
    total = cfg.get('total_weeks') or 0
    start = cfg.get('start_date') or ''
    summary = [
        f"计划: {title} {version} · 总周数 {total} · 起始 {start}".rstrip(),
    ]
    cw = data.get('current_week')
    if cw is not None:
        summary.append(f"当前周: 第 {cw} 周")
    weeks = data.get('weeks') or []
    sections = []
    for w in weeks:
        wn = w.get('week_number')
        rows = []
        for d in w.get('days') or []:
            dlbl = d.get('day_label') or ''
            sessions = d.get('sessions') or []
            if not sessions:
                rows.append(f"{dlbl} · 休息日")
                continue
            for s in sessions:
                if s.get('is_rest_day'):
                    rows.append(f"{dlbl} · 休息日")
                    continue
                t = _fmt_session_time(s)
                head = (f"{dlbl} · {t} · {s.get('session_label', '')} · "
                        f"{s.get('total_sets', 0)} 组").replace(' · · ', ' · ').strip(' ·')
                rows.append(head)
                for m in s.get('movements') or []:
                    rows.append(_fmt_movement_line(m))  # 去掉手写缩进:buildDataText 统一加 '  · '
        if rows:
            sections.append({"heading": f"第 {wn} 周", "rows": rows})
    if not sections:
        summary.append("尚无周计划")
    return summary, sections


def _snapshot_week(data):
    """单周: 完成度 + 7 天明细"""
    completion = data.get('completion') or {}
    weeks = data.get('weeks') or []
    if not weeks:
        return [f"第 {data.get('focus_week', '?')} 周 · 无数据"], []
    week = weeks[0]
    wn = week.get('week_number')
    rate = completion.get('completion_rate')
    plan = completion.get('plan_sets', 0)
    actual = completion.get('actual_sets', 0)
    summary = [f"第 {wn} 周 · 完成度 {_fmt_rate(rate)} ({actual}/{plan} 组)"]
    sections = []
    for d in week.get('days') or []:
        dlbl = d.get('day_label') or ''
        sessions = d.get('sessions') or []
        if not sessions:
            sections.append({"heading": dlbl, "rows": ["休息日"]})
            continue
        for s in sessions:
            if s.get('is_rest_day'):
                sections.append({"heading": dlbl, "rows": ["休息日"]})
                continue
            t = _fmt_session_time(s)
            head = (f"{t} · {s.get('session_label', '')} · {s.get('total_sets', 0)} 组").replace(' · · ', ' · ').strip(' ·')
            rows = [head] + [_fmt_movement_line(m) for m in s.get('movements') or []]  # 去掉手写缩进:buildDataText 统一加 '  · '
            sections.append({"heading": dlbl, "rows": rows})
    return summary, sections


def _snapshot_day(data):
    """今日/指定日: 训练段 + 动作 + 实时完成进度(today/day 共用)"""
    if data.get('unstarted'):
        return [f"{data.get('date', '')} · 计划尚未开始",
                f"起始: {data.get('start_date', '')}"], []
    if data.get('is_rest'):
        return [f"{data.get('date', '')} · 计划第 {data.get('plan_week', '?')} 周",
                "今日休息"], []
    date_str = data.get('date', '')
    pweek = data.get('plan_week')
    completion = data.get('completion') or {}
    rate = completion.get('rate')
    plan = completion.get('plan_sets', 0)
    done = completion.get('done_sets', 0)
    summary = [
        f"{date_str} · 计划第 {pweek} 周",
        f"完成度: {_fmt_rate(rate)} ({done}/{plan} 组)",
    ]
    sections = []
    for s in data.get('sessions') or []:
        if s.get('is_rest_day'):
            continue
        t = _fmt_session_time(s)
        head = (f"{s.get('session_label', '')} {t} · {s.get('total_sets', 0)} 组").replace(' · · ', ' · ').strip()
        rows = [head] + [_fmt_movement_line(m) for m in s.get('movements') or []]  # 去掉手写缩进:buildDataText 统一加 '  · '
        sections.append({"heading": s.get('session_label') or '训练段', "rows": rows})
    if not sections:
        summary.append("今日无训练安排")
    return summary, sections


# today 与 day 共享 snapshot 函数（#255 已合并）
_snapshot_today = _snapshot_day


def _snapshot_overview(data):
    """概览: KPI(总周数/完成率/训练日/动作数/当前周/剩余周/剩余训练日/周期状态)"""
    cfg = data.get('config') or {}
    kpi = data.get('kpi') or {}
    title = cfg.get('title') or '健身计划'
    summary = [
        f"计划: {title} · 总周数 {kpi.get('total_weeks', '?')}",
        f"整体完成率: {_fmt_rate(kpi.get('overall_rate'))} · 训练日 {kpi.get('training_days', '?')} · 动作 {kpi.get('total_movements', '?')} · 总 session {kpi.get('total_sessions', '?')}",
        f"当前周: 第 {kpi.get('current_week', '?')} 周 · 剩余周: {kpi.get('remaining_weeks', '?')} · 剩余训练日: {kpi.get('remaining_training_days', '?')}",
        f"周期: {kpi.get('period_start', '')} ~ {kpi.get('period_end', '')} · 状态: {kpi.get('period_status', '')}",
    ]
    weekly = data.get('weekly_rates') or []
    sections = []
    if weekly:
        rows = []
        for w in weekly:
            rows.append(
                f"第 {w.get('week_number', '?')} 周 · {_fmt_rate(w.get('completion_rate'))} "
                f"({w.get('actual_sets', 0)}/{w.get('plan_sets', 0)} 组 · 训练日 {w.get('plan_days', 0)})"
            )
        sections.append({"heading": "每周完成率", "rows": rows})
    return summary, sections


def _snapshot_vs(data):
    """vs: 完成度/偏差 + 动作级对比行"""
    rate = data.get('completion_rate')
    dev = data.get('deviation')
    sd = data.get('start_date', '')
    ed = data.get('end_date', '')
    summary = [
        f"区间: {sd} ~ {ed}",
        f"完成度: {_fmt_rate(rate)} · 偏差: {dev if dev is not None else '—'}%",
    ]
    rows = []
    for r in data.get('movement_rows') or []:
        devv = r.get('deviation_pct')
        devv_s = f"{devv}%" if devv is not None else '—'
        rows.append(
            f"{r.get('movement', '?')} · 计划 {r.get('plan_sets', 0)} 组 · "
            f"实做 {r.get('actual_sets', 0)} 组 · 偏差 {devv_s}"
        )
    sections = [{"heading": "动作级对比", "rows": rows}] if rows else []
    return summary, sections


def _snapshot_completion(data):
    """完成率: 每周完成率列表"""
    weekly = data.get('weekly') or []
    if not weekly:
        return ["尚无周完成率数据"], []
    summary = ["每周完成率"]
    rows = [
        f"第 {w.get('week_number', '?')} 周 · {_fmt_rate(w.get('completion_rate'))} "
        f"({w.get('actual_sets', 0)}/{w.get('plan_sets', 0)} 组)"
        for w in weekly
    ]
    return summary, [{"heading": "每周完成率", "rows": rows}]


def _snapshot_missed(data):
    """漏练: 漏练日期 + 应练动作 + 计划/实做组数"""
    days = data.get('days', 28)
    missed = data.get('missed') or []
    summary = [f"近 {days} 天漏练 {len(missed)} 天"]
    sections = []
    for m in missed:
        head = (f"{m.get('date', '')} · 第 {m.get('plan_week', '?')} 周{m.get('dow_label', '')} · "
                f"应练 {m.get('plan_sets', 0)} 组 · 实做 {m.get('done_sets', 0)} 组")
        rows = [head] + [n for n in (m.get('movements') or [])]  # 去掉手写缩进:buildDataText 统一加 '  · '
        sections.append({"heading": m.get('date', ''), "rows": rows})
    if not sections:
        summary.append("无漏练，保持得很好！")
    return summary, sections


def _snapshot_movement(data):
    """动作完成率: 动作 TOP 榜(名次/完成率/实做/计划组数)"""
    days = data.get('days', 28)
    ranking = data.get('ranking') or []
    if ranking:
        plan_total = sum(r.get('plan_sets', 0) for r in ranking)
        done_total = sum(r.get('done_sets', 0) for r in ranking)
        rate = round(done_total / plan_total * 100, 1) if plan_total else None
    else:
        rate = None
    summary = [f"近 {days} 天动作 {len(ranking)} 个", f"总完成率: {_fmt_rate(rate)}"]
    rows = []
    for i, r in enumerate(ranking, 1):
        rows.append(
            f"#{i} {r.get('movement', '?')} · 完成率 {_fmt_rate(r.get('rate'))} · "
            f"实做 {r.get('done_sets', 0)}/{r.get('plan_sets', 0)} 组"
        )
    sections = [{"heading": "动作 TOP 榜", "rows": rows}] if rows else []
    return summary, sections


def _snapshot_action(data):
    """动作反查: 出现位置 + 频率 + 下次练习日 + 总组数 + 部位 + 重量区间"""
    if data.get('error'):
        return [f"动作: {data.get('query', '')}", f"提示: {data['error']}"], []
    if data.get('candidates'):
        cand = '、'.join(data['candidates'])
        return [f"动作: {data.get('query', '')}", "未找到完全匹配", f"候选: {cand}"], []
    summary_data = data.get('summary') or {}
    query = data.get('query', '')
    parts = summary_data.get('parts') or []
    parts_s = '、'.join(parts) if parts else '—'
    weight_min = summary_data.get('weight_min')
    weight_max = summary_data.get('weight_max')
    weight_s = (f"{weight_min}-{weight_max}kg"
                if (weight_min is not None and weight_max is not None) else '—')
    summary = [
        f"动作: {query}",
        f"出现: {summary_data.get('weeks_with', '?')} 周 · 频率 {summary_data.get('times_per_week', '?')} 次/周 · 总组数 {summary_data.get('total_sets', '?')}",
        f"部位: {parts_s} · 重量: {weight_s}",
        f"下次练习日: {data.get('next_date', '—')} (第 {data.get('next_week', '?')} 周)",
    ]
    rows = []
    for p in data.get('positions') or []:
        head = (f"第 {p.get('week', '?')} 周{p.get('dow_label', '')} · "
                f"{p.get('session_label', '')} {p.get('time', '')} · {p.get('sets', 0)} 组").replace('  ', ' ').strip()
        detail = _fmt_movement_line({
            "name": p.get('name', ''),
            "part": p.get('part', ''),
            "reps": p.get('reps'),
            "weight": p.get('weight'),
            "unit": p.get('unit', 'kg'),
            "sets": p.get('sets', 0),
        })
        rows.append(head)
        rows.append(detail)  # 去掉手写缩进:buildDataText 统一加 '  · '
    sections = [{"heading": "出现位置", "rows": rows}] if rows else []
    return summary, sections


# mode → snapshot 调度表（#323 修复点）
# _render_html 用此表按 mode 取对应 builder，注入 scene.snapshot
_SNAPSHOT_BUILDERS = {
    'full': _snapshot_full,
    'week': _snapshot_week,
    'today': _snapshot_today,
    'day': _snapshot_day,
    'overview': _snapshot_overview,
    'vs': _snapshot_vs,
    'completion': _snapshot_completion,
    'missed': _snapshot_missed,
    'movement': _snapshot_movement,
    'action': _snapshot_action,
}


def _render_html(data: dict, mode: str = 'full') -> str:
    """读模板 + Base 管线注入（#323：显式传 summary/sections 给 envelope，覆盖 auto_snapshot 空壳）

    为何不调 render_template：render_template 内部 envelope 调用不转发
    summary/sections kwargs（_base_render.py L186-214），会再次落入 auto_snapshot
    空壳。直接 envelope() + inject_base() 等价 render_template 的 status='ok' 分支。
    """
    command_cn = _SCENE_NAMES.get(mode, '看训练计划')
    wake_word = command_cn  # scene 名即唤醒词（Base 头部一致）
    builder = _SNAPSHOT_BUILDERS.get(mode, _snapshot_full)
    summary, sections = builder(data)
    envelope(data, command_cn, wake_word=wake_word,
             render_cmd=(data.get('meta') or {}).get('render_cmd', '（本地渲染）'),
             summary=summary, sections=sections,
             scene_id=command_cn)
    payload = {'status': 'ok', 'data': data, 'message': '健身计划 HTML 已生成'}
    template_text = TEMPLATE_PATH.read_text(encoding='utf-8')
    return inject_base(template_text, payload)


def render(mode='full', week=None, start_date=None, end_date=None, days=None, day_date=None, action_name=None,
           include_review=False, output_path=None):
    """主渲染函数"""
    conn = _get_db()
    # 2026-08-10 #255 审查: 日期参数统一预解析(day 用 --date;vs 用 --start/--end),非法值返回友好错误
    def _parse_d(v):
        if not v:
            return None
        try:
            return date.fromisoformat(str(v))
        except ValueError:
            raise ValueError(f'日期格式无效: {v!r}(应为 YYYY-MM-DD)')
    try:
        day_d = _parse_d(day_date)
        vs_start = _parse_d(start_date)
        vs_end = _parse_d(end_date)
        builders = {
            'full': lambda: build_full_data(conn, focus_week=week),
            'week': lambda: build_week_data(conn, week),
            'today': lambda: build_today_data(conn),
            'day': lambda: build_day_data(conn, day_d or date.today()),
            'overview': lambda: build_overview_data(conn),
            'vs': lambda: build_vs_data(conn, vs_start, vs_end),
            'completion': lambda: build_completion_data(conn),
            'missed': lambda: build_missed_data(conn, days or 28),
            'movement': lambda: build_movement_data(conn, days or 28),
            'action': lambda: build_action_data(conn, action_name),
        }
        if mode not in builders:
            raise ValueError(f'未知 mode: {mode}')
        data = builders[mode]()
    except ValueError as e:
        # 2026-08-10 #255 审查: 非法参数 → 友好错误(不再裸 traceback)
        return f'⚠️ {e}'
    finally:
        conn.close()

    if data is None:
        return "尚未制定健身计划。"

    # 2026-08-10 #255:统一注入 meta(排障日志 + 底部数据源行依赖)
    # 2026-08-13 #323:wake_word 来自模块级 _SCENE_NAMES,与 command_cn 一致(避免硬编码「看训练计划」)
    from render_crud_view import _quote_arg
    data['meta'] = {
        'generated_at': date.today().isoformat(),
        'wake_word': _SCENE_NAMES.get(mode, '看训练计划'),
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

    # 2026-08-13 #323:显式传 mode 给 _render_html,scene 名按 mode 切换 + 注入 per-mode snapshot
    html = _render_html(data, mode)
    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
        return output_path

    default_path = html_path(SKILL_DIR, _SCENE_NAMES.get(mode, '看训练计划'))
    write_html(html, default_path)
    return str(default_path)


def main():
    p = argparse.ArgumentParser(
        description='渲染健身计划 HTML(多模式 · 2026-08-02 ticket #6)'
    )
    p.add_argument('-m', '--mode', default='full',
                   choices=['full', 'week', 'today', 'day', 'overview', 'vs', 'completion', 'missed', 'movement', 'action'],
                   help='渲染模式(full=全计划 / week=单周 / today=今日 / day=指定日期 / overview=概览 / vs=对比 / completion=完成率 / missed=漏练 / movement=动作榜)')
    p.add_argument('-w', '--week', type=int, help='周次(week 模式必用;full 模式可聚焦)')
    p.add_argument('--date', help='目标日期 YYYY-MM-DD(day 模式;默认今天)')
    p.add_argument('--name', help='动作名(action 模式,支持子串匹配)')
    p.add_argument('--start', help='开始日期 YYYY-MM-DD(vs 模式)')
    p.add_argument('--end', help='结束日期 YYYY-MM-DD(vs 模式)')
    p.add_argument('--days', type=int, help='回溯天数(missed/movement 默认 28)')
    p.add_argument('--review', action='store_true', help='打开复盘 section(full 模式)')
    p.add_argument('-o', '--output', help='输出文件路径')
    args = p.parse_args()

    result = render(args.mode, args.week, args.start, args.end, args.days, day_date=args.date, action_name=args.name,
                    include_review=args.review, output_path=args.output)
    if isinstance(result, str) and not args.output:
        print(result)
    elif args.output:
        print(f'→ {result}')


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()
