import sqlite3

conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()
cur.execute('SELECT id, time, food_name, calories, protein, carbs, fat, grams FROM food_log WHERE date = "2026-07-12" ORDER BY created_at')
rows = cur.fetchall()

print(f"{'ID':>4s} | {'时间':<8s} | {'食物':<22s} | {'热量':>6s} | {'蛋白':>5s} | {'碳水':>5s} | {'脂肪':>5s} | {'克数':>6s}")
print("-" * 100)
for r in rows:
    print(f"{r[0]:4d} | {r[1]:<8s} | {r[2]:<22s} | {r[3]:6.1f} | {r[4]:5.1f} | {r[5]:5.1f} | {r[6]:5.1f} | {r[7]:6.1f}")

cur.execute('SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*) FROM food_log WHERE date = "2026-07-12"')
tot = cur.fetchone()
print("-" * 100)
print(f"{'':>4s} | {'合计':<22s} | {tot[0]:6.1f} | {tot[1]:5.1f} | {tot[2]:5.1f} | {tot[3]:5.1f} | {'':>6s} | {tot[4]:.0f} 条")
conn.close()
