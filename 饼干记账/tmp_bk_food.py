# -*- coding: utf-8 -*-
import json, subprocess

r = subprocess.run(
    ['python', 'scripts/query/cli.py', 'list',
     '--from', '2026-08-06', '--to', '2026-08-15',
     '--type', 'expense', '--json'],
    capture_output=True, text=True, encoding='utf-8'
)
data = json.loads(r.stdout)
recs = data['data']['records']

food_cats = ['餐饮', '居家/食品', '居家/菜市场']
food = [x for x in recs if any(x['category'].startswith(c) for c in food_cats)]

print('===== 饼干记账 · 8/6-8/15 食物类记录 =====')
print(f'共 {len(food)} 条')
print()
print(f"{'日期时间':<19} {'金额':>7} {'账户':<10} {'分类':<25} 备注")
print('-' * 110)
for r in sorted(food, key=lambda x: x['time']):
    print(f"{r['time']:<19} {r['amount']:>7.2f} {r.get('account',''):<10} {r['category']:<25} {r['note'][:50]}")
