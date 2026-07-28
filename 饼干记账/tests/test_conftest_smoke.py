"""conftest smoke test — 证明 pytest + conftest fixture 都能正常工作。

跑 `python -m pytest tests/test_conftest_smoke.py` 退出码 0 即地基可用。
后续 test_validators / test_render / test_payloads 都依赖 conftest。
"""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def test_conftest_fixtures_exist(tmp_db_dir, empty_db, html_dir):
    """3 个核心 fixture 都返回有效 Path 且指向同一个 tmp 根。"""
    assert tmp_db_dir.exists()
    assert empty_db == tmp_db_dir
    assert html_dir.exists()
    assert html_dir.parent == tmp_db_dir
    assert html_dir.name == "biscuit_accountant_html"


def test_seeded_db_loads_30_records(seeded_db):
    """seeded_db fixture 注入 30 条样本记录"""
    import sqlite3
    from db import DB_PATH, TABLE_NAME
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        n = cur.fetchone()[0]
    finally:
        conn.close()
    assert n == 30


def test_run_cli_wrapper_works(run_cli):
    """run_cli wrapper 能跑 record_bill.py stats --json"""
    rc, out, err = run_cli(["record_bill.py", "stats", "--json"])
    assert rc == 0, f"rc={rc} err={err}"
    import json
    data = json.loads(out)
    assert data["status"] == "ok"
    assert data["data"]["total_records"] == 0  # empty DB by default (tmp_db_dir)


def test_parse_cli_json_wrapper(parse_cli_json):
    """parse_cli_json wrapper 能解析 record_bill.py summary"""
    data = parse_cli_json(["summary"])
    assert data["status"] == "ok"
    assert "date" in data["data"]
    assert "count" in data["data"]
