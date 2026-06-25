#!/usr/bin/env python3
"""
Daily Recorder - 状态/统计/维护脚本
支持数据库初始化、状态查看、消息统计、索引重建
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from db import Database


def show_status(db: Database):
    """显示数据库基本状态"""
    registry = db.get_registry_info()
    print(f"数据库目录: {db._db_dir}")
    print(f"meta 数据库: {db._meta_path}")
    print(f"分库文件数: {len(registry)}")
    for info in registry:
        active = "✅ 活跃" if info["is_active"] else "  "
        print(f"  {active} seq={info['seq']:03d} | {info['filename']} | {info['size_mb']}MB")
    print()
    # 查 meta.db 中 checkpoint 数
    conn = sqlite3.connect(str(db._meta_path))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM scan_checkpoint")
    cp_count = cur.fetchone()[0]
    cur.execute("SELECT MIN(updated_at), MAX(updated_at) FROM scan_checkpoint")
    row = cur.fetchone()
    if row[0] is not None:
        beijing = timezone(timedelta(hours=8))
        min_dt = datetime.fromtimestamp(row[0], tz=beijing).strftime("%Y-%m-%d %H:%M:%S")
        max_dt = datetime.fromtimestamp(row[1], tz=beijing).strftime("%Y-%m-%d %H:%M:%S")
        print(f"scan_checkpoint: {cp_count} 条 ({min_dt} ~ {max_dt})")
    conn.close()


def show_stats(db: Database):
    """显示消息统计（遍历所有分库）"""
    beijing = timezone(timedelta(hours=8))
    today = datetime.now(beijing).strftime("%Y%m%d")

    # 总数（遍历所有分库）
    rows = db.query_recent(limit=100000, channel=None)
    total = len(rows)
    today_count = sum(1 for r in rows if r[6] == today)

    att_rows = db.query_attachments(limit=100000)
    att_total = len(att_rows)
    att_today = sum(1 for r in att_rows if r[6] == today)

    print(f"=== 消息统计 ===")
    print(f"消息总数: {total}")
    print(f"今日消息: {today_count}")
    print(f"附件总数: {att_total}")
    print(f"今日附件: {att_today}")

    # 按渠道统计
    print(f"\n=== 按渠道统计 ===")
    channel_map = {}
    for r in rows:
        ch = r[2] or 'unknown'
        channel_map[ch] = channel_map.get(ch, 0) + 1
    for ch, cnt in sorted(channel_map.items(), key=lambda x: -x[1]):
        print(f"  {ch}: {cnt} 条")

    # 最近 7 天每日统计
    print(f"\n=== 最近 7 天 ===")
    date_map = {}
    cutoff = (datetime.now(beijing) - timedelta(days=7)).strftime("%Y%m%d")
    for r in rows:
        d = r[6]
        if d >= cutoff:
            date_map[d] = date_map.get(d, 0) + 1
    for d, cnt in sorted(date_map.items(), reverse=True):
        print(f"  {d}: {cnt} 条")

    # 分库文件信息
    print(f"\n=== 分库文件 ===")
    db.refresh_registry_sizes()
    for info in db.get_registry_info():
        active = "✅ 活跃" if info["is_active"] else "  "
        print(f"  {active} {info['filename']} | {info['size_mb']}MB")


def reindex(db: Database):
    """重建所有分库文件的索引"""
    for data_path in db._all_data_files():
        conn = sqlite3.connect(str(data_path))
        conn.execute("REINDEX")
        conn.commit()
        conn.close()
        print(f"  索引重建: {data_path.name}")
    print("索引重建完成")


def main():
    parser = argparse.ArgumentParser(description="录音机状态/统计/维护")
    parser.add_argument("--init", action="store_true", help="初始化数据库（建表建索引）")
    parser.add_argument("--stats", action="store_true", help="显示消息统计")
    parser.add_argument("--reindex", action="store_true", help="重建数据库索引")
    args = parser.parse_args()

    if args.init:
        db = Database()
        print(f"数据库初始化完成: {db.db_path}")
        return

    if args.reindex:
        db = Database()
        reindex(db)
        return

    if args.stats:
        db = Database()
        show_stats(db)
        return

    # 默认：显示状态
    db = Database()
    show_status(db)


if __name__ == "__main__":
    main()
