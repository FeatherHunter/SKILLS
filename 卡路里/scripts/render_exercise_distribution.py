#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_exercise_distribution.py — 运动分布/贡献 HTML 渲染器(报告型 · 双模式)

对应 SKILL.md 唤醒词:
  - 查运动分布 → mode='distribution' (默认)
  - 查运动贡献 → mode='contribution'
对应模板: templates/exercise_distribution.html

v2.4.8 修:列名对齐 db.py schema(exercise_log/food_log 2026-07-12 重构后)
  · exercise_log: type → exercise_type, calories → calories_burned,
                   minutes → duration_minutes, sets → set_index
  · food_log: calorie → calories
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'exercise_distribution.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path, html_scene_path  # noqa
from _cmd_maps import EXERCISE_DISTRIBUTION_MODE_MAP  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok")
    return raw


def build_data(start, end, mode='distribution', tdee=1700):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    # 取每日运动(列名按 db.py:135-145)
    cur.execute("""
        SELECT date, exercise_type, category, calories_burned, duration_minutes, set_index, count(*)
        FROM exercise_log
        WHERE date BETWEEN ? AND ?
        GROUP BY date, exercise_type, category ORDER BY date
    """, (start, end))
    rows = cur.fetchall()
    # 取每日摄入(food_log 列名按 db.py:107-117)
    cur.execute("""
        SELECT date, COALESCE(SUM(calories), 0)
        FROM food_log WHERE date BETWEEN ? AND ?
        GROUP BY date
    """, (start, end))
    intake_by_day = dict(cur.fetchall())
    conn.close()

    # 4 分类
    buckets = {'strength':{'count':0,'calorie':0,'minutes':0},
               'cardio':   {'count':0,'calorie':0,'minutes':0},
               'flex':     {'count':0,'calorie':0,'minutes':0},
               'daily':    {'count':0,'calorie':0,'minutes':0}}
    _CAT_MAP = {'力量':'strength','有氧':'cardio','柔韧':'flex','日常':'daily'}
    for date_, type_, cat, cal, mins, sets, n in rows:
        key = _CAT_MAP.get(cat, 'daily')
        buckets[key]['count'] += n
        buckets[key]['calorie'] += cal or 0   # None 防护(2026-08-02 · ticket #5 对抗审查)
        buckets[key]['minutes'] += mins or 0

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    active_days = len({r[0] for r in rows})
    total_calorie = sum(b['calorie'] for b in buckets.values())
    total_min = sum(b['minutes'] for b in buckets.values())
    total_sets = sum(b['count'] for b in buckets.values())
    avg_cal = round(total_calorie / days) if days else 0
    avg_min = round(total_min / max(active_days, 1))
    avg_set = round(total_sets / max(active_days, 1))

    total_intake = sum(intake_by_day.values())
    weekly_deficit = tdee * days + total_calorie - total_intake
    contrib_pct = round(total_calorie / max(total_intake, 1) * 100, 1)

    base = {
        'summary': {
            'active_days': active_days,
            'total_calorie': total_calorie,
            'avg_calorie': avg_cal,
            'total_minutes': total_min,
            'avg_minutes': avg_min,
            'total_sets': total_sets,
            'avg_sets': avg_set,
            'contribution_pct': contrib_pct,
            'weekly_deficit': weekly_deficit,
        },
        'breakdown': buckets,
        'contrib': {
            'exercise': total_calorie,
            'tdee': tdee * days,
            'intake': total_intake,
            'exercise_pct': contrib_pct,
            'intake_pct': 100,
            'weekly_deficit': weekly_deficit,
            'contribution_pct': contrib_pct,
        },
        'series': [{'date': start, 'total_calorie': total_calorie}] * days,
        'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
        'mode': mode,
    }
    return {'status': 'ok', 'data': base, 'message': f'已生成 {start} ~ {end} 运动{mode}({days} 天)'}


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染运动分布/贡献 HTML(报告型)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int)
    p.add_argument('--mode', choices=['distribution','contribution'], default='distribution')
    p.add_argument('--mock', help='mock JSON 文件(代替 DB 查询)')
    p.add_argument('--tdee', type=int, default=1700)
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02 ticket #5)')
    p.add_argument('--output')
    args = p.parse_args()
    # ⭐ 思考链强制(R3 · 2026-08-02 ticket #5 运动 39 场景对齐)
    from render_crud_view import _chain_valid
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读DB→3.渲染报表"', file=sys.stderr)
        return 2
    if args.days:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
    else:
        end_d = date.fromisoformat(args.end or date.today().isoformat())
        start_d = date.fromisoformat(args.start or (end_d - timedelta(days=6)).isoformat())
    s, e = start_d.isoformat(), end_d.isoformat()
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e, mode=args.mode, tdee=args.tdee)
        # mock 缺 mode 字段时手动注入
        if 'mode' not in data.get('data', {}):
            data['data']['mode'] = args.mode
        # R5 场景命名 + meta 注入(2026-08-02 · ticket #5)
        scene = '看运动类型分布' if args.mode == 'distribution' else '看运动贡献'
        data['data']['meta']['chain'] = args.chain.strip()
        data['data']['meta']['wake_word'] = scene
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   模式: {args.mode} | 范围: {s} ~ {e} | 运动 {sm["active_days"]}/{data["data"]["meta"]["days"]} 天 | {sm["total_calorie"]} 卡')
    return 0


if __name__ == '__main__':
    sys.exit(main())
