import sqlite3
from pathlib import Path

db = Path.home() / 'Downloads/../2Study/StudyNotes/.db/calorie_data.db'
# Actual path
db = r'D:\2Study\StudyNotes\.db\calorie_data.db'
conn = sqlite3.connect(db)
cur = conn.cursor()

print('=== Q: 你的体重数据特征 ===')
print()

# 1. 多少天数据?
cur.execute('SELECT COUNT(*), MIN(date), MAX(date) FROM weight_log')
n, mn, mx = cur.fetchone()
print(f'1. 总记录数:{n} 条,日期范围:{mn} → {mx}')

# 2. 取最近 60 天 - sample for std analysis
cur.execute('SELECT date, weight_kg FROM weight_log ORDER BY date DESC LIMIT 60')
rows = cur.fetchall()
print(f'2. 最近 60 条记录:')
for d, w in rows[:10]:
    print(f'   {d}: {w}kg')
if len(rows) > 10:
    print(f'   ...(共 {len(rows)} 条,跳过中间)')
for d, w in rows[-5:]:
    print(f'   {d}: {w}kg')

import statistics
weights = [w for d, w in rows if w is not None]
if len(weights) > 1:
    print()
    print(f'3. 波动统计(最近 60 条):')
    print(f'   mean = {statistics.mean(weights):.2f} kg')
    print(f'   stdev = {statistics.stdev(weights):.2f} kg')
    print(f'   min = {min(weights):.2f}, max = {max(weights):.2f}')
    print(f'   range = {max(weights) - min(weights):.2f} kg')
    print(f'   CV (变异系数) = {statistics.stdev(weights)/statistics.mean(weights)*100:.1f}%')

# 4. 目标体重
cur.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id=1')
goal, deadline = cur.fetchone()
print()
print(f'4. 目标:weight_goal = {goal} kg, deadline = {deadline}')

# 5. 称重频率(间隔天数)
from datetime import datetime
dates = sorted([d for d, w in rows], reverse=True)
gaps = []
for i in range(1, min(20, len(dates))):
    d1 = datetime.strptime(dates[i-1], '%Y-%m-%d')
    d2 = datetime.strptime(dates[i], '%Y-%m-%d')
    gaps.append((d1 - d2).days)
if gaps:
    print()
    print(f'5. 称重频率(最近 20 个间隔):median = {statistics.median(gaps)} 天,mean = {statistics.mean(gaps):.1f}')

conn.close()