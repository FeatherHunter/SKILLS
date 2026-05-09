#!/usr/bin/env python3
"""
卡路里 - 热量追踪脚本 v2.0
支持：食物记录(热量/蛋白质/碳水/脂肪)、每日目标、体重追踪
"""

import sqlite3
import os
import sys
from datetime import date, datetime
from pathlib import Path

# Database path - three-tier lookup: env var > skill dir > parent .db folder
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"

def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename

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
    except:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN goal_deadline TEXT')
    except:
        pass
    c.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON nutrition_products(product_name)')

    conn.commit()
    conn.close()


def get_db():
    """Get database connection"""
    if not DB_PATH.exists():
        init_db()
    return sqlite3.connect(DB_PATH)


def infer_meal_type(time_str):
    """根据时间自动推断餐次"""
    try:
        hour = int(time_str.split(':')[0])
    except:
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


def add_entry(food_name, calories, protein, carbs=0, fat=0, grams=100, note='', target_date=None, target_time=None):
    """添加食物记录"""
    try:
        calories = int(calories)
        protein = int(protein)
        carbs = int(carbs)
        fat = int(fat)
        grams = int(grams)
    except ValueError:
        print("Error: All nutrition values must be numbers")
        return False

    if calories < 0 or protein < 0 or carbs < 0 or fat < 0 or grams <= 0:
        print("Error: Values cannot be negative")
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

    meal = infer_meal_type(now)
    print(f"✓ 已记录：{food_name} ({calories}卡, {protein}蛋白, {carbs}碳, {fat}脂, {grams}克)")
    print(f"  餐次：{meal} | 条目ID：{entry_id}")

    if goal_row:
        cal_goal, pro_goal, carb_goal, fat_goal = goal_row[1], goal_row[2], goal_row[3], goal_row[4]
        remaining = cal_goal - total_cal
        print(f"  今日：{total_cal}/{cal_goal}卡 | 蛋白{total_pro}/{pro_goal}克 | 碳{total_carbs}/{carb_goal}克 | 脂{total_fat}/{fat_goal}克")
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


def set_goal(calorie_goal, protein_goal=None, carbs_goal=None, fat_goal=None):
    """设置每日目标"""
    try:
        calorie_goal = int(calorie_goal)
        if calorie_goal <= 0:
            print("Error: Calorie goal must be positive")
            return False
    except ValueError:
        print("Error: Calories must be a number")
        return False

    conn = get_db()
    c = conn.cursor()

    # 如果没指定宏量营养目标，使用默认值
    protein_goal = protein_goal or 150
    carbs_goal = carbs_goal or 200
    fat_goal = fat_goal or 60

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
        meal = infer_meal_type(time) if time else ""
        print(f"{entry_id:>3} | {time[0:5]:>5} | {food_name:15} | {grams:>4} | {calories:>5} | {protein:>5} | {carbs:>4} | {fat:>4} | {note or ''}")

    print("-" * 70)
    return rows


def summary(target_date=None):
    """显示每日摘要"""
    if target_date is None:
        target_date = date.today().isoformat()

    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*)
        FROM entries
        WHERE date = ?
    ''', (target_date,))

    total_cal, total_pro, total_carbs, total_fat, entry_count = c.fetchone()
    total_cal = total_cal or 0
    total_pro = total_pro or 0
    total_carbs = total_carbs or 0
    total_fat = total_fat or 0
    entry_count = entry_count or 0

    goal = get_goal()
    conn.close()

    print(f"\n{'='*60}")
    print(f"今日摘要 - {target_date}")
    print(f"{'='*60}")
    print(f"记录数：{entry_count}")

    if goal:
        cal_goal, pro_goal, carb_goal, fat_goal = goal[1], goal[2], goal[3], goal[4]
        cal_remaining = cal_goal - total_cal
        pro_remaining = pro_goal - total_pro
        carb_remaining = carb_goal - total_carbs
        fat_remaining = fat_goal - total_fat

        print(f"\n热量：{total_cal}/{cal_goal}卡 | 剩余：{cal_remaining:+d}")
        print(f"蛋白：{total_pro}/{pro_goal}克 | 剩余：{pro_remaining:+d}")
        print(f"碳水：{total_carbs}/{carb_goal}克 | 剩余：{carb_remaining:+d}")
        print(f"脂肪：{total_fat}/{fat_goal}克 | 剩余：{fat_remaining:+d}")

        if cal_remaining < 0:
            print(f"\n⚠️ 热量超标：{abs(cal_remaining)}卡")
    else:
        print(f"\n总热量：{total_cal}卡（未设置目标）")

    print(f"{'='*60}\n")

    if entry_count > 0:
        list_entries(target_date)


def log_weight(weight_kg, height_cm=None, note='', target_date=None, target_time=None):
    """记录体重"""
    try:
        weight_kg = float(weight_kg)
        if weight_kg <= 0:
            print("Error: Weight must be positive")
            return False
    except ValueError:
        print("Error: Weight must be a number")
        return False

    height_cm = float(height_cm) if height_cm else None
    
    # 计算BMI
    bmi = None
    if height_cm and height_cm > 0:
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
    """设置体重目标
    
    Args:
        weight_goal: 目标体重(kg)，如 73.0
        deadline: 目标日期，如 '2026-07-01'，可选
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO daily_goal (id, weight_goal, goal_deadline, updated_at)
        VALUES (1, ?, ?, datetime('now'))
    ''', (weight_goal, deadline))
    conn.commit()
    conn.close()
    print(f"✓ 体重目标已设定：{weight_goal} kg" + (f" | 目标日期：{deadline}" if deadline else ""))


def get_weight_goal():
    """获取体重目标，返回 (weight_goal, deadline, days_left, daily_change_rate, calorie_adjustment)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()

    if not row or not row[0]:
        return None

    weight_goal, deadline = row

    # 获取最近一次体重
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = c.fetchone()
    conn.close()

    if not wrow:
        return (weight_goal, deadline, None, None, None)

    current_weight, current_date = wrow

    # 计算日均变化（近30天有记录期间）
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT MIN(weight_kg), MAX(weight_kg), date FROM weight_log
        WHERE date >= date('now', '-30 days')
    ''')
    min_w, max_w, _ = c.fetchone()
    conn.close()

    daily_change_rate = None
    days_left = None
    calorie_adjustment = None

    if deadline:
        from datetime import datetime
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
        today_dt = datetime.strptime(current_date, '%Y-%m-%d')
        days_left = (deadline_dt - today_dt).days

    if days_left is not None and days_left > 0:
        gap = current_weight - weight_goal
        required_daily = gap / days_left  # kg/day

        # 7700kcal ≈ 1kg 脂肪
        calorie_adjustment = int(required_daily * 7700)  # 正=需增加缺口，负=需减少缺口

    return (weight_goal, deadline, days_left, daily_change_rate, calorie_adjustment)


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
    from datetime import date
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
    from collections import defaultdict
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

    c.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
        FROM entries
        WHERE date >= date('now', '-' || ? || ' days')
        GROUP BY date
        ORDER BY date DESC
    ''', (days,))

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
            status = f"{remaining:+d}卡" if remaining != 0 else "达标"
        else:
            status = "未设目标"
        
        print(f"{date_str:>10} | {total_cal:>5} | {total_pro:>5} | {total_carbs:>5} | {total_fat:>5} | {status}")

    print()


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
  goal <热量> [蛋白质] [碳水] [脂肪]  设置每日目标
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
  goal 1800 156 200 60
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
                sys.exit(1)
            food = sys.argv[2]
            calories = sys.argv[3]
            protein = sys.argv[4]
            carbs = sys.argv[5] if len(sys.argv) > 5 else 0
            fat = sys.argv[6] if len(sys.argv) > 6 else 0
            grams = sys.argv[7] if len(sys.argv) > 7 else 100
            note = sys.argv[8] if len(sys.argv) > 8 else ''
            add_entry(food, calories, protein, carbs, fat, grams, note)

        elif command == "delete":
            if len(sys.argv) < 3:
                print("Error: delete requires <id>")
                sys.exit(1)
            delete_entry(sys.argv[2])

        elif command == "list":
            list_entries()

        elif command == "summary":
            summary()

        elif command == "goal":
            if len(sys.argv) < 3:
                print("Error: goal requires <calories> [protein] [carbs] [fat]")
                sys.exit(1)
            calorie_goal = sys.argv[2]
            protein_goal = sys.argv[3] if len(sys.argv) > 3 else None
            carbs_goal = sys.argv[4] if len(sys.argv) > 4 else None
            fat_goal = sys.argv[5] if len(sys.argv) > 5 else None
            set_goal(calorie_goal, protein_goal, carbs_goal, fat_goal)

        elif command == "weight":
            if len(sys.argv) < 3:
                print("Error: weight requires <kg> [height_cm] [note]")
                sys.exit(1)
            weight = sys.argv[2]
            height = sys.argv[3] if len(sys.argv) > 3 else None
            note = sys.argv[4] if len(sys.argv) > 4 else ''
            log_weight(weight, height, note)

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
            saturated_fat = float(sys.argv[7]) if sys.argv[7] != '0' else None
            carbs = float(sys.argv[8])
            sugar = float(sys.argv[9]) if sys.argv[9] != '0' else None
            fiber = float(sys.argv[10]) if sys.argv[10] != '0' else None
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


# ============================================================
# 分析系统 - 10个分析函数
# ============================================================

def _parse_date(s):
    """解析日期字符串为 YYYY-MM-DD"""
    if s is None:
        return None
    s = str(s).strip()
    # 支持 YYYYMMDD 和 YYYY-MM-DD
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _days_between(d1, d2):
    """计算两个日期之间的天数差"""
    from datetime import datetime
    try:
        return (datetime.strptime(d2, '%Y-%m-%d') - datetime.strptime(d1, '%Y-%m-%d')).days
    except:
        return 0


# ---- 体重分析 ----

def weight_trend(start_date, end_date=None):
    """体重趋势分析，近30天或指定范围"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, weight_kg, note FROM weight_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无体重记录（{start_date} ~ {end_date}）")
        return None

    weights = [(r[0], r[1], r[2] or '') for r in rows]
    count = len(weights)
    avg_w = sum(w[1] for w in weights) / count
    max_w = max(w[1] for w in weights)
    min_w = min(w[1] for w in weights)
    first_w = weights[0][1]
    last_w = weights[-1][1]
    change = last_w - first_w
    span = _days_between(weights[0][0], weights[-1][0]) + 1
    daily_rate = (change / span) * 1000  # g/天

    if abs(daily_rate) < 10:
        trend_label = "平稳 ✓"
    elif change > 0:
        trend_label = "上升 ↑"
    else:
        trend_label = "下降 ✓"

    print(f"""
📊 体重趋势（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{count}条
  均重：{avg_w:.1f}kg | 最高：{max_w:.1f}kg | 最低：{min_w:.1f}kg
  首日：{weights[0][0]} {first_w:.1f}kg
  末日：{weights[-1][0]} {last_w:.1f}kg
  变化：{change:+.1f}kg | 日均变化：{daily_rate:+.0f}g/天
  趋势判断：{trend_label}
{'-'*40}""")
    return rows


def weight_compare(start_date, end_date, compare_start, compare_end):
    """两个时间段体重对比"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    compare_start = _parse_date(compare_start)
    compare_end = _parse_date(compare_end)

    conn = get_db()
    c = conn.cursor()

    def avg_weight(s, e):
        c.execute('''SELECT AVG(weight_kg) FROM weight_log WHERE date >= ? AND date <= ?''', (s, e))
        r = c.fetchone()[0]
        return r

    def first_last(s, e):
        c.execute('''SELECT weight_kg, date FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date ASC LIMIT 1''', (s, e))
        r1 = c.fetchone()
        c.execute('''SELECT weight_kg FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT 1''', (s, e))
        r2 = c.fetchone()
        return (r1[0], r1[1]) if r1 else None, r2[0] if r2 else None

    avg1 = avg_weight(start_date, end_date)
    avg2 = avg_weight(compare_start, compare_end)
    fl1 = first_last(start_date, end_date)
    fl2 = first_last(compare_start, compare_end)
    conn.close()

    if avg1 is None or avg2 is None:
        print("⚠️ 对比时间段内无体重记录，无法对比")
        return None

    avg_diff = avg1 - avg2
    change1 = fl1[1] - fl1[0] if fl1[0] and fl1[1] else 0
    change2 = fl2[1] - fl2[0] if fl2[0] and fl2[1] else 0
    change_diff = change1 - change2

    if change_diff > 0:
        speed_label = "较上期加速下降" if change1 < 0 else "较上期加速上升"
    elif change_diff < 0:
        speed_label = "较上期减速下降" if change1 < 0 else "较上期减速上升"
    else:
        speed_label = "节奏与上期相同"

    print(f"""
⚖️ 体重对比
{'-'*40}
  本期（{start_date} ~ {end_date}）
    均重：{avg1:.1f}kg
    首→末：{fl1[0]:.1f} → {fl1[1]:.1f}kg（{change1:+.1f}kg）
  对比（{compare_start} ~ {compare_end}）
    均重：{avg2:.1f}kg
    首→末：{fl2[0]:.1f} → {fl2[1]:.1f}kg（{change2:+.1f}kg）
  变化：{avg_diff:+.1f}kg（{'下降' if avg_diff < 0 else '上升'}）
  趋势：{speed_label}
{'-'*40}""")
    return avg_diff


def weight_milestone():
    """体重目标进度分析"""
    result = get_weight_goal()
    if not result or result[0] is None:
        print("⚠️ 未设定体重目标，请说「设定体重目标 XXkg」")
        return None

    weight_goal, deadline, days_left, daily_change_rate, calorie_adj = result

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    row = c.fetchone()
    if not row:
        print("⚠️ 未记录体重")
        conn.close()
        return None
    current_weight, current_date = row
    conn.close()

    gap = current_weight - weight_goal

    # 计算实际日均变化（近30天）
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT MIN(weight_kg), MAX(weight_kg) FROM weight_log WHERE date >= date('now', '-30 days')''')
    min_w, max_w = c.fetchone()
    conn.close()

    actual_daily = None
    if min_w and max_w and min_w != max_w:
        actual_daily = (max_w - min_w) / 30

    # 估算剩余时间
    if days_left is not None:
        est_days = days_left
    elif actual_daily and actual_daily != 0:
        est_days = abs(gap / actual_daily)
    else:
        est_days = None

    if est_days and est_days > 0:
        from datetime import datetime, timedelta
        est_date = (datetime.strptime(current_date, '%Y-%m-%d') + timedelta(days=est_days)).strftime('%Y-%m-%d')
    else:
        est_date = "未知"

    # 状态判断
    if days_left is not None and actual_daily:
        required = gap / days_left if days_left > 0 else 0
        diff = actual_daily - required
        if abs(diff) < 0.02:
            status = "进度正常 ✓"
        elif diff > 0:
            status = "进度超前 ✓"
        else:
            status = "进度偏慢 ⚠️"
    else:
        status = "无法评估"

    gap_str = f"{gap:+.1f}kg"
    actual_str = f"{actual_daily:.2f}kg/天" if actual_daily else "数据不足"
    est_date_str = est_date if isinstance(est_date, str) else "未知"
    est_days_str = f"{est_days:.0f}天" if est_days else "未知"

    print(f"""🎯 体重目标进度
{'-'*40}
  当前：{current_weight:.1f}kg（{current_date}）
  目标：{weight_goal:.1f}kg""" + (f" | 目标日期：{deadline}" if deadline else "") + f"""
  差距：{gap_str} | 实际日均变化：{actual_str}（近30天）
  预计达成：{est_date_str}（约{est_days_str}）
  状态：{status}
{'-'*40}""")
    return result


def weight_volatility(start_date, end_date=None):
    """体重波动分析"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, weight_kg, note FROM weight_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows or len(rows) < 3:
        print(f"⚠️ 记录不足（{start_date} ~ {end_date}），需要至少3条记录")
        return None

    weights = [r[1] for r in rows]
    dates = [r[0] for r in rows]

    import statistics
    std_dev = statistics.stdev(weights) if len(weights) >= 2 else 0

    # 计算周间波动
    from collections import defaultdict
    from datetime import datetime

    week_weights = defaultdict(list)
    for d, w in zip(dates, weights):
        week_key = datetime.strptime(d, '%Y-%m-%d').strftime('%Y-W%W')
        week_weights[week_key].append(w)

    week_avgs = [sum(v) / len(v) for v in week_weights.values()]
    week_std = statistics.stdev(week_avgs) if len(week_avgs) >= 2 else 0

    # 标记异常（单日涨跌幅 > 0.5kg）
    anomalies = []
    for i in range(1, len(rows)):
        diff = rows[i][1] - rows[i-1][1]
        if abs(diff) > 0.5:
            note = rows[i][2] or ""
            anomalies.append(f"{rows[i][0]} {diff:+.1f}kg（{note}）")

    if std_dev < 0.3:
        vol_label = "波动正常 ✓"
    elif std_dev < 0.6:
        vol_label = "波动中等"
    else:
        vol_label = "波动较大 ⚠️"

    print(f"""📉 体重波动分析（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{len(rows)}条
  日间波动：±{std_dev:.2f}kg（标准差）
  周间波动：±{week_std:.2f}kg""")
    if anomalies:
        print(f"  异常记录（单日>0.5kg）：")
        for a in anomalies:
            print(f"    - {a}")
    else:
        print(f"  异常记录：无")
    print(f"  评估：{vol_label}")
    print(f"{'-'*40}")

def diet_calorie_trend(start_date, end_date=None):
    """饮食热量趋势"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
        FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    total_cal = sum(r[1] or 0 for r in rows)
    avg_cal = total_cal / len(rows)

    goal = get_goal()
    cal_goal = goal[1] if goal else None
    on_target = sum(1 for r in rows if cal_goal and abs((r[1] or 0) - cal_goal) <= cal_goal * 0.1)

    from datetime import datetime
    weekday_cal, weekend_cal = 0, 0
    wd_count, we_count = 0, 0
    for r in rows:
        weekday = datetime.strptime(r[0], '%Y-%m-%d').weekday()
        if weekday < 5:
            weekday_cal += r[1] or 0
            wd_count += 1
        else:
            weekend_cal += r[1] or 0
            we_count += 1

    wd_avg = weekday_cal / wd_count if wd_count else 0
    we_avg = weekend_cal / we_count if we_count else 0

    print(f"""🔥 热量趋势（{start_date} ~ {end_date}）
{'-'*40}
  总摄入：{total_cal:.0f}卡 | 日均：{avg_cal:.0f}卡 | 天数：{len(rows)}""")
    if cal_goal:
        print(f"  目标：{cal_goal}卡 | 合规天数：{on_target}/{len(rows)}天")
    print(f"  工作日日均：{wd_avg:.0f}卡 | 周末日均：{we_avg:.0f}卡")
    print(f"{'-'*40}""")
    return rows


def diet_macro_ratio(start_date, end_date=None):
    """营养素占比分析"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT SUM(protein)*4, SUM(carbs)*4, SUM(fat)*9
        FROM entries
        WHERE date >= ? AND date <= ?
    ''', (start_date, end_date))
    row = c.fetchone()
    conn.close()

    if not row or sum(row) == 0:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    cal_from_pro, cal_from_carb, cal_from_fat = row
    total_cal_from_macros = cal_from_pro + cal_from_carb + cal_from_fat
    if total_cal_from_macros == 0:
        total_cal_from_macros = 1

    pct_pro = cal_from_pro / total_cal_from_macros * 100
    pct_carb = cal_from_carb / total_cal_from_macros * 100
    pct_fat = cal_from_fat / total_cal_from_macros * 100

    goal = get_goal()

    def macro_target_pct(macro_cal, total_macro_cal):
        if total_macro_cal <= 0:
            return None
        return macro_cal / total_macro_cal * 100

    def eval_pct(pct, name):
        if pct is None:
            return f"{pct:.0f}%（未设目标）"
        diff = pct - 35 if name == '碳' else (pct - 30 if name == '蛋白' else pct - 35)
        arrow = "↑" if diff > 3 else ("↓" if diff < -3 else "✓")
        status = "偏高" if diff > 3 else ("偏低" if diff < -3 else "正常")
        return f"{pct:.0f}% {arrow} {status}"

    print(f"""🥗 营养素占比（{start_date} ~ {end_date}）
{'-'*40}
  蛋白质：{eval_pct(pct_pro, '蛋白')}
  碳  水：{eval_pct(pct_carb, '碳')}
  脂  肪：{eval_pct(pct_fat, '脂')}
{'-'*40}""")
    return row


def diet_food_ranking(start_date, end_date=None, category='high_calorie', top_n=5):
    """食物TOP榜
    category: high_calorie | low_calorie | frequent | high_carb | high_protein
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT food_name, SUM(calories) as total_cal, SUM(grams) as total_grams,
               SUM(protein), SUM(carbs), SUM(fat), COUNT(*) as cnt
        FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY food_name
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    if category == 'high_calorie':
        sorted_rows = sorted(rows, key=lambda x: x[1], reverse=True)[:top_n]
        title = f"🔥 热量炸弹榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]:>6}卡（{r[6]}次）  均{r[1]//max(r[6],1)}卡/次"
    elif category == 'low_calorie':
        sorted_rows = sorted(rows, key=lambda x: x[1]/max(x[6],1))[:top_n]
        title = f"🥬 低热量健康榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]:>6}卡（{r[6]}次）  均{r[1]//max(r[6],1)}卡/次"
    elif category == 'frequent':
        sorted_rows = sorted(rows, key=lambda x: x[6], reverse=True)[:top_n]
        title = f"📅 频繁吃榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[6]}次 | 总{r[1]}卡 | 均{r[1]//max(r[6],1)}卡/次"
    elif category == 'high_carb':
        sorted_rows = sorted(rows, key=lambda x: x[4] or 0, reverse=True)[:top_n]
        title = f"🍚 高碳水榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[4] or 0:>6}克碳（{r[6]}次）"
    elif category == 'high_protein':
        sorted_rows = sorted(rows, key=lambda x: x[3] or 0, reverse=True)[:top_n]
        title = f"💪 高蛋白榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[3] or 0:>6}克蛋白（{r[6]}次）"
    else:
        sorted_rows = rows[:top_n]
        title = f"📋 食物榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]}卡"

    print(f"{title}\n{'-'*50}")
    for i, r in enumerate(sorted_rows, 1):
        print(f"  {i}. " + line(r))
    print(f"{'-'*50}")
    return sorted_rows


def diet_deficit_analysis(start_date, end_date=None):
    """热量缺口分析"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, SUM(calories) FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY date ORDER BY date ASC
    ''', (start_date, end_date))
    diet_rows = c.fetchall()

    c.execute('''
        SELECT date, SUM(calories_burned) FROM exercise_log
        WHERE date >= ? AND date <= ?
        GROUP BY date ORDER BY date ASC
    ''', (start_date, end_date))
    ex_rows = c.fetchall()
    conn.close()

    if not diet_rows:
        print(f"⚠️ 无记录（{start_date} ~ {end_date}）")
        return None

    diet_map = {r[0]: r[1] for r in diet_rows}
    ex_map = {r[0]: r[1] for r in ex_rows}

    all_dates = sorted(set(diet_map.keys()))
    days = len(all_dates)

    total_intake = sum(diet_map.values())
    total_ex = sum(ex_map.values())
    avg_intake = total_intake / days
    avg_ex = total_ex / days

    c2 = get_db()
    cur2 = c2.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    c2.close()
    current_weight = wrow[0] if wrow else 70
    bmr = current_weight * 24 * 1.3

    avg_deficit = bmr + avg_ex - avg_intake
    total_deficit = avg_deficit * days
    kg_equivalent = total_deficit / 7700

    diet_contrib = abs(total_deficit - total_ex * days) / abs(total_deficit) * 100 if total_deficit != 0 else 0
    ex_contrib = total_ex / abs(total_deficit) * 100 if total_deficit != 0 else 0

    print(f"""📉 热量缺口分析（{start_date} ~ {end_date}）
{'-'*40}
  日均摄入：{avg_intake:.0f}卡 | 基础代谢：约{bmr:.0f}卡（{current_weight:.0f}kg）| 运动消耗：日均{avg_ex:.0f}卡
  日均缺口：{avg_deficit:.0f}卡（{'偏小' if 0 < avg_deficit < 300 else ('过大' if avg_deficit > 700 else '正常')}）
  累计缺口：{total_deficit:.0f}卡 ≈ {kg_equivalent:.2f}kg
  饮食贡献：{diet_contrib:.0f}% | 运动贡献：{ex_contrib:.0f}%
{'-'*40}""")
    return {'avg_deficit': avg_deficit, 'total_deficit': total_deficit, 'kg_equivalent': kg_equivalent}


# ---- 运动分析 ----

def exercise_trend(start_date, end_date=None):
    """运动趋势"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, exercise_type, duration_minutes, calories_burned
        FROM exercise_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无运动记录（{start_date} ~ {end_date}）")
        return None

    span = _days_between(start_date, end_date) + 1
    days_with_ex = len(set(r[0] for r in rows))
    total_cal = sum(r[3] for r in rows)
    total_dur = sum(r[2] or 0 for r in rows)
    avg_cal = total_cal / span
    avg_dur = total_dur / span

    dates = sorted(set(r[0] for r in rows))
    longest_streak = 1
    current_streak = 1
    from datetime import datetime
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], '%Y-%m-%d')
        d2 = datetime.strptime(dates[i], '%Y-%m-%d')
        if (d2 - d1).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    if len(dates) >= 2:
        max_gap = max((datetime.strptime(dates[i], '%Y-%m-%d') - datetime.strptime(dates[i-1], '%Y-%m-%d')).days - 1
                      for i in range(1, len(dates)))
    else:
        max_gap = span - 1

    print(f"""🏃 运动趋势（{start_date} ~ {end_date}）
{'-'*40}
  运动天数：{days_with_ex}/{span}天（{days_with_ex/span*100:.0f}%）
  总时长：{total_dur}分钟 | 总消耗：{total_cal}卡
  日均消耗：{avg_cal:.0f}卡/天 | 日均时长：{avg_dur:.0f}分钟/天
  最长连续运动：{longest_streak}天
  最长休息：{max_gap}天{" ⚠️ 建议动起来" if max_gap >= 7 else ""}
{'-'*40}""")
    return rows


def exercise_type_breakdown(start_date, end_date=None):
    """运动类型分布"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT exercise_type, SUM(calories_burned), COUNT(*), SUM(duration_minutes)
        FROM exercise_log
        WHERE date >= ? AND date <= ?
        GROUP BY exercise_type
        ORDER BY SUM(calories_burned) DESC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无运动记录（{start_date} ~ {end_date}）")
        return None

    total_cal = sum(r[1] for r in rows)
    total_cnt = sum(r[2] for r in rows)
    total_dur = sum(r[3] or 0 for r in rows)

    print(f"📊 运动类型分布（{start_date} ~ {end_date}）\n{'-'*40}")
    for r in rows:
        etype, cal, cnt, dur = r
        pct = cal / total_cal * 100
        print(f"  {etype:15} 消耗{cal}卡（{pct:.0f}%）| {cnt}次 | {dur or 0}分钟")
    print(f"\n  总计：{total_cal}卡 | {total_cnt}次 | {total_dur}分钟")
    print(f"{'-'*40}")
    return rows


def exercise_deficit_contribution(start_date, end_date=None):
    """运动对热量缺口的贡献"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT SUM(calories_burned) FROM exercise_log WHERE date >= ? AND date <= ?''', (start_date, end_date))
    total_ex = c.fetchone()[0] or 0
    c.execute('''SELECT SUM(calories) FROM entries WHERE date >= ? AND date <= ?''', (start_date, end_date))
    total_intake = c.fetchone()[0] or 0
    conn.close()

    span = _days_between(start_date, end_date) + 1

    c2 = get_db()
    cur2 = c2.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    c2.close()
    current_weight = wrow[0] if wrow else 70
    bmr = current_weight * 24 * 1.3

    bmr_total = bmr * span
    diet_deficit = bmr_total - total_intake
    total_deficit = bmr_total - total_intake + total_ex

    if total_deficit == 0:
        diet_pct = 50
        ex_pct = 50
    else:
        diet_pct = abs(diet_deficit) / abs(total_deficit) * 100
        ex_pct = total_ex / abs(total_deficit) * 100

    print(f"""💪 运动缺口贡献（{start_date} ~ {end_date}）
{'-'*40}
  饮食缺口：{diet_deficit:.0f}卡（{diet_pct:.0f}%）
  运动缺口：{total_ex:.0f}卡（{ex_pct:.0f}%）
  评估：{'运动贡献偏低，建议增加运动比例' if ex_pct < 15 else ('运动贡献较高 ✓' if ex_pct > 25 else '运动贡献适中')}
{'-'*40}""")
    return {'diet_pct': diet_pct, 'ex_pct': ex_pct}


# ---- 综合报告 ----

def weight_analysis(start_date, end_date=None, analysis_type='trend'):
    """体重分析统一入口
    
    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'trend': 趋势分析（均重/日均变化/趋势判断）
            - 'compare': 同期对比（需要 compare_start/compare_end）
            - 'milestone': 目标进度（预计达成日/状态）
            - 'volatility': 波动分析（标准差/异常记录）
    """
    if analysis_type == 'trend':
        return weight_trend(start_date, end_date)
    elif analysis_type == 'compare':
        # compare 需要额外参数，由调用方传入 compare_start/compare_end
        return weight_compare(start_date, end_date or start_date, start_date, end_date or start_date)
    elif analysis_type == 'milestone':
        return weight_milestone()
    elif analysis_type == 'volatility':
        return weight_volatility(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用趋势分析")
        return weight_trend(start_date, end_date)


def diet_analysis(start_date, end_date=None, analysis_type='calorie_trend'):
    """饮食分析统一入口
    
    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'calorie_trend': 热量趋势（工作日vs周末/合规率）
            - 'macro_ratio': 碳水/蛋白质/脂肪占比分析
            - 'food_ranking': 食物TOP榜（热量炸弹/低热量/频繁吃/高碳水/高蛋白）
            - 'deficit_analysis': 热量缺口分析（饮食+运动贡献）
    """
    if analysis_type == 'calorie_trend':
        return diet_calorie_trend(start_date, end_date)
    elif analysis_type == 'macro_ratio':
        return diet_macro_ratio(start_date, end_date)
    elif analysis_type == 'food_ranking':
        return diet_food_ranking(start_date, end_date, category='high_calorie')
    elif analysis_type == 'deficit_analysis':
        return diet_deficit_analysis(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用热量趋势")
        return diet_calorie_trend(start_date, end_date)


def exercise_analysis(start_date, end_date=None, analysis_type='exercise_trend'):
    """运动分析统一入口
    
    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'exercise_trend': 运动趋势（天数/时长/消耗/间隔）
            - 'type_breakdown': 运动类型分布（消耗/频次/时长占比）
            - 'deficit_contribution': 运动对缺口的贡献占比
    """
    if analysis_type == 'exercise_trend':
        return exercise_trend(start_date, end_date)
    elif analysis_type == 'type_breakdown':
        return exercise_type_breakdown(start_date, end_date)
    elif analysis_type == 'deficit_contribution':
        return exercise_deficit_contribution(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用运动趋势")
        return exercise_trend(start_date, end_date)


def dashboard(start_date, end_date=None):
    """综合健康报告"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    print(f"""
{'='*55}
  📋 综合健康报告（{start_date} ~ {end_date}）
{'='*55}""")

    print("\n📊 体重趋势")
    try:
        weight_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取体重数据: {e}")

    print("\n🔥 热量趋势")
    try:
        diet_calorie_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取热量数据: {e}")

    print("\n🏃 运动趋势")
    try:
        exercise_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取运动数据: {e}")

    print("\n📉 热量缺口")
    try:
        diet_deficit_analysis(start_date, end_date)
    except Exception as e:
        print(f"  无法获取缺口数据: {e}")

    print(f"\n{'='*55}")
