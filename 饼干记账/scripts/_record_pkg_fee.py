#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""补一笔 -2.00 山姆订单包装费(拆细时漏记)"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\饼干记账\scripts\record_bill.py"

r = subprocess.run([
    sys.executable, CLI, "add",
    "--category", "其他",
    "--amount", "-2.00",
    "--time", "2026-07-30 16:59:36",
    "--account", "支付宝",
    "--note", "山姆极速达订单包装费(20260730 订单 流水号 2607301659405561281000171,商品 -128.70 + 包装 -2.00 + 配送 0 = 实付 130.70,拆细时漏记这笔包装费)",
], capture_output=True, text=True, encoding="utf-8")

print("STDOUT:", r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
