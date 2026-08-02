#!/usr/bin/env python3
"""
运动记录 CLI v1.0

使用方法：
    # 添加运动记录
    python3 exercise_tracker.py add --date 2026-05-12 --type 骑行 --calories 90 --minutes 10
    python3 exercise_tracker.py add --date 2026-05-12 --type 俯卧撑 --calories 50 --minutes 15 --reps 30
    
    # 更新记录
    python3 exercise_tracker.py update --id 1 --calories 100 --note "骑得更快了"
    
    # 查询记录（多种方式）
    python3 exercise_tracker.py list                        # 今日记录
    python3 exercise_tracker.py list --days 7              # 最近7天
    python3 exercise_tracker.py list --date 2026-05-12     # 指定日期
    python3 exercise_tracker.py list --from 2026-05-01 --to 2026-05-10  # 日期范围
    python3 exercise_tracker.py list --type 骑行          # 按运动类型
    python3 exercise_tracker.py list --type 俯卧撑 --days 30  # 类型+天数
    
    # 汇总统计
    python3 exercise_tracker.py summary                    # 今日汇总
    python3 exercise_tracker.py summary --days 7           # 最近7天汇总
    python3 exercise_tracker.py summary --from 2026-05-01 --to 2026-05-10  # 范围汇总
    
    # 运动类型统计
    python3 exercise_tracker.py stats --type breakdown     # 类型分布
    python3 exercise_tracker.py stats --type total         # 各类型总消耗
    
    # 热量趋势
    python3 exercise_tracker.py trend --days 7            # 7天热量趋势
    
    # 帮助
    python3 exercise_tracker.py --help
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn, init_db as _init_db

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)


# ============ 自然时间窗口解析(2026-08-02 · ticket #5 运动) ============
# 供 render_exercise_summary / render_exercise_recap 等共享
WINDOWS = ('today', 'yesterday', 'week', 'last-week', 'month', 'last-month')


def resolve_window(window: str | None = None, days: int | None = None,
                   from_date: str | None = None, to_date: str | None = None,
                   now: datetime | None = None):
    """把自然窗口/最近 N 天/自定义区间统一解析为 (start, end)

    优先级:window > days > (from, to);都不给 → 今天。
    window: today / yesterday / week(周一到今天)/ last-week(上周一到周日)/
            month(1 号到今天)/ last-month(上月 1 号到月末)
    """
    now = now or datetime.now()
    today = now.date()
    if window == 'today':
        return today.isoformat(), today.isoformat()
    if window == 'yesterday':
        d = today - timedelta(days=1)
        return d.isoformat(), d.isoformat()
    if window == 'week':
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat()
    if window == 'last-week':
        this_week_start = today - timedelta(days=today.weekday())
        end = this_week_start - timedelta(days=1)
        start = end - timedelta(days=6)
        return start.isoformat(), end.isoformat()
    if window == 'month':
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat()
    if window == 'last-month':
        first_this = today.replace(day=1)
        end = first_this - timedelta(days=1)
        start = end.replace(day=1)
        return start.isoformat(), end.isoformat()
    if days:
        start = today - timedelta(days=days - 1)
        return start.isoformat(), today.isoformat()
    if from_date:
        return from_date, to_date or today.isoformat()
    return today.isoformat(), today.isoformat()


def parse_time(time_str=None):
    """解析时间字符串，默认当前时间"""
    if not time_str:
        return datetime.now().strftime("%H:%M:%S")
    try:
        dt = datetime.strptime(time_str, "%H:%M:%S")
        return dt.strftime("%H:%M:%S")
    except ValueError:
        try:
            dt = datetime.strptime(time_str, "%H:%M")
            return dt.strftime("%H:%M:%S")
        except ValueError:
            return datetime.now().strftime("%H:%M:%S")


def cmd_add(args):
    """添加运动记录"""
    _init_db(DB_PATH)  # 2026-07-13 改:本地 init_db 已删,统一调 db.init_db
    conn = get_db()
    cursor = conn.cursor()

    time_str = parse_time(args.time)

    try:
        cursor.execute("""
            INSERT INTO exercise_log (
                date, time, exercise_type, duration_minutes, calories_burned,
                note, reps,
                category, difficulty, distance_km, avg_heart_rate, set_index, load_kg,
                steps, max_heart_rate, is_backfill
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            args.date,
            time_str,
            args.type,
            args.minutes if args.minutes else None,
            args.calories,
            args.note or '',
            args.reps if args.reps else None,
            args.category if hasattr(args, 'category') and args.category else None,
            args.difficulty if hasattr(args, 'difficulty') and args.difficulty else None,
            args.distance if hasattr(args, 'distance') and args.distance else None,
            args.heart_rate if hasattr(args, 'heart_rate') and args.heart_rate else None,
            args.set_index if hasattr(args, 'set_index') and args.set_index else None,
            args.load if hasattr(args, 'load') and args.load else None,
            args.steps if hasattr(args, 'steps') and args.steps else None,
            args.max_heart_rate if hasattr(args, 'max_heart_rate') and args.max_heart_rate else None,
            1 if (hasattr(args, 'backfill') and args.backfill) else 0,
        ))
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()

        print(f"✓ 运动记录已添加 (ID: {record_id})")
        print(f"  日期: {args.date} {time_str}")
        print(f"  类型: {args.type}")
        if args.category:
            print(f"  分类: {args.category}")
        if args.difficulty:
            print(f"  强度: {args.difficulty}")
        print(f"  时长: {args.minutes if args.minutes else '未知'} 分钟")
        if args.distance:
            print(f"  距离: {args.distance} km")
        if args.heart_rate:
            print(f"  平均心率: {args.heart_rate} bpm")
        if hasattr(args, 'max_heart_rate') and args.max_heart_rate:
            print(f"  最高心率: {args.max_heart_rate} bpm")
        if hasattr(args, 'steps') and args.steps:
            print(f"  步数: {args.steps}")
        print(f"  消耗: {args.calories} 卡")
        if args.set_index:
            print(f"  组号: 第 {args.set_index} 组")
        if args.reps:
            print(f"  次数: {args.reps}")
        if args.load:
            print(f"  单侧重量: {args.load} kg")
        if args.note:
            print(f"  备注: {args.note}")
        if hasattr(args, 'backfill') and args.backfill:
            print(f"  补录标识: 是")
    except Exception as e:
        print(f"✗ 添加失败: {e}")
        sys.exit(1)


def cmd_update(args):
    """更新运动记录"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM exercise_log WHERE id = ?", (args.id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 记录 ID {args.id} 不存在")
        conn.close()
        sys.exit(1)

    updates = []
    values = []

    if args.calories is not None:
        updates.append("calories_burned = ?")
        values.append(args.calories)
    if args.minutes is not None:
        updates.append("duration_minutes = ?")
        values.append(args.minutes)
    if args.type is not None:
        updates.append("exercise_type = ?")
        values.append(args.type)
    if args.note is not None:
        updates.append("note = ?")
        values.append(args.note)
    if args.reps is not None:
        updates.append("reps = ?")
        values.append(args.reps)
    if args.date is not None:
        updates.append("date = ?")
        values.append(args.date)
    # 扩展字段（运动功能 · 2026-06-29）
    if args.category is not None:
        updates.append("category = ?")
        values.append(args.category)
    if args.difficulty is not None:
        updates.append("difficulty = ?")
        values.append(args.difficulty)
    if args.distance is not None:
        updates.append("distance_km = ?")
        values.append(args.distance)
    if args.heart_rate is not None:
        updates.append("avg_heart_rate = ?")
        values.append(args.heart_rate)
    if args.set_index is not None:
        updates.append("set_index = ?")
        values.append(args.set_index)
    if args.load is not None:
        updates.append("load_kg = ?")
        values.append(args.load)
    if hasattr(args, 'steps') and args.steps is not None:
        updates.append("steps = ?")
        values.append(args.steps)
    if hasattr(args, 'max_heart_rate') and args.max_heart_rate is not None:
        updates.append("max_heart_rate = ?")
        values.append(args.max_heart_rate)
    if hasattr(args, 'backfill') and args.backfill is not None:
        updates.append("is_backfill = ?")
        values.append(1 if args.backfill else 0)

    if not updates:
        print("✗ 没有提供要更新的字段")
        sys.exit(1)

    values.append(args.id)

    try:
        cursor.execute(f"""
            UPDATE exercise_log
            SET {', '.join(updates)}
            WHERE id = ?
        """, values)
        conn.commit()
        conn.close()

        print(f"✓ 记录 ID {args.id} 已更新")
    except Exception as e:
        print(f"✗ 更新失败: {e}")
        sys.exit(1)


def cmd_list(args):
    """查询运动记录"""
    conn = get_db()
    cursor = conn.cursor()

    conditions = []
    params = []

    if args.date:
        conditions.append("date = ?")
        params.append(args.date)
    elif args.days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days - 1)).strftime("%Y-%m-%d")
        conditions.append("date >= ? AND date <= ?")
        params.extend([start_date, end_date])
    elif args.from_date:
        conditions.append("date >= ?")
        params.append(args.from_date)
        if args.to_date:
            conditions.append("date <= ?")
            params.append(args.to_date)

    if args.type:
        conditions.append("exercise_type LIKE ?")
        params.append(f"%{args.type}%")
    if args.category:
        conditions.append("category = ?")
        params.append(args.category)
    if getattr(args, 'has_note', False):
        conditions.append("note IS NOT NULL AND note != ''")

    # 软删除过滤(ticket #5 运动 · 2026-08-02)
    conditions.append("COALESCE(is_deleted, 0) = 0")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT * FROM exercise_log
        {where_clause}
        ORDER BY date DESC, time DESC
    """

    if args.limit:
        query += f" LIMIT {args.limit}"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("没有找到运动记录")
        return

    print(f"=== 运动记录 ({len(rows)} 条) ===")
    for row in rows:
        parts = [f"[{row['id']}]", f"{row['date']} {row['time'] or ''}",
                 f"{row['exercise_type']}"]
        if row['category']:
            parts.append(f"[{row['category']}]")
        if row['difficulty']:
            parts.append(f"强度={row['difficulty']}")
        if row['set_index']:
            parts.append(f"第{row['set_index']}组")
        if row['duration_minutes']:
            parts.append(f"{row['duration_minutes']}分钟")
        if row['distance_km']:
            parts.append(f"{row['distance_km']}km")
        if row['avg_heart_rate']:
            parts.append(f"HR={row['avg_heart_rate']}")
        parts.append(f"{row['calories_burned']}卡")
        if row['reps']:
            parts.append(f"{row['reps']}次")
        if row['load_kg']:
            parts.append(f"单侧{row['load_kg']}kg")
        if row['note']:
            parts.append(f"| {row['note']}")
        print(' | '.join(parts))


def cmd_summary(args):
    """运动汇总统计"""
    conn = get_db()
    cursor = conn.cursor()
    
    if args.from_date and args.to_date:
        start_date = args.from_date
        end_date = args.to_date
    elif args.days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=args.days - 1)).strftime("%Y-%m-%d")
    else:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            SUM(calories_burned) as total_cal,
            SUM(duration_minutes) as total_min,
            AVG(calories_burned) as avg_cal
        FROM exercise_log 
        WHERE date >= ? AND date <= ? AND COALESCE(is_deleted, 0) = 0
    """, (start_date, end_date))
    
    row = cursor.fetchone()
    
    print(f"=== 运动汇总 ({start_date} ~ {end_date}) ===")
    print(f"运动次数: {row['count']} 次")
    print(f"总消耗: {row['total_cal'] or 0} 卡")
    print(f"总时长: {row['total_min'] or 0} 分钟")
    print(f"日均消耗: {int(row['avg_cal'] or 0)} 卡")
    
    cursor.execute("""
        SELECT 
            exercise_type,
            COUNT(*) as count,
            SUM(calories_burned) as total_cal,
            SUM(duration_minutes) as total_min
        FROM exercise_log 
        WHERE date >= ? AND date <= ? AND COALESCE(is_deleted, 0) = 0
        GROUP BY exercise_type
        ORDER BY total_cal DESC
    """, (start_date, end_date))
    
    type_rows = cursor.fetchall()
    
    if type_rows:
        print()
        print("--- 各类型统计 ---")
        for tr in type_rows:
            print(f"{tr['exercise_type']}: {tr['count']}次 | {tr['total_cal']}卡 | {tr['total_min'] or 0}分钟")
    
    conn.close()


def cmd_stats(args):
    """运动类型统计分析"""
    conn = get_db()
    cursor = conn.cursor()
    
    if args.stats_type == 'breakdown':
        cursor.execute("""
            SELECT 
                exercise_type,
                COUNT(*) as count,
                SUM(calories_burned) as total_cal,
                SUM(duration_minutes) as total_min
            FROM exercise_log 
            GROUP BY exercise_type
            ORDER BY total_cal DESC
        """)
        rows = cursor.fetchall()
        
        print("=== 运动类型分布 ===")
        total_cal = sum(r['total_cal'] for r in rows) if rows else 0
        for row in rows:
            pct = row['total_cal'] / total_cal * 100 if total_cal > 0 else 0
            print(f"{row['exercise_type']}: {row['count']}次 | {row['total_cal']}卡 | {row['total_min'] or 0}分钟 | {pct:.1f}%")
    
    elif args.stats_type == 'total':
        cursor.execute("""
            SELECT exercise_type, SUM(calories_burned) as total
            FROM exercise_log 
            GROUP BY exercise_type
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        
        print("=== 各类型总消耗排名 ===")
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row['exercise_type']}: {row['total']}卡")
    
    conn.close()


def cmd_trend(args):
    """热量趋势"""
    conn = get_db()
    cursor = conn.cursor()
    
    days = args.days or 7
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT date, SUM(calories_burned) as daily_cal
        FROM exercise_log 
        WHERE date >= ? AND date <= ? AND COALESCE(is_deleted, 0) = 0
        GROUP BY date
        ORDER BY date ASC
    """, (start_date, end_date))
    
    rows = cursor.fetchall()
    
    print(f"=== 热量趋势 (最近{days}天) ===")
    
    cal_map = {row['date']: row['daily_cal'] for row in rows}
    
    for i in range(days):
        date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
        cal = cal_map.get(date, 0)
        bar = "█" * (cal // 50) if cal > 0 else "-"
        print(f"{date}: {cal:>4}卡 {bar}")
    
    conn.close()


# ============ 写操作函数(2026-08-02 · ticket #5 运动 · render_exercise_receipt 复用) ============

_FIELD_ALIASES = {
    'type': 'exercise_type', 'calories': 'calories_burned', 'minutes': 'duration_minutes',
    '时长': 'duration_minutes', '热量': 'calories_burned', '类型': 'exercise_type',
    '日期': 'date', '备注': 'note', '分类': 'category', '强度': 'difficulty',
    '距离': 'distance_km', '平均心率': 'avg_heart_rate', '最高心率': 'max_heart_rate',
    '组号': 'set_index', '次数': 'reps', '重量': 'load_kg', '步数': 'steps', '时段': 'period',
}
_FIELD_REVERSE = {v: k for k, v in _FIELD_ALIASES.items()}


def _col_for(field: str) -> str:
    """用户字段名 → DB 列名(支持中文别名)"""
    return _FIELD_ALIASES.get(field, field)


def _row_dict(row) -> dict:
    """sqlite3.Row → dict(排除内部列,供回执 diff)"""
    d = dict(row)
    return d


def add_record(date, exercise_type, calories_burned, minutes=None, time_str=None, note='',
               reps=None, category=None, difficulty=None, distance=None, heart_rate=None,
               max_heart_rate=None, steps=None, period=None, set_index=None, load_kg=None,
               is_backfill=False, conn=None):
    """写一条运动记录,返回 (record_id, record dict)

    供 CLI cmd_add 与 render_exercise_receipt 共用(2026-08-02 · ticket #5)
    """
    own_conn = conn is None
    conn = conn or get_db()
    if own_conn:
        _init_db(DB_PATH)  # 共享 conn 场景由调用方负责初始化(避免 batch 循环锁冲突 · 2026-08-02)
    cursor = conn.cursor()
    time_str = parse_time(time_str)
    cursor.execute("""
        INSERT INTO exercise_log (
            date, time, exercise_type, duration_minutes, calories_burned,
            note, reps, category, difficulty, distance_km, avg_heart_rate,
            set_index, load_kg, steps, max_heart_rate, is_backfill
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (date, time_str, exercise_type, minutes, calories_burned, note, reps,
          category, difficulty, distance, heart_rate, set_index, load_kg,
          steps, max_heart_rate, 1 if is_backfill else 0))
    record_id = cursor.lastrowid
    if own_conn:
        conn.commit()
        conn.close()
    return record_id, {'id': record_id, 'date': date, 'time': time_str,
                       'exercise_type': exercise_type, 'duration_minutes': minutes,
                       'calories_burned': calories_burned, 'note': note, 'reps': reps,
                       'category': category, 'difficulty': difficulty, 'distance_km': distance,
                       'avg_heart_rate': heart_rate, 'max_heart_rate': max_heart_rate,
                       'steps': steps, 'period': period, 'set_index': set_index,
                       'load_kg': load_kg, 'is_backfill': 1 if is_backfill else 0}


def update_record(record_id, fields: dict, conn=None):
    """更新一条记录(fields = {DB列名: 新值}),返回 (old, new) dict

    2026-08-02 · ticket #5:支持字段名中文别名 + 改前/改后 diff
    """
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM exercise_log WHERE id = ?', (record_id,)).fetchone()
    if not row:
        raise ValueError(f'记录 ID {record_id} 不存在')
    old = _row_dict(row)
    updates, values = [], []
    for col, val in fields.items():
        col = _col_for(col)
        if col not in old:
            raise ValueError(f'未知字段: {col}')
        updates.append(f'{col} = ?')
        values.append(val)
    if updates:
        values.append(record_id)
        cursor.execute(f"UPDATE exercise_log SET {', '.join(updates)}, updated_at = ? WHERE id = ?",
                       values[:-1] + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record_id])
    if own_conn:
        conn.commit()
    new_row = cursor.execute('SELECT * FROM exercise_log WHERE id = ?', (record_id,)).fetchone()
    new = _row_dict(new_row)
    if own_conn:
        conn.close()
    return old, new


def delete_record(record_id, conn=None):
    """软删除一条记录,返回删除前快照 dict(2026-08-02 · ticket #5)"""
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    row = cursor.execute('SELECT * FROM exercise_log WHERE id = ?', (record_id,)).fetchone()
    if not row:
        raise ValueError(f'记录 ID {record_id} 不存在')
    snapshot = _row_dict(row)
    cursor.execute('UPDATE exercise_log SET is_deleted = 1, updated_at = ? WHERE id = ?',
                   (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record_id))
    if own_conn:
        conn.commit()
        conn.close()
    return snapshot


def delete_day(date, conn=None):
    """软删除某天全部记录,返回删除条数"""
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE exercise_log SET is_deleted = 1, updated_at = ? WHERE date = ? AND COALESCE(is_deleted, 0) = 0",
                   (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), date))
    count = cursor.rowcount
    if own_conn:
        conn.commit()
        conn.close()
    return count


def delete_range(from_date, to_date, conn=None):
    """软删除时间范围内全部记录,返回删除条数"""
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE exercise_log SET is_deleted = 1, updated_at = ? WHERE date BETWEEN ? AND ? AND COALESCE(is_deleted, 0) = 0",
                   (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), from_date, to_date))
    count = cursor.rowcount
    if own_conn:
        conn.commit()
        conn.close()
    return count


def update_day(date, fields: dict, conn=None):
    """按日期更新某天全部记录(fields = {DB列名: 新值}),返回 (matched, [(old, new), ...])"""
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT id FROM exercise_log WHERE date = ? AND COALESCE(is_deleted, 0) = 0", (date,)).fetchall()
    results = []
    for r in rows:
        old, new = update_record(r['id'], fields, conn=conn)
        results.append((old, new))
    if own_conn:
        conn.commit()
        conn.close()
    return len(rows), results


def copy_yesterday(target_date=None, conn=None):
    """把昨天记录复制到目标日期(默认今天),返回 (copied, skipped, list)

    跳过判定:目标日期已有 同 exercise_type + 同 calories_burned + 同 duration_minutes 的记录
    (2026-08-02 · ticket #5 · SKILL.md 交互规则)
    """
    own_conn = conn is None
    conn = conn or get_db()
    cursor = conn.cursor()
    today = datetime.now().date()
    target = target_date or today.isoformat()
    source = (today - timedelta(days=1)).isoformat()

    rows = cursor.execute(
        "SELECT * FROM exercise_log WHERE date = ? AND COALESCE(is_deleted, 0) = 0",
        (source,)).fetchall()
    copied, skipped, details = 0, 0, []
    for r in rows:
        dup = cursor.execute(
            "SELECT id FROM exercise_log WHERE date = ? AND exercise_type = ? "
            "AND calories_burned = ? AND COALESCE(duration_minutes, -1) = COALESCE(?, -1) "
            "AND COALESCE(is_deleted, 0) = 0 LIMIT 1",
            (target, r['exercise_type'], r['calories_burned'], r['duration_minutes'])).fetchone()
        if dup:
            skipped += 1
            details.append({'type': r['exercise_type'], 'status': 'skipped'})
            continue
        add_record(target, r['exercise_type'], r['calories_burned'],
                   minutes=r['duration_minutes'], time_str=r['time'], note=r['note'] or '',
                   reps=r['reps'], category=r['category'], difficulty=r['difficulty'],
                   distance=r['distance_km'], heart_rate=r['avg_heart_rate'],
                   max_heart_rate=r['max_heart_rate'], steps=r['steps'],
                   set_index=r['set_index'], load_kg=r['load_kg'], conn=conn)
        copied += 1
        details.append({'type': r['exercise_type'], 'status': 'copied'})
    if own_conn:
        conn.commit()
        conn.close()
    return copied, skipped, details, source, target


def batch_add(items, conn=None):
    """批量写入(items = [dict(date/type/calories/minutes/note...)]),返回统计

    2026-08-02 · ticket #5 · 逐条校验,失败原因收集
    """
    own_conn = conn is None
    conn = conn or get_db()
    written = skipped = failed = 0
    failures = []
    for it in items:
        try:
            date = it['date']
            etype = it['type']
            calories = int(it.get('calories', 0))
            minutes = int(it['minutes']) if it.get('minutes') else None
            if not etype or calories <= 0:
                raise ValueError('类型/热量无效')
            add_record(date, etype, calories, minutes=minutes,
                       note=it.get('note', ''), category=it.get('category'),
                       is_backfill=True, conn=conn)
            written += 1
        except Exception as e:
            failed += 1
            failures.append({'item': it, 'reason': str(e)})
    if own_conn:
        conn.commit()
        conn.close()
    return {'written': written, 'skipped': skipped, 'failed': failed, 'failures': failures}


def cmd_batch_add(args):
    """批量补记运动 CLI"""
    _init_db(DB_PATH)
    items = []
    for line in args.items.split(';'):
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) < 3:
            print(f"✗ 格式错误(需 日期 类型 热量 [时长]): {line.strip()}")
            continue
        date, etype, calories = parts[0], parts[1], parts[2]
        minutes = parts[3] if len(parts) > 3 else None
        items.append({'date': date, 'type': etype, 'calories': int(calories),
                      'minutes': int(minutes) if minutes else None})
    if not items:
        print("✗ 没有可写入的条目")
        sys.exit(1)
    result = batch_add(items)
    print(f"✓ 批量补记完成: 写入 {result['written']} / 失败 {result['failed']}")
    for f in result['failures']:
        print(f"  ✗ {f['item']}: {f['reason']}")


def cmd_copy(args):
    """复制昨日运动 CLI"""
    _init_db(DB_PATH)
    copied, skipped, details, source, target = copy_yesterday(args.target)
    print(f"✓ 复制完成: {source} → {target}")
    print(f"  复制 {copied} 条 / 跳过 {skipped} 条")
    for d in details:
        print(f"  {d['status']}: {d['type']}")


def cmd_delete(args):
    """删运动记录 CLI(软删除)"""
    _init_db(DB_PATH)
    snapshot = delete_record(args.id)
    print(f"✓ 记录 #{args.id} 已删除(软删除)")
    print(f"  快照: {snapshot['date']} {snapshot['exercise_type']} {snapshot['calories_burned']}卡")


def cmd_delete_day(args):
    _init_db(DB_PATH)
    count = delete_day(args.date)
    print(f"✓ 已删除 {args.date} 的运动记录 {count} 条")


def cmd_delete_range(args):
    _init_db(DB_PATH)
    count = delete_range(args.from_date, args.to_date)
    print(f"✓ 已删除 {args.from_date} ~ {args.to_date} 的运动记录 {count} 条")


def cmd_update_day(args):
    """改某日运动 CLI"""
    _init_db(DB_PATH)
    fields = dict(zip(args.field, args.value)) if args.field else {}
    if not fields:
        print("✗ 需要 --field/--value 成对参数")
        sys.exit(1)
    matched, results = update_day(args.date, fields)
    print(f"✓ 命中 {matched} 条记录并更新")
    for old, new in results:
        changed = [k for k in new if k not in ('created_at', 'updated_at') and old.get(k) != new.get(k)]
        print(f"  #{old['id']} {old['exercise_type']}: " + ', '.join(f"{k}: {old.get(k)}→{new.get(k)}" for k in changed[:5]))


def main():
    parser = argparse.ArgumentParser(description="运动记录 CLI", prog="exercise_tracker.py")
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # add 子命令
    add_parser = subparsers.add_parser('add', help='添加运动记录')
    add_parser.add_argument('--date', required=True, help='日期 (YYYY-MM-DD)')
    add_parser.add_argument('--type', required=True, help='运动类型')
    add_parser.add_argument('--calories', type=int, required=True, help='消耗卡路里')
    add_parser.add_argument('--minutes', type=int, help='运动时长(分钟)')
    add_parser.add_argument('--time', help='时间 (HH:MM:SS)')
    add_parser.add_argument('--note', help='备注')
    add_parser.add_argument('--reps', type=int, help='动作次数(如俯卧撑个数)')
    # 扩展字段（运动功能 · 2026-06-29）
    add_parser.add_argument('--category', choices=['有氧', '力量', '柔韧', '日常'],
                            help='运动分类（AI 推断时必填）')
    add_parser.add_argument('--difficulty', choices=['easy', 'normal', 'hard'],
                            help='强度等级')
    add_parser.add_argument('--distance', type=float, help='距离 km（跑步/骑行）')
    add_parser.add_argument('--heart-rate', type=int, dest='heart_rate',
                            help='平均心率 bpm')
    add_parser.add_argument('--set', type=int, dest='set_index',
                            help='力量场景：第几组')
    add_parser.add_argument('--load', type=float, help='力量场景：单侧重量 kg')

    # update 子命令
    update_parser = subparsers.add_parser('update', help='更新运动记录')
    update_parser.add_argument('--id', type=int, required=True, help='记录ID')
    update_parser.add_argument('--type', help='运动类型')
    update_parser.add_argument('--calories', type=int, help='消耗卡路里')
    update_parser.add_argument('--minutes', type=int, help='运动时长(分钟)')
    update_parser.add_argument('--date', help='日期 (YYYY-MM-DD)')
    update_parser.add_argument('--note', help='备注')
    update_parser.add_argument('--reps', type=int, help='动作次数')
    # 扩展字段
    update_parser.add_argument('--category', choices=['有氧', '力量', '柔韧', '日常'])
    update_parser.add_argument('--difficulty', choices=['easy', 'normal', 'hard'])
    update_parser.add_argument('--distance', type=float, help='距离 km')
    update_parser.add_argument('--heart-rate', type=int, dest='heart_rate', help='平均心率 bpm')
    update_parser.add_argument('--set', type=int, dest='set_index', help='第几组')
    update_parser.add_argument('--load', type=float, help='单侧重量 kg')

    # list 子命令
    list_parser = subparsers.add_parser('list', help='查询运动记录')
    list_parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    list_parser.add_argument('--days', type=int, help='最近N天')
    list_parser.add_argument('--from', dest='from_date', help='开始日期 (YYYY-MM-DD)')
    list_parser.add_argument('--to', dest='to_date', help='结束日期 (YYYY-MM-DD)')
    list_parser.add_argument('--type', help='运动类型(模糊匹配)')
    list_parser.add_argument('--category', choices=['有氧', '力量', '柔韧', '日常'],
                             help='按分类筛选')
    list_parser.add_argument('--limit', type=int, help='限制返回条数')
    
    # summary 子命令
    summary_parser = subparsers.add_parser('summary', help='运动汇总统计')
    summary_parser.add_argument('--days', type=int, help='最近N天')
    summary_parser.add_argument('--from', dest='from_date', help='开始日期 (YYYY-MM-DD)')
    summary_parser.add_argument('--to', dest='to_date', help='结束日期 (YYYY-MM-DD)')
    
    # stats 子命令
    stats_parser = subparsers.add_parser('stats', help='运动类型统计')
    stats_parser.add_argument('--type', dest='stats_type', default='breakdown',
                              choices=['breakdown', 'total'], help='统计类型')
    
    # trend 子命令
    trend_parser = subparsers.add_parser('trend', help='热量趋势')
    trend_parser.add_argument('--days', type=int, help='最近N天')

    # 2026-08-02 · ticket #5 运动:新子命令
    add_parser.add_argument('--steps', type=int, help='步数(日常活动)')
    add_parser.add_argument('--max-heart-rate', type=int, dest='max_heart_rate', help='最高心率 bpm')
    add_parser.add_argument('--backfill', action='store_true', help='补录标识')
    update_parser.add_argument('--steps', type=int, help='步数')
    update_parser.add_argument('--max-heart-rate', type=int, dest='max_heart_rate', help='最高心率 bpm')
    update_parser.add_argument('--backfill', type=int, help='补录标识(1/0)')
    list_parser.add_argument('--has-note', action='store_true', help='只看带备注的记录')

    batch_parser = subparsers.add_parser('batch-add', help='批量补记运动')
    batch_parser.add_argument('--items', required=True, help='条目(分号分隔:日期 类型 热量 [时长])')
    copy_parser = subparsers.add_parser('copy', help='复制昨日运动到今天(或指定日期)')
    copy_parser.add_argument('--target', help='目标日期(默认今天)')
    del_parser = subparsers.add_parser('delete', help='删除一条运动记录(软删除)')
    del_parser.add_argument('--id', type=int, required=True, help='记录ID')
    del_day_parser = subparsers.add_parser('delete-day', help='删除某天全部运动记录')
    del_day_parser.add_argument('--date', required=True, help='日期 (YYYY-MM-DD)')
    del_range_parser = subparsers.add_parser('delete-range', help='删除时间范围内运动记录')
    del_range_parser.add_argument('--from', dest='from_date', required=True, help='开始日期')
    del_range_parser.add_argument('--to', dest='to_date', required=True, help='结束日期')
    update_day_parser = subparsers.add_parser('update-day', help='按日期批量更新运动记录')
    update_day_parser.add_argument('--date', required=True, help='日期 (YYYY-MM-DD)')
    update_day_parser.add_argument('--field', action='append', help='字段名(可多次)')
    update_day_parser.add_argument('--value', action='append', help='新值(与 --field 成对)')

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    if args.command == 'add':
        cmd_add(args)
    elif args.command == 'update':
        cmd_update(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'summary':
        cmd_summary(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'trend':
        cmd_trend(args)
    elif args.command == 'batch-add':
        cmd_batch_add(args)
    elif args.command == 'copy':
        cmd_copy(args)
    elif args.command == 'delete':
        cmd_delete(args)
    elif args.command == 'delete-day':
        cmd_delete_day(args)
    elif args.command == 'delete-range':
        cmd_delete_range(args)
    elif args.command == 'update-day':
        cmd_update_day(args)


if __name__ == '__main__':
    main()