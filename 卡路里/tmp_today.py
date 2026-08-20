import sqlite3
db = r'D:\2Study\StudyNotes\.db\calorie_data.db'
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute("""SELECT id, time, food_name, grams, calories, protein
               FROM food_log WHERE date=? ORDER BY time""", ('2026-08-18',))
rows = cur.fetchall()
total_cal = sum(r[4] for r in rows)
total_p = sum(r[5] for r in rows)
print(f"8/18 共 {len(rows)} 条, 总 {total_cal:.0f} 千卡, 蛋白 {total_p:.1f}g")
print()
for r in rows:
    print(f"{r[1]}  {r[2]:<20}  {r[3]:>5}g  {r[4]:>5} 千卡  P{r[5]:.1f}")
