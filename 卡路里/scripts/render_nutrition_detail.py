#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_nutrition_detail.py — 看营养素深度 HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 看营养素深度
对应模板: templates/nutrition_detail.html

呈现数据: 纤维/钠/糖 实际 vs 推荐(固定 DRI 表)
数据来源: food_log × nutrition_products(按食物名关联,按克数折算每 100g);
         无食品库记录的条目标记「缺数据」(不参与合计)。
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'nutrition_detail.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa

# 固定推荐值(中国居民膳食指南 2022 · 每 100g 食品库数据折算)
DRI = {
    'fiber': {'label': '膳食纤维', 'unit': 'g', 'target': 25, 'good': '≥25g/天'},
    'sodium': {'label': '钠', 'unit': 'mg', 'target': 2000, 'good': '≤2000mg/天'},
    'sugar': {'label': '糖', 'unit': 'g', 'target': 50, 'good': '≤50g/天'},
}


def build_data(start, end):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute('''
        SELECT food_name, grams FROM food_log
        WHERE date BETWEEN ? AND ? AND food_name != '💧水'
    ''', (start, end))
    meals = cur.fetchall()

    # 食品库按名称聚合(每 100g 纤维/钠/糖)
    cur.execute('''
        SELECT product_name, dietary_fiber, sodium, sugar FROM nutrition_products
        WHERE is_deprecated = 0
    ''')
    lib = {}
    for name, fiber, sodium, sugar in cur.fetchall():
        lib.setdefault(name, []).append((fiber, sodium, sugar))
    conn.close()

    totals = {'fiber': 0.0, 'sodium': 0.0, 'sugar': 0.0}
    missing = set()
    matched = 0
    for food, grams in meals:
        grams = float(grams or 0)
        if food not in lib or grams <= 0:
            missing.add(food)
            continue
        fiber, sodium, sugar = lib[food][0]
        scale = grams / 100.0
        totals['fiber'] += (fiber or 0) * scale
        totals['sodium'] += (sodium or 0) * scale
        totals['sugar'] += (sugar or 0) * scale
        matched += 1

    items = []
    for key, spec in DRI.items():
        val = round(totals[key], 1)
        target = spec['target']
        pct = round(val / target * 100, 1) if target else 0
        items.append({
            'key': key, 'label': spec['label'], 'unit': spec['unit'],
            'value': val, 'target': target, 'pct': pct,
            'good': spec['good'], 'status': 'ok' if pct <= 100 else 'over',
        })

    return {
        'status': 'ok',
        'data': {
            'summary': {'days': (date.fromisoformat(end) - date.fromisoformat(start)).days + 1,
                        'matched_meals': matched, 'missing_foods': sorted(missing)},
            'items': items,
            'meta': {'start': start, 'end': end, 'today': date.today().isoformat()},
        },
        'message': f'营养素深度 {start} ~ {end}',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染营养素深度 HTML(结果型 · 纤维/钠/糖)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int, default=7)
    p.add_argument('--output')
    args = p.parse_args()
    if not args.start or not args.end:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
        s, e = start_d.isoformat(), end_d.isoformat()
    else:
        s, e = args.start, args.end
    try:
        data = build_data(s, e)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '营养素深度')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   范围 {s} ~ {e} | 匹配 {sm["matched_meals"]} 餐 | 缺数据 {len(sm["missing_foods"])} 种食物')
    return 0


if __name__ == '__main__':
    sys.exit(main())
