# -*- coding: utf-8 -*-
import subprocess, sys, sqlite3

# 营养按每 100g 估算
# 牛排汉堡(类似巨无霸) 250 千卡/100g, P13/C25/F11
# 蛋糕 340 千卡/100g, P4/C33/F20
# 馒头 220 千卡/100g, P7/C47/F1
# 米饭 116 千卡/100g, P2.6/C25/F0.3
# 辣椒炒肉 170 千卡/100g, P8/C5/F12
# 肉末茄子 130 千卡/100g, P3/C8/F9

items = [
    ("牛排汉堡(AI估算)", "350", "26.0", "50.0", "22.0", "200",
     "2026-08-16", "12:00:00", "午餐",
     "AI估算,牛排汉堡 1 个~200g(类似巨无霸级)·库无"),
    ("蛋糕(AI估算)", "680", "8.0", "66.0", "40.0", "200",
     "2026-08-16", "15:00:00", "下午茶",
     "AI估算,蛋糕 200g·库无(可按花蛋糕/磅蛋糕估算)"),
    ("馒头", "220", "14.0", "94.0", "2.0", "200",
     "2026-08-16", "18:00:00", "晚餐",
     "AI估算,馒头 2 个~200g·库无"),
    ("米饭", "290", "6.5", "63.0", "0.8", "250",
     "2026-08-16", "18:00:00", "晚餐",
     "AI估算,米饭 250g·库无"),
    ("辣椒炒肉", "680", "32.0", "20.0", "48.0", "400",
     "2026-08-16", "18:00:00", "晚餐",
     "AI估算,辣椒炒肉 400g·库无"),
    ("肉末茄子", "260", "6.0", "16.0", "18.0", "200",
     "2026-08-16", "18:00:00", "晚餐",
     "AI估算,肉末茄子 200g·库无"),
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
cur.execute("SELECT COUNT(*), COALESCE(SUM(calories),0) FROM food_log WHERE date='2026-08-16'")
n, c = cur.fetchone()
print(f"\n8/16: {n} 条 · {c} 千卡")