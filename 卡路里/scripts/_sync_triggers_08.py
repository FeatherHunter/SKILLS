#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 scene_data 中缺失分类增量同步进 _triggers.py(并发覆盖修复 · 2026-08-02)

背景:commit 6517ac8(健身计划 data_source 重同步)整文件重写 _triggers.py,
误删 基础信息 4 / 身体细节 13 / 身材照片 10 / 目标管理 25(共 52 词)。
本脚本以 .scratch/scene_data/NN-分类.json 为权威,只增量追加缺失 wake_word,
不整文件覆盖、不动已有条目。

用法: python scripts/_sync_triggers_08.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'scripts' / '_triggers.py'

# 缺失分类 → scene_data 文件(按 08 修复顺序)
MISSING = [
    ('06-目标管理.json', '目标管理'),
    ('07-基础信息.json', '基础信息'),
    ('08-身体细节.json', '身体细节'),
    ('09-身材照片.json', '身材照片'),
]


def render_entry(s: dict, category: str) -> str:
    t = s['prompt_template'].replace('\n', '\\n')
    dep = {'true': 'True', 'false': 'False'}[str(s["depends_on_external"]).lower()]
    return f'''    {{
            'category': '{category}',     'wake_word': '{s["wake_word"]}',     'desc': '{s["user_intent"]}',
            'main_prompt': {{
        'cli': '{s["data_source"]}', 'text': '{t}'}},
        'fill_hints': [],
            'variants': [],
            'key': '{s["key"]}', 'name': '{s["name"]}', 'subfunction': '{s["subfunction"]}', 'output_type': '{s["output_type"]}',
            'html_template': '{s["html_template"]}', 'data_source': '{s["data_source"]}', 'prompt_template': '{t}',
            'user_intent': '{s["user_intent"]}', 'data_fields': {json.dumps(s["data_fields"], ensure_ascii=False)},
            'depends_on_external': {dep}, 'order': {s["order"]}}},'''


def main():
    text = DEST.read_text(encoding='utf-8')
    # 现有 wake_word 集合(避免重复插入)
    existing = set(re.findall(r"'wake_word': '([^']+)'", text))
    added = 0
    skipped = []

    # 按分类分批:每个分类块插到 '分析' 块之前(保持分类顺序:... 健身计划 → 目标管理 → 基础信息 → 身体细节 → 身材照片 → 分析)
    # 找 '分析' 分类第一条的开头 '{' 位置作为所有插入锚点(先插的在前)
    anchor = text.find("'category': '分析'")
    if anchor == -1:
        raise SystemExit('❌ 未找到分析分类锚点')
    brace_start = text.rfind('    {', 0, anchor)
    if brace_start == -1:
        raise SystemExit('❌ 未找到分析块开头')

    blocks = []
    for fname, cat in MISSING:
        src = ROOT / '.scratch' / 'scene_data' / fname
        scenes = json.loads(src.read_text(encoding='utf-8'))
        cat_scenes = [s for s in scenes if s['category'] == cat]
        entries = []
        for s in cat_scenes:
            if s['wake_word'] in existing:
                skipped.append(s['wake_word'])
                continue
            entries.append(render_entry(s, cat))
            existing.add(s['wake_word'])
        if entries:
            blocks.append('\n'.join(entries) + '\n')
            added += len(entries)
        print(f'{fname} ({cat}): 插入 {len(entries)} 条,跳过已存在 {len(cat_scenes)-len(entries)} 条')

    if not blocks:
        print('✅ 无缺失,无需同步')
        return

    new_block = '\n'.join(blocks)
    text = text[:brace_start] + new_block + text[brace_start:]
    DEST.write_text(text, encoding='utf-8')
    print(f'✅ 增量插入 {added} 条;跳过已存在 {len(skipped)} 条: {skipped[:10]}')


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()
