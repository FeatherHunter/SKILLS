#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_today_diet.py — 今日饮食 HTML 渲染器(报告型 · 单日 4 餐)

对应 SKILL.md 唤醒词: 查今天吃 / 查吃的记录
对应模板: templates/today_diet.html
- 输出目录: $DATA_DIR/calorie_html/today_diet_<TS>.html (手册 §4.1)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
"""
import argparse, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'today_diet.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


MEAL_TYPE_LABELS = {'breakfast':'早餐', 'lunch':'午餐', 'dinner':'晚餐', 'snack':'加餐'}
MEAL_TARGETS = {'breakfast':450, 'lunch':650, 'dinner':550, 'snack':150}


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def build_data(day):
    """从 calorie_data.db 查 food_log + daily_goal + 餐次聚合"""
    from db import find_db_path
    import sqlite3

    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT calorie, protein, carbohydrates, fat, water_ml FROM daily_goal ORDER BY id DESC LIMIT 1")
    goal = cur.fetchone() or {'calorie':1800, 'protein':120, 'carbohydrates':200, 'fat':60, 'water_ml':2000}

    cur.execute("""
        SELECT time, meal_type, food_name, grams, calorie, protein, carbohydrates, fat
        FROM food_log
        WHERE date = ?
        ORDER BY time
    """, (day,))
    rows = cur.fetchall()
    conn.close()

    meals = [dict(r) for r in rows]
    for m in meals:
        m['protein'] = m.get('protein', 0) or 0
        m['carb'] = m.get('carbohydrates', 0) or 0
        m['fat'] = m.get('fat', 0) or 0
        m.pop('carbohydrates', None)

    # 餐次汇总
    summary_meals = {}
    for m in meals:
        k = m['meal_type']
        if k not in summary_meals:
            summary_meals[k] = {'calorie': 0, 'target': MEAL_TARGETS.get(k, 200)}
        summary_meals[k]['calorie'] += m['calorie']

    total_cal = sum(m['calorie'] for m in meals)
    total_prot = sum(m['protein'] for m in meals)
    total_carb = sum(m['carb'] for m in meals)
    total_fat = sum(m['fat'] for m in meals)
    water = sum(m.get('water_ml', 0) for m in meals if m.get('food_name') == '💧水')

    def pct(v, t):
        return round(v / t * 100) if t else 0

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'calorie': total_cal,
                'target': goal['calorie'],
                'protein_g': total_prot,
                'protein_target': goal['protein'],
                'protein_pct': pct(total_prot, goal['protein']),
                'carb_g': total_carb,
                'carb_target': goal['carbohydrates'],
                'carb_pct': pct(total_carb, goal['carbohydrates']),
                'fat_g': total_fat,
                'fat_target': goal['fat'],
                'fat_pct': pct(total_fat, goal['fat']),
                'water_ml': water,
                'water_target': goal['water_ml'],
                'meals': summary_meals,
            },
            'meals': meals,
            'meta': {
                'date': day,
                'today': date.today().isoformat(),
            },
        },
        'message': f'已生成 {day} 今日饮食({len(meals)} 条)',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 或 重复出现')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace('<!--INJECT-DATA-->', inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染今日饮食 HTML(报告型 · 单日 4 餐)')
    p.add_argument('--date', help='日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--mock', help='从 mock JSON 文件加载(代替 DB 查询)')
    p.add_argument('--output', help='输出文件路径(默认 calorie_html/today_diet_<TS>.html)')
    args = p.parse_args()

    day = args.date or date.today().isoformat()
    try:
        if args.mock:
            data = _load_data(args.mock)
        else:
            data = build_data(day)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        out_path = html_path(SKILL_DIR, 'today_diet')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['data']['summary']
    remain = s['target'] - s['calorie']
    print(f'✅ {out_path}')
    print(f'   日期: {day} | 热量: {s["calorie"]:,} / {s["target"]} | 剩余: {remain} 卡 | {len(data["data"]["meals"])} 条记录')
    return 0


if __name__ == '__main__':
    sys.exit(main())
