"""SM5 快递购物域测试(fixture 临时库 · 不碰生产库)

覆盖场景: 购物清单(添加/查重/销项/例行到期)/ 缺货检测(阈值/默认/建议量/进清单)/
          快递跟踪(快递中/等待天数/超时/收货确认)/ 囤货盘点(阈值设置/库存状态/修正)
seam: scripts/快递购物/ops.py 公共函数(注入 conn)
e2e: 每场景 ≥1 次 CLI 端到端(临时库 + 临时输出目录)
"""
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from 快递购物 import ops, schema

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
CLI = SCRIPTS_DIR / "快递购物" / "cli.py"


# ── fixture: 临时库(最小 items/item_locations + 域表)──────────────────────


@pytest.fixture
def ex_db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "test_express.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            photo TEXT,
            access_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE item_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            location_status TEXT DEFAULT '在家',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL
        )
    """)
    schema.ensure_tables(conn)
    from 物品 import events as item_events
    item_events.ensure_tables(conn)
    conn.commit()
    yield conn
    conn.close()


def _seed_item(conn, name="牛奶", category_id=None, qty=0, status="在家",
               created_at=None, access_count=0):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO items (name, category_id, access_count) VALUES (?, ?, ?)",
        (name, category_id, access_count))
    item_id = cur.lastrowid
    cur.execute(
        "INSERT INTO item_locations (item_id, location, quantity, location_status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, "厨房/储物柜", qty, status, created_at, created_at))
    conn.commit()
    return item_id


def _seed_category(conn, name):
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


# ── 购物清单 ──────────────────────────────────────────────────────────────


def test_list_add_creates_pending_item(ex_db):
    iid = ops.list_add(ex_db, "牛奶", quantity=2)
    row = ex_db.execute("SELECT * FROM shopping_items WHERE id = ?", (iid,)).fetchone()
    assert row["name"] == "牛奶"
    assert row["quantity"] == 2
    assert row["source"] == "手动"
    assert row["status"] == "待买"


def test_list_add_dup_pending_rejected(ex_db):
    ops.list_add(ex_db, "牛奶")
    with pytest.raises(ValueError, match="已在购物清单中"):
        ops.list_add(ex_db, "牛奶")


def test_list_add_same_name_done_allowed(ex_db):
    iid = ops.list_add(ex_db, "牛奶")
    with pytest.raises(ValueError, match="已在购物清单中"):
        ops.list_add(ex_db, "牛奶")
    ops.list_check(ex_db, [iid])
    iid2 = ops.list_add(ex_db, "牛奶")  # 已买后同名可再加
    assert iid2 > iid


def test_list_add_routine_validation(ex_db):
    with pytest.raises(ValueError, match="例行周期"):
        ops.list_add(ex_db, "牛奶", routine="每天")
    ops.list_add(ex_db, "牛奶", routine="每周")


def test_list_view_groups_dupes(ex_db):
    ops.list_add(ex_db, "牛奶")
    ops.list_add(ex_db, "面包")
    # 直接 SQL 构造重复(绕过 add 时查重;模拟历史脏数据/并发写入)
    cur = ex_db.cursor()
    cur.execute(
        "INSERT INTO shopping_items (name, quantity, source, status, note, created_at, updated_at) "
        "VALUES ('牛奶', 1, '缺货检测', '待买', '', '2026-08-05', '2026-08-05')")
    ex_db.commit()
    view = ops.list_view(ex_db)
    assert len(view["items"]) == 3
    assert view["dupes"] == ["牛奶"]


def test_list_check_marks_done(ex_db):
    iid = ops.list_add(ex_db, "牛奶")
    done = ops.list_check(ex_db, [iid])
    assert done == 1
    row = ex_db.execute("SELECT * FROM shopping_items WHERE id = ?", (iid,)).fetchone()
    assert row["status"] == "已买"
    assert ops.list_view(ex_db)["items"] == []


def test_routine_reactivate_after_cycle(ex_db):
    ops.list_add(ex_db, "牛奶", routine="每周")
    iid = ex_db.execute("SELECT id FROM shopping_items").fetchone()["id"]
    ops.list_check(ex_db, [iid])
    # 模拟 8 天前销项(last_done_at 手工改旧)
    old = (date.today() - timedelta(days=8)).isoformat()
    ex_db.execute("UPDATE shopping_items SET last_done_at = ?, status = '已买' WHERE id = ?",
                  (old, iid))
    ex_db.commit()
    view = ops.list_view(ex_db)
    assert [d["name"] for d in view["routine_due"]] == ["牛奶"]
    row = ex_db.execute("SELECT status FROM shopping_items WHERE id = ?", (iid,)).fetchone()
    assert row["status"] == "待买"


def test_routine_not_due_within_cycle(ex_db):
    ops.list_add(ex_db, "牛奶", routine="每周")
    iid = ex_db.execute("SELECT id FROM shopping_items").fetchone()["id"]
    ops.list_check(ex_db, [iid])
    old = (date.today() - timedelta(days=3)).isoformat()
    ex_db.execute("UPDATE shopping_items SET last_done_at = ? WHERE id = ?", (old, iid))
    ex_db.commit()
    assert ops.list_view(ex_db)["routine_due"] == []


# ── 缺货检测 ──────────────────────────────────────────────────────────────


def test_missing_detect_uses_default_threshold(ex_db):
    _seed_item(ex_db, "牛奶", qty=0)
    result = ops.missing_detect(ex_db)
    assert len(result["items"]) == 1
    it = result["items"][0]
    assert it["current"] == 0
    assert it["threshold"] == 1
    assert it["threshold_source"] == "默认"
    assert it["status"] == "空"
    assert it["suggest"] == 2  # max(2×1−0, 1)


def test_missing_detect_low_and_full(ex_db):
    _seed_item(ex_db, "牛奶", qty=1)  # 阈值默认1 → 充足,不报
    _seed_item(ex_db, "面包", qty=0)  # 空 → 报
    result = ops.missing_detect(ex_db)
    assert [it["name"] for it in result["items"]] == ["面包"]


def test_missing_detect_set_threshold(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=1)
    ops.stock_set_threshold(ex_db, mid, 3)
    result = ops.missing_detect(ex_db)
    it = next(x for x in result["items"] if x["id"] == mid)
    assert it["threshold"] == 3
    assert it["threshold_source"] == "囤货设置"
    assert it["status"] == "低"
    assert it["suggest"] == 5  # max(2×3−1, 1)


def test_missing_detect_scope_by_category(ex_db):
    c1 = _seed_category(ex_db, "食品")
    c2 = _seed_category(ex_db, "日用品")
    _seed_item(ex_db, "牛奶", category_id=c1, qty=0)
    _seed_item(ex_db, "纸巾", category_id=c2, qty=0)
    result = ops.missing_detect(ex_db, category_id=c1)
    assert [it["name"] for it in result["items"]] == ["牛奶"]


def test_missing_to_list_adds_with_suggest(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=0)
    r = ops.missing_to_list(ex_db, [mid])
    assert r["added"] == 1
    assert r["dup_skips"] == []
    row = ex_db.execute("SELECT * FROM shopping_items").fetchone()
    assert row["source"] == "缺货检测"
    assert row["quantity"] == 2  # 建议量
    assert "缺货检测" in row["note"]


def test_missing_to_list_skips_dup(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=0)
    ops.list_add(ex_db, "牛奶")
    r = ops.missing_to_list(ex_db, [mid])
    assert r["added"] == 0
    assert r["dup_skips"] == ["牛奶"]


# ── 快递跟踪 ──────────────────────────────────────────────────────────────


def test_express_view_lists_delivery_items(ex_db):
    _seed_item(ex_db, "新书", qty=1, status="快递中")
    _seed_item(ex_db, "牛奶", qty=2)  # 在家,不算快递
    result = ops.express_view(ex_db)
    assert len(result["items"]) == 1
    it = result["items"][0]
    assert it["name"] == "新书"
    assert it["days"] >= 0
    assert it["overdue"] is False


def test_express_view_waits_days(ex_db):
    created = (date.today() - timedelta(days=10)).isoformat()
    _seed_item(ex_db, "旧快递", qty=1, status="快递中", created_at=created)
    result = ops.express_view(ex_db, timeout_days=7)
    assert result["items"][0]["days"] >= 10
    assert result["items"][0]["overdue"] is True


def test_express_receive_changes_status(ex_db):
    mid = _seed_item(ex_db, "新书", qty=1, status="快递中")
    r = ops.express_receive(ex_db, mid, to_status="在家")
    assert r["to_status"] == "在家"
    row = ex_db.execute(
        "SELECT location_status FROM item_locations WHERE item_id = ?", (mid,)).fetchone()
    assert row["location_status"] == "在家"
    ev = ex_db.execute("SELECT * FROM item_events WHERE item_id = ?", (mid,)).fetchone()
    assert ev["event_type"] == "status_changed"
    payload = json.loads(ev["payload_json"])
    assert payload["before"]["location_status"] == "快递中"
    assert payload["after"]["location_status"] == "在家"


def test_express_receive_none_fails(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=1)  # 在家,无快递中
    with pytest.raises(ValueError, match="没有「快递中」"):
        ops.express_receive(ex_db, mid)


# ── 囤货盘点 ──────────────────────────────────────────────────────────────


def test_stock_view_lists_threshold_items(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=5)
    ops.stock_set_threshold(ex_db, mid, 2)
    result = ops.stock_view(ex_db)
    it = result["items"][0]
    assert it["current"] == 5
    assert it["threshold"] == 2
    assert it["status"] == "充足"


def test_stock_status_low_and_empty(ex_db):
    m1 = _seed_item(ex_db, "牛奶", qty=1)
    m2 = _seed_item(ex_db, "面包", qty=0)
    ops.stock_set_threshold(ex_db, m1, 3)
    ops.stock_set_threshold(ex_db, m2, 2)
    statuses = {it["name"]: it["status"] for it in ops.stock_view(ex_db)["items"]}
    assert statuses["牛奶"] == "低"
    assert statuses["面包"] == "空"


def test_stock_set_threshold_upsert(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=1)
    ops.stock_set_threshold(ex_db, mid, 2)
    ops.stock_set_threshold(ex_db, mid, 4)
    result = ops.stock_view(ex_db)
    assert result["items"][0]["threshold"] == 4


def test_stock_set_threshold_validation(ex_db):
    mid = _seed_item(ex_db, "牛奶")
    with pytest.raises(ValueError, match="阈值"):
        ops.stock_set_threshold(ex_db, mid, 0)
    with pytest.raises(ValueError, match="不存在"):
        ops.stock_set_threshold(ex_db, 9999, 2)


def test_stock_fix_updates_quantity(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=3)
    r = ops.stock_fix(ex_db, mid, 1)
    assert r["quantity"] == 1
    row = ex_db.execute(
        "SELECT quantity FROM item_locations WHERE item_id = ?", (mid,)).fetchone()
    assert row["quantity"] == 1
    ev = ex_db.execute("SELECT * FROM item_events WHERE item_id = ?", (mid,)).fetchone()
    assert ev["event_type"] == "quantity_changed"
    payload = json.loads(ev["payload_json"])
    assert payload["before"]["quantity"] == 3
    assert payload["after"]["quantity"] == 1


def test_stock_fix_zero_deletes_location(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=1)
    ops.stock_fix(ex_db, mid, 0)
    rows = ex_db.execute(
        "SELECT * FROM item_locations WHERE item_id = ?", (mid,)).fetchall()
    assert len(rows) == 0


def test_stock_fix_no_stock_location_fails(ex_db):
    mid = _seed_item(ex_db, "牛奶", qty=1, status="快递中")
    with pytest.raises(ValueError, match="没有「在家/备用」"):
        ops.stock_fix(ex_db, mid, 2)


# ── 渲染信封(08 复制数据 5 段 / 复制日志 6 段)──────────────────────────────


def test_envelope_contract():
    from render_快递购物 import build_envelope
    env = build_envelope({"items": [{"id": 1}]}, "SM5-1", "购物清单", "购物清单", target="购物清单")
    assert env["status"] == "ok"
    cd = env["data"]["copy_data"]
    assert set(cd) == {"scene_id", "command_cn", "occurred_at", "target", "payload"}
    cl = env["data"]["copy_log"]
    assert set(cl) == {"scene", "thinking", "data_structure", "call_chain", "timestamp", "exception"}
    assert env["data"]["meta"]["scene_id"] == "SM5-1"


# ── CLI 端到端(每场景 ≥1 · 临时库 + 临时输出)────────────────────────────────


def _run_cli(tmp_path, *args):
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, str(CLI), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    return r


def _seed_cli_db(tmp_path, rows):
    """往 CLI 将使用的库(tmp_path/home.db)里种数据(最小结构;init_db 会自动补齐)"""
    conn = sqlite3.connect(str(tmp_path / "home.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category_id INTEGER, photo TEXT, access_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS item_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL, location TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 1, location_status TEXT DEFAULT '在家', created_at TEXT, updated_at TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER, name TEXT NOT NULL)")
    conn.commit()
    cur = conn.cursor()
    last_id = None
    for name, qty, status in rows:
        cur.execute("INSERT INTO items (name) VALUES (?)", (name,))
        item_id = cur.lastrowid
        cur.execute("INSERT INTO item_locations (item_id, location, quantity, location_status) VALUES (?, '厨房/储物柜', ?, ?)", (item_id, qty, status))
        last_id = item_id
    conn.commit()
    conn.close()
    return last_id


def test_e2e_shopping_list_html(tmp_path):
    r = _run_cli(tmp_path, "list-add", "--name", "牛奶", "--quantity", "2")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "home.html"
    r = _run_cli(tmp_path, "list", "--output", str(out))
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert "购物清单" in html
    assert "牛奶" in html


def test_e2e_missing_html(tmp_path):
    _seed_cli_db(tmp_path, [("牛奶", 0, "在家")])
    out = tmp_path / "missing.html"
    r = _run_cli(tmp_path, "missing", "--output", str(out))
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert "缺货" in html
    assert "牛奶" in html


def test_e2e_express_html_and_receive(tmp_path):
    item_id = _seed_cli_db(tmp_path, [("新书", 1, "快递中")])
    out = tmp_path / "express.html"
    r = _run_cli(tmp_path, "express", "--output", str(out))
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert "快递中" in html
    assert "新书" in html
    r = _run_cli(tmp_path, "express-receive", "--id", str(item_id))
    assert r.returncode == 0, r.stderr
    assert "已确认收货" in r.stdout


def test_e2e_stock_html(tmp_path):
    item_id = _seed_cli_db(tmp_path, [("纸巾", 1, "在家")])
    r = _run_cli(tmp_path, "stock-set-threshold", "--id", str(item_id), "--threshold", "3")
    assert r.returncode == 0, r.stderr
    out = tmp_path / "stock.html"
    r = _run_cli(tmp_path, "stock", "--output", str(out))
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert "囤货" in html
    assert "纸巾" in html
    assert "低" in html
