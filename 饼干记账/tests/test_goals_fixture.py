"""goals.json fixture 测试(T0 #164 第 8 项 · 目标域载体)

覆盖:路径约定(与 db 同级)/ 读写 helper / 备份包含 goals.json
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from db import DB_FILENAME


class TestGoalsFixture:
    def test_goals_file_follows_db_dir(self, tmp_db_dir, goals_file):
        """goals.json 与 db 同级(跟随 SKILLS_DB_PATH)"""
        assert goals_file == tmp_db_dir / "goals.json"
        assert goals_file.parent == tmp_db_dir

    def test_goals_rw_roundtrip(self, goals_rw):
        """读写 helper:save → load 一致;不存在时 load 返回空 dict"""
        load, save = goals_rw
        assert load() == {}
        save({"budgets": [{"month": "2026-08", "amount": 3000}], "savings": []})
        assert load()["budgets"][0]["amount"] == 3000

    def test_goals_rw_atomic_write(self, goals_file, goals_rw):
        """原子写:临时文件 + replace,不留 .tmp 残留"""
        load, save = goals_rw
        save({"a": 1})
        assert not goals_file.with_suffix(".json.tmp").exists()

    def test_backup_includes_goals(self, tmp_db_dir, goals_file, monkeypatch):
        """备份机制包含 goals.json(与 backup.py 集成)"""
        import sys
        SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        for mod in ("db", "backup"):
            if mod in sys.modules:
                del sys.modules[mod]
        monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_db_dir))
        from db import init_db
        import backup as bk
        init_db()
        goals_file.write_text('{"budgets": []}', encoding="utf-8")
        target = bk.create_backup()
        assert (target / "goals.json").exists()
