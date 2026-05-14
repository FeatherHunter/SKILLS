#!/usr/bin/env python3
"""
Daily Recorder - 查询脚本
支持灵活的时间范围查询
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from db import Database

DB_PATH = Path("/mnt/d/2Study/StudyNotes/.db/daily_recorder.db")


def ts_to_str(ts: int) -> str:
    """微秒时间戳 -> 可读字符串"""
    dt = datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc)
    beijing = dt.astimezone(timezone(timedelta(hours=8)))
    return beijing.strftime("%Y-%m-%d %H:%M:%S")


def parse_ts(s: str) -> int:
    """解析时间字符串为微秒时间戳"""
    beijing = timezone(timedelta(hours=8))
    if len(s) == 8:
        dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]), 0, 0, 0, tzinfo=beijing)
    elif len(s) == 14:
        dt = datetime(int(s[:4]), int(s[4:6]), int(s[6:8]),
                      int(s[8:10]), int(s[10:12]), int(s[12:14]), tzinfo=beijing)
    else:
        raise ValueError(f"不支持的时间格式: {s}")
    return int(dt.timestamp() * 1_000_000)


def main():
    parser = argparse.ArgumentParser(description="查询用户消息和附件")
    parser.add_argument("--start", type=str, help="开始时间 YYYYMMDDHHMMSS 或 YYYYMMDD")
    parser.add_argument("--end", type=str, help="结束时间 YYYYMMDDHHMMSS 或 YYYYMMDD")
    parser.add_argument("--date", type=str, help="单日 YYYYMMDD（优先于 start/end）")
def main():
    parser = argparse.ArgumentParser(description="查询用户消息和附件")
    parser.add_argument("--start", type=str, help="开始时间 YYYYMMDDHHMMSS 或 YYYYMMDD")
    parser.add_argument("--end", type=str, help="结束时间 YYYYMMDDHHMMSS 或 YYYYMMDD")
    parser.add_argument("--date", type=str, help="单日 YYYYMMDD（优先于 start/end）")
    parser.add_argument("--recent", type=int, help="最近 N 条消息（忽略日期过滤，按最新排序）")
    parser.add_argument("--limit", type=int, default=1000, help="最大返回条数")
    parser.add_argument("--attachments", action="store_true", help="同时查询附件")
    args = parser.parse_args()

    db = Database(DB_PATH)

    # 解析时间参数
    start_ts = None
    end_ts = None
    recent_mode = args.recent is not None

    if not recent_mode:
        if args.date:
            year = int(args.date[:4])
            month = int(args.date[4:6])
            day = int(args.date[6:8])
            beijing = timezone(timedelta(hours=8))
            start_dt = datetime(year, month, day, 0, 0, 0, tzinfo=beijing)
            end_dt = datetime(year, month, day, 23, 59, 59, tzinfo=beijing)
            start_ts = int(start_dt.timestamp() * 1_000_000)
            end_ts = int(end_dt.timestamp() * 1_000_000)
        else:
            if args.start:
                start_ts = parse_ts(args.start)
            if args.end:
                end_ts = parse_ts(args.end)

    # 查询消息（recent 模式按最新排序）
    rows = db.query_recent(args.recent) if recent_mode else db.query(start_ts=start_ts, end_ts=end_ts, limit=args.limit)

    if not rows:
        print("没有找到消息")
    else:
        print(f"消息 {len(rows)} 条\n")
        for msg_id, ts, channel, sender_id, content, has_attachment, date in rows:
            att_flag = " [有附件]" if has_attachment else ""
            print(f"[{ts_to_str(ts)}] [{channel}]{att_flag}")
            print(f"  {content[:100]}{'...' if len(content) > 100 else ''}")
            print()

    # 查询附件
    if args.attachments:
        att_rows = db.query_attachments(start_ts=start_ts, end_ts=end_ts, limit=args.limit)
        if att_rows:
            print(f"\n附件 {len(att_rows)} 条\n")
            for msg_id, ts, channel, sender_id, file_path, file_type, date in att_rows:
                print(f"[{ts_to_str(ts)}] [{channel}] [{file_type}]")
                print(f"  {file_path}")
                print()


if __name__ == "__main__":
    main()