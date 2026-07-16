import sqlite3

conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()

cur.execute('SELECT COUNT(*), SUM(calories) FROM entries WHERE date = "2026-07-12"')
r = cur.fetchone()
print(f'Today 7/12: count={r[0]}, total_cal={r[1]}')

cur.execute('SELECT MAX(id), MIN(id) FROM entries')
ids = cur.fetchone()
print(f'Max ID: {ids[0]}, Min ID: {ids[1]}')

conn.close()
