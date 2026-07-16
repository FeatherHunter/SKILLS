import sqlite3

conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()

# Step 1: Rename entries → food_log_new, food_log → food_log_dup
cur.execute('ALTER TABLE entries RENAME TO food_log_new')
cur.execute('ALTER TABLE food_log RENAME TO food_log_dup')

# Step 2: food_log_new → food_log (this becomes the main table with all data)
cur.execute('ALTER TABLE food_log_new RENAME TO food_log')

# Step 3: Drop the duplicate-only table
cur.execute('DROP TABLE food_log_dup')

conn.commit()
print('Migration done: entries → food_log with all historical data')

# Verify
cur.execute('SELECT COUNT(*) FROM food_log')
print(f'Total records in food_log: {cur.fetchone()[0]}')

cur.execute('SELECT MIN(id), MAX(id) FROM food_log')
r = cur.fetchone()
print(f'ID range: {r[0]} - {r[1]}')

conn.close()
