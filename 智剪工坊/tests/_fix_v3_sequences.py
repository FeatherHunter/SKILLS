"""
修复 V3.json 的 sequences bug：
V2 是 1 条 chain，V3 因 bug 拆成了 3 条 chain。
把 V3 的 sequences 字段恢复成 V2 一样（保留其他 V3 字段如 revision/_meta/cover/ending 等等）。
"""
import json

with open(r'D:\2Study\StudyNotes\2026\自媒体\DAY2\intent_v3.json', encoding='utf-8') as f:
    v3 = json.load(f)
with open(r'D:\2Study\StudyNotes\2026\自媒体\DAY2\intent_v2.json', encoding='utf-8') as f:
    v2 = json.load(f)

# V3 保留所有字段，只替换 sequences
v3['sequences'] = v2['sequences']

with open(r'D:\2Study\StudyNotes\2026\自媒体\DAY2\intent_v3.json', 'w', encoding='utf-8') as f:
    json.dump(v3, f, ensure_ascii=False, indent=2)

print('V3 sequences 已修复为 V2 一样。')
print('修复后 V3 sequences:')
print(json.dumps(v3['sequences'], ensure_ascii=False, indent=2)[:1500])
