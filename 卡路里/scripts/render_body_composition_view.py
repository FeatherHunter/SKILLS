#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_composition_view.py — 体脂查询结果 HTML 渲染器(v1.0 · ticket #9)

对应 SKILL.md 唤醒词: 看体脂 / 看体脂趋势 / 对比体脂
对应模板: templates/body_composition_view.html
- 数据源: body_composition 表(实读 DB,无 mock)
- 输出目录: $DATA_DIR/calorie_html/<场景名>_<类型中文>_<TS>.html(html_scene_path 规则)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据契约(与 scene-index §8 一致):
  - 看体脂: 表(日期/体脂率/来源) + 来源筛选器(皮褶钳/健身房/医院/全部) + 当前
  - 看体脂趋势: 折线(默认最近来源,可切换) + KPI(变化/平均/最低)
  - 对比体脂: 时间1/时间2 + Δ + 变化率(注明同来源对比)

用法:
    python scripts/render_body_composition_view.py --mode list [--source gym]
    python scripts/render_body_composition_view.py --mode trend [--source gym] [--days 90]
    python scripts/render_body_composition_view.py --mode compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> [--source <s>]
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_composition_view.html'

sys.path.insert(0, str(SCRIPT_DIR))
from db import find_db_path  # noqa: E402
from html_paths import html_scene_path  # noqa: E402
from source_constants import SOURCE_CHOICES, SOURCE_LABELS, SOURCE_HOME_CALIPER  # noqa: E402


SCENE_NAME = {
    'list':    '看体脂',
    'trend':   '看体脂趋势',
    'compare': '对比体脂',
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


def build_list(c, source=None):
    params = []
    sql = ("SELECT id, date, source, body_fat_pct, note FROM body_composition "
           "WHERE is_deprecated = 0")
    if source:
        sql += " AND source = ?"
        params.append(source)
    sql += " ORDER BY date DESC, id DESC"
    rows = _rows(c, sql, params)
    current = rows[0] if rows else None
    # 来源分组计数(筛选器数据)
    groups = []
    for s in SOURCE_CHOICES:
        n = sum(1 for r in rows if r['source'] == s)
        groups.append({'value': s, 'label': SOURCE_LABELS[s], 'n': n})
    return {
        'mode': 'list',
        'rows': rows,
        'current': current,
        'filter': {'active': source or 'all', 'groups': groups},
        'source_labels': SOURCE_LABELS,
    }


def build_trend(c, source=None, days=90):
    if not source:
        r = c.execute(
            "SELECT source FROM body_composition WHERE is_deprecated = 0 "
            "ORDER BY date DESC, id DESC LIMIT 1"
        ).fetchone()
        source = r[0] if r else SOURCE_HOME_CALIPER
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = _rows(c, """
        SELECT date, AVG(body_fat_pct) AS avg_pct, COUNT(*) AS n
        FROM body_composition
        WHERE is_deprecated = 0 AND date >= ? AND source = ?
        GROUP BY date ORDER BY date ASC
    """, (since, source))
    values = [r['avg_pct'] for r in rows if r['avg_pct'] is not None]
    kpi = {
        'count': len(values),
        'avg': round(sum(values) / len(values), 2) if values else None,
        'min': min(values) if values else None,
        'max': max(values) if values else None,
        'delta': round(values[-1] - values[0], 2) if len(values) >= 2 else None,
    }
    return {
        'mode': 'trend',
        'source': source,
        'rows': rows,
        'kpi': kpi,
        'days': days,
    }


def build_compare(c, start1, end1, start2, end2, source=None):
    def _period(s, e):
        params = [s, e]
        sql = ("SELECT AVG(body_fat_pct) AS avg_pct, MIN(body_fat_pct) AS min_pct, "
               "MAX(body_fat_pct) AS max_pct, COUNT(*) AS n FROM body_composition "
               "WHERE is_deprecated = 0 AND date >= ? AND date <= ?")
        if source:
            sql += " AND source = ?"
            params.append(source)
        return _rows(c, sql, params)[0]

    p1 = _period(start1, end1)
    p2 = _period(start2, end2)
    delta = pct = None
    if p1['avg_pct'] is not None and p2['avg_pct'] is not None:
        delta = round(p2['avg_pct'] - p1['avg_pct'], 2)
        if p1['avg_pct']:
            pct = round((p2['avg_pct'] - p1['avg_pct']) / p1['avg_pct'] * 100, 2)
    return {
        'mode': 'compare',
        'period1': {'start': start1, 'end': end1, **p1},
        'period2': {'start': start2, 'end': end2, **p2},
        'delta': delta,
        'pct_change': pct,
        'source': source or 'all',
        'same_source_note': '两次对比须同来源才有意义' if not source else f'同来源「{SOURCE_LABELS.get(source, source)}」对比',
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data}, ensure_ascii=False).replace('</', '<\\/')
    return template.replace(placeholder, f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染体脂查询结果 HTML(v1.0 · ticket #9)')
    p.add_argument('--mode', choices=['list', 'trend', 'compare'], required=True,
                   help='list=看体脂 / trend=看体脂趋势 / compare=对比体脂')
    p.add_argument('--source', choices=SOURCE_CHOICES, help='来源筛选(list/trend/compare)')
    p.add_argument('--days', type=int, default=90, help='trend 时间窗')
    p.add_argument('--start1', help='compare: 第一段时间起点')
    p.add_argument('--end1', help='compare: 第一段时间终点')
    p.add_argument('--start2', help='compare: 第二段时间起点')
    p.add_argument('--end2', help='compare: 第二段时间终点')
    p.add_argument('--output', help='输出文件路径(默认 html_scene_path 规则)')
    args = p.parse_args()

    c = _get_conn()
    try:
        if args.mode == 'list':
            data = build_list(c, source=args.source)
        elif args.mode == 'trend':
            data = build_trend(c, source=args.source, days=args.days)
        else:
            if not (args.start1 and args.end1 and args.start2 and args.end2):
                print('❌ compare 模式需 --start1/--end1/--start2/--end2', file=sys.stderr)
                return 1
            data = build_compare(c, args.start1, args.end1, args.start2, args.end2, source=args.source)
    finally:
        c.close()

    html = render_html(data)
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, SCENE_NAME[args.mode], 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
