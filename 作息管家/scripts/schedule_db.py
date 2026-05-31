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
    # 1. 环境变量（最高优先级，设了就直接用）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p / db_filename
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

# ============ 基础读写接口 ============
def _configure_connection(conn):
    """配置连接：WAL模式 + 并发安全"""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

def get_connection():
    """获取作息管家数据库连接"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    _configure_connection(conn)
    return conn

def get_dr_connection():
    """获取语录数据库连接"""
    conn = sqlite3.connect(str(DR_DB_PATH))
    _configure_connection(conn)
    return conn

# ============ 数据库初始化 ============
def init_db():
    """初始化作息管家数据库"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    _configure_connection(conn)
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
            source_contents TEXT,
            source_timestamps TEXT,
            analysis_reasoning TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 每日作息摘要（KV结构，适配任意分类）
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            total_minutes INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, category)
        )
    ''')

    # 计划作息表（每天24小时，每小时一个计划描述）
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedule_plans (
            date TEXT PRIMARY KEY,
            hour_0_planned TEXT,
            hour_1_planned TEXT,
            hour_2_planned TEXT,
            hour_3_planned TEXT,
            hour_4_planned TEXT,
            hour_5_planned TEXT,
            hour_6_planned TEXT,
            hour_7_planned TEXT,
            hour_8_planned TEXT,
            hour_9_planned TEXT,
            hour_10_planned TEXT,
            hour_11_planned TEXT,
            hour_12_planned TEXT,
            hour_13_planned TEXT,
            hour_14_planned TEXT,
            hour_15_planned TEXT,
            hour_16_planned TEXT,
            hour_17_planned TEXT,
            hour_18_planned TEXT,
            hour_19_planned TEXT,
            hour_20_planned TEXT,
            hour_21_planned TEXT,
            hour_22_planned TEXT,
            hour_23_planned TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

# ============ 查询接口（AI同步用）===========
def get_last_record_full():
    """
    获取 schedule_records 中最后一条完整记录
    返回: dict 或 None
    用于AI同步时确定游标位置
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, date, time_start, time_end, duration_minutes, 
               activity, category, source_contents, source_timestamps, analysis_reasoning
        FROM schedule_records
        ORDER BY date DESC, time_end DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    conn.close()
    if row:
        return {
            'id': row[0], 'date': row[1], 'time_start': row[2], 'time_end': row[3],
            'duration_minutes': row[4], 'activity': row[5], 'category': row[6],
            'source_contents': row[7], 'source_timestamps': row[8], 'analysis_reasoning': row[9]
        }
    return None

def get_messages_before(before_time_str, limit=10):
    """
    获取 before_time 之前的N条消息（用于确定AI分析起始点）
    before_time 格式: "2026-05-20 22:41:00"
    返回: list of (msg_id, time_str, channel, content)
    """
    from_ts = _time_str_to_ts(before_time_str) - 1
    conn = get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, message_id, timestamp, channel, sender_id, content
        FROM user_messages
        WHERE timestamp < ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (from_ts, limit))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        msg_id, msg_id2, ts, channel, sender_id, content = row
        result.append((str(msg_id), _ts_to_time(ts), channel, content))
    return result  # 已按时间倒序，调用方需要反转

def get_messages_from(from_time_str, to_time_str=None):
    """
    获取 from_time 到 to_time 为止的所有消息
    from_time / to_time 格式: "2026-05-20 22:41:00"
    to_time 为空时获取到当前时间
    返回: list of (msg_id, time_str_HHMM, channel, content)
    """
    from_ts = _time_str_to_ts(from_time_str)
    to_ts = _time_str_to_ts(to_time_str) if to_time_str else _time_str_to_ts(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    conn = get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, message_id, timestamp, channel, sender_id, content
        FROM user_messages
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    ''', (from_ts, to_ts))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        msg_id, msg_id2, ts, channel, sender_id, content = row
        time_str = _ts_to_time(ts)
        result.append((str(msg_id), time_str.split(" ")[1][:5], channel, content))
    return result


def get_messages_for_sync(cursor_datetime_str, end_time_str=None):
    """
    获取同步所需的全部消息
    1. 获取游标前10条消息（AI上下文参考，不处理）
    2. 获取游标时间之后到结束时间的所有新消息（实际处理）
    end_time_str: 结束时间，格式 "2026-05-20 22:41:00"，为空则到当前时间
    返回: (cursor_datetime, prev_messages, new_messages)
    """
    # 获取游标前10条消息（用于AI理解上下文，不写入）
    prev_messages = get_messages_before(cursor_datetime_str, limit=10)
    # 反转，按时间正序（最早在前）
    prev_messages = list(reversed(prev_messages))
    
    # 获取游标时间之后到结束时间的所有新消息
    new_messages = get_messages_from(cursor_datetime_str, end_time_str)
    
    return cursor_datetime_str, prev_messages, new_messages

# ============ 同步粒度校验（委托给 block_count.py）============
from block_count import get_required_block_count, validate_record_count


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
    """'2026-05-20 22:41:00' → 微秒时间戳（与数据库16位时间戳一致）"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000000)
    except:
        return 0

# ============ 作息记录操作（完整字段）===========
def add_record_full(date, time_start, time_end, duration_minutes, activity, category,
                  source_contents, source_timestamps, analysis_reasoning):
    """
    增加一条作息记录（全部字段校验）
    必须传入全部9个字段，缺一不可
    """
    # 字段完整性校验
    required_fields = {
        'date': date, 'time_start': time_start, 'time_end': time_end,
        'duration_minutes': duration_minutes, 'activity': activity,
        'category': category, 'source_contents': source_contents,
        'source_timestamps': source_timestamps, 'analysis_reasoning': analysis_reasoning
    }
    missing = [k for k, v in required_fields.items() if v is None or v == '']
    if missing:
        raise ValueError(f"缺少必填字段: {', '.join(missing)}")

    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO schedule_records
        (date, time_start, time_end, duration_minutes, activity, category,
         source_contents, source_timestamps, analysis_reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (date, time_start, time_end, duration_minutes, activity, category,
          source_contents, source_timestamps, analysis_reasoning))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id

def update_record(record_id, **kwargs):
    """
    更新一条作息记录（按id定位）
    kwargs: date/time_start/time_end/duration_minutes/activity/category/source_contents/source_timestamps/analysis_reasoning
    """
    if not record_id:
        raise ValueError("record_id 不能为空")

    allowed_fields = {'date', 'time_start', 'time_end', 'duration_minutes',
                     'activity', 'category', 'source_contents',
                     'source_timestamps', 'analysis_reasoning'}

    updates = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}
    if not updates:
        raise ValueError("没有有效的更新字段")

    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [record_id]

    conn = get_connection()
    c = conn.cursor()
    c.execute(f'UPDATE schedule_records SET {set_clause} WHERE id = ?', values)
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected

RECORD_KEYS = ['id', 'date', 'time_start', 'time_end', 'duration_minutes', 'activity', 'category', 'source_contents', 'source_timestamps', 'analysis_reasoning', 'created_at']

def get_records_by_date(date_str):
    """获取指定日期的所有作息记录（按时间排序）返回字典列表"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, date, time_start, time_end, duration_minutes, activity, category, source_contents, source_timestamps, analysis_reasoning, created_at
        FROM schedule_records
        WHERE date = ?
        ORDER BY time_start
    ''', (date_str,))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(RECORD_KEYS, row)) for row in rows]

def get_records_range(start_date, end_date):
    """获取日期范围内的所有作息记录，返回字典列表"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT id, date, time_start, time_end, duration_minutes, activity, category, source_contents, source_timestamps, analysis_reasoning, created_at
        FROM schedule_records
        WHERE date >= ? AND date <= ?
        ORDER BY date, time_start
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return [dict(zip(RECORD_KEYS, row)) for row in rows]

def has_records_for_date(date_str):
    """检查指定日期是否已有记录"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM schedule_records WHERE date = ?', (date_str,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

# ============ 摘要操作 ============
def add_summary(date, category, total_minutes):
    """
    增加一条每日摘要记录（KV结构）
    date: 日期（YYYY-MM-DD）
    category: 分类名（AI自由填写）
    total_minutes: 该分类总分钟数
    """
    if not date:
        raise ValueError("date 不能为空")
    if not category:
        raise ValueError("category 不能为空")
    if total_minutes is None or total_minutes < 0:
        raise ValueError("total_minutes 不能为空且必须 >= 0")

    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO daily_summary (date, category, total_minutes)
        VALUES (?, ?, ?)
        ON CONFLICT(date, category) DO UPDATE SET
            total_minutes = excluded.total_minutes,
            generated_at = CURRENT_TIMESTAMP
    ''', (date, category, total_minutes))
    conn.commit()
    conn.close()
    return {'date': date, 'category': category, 'total_minutes': total_minutes}

def get_daily_summary(date_str):
    """获取每日摘要，返回 list of {category, total_minutes}"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT category, total_minutes
        FROM daily_summary
        WHERE date = ?
        ORDER BY total_minutes DESC
    ''', (date_str,))
    rows = c.fetchall()
    conn.close()
    return [{'category': row[0], 'total_minutes': row[1]} for row in rows] if rows else []

def get_summaries_range(start_date, end_date):
    """获取日期范围内的摘要，返回 list of {date, category, total_minutes}"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT date, category, total_minutes
        FROM daily_summary
        WHERE date >= ? AND date <= ?
        ORDER BY date, total_minutes DESC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()
    return [{'date': row[0], 'category': row[1], 'total_minutes': row[2]} for row in rows]

# ============ 计划作息操作 ============
def upsert_plan(date, hour_plans):
    """
    新增或更新计划作息（upsert）
    date: 日期（YYYY-MM-DD）
    hour_plans: dict，key 为 hour_0 ~ hour_23，value 为计划描述
    例如: {'hour_0': '睡觉', 'hour_8': '30min通勤+30min工作'}
    注意: 必须提供全部24个小时段，不能遗漏
    """
    if not date:
        raise ValueError("date 不能为空")
    if not hour_plans:
        raise ValueError("hour_plans 不能为空")

    # 校验 hour_plans 的 key
    valid_keys = {f'hour_{i}' for i in range(24)}
    invalid = [k for k in hour_plans.keys() if k not in valid_keys]
    if invalid:
        raise ValueError(f"无效的小时字段: {', '.join(invalid)}")

    # 校验是否填满了全部24小时
    missing = valid_keys - set(hour_plans.keys())
    if missing:
        missing_hours = sorted([int(k.split('_')[1]) for k in missing])
        raise ValueError(f"以下时间段未填写: {missing_hours}，要求填满全部24个小时（hour_0 到 hour_23）")

    # 校验是否有空值
    empty_fields = [k for k, v in hour_plans.items() if not v or not str(v).strip()]
    if empty_fields:
        empty_hours = sorted([int(k.split('_')[1]) for k in empty_fields])
        raise ValueError(f"以下时间段内容为空: {empty_hours}，所有时间段必须有内容")

    conn = get_connection()
    c = conn.cursor()

    try:
        # 尝试 INSERT
        hour_cols = ', '.join([f'hour_{i}_planned' for i in range(24)])
        c.execute(f'''
            INSERT INTO schedule_plans (date, {hour_cols})
            VALUES ({', '.join(['?' for _ in range(25)])})
        ''', [date] + [hour_plans.get(f'hour_{i}') for i in range(24)])
        conn.commit()
        action = 'insert'
    except sqlite3.IntegrityError:
        # 日期已存在，执行 UPDATE（只更新提供的字段，保留其他）
        conn.rollback()
        set_parts = []
        values = []
        for i in range(24):
            key = f'hour_{i}'
            if key in hour_plans:
                set_parts.append(f'hour_{i}_planned = ?')
                values.append(hour_plans[key])
        
        if set_parts:
            values.append(date)
            c.execute(f'''
                UPDATE schedule_plans 
                SET {', '.join(set_parts)}, updated_at = CURRENT_TIMESTAMP
                WHERE date = ?
            ''', values)
            conn.commit()
        action = 'update'

    conn.close()
    return {'date': date, 'action': action}

def get_plan(date):
    """
    获取指定日期的计划作息
    date: 日期（YYYY-MM-DD）
    返回: dict 或 None
    """
    conn = get_connection()
    c = conn.cursor()
    hour_cols = ', '.join([f'hour_{i}_planned' for i in range(24)])
    c.execute(f'''
        SELECT date, {hour_cols}, created_at, updated_at
        FROM schedule_plans WHERE date = ?
    ''', (date,))
    row = c.fetchone()
    conn.close()
    if row:
        result = {'date': row[0]}
        for i in range(24):
            result[f'hour_{i}'] = row[i + 1]
        result['created_at'] = row[25]
        result['updated_at'] = row[26]
        return result
    return None

def get_plans(dates):
    """
    获取多个日期的计划作息
    dates: list of date strings 或 逗号分隔的字符串
    返回: list of dict
    """
    if isinstance(dates, str):
        # 支持逗号分隔的字符串
        dates = [d.strip() for d in dates.split(',')]
    
    if not dates:
        return []

    placeholders = ', '.join(['?' for _ in dates])
    conn = get_connection()
    c = conn.cursor()
    hour_cols = ', '.join([f'hour_{i}_planned' for i in range(24)])
    c.execute(f'''
        SELECT date, {hour_cols}, created_at, updated_at
        FROM schedule_plans WHERE date IN ({placeholders})
        ORDER BY date
    ''', dates)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        result = {'date': row[0]}
        for i in range(24):
            result[f'hour_{i}'] = row[i + 1]
        result['created_at'] = row[25]
        result['updated_at'] = row[26]
        results.append(result)
    return results

# ============ 初始化 ============
if __name__ == "__main__":
    init_db()
    print("✓ 作息管家数据库初始化完成")
    print(f"  数据路径: {DB_PATH}")
    print(f"  语录路径: {DR_DB_PATH}")
    last = get_last_record_full()
    print(f"  最后记录: {last if last else '（无）'}")