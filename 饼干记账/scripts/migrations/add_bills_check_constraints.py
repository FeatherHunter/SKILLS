#!/usr/bin/env python3
"""add_bills_check_constraints.py — bills 表加 CHECK 约束（defense-in-depth）

依据 spec.md §Implementation Decisions #4 给 bills 表加 SQLite CHECK 约束：
  - CHECK (amount != 0)
  - CHECK (currency IN ('CNY', '人民币'))
  - CHECK (ledger IS NOT NULL AND ledger != '')

支持：
  --dry-run   仅打印将要做什么，不修改 schema
  --rollback  移除 CHECK 约束（重建无 CHECK 的表）

幂等：再跑一次会识别「已存在 / 已不存在」并跳过。

技术限制：SQLite 不支持 ALTER TABLE ADD CONSTRAINT，必须用
「CREATE NEW → INSERT ... SELECT → DROP OLD → RENAME」模式重建表。

依赖：跑前会调用 db.init_db() 确保 bills 表存在。
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent.parent  # scripts/migrations/.. → .. = skill root
_SCRIPTS_PARENT = _SCRIPT_DIR.parent  # scripts/
if str(_SCRIPTS_PARENT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PARENT))

from db import DB_PATH, TABLE_NAME, init_db  # noqa: E402

# 迁移前 CSV 备份目录（与生产 backups/ 一致：skill_root/backups/）
BACKUPS_DIR = _SKILL_DIR / "backups"


# ── schema 定义 ─────────────────────────────────────────────────────────────

# 含 CHECK 的 CREATE TABLE
SCHEMA_WITH_CHECK = f"""
CREATE TABLE {TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    time TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount != 0),
    account TEXT DEFAULT '',
    ledger TEXT DEFAULT '生活' CHECK (ledger IS NOT NULL AND ledger != ''),
    currency TEXT DEFAULT '人民币' CHECK (currency IN ('CNY', '人民币')),
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

# 无 CHECK 的 CREATE TABLE（rollback 用，与 db.py init_db 原始定义对齐）
SCHEMA_WITHOUT_CHECK = f"""
CREATE TABLE {TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    time TEXT NOT NULL,
    amount REAL NOT NULL,
    account TEXT DEFAULT '',
    ledger TEXT DEFAULT '生活',
    currency TEXT DEFAULT '人民币',
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""


# ── 辅助函数 ─────────────────────────────────────────────────────────────────

def _get_bills_sql(conn) -> str:
    """返回 bills 表的 CREATE SQL"""
    cur = conn.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,))
    row = cur.fetchone()
    return row[0] if row else ""


def _has_checks(bills_sql: str) -> bool:
    """判断 CREATE SQL 是否含 CHECK 子句"""
    return "CHECK" in bills_sql.upper()


def _backup_bills_csv(conn) -> Path | None:
    """迁移前把 bills 全量数据备份成 CSV（一次性安全网）。

    若 bills 表为空则跳过；返回备份文件路径或 None。
    备份目录 BACKUPS_DIR（= skill_root/backups/）。
    """
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
    n = cur.fetchone()[0]
    if n == 0:
        return None

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = BACKUPS_DIR / f"bills_pre_check_constraints_{ts}.csv"

    cur.execute(f"SELECT id, category, time, amount, account, ledger, currency, note, created_at FROM {TABLE_NAME}")
    rows = cur.fetchall()
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "category", "time", "amount", "account", "ledger", "currency", "note", "created_at"])
        for row in rows:
            writer.writerow(row)
    return csv_path


def _rebuild_table(conn, new_schema_sql: str) -> None:
    """重建 bills 表：
    1. 用 new_schema_sql 创建 bills_new
    2. INSERT INTO bills_new SELECT * FROM bills
    3. DROP TABLE bills
    4. ALTER TABLE bills_new RENAME TO bills
    5. 重建索引
    """
    cur = conn.cursor()
    tmp_name = f"{TABLE_NAME}__migration_tmp"

    # 把 SCHEMA 中的 {TABLE_NAME} 换成 tmp_name（new_schema_sql 已含 CREATE TABLE）
    tmp_schema = new_schema_sql.replace(TABLE_NAME, tmp_name, 1)
    # 但是 PRIMARY KEY AUTOINCREMENT 必须用 bills 这个名字吗？不是，可以用任意名
    cur.executescript(tmp_schema)

    # 复制数据
    cur.execute(
        f"INSERT INTO {tmp_name} (id, category, time, amount, account, ledger, currency, note, created_at) "
        f"SELECT id, category, time, amount, account, ledger, currency, note, created_at FROM {TABLE_NAME}"
    )

    # 旧表删掉
    cur.execute(f"DROP TABLE {TABLE_NAME}")

    # 重命名
    cur.execute(f"ALTER TABLE {tmp_name} RENAME TO {TABLE_NAME}")

    # 重建索引（db.py init_db 里的两个）
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_time ON {TABLE_NAME}(time)")
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_category ON {TABLE_NAME}(category)")

    conn.commit()


# ── 主流程 ───────────────────────────────────────────────────────────────────

def cmd_apply(conn, dry_run: bool = False) -> int:
    """加 CHECK 约束（幂等）"""
    bills_sql = _get_bills_sql(conn)
    if _has_checks(bills_sql):
        print(f"✓ bills 表已含 CHECK 约束，跳过")
        return 0

    print(f"📥 将给 bills 表加 3 个 CHECK 约束：")
    print(f"   1. CHECK (amount != 0)")
    print(f"   2. CHECK (currency IN ('CNY', '人民币'))")
    print(f"   3. CHECK (ledger IS NOT NULL AND ledger != '')")

    if dry_run:
        print(f"   [DRY-RUN] 不修改 schema")
        return 0

    # 真做前先备份 CSV（防御性）
    backup_path = _backup_bills_csv(conn)
    if backup_path:
        print(f"   已备份到: {backup_path}")

    # 真做：表重建
    print(f"🔧 开始重建 bills 表（含 CHECK）...")
    _rebuild_table(conn, SCHEMA_WITH_CHECK)
    print(f"✓ 已加 CHECK 约束")
    return 0


def cmd_rollback(conn, dry_run: bool = False) -> int:
    """移除 CHECK 约束（幂等）"""
    bills_sql = _get_bills_sql(conn)
    if not _has_checks(bills_sql):
        print(f"✓ bills 表已无 CHECK 约束，跳过 rollback")
        return 0

    print(f"📥 将从 bills 表移除 CHECK 约束")

    if dry_run:
        print(f"   [DRY-RUN] 不修改 schema")
        return 0

    print(f"🔧 开始重建 bills 表（无 CHECK）...")
    _rebuild_table(conn, SCHEMA_WITHOUT_CHECK)
    print(f"✓ 已移除 CHECK 约束")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="给 bills 表加 SQLite CHECK 约束（amount!=0 / currency 白名单 / ledger 非空）"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不修改 schema")
    parser.add_argument("--rollback", action="store_true", help="移除 CHECK 约束")
    args = parser.parse_args()

    print(f"📄 数据库: {DB_PATH}")

    # 确保表存在
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        if args.rollback:
            return cmd_rollback(conn, dry_run=args.dry_run)
        return cmd_apply(conn, dry_run=args.dry_run)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
