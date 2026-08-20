# -*- coding: utf-8 -*-
import subprocess, sys, sqlite3

# 把子肉 (卤五花肉) ~350 千卡/100g
# 卤蛋 ~200 千卡/100g
# 豆腐干 id 1442  427 千卡/100g
# 炒青菜  ~60 千卡/100g
# 蛋饺 ~220 千卡/100g

items = [
    ("把子肉(AI估算)", "357", "9.5", "0.5", "34.0", "102",
     "2026-08-17", "13:30:00", "午餐",
     "AI估算,把子肉 102g·库无"),
    ("卤蛋", "186", "13.5", "2.5", "13.4", "93",
     "2026-08-17", "13:30:00", "午餐",
     "AI估算,卤蛋 93g·库无"),
    ("豆腐干", "307", "14.1", "8.2", "25.3", "72",
     "2026-08-17", "13:30:00", "午餐",
     "库命中 id 1442·427 千卡/100g"),
    ("炒青菜(AI估算)", "53", "1.5", "5.0", "2.5", "89",
     "2026-08-17", "13:30:00", "午餐",
     "AI估算,炒青菜 89g·库无"),
    ("蛋饺(AI估算)", "167", "7.5", "5.0", "13.5", "76",
     "2026-08-17", "13:30:00", "午餐",
     "AI估算,蛋饺 76g·库无"),
]

for food, cal, p, c, f, grams, date, time, meal, note in items:
    r = subprocess.run(
        [sys.executable, "scripts/calorie_tracker.py", "add",
         food, cal, p, c, f, grams,
         "--date", date, "--time", time, "--meal", meal, "--note", note],
        capture_output=True, text=True, encoding="utf-8"
    )
    out = r.stdout.strip() or r.stderr.strip()
    print(f"  [{food[:20]}] {out[:150]}")

db = r'D:\2Study\StudyNotes\.db\calorie_data.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("SELECT COUNT(*), COALESCE(SUM(calories),0) FROM food_log WHERE date='2026-08-17'")
n, c = cur.fetchone()
print(f"\n8/17 今日: {n} 条 · {c} 千卡")