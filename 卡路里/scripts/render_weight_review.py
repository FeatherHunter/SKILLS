#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_review.py — 体重复盘 / 看里程碑回溯 结果 HTML 渲染器(ticket #4)

对应 SKILL.md 唤醒词(7 个):
  - 体重复盘（本周）     → --type week
  - 体重复盘（本月）     → --type month
  - 体重复盘（最近 90 天）→ --type 90d
  - 体重复盘（今年）     → --type year(含月度趋势)
  - 体重复盘（自定义时间）→ --start <S> --end <E>
  - 看里程碑回溯         → --type milestones
  - 看体重总览           → 见 render_weight_dashboard.py
对应模板: templates/weight_review.html
用法:
  python scripts/render_weight_review.py --type week --chain "1.识别→2.读DB→3.复盘→4.渲染"
  python scripts/render_weight_review.py --type milestones --chain "..."
"""
import argparse, calendar, json, statistics, sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_review.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def _db():
    from db import find_db_path, get_db
    return get_db(find_db_path(SKILL_DIR))


def _rows(start, end):
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT date, weight_kg FROM weight_log WHERE date BETWEEN ? AND ? ORDER BY date', (start, end))
    rows = cur.fetchall()
    conn.close()
    return rows


def _window(t):
    today = date.today()
    if t == 'week':
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat(), today.isoformat(), '本周', '上周'
    if t == 'month':
        return today.replace(day=1).isoformat(), today.isoformat(), '本月', '上月'
    if t == '90d':
        return (today - timedelta(days=89)).isoformat(), today.isoformat(), '最近 90 天', '上一段 90 天'
    if t == 'year':
        return f'{today.year}-01-01', today.isoformat(), '今年', '去年'
    raise ValueError(f'未知窗口 {t}')


def _milestones(rows):
    """里程碑:从历史最高起累计减重 5/10/15/20kg 达成记录"""
    if not rows:
        return []
    max_w = max(r[1] for r in rows)
    out = []
    for delta in (5, 10, 15, 20):
        th = max_w - delta
        hit = next((r for r in rows if r[1] <= th), None)
        if hit:
            start_elapsed = (date.fromisoformat(hit[0]) - date.fromisoformat(rows[0][0])).days
            out.append({'name': f'减重 {delta}kg', 'date': hit[0], 'kg': hit[1],
                        'elapsed_days': max(0, start_elapsed)})
    return out


def build_review(review_type, start=None, end=None):
    """复盘(周/月/90 天/今年/自定义)+ 里程碑回溯"""
    today = date.today()
    if review_type == 'milestones':
        rows = _rows('2000-01-01', today.isoformat())
        ms = _milestones(rows)
        if not ms:
            return None, '尚未达成任何减重里程碑'
        summary = f'共达成 {len(ms)} 个里程碑:' + '、'.join(f"{m['name']}({m['date']})" for m in ms[:3])
        return {
            'type': 'milestones',
            'title': '看里程碑回溯',
            'subtitle': f'从历史最高 {max(r[1] for r in rows)}kg 起算 · 共 {len(rows)} 条记录',
            'kpis': [
                {'label': '里程碑数', 'value': str(len(ms)), 'extra': '5/10/15/20kg'},
                {'label': '历史最高', 'value': f'{max(r[1] for r in rows)} kg', 'extra': ''},
                {'label': '当前体重', 'value': f'{rows[-1][1]} kg', 'extra': rows[-1][0]},
                {'label': '总减重', 'value': f'{max(r[1] for r in rows) - rows[-1][1]:.1f} kg', 'extra': '距历史最高'},
            ],
            'milestones': ms,
            'table_title': '里程碑',
            'summary': summary,
        }, None

    if review_type == 'range':
        if not start or not end:
            return None, '--type range 需要 --start 与 --end'
        cur_s, cur_e, cur_label, prev_label = start, end, '该区间', '上一段等长区间'
    else:
        cur_s, cur_e, cur_label, prev_label = _window(review_type)
    rows = _rows(cur_s, cur_e)
    if not rows:
        return None, f'{cur_label}({cur_s} ~ {cur_e})无体重记录'
    # 上一段等长区间
    days = (date.fromisoformat(cur_e) - date.fromisoformat(cur_s)).days + 1
    prev_end = date.fromisoformat(cur_s) - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    prev_rows = _rows(prev_start.isoformat(), prev_end.isoformat())

    delta = round(rows[-1][1] - rows[0][1], 2)
    avg = round(statistics.mean([r[1] for r in rows]), 2)
    vs_last = None
    if prev_rows:
        prev_avg = round(statistics.mean([r[1] for r in prev_rows]), 2)
        vs_last = round(avg - prev_avg, 2)
    points = [{'date': r[0], 'kg': r[1]} for r in rows]
    month = review_type == 'year'
    monthly = None
    if month:
        monthly = defaultdict(list)
        for r in rows:
            monthly[r[0][:7]].append(r[1])
        monthly = [{'month': m, 'avg': round(statistics.mean(v), 2)} for m, v in sorted(monthly.items())]

    title = {'week': '体重复盘（本周）', 'month': '体重复盘（本月）', '90d': '体重复盘（最近 90 天）',
             'year': '体重复盘（今年）', 'range': '体重复盘（自定义时间）'}[review_type]
    kpis = [
        {'label': '期间变化', 'value': f'{delta:+.1f} kg', 'extra': f'{rows[0][1]} → {rows[-1][1]}',
         'cls': 'good' if delta < 0 else 'bad'},
        {'label': '期间均值', 'value': f'{avg} kg', 'extra': f'{len(rows)} 条'},
    ]
    if month:
        kpis.append({'label': '年度均值', 'value': f'{avg} kg', 'extra': f'{len(monthly)} 个月'})
        kpis.append({'label': '月份数', 'value': str(len(monthly)), 'extra': '有记录'})
    else:
        kpis.append({'label': f'vs {prev_label}', 'value': (f'{vs_last:+.1f} kg' if vs_last is not None else '—'),
                     'extra': '均值差'})
        kpis.append({'label': '记录天数', 'value': str(len(rows)), 'extra': f'{cur_s} ~ {cur_e}'})
    summary = f'{cur_label}变化 {delta:+.1f} kg(均值 {avg}kg)'
    if vs_last is not None:
        summary += f' · vs {prev_label} 均值 {vs_last:+.1f}kg'
    return {
        'type': review_type,
        'title': title,
        'subtitle': f'{cur_s} ~ {cur_e} · {len(rows)} 条记录',
        'kpis': kpis,
        'points': points,
        'monthly': monthly,
        'summary': summary,
    }, None


def main():
    p = argparse.ArgumentParser(description='渲染体重复盘/里程碑 HTML(ticket #4)')
    p.add_argument('--type', choices=['week', 'month', '90d', 'year', 'range', 'milestones'], default='week')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        return 2

    try:
        data, err = build_review(args.type, start=args.start, end=args.end)
        if err:
            print(f'❌ {err}', file=sys.stderr)
            return 1
        scene_name = data['title']
        data['meta'] = {'generated_at': date.today().isoformat(), 'chain': args.chain.strip(),
                        'wake_word': scene_name}
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
        data['meta']['source'] = 'weight_log (复盘)'
        payload = {'status': 'ok', 'data': data, 'message': '已生成体重复盘'}
        html = render_html(payload)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene_name, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   类型: {args.type}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
