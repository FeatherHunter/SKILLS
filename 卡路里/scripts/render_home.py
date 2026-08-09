#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_home.py — 卡路里主面板 HTML 渲染器(主页 9 场景 · ticket #2)

对应 SKILL.md 唤醒词: 看今日主页 / 看今日饮食概览 / 看今日运动概览 / 看今日体重概览 /
看今日目标进度 / 看本周主页 / 看本月主页 / 看连续记录天数 / 看今日热量预算
(aliases: 开卡路里 / 卡路里面板 / 今日卡路里 → 看今日主页)

设计原则(R1-R8 · #8 经验沉淀 2026-08-02):
- R4 自描述:渲染器按 --section/--period 推断场景名(meta.wake_word),不依赖外部传参
- R3 思考链:--chain 必传(live 模式),注入 meta.chain(复制日志可带出),未传→报错 exit2
- R5 命名:输出 <场景名>_结果_<TS>.html,统一 html_scene_path() 入口
- R1 视图分离:UI 只放用户数据;原始聚合留在 __DATA__
- R6 呈现完整:每视图含真实数值 + 一句话总结
- R8 移动端:6 KPI 卡 2x3 网格(模板 CSS 控制)

用法:
    python scripts/render_home.py [--date YYYY-MM-DD]
        [--section {diet,exercise,weight,goals,streak,budget}]
        [--period {week,month}]
        --chain "1.识别→2.读DB聚合→3.渲染"   # 必填
        [--output <path>] [--wake-word <场景名>]
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'home_dashboard.html'

sys.path.insert(0, str(SCRIPT_DIR))
from analysis import dashboard
from analysis._utils import calc_tdee
from _triggers import TRIGGERS
from db import find_db_path, get_db
from html_paths import html_scene_path

# 场景名 → 参数映射(R4 自描述 · 2026-08-02 ticket #2)
VIEW_SCENES = {
    'overview': '看今日主页',
    'diet': '看今日饮食概览',
    'exercise': '看今日运动概览',
    'weight': '看今日体重概览',
    'goals': '看今日目标进度',
    'week': '看本周主页',
    'month': '看本月主页',
    'streak': '看连续记录天数',
    'budget': '看今日热量预算',
}


def _chain_valid(chain):
    """思考链有效性校验(R3 · 与 render_crud_view 同规则)"""
    chain = (chain or '').strip()
    if len(chain) < 8:
        return False
    if not any(m in chain for m in ('→', '->', '1.', '1、', '2.', '第一步')):
        return False
    if chain.lower() in ('x', 'xx', 'xxx', '思考链', 'chain', '无', 'none'):
        return False
    return True


def _quote_arg(a: str) -> str:
    """参数加引号(含空格/特殊字符),保证 render_cmd 可复制直接执行(C10)"""
    if not a:
        return '""'
    if any(ch in a for ch in (' ', '"', "'", '\\', '&', '|', '>', '<', '(', ')')):
        return '"' + a.replace('"', '\\"') + '"'
    return a


def _goal_row():
    """读 daily_goal(id=1)"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    c = conn.cursor()
    row = c.execute('SELECT * FROM daily_goal WHERE id = 1').fetchone()
    if not row:
        conn.close()
        return None
    cols = [d[0] for d in c.description]
    conn.close()
    return dict(zip(cols, row))


def _today_actual(target_date: str) -> dict:
    """今日 food_log 实际聚合(热量/蛋白/饮水 ml)"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    row = conn.execute('''
        SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
               COALESCE(SUM(grams),0)
        FROM food_log WHERE date = ? AND food_name = '💧水'
    ''', (target_date,)).fetchone()
    cal = conn.execute('SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0) FROM food_log WHERE date = ?',
                       (target_date,)).fetchone()
    conn.close()
    return {'calorie': cal[0], 'protein': cal[1], 'water': row[2]}


def _pct(actual, goal):
    return round(actual / goal * 100, 1) if goal else None


def _today_exercise(target_date: str) -> dict:
    """今日运动聚合(消耗/时长)"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    row = conn.execute('''
        SELECT COALESCE(SUM(calories_burned),0), COALESCE(SUM(duration_minutes),0), COUNT(*)
        FROM exercise_log WHERE date = ?
    ''', (target_date,)).fetchone()
    conn.close()
    return {'burn': row[0], 'minutes': row[1], 'count': row[2]}


def _streak(target_date: str) -> dict:
    """连续记录天数:最近连续 N 天(饮食/饮水/运动/体重任一项)有记录 + 历史最长"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    d = date.fromisoformat(target_date)
    # 从目标日往前数,任一项有记录即算连续
    cur = 0
    cursor = d
    while True:
        ds = cursor.isoformat()
        food = conn.execute('SELECT COUNT(*) FROM food_log WHERE date = ?', (ds,)).fetchone()[0]
        ex = conn.execute('SELECT COUNT(*) FROM exercise_log WHERE date = ?', (ds,)).fetchone()[0]
        wt = conn.execute('SELECT COUNT(*) FROM weight_log WHERE date = ?', (ds,)).fetchone()[0]
        if food == 0 and ex == 0 and wt == 0:
            break
        cur += 1
        cursor -= timedelta(days=1)
        if cur > 4000:
            break
    # 历史最长:全表扫描连续段(简化:按日期去重后找最长连续)
    rows = conn.execute('SELECT DISTINCT date FROM food_log').fetchall()
    rows += conn.execute('SELECT DISTINCT date FROM exercise_log').fetchall()
    rows += conn.execute('SELECT DISTINCT date FROM weight_log').fetchall()
    conn.close()
    days = sorted({r[0] for r in rows})
    longest = 0
    run = 0
    prev = None
    for ds in days:
        dd = date.fromisoformat(ds)
        if prev is not None and (dd - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = dd
    return {'current': cur, 'longest': longest}


def _week_trend(target_date: str, days: int = 7) -> dict:
    """最近 N 天趋势(饮食热量 + 体重)供主页趋势小图"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    d = date.fromisoformat(target_date)
    trend = []
    for i in range(days - 1, -1, -1):
        ds = (d - timedelta(days=i)).isoformat()
        row = conn.execute('SELECT COALESCE(SUM(calories),0) FROM food_log WHERE date = ?', (ds,)).fetchone()
        cal = row[0]
        wrow = conn.execute('SELECT weight_kg FROM weight_log WHERE date = ? ORDER BY time DESC LIMIT 1', (ds,)).fetchone()
        trend.append({'date': ds, 'calories': cal, 'weight': wrow[0] if wrow else None})
    conn.close()
    return trend


def _period_range(period: str, target_date: str) -> tuple:
    """周期范围:week=本周一..今天;month=本月1号..今天"""
    d = date.fromisoformat(target_date)
    if period == 'week':
        start = d - timedelta(days=d.isoweekday() - 1)
    elif period == 'month':
        start = d.replace(day=1)
    else:
        start = d
    return start.isoformat(), target_date


def _period_summary(period: str, start: str, end: str) -> dict:
    """周期聚合(饮食/运动累计 + 体重趋势)"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    diet = conn.execute('''
        SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0), COUNT(DISTINCT date)
        FROM food_log WHERE date BETWEEN ? AND ?
    ''', (start, end)).fetchone()
    ex = conn.execute('''
        SELECT COALESCE(SUM(calories_burned),0), COALESCE(SUM(duration_minutes),0), COUNT(DISTINCT date)
        FROM exercise_log WHERE date BETWEEN ? AND ?
    ''', (start, end)).fetchone()
    wt = conn.execute('''
        SELECT MIN(date), MAX(date) FROM weight_log WHERE date BETWEEN ? AND ?
    ''', (start, end)).fetchone()
    wstart = wend = None
    if wt[0] and wt[1] and wt[0] != wt[1]:
        a = conn.execute('SELECT weight_kg FROM weight_log WHERE date = ? ORDER BY time ASC LIMIT 1', (wt[0],)).fetchone()
        b = conn.execute('SELECT weight_kg FROM weight_log WHERE date = ? ORDER BY time DESC LIMIT 1', (wt[1],)).fetchone()
        if a and b:
            wstart, wend = a[0], b[0]
    conn.close()
    return {
        'diet_calories': diet[0], 'diet_protein': diet[1], 'diet_days': diet[2],
        'exercise_burn': ex[0], 'exercise_minutes': ex[1], 'exercise_days': ex[2],
        'weight_start': wstart, 'weight_end': wend,
    }


def _budget(target_date: str) -> dict:
    """今日热量预算:TDEE(档案) + 运动消耗 + 已摄入 + 剩余可吃"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    prof = conn.execute('SELECT height_cm, age, gender, activity_level FROM user_profile WHERE id = 1').fetchone()
    wt = conn.execute('SELECT weight_kg FROM weight_log WHERE date <= ? ORDER BY date DESC, time DESC LIMIT 1',
                      (target_date,)).fetchone()
    conn.close()
    tdee = None
    if prof and wt:
        try:
            tdee = round(calc_tdee(wt[0], prof[0] or 170, prof[1] or 30, prof[2] or 'male', prof[3] or 'moderate'))
        except Exception:
            tdee = None
    act = _today_actual(target_date)
    ex = _today_exercise(target_date)
    remaining = (tdee + ex['burn'] - act['calorie']) if tdee is not None else None
    return {'tdee': tdee, 'exercise_burn': ex['burn'], 'intake': act['calorie'], 'remaining': remaining}


def build_today_status(target_date: str) -> dict:
    """检测今日是否记录了 饮食/饮水/运动/体重(含 H1.4/H1.5 扩展 · 2026-08-02)"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    c = conn.cursor()

    c.execute('SELECT COUNT(*), COALESCE(SUM(calories), 0) FROM food_log WHERE date = ?', (target_date,))
    food_count, food_cal = c.fetchone()

    c.execute('SELECT COUNT(*), COALESCE(SUM(calories), 0) FROM food_log WHERE date = ? AND food_name LIKE ?',
              (target_date, '%水%'))
    water_count, water_cal = c.fetchone()

    c.execute('SELECT COUNT(*), COALESCE(SUM(calories_burned), 0) FROM exercise_log WHERE date = ?', (target_date,))
    exercise_count, exercise_cal = c.fetchone()

    c.execute('SELECT COUNT(*) FROM weight_log WHERE date = ?', (target_date,))
    weight_count = c.fetchone()[0]

    # H1.4 对接(ticket #4 Success Criteria #5):体重 widget 显示实际数值
    c.execute('SELECT weight_kg FROM weight_log WHERE date = ? ORDER BY time DESC LIMIT 1', (target_date,))
    w_row = c.fetchone()
    latest_kg = w_row[0] if w_row else None
    c.execute('SELECT weight_goal FROM daily_goal WHERE id = 1')
    g = c.fetchone()
    goal_kg = g[0] if g and g[0] else None
    week_ago = (date.fromisoformat(target_date) - timedelta(days=7)).isoformat()
    c.execute('SELECT weight_kg FROM weight_log WHERE date <= ? ORDER BY date DESC, time DESC LIMIT 1', (week_ago,))
    prev = c.fetchone()
    delta_7d = round(latest_kg - prev[0], 1) if latest_kg is not None and prev else None
    goal_diff = round(latest_kg - goal_kg, 1) if latest_kg is not None and goal_kg is not None else None

    # 健身计划待办对接(ticket #6 Success Criteria #5):今日有训练计划但实绩不足 → 待办
    workout_todo = False
    try:
        from workout_plan import calc_plan_week, get_plan_config
        cfg = get_plan_config()
        if cfg:
            td = date.fromisoformat(target_date)
            wn = calc_plan_week(td, cfg)
            if wn is not None:
                c.execute('''
                    SELECT COALESCE(SUM(total_sets),0) FROM workout_plans
                    WHERE week_number=? AND day_of_week=? AND is_rest_day=0
                ''', (wn, td.isoweekday()))
                plan_sets = c.fetchone()[0]
                if plan_sets > 0:
                    c.execute('SELECT COUNT(*) FROM exercise_log WHERE date = ?', (target_date,))
                    done_sets = c.fetchone()[0]
                    if done_sets < plan_sets:
                        workout_todo = True
    except Exception:
        pass  # 计划未配置/异常时静默跳过,不影响主页

    conn.close()

    todo = []
    if food_count == 0:
        todo.append({'key': 'food', 'label': '记录饮食', 'priority': 'high'})
    if water_count == 0:
        todo.append({'key': 'water', 'label': '记录饮水', 'priority': 'medium'})
    if exercise_count == 0:
        todo.append({'key': 'exercise', 'label': '记录运动', 'priority': 'low'})
    if weight_count == 0:
        todo.append({'key': 'weight', 'label': '记录体重', 'priority': 'low'})
    if workout_todo:
        todo.append({'key': 'workout', 'label': '完成今日训练', 'priority': 'high'})

    return {
        'food': {'count': food_count, 'calories': int(food_cal)},
        'water': {'count': water_count, 'calories': int(water_cal)},
        'exercise': {'count': exercise_count, 'calories': int(exercise_cal)},
        'weight': {'count': weight_count, 'latest_kg': latest_kg, 'goal_kg': goal_kg,
                   'goal_diff': goal_diff, 'delta_7d': delta_7d},
        'workout': {'todo': workout_todo},
        'todo': todo,
    }


def build_recent_logs(target_date: str, limit: int = 5) -> dict:
    """最近 5 条记录"""
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    c = conn.cursor()

    c.execute('''
        SELECT time, food_name, calories, protein
        FROM food_log WHERE date = ?
        ORDER BY time DESC LIMIT ?
    ''', (target_date, limit))
    foods = [{'time': r[0], 'name': r[1], 'calories': r[2], 'protein': r[3]} for r in c.fetchall()]

    c.execute('''
        SELECT time, exercise_type, calories_burned, duration_minutes
        FROM exercise_log WHERE date = ?
        ORDER BY time DESC LIMIT ?
    ''', (target_date, limit))
    exercises = [{'time': r[0], 'type': r[1], 'calories': r[2], 'minutes': r[3]} for r in c.fetchall()]

    conn.close()
    return {'foods': foods, 'exercises': exercises}


QUICK_ACTIONS = [
    {'label': '记录饮食',    'wake_word': '记一餐',       'command': 'python scripts/render_crud_receipt.py --live-diet-add ...'},
    {'label': '查今日吃',    'wake_word': '看今日饮食',   'command': 'python scripts/render_today_diet.py'},
    {'label': '记录运动',    'wake_word': '记运动',       'command': 'python scripts/exercise_tracker.py add ...'},
    {'label': '查健康报告',  'wake_word': '查健康报告',   'command': 'python scripts/render_health_dashboard.py --days 7'},
    {'label': '查热量趋势',  'wake_word': '查热量趋势',   'command': 'python scripts/render_health_dashboard.py --days 30'},
    {'label': '查食物排行',  'wake_word': '查食物排行',   'command': 'python scripts/render_food_ranking.py --all'},
    {'label': '扫禁忌',      'wake_word': '扫禁忌',       'command': 'python scripts/render_contraindication.py'},
    {'label': '复盘',        'wake_word': '复盘',         'command': 'python scripts/render_review.py'},
]


def _attach_prompts(actions):
    """对每个 quick_action,按 wake_word 查 TRIGGERS,附加 prompt 字段。

    prompt 优先用于前端展示与复制;command 作为 fallback。
    """
    wake_to_prompt = {t['wake_word']: t['main_prompt']['text'] for t in TRIGGERS}
    out = []
    for a in actions:
        wake = a.get('wake_word', '')
        prompt = wake_to_prompt.get(wake, '') if wake else ''
        out.append({**a, 'prompt': prompt, 'wake_word': wake})
    return out


def build_data(target_date: str, view: str = 'overview', period: str = None) -> dict:
    """组装主面板数据契约(view 决定渲染哪个场景视图)"""
    dash_data = dashboard(target_date, target_date, as_dict=True)
    data = {
        'date': target_date,
        'view': view,
        'dashboard': dash_data['data'],
        'today_status': build_today_status(target_date),
        'recent_logs': build_recent_logs(target_date),
        'quick_actions': _attach_prompts(QUICK_ACTIONS),
    }

    # 各 section 视图数据(R6 呈现数据完整性 · ticket #2)
    if view == 'overview':
        # 权威清单 §1:6 张 KPI 卡(饮食/运动/体重/目标/进度/连续)+ 趋势小图 + 一句话
        goal = _goal_row() or {}
        act = _today_actual(target_date)
        ex = _today_exercise(target_date)
        w = data['today_status']['weight']
        st = _streak(target_date)
        goal_items = [
            {'label': '热量', 'goal': goal.get('calorie_goal'), 'actual': act['calorie'],
             'pct': _pct(act['calorie'], goal.get('calorie_goal'))},
            {'label': '蛋白', 'goal': goal.get('protein_goal'), 'actual': act['protein'],
             'pct': _pct(act['protein'], goal.get('protein_goal'))},
            {'label': '饮水', 'goal': goal.get('water_goal'), 'actual': act['water'],
             'pct': _pct(act['water'], goal.get('water_goal'))},
            {'label': '运动', 'goal': goal.get('exercise_goal'), 'actual': ex['burn'],
             'pct': _pct(ex['burn'], goal.get('exercise_goal'))},
        ]
        done = sum(1 for it in goal_items if it['pct'] is not None and it['pct'] >= 100)
        progress_pct = round(done / len(goal_items) * 100) if goal_items else 0
        # 2026-08-09 信息重复审查:目标卡=达标计数(结果维度),进度卡=记录完整度(过程维度),语义分离
        ts_now = data['today_status']
        recorded = sum(1 for k in ('food', 'water', 'exercise', 'weight') if ts_now[k]['count'] > 0)
        record_pct = round(recorded / 4 * 100) if goal_items else 0
        missing_labels = [t['label'] for t in ts_now['todo']]
        kpis = [
            {'key': 'diet', 'label': '饮食', 'icon': '🔥', 'value': act['calorie'], 'unit': '卡',
             'detail': f"目标 {goal.get('calorie_goal') or '—'} 卡",
             'pct': _pct(act['calorie'], goal.get('calorie_goal'))},
            {'key': 'exercise', 'label': '运动', 'icon': '🏃', 'value': ex['burn'], 'unit': '卡',
             'detail': f"{ex['minutes'] or 0} 分钟 · {ex['count'] or 0} 条",
             'pct': _pct(ex['burn'], goal.get('exercise_goal'))},
            {'key': 'weight', 'label': '体重', 'icon': '⚖️', 'value': w['latest_kg'] if w['latest_kg'] is not None else '—', 'unit': 'kg',
             'detail': (f"距目标 {w['goal_diff']:+.1f} kg" if w['goal_diff'] is not None else '未设目标')
                       + (f" · Δ7天 {w['delta_7d']:+.1f} kg" if w['delta_7d'] is not None else ''),
             'pct': None},
            {'key': 'goal', 'label': '目标', 'icon': '🎯', 'value': f"{done}/4", 'unit': '项达标',
             'detail': '热量/蛋白/饮水/运动', 'pct': progress_pct},
            {'key': 'progress', 'label': '进度', 'icon': '📊', 'value': f"{recorded}/4", 'unit': '类已记录',
             'detail': ('缺 ' + '、'.join(missing_labels)) if missing_labels else '',
             'pct': record_pct},
            {'key': 'streak', 'label': '连续', 'icon': '🔥', 'value': st['current'], 'unit': '天',
             'detail': f"历史最长 {st['longest']} 天", 'pct': None},
        ]
        # 一句话总结(2026-08-09 信息重复审查:判断句 · 不复述卡片数字 · KPI 卡=唯一事实源)
        judge = []
        cp = _pct(act['calorie'], goal.get('calorie_goal'))
        ep = _pct(ex['burn'], goal.get('exercise_goal'))
        if cp is not None:
            judge.append('热量已达标' if cp >= 100 else '热量接近达标' if cp >= 80 else '热量偏少')
        if ep is not None:
            judge.append('运动超额完成' if ep >= 100 else '运动已达标' if ep >= 80 else '运动偏少')
        if w['latest_kg'] is not None and w['delta_7d'] is not None:
            judge.append('近7天体重' + ('下降' if w['delta_7d'] < 0 else '上升' if w['delta_7d'] > 0 else '持平'))
        summary = ' · '.join(judge) if judge else '今天还没有记录,从记一餐开始吧。'
        data['home'] = {'kpis': kpis, 'trend': _week_trend(target_date), 'summary': summary}
    elif view == 'diet':
        goal = _goal_row() or {}
        act = _today_actual(target_date)
        data['diet'] = {
            'calories': act['calorie'],
            'protein': act['protein'],
            'goal_cal': goal.get('calorie_goal'),
            'goal_protein': goal.get('protein_goal'),
            'cal_pct': _pct(act['calorie'], goal.get('calorie_goal')),
            'protein_pct': _pct(act['protein'], goal.get('protein_goal')),
        }
    elif view == 'exercise':
        ex = _today_exercise(target_date)
        goal = _goal_row() or {}
        data['exercise'] = {
            'burn': ex['burn'],
            'minutes': ex['minutes'],
            'count': ex['count'],
            'goal': goal.get('exercise_goal'),
            'pct': _pct(ex['burn'], goal.get('exercise_goal')),
        }
    elif view == 'weight':
        w = data['today_status']['weight']
        data['weight'] = {
            'latest_kg': w['latest_kg'],
            'goal_kg': w['goal_kg'],
            'goal_diff': w['goal_diff'],
            'delta_7d': w['delta_7d'],
        }
    elif view == 'goals':
        goal = _goal_row() or {}
        act = _today_actual(target_date)
        ex = _today_exercise(target_date)
        items = [
            {'label': '热量', 'goal': goal.get('calorie_goal'), 'actual': act['calorie'],
             'pct': _pct(act['calorie'], goal.get('calorie_goal'))},
            {'label': '蛋白', 'goal': goal.get('protein_goal'), 'actual': act['protein'],
             'pct': _pct(act['protein'], goal.get('protein_goal'))},
            {'label': '饮水', 'goal': goal.get('water_goal'), 'actual': act['water'],
             'pct': _pct(act['water'], goal.get('water_goal'))},
            {'label': '运动', 'goal': goal.get('exercise_goal'), 'actual': ex['burn'],
             'pct': _pct(ex['burn'], goal.get('exercise_goal'))},
        ]
        pcts = [(it['label'], it['pct']) for it in items if it['pct'] is not None]
        if pcts:
            done = sum(1 for it in items if it['pct'] is not None and it['pct'] >= 100)
            low = min(pcts, key=lambda x: x[1])
            summary = f'4 项中 {done} 项达标 · 最需补{low[0]}'
        else:
            summary = '未设营养目标'
        data['goals'] = {'items': items, 'summary': summary}
        # #66 2026-08-04:暂停读端联动 — 主页目标 widget 横幅(仅提示,数据照常)
        from goal_manager import get_paused_state
        ps = get_paused_state()
        if ps and ps.get('paused'):
            at = ps.get('paused_at') or '?'
            data['goals']['paused'] = {
                'paused_at': at,
                'title': '目标已暂停',
                'sub': f'暂停于 {at} · 记录照常 · 说「重启所有目标」恢复',
            }
            # 2026-08-04:暂停态考核评语与横幅语义冲突 → 中性 summary
            data['goals']['paused_summary'] = '暂停期间不考核 · 记录照常 · 说「重启所有目标」恢复'
    elif view == 'week' or view == 'month':
        start, end = _period_range(view, target_date)
        s = _period_summary(view, start, end)
        wt = s['weight_start']
        s['weight_change'] = round(s['weight_end'] - wt, 1) if wt is not None and s['weight_end'] is not None else None
        data['period'] = {'period': view, 'start': start, 'end': end, **s}
    elif view == 'streak':
        st = _streak(target_date)
        data['streak'] = st
        if st['current'] == 0:
            data['streak']['summary'] = '暂无连续记录'
        elif st['current'] >= st['longest']:
            data['streak']['summary'] = '连续记录追平历史最长 · 保持住'
        else:
            data['streak']['summary'] = f'距历史最长还差 {st["longest"] - st["current"]} 天'
    elif view == 'budget':
        b = _budget(target_date)
        summary = None
        if b['remaining'] is not None:
            if b['remaining'] >= 0:
                summary = '今日额度内 · 可正常安排正餐'
            else:
                summary = '已超预算 · 建议减少加餐'
        b['summary'] = summary
        data['budget'] = b
    return data


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '主面板已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染卡路里主面板 HTML(主页 9 场景 · Apple 风)')
    p.add_argument('--date', help='日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--section', choices=['diet', 'exercise', 'weight', 'goals', 'streak', 'budget'],
                   help='今日维度聚焦视图(看今日xxx场景)')
    p.add_argument('--period', choices=['week', 'month'], help='周期视图(看本周/本月主页)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--wake-word', help='唤醒词(覆盖渲染器自推断,供「复制日志」带出)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    # R3 思考链强制校验(2026-08-02 用户拍板):live 模式必传 + 有效性校验
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读DB聚合(饮食/运动/体重/目标)→3.渲染HTML"', file=sys.stderr)
        return 2

    target_date = args.date or date.today().isoformat()
    if args.period:
        view = args.period
    elif args.section:
        view = args.section
    else:
        view = 'overview'
    scene_name = args.wake_word or VIEW_SCENES[view]

    try:
        data = build_data(target_date, view=view, period=args.period)
        # 调试元数据注入(不进 UI,复制日志可带出;R1 视图分离 + R4 自描述 + C10 引号)
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['meta'] = {
            'fetched_at': date.today().isoformat(),
            'wake_word': scene_name,
            'chain': args.chain,
            'view': view,
            'render_cmd': f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv),
        }
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene_name, 'result')
    out_path.write_text(html, encoding='utf-8')

    todo = data['today_status']['todo']
    todo_summary = f' — {", ".join(t["label"] for t in todo[:3])}' if todo else ' — 全部完成 ✓'
    print(f'✅ {out_path}')
    print(f'   场景: {scene_name} | 日期: {target_date} | 待办: {len(todo)} 项{todo_summary}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
