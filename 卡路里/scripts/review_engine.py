#!/usr/bin/env python3
"""复盘模块 - 5 维数据查询 + 衍生计算 + 摘要提取

数据流:
    review_tracker review --gen
        ↓
    query_5dims(start, end) → raw_data
        ↓
    derive(raw_data) → enriched_data
        ↓
    review_prompts.build_html_prompt(enriched_data)
        ↓
    LLM → 完整 HTML
        ↓
    extract_summary(html) → 飞书消息字段
"""

import json
import sqlite3
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

import db as db_module
import workout_plan


# ==================== 时间范围解析 ====================

def parse_range(range_arg: str | None, range_type: str = 'week') -> tuple[str, str]:
    """解析时间范围 → (start_date, end_date) 字符串 YYYY-MM-DD

    Args:
        range_arg: "2026-07-08:2026-07-14" 格式,或 None
        range_type: day / week / month / year(默认 week)

    Returns:
        (start, end) 元组
    """
    today = date.today()

    if range_arg:
        # 解析 "2026-07-08:2026-07-14" 或 "7/8:7/14"
        if ':' in range_arg:
            parts = range_arg.split(':')
            start = _normalize_date(parts[0].strip(), today)
            end = _normalize_date(parts[1].strip(), today)
        else:
            # 单日期 = 当天
            start = end = _normalize_date(range_arg.strip(), today)
        return start.isoformat(), end.isoformat()

    # 默认范围
    if range_type == 'day':
        return today.isoformat(), today.isoformat()
    elif range_type == 'week':
        # 过去 7 天(包含今天)
        start = today - timedelta(days=6)
        return start.isoformat(), today.isoformat()
    elif range_type == 'month':
        # 本月 1 号到今天
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat()
    elif range_type == 'year':
        # 今年 1/1 到今天
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat()
    else:
        raise ValueError(f"未知 range_type: {range_type}")


def _normalize_date(s: str, ref: date) -> date:
    """支持 "2026-07-08" 或 "7/8" 格式"""
    s = s.strip()
    # ISO 格式
    if '-' in s and len(s) == 10:
        return datetime.strptime(s, '%Y-%m-%d').date()
    # "7/8" 格式(月/日)
    if '/' in s:
        parts = s.split('/')
        month = int(parts[0])
        day = int(parts[1])
        return ref.replace(month=month, day=day)
    # 数字格式(8 = 8号)
    if s.isdigit():
        return ref.replace(day=int(s))
    raise ValueError(f"无法解析日期: {s}")


# ==================== 5 维数据查询 ====================

def query_5dims(start: str, end: str, skill_dir: Path) -> dict:
    """查询 5 维原始数据(按天聚合)

    Returns:
        dict with keys:
            range, daily_intake, daily_burn, weight_logs, fitness_plan,
            daily_intake_summary, daily_burn_summary,
            user_profile, nutrition_targets, weight_goal
    """
    db_path = db_module.find_db_path(skill_dir)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # 1. 每日摄入(按 date 聚合)
        daily_intake_rows = conn.execute('''
            SELECT date,
                SUM(calories) AS total_calorie,
                SUM(protein) AS total_protein,
                SUM(carbs) AS total_carbs,
                SUM(fat) AS total_fat,
                COUNT(*) AS meal_count
            FROM food_log
            WHERE food_name != '💧水'  -- 排除饮水
              AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        ''', (start, end)).fetchall()

        daily_intake = [dict(r) for r in daily_intake_rows]

        # 2. 每日消耗
        daily_burn_rows = conn.execute('''
            SELECT date,
                SUM(calories_burned) AS total_burned,
                SUM(duration_minutes) AS total_minutes,
                GROUP_CONCAT(DISTINCT exercise_type) AS types,
                GROUP_CONCAT(DISTINCT category) AS categories
            FROM exercise_log
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        ''', (start, end)).fetchall()

        daily_burn = [dict(r) for r in daily_burn_rows]

        # 3. 体重日志
        weight_rows = conn.execute('''
            SELECT date, weight_kg, height_cm
            FROM weight_log
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        ''', (start, end)).fetchall()
        weight_logs = [dict(r) for r in weight_rows]

        # 4. 健身计划(循环计算每天的 plan)
        fitness_plan_data = _query_fitness_plan(conn, start, end)

        # 5. user_profile(从 weight_log 取身高,从 config 取年龄+性别)
        user_profile = _query_user_profile(conn)

        # 6. daily_goal(单行)
        goal_row = conn.execute(
            'SELECT * FROM daily_goal WHERE id = 1'
        ).fetchone()
        nutrition_targets = dict(goal_row) if goal_row else {}

        return {
            'range': {'start': start, 'end': end, 'days': _days_between(start, end) + 1},
            'daily_intake': daily_intake,
            'daily_burn': daily_burn,
            'weight_logs': weight_logs,
            'fitness_plan': fitness_plan_data,
            'user_profile': user_profile,
            'nutrition_targets': nutrition_targets,
        }
    finally:
        conn.close()


def _query_fitness_plan(conn, start: str, end: str) -> list[dict]:
    """查询区间内每天的健身计划(走循环逻辑)

    Returns:
        list of dict: [
            {date, plan_label, plan_movements, plan_total_sets},
            ...
        ]
    """
    config_row = conn.execute(
        'SELECT * FROM workout_plan_config WHERE id = 1'
    ).fetchone()
    if not config_row:
        return []

    config = dict(config_row)
    total_weeks = config['total_weeks']
    plan_start = datetime.strptime(config['start_date'], '%Y-%m-%d').date()

    # 查询所有 plans
    all_plans_rows = conn.execute('''
        SELECT * FROM workout_plans
        ORDER BY week_number, day_of_week, session_index
    ''').fetchall()
    all_plans = [dict(r) for r in all_plans_rows]

    # 按 (week_number, day_of_week) 索引
    plan_index = {}
    for p in all_plans:
        key = (p['week_number'], p['day_of_week'])
        plan_index.setdefault(key, []).append(p)

    # 计算区间内每天的 plan
    start_d = datetime.strptime(start, '%Y-%m-%d').date()
    end_d = datetime.strptime(end, '%Y-%m-%d').date()

    result = []
    cur = start_d
    while cur <= end_d:
        real_week = ((cur - plan_start).days // 7) + 1
        plan_week = ((real_week - 1) % total_weeks) + 1
        day_of_week = cur.isoweekday()

        plans = plan_index.get((plan_week, day_of_week), [])
        for p in plans:
            result.append({
                'date': cur.isoformat(),
                'week_number': plan_week,
                'day_of_week': day_of_week,
                'session_label': p['session_label'],
                'is_rest_day': p['is_rest_day'],
                'total_sets': p['total_sets'],
                'movements': json.loads(p['movements']) if p['movements'] else [],
            })
        cur += timedelta(days=1)

    return result


def _query_user_profile(conn) -> dict:
    """查询用户基础信息

    数据库无 user_profile 表,从以下来源聚合:
    - 身高:weight_log 最近一条
    - 年龄+性别:从 config-calorie.ts 或环境变量读(待实现)
    """
    height_row = conn.execute('''
        SELECT height_cm FROM weight_log
        WHERE height_cm IS NOT NULL
        ORDER BY date DESC LIMIT 1
    ''').fetchone()
    height = height_row['height_cm'] if height_row else None

    # TODO: 从 config 读年龄+性别,目前用环境变量 fallback
    import os
    return {
        'height_cm': height,
        'age': int(os.environ.get('USER_AGE', 30)),  # 默认 30
        'gender': os.environ.get('USER_GENDER', 'male'),  # 默认 male
    }


def _days_between(start: str, end: str) -> int:
    """两个日期相差几天"""
    start_d = datetime.strptime(start, '%Y-%m-%d').date()
    end_d = datetime.strptime(end, '%Y-%m-%d').date()
    return (end_d - start_d).days


# ==================== 衍生计算 ====================

def derive(raw_data: dict) -> dict:
    """衍生计算:Mifflin-St Jeor TDEE / 缺口 / 理论减重 / 营养结构比例"""
    enriched = dict(raw_data)

    # 1. TDEE(每日总能量消耗)
    enriched['tdee'] = _calc_tdee(
        weight_kg=_get_latest_weight(raw_data.get('weight_logs', [])),
        height_cm=raw_data.get('user_profile', {}).get('height_cm'),
        age=raw_data.get('user_profile', {}).get('age', 30),
        gender=raw_data.get('user_profile', {}).get('gender', 'male'),
    )

    # 2. 摄入汇总
    daily_intake = raw_data.get('daily_intake', [])
    if daily_intake:
        enriched['intake_summary'] = {
            'days_count': len(daily_intake),
            'avg_calorie': round(sum(d['total_calorie'] for d in daily_intake) / len(daily_intake), 1),
            'avg_protein': round(sum(d['total_protein'] for d in daily_intake) / len(daily_intake), 1),
            'avg_carbs': round(sum(d['total_carbs'] for d in daily_intake) / len(daily_intake), 1),
            'avg_fat': round(sum(d['total_fat'] for d in daily_intake) / len(daily_intake), 1),
        }
    else:
        enriched['intake_summary'] = {
            'days_count': 0,
            'avg_calorie': 0, 'avg_protein': 0, 'avg_carbs': 0, 'avg_fat': 0,
        }

    # 3. 消耗汇总
    daily_burn = raw_data.get('daily_burn', [])
    if daily_burn:
        enriched['burn_summary'] = {
            'days_count': len(daily_burn),
            'total_burned': sum(d['total_burned'] for d in daily_burn),
            'avg_burned': round(sum(d['total_burned'] for d in daily_burn) / len(daily_burn), 1),
            'total_minutes': sum(d['total_minutes'] or 0 for d in daily_burn),
        }
    else:
        enriched['burn_summary'] = {
            'days_count': 0, 'total_burned': 0, 'avg_burned': 0, 'total_minutes': 0,
        }

    # 4. 营养结构比例(按热量)
    intake = enriched['intake_summary']
    total_kcal = intake['avg_protein'] * 4 + intake['avg_carbs'] * 4 + intake['avg_fat'] * 9
    if total_kcal > 0:
        enriched['macro_ratio'] = {
            'protein_pct': round(intake['avg_protein'] * 4 / total_kcal * 100),
            'carbs_pct': round(intake['avg_carbs'] * 4 / total_kcal * 100),
            'fat_pct': round(intake['avg_fat'] * 9 / total_kcal * 100),
        }
    else:
        enriched['macro_ratio'] = {'protein_pct': 0, 'carbs_pct': 0, 'fat_pct': 0}

    # 5. 缺口(周)
    days = raw_data.get('range', {}).get('days', 7)
    total_intake = intake['avg_calorie'] * days
    total_burned_exercise = enriched['burn_summary']['total_burned']
    total_burned_all = total_burned_exercise + enriched['tdee'] * days
    weekly_deficit = total_burned_all - total_intake  # 正=赤字
    enriched['weekly_deficit'] = round(weekly_deficit)
    enriched['avg_daily_deficit'] = round(weekly_deficit / days)
    enriched['theoretical_weight_loss'] = round(weekly_deficit / 7700, 1)  # 7700 kcal/kg

    return enriched


def _calc_tdee(weight_kg: float | None, height_cm: float | None,
               age: int, gender: str) -> int:
    """Mifflin-St Jeor 公式 + 活动系数

    BMR = 10*W + 6.25*H - 5*A + (5 男 / -161 女)
    TDEE = BMR × 活动系数(轻度 1.375 / 中度 1.55 / 高度 1.725)
    """
    if not weight_kg or not height_cm:
        return 1800  # fallback 默认值

    if gender == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    # 活动系数:用 1.55(中等活动),无更细数据
    activity_factor = 1.55
    return round(bmr * activity_factor)


def _get_latest_weight(weight_logs: list[dict]) -> float | None:
    """从 weight_logs 取最后一条的体重"""
    if not weight_logs:
        return None
    return weight_logs[-1].get('weight_kg')


# ==================== 摘要提取 ====================

def extract_summary(html_output: str) -> dict:
    """从 LLM 输出的 HTML 提取 3+3+3 摘要(用于飞书消息)

    Returns:
        dict with keys: date_range, win_1..3, fail_1..3, todo_1..3
    """
    from html.parser import HTMLParser

    class FieldExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.current_field = None
            self.current_text = ''
            self.results = {}

        def handle_starttag(self, tag, attrs):
            attrs_dict = dict(attrs)
            if 'data-field' in attrs_dict:
                self.current_field = attrs_dict['data-field']
                self.current_text = ''

        def handle_data(self, data):
            if self.current_field:
                self.current_text += data

        def handle_endtag(self, tag):
            if self.current_field and tag in ('span', 'div', 'li', 'h2', 'h3'):
                self.results[self.current_field] = self.current_text.strip()
                self.current_field = None

    parser = FieldExtractor()
    parser.feed(html_output)

    return {
        'date_range': parser.results.get('date_range', ''),
        'win_1': parser.results.get('win_1', ''),
        'win_2': parser.results.get('win_2', ''),
        'win_3': parser.results.get('win_3', ''),
        'fail_1': parser.results.get('fail_1', ''),
        'fail_2': parser.results.get('fail_2', ''),
        'fail_3': parser.results.get('fail_3', ''),
        'todo_1': parser.results.get('todo_1', ''),
        'todo_2': parser.results.get('todo_2', ''),
        'todo_3': parser.results.get('todo_3', ''),
    }