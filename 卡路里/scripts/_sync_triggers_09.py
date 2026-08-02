# -*- coding: utf-8 -*-
"""把 09-身材照片.json 的 10 场景同步进 _triggers.py(纯增量插入 · 2026-08-02)

背景:6517ac8(健身计划「并发覆盖修复」)整文件提交时把身材照片 10 词连同
目标管理/基础信息/身体细节一起删掉,本脚本只补身材照片(权威 = scene_data/09)。

与 _sync_triggers_05.py 区别:05 是"替换旧块",09 是**纯追加**——
插入锚点 = 第一个 'category': '分析' 条目之前,不动任何已有条目。
用法: python scripts/_sync_triggers_09.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.scratch' / 'scene_data' / '09-身材照片.json'
DEST = ROOT / 'scripts' / '_triggers.py'

scenes = json.loads(SRC.read_text(encoding='utf-8'))

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
    entry = f'''    {{
            'category': '身材照片',     'wake_word': '{ws}',     'desc': '{desc}',
            'main_prompt': {{
        'cli': '{s["data_source"]}', 'text': '{t}'}},
        'fill_hints': [],
            'variants': [],
            'key': '{s["key"]}', 'name': '{s["name"]}', 'subfunction': '{s["subfunction"]}', 'output_type': '{s["output_type"]}',
            'html_template': '{s["html_template"]}', 'data_source': '{s["data_source"]}', 'prompt_template': '{t}',
            'user_intent': '{s["user_intent"]}', 'data_fields': {json.dumps(s["data_fields"], ensure_ascii=False)},
            'depends_on_external': {dep}, 'order': {s["order"]}}},'''
    return entry


def main():
    text = DEST.read_text(encoding='utf-8')

    # 防重入:已存在则不重复插入
    if all(f"'key': '{s['key']}'" in text for s in scenes):
        print('ℹ️  10 场景 key 已全部在 _triggers.py,跳过(防重入)')
        return 0

    # 锚点:第一个 'category': '分析' 条目之前(纯追加,不动已有内容)
    end = text.find("'category': '分析'")
    if end == -1:
        raise SystemExit('❌ 未找到分析分类锚点')
    brace_start = text.rfind('    {', 0, end)
    if brace_start == -1:
        raise SystemExit('❌ 未找到分析块开头')
    # 校验插入点前是条目结束(`,}` 或 `},`),防止插进字符串
    before = text[brace_start - 20:brace_start]
    if '},' not in before and '}' not in before.splitlines()[-1]:
        raise SystemExit(f'❌ 锚点前结构异常: {before!r}')

    entries = '\n'.join(render_entry(s) for s in scenes) + '\n'
    text = text[:brace_start] + entries + text[brace_start:]

    # 头部注释同步(数据回来,注释就不该再写"待同步")
    if '身材照片 10 场景已同步' not in text:
        text = text.replace(
            '- ⏳ 其余分类仍为旧版运行时数据,待各自分类 ticket 同步。',
            '- ✅ **身材照片 10 场景已同步**(2026-08-02 · ticket #10):8 条唯一触发词(记身材照×3 / 查身材照 / 对比两张照片 / 生成身材照GIF / 删身材照 / 改照片标签 / 加照片标签 / 删照片标签)\n'
            '  (category=\'身材照片\', 新 13 字段 scene 格式;6517ac8 并发整文件覆盖误删,已按 scene_data/09 权威增量补回)\n'
            '- ⏳ 其余分类仍为旧版运行时数据,待各自分类 ticket 同步。',
            1)

    DEST.write_text(text, encoding='utf-8')
    print(f'✅ 已增量插入 {len(scenes)} 条身材照片条目(分析块之前)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
