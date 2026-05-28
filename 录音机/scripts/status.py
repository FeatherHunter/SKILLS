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
from db import Database, DB_PATH


def show_status(db_path: Path):
    """显示数据库基本状态"""
    print(f"数据库路径: {db_path}")
    if not db_path.exists():
        print("状态: 数据库文件不存在，请先运行 --init")
        return

    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"文件大小: {size_mb:.2f} MB")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # 各表记录数
    for table in ["user_messages", "user_attachments", "scan_checkpoint"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"{table}: {count} 条记录")

    # checkpoint 概况
    cur.execute("SELECT MIN(updated_at), MAX(updated_at) FROM scan_checkpoint")
    row = cur.fetchone()
    if row[0] is not None:
        beijing = timezone(timedelta(hours=8))
        min_dt = datetime.fromtimestamp(row[0], tz=beijing).strftime("%Y-%m-%d %H:%M:%S")
        max_dt = datetime.fromtimestamp(row[1], tz=beijing).strftime("%Y-%m-%d %H:%M:%S")
        print(f"checkpoint 时间范围: {min_dt} ~ {max_dt}")

    # 日期覆盖
    cur.execute("SELECT MIN(date), MAX(date) FROM user_messages")
    row = cur.fetchone()
    if row[0]:
        print(f"消息日期范围: {row[0]} ~ {row[1]}")

    conn.close()


def show_stats(db_path: Path):
    """显示消息统计"""
    if not db_path.exists():
        print("数据库不存在，请先运行 --init")
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    beijing = timezone(timedelta(hours=8))
    today = datetime.now(beijing).strftime("%Y%m%d")

    # 总数
    cur.execute("SELECT COUNT(*) FROM user_messages")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_messages WHERE date = ?", (today,))
    today_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_attachments")
    att_total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM user_attachments WHERE date = ?", (today,))
    att_today = cur.fetchone()[0]

    print(f"=== 消息统计 ===")
    print(f"消息总数: {total}")
    print(f"今日消息: {today_count}")
    print(f"附件总数: {att_total}")
    print(f"今日附件: {att_today}")

    # 按渠道统计
    print(f"\n=== 按渠道统计 ===")
    cur.execute("SELECT channel, COUNT(*) FROM user_messages GROUP BY channel ORDER BY COUNT(*) DESC")
    for channel, count in cur.fetchall():
        print(f"  {channel or 'unknown'}: {count} 条")

    # 最近 7 天每日统计
    print(f"\n=== 最近 7 天 ===")
    cur.execute("""
        SELECT date, COUNT(*) FROM user_messages
        WHERE date >= ?
        GROUP BY date ORDER BY date DESC
        LIMIT 7
    """, ((datetime.now(beijing) - timedelta(days=7)).strftime("%Y%m%d"),))
    for date, count in cur.fetchall():
        print(f"  {date}: {count} 条")

    conn.close()


def reindex(db_path: Path):
    """重建数据库索引"""
    if not db_path.exists():
        print("数据库不存在，请先运行 --init")
        return

    conn = sqlite3.connect(str(db_path))
    conn.execute("REINDEX")
    conn.commit()
    conn.close()
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
        reindex(DB_PATH)
        return

    if args.stats:
        show_stats(DB_PATH)
        return

    # 默认：显示状态
    show_status(DB_PATH)


if __name__ == "__main__":
    main()
