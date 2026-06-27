#!/usr/bin/env python3
"""
Database module for Daily Recorder - 多 DB 滚动存储版本

架构：
  .db/
    daily_recorder_meta.db    ← scan_checkpoint + 分库序号（永不滚动，极小）
    daily_recorder.db         ← 数据文件1（序号0，当前活跃）
    daily_recorder_001.db     ← 数据文件2（序号1，超限后新建）
    daily_recorder_002.db     ← 数据文件3（序号2）
    ...

去重机制：
  - (content, timestamp) 全局唯一约束，跨 DB 也生效
  - 同一消息不论落在哪个分库，都只会入库一次

文件滚动策略（方案B）：
  - 写入前检查当前活跃 DB 文件大小
  - 若 >= 50MB，本次写入当前文件，下一次写入时自动创建新文件
  - 新文件序号 = max(已有序号) + 1
"""

import sqlite3
import os
import time
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "daily_recorder.db"
META_FILENAME = "daily_recorder_meta.db"
MAX_SIZE_MB = 50  # GitHub 100MB 上限的安全阈值


def _find_db_dir(skill_dir) -> Path:
    """查找 .db 目录：环境变量 > 父目录层层找 > 技能目录 fallback"""
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        db_dir = Path(env_path)
        db_dir.mkdir(parents=True, exist_ok=True)
        return db_dir

    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return db_dir

    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(parents=True, exist_ok=True)
    return default_db_dir


def _seq_to_filename(seq: int) -> str:
    """序号转数据文件名：seq=0 → daily_recorder.db，seq=1 → daily_recorder_001.db"""
    if seq == 0:
        return "daily_recorder.db"
    return f"daily_recorder_{seq:03d}.db"


def _filename_to_seq(filename: str) -> int | None:
    """数据文件名转序号：daily_recorder.db → 0，daily_recorder_001.db → 1"""
    if filename == "daily_recorder.db":
        return 0
    if filename.startswith("daily_recorder_") and filename.endswith(".db"):
        try:
            return int(filename[len("daily_recorder_"):-3])
        except ValueError:
            pass
    return None


# ── DBManager ─────────────────────────────────────────────────────────────────

class DBManager:
    """
    多 DB 滚动存储管理器。

    封装所有复杂度，对 record.py / query.py 保持原有调用接口不变。
    """

    def __init__(self, db_dir: Path = None, max_size_mb: int = MAX_SIZE_MB):
        if db_dir is None:
            db_dir = _find_db_dir(SKILL_DIR)
        self._db_dir = Path(db_dir)
        self._meta_path = self._db_dir / META_FILENAME
        self._max_size_mb = max_size_mb
        self._current_seq = None  # 延迟初始化

        # 确保目录存在
        self._db_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 meta.db（如果不存在）
        self._init_meta_db()

        # 迁移：扫描目录，把现有数据文件注册到 db_registry
        # （兼容旧版只有一个 daily_recorder.db 的情况）
        self._migrate_existing_files()

    def get_registry_info(self) -> list[dict]:
        """
        返回所有数据文件的注册信息（含序号、大小、是否活跃）。
        供 status.py / query.py 展示。
        """
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("""
            SELECT seq, filename, file_path, size_mb, is_active, created_at
            FROM db_registry ORDER BY seq ASC
        """)
        rows = cur.fetchall()
        conn.close()

        result = []
        for row in rows:
            path = Path(row[2])
            size_mb = self._file_size_mb(path) if path.exists() else row[3]
            result.append({
                "seq": row[0],
                "filename": row[1],
                "file_path": str(path),
                "size_mb": round(size_mb, 2),
                "is_active": bool(row[4]),
                "created_at": row[5],
            })
        return result

    def refresh_registry_sizes(self):
        """更新 db_registry 中各文件的当前大小"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("SELECT seq, file_path FROM db_registry")
        rows = cur.fetchall()
        conn.close()
        for seq, file_path in rows:
            size_mb = self._file_size_mb(Path(file_path))
            conn2 = sqlite3.connect(str(self._meta_path))
            cur2 = conn2.cursor()
            cur2.execute("UPDATE db_registry SET size_mb = ? WHERE seq = ?", (size_mb, seq))
            conn2.commit()
            conn2.close()

    # ── Checkpoint（读写 meta.db）────────────────────────────────────────────

    def _migrate_existing_files(self):
        """
        扫描 .db 目录，把尚未注册到 db_registry 的数据文件补录进去。
        兼容旧版只有 daily_recorder.db 的情况。
        如果 db_registry 已经有记录，说明已迁移过，跳过。
        """
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM db_registry")
        count = cur.fetchone()[0]
        conn.close()

        if count > 0:
            return  # 已经迁移过，跳过

        # 扫描目录，找所有数据文件并注册
        data_files = []
        for f in self._db_dir.iterdir():
            if f.suffix == ".db" and f.name.startswith("daily_recorder") and f.name != META_FILENAME:
                seq = _filename_to_seq(f.name)
                if seq is not None:
                    data_files.append((seq, f))

        if not data_files:
            # 完全没有数据文件，初始化第一个（daily_recorder.db，seq=0）
            seq = 0
            data_path = self._db_dir / _seq_to_filename(seq)
            self._init_data_db(data_path)
            self._register_data_file(data_path, seq, is_active=True)
            self._current_seq = 0
            return

        # 按序号排，最大序号的设为活跃
        data_files.sort(key=lambda x: x[0])
        for seq, f in data_files:
            is_active = (seq == data_files[-1][0])
            self._register_data_file(f, seq, is_active=is_active)

        self._current_seq = data_files[-1][0]

    def _list_data_files(self) -> list[Path]:
        """返回所有数据文件路径，按序号排序（来自 db_registry）"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("SELECT seq, file_path FROM db_registry ORDER BY seq ASC")
        rows = cur.fetchall()
        conn.close()
        return [Path(row[1]) for row in rows]

    def _active_data_file(self) -> Path:
        """返回当前活跃数据文件路径（来自 db_registry）"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("SELECT seq, file_path FROM db_registry WHERE is_active = 1")
        row = cur.fetchone()
        conn.close()

        if row:
            self._current_seq = row[0]
            return Path(row[1])

        # 完全没有注册过，初始化第一个
        seq = 0
        data_path = self._db_dir / _seq_to_filename(seq)
        self._init_data_db(data_path)
        self._register_data_file(data_path, seq, is_active=True)
        self._current_seq = seq
        return data_path

    def _file_size_mb(self, path: Path) -> float:
        """返回文件大小（MB）"""
        if not path.exists():
            return 0.0
        return path.stat().st_size / (1024 * 1024)

    def _ensure_capacity(self):
        """
        检查当前活跃文件是否已满（>= MAX_SIZE_MB）。
        如果已满，下次写入时会创建新文件。
        方案B：本次写入当前文件，下一次写入时检测到超限则自动创建新文件。
        """
        active = self._active_data_file()
        size_mb = self._file_size_mb(active)
        if size_mb >= self._max_size_mb:
            # 当前文件已满，创建新文件
            next_seq = self._current_seq + 1
            new_path = self._db_dir / _seq_to_filename(next_seq)
            self._init_data_db(new_path)
            self._register_data_file(new_path, next_seq, is_active=True)
            self._update_active_file(next_seq)

    # ── Schema 初始化 ───────────────────────────────────────────────────────

    def _init_meta_db(self):
        """初始化 meta.db"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        # 文件注册表：记录所有数据分库文件
        # active_file 字段直接标识当前活跃文件，无需再靠 current_seq 推断
        cur.execute("""
            CREATE TABLE IF NOT EXISTS db_registry (
                seq          INTEGER PRIMARY KEY,
                filename     VARCHAR(100) NOT NULL,
                file_path    VARCHAR(500) NOT NULL,
                size_mb      REAL DEFAULT 0,
                is_active    INTEGER DEFAULT 0,
                created_at   INTEGER NOT NULL
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
        conn.commit()
        conn.close()

    def _register_data_file(self, data_path: Path, seq: int, is_active: bool = False):
        """将新数据文件注册到 meta.db 的 db_registry 表"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO db_registry (seq, filename, file_path, is_active, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (seq, data_path.name, str(data_path), 1 if is_active else 0, int(time.time())))
        conn.commit()
        conn.close()

    def _update_active_file(self, seq: int):
        """将指定序号设为活跃文件（取消其他活跃状态）"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("UPDATE db_registry SET is_active = 0")
        cur.execute("UPDATE db_registry SET is_active = 1 WHERE seq = ?", (seq,))
        conn.commit()
        conn.close()
        self._current_seq = seq

    def _init_data_db(self, data_path: Path):
        """初始化一个数据 DB 文件（创建表结构）"""
        conn = sqlite3.connect(str(data_path))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id      VARCHAR(255),
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
        # (content, timestamp) 全局唯一约束：同一消息不会跨 DB 重复录入
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_um_content_ts ON user_messages(content, timestamp)")
        # (message_id) 部分唯一索引（2026-06-27 新增）：
        #   - 配合 record.py fallback 简化（不再带 session_file 名），跨文件去重稳
        #   - 部分索引 WHERE：空 message_id 不参与唯一约束（允许多条 fallback 消息共存）
        #   - 配合 INSERT OR IGNORE，同消息跨文件重复扫描时直接跳过
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_um_msg_id_unique ON user_messages(message_id) WHERE message_id IS NOT NULL AND message_id != ''")
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_um_date ON user_messages(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_um_timestamp ON user_messages(timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ua_date ON user_attachments(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ua_timestamp ON user_attachments(timestamp)")
        conn.commit()
        conn.close()

    # ── Checkpoint（读写 meta.db）────────────────────────────────────────────

    def get_checkpoint(self, session_file: str) -> dict | None:
        """读取指定 session 的 checkpoint（来自 meta.db）"""
        # 优先使用已有 checkpoint 事务的连接
        if hasattr(self, '_meta_conn') and self._meta_conn is not None:
            self._meta_cur.execute("""
                SELECT last_timestamp, last_message_id
                FROM scan_checkpoint WHERE session_file = ?
            """, (session_file,))
            row = self._meta_cur.fetchone()
            if row:
                return {"last_timestamp": row[0], "last_message_id": row[1]}
            return None

        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT last_timestamp, last_message_id
                FROM scan_checkpoint WHERE session_file = ?
            """, (session_file,))
            row = cur.fetchone()
        finally:
            conn.close()
        if row:
            return {"last_timestamp": row[0], "last_message_id": row[1]}
        return None

    def checkpoint_progress(self, session_file: str, last_timestamp: int, last_message_id: str):
        """扫描循环中逐条调用，实时更新 checkpoint（必须在 begin_checkpoint_transaction 之后）"""
        self._meta_cur.execute("""
            INSERT OR REPLACE INTO scan_checkpoint
            (session_file, last_timestamp, last_message_id, updated_at)
            VALUES (?, ?, ?, ?)
        """, (session_file, last_timestamp, last_message_id, int(time.time())))
        if self._commit_counter >= 49:
            self._meta_conn.commit()
            self._commit_counter = 0
        else:
            self._commit_counter += 1

    def checkpoint_finalize(self, session_file: str, last_timestamp: int, last_message_id: str):
        """扫描完一个文件后调用，兜底更新 checkpoint（优先复用事务连接）"""
        if hasattr(self, '_meta_conn') and self._meta_conn is not None:
            self._meta_cur.execute("""
                INSERT OR REPLACE INTO scan_checkpoint
                (session_file, last_timestamp, last_message_id, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_file, last_timestamp, last_message_id, int(time.time())))
            self._meta_conn.commit()
            return

        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR REPLACE INTO scan_checkpoint
                (session_file, last_timestamp, last_message_id, updated_at)
                VALUES (?, ?, ?, ?)
            """, (session_file, last_timestamp, last_message_id, int(time.time())))
            conn.commit()
        finally:
            conn.close()

    def begin_checkpoint_transaction(self):
        """开启 meta.db 的 checkpoint 事务"""
        self._meta_conn = sqlite3.connect(str(self._meta_path), timeout=30)
        self._meta_conn.execute("PRAGMA journal_mode=WAL")
        self._meta_cur = self._meta_conn.cursor()
        self._commit_counter = 0

    def preload_checkpoints(self) -> dict:
        """一次性预加载所有 checkpoint（来自 meta.db）"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("SELECT session_file, last_timestamp, last_message_id FROM scan_checkpoint")
        result = {row[0]: {'last_timestamp': row[1], 'last_message_id': row[2]} for row in cur.fetchall()}
        conn.close()
        return result

    def end_checkpoint_transaction(self):
        """提交并关闭 checkpoint 事务"""
        if self._meta_conn:
            self._meta_conn.commit()
            self._meta_conn.close()
            self._meta_conn = None
            self._meta_cur = None

    def clear_all_checkpoints(self):
        """清空所有 checkpoint（用于全量重扫）"""
        conn = sqlite3.connect(str(self._meta_path))
        cur = conn.cursor()
        cur.execute("DELETE FROM scan_checkpoint")
        conn.commit()
        conn.close()

    # ── 写入（自动路由到当前活跃分库）──────────────────────────────────────

    def insert_message(self, msg: dict):
        """写入一条用户消息到当前活跃数据文件，超限时自动滚动"""
        self._ensure_capacity()
        active = self._active_data_file()

        conn = sqlite3.connect(str(active))
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
        except sqlite3.IntegrityError:
            # 极端 race condition 兜底（2026-06-27 新增）：
            #   理论上 INSERT OR IGNORE 已处理唯一约束冲突，但为了双重保险捕获
            pass
        finally:
            conn.close()

    def insert_attachment(self, att: dict):
        """写入一条附件记录到当前活跃数据文件，超限时自动滚动"""
        self._ensure_capacity()
        active = self._active_data_file()

        conn = sqlite3.connect(str(active))
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
            conn.close()

    # ── 查询（遍历所有分库，合并结果）────────────────────────────────────────

    def _all_data_files(self) -> list[Path]:
        """返回所有数据文件路径（含超限后新建的）"""
        return self._list_data_files()

    def query(self, start_ts: int = None, end_ts: int = None, date: str = None,
              channel: str = None, sender_id: str = None, limit: int = 1000):
        """
        按条件查询消息，遍历所有分库合并结果。
        返回 (message_id, timestamp, channel, sender_id, content, has_attachment, date)
        """
        all_files = self._all_data_files()
        results = []

        for data_path in all_files:
            conn = sqlite3.connect(str(data_path))
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
            if channel:
                conditions.append("channel = ?")
                params.append(channel)
            if sender_id:
                conditions.append("sender_id = ?")
                params.append(sender_id)

            where = " AND ".join(conditions) if conditions else "1=1"
            cur.execute(f"""
                SELECT message_id, timestamp, channel, sender_id, content, has_attachment, date
                FROM user_messages
                WHERE {where}
                ORDER BY timestamp ASC
            """, params)

            rows = cur.fetchall()
            conn.close()
            results.extend(rows)

        # 全局排序 + limit
        results.sort(key=lambda r: r[1])  # 按 timestamp 升序
        return results[:limit]

    def query_attachments(self, start_ts: int = None, end_ts: int = None, date: str = None,
                          channel: str = None, file_type: str = None, limit: int = 1000):
        """按条件查询附件，遍历所有分库合并结果"""
        all_files = self._all_data_files()
        results = []

        for data_path in all_files:
            conn = sqlite3.connect(str(data_path))
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
            if channel:
                conditions.append("channel = ?")
                params.append(channel)
            if file_type:
                conditions.append("file_type LIKE ?")
                params.append(f"{file_type}%")

            where = " AND ".join(conditions) if conditions else "1=1"
            cur.execute(f"""
                SELECT message_id, timestamp, channel, sender_id, file_path, file_type, date
                FROM user_attachments
                WHERE {where}
                ORDER BY timestamp ASC
            """, params)

            rows = cur.fetchall()
            conn.close()
            results.extend(rows)

        results.sort(key=lambda r: r[1])
        return results[:limit]

    def query_recent(self, limit: int = 50, channel: str = None, sender_id: str = None):
        """查询最近 N 条消息，遍历所有分库合并后按最新时间倒序"""
        all_files = self._all_data_files()
        results = []

        for data_path in all_files:
            conn = sqlite3.connect(str(data_path))
            cur = conn.cursor()

            conditions = []
            params = []
            if channel:
                conditions.append("channel = ?")
                params.append(channel)
            if sender_id:
                conditions.append("sender_id = ?")
                params.append(sender_id)

            where = " AND ".join(conditions) if conditions else "1=1"
            cur.execute(f"""
                SELECT message_id, timestamp, channel, sender_id, content, has_attachment, date
                FROM user_messages
                WHERE {where}
                ORDER BY timestamp DESC
                LIMIT ?
            """, (*params, limit))

            rows = cur.fetchall()
            conn.close()
            results.extend(rows)

        # 全局倒序取最新
        results.sort(key=lambda r: r[1], reverse=True)
        return results[:limit]

    # ── 兼容性别名 ──────────────────────────────────────────────────────────

    @property
    def db_path(self) -> Path:
        """兼容旧接口，返回当前活跃数据文件路径"""
        return self._active_data_file()


# ── 向后兼容：Database 类（record.py 仍在用）──────────────────────────────────

class Database(DBManager):
    """向后兼容 wrapper，record.py 的旧接口继续能用"""

    def __init__(self, db_path=None, max_size_mb=MAX_SIZE_MB):
        if db_path is not None:
            # 旧接口可能传入 db_path，但新架构忽略此参数
            db_path = Path(db_path) if db_path else None
            db_dir = db_path.parent if db_path else None
        else:
            db_dir = None
        super().__init__(db_dir=db_dir, max_size_mb=max_size_mb)
