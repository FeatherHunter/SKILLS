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
from render_crud_view import _chain_valid  # 思考链校验单一来源(2026-08-02)


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


# 中文标签映射(2026-08-02 用户拍板:diff 卡必须中文,用户看不懂英文键名)
FIELD_LABELS = {
    'height_cm': '身高',
    'age': '年龄',
    'gender': '性别',
    'activity_level': '活动量',
    'note': '备注',
    'weight_kg': '体重',
    'bmi': 'BMI',
}


def _label_for(record_key: str) -> str:
    """字段键 → 中文标签(如 height_cm → 身高)"""
    return FIELD_LABELS.get(record_key, record_key)


def _latest_weight_kg():
    """最新体重(kg),TDEE 综合影响计算用"""
    import db as db_module
    from pathlib import Path
    try:
        db_path = db_module.find_db_path(Path(__file__).parent.parent)
        with db_module.connection(db_path) as conn:
            row = conn.execute(
                'SELECT weight_kg FROM weight_log ORDER BY date DESC, time DESC LIMIT 1'
            ).fetchone()
        return row['weight_kg'] if row else None
    except Exception:
        return None


def _tdee_estimate(age, gender, height_cm, activity_level):
    """按 Mifflin-St Jeor 估算 TDEE(综合影响卡用)"""
    from analysis._utils import get_activity_factor
    w = _latest_weight_kg()
    if not w or not height_cm or not age:
        return None, None
    bmr = 10 * w + 6.25 * height_cm - 5 * age + (5 if gender == 'male' else -161)
    factor = get_activity_factor(activity_level)
    return round(bmr * factor), round(bmr * factor - bmr * 1.55, 0)  # TDEE, 相对默认系数差


def _profile_receipt(op: str, old_record: dict, new_record: dict, kpis: list,
                     entity_label: str, action_at: str, summary: str = '') -> dict:
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
            'summary': summary,
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
    summary = (f"档案已{'设置' if is_first else '更新'}:身高{new.get('height_cm')}cm / 年龄{new.get('age')} / "
               f"性别{'男' if new.get('gender')=='male' else '女' if new.get('gender')=='female' else '—'} / "
               f"活动量 {label}(系数×{factor})")
    return _profile_receipt(op, old, new, kpis, '设置档案', new.get('updated_at', '')[:16].replace('T', ' '), summary)


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
    summary = (f"活动量已设置:{ACTIVITY_LEVEL_LABELS.get(old_level, old_level)} → "
               f"{result['activity_label']}({result['activity_level']}),TDEE 系数 {old_f} → {new_f}"
               f"({delta_pct:+.1f}%),每日消耗{delta_pct:+.1f}%")
    return _profile_receipt('update', old, new, kpis, '设活动量',
                            result['updated_at'][:16].replace('T', ' '), summary)


def build_live_profile_update(field_value_pairs):
    """改档案:一次改多字段 + 组装合并回执(呈现:改前/改后 + 影响提示)

    Args:
        field_value_pairs: [(field, value), ...] 成对列表(支持多字段一行一条)
    """
    import profile
    from analysis._utils import ACTIVITY_LEVEL_LABELS

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

    # KPI:字段数 / 改前 / 改后 / TDEE 综合影响 / 更新时间
    # 改前/改后显示首个变更字段的具体对比(2026-08-02 对抗审查:空转「见下方对比」无意义)
    first = results[0]
    last = results[-1]
    multi = len(results) > 1
    first_col = _FIELD_TO_COL.get(first['field'], first['field'])
    first_label = _label_for(first_col)
    first_old_disp = str(first['old_value'])
    first_new_disp = str(first['new_value'])
    if first_col == 'activity_level':
        first_old_disp = ACTIVITY_LEVEL_LABELS.get(str(first['old_value']).lower(), first['old_value'])
        first_new_disp = ACTIVITY_LEVEL_LABELS.get(str(first['new_value']).lower(), first['new_value'])
    if first_col == 'gender':
        first_old_disp = '男' if first['old_value'] == 'male' else '女' if first['old_value'] == 'female' else str(first['old_value'])
        first_new_disp = '男' if first['new_value'] == 'male' else '女' if first['new_value'] == 'female' else str(first['new_value'])
    tdee_new, _ = _tdee_estimate(
        new.get('age'), new.get('gender'), new.get('height_cm'), new.get('activity_level'))
    kpis = [
        {'label': '字段', 'value': f"{len(results)} 项" if multi else first['label'],
         'extra': '、'.join(r['label'] for r in results) if multi else f"field={first['field']}"},
        {'label': f'改前({first_label})', 'value': first_old_disp,
         'extra': f'共 {len(results)} 项变更' if multi else '—'},
        {'label': f'改后({first_label})', 'value': first_new_disp,
         'extra': f'其余见下方' if multi else '—'},
        {'label': '更新时间', 'value': last['updated_at'][:16].replace('T', ' '),
         'extra': 'id=1'},
    ]
    if tdee_new:
        kpis.append({'label': 'TDEE 估算', 'value': f'{tdee_new:,} 卡/天',
                     'extra': f'按最新体重×系数'})

    # 1 句话总结(2026-08-02 用户拍板:prompt 承诺的总结必须在 HTML 有对应物)
    changes = []
    for r in results:
        col = _FIELD_TO_COL.get(r['field'], r['field'])
        if col == 'activity_level':
            old_label = ACTIVITY_LEVEL_LABELS.get(str(r['old_value']).lower(), r['old_value'])
            new_label = ACTIVITY_LEVEL_LABELS.get(str(r['new_value']).lower(), r['new_value'])
            changes.append(f"活动量 {old_label}→{new_label}")
        else:
            changes.append(f"{r['label']} {r['old_value']}→{r['new_value']}")
    summary = f"已修改 {len(results)} 项:" + '、'.join(changes)
    if tdee_new:
        summary += f";TDEE 约 {tdee_new:,} 卡/天"
    return _profile_receipt('update', old, new, kpis, '改档案',
                            last['updated_at'][:16].replace('T', ' '), summary)


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
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    # ⭐ 思考链强制校验(2026-08-02 用户拍板):live 模式必传 + 有效性校验,防止 AI 偷懒
    if not args.mock and not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print("     --chain \"1.解析用户意图→2.调用CLI写库→3.生成回执\"", file=sys.stderr)
        return 2

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

    # 输出名与场景关联 + 类型后缀(2026-08-02 用户拍板:HTML 名 = 场景名_类型)
    if args.live_profile_set:
        cmd_name, ot = '设置档案', 'receipt'
    elif args.live_profile_activity:
        cmd_name, ot = '设活动量', 'receipt'
    elif args.live_profile_update:
        cmd_name, ot = '改档案', 'receipt'
    else:
        cmd_name, ot = '操作回执', None

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
        # AI 思考链注入 meta(复制日志带出 · 2026-08-02)
        if not args.mock and args.chain:
            data['data']['meta']['chain'] = args.chain.strip()
            data['data']['meta']['wake_word'] = cmd_name
        # 复制日志自描述字段(2026-08-02):渲染命令 + 数据来源
        if not args.mock:
            argv = sys.argv[1:]
            if '--output' in argv:
                i = argv.index('--output')
                argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
            data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(argv)
            data['data']['meta']['source'] = 'user_profile (写库回执)'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
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
