#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查 DB 看是否有"厨房冰箱冷冻层",并显示所有 item_locations 位置分布"""
import sqlite3

DB = r"D:\2Study\StudyNotes\.db\home.db"
c = sqlite3.connect(DB).cursor()

# 1) 查"厨房冰箱冷冻层"
print("=== 搜索 '厨房冰箱冷冻层' ===")
c.execute("SELECT item_id, location, quantity, location_status FROM item_locations WHERE location LIKE '%厨房%冷冻层%'")
for r in c.fetchall():
    print(r)

# 2) 查"厨房冰箱"任何位置
print("\n=== 搜索 '厨房冰箱' (任何) ===")
c.execute("SELECT item_id, location, quantity, location_status FROM item_locations WHERE location LIKE '%厨房冰箱%'")
for r in c.fetchall():
    print(r)

# 3) 查所有位置分布(去重)
print("\n=== 全部 item_locations 位置去重 ===")
c.execute("SELECT DISTINCT location FROM item_locations ORDER BY location")
for r in c.fetchall():
    print(" ", r[0])
