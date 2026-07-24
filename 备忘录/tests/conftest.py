"""
备忘录 tests 共用 fixture
- 把 script/ 加入 sys.path,让 memo_cli / memo_render / feishu_sync 可 import
- 提供临时数据库 fixture(env_with_tmp_db: 用于 CLI 子进程隔离)
"""
import sys
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SCRIPT_DIR = SKILL_DIR / "script"
sys.path.insert(0, str(SCRIPT_DIR))


@pytest.fixture
def env_with_tmp_db(tmp_path):
    """用 tmp 目录建库,环境变量隔离不污染真实 D:/.db。
    适合需要 CLI 子进程的测试(test_payloads / test_wish_plan)。
    """
    db_dir = tmp_path
    db_path = db_dir / "memo.db"
    init_sql = (SCRIPT_DIR / "init.sql").read_text(encoding="utf-8")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript(init_sql)
    conn.commit()
    conn.close()
    env = {"SKILLS_DB_PATH": str(db_dir), "PATH": "/usr/bin:/bin"}
    return env


@pytest.fixture
def in_memory_db(monkeypatch):
    """用 :memory: 临时库替换默认 DB_PATH,跑完即弃(进程内测试用)。
    主要供 in-process memo_cli 函数直接调用时使用。
    """
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SCRIPT_DIR / "init.sql").read_text(encoding="utf-8"))
    conn.commit()

    def fake_get_conn():
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.executescript((SCRIPT_DIR / "init.sql").read_text(encoding="utf-8"))
        return c

    from memo_cli import get_conn as real_get_conn
    monkeypatch.setattr("memo_cli.get_conn", fake_get_conn)
    yield conn
    conn.close()