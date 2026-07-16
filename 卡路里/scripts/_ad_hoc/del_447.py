import sqlite3

conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()

# Delete entry 447
cur.execute('DELETE FROM food_log WHERE id = 447')
conn.commit()
print(f'Deleted {cur.rowcount} row(s)')

# Verify today's total
cur.execute('SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*) FROM food_log WHERE date = "2026-07-12"')
r = cur.fetchone()
print(f'Today after delete: {r[0]:.0f} kcal | protein {r[1]:.1f}g | carbs {r[2]:.1f}g | fat {r[3]:.1f}g | {r[4]} entries')

conn.close()
