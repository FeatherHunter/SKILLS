import json, subprocess
r = subprocess.run(
    ['python','scripts/query/cli.py','list','--date','2026-08-14','--type','expense','--json'],
    capture_output=True, text=True, encoding='utf-8'
)
d = json.loads(r.stdout)
recs = d['data']['records']
print(f'8/14 共 {len(recs)} 笔, ¥{sum(abs(x["amount"]) for x in recs):.2f}')
print()
for r in sorted(recs, key=lambda x: x['time']):
    print(f"  {r['time']}  ¥{abs(r['amount']):>7.2f}  {r.get('account',''):<10}  {r['category']:<20}  {r['note'][:60]}")