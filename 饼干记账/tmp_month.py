import json, subprocess
from collections import defaultdict

r = subprocess.run(
    ['python','scripts/query/cli.py','list',
     '--from','2026-08-01','--to','2026-08-31',
     '--type','expense','--json'],
    capture_output=True, text=True, encoding='utf-8'
)
d = json.loads(r.stdout)
recs = d['data']['records']
total = sum(abs(x['amount']) for x in recs)
print(f'本月 8/1-8/19(已记录) 共 {len(recs)} 笔, 总 ¥{total:.2f}')
print()

by_day = defaultdict(lambda: [0, 0])
for r in recs:
    day = r['time'][:10]
    by_day[day][0] += 1
    by_day[day][1] += abs(r['amount'])

print('=== 每天 ===')
for d in sorted(by_day.keys()):
    cnt, amt = by_day[d]
    print(f'  {d}  {cnt} 笔  ¥{amt:.2f}')

print()
print('=== 按分类 ===')
by_cat = defaultdict(lambda: [0, 0.0])
for r in recs:
    by_cat[r['category']][0] += 1
    by_cat[r['category']][1] += abs(r['amount'])
for c, (cnt, amt) in sorted(by_cat.items(), key=lambda x: -x[1][1]):
    print(f'  {c:<25} {cnt} 笔  ¥{amt:.2f}')