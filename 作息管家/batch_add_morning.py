#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量为 2026-08-04 ~ 2026-08-31 每天补 3 条晨练计划。
幂等:走 ensure-plan-event(date, time_start, time_end, title),三元组查重。
"""
import subprocess
import json
import sys
from datetime import date, timedelta

CLI = "scripts/schedule_cli.py"
START = date(2026, 8, 4)
END = date(2026, 8, 31)
DAYS = (END - START).days + 1  # 28

# (time_start, time_end, title, category, notes)
EVENTS = [
    ("09:00", "09:20", "八段锦",     "健康.八段锦", "晨练·八段锦"),
    ("09:20", "09:40", "固定练习",   "健康.健身",   "晨练·固定练习"),
    ("09:40", "10:00", "元母意程",   "健康.修行",   "晨练·元母意程"),
]

def call_cli(*args):
    """调 CLI,返回 (ok, payload)"""
    proc = subprocess.run(
        [sys.executable, CLI, *args],
        capture_output=True, text=True, encoding="utf-8",
    )
    out = proc.stdout.strip()
    try:
        data = json.loads(out)
    except Exception:
        return False, {"raw_stdout": out, "raw_stderr": proc.stderr}
    return data.get("status") == "ok", data

def main():
    total = 0
    ok = 0
    skipped = 0
    failed = []
    new_ids = []
    for i in range(DAYS):
        d = START + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        for ts, te, title, cat, note in EVENTS:
            total += 1
            success, payload = call_cli(
                "ensure-plan-event", d_str,
                "--time-start", ts, "--time-end", te,
                "--title", title, "--category", cat,
                "--notes", note,
            )
            if success:
                # 看 data.found / data.id 判断新建 or 跳过
                inner = payload.get("data", {})
                if inner.get("created") or inner.get("is_new") or "id" in inner and not inner.get("found"):
                    new_ids.append((d_str, ts, te, title, inner.get("id")))
                    ok += 1
                else:
                    skipped += 1
            else:
                failed.append((d_str, ts, te, title, payload.get("message", str(payload))))

    print("=" * 60)
    print(f"日期范围: {START} ~ {END} ({DAYS} 天)")
    print(f"总条数: {total} ({DAYS} 天 × 3 条)")
    print(f"✓ 新建: {ok}")
    print(f"⊘ 跳过(已存在/幂等): {skipped}")
    print(f"✗ 失败: {len(failed)}")
    if failed:
        print("\n失败明细:")
        for d, ts, te, title, msg in failed:
            print(f"  {d} {ts}-{te} {title}: {msg}")
    print("=" * 60)
    if new_ids:
        print(f"\n新建 ID 范围: {new_ids[0][4]} ~ {new_ids[-1][4]} (示例)")

if __name__ == "__main__":
    main()
