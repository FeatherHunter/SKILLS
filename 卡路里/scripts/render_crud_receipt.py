#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_crud_receipt.py — 通用 CRUD 操作回执 HTML 渲染器(回执型)

对应 SKILL.md 唤醒词(10 个):
  - 删饮食记录/改饮食记录 → mode=update/delete
  - 存食品/改食品   → mode=update/create
  - 删身材照       → mode=delete
  - 改照片标签     → mode=update
  - 改运动记录     → mode=update
  - 改体重记录     → mode=update
  - 设置档案       → mode=create/update(live-profile-set)
  - 设活动量       → mode=update(live-profile-activity)
  - 改档案         → mode=update(live-profile-update)
  - 改体重记录/改某日体重 → live-weight-update(ticket #4)
  - 删体重记录/删某日体重/批量删体重 → live-weight-delete(ticket #4)
对应模板: templates/crud_receipt.html

数据来源(互斥):
  --mock <json>                    mock 数据(测试)
  --live-profile-set               实读 DB:设置档案(全量写库 + 回执一体 · ticket #8)
  --live-profile-activity <level>  实读 DB:设活动量(写库 + 回执一体 · ticket #8)
  --live-profile-update           实读 DB:改档案(--field/--value,写库 + 回执一体)
  --live-weight-update            实读 DB:改体重记录(--id 或 --date,写库 + 回执一体 · ticket #4)
  --live-weight-delete            实读 DB:删体重记录(--id/--date/--start --end,写库 + 回执一体 · ticket #4)
"""
import argparse, json, sys
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path, html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # 校验+引号单一来源(2026-08-02)


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def render_html(data):
    # 2026-08-09 #43:批量删除用专门回执模板(weight_batch_delete.html)
    if data.get('data', {}).get('batch'):
        template = (SKILL_DIR / 'templates' / 'weight_batch_delete.html').read_text(encoding='utf-8')
    else:
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
    # 饮食记录(ticket #3 · 2026-08-02)
    'food_name': '食物名',
    'grams': '克数',
    'calories': '热量',
    'protein': '蛋白',
    'carbs': '碳水',
    'fat': '脂肪',
    'time': '时间',
    'date': '日期',
    'meal': '餐别',
    # 食品库(ticket #3 · 2026-08-02)
    'product_name': '食品名',
    'brand': '品牌',
    'saturated_fat': '饱和脂肪',
    'carbohydrates': '碳水',
    'sugar': '糖',
    'dietary_fiber': '膳食纤维',
    'sodium': '钠',
    'category': '分类',
    'source': '来源',
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
                     entity_label: str, action_at: str, summary: str = '', record_id: int = 1) -> dict:
    """组装 profile 回执数据契约(与 mock_crud_receipt.json 同构)

    record_id 默认 1(档案单行表);体重改记录按 ID 时传真实 id
    (2026-08-03 · ticket #43 场景 6 终审:硬编码 1 导致 idCard 显示 #1 而 summary 显示 #40)
    """
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': record_id,
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


def build_live_profile_set(age=None, gender=None, height=None, activity=None, note=None, reason=''):
    """设置档案:全量写库 + 组装回执(呈现:身高/年龄/性别/活动量 + 设置时间)

    首次设置 op=create;已存在档案 op=update(改前/改后对比)。
    reason: AI 采访式引导的推荐理由(2026-08-02 · 语义映射必须可审计 R6)
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

    # 逐字段影响提示(2026-08-02 缺口修复:设置档案也应有改前/改后+影响,同改档案)
    _FIELD_TO_COL = {'height': 'height_cm', 'activity': 'activity_level'}
    impact_map = {}
    for f, col in (('height', 'height_cm'), ('age', 'age'), ('gender', 'gender'), ('activity', 'activity_level')):
        old_v = old.get(col) if old else None
        new_v = new.get(col)
        if old_v != new_v:
            imp = profile._compute_impact(f, old_v, new_v)
            if imp:
                impact_map[col] = imp
    new_disp = {**new, **{f'__impact_{k}': v for k, v in impact_map.items()}}

    # 信息唯一性(2026-08-02):KPI 与 summary/diff 重复 → 只留 summary,不填 kpis
    summary = (f"档案已{'设置' if is_first else '更新'}:身高{new.get('height_cm')}cm / 年龄{new.get('age')} / "
               f"性别{'男' if new.get('gender')=='male' else '女' if new.get('gender')=='female' else '—'} / "
               f"活动量 {label}(系数×{factor})")
    # 无实际变化检测(2026-08-02 用户反馈:重复设置相同值 → 回执应明确告知,不假装变更)
    if not is_first:
        _SKIP = {'created_at', 'updated_at', 'id'}
        changed = any(old.get(k) != new.get(k) for k in new if k not in _SKIP and not k.startswith('__impact_'))
        if not changed:
            summary += ";以上值与当前档案一致,未产生实际变化"
    if reason:
        summary += f";推荐理由:{reason}"
    return _profile_receipt(op, old, new_disp, [], '设置档案', new.get('updated_at', '')[:16].replace('T', ' '), summary)


def build_live_profile_activity(level: str, reason=''):
    """设活动量:写库 + 组装回执(呈现:活动等级 + 影响(TDEE 系数))

    reason: AI 对用户语义(如「运动量很大」)→ 档位映射的说明(2026-08-02 · R6 语义映射可审计)
    """
    import profile
    from analysis._utils import ACTIVITY_LEVEL_LABELS, TDEE_ACTIVITY_FACTORS, get_activity_factor

    old = profile.get_profile()
    old_level = old.get('activity_level') or 'moderate'
    result = profile.set_activity_level(level)
    new = profile.get_profile()

    old_f = TDEE_ACTIVITY_FACTORS.get(old_level, 1.55)
    new_f = result['activity_factor']
    delta_pct = round((new_f - old_f) / old_f * 100, 1) if old_f else 0

    # 影响提示注入(2026-08-02 缺口修复:diff 卡逐字段影响,同改档案/设置档案)
    impact = (f"活动量 {ACTIVITY_LEVEL_LABELS.get(old_level, old_level)} → "
              f"{result['activity_label']},TDEE 系数 {old_f} → {new_f}({delta_pct:+.1f}%)")
    new_disp = {**new, '__impact_activity_level': impact}

    # 信息唯一性(2026-08-02):KPI 与 summary/diff 重复 → 只留 summary,不填 kpis
    summary = (f"活动量已设置:{ACTIVITY_LEVEL_LABELS.get(old_level, old_level)} → "
               f"{result['activity_label']}({result['activity_level']}),TDEE 系数 {old_f} → {new_f}"
               f"({delta_pct:+.1f}%),每日消耗{delta_pct:+.1f}%")
    if reason:
        summary += f";映射依据:{reason}"
    return _profile_receipt('update', old, new_disp, [], '设活动量',
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

    # 信息唯一性(2026-08-02):KPI 与 summary/diff 重复 → 只留 summary,不填 kpis
    first = results[0]
    last = results[-1]
    tdee_new, _ = _tdee_estimate(
        new.get('age'), new.get('gender'), new.get('height_cm'), new.get('activity_level'))

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
    return _profile_receipt('update', old, new, [], '改档案',
                            last['updated_at'][:16].replace('T', ' '), summary)


# ==================== ticket #4 · 体重 改/删 live 模式 ====================

def _weight_record(weight_id):
    """查单条体重记录"""
    import db as db_module
    db_path = db_module.find_db_path(Path(__file__).parent.parent)
    with db_module.connection(db_path) as conn:
        row = conn.execute(
            'SELECT id, date, time, weight_kg, bmi, note FROM weight_log WHERE id = ?', (weight_id,)
        ).fetchone()
    return dict(row) if row else None


def build_live_weight_update(target_id=None, target_date=None, weight_kg=None, note=None):
    """改体重记录 / 改某日体重:写库 + 组装回执(呈现:命中条数/改前/改后 + 影响字段)

    按 ID:改 1 条,按日期:命中 1+ 条全改
    """
    import weight

    if target_id is not None:
        old = _weight_record(target_id)
        if old is None:
            raise ValueError(f'体重记录 ID {target_id} 不存在')
        r = weight.update_weight(target_id, weight_kg=weight_kg, note=note)
        if r is None:
            raise ValueError('更新失败')
        new = _weight_record(target_id)
        summary = f"已修改 #{target_id}({r['date']}):体重 {r['old_weight']}→{r['new_weight']}kg"
        if note is not None and r.get('note') is not None:
            # 2026-08-03 · ticket #43 场景 6 终审:备注变更补旧值,与体重「旧→新」格式一致(原"备注→新值"歧义)
            old_note = (old or {}).get('note') or '(无)'
            summary += f",备注 {old_note}→{r['note']}"
        if r.get('bmi'):
            summary += f";BMI {r['bmi']}"
        return _profile_receipt('update', old, new, [], '体重记录', r['date'], summary, target_id)

    # 按日期
    if not target_date:
        raise ValueError('--live-weight-update 需要 --id 或 --date')
    r = weight.update_weight_by_date(target_date, weight_kg=weight_kg, note=note)
    if r is None:
        raise ValueError(f'{target_date} 无体重记录')
    old_rows = r['old_rows']
    first = old_rows[0]
    old_record = {'date': first['date'], 'time': first['time'],
                  'weight_kg': first['weight_kg'], 'bmi': first['bmi'], 'note': first['note']}
    new_record = {'date': target_date, 'weight_kg': r['new_weight'] or first['weight_kg'],
                  'bmi': r['bmi'] if r['bmi'] is not None else first['bmi'],
                  'note': r['note'] if r['note'] is not None else first['note']}
    # 2026-08-04 · ticket #43 场景 7 终审:备注-only 更新不再出现 "体重 X→Nonekg"(仅改体重才带体重段,
    # 备注变更补旧值,与改体重记录(按 ID)路径同款格式)
    summary = f"已修改 {target_date} 的 {r['hit_count']} 条记录"
    segments = []
    if r['new_weight'] is not None:
        segments.append(f"体重 {first['weight_kg']}→{r['new_weight']}kg")
    if r['note'] is not None:
        segments.append(f"备注 {first['note'] or '(无)'}→{r['note']}")
    if segments:
        summary += ":" + ", ".join(segments)
    if r['bmi']:
        summary += f";BMI {r['bmi']}"
    return {
        'status': 'ok',
        'data': {
            'op': 'update',
            'record_id': first['id'],
            'old_record': old_record,
            'new_record': new_record,
            'context': {'kpis': [{'label': '命中条数', 'value': str(r['hit_count']), 'extra': target_date}]},
            'meta': {'action_at': target_date, 'entity_type': '体重记录'},
            'summary': summary,
        },
        'message': '已生成改体重记录 回执',
    }


def build_live_weight_delete(target_id=None, target_date=None, start=None, end=None):
    """删体重记录 / 删某日体重 / 批量删体重:删除 + 组装回执(呈现:确认回执含快照/条数/范围)"""
    import weight

    if target_id is not None:
        r = weight.delete_weight(target_id)
        if r is None:
            raise ValueError(f'体重记录 ID {target_id} 不存在')
        snap = {'date': r['date'], 'time': r['time'], 'weight_kg': r['weight_kg'], 'bmi': r['bmi'], 'note': r['note']}
        summary = f"已删除 #{r['id']}({r['date']} {r['time'][:5]}) 体重 {r['weight_kg']}kg"
        totals = [{'label': '被删记录', 'value': f"{r['date']} {r['weight_kg']}kg", 'unit': ''}]
        undo = f"python scripts/calorie_tracker.py weight {r['weight_kg']} --note '{r['note'] or ''}' --date {r['date']}"
        return _weight_delete_receipt('delete', r['id'], snap, totals, summary, r['date'], undo)

    if target_date is not None:
        r = weight.delete_weight_by_date(target_date)
        if r is None:
            raise ValueError(f'{target_date} 无体重记录')
        first = r['snapshot'][0]
        summary = f"已删除 {target_date} 的 {r['deleted_count']} 条记录(如 {first['weight_kg']}kg)"
        totals = [{'label': '删除条数', 'value': str(r['deleted_count']), 'unit': '条'},
                  {'label': '日期', 'value': target_date, 'unit': ''}]
        undo = f"python scripts/calorie_tracker.py weight {first['weight_kg']} --date {target_date}"
        return _weight_delete_receipt('delete', first['id'], r['snapshot'][0], totals, summary, target_date, undo)

    if start and end:
        r = weight.delete_weight_range(start, end)
        if r is None:
            raise ValueError(f'{start} ~ {end} 无体重记录')
        first = r['snapshot'][0]
        summary = f"已删除 {start} ~ {end} 的 {r['deleted_count']} 条记录"
        totals = [{'label': '时间范围', 'value': f'{start} ~ {end}', 'unit': ''},
                  {'label': '删除条数', 'value': str(r['deleted_count']), 'unit': '条'}]
        undo = f"python scripts/calorie_tracker.py weight {first['weight_kg']} --date {first['date']}"
        # 2026-08-09 #43 用户拍板:批量删除用专门回执(全量明细表)
        # 2026-08-09 #43 审查建议①:删除后最新体重提示(破坏性操作后用户关心数据现状)
        import sqlite3 as _sq
        import db as db_module
        _db = db_module.find_db_path(SKILL_DIR)
        _conn = _sq.connect(str(_db))
        _latest = _conn.execute(
            'SELECT date, weight_kg FROM weight_log ORDER BY date DESC, time DESC LIMIT 1').fetchone()
        _conn.close()
        latest_after = {'date': _latest[0], 'weight_kg': _latest[1]} if _latest else None
        return _weight_delete_receipt('delete', first['id'], r['snapshot'][0], totals, summary,
                                      f'{start} ~ {end}', undo, items=r['snapshot'], batch=True,
                                      latest_after=latest_after)

    raise ValueError('--live-weight-delete 需要 --id / --date / --start+--end 之一')


def _weight_delete_receipt(op, record_id, snapshot, totals, summary, action_at, undo_cli,
                           items=None, batch=False, latest_after=None):
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': record_id,
            'old_record': snapshot,
            'new_record': {},
            'items': items or [],
            'batch': batch,
            'latest_after': latest_after,
            'context': {'kpis': [], 'totals': totals},
            'meta': {'action_at': action_at, 'entity_type': '体重记录', 'undo_cli': undo_cli},
            'summary': summary,
        },
        'message': '已生成删体重记录 回执',
    }


# ==================== 饮食记录 live 模式(ticket #3 · 2026-08-02) ====================

def _diet_receipt(op: str, record_id, old_record: dict, new_record: dict,
                  entity_label: str, action_at: str, summary: str = '',
                  kpis: list | None = None, items: list | None = None) -> dict:
    """组装饮食回执数据契约(与 profile 回执同构,复用 crud_receipt.html)

    items: 明细列表(如复制昨日饮食的复制明细 · #44 审查),模板以「明细卡」展示
    """
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': record_id,
            'old_record': old_record or {},
            'new_record': new_record or {},
            'context': {'kpis': kpis or [], 'items': items or []},
            'meta': {
                'action_at': action_at,
                'entity_type': entity_label,
            },
            'summary': summary,
        },
        'message': f'已生成{entity_label} 回执',
    }


def build_live_diet_add(food, calories, protein, carbs='0', fat='0', grams='100',
                        note='', target_date=None, target_time=None, meal=None):
    """记一餐 / 记一餐(含备注) / 补记饮食:写库 + 回执(呈现:食物/克数/营养 + 餐别 + 时间 + 一句话)"""
    import diet
    r = diet.add_meal(food, calories, protein, carbs, fat, grams, note,
                      target_date=target_date, target_time=target_time,
                      meal_override=meal)
    if r is None:
        raise ValueError('记一餐失败(数值校验不过)')
    if r.get('duplicate'):
        # #262 幂等防重:同 date+time+food_name+grams+calories 已存在 → 未写库,回执如实提示
        # (duplicate 分支返回 dict 缺营养字段,不能走下方正常 new_record 构建;用输入参数回填)
        new_record = {
            'food_name': r['food_name'], 'grams': grams, 'calories': calories,
            'protein': protein, 'carbs': carbs, 'fat': fat,
            'note': note or '', 'meal': r['meal'], 'time': r['time'], 'date': r['date'],
        }
        summary = r.get('message') or f"{r['food_name']} 重复记录已跳过(未重复写入)"
        return _diet_receipt('create', r.get('dup_id') or 0, {}, new_record, '记一餐',
                             f"{r['date']} {r['time']}", summary)
    new_record = {
        'food_name': r['food_name'], 'grams': r['grams'], 'calories': r['calories'],
        'protein': r['protein'], 'carbs': r['carbs'], 'fat': r['fat'],
        'note': r['note'] or '', 'meal': r['meal'], 'time': r['time'], 'date': r['date'],
    }
    date_label = '今日' if not target_date else r['date']
    summary = (f"{r['food_name']}({r['grams']}g, {r['calories']}卡)已记入{date_label} {r['meal']} "
               f"({r['time'][:5]})")
    if r['cal_goal']:
        rem = r['remaining_cal'] or 0
        marker = '剩余' if rem > 0 else '超标'
        # #44 审查:补记场景累计段用「当日累计」,避免日期重复(已记入 X …;X 累计 → 当日累计)
        cumulative = '当日累计' if target_date else '今日累计'
        summary += f";{cumulative} {r['today_total_cal']}/{r['cal_goal']}卡,{marker} {abs(rem):.0f}卡"
    return _diet_receipt('create', r['id'], {}, new_record, '记一餐',
                         f"{r['date']} {r['time']}", summary)


def build_live_diet_batch(input_path):
    """批量补记饮食:写库 + 回执(呈现:写入/跳过/失败条数 + 失败明细)"""
    import json as _json
    from pathlib import Path as _P
    import diet
    p = _P(input_path)
    if not p.exists():
        raise FileNotFoundError(f'批量补记输入文件不存在: {input_path}')
    entries = _json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(entries, list):
        raise ValueError('批量补记 JSON 顶层必须是数组(每项一餐)')
    r = diet.add_meals_batch(entries)
    new_record = {'写入': r['added'], '跳过': r['skipped'], '失败': r['failed']}
    summary = f"批量补记完成:写入 {r['added']} 条"
    if r['skipped']:
        summary += f",跳过 {r['skipped']} 条"
    if r['failed']:
        summary += f",失败 {r['failed']} 条"
    fail_detail = ';'.join(f"第{idx+1}条:{reason}" for idx, reason in r['failures'][:5])
    if fail_detail:
        summary += f";{fail_detail}"
    return _diet_receipt('create', 0, {}, new_record, '批量补记饮食',
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary)


def build_live_diet_batch_meal(input_path):
    """同餐多食物 → 单一回执(issue #158 · 2026-08-09)

    现象:用户「中午吃米饭、清蒸鱼、炒青菜、豆腐汤」→ AI 逐个调 add,
    每个食物一个 receipt,聊天窗口被 N 个回执挤满。
    修复:AI 把同餐多个食物一次性传入 --input(每项一个食物,同 date/time),
    写库 N 条但**只回 1 个 receipt**:餐别/时间 + 全部食物列表 + 营养合计。

    输入 JSON(每项一个食物,同餐同 date/time):
        [{"food_name":"米饭","grams":200,"calories":232,"protein":4.3,"carbs":50,"fat":0.5},
         {"food_name":"清蒸鱼","grams":150,"calories":165,"protein":28,"carbs":0,"fat":6}]
    可选: meal(餐别,仅展示用 — food_log 无 meal 列,由 time 推断)/ date / time

    V3 调用透明:summary 明确「本次写库 N 条 → 合并为 1 个回执」。
    """
    import json as _json
    from pathlib import Path as _P
    import diet
    p = _P(input_path)
    if not p.exists():
        raise FileNotFoundError(f'同餐批量输入文件不存在: {input_path}')
    entries = _json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(entries, list) or not entries:
        raise ValueError('同餐批量 JSON 顶层必须是非空数组(每项一个食物)')

    # 同餐公共字段(取第一项,整餐一致;date 缺省=今天,time 缺省=now)
    meal = entries[0].get('meal') or ''
    d = entries[0].get('date') or date.today().isoformat()
    t = entries[0].get('time') or datetime.now().strftime('%H:%M:%S')

    # 竞态修复(2026-08-09 对抗审查):add_meals_batch 内部对未显式传 time 的条目
    # 各自取 datetime.now(),跨秒时各条 time 不同 → 回查 date+time 只命中部分/0 条。
    # 同餐同时刻是语义要求 → 统一注入 date/time 到每个 entry,消除竞态。
    for e in entries:
        e['date'] = d
        e['time'] = t

    r = diet.add_meals_batch(entries)
    added = r['added']
    # 幂等防重(2026-08-11 #262): added=0 但 skipped>0(全重复)时,回查已存在本餐生成回执而非报错
    # 语义: 同餐重复调用(如反复补录同一餐) → 展示已有记录 + 明确「已存在,未重复写入」
    if added == 0 and not (r.get('skipped') or r.get('failed')):
        raise ValueError('同餐批量写入 0 条,请检查输入格式')
    # 全重复 = 本次 0 条新增 + 有跳过(重复或非法)且无真实写入;去重展示已有本餐
    all_duplicate = added == 0 and (r.get('skipped', 0) > 0)

    # 写库成功后回查本餐明细(按 date+time,只取最近 added 条 → 列表 + 合计)
    # 全重复时回查该餐去重后食物(dedupe=True),避免历史重复行撑爆 items
    items, totals = _fetch_meal_items(d, t, added if added > 0 else 1, dedupe=all_duplicate)
    cal, pro, carb, fat = totals

    # 餐别从 time 推断(food_log 无 meal 列 · add_meals_batch 不写 meal)
    meal_label = meal or diet.infer_meal_type(t)
    new_record = {
        'meal': meal_label, 'time': t, 'date': d,
        'food_count': added, 'total_calories': cal,
        'total_protein': pro, 'total_carbs': carb, 'total_fat': fat,
    }
    date_label = d if d != date.today().isoformat() else '今日'
    summary = (f"{meal_label} {len(items)} 个食物已记入 {date_label}"
               f" · 共 {cal} 卡(蛋白 {pro}g/碳水 {carb}g/脂肪 {fat}g)")
    if r['skipped'] or r['failed']:
        summary += f" · 跳过 {r['skipped']} 条,失败 {r['failed']} 条"
    # V3 调用透明:AI 内部写库 N 条,统一 1 个回执
    if all_duplicate:
        summary += " · 本餐记录已存在,未重复写入"
    else:
        summary += f" · 本次写库 {added} 条 → 合并 1 个回执"
    kpis = [
        {'label': '食物数', 'value': f'{len(items)} 种', 'extra': '本餐'},
        {'label': '总热量', 'value': f'{cal} 卡', 'extra': '合计'},
        {'label': '总蛋白', 'value': f'{pro} g', 'extra': '合计'},
        {'label': '总碳水', 'value': f'{carb} g', 'extra': '合计'},
        {'label': '总脂肪', 'value': f'{fat} g', 'extra': '合计'},
    ]
    return _diet_receipt('create', 0, {}, new_record, '记一餐(同餐合并)',
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary,
                         kpis=kpis, items=items)


def _fetch_meal_items(date_str, time_str, n_expected, dedupe=False):
    """回查同餐写入的记录明细(按 date+time),返回 (items, (cal, pro, carb, fat))

    items 与模板 crud_receipt.html 明细卡字段对齐:time/food_name/grams/calories + label
    dedupe=True: 按 food_name 去重(幂等全重复场景,展示已有食物而非历史重复行)
    """
    import diet as _diet
    conn = _diet._get_db()
    cur = conn.cursor()
    if dedupe:
        # 全重复:按 food_name 去重取最新一条(展示本餐已有食物清单)
        cur.execute('''
            SELECT time, food_name, grams, calories, protein, carbs, fat
            FROM food_log
            WHERE date = ? AND time = ?
              AND id IN (SELECT MAX(id) FROM food_log WHERE date = ? AND time = ? GROUP BY food_name)
            ORDER BY id
        ''', (date_str, time_str, date_str, time_str))
    else:
        cur.execute('''
            SELECT time, food_name, grams, calories, protein, carbs, fat
            FROM food_log
            WHERE date = ? AND time = ?
            ORDER BY id DESC LIMIT ?
        ''', (date_str, time_str, n_expected))
    rows = cur.fetchall()
    conn.close()
    items = []
    cal = pro = carb = fat = 0.0
    for r in rows:
        items.append({'label': '已写入', 'time': r[0] or '', 'food_name': r[1],
                      'grams': r[2] or 0, 'calories': r[3] or 0})
        cal += r[3] or 0; pro += r[4] or 0; carb += r[5] or 0; fat += r[6] or 0
    return items, (round(cal), round(pro, 1), round(carb, 1), round(fat, 1))


def build_live_diet_copy(from_date, to_date=None):
    """复制昨日饮食:写库 + 回执(呈现:复制条数/跳过条数)"""
    import diet
    from datetime import date as _date, timedelta as _td
    if not from_date:
        from_date = (_date.today() - _td(days=1)).isoformat()
    r = diet.copy_meals(from_date, to_date)
    new_record = {'from': r['from_date'], 'to': r['to_date'],
                  '复制': r['copied'], '跳过': r['skipped']}
    summary = f"已从 {r['from_date']} 复制 {r['copied']} 条到 {r['to_date']}"
    if r['skipped']:
        summary += f"(同日同食物已存在,跳过 {r['skipped']} 条)"
    # #44 审查(用户第一性原理):复制明细展示——用户需要知道复制了哪些数据
    items = [{'label': '已复制', 'time': it['time'], 'food_name': it['food_name'],
              'grams': it['grams'], 'calories': it['calories']} for it in r['copied_items']]
    items += [{'label': '已跳过', 'time': it['time'], 'food_name': it['food_name'],
               'grams': it['grams'], 'calories': it['calories']} for it in r['skipped_items']]
    return _diet_receipt('create', 0, {}, new_record, '复制昨日饮食',
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary,
                         items=items)


def build_live_diet_update(entry_id, **kwargs):
    """改饮食记录:写库 + 回执(呈现:改前/改后 + 影响字段)"""
    import diet
    r = diet.update_meal(entry_id, **kwargs)
    if not r['ok']:
        raise ValueError(r['error'])
    b, a = r['before'], r['after']
    new_record = {k: v for k, v in a.items() if k != 'id'}
    old_record = {k: v for k, v in b.items() if k != 'id'}
    summary = f"已改 {a['food_name']}:{'、'.join(r['changed'])}"
    return _diet_receipt('update', entry_id, old_record, new_record, '改饮食记录',
                         f"{a['date']} {a['time']}", summary)


def build_live_diet_update_date(target_date, **kwargs):
    """改某日饮食:按日期批量改 + 回执(呈现:命中条数/改前/改后)"""
    import diet
    r = diet.update_meals_by_date(target_date, **kwargs)
    if not r['ok']:
        raise ValueError(r['error'])
    summary = f"改某日饮食:{target_date} 命中 {r['matched']} 条,已更新 {r['updated']} 条"
    if r['changed_fields']:
        summary += f"(字段:{'、'.join(r['changed_fields'])})"
    # 改前/改后(权威清单 D2.2):字段级 diff——旧值唯一则显示,多种则标注
    old_record = {'date': None, '命中': None, '更新': None}
    new_record = {'date': target_date, '命中': r['matched'], '更新': r['updated']}
    for k in r['changed_fields']:
        olds = sorted({b.get(k) for b in r['before']}, key=lambda v: str(v))
        news = {a.get(k) for a in r['after']}
        old_record[k] = olds[0] if len(olds) == 1 else ('(多种旧值)' if len(olds) > 1 else None)
        new_record[k] = next(iter(news), None)
    return _diet_receipt('update', 0, old_record, new_record,
                         '改某日饮食', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary)


def build_live_diet_delete(entry_id):
    """删饮食记录:写库 + 回执(呈现:删除前快照/确认回执)"""
    import diet
    conn = diet._get_db()
    c = conn.cursor()
    c.execute('SELECT id, date, time, food_name, grams, calories, protein, carbs, fat, note FROM food_log WHERE id = ?', (entry_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise ValueError(f'记录 {entry_id} 不存在')
    keys = ('id', 'date', 'time', 'food_name', 'grams', 'calories', 'protein', 'carbs', 'fat', 'note')
    old_record = dict(zip(keys, row))
    old_record.pop('id', None)
    diet.delete_meal(entry_id)
    summary = f"已删除 {old_record['food_name']}({old_record['calories']}卡, {old_record['date']} {old_record['time'][:5]})"
    return _diet_receipt('delete', entry_id, old_record, {}, '删饮食记录',
                         f"{old_record['date']} {old_record['time']}", summary)


def build_live_diet_delete_meal(target_date, meal_type):
    """删一餐:按餐别删 + 回执(呈现:餐别选择/删除条数/删除明细)"""
    import diet
    r = diet.delete_meals_by_type(target_date, meal_type)
    if not r['ok']:
        raise ValueError(r['error'])
    summary = f"已删除 {target_date} {meal_type} 的 {r['deleted']} 条记录"
    # #44 审查(用户第一性原理):删除必须知道删了什么——删除前明细
    items = [{'label': '已删除', 'time': it['time'], 'food_name': it['food_name'],
              'grams': it['grams'], 'calories': it['calories'],
              'note': it.get('note') or ''} for it in r['before']]
    return _diet_receipt('delete', 0, {}, {'date': r['date'], '餐别': r['meal'], '删除': r['deleted']},
                         '删一餐', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary,
                         items=items)


def build_live_diet_delete_date(target_date):
    """删某日饮食:一整天清空 + 回执(呈现:删除条数/日期/删除明细)"""
    import diet
    r = diet.delete_meals_by_date(target_date)
    summary = f"已清空 {r['date']} 的 {r['deleted']} 条饮食记录"
    # #44 审查(用户第一性原理):删除必须知道删了什么——删除前明细
    items = [{'label': '已删除', 'time': it['time'], 'food_name': it['food_name'],
              'grams': it['grams'], 'calories': it['calories'],
              'note': it.get('note') or ''} for it in r['before']]
    return _diet_receipt('delete', 0, {}, {'date': r['date'], '删除': r['deleted']},
                         '删某日饮食', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary,
                         items=items)


def build_live_diet_delete_range(start_date, end_date):
    """批量删饮食:按日期范围删 + 回执(呈现:时间范围/删除条数/删除明细/确认回执)"""
    import diet
    r = diet.delete_meals_by_range(start_date, end_date)
    summary = f"已删除 {r['start']} ~ {r['end']} 的 {r['deleted']} 条饮食记录"
    # #44 审查(用户第一性原理):删除必须知道删了什么——删除前明细
    items = [{'label': '已删除', 'time': it['time'], 'food_name': it['food_name'],
              'grams': it['grams'], 'calories': it['calories'],
              'note': it.get('note') or ''} for it in r['before']]
    return _diet_receipt('delete', 0, {}, {'start': r['start'], 'end': r['end'], '删除': r['deleted']},
                         '批量删饮食', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary,
                         items=items)


def build_live_water_add(ml, target_date=None):
    """记喝水:写库 + 回执(呈现:累计今日饮水量/距目标 + 一句话)"""
    import water
    r = water.add_water(ml, target_date=target_date)
    if r is None:
        raise ValueError('记喝水失败(ml 校验不过)')
    date_label = '今日' if not target_date else r['date']
    # #44 审查:超目标不写「剩余 -X」,改「超过 X」
    if r['remaining_ml'] >= 0:
        remain_txt = f"剩余 {r['remaining_ml']}ml"
    else:
        remain_txt = f"超过 {abs(r['remaining_ml'])}ml"
    summary = (f"已记录饮水 {r['ml']}ml,{date_label}累计 {r['today_total_ml']}/{r['water_goal_ml']}ml "
               f"({remain_txt})")
    new_record = {'ml': r['ml'], 'today_total_ml': r['today_total_ml'], 'target_ml': r['water_goal_ml'],
                  'remaining_ml': r['remaining_ml'], 'date': r['date'], 'time': r['time']}
    return _diet_receipt('create', r['id'], {}, new_record, '记喝水',
                         f"{r['date']} {r['time']}", summary)


def build_live_product_add(name, brand, calories, protein, fat, saturated_fat,
                           carbohydrates, sugar, dietary_fiber, sodium, note=''):
    """存食品:写库 + 回执(呈现:写入回执 + 名称)"""
    import product_library
    ok = product_library.add_product(name, brand, calories, protein, fat, saturated_fat,
                                     carbohydrates, sugar, dietary_fiber, sodium, note)
    if not ok:
        raise ValueError('存食品失败')
    new_record = {'product_name': name, 'brand': brand or '', 'calories': calories,
                  'protein': protein, 'fat': fat, 'carbohydrates': carbohydrates}
    summary = f"已存入食品库「{name}」(热量 {calories} 卡/100g)"
    return _diet_receipt('create', 0, {}, new_record, '存食品',
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary)


def build_live_product_update(product_id, **kwargs):
    """改食品:写库 + 回执(呈现:改前/改后)"""
    import product_library
    conn = product_library._get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM nutrition_products WHERE id = ?', (product_id,))
    cols = [d[0] for d in c.description]
    row = c.fetchone()
    conn.close()
    if not row:
        raise ValueError(f'食品 {product_id} 不存在')
    before = dict(zip(cols, row))
    old_name = before.get('product_name', '')
    ok = product_library.update_product(product_id, **kwargs)
    if not ok:
        raise ValueError('改食品失败')
    summary = f"已更新「{old_name}」:{'、'.join(kwargs)}"
    # 改前/改后(权威清单 D4.4):旧值全量快照
    old_record = {k: before.get(k) for k in kwargs}
    new_record = dict(kwargs)
    return _diet_receipt('update', product_id, old_record, new_record,
                         '改食品', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary)


def build_live_product_deprecate(product_id):
    """下架食品:标废弃 + 回执(呈现:标废弃回执 + 提示已下架)"""
    import product_library
    r = product_library.deprecate_product(product_id)
    if not r['ok']:
        raise ValueError(r['error'])
    summary = f"「{r['name']}」已下架,搜索/查询/导入去重不再出现"
    # 改前/改后(权威清单 D4.5):状态 正常→已下架;提示放 summary 即可,不占 diff 字段
    return _diet_receipt('update', r['id'], {'product_name': r['name'], 'is_deprecated': 0},
                         {'product_name': r['name'], 'is_deprecated': 1},
                         '下架食品', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), summary)


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
    # 饮食记录 live 模式(ticket #3 · 2026-08-02)
    g.add_argument('--live-diet-add', action='store_true',
                   help='记一餐/补记饮食:写库 + 回执(flag 后接位置参数 food cal pro,可选 --carbs/--fat/--grams/--note/--date/--time/--meal)')
    g.add_argument('--live-diet-batch', action='store_true',
                   help='批量补记饮食:从 --input JSON 数组写库 + 回执')
    g.add_argument('--live-diet-batch-meal', action='store_true',
                   help='同餐多食物(issue #158):从 --input JSON 数组写库 + 单一回执(食物列表+营养合计)')
    g.add_argument('--live-diet-copy', action='store_true',
                   help='复制昨日饮食:写库 + 回执(--from/--to 可选)')
    g.add_argument('--live-diet-update', action='store_true',
                   help='改饮食记录:写库 + 回执(flag 后接 <id> + 字段)')
    g.add_argument('--live-diet-update-date', action='store_true',
                   help='改某日饮食:按日期批量改 + 回执(flag 后接 <date> + 字段)')
    g.add_argument('--live-diet-delete', action='store_true',
                   help='删饮食记录:写库 + 回执(flag 后接 <id>)')
    g.add_argument('--live-diet-delete-meal', action='store_true',
                   help='删一餐:按餐别删 + 回执(flag 后接 <date> <餐别>)')
    g.add_argument('--live-diet-delete-date', action='store_true',
                   help='删某日饮食:一整天清空 + 回执(flag 后接 <date>)')
    g.add_argument('--live-diet-delete-range', action='store_true',
                   help='批量删饮食:按日期范围删 + 回执(flag 后接 <start> <end>)')
    g.add_argument('--live-water-add', action='store_true',
                   help='记喝水:写库 + 回执(flag 后接 <ml>,可选 --date)')
    g.add_argument('--live-product-add', action='store_true',
                   help='存食品:写库 + 回执(flag 后接 11 个营养字段)')
    g.add_argument('--live-product-update', action='store_true',
                   help='改食品:写库 + 回执(flag 后接 <id> + 字段)')
    g.add_argument('--live-product-deprecate', action='store_true',
                   help='下架食品:标废弃 + 回执(flag 后接 <id>)')
    # 体重记录 live 模式(ticket #4 · 2026-08-02)
    g.add_argument('--live-weight-update', action='store_true',
                   help='改体重记录/改某日体重:写库 + 回执(flag 后接 <id|date>,可带 --weight/--note)')
    g.add_argument('--live-weight-delete', action='store_true',
                   help='删体重记录/删某日体重/批量删体重:写库 + 回执(flag 后接 <id|date|start end>)')
    p.add_argument('--age', type=int, help='设置档案:年龄')
    p.add_argument('--gender', help='设置档案:male/female')
    p.add_argument('--height', type=float, help='设置档案:身高(cm)')
    p.add_argument('--activity', help='设置档案:活动量档位')
    p.add_argument('--note', help='设置档案:备注 / 记一餐:备注')
    p.add_argument('--field', action='append', help='改档案/改食品字段(可多次)')
    p.add_argument('--value', action='append', help='改档案新值(与 --field 成对,可多次)')
    p.add_argument('--date', help='记一餐/记喝水:日期 YYYY-MM-DD')
    p.add_argument('--time', help='记一餐:时间 HH:MM')
    p.add_argument('--meal', help='记一餐:餐别(早餐/午餐/下午茶/晚餐/夜宵)')
    p.add_argument('--from', dest='from_date', help='复制昨日饮食:来源日期')
    p.add_argument('--to', dest='to_date', help='复制昨日饮食:目标日期')
    p.add_argument('--input', help='批量补记:JSON 文件路径')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--reason', help='AI 映射/推荐理由(设活动量:语义→档位;设置档案:采访推荐 · 2026-08-02 R6)')
    p.add_argument('--output')
    args, extra = p.parse_known_args()

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
    _LIVE_NAMES = {
        'live_profile_set': ('设置档案', 'receipt'),
        'live_profile_activity': ('设活动量', 'receipt'),
        'live_profile_update': ('改档案', 'receipt'),
        'live_diet_add': ('记一餐', 'receipt'),
        'live_diet_batch': ('批量补记饮食', 'receipt'),
        'live_diet_batch_meal': ('记一餐(同餐合并)', 'receipt'),
        'live_diet_copy': ('复制昨日饮食', 'receipt'),
        'live_diet_update': ('改饮食记录', 'receipt'),
        'live_diet_update_date': ('改某日饮食', 'receipt'),
        'live_diet_delete': ('删饮食记录', 'receipt'),
        'live_diet_delete_meal': ('删一餐', 'receipt'),
        'live_diet_delete_date': ('删某日饮食', 'receipt'),
        'live_diet_delete_range': ('批量删饮食', 'receipt'),
        'live_water_add': ('记喝水', 'receipt'),
        'live_product_add': ('存食品', 'receipt'),
        'live_product_update': ('改食品', 'receipt'),
        'live_product_deprecate': ('下架食品', 'receipt'),
        'live_weight_update': ('改体重记录', 'receipt'),
        'live_weight_delete': ('删体重记录', 'receipt'),
    }
    active = None
    for flag_name in ('live_profile_set', 'live_profile_activity', 'live_profile_update',
                      'live_diet_add', 'live_diet_batch', 'live_diet_batch_meal', 'live_diet_copy',
                      'live_diet_update', 'live_diet_update_date', 'live_diet_delete',
                      'live_diet_delete_meal', 'live_diet_delete_date', 'live_diet_delete_range',
                      'live_water_add', 'live_product_add', 'live_product_update',
                      'live_product_deprecate', 'live_weight_update', 'live_weight_delete'):
        if getattr(args, flag_name.replace('-', '_')):
            active = flag_name
            break
    cmd_name, ot = _LIVE_NAMES.get(active, ('操作回执', None))
    # issue #49 · 2026-08-11 拍板:记一餐回执文件名带食物名(仅 live_diet_add,其余保持原样)
    file_suffix = None

    try:
        if args.mock:
            data = _load_data(args.mock)
        elif args.live_profile_set:
            data = build_live_profile_set(age=args.age, gender=args.gender,
                                          height=args.height, activity=args.activity,
                                          note=args.note, reason=args.reason or '')
        elif args.live_profile_activity:
            data = build_live_profile_activity(args.live_profile_activity, reason=args.reason or '')
        elif args.live_profile_update:
            data = build_live_profile_update(list(zip(fields, values)))
        elif args.live_diet_add:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-add') + 1:]
            pos = []
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--'):
                    k = rest[i][2:]
                    if i + 1 < len(rest) and not rest[i+1].startswith('--'):
                        kw[k] = rest[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    pos.append(rest[i])
                    i += 1
            if len(pos) < 3:
                print('❌ --live-diet-add 需要 <food> <calories> <protein> [carbs] [fat] [grams] [note]',
                      file=sys.stderr)
                return 1
            food, cal, pro = pos[0], pos[1], pos[2]
            file_suffix = food  # issue #49:文件名带食物名,下载多时可直接识别
            data = build_live_diet_add(food, cal, pro,
                                       carbs=pos[3] if len(pos) > 3 else kw.get('carbs', '0'),
                                       fat=pos[4] if len(pos) > 4 else kw.get('fat', '0'),
                                       grams=pos[5] if len(pos) > 5 else kw.get('grams', '100'),
                                       note=pos[6] if len(pos) > 6 else (kw.get('note') or ''),
                                       target_date=kw.get('date'), target_time=kw.get('time'),
                                       meal=kw.get('meal'))
        elif args.live_diet_batch:
            data = build_live_diet_batch(args.input)
        elif args.live_diet_batch_meal:
            if not args.input:
                print('❌ --live-diet-batch-meal 需要 --input <json>', file=sys.stderr)
                return 1
            data = build_live_diet_batch_meal(args.input)
        elif args.live_diet_copy:
            data = build_live_diet_copy(args.from_date, args.to_date)
        elif args.live_diet_update:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-update') + 1:]
            entry_id = None
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--'):
                    k = rest[i][2:]
                    if i + 1 < len(rest) and not rest[i+1].startswith('--'):
                        kw[k] = rest[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    if entry_id is None:
                        entry_id = rest[i]
                    i += 1
            if entry_id is None:
                print('❌ --live-diet-update 需要 <id>', file=sys.stderr)
                return 1
            _FMAP = {'grams': 'grams', 'food': 'food_name', 'calories': 'calories',
                     'protein': 'protein', 'carbs': 'carbs', 'fat': 'fat',
                     'date': 'date', 'time': 'time', 'note': 'note'}
            data = build_live_diet_update(entry_id, **{_FMAP[k]: v for k, v in kw.items() if k in _FMAP})
        elif args.live_diet_update_date:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-update-date') + 1:]
            target_date = None
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--'):
                    k = rest[i][2:]
                    if i + 1 < len(rest) and not rest[i+1].startswith('--'):
                        kw[k] = rest[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    if target_date is None:
                        target_date = rest[i]
                    i += 1
            if not target_date or not kw:
                print('❌ --live-diet-update-date 需要 <date> + 至少 1 个字段', file=sys.stderr)
                return 1
            _FMAP = {'grams': 'grams', 'food': 'food_name', 'calories': 'calories',
                     'protein': 'protein', 'carbs': 'carbs', 'fat': 'fat',
                     'date': 'date', 'time': 'time', 'note': 'note'}
            data = build_live_diet_update_date(target_date, **{_FMAP[k]: v for k, v in kw.items() if k in _FMAP})
        elif args.live_diet_delete:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-delete') + 1:]
            entry_id = rest[0] if rest else None
            if entry_id is None or entry_id.startswith('--'):
                print('❌ --live-diet-delete 需要 <id>', file=sys.stderr)
                return 1
            data = build_live_diet_delete(entry_id)
        elif args.live_diet_delete_meal:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-delete-meal') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if len(pos) < 2:
                print('❌ --live-diet-delete-meal 需要 <date> <餐别>', file=sys.stderr)
                return 1
            data = build_live_diet_delete_meal(pos[0], pos[1])
        elif args.live_diet_delete_date:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-delete-date') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if not pos:
                print('❌ --live-diet-delete-date 需要 <date>', file=sys.stderr)
                return 1
            data = build_live_diet_delete_date(pos[0])
        elif args.live_diet_delete_range:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-diet-delete-range') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if len(pos) < 2:
                print('❌ --live-diet-delete-range 需要 <start> <end>', file=sys.stderr)
                return 1
            data = build_live_diet_delete_range(pos[0], pos[1])
        elif args.live_water_add:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-water-add') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if not pos:
                print('❌ --live-water-add 需要 <ml>', file=sys.stderr)
                return 1
            data = build_live_water_add(pos[0], target_date=args.date)
        elif args.live_product_add:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-product-add') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if len(pos) < 11:
                print('❌ --live-product-add 需要 <name> <brand> <cal> <pro> <fat> <sat> <carb> <sugar> <fiber> <sodium> [note]',
                      file=sys.stderr)
                return 1
            data = build_live_product_add(pos[0], pos[1], float(pos[2]), float(pos[3]), float(pos[4]),
                                          float(pos[5]) or None, float(pos[6]), float(pos[7]) or None,
                                          float(pos[8]) or None, float(pos[9]),
                                          pos[10] if len(pos) > 10 else '')
        elif args.live_product_update:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-product-update') + 1:]
            pid = None
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--'):
                    k = rest[i][2:]
                    if i + 1 < len(rest) and not rest[i+1].startswith('--'):
                        kw[k] = rest[i+1]
                        i += 2
                    else:
                        i += 1
                else:
                    if pid is None:
                        pid = rest[i]
                    i += 1
            # 白名单过滤(同 --live-diet-update 的 _FMAP 模式 · #44 缺陷C):
            # --chain/--output 等框架参数不得当作「已更新字段」进入回执
            _PRODUCT_FIELDS = {'product_name', 'brand', 'calories', 'protein', 'fat',
                               'saturated_fat', 'carbohydrates', 'sugar', 'dietary_fiber',
                               'sodium', 'note', 'category'}
            kw = {k: v for k, v in kw.items() if k in _PRODUCT_FIELDS}
            if pid is None or not kw:
                print('❌ --live-product-update 需要 <id> + 至少 1 个字段', file=sys.stderr)
                return 1
            data = build_live_product_update(pid, **kw)
        elif args.live_product_deprecate:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-product-deprecate') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            if not pos:
                print('❌ --live-product-deprecate 需要 <id>', file=sys.stderr)
                return 1
            data = build_live_product_deprecate(pos[0])
        elif args.live_weight_update:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-weight-update') + 1:]
            pos = [a for a in rest if not a.startswith('--')]
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--') and i + 1 < len(rest) and not rest[i+1].startswith('--'):
                    kw[rest[i][2:]] = rest[i+1]
                    i += 2
                else:
                    i += 1
            if not pos:
                print('❌ --live-weight-update 需要 <id> 或 <date>', file=sys.stderr)
                return 1
            target = pos[0]
            try:
                w_id = int(target)
                data = build_live_weight_update(target_id=w_id, weight_kg=kw.get('weight'),
                                                note=kw.get('note'))
            except ValueError:
                data = build_live_weight_update(target_date=target, weight_kg=kw.get('weight'),
                                                note=kw.get('note'))
        elif args.live_weight_delete:
            import sys as _sys
            rest = _sys.argv[_sys.argv.index('--live-weight-delete') + 1:]
            pos = []
            kw = {}
            i = 0
            while i < len(rest):
                if rest[i].startswith('--'):
                    if i + 1 < len(rest) and not rest[i + 1].startswith('--'):
                        kw[rest[i][2:]] = rest[i + 1]
                        i += 2
                    else:
                        i += 1
                else:
                    pos.append(rest[i])
                    i += 1
            # 2026-08-09 #43 验收修复:原逻辑跳过 flag 值,data_source 的
            # --id/--date/--start+--end 写法全部不可复现(第 4 层链路断)
            # → 支持 flag 形式 + 兼容裸位置参数
            # R5 场景名按删除方式区分(2026-08-09 #43):区间=批量删体重 / 日期=删某日体重 / id=删体重记录
            if 'id' in kw:
                data = build_live_weight_delete(target_id=int(kw['id']))
                cmd_name = '删体重记录'
            elif 'date' in kw:
                data = build_live_weight_delete(target_date=kw['date'])
                cmd_name = '删某日体重'
            elif 'start' in kw and 'end' in kw:
                data = build_live_weight_delete(start=kw['start'], end=kw['end'])
                cmd_name = '批量删体重'
            elif pos:
                if len(pos) >= 2:
                    data = build_live_weight_delete(start=pos[0], end=pos[1])
                    cmd_name = '批量删体重'
                else:
                    target = pos[0]
                    try:
                        data = build_live_weight_delete(target_id=int(target))
                    except ValueError:
                        data = build_live_weight_delete(target_date=target)
            else:
                print('❌ --live-weight-delete 需要 <id|date|start end>', file=sys.stderr)
                return 1
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
            data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
            src = 'food_log (写库回执)' if active.startswith(('live_diet', 'live_water')) else (
                  'nutrition_products (写库回执)' if active.startswith('live_product') else (
                  'weight_log (写库回执)' if active.startswith('live_weight') else 'user_profile (写库回执)'))
            data['data']['meta']['source'] = src
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else (
        html_scene_path(SKILL_DIR, cmd_name, ot, suffix=file_suffix) if ot else html_path(SKILL_DIR, cmd_name, suffix=file_suffix))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   操作: {d["op"]} | #{d["record_id"]} | {d["meta"]["entity_type"]}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
