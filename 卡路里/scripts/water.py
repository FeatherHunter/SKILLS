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
    """
    try:
        ml = int(ml)
        if ml <= 0:
            print("Error: 饮水量必须为正数")
            return False
    except ValueError:
        print("Error: 饮水量必须是数字（ml）")
        return False

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

    print(f"✓ 已记录饮水：{ml}ml（条目ID：{entry_id}）")

    date_label = today if target_date else '今日'
    if goal_row:
        water_goal = goal_row[6] if len(goal_row) > 6 and goal_row[6] else 2000
        remaining = water_goal - total_water
        print(f"  {date_label}饮水：{total_water}/{water_goal}ml | 剩余：{remaining:+.0f}ml")
    else:
        print(f"  {date_label}饮水：{total_water}ml（未设置目标）")

    return True