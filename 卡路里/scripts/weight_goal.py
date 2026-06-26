#!/usr/bin/env python3
"""体重目标 — 设定目标 + 达成进度

数据存储：daily_goal 表的 weight_goal / goal_deadline 列
进度计算：
- 距离 deadline 的天数
- 每日需减/增多少 kg（缺口）
- 推荐每日热量调整（7700 kcal/kg）
"""

import sys
from datetime import datetime
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


def set_weight_goal(weight_goal, deadline=None):
    """设置体重目标

    Args:
        weight_goal: 目标体重（kg）
        deadline: 目标日期（YYYY-MM-DD），可选
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE daily_goal
        SET weight_goal = ?, goal_deadline = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (weight_goal, deadline))
    if c.rowcount == 0:
        c.execute('''
            INSERT INTO daily_goal (id, weight_goal, goal_deadline)
            VALUES (1, ?, ?)
        ''', (weight_goal, deadline))
    conn.commit()
    conn.close()
    print(f"✓ 体重目标已设定：{weight_goal} kg"
          + (f" | 目标日期：{deadline}" if deadline else ""))


def get_weight_goal():
    """获取体重目标及进度数据

    Returns:
        tuple: (weight_goal, deadline, days_left, None, calorie_adjustment)
               若未设置返回 None
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1')
    row = c.fetchone()

    if not row or not row[0]:
        conn.close()
        return None

    weight_goal, deadline = row

    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = c.fetchone()
    if not wrow:
        conn.close()
        return (weight_goal, deadline, None, None, None)

    current_weight, current_date = wrow

    days_left = None
    calorie_adjustment = None

    if deadline:
        try:
            deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
            today_dt = datetime.strptime(current_date, '%Y-%m-%d')
            days_left = (deadline_dt - today_dt).days
        except (ValueError, TypeError):
            days_left = None

    if days_left is not None and days_left > 0:
        gap = current_weight - weight_goal
        required_daily = gap / days_left
        calorie_adjustment = int(required_daily * 7700)

    conn.close()
    return (weight_goal, deadline, days_left, None, calorie_adjustment)


def print_goal_progress():
    """打印体重目标达成进度报告"""
    result = get_weight_goal()
    if not result or result[0] is None:
        print("\n⚠️ 未设定体重目标，请说「设定体重目标 73kg」或「设定体重目标 73kg 目标日期 2026-07-01」")
        return

    weight_goal, deadline, days_left, daily_change_rate, calorie_adj = result

    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    row = c.fetchone()
    conn.close()

    if not row:
        print(f"\n⚠️ 未记录体重，无法计算进度")
        return

    current_weight, current_date = row
    gap = current_weight - weight_goal

    print(f"\n{'='*45}")
    print(f"  体重目标进度报告")
    print(f"{'='*45}")
    print(f"  当前体重：{current_weight:.1f} kg（{current_date}）")
    print(f"  目标体重：{weight_goal:.1f} kg" + (f"（{deadline}）" if deadline else ""))
    print(f"  差距：{'+' if gap > 0 else ''}{gap:.1f} kg")
    if days_left is not None:
        print(f"  剩余天数：{days_left}天")
        if days_left > 0:
            required_daily = gap / days_left
            print(f"  每日需{'减' if required_daily > 0 else '增'}{abs(required_daily):.2f} kg")
    if calorie_adj is not None:
        if calorie_adj > 1000:
            print(f"  ⚠️ 警告：每日需增加 {calorie_adj} kcal 缺口（极端目标，建议调整目标或延期）")
        elif calorie_adj > 0:
            print(f"  建议：每日需增加 {calorie_adj} kcal 缺口")
        elif calorie_adj < -1000:
            print(f"  ⚠️ 警告：当前进度大幅超前，建议适当增加摄入")
        elif calorie_adj < 0:
            print(f"  建议：每日需减少 {abs(calorie_adj)} kcal 缺口（当前进度超前）")
        else:
            print(f"  状态：完美匹配，按当前节奏可达成目标")

    print(f"{'='*45}\n")