import sqlite3
conn = sqlite3.connect(r'D:\2Study\StudyNotes\.db\calorie_data.db')
cur = conn.cursor()

# Check schema types
cur.execute("PRAGMA table_info(food_log)")
for r in cur.fetchall():
    print(f'{r[1]}: {r[2]}')

# Check today's records
print('\n=== Today 7/12 ===')
cur.execute('SELECT id, food_name, calories, protein, carbs, fat, grams, note FROM food_log WHERE date = "2026-07-12" ORDER BY created_at')
for r in cur.fetchall():
    print(f'{r[0]:4d} | {r[1]:<22s} | {r[2]:6.1f} | {r[3]:5.1f} | {r[4]:5.1f} | {r[5]:5.1f} | {r[6]:7.1f} | {r[7]}')

# Total
cur.execute('SELECT SUM(calories) FROM food_log WHERE date = "2026-07-12"')
print(f'\n今日总热量: {cur.fetchone()[0]:.1f} kcal')

conn.close()
