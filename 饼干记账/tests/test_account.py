"""tests/test_account.py — 账户域 4 场景 CLI/HTML 测试(隔离契约:scripts/account/ + templates/账户/)

覆盖(对齐 scenes/account.yaml 4 场景):
- 新增账户(add → goals.json 账户表;重名/空名报错;保留 goals.json 其他键)
- 改账户(update 改名 → 账户表 + bills.account;停用/启用;账户不存在报错)
- 账户转账(transfer 两笔 #转账:转出支出 + 转入收入;同账户/负数报错;不影响收支统计)
- 看账户汇总(summary 余额卡 = 收支累计推算;停用灰显 + 不含于合计;未登记账户自动暴露;最近流水)
- HTML 渲染(4 模板:采集/选择/结果型;BOM + charset + payload + 复制按钮 + B1 toast + meta 对齐 yaml)

外部行为校验:CLI --json 三段式 {status, data, message};render.py 输出合法 HTML。
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

ACCOUNT_CLI = SCRIPTS_DIR / "account" / "cli.py"
ACCOUNT_RENDER = SCRIPTS_DIR / "account" / "render.py"


def _env(tmp_db_dir):
    return {
        **os.environ.copy(),
        "SKILLS_DB_PATH": str(tmp_db_dir),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _run_cli(tmp_db_dir, *args):
    result = subprocess.run(
        [sys.executable, str(ACCOUNT_CLI)] + list(args) + ["--json"],
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )
    assert result.returncode == 0, (
        f"account/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def _run_render(tmp_db_dir, form_type, *extra, out_name="out.html"):
    out_dir = tmp_db_dir / "html_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    result = subprocess.run(
        [sys.executable, str(ACCOUNT_RENDER), form_type, "--out", str(out_path)] + list(extra),
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )
    return result, out_path


def _insert(tmp_db_dir, category, amount, time_str, note="", account="", ledger="生活"):
    """直接向临时库插记录(复用 conftest 的 db 模块路径解析)"""
    from db import init_db, TABLE_NAME
    conn = init_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category, time_str, amount, account, ledger, "人民币", note),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _goals(tmp_db_dir) -> dict:
    p = tmp_db_dir / "goals.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _seed_accounts(tmp_db_dir, names=("招行卡", "支付宝", "花呗")):
    """登记 3 个账户 + 典型流水:收入 8000 招行 / 支出 35 支付宝 / 转账 500 支付宝→招行"""
    for n, t in [("招行卡", "银行卡"), ("支付宝", "支付"), ("花呗", "信用")]:
        _run_cli(tmp_db_dir, "add", "--name", n, "--type", t)
    _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-08-09 09:00:00", "工资", "招行卡")
    _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-09 12:00:00", "午饭", "支付宝")
    _run_cli(tmp_db_dir, "transfer", "--amount", "500", "--from", "支付宝", "--to", "招行卡",
             "--time", "2026-08-09 10:00:00")


# ── 新增账户(account-1-1) ────────────────────────────────────────────────────

class TestAddAccount:
    def test_add_creates_goals_entry(self, tmp_db_dir):
        """新增账户 → goals.json accounts 含 {name, type, disabled, created_at}"""
        data = _run_cli(tmp_db_dir, "add", "--name", "招行卡", "--type", "银行卡")
        assert data["status"] == "ok"
        a = data["data"]["account"]
        assert a["name"] == "招行卡" and a["type"] == "银行卡" and a["disabled"] is False
        g = _goals(tmp_db_dir)
        assert g["accounts"][0]["name"] == "招行卡"
        assert "created_at" in g["accounts"][0]

    def test_add_preserves_other_goals_keys(self, tmp_db_dir):
        """账户域只写 accounts 键,保留目标域键(如 budgets)"""
        (tmp_db_dir / "goals.json").write_text(
            json.dumps({"budgets": [{"month": "2026-08"}]}, ensure_ascii=False), encoding="utf-8")
        _run_cli(tmp_db_dir, "add", "--name", "微信")
        g = _goals(tmp_db_dir)
        assert g["budgets"] == [{"month": "2026-08"}]
        assert g["accounts"][0]["name"] == "微信"

    def test_add_duplicate_errors(self, tmp_db_dir):
        """重名账户 → error(需用户确认)"""
        _run_cli(tmp_db_dir, "add", "--name", "招行卡")
        data = _run_cli(tmp_db_dir, "add", "--name", "招行卡")
        assert data["status"] == "error"
        assert "已存在" in data["message"]

    def test_add_empty_name_errors(self, tmp_db_dir):
        """空账户名 → error"""
        data = _run_cli(tmp_db_dir, "add", "--name", "   ")
        assert data["status"] == "error"
        assert "不能为空" in data["message"]


# ── 账户清单 ─────────────────────────────────────────────────────────────────

class TestListAccounts:
    def test_list_returns_accounts(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "list")
        assert data["status"] == "ok"
        assert data["data"]["count"] == 3
        assert [a["name"] for a in data["data"]["accounts"]] == ["招行卡", "支付宝", "花呗"]

    def test_list_empty(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "list")
        assert data["status"] == "ok" and data["data"]["accounts"] == []


# ── 改账户(account-2-1) ──────────────────────────────────────────────────────

class TestUpdateAccount:
    def test_rename_updates_goals_and_bills(self, tmp_db_dir):
        """改名 → 账户表 + 历史流水同步改名(记录保留)"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "update", "--name", "招行卡", "--new-name", "招行工资卡")
        assert data["status"] == "ok"
        assert any("改名" in c for c in data["data"]["changes"])
        names = {a["name"] for a in _goals(tmp_db_dir)["accounts"]}
        assert "招行卡" not in names and "招行工资卡" in names
        # bills 历史记录已改名(工资 + 转入两笔)
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            rows = [r[0] for r in conn.execute("SELECT account FROM bills WHERE account = '招行工资卡'")]
            assert len(rows) == 2, f"改名后 bills 应为 2 笔新名,实际 {rows}"
            legacy = conn.execute("SELECT COUNT(*) FROM bills WHERE account = '招行卡'").fetchone()[0]
            assert legacy == 0
        finally:
            conn.close()

    def test_rename_to_existing_errors(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "update", "--name", "花呗", "--new-name", "支付宝")
        assert data["status"] == "error" and "已存在" in data["message"]

    def test_disable_and_enable(self, tmp_db_dir):
        """停用/启用 → disabled 标记切换"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "update", "--name", "花呗", "--disable")
        assert data["status"] == "ok"
        assert any("停用" in c for c in data["data"]["changes"])
        assert _goals(tmp_db_dir)["accounts"][2]["disabled"] is True
        _run_cli(tmp_db_dir, "update", "--name", "花呗", "--enable")
        assert _goals(tmp_db_dir)["accounts"][2]["disabled"] is False

    def test_update_missing_account_errors(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "update", "--name", "不存在", "--disable")
        assert data["status"] == "error" and "不存在" in data["message"]

    def test_update_no_changes_errors(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "update", "--name", "招行卡")
        assert data["status"] == "error" and "没有可执行的变更" in data["message"]


# ── 账户转账(account-3-1) ────────────────────────────────────────────────────

class TestTransfer:
    def test_transfer_creates_two_records(self, tmp_db_dir):
        """转账 → 两笔 #转账:转出支出(源账户)+ 转入收入(目标账户),同一时刻"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "transfer", "--amount", "300", "--from", "招行卡",
                        "--to", "支付宝", "--time", "2026-08-09 15:00:00")
        assert data["status"] == "ok"
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            conn.row_factory = sqlite3.Row
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM bills WHERE category LIKE '转账/%' ORDER BY id")]
        finally:
            conn.close()
        assert len(rows) == 4  # 2(seed) + 2(本次)
        out_r = [r for r in rows if r["category"] == "转账/转出"][-1]
        in_r = [r for r in rows if r["category"] == "转账/转入"][-1]
        assert out_r["amount"] == -300.0 and out_r["account"] == "招行卡"
        assert in_r["amount"] == 300.0 and in_r["account"] == "支付宝"
        assert out_r["ledger"] == "转账" and in_r["ledger"] == "转账"
        assert "#转账" in out_r["note"] and "支付宝" in out_r["note"]
        assert "#转账" in in_r["note"] and "招行卡" in in_r["note"]
        assert out_r["time"] == in_r["time"] == "2026-08-09 15:00:00"

    def test_transfer_same_account_errors(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "transfer", "--amount", "100", "--from", "支付宝", "--to", "支付宝")
        assert data["status"] == "error" and "相同" in data["message"]

    def test_transfer_negative_errors(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "transfer", "--amount", "-50", "--from", "支付宝", "--to", "招行卡")
        assert data["status"] == "error" and "正数" in data["message"]

    def test_transfer_bad_time_errors(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "transfer", "--amount", "50", "--from", "支付宝",
                        "--to", "招行卡", "--time", "2026/08/09")
        assert data["status"] == "error"


# ── 看账户汇总(account-4-1) ──────────────────────────────────────────────────

class TestSummary:
    def test_balance_includes_transfer(self, tmp_db_dir):
        """余额 = 收支累计推算,含转账(招行 +500 / 支付宝 -500)"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "summary")
        assert data["status"] == "ok"
        by_name = {a["name"]: a for a in data["data"]["accounts"]}
        # 招行卡: 收入 8000 + 转入 500 = 8500;支付宝: -支出 35 - 转出 500 = -535
        assert by_name["招行卡"]["balance"] == 8500.0
        assert by_name["支付宝"]["balance"] == -535.0
        assert by_name["花呗"]["balance"] == 0.0

    def test_transfer_excluded_from_income_expense(self, tmp_db_dir):
        """不影响收支统计:支出/收入 KPI 不含 #转账"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "summary")
        t = data["data"]["totals"]
        assert t["income"] == 8000.0   # 不含转入 500
        assert t["expense"] == 35.0    # 不含转出 500
        assert t["net"] == 7965.0
        assert t["transfer_count"] == 2 and t["transfer_total"] == 1000.0
        # 一致性:总余额 = 净额(转账在总和中抵消)
        assert round(t["balance"], 2) == round(t["net"], 2)

    def test_disabled_account_greyed_and_excluded(self, tmp_db_dir):
        """停用账户:disabled=True + 不含于合计"""
        _seed_accounts(tmp_db_dir)
        _run_cli(tmp_db_dir, "update", "--name", "花呗", "--disable")
        data = _run_cli(tmp_db_dir, "summary")
        by_name = {a["name"]: a for a in data["data"]["accounts"]}
        assert by_name["花呗"]["disabled"] is True
        assert data["data"]["totals"]["count"] == 4  # 活跃账户全部流水(招行 2 + 支付宝 2)

    def test_unregistered_account_surfaced(self, tmp_db_dir):
        """bills 有流水但未登记 → 自动暴露(registered=False),不丢数据"""
        _seed_accounts(tmp_db_dir)
        _insert(tmp_db_dir, "出行/网约车", -20.0, "2026-08-08 20:00:00", "打车", "微信")
        data = _run_cli(tmp_db_dir, "summary")
        by_name = {a["name"]: a for a in data["data"]["accounts"]}
        assert "微信" in by_name
        assert by_name["微信"]["registered"] is False
        assert by_name["微信"]["balance"] == -20.0
        assert by_name["招行卡"]["registered"] is True

    def test_summary_empty(self, tmp_db_dir):
        """无账户无流水 → 空态数据(不崩)"""
        data = _run_cli(tmp_db_dir, "summary")
        assert data["status"] == "ok"
        assert data["data"]["accounts"] == []
        assert data["data"]["totals"]["balance"] == 0.0

    def test_summary_flows_sorted_desc(self, tmp_db_dir):
        """最近流水摘要:时间倒序,最多 12 笔"""
        _seed_accounts(tmp_db_dir)
        data = _run_cli(tmp_db_dir, "summary")
        flows = data["data"]["flows"]
        times = [f["time"] for f in flows]
        assert times == sorted(times, reverse=True)
        assert len(flows) == 4  # seed = 2 条普通 + 2 条转账,共 4 笔
        assert all("account" in f and "category" in f for f in flows)


# ── HTML 渲染(4 模板) ────────────────────────────────────────────────────────

class TestRender:
    def _assert_well_formed(self, html_path, expect_wake=None, expect_scene=None):
        assert html_path.exists(), f"输出 HTML 不存在: {html_path}"
        raw = html_path.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf", "缺 UTF-8 BOM"
        text = raw.decode("utf-8-sig")
        assert 'charset="UTF-8"' in text, "缺 charset"
        m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
        assert m, "缺 payload 注入点"
        payload = json.loads(m.group(1))
        # 08 §4 硬标准:复制按钮 + B1 toast
        assert 'id="copyDataBtn"' in text and 'id="copyLogBtn"' in text, "缺复制按钮"
        assert 'id="toastClose"' in text and "4500" in text, "缺 B1 toast"
        # meta 对齐 scenes/account.yaml(门禁 A 层 1)
        meta = payload.get("data", {}).get("meta", {})
        if expect_wake:
            assert meta.get("wake_word") == expect_wake, f"wake_word 期望 {expect_wake},实际 {meta.get('wake_word')}"
        if expect_scene:
            assert meta.get("scene_id") == expect_scene, f"scene_id 期望 {expect_scene},实际 {meta.get('scene_id')}"
        return payload, text

    def test_add_form(self, tmp_db_dir):
        """新增账户采集表单(account-1-1)"""
        _seed_accounts(tmp_db_dir)
        result, out_path = _run_render(tmp_db_dir, "add-form", "--name", "微信", "--type", "支付")
        assert result.returncode == 0, result.stderr
        payload, text = self._assert_well_formed(out_path, "新增账户", "account_add")
        assert payload["data"]["form"]["name"] == "微信"
        # 账户建议点选(已有账户 chips)
        assert "sugg-btn" in text

    def test_transfer_form(self, tmp_db_dir):
        """账户转账采集表单(account-3-1)"""
        _seed_accounts(tmp_db_dir)
        result, out_path = _run_render(tmp_db_dir, "transfer-form", "--amount", "200",
                                       "--from", "支付宝", "--to", "招行卡")
        assert result.returncode == 0, result.stderr
        payload, text = self._assert_well_formed(out_path, "账户转账", "account_transfer")
        f = payload["data"]["form"]
        assert f["amount"] == "200" and f["from"] == "支付宝" and f["to"] == "招行卡"
        assert len(f["accounts"]) == 3

    def test_update_form_diff(self, tmp_db_dir):
        """改账户选择确认(account-2-1):diff 预览"""
        _seed_accounts(tmp_db_dir)
        result, out_path = _run_render(tmp_db_dir, "update-form", "--name", "招行卡",
                                       "--new-name", "招行工资卡")
        assert result.returncode == 0, result.stderr
        payload, text = self._assert_well_formed(out_path, "改账户", "account_update")
        changes = payload["data"]["form"]["changes"]
        assert any(c["field"] == "账户名" and c["old"] == "招行卡" and c["new"] == "招行工资卡"
                   for c in changes)

    def test_update_form_disable(self, tmp_db_dir):
        _seed_accounts(tmp_db_dir)
        result, out_path = _run_render(tmp_db_dir, "update-form", "--name", "花呗", "--disable")
        assert result.returncode == 0, result.stderr
        payload, _ = self._assert_well_formed(out_path, "改账户", "account_update")
        assert any("停用" in c["new"] for c in payload["data"]["form"]["changes"])

    def test_update_form_missing_account_error(self, tmp_db_dir):
        """改账户目标不在账户表 → 渲染失败(exit 1,提示新增)"""
        result, out_path = _run_render(tmp_db_dir, "update-form", "--name", "不存在", "--disable")
        assert result.returncode == 1
        assert "不在账户表" in result.stderr

    def test_view_summary(self, tmp_db_dir):
        """看账户汇总结果型 HTML(account-4-1):余额卡 + KPI + 最近流水 + 弹层三选一"""
        _seed_accounts(tmp_db_dir)
        result, out_path = _run_render(tmp_db_dir, "view")
        assert result.returncode == 0, result.stderr
        payload, text = self._assert_well_formed(out_path, "看账户汇总", "account_summary")
        d = payload["data"]
        assert len(d["accounts"]) == 3
        assert d["totals"]["income"] == 8000.0
        # 弹层三选一(结果型 · 08 §4)
        assert 'data-f="text"' in text and 'data-f="json"' in text and 'data-f="csv"' in text
        # 停用灰显样式类
        assert "acct-card" in text and "disabled" in text

    def test_view_summary_with_disabled_and_unregistered(self, tmp_db_dir):
        """汇总 HTML:停用账户 badge + 未登记账户 badge"""
        _seed_accounts(tmp_db_dir)
        _run_cli(tmp_db_dir, "update", "--name", "花呗", "--disable")
        _insert(tmp_db_dir, "餐饮", -15.0, "2026-08-09 13:00:00", "水", "微信")
        result, out_path = _run_render(tmp_db_dir, "view")
        payload, text = self._assert_well_formed(out_path, "看账户汇总", "account_summary")
        by_name = {a["name"]: a for a in payload["data"]["accounts"]}
        assert by_name["花呗"]["disabled"] is True
        assert by_name["微信"]["registered"] is False

    def test_view_empty(self, tmp_db_dir):
        """无账户 → 空态 HTML 正常生成"""
        result, out_path = _run_render(tmp_db_dir, "view")
        assert result.returncode == 0, result.stderr
        self._assert_well_formed(out_path, "看账户汇总", "account_summary")

    def test_all_forms_have_bom(self, tmp_db_dir):
        """4 模板输出全部带 BOM(Windows 记事本兼容)"""
        _seed_accounts(tmp_db_dir)
        for form, extra, name in [
            ("add-form", ["--name", "微信"], "add"),
            ("transfer-form", ["--amount", "1", "--from", "支付宝", "--to", "招行卡"], "t"),
            ("update-form", ["--name", "花呗", "--disable"], "u"),
            ("view", [], "v"),
        ]:
            result, out_path = _run_render(tmp_db_dir, form, *extra, out_name=f"{name}.html")
            assert result.returncode == 0, result.stderr
            assert out_path.read_bytes()[:3] == b"\xef\xbb\xbf", f"{form} 缺 BOM"
