import json
from pathlib import Path

intent = Path(r'D:\2Study\StudyNotes\2026\自媒体\DAY2\intent.json')
data = json.loads(intent.read_text(encoding='utf-8'))

iv_list = data['videos']
seq_videos = data['sequences'][0]['videos']  # [2, 1, 3, ...]

print('intent index → filename → videoEntries index (按字母排序)')
print('=' * 60)
entries = sorted([v['file'] for v in iv_list])
for seq_idx in seq_videos:
    intent_video = next((v for v in iv_list if v['index'] == seq_idx), None)
    if not intent_video:
        print(f'  seq={seq_idx}: NOT FOUND in intent.videos')
        continue
    fname = intent_video['file']
    entry_idx = entries.index(fname)
    print(f'  seq={seq_idx:2d} → "{fname[:30]}..." → videoEntries[{entry_idx}]')

print()
print('最终 dropdown 应该显示的顺序:')
for i, seq_idx in enumerate(seq_videos):
    intent_video = next((v for v in iv_list if v['index'] == seq_idx), None)
    fname = intent_video['file'] if intent_video else '?'
    entry_idx = entries.index(fname) if intent_video else '?'
    print(f'  第{i+1}个: {fname[:50]}')
