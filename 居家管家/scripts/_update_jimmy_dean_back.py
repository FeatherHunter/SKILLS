#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ID=1027 Jimmy Dean 加背面信息(过期日期/经销商/加热方式)"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\居家管家\scripts\home_manager.py"

r = subprocess.run([
    sys.executable, CLI, "update",
    "--id", "1027",
    "--expiration-date", "2027-01-17",
    "--add-tag", "9个月保质期,2026-04-23生产,2027-01-17过期,泰森华东,空气炸锅200°C,烤箱180°C,微波30秒,无需解冻,锡纸包裹,条形码6923146015261",
    "--remark", "山姆会员商店极速达,Jimmy Dean 美式鸡排松饼组合装,1.256kg(鸡排 696g + 松饼 560g),共 8 份(1 鸡排+1 松饼 = 1 count,鸡排和松饼分开装),盒装含铝箔。经销商:泰森华东食品发展有限公司(江苏南通),始于1989。需 -18°C 及以下冷冻贮存(冷藏会坏,保质期 9 个月)。**加热无需解冻**:①空气炸锅 200°C 鸡排 6min,加松饼翻面再 6min ②烤箱 180°C 同 6+6min ③松饼微波中火 30s / 鸡排油炸 165°C 5min。锡纸包裹食用(防松饼碎掉)。生产日期 2026-04-23(TRZ6135),保质到期 2027-01-17。购买日 2026-07-30。条形码 6923146015261。",
], capture_output=True, text=True, encoding="utf-8")

print("STDOUT:", r.stdout)
if r.stderr:
    print("STDERR:", r.stderr)
print(f"exit: {r.returncode}")
