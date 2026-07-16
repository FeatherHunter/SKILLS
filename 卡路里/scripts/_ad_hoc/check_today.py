import sqlite3

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('SELECT id, date, time, food_name, calories, protein, carbs, fat, grams, note FROM entries WHERE date >= "2026-07-11" ORDER BY created_at DESC LIMIT 15')
rows = cur.fetchall()

for r in rows:
    print(f'{r[0]:4d} | {r[1]:10s} | {r[2]} | {r[3]:<22s} | {r[2]:<8s} | {r[4]:6.1f} | {r[5]:5.1f} | {r[6]:5.1f} | {r[7]:5.1f} | {r[8]:7.1f} | {r[9]}')

print('\n--- Today per Python ---')
from datetime import date
today = str(date.today())
print(f'Python date.today() = {today}')

cur.execute('SELECT COUNT(*), SUM(calories) FROM entries WHERE date = ?', (today,))
r = cur.fetchone()
print(f'Today ({today}): count={r[0]}, total_cal={r[1]}')

conn.close()
