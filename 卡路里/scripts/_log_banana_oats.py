#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""记吃了:香蕉 200g + 山姆快熟燕麦片 50g"""
import subprocess
import sys

CLI = r"D:\2Study\StudyNotes\SKILLS\卡路里\scripts\calorie_tracker.py"

# 香蕉 200g:89 × 2 = 178 kcal;1.1 × 2 = 2.2g 蛋白;22.8 × 2 = 45.6g 碳;0.3 × 2 = 0.6g 脂肪
print("[1] 香蕉 200g")
r1 = subprocess.run([
    sys.executable, CLI, "add",
    "香蕉(去皮,生)",  # 食物名
    "178",            # 该份量热量(89×2)
    "2.2",            # 蛋白
    "0.6",            # 脂肪
    "0",              # 饱和脂肪(库没存,可省或传 0)
    "45.6",           # 碳水
    "0",              # 糖
    "0",              # 膳食纤维
    "2",              # 钠 mg(1×2=2)
    "200",            # 克数
], capture_output=True, text=True, encoding="utf-8")
print(r1.stdout)
if r1.stderr: print("STDERR:", r1.stderr)

# 燕麦 50g:412 × 0.5 = 206 kcal;12.2 × 0.5 = 6.1g 蛋白;54.7 × 0.5 = 27.35g 碳;13.6 × 0.5 = 6.8g 脂肪
print("\n[2] 山姆高纤快熟燕麦片 50g")
r2 = subprocess.run([
    sys.executable, CLI, "add",
    "Member's Mark高纤快熟燕麦片",
    "206",
    "6.1",
    "6.8",
    "0",
    "27.35",
    "0",
    "0",
    "3",        # 钠 6×0.5=3
    "50",
], capture_output=True, text=True, encoding="utf-8")
print(r2.stdout)
if r2.stderr: print("STDERR:", r2.stderr)
