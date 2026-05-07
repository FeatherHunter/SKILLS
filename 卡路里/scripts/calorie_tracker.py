#!/usr/bin/env python3
"""
卡路里 - 热量追踪脚本 v2.0
支持：食物记录(热量/蛋白质/碳水/脂肪)、每日目标、体重追踪
"""

import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

# Database path relative to skill directory
SKILL_DIR = Path(__file__).parent.parent
DB_PATH = SKILL_DIR / "calorie_data.db"


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
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
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

    # Create indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_weight_date ON weight_log(date)')

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


def weight_history(days=30):
    """显示体重历史"""
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        SELECT date, time, weight_kg, bmi, note
        FROM weight_log
        ORDER BY date DESC, time DESC
        LIMIT ?
    ''', (days,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print("无体重记录")
        return

    print(f"\n体重历史（最近{days}天）：")
    print("-" * 50)
    print(f"{'日期':>10} | {'时间':>5} | {'体重(kg)':>8} | {'BMI':>5} | 备注")
    print("-" * 50)

    for date_str, time_str, weight, bmi, note in rows:
        bmi_str = f"{bmi:.1f}" if bmi else "-"
        note_str = note or ""
        print(f"{date_str:>10} | {time_str[0:5] if time_str else '':>5} | {weight:>8.1f} | {bmi_str:>5} | {note_str}")

    # 计算变化
    if len(rows) >= 2:
        first_weight = rows[-1][2]
        last_weight = rows[0][2]
        change = last_weight - first_weight

        print("-" * 50)
        if change > 0:
            print(f"变化：+{change:.1f}公斤")
        elif change < 0:
            print(f"变化：{change:.1f}公斤")
        else:
            print(f"变化：无变化")

    print()


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

示例：
  add "鸡胸肉" 165 31 0 3 150
  add "米饭" 116 2 25 0 200
  goal 1800 156 200 60
  weight 70 178
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

        else:
            print(f"Error: Unknown command '{command}'")
            usage()
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
