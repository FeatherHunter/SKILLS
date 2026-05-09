#!/usr/bin/env python3
"""
Database module for Daily Recorder
"""

import sqlite3
import time
from pathlib import Path


class Database:
    def __init__(self, db_path):
        if isinstance(db_path, str):
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
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
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
        conn.close()

    def insert_attachment(self, att: dict):
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
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
        conn.close()

    def get_checkpoint(self, session_file: str) -> dict | None:
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("""
            SELECT last_timestamp, last_message_id
            FROM scan_checkpoint WHERE session_file = ?
        """, (session_file,))
        row = cur.fetchone()
        conn.close()
        if row:
            return {"last_timestamp": row[0], "last_message_id": row[1]}
        return None

    def upsert_checkpoint(self, session_file: str, last_timestamp: int, last_message_id: str):
        conn = sqlite3.connect(str(self.db_path))
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO scan_checkpoint
            (session_file, last_timestamp, last_message_id, updated_at)
            VALUES (?, ?, ?, ?)
        """, (session_file, last_timestamp, last_message_id, int(time.time())))
        conn.commit()
        conn.close()

    def query(self, start_ts: int = None, end_ts: int = None, date: str = None, limit: int = 1000):
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