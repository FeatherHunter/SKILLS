#!/usr/bin/env python3
"""
卡路里 - 热量追踪脚本 v2.0
支持：食物记录(热量/蛋白质/碳水/脂肪)、每日目标、体重追踪
"""

import sqlite3
import os
import sys
from datetime import date, datetime, timedelta
from collections import defaultdict
from pathlib import Path

from db_utils import find_db_path as _find_db_path
from db_utils import get_db as _get_db_conn

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


def init_db():
    """Initialize database with new schema"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Food entries table - v2.0
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            food_name TEXT NOT NULL,
            grams INTEGER NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER DEFAULT 0,
            carbs INTEGER DEFAULT 0,
            fat INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Daily goal - v2.0 (with macros)
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_goal (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            calorie_goal INTEGER NOT NULL DEFAULT 1800,
            protein_goal INTEGER DEFAULT 150,
            carbs_goal INTEGER DEFAULT 200,
            fat_goal INTEGER DEFAULT 60,
            weight_goal REAL,
            goal_deadline TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Exercise log - v1.0
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercise_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            exercise_type TEXT NOT NULL,
            duration_minutes INTEGER,
            calories_burned INTEGER NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Weight log - v2.0 (kg + height + BMI)
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            weight_kg REAL NOT NULL,
            height_cm REAL,
            bmi REAL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Nutrition products table - for storing nutrition facts per 100g
    c.execute('''
        CREATE TABLE IF NOT EXISTS nutrition_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            brand TEXT,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            saturated_fat REAL,
            carbohydrates REAL NOT NULL,
            sugar REAL,
            dietary_fiber REAL,
            sodium REAL NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_weight_date ON weight_log(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_exercise_date ON exercise_log(date)')

    # Migration: add weight_goal/goal_deadline if not exist
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN weight_goal REAL')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN goal_deadline TEXT')
    except Exception:
        pass
    # Migration: add water_goal if not exist (v2.2)
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN water_goal INTEGER DEFAULT 2000')
    except Exception:
        pass
    c.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON nutrition_products(product_name)')

    conn.commit()
    conn.close()


def get_db():
    """Get database connection, auto-init if needed"""
    if not DB_PATH.exists():
        init_db()
    return _get_db_conn(DB_PATH)


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


def add_entry(food_name, calories, protein, carbs=0, fat=0, grams=100, note='',
              target_date=None, target_time=None, meal_override=None):
    """添加食物记录"""
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

    # 餐次验证（若用户指定了 --meal）
    valid_meals = ('早餐', '午餐', '下午茶', '晚餐', '夜宵')
    if meal_override is not None and meal_override not in valid_meals:
        print(f"Error: --meal 必须是以下值之一：{', '.join(valid_meals)}")
        return False

    conn = get_db()
    c = conn.cursor()

    today = target_date or date.today().isoformat()
    now = target_time or datetime.now().strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO entries (date, time, food_name, grams, calories, protein, carbs, fat, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (today, now, food_name, grams, calories, protein, carbs, fat, note))

    entry_id = c.lastrowid
    conn.commit()

    # 获取今日汇总
    c.execute('''
        SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM entries
        WHERE date = ?
    ''', (today,))
    total_cal, total_pro, total_carbs, total_fat, entry_count = c.fetchone()

    # 获取目标
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    goal_row = c.fetchone()
    conn.close()

    # 餐次：用户指定优先，否则按时间推断
    meal = meal_override if meal_override else infer_meal_type(now)
    date_label = today if target_date else '今日'
    print(f"✓ 已记录：{food_name} ({calories}卡, {protein}蛋白, {carbs}碳, {fat}脂, {grams}克)")
    print(f"  餐次：{meal} | 条目ID：{entry_id}")

    if goal_row:
        cal_goal, pro_goal, carb_goal, fat_goal = goal_row[1], goal_row[2], goal_row[3], goal_row[4]
        remaining = cal_goal - total_cal
        print(f"  {date_label}：{total_cal}/{cal_goal}卡 | 蛋白{total_pro}/{pro_goal}克 | 碳{total_carbs}/{carb_goal}克 | 脂{total_fat}/{fat_goal}克")
        if remaining > 0:
            print(f"  剩余：{remaining}卡")
        else:
            print(f"  ⚠️ 超标：{abs(remaining)}卡")

    return True


def delete_entry(entry_id):
    """删除记录"""
    try:
        entry_id = int(entry_id)
    except ValueError:
        print("Error: Entry ID must be a number")
        return False

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT food_name, calories FROM entries WHERE id = ?', (entry_id,))
    row = c.fetchone()

    if not row:
        print(f"Error: Entry ID {entry_id} not found")
        conn.close()
        return False

    c.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
    conn.commit()
    conn.close()

    print(f"✓ Deleted entry {entry_id}: {row[0]} ({row[1]} cal)")
    return True


def set_goal(calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal=None):
    """设置每日目标（v2.2 支持饮水目标）"""
    # 强制 4 参检查（2026-06-09 修改）
    if None in (protein_goal, carbs_goal, fat_goal):
        print("Error: goal 必须 4 个参数全传")
        print("  用法: goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]")
        print("  示例: goal 1850 150 200 50 2000")
        return False

    # 类型转换
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

    # 饮水目标（可选）
    if water_goal is not None:
        try:
            water_goal = int(water_goal)
            if water_goal < 0:
                print("Error: 饮水目标不能为负数")
                return False
        except ValueError:
            print("Error: 饮水目标必须是数字")
            return False

    # 自洽性提示（不阻断，只警告）
    calculated = protein_goal * 4 + carbs_goal * 4 + fat_goal * 9
    diff = calculated - calorie_goal
    if abs(diff) > 50:
        print(f"⚠️ 提示：营养目标换算约 {calculated} 卡，与热量目标 {calorie_goal} 卡相差 {diff:+d} 卡（>50）")

    conn = get_db()
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


def get_goal():
    """获取每日目标"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row


def list_entries(target_date=None):
    """列出某日所有记录"""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, food_name, grams, calories, protein, carbs, fat, time, note
        FROM entries
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


def summary(target_date=None):
    """显示每日摘要"""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()
    c = conn.cursor()

    # 食物统计（排除饮水）
    c.execute('''
        SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM entries
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
        FROM entries
        WHERE date = ? AND food_name = '💧水'
    ''', (target_date,))
    total_water = c.fetchone()[0]

    goal = get_goal()
    conn.close()

    print(f"\n{'='*60}")
    print(f"今日摘要 - {target_date}")
    print(f"{'='*60}")
    print(f"记录数：{entry_count}")

    if goal:
        cal_goal, pro_goal, carb_goal, fat_goal = goal[1], goal[2], goal[3], goal[4]
        water_goal = goal[6] if len(goal) > 6 and goal[6] else 2000
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
        list_entries(target_date)


def log_weight(weight_kg, height_cm, note='', target_date=None, target_time=None):
    """记录体重（身高必传，BMI 必须计算）"""
    try:
        weight_kg = float(weight_kg)
        if weight_kg <= 0:
            print("Error: Weight must be positive")
            return False
    except ValueError:
        print("Error: Weight must be a number")
        return False

    try:
        height_cm = float(height_cm)
        if height_cm <= 0:
            print("Error: Height must be a positive number (cm)")
            return False
    except (ValueError, TypeError):
        print("Error: Height must be a number (cm)")
        return False

    # 计算BMI（身高必传，BMI 必须计算）
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)
    bmi = round(bmi, 1)

    conn = get_db()
    c = conn.cursor()

    today = target_date or date.today().isoformat()
    now = target_time or datetime.now().strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO weight_log (date, time, weight_kg, height_cm, bmi, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (today, now, weight_kg, height_cm, bmi, note))

    conn.commit()
    conn.close()

    print(f"✓ 体重已记录：{weight_kg}公斤")
    if bmi:
        print(f"  BMI：{bmi}")
    if note:
        print(f"  备注：{note}")
    return True


def update_weight(weight_id, weight_kg=None, height_cm=None, note=None):
    """按 ID 更新体重记录，若传身高则重算 BMI"""
    try:
        weight_id = int(weight_id)
    except ValueError:
        print("Error: 体重记录 ID 必须是数字")
        return False

    if weight_kg is None and height_cm is None and note is None:
        print("Error: 至少需要传入 --weight 或 --height 或 --note 中的一个")
        return False

    conn = get_db()
    c = conn.cursor()

    # 检查记录是否存在
    c.execute('SELECT id, weight_kg, height_cm FROM weight_log WHERE id = ?', (weight_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: 体重记录 ID {weight_id} 不存在")
        conn.close()
        return False

    old_weight, old_height = row[1], row[2]

    # 计算新 BMI（若传了体重或身高）
    # 类型转换（CLI 参数为字符串）
    new_weight = float(weight_kg) if weight_kg is not None else old_weight
    new_height = float(height_cm) if height_cm is not None else old_height

    if new_height is None or new_height <= 0:
        print("Error: 该记录缺少身高数据，无法单独修改体重（BMI 重算需要身高）")
        print("  提示：请同时传入 --height <身高cm>")
        print(f"  示例: weight-update {weight_id} --weight {weight_kg} --height <身高cm>")
        conn.close()
        return False

    height_m = new_height / 100
    bmi = round(new_weight / (height_m ** 2), 1)

    # 构造更新字段
    set_parts = ["weight_kg = ?", "height_cm = ?", "bmi = ?"]
    values = [new_weight, new_height, bmi]

    if note is not None:
        set_parts.append("note = ?")
        values.append(note)

    values.append(weight_id)
    set_clause = ", ".join(set_parts)

    c.execute(f'UPDATE weight_log SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()

    print(f"✓ 已更新体重记录 ID {weight_id}")
    print(f"  体重：{old_weight} → {new_weight} kg | BMI：{bmi}")
    if note is not None:
        print(f"  备注：{note}")
    return True


def weight_history(days=30, start_date=None, end_date=None):
    """显示体重历史
    
    支持三种调用方式：
    - weight_history(days=30)              # 最近N天（向后兼容）
    - weight_history(start_date='2026-01-01', end_date='2026-05-09')  # 日期范围
    - weight_history(start_date='2026-05-09', end_date='2026-05-09')  # 单日查询
    """
    conn = get_db()
    c = conn.cursor()

    # 构建查询条件
    if start_date and end_date:
        # 日期范围查询
        c.execute('''
            SELECT date, time, weight_kg, bmi, note
            FROM weight_log
            WHERE date >= ? AND date <= ?
            ORDER BY date DESC, time DESC
        ''', (start_date, end_date))
        if start_date == end_date:
            range_desc = start_date
        else:
            range_desc = f"{start_date} ~ {end_date}"
    elif start_date:
        # 单日查询
        c.execute('''
            SELECT date, time, weight_kg, bmi, note
            FROM weight_log
            WHERE date = ?
            ORDER BY time DESC
        ''', (start_date,))
        range_desc = start_date
    else:
        # 默认最近N天（向后兼容）
        c.execute('''
            SELECT date, time, weight_kg, bmi, note
            FROM weight_log
            ORDER BY date DESC, time DESC
            LIMIT ?
        ''', (days,))
        range_desc = f"最近{days}天"

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"无体重记录（{range_desc}）")
        return None

    print(f"\n体重历史（{range_desc}）：{len(rows)}条记录")
    print("-" * 60)
    print(f"{'日期':>10} | {'时间':>5} | {'体重(kg)':>8} | {'BMI':>5} | 备注")
    print("-" * 60)

    for date_str, time_str, weight, bmi, note in rows:
        bmi_str = f"{bmi:.1f}" if bmi else "-"
        note_str = note or ""
        print(f"{date_str:>10} | {time_str[0:5] if time_str else '':>5} | {weight:>8.1f} | {bmi_str:>5} | {note_str}")

    # 计算变化
    if len(rows) >= 2:
        first_weight = rows[-1][2]
        last_weight = rows[0][2]
        change = last_weight - first_weight
        day_span = (datetime.strptime(rows[0][0], '%Y-%m-%d') - datetime.strptime(rows[-1][0], '%Y-%m-%d')).days + 1
        daily_avg = change / day_span if day_span > 0 else 0

        print("-" * 60)
        print(f"时间跨度：{day_span}天 | 首日：{first_weight:.1f}kg → 末日：{last_weight:.1f}kg")
        if change > 0:
            print(f"变化：+{change:.1f}公斤 | 日均：+{daily_avg:.2f}公斤/天")
        elif change < 0:
            print(f"变化：{change:.1f}公斤 | 日均：{daily_avg:.2f}公斤/天")
        else:
            print(f"变化：无变化")

    print()
    return rows


def set_weight_goal(weight_goal, deadline=None):
    """设置体重目标"""
    conn = get_db()
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
    """获取体重目标"""
    conn = get_db()
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


def add_exercise(exercise_type, calories_burned, duration_minutes=None, reps=None, note='', target_date=None, target_time=None):
    """记录运动消耗
    
    Args:
        exercise_type: 运动类型，如 '跑步'、'钻石俯卧撑'
        calories_burned: 消耗卡路里
        duration_minutes: 运动时长（分钟）
        reps: 动作次数/组数，如 20个
        note: 备注
        target_date: 记录日期，默认今天
    """
    if target_date is None:
        target_date = date.today().strftime('%Y-%m-%d')

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO exercise_log (date, time, exercise_type, duration_minutes, calories_burned, note, reps)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (target_date, target_time or '', exercise_type, duration_minutes, calories_burned, note, reps))
    conn.commit()
    conn.close()
    
    reps_str = f" {reps}个" if reps else ""
    dur_str = f" {duration_minutes}分钟" if duration_minutes else ""
    print(f"✓ 已记录运动：{exercise_type}{reps_str}{dur_str} {calories_burned}卡")


def get_exercise_log(target_date=None, days=7):
    """获取运动记录
    
    Args:
        target_date: 查询日期（单日）
        days: 查询近N天（默认7）
    """
    conn = get_db()
    c = conn.cursor()

    if target_date:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date = ?
            ORDER BY time DESC
        ''', (target_date,))
    else:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date >= date('now', ?)
            ORDER BY date DESC, time DESC
        ''', (f'-{days} days',))

    rows = c.fetchall()
    conn.close()
    return rows


def exercise_summary(days=7):
    """显示近N天运动汇总"""
    rows = get_exercise_log(days=days)
    if not rows:
        print(f"\n近{days}天无运动记录")
        return

    # 按日汇总
    daily = defaultdict(list)
    for row in rows:
        # row: (date, time, exercise_type, duration_minutes, calories_burned, note, reps)
        daily[row[0]].append({
            'type': row[2],
            'cal': row[4],
            'dur': row[3],
            'reps': row[6]
        })

    total_cal = sum(sum(r['cal'] for r in items) for items in daily.values())
    total_days = len(daily)

    print(f"\n近{days}天运动汇总：{total_cal}卡 / {total_days}天")
    print("-" * 50)
    for d, items in sorted(daily.items()):
        detail = []
        for r in items:
            s = f"{r['type']}"
            if r['reps']:
                s += f" {r['reps']}个"
            if r['dur']:
                s += f" {r['dur']}分钟"
            s += f" {r['cal']}卡"
            detail.append(s)
        print(f"  {d}: {' | '.join(detail)}")
    print(f"\n  日均: {total_cal / total_days:.0f}卡/天" if total_days else "")


def goal_progress_report():
    """体重目标达成进度报告"""
    result = get_weight_goal()
    if not result or result[0] is None:
        print("\n⚠️ 未设定体重目标，请说「设定体重目标 73kg」或「设定体重目标 73kg 目标日期 2026-07-01」")
        return

    weight_goal, deadline, days_left, daily_change_rate, calorie_adj = result

    # 获取最新体重
    conn = get_db()
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


def add_product(product_name, brand, calories, protein, fat, saturated_fat, carbohydrates, sugar, dietary_fiber, sodium, note=''):
    """添加食品营养成分表"""
    try:
        conn = get_db()
        c = conn.cursor()

        c.execute('''
            INSERT INTO nutrition_products 
            (product_name, brand, calories, protein, fat, saturated_fat, carbohydrates, sugar, dietary_fiber, sodium, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_name, brand, calories, protein, fat, saturated_fat, carbohydrates, sugar, dietary_fiber, sodium, note))

        product_id = c.lastrowid
        conn.commit()
        conn.close()

        print(f"✓ 已添加营养成分表：{product_name}")
        print(f"  品牌：{brand or '-'}")
        print(f"  热量：{calories}千卡/100g")
        print(f"  蛋白质：{protein}克 | 脂肪：{fat}克 | 碳水：{carbohydrates}克")
        print(f"  饱和脂肪：{saturated_fat or '-'}克 | 糖：{sugar or '-'}克 | 膳食纤维：{dietary_fiber or '-'}克")
        print(f"  钠：{sodium}毫克")
        if note:
            print(f"  备注：{note}")
        print(f"  ID：{product_id}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def search_product(keyword):
    """搜索食品营养成分"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, product_name, brand, calories, protein, fat, saturated_fat, 
               carbohydrates, sugar, dietary_fiber, sodium, note, updated_at
        FROM nutrition_products
        WHERE product_name LIKE ? OR brand LIKE ?
        ORDER BY product_name
    ''', (f'%{keyword}%', f'%{keyword}%'))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"未找到包含「{keyword}」的食品")
        return []

    print(f"\n找到 {len(rows)} 个匹配的食品：")
    print("-" * 90)
    print(f"{'ID':>3} | {'产品名称':20} | {'品牌':10} | {'热量':>5} | {'蛋白':>5} | {'脂':>4} | {'碳':>5} | {'钠':>6} | 更新日期")
    print("-" * 90)

    for row in rows:
        id_, name, brand, cal, pro, fat_, sat_fat, carb, sugar, fiber, sodium, note, updated = row
        brand = brand or '-'
        sat_fat_str = f"{sat_fat}" if sat_fat else '-'
        sugar_str = f"{sugar}" if sugar else '-'
        fiber_str = f"{fiber}" if fiber else '-'
        print(f"{id_:>3} | {name:20} | {brand:10} | {cal:>5} | {pro:>5} | {fat_:>4} | {carb:>5} | {sodium:>6} | {updated[:10]}")

    print("-" * 90)
    return rows


def update_product(product_id, **kwargs):
    """更新食品营养成分"""
    allowed_fields = ['product_name', 'brand', 'calories', 'protein', 'fat', 
                      'saturated_fat', 'carbohydrates', 'sugar', 'dietary_fiber', 
                      'sodium', 'note']

    # Filter valid fields
    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if not update_data:
        print("Error: No valid fields to update")
        return False

    if not product_id:
        print("Error: Product ID is required")
        return False

    conn = get_db()
    c = conn.cursor()

    # Check if product exists
    c.execute('SELECT product_name FROM nutrition_products WHERE id = ?', (product_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: Product ID {product_id} not found")
        conn.close()
        return False

    old_name = row[0]

    # Build update query
    set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(update_data.values())
    values.append(product_id)

    c.execute(f'UPDATE nutrition_products SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()

    print(f"✓ 已更新「{old_name}」营养成分表")
    for k, v in update_data.items():
        print(f"  {k}: {v}")
    return True


def list_products(limit=50):
    """列出所有食品营养成分"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, product_name, brand, calories, protein, fat, saturated_fat,
               carbohydrates, sugar, dietary_fiber, sodium, note, created_at
        FROM nutrition_products
        ORDER BY updated_at DESC
        LIMIT ?
    ''', (limit,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print("营养成分库为空，请先添加食品营养成分")
        return []

    print(f"\n食品营养成分库（共{len(rows)}条）：")
    print("-" * 90)
    print(f"{'ID':>3} | {'产品名称':20} | {'品牌':10} | {'热量':>5} | {'蛋白':>5} | {'脂':>4} | {'碳':>5} | {'钠':>6}")
    print("-" * 90)

    for row in rows:
        id_, name, brand, cal, pro, fat_, sat_fat, carb, sugar, fiber, sodium, note, created = row
        brand = brand or '-'
        print(f"{id_:>3} | {name:20} | {brand:10} | {cal:>5} | {pro:>5} | {fat_:>4} | {carb:>5} | {sodium:>6}")

    print("-" * 90)
    return rows


def history(days=7):
    """显示热量历史"""
    conn = get_db()
    c = conn.cursor()

    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
        FROM entries
        WHERE date >= ?
        GROUP BY date
        ORDER BY date DESC
    ''', (start,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"最近{days}天无记录")
        return

    goal = get_goal()
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


def add_water(ml, target_date=None, target_time=None):
    """记录饮水"""
    try:
        ml = int(ml)
        if ml <= 0:
            print("Error: 饮水量必须为正数")
            return False
    except ValueError:
        print("Error: 饮水量必须是数字（ml）")
        return False

    conn = get_db()
    c = conn.cursor()

    today = target_date or date.today().isoformat()
    now = target_time or datetime.now().strftime("%H:%M:%S")

    c.execute('''
        INSERT INTO entries (date, time, food_name, grams, calories, protein, carbs, fat, note)
        VALUES (?, ?, '💧水', ?, 0, 0, 0, 0, '')
    ''', (today, now, ml))

    entry_id = c.lastrowid
    conn.commit()

    # 今日饮水汇总
    c.execute('''
        SELECT COALESCE(SUM(grams), 0)
        FROM entries
        WHERE date = ? AND food_name = '💧水'
    ''', (today,))
    total_water = c.fetchone()[0]

    # 获取目标
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    goal_row = c.fetchone()
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


def usage():
    """Print usage information"""
    print("""
卡路里 - 用法

命令：
  add <食物> <卡路里> <蛋白质> [碳水] [脂肪] [克数] [备注]
                                   添加食物记录
  delete <id>                       删除记录
  list                               列出今日记录
  summary                            今日摘要
  goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]
                                   设置每日目标
  water <ml>                        记录饮水
  weight <公斤> [身高cm] [备注]       记录体重
  weight-history [天数]              体重历史（默认30天）
  history [天数]                    热量历史（默认7天）

  add-product <名称> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠> [备注]
                                   添加食品营养成分表
  search-product <关键词>             搜索营养成分
  update-product <id> [--字段 值]    更新营养成分
  list-products [数量]               列出所有营养成分

示例：
  add "鸡胸肉" 165 31 0 3 150
  add "米饭" 116 2 25 0 200
  goal 1800 150 200 50 2000
  water 500
  weight 70 178
  add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "经典款330ml"
  search-product "可乐"
  update-product 1 --calories 45 --note "更新包装"
""")


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "add":
            if len(sys.argv) < 5:
                print("Error: add requires <food> <calories> <protein> [carbs] [fat] [grams] [note]")
                print("  用法: add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] [--date YYYY-MM-DD] [--time HH:MM] [--meal 餐次]")
                print("  示例: add \"鸡胸肉\" 165 31 0 3 150")
                print("  示例: add \"面包\" 150 3 20 5 80 --date 2026-06-20 --time 15:00 --meal 午餐")
                sys.exit(1)
            # 解析 --key value 风格参数
            positional = []
            kwargs = {}
            args = sys.argv[2:]
            i = 0
            while i < len(args):
                if args[i].startswith('--'):
                    key = args[i][2:]
                    if i + 1 < len(args) and not args[i+1].startswith('--'):
                        kwargs[key] = args[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    positional.append(args[i])
                    i += 1

            food = positional[0] if len(positional) > 0 else None
            calories = positional[1] if len(positional) > 1 else None
            protein = positional[2] if len(positional) > 2 else None
            carbs = positional[3] if len(positional) > 3 else '0'
            fat = positional[4] if len(positional) > 4 else '0'
            grams = positional[5] if len(positional) > 5 else '100'
            note = positional[6] if len(positional) > 6 else ''

            if not food or not calories or not protein:
                print("Error: 食物、热量、蛋白质为必填参数")
                sys.exit(1)

            target_date = kwargs.get('date')
            target_time = kwargs.get('time')
            meal_override = kwargs.get('meal')

            add_entry(food, calories, protein, carbs, fat, grams, note,
                      target_date=target_date, target_time=target_time,
                      meal_override=meal_override)

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires <id>")
                sys.exit(1)
            delete_entry(sys.argv[2])

        elif command == "list":
            list_entries()

        elif command == "summary":
            summary()

        elif command == "water":
            if len(sys.argv) < 3:
                print("Error: water requires <ml>")
                print("  用法: water <ml> [--date YYYY-MM-DD]")
                print("  示例: water 500")
                print("  示例: water 500 --date 2026-06-20")
                sys.exit(1)
            # 解析 --date 参数
            water_ml = sys.argv[2]
            target_date = None
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i].startswith('--date') and i + 1 < len(args):
                    target_date = args[i + 1]
                    i += 2
                else:
                    i += 1
            add_water(water_ml, target_date=target_date)

        elif command == "goal":
            if len(sys.argv) < 6:
                print("Error: goal 必须 4 个参数全传（v2.2 修改）")
                print("  用法: goal <热量> <蛋白> <碳水> <脂肪> [饮水ml]")
                print("  示例: goal 1850 150 200 50 2000")
                sys.exit(1)
            calorie_goal = sys.argv[2]
            protein_goal = sys.argv[3]
            carbs_goal = sys.argv[4]
            fat_goal = sys.argv[5]
            water_goal = sys.argv[6] if len(sys.argv) > 6 else None
            set_goal(calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal)

        elif command == "weight":
            if len(sys.argv) < 4:
                print("Error: weight requires <kg> <height_cm> [note]")
                print("  用法: weight <公斤> <身高cm> [备注]")
                print("  示例: weight 70 178")
                sys.exit(1)
            weight = sys.argv[2]
            height = sys.argv[3]
            note = sys.argv[4] if len(sys.argv) > 4 else ''
            log_weight(weight, height, note)

        elif command == "weight-update":
            if len(sys.argv) < 3:
                print("Error: weight-update requires <id> [--weight <公斤>] [--height <身高cm>] [--note <备注>]")
                print("  用法: weight-update <记录ID> [--weight <公斤>] [--height <身高cm>] [--note <备注>]")
                print("  示例: weight-update 5 --weight 69.5")
                print("  示例: weight-update 5 --height 179")
                sys.exit(1)
            weight_id = sys.argv[2]
            # 解析 --weight, --height, --note
            kwargs = {}
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i].startswith('--'):
                    key = args[i][2:]
                    if key in ('weight', 'height', 'note'):
                        if i + 1 < len(args) and not args[i+1].startswith('--'):
                            kwargs[key] = args[i+1]
                            i += 2
                        else:
                            i += 1
                    else:
                        i += 1
                else:
                    i += 1
            update_weight(weight_id,
                          weight_kg=kwargs.get('weight'),
                          height_cm=kwargs.get('height'),
                          note=kwargs.get('note'))

        elif command == "weight-history":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            weight_history(days)

        elif command == "history":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            history(days)

        elif command == "add-product":
            if len(sys.argv) < 11:
                print("Error: add-product requires <name> <brand> <cal> <protein> <fat> <saturated_fat> <carbs> <sugar> <fiber> <sodium> [note]")
                sys.exit(1)
            product_name = sys.argv[2]
            brand = sys.argv[3]
            calories = float(sys.argv[4])
            protein = float(sys.argv[5])
            fat = float(sys.argv[6])
            saturated_fat = float(sys.argv[7]) or None
            carbs = float(sys.argv[8])
            sugar = float(sys.argv[9]) or None
            fiber = float(sys.argv[10]) or None
            sodium = float(sys.argv[11])
            note = sys.argv[12] if len(sys.argv) > 12 else ''
            add_product(product_name, brand, calories, protein, fat, saturated_fat, carbs, sugar, fiber, sodium, note)

        elif command == "search-product":
            if len(sys.argv) < 3:
                print("Error: search-product requires <keyword>")
                sys.exit(1)
            search_product(sys.argv[2])

        elif command == "update-product":
            if len(sys.argv) < 3:
                print("Error: update-product requires <product_id> [--field value ...]")
                sys.exit(1)
            product_id = sys.argv[2]
            # Parse --key value pairs
            kwargs = {}
            args = sys.argv[3:]
            i = 0
            while i < len(args):
                if args[i].startswith('--'):
                    key = args[i][2:]
                    if i + 1 < len(args) and not args[i+1].startswith('--'):
                        kwargs[key] = args[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            update_product(product_id, **kwargs)

        elif command == "list-products":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            list_products(limit)

        else:
            print(f"Error: Unknown command '{command}'")
            usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
