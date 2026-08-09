#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""用 Python 跑 backfill,保存为 UTF-8 JSON(避免 PowerShell 重定向的 UTF-16 问题)"""
from _io_guard import guard_io; guard_io()
import subprocess
import json
import sys
from pathlib import Path

CLI = r"D:\2Study\StudyNotes\SKILLS\卡路里\scripts\xunji_bridge.py"
out = sys.argv[1]

r = subprocess.run(
    [sys.executable, CLI, "backfill", "--days", "7"],
    capture_output=True, text=True, encoding="utf-8"
)
data = json.loads(r.stdout)
Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ 已保存到 {out}")
print(f"end_date={data['end_date']} days={data['days']} inserted={data['total_inserted']} updated={data['total_updated']}")
