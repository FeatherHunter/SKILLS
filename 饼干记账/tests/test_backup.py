"""backup.py 备份机制测试(公共层 · T0 #164 第 9 项)

覆盖:create(db+goals.json)/ goals.json 缺失跳过 / list / restore(含恢复前自动备份)/ db 校验
"""

from __future__ import annotations

import sys
import sqlite3
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import backup as bk  # noqa: E402
from db import DB_FILENAME  # noqa: E402


@pytest.fixture
def tmp_env(tmp_path, monkeypatch):
    """临时数据目录:SKILLS_DB_PATH → tmp_path,清 db 缓存"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    for mod in ("db", "backup"):
        if mod in sys.modules:
            del sys.modules[mod]
    import backup  # noqa: F811
    return tmp_path


class TestBackup:
    def test_create_copies_db(self, tmp_env):
        from db import init_db
        init_db()
        target = bk.create_backup()
        assert target.is_dir()
        assert (target / DB_FILENAME).exists()

    def test_create_skips_missing_goals(self, tmp_env, capsys):
        from db import init_db
        init_db()
        bk.create_backup()
        out = capsys.readouterr().out
        assert "goals.json (不存在,跳过)" in out

    def test_create_includes_goals_when_present(self, tmp_env):
        from db import init_db
        init_db()
        (tmp_env / "goals.json").write_text('{"budgets":[]}', encoding="utf-8")
        target = bk.create_backup()
        assert (target / "goals.json").exists()

    def test_list_shows_backups(self, tmp_env, capsys):
        from db import init_db
        init_db()
        bk.create_backup()
        bk.create_backup()
        items = bk.list_backups()
        assert len(items) == 2
        out = capsys.readouterr().out
        assert "biscuit_accountant.db" in out

    def test_restore_restores_db(self, tmp_env):
        """改动 db 后 restore 还原"""
        from db import init_db, TABLE_NAME
        conn = init_db()
        conn.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
            "VALUES ('餐饮', '2026-08-01 12:00:00', -10.0, '测试')"
        )
        conn.commit()
        conn.close()
        bk.create_backup()  # 备份含 1 条

        # 再插入 1 条(污染)
        conn = sqlite3.connect(str(tmp_env / DB_FILENAME))
        conn.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
            "VALUES ('出行', '2026-08-02 12:00:00', -5.0, '污染')"
        )
        conn.commit()
        conn.close()

        # 找到最新备份并恢复
        items = bk.list_backups()
        name = items[0].name
        bk.restore_backup(name)

        # 恢复后应只有 1 条(备份时的数据)
        conn = sqlite3.connect(str(tmp_env / DB_FILENAME))
        n = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        conn.close()
        assert n == 1, f"恢复后应回到备份时 1 条,实际 {n}"

    def test_restore_creates_safety_backup(self, tmp_env, capsys):
        from db import init_db
        init_db()
        bk.create_backup()
        items = bk.list_backups()
        bk.restore_backup(items[0].name)
        out = capsys.readouterr().out
        assert "恢复前自动备份现状" in out

    def test_restore_missing_backup_fails(self, tmp_env):
        with pytest.raises(SystemExit):
            bk.restore_backup("不存在的备份")
