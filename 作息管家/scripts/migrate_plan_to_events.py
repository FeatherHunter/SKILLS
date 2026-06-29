# -*- coding: utf-8 -*-
"""
migrate_plan_to_events.py — 老 schedule_plans 表迁移脚本（idempotent）

目的:
  把旧表（24 个 hour_N_planned 字段的"按小时格子"模型）
  迁移到新表（按事件"time_start / time_end / title / notes"模型）。

旧表 → 新表映射:
  每个 (date, hour_N_planned)  →  1 条新表记录
    time_start = "{N:02d}:00"
    time_end   = "{N+1:02d}:00"   (hour_23 → "24:00" 哨兵)
    title      = hour_N_planned 原文
    notes      = NULL
    category   = NULL
    feishu_event_id = NULL
    last_synced_at  = NULL
    is_active = 1

幂等性:
  检测到 schedule_plans_legacy_2026_06_29 已存在 → 直接退出
  检测到 schedule_plans 表已带新 schema → 旧表若还在则 RENAME
  否则 → 旧表如果存在就 RENAME + 建新表 + 迁数据
  否则 → 直接建新表（全新安装）

用法:
  python scripts/migrate_plan_to_events.py
"""

import sqlite3
import sys
from pathlib import Path

# 复用 schedule_db 的路径解析，保持 DB 一致
sys.path.insert(0, str(Path(__file__).parent))
from schedule_db import get_connection, DB_PATH

LEGACY_TABLE_NAME = "schedule_plans_legacy_2026_06_29"
NEW_TABLE_NAME = "schedule_plans"


def table_columns(conn, table_name: str) -> set[str]:
    """取表的全部列名（用于判断 schema 类型）"""
    c = conn.cursor()
    rows = c.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {r[1] for r in rows}


def table_exists(conn, table_name: str) -> bool:
    c = conn.cursor()
    r = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return r is not None


def has_new_schema(conn, table_name: str) -> bool:
    """判断某表是否为新版 schema（必含 time_start + is_active + feishu_event_id）"""
    if not table_exists(conn, table_name):
        return False
    cols = table_columns(conn, table_name)
    return {"time_start", "is_active", "feishu_event_id"}.issubset(cols)


def create_new_schema(conn) -> None:
    """CREATE 新 schedule_plans 表（含索引）"""
    c = conn.cursor()
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {NEW_TABLE_NAME} (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            time_start      TEXT    NOT NULL,
            time_end        TEXT    NOT NULL,
            title           TEXT    NOT NULL,
            notes           TEXT,
            category        TEXT,
            feishu_event_id TEXT,
            last_synced_at  TEXT,
            is_active       INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT    DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute(f'CREATE INDEX IF NOT EXISTS idx_plans_date ON {NEW_TABLE_NAME}(date)')
    c.execute(f'CREATE INDEX IF NOT EXISTS idx_plans_date_time ON {NEW_TABLE_NAME}(date, time_start)')
    conn.commit()


def migrate_data_from(conn, src_table: str) -> int:
    """从 src_table 读旧 24-hour 数据，INSERT 到新表。
    src_table 必须有 date + hour_0_planned..hour_23_planned 列。"""
    c = conn.cursor()
    cols = table_columns(conn, src_table)
    # 安全检查：源表应有 24 个 hour_N_planned 列
    needed = {f"hour_{i}_planned" for i in range(24)}
    if not needed.issubset(cols):
        raise RuntimeError(f"{src_table} 不是旧 schema（缺 hour_N_planned 列），放弃迁移")

    rows = c.execute(
        f"SELECT date, {', '.join(f'hour_{i}_planned' for i in range(24))} FROM {src_table}"
    ).fetchall()

    inserted = 0
    for row in rows:
        date_val = row[0]
        for h in range(24):
            title = row[1 + h]
            if title is None or not str(title).strip():
                continue
            time_start = f"{h:02d}:00"
            time_end = f"{h+1:02d}:00" if h < 23 else "24:00"
            c.execute(f'''
                INSERT INTO {NEW_TABLE_NAME}
                    (date, time_start, time_end, title, notes, category,
                     feishu_event_id, last_synced_at, is_active)
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 1)
            ''', (date_val, time_start, time_end, str(title).strip()))
            inserted += 1
    conn.commit()
    return inserted


def main():
    print("=" * 60)
    print("  作息管家 — 老 schedule_plans 表迁移脚本")
    print("=" * 60)
    print(f"  DB: {DB_PATH}")
    print()

    conn = get_connection()
    try:
        # 1) 幂等：legacy 已存在则跳过
        if table_exists(conn, LEGACY_TABLE_NAME):
            print(f"  → 检测到 {LEGACY_TABLE_NAME} 已存在，迁移已完成。")
            print(f"  → 旧数据全部保留在该表中，必要时可手动回滚。")
            if not table_exists(conn, NEW_TABLE_NAME):
                print(f"  → 但 {NEW_TABLE_NAME} 不存在！请手动检查或重新跑 init。")
            return

        legacy_exists = table_exists(conn, LEGACY_TABLE_NAME)
        new_exists = table_exists(conn, NEW_TABLE_NAME)
        new_is_new_schema = new_exists and has_new_schema(conn, NEW_TABLE_NAME)

        # 2) 三种场景：
        #    a. 旧表存在 + 新表不存在（最常见——init_db 跑过旧 schema）
        #    b. 旧表存在 + 新表已建好（新 schema，例如本脚本上一步异常中断）
        #    c. 全新 DB（什么都没有）

        if new_is_new_schema:
            # 场景 b：新表已建好，旧表还在 → 直接把旧表重命名
            print(f"  → 新 schema 已存在 (含 time_start/is_active/feishu_event_id)")
            if table_exists(conn, "schedule_plans_backup_for_migration"):
                # 极端情况：本脚本上次异常中断但留了 backup，删掉重来
                conn.execute("DROP TABLE schedule_plans_backup_for_migration")
            # 此时 "schedule_plans" 已指向新版；旧表的原名应还在 → 但实际上旧版 schema
            # 已被新版覆盖，sqlite_master 里只能看到一个 schedule_plans
            # 此场景主要发生在"中途崩溃"
            print(f"  → 旧表处理：跳过（如有残留的旧表，请手动处理）")
            print(f"  → 迁移完成。")
            return

        old_table_to_rename = None
        if table_exists(conn, "schedule_plans"):
            cols = table_columns(conn, "schedule_plans")
            if {"time_start", "is_active"}.issubset(cols):
                # 不可能（已经走到上面的 new_is_new_schema 分支）
                pass
            elif {"hour_0_planned"}.issubset(cols):
                # 旧 schema
                old_table_to_rename = "schedule_plans"
            else:
                print(f"  → schedule_plans 表既不是旧 schema 也不是新 schema，字段：{sorted(cols)}")
                print(f"  → 请人工检查后重跑。")
                return

        if old_table_to_rename:
            # ---- 常规路径：旧表 + 无新表 ----
            print(f"  [1/4] 把旧 {old_table_to_rename} 重命名 → {LEGACY_TABLE_NAME} ...")
            conn.execute(f"ALTER TABLE {old_table_to_rename} RENAME TO {LEGACY_TABLE_NAME}")
            conn.commit()
            print("        OK")

            print(f"  [2/4] CREATE 新 schema (schedule_plans) ...")
            create_new_schema(conn)
            print("        OK")

            print(f"  [3/4] 从 {LEGACY_TABLE_NAME} 迁数据 → 新表 ...")
            n = migrate_data_from(conn, LEGACY_TABLE_NAME)
            print(f"        OK，迁移了 {n} 条记录")

            print(f"  [4/4] 校验：新表活跃记录数 ...")
            count = conn.execute(
                f"SELECT COUNT(*) FROM {NEW_TABLE_NAME} WHERE is_active=1"
            ).fetchone()[0]
            print(f"        新表活跃事件数：{count}")
            print()
            print("=" * 60)
            print(f"  ✅ 迁移完成。")
            print(f"  旧表保留为: {LEGACY_TABLE_NAME}")
            print(f"  新表已就绪: {NEW_TABLE_NAME}（11 字段含 is_active / feishu_event_id）")
            print(f"  旧表路径: {DB_PATH}")
            print("=" * 60)
        else:
            # ---- 全新 DB ----
            print(f"  → 当前 DB 不存在 schedule_plans 表（全新安装），直接建新表 ...")
            create_new_schema(conn)
            print("        OK")
            print()
            print("=" * 60)
            print(f"  ✅ 全新安装完成：新 {NEW_TABLE_NAME} 表已就绪。")
            print(f"  新表路径: {DB_PATH}")
            print("=" * 60)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
