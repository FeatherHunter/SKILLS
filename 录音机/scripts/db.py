#!/usr/bin/env python3
"""
Database module for Daily Recorder
"""

import sqlite3
import os
import time
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "daily_recorder.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 父目录 > 技能目录"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        return Path(env_path) / db_filename
    # 2. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return db_dir / db_filename
    # 3. 技能目录下 .db 子目录（默认 fallback）
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


class Database:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = DB_PATH
        elif isinstance(db_path, str):
            db_path = Path(db_path)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id      VARCHAR(255) UNIQUE NOT NULL,
                session_file    VARCHAR(500) NOT NULL,
                timestamp       INTEGER NOT NULL,
                channel         VARCHAR(50),
                sender_id       VARCHAR(255),
                content         TEXT NOT NULL,
                date            VARCHAR(8) NOT NULL,
                has_attachment  INTEGER DEFAULT 0,
                created_at      INTEGER NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_attachments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id      VARCHAR(255),
                session_file    VARCHAR(500),
                timestamp       INTEGER NOT NULL,
                date            VARCHAR(8),
                channel         VARCHAR(50),
                sender_id       VARCHAR(255),
                file_path       TEXT NOT NULL,
                file_type       VARCHAR(50),
                created_at      INTEGER NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scan_checkpoint (
                session_file    VARCHAR(500) PRIMARY KEY,
                last_timestamp  INTEGER NOT NULL,
                last_message_id VARCHAR(255) NOT NULL,
                updated_at      INTEGER NOT NULL
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_um_date ON user_messages(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_um_timestamp ON user_messages(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ua_date ON user_attachments(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ua_timestamp ON user_attachments(timestamp)")
        conn.commit()
        conn.close()

    def insert_message(self, msg: dict):
        _conn = getattr(self, '_conn', None)
        conn = _conn if _conn is not None else sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO user_messages
                (message_id, session_file, timestamp, channel, sender_id, content, date, has_attachment, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg.get("message_id", ""),
                msg.get("session_file", ""),
                msg["timestamp"],
                msg.get("channel", ""),
                msg.get("sender_id", ""),
                msg["content"],
                msg["date"],
                msg.get("has_attachment", 0),
                int(time.time()),
            ))
            conn.commit()
        finally:
            if conn is not _conn:
                conn.close()

    def insert_attachment(self, att: dict):
        _conn = getattr(self, '_conn', None)
        conn = _conn if _conn is not None else sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO user_attachments
                (message_id, session_file, timestamp, channel, sender_id, file_path, file_type, date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                att.get("message_id", ""),
                att.get("session_file", ""),
                att["timestamp"],
                att.get("channel", ""),
                att.get("sender_id", ""),
                att["file_path"],
                att.get("file_type", ""),
                att.get("date", ""),
                int(time.time()),
            ))
            conn.commit()
        finally:
            if conn is not _conn:
                conn.close()

    def get_checkpoint(self, session_file: str) -> dict | None:
        _conn = getattr(self, '_conn', None)
        conn = _conn if _conn is not None else sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT last_timestamp, last_message_id
                FROM scan_checkpoint WHERE session_file = ?
            """, (session_file,))
            row = cur.fetchone()
        finally:
            if conn is not _conn:
                conn.close()
        if row:
            return {"last_timestamp": row[0], "last_message_id": row[1]}
        return None

    def checkpoint_finalize(self, session_file: str, last_timestamp: int, last_message_id: str):
        """扫描完一个文件后调用，兜底更新 checkpoint（独立连接，可脱离事务使用）"""
        _conn = getattr(self, '_conn', None)
        conn = _conn if _conn is not None else sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR REPLACE INTO scan_checkpoint
                (session_file, last_timestamp, last_message_id, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_file, last_timestamp, last_message_id, int(time.time())))
            conn.commit()
        finally:
            if conn is not _conn:
                conn.close()

    def checkpoint_progress(self, session_file: str, last_timestamp: int, last_message_id: str):
        """扫描循环中逐条调用，实时更新 checkpoint（必须在 begin_checkpoint_transaction 之后）"""
        self._cur.execute("""
            INSERT OR REPLACE INTO scan_checkpoint
            (session_file, last_timestamp, last_message_id, updated_at)
            VALUES (?, ?, ?, ?)
        """, (session_file, last_timestamp, last_message_id, int(time.time())))
        # 【优化】只每 50 条消息 commit 一次，避免 9P 往返开销
        if self._commit_counter >= 50:
            self._conn.commit()
            self._commit_counter = 0
        else:
            self._commit_counter += 1

    def begin_checkpoint_transaction(self):
        """开启 checkpoint 事务（搭配 checkpoint_progress 和 end_checkpoint_transaction 使用）"""
        self._conn = sqlite3.connect(str(self.db_path), timeout=30)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._cur = self._conn.cursor()
        self._commit_counter = 0

    def preload_checkpoints(self) -> dict:
        """一次性预加载所有 checkpoint，避免逐文件查询（每次查询都走 9P 协议到 /mnt/d）"""
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("SELECT session_file, last_timestamp, last_message_id FROM scan_checkpoint")
        result = {row[0]: {'last_timestamp': row[1], 'last_message_id': row[2]} for row in cur.fetchall()}
        conn.close()
        return result

    def end_checkpoint_transaction(self):
        """提交并关闭 checkpoint 事务"""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            self._cur = None

    def query(selfself, start_ts: int = None, end_ts: int = None, date: str = None, limit: int = 1000):
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        conditions = []
        params = []

        if start_ts is not None:
            conditions.append("timestamp >= ?")
            params.append(start_ts)
        if end_ts is not None:
            conditions.append("timestamp <= ?")
            params.append(end_ts)
        if date:
            conditions.append("date = ?")
            params.append(date)

        where = " AND ".join(conditions) if conditions else "1=1"

        cur.execute(f"""
            SELECT message_id, timestamp, channel, sender_id, content, has_attachment, date
            FROM user_messages
            WHERE {where}
            ORDER BY timestamp ASC
            LIMIT ?
        """, (*params, limit))

        rows = cur.fetchall()
        conn.close()
        return rows

    def query_attachments(self, start_ts: int = None, end_ts: int = None, date: str = None, limit: int = 1000):
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()

        conditions = []
        params = []

        if start_ts is not None:
            conditions.append("timestamp >= ?")
            params.append(start_ts)
        if end_ts is not None:
            conditions.append("timestamp <= ?")
            params.append(end_ts)
        if date:
            conditions.append("date = ?")
            params.append(date)

        where = " AND ".join(conditions) if conditions else "1=1"

        cur.execute(f"""
            SELECT message_id, timestamp, channel, sender_id, file_path, file_type, date
            FROM user_attachments
            WHERE {where}
            ORDER BY timestamp ASC
            LIMIT ?
        """, (*params, limit))

        rows = cur.fetchall()
        conn.close()
        return rows

    def query_recent(self, limit: int = 50):
        """查询最近 N 条消息（按最新时间倒序）"""
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("""
            SELECT message_id, timestamp, channel, sender_id, content, has_attachment, date
            FROM user_messages
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return rows