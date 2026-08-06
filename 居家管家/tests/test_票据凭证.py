"""SM6 票据凭证域 · fixture 临时库测试(G6)

隔离原则: 每测试独立临时库(monkeypatch SKILLS_DB_PATH → tmp_path),
        绝不触碰生产库; 账号场景额外 monkeypatch accounts 模块级路径。
"""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

TODAY = date.today()


@pytest.fixture
def rconn(tmp_path, monkeypatch):
    """域临时库连接(懒解析 env, 每测试独立) + 种子 items/categories(G6 fixture 隔离)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    from 票据凭证.db import get_conn
    conn = get_conn()
    conn.execute("""CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, category TEXT, category_id INTEGER)""")
    conn.execute("""CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, parent_id INTEGER)""")
    conn.execute("INSERT INTO items (name, category, category_id) VALUES ('空气炸锅', '厨房电器', 1)")
    conn.execute("INSERT INTO items (name, category, category_id) VALUES ('扫地机', '清洁工具', 2)")
    conn.execute("INSERT INTO categories (id, name) VALUES (1, '厨房电器')")
    conn.execute("INSERT INTO categories (id, name) VALUES (2, '清洁工具')")
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def account_env(tmp_path, monkeypatch):
    """账号场景: 隔离 accounts.py 的 DB 路径 + 主密钥文件"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import accounts
    monkeypatch.setattr(accounts, "DB_PATH", tmp_path / "home.db")
    monkeypatch.setattr(accounts, "MASTER_KEY_FILE", tmp_path / ".master.key")
    monkeypatch.setattr(accounts, "SKILL_DIR", tmp_path)
    return tmp_path


def d(offset_days):
    """相对今天的日期串(YYYY-MM-DD)"""
    return (TODAY + timedelta(days=offset_days)).isoformat()


# ── 购买记录 ────────────────────────────────────────────────────────

def test_purchase_add_and_list(rconn):
    from 票据凭证 import ops
    pid = ops.purchase_add(rconn, 1, d(-30), price=99.5, channel="京东",
                           merchant_contact="客服A", return_window_days=7)
    rows = ops.purchase_list(rconn)
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == pid
    assert r["purchased_at"] == d(-30)
    assert r["price"] == 99.5
    assert r["channel"] == "京东"
    assert r["merchant_contact"] == "客服A"


def test_purchase_return_window_default_7(rconn):
    from 票据凭证 import ops
    ops.purchase_add(rconn, 1, d(0))
    rows = ops.purchase_list(rconn)
    assert rows[0]["return_end"] == d(7)
    assert rows[0]["return_days_left"] == 7


def test_purchase_return_window_custom(rconn):
    from 票据凭证 import ops
    ops.purchase_add(rconn, 1, d(0), return_window_days=30)
    assert ops.purchase_list(rconn)[0]["return_days_left"] == 30


def test_purchase_return_window_negative_rejected(rconn):
    from 票据凭证 import ops
    with pytest.raises(ValueError):
        ops.purchase_add(rconn, 1, d(0), return_window_days=-1)


def test_purchase_invalid_date_rejected(rconn):
    from 票据凭证 import ops
    with pytest.raises(ValueError):
        ops.purchase_add(rconn, 1, "2026-13-45")


def test_purchase_list_filter_by_year(rconn):
    from 票据凭证 import ops
    ops.purchase_add(rconn, 1, "2025-01-01")
    ops.purchase_add(rconn, 1, "2026-01-01")
    assert len(ops.purchase_list(rconn, year=2025)) == 1
    assert len(ops.purchase_list(rconn, year=2026)) == 1


def test_purchase_stats_aggregate(rconn):
    from 票据凭证 import ops
    ops.purchase_add(rconn, 1, d(-10), price=50)
    ops.purchase_add(rconn, 2, d(-5), price=150)
    stats = ops.purchase_stats(rconn)
    assert stats["count"] == 2
    assert stats["total_price"] == 200.0


# ── 保修与保养 ──────────────────────────────────────────────────────

def test_warranty_register_and_status_in(rconn):
    from 票据凭证 import ops
    wid = ops.warranty_register(rconn, 1, "保修", d(0), 365)
    items = ops.warranty_list(rconn)
    assert len(items) == 1
    assert items[0]["status"] == "在保"
    assert items[0]["id"] == wid


def test_warranty_status_expiring(rconn):
    from 票据凭证 import ops
    ops.warranty_register(rconn, 1, "保修", d(0), 10)
    assert ops.warranty_list(rconn)[0]["status"] == "即将到期"


def test_warranty_status_expired(rconn):
    from 票据凭证 import ops
    ops.warranty_register(rconn, 1, "保修", d(-400), 365)
    assert ops.warranty_list(rconn)[0]["status"] == "已过"


def test_warranty_repair_event(rconn):
    from 票据凭证 import ops
    wid = ops.warranty_register(rconn, 1, "保修", d(0), 365)
    ops.warranty_repair(rconn, wid, d(-1), cost=200, note="换屏")
    events = ops.warranty_events(rconn, wid)
    assert len(events) == 1
    assert events[0]["event_type"] == "维修"
    assert events[0]["cost"] == 200
    assert ops.warranty_list(rconn)[0]["repair_count"] == 1


def test_warranty_maintain_updates_last_done(rconn):
    from 票据凭证 import ops
    wid = ops.warranty_register(rconn, 1, "保养", d(0), 30)
    ops.warranty_maintain(rconn, wid, d(0))
    items = ops.warranty_list(rconn)
    assert items[0]["last_done_date"] == d(0)
    assert items[0]["events"][0]["event_type"] == "保养执行"
    assert items[0]["status"] == "已做"


def test_warranty_maintenance_expired_due(rconn):
    from 票据凭证 import ops
    ops.warranty_register(rconn, 1, "保养", d(-40), 30)
    assert ops.warranty_list(rconn)[0]["status"] == "到期未做"


def test_warranty_maintain_only_for_maintenance_kind(rconn):
    from 票据凭证 import ops
    wid = ops.warranty_register(rconn, 1, "保修", d(0), 365)
    with pytest.raises(ValueError):
        ops.warranty_maintain(rconn, wid, d(0))


# ── 证件 ────────────────────────────────────────────────────────────

def test_cert_add_masked_and_no_plaintext(rconn):
    from 票据凭证 import ops
    ops.cert_add(rconn, "护照", "张三", "E12345678", d(-30), d(730))
    items = ops.cert_list(rconn)
    assert len(items) == 1
    assert items[0]["number_masked"] == "****5678"
    assert "cert_number" not in items[0]
    assert items[0]["cert_status"] == "有效"


def test_cert_sorted_by_expiry(rconn):
    from 票据凭证 import ops
    ops.cert_add(rconn, "身份证", "张三", "110101199001011234", d(0), d(365))
    ops.cert_add(rconn, "驾照", "张三", "110101", d(0), d(30))
    ops.cert_add(rconn, "护照", "张三", "E1", d(0), d(100))
    items = ops.cert_list(rconn)
    assert [i["cert_type"] for i in items] == ["驾照", "护照", "身份证"]


def test_cert_status_thresholds(rconn):
    from 票据凭证 import ops
    ops.cert_add(rconn, "身份证", "张三", "X", d(0), d(10))
    ops.cert_add(rconn, "驾照", "张三", "X", d(0), d(-1))
    items = {i["cert_type"]: i for i in ops.cert_list(rconn)}
    assert items["身份证"]["cert_status"] == "即将到期"
    assert items["驾照"]["cert_status"] == "已过期"


def test_cert_invalid_type_rejected(rconn):
    from 票据凭证 import ops
    with pytest.raises(ValueError):
        ops.cert_add(rconn, "房产证", "张三", "X", d(0), d(365))


# ── 账号密码(敏感) ──────────────────────────────────────────────────

def test_account_flow(account_env):
    from 票据凭证.account_ops import (
        _write_master_key, is_master_key_set, account_add_typed,
        account_list_masked, account_show_typed,
    )
    _write_master_key("test-key-123")
    assert is_master_key_set()
    res = account_add_typed("淘宝", "user1", "p@ssW0rd", "test-key-123", account_type="购物")
    assert res["success"]

    rows = account_list_masked()
    assert len(rows) == 1
    assert rows[0]["platform"] == "淘宝"
    assert rows[0]["type"] == "购物"
    assert "password" not in rows[0]
    assert rows[0]["password_masked"] == "******"

    shown = account_show_typed("淘宝", "test-key-123")
    assert shown["success"] and shown["password"] == "p@ssW0rd"

    bad = account_show_typed("淘宝", "wrong-key")
    assert not bad["success"]


def test_account_wrong_master_key_rejected(account_env):
    from 票据凭证.account_ops import _write_master_key, account_add_typed
    _write_master_key("test-key-123")
    res = account_add_typed("京东", "u", "pw", "bad-key")
    assert not res["success"]


def test_account_update_typed(account_env):
    from 票据凭证.account_ops import (
        _write_master_key, account_add_typed, account_update_typed, account_show_typed,
    )
    _write_master_key("test-key-123")
    account_add_typed("微信", "old_user", "old_pw", "test-key-123", account_type="社交")
    res = account_update_typed("微信", "test-key-123",
                               username="new_user", password="new_pw", account_type="银行")
    assert res["success"]
    shown = account_show_typed("微信", "test-key-123")
    assert shown["username"] == "new_user"
    assert shown["password"] == "new_pw"
    bad = account_update_typed("微信", "wrong-key", username="x")
    assert not bad["success"]


# ── payload 契约(08 规范 · 敏感不出 HTML) ───────────────────────────

def test_payloads_smoke(rconn, account_env):
    from 票据凭证 import ops
    from 票据凭证.payloads import (
        purchase_payload, warranty_payload, certificates_payload, accounts_payload,
    )
    ops.purchase_add(rconn, 1, d(0), price=10)
    ops.warranty_register(rconn, 1, "保修", d(0), 365)
    ops.cert_add(rconn, "护照", "张三", "E12345678", d(0), d(30))
    from 票据凭证.account_ops import _write_master_key, account_add_typed
    _write_master_key("test-key-123")
    account_add_typed("淘宝", "u", "pw", "test-key-123")

    p = purchase_payload(rconn)
    assert p["status"] == "ok" and p["data"]["meta"]["scene_id"] == "SM6-1"

    w = warranty_payload(rconn)
    assert w["status"] == "ok" and w["data"]["items"][0]["status"] == "在保"

    c = certificates_payload(rconn)
    assert c["status"] == "ok" and c["data"]["items"][0]["number_masked"] == "****5678"
    raw = json.dumps(c, ensure_ascii=False)
    assert "E12345678" not in raw  # 敏感: 明文证件号不得出现在 payload

    a = accounts_payload(rconn)
    assert a["status"] == "ok"
    raw = json.dumps(a, ensure_ascii=False)
    assert "pw" not in raw and '"password"' not in raw  # 敏感: 明文密码永不出现在 HTML payload


# ── CLI E2E(每场景 ≥1) ─────────────────────────────────────────────

def seed_items(db_path):
    """CLI 测试种子: 最小 items/categories(域表 FK 依赖)"""
    conn = sqlite3.connect(str(db_path))
    conn.execute("""CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, category TEXT, category_id INTEGER)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, parent_id INTEGER)""")
    conn.execute("INSERT INTO items (name, category_id) VALUES ('空气炸锅', 1)")
    conn.execute("INSERT INTO items (name, category_id) VALUES ('扫地机', 2)")
    conn.execute("INSERT INTO categories (id, name) VALUES (1, '厨房电器')")
    conn.execute("INSERT INTO categories (id, name) VALUES (2, '清洁工具')")
    conn.commit()
    conn.close()


def test_cli_purchase_add_and_list_e2e(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    seed_items(tmp_path / "home.db")
    from 票据凭证.cli import main
    assert main(["purchase", "add", "--item-id", "1", "--date", d(0),
                 "--price", "88", "--channel", "山姆"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["scene_id"] == "SM6-1"
    assert main(["purchase", "list", "--output", str(tmp_path / "p.html")]) == 0
    html = (tmp_path / "p.html").read_text(encoding="utf-8")
    assert "<!--INJECT-DATA-->" not in html
    assert "购买记录" in html


def test_cli_warranty_e2e(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    seed_items(tmp_path / "home.db")
    from 票据凭证.cli import main
    assert main(["warranty", "register", "--item-id", "1", "--kind", "保修",
                 "--start-date", d(-400), "--duration-days", "365"]) == 0
    assert main(["warranty", "list", "--output", str(tmp_path / "w.html")]) == 0
    html = (tmp_path / "w.html").read_text(encoding="utf-8")
    assert "保修" in html


def test_cli_cert_e2e(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    seed_items(tmp_path / "home.db")
    from 票据凭证.cli import main
    assert main(["cert", "add", "--type", "护照", "--holder", "张三",
                 "--number", "E12345678", "--expires-at", d(30)]) == 0
    assert main(["cert", "list", "--output", str(tmp_path / "c.html")]) == 0
    html = (tmp_path / "c.html").read_text(encoding="utf-8")
    assert "****5678" in html
    assert "E12345678" not in html  # 敏感: HTML 内不得有明文证件号


def test_cli_account_e2e(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import accounts
    monkeypatch.setattr(accounts, "DB_PATH", tmp_path / "home.db")
    monkeypatch.setattr(accounts, "MASTER_KEY_FILE", tmp_path / ".master.key")
    from 票据凭证.cli import main
    assert main(["account", "init-master", "--master-key", "test-key-123"]) == 0
    assert main(["account", "add", "--platform", "淘宝", "--user", "u1",
                 "--pass", "secret123", "--master-key", "test-key-123", "--type", "购物"]) == 0
    assert main(["account", "list", "--output", str(tmp_path / "a.html")]) == 0
    html = (tmp_path / "a.html").read_text(encoding="utf-8")
    assert "******" in html
    assert "secret123" not in html  # 敏感: HTML 内不得有明文密码
    assert main(["account", "show", "--platform", "淘宝", "--master-key", "test-key-123"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["payload"]["password"] == "secret123"


def test_cli_error_graceful_degradation(tmp_path, monkeypatch, capsys):
    """08 三层反馈: 业务失败 → 结构化错误 JSON, 不裸堆栈"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    from 票据凭证.cli import main
    assert main(["cert", "add", "--type", "房产证", "--expires-at", d(30)]) != 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["status"] == "error"
    assert "suggestion" in out
    assert main(["purchase", "add", "--item-id", "1", "--date", "bad-date"]) == 1
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["status"] == "error"
