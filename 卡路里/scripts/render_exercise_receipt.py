#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_receipt.py — 运动写操作回执 HTML 渲染器(回执型 · 13 场景一体)

对应 SKILL.md 唤醒词(13 个):
  - 记运动 / 记运动（含备注）/ 记有氧运动 → --live-add
  - 记力量训练                            → --live-add-strength(每组一行)
  - 记日常活动                            → --live-add-daily(步数/时段)
  - 补记运动                              → --live-backfill(补录标识 + 冲突提示)
  - 批量补记运动                          → --live-batch-add(写入/跳过/失败)
  - 复制昨日运动                          → --live-copy(复制条数/跳过条数)
  - 改运动记录                            → --live-update(改前/改后)
  - 改某日运动                            → --live-update-day(命中条数/改前/改后)
  - 删运动记录                            → --live-delete(软删除 + 快照)
  - 删某日运动                            → --live-delete-day(删除条数)
  - 批量删运动                            → --live-delete-range(范围/删除条数)
对应模板: templates/crud_receipt.html

2026-08-02 · ticket #5 运动 · R3 思考链强制(--chain 必传)+ R5 命名(<场景名>_回执_TS.html)
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
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
import exercise_tracker as et  # noqa


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


# 回执展示字段白名单(隐藏内部列:created_at/updated_at/xunji_*/is_deleted)
_SKIP_KEYS = {'id', 'created_at', 'updated_at', 'is_deleted', 'xunji_localid', 'xunji_title',
              'intensity', 'period'}


def _disp(record: dict) -> dict:
    """记录 → 回执展示字段(去内部列 + None 过滤)"""
    return {k: v for k, v in record.items()
            if k not in _SKIP_KEYS and v is not None and v != ''}


def _receipt(op: str, record_id, old_record: dict, new_record: dict,
             entity_label: str, summary: str, action_at: str | None = None) -> dict:
    return {
        'status': 'ok',
        'data': {
            'op': op,
            'record_id': record_id,
            'old_record': old_record or {},
            'new_record': new_record or {},
            'context': {'kpis': []},
            'meta': {
                'action_at': action_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'entity_type': entity_label,
            },
            'summary': summary,
        },
        'message': f'已生成{entity_label} 回执',
    }


def _fmt_strength(total_sets, load_kg, reps):
    return f"{total_sets} 组 × {load_kg}kg × {reps} 次"


def build_live_add(date, etype, calories, minutes=None, time_str=None, note='',
                   category=None, distance=None, heart_rate=None, max_heart_rate=None,
                   steps=None, period=None, reps=None, set_index=None, load_kg=None,
                   is_backfill=False):
    """记运动 / 记运动（含备注）/ 记有氧运动 / 补记运动(冲突提示)"""
    conflict_note = ''
    if is_backfill and etype:
        conn = et.get_db()
        cnt = conn.execute(
            "SELECT COUNT(*) FROM exercise_log WHERE date = ? AND exercise_type = ? "
            "AND COALESCE(is_deleted, 0) = 0", (date, etype)).fetchone()[0]
        conn.close()
        if cnt:
            conflict_note = f";补录冲突提示:该日期已有同类型记录 {cnt} 条,请先向用户确认"
    rid, rec = et.add_record(date, etype, calories, minutes=minutes, time_str=time_str,
                             note=note or '', category=category, distance=distance,
                             heart_rate=heart_rate, max_heart_rate=max_heart_rate,
                             steps=steps, period=period, reps=reps,
                             set_index=set_index, load_kg=load_kg, is_backfill=is_backfill)
    parts = [f"{rec['exercise_type']} {rec['calories_burned']} 卡"]
    if rec.get('duration_minutes'):
        parts.append(f"{rec['duration_minutes']} 分钟")
    if rec.get('distance_km'):
        parts.append(f"{rec['distance_km']}km")
    if rec.get('avg_heart_rate'):
        parts.append(f"平均心率 {rec['avg_heart_rate']}")
    if rec.get('max_heart_rate'):
        parts.append(f"最高心率 {rec['max_heart_rate']}")
    if rec.get('steps'):
        parts.append(f"{rec['steps']} 步")
    if rec.get('note'):
        parts.append(f"备注:{rec['note']}")
    label = '补记运动' if is_backfill else '记运动'
    summary = f"已记录:{'、'.join(parts)}{' · 补录' if is_backfill else ''}{conflict_note}"
    return _receipt('add', rid, {}, _disp(rec), label, summary, rec['time'] and f"{date} {rec['time']}")


def build_live_add_strength(date, etype, sets, load_kg, reps, note=''):
    """记力量训练:每组一行写入 + N 组 × kg × reps 汇总"""
    conn = et.get_db()
    ids = []
    for s in range(1, sets + 1):
        rid, _ = et.add_record(date, etype, 0, minutes=None, note=note or '',
                               category='力量', set_index=s, load_kg=load_kg, reps=reps, conn=conn)
        ids.append(rid)
    conn.commit()
    conn.close()
    summary = f"已记录 {etype}:{_fmt_strength(sets, load_kg, reps)}"
    new = {'exercise_type': etype, 'date': date, 'set_index': f'1~{sets}',
           'load_kg': load_kg, 'reps': reps, 'note': note or ''}
    return _receipt('add', ids[0], {}, _disp(new), '记力量训练', summary,
                    f"{date} {datetime.now().strftime('%H:%M:%S')}")


def build_live_add_daily(date, etype, minutes, steps=None, period=None, calories=None):
    """记日常活动:步数/时段/消耗"""
    rid, rec = et.add_record(date, etype, calories or 0, minutes=minutes,
                             category='日常', steps=steps, period=period)
    parts = [f"{rec['exercise_type']} {rec['duration_minutes']} 分钟"]
    if rec.get('steps'):
        parts.append(f"{rec['steps']} 步")
    if rec.get('period'):
        parts.append(f"{rec['period']}")
    if rec.get('calories_burned'):
        parts.append(f"{rec['calories_burned']} 卡")
    return _receipt('add', rid, {}, _disp(rec), '记日常活动', f"已记录:{'、'.join(parts)}",
                    f"{date} {rec['time']}")


def build_live_batch_add(items):
    """批量补记运动:写入/跳过/失败统计"""
    result = et.batch_add(items)
    summary = (f"批量补记完成:写入 {result['written']} 条 / 跳过 {result['skipped']} 条 / "
               f"失败 {result['failed']} 条")
    new = {'written': result['written'], 'skipped': result['skipped'],
           'failed': result['failed'],
           'failures': '\n'.join(f"{f['item'].get('date')} {f['item'].get('type')}: {f['reason']}"
                                 for f in result['failures']) or None}
    return _receipt('add', f"{result['written']} 条", {}, _disp(new), '批量补记运动', summary)


def build_live_copy(target):
    """复制昨日运动:复制条数/跳过条数"""
    copied, skipped, details, source, target = et.copy_yesterday(target)
    summary = f"已复制昨日运动 {source} → {target}:复制 {copied} 条 / 跳过 {skipped} 条"
    new = {'source_date': source, 'target_date': target,
           'copied': copied, 'skipped': skipped}
    return _receipt('add', f"{copied} 条", {}, _disp(new), '复制昨日运动', summary)


def build_live_update(record_id, field_value_pairs):
    """改运动记录:改前/改后 diff"""
    fields = {f: v for f, v in field_value_pairs}
    old, new = et.update_record(record_id, fields)
    changed = [k for k in new if k not in _SKIP_KEYS and old.get(k) != new.get(k)]
    summary = f"已修改 {len(changed)} 项:" + '、'.join(
        f"{k} {old.get(k)}→{new.get(k)}" for k in changed[:8]) or '无字段变化'
    return _receipt('update', record_id, _disp(old), _disp(new), '改运动记录', summary)


def build_live_update_day(date, field_value_pairs):
    """改某日运动:命中条数 + 改前/改后"""
    fields = {f: v for f, v in field_value_pairs}
    matched, results = et.update_day(date, fields)
    summary = f"已更新 {matched} 条记录(日期 {date})"
    return _receipt('update', f"{matched} 条", {}, {'matched': matched, 'date': date},
                    '改某日运动', summary)


def build_live_delete(record_id):
    """删运动记录:软删除 + 快照"""
    snapshot = et.delete_record(record_id)
    summary = f"已删除 #{record_id}:{snapshot['exercise_type']} {snapshot['calories_burned']} 卡"
    return _receipt('delete', record_id, _disp(snapshot), {}, '删运动记录', summary)


def build_live_delete_day(date):
    """删某日运动:删除条数/日期"""
    count = et.delete_day(date)
    summary = f"已删除 {date} 的运动记录 {count} 条"
    return _receipt('delete', f"{count} 条", {}, {'date': date, 'deleted_count': count},
                    '删某日运动', summary)


def build_live_delete_range(from_date, to_date):
    """批量删运动:时间范围/删除条数"""
    count = et.delete_range(from_date, to_date)
    summary = f"已删除 {from_date} ~ {to_date} 的运动记录 {count} 条"
    return _receipt('delete', f"{count} 条", {},
                    {'start_date': from_date, 'end_date': to_date, 'deleted_count': count},
                    '批量删运动', summary)


def _scene_name_for(mode: str) -> str:
    return {
        'add': '记运动', 'add_strength': '记力量训练', 'add_daily': '记日常活动',
        'backfill': '补记运动', 'batch_add': '批量补记运动', 'copy': '复制昨日运动',
        'update': '改运动记录', 'update_day': '改某日运动',
        'delete': '删运动记录', 'delete_day': '删某日运动', 'delete_range': '批量删运动',
    }[mode]


def main():
    p = argparse.ArgumentParser(description='渲染运动写操作回执 HTML(13 场景一体)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--live-add', action='store_true', help='记运动(含备注/有氧)')
    g.add_argument('--live-add-strength', action='store_true', help='记力量训练(每组一行)')
    g.add_argument('--live-add-daily', action='store_true', help='记日常活动')
    g.add_argument('--live-backfill', action='store_true', help='补记运动')
    g.add_argument('--live-batch-add', action='store_true', help='批量补记运动')
    g.add_argument('--live-copy', action='store_true', help='复制昨日运动')
    g.add_argument('--live-update', action='store_true', help='改运动记录')
    g.add_argument('--live-update-day', action='store_true', help='改某日运动')
    g.add_argument('--live-delete', action='store_true', help='删运动记录')
    g.add_argument('--live-delete-day', action='store_true', help='删某日运动')
    g.add_argument('--live-delete-range', action='store_true', help='批量删运动')
    p.add_argument('--date', help='日期 (YYYY-MM-DD)')
    p.add_argument('--type', help='运动类型')
    p.add_argument('--calories', type=int, help='消耗卡路里')
    p.add_argument('--minutes', type=int, help='时长(分钟)')
    p.add_argument('--time', help='时间 (HH:MM)')
    p.add_argument('--note', help='备注')
    p.add_argument('--category', choices=['有氧', '力量', '柔韧', '日常'], help='分类')
    p.add_argument('--distance', type=float, help='距离 km')
    p.add_argument('--avg-hr', type=int, dest='avg_hr', help='平均心率')
    p.add_argument('--max-hr', type=int, dest='max_hr', help='最高心率')
    p.add_argument('--steps', type=int, help='步数')
    p.add_argument('--period', help='时段(上午/下午/晚上)')
    p.add_argument('--reps', type=int, help='次数')
    p.add_argument('--sets', type=int, help='力量:组数')
    p.add_argument('--load', type=float, help='力量:单侧重量 kg')
    p.add_argument('--id', type=int, help='记录 ID')
    p.add_argument('--items', help='批量条目(分号分隔:日期 类型 热量 [时长])')
    p.add_argument('--target', help='复制目标日期(默认今天)')
    p.add_argument('--from', dest='from_date', help='开始日期')
    p.add_argument('--to', dest='to_date', help='结束日期')
    p.add_argument('--field', action='append', help='改:字段名(可多次)')
    p.add_argument('--value', action='append', help='改:新值(与 --field 成对)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    # ⭐ 思考链强制校验(R3 · 同 render_crud_receipt)
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.解析用户意图→2.调用CLI写库→3.生成回执"', file=sys.stderr)
        return 2

    # 模式 → 场景名 + 构建函数
    mode = None
    for m in ('add', 'add_strength', 'add_daily', 'backfill', 'batch_add', 'copy',
              'update', 'update_day', 'delete', 'delete_day', 'delete_range'):
        if getattr(args, f'live_{m}'):
            mode = m
            break
    scene = _scene_name_for(mode)

    try:
        if mode == 'add':
            data = build_live_add(args.date or datetime.now().strftime('%Y-%m-%d'),
                                  args.type or '', args.calories or 0, minutes=args.minutes,
                                  time_str=args.time, note=args.note, category=args.category,
                                  distance=args.distance, heart_rate=args.avg_hr,
                                  max_heart_rate=args.max_hr, steps=args.steps,
                                  period=args.period, reps=args.reps, load_kg=args.load)
        elif mode == 'add_strength':
            if not (args.type and args.sets and args.load is not None and args.reps):
                print('❌ --live-add-strength 需要 --type/--sets/--load/--reps', file=sys.stderr)
                return 1
            data = build_live_add_strength(args.date or datetime.now().strftime('%Y-%m-%d'),
                                           args.type, args.sets, args.load, args.reps,
                                           note=args.note)
        elif mode == 'add_daily':
            data = build_live_add_daily(args.date or datetime.now().strftime('%Y-%m-%d'),
                                        args.type or '', args.minutes or 0,
                                        steps=args.steps, period=args.period,
                                        calories=args.calories)
        elif mode == 'backfill':
            data = build_live_add(args.date or '', args.type or '', args.calories or 0,
                                  minutes=args.minutes, note=args.note,
                                  category=args.category, is_backfill=True)
        elif mode == 'batch_add':
            items = []
            for line in (args.items or '').split(';'):
                parts = line.strip().split()
                if len(parts) >= 3:
                    items.append({'date': parts[0], 'type': parts[1],
                                  'calories': int(parts[2]),
                                  'minutes': int(parts[3]) if len(parts) > 3 else None})
            data = build_live_batch_add(items)
        elif mode == 'copy':
            data = build_live_copy(args.target)
        elif mode == 'update':
            if not args.id:
                print('❌ --live-update 需要 --id', file=sys.stderr)
                return 1
            data = build_live_update(args.id, list(zip(args.field or [], args.value or [])))
        elif mode == 'update_day':
            data = build_live_update_day(args.date or '', list(zip(args.field or [], args.value or [])))
        elif mode == 'delete':
            if not args.id:
                print('❌ --live-delete 需要 --id', file=sys.stderr)
                return 1
            data = build_live_delete(args.id)
        elif mode == 'delete_day':
            data = build_live_delete_day(args.date or '')
        elif mode == 'delete_range':
            data = build_live_delete_range(args.from_date or '', args.to_date or '')

        # 思考链 + 自描述注入(复制日志带出 · R2/R3)
        data['data']['meta']['chain'] = args.chain.strip()
        data['data']['meta']['wake_word'] = scene
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['data']['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(
            _quote_arg(a) for a in argv)
        data['data']['meta']['source'] = 'exercise_log (写库回执)'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'receipt')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   操作: {d["op"]} | #{d["record_id"]} | {d["meta"]["entity_type"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
