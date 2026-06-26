#!/usr/bin/env python3
"""运动记录 — 运动添加/查询/汇总

数据存储：exercise_log 表
- exercise_type, duration_minutes, calories_burned, reps
- 支持 reps（次数）字段，如俯卧撑 20 个

注意：exercise_tracker.py 是更完整的 CLI（add/update/list/summary/stats/trend），
本模块仅提供 calorie_tracker.py 内部需要的核心 add/list/summary。
"""

import sys
from collections import defaultdict
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


def add_exercise(exercise_type, calories_burned, duration_minutes=None, reps=None,
                 note='', target_date=None, target_time=None):
    """记录运动消耗

    Args:
        exercise_type: 运动类型，如 '跑步'、'钻石俯卧撑'
        calories_burned: 消耗卡路里
        duration_minutes: 运动时长（分钟），可选
        reps: 动作次数，如 20 个，可选
        note: 备注
        target_date: 目标日期（YYYY-MM-DD），默认今天
        target_time: 目标时间（HH:MM:SS），可选
    """
    if target_date is None:
        target_date = date.today().strftime('%Y-%m-%d')

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        INSERT INTO exercise_log (date, time, exercise_type, duration_minutes, calories_burned, note, reps)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (target_date, target_time or '', exercise_type, duration_minutes, calories_burned, note, reps))
    conn.commit()
    conn.close()

    reps_str = f" {reps}个" if reps else ""
    dur_str = f" {duration_minutes}分钟" if duration_minutes else ""
    print(f"✓ 已记录运动：{exercise_type}{reps_str}{dur_str} {calories_burned}卡")


def get_exercise_log(target_date=None, days=7):
    """获取运动记录

    Args:
        target_date: 查询日期（单日），可选
        days: 查询近 N 天（默认 7）

    Returns:
        list of Row
    """
    conn = _get_db()
    c = conn.cursor()

    if target_date:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date = ?
            ORDER BY time DESC
        ''', (target_date,))
    else:
        c.execute('''
            SELECT date, time, exercise_type, duration_minutes, calories_burned, note, reps
            FROM exercise_log
            WHERE date >= date('now', ?)
            ORDER BY date DESC, time DESC
        ''', (f'-{days} days',))

    rows = c.fetchall()
    conn.close()
    return rows


def print_exercise_summary(days=7):
    """显示近 N 天运动汇总（按日聚合 + 类型明细 + 日均）"""
    rows = get_exercise_log(days=days)
    if not rows:
        print(f"\n近{days}天无运动记录")
        return

    daily = defaultdict(list)
    for row in rows:
        daily[row[0]].append({
            'type': row[2],
            'cal': row[4],
            'dur': row[3],
            'reps': row[6]
        })

    total_cal = sum(sum(r['cal'] for r in items) for items in daily.values())
    total_days = len(daily)

    print(f"\n近{days}天运动汇总：{total_cal}卡 / {total_days}天")
    print("-" * 50)
    for d, items in sorted(daily.items()):
        detail = []
        for r in items:
            s = f"{r['type']}"
            if r['reps']:
                s += f" {r['reps']}个"
            if r['dur']:
                s += f" {r['dur']}分钟"
            s += f" {r['cal']}卡"
            detail.append(s)
        print(f"  {d}: {' | '.join(detail)}")
    print(f"\n  日均: {total_cal / total_days:.0f}卡/天" if total_days else "")