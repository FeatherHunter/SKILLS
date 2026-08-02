#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_home.py — 卡路里主面板 HTML 渲染器

对应 SKILL.md 唤醒词: 开卡路里 / 卡路里面板 / 今日卡路里

设计原则(《预置 HTML + 注入数据指导手册》):
- 复用 analysis.dashboard(as_dict=True) 拿 4 维数据
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次
- Apple 风:浅色 + 系统字体 + 蓝色主色 + 圆角 + 留白
- 结果型(A 类),无 AI 互动需求

用法:
    python scripts/render_home.py                              # 默认今天
    python scripts/render_home.py --date 2026-07-23            # 指定日期
    python scripts/render_home.py --output <path>             # 指定输出
"""
import argparse
import json
from html_paths import html_path
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'home_dashboard.html'

sys.path.insert(0, str(SCRIPT_DIR))
from analysis import dashboard
from _triggers import TRIGGERS
from db import find_db_path, get_db


def build_today_status(target_date: str) -> dict:
    """检测今日是否记录了 饮食/饮水/运动/体重"""
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

    # H1.4 对接(2026-08-02 · ticket #4 Success Criteria #5):体重 widget 显示实际数值
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

    # 健身计划待办对接(2026-08-02 · ticket #6 Success Criteria #5):今日有训练计划但实绩不足 → 待办
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


def build_data(target_date: str) -> dict:
    """组装主面板数据契约"""
    dash_data = dashboard(target_date, target_date, as_dict=True)
    return {
        'date': target_date,
        'dashboard': dash_data['data'],
        'today_status': build_today_status(target_date),
        'recent_logs': build_recent_logs(target_date),
        'quick_actions': _attach_prompts(QUICK_ACTIONS),
    }


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
    p = argparse.ArgumentParser(description='渲染卡路里主面板 HTML(Apple 风)')
    p.add_argument('--date', help='日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    target_date = args.date or date.today().isoformat()

    try:
        data = build_data(target_date)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '主页仪表盘')
    out_path.write_text(html, encoding='utf-8')

    todo = data['today_status']['todo']
    todo_summary = f' — {", ".join(t["label"] for t in todo[:3])}' if todo else ' — 全部完成 ✓'
    print(f'✅ {out_path}')
    print(f'   日期: {target_date} | 待办: {len(todo)} 项{todo_summary}')
    return 0


if __name__ == '__main__':
    sys.exit(main())