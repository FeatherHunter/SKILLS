"""pytest 配置 — 共享 fixture

添加 scripts/ 到 sys.path,让测试可 import schedule_db / validators / render 等.
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest


SCHEMA_SQL = """
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
        );
        CREATE TABLE IF NOT EXISTS daily_summary (
            date TEXT NOT NULL,
            category TEXT NOT NULL,
            total_minutes INTEGER DEFAULT 0,
            generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (date, category)
        );
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time_start TEXT NOT NULL,
            time_end TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            category TEXT,
            feishu_event_id TEXT,
            last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            completion TEXT DEFAULT NULL,
            completion_note TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """


@pytest.fixture(autouse=True)
def conn(monkeypatch, tmp_path):
    """每 case 一个 **tempfile SQLite DB**,monkeypatch schedule_db.get_connection
    让它返回每次新建的 conn(同一 file,数据跨连接持久)。

    为什么不用 in-memory:sqlite3.Connection 是 immutable C type,close() 不可
    patch;而 schedule_db 函数 finally 会 close()。in-memory conn 关闭后失效,
    且新 in-memory conn 是空白 DB → 数据丢失。改用 tempfile 文件 DB,close
    后文件仍在,新 conn 连同一 file 数据仍在。
    """
    import sqlite3
    import schedule_db as _db

    db_path = tmp_path / "test_schedule.db"
    # 初始建表
    init = sqlite3.connect(str(db_path))
    init.row_factory = sqlite3.Row
    init.executescript(SCHEMA_SQL)
    init.commit()
    init.close()

    def _factory():
        new = sqlite3.connect(str(db_path))
        new.row_factory = sqlite3.Row
        return new

    monkeypatch.setattr(_db, "get_connection", _factory)
    # 跳过飞书同步(测试不需要,且可能 hang 网络)
    monkeypatch.setattr(_db, "_sync_one_feishu", lambda *args, **kwargs: None)
    yield None


@pytest.fixture
def today_str():
    """固定日期 2026-07-15 避免测试用例依赖时间"""
    return "2026-07-15"
