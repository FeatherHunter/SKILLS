# -*- coding: utf-8 -*-
"""身材照片条目去重:18 条重复 → 权威 scene_data/09 的 10 条(2026-08-02)

背景:并发 session 恢复了 8 条 + _sync_triggers_09 插入了 10 条(部分 key 重复)。
本脚本:定位 身材照片 连续块(第一条条目开头 → 最后一条条目结束),整体替换为权威 10 条。
"""
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.scratch' / 'scene_data' / '09-身材照片.json'
DEST = ROOT / 'scripts' / '_triggers.py'

DESC_MAP = {
    'body_photo_add_single': '存一张身材照(发图/路径双模式)',
    'body_photo_add_note': '存一张带备注的身材照',
    'body_photo_add_batch': '批量存多张身材照(逐张状态明细)',
    'body_photo_list': '浏览身材照(网格 + 时间/标签筛选 + 计数)',
    'body_photo_compare': '两张照片并排对比(间隔天数/标签/备注)',
    'body_photo_gif': '时间段多张照片合成变化 GIF(帧数/首末日期)',
    'body_photo_delete': '删除照片(先列候选 → 快照确认 → 回执)',
    'body_photo_tag_set': '标签覆盖整套(可多个,改前/改后对比)',
    'body_photo_tag_add': '追加标签(可多个,判重提示)',
    'body_photo_tag_remove': '移除标签(可多个,至少保留 1 个)',
}


def render_entry(s: dict) -> str:
    ws = s['wake_word']
    desc = DESC_MAP.get(s['key'], s['name'])
    t = s['prompt_template'].replace('\n', '\\n')
    dep = {'true': 'True', 'false': 'False'}[str(s['depends_on_external']).lower()]
    return f'''    {{
            'category': '身材照片',     'wake_word': '{ws}',     'desc': '{desc}',
            'main_prompt': {{
        'cli': '{s["data_source"]}', 'text': '{t}'}},
        'fill_hints': [],
            'variants': [],
            'key': '{s["key"]}', 'name': '{s["name"]}', 'subfunction': '{s["subfunction"]}', 'output_type': '{s["output_type"]}',
            'html_template': '{s["html_template"]}', 'data_source': '{s["data_source"]}', 'prompt_template': '{t}',
            'user_intent': '{s["user_intent"]}', 'data_fields': {json.dumps(s["data_fields"], ensure_ascii=False)},
            'depends_on_external': {dep}, 'order': {s["order"]}}},'''


def main():
    scenes = json.loads(SRC.read_text(encoding='utf-8'))
    text = DEST.read_text(encoding='utf-8')

    marks = [m.start() for m in re.finditer(r"'category': '身材照片'", text)]
    if not marks:
        raise SystemExit('❌ 未找到身材照片条目')
    first = marks[0]
    last = marks[-1]
    # 块开头:第一条条目开头的 '    {'
    block_start = text.rfind('    {', 0, first)
    if block_start == -1:
        raise SystemExit('❌ 未找到身材照片块开头')
    # 块结尾:最后一条条目的 '},'(找该条目内最后一个 '},' 之后的换行)
    tail = text[last:]
    # 最后一条结束 = 下一个 '    {' 之前(若有)或文件该处最近的 '},'
    nxt = text.find('    {', last + 10)
    if nxt == -1:
        raise SystemExit('❌ 未找到身材照片块结束边界')
    block_end = nxt

    # 校验:块内全是身材照片(安全断言)
    block = text[block_start:block_end]
    non_photo = re.findall(r"'category': '(?!身材照片)[^']+'", block)
    if non_photo:
        raise SystemExit(f'❌ 块内混入其他分类: {non_photo[:3]}')

    entries = '\n'.join(render_entry(s) for s in scenes) + '\n'
    new_text = text[:block_start] + entries + text[block_end:]

    DEST.write_text(new_text, encoding='utf-8')
    print(f'✅ 身材照片块已按权威 scene_data/09 重建:18 条重复 → {len(scenes)} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
