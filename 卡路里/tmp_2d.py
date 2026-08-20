# -*- coding: utf-8 -*-
import sqlite3
db = r'D:\2Study\StudyNotes\.db\calorie_data.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("PRAGMA table_info(food_log)")
for r in cur.fetchall():
    print(r)

for d in ['2026-08-15', '2026-08-16']:
    print(f"\n=== {d} ===")
    cur.execute("""SELECT id, time, food_name, grams, calories, protein, note
                   FROM food_log WHERE date=? ORDER BY time""", (d,))
    rows = cur.fetchall()
    total = 0
    for r in rows:
        total += r[4]
        print(f"  {r}")
    print(f"  -- 共 {len(rows)} 条 · 合计 {total:.0f} 千卡 --")