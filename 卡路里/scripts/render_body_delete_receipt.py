#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_delete_receipt.py — 删体脂/删围度 删除回执 HTML 渲染器(v1.0 · ticket #9)

对应 SKILL.md 唤醒词: 删体脂 / 删围度
对应模板: templates/crud_receipt.html
- 数据源: body_composition / body_measurements 表(实读 DB)
- 流程: 删除前快照(日期/数值/来源) → 软删除 → 回执
- 输出目录: $DATA_DIR/calorie_html/删体脂_回执_<TS>.html(html_scene_path 规则)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据契约(与 scene-index §8 一致): 删除前快照 / 确认回执

用法:
    python scripts/render_body_delete_receipt.py --entity composition --id <ID>
    python scripts/render_body_delete_receipt.py --entity measurements --id <ID>
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path, init_db  # noqa: E402
from html_paths import html_scene_path  # noqa: E402
from source_constants import SOURCE_LABELS  # noqa: E402
from validators import MEASUREMENT_FIELDS  # noqa: E402
from render_crud_view import _chain_valid  # noqa: E402 · 思考链校验单一来源(2026-08-02)

ENTITY = {
    'composition': {
        'table': 'body_composition',
        'scene': '删体脂',
        'columns': ['id', 'date', 'source', 'body_fat_pct', 'note'],
        'labels': {'body_fat_pct': '体脂率(%)', 'source': '来源', 'note': '备注'},
    },
    'measurements': {
        'table': 'body_measurements',
        'scene': '删围度',
        'columns': ['id', 'date'] + MEASUREMENT_FIELDS + ['note'],
        'labels': {
            'chest_cm': '胸围(cm)', 'waist_cm': '腰围(cm)', 'abdomen_cm': '腹围(cm)',
            'hip_cm': '臀围(cm)', 'shoulder_cm': '肩围(cm)',
            'left_thigh_cm': '左大腿(cm)', 'right_thigh_cm': '右大腿(cm)',
            'left_calf_cm': '左小腿(cm)', 'right_calf_cm': '右小腿(cm)',
            'left_arm_cm': '左上臂(cm)', 'right_arm_cm': '右上臂(cm)',
            'left_forearm_cm': '左前臂(cm)', 'right_forearm_cm': '右前臂(cm)',
            'note': '备注',
        },
    },
}

METRIC_LABELS = {
    'chest_cm': '胸围', 'waist_cm': '腰围', 'abdomen_cm': '腹围', 'hip_cm': '臀围',
    'left_thigh_cm': '左大腿', 'right_thigh_cm': '右大腿',
    'left_calf_cm': '左小腿', 'right_calf_cm': '右小腿',
    'left_arm_cm': '左上臂', 'right_arm_cm': '右上臂',
    'left_forearm_cm': '左前臂', 'right_forearm_cm': '右前臂',
    'shoulder_cm': '肩围',
}


def _get_conn():
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not p.exists():
        init_db(p)
    return sqlite3.connect(str(p))


def build_delete(entity, record_id, _chain=''):
    spec = ENTITY[entity]
    table = spec['table']
    cols = spec['columns']
    c = _get_conn()
    try:
        cur = c.execute(
            f"SELECT {', '.join(cols)} FROM {table} WHERE id = ? AND is_deprecated = 0",
            (record_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"{spec['scene']}: 记录 #{record_id} 不存在或已删除")
        snapshot = dict(zip(cols, row))

        # 删除前快照 → 软删除
        c.execute(
            f"UPDATE {table} SET is_deprecated = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (record_id,),
        )
        c.commit()
    finally:
        c.close()

    # 快照摘要
    if entity == 'composition':
        src = SOURCE_LABELS.get(snapshot.get('source'), snapshot.get('source') or '—')
        detail = f"日期 {snapshot['date']} · 体脂率 {snapshot['body_fat_pct']}% · 来源 {src}"
        if snapshot.get('note'):
            detail += f" · 备注 {snapshot['note']}"
    else:
        filled = [f"{METRIC_LABELS[col]} {snapshot[col]}cm"
                  for col in MEASUREMENT_FIELDS if snapshot.get(col) is not None]
        detail = f"日期 {snapshot['date']} · " + ('、'.join(filled) if filled else '无围度')
        if snapshot.get('note'):
            detail += f" · 备注 {snapshot['note']}"

    summary = f"已删除{spec['scene']} #{record_id}({detail})"

    return {
        'status': 'ok',
        'data': {
            'scene': spec['scene'],
            'action': 'delete',
            'op': 'delete',
            'record_id': record_id,
            'summary': summary,
            'items': [{'id': record_id, 'date': snapshot['date'], 'detail': detail,
                       'status': '已删除', 'reason': ''}],
            'tag_diff': None,
            'distance': None,
            'no_change': False,
            'meta': {
                'action_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': spec['scene'],
                'wake_word': spec['scene'],
                'source': f'{table} (删除前快照)',
                'chain': _chain,
            },
        },
        'message': f'已生成{spec["scene"]} 回执',
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace(placeholder, f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染删体脂/删围度 删除回执 HTML(v1.0 · ticket #9)')
    p.add_argument('--entity', choices=['composition', 'measurements'], required=True)
    p.add_argument('--id', type=int, required=True)
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径(默认 html_scene_path 规则)')
    args = p.parse_args()

    # ⭐ 思考链强制校验(R3 · 2026-08-02 用户拍板)
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.列候选→2.确认→3.删除→4.回执"', file=sys.stderr)
        return 2

    spec = ENTITY[args.entity]
    try:
        data = build_delete(args.entity, args.id, _chain=args.chain)
    except ValueError as e:
        print(f'❌ {e}', file=sys.stderr)
        return 1

    html = render_html(data)
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, spec['scene'], 'receipt')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
