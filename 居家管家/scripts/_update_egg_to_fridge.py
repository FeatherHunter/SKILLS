#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 ID=1026 鸡蛋移位置到客厅冰箱上层,加主图,同步过期日期,改存储 tag"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"

PHOTO_PATH = r"D:\2Study\StudyNotes\.db\HomeHub\photos\待录入_鸡蛋主图.jpg"

r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1026",
    "--new-location", "客厅/冰箱上层",
    "--location-status", "在家",
    "--expiration-date", "2026-08-26",
    "--remove-tag", "常温保存",
    "--add-tag", "冷藏保存,2°C-6°C,GB 2749,30天保质期,2026-08-26过期",
    "--photo", PHOTO_PATH,
], capture_output=True, text=True, encoding="utf-8")

print("STDOUT:", r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
