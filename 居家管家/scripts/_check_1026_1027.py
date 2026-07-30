#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""查 ID 1026/1027 的完整状态 + schema"""
import sqlite3

DB = r"D:\2Study\StudyNotes\.db\home.db"
c = sqlite3.connect(DB).cursor()

# 查 items 表 schema
c.execute("PRAGMA table_info(items)")
print("ITEMS columns:", [r[1] for r in c.fetchall()])

c.execute("PRAGMA table_info(item_locations)")
print("ITEM_LOCATIONS columns:", [r[1] for r in c.fetchall()])

c.execute("PRAGMA table_info(item_tags)")
print("ITEM_TAGS columns:", [r[1] for r in c.fetchall()])

print()
for item_id in (1026, 1027):
    print(f"========== ID {item_id} ==========")
    c.execute("SELECT name, remark FROM items WHERE id=?", (item_id,))
    r = c.fetchone()
    if r:
        print(f"NAME: {r[0]}")
        print(f"REMARK: {r[1]}")
    c.execute("SELECT location, location_status, expiration_date, purchase_date FROM item_locations WHERE item_id=?", (item_id,))
    for loc in c.fetchall():
        print(f"LOCATION: {loc[0]} | status={loc[1]} | exp={loc[2]} | pur={loc[3]}")
    c.execute("SELECT tag FROM item_tags WHERE item_id=?", (item_id,))
    tags = [t[0] for t in c.fetchall()]
    print(f"TAGS ({len(tags)}): {tags}")
    print()
