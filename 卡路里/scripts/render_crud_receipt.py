#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_crud_receipt.py — 通用 CRUD 操作回执 HTML 渲染器(回执型)

对应 SKILL.md 唤醒词(10 个):
  - 删吃的/改吃的   → mode=update/delete
  - 存食品/改食品   → mode=update/create
  - 删身材照       → mode=delete
  - 改照片标签     → mode=update
  - 改运动记录     → mode=update
  - 改体重记录     → mode=update
  - 设置档案       → mode=create/update(live-profile-set)
  - 设活动量       → mode=update(live-profile-activity)
  - 改档案         → mode=update(live-profile-update)
对应模板: templates/crud_receipt.html

数据来源(互斥):
  --mock <json>                    mock 数据(测试)
  --live-profile-set               实读 DB:设置档案(全量写库 + 回执一体 · ticket #8)
  --live-profile-activity <level>  实读 DB:设活动量(写库 + 回执一体 · ticket #8)
  --live-profile-update           实读 DB:改档案(--field/--value,写库 + 回执一体)
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path, html_scene_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def _profile_receipt(op: str, old_record: dict, new_record: dict, kpis: list,
                     entity_label: str, action_at: str) -> dict:
    """组装 profile 回执数据契约(与 mock_crud_receipt.json 同构)"""
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': 1,
            'old_record': old_record,
            'new_record': new_record,
            'context': {'kpis': kpis},
            'meta': {
                'action_at': action_at,
                'entity_type': entity_label,
            },
        },
        'message': f'已生成{entity_label} 回执',
    }


def build_live_profile_set(age=None, gender=None, height=None, activity=None, note=None):
    """设置档案:全量写库 + 组装回执(呈现:身高/年龄/性别/活动量 + 设置时间)

    首次设置 op=create;已存在档案 op=update(改前/改后对比)。
    """
    import profile
    from analysis._utils import ACTIVITY_LEVEL_LABELS, TDEE_ACTIVITY_FACTORS

    old = profile.get_profile()
    is_first = not old
    result = profile.set_profile(age=age, gender=gender, height_cm=height,
                                  note=note, activity_level=activity)
    new = profile.get_profile()

    al = new.get('activity_level') or 'moderate'
    factor = TDEE_ACTIVITY_FACTORS.get(al, 1.55)
    label = ACTIVITY_LEVEL_LABELS.get(al, al)
    op = 'create' if is_first else 'update'
    kpis = [
        {'label': '身高', 'value': f"{new.get('height_cm')} cm" if new.get('height_cm') else '—'},
        {'label': '年龄', 'value': str(new.get('age', '—'))},
        {'label': '性别', 'value': '男' if new.get('gender') == 'male' else '女' if new.get('gender') == 'female' else '—'},
        {'label': '活动量', 'value': f'{label}', 'extra': f'系数 × {factor}'},
    ]
    return _profile_receipt(op, old, new, kpis, '设置档案', new.get('updated_at', '')[:16].replace('T', ' '))


def build_live_profile_activity(level: str) -> dict:
    """设活动量:写库 + 组装回执(呈现:活动等级 + 影响(TDEE 系数))"""
    import profile
    from analysis._utils import ACTIVITY_LEVEL_LABELS, TDEE_ACTIVITY_FACTORS, get_activity_factor

    old = profile.get_profile()
    old_level = old.get('activity_level') or 'moderate'
    result = profile.set_activity_level(level)
    new = profile.get_profile()

    old_f = TDEE_ACTIVITY_FACTORS.get(old_level, 1.55)
    new_f = result['activity_factor']
    delta_pct = round((new_f - old_f) / old_f * 100, 1) if old_f else 0

    kpis = [
        {'label': '活动量', 'value': result['activity_label'],
         'extra': f"({result['activity_level']})"},
        {'label': 'TDEE 系数', 'value': f'{old_f} → {new_f}',
         'extra': f'{delta_pct:+.1f}%'},
        {'label': '影响', 'value': f'每日消耗{delta_pct:+.1f}%',
         'extra': '仅日常活动,运动另计'},
        {'label': '更新时间', 'value': result['updated_at'][:16].replace('T', ' '),
         'extra': 'id=1'},
    ]
    return _profile_receipt('update', old, new, kpis, '设活动量', result['updated_at'][:16].replace('T', ' '))


def build_live_profile_update(field_value_pairs):
    """改档案:一次改多字段 + 组装合并回执(呈现:改前/改后 + 影响提示)

    Args:
        field_value_pairs: [(field, value), ...] 成对列表(支持多字段一行一条)
    """
    import profile

    old = profile.get_profile()
    results = []
    for field, value in field_value_pairs:
        results.append(profile.update_profile_field(field, value))
    new = profile.get_profile()

    # 影响提示注入 new_record(逐字段显示在 diff 新值下方)
    # 注意:update_profile_field 的 field 是别名(height/activity),new_record 键是列名(height_cm/activity_level)
    _FIELD_TO_COL = {'height': 'height_cm', 'activity': 'activity_level'}
    impact_map = {}
    for r in results:
        if r.get('impact'):
            col = _FIELD_TO_COL.get(r['field'], r['field'])
            impact_map[col] = r['impact']
    new = {**new, **{f'__impact_{k}': v for k, v in impact_map.items()}}

    # KPI:字段数 / 改前 / 改后 / 更新时间(多字段时显示首字段对比)
    first = results[0]
    last = results[-1]
    multi = len(results) > 1
    kpis = [
        {'label': '字段', 'value': f"{len(results)} 项" if multi else first['label'],
         'extra': '、'.join(r['label'] for r in results) if multi else f"field={first['field']}"},
        {'label': '改前', 'value': '见下方对比' if multi else str(first['old_value']),
         'extra': '—'},
        {'label': '改后', 'value': '见下方对比' if multi else str(first['new_value']),
         'extra': '—'},
        {'label': '更新时间', 'value': last['updated_at'][:16].replace('T', ' '),
         'extra': 'id=1'},
    ]
    return _profile_receipt('update', old, new, kpis, '改档案', last['updated_at'][:16].replace('T', ' '))


def main():
    p = argparse.ArgumentParser(description='渲染 CRUD 操作回执 HTML')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mock', help='mock JSON(通用 CRUD 实际数据由各 CLI 写入)')
    g.add_argument('--live-profile-set', action='store_true',
                   help='实读 DB 设置档案(全量写库 + 回执)')
    g.add_argument('--live-profile-activity', metavar='LEVEL',
                   help='实读 DB 设活动量(sedentary/light/moderate/active/very_active)')
    g.add_argument('--live-profile-update', action='store_true',
                   help='实读 DB 改档案(需 --field/--value)')
    p.add_argument('--age', type=int, help='设置档案:年龄')
    p.add_argument('--gender', help='设置档案:male/female')
    p.add_argument('--height', type=float, help='设置档案:身高(cm)')
    p.add_argument('--activity', help='设置档案:活动量档位')
    p.add_argument('--note', help='设置档案:备注')
    p.add_argument('--field', action='append', help='改档案字段(height/age/gender/activity/note,可多次)')
    p.add_argument('--value', action='append', help='改档案新值(与 --field 成对,可多次)')
    p.add_argument('--output')
    args = p.parse_args()

    if args.live_profile_update:
        fields = args.field or []
        values = args.value or []
        if not fields or len(fields) != len(values):
            print('❌ --live-profile-update 需要成对的 --field 与 --value(可多对)', file=sys.stderr)
            return 1
    if args.live_profile_set and (args.age is None and args.gender is None and
                                  args.height is None and args.activity is None):
        print('❌ --live-profile-set 至少需要 --age/--gender/--height/--activity 之一', file=sys.stderr)
        return 1

    try:
        if args.mock:
            data = _load_data(args.mock)
        elif args.live_profile_set:
            data = build_live_profile_set(age=args.age, gender=args.gender,
                                          height=args.height, activity=args.activity,
                                          note=args.note)
        elif args.live_profile_activity:
            data = build_live_profile_activity(args.live_profile_activity)
        else:
            data = build_live_profile_update(list(zip(fields, values)))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    # 输出名与场景关联 + 类型后缀(2026-08-02 用户拍板:HTML 名 = 场景名_类型)
    if args.live_profile_set:
        cmd_name, ot = '设置档案', 'receipt'
    elif args.live_profile_activity:
        cmd_name, ot = '设活动量', 'receipt'
    elif args.live_profile_update:
        cmd_name, ot = '改档案', 'receipt'
    else:
        cmd_name, ot = '操作回执', None
    out_path = Path(args.output) if args.output else (
        html_scene_path(SKILL_DIR, cmd_name, ot) if ot else html_path(SKILL_DIR, cmd_name))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   操作: {d["op"]} | #{d["record_id"]} | {d["meta"]["entity_type"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
