# -*- coding: utf-8 -*-
"""规格阶段 · 底层 DB 数据盘点（只读，不写任何数据）

用途：三层评估法的第 1 层——摸清 schedule_data.db 到底存了什么。
运行：python scripts/audit_db.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from schedule_db import DB_PATH  # noqa: E402

TABLES = ("schedule_records", "daily_summary", "schedule_plans",
          "schedule_plans_legacy_2026_06_29")


def main():
    print(f"DB: {DB_PATH}\n")
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    print("== 各表行数 ==")
    for t in TABLES:
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {n}")
        except sqlite3.OperationalError as e:
            print(f"  {t}: ERR {e}")

    print("\n== schedule_records 覆盖 ==")
    print("  日期范围:", cur.execute(
        "SELECT MIN(date), MAX(date) FROM schedule_records").fetchone())
    print("  有数据的天数:", cur.execute(
        "SELECT COUNT(DISTINCT date) FROM schedule_records").fetchone()[0])
    print("  记录最多的 5 天:")
    for d, n in cur.execute(
            "SELECT date, COUNT(*) FROM schedule_records GROUP BY date "
            "ORDER BY COUNT(*) DESC LIMIT 5"):
        print(f"    {d}: {n} 条")
    print("  分类分布(前 12):")
    for cat, n in cur.execute(
            "SELECT category, COUNT(*) FROM schedule_records "
            "GROUP BY category ORDER BY COUNT(*) DESC LIMIT 12"):
        print(f"    {cat}: {n}")

    print("\n== daily_summary 覆盖 ==")
    print("  行数:", cur.execute("SELECT COUNT(*) FROM daily_summary").fetchone()[0])
    print("  天数:", cur.execute(
        "SELECT COUNT(DISTINCT date) FROM daily_summary").fetchone()[0])
    print("  日期范围:", cur.execute(
        "SELECT MIN(date), MAX(date) FROM daily_summary").fetchone())

    print("\n== schedule_plans 覆盖 ==")
    print("  日期范围:", cur.execute(
        "SELECT MIN(date), MAX(date) FROM schedule_plans").fetchone())
    print("  有计划的天数:", cur.execute(
        "SELECT COUNT(DISTINCT date) FROM schedule_plans").fetchone()[0])
    print("  完成状态:", cur.execute(
        "SELECT completion, COUNT(*) FROM schedule_plans GROUP BY completion").fetchall())
    print("  is_active=0 数量:", cur.execute(
        "SELECT COUNT(*) FROM schedule_plans WHERE is_active=0").fetchone()[0])
    print("  已同步飞书事件数:", cur.execute(
        "SELECT COUNT(*) FROM schedule_plans WHERE feishu_event_id IS NOT NULL AND feishu_event_id != ''").fetchone()[0])

    con.close()


if __name__ == "__main__":
    main()
