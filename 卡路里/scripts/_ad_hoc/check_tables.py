import sqlite3
conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('All tables:', tables)
print('\nentries exists?', 'entries' in tables)
print('food_log exists?', 'food_log' in tables)

if 'food_log' in tables:
    cur.execute('SELECT COUNT(*) FROM food_log')
    print(f'food_log records: {cur.fetchone()[0]}')
conn.close()
