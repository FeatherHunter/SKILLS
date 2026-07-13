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
                category, difficulty, distance_km, avg_heart_rate, set_index, load_kg
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            print(f"  心率: {args.heart_rate} bpm")
        print(f"  消耗: {args.calories} 卡")
        if args.set_index:
            print(f"  组号: 第 {args.set_index} 组")
        if args.reps:
            print(f"  次数: {args.reps}")
        if args.load:
            print(f"  单侧重量: {args.load} kg")
        if args.note:
            print(f"  备注: {args.note}")
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
        WHERE date >= ? AND date <= ?
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
        WHERE date >= ? AND date <= ?
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
        WHERE date >= ? AND date <= ?
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


if __name__ == '__main__':
    main()