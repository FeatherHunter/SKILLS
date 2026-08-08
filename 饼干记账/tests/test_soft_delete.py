"""软删字段测试(G7 决议 A 项 · 软删契约 · #201 前置块)

覆盖:schema 含 deleted_at / 查询默认排除 / include_deleted / undo/restore / 重复操作错误 / 迁移幂等
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def seeded(tmp_db_dir):
    """初始化 db + 插入 2 条记录"""
    from db import init_db, TABLE_NAME
    conn = init_db()
    cur = conn.cursor()
    for i, amt in enumerate([-35.0, -20.0]):
        cur.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
            "VALUES (?, ?, ?, ?)",
            ("餐饮", f"2026-08-0{i+1} 12:00:00", amt, f"记录{i+1}"),
        )
    conn.commit()
    conn.close()
    return tmp_db_dir


class TestSchema:
    def test_deleted_at_column_exists(self, seeded):
        from db import init_db, TABLE_NAME
        conn = init_db()
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()]
        conn.close()
        assert "deleted_at" in cols

    def test_new_records_default_null(self, seeded):
        from db import fetch_all
        rows = fetch_all(include_deleted=True)
        assert all(r["deleted_at"] is None for r in rows)


class TestQueryFilter:
    def test_default_excludes_deleted(self, seeded):
        """撤销后默认查询不可见"""
        from db import fetch_all, undo_bill
        rows = fetch_all()
        assert len(rows) == 2
        undo_bill(rows[0]["id"])
        assert len(fetch_all()) == 1

    def test_include_deleted_shows_all(self, seeded):
        from db import fetch_all, undo_bill
        rows = fetch_all()
        undo_bill(rows[0]["id"])
        assert len(fetch_all(include_deleted=True)) == 2

    def test_get_by_id_excludes_deleted(self, seeded):
        from db import fetch_all, get_by_id, undo_bill
        rows = fetch_all()
        undo_bill(rows[0]["id"])
        assert get_by_id(rows[0]["id"]) is None
        assert get_by_id(rows[0]["id"], include_deleted=True) is not None


class TestUndoRestore:
    def test_undo_sets_timestamp(self, seeded):
        from db import fetch_all, undo_bill
        rid = fetch_all()[0]["id"]
        r = undo_bill(rid)
        assert r["success"] and r["action"] == "undo"
        assert r["deleted_at"] is not None
        row = fetch_all(include_deleted=True)[0]
        assert row["deleted_at"] is not None

    def test_restore_clears_timestamp(self, seeded):
        from db import fetch_all, undo_bill, restore_bill
        rid = fetch_all()[0]["id"]
        undo_bill(rid)
        r = restore_bill(rid)
        assert r["success"] and r["action"] == "restore"
        assert r["deleted_at"] is None
        assert len(fetch_all()) == 2

    def test_double_undo_fails(self, seeded):
        from db import fetch_all, undo_bill
        rid = fetch_all()[0]["id"]
        undo_bill(rid)
        r2 = undo_bill(rid)
        assert not r2["success"] and "已撤销" in r2["error"]

    def test_restore_not_deleted_fails(self, seeded):
        from db import fetch_all, restore_bill
        rid = fetch_all()[0]["id"]
        r = restore_bill(rid)
        assert not r["success"] and "未撤销" in r["error"]


class TestMigration:
    def test_existing_db_gets_column(self, tmp_db_dir, monkeypatch):
        """已有库(无 deleted_at 列)init_db 幂等补列"""
        import sys
        # 先建一个旧 schema 库
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        conn.execute(
            "CREATE TABLE bills (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, "
            "time TEXT NOT NULL, amount REAL NOT NULL, account TEXT DEFAULT '', "
            "ledger TEXT DEFAULT '生活', currency TEXT DEFAULT '人民币', "
            "note TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        conn.execute("INSERT INTO bills (category, time, amount) VALUES ('餐饮', '2026-08-01 12:00:00', -10.0)")
        conn.commit()
        conn.close()

        # 重新 import db(清缓存,SKILLS_DB_PATH 指向 tmp)
        import sys as _sys
        for mod in ("db",):
            if mod in _sys.modules:
                del _sys.modules[mod]
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_db_dir))
        from db import init_db, fetch_all, TABLE_NAME
        conn = init_db()
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({TABLE_NAME})").fetchall()]
        conn.close()
        assert "deleted_at" in cols
        # 旧数据未删(可见)
        assert len(fetch_all()) == 1
