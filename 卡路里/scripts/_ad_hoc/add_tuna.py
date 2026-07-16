import sqlite3
from datetime import datetime, date

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'

# Add a new entry for today (7/13)
conn = sqlite3.connect(db_path)
cur = conn.cursor()
today = '2026-07-13'
now = datetime.now().strftime('%H:%M:%S')

cur.execute(
    'INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
    (today, now, "金枪鱼饼干(Member's Mark黄油芥末味)", 22, 113.1, 2, 13.4, 5.7, '')
)
conn.commit()

entry_id = cur.lastrowid

# Summary
cur.execute('SELECT SUM(calories), SUM(protein), SUM(carbs), SUM(fat), COUNT(*) FROM food_log WHERE date = ?', (today,))
total_cal, total_pro, total_carbs, total_fat, entry_count = cur.fetchone()
conn.close()

print(f'✓ 已记录: 金枪鱼饼干 22g = 113.1 kcal')
print(f'  条目ID: {entry_id}')
print(f'  今日: {total_cal:.1f} kcal | 蛋白 {total_pro:.1f}g | 碳水 {total_carbs:.1f}g | 脂肪 {total_fat:.1f}g | {entry_count} 条')
