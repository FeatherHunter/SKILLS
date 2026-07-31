#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""记一笔菜园子果蔬 ¥4.00 暂存"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\饼干记账\scripts\record_bill.py"

r = subprocess.run([
    sys.executable, CLI, "add",
    "--category", "餐饮/日常采购",
    "--amount", "-4.00",
    "--time", "2026-07-31 14:11:00",
    "--account", "花呗",
    "--note", "菜园子果蔬(具体菜名未告知) 商品 ¥5.00 + 优惠(碰友日立减) -¥1.00 = 实付 ¥4.00,支付宝支付,2026-07-31 14:11。后续如知道具体菜名,可 update 备注或拆细。",
], capture_output=True, text=True, encoding="utf-8")
print("STDOUT:", r.stdout)
if r.stderr: print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
