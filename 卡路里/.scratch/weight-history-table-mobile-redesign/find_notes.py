"""检查 note 行在哪"""
import json
from pathlib import Path

# Find the data injected in sample
import re
html = Path('.scratch/weight-history-table-mobile-redesign/sample.html').read_text(encoding='utf-8')
m = re.search(r'window\.__DATA__\s*=\s*(\{.*?\})\s*;\s*</script>', html, re.DOTALL)
data = json.loads(m.group(1))
items = data['data']['items']
print(f"Total items: {len(items)}")
note_rows = []
for i, it in enumerate(items):
    if it.get('note'):
        note_rows.append((i, it['date'], it['note']))
        print(f"  Row {i}: date={it['date']} note={it['note']!r}")
print(f"\nTotal note rows: {len(note_rows)}")