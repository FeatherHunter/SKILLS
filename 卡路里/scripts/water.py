#!/usr/bin/env python3
"""饮水记录 — 饮水量追踪

数据存储：复用 food_log 表，food_name='💧水'，grams 存 ml，calories=0
"""

import sys
from datetime import date, datetime
from pathlib import Path

from db import find_db_path, get_db, init_db

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def add_water(ml, target_date=None, target_time=None):
    """记录饮水量（ml）

    Args:
        ml: 饮水量（毫升）
        target_date: 目标日期（YYYY-MM-DD），默认今天
        target_time: 目标时间（HH:MM:SS），默认当前

    Returns(v2.4.16 改):
        成功:dict 含 id/date/time/ml/today_total/water_goal 等(V1.0 §02 第②特性)
            例:{'id': 88, 'date': '2026-07-27', 'time': '12:00:00', 'ml': 500, 'rows_affected': 1,
                'today_total_ml': 1500, 'water_goal_ml': 2000, 'remaining_ml': 500}
        失败:None
    """
    try:
        ml = int(ml)
        if ml <= 0:
            print("Error: 饮水量必须为正数")
            return None
    except ValueError:
        print("Error: 饮水量必须是数字（ml）")
        return None

    conn = _get_db()
    c = conn.cursor()

    today = target_date or date.today().isoformat()
    now = target_time or datetime.now().strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
        VALUES (?, ?, '💧水', ?, 0, 0, 0, 0, '')
    ''', (today, now, ml))

    entry_id = c.lastrowid
    conn.commit()

    # 今日饮水汇总
    c.execute('''
        SELECT COALESCE(SUM(grams), 0)
        FROM food_log
        WHERE date = ? AND food_name = '💧水'
    ''', (today,))
    total_water = c.fetchone()[0]

    from nutrition_goal import get_nutrition_goal
    goal_row = get_nutrition_goal()
    conn.close()

    # v2.4.16:CLI 端负责打印回执(契约格式),本函数只返 dict
    water_goal = None
    if goal_row and len(goal_row) > 6 and goal_row[6]:
        water_goal = goal_row[6]

    return {
        'id': entry_id,
        'date': today,
        'time': now,
        'ml': ml,
        'rows_affected': 1,
        'today_total_ml': total_water,
        'water_goal_ml': water_goal if water_goal else 2000,
        'remaining_ml': (water_goal or 2000) - total_water,
    }