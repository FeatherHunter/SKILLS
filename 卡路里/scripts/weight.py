#!/usr/bin/env python3
"""体重记录 — 体重添加/修改/历史

数据存储：weight_log 表
- weight_kg, height_cm(2026-07-20 起新记录只读 user_profile.height_cm), bmi
- 身高只在 user_profile(单一来源),新记录 weight_log.height_cm 自动从 profile 读

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


def log_weight(weight_kg, note='', target_date=None, target_time=None):
    """记录体重(2026-07-20 改:身高从 user_profile 自动读,不再接收 height 参数)

    Args:
        weight_kg: 体重(公斤)
        note: 备注
        target_date: 目标日期(YYYY-MM-DD),默认今天
        target_time: 目标时间(HH:MM:SS),默认当前

    Returns(v2.4.14 改):
        成功:dict 含 id/date/time/kg/bmi/note,满足 V1.0 §02 第②特性"回执 = ID + 时间戳 + 影响行数"
            例:{'id': 17, 'date': '2026-07-27', 'time': '12:00:00', 'kg': 70.0, 'bmi': 22.3, 'note': '测试', 'rows_affected': 1}
        失败:None
    """
    try:
        weight_kg = float(weight_kg)
        if weight_kg <= 0:
            print("Error: Weight must be positive")
            return None
    except ValueError:
        print("Error: Weight must be a number")
        return None

    # 2026-07-20 改:身高从 user_profile 读(单一来源)
    from profile import get_profile as _get_user_profile
    _p = _get_user_profile()
    if not _p or not _p.get('height_cm'):
        print("Error: user_profile 未设身高,无法计算 BMI")
        print("  请先跑:calorie_tracker.py profile set 30 male --height 177")
        return None
    height_cm = _p['height_cm']

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

    new_id = c.lastrowid
    conn.commit()
    conn.close()

    # v2.4.14:CLI 端负责渲染(V1.0 §02 第②特性"写入后回执"),本函数只返 dict
    return {
        'id': new_id,
        'date': today,
        'time': now,
        'kg': weight_kg,
        'bmi': bmi,
        'note': note,
        'rows_affected': 1,
    }


def update_weight(weight_id, weight_kg=None, note=None):
    """按 ID 更新体重记录(2026-07-20 改:height_cm 参数已删除)

    Args:
        weight_id: 体重记录 ID
        weight_kg: 新体重(公斤),可选
        note: 新备注,可选

    Returns(v2.4.18a 改):
        成功:dict 含 id/date/time/old_kg/new_kg/bmi/note/rows_affected (V1.0 §02 第②特性)
        失败:None

    注意:
        - 至少需要传入 --weight / --note 中的一个
        - BMI 自动从 user_profile 读身高重算(2026-07-20 改)
    """
    try:
        weight_id = int(weight_id)
    except ValueError:
        print("Error: 体重记录 ID 必须是数字")
        return None

    if weight_kg is None and note is None:
        print("Error: 至少需要传入 --weight 或 --note 中的一个")
        return None

    # 2026-07-20 改:身高从 user_profile 读
    from profile import get_profile as _get_user_profile
    _p = _get_user_profile()
    profile_height = _p.get('height_cm') if _p else None
    if profile_height is None or profile_height <= 0:
        print("Error: user_profile 未设身高,无法重算 BMI")
        print("  请先跑:calorie_tracker.py profile set 30 male --height 177")
        return None

    conn = _get_db()
    c = conn.cursor()

    c.execute('SELECT id, weight_kg, date, time FROM weight_log WHERE id = ?', (weight_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: 体重记录 ID {weight_id} 不存在")
        conn.close()
        return None

    old_id, old_weight, old_date, old_time = row

    new_weight = float(weight_kg) if weight_kg is not None else old_weight

    height_m = profile_height / 100
    bmi = round(new_weight / (height_m ** 2), 1)

    # 2026-07-20 改:不再写 height_cm 列(保留列,不动数据)
    set_parts = ["weight_kg = ?", "bmi = ?"]
    values = [new_weight, bmi]

    if note is not None:
        set_parts.append("note = ?")
        values.append(note)

    values.append(weight_id)
    set_clause = ", ".join(set_parts)

    c.execute(f'UPDATE weight_log SET {set_clause} WHERE id = ?', values)
    rows = c.rowcount
    conn.commit()
    conn.close()

    # v2.4.18a:CLI 端负责打印回执(契约格式)
    return {
        'id': old_id,
        'date': old_date,
        'time': old_time,
        'old_weight': old_weight,
        'new_weight': new_weight,
        'bmi': bmi,
        'note': note,
        'rows_affected': rows,
    }


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


# ===================== 2026-08-02 · 体重 58 场景业务层扩展(ticket #4) =====================

NOTE_TAGS = ['晨起空腹', '运动后', '睡前', '餐前', '餐后', '晨起', '空腹', '早起', '运动前', '生理期']


def note_tag(note):
    """备注 → 分类标签(看「有备注」的体重记录 · 分类分布)"""
    if not note:
        return None
    for tag in NOTE_TAGS:
        if tag in note:
            return tag
    return '其他'


def get_weight_goal_value():
    """统一读 daily_goal.weight_goal(目标体重单行表 id=1)"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal FROM daily_goal WHERE id = 1')
    g = c.fetchone()
    conn.close()
    return g[0] if g and g[0] else None


def delta_last(target_date=None):
    """距上次体重(kg):目标记录之前的最后一条(或目标当天首条之前)。无上次 → None"""
    d = target_date or date.today().isoformat()
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT weight_kg FROM weight_log
        WHERE (date < ?) OR (date = ? AND time < (SELECT MIN(time) FROM weight_log WHERE date = ?))
        ORDER BY date DESC, time DESC LIMIT 1
    ''', (d, d, d))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def goal_diff(weight_kg):
    """与目标体重差距(kg):有目标 → 返回差值;无目标 → None"""
    goal = get_weight_goal_value()
    if goal is None:
        return None
    return round(weight_kg - goal, 1)


def delete_weight(weight_id):
    """按 ID 删除体重记录(软删替代方案:物理 DELETE,返回删除前快照)

    Returns:
        dict: {id, date, time, weight_kg, bmi, note, deleted_count}
        失败:None(带错误输出)
    """
    try:
        weight_id = int(weight_id)
    except ValueError:
        print('Error: 体重记录 ID 必须是数字')
        return None
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT id, date, time, weight_kg, bmi, note FROM weight_log WHERE id = ?', (weight_id,))
    row = c.fetchone()
    if not row:
        print(f'Error: 体重记录 ID {weight_id} 不存在')
        conn.close()
        return None
    c.execute('DELETE FROM weight_log WHERE id = ?', (weight_id,))
    conn.commit()
    conn.close()
    return {
        'id': row[0], 'date': row[1], 'time': row[2], 'weight_kg': row[3],
        'bmi': row[4], 'note': row[5], 'deleted_count': 1,
    }


def delete_weight_by_date(target_date):
    """按日期删除该日全部体重记录

    Returns:
        dict: {date, deleted_count, snapshot: [dict...]} 或 None(无记录)
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT id, date, time, weight_kg, bmi, note FROM weight_log WHERE date = ? ORDER BY time', (target_date,))
    rows = c.fetchall()
    if not rows:
        conn.close()
        print(f'Error: {target_date} 无体重记录')
        return None
    c.execute('DELETE FROM weight_log WHERE date = ?', (target_date,))
    conn.commit()
    conn.close()
    return {
        'date': target_date,
        'deleted_count': len(rows),
        'snapshot': [{'id': r[0], 'date': r[1], 'time': r[2], 'weight_kg': r[3], 'bmi': r[4], 'note': r[5]} for r in rows],
    }


def delete_weight_range(start_date, end_date):
    """按日期范围批量删除体重记录

    Returns:
        dict: {start, end, deleted_count, snapshot: [dict...]} 或 None(无记录)
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, date, time, weight_kg, bmi, note FROM weight_log
        WHERE date BETWEEN ? AND ? ORDER BY date, time
    ''', (start_date, end_date))
    rows = c.fetchall()
    if not rows:
        conn.close()
        print(f'Error: {start_date} ~ {end_date} 无体重记录')
        return None
    c.execute('DELETE FROM weight_log WHERE date BETWEEN ? AND ?', (start_date, end_date))
    conn.commit()
    conn.close()
    return {
        'start': start_date, 'end': end_date,
        'deleted_count': len(rows),
        'snapshot': [{'id': r[0], 'date': r[1], 'time': r[2], 'weight_kg': r[3], 'bmi': r[4], 'note': r[5]} for r in rows],
    }


def update_weight_by_date(target_date, weight_kg=None, note=None):
    """按日期定位更新体重记录(改某日体重 · 命中 1+ 条全改)

    Returns:
        dict: {date, hit_count, old_rows: [dict...], new_weight, bmi, note}
        失败:None(无记录 / 缺参)
    """
    if weight_kg is None and note is None:
        print('Error: 至少需要传入 --weight 或 --note 中的一个')
        return None
    from profile import get_profile as _get_user_profile
    _p = _get_user_profile()
    profile_height = _p.get('height_cm') if _p else None
    if profile_height is None or profile_height <= 0:
        print('Error: user_profile 未设身高,无法重算 BMI')
        return None
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT id, date, time, weight_kg, bmi, note FROM weight_log WHERE date = ? ORDER BY time', (target_date,))
    rows = c.fetchall()
    if not rows:
        conn.close()
        print(f'Error: {target_date} 无体重记录')
        return None
    old_rows = [{'id': r[0], 'date': r[1], 'time': r[2], 'weight_kg': r[3], 'bmi': r[4], 'note': r[5]} for r in rows]
    height_m = profile_height / 100
    new_bmi = None
    if weight_kg is not None:
        new_kg = float(weight_kg)
        new_bmi = round(new_kg / (height_m ** 2), 1)
        c.execute('UPDATE weight_log SET weight_kg = ?, bmi = ? WHERE date = ?', (new_kg, new_bmi, target_date))
    if note is not None:
        c.execute('UPDATE weight_log SET note = ? WHERE date = ?', (note, target_date))
    conn.commit()
    conn.close()
    return {
        'date': target_date,
        'hit_count': len(rows),
        'old_rows': old_rows,
        'new_weight': float(weight_kg) if weight_kg is not None else None,
        'bmi': new_bmi,
        'note': note,
    }


def batch_log_weight(items):
    """批量补录体重(批量补录体重 · 写入/跳过/失败条数 + 明细)

    Args:
        items: [{date: 'YYYY-MM-DD', kg: float}, ...] 按时间顺序

    Returns:
        dict: {wrote, skipped, failed, items: [{date, kg, status, reason}]}
    """
    from profile import get_profile as _get_user_profile
    _p = _get_user_profile()
    height_cm = _p.get('height_cm') if _p else None
    height_m = (height_cm / 100) if height_cm else None

    conn = _get_db()
    c = conn.cursor()
    results = []
    wrote = skipped = failed = 0
    for it in items:
        d = it.get('date')
        try:
            kg = float(it.get('kg'))
        except (TypeError, ValueError):
            failed += 1
            results.append({'date': d, 'kg': it.get('kg'), 'status': '失败', 'reason': '体重非数字'})
            continue
        if kg <= 0:
            failed += 1
            results.append({'date': d, 'kg': kg, 'status': '失败', 'reason': '体重必须为正数'})
            continue
        if not d or not date.fromisoformat(d):
            failed += 1
            results.append({'date': d, 'kg': kg, 'status': '失败', 'reason': '日期格式错误'})
            continue
        c.execute('SELECT weight_kg FROM weight_log WHERE date = ? ORDER BY time DESC LIMIT 1', (d,))
        exist = c.fetchone()
        if exist:
            skipped += 1
            results.append({'date': d, 'kg': kg, 'status': '跳过', 'reason': f'已有记录 {exist[0]}kg'})
            continue
        bmi = round(kg / (height_m ** 2), 1) if height_m else None
        c.execute('INSERT INTO weight_log (date, time, weight_kg, height_cm, bmi, note) VALUES (?, ?, ?, ?, ?, ?)',
                  (d, '08:00:00', kg, height_cm, bmi, ''))
        wrote += 1
        results.append({'date': d, 'kg': kg, 'status': '写入', 'reason': ''})
    conn.commit()
    conn.close()
    return {'wrote': wrote, 'skipped': skipped, 'failed': failed, 'items': results}


def fetch_weight_logs(start, end, note_only=False):
    """区间体重记录(渲染层共用):date/kg/bmi/delta/note/anomaly 带排序"""
    conn = _get_db()
    c = conn.cursor()
    if note_only:
        c.execute('''
            SELECT date, weight_kg, bmi, note FROM weight_log
            WHERE date BETWEEN ? AND ? AND note IS NOT NULL AND note != ''
            ORDER BY date, time
        ''', (start, end))
    else:
        c.execute('''
            SELECT date, weight_kg, bmi, note FROM weight_log
            WHERE date BETWEEN ? AND ? ORDER BY date, time
        ''', (start, end))
    rows = c.fetchall()
    c.execute('SELECT height_cm FROM user_profile ORDER BY id DESC LIMIT 1')
    h = c.fetchone()
    conn.close()
    height_m = (h[0] / 100) if h and h[0] else None
    items = []
    prev = None
    for d, kg, bmi, note in rows:
        if bmi is None and height_m:
            bmi = round(kg / (height_m ** 2), 1)
        delta = round(kg - prev, 1) if prev is not None else 0
        items.append({'date': d, 'kg': kg, 'bmi': bmi, 'delta': delta, 'note': note or '', 'tag': note_tag(note)})
        prev = kg
    return items