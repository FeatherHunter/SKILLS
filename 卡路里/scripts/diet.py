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

    # v2.4.16:CLI 端负责打印回执(契约格式),本函数只返 dict
    cal_goal, pro_goal, carb_goal, fat_goal = None, None, None, None
    if goal:
        cal_goal, pro_goal, carb_goal, fat_goal = goal[1], goal[2], goal[3], goal[4]

    return {
        'id': entry_id,
        'date': today,
        'time': now,
        'food_name': food_name,
        'meal': meal,
        'calories': calories,
        'protein': protein,
        'carbs': carbs,
        'fat': fat,
        'grams': grams,
        'note': note,
        'rows_affected': 1,
        'date_label': date_label,
        'today_total_cal': total_cal,
        'today_total_pro': total_pro,
        'today_total_carbs': total_carbs,
        'today_total_fat': total_fat,
        'cal_goal': cal_goal,
        'pro_goal': pro_goal,
        'carb_goal': carb_goal,
        'fat_goal': fat_goal,
        'remaining_cal': (cal_goal - total_cal) if cal_goal else None,
    }


# 可更新的字段白名单(v2.2.0 对齐 add_meal 接口)
# 注意: meal_type 不存 DB(从 time 推断),所以不在支持列表
_MEAL_UPDATABLE = {
    'food_name', 'grams', 'note',
    'date', 'time',
    'calories', 'protein', 'carbs', 'fat',
}


def update_meal(entry_id, **kwargs):
    """更新一条食物记录的任意可改字段(v2.2.0 接口对齐 add_meal)

    支持 8 个字段(与 add_meal 对称):
      - 标签: food_name, grams, note
      - 时间: date, time(meal_type 从 time 推断,不存 DB)
      - 营养: calories, protein, carbs, fat

    返回 dict{"ok": bool, "before": {...}, "after": {...}, "changed": [字段]}
    失败时 {"ok": False, "error": str}。
    """
    try:
        entry_id = int(entry_id)
    except (ValueError, TypeError):
        return {"ok": False, "error": "Entry ID must be a number"}

    bad = set(kwargs) - _MEAL_UPDATABLE
    if bad:
        return {"ok": False, "error": f"不支持字段: {sorted(bad)}; 支持: {sorted(_MEAL_UPDATABLE)}"}
    if not kwargs:
        return {"ok": False, "error": "至少传 1 个字段"}

    conn = _get_db()
    c = conn.cursor()

    # 改前全字段快照(回执 UI 用)
    c.execute('''
        SELECT id, date, time, food_name, grams, calories, protein, carbs, fat, note
        FROM food_log WHERE id = ?
    ''', (entry_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": f"Entry ID {entry_id} not found"}

    keys = ('id', 'date', 'time', 'food_name', 'grams', 'calories', 'protein', 'carbs', 'fat', 'note')
    before = dict(zip(keys, row))

    # 类型转换 + 负值校验
    typed = {}
    for k, v in kwargs.items():
        if k in ('grams', 'calories', 'protein', 'carbs', 'fat'):
            try:
                v = float(v)
            except (ValueError, TypeError):
                conn.close()
                return {"ok": False, "error": f"{k} 必须是数字: {v}"}
            if v < 0:
                conn.close()
                return {"ok": False, "error": f"{k} 不能为负: {v}"}
        typed[k] = v

    updates = ', '.join(f"{k} = ?" for k in typed)
    params = list(typed.values()) + [entry_id]
    c.execute(f"UPDATE food_log SET {updates} WHERE id = ?", params)
    conn.commit()

    # 改后快照(给回执 UI 用)
    c.execute('''
        SELECT id, date, time, food_name, grams, calories, protein, carbs, fat, note
        FROM food_log WHERE id = ?
    ''', (entry_id,))
    after = dict(zip(keys, c.fetchone()))
    conn.close()

    changed = [k for k in typed if before.get(k) != after.get(k)]
    print(f"✓ Updated entry {entry_id}: {after['food_name']} ({after['grams']}克, {after['calories']}卡)")
    print(f"  改动字段: {changed}")
    return {"ok": True, "before": before, "after": after, "changed": changed}


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


def copy_meals(from_date, to_date=None):
    """复制某日饮食到另一日(复制昨日饮食 · D1.8)

    只复制食物记录(排除 💧水),保持 time 不变。
    目标日已有同名同时间记录则跳过(防重复)。

    Returns:
        dict{ok, copied, skipped, from_date, to_date,
             copied_items, skipped_items}  # #44 审查:明细透出,回执可展示复制了什么
    """
    if to_date is None:
        to_date = date.today().isoformat()
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT time, food_name, grams, calories, protein, carbs, fat, note
        FROM food_log WHERE date = ? AND food_name != '💧水' ORDER BY time
    ''', (from_date,))
    rows = c.fetchall()
    copied = skipped = 0
    copied_items = []
    skipped_items = []
    for time_, food, grams, cal, pro, carb, fat, note in rows:
        c.execute('''
            SELECT COUNT(*) FROM food_log
            WHERE date = ? AND time = ? AND food_name = ?
        ''', (to_date, time_, food))
        if c.fetchone()[0] > 0:
            skipped += 1
            skipped_items.append({'time': time_, 'food_name': food, 'grams': grams,
                                  'calories': cal})
            continue
        c.execute('''
            INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (to_date, time_, food, grams, cal, pro, carb, fat, note))
        copied += 1
        copied_items.append({'time': time_, 'food_name': food, 'grams': grams,
                             'calories': cal})
    conn.commit()
    conn.close()
    return {'ok': True, 'copied': copied, 'skipped': skipped,
            'from_date': from_date, 'to_date': to_date,
            'copied_items': copied_items, 'skipped_items': skipped_items}


def add_meals_batch(entries):
    """批量补记饮食(D1.4 · 一次录多餐)

    Args:
        entries: list of dict,每项含 date/time/food_name/grams/calories/protein/carbs/fat/note
                 (calories/protein 必填,其余可缺省)

    Returns:
        dict{ok, added, skipped, failed, failures: [(index, reason), ...]}
    """
    conn = _get_db()
    c = conn.cursor()
    added = skipped = 0
    failures = []
    for i, e in enumerate(entries):
        try:
            food = str(e.get('food_name', '')).strip()
            cal = float(e.get('calories', 0))
            pro = float(e.get('protein', 0))
            if not food or cal < 0 or pro < 0:
                skipped += 1
                failures.append((i, '食物名必填,营养值不能为负'))
                continue
            c.execute('''
                INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(e.get('date', date.today().isoformat())),
                str(e.get('time', datetime.now().strftime('%H:%M:%S'))),
                food,
                float(e.get('grams', 100) or 100),
                cal, pro,
                float(e.get('carbs', 0) or 0),
                float(e.get('fat', 0) or 0),
                str(e.get('note', '') or ''),
            ))
            added += 1
        except (ValueError, TypeError) as ex:
            skipped += 1
            failures.append((i, f'数值非法: {ex}'))
    conn.commit()
    conn.close()
    return {'ok': True, 'added': added, 'skipped': skipped, 'failed': len(failures),
            'failures': failures}


def update_meals_by_date(target_date, **kwargs):
    """改某日饮食(D2.2 · 按日期批量更新)

    对目标日全部食物记录(排除 💧水)应用相同字段更新。
    支持字段同 update_meal(_MEAL_UPDATABLE)。

    Returns:
        dict{ok, matched, updated, before: [..], after: [..], changed_fields}
    """
    bad = set(kwargs) - _MEAL_UPDATABLE
    if bad:
        return {"ok": False, "error": f"不支持字段: {sorted(bad)}; 支持: {sorted(_MEAL_UPDATABLE)}"}
    if not kwargs:
        return {"ok": False, "error": "至少传 1 个字段"}

    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM food_log WHERE date = ? AND food_name != ?',
              (target_date, '💧水'))
    ids = [r[0] for r in c.fetchall()]
    if not ids:
        conn.close()
        return {"ok": True, "matched": 0, "updated": 0, "before": [], "after": [],
                "changed_fields": []}

    # 改前快照
    before = []
    for i in ids:
        c.execute('SELECT food_name, grams, calories, protein, carbs, fat, note, time FROM food_log WHERE id = ?', (i,))
        before.append(dict(zip(('food_name', 'grams', 'calories', 'protein', 'carbs', 'fat', 'note', 'time'), c.fetchone())))

    typed = {}
    for k, v in kwargs.items():
        if k in ('grams', 'calories', 'protein', 'carbs', 'fat'):
            try:
                v = float(v)
            except (ValueError, TypeError):
                conn.close()
                return {"ok": False, "error": f"{k} 必须是数字: {v}"}
            if v < 0:
                conn.close()
                return {"ok": False, "error": f"{k} 不能为负: {v}"}
        typed[k] = v

    updates = ', '.join(f"{k} = ?" for k in typed)
    params = list(typed.values())
    c.execute(f"UPDATE food_log SET {updates} WHERE date = ? AND food_name != ?",
              params + [target_date, '💧水'])
    conn.commit()

    after = []
    for i in ids:
        c.execute('SELECT food_name, grams, calories, protein, carbs, fat, note, time FROM food_log WHERE id = ?', (i,))
        after.append(dict(zip(('food_name', 'grams', 'calories', 'protein', 'carbs', 'fat', 'note', 'time'), c.fetchone())))
    conn.close()
    return {"ok": True, "matched": len(ids), "updated": len(ids),
            "before": before, "after": after, "changed_fields": sorted(typed)}


def delete_meals_by_date(target_date):
    """删某日饮食(D2.5 · 一整天清空,排除 💧水)

    Returns:
        dict{ok, deleted, date, before}
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute("SELECT date, time, food_name, grams, calories, note FROM food_log WHERE date = ? AND food_name != ?",
              (target_date, '💧水'))
    before = [dict(zip(('date', 'time', 'food_name', 'grams', 'calories', 'note'), r)) for r in c.fetchall()]
    c.execute("DELETE FROM food_log WHERE date = ? AND food_name != ?",
              (target_date, '💧水'))
    conn.commit()
    conn.close()
    return {'ok': True, 'deleted': len(before), 'date': target_date, 'before': before}


def delete_meals_by_range(start_date, end_date):
    """批量删饮食(D2.6 · 按日期范围,排除 💧水)

    Returns:
        dict{ok, deleted, start, end, before}
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute("SELECT date, time, food_name, grams, calories, note FROM food_log WHERE date BETWEEN ? AND ? AND food_name != ?",
              (start_date, end_date, '💧水'))
    before = [dict(zip(('date', 'time', 'food_name', 'grams', 'calories', 'note'), r)) for r in c.fetchall()]
    c.execute("DELETE FROM food_log WHERE date BETWEEN ? AND ? AND food_name != ?",
              (start_date, end_date, '💧水'))
    conn.commit()
    conn.close()
    return {'ok': True, 'deleted': len(before), 'start': start_date, 'end': end_date, 'before': before}


def delete_meals_by_type(target_date, meal_type):
    """删一餐(D2.4 · 按餐别删某日某餐)

    餐别按时间窗推断(与 infer_meal_type 同口径):
      早餐 6-10 / 午餐 10-14 / 下午茶 14-18 / 晚餐 18-22 / 夜宵 其他
    支持 4 类聚合(与餐别分布同口径):加餐 = 下午茶 + 夜宵

    Returns:
        dict{ok, deleted, date, meal, before}
    """
    windows = {
        '早餐': (6, 10), '午餐': (10, 14), '下午茶': (14, 18),
        '晚餐': (18, 22), '夜宵': (0, 6),
        '加餐': (14, 22, 0, 6),  # 复合:下午茶 + 夜宵
    }
    if meal_type not in windows:
        return {"ok": False, "error": f"餐别必须是 {'/'.join(windows)} 之一"}
    lo, hi = windows[meal_type][0], windows[meal_type][1]
    conn = _get_db()
    c = conn.cursor()
    if meal_type == '加餐':
        lo2, hi2 = windows[meal_type][2], windows[meal_type][3]
        c.execute('''
            SELECT date, time, food_name, grams, calories, note FROM food_log
            WHERE date = ? AND food_name != ? AND (
                (CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?)
                OR (CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?))
        ''', (target_date, '💧水', lo, hi, lo2, hi2))
        before = [dict(zip(('date', 'time', 'food_name', 'grams', 'calories', 'note'), r)) for r in c.fetchall()]
        c.execute('''
            DELETE FROM food_log
            WHERE date = ? AND food_name != ? AND (
                (CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?)
                OR (CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?))
        ''', (target_date, '💧水', lo, hi, lo2, hi2))
    elif lo < hi:
        c.execute('''
            SELECT date, time, food_name, grams, calories, note FROM food_log
            WHERE date = ? AND food_name != ? AND CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?
        ''', (target_date, '💧水', lo, hi))
        before = [dict(zip(('date', 'time', 'food_name', 'grams', 'calories', 'note'), r)) for r in c.fetchall()]
        c.execute('''
            DELETE FROM food_log
            WHERE date = ? AND food_name != ? AND CAST(strftime('%H', time) AS INT) >= ? AND CAST(strftime('%H', time) AS INT) < ?
        ''', (target_date, '💧水', lo, hi))
    else:  # 夜宵 0-6(跨日窗)
        c.execute('''
            SELECT date, time, food_name, grams, calories, note FROM food_log
            WHERE date = ? AND food_name != ? AND (CAST(strftime('%H', time) AS INT) >= ? OR CAST(strftime('%H', time) AS INT) < ?)
        ''', (target_date, '💧水', lo, hi))
        before = [dict(zip(('date', 'time', 'food_name', 'grams', 'calories', 'note'), r)) for r in c.fetchall()]
        c.execute('''
            DELETE FROM food_log
            WHERE date = ? AND food_name != ? AND (CAST(strftime('%H', time) AS INT) >= ? OR CAST(strftime('%H', time) AS INT) < ?)
        ''', (target_date, '💧水', lo, hi))
    conn.commit()
    conn.close()
    return {'ok': True, 'deleted': len(before), 'date': target_date, 'meal': meal_type, 'before': before}


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