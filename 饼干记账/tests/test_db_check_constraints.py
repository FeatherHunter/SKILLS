"""bills 表 CHECK 约束测试（ticket 03）

defense-in-depth：直接 SQL 绕过 CLI 也无法保存脏数据。

测试接缝：
- 跑迁移脚本 `scripts/migrations/add_bills_check_constraints.py`
- 检查 bills 表的 SQL schema 含 CHECK 子句
- INSERT amount=0 → IntegrityError
- INSERT currency='USD' → IntegrityError
- INSERT ledger='' → IntegrityError
- --rollback 后 CHECK 消失
- --dry-run 不修改 schema
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "scripts" / "migrations"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ── 迁移脚本路径 ─────────────────────────────────────────────────────────────

MIGRATION_SCRIPT = MIGRATIONS_DIR / "add_bills_check_constraints.py"

# 一条合法 sample（便于 INSERT 成功后取 baseline）
VALID_BILL = {
    "category": "餐饮/外卖/午餐",
    "time": "2026-07-28 12:00:00",
    "amount": -35.0,
    "account": "支付宝",
    "ledger": "生活",
    "currency": "人民币",
    "note": "午饭",
}


def _run_migration(tmp_db_dir, *args, expect_rc=0):
    """跑迁移脚本（带 SKILLS_DB_PATH env），返回 (rc, out, err)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(MIGRATION_SCRIPT)] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=30,
    )
    assert result.returncode == expect_rc, (
        f"迁移脚本 rc={result.returncode}（期望 {expect_rc}）\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result.returncode, result.stdout, result.stderr


def _insert_via_raw_sql(tmp_db_dir, *, amount=None, currency=None, ledger=None):
    """绕过 CLI，直接用 sqlite3 INSERT 脏数据，期望被 CHECK 拦截"""
    from db import DB_PATH, TABLE_NAME
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        # 确保 bills 表存在（init_db 没跑过的话）
        from db import init_db
        init_db()
        # 用 INSERT OR IGNORE 不会触发 IntegrityError？不，会触发，IntegrityError 是 CHECK 失败时的异常
        b = dict(VALID_BILL)
        if amount is not None:
            b["amount"] = amount
        if currency is not None:
            b["currency"] = currency
        if ledger is not None:
            b["ledger"] = ledger
        try:
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (b["category"], b["time"], b["amount"], b["account"],
                 b["ledger"], b["currency"], b["note"]),
            )
            conn.commit()
            return None  # 没抛异常 → INSERT 成功（不该走到这步）
        except sqlite3.IntegrityError as e:
            return e  # CHECK 触发
    finally:
        conn.close()


def _bills_sql(tmp_db_dir):
    """返回 bills 表的 CREATE SQL（含 CHECK 子句）"""
    from db import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.cursor()
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='bills'")
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


# ── 测试用例 ─────────────────────────────────────────────────────────────────

class TestMigrationScriptExists:
    """迁移脚本存在性 + 参数支持"""

    def test_migration_script_exists(self):
        assert MIGRATION_SCRIPT.exists(), f"迁移脚本不存在: {MIGRATION_SCRIPT}"

    def test_help_lists_dry_run_and_rollback(self, tmp_db_dir):
        rc, out, err = _run_migration(tmp_db_dir, "--help", expect_rc=0)
        # argparse 自动把 --dry-run / --rollback 列在 help 里
        assert "--dry-run" in out
        assert "--rollback" in out


class TestDryRun:
    """--dry-run 不修改 schema"""

    def test_dry_run_does_not_modify_schema(self, tmp_db_dir):
        from db import init_db
        init_db()
        sql_before = _bills_sql(tmp_db_dir)

        _run_migration(tmp_db_dir, "--dry-run", expect_rc=0)

        sql_after = _bills_sql(tmp_db_dir)
        assert sql_after == sql_before, (
            f"--dry-run 后 schema 变了\nbefore: {sql_before}\nafter: {sql_after}"
        )

    def test_dry_run_reports_pending_changes(self, tmp_db_dir):
        from db import init_db
        init_db()
        rc, out, err = _run_migration(tmp_db_dir, "--dry-run", expect_rc=0)
        # 报告会加 CHECK（如果没有的话）
        assert "CHECK" in out.upper() or "已存在" in out or "skip" in out.lower()


class TestCheckConstraintsApplied:
    """跑迁移后 bills 表含 3 个 CHECK"""

    def test_schema_contains_three_checks(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        sql = _bills_sql(tmp_db_dir)
        assert sql is not None
        # CHECK 子句数 ≥ 3
        check_count = sql.upper().count("CHECK")
        assert check_count >= 3, f"CHECK 子句数={check_count}（期望 ≥3）\nsql: {sql}"

    def test_check_amount_not_zero(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        sql = _bills_sql(tmp_db_dir).upper()
        # CHECK (amount != 0) — 容忍 SQLite 序列化空格差异（!= / <>）
        assert "AMOUNT != 0" in sql or "AMOUNT<>0" in sql or "AMOUNT <> 0" in sql

    def test_check_currency_in_whitelist(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        sql = _bills_sql(tmp_db_dir)
        # CHECK (currency IN ('CNY', '人民币'))
        assert "CURRENCY" in sql.upper()
        assert "CNY" in sql.upper()
        assert "人民币" in sql

    def test_check_ledger_not_empty(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        sql = _bills_sql(tmp_db_dir).upper()
        # CHECK (ledger IS NOT NULL AND ledger != '')
        assert "LEDGER IS NOT NULL" in sql
        assert "LEDGER != ''" in sql.upper() or "LEDGER<>''" in sql.upper()


class TestDirtyInsertsBlocked:
    """跑迁移后 INSERT 脏数据被 CHECK 拦截"""

    def test_zero_amount_blocked(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        err = _insert_via_raw_sql(tmp_db_dir, amount=0.0)
        assert err is not None, "amount=0 应被 CHECK 拦截"
        assert "CHECK" in str(err).upper()

    def test_bad_currency_blocked(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        err = _insert_via_raw_sql(tmp_db_dir, currency="USD")
        assert err is not None, "currency='USD' 应被 CHECK 拦截"
        assert "CHECK" in str(err).upper()

    def test_empty_ledger_blocked(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        err = _insert_via_raw_sql(tmp_db_dir, ledger="")
        assert err is not None, "ledger='' 应被 CHECK 拦截"
        assert "CHECK" in str(err).upper()

    def test_valid_bill_still_inserts(self, tmp_db_dir):
        """合法数据仍能写入"""
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        err = _insert_via_raw_sql(tmp_db_dir)  # 用 VALID_BILL 默认值
        assert err is None, f"合法记录不应被拦截: {err}"


class TestRollback:
    """--rollback 后 CHECK 消失，脏数据又能写入了"""

    def test_rollback_removes_checks(self, tmp_db_dir):
        from db import init_db
        init_db()
        # 1. 先 apply
        _run_migration(tmp_db_dir, expect_rc=0)
        sql_after_apply = _bills_sql(tmp_db_dir)
        assert "CHECK" in sql_after_apply.upper()

        # 2. rollback
        _run_migration(tmp_db_dir, "--rollback", expect_rc=0)
        sql_after_rollback = _bills_sql(tmp_db_dir)
        # CHECK 应消失（或数量减少）
        check_count = sql_after_rollback.upper().count("CHECK")
        # 容忍 db.py init_db 的 index 等；但 bills 表本身不应再含 CHECK
        # （CREATE TABLE 中的 CHECK 子句数应为 0）
        # 注意：CREATE INDEX 不算 CHECK，但 sqlite_master 只返回 CREATE TABLE sql
        assert check_count == 0 or "amount != 0" not in sql_after_rollback.lower(), (
            f"--rollback 后 bills 表仍含 CHECK: {sql_after_rollback}"
        )

    def test_zero_amount_inserts_after_rollback(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        _run_migration(tmp_db_dir, "--rollback", expect_rc=0)
        # rollback 后 amount=0 又能写了
        err = _insert_via_raw_sql(tmp_db_dir, amount=0.0)
        assert err is None, f"rollback 后 amount=0 应能写: {err}"


class TestIdempotent:
    """迁移幂等：跑两次不报错"""

    def test_run_twice_succeeds(self, tmp_db_dir):
        from db import init_db
        init_db()
        _run_migration(tmp_db_dir, expect_rc=0)
        # 第二次跑：应当识别「已存在」并跳过
        _run_migration(tmp_db_dir, expect_rc=0)
        sql = _bills_sql(tmp_db_dir)
        assert "CHECK" in sql.upper()
