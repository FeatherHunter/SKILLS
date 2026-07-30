#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 Jimmy Dean 鸡排/松饼的营养成分存到卡路里食品库(nutrition_products)"""
import sqlite3
import subprocess
import sys
from pathlib import Path

CLI = r"D:\2Study\StudyNotes\SKILLS\卡路里\scripts\calorie_tracker.py"
DB = r"D:\2Study\StudyNotes\.db\calorie_data.db"

# 1) 清掉刚才的 test 记录
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("DELETE FROM nutrition_products WHERE product_name = 'test'")
conn.commit()
print(f"[清] test 记录删除: {cur.rowcount} 行\n")
conn.close()

SOURCE = "包装标签实测 2026-07-30(山姆极速达 Jimmy Dean Chicken Fillet & Biscuit Combo,生产日 2026-04-23,过期日 2027-01-17)"

# 2) 鸡排:178 kcal/14.4g 蛋白/7.2g 脂肪/0.9g 饱/13.7g 碳/1.9g 糖/纤维 0/598mg 钠
print("[1] 鸡排 add:")
r1 = subprocess.run([
    sys.executable, CLI, "add-product",
    "Jimmy Dean 鲜炸鸡排(速冻调制食品)",  # product_name
    "Jimmy Dean",                          # brand
    "178",                                  # calories (kcal/100g)
    "14.4",                                 # protein
    "7.2",                                  # fat
    "0.9",                                  # saturated_fat
    "13.7",                                 # carbs
    "1.9",                                  # sugar
    "0",                                    # fiber (包装未标)
    "598",                                  # sodium (mg)
    f"SB/T 10379,保质期 9 个月,冷冻 -18°C 贮存,2026-04-23 生产,2027-01-17 过期。{SOURCE}",
], capture_output=True, text=True, encoding="utf-8")
print(r1.stdout)
if r1.stderr: print("STDERR:", r1.stderr)
print(f"exit: {r1.returncode}\n")

# 3) 松饼:426 kcal/6.2g 蛋白/23.8g 脂肪/13.5g 饱/46.8g 碳/4.9g 糖/纤维 0/746mg 钠
print("[2] 松饼 add:")
r2 = subprocess.run([
    sys.executable, CLI, "add-product",
    "Jimmy Dean 黄油松饼(糕点)",  # product_name
    "Jimmy Dean",                  # brand
    "426",                          # calories
    "6.2",                          # protein
    "23.8",                         # fat
    "13.5",                         # saturated_fat
    "46.8",                         # carbs
    "4.9",                          # sugar
    "0",                            # fiber (包装未标)
    "746",                          # sodium
    f"GB 7099(糕点国标),含法国进口黄油 ≥6%,冷冻 -18°C 贮存,2026-04-23 生产,2027-01-17 过期。{SOURCE}",
], capture_output=True, text=True, encoding="utf-8")
print(r2.stdout)
if r2.stderr: print("STDERR:", r2.stderr)
print(f"exit: {r2.returncode}")
