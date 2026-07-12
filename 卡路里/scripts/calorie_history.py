#!/usr/bin/env python3
"""热量历史 — 最近 N 天每日摄入聚合

数据来源：food_log 表（排除饮水）
显示：日期 / 热量 / 蛋白 / 碳 / 脂 / vs 目标状态
"""

import sys
from datetime import datetime, timedelta
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


def get_calorie_history(days=7):
    """显示最近 N 天热量历史（按日期聚合）

    Args:
        days: 查询天数，默认 7
    """
    conn = _get_db()
    c = conn.cursor()

    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
        FROM food_log
        WHERE date >= ?
        GROUP BY date
        ORDER BY date DESC
    ''', (start,))

    rows = c.fetchall()

    from nutrition_goal import get_nutrition_goal
    goal = get_nutrition_goal()
    conn.close()

    if not rows:
        print(f"最近{days}天无记录")
        return

    cal_goal = goal[1] if goal else None

    print(f"\n热量历史（最近{days}天）：")
    print("-" * 70)
    print(f"{'日期':>10} | {'卡':>5} | {'蛋白':>5} | {'碳':>5} | {'脂':>5} | 状态")
    print("-" * 70)

    for date_str, total_cal, total_pro, total_carbs, total_fat in rows:
        if cal_goal:
            remaining = cal_goal - total_cal
            status = f"{remaining:+.0f}卡" if remaining != 0 else "达标"
        else:
            status = "未设目标"

        print(f"{date_str:>10} | {total_cal:>5} | {total_pro:>5} | {total_carbs:>5} | {total_fat:>5} | {status}")

    print()