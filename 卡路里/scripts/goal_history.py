#!/usr/bin/env python3
"""目标历史 — 历史达成/未达成统计（看目标历史完成 · 新增场景）

基于 food_log + daily_goal：按日聚合实际 vs 目标，判定每日达成（80%-120% 带）。
无独立历史表，从现有数据推导（daily_goal 单行表，goal 变更前值不落库）。

返回：
    list_completed_goals(days) → {goal_history: [...], completed_count, incomplete_count}
"""

import sys
from datetime import date, timedelta
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


def _daily_actual(start_date, end_date):
    """按日聚合 food_log 的热量/蛋白/碳水/脂肪/饮水"""
    conn = _get_db()
    rows = conn.execute('''
        SELECT date,
               COALESCE(SUM(calories), 0) as cal,
               COALESCE(SUM(protein), 0) as pro,
               COALESCE(SUM(carbs), 0) as carb,
               COALESCE(SUM(fat), 0) as fat
        FROM food_log
        WHERE date BETWEEN ? AND ?
        GROUP BY date
    ''', (start_date, end_date)).fetchall()
    conn.close()
    return {r['date']: {'cal': r['cal'], 'pro': r['pro'], 'carb': r['carb'], 'fat': r['fat']} for r in rows}


def list_completed_goals(days=30):
    """列出过去 N 天每日目标达成情况

    Args:
        days: 回看天数（默认 30）

    Returns:
        dict {
            goal_history: [{date, calorie_actual, calorie_goal, pct, status: 完成/未完成/无记录}],
            completed_count, incomplete_count
        }
    """
    today = date.today()
    start = (today - timedelta(days=days - 1)).isoformat()
    end = today.isoformat()

    conn = _get_db()
    goal = conn.execute(
        'SELECT calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal FROM daily_goal WHERE id = 1'
    ).fetchone()
    conn.close()

    cal_goal = goal['calorie_goal'] if goal else None
    actual = _daily_actual(start, end)

    history = []
    completed = 0
    incomplete = 0
    for i in range(days):
        d = (today - timedelta(days=i)).isoformat()
        row = actual.get(d)
        if row is None:
            history.append({'date': d, 'calorie_actual': 0, 'calorie_goal': cal_goal,
                            'pct': 0, 'status': '无记录'})
            continue
        if cal_goal:
            pct = round(row['cal'] / cal_goal * 100, 1)
            status = '完成' if 80 <= pct <= 120 else '未完成'
        else:
            pct = None
            status = '未完成'
        if status == '完成':
            completed += 1
        elif status == '未完成':
            incomplete += 1
        history.append({'date': d, 'calorie_actual': row['cal'], 'calorie_goal': cal_goal,
                        'pct': pct, 'status': status})

    history.reverse()  # 时间正序
    return {
        'goal_history': history,
        'completed_count': completed,
        'incomplete_count': incomplete,
    }


if __name__ == '__main__':
    import json
    days = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
    result = list_completed_goals(days)
    print(json.dumps(result, ensure_ascii=False, indent=2))
