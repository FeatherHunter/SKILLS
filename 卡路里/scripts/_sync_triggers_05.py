# -*- coding: utf-8 -*-
"""把 05-健身计划.json 的 29 场景同步进 _triggers.py(替换旧健身计划 11 条 legacy)

生成 13 字段新格式条目(对齐 07-基础信息/08-身体细节 先例),插入原旧块位置。
用法: python scripts/_sync_triggers_05.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.scratch' / 'scene_data' / '05-健身计划.json'
DEST = ROOT / 'scripts' / '_triggers.py'

scenes = json.loads(SRC.read_text(encoding='utf-8'))

# 生成条目文本(与 08-身体细节 的 13 字段格式一致)
def render_entry(s: dict) -> str:
    ws = s['wake_word']
    desc_map = {
        'plan_view_this_week': '本周训练日历(7 天表 + 完成度)',
        'plan_view_next_week': '下周训练日历预览(含待练状态)',
        'plan_view_last_week': '上周训练日历 + 完成率回顾',
        'plan_view_week': '指定周次训练日历',
        'plan_view_today': '今日动作/组数/重量 + 实时完成进度',
        'plan_overview': '计划总览 KPI + 每周完成率列表',
        'plan_vs_actual': '计划 vs 实际对比(完成度/偏差/动作级表)',
        'plan_set': 'AI 采访式创建计划(预览确认 → 写入回执)',
        'plan_copy': '复制整计划或某周作为模板',
        'plan_set_rest': '标记某天为休息日(或取消)',
        'plan_add_movement': '给某天/时段加动作(组数/重量)',
        'plan_set_week': '快速设置一周 7 天安排',
        'plan_update': '改计划配置字段(改前/改后 + 影响)',
        'plan_update_day': '改某天训练安排(改前/改后)',
        'plan_delete_day': '删某天训练(快照确认 → 回执)',
        'plan_update_movement': '替换动作(改前/改后 + 组数变化)',
        'plan_delete': '删除整个计划(确认 → 回执 + 提示)',
        'plan_execute': '4 步落地(补计划/记心愿/推送/回写)',
        'plan_execute_weekend': '批量落地到本周末(跨天汇总)',
        'plan_execute_month': '批量落地到本月底(跨天汇总)',
        'plan_sync_xunji': '推 plan 到训记(前置审计动作名)',
        'plan_backfill_xunji': '拉训记实绩回写 exercise_log',
        'plan_review_week': '本周复盘(KPI + 趋势 + 上周对比)',
        'plan_review_month': '本月复盘(KPI + 趋势 + 上月对比)',
        'plan_review_all': '全部复盘(总完成率 + 高频动作)',
        'plan_completion_rate': '每周完成率折线趋势',
        'plan_missed': '漏练日期 + 应练动作列表',
        'plan_movement_rate': '动作完成率 TOP 榜',
        'plan_contraindication': '禁忌动作扫描(腰/膝/肩 + 替代建议)',
    }
    desc = desc_map.get(s['key'], s['name'])
    t = s['prompt_template'].replace('\n', '\\n')
    dep = {'true': 'True', 'false': 'False'}[str(s["depends_on_external"]).lower()]
    # main_prompt.text = prompt_template;cli = data_source
    entry = f'''    {{
            'category': '健身计划',     'wake_word': '{ws}',     'desc': '{desc}',
            'main_prompt': {{
        'cli': '{s["data_source"]}', 'text': '{t}'}},
        'fill_hints': [],
            'variants': [],
            'key': '{s["key"]}', 'name': '{s["name"]}', 'subfunction': '{s["subfunction"]}', 'output_type': '{s["output_type"]}',
            'html_template': '{s["html_template"]}', 'data_source': '{s["data_source"]}', 'prompt_template': '{t}',
            'user_intent': '{s["user_intent"]}', 'data_fields': {json.dumps(s["data_fields"], ensure_ascii=False)},
            'depends_on_external': {dep}, 'order': {s["order"]}}},'''
    return entry

entries = '\n'.join(render_entry(s) for s in scenes)

text = DEST.read_text(encoding='utf-8')

# 定位旧健身计划块:从 'category': '健身计划' 第一条到 'category': '分析' 前一条
start = text.find("'category': '健身计划'")
end = text.find("'category': '分析'")
if start == -1 or end == -1 or start > end:
    raise SystemExit('❌ 定位旧健身计划块失败')

# end 之前可能残留旧块的尾部 '},' 或 '}'——往回找该条目开头的 '    {'
# 分析条目的开头 '    {' 位于 end 之前最近的一个
brace_start = text.rfind('    {', 0, end)
if brace_start == -1:
    raise SystemExit('❌ 未找到分析块开头花括号')

# 新块开头自带 '    {'(entry 模板),因此替换起点 = 旧健身计划条目开头的 '    {'
old_block_start = text.rfind('    {', 0, start)
if old_block_start == -1:
    raise SystemExit('❌ 未找到旧健身计划块开头')

new_block = entries + '\n'
text = text[:old_block_start] + new_block + text[brace_start:]

DEST.write_text(text, encoding='utf-8')
print(f'✅ 已替换旧健身计划块 → 插入 {len(scenes)} 条新 13 字段条目')
