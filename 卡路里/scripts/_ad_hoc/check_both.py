import sqlite3

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check both tables
print("=== food_log table ===")
cur.execute('SELECT COUNT(*) FROM entries')
print(f'entries count: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM food_log')
print(f'food_log count: {cur.fetchone()[0]}')

# Check schemas
cur.execute("PRAGMA table_info(entries)")
e_cols = [r[1] for r in cur.fetchall()]
print(f'entries cols: {e_cols}')

cur.execute("PRAGMA table_info(food_log)")
f_cols = [r[1] for r in cur.fetchall()]
print(f'food_log cols: {f_cols}')

conn.close()
