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

路径两层查找：环境变量 SKILLS_DB_PATH > D:/.db（WSL 转 /mnt/d/.db/）
"""

import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional

# ============ 时间归一化工具(飞书 ISO 8601 不接受 24:00,自动转次日 00:00)===========
def normalize_time(t: str) -> str:
    """
    把 HH:MM 字符串归一化:
    - '24:00' → '23:59'(飞书 ISO 8601 不接受 24:00,会转次日 00:00 导致对账失败;统一用 23:59)
    - 其他原样返回
    """
    if t == "24:00":
        return "23:59"
    return t

# ============ 日期归一化工具(与 schedule_plans.date 字段对齐:'YYYY-MM-DD')===========
def _normalize_date(d) -> str:
    """
    把日期字符串归一为 'YYYY-MM-DD' 格式（与 schedule_plans.date 字段一致）。

    支持的输入格式：
      - '2026-07-03'         → '2026-07-03'（标准 ISO）
      - '20260703'           → '2026-07-03'（紧凑 8 位）
      - '2026/07/03'         → '2026-07-03'（斜杠）
      - '2026.07.03'         → '2026-07-03'（点）

    非法格式抛 ValueError。
    修复日期：2026-07-03（query-plans 传 20260703 却查不到数据的 bug）。
    """
    if not d or not isinstance(d, str):
        raise ValueError(f"date 参数无效：{d!r}")
    s = d.strip().replace('/', '-').replace('.', '-')
    if len(s) == 8 and s.isdigit():
        s = f"{s[:4]}-{s[4:6]}-{s[6:]}"
    try:
        datetime.strptime(s, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(
            f"日期格式非法：{d!r}（期望 YYYY-MM-DD 或 YYYYMMDD）"
        ) from e
    return s

# ============ 路径配置（两层查找）===========
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "schedule_data.db"
DR_FILENAME = "daily_recorder.db"

def _fallback_db_dir():
    """全局 fallback DB 目录：Windows → D:/.db，WSL → /mnt/d/.db"""
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    raise RuntimeError(
        'SKILLS_DB_PATH 未设置，且 D: 盘未挂载到 /mnt/d/。'
        '请检查 WSL automount 配置或设置 SKILLS_DB_PATH 环境变量。'
    )

def _find_db_path(skill_dir, db_filename):
    """两层查找DB路径：环境变量 SKILLS_DB_PATH > D:/.db"""
    # 1. 环境变量（最高优先级，设了就直接用）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path)
        p.mkdir(parents=True, exist_ok=True)
        return p / db_filename
    # 2. fallback: D:\.db\（WSL 自动转 /mnt/d/.db/）
    db_dir = _fallback_db_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / db_filename

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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            edit_count INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # 迁移：已有 DB 补加 updated_at / edit_count 字段(2026-07-24)
    try:
        c.execute("ALTER TABLE schedule_records ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE schedule_records ADD COLUMN edit_count INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

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

    # 旧版日程计划表（每天24小时，每小时一个计划描述，2026-06-29 已被事件型 schema 取代）
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

def get_messages_from(from_time_str, to_time_str=None, limit=None, offset=0):
    """
    获取 from_time 到 to_time 为止的消息（支持分页）
    from_time / to_time 格式: "2026-05-20 22:41:00"
    to_time 为空时获取到当前时间
    limit: 每页条数，None 表示不限制
    offset: 跳过前 N 条
    返回: list of (msg_id, time_str_HHMM, channel, content)
    """
    from_ts = _time_str_to_ts(from_time_str)
    to_ts = _time_str_to_ts(to_time_str) if to_time_str else _time_str_to_ts(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    conn = get_dr_connection()
    c = conn.cursor()
    if limit is not None:
        c.execute('''
            SELECT id, message_id, timestamp, channel, sender_id, content
            FROM user_messages
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
            LIMIT ? OFFSET ?
        ''', (from_ts, to_ts, limit, offset))
    else:
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


def count_messages_from(from_time_str, to_time_str=None):
    """
    统计 from_time 到 to_time 之间的消息总数
    from_time / to_time 格式: "2026-05-20 22:41:00"
    """
    from_ts = _time_str_to_ts(from_time_str)
    to_ts = _time_str_to_ts(to_time_str) if to_time_str else _time_str_to_ts(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    conn = get_dr_connection()
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM user_messages
        WHERE timestamp >= ? AND timestamp <= ?
    ''', (from_ts, to_ts))
    count = c.fetchone()[0]
    conn.close()
    return count


def get_messages_for_sync(cursor_datetime_str, end_time_str=None, limit=None, offset=0):
    """
    获取同步所需的消息（支持分页）
    1. 获取游标前10条消息（AI上下文参考，不处理）
    2. 获取游标时间之后到结束时间的消息（实际处理，支持分页）
    end_time_str: 结束时间，格式 "2026-05-20 22:41:00"，为空则到当前时间
    limit: 每页条数，None 表示不限制
    offset: 跳过前 N 条
    返回: (cursor_datetime, prev_messages, new_messages)
    """
    # 获取游标前10条消息（用于AI理解上下文，不写入）
    prev_messages = get_messages_before(cursor_datetime_str, limit=10)
    # 反转，按时间正序（最早在前）
    prev_messages = list(reversed(prev_messages))

    # 获取游标时间之后到结束时间的消息（支持分页）
    new_messages = get_messages_from(cursor_datetime_str, end_time_str, limit=limit, offset=offset)

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
    category 必须通过白名单校验(2026-07-22 重构后强制)
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

    # category 白名单校验(2026-07-22 分类系统重构)
    from validators import validate_category
    _valid, _err = validate_category(category)
    if not _valid:
        raise ValueError(f"category 校验失败: {_err}")

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

def update_record(record_id, fields: dict = None, **kwargs) -> dict:
    """
    更新一条作息记录(按 id 定位)。

    双重支持两种调用方式(2026-07-24 重构):
      - update_record(rid, fields={"category": "工作.AI"})
      - update_record(rid, category="工作.AI")  # kwargs 形式

    自动维护审计字段:updated_at = CURRENT_TIMESTAMP, edit_count = edit_count + 1。

    Args:
        record_id: 记录 ID
        fields: dict 形式的字段映射(可与 kwargs 并存)
        **kwargs: 字段=值 形式

    Returns:
        dict {
            "before":     {11 字段 dict},   # 修改前完整记录
            "after":      {11 字段 dict},   # 修改后完整记录
            "diff":       {field: {"old": X, "new": Y}, ...},  # 只含真正修改的字段
            "edit_count": int,             # 当前 edit_count(修改后)
            "within_24h": bool,            # 记录 date 是否在今天(用户友好提示用)
            "enforce_24h_warned": bool,    # True 如果超出 24h 但仍允许(2026-07-24 加)
        }

    Raises:
        ValueError: 无效字段 / category 非法 / 无更新 / record_id 不存在
    """
    if not record_id:
        raise ValueError("record_id 不能为空")

    # 合并 fields + kwargs
    all_updates = dict(kwargs)
    if fields:
        all_updates.update(fields)

    # 完全没传任何字段 → 报错(防误调)
    if not all_updates:
        raise ValueError("必须至少传 1 个字段(无 fields/kwargs)")

    allowed_fields = {'date', 'time_start', 'time_end', 'duration_minutes',
                     'activity', 'category', 'source_contents',
                     'source_timestamps', 'analysis_reasoning'}

    # 只过滤字段名合法性(允许空字符串 — 用户可能想清空 source_contents)
    updates = {k: v for k, v in all_updates.items() if k in allowed_fields}
    # 注:全部字段被过滤不算错,只是 noop(下面 SELECT before 后会直接返回空 diff)

    # category 白名单校验(2026-07-22 分类系统重构)
    if 'category' in updates:
        from validators import validate_category
        _valid, _err = validate_category(updates['category'])
        if not _valid:
            raise ValueError(f"category 校验失败: {_err}")

    conn = get_connection()
    try:
        c = conn.cursor()
        # Step 1: 拿 before 完整记录
        c.execute('SELECT id, date, time_start, time_end, duration_minutes, activity, '
                  'category, source_contents, source_timestamps, analysis_reasoning, '
                  'created_at, updated_at, edit_count '
                  'FROM schedule_records WHERE id = ?', (record_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"record_id={record_id} 不存在")
        keys = ['id', 'date', 'time_start', 'time_end', 'duration_minutes', 'activity',
                'category', 'source_contents', 'source_timestamps', 'analysis_reasoning',
                'created_at', 'updated_at', 'edit_count']
        before = dict(zip(keys, row))

        # Step 2: 算 diff(只含真正改了的字段)
        diff = {}
        for k, v_new in updates.items():
            v_old = before.get(k)
            # 用 str() 比较避免 type 不一致误报 diff
            if str(v_old) != str(v_new):
                diff[k] = {"old": v_old, "new": v_new}
        if not diff:
            # 用户传了字段但值没变 → 视为无操作,返回 before + 空 diff
            return {
                "before": before, "after": before, "diff": {},
                "edit_count": before["edit_count"], "within_24h": False, "enforce_24h_warned": False,
            }

        # Step 3: UPDATE(自动维护 updated_at + edit_count)
        new_edit_count = before["edit_count"] + 1
        set_parts = [f"{k} = ?" for k in diff.keys()]
        set_parts.append("updated_at = CURRENT_TIMESTAMP")
        set_parts.append("edit_count = ?")
        values = [v["new"] for v in diff.values()] + [new_edit_count, record_id]
        c.execute(f'UPDATE schedule_records SET {", ".join(set_parts)} WHERE id = ?', values)
        conn.commit()

        # Step 4: 拿 after 完整记录
        c.execute('SELECT id, date, time_start, time_end, duration_minutes, activity, '
                  'category, source_contents, source_timestamps, analysis_reasoning, '
                  'created_at, updated_at, edit_count '
                  'FROM schedule_records WHERE id = ?', (record_id,))
        row2 = c.fetchone()
        after = dict(zip(keys, row2))

        # Step 5: 24h 检查(软提示 — 操作规范说"24h 内强烈推荐",但不强制阻断)
        from datetime import date as _d
        try:
            record_date = _d.fromisoformat(before["date"])
            today = _d.today()
            within_24h = abs((today - record_date).days) <= 1
        except Exception:
            within_24h = False

        return {
            "before": before, "after": after, "diff": diff,
            "edit_count": new_edit_count, "within_24h": within_24h, "enforce_24h_warned": False,
        }
    finally:
        conn.close()

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

def get_record_by_id(record_id):
    """
    按 ID 查询单条作息记录,返回完整 13 字段 dict(含 updated_at + edit_count,2026-07-24);
    无则返回 None。
    100% 字段暴露原则:CLI 把全字段提供给上层,上层自己决定如何渲染。
    """
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT id, date, time_start, time_end, duration_minutes, activity,
                   category, source_contents, source_timestamps,
                   analysis_reasoning, created_at, updated_at, edit_count
            FROM schedule_records WHERE id = ?
        ''', (record_id,))
        row = c.fetchone()
        if not row:
            return None
        # 13 字段(2026-07-24 加 updated_at + edit_count)
        _KEYS_13 = ['id', 'date', 'time_start', 'time_end', 'duration_minutes', 'activity',
                    'category', 'source_contents', 'source_timestamps', 'analysis_reasoning',
                    'created_at', 'updated_at', 'edit_count']
        return dict(zip(_KEYS_13, row))
    finally:
        conn.close()

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

# ============ 旧版日程计划操作（2026-06-29 之前的小时格模型）===========
def upsert_plan(date, hour_plans):
    """
    新增或更新旧版日程（upsert，2026-06-29 之前的小时格模型）
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

def _read_plan_dict(date: str) -> dict | None:
    """
    内部：从新 schedule_plans（事件型）按 hour 聚合，返回 {date, hour_0..hour_23, created_at, updated_at} dict。
    - 每条事件映射到 time_start 的整点小时（hour_N）
    - 该小时内若有多条事件，title 用 "+" 拼接
    - 仅取 is_active=1 的事件
    - 旧 gen_report 脚本 + 其他下游消费者均依赖此 dict 形状
    """
    date = _normalize_date(date)  # 容错：20260703 / 2026-07-03 / 2026/07/03 都归一为 2026-07-03
    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)  # 幂等建表
        c = conn.cursor()
        # 拉该日所有活跃事件，按 time_start ASC
        c.execute('''
            SELECT time_start, time_end, title
            FROM schedule_plans
            WHERE date = ? AND is_active = 1
            ORDER BY time_start
        ''', (date,))
        rows = c.fetchall()
        # 拉 created_at / updated_at（取最新）
        c.execute('''
            SELECT MIN(created_at) AS first_created, MAX(updated_at) AS last_updated
            FROM schedule_plans
            WHERE date = ?
        ''', (date,))
        ts_row = c.fetchone()
        first_created, last_updated = ts_row[0], ts_row[1]

        result = {'date': date}
        for i in range(24):
            result[f'hour_{i}'] = ''  # 默认空（迁移前旧空小时也是 None）
        # 按整点小时分桶拼接
        bucket = {i: [] for i in range(24)}
        for ts, te, title in rows:
            try:
                start_hour = int(ts.split(":")[0])
                if 0 <= start_hour <= 23:
                    bucket[start_hour].append(str(title).strip())
            except Exception:
                continue
        for i in range(24):
            if bucket[i]:
                result[f'hour_{i}'] = "+".join(bucket[i])
        result['created_at'] = first_created
        result['updated_at'] = last_updated
        return result
    finally:
        conn.close()


def get_plan(date):
    """
    获取指定日期的日程聚合视图（向旧接口兼容：从新事件表聚合，按 hour 0..23 组织）
    date: 日期（YYYY-MM-DD）
    返回: dict 或 None — 含 date / hour_0..hour_23 / created_at / updated_at
    """
    result = _read_plan_dict(date)
    return result


def get_plans(dates):
    """
    获取多个日期的日程聚合视图（向旧接口兼容）
    dates: list of date strings 或 逗号分隔的字符串
    返回: list of dict
    """
    if isinstance(dates, str):
        dates = [d.strip() for d in dates.split(',')]
    if not dates:
        return []
    results = []
    for d in dates:
        r = _read_plan_dict(d)
        if r is not None:
            results.append(r)
    return results

# ============ 初始化 ============
if __name__ == "__main__":
    init_db()
    print("✓ 作息管家数据库初始化完成")
    print(f"  数据路径: {DB_PATH}")
    print(f"  语录路径: {DR_DB_PATH}")
    last = get_last_record_full()
    print(f"  最后记录: {last if last else '（无）'}")
# ============================================================
# 新版 schedule_plans（事件型 schema，2026-06-29 重构）
# ============================================================
# 与旧 hour_N_planned 模型共存：迁移前旧表继续工作；迁移脚本会把
# schedule_plans 重命名为 schedule_plans_legacy_2026_06_29 后，
# 这里建同名新表。新版函数与旧版 upsert_plan / get_plan / get_plans
# 完全独立，CLI 层只暴露新版命令。
#
# 新表字段：
#   id, date, time_start, time_end, title, notes, category,
#   feishu_event_id, last_synced_at, is_active, created_at, updated_at
# ============================================================

def _ensure_new_plans_schema(conn) -> None:
    """幂等创建新版 schedule_plans 表。供新 CRUD 函数首次调用时自动建表。"""
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            time_start      TEXT    NOT NULL,
            time_end        TEXT    NOT NULL,
            title           TEXT    NOT NULL,
            notes           TEXT,
            category        TEXT,
            feishu_event_id TEXT,
            last_synced_at  TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            completion      TEXT    DEFAULT NULL,
            completion_note TEXT    DEFAULT NULL,
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_plans_date ON schedule_plans(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_plans_date_time ON schedule_plans(date, time_start)')

    # 迁移：已有 DB 补加 completion 字段（2026-07-12）
    try:
        c.execute("ALTER TABLE schedule_plans ADD COLUMN completion TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE schedule_plans ADD COLUMN completion_note TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass


def _to_minutes(hhmm: str) -> int:
    """HH:MM 字符串 → 从 00:00 起算的分钟数。无效时抛 ValueError。"""
    if not isinstance(hhmm, str) or len(hhmm) < 4 or hhmm[2] != ":":
        raise ValueError(f"非法时间格式：{hhmm!r}（应为 HH:MM）")
    try:
        h, m = hhmm.split(":", 1)
        h, m = int(h), int(m)
        if h < 0 or h > 24 or m < 0 or m >= 60:
            raise ValueError
        return h * 60 + m
    except Exception as e:
        raise ValueError(f"非法时间格式：{hhmm!r}") from e


def _validate_event(e: dict, idx: int) -> tuple[int, int]:
    """校验一条 event 字段合法，返回 (start_min, end_min)。"""
    required = ("time_start", "time_end", "title")
    missing = [k for k in required if not e.get(k)]
    if missing:
        raise ValueError(f"events[{idx}] 缺字段：{missing}")
    start_min = _to_minutes(e["time_start"])
    end_min = _to_minutes(e["time_end"])
    if end_min <= start_min:
        raise ValueError(f"events[{idx}] time_end 必须 > time_start（{e['time_start']}~{e['time_end']}）")
    if start_min < 0 or end_min > 24 * 60:
        raise ValueError(f"events[{idx}] 时间超界（{e['time_start']}~{e['time_end']}，合法范围 00:00~24:00）")
    if not str(e.get("title", "")).strip():
        raise ValueError(f"events[{idx}] title 为空")
    if not isinstance(e.get("notes", None), (str, type(None))):
        raise ValueError(f"events[{idx}] notes 必须为字符串或 null")
    return start_min, end_min


def validate_24h_coverage(events: list[dict]) -> str | None:
    """
    校验 events 联合区间是否覆盖 [00:00, 24:00]（24*60 = 1440 分钟）。
    返回 None = 通过；非 None = 错误描述。
    """
    if not events:
        return "events 为空，至少需要 1 条"
    # 起点必须 00:00
    if events[0].get("time_start") != "00:00":
        return f"首事件 time_start 必须为 00:00，当前为 {events[0].get('time_start')}"
    # 终点必须 24:00
    if events[-1].get("time_end") != "24:00":
        return f"末事件 time_end 必须为 24:00，当前为 {events[-1].get('time_end')}"

    last_end = 0
    for idx, e in enumerate(events):
        start_min, end_min = _validate_event(e, idx)
        if start_min != last_end:
            return (
                f"events[{idx}] time_start={e['time_start']} 与上一条 time_end 不连续"
                f"（应有 {last_end // 60:02d}:{last_end % 60:02d}）"
            )
        last_end = end_min
    if last_end != 24 * 60:
        return f"事件区间总和不等于 24 小时（当前到 {last_end} 分钟，应到 1440 分钟）"
    return None


def last_minute(minutes: int) -> str:
    """辅助：分钟数→"MM" 格式（00-59）"""
    return f"{minutes % 60:02d}"


def list_plan_events(date: str, include_inactive: bool = False) -> list[dict]:
    """查询某日日程事件，按 time_start ASC。
    include_inactive=True 时同时返回 is_active=0 的记录（用于 diff_and_sync）。"""
    date = _normalize_date(date)  # 容错：同上
    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()
        cols = ("id", "date", "time_start", "time_end", "title", "notes", "category",
                "feishu_event_id", "last_synced_at", "is_active", "completion", "completion_note")
        if include_inactive:
            c.execute(f'''
                SELECT {", ".join(cols)}
                FROM schedule_plans
                WHERE date = ?
                ORDER BY time_start
            ''', (date,))
        else:
            c.execute(f'''
                SELECT {", ".join(cols)}
                FROM schedule_plans
                WHERE date = ? AND is_active = 1
                ORDER BY time_start
            ''', (date,))
        rows = c.fetchall()
        return [
            dict(zip(cols, r))
            for r in rows
        ]
    finally:
        conn.close()


def search_plan_event(date: str, title: str,
                       time_start: str | None = None,
                       time_end: str | None = None) -> dict | None:
    """按日期[+时间[+标题]]查找活跃日程事件。返回匹配的第一条或 None。

    2026-07-12 新增：轻量查询接口，供 ensure-plan-event 和 AI 诊断使用。
    2026-07-15 升级：补计划幂等性修复 - 支持按 (date+time) 三元组精确查重。

    查重维度（按以下优先级构造 WHERE）：
      1. date 必传
      2. time_start + time_end 同时传入 → 按 (date+time_start+time_end) 三元组
         （title 不参与匹配，title 是展示标签，不是身份）
      3. 否则按 (date+title) 二元组（兼容旧调用方）

    Args:
        date:       日期 YYYY-MM-DD
        title:      标题
        time_start: 可选，时段开始 HH:MM（与 time_end 同时传入触发三元组查重）
        time_end:   可选，时段结束 HH:MM

    Returns:
        dict | None: 匹配的第一条活跃事件（按 time_start 排序）或 None
    """
    date = _normalize_date(date)
    if time_start is not None:
        time_start = normalize_time(time_start)
    if time_end is not None:
        time_end = normalize_time(time_end)

    # 构造 WHERE 条件 + 参数（参数化防 SQL 注入）
    where_clauses = ["date = ?", "is_active = 1"]
    where_params: list = [date]
    if time_start is not None and time_end is not None:
        # 三元组查重（修复后路径）— title 不参与
        where_clauses.append("time_start = ?")
        where_params.append(time_start)
        where_clauses.append("time_end = ?")
        where_params.append(time_end)
    else:
        # 二元组查重（兼容旧调用方）— 保留
        where_clauses.append("title = ?")
        where_params.append(title)

    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()
        cols = ("id", "date", "time_start", "time_end", "title", "notes", "category",
                "feishu_event_id", "last_synced_at", "is_active", "completion", "completion_note")
        c.execute(f'''
            SELECT {", ".join(cols)}
            FROM schedule_plans
            WHERE {" AND ".join(where_clauses)}
            ORDER BY time_start
            LIMIT 1
        ''', where_params)
        r = c.fetchone()
        if not r:
            return None
        return dict(zip(cols, r))
    finally:
        conn.close()


def ensure_plan_event(date: str, time_start: str, time_end: str,
                      title: str, notes: str = None, category: str = None) -> dict:
    """确保某日程事件存在（幂等）。

    语义：确保本地 DB 和飞书日历两边都有该事件。缺哪边建哪边。

    流程：
      1. 查本地 DB → 有且 feishu_event_id 不为空 → found
      2. 查本地 DB → 有但 feishu_event_id 为空 → 尝试创建飞书事件并回写 ID
      3. 查本地 DB → 无 → INSERT 本地 → 尝试创建飞书事件并回写 ID
      飞书不可用时跳过（不阻塞本地写入）。"""
    date = _normalize_date(date)
    time_start_norm = normalize_time(time_start)
    time_end = normalize_time(time_end)
    # 2026-07-15 修复：按 (date+time_start+time_end) 三元组查重
    # title 不参与匹配 — 同一时段不同 title 视为同一条（幂等性第一性）
    existing = search_plan_event(date, title, time_start=time_start_norm, time_end=time_end)

    feishu_result = None

    if existing:
        if existing.get('feishu_event_id'):
            return {"action": "found", "id": existing["id"], "event": existing}
        # 有本地但未同步飞书 → 尝试同步
        feishu_result = _sync_one_feishu(existing['id'], date, time_start_norm, time_end, title, notes)
        event = get_plan_event(existing['id'])
        return {"action": "found", "id": existing["id"], "event": event, "feishu": feishu_result or "unavailable"}

    # 本地不存在 → INSERT
    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()
        c.execute('''
            INSERT INTO schedule_plans
                (date, time_start, time_end, title, notes, category, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (date, time_start_norm, time_end, title, notes, category))
        conn.commit()
        new_id = c.lastrowid
        # 尝试同步飞书
        feishu_result = _sync_one_feishu(new_id, date, time_start_norm, time_end, title, notes)
        event = get_plan_event(new_id)
        return {"action": "created", "id": new_id, "event": event, "feishu": feishu_result or "unavailable"}
    finally:
        conn.close()


def _parse_iso_time(iso_str: str) -> str:
    """从 ISO 8601 字符串提取 HH:MM（不依赖 datetime，避免时区解析坑）。

    例: '2026-07-15T10:00:00+08:00' → '10:00'
       '2026-07-15T22:30:00.000+08:00' → '22:30'
       '20260715T100000+0800'（紧凑格式）→ '10:00'

    失败返回空串。"""
    if not iso_str:
        return ""
    # 找 T
    t_idx = iso_str.find('T')
    if t_idx < 0 or t_idx + 6 > len(iso_str):
        return ""
    # T 后 5 字符固定是 HH:MM
    return iso_str[t_idx + 1: t_idx + 6]


def _sync_one_feishu(event_id: int, date: str, time_start: str, time_end: str,
                     title: str, notes: Optional[str] = None) -> Optional[str]:
    """为单条本地事件创建飞书日历事件并回写 feishu_event_id。

    飞书不可用（未装/未授权/API 失败）返回 None，不抛异常。

    2026-07-15 修复：飞书侧按 (date+time_start+time_end+title) 四元组查重。
    旧逻辑只按 title 查，导致同 title 不同时段事件会误绑，飞书侧出现重复。
    新逻辑：先按 title 拿候选，再 time 精确比对。"""
    try:
        from feishu_sync import is_feishu_available, create_event, search_events

        if not is_feishu_available():
            return None

        # 2026-07-15 修复：飞书侧按 (date+time_start+time_end+title) 四元组查重
        # 飞书 search_events 不支持 time 过滤，先按 title 拿候选再 time 比对
        existing_fs = search_events(date, date, query=title)
        for ev in existing_fs:
            if ev.summary != title:
                continue
            ev_time_start = _parse_iso_time(ev.start)
            ev_time_end = _parse_iso_time(ev.end)
            if ev_time_start == time_start and ev_time_end == time_end:
                # 飞书已有匹配 (date+time+title 一致) → 回写 ID（幂等）
                set_feishu_event_id(event_id, ev.event_id)
                return "found_feishu"

        # 飞书没有匹配 → 创建
        iso_start = f"{date}T{time_start}:00+08:00"
        iso_end = f"{date}T{time_end}:00+08:00"
        desc = f"作息管家自动同步 · {notes}" if notes else "作息管家自动同步"
        ev = create_event(iso_start, iso_end, title, description=desc)
        if ev and ev.event_id:
            set_feishu_event_id(event_id, ev.event_id)
            return "created_feishu"
        return None
    except Exception:
        return None


def upsert_plan_events(date: str, events: list[dict], validate_24h: bool = True) -> dict:
    """
    整日覆盖式 upsert。
    events: [{"time_start":"00:00","time_end":"01:00","title":"睡觉","notes":"深度","category":"休息"}, ...]
    - 联合区间必须 ⊇ [00:00, 24:00]（validate_24h=True 时校验）
    - 与 (date, time_start) 命中已有记录 → UPDATE
    - 不命中 → INSERT（feishu_event_id 为 NULL，需后续手动同步）
    - 旧 is_active=1 但新批次中无 → 软删除（is_active=0），不破坏飞书事件（由 diff_and_sync 清理）
    返回: {"added":N, "updated":M, "deactivated":K, "total_active":X}
    """
    date = _normalize_date(date)  # 容错：写库前归一，避免不同调用方写入不同格式
    if validate_24h:
        err = validate_24h_coverage(events)
        if err:
            raise ValueError(f"24 小时覆盖校验失败：{err}")

    # category 白名单校验(2026-07-22 分类系统重构) - 在循环外做一次,提前失败
    from validators import validate_category as _validate_category
    for _idx, _e in enumerate(events):
        _cat = _e.get("category")
        if _cat:
            _v, _err = _validate_category(_cat)
            if not _v:
                raise ValueError(f"事件[{_idx}] '{_e.get('title', '?')}' category 校验失败: {_err}")

    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()

        # 取出当前所有 is_active=1 的事件
        c.execute('SELECT id, time_start, time_end FROM schedule_plans WHERE date = ? AND is_active = 1', (date,))
        existing = {f"{r[1]}_{r[2]}": r[0] for r in c.fetchall()}

        added = updated = deactivated = 0
        now_keys = set()

        for e in events:
            # 数据规范化:24:00 → 23:59(飞书 ISO 8601 不接受 24:00)
            e["time_end"] = normalize_time(e["time_end"])
            key = f"{e['time_start']}_{e['time_end']}"
            now_keys.add(key)
            title = str(e["title"]).strip()
            notes = e.get("notes")
            category = e.get("category")
            if key in existing:
                c.execute('''
                    UPDATE schedule_plans
                    SET title=?, notes=?, category=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                ''', (title, notes, category, existing[key]))
                if c.rowcount > 0:
                    updated += 1
            else:
                # 冲突场景：同一 (date, time_start) 多条 — 暂按 (date,start,end) 自然覆盖；
                # 实际不会出现，因 24h 严格衔接
                c.execute('''
                    INSERT INTO schedule_plans
                        (date, time_start, time_end, title, notes, category, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                ''', (date, e["time_start"], e["time_end"], title, notes, category))
                added += 1

        # 软删除：旧活跃 + 新批次中没有的
        for key, eid in existing.items():
            if key not in now_keys:
                c.execute('UPDATE schedule_plans SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?', (eid,))
                if c.rowcount > 0:
                    deactivated += 1

        conn.commit()

        # 计算剩余活跃事件数
        c.execute('SELECT COUNT(*) FROM schedule_plans WHERE date = ? AND is_active = 1', (date,))
        total_active = c.fetchone()[0]

        return {"added": added, "updated": updated, "deactivated": deactivated, "total_active": total_active}
    finally:
        conn.close()


def update_plan_event(event_id: int, fields: dict) -> bool:
    """单条 UPDATE。fields 可含: title/notes/category/time_start/time_end/completion/completion_note。
    注:不在此处同步飞书(飞书同步由 CLI 询问流程触发,避免隐式副作用)。"""
    allowed = {"title", "notes", "category", "time_start", "time_end", "completion", "completion_note"}
    sets = []
    values = []
    # category 白名单校验(2026-07-22 分类系统重构)
    if 'category' in fields and fields['category']:
        from validators import validate_category
        _v, _err = validate_category(fields['category'])
        if not _v:
            raise ValueError(f"category 校验失败: {_err}")
    for k, v in fields.items():
        if k in allowed:
            # 数据规范化:24:00 → 23:59
            if k == "time_end":
                v = normalize_time(v)
            sets.append(f"{k}=?")
            values.append(v)
    if not sets:
        return False
    sets.append("updated_at=CURRENT_TIMESTAMP")
    values.append(event_id)
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(f'UPDATE schedule_plans SET {", ".join(sets)} WHERE id=?', values)
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def deactivate_plan_event(event_id: int) -> bool:
    """单条软删（is_active=0）。不动飞书——由 CLI 层询问是否同步删除飞书事件。"""
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('UPDATE schedule_plans SET is_active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?', (event_id,))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def set_feishu_event_id(event_id: int, feishu_event_id: str) -> bool:
    """飞书同步成功后回写 event_id 与 last_synced_at。
    如果传入 None/空串 → 清除关联（用于同步删除后清状态）。"""
    conn = get_connection()
    try:
        c = conn.cursor()
        if feishu_event_id:
            c.execute('''
                UPDATE schedule_plans
                SET feishu_event_id=?, last_synced_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (feishu_event_id, event_id))
        else:
            c.execute('''
                UPDATE schedule_plans
                SET feishu_event_id=NULL, last_synced_at=NULL
                WHERE id=?
            ''', (event_id,))
        conn.commit()
        return c.rowcount > 0
    finally:
        conn.close()


def get_plan_event(event_id: int) -> dict | None:
    """单条读。"""
    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()
        c.execute('''
            SELECT id, date, time_start, time_end, title, notes, category,
                   feishu_event_id, last_synced_at, is_active, completion, completion_note
            FROM schedule_plans
            WHERE id=?
        ''', (event_id,))
        r = c.fetchone()
        if not r:
            return None
        return {
            "id": r[0], "date": r[1], "time_start": r[2], "time_end": r[3],
            "title": r[4], "notes": r[5], "category": r[6],
            "feishu_event_id": r[7], "last_synced_at": r[8], "is_active": r[9],
            "completion": r[10], "completion_note": r[11],
        }
    finally:
        conn.close()
