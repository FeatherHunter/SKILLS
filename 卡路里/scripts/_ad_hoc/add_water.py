import sqlite3
from datetime import datetime, date

db_path = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
today = str(date.today())
now = datetime.now().strftime('%H:%M:%S')
cur.execute(
    'INSERT INTO entries (date, time, food_name, grams, calories, protein, carbs, fat, note) VALUES (?, ?, ?, ?, 0, 0, 0, 0, "")',
    (today, now, '💧水', 2000)
)
conn.commit()
print(f'✓ 已记录: 💧水 2000ml ({today} {now})')
conn.close()
