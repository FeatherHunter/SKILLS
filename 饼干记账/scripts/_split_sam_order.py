#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 ID=6950 的 -130.70 拆成 3 笔(蛋/松饼/水饺),分类改用「日常采购」对齐 user 习惯"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\饼干记账\scripts\record_bill.py"

# 1) 把 6950 改成鸡蛋那笔
r1 = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "6950",
    "--category", "餐饮/日常采购",
    "--amount", "-18.90",
    "--note", "Member's Mark 精选鲜鸡蛋 1.59kg(30枚)",
], capture_output=True, text=True, encoding="utf-8")
print("=== 改 6950 → 鸡蛋 -18.90 ===")
print(r1.stdout)
if r1.stderr:
    print("STDERR:", r1.stderr)
print(f"exit: {r1.returncode}\n")

# 2) add 松饼
r2 = subprocess.run([
    sys.executable, CLI, "add",
    "--category", "餐饮/日常采购",
    "--amount", "-59.90",
    "--time", "2026-07-30 16:59:36",
    "--account", "支付宝",
    "--note", "Jimmy Dean 鸡排松饼组合 1.256kg",
], capture_output=True, text=True, encoding="utf-8")
print("=== add 松饼 -59.90 ===")
print(r2.stdout)
if r2.stderr:
    print("STDERR:", r2.stderr)
print(f"exit: {r2.returncode}\n")

# 3) add 水饺
r3 = subprocess.run([
    sys.executable, CLI, "add",
    "--category", "餐饮/日常采购",
    "--amount", "-49.90",
    "--time", "2026-07-30 16:59:36",
    "--account", "支付宝",
    "--note", "湾仔码头 黑猪肉大白菜水饺 1.62kg(81只)",
], capture_output=True, text=True, encoding="utf-8")
print("=== add 水饺 -49.90 ===")
print(r3.stdout)
if r3.stderr:
    print("STDERR:", r3.stderr)
print(f"exit: {r3.returncode}")
