#!/usr/bin/env python3
"""体重记录 — 体重添加/修改/历史

数据存储：weight_log 表
- weight_kg, height_cm, bmi (kg/m²)
- 身高必传，BMI 自动计算

关联：
- 体重目标 → weight_goal.py
- 身材照片 → body_photo_tracker.py（通过 created_at 关联最近体重）
"""

import sys
from datetime import date, datetime, timedelta
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


def log_weight(weight_kg, height_cm, note='', target_date=None, target_time=None):
    """记录体重（身高必传，BMI 必须计算）

    Args:
        weight_kg: 体重（公斤）
        height_cm: 身高（厘米），必传
        note: 备注
        target_date: 目标日期（YYYY-MM-DD），默认今天
        target_time: 目标时间（HH:MM:SS），默认当前
    """
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

    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)

    conn = _get_db()
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
    """按 ID 更新体重记录，若传身高则重算 BMI

    Args:
        weight_id: 体重记录 ID
        weight_kg: 新体重（公斤），可选
        height_cm: 新身高（厘米），可选
        note: 新备注，可选

    Returns:
        bool: 是否更新成功

    注意：
        - 至少需要传入 --weight / --height / --note 中的一个
        - 若旧记录无身高数据，必须同时传 --weight 和 --height
    """
    try:
        weight_id = int(weight_id)
    except ValueError:
        print("Error: 体重记录 ID 必须是数字")
        return False

    if weight_kg is None and height_cm is None and note is None:
        print("Error: 至少需要传入 --weight 或 --height 或 --note 中的一个")
        return False

    conn = _get_db()
    c = conn.cursor()

    c.execute('SELECT id, weight_kg, height_cm FROM weight_log WHERE id = ?', (weight_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: 体重记录 ID {weight_id} 不存在")
        conn.close()
        return False

    old_weight, old_height = row[1], row[2]

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


def get_weight_history(days=30, start_date=None, end_date=None):
    """显示体重历史

    支持三种调用方式：
    - get_weight_history(days=30)              # 最近N天（向后兼容）
    - get_weight_history(start_date='2026-01-01', end_date='2026-05-09')  # 日期范围
    - get_weight_history(start_date='2026-05-09', end_date='2026-05-09')  # 单日查询
    """
    conn = _get_db()
    c = conn.cursor()

    if start_date and end_date:
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
        c.execute('''
            SELECT date, time, weight_kg, bmi, note
            FROM weight_log
            WHERE date = ?
            ORDER BY time DESC
        ''', (start_date,))
        range_desc = start_date
    else:
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