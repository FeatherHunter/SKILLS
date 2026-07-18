#!/usr/bin/env python3
"""饮食记录 — 食物添加/删除/查询/每日摘要

餐次按时间自动推断（可用 --meal 手动覆盖）：
  早餐 6-10 / 午餐 10-14 / 下午茶 14-18 / 晚餐 18-22 / 夜宵 其他

饮水记录在 water.py（使用 food_name='💧水' 标记）
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
    """获取数据库连接，必要时初始化"""
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def infer_meal_type(time_str):
    """根据时间自动推断餐次"""
    try:
        hour = int(time_str.split(':')[0])
    except Exception:
        return "其他"

    if 6 <= hour < 10:
        return "早餐"
    elif 10 <= hour < 14:
        return "午餐"
    elif 14 <= hour < 18:
        return "下午茶"
    elif 18 <= hour < 22:
        return "晚餐"
    else:
        return "夜宵"


def add_meal(food_name, calories, protein, carbs=0, fat=0, grams=100, note='',
             target_date=None, target_time=None, meal_override=None):
    """添加食物记录

    Args:
        food_name: 食物名称
        calories: 热量（卡）
        protein: 蛋白质（克）
        carbs: 碳水（克），默认 0
        fat: 脂肪（克），默认 0
        grams: 克数，默认 100
        note: 备注
        target_date: 目标日期（YYYY-MM-DD），默认今天
        target_time: 目标时间（HH:MM:SS），默认当前
        meal_override: 手动指定餐次（早餐/午餐/下午茶/晚餐/夜宵）
    """
    try:
        calories = float(calories)
        protein = float(protein)
        carbs = float(carbs)
        fat = float(fat)
        grams = float(grams)
    except ValueError:
        print("Error: All nutrition values must be numbers")
        return False

    if calories < 0 or protein < 0 or carbs < 0 or fat < 0 or grams <= 0:
        print("Error: Values cannot be negative")
        return False

    valid_meals = ('早餐', '午餐', '下午茶', '晚餐', '夜宵')
    if meal_override is not None and meal_override not in valid_meals:
        print(f"Error: --meal 必须是以下值之一：{', '.join(valid_meals)}")
        return False

    conn = _get_db()
    c = conn.cursor()

    today = target_date or date.today().isoformat()
    now = target_time or datetime.now().strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (today, now, food_name, grams, calories, protein, carbs, fat, note))

    entry_id = c.lastrowid
    conn.commit()

    # 今日汇总
    c.execute('''
        SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM food_log
        WHERE date = ?
    ''', (today,))
    total_cal, total_pro, total_carbs, total_fat, entry_count = c.fetchone()

    # 读取目标
    from nutrition_goal import get_nutrition_goal
    goal = get_nutrition_goal()
    conn.close()

    meal = meal_override if meal_override else infer_meal_type(now)
    date_label = today if target_date else '今日'
    print(f"✓ 已记录：{food_name} ({calories}卡, {protein}蛋白, {carbs}碳, {fat}脂, {grams}克)")
    print(f"  餐次：{meal} | 条目ID：{entry_id}")

    if goal:
        cal_goal, pro_goal, carb_goal, fat_goal = goal[1], goal[2], goal[3], goal[4]
        remaining = cal_goal - total_cal
        print(f"  {date_label}：{total_cal}/{cal_goal}卡 | 蛋白{total_pro}/{pro_goal}克 | 碳{total_carbs}/{carb_goal}克 | 脂{total_fat}/{fat_goal}克")
        if remaining > 0:
            print(f"  剩余：{remaining}卡")
        else:
            print(f"  ⚠️ 超标：{abs(remaining)}卡")

    return True


def update_meal(entry_id, grams=None, food_name=None, note=None):
    """更新一条食物记录

    Args:
        entry_id: 记录 ID
        grams: 克数（可选）
        food_name: 食物名称（可选）
        note: 备注（可选）
    """
    try:
        entry_id = int(entry_id)
    except ValueError:
        print("Error: Entry ID must be a number")
        return False

    conn = _get_db()
    c = conn.cursor()

    c.execute('SELECT food_name, grams, calories FROM food_log WHERE id = ?', (entry_id,))
    row = c.fetchone()

    if not row:
        print(f"Error: Entry ID {entry_id} not found")
        conn.close()
        return False

    old_food, old_grams, old_cal = row
    updates = []
    params = []
    if grams is not None:
        updates.append('grams = ?')
        params.append(float(grams))
    if food_name is not None:
        updates.append('food_name = ?')
        params.append(food_name)
    if note is not None:
        updates.append('note = ?')
        params.append(note)

    if not updates:
        print("Error: No fields to update")
        conn.close()
        return False

    params.append(entry_id)
    c.execute(f"UPDATE food_log SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

    new_grams = grams if grams is not None else old_grams
    new_food = food_name if food_name is not None else old_food
    print(f"✓ Updated entry {entry_id}: {new_food} ({new_grams}克)")
    return True


def delete_meal(entry_id):
    """删除一条食物记录"""
    try:
        entry_id = int(entry_id)
    except ValueError:
        print("Error: Entry ID must be a number")
        return False

    conn = _get_db()
    c = conn.cursor()

    c.execute('SELECT food_name, calories FROM food_log WHERE id = ?', (entry_id,))
    row = c.fetchone()

    if not row:
        print(f"Error: Entry ID {entry_id} not found")
        conn.close()
        return False

    c.execute('DELETE FROM food_log WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

    print(f"✓ Deleted entry {entry_id}: {row[0]} ({row[1]} cal)")
    return True


def list_meals(target_date=None):
    """列出某日所有饮食记录（默认今日）"""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = _get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, food_name, grams, calories, protein, carbs, fat, time, note
        FROM food_log
        WHERE date = ?
        ORDER BY time
    ''', (target_date,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"{target_date} 无记录")
        return []

    print(f"\n{target_date} 饮食记录：")
    print("-" * 70)
    print(f"{'ID':>3} | {'时间':>5} | {'食物':15} | {'克':>4} | {'卡':>5} | {'蛋白':>5} | {'碳':>4} | {'脂':>4} | 备注")
    print("-" * 70)

    for entry_id, food_name, grams, calories, protein, carbs, fat, time, note in rows:
        print(f"{entry_id:>3} | {time[0:5]:>5} | {food_name:15} | {grams:>4} | {calories:>5} | {protein:>5} | {carbs:>4} | {fat:>4} | {note or ''}")

    print("-" * 70)
    return rows


def get_daily_summary(target_date=None):
    """显示每日摘要（含饮水、目标对比、详细列表）"""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = _get_db()
    c = conn.cursor()

    # 食物统计（排除饮水）
    c.execute('''
        SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM food_log
        WHERE date = ? AND food_name != '💧水'
    ''', (target_date,))

    total_cal, total_pro, total_carbs, total_fat, entry_count = c.fetchone()
    total_cal = total_cal or 0
    total_pro = total_pro or 0
    total_carbs = total_carbs or 0
    total_fat = total_fat or 0
    entry_count = entry_count or 0

    # 饮水统计
    c.execute('''
        SELECT COALESCE(SUM(grams), 0)
        FROM food_log
        WHERE date = ? AND food_name = '💧水'
    ''', (target_date,))
    total_water = c.fetchone()[0]

    from nutrition_goal import get_nutrition_goal
    goal = get_nutrition_goal()
    conn.close()

    print(f"\n{'='*60}")
    print(f"今日摘要 - {target_date}")
    print(f"{'='*60}")
    print(f"记录数：{entry_count}")

    if goal:
        cal_goal, pro_goal, carb_goal, fat_goal = goal[1], goal[2], goal[3], goal[4]
        # water_goal 在 daily_goal 表索引 8(2026-07-18 修:索引 6 是 weight_goal 不是 water)
        water_goal = goal[8] if len(goal) > 8 and goal[8] else 2000
        cal_remaining = cal_goal - total_cal
        pro_remaining = pro_goal - total_pro
        carb_remaining = carb_goal - total_carbs
        fat_remaining = fat_goal - total_fat
        water_remaining = water_goal - total_water

        print(f"\n热量：{total_cal}/{cal_goal}卡 | 剩余：{cal_remaining:+.0f}")
        print(f"蛋白：{total_pro}/{pro_goal}克 | 剩余：{pro_remaining:+.0f}")
        print(f"碳水：{total_carbs}/{carb_goal}克 | 剩余：{carb_remaining:+.0f}")
        print(f"脂肪：{total_fat}/{fat_goal}克 | 剩余：{fat_remaining:+.0f}")
        print(f"饮水：{total_water}/{water_goal}ml | 剩余：{water_remaining:+.0f}")

        if cal_remaining < 0:
            print(f"\n⚠️ 热量超标：{abs(cal_remaining)}卡")
    else:
        print(f"\n总热量：{total_cal}卡（未设置目标）")
        print(f"饮水：{total_water}ml")

    print(f"{'='*60}\n")

    if entry_count > 0 or total_water > 0:
        list_meals(target_date)