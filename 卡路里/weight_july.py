import sqlite3

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Query July weight records
cur.execute('SELECT date, weight_kg, height_cm, bmi FROM weight_log WHERE date >= "2026-07-01" AND date <= "2026-07-12" ORDER BY date')
rows = cur.fetchall()

print(f"{'日期':<12s} | {'体重(kg)':>8s} | {'身高(cm)':>8s} | {'BMI':>5s}")
print("-" * 50)
for r in rows:
    print(f"{r[0]:<12s} | {r[1]:8.1f} | {r[2]:8.1f} | {r[3]:5.1f}")

# Summary stats
cur.execute('SELECT MIN(weight_kg), MAX(weight_kg), AVG(weight_kg), COUNT(*) FROM weight_log WHERE date >= "2026-07-01" AND date <= "2026-07-12"')
stats = cur.fetchone()
print("-" * 50)
print(f"最低: {stats[0]:.1f}kg | 最高: {stats[1]:.1f}kg | 均值: {stats[2]:.1f}kg | 共 {stats[3]} 条")

# Weight change
if len(rows) >= 2:
    change = rows[-1][1] - rows[0][1]
    print(f"\n月初→今日变化: {change:+.1f}kg")

conn.close()
