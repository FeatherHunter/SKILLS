#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_plan_receipt.py — 健身计划写类场景回执渲染器(2026-08-02 · ticket #6)

对应 SKILL.md 唤醒词:定训练计划 / 复制训练计划 / 定休息日 / 加训练动作 / 定一周计划 / 改训练计划 / 改某天训练 / 删某天训练 / 改动作 / 撤销训练计划 / 同步到训记 / 拉训记实绩

设计(对齐 #8 经验 R1-R8):
- R3 思考链强制:live 模式 --chain 必传 + 有效性校验
- R5 命名:html_scene_path(场景名, 类型中文)统一入口
- R6 呈现数据完整性:diff 中文标签 + 改前/改后 + 1 句话 summary 在回执顶部
- R1 视图分离:meta 进复制日志不进 UI
- R2 传输层:复制数据 / 复制日志双按钮(模板自带)
- R8 移动端优先:回执模板已适配 375px

用法:
    python scripts/render_plan_receipt.py --live-plan-set --plan-json <JSON> --chain "..."
    python scripts/render_plan_receipt.py --live-plan-copy [--new-title X]
    python scripts/render_plan_receipt.py --live-plan-rest --week 1 --day 3 [--rest 1|0]
    python scripts/render_plan_receipt.py --live-plan-add --week 1 --day 3 --name 深蹲 --sets 4
    python scripts/render_plan_receipt.py --live-plan-set-week --week 1 --days-json "..."
    python scripts/render_plan_receipt.py --live-plan-update --field title --value 新标题
    python scripts/render_plan_receipt.py --live-plan-update-day --week 1 --day 3 --session 1 --label 新时段
    python scripts/render_plan_receipt.py --live-plan-delete-day --week 1 --day 3
    python scripts/render_plan_receipt.py --live-plan-update-movement --week 1 --day 3 --session 1 --old-name A --new-name B
    python scripts/render_plan_receipt.py --live-plan-delete
    python scripts/render_plan_receipt.py --live-plan-sync --date D --results-json "..."
    python scripts/render_plan_receipt.py --live-plan-backfill --date D --results-json "..."
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa: E402
from render_goal_common import chain_valid  # noqa: E402

# 场景名(输出命名 + R4 自描述)
SCENE = {
    'plan_set': '定训练计划', 'plan_copy': '复制训练计划', 'plan_rest': '定休息日',
    'plan_add': '加训练动作', 'plan_set_week': '定一周计划',
    'plan_update': '改训练计划', 'plan_update_day': '改某天训练',
    'plan_delete_day': '删某天训练', 'plan_update_movement': '改动作',
    'plan_delete': '撤销训练计划', 'plan_sync': '同步到训记', 'plan_backfill': '拉训记实绩',
}

_FIELD_LABELS = {
    'title': '标题', 'total_weeks': '总周数', 'start_date': '开始日期',
    'description': '描述', 'version': '版本',
    'session_label': '时段名', 'time_start': '开始时间', 'time_end': '结束时间',
    'total_sets': '总组数', 'is_rest_day': '休息日',
    'name': '动作名', 'sets': '组数', 'weight': '重量',
}


def _label(key):
    return _FIELD_LABELS.get(key, key)


def _disp_val(key, val):
    if key == 'is_rest_day':
        return '休息' if val else '训练'
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    return val


def _receipt(op, entity, old, new, diff, summary, chain, source, action_at=None):
    """组装回执数据契约(与 crud_receipt.html 同构)"""
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': None,
            'entity_type': entity,
            'old_record': old or {},
            'new_record': new or {},
            'diff': diff,
            'context': {'kpis': []},
            'meta': {
                'action_at': action_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': entity,
                'source': source,
                'chain': chain,
                'wake_word': entity,
            },
            'summary': summary,
        },
        'message': f'已生成{entity} 回执',
    }


def _build_diff(items):
    """items: [{label, unit, old, new}] → diff 结构"""
    return {'items': items}


def _read_config(conn):
    c = conn.cursor()
    c.execute('SELECT title, version, description, total_weeks, start_date FROM workout_plan_config WHERE id=1')
    row = c.fetchone()
    if not row:
        return None
    return {'title': row[0], 'version': row[1], 'description': row[2],
            'total_weeks': row[3], 'start_date': row[4]}


def _get_config_snapshot(plan_generator_mod):
    """读当前 config 快照(连接即开即关,防锁)"""
    db = plan_generator_mod._get_db()
    try:
        return _read_config(db)
    finally:
        db.close()


# ═══════════════════ build_live_* 系列 ═══════════════════

def build_live_plan_set(chain, plan_json, title=None, total_weeks=None, start_date=None):
    """定训练计划:写 config + weeks(单计划模型:覆盖旧计划)+ 回执

    plan_json: AI 采访后生成的完整计划 JSON({config, weeks}),预览已走
    render_plan_builder.py --mock;本函数只做写库 + 回执。
    """
    import plan_generator
    old = _get_config_snapshot(plan_generator)
    plan = json.loads(plan_json) if isinstance(plan_json, str) else plan_json
    if title or total_weeks or start_date:
        plan.setdefault('config', {}).update({
            'title': title or plan.get('config', {}).get('title', ''),
            'total_weeks': total_weeks or plan.get('config', {}).get('total_weeks', 0),
            'start_date': start_date or plan.get('config', {}).get('start_date', ''),
        })
    res = plan_generator.write_plan(plan)
    if res.get('errors'):
        raise ValueError('计划校验失败: ' + '; '.join(res['errors']))
    new = _get_config_snapshot(plan_generator)
    diff = _build_diff([
        {'label': '标题', 'unit': '', 'old': old['title'] if old else None, 'new': new['title']},
        {'label': '总周数', 'unit': '周', 'old': old['total_weeks'] if old else None, 'new': new['total_weeks']},
        {'label': '开始日期', 'unit': '', 'old': old['start_date'] if old else None, 'new': new['start_date']},
    ])
    summary = f"训练计划已设置:标题「{new['title']}」/ {new['total_weeks']} 周循环 / 起始 {new['start_date']} / 共 {res['inserted_count']} 条训练数据"
    return _receipt('create', '定训练计划', old, new, diff, summary, chain,
                    'workout_plan_config + workout_plans')


def build_live_plan_copy(chain, new_title=None):
    """复制训练计划:copy_plan(单计划模型:另存为新标题)+ 回执"""
    import plan_generator
    old = _get_config_snapshot(plan_generator)
    if old is None:
        raise ValueError('尚未制定训练计划,无法复制')
    res = plan_generator.copy_plan(new_title=new_title)
    new = _get_config_snapshot(plan_generator)
    diff = _build_diff([
        {'label': '标题', 'unit': '', 'old': old['title'], 'new': new['title']},
        {'label': '复制条数', 'unit': '行', 'old': None, 'new': res['copied_rows']},
    ])
    summary = f"计划已复制为新标题「{new['title']}」,共 {res['copied_rows']} 行训练数据"
    return _receipt('create', '复制训练计划', old, new, diff, summary, chain,
                    'workout_plan_config + workout_plans')


def build_live_plan_rest(chain, week, day, rest):
    """定休息日:标记某天休息/取消(该天全部 session 标记)+ 回执"""
    import plan_generator
    db = plan_generator._get_db()
    try:
        c = db.cursor()
        c.execute('SELECT session_index, session_label FROM workout_plans WHERE week_number=? AND day_of_week=?', (week, day))
        rows = c.fetchall()
        if not rows:
            raise ValueError(f'第 {week} 周 周{day} 没有训练数据')
        before = [{'session_index': r[0], 'session_label': r[1]} for r in rows]
        for r in rows:
            plan_generator.update_session(week, day, r[0], is_rest_day=1 if rest else 0)
        after = [{'session_index': r[0], 'session_label': r[1], 'is_rest_day': 1 if rest else 0} for r in rows]
    finally:
        db.close()
    diff = _build_diff([{'label': f'周{day} 共{len(rows)}时段', 'unit': '',
                         'old': '训练' if not rest else '休息', 'new': '休息' if rest else '训练'}])
    summary = f"周{day} 已{'标记为休息日' if rest else '取消休息(恢复训练)'},涉及 {len(rows)} 个时段"
    return _receipt('update', '定休息日', before, after, diff, summary, chain,
                    'workout_plans(week=%d day=%d)' % (week, day))


def build_live_plan_add(chain, week, day, name, sets, weight=None, session=None):
    """加训练动作:给某天某时段加动作 + 回执"""
    import plan_generator
    db = plan_generator._get_db()
    try:
        c = db.cursor()
        if session is not None:
            c.execute('SELECT movements FROM workout_plans WHERE week_number=? AND day_of_week=? AND session_index=?', (week, day, session))
        else:
            c.execute('SELECT session_index, movements FROM workout_plans WHERE week_number=? AND day_of_week=? ORDER BY session_index LIMIT 1', (week, day))
        row = c.fetchone()
        if not row:
            raise ValueError(f'第 {week} 周 周{day} 没有训练时段,请先创建时段')
        si = row[0] if session is None else session
        movements = json.loads(row[1]) if row[1] else []
    finally:
        db.close()
    new_mv = {'name': name, 'part': '?', 'sets': [{'reps': 10, 'weight': weight or 0}]}
    movements.append(new_mv)
    plan_generator.update_session(week, day, si, movements=movements, total_sets=len(movements))
    diff = _build_diff([{'label': '新增动作', 'unit': '', 'old': None, 'new': f'{name} × {sets} 组'}])
    summary = f"已加动作「{name}」{sets} 组{' × ' + str(weight) + 'kg' if weight else ''} 到第{week}周周{day}"
    return _receipt('create', '加训练动作', None, new_mv, diff, summary, chain,
                    'workout_plans(week=%d day=%d session=%d)' % (week, day, si))


def build_live_plan_set_week(chain, week, days_json):
    """定一周计划:一次设置 7 天(JSON: {day_of_week: [sessions]})"""
    import plan_generator
    days = json.loads(days_json) if isinstance(days_json, str) else days_json
    db0 = plan_generator._get_db()
    try:
        db0.execute('DELETE FROM workout_plans WHERE week_number=?', (week,))
        db0.commit()
    finally:
        db0.close()
    inserted = 0
    for dow, sessions in days.items():
        for sess in sessions:
            plan_generator.add_session({
                'week_number': week, 'day_of_week': int(dow),
                'session_label': sess.get('label', '训练'),
                'time_start': sess.get('time_start'), 'time_end': sess.get('time_end'),
                'is_rest_day': sess.get('rest', False),
                'total_sets': sess.get('total_sets', 0),
                'movements': sess.get('movements', []),
            })
            inserted += 1
    diff = _build_diff([{'label': '周次', 'unit': '', 'old': None, 'new': f'第 {week} 周'}])
    summary = f"第 {week} 周计划已写入:共 {inserted} 个训练时段"
    return _receipt('create', '定一周计划', None, {'week': week, 'sessions': inserted},
                    diff, summary, chain, 'workout_plans(week=%d)' % week)


def build_live_plan_update(chain, fields, values):
    """改训练计划:改 config 字段(可多对)+ 回执(改前/改后 + 影响)"""
    import plan_generator
    old = _get_config_snapshot(plan_generator)
    if old is None:
        raise ValueError('尚未制定训练计划')
    updates = {k: v for k, v in zip(fields, values)}
    plan_generator.update_config(**updates)
    new = _get_config_snapshot(plan_generator)
    diff_items = []
    for k, v in updates.items():
        diff_items.append({'label': _label(k), 'unit': '',
                           'old': _disp_val(k, old.get(k)), 'new': _disp_val(k, new.get(k))})
    summary_parts = [f"{_label(k)}:{old.get(k)}→{new.get(k)}" for k in updates]
    if 'start_date' in updates:
        summary_parts.append('提示:改开始日期会影响周次计算')
    summary = ';'.join(summary_parts)
    return _receipt('update', '改训练计划', old, new, _build_diff(diff_items), summary, chain,
                    'workout_plan_config')


def build_live_plan_update_day(chain, week, day, session, label=None, time_start=None,
                               time_end=None, total_sets=None):
    """改某天训练:改某时段字段 + 回执"""
    import plan_generator
    db = plan_generator._get_db()
    try:
        c = db.cursor()
        c.execute('SELECT session_label, time_start, time_end, total_sets FROM workout_plans '
                  'WHERE week_number=? AND day_of_week=? AND session_index=?', (week, day, session))
        row = c.fetchone()
        if not row:
            raise ValueError(f'第 {week} 周 周{day} 时段 {session} 不存在')
        before = {'session_label': row[0], 'time_start': row[1], 'time_end': row[2], 'total_sets': row[3]}
    finally:
        db.close()
    kw = {}
    if label: kw['session_label'] = label
    if time_start: kw['time_start'] = time_start
    if time_end: kw['time_end'] = time_end
    if total_sets is not None: kw['total_sets'] = total_sets
    plan_generator.update_session(week, day, session, **kw)
    after = {**before, **kw}
    diff_items = [{'label': _label(k), 'unit': '', 'old': before.get(k), 'new': after.get(k)} for k in kw]
    summary = f"周{day} 时段 {session} 已更新:{';'.join(f'{_label(k)}→{v}' for k, v in kw.items())}"
    return _receipt('update', '改某天训练', before, after, _build_diff(diff_items), summary, chain,
                    'workout_plans(week=%d day=%d session=%d)' % (week, day, session))


def build_live_plan_delete_day(chain, week, day):
    """删某天训练:删整天(快照 → 确认 → 回执)"""
    import plan_generator
    result = plan_generator.delete_day(week, day)
    if result['deleted_sessions'] == 0:
        raise ValueError(f'第 {week} 周 周{day} 没有训练数据')
    diff = _build_diff([{'label': f'周{day} 时段', 'unit': '个', 'old': result['deleted_sessions'], 'new': 0}])
    summary = f"已删除第 {week} 周 周{day} 的全部 {result['deleted_sessions']} 个训练时段"
    return _receipt('delete', '删某天训练', result['snapshot'], None, diff, summary, chain,
                    'workout_plans(week=%d day=%d)' % (week, day))


def build_live_plan_update_movement(chain, week, day, session, old_name, new_name, sets=None):
    """改动作:替换动作/改组数 + 回执"""
    import plan_generator
    db = plan_generator._get_db()
    try:
        c = db.cursor()
        c.execute('SELECT movements FROM workout_plans WHERE week_number=? AND day_of_week=? AND session_index=?', (week, day, session))
        row = c.fetchone()
        if not row:
            raise ValueError(f'第 {week} 周 周{day} 时段 {session} 不存在')
        movements = json.loads(row[0]) if row[0] else []
    finally:
        db.close()
    hit = False
    for m in movements:
        if m.get('name') == old_name:
            m['name'] = new_name
            if sets is not None:
                m['sets'] = [{'reps': 10, 'weight': 0}] * sets
            hit = True
            break
    if not hit:
        raise ValueError(f'动作「{old_name}」不在该时段中')
    plan_generator.update_session(week, day, session, movements=movements, total_sets=len(movements))
    diff = _build_diff([{'label': '动作', 'unit': '', 'old': old_name, 'new': new_name},
                        {'label': '组数', 'unit': '组', 'old': None, 'new': sets}])
    summary = f"动作已替换:{old_name} → {new_name}{' × ' + str(sets) + ' 组' if sets else ''}"
    return _receipt('update', '改动作', {'name': old_name}, {'name': new_name}, diff, summary, chain,
                    'workout_plans(week=%d day=%d session=%d)' % (week, day, session))


def build_live_plan_delete(chain):
    """撤销训练计划:删整个计划 + 回执"""
    import plan_generator
    result = plan_generator.delete_plan()
    if result['deleted_rows'] == 0 and result['deleted_config'] is None:
        raise ValueError('尚未制定训练计划')
    diff = _build_diff([{'label': '计划', 'unit': '', 'old': result['deleted_config']['title'] if result['deleted_config'] else '—',
                         'new': '(已删除)'},
                        {'label': '删除数据', 'unit': '行', 'old': result['deleted_rows'], 'new': 0}])
    summary = f"训练计划「{result['deleted_config']['title'] if result['deleted_config'] else '—'}」已撤销,删除 {result['deleted_rows']} 行训练数据;可用「定训练计划」重新制定"
    return _receipt('delete', '撤销训练计划', result['deleted_config'], None, diff, summary, chain,
                    'workout_plan_config + workout_plans')


def build_live_plan_sync(chain, date_str, results_json=None):
    """同步到训记:Step 3 单做(审计动作名前置由 AI 完成)+ 回执"""
    results = json.loads(results_json) if results_json else {'date': date_str, 'pushed': 0, 'results': []}
    diff = _build_diff([{'label': '推送日期', 'unit': '', 'old': None, 'new': date_str},
                        {'label': '推送条数', 'unit': '条', 'old': None, 'new': results.get('pushed', 0)}])
    summary = f"已推送到训记:{results.get('pushed', 0)} 条训练(日期 {date_str})"
    return _receipt('create', '同步到训记', None, results, diff, summary, chain,
                    'xunji_bridge.push-plan')


def build_live_plan_backfill(chain, date_str, results_json=None):
    """拉训记实绩:Step 4 单做 + 回执"""
    results = json.loads(results_json) if results_json else {'date': date_str, 'inserted': 0, 'updated': 0}
    diff = _build_diff([{'label': '回写日期', 'unit': '', 'old': None, 'new': date_str},
                        {'label': '新增', 'unit': '条', 'old': None, 'new': results.get('inserted', 0)},
                        {'label': '更新', 'unit': '条', 'old': None, 'new': results.get('updated', 0)}])
    summary = f"训记实绩已回写:新增 {results.get('inserted', 0)} 条,更新 {results.get('updated', 0)} 条(日期 {date_str})"
    return _receipt('create', '拉训记实绩', None, results, diff, summary, chain,
                    'xunji_bridge.backfill')


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='健身计划写类场景回执渲染器(ticket #6)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--live-plan-set', action='store_true')
    g.add_argument('--live-plan-copy', action='store_true')
    g.add_argument('--live-plan-rest', action='store_true')
    g.add_argument('--live-plan-add', action='store_true')
    g.add_argument('--live-plan-set-week', action='store_true')
    g.add_argument('--live-plan-update', action='store_true')
    g.add_argument('--live-plan-update-day', action='store_true')
    g.add_argument('--live-plan-delete-day', action='store_true')
    g.add_argument('--live-plan-update-movement', action='store_true')
    g.add_argument('--live-plan-delete', action='store_true')
    g.add_argument('--live-plan-sync', action='store_true')
    g.add_argument('--live-plan-backfill', action='store_true')
    p.add_argument('--title')
    p.add_argument('--plan-json', help='定训练计划:完整计划 JSON({config, weeks},AI 采访输出)')
    p.add_argument('--total-weeks', type=int)
    p.add_argument('--start-date')
    p.add_argument('--new-title')
    p.add_argument('--week', type=int)
    p.add_argument('--day', type=int)
    p.add_argument('--rest', type=int, default=1)
    p.add_argument('--session', type=int)
    p.add_argument('--name')
    p.add_argument('--sets', type=int)
    p.add_argument('--weight', type=float)
    p.add_argument('--days-json')
    p.add_argument('--field', action='append')
    p.add_argument('--value', action='append')
    p.add_argument('--label')
    p.add_argument('--time-start')
    p.add_argument('--time-end')
    p.add_argument('--total-sets', type=int)
    p.add_argument('--old-name')
    p.add_argument('--new-name')
    p.add_argument('--date')
    p.add_argument('--results-json')
    p.add_argument('--chain', required=True, help='AI 思考链(强制)')
    p.add_argument('--output')
    args = p.parse_args()

    if not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        return 2

    builders = {
        'plan_set': lambda: build_live_plan_set(args.chain, args.plan_json, args.title, args.total_weeks, args.start_date),
        'plan_copy': lambda: build_live_plan_copy(args.chain, args.new_title),
        'plan_rest': lambda: build_live_plan_rest(args.chain, args.week, args.day, args.rest),
        'plan_add': lambda: build_live_plan_add(args.chain, args.week, args.day, args.name, args.sets, args.weight, args.session),
        'plan_set_week': lambda: build_live_plan_set_week(args.chain, args.week, args.days_json),
        'plan_update': lambda: build_live_plan_update(args.chain, args.field or [], args.value or []),
        'plan_update_day': lambda: build_live_plan_update_day(args.chain, args.week, args.day, args.session, args.label, args.time_start, args.time_end, args.total_sets),
        'plan_delete_day': lambda: build_live_plan_delete_day(args.chain, args.week, args.day),
        'plan_update_movement': lambda: build_live_plan_update_movement(args.chain, args.week, args.day, args.session, args.old_name, args.new_name, args.sets),
        'plan_delete': lambda: build_live_plan_delete(args.chain),
        'plan_sync': lambda: build_live_plan_sync(args.chain, args.date, args.results_json),
        'plan_backfill': lambda: build_live_plan_backfill(args.chain, args.date, args.results_json),
    }
    live_map = {
        '--live-plan-set': 'plan_set', '--live-plan-copy': 'plan_copy',
        '--live-plan-rest': 'plan_rest', '--live-plan-add': 'plan_add',
        '--live-plan-set-week': 'plan_set_week', '--live-plan-update': 'plan_update',
        '--live-plan-update-day': 'plan_update_day', '--live-plan-delete-day': 'plan_delete_day',
        '--live-plan-update-movement': 'plan_update_movement', '--live-plan-delete': 'plan_delete',
        '--live-plan-sync': 'plan_sync', '--live-plan-backfill': 'plan_backfill',
    }
    key = next((k for flag, k in live_map.items() if getattr(args, flag)), None)
    if key is None:
        print('❌ 未识别 live 模式', file=sys.stderr)
        return 1

    try:
        data = builders[key]()
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    scene_name = SCENE[key]
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene_name, 'receipt')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    s = data['data'].get('summary', '')
    print(f'✅ {out_path}')
    print(f'   {s}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
