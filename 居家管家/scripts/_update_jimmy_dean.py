#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ID=1027 Jimmy Dean 加主图 + 增量 tag"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"

PHOTO = r"D:\2Study\StudyNotes\.db\HomeHub\photos\待录入_松饼主图.jpg"

r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1027",
    "--add-tag", "8 Count/Box,鸡排696g,松饼560g,法国进口黄油,冷鲜鸡胸肉,1+1 combo,鸡排松饼分开装,Quality Guaranteed,含铝箔包装,需冷冻保存,美式早餐",
    "--photo", PHOTO,
], capture_output=True, text=True, encoding="utf-8")

print("STDOUT:", r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
