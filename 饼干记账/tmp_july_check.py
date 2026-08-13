# -*- coding: utf-8 -*-
import json

d = json.load(open('tmp_july_expense.json', encoding='utf-8-sig'))
records = d['data']['records']

print('=== 7月支出 Top10 ===')
for r in sorted(records, key=lambda x: x['amount'])[:10]:
    print('{} {:>9.2f} {} | {}'.format(r['time'][:10], r['amount'], r['category'], r['note'][:40]))

# 大额合计占比
top_sum = sum(r['amount'] for r in sorted(records, key=lambda x: x['amount'])[:4])
print()
print('Top4 合计: {:.2f}'.format(top_sum))
print('7月支出总计: {:.2f}'.format(d['data']['expense']))
