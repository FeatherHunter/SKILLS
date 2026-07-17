#!/usr/bin/env python3
"""复盘模块 - 业务层(③)

按 5 层架构定位:
- ③ 业务层:领域查询 + 衍生计算 + 摘要提取
- 所有 SQL 走 db.connection()(数据层 ④)
- 不直接 sqlite3.connect (符合"所有 SQL 走 db.py")
"""

import json
import math
import statistics
import sys
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

# Windows 上统一 UTF-8 输出(避免 subprocess 编码冲突)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import db as db_module  # ④ 数据层
import profile          # 用户档案(③ 业务层)
import workout_plan     # 健身计划循环逻辑


# ==================== 错误类(契约层用) ====================

class ReviewError(Exception):
    """复盘模块错误基类"""
    pass


class RangeParseError(ReviewError):
    """日期范围解析错误"""
    pass


class DataNotFoundError(ReviewError):
    """数据缺失错误(如没有 workout_plan_config)"""
    pass


# ==================== 时间范围解析 ====================

def parse_range(range_arg, range_type='week'):
    """解析时间范围 → (start_date, end_date) tuple

    Args:
        range_arg: "2026-07-08:2026-07-14" 格式,或 None
        range_type: day / week / month / year(默认 week = 过去 7 天)

    Returns:
        (start, end) 元组,ISO 格式字符串

    Raises:
        RangeParseError: 日期格式无法解析
    """
    today = date.today()

    if range_arg:
        if ':' in range_arg:
            parts = range_arg.split(':')
            try:
                start = _normalize_date(parts[0].strip(), today)
                end = _normalize_date(parts[1].strip(), today)
            except ValueError as e:
                raise RangeParseError(f"日期格式错误: {e}")
        else:
            try:
                start = end = _normalize_date(range_arg.strip(), today)
            except ValueError as e:
                raise RangeParseError(f"日期格式错误: {e}")
        return start.isoformat(), end.isoformat()

    # 默认范围
    if range_type == 'day':
        return today.isoformat(), today.isoformat()
    elif range_type == 'week':
        # 过去 7 天(包含今天)
        start = today - timedelta(days=6)
        return start.isoformat(), today.isoformat()
    elif range_type == 'month':
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat()
    elif range_type == 'year':
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat()
    else:
        raise RangeParseError(f"未知 range_type: {range_type}")


def _normalize_date(s, ref):
    """支持 "2026-07-08" / "7/8" / "8" 格式"""
    s = s.strip()
    if '-' in s and len(s) == 10:
        return datetime.strptime(s, '%Y-%m-%d').date()
    if '/' in s:
        parts = s.split('/')
        return ref.replace(month=int(parts[0]), day=int(parts[1]))
    if s.isdigit():
        return ref.replace(day=int(s))
    raise ValueError(f"无法解析日期: {s}")


# ==================== 5 维数据查询 ====================

def query_5dims(start, end, skill_dir):
    """查询 5 维原始数据(按天聚合)

    按 5 层规范:所有 SQL 走 db.connection()

    Args:
        start: 开始日期 ISO 字符串
        end: 结束日期 ISO 字符串
        skill_dir: 技能根目录(用于 db.find_db_path)

    Returns:
        dict 含 keys: range, daily_intake, daily_burn, weight_logs,
                      fitness_plan, user_profile, nutrition_targets

    Raises:
        DataNotFoundError: 关键表无数据(如没有 workout_plan_config)
    """
    db_path = db_module.find_db_path(skill_dir)

    # ✅ 符合 5 层:用 db.connection() context manager
    with db_module.connection(db_path) as conn:
        # 1. 每日摄入
        daily_intake = [dict(r) for r in conn.execute('''
            SELECT date,
                SUM(calories) AS total_calorie,
                SUM(protein) AS total_protein,
                SUM(carbs) AS total_carbs,
                SUM(fat) AS total_fat,
                COUNT(*) AS meal_count
            FROM food_log
            WHERE food_name != '💧水'
              AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        ''', (start, end)).fetchall()]

        # 2. 每日消耗
        daily_burn = [dict(r) for r in conn.execute('''
            SELECT date,
                SUM(calories_burned) AS total_burned,
                SUM(duration_minutes) AS total_minutes,
                GROUP_CONCAT(DISTINCT exercise_type) AS types,
                GROUP_CONCAT(DISTINCT category) AS categories
            FROM exercise_log
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
        ''', (start, end)).fetchall()]

        # 3. 体重日志
        weight_logs = [dict(r) for r in conn.execute('''
            SELECT date, weight_kg, height_cm
            FROM weight_log
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        ''', (start, end)).fetchall()]

        # 4. 健身计划(必须存在,否则失败)
        config_row = conn.execute(
            'SELECT * FROM workout_plan_config WHERE id = 1'
        ).fetchone()
        if not config_row:
            raise DataNotFoundError(
                "workout_plan_config 表无数据,"
                "请先'制定健身计划'初始化"
            )
        config = dict(config_row)
        fitness_plan_data = _query_fitness_plan(conn, start, end, config)

        # 5. user_profile(从 weight_log 取身高,从 USER_AGE/GENDER env 取)
        user_profile = _query_user_profile(conn)

        # 6. daily_goal(单行)
        goal_row = conn.execute(
            'SELECT * FROM daily_goal WHERE id = 1'
        ).fetchone()
        nutrition_targets = dict(goal_row) if goal_row else {}

        # 7. Top 5 频繁吃食物(高频榜:出现次数降序)
        #    排除饮水(💧水),跟其他 5 维一致
        top_foods_rows = conn.execute('''
            SELECT food_name, SUM(calories) AS total_cal, COUNT(*) AS cnt
            FROM food_log
            WHERE food_name != '💧水'
              AND date BETWEEN ? AND ?
            GROUP BY food_name
            ORDER BY cnt DESC, total_cal DESC
            LIMIT 5
        ''', (start, end)).fetchall()
        top_foods = [
            {
                'name': row[0],
                'total_cal': row[1],
                'cnt': row[2],
                'avg_cal_per_meal': round(row[1] / max(row[2], 1)),
            }
            for row in top_foods_rows
        ]

    return {
        'range': {
            'start': start,
            'end': end,
            'days': _days_between(start, end) + 1,
        },
        'daily_intake': daily_intake,
        'daily_burn': daily_burn,
        'weight_logs': weight_logs,
        'fitness_plan': fitness_plan_data,
        'user_profile': user_profile,
        'nutrition_targets': nutrition_targets,
        'top_foods': top_foods,
    }


def _query_fitness_plan(conn, start, end, config):
    """查询区间内每天的健身计划(走循环逻辑)"""
    from datetime import datetime, timedelta

    total_weeks = config['total_weeks']
    plan_start = datetime.strptime(config['start_date'], '%Y-%m-%d').date()

    all_plans = [dict(r) for r in conn.execute('''
        SELECT * FROM workout_plans
        ORDER BY week_number, day_of_week, session_index
    ''').fetchall()]

    plan_index = {}
    for p in all_plans:
        key = (p['week_number'], p['day_of_week'])
        plan_index.setdefault(key, []).append(p)

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


def _query_user_profile(conn):
    """查询用户基础信息

    优先从 user_profile 表(由 profile.set_profile 设置)读取
    fallback:身高从 weight_log,年龄/性别默认 30/male
    """
    p = profile.get_profile()
    if p:
        height = p.get('height_cm')
        if height is None:
            height_row = conn.execute('''
                SELECT height_cm FROM weight_log
                WHERE height_cm IS NOT NULL
                ORDER BY date DESC LIMIT 1
            ''').fetchone()
            height = height_row['height_cm'] if height_row else None
        return {
            'height_cm': height,
            'age': p.get('age') or 30,
            'gender': p.get('gender') or 'male',
        }

    # 老库 fallback:身高从 weight_log,年龄/性别从 env
    import os
    height_row = conn.execute('''
        SELECT height_cm FROM weight_log
        WHERE height_cm IS NOT NULL
        ORDER BY date DESC LIMIT 1
    ''').fetchone()
    height = height_row['height_cm'] if height_row else None
    return {
        'height_cm': height,
        'age': int(os.environ.get('USER_AGE', 30)),
        'gender': os.environ.get('USER_GENDER', 'male'),
    }


def _days_between(start, end):
    """两个日期相差几天"""
    start_d = datetime.strptime(start, '%Y-%m-%d').date()
    end_d = datetime.strptime(end, '%Y-%m-%d').date()
    return (end_d - start_d).days


# ==================== 衍生计算 ====================

def derive(raw_data):
    """衍生计算:Mifflin-St Jeor TDEE / 缺口 / 理论减重 / 营养结构比例

    2026-07-17 修复:
    - 区分 complete_days(完整日)和 today_partial(今日不完整)
    - avg_* / 缺口 / 营养达标率 都用 complete_days,避免今日污染
    - today_partial 单独装填 HTML,展示"今日进度"
    """
    enriched = dict(raw_data)

    # 0. 区分完整日 vs 今日(partial)
    today_iso = date.today().isoformat()
    daily_intake_full = raw_data.get('daily_intake', [])
    complete_days_intake = [d for d in daily_intake_full if d['date'] < today_iso]
    today_partial_intake = next((d for d in daily_intake_full if d['date'] == today_iso), None)

    daily_burn_full = raw_data.get('daily_burn', [])
    complete_days_burn = [d for d in daily_burn_full if d['date'] < today_iso]
    today_partial_burn = next((d for d in daily_burn_full if d['date'] == today_iso), None)

    enriched['today_partial'] = {
        'intake': today_partial_intake,
        'burn': today_partial_burn,
    }
    enriched['complete_days_count'] = len(complete_days_intake)

    # 1. TDEE(用最新体重,可能是今日的)
    latest_weight = _get_latest_weight(raw_data.get('weight_logs', []))
    user_profile = raw_data.get('user_profile', {})
    enriched['tdee'] = _calc_tdee(
        weight_kg=latest_weight,
        height_cm=user_profile.get('height_cm'),
        age=user_profile.get('age', 30),
        gender=user_profile.get('gender', 'male'),
    )

    # 2. 摄入汇总(用 complete_days,排除今日)
    if complete_days_intake:
        enriched['intake_summary'] = {
            'days_count': len(complete_days_intake),
            'avg_calorie': round(sum(d['total_calorie'] for d in complete_days_intake) / len(complete_days_intake), 1),
            'avg_protein': round(sum(d['total_protein'] for d in complete_days_intake) / len(complete_days_intake), 1),
            'avg_carbs': round(sum(d['total_carbs'] for d in complete_days_intake) / len(complete_days_intake), 1),
            'avg_fat': round(sum(d['total_fat'] for d in complete_days_intake) / len(complete_days_intake), 1),
        }
    elif today_partial_intake:
        # 只有今日数据,日均=今日(标注 partial)
        d = today_partial_intake
        enriched['intake_summary'] = {
            'days_count': 1,
            'is_partial': True,
            'avg_calorie': d['total_calorie'],
            'avg_protein': d['total_protein'],
            'avg_carbs': d['total_carbs'],
            'avg_fat': d['total_fat'],
        }
    else:
        enriched['intake_summary'] = {
            'days_count': 0,
            'avg_calorie': 0, 'avg_protein': 0, 'avg_carbs': 0, 'avg_fat': 0,
        }

    # 3. 消耗汇总(用 complete_days,排除今日)
    if complete_days_burn:
        enriched['burn_summary'] = {
            'days_count': len(complete_days_burn),
            'total_burned': sum(d['total_burned'] for d in complete_days_burn),
            'avg_burned': round(sum(d['total_burned'] for d in complete_days_burn) / len(complete_days_burn), 1),
            'total_minutes': sum(d['total_minutes'] or 0 for d in complete_days_burn),
        }
    elif today_partial_burn:
        d = today_partial_burn
        enriched['burn_summary'] = {
            'days_count': 1,
            'is_partial': True,
            'total_burned': d['total_burned'],
            'avg_burned': d['total_burned'],
            'total_minutes': d['total_minutes'] or 0,
        }
    else:
        enriched['burn_summary'] = {
            'days_count': 0, 'total_burned': 0, 'avg_burned': 0, 'total_minutes': 0,
        }

    # 4. 营养结构比例(基于 intake_summary)
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

    # 5. 缺口(基于完整日)
    #    days 用 complete_days_count(不是 range.days),避免除以 7 但只有 6 天完整
    days = enriched['complete_days_count'] if enriched['complete_days_count'] > 0 else raw_data.get('range', {}).get('days', 7)
    total_intake = intake['avg_calorie'] * days
    total_burned_exercise = enriched['burn_summary']['total_burned']
    total_burned_all = total_burned_exercise + enriched['tdee'] * days
    weekly_deficit = total_burned_all - total_intake  # 正=赤字
    enriched['weekly_deficit'] = round(weekly_deficit)
    enriched['avg_daily_deficit'] = round(weekly_deficit / days) if days > 0 else 0
    enriched['theoretical_weight_loss'] = round(weekly_deficit / 7700, 1)

    # 6. 营养配比达标率(基于 complete_days,避免今日污染)
    enriched['nutrition_match'] = _calc_nutrition_match_rate(
        complete_days_intake,  # ← 用完整日,不是 daily_intake_full
        raw_data.get('nutrition_targets', {}),
    )

    # 7. 体重趋势 SVG(算法渲染,自动 Y 轴 + 智能 X 密度)
    weight_trend_result = _render_weight_trend_svg(
        raw_data.get('weight_logs', []),
        goal_weight=raw_data.get('nutrition_targets', {}).get('weight_goal') if raw_data.get('nutrition_targets') else None,
    )
    enriched['weight_trend_svg'] = weight_trend_result['svg']
    enriched['weight_trend_meta'] = weight_trend_result['meta']

    return enriched


def _render_weight_trend_svg(weight_logs, goal_weight=None):
    """渲染体重趋势 SVG(2026-07-17 设计)

    解决 B3( Y 轴硬编码)+ B4( X 轴硬编码)+ 智能密度:
    - Y 轴范围 自动算(data min/max ± 0.3kg 余量)
    - X 轴密度 智能:
      - ≤7 个数据点:每天显示
      - ≤30 个数据点:每 5 天
      - ≤90 个数据点:每 7 天(按周)
      - >90 个数据点:每 30 天(按月)

    返回:
        {
            'svg': '<svg>...</svg>' 完整 SVG 字符串,
            'meta': {
                'data_count': N,
                'y_min': 87.5,
                'y_max': 90.0,
                'title': '7 天体重趋势',
                'range_text': '88.25 ~ 89.15 kg',
                'has_goal_line': True/False,
            }
        }
    """
    if not weight_logs:
        return {
            'svg': '<svg viewBox="0 0 320 110" preserveAspectRatio="xMidYMid meet"></svg>',
            'meta': {
                'data_count': 0, 'y_min': 0, 'y_max': 0,
                'title': '体重趋势', 'range_text': '—', 'has_goal_line': False,
            },
        }

    # 1. 数据预处理(每天取最后一条)
    daily_last = {}
    for w in weight_logs:
        daily_last[w['date']] = w['weight_kg']
    points = sorted(
        [{'date': d, 'weight': w} for d, w in daily_last.items()],
        key=lambda x: x['date'],
    )
    n = len(points)

    # 2. X 轴密度(基于数据点数)
    if n <= 7:
        x_step_show = 1
    elif n <= 30:
        x_step_show = 5
    elif n <= 90:
        x_step_show = 7
    else:
        x_step_show = 30

    # 3. Y 轴范围(自动算 + goal_weight 智能处理)
    weights = [p['weight'] for p in points]
    w_min, w_max = min(weights), max(weights)

    # goal_weight 距实际数据 > 5kg 不纳入 Y 轴(否则太远把图拉糊)
    goal_in_range = False
    if goal_weight is not None:
        data_mid = (w_min + w_max) / 2
        distance_from_data = abs(goal_weight - data_mid)
        if distance_from_data <= 5.0:
            w_min = min(w_min, goal_weight)
            w_max = max(w_max, goal_weight)
            goal_in_range = True

    # 加 0.3kg 余量
    y_min = math.floor(w_min - 0.3)
    y_max = math.ceil(w_max + 0.3)
    if y_max - y_min < 1:
        # 数据波动小(<1kg),扩大范围
        y_min -= 0.5
        y_max += 0.5

    y_range = y_max - y_min

    # 4. SVG 尺寸(viewBox 0 0 320 110)
    width, height = 320, 110
    margin_left = 42
    margin_right = 8
    margin_top = 16
    margin_bottom = 22
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    # 5. 坐标计算
    x_coords = [
        margin_left + (i / max(n - 1, 1)) * plot_w
        for i in range(n)
    ]
    y_coords = [
        margin_top + (1 - (w - y_min) / y_range) * plot_h
        for w in weights
    ]

    # 6. SVG parts
    parts = [
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" style="display:block;">'
    ]

    # Y 轴线
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top}" '
        f'x2="{margin_left}" y2="{margin_top + plot_h}" '
        f'stroke="#C7C7CC" stroke-width="1"/>'
    )

    # Y 轴刻度(4 tick)
    for i in range(4):
        y_val = y_max - (i / 3) * y_range
        y_pos = margin_top + (i / 3) * plot_h
        parts.append(
            f'<text x="{margin_left - 4}" y="{y_pos + 4:.1f}" '
            f'text-anchor="end" font-size="9" fill="#8E8E93">'
            f'{y_val:.1f}</text>'
        )

    # Y 单位标签
    parts.append(
        f'<text x="{margin_left - 4}" y="{height - 6}" '
        f'text-anchor="end" font-size="8" fill="#C7C7CC">kg</text>'
    )

    # X 轴线
    parts.append(
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" '
        f'x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" '
        f'stroke="#C7C7CC" stroke-width="1"/>'
    )

    # 数据线
    poly_points = ' '.join(
        f'{x_coords[i]:.1f},{y_coords[i]:.1f}' for i in range(n)
    )
    parts.append(
        f'<polyline points="{poly_points}" fill="none" stroke="#34C759" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # 数据点 + 标签
    weight_min_val = min(weights)
    weight_max_val = max(weights)
    for i in range(n):
        x, y = x_coords[i], y_coords[i]
        w = weights[i]
        is_min = w == weight_min_val and weight_min_val != weight_max_val
        is_max = w == weight_max_val and weight_min_val != weight_max_val
        is_last = i == n - 1

        if is_min:
            color = '#FF9500'
            label = f'{w} ▼'
        elif is_last:
            color = '#007AFF'
            label = f'{w} ▲'
        elif is_max:
            color = '#AF52DE'
            label = f'{w} ★'
        else:
            color = '#34C759'
            label = None

        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{4 if (is_min or is_last or is_max) else 3}" '
            f'fill="{color}"/>'
        )
        if label:
            label_y = y - 6 if y > 20 else y + 12
            parts.append(
                f'<text x="{x:.1f}" y="{label_y:.1f}" '
                f'text-anchor="middle" font-size="9" '
                f'fill="{color}" font-weight="700">{label}</text>'
            )

    # X 轴日期(按 x_step_show 间隔)
    for i in range(n):
        if i % x_step_show == 0 or i == n - 1:
            x = x_coords[i]
            date_obj = points[i]['date']
            # 'YYYY-MM-DD' → 'MM/DD'
            month_day = date_obj[5:].replace('-', '/')
            parts.append(
                f'<text x="{x:.1f}" y="{height - 6}" '
                f'text-anchor="middle" font-size="9" '
                f'fill="#8E8E93">{month_day}</text>'
            )

    # 目标体重虚线(只在 goal_in_range 时画)
    has_goal_line = goal_in_range
    if has_goal_line:
        goal_y = margin_top + (1 - (goal_weight - y_min) / y_range) * plot_h
        parts.append(
            f'<line x1="{margin_left}" y1="{goal_y:.1f}" '
            f'x2="{margin_left + plot_w}" y2="{goal_y:.1f}" '
            f'stroke="#34C759" stroke-width="0.5" '
            f'stroke-dasharray="3,3" opacity="0.4"/>'
        )
        parts.append(
            f'<text x="{margin_left + plot_w - 2}" y="{goal_y - 3:.1f}" '
            f'text-anchor="end" font-size="8" fill="#34C759">'
            f'目标 {goal_weight}</text>'
        )

    parts.append('</svg>')
    svg_str = '\n'.join(parts)

    # 标题:基于数据点数
    title = f'{n} 天体重趋势' if n <= 14 else f'近 {n} 天体重趋势'
    range_text = f'{w_min:.1f} ~ {w_max:.1f} kg'

    meta_payload = {
        'data_count': n,
        'y_min': y_min,
        'y_max': y_max,
        'title': title,
        'range_text': range_text,
        'has_goal_line': has_goal_line,
    }
    if goal_weight is not None:
        meta_payload['goal_weight'] = goal_weight
        meta_payload['goal_in_range'] = goal_in_range
        if not goal_in_range:
            # goal 不在范围,但提示距图底/顶多远
            data_mid = (min(weights) + max(weights)) / 2
            meta_payload['distance_from_data'] = round(
                abs(goal_weight - data_mid), 1
            )

    return {
        'svg': svg_str,
        'meta': meta_payload,
    }


def _calc_nutrition_match_rate(daily_intake, nutrition_targets):
    """统计 N 天里营养配比达标的天数(2026-07-17 设计)

    达标定义(同时满足):
    - 卡路里:实际 vs 目标,偏差 ≤ 10%(±185 卡,目标 1850)
    - 蛋白:实际 ≥ 目标 × 80%(目标 163 × 80% = 130g)

    Returns:
        {
            'days_count': N,
            'matched_days': M,
            'match_rate_pct': round(M/N*100),
            'summary': '43%(3/7 天 配比达标)',
        }
    """
    if not daily_intake:
        return {
            'days_count': 0,
            'matched_days': 0,
            'match_rate_pct': 0,
            'summary': '无数据',
        }

    cal_goal = nutrition_targets.get('calorie_goal') if nutrition_targets else None
    protein_goal = nutrition_targets.get('protein_goal') if nutrition_targets else None

    if not cal_goal or not protein_goal:
        return {
            'days_count': len(daily_intake),
            'matched_days': 0,
            'match_rate_pct': 0,
            'summary': '无营养目标',
        }

    matched = 0
    for day in daily_intake:
        cal_ok = abs(day['total_calorie'] - cal_goal) <= cal_goal * 0.10
        protein_ok = day['total_protein'] >= protein_goal * 0.80
        if cal_ok and protein_ok:
            matched += 1

    total = len(daily_intake)
    pct = round(matched / total * 100)

    return {
        'days_count': total,
        'matched_days': matched,
        'match_rate_pct': pct,
        'summary': f'{pct}%({matched}/{total} 天 配比达标)',
    }


def _calc_tdee(weight_kg, height_cm, age, gender='male'):
    """Mifflin-St Jeor 公式 + 活动系数 1.55(中度)

    BMR: 10W + 6.25H - 5A + (5 男 / -161 女)
    TDEE = BMR × 1.55
    """
    if not weight_kg or not height_cm:
        return 1800  # fallback

    if gender == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    return round(bmr * 1.55)


def _get_latest_weight(weight_logs):
    if not weight_logs:
        return None
    return weight_logs[-1].get('weight_kg')


# ==================== 摘要提取 ====================

class _SummaryExtractor(HTMLParser):
    """从 LLM 输出的 HTML 提取 data-field 内容"""

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


def extract_summary(html_output):
    """从 LLM 输出的 HTML 提取 3+3+3 摘要

    Args:
        html_output: 完整 HTML 字符串

    Returns:
        dict 含 keys: date_range, win_1..3, fail_1..3, todo_1..3
    """
    parser = _SummaryExtractor()
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