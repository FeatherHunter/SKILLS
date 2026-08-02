# -*- coding: utf-8 -*-
"""从 .scratch/scene_data/05-健身计划.json 生成 docs/scene-prompts/05-健身计划.md 定稿存档

防止手抄漂移:prompt 文本直接从 JSON 提取。
用法: python scripts/_gen_scene_prompts_05.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / '.scratch' / 'scene_data' / '05-健身计划.json'
DST = ROOT / 'docs' / 'scene-prompts' / '05-健身计划.md'

SUBFUNC_ORDER = ['定训练计划', '看训练计划', '改训练计划', '落地训练', '计划复盘', '安全检查']

OUTPUT_TYPE_CN = {'process': '过程', 'result': '结果', 'receipt': '回执'}

scenes = json.loads(SRC.read_text(encoding='utf-8'))

lines = []
lines.append('# 健身计划 29 场景 · 定稿 prompt 存档')
lines.append('')
lines.append('> **定稿时间**:2026-08-02 · 用户逐条确认(29/29,经对抗式审查 8 处修订后全部通过)')
lines.append('> **权威声明**:本文件为 git 提交的只读快照。**修改 prompt 必须重新经用户逐条确认**,')
lines.append('> 不得由 agent 单方改动。开发期副本 `.scratch/scene_data/05-健身计划.json` 与')
lines.append('> `scripts/_triggers.py` 仅为本快照的衍生副本,以本文件为准。')
lines.append('> 关联:Github #6 · 地图 #1 Notes · 分类 issue 开发须知')
lines.append('')
lines.append('## 格式约定(2026-08-02 讨论沉淀)')
lines.append('')
lines.append('1. **prompt 是用户对 AI 说的话,不是流程手册**(最高优先级 · 用户纠偏)')
lines.append('   - 保留:呈现数据承诺(「给我看改前/改后」「给我回执」)、交互参与承诺(「逐动作确认」)、危险操作确认承诺(「删除前先让我确认」)、输入引导填空')
lines.append('   - 删除:「请你先问…」「先给我看…确认后再…」等 AI 执行步骤描述(AI 流程由 SKILL.md 唤醒词底层设计决定)')
lines.append('2. 循环计划结构:加/改动作的填空含「加到第几周/要改的周(选填,空=所有周)」,body 明示默认语义')
lines.append('3. 删除/撤销类场景必含确认承诺(对齐删体脂/删围度先例)')
lines.append('4. 「完成后给 1 句话总结」并入 body 段,不放最后;无英文;括号提示在字段名后、冒号前')
lines.append('5. 单一必填字段不写「不知道可空着」;选项说明放 body')
lines.append('6. 交互原则:信息全直接执行,缺失才补问,不强制采访式引导')
lines.append('')

# 按 SUBFUNC_ORDER 分组
by_sub = {}
for s in scenes:
    by_sub.setdefault(s['subfunction'], []).append(s)

n = 1
for sub in SUBFUNC_ORDER:
    lines.append(f'## {sub}({len(by_sub.get(sub, []))})')
    lines.append('')
    for s in sorted(by_sub.get(sub, []), key=lambda x: x['order']):
        lines.append(f'### {n}. {s["name"]}(`{s["key"]}`)')
        lines.append('')
        lines.append(f'- 分类:健身计划 · 子功能:{s["subfunction"]} · 类型:{OUTPUT_TYPE_CN.get(s["output_type"], s["output_type"])}')
        lines.append(f'- 呈现数据:{s["user_intent"]}')
        lines.append(f'- data_source:`{s["data_source"]}`')
        lines.append('')
        lines.append('```')
        lines.append(s['prompt_template'])
        lines.append('```')
        lines.append('')
        n += 1

DST.parent.mkdir(parents=True, exist_ok=True)
DST.write_text('\n'.join(lines), encoding='utf-8')
print(f'✅ {DST} ({len(scenes)} 场景)')
