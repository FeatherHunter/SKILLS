#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""记这笔山姆订单支出,避免 PowerShell 5.1 中文乱码"""
import subprocess
import sys
import json

CLI = r"D:\2Study\StudyNotes\SKILLS\饼干记账\scripts\record_bill.py"

r = subprocess.run(
    [
        sys.executable, CLI, "add",
        "--category", "餐饮/食材",
        "--amount", "-130.70",
        "--time", "2026-07-30 16:59:36",
        "--account", "支付宝",
        "--note", "山姆:Member's Mark鲜鸡蛋30枚 + Jimmy Dean鸡排松饼1.256kg + 湾仔码头黑猪肉大白菜水饺81只",
    ],
    capture_output=True, text=True, encoding="utf-8"
)

print("=== STDOUT ===")
print(r.stdout)
print("=== STDERR ===")
print(r.stderr)
print(f"=== EXIT: {r.returncode} ===")
