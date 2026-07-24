#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_nutrition_ratio.py — 营养配比 HTML 渲染器(报告型 · 3 维配比)

对应 SKILL.md 唤醒词: 查营养配比
对应模板: templates/nutrition_ratio.html
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'nutrition_ratio.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def build_data(start, end):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(protein), 0), COALESCE(SUM(carbohydrates), 0), COALESCE(SUM(fat), 0), COALESCE(SUM(calorie), 0)
        FROM food_log WHERE date BETWEEN ? AND ?
    """, (start, end))
    p_g, c_g, f_g, total_cal = cur.fetchone()
    cur.execute("SELECT protein, carbohydrates, fat, calorie FROM daily_goal ORDER BY id DESC LIMIT 1")
    g = cur.fetchone() or (120, 200, 60, 1800)
    conn.close()
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    tp = g[0] * days; tc = g[1] * days; tf = g[2] * days
    p_pct = round(p_g * 4 / total_cal * 100) if total_cal else 0
    c_pct = round(c_g * 4 / total_cal * 100) if total_cal else 0
    f_pct = round(f_g * 9 / total_cal * 100) if total_cal else 0
    bad = sum([p_pct < 5, c_pct < 30 or c_pct > 70, f_pct > 40])
    return {
        'status': 'ok',
        'data': {
            'summary': {
                'total_calorie': total_cal,
                'protein_g': p_g, 'protein_pct': p_pct,
                'carb_g': c_g, 'carb_pct': c_pct,
                'fat_g': f_g, 'fat_pct': f_pct,
                'balance': 'good' if bad == 0 else ('warn' if bad <= 1 else 'bad'),
            },
            'target': {'protein_g': tp, 'carb_g': tc, 'fat_g': tf},
            'range': {
                'protein': {'min': 10, 'max': 20, 'label': '10-20%'},
                'carb':    {'min': 45, 'max': 65, 'label': '45-65%'},
                'fat':     {'min': 20, 'max': 35, 'label': '20-35%'},
            },
            'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
        },
        'message': f'已生成 {start} ~ {end} 营养配比({days} 天)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 或 重复出现')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染营养配比 HTML(报告型 · 3 维配比)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int)
    p.add_argument('--mock')
    p.add_argument('--output')
    args = p.parse_args()
    if args.days:
        end = date.today()
        start = end - timedelta(days=args.days - 1)
    else:
        end = date.fromisoformat(args.end or date.today().isoformat())
        start = date.fromisoformat(args.start or (end - timedelta(days=6)).isoformat())
    s, e = start.isoformat(), end.isoformat()
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'nutrition_ratio')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围: {s} ~ {e} | 蛋白 {sm["protein_pct"]}% / 碳水 {sm["carb_pct"]}% / 脂肪 {sm["fat_pct"]}% | {sm["balance"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
