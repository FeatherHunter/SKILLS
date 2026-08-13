"""tests/test_ledger.py — 账本 ledgers 键测试(wayfinder #311 T7 · T4 #308 契约)

覆盖(T4 测试约束):
- 缺键读空 / 新增 / 重名拒绝 / 改名同步 bills(含软删) / 停用·启用 / list
- 原子写保留其他键(budgets/savings/accounts)
- 渲染器读取:render_write.py / link 读 ledgers 键 → form.selector.ledger.options
  (键空 → options 空数组 · 供 smartSelect 降级普通输入)

隔离:SKILLS_DB_PATH → tmp_path,生产 goals.json 与生产账本只读。
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

LEDGER_CLI = SCRIPTS_DIR / "ledger" / "cli.py"


def _env(tmp_db_dir):
    return {
        **os.environ.copy(),
        "SKILLS_DB_PATH": str(tmp_db_dir),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _run_cli(tmp_db_dir, *args):
    result = subprocess.run(
        [sys.executable, str(LEDGER_CLI)] + list(args) + ["--json"],
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )
    assert result.returncode == 0, (
        f"ledger/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def _goals(tmp_db_dir) -> dict:
    p = tmp_db_dir / "goals.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _insert(tmp_db_dir, category, amount, time_str, note="", account="", ledger="生活",
            deleted=False):
    """直接向临时库插记录(含软删场景)"""
    from db import init_db, TABLE_NAME
    conn = init_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note, deleted_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (category, time_str, amount, account, ledger, "人民币", note,
             "2026-08-01 00:00:00" if deleted else None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _ledger_names(conn):
    cur = conn.execute("SELECT ledger, deleted_at FROM bills")
    return cur.fetchall()


# ── 新增账本 ─────────────────────────────────────────────────────────────────

class TestAddLedger:
    def test_add_creates_goals_entry(self, tmp_db_dir):
        """新增账本 → goals.json ledgers 含 {name, disabled, created_at}"""
        data = _run_cli(tmp_db_dir, "add", "--name", "旅行")
        assert data["status"] == "ok"
        l = data["data"]["ledger"]
        assert l["name"] == "旅行" and l["disabled"] is False
        assert "created_at" in l
        g = _goals(tmp_db_dir)
        assert g["ledgers"][0]["name"] == "旅行"

    def test_add_preserves_other_goals_keys(self, tmp_db_dir):
        """ledgers 域只写 ledgers 键,保留 budgets/savings/accounts"""
        (tmp_db_dir / "goals.json").write_text(
            json.dumps({
                "budgets": [{"month": "2026-08"}],
                "savings": [{"name": "换手机"}],
                "accounts": [{"name": "招行卡", "disabled": False}],
            }, ensure_ascii=False), encoding="utf-8")
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        g = _goals(tmp_db_dir)
        assert g["budgets"] == [{"month": "2026-08"}]
        assert g["savings"] == [{"name": "换手机"}]
        assert g["accounts"] == [{"name": "招行卡", "disabled": False}]
        assert g["ledgers"][0]["name"] == "旅行"

    def test_add_duplicate_errors(self, tmp_db_dir):
        """重名账本 → error(需用户确认)"""
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        data = _run_cli(tmp_db_dir, "add", "--name", "旅行")
        assert data["status"] == "error"
        assert "已存在" in data["message"]

    def test_add_empty_name_errors(self, tmp_db_dir):
        """空账本名 → error"""
        data = _run_cli(tmp_db_dir, "add", "--name", "   ")
        assert data["status"] == "error"
        assert "不能为空" in data["message"]

    def test_add_long_name_errors(self, tmp_db_dir):
        """>30 字账本名 → error(与 accounts 同规则)"""
        data = _run_cli(tmp_db_dir, "add", "--name", "账" * 31)
        assert data["status"] == "error"
        assert "过长" in data["message"]


# ── 账本清单 ─────────────────────────────────────────────────────────────────

class TestListLedgers:
    def test_list_returns_ledgers(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        _run_cli(tmp_db_dir, "add", "--name", "餐饮")
        data = _run_cli(tmp_db_dir, "list")
        assert data["status"] == "ok"
        assert data["data"]["count"] == 2
        assert [l["name"] for l in data["data"]["ledgers"]] == ["旅行", "餐饮"]

    def test_list_empty_when_key_missing(self, tmp_db_dir):
        """缺键 → 读作空数组(list 返回 count=0 空列表)"""
        data = _run_cli(tmp_db_dir, "list")
        assert data["status"] == "ok"
        assert data["data"]["count"] == 0
        assert data["data"]["ledgers"] == []

    def test_list_empty_file(self, tmp_db_dir):
        """空 goals.json 文件 → 空数组"""
        (tmp_db_dir / "goals.json").write_text("", encoding="utf-8")
        data = _run_cli(tmp_db_dir, "list")
        assert data["status"] == "ok"
        assert data["data"]["ledgers"] == []


# ── 改账本(改名 / 停用 / 启用) ────────────────────────────────────────────────

class TestUpdateLedger:
    def test_rename_updates_goals_and_bills(self, tmp_db_dir):
        """改名 → goals.json ledgers + bills.ledger 全部跟随(含软删记录)"""
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        _insert(tmp_db_dir, "出行/网约车", -20.0, "2026-08-01 12:00:00", "打车", "微信", "旅行")
        _insert(tmp_db_dir, "玩乐/旅游", -800.0, "2026-07-01 12:00:00", "门票", "微信", "旅行",
                deleted=True)
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--new-name", "旅游")
        assert data["status"] == "ok"
        assert data["data"]["ledger"]["name"] == "旅游"
        assert "改名" in data["data"]["changes"][0]
        assert "历史流水改名 2 笔" in data["data"]["changes"][1]
        assert _goals(tmp_db_dir)["ledgers"][0]["name"] == "旅游"
        from db import init_db
        conn = init_db()
        try:
            rows = _ledger_names(conn)
            assert rows == [("旅游", None), ("旅游", "2026-08-01 00:00:00")]
        finally:
            conn.close()

    def test_rename_same_name_errors(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--new-name", "旅行")
        assert data["status"] == "error"
        assert "无需修改" in data["message"]

    def test_rename_to_existing_errors(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        _run_cli(tmp_db_dir, "add", "--name", "餐饮")
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--new-name", "餐饮")
        assert data["status"] == "error"
        assert "已存在" in data["message"]

    def test_update_missing_target_errors(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "update", "--name", "不存在", "--disable")
        assert data["status"] == "error"
        assert "不存在" in data["message"]

    def test_update_no_changes_errors(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行")
        assert data["status"] == "error"
        assert "没有可执行的变更" in data["message"]

    def test_disable_and_enable(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--disable")
        assert data["status"] == "ok"
        assert data["data"]["ledger"]["disabled"] is True
        assert _goals(tmp_db_dir)["ledgers"][0]["disabled"] is True
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--enable")
        assert data["data"]["ledger"]["disabled"] is False
        assert _goals(tmp_db_dir)["ledgers"][0]["disabled"] is False

    def test_rename_disabled_ledger(self, tmp_db_dir):
        """停用账本仍可改名(历史记录跟随)"""
        _run_cli(tmp_db_dir, "add", "--name", "旅行")
        _run_cli(tmp_db_dir, "update", "--name", "旅行", "--disable")
        data = _run_cli(tmp_db_dir, "update", "--name", "旅行", "--new-name", "旅游")
        assert data["status"] == "ok"
        l = _goals(tmp_db_dir)["ledgers"][0]
        assert l["name"] == "旅游" and l["disabled"] is True


# ── 渲染器读取(供 T6 smartSelect 消费) ────────────────────────────────────────

class TestRendererReadsLedgers:
    def test_render_write_selector_options(self, tmp_db_dir):
        """render_write 采集表单 payload → form.selector.ledger.options 来自 ledgers 键"""
        (tmp_db_dir / "goals.json").write_text(
            json.dumps({"ledgers": [
                {"name": "旅行", "disabled": False},
                {"name": "餐饮", "disabled": True},
            ]}, ensure_ascii=False), encoding="utf-8")
        import render_write as rw
        payload = rw.build_payload("expense", {"amount": "35", "category": "餐饮/外卖/午餐"},
                                   "午饭", "", [])
        opts = payload["data"]["form"]["selector"]["ledger"]["options"]
        assert opts == [
            {"name": "旅行", "disabled": False},
            {"name": "餐饮", "disabled": True},
        ]

    def test_render_write_selector_empty_when_key_missing(self, tmp_db_dir):
        """键空/缺键 → options 空数组(组件降级普通输入)"""
        import render_write as rw
        payload = rw.build_payload("expense", {"amount": "35"}, "", "", [])
        assert payload["data"]["form"]["selector"]["ledger"]["options"] == []

    def test_link_form_selector_options(self, tmp_db_dir):
        """link 联动采集表单 → form.selector.ledger.options 来自 ledgers 键"""
        (tmp_db_dir / "goals.json").write_text(
            json.dumps({"ledgers": [
                {"name": "旅行", "disabled": False},
            ]}, ensure_ascii=False), encoding="utf-8")
        from link.cli import build_form_payload
        payload = build_form_payload("purchase", {"amount": "199", "item": "空气炸锅"}, "", "")
        opts = payload["data"]["form"]["selector"]["ledger"]["options"]
        assert opts == [{"name": "旅行", "disabled": False}]

    def test_link_form_selector_empty_when_key_missing(self, tmp_db_dir):
        from link.cli import build_form_payload
        payload = build_form_payload("meal", {"amount": "35", "ate": "鸡腿饭"}, "", "")
        assert payload["data"]["form"]["selector"]["ledger"]["options"] == []

    def test_render_write_ignores_malformed_ledgers(self, tmp_db_dir):
        """损坏 goals.json → 空数组(不抛错,渲染照常)"""
        (tmp_db_dir / "goals.json").write_text("{not json", encoding="utf-8")
        import render_write as rw
        payload = rw.build_payload("expense", {"amount": "35"}, "", "", [])
        assert payload["data"]["form"]["selector"]["ledger"]["options"] == []
