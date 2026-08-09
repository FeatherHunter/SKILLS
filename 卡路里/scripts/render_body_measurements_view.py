#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_measurements_view.py — 围度查询结果 HTML 渲染器(v1.0 · ticket #9)

对应 SKILL.md 唤醒词: 看围度 / 看围度趋势 / 对比围度
对应模板: templates/body_measurements_view.html
- 数据源: body_measurements 表(实读 DB,无 mock)
- 输出目录: $DATA_DIR/calorie_html/<场景名>_<类型中文>_<TS>.html(html_scene_path 规则)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据契约(与 scene-index §8 一致):
  - 看围度: 表(日期/各围度) + 部位筛选器(只看某部位历史)
  - 看围度趋势: 部位选择 → 折线 + 变化摘要
  - 对比围度: 两个日期 13 项 Δ

用法:
    python scripts/render_body_measurements_view.py --mode list [--metric waist-cm]
    python scripts/render_body_measurements_view.py --mode trend --metric waist-cm [--days 90]
    python scripts/render_body_measurements_view.py --mode compare --date1 <D1> --date2 <D2>
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_measurements_view.html'

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path  # noqa: E402
from html_paths import html_scene_path  # noqa: E402
from validators import MEASUREMENT_FIELDS, _caliper_cli_name  # noqa: E402
from render_crud_view import _chain_valid  # noqa: E402 · 思考链校验单一来源(2026-08-02)
from render_goal_common import build_meta  # noqa: E402 · 08 规范复制日志 META(R4 自描述)

METRIC_CLI = {_caliper_cli_name(f): f for f in MEASUREMENT_FIELDS}
METRIC_LABELS = {
    'chest_cm': '胸围', 'waist_cm': '腰围', 'abdomen_cm': '腹围', 'hip_cm': '臀围',
    'left_thigh_cm': '左大腿', 'right_thigh_cm': '右大腿',
    'left_calf_cm': '左小腿', 'right_calf_cm': '右小腿',
    'left_arm_cm': '左上臂', 'right_arm_cm': '右上臂',
    'left_forearm_cm': '左前臂', 'right_forearm_cm': '右前臂',
    'shoulder_cm': '肩围',
}

SCENE_NAME = {
    'list':    '看围度',
    'trend':   '看围度趋势',
    'compare': '对比围度',
}
SCENE_ID = {
    'list':    'body_meas_list',
    'trend':   'body_meas_trend',
    'compare': 'body_meas_compare',
}


def _get_conn():
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    import sqlite3
    if not p.exists():
        from db import init_db
        init_db(p)
    return sqlite3.connect(str(p))


def _rows(c, sql, params):
    cur = c.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def build_list(c, metric=None):
    all_cols = ['id', 'date'] + MEASUREMENT_FIELDS + ['note']
    sql = "SELECT " + ', '.join(all_cols) + " FROM body_measurements WHERE is_deprecated = 0"
    sql += " ORDER BY date DESC, id DESC"
    rows = _rows(c, sql, [])
    # 部位筛选器:各部位有数据的日期数(全量统计)
    filters = []
    for cli, col in METRIC_CLI.items():
        n = sum(1 for r in rows if r.get(col) is not None)
        filters.append({'value': cli, 'label': METRIC_LABELS[col], 'n': n})
    return {
        'mode': 'list',
        'rows': rows,
        'metric_labels': METRIC_LABELS,
        'metric_cli': METRIC_CLI,
        'filter': {'active': metric or '', 'items': filters},
    }


def build_trend_all(c, days=90, active_metric=None):
    """全部位序列(2026-08-05 客户端切换):默认最近有数据的部位 + 各部位 series"""
    since = (date.today() - timedelta(days=days)).isoformat()
    active = None
    series = {}
    for cli, col in METRIC_CLI.items():
        rows = _rows(c, f"""
            SELECT date, AVG({col}) AS avg_val, COUNT(*) AS n
            FROM body_measurements
            WHERE is_deprecated = 0 AND date >= ? AND {col} IS NOT NULL
            GROUP BY date ORDER BY date ASC
        """, (since,))
        if rows:
            series[cli] = {'label': METRIC_LABELS[col], 'rows': rows}
            if active is None:
                last = c.execute(
                    f"SELECT date FROM body_measurements WHERE is_deprecated = 0 AND {col} IS NOT NULL "
                    f"ORDER BY date DESC, id DESC LIMIT 1"
                ).fetchone()
                if last:
                    active = cli

    active = active_metric if active_metric in series else (active or (list(series.keys())[0] if series else None))

    def _kpi(rows):
        values = [r['avg_val'] for r in rows if r['avg_val'] is not None]
        return {
            'count': len(values),
            'avg': round(sum(values) / len(values), 2) if values else None,
            'min': min(values) if values else None,
            'max': max(values) if values else None,
            'delta': round(values[-1] - values[0], 2) if len(values) >= 2 else None,
        }

    rows = series.get(active, {}).get('rows', []) if active else []
    return {
        'mode': 'trend',
        'metric': active,
        'metric_label': series.get(active, {}).get('label', ''),
        'series': series,
        'rows': rows,
        'kpi': _kpi(rows),
        'days': days,
    }


def build_compare(c, date1, date2):
    def _snap(day):
        cols = ['id'] + MEASUREMENT_FIELDS
        r = _rows(c, f"SELECT {', '.join(cols)} FROM body_measurements "
                     f"WHERE is_deprecated = 0 AND date = ? ORDER BY id DESC LIMIT 1", (day,))
        return r[0] if r else None

    snap1 = _snap(date1)
    snap2 = _snap(date2)
    if not snap1:
        return {'mode': 'compare', 'error': f'{date1} 无围度记录'}
    if not snap2:
        return {'mode': 'compare', 'error': f'{date2} 无围度记录'}
    deltas = []
    for col in MEASUREMENT_FIELDS:
        v1, v2 = snap1.get(col), snap2.get(col)
        if v1 is not None and v2 is not None:
            deltas.append({
                'label': METRIC_LABELS[col],
                'before': v1, 'after': v2,
                'delta': round(v2 - v1, 2),
                'pct': round((v2 - v1) / v1 * 100, 2) if v1 else None,
            })
    deltas.sort(key=lambda d: abs(d['delta']), reverse=True)
    return {
        'mode': 'compare',
        'date1': date1, 'date2': date2,
        'deltas': deltas,
        'n_compared': len(deltas),
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data}, ensure_ascii=False).replace('</', '<\\/')
    return template.replace(placeholder, f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染围度查询结果 HTML(v1.0 · ticket #9)')
    p.add_argument('--mode', choices=['list', 'trend', 'compare'], required=True,
                   help='list=看围度 / trend=看围度趋势 / compare=对比围度')
    p.add_argument('--metric', choices=list(METRIC_CLI.keys()), help='部位(list/trend 用)')
    p.add_argument('--days', type=int, default=90, help='trend 时间窗')
    p.add_argument('--date1', help='compare: 第一次日期')
    p.add_argument('--date2', help='compare: 第二次日期')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径(默认 html_scene_path 规则)')
    args = p.parse_args()

    # ⭐ 思考链强制校验(R3 · 2026-08-02 用户拍板)
    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别→2.选部位→3.读DB→4.渲染"', file=sys.stderr)
        return 2

    c = _get_conn()
    try:
        if args.mode == 'list':
            data = build_list(c, metric=args.metric)
        elif args.mode == 'trend':
            data = build_trend_all(c, days=args.days, active_metric=args.metric)
        else:
            if not (args.date1 and args.date2):
                print('❌ compare 模式需 --date1/--date2', file=sys.stderr)
                return 1
            data = build_compare(c, args.date1, args.date2)
    finally:
        c.close()

    # 08 规范复制日志 META(R4 自描述 · meta 不进 UI,复制日志带出)
    data['meta'] = build_meta(
        wake_word=SCENE_NAME[args.mode],
        source='body_measurements 表(is_deprecated=0)',
        chain=args.chain,
        extra={'scene_id': SCENE_ID[args.mode]},
    )

    html = render_html(data)
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, SCENE_NAME[args.mode], 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
