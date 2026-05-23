#!/usr/bin/env python3
"""
睡眠记录管理 - CLI工具
支持添加、更新、查询睡眠记录
"""

import argparse
from datetime import datetime
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)


def init_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT NOT NULL UNIQUE,
            sleep_hours     REAL NOT NULL,
            bedtime         TEXT,
            wake_time       TEXT,
            note            TEXT,
            created_at      INTEGER NOT NULL,
            updated_at      INTEGER
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sleep_date ON sleep_records(date)")
    conn.commit()
    conn.close()


def add_sleep(date, sleep_hours, bedtime, wake_time, note):
    """添加睡眠记录"""
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    # 检查是否已存在
    cur.execute("SELECT id FROM sleep_records WHERE date = ?", (date,))
    if cur.fetchone():
        print(f"⚠ {date} 已存在记录，请用 update 命令更新")
        conn.close()
        return
    
    cur.execute("""
        INSERT INTO sleep_records (date, sleep_hours, bedtime, wake_time, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date, sleep_hours, bedtime, wake_time, note, now))
    conn.commit()
    conn.close()
    print(f"✓ 已添加睡眠记录: {date} {sleep_hours}小时")


def update_sleep(date, **kwargs):
    """更新睡眠记录"""
    conn = get_db()
    cur = conn.cursor()
    
    updates = []
    params = []
    for key, value in kwargs.items():
        if value is not None:
            updates.append(f"{key} = ?")
            params.append(value)
    
    if not updates:
        print("没有需要更新的字段")
        conn.close()
        return
    
    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(date)
    
    cur.execute(f"UPDATE sleep_records SET {', '.join(updates)} WHERE date = ?", params)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    
    if affected:
        print(f"✓ 已更新 {date}")
    else:
        print(f"⚠ {date} 没有记录")


def list_sleep(days=7):
    """查询最近N天睡眠记录"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, sleep_hours, bedtime, wake_time, note
        FROM sleep_records
        ORDER BY date DESC
        LIMIT ?
    """, (days,))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print(f"最近{days}天没有睡眠记录")
        return
    
    print(f"=== 最近{days}天睡眠记录 ===\n")
    for r in rows:
        print(f"📅 {r['date']}")
        print(f"   睡眠时长: {r['sleep_hours']}小时")
        if r['bedtime']:
            print(f"   就寝: {r['bedtime']} | 起床: {r['wake_time']}")
        if r['note']:
            print(f"   备注: {r['note']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="睡眠记录管理")
    subparsers = parser.add_subparsers(dest='cmd', help='子命令')

    # add
    p_add = subparsers.add_parser('add', help='添加睡眠记录')
    p_add.add_argument('date', help='日期 YYYY-MM-DD')
    p_add.add_argument('--hours', dest='sleep_hours', type=float, required=True, help='睡眠时长（小时）')
    p_add.add_argument('--bed', dest='bedtime', help='就寝时间 HH:MM')
    p_add.add_argument('--wake', dest='wake_time', help='起床时间 HH:MM')
    p_add.add_argument('--note', help='备注')

    # update
    p_update = subparsers.add_parser('update', help='更新睡眠记录')
    p_update.add_argument('date', help='日期 YYYY-MM-DD')
    p_update.add_argument('--hours', dest='sleep_hours', type=float, help='睡眠时长（小时）')
    p_update.add_argument('--bed', dest='bedtime', help='就寝时间 HH:MM')
    p_update.add_argument('--wake', dest='wake_time', help='起床时间 HH:MM')
    p_update.add_argument('--note', help='备注')

    # list
    p_list = subparsers.add_parser('list', help='查询睡眠记录')
    p_list.add_argument('--days', type=int, default=7, help='查询天数，默认7天')

    args = parser.parse_args()
    init_table()

    if args.cmd == 'add':
        add_sleep(args.date, args.sleep_hours, args.bedtime, args.wake_time, args.note)
    elif args.cmd == 'update':
        kwargs = {k: v for k, v in vars(args).items() if k not in ['cmd', 'date'] and v is not None}
        update_sleep(args.date, **kwargs)
    elif args.cmd == 'list':
        list_sleep(args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()