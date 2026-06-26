#!/usr/bin/env python3
"""每日营养目标 — 热量/蛋白/碳水/脂肪/饮水

数据存储：daily_goal 表（固定 id=1）
- calorie_goal / protein_goal / carbs_goal / fat_goal — 四大营养目标
- water_goal — 饮水目标（v2.2 新增）
- weight_goal / goal_deadline — 体重目标（被 weight_goal.py 写）

设置约束（v2.2 修改）：
- 必须 4 参全传（calorie/protein/carbs/fat）
- 第 5 参可选饮水
- 自洽性校验：蛋白*4 + 碳*4 + 脂*9 vs 热量目标，相差 > 50 卡给警告
"""

import sys
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


def set_nutrition_goal(calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal=None):
    """设置每日营养目标（v2.2 支持饮水目标）

    Args:
        calorie_goal: 热量目标（卡）
        protein_goal: 蛋白质目标（克）
        carbs_goal: 碳水目标（克）
        fat_goal: 脂肪目标（克）
        water_goal: 饮水目标（ml），可选
    """
    # 强制 4 参检查
    if None in (protein_goal, carbs_goal, fat_goal):
        print("Error: goal 必须 4 个参数全传")
        print("  用法: goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]")
        print("  示例: goal 1850 150 200 50 2000")
        return False

    try:
        calorie_goal = int(calorie_goal)
        protein_goal = int(protein_goal)
        carbs_goal = int(carbs_goal)
        fat_goal = int(fat_goal)
        if calorie_goal <= 0:
            print("Error: 热量目标必须为正数")
            return False
        if protein_goal < 0 or carbs_goal < 0 or fat_goal < 0:
            print("Error: 营养目标不能为负数")
            return False
    except ValueError:
        print("Error: 参数必须是数字")
        return False

    if water_goal is not None:
        try:
            water_goal = int(water_goal)
            if water_goal < 0:
                print("Error: 饮水目标不能为负数")
                return False
        except ValueError:
            print("Error: 饮水目标必须是数字")
            return False

    # 自洽性提示
    calculated = protein_goal * 4 + carbs_goal * 4 + fat_goal * 9
    diff = calculated - calorie_goal

    conn = _get_db()
    c = conn.cursor()

    if water_goal is not None:
        c.execute('''
            INSERT OR REPLACE INTO daily_goal (id, calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal))
    else:
        c.execute('''
            INSERT OR REPLACE INTO daily_goal (id, calorie_goal, protein_goal, carbs_goal, fat_goal, updated_at)
            VALUES (1, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (calorie_goal, protein_goal, carbs_goal, fat_goal))

    conn.commit()
    conn.close()

    print(f"✓ 每日目标已设置：")
    print(f"  热量：{calorie_goal}卡")
    print(f"  蛋白质：{protein_goal}克")
    print(f"  碳水：{carbs_goal}克")
    print(f"  脂肪：{fat_goal}克")
    if water_goal is not None:
        print(f"  饮水：{water_goal}ml")
    if abs(diff) <= 50:
        print(f"  自洽性：换算 {calculated} 卡（差异 {diff:+d}）✅")
    return True


def get_nutrition_goal():
    """获取每日目标（返回 sqlite3.Row 或 None）

    列顺序：id, calorie_goal, protein_goal, carbs_goal, fat_goal,
            weight_goal, goal_deadline, water_goal, updated_at
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row