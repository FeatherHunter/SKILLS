import json, subprocess
r=subprocess.run(
    ['python','scripts/query/cli.py','list','--date','2026-08-18','--type','expense','--json'],
    capture_output=True, text=True, encoding='utf-8'
)
d=json.loads(r.stdout)
recs=d['data']['records']
total = sum(abs(x['amount']) for x in recs)
print(f'8/18 共 {len(recs)} 笔, 总 {total:.2f}')
print()
for x in sorted(recs, key=lambda r:r['time']):
    print(f"{x['time']}  {x['amount']:>7.2f}  {x.get('account',''):<8}  {x['category']:<20}  {x['note'][:50]}")
