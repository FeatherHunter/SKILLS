#!/usr/bin/env python3
"""健身计划 — 循环逻辑 + 按日期查询

核心算法：
  real_week = (date - start_date).days // 7 + 1
  plan_week = ((real_week - 1) % total_weeks) + 1
  day_of_week = date.isoweekday()  (1=Mon...7=Sun)

查询：SELECT * WHERE week_number=plan_week AND day_of_week=day_of_week
"""

import json
from datetime import date, datetime
from pathlib import Path

from db import find_db_path, get_db, init_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def get_plan_config():
    """获取计划元信息"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT id, title, version, description, total_weeks, start_date FROM workout_plan_config')
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row[0], 'title': row[1], 'version': row[2],
        'description': row[3], 'total_weeks': row[4], 'start_date': row[5],
    }


def calc_plan_week(target_date, config):
    """计算 target_date 对应的计划周次。

    Args:
        target_date: date 对象
        config: get_plan_config() 返回值

    Returns:
        int: 计划周次（1-based）
        None: config 为 None 时,或 target_date 早于 start_date(2026-07-13 修:之前返 1 伪装成"已存在",现返 None 表明"未开始")
    """
    if not config:
        return None
    start = datetime.strptime(config['start_date'], '%Y-%m-%d').date()
    days_diff = (target_date - start).days
    if days_diff < 0:
        return None  # 计划未开始(start 之前的日期)
    real_week = days_diff // 7 + 1
    return ((real_week - 1) % config['total_weeks']) + 1


def get_day_plan(target_date=None):
    """查询某天的所有训练时间段。

    Args:
        target_date: date 对象，默认今天

    Returns:
        dict: {config, sessions}，sessions 为 list
    """
    if target_date is None:
        target_date = date.today()

    config = get_plan_config()
    week = calc_plan_week(target_date, config)
    dow = target_date.isoweekday()

    # 2026-07-13 修:计划未开始时返 unstarted=True 标志(而不是伪装成 week=1)
    if week is None and config is not None:
        return {
            "date": target_date.strftime('%Y-%m-%d'),
            "plan_week": None,
            "day_of_week": dow,
            "config": config,
            "sessions": [],
            "unstarted": True,
        }

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, week_number, day_of_week, session_index, session_label,
               time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans
        WHERE week_number = ? AND day_of_week = ?
        ORDER BY session_index
    ''', (week, dow))
    rows = c.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        sessions.append({
            'id': r[0], 'week_number': r[1], 'day_of_week': r[2],
            'session_index': r[3], 'session_label': r[4],
            'time_start': r[5], 'time_end': r[6],
            'is_rest_day': r[7], 'total_sets': r[8],
            'movements': json.loads(r[9]) if r[9] else [],
        })

    return {
        'date': target_date.strftime('%Y-%m-%d'),
        'plan_week': week,
        'day_of_week': dow,
        'config': config,
        'sessions': sessions,
    }
