#!/usr/bin/env python3
"""
作息管家 - 数据库底层模块
提供数据库初始化、增删改查的基础接口

增量同步逻辑（核心）：
  1. 获取 schedule_records 中最后一条记录的 date + time_end
  2. 获取该时间点之前的最后一条消息（理解上下文）
  3. 获取该时间点之后的所有新消息
  4. 分析 → 写入 schedule_records
  5. 下次继续从最新的最后一条记录开始

路径三层查找：环境变量 SKILLS_DB_PATH > 技能目录 > 父目录.db
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime, date, timedelta

# ============ 路径配置（三层查找）===========
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "schedule_data.db"
DR_FILENAME = "daily_recorder.db"

def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 技能目录
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename

DB_DIR = SKILL_DIR  # 兼容旧代码，指向技能目录
DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
DR_DB_PATH = _find_db_path(SKILL_DIR, DR_FILENAME)

# ============ 数据库初始化 ============
def init_db():
    """初始化作息管家数据库（去掉checkpoint表）"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # 作息记录主表
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            duration_minutes INTEGER,
            activity TEXT NOT NULL,
            category TEXT NOT NULL,
            source_messages TEXT,
            source_message_times TEXT,
            analysis_reasoning TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 每日作息摘要
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT PRIMARY KEY,
            total_sleep_minutes INTEGER DEFAULT 0,
            total_work_minutes INTEGER DEFAULT 0,
            total_exercise_minutes INTEGER DEFAULT 0,
            total_commute_minutes INTEGER DEFAULT 0,
            total_eating_minutes INTEGER DEFAULT 0,
            total_learning_minutes INTEGER DEFAULT 0,
            total_entertainment_minutes INTEGER DEFAULT 0,
            total_unknown_minutes INTEGER DEFAULT 0,
            
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# ============ 基础读写接口 ============
def get_connection():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))

def get_dr_connection():
    """获取语录数据库连接"""
    return sqlite3.connect(str(DR_DB_PATH))

# ============ 增量同步核心函数 ============
def get_last_record():
    """
    获取 schedule_records 中最后一条记录
    返回: (date, time_start, time_end) 或 None
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT date, time_start, time_end FROM schedule_records
        ORDER BY date DESC, time_end DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    conn.close()
    return row  # e.g. ('2026-05-20', '22:41', '23:59')

def get_prev_message(before_time_str):
    """
    获取 before_time 之前的最后一条消息（理解上下文用）
    before_time 格式: "2026-05-20 22:41:00"
    返回: (msg_id, time_str, channel, content) 或 None
    """
    from_ts = _time_str_to_ts(before_time_str) - 1
    conn = get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, message_id, timestamp, channel, sender_id, content
        FROM user_messages
        WHERE timestamp < ?
        ORDER BY timestamp DESC
        LIMIT 1
    ''', (from_ts,))
    row = c.fetchone()
    conn.close()
    if row:
        msg_id, msg_id2, ts, channel, sender_id, content = row
        return (str(msg_id), _ts_to_time(ts), channel, content)
    return None

def get_messages_after(after_time_str):
    """
    获取 after_time 之后的所有消息
    after_time 格式: "2026-05-20 22:41:00"
    返回: list of (msg_id, time_str_HHMM, channel, content)
    """
    from_ts = _time_str_to_ts(after_time_str)
    conn = get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, message_id, timestamp, channel, sender_id, content
        FROM user_messages
        WHERE timestamp > ?
        ORDER BY timestamp
    ''', (from_ts,))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        msg_id, msg_id2, ts, channel, sender_id, content = row
        time_str = _ts_to_time(ts)
        result.append((str(msg_id), time_str.split(" ")[1][:5], channel, content))
    return result

def get_messages_between(start_time_str, end_time_str):
    """
    获取两个时间点之间的所有消息
    格式: "2026-05-20 00:00:00" ~ "2026-05-20 23:59:59"
    返回: list of (msg_id, time_str_HHMM, channel, content)
    """
    from_ts = _time_str_to_ts(start_time_str)
    to_ts = _time_str_to_ts(end_time_str)
    
    # 用 date 字段过滤，格式是 YYYYMMDD
    start_date = start_time_str.split(" ")[0].replace("-", "")
    end_date = end_time_str.split(" ")[0].replace("-", "")
    
    conn = get_dr_connection()
    c = conn.cursor()
    if start_date == end_date:
        c.execute('''
            SELECT id, message_id, timestamp, channel, sender_id, content
            FROM user_messages
            WHERE date = ?
            ORDER BY timestamp
        ''', (start_date,))
    else:
        c.execute('''
            SELECT id, message_id, timestamp, channel, sender_id, content
            FROM user_messages
            WHERE date >= ? AND date <= ?
            ORDER BY timestamp
        ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        msg_id, msg_id2, ts, channel, sender_id, content = row
        time_str = _ts_to_time(ts)
        result.append((str(msg_id), time_str.split(" ")[1][:5], channel, content))
    return result

# ============ 时间转换工具 ============
def _ts_to_time(ts):
    """13位毫秒时间戳 → '2026-05-20 22:41:00'"""
    try:
        ts = int(ts) // 1000000
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "2000-01-01 00:00:00"

def _time_str_to_ts(time_str):
    """'2026-05-20 22:41:00' → 毫秒时间戳"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)
    except:
        return 0

# ============ 作息记录操作 ============
def add_record(date, time_start, time_end, activity, category,
               source_messages="", source_message_times="", analysis_reasoning="",
               duration_minutes=None):
    """添加一条作息记录"""
    if duration_minutes is None:
        try:
            h1, m1 = map(int, time_start.split(":"))
            h2, m2 = map(int, time_end.split(":"))
            duration_minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
            if duration_minutes < 0:
                duration_minutes += 1440
        except:
            duration_minutes = 0

    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO schedule_records
        (date, time_start, time_end, duration_minutes, activity, category, source_messages, source_message_times, analysis_reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, time_start, time_end, duration_minutes, activity, category, source_messages, source_message_times, analysis_reasoning))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id

def get_records_by_date(date_str):
    """获取指定日期的所有作息记录（按时间排序）"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, time_start, time_end, duration_minutes, activity, category, source_messages, source_message_times, analysis_reasoning
        FROM schedule_records
        WHERE date = ?
        ORDER BY time_start
    ''', (date_str,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_records_range(start_date, end_date):
    """获取日期范围内的所有作息记录"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, date, time_start, time_end, duration_minutes, activity, category, source_messages, source_message_times, analysis_reasoning
        FROM schedule_records
        WHERE date >= ? AND date <= ?
        ORDER BY date, time_start
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_date_records(date_str):
    """清空指定日期的所有记录（重新生成时用）"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM schedule_records WHERE date = ?', (date_str,))
    conn.commit()
    conn.close()

# ============ 摘要操作 ============
def save_daily_summary(date_str, summary_dict):
    """保存每日作息摘要"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO daily_summary
        (date, total_sleep_minutes, total_work_minutes, total_exercise_minutes,
         total_commute_minutes, total_eating_minutes, total_learning_minutes,
         total_entertainment_minutes, total_unknown_minutes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        date_str,
        summary_dict.get("sleep", 0), summary_dict.get("work", 0),
        summary_dict.get("exercise", 0), summary_dict.get("commute", 0),
        summary_dict.get("eating", 0), summary_dict.get("learning", 0),
        summary_dict.get("entertainment", 0), summary_dict.get("unknown", 0)
    ))
    conn.commit()
    conn.close()

def get_daily_summary(date_str):
    """获取每日摘要"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_summary WHERE date = ?', (date_str,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "date": row[0], "sleep": row[1], "work": row[2], "exercise": row[3],
            "commute": row[4], "eating": row[5], "learning": row[6],
            "entertainment": row[7], "unknown": row[8]
        }
    return None

def get_summaries_range(start_date, end_date):
    """获取日期范围内的摘要"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT date, total_sleep_minutes, total_work_minutes, total_exercise_minutes,
               total_commute_minutes, total_eating_minutes, total_learning_minutes,
               total_entertainment_minutes, total_unknown_minutes        FROM daily_summary
        WHERE date >= ? AND date <= ?
        ORDER BY date
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return rows

# ============ 初始化 ============
if __name__ == "__main__":
    init_db()
    print("✓ 作息管家数据库初始化完成")
    print(f"  数据路径: {DB_PATH}")
    print(f"  语录路径: {DR_DB_PATH}")
    last = get_last_record()
    print(f"  最后记录: {last if last else '（无）'}")