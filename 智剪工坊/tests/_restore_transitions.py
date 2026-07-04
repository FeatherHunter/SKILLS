import json
target = r'D:\2Study\StudyNotes\2026\自媒体\DAY2'

# 取 V2 的 transitions（V5 应该有 13 条 transitions，type=fade 因为 V2 没存 type）
with open(f'{target}/intent_v2.json', encoding='utf-8') as f:
    v2 = json.load(f)
v2_trans = v2['sequences'][0].get('transitions', [])

# 给每条加 type='fade'，匹配 HTML 的「默认」语义
new_trans = []
for tr in v2_trans:
    new_tr = dict(tr)
    if not new_tr.get('type'):
        new_tr['type'] = 'fade'
    new_trans.append(new_tr)

# 写入 V4 和 intent.json（也是 V5 用 V4 内容）
for fname in ['intent.json', 'intent_v4.json', 'intent_v5.json']:
    path = f'{target}/{fname}'
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    if d.get('sequences'):
        d['sequences'][0]['name'] = '开场'
        d['sequences'][0]['transitions'] = new_trans
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f'{fname}: 已加 transitions {len(new_trans)} 条')

print('OK')
