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
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'home_dashboard.html'

sys.path.insert(0, str(SCRIPT_DIR))
from analysis import dashboard
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

    return {
        'food': {'count': food_count, 'calories': int(food_cal)},
        'water': {'count': water_count, 'calories': int(water_cal)},
        'exercise': {'count': exercise_count, 'calories': int(exercise_cal)},
        'weight': {'count': weight_count},
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
    {'label': '记录饮食',    'command': 'python scripts/calorie_tracker.py add ...'},
    {'label': '查今日吃',    'command': 'python scripts/calorie_tracker.py summary'},
    {'label': '记录运动',    'command': 'python scripts/exercise_tracker.py add ...'},
    {'label': '查健康报告',  'command': 'python scripts/render_health_dashboard.py --days 7'},
    {'label': '查热量趋势',  'command': 'python scripts/render_health_dashboard.py --days 30'},
    {'label': '查食物排行',  'command': 'python scripts/render_food_ranking.py --all'},
    {'label': '扫禁忌',      'command': 'python scripts/render_contraindication.py'},
    {'label': '复盘',        'command': 'python scripts/render_review.py'},
]


def build_data(target_date: str) -> dict:
    """组装主面板数据契约"""
    dash_data = dashboard(target_date, target_date, as_dict=True)
    return {
        'date': target_date,
        'dashboard': dash_data['data'],
        'today_status': build_today_status(target_date),
        'recent_logs': build_recent_logs(target_date),
        'quick_actions': QUICK_ACTIONS,
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

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'home_dashboard')
    out_path.write_text(html, encoding='utf-8')

    todo = data['today_status']['todo']
    todo_summary = f' — {", ".join(t["label"] for t in todo[:3])}' if todo else ' — 全部完成 ✓'
    print(f'✅ {out_path}')
    print(f'   日期: {target_date} | 待办: {len(todo)} 项{todo_summary}')
    return 0


if __name__ == '__main__':
    sys.exit(main())