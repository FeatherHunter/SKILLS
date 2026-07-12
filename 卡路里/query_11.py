import sqlite3

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT id, food_name, calories, protein, carbs, fat, grams, note, created_at FROM entries WHERE date = "2026-07-11" ORDER BY created_at')
rows = cur.fetchall()

print(f"{'ID':>4s} | {'食物':<22s} | {'热量':>6s} | {'蛋白':>5s} | {'碳水':>5s} | {'脂肪':>5s} | {'克数':>6s} | 备注")
print("-" * 110)
for r in rows:
    note = r[7] if r[7] else ""
    print(f"{r[0]:4d} | {r[1]:<22s} | {r[2]:6.1f} | {r[3]:5.1f} | {r[4]:5.1f} | {r[5]:5.1f} | {r[6]:6.1f} | {note}")

cur.execute('SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*) FROM entries WHERE date = "2026-07-11"')
tot = cur.fetchall()
print("-" * 110)
print(f"{'':>4s} | {'合计':<22s} | {tot[0][0]:6.1f} | {tot[0][1]:5.1f} | {tot[0][2]:5.1f} | {tot[0][3]:5.1f} | {'':>6s} | {tot[0][4]:.0f} 条")

# Also check 7/12
cur.execute('SELECT id, food_name, calories, protein, carbs, fat, grams, note FROM entries WHERE date = "2026-07-12" ORDER BY created_at')
today = cur.fetchall()
if today:
    print("\n=== 今天的记录 ===")
    for r in today:
        note = r[7] if r[7] else ""
        print(f"{r[0]:4d} | {r[1]:<22s} | {r[2]:6.1f} | {r[3]:5.1f} | {r[4]:5.1f} | {r[5]:5.1f} | {r[6]:6.1f} | {note}")
else:
    print("\n今天(7/12)暂无记录")

conn.close()
