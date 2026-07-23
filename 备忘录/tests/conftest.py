"""
备忘录 tests 共用 fixture
- 把 script/ 加入 sys.path,让 memo_cli / memo_render / feishu_sync 可 import
- 提供临时数据库 fixture(用 :memory: + 复制 schema)
"""
import sys
from pathlib import Path
import pytest

SKILL_DIR = Path(__file__).parent.parent
SCRIPT_DIR = SKILL_DIR / "script"
sys.path.insert(0, str(SCRIPT_DIR))


@pytest.fixture
def in_memory_db(monkeypatch):
    """用 :memory: 临时库替换默认 DB_PATH,跑完即弃。
    跑前自动执行 init.sql 建表,FTS5 触发器等。
    """
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript((SCRIPT_DIR / "init.sql").read_text(encoding="utf-8"))
    # init.sql 第 1 行是 PRAGMA,在 :memory: 模式下允许
    conn.commit()

    # 把 memo_cli.get_conn 替换为返回 :memory: 连接
    def fake_get_conn():
        c = sqlite3.connect(":memory:")
        c.row_factory = sqlite3.Row
        c.executescript((SCRIPT_DIR / "init.sql").read_text(encoding="utf-8"))
        return c

    from memo_cli import get_conn as real_get_conn
    monkeypatch.setattr("memo_cli.get_conn", fake_get_conn)
    yield conn
    conn.close()