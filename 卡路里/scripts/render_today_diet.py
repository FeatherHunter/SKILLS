#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_today_diet.py — 今日饮食 HTML 渲染器(报告型 · 单日 4 餐)

对应 SKILL.md 唤醒词: 查今天吃 / 查吃的记录
对应模板: templates/today_diet.html
- 输出目录: $DATA_DIR/calorie_html/今日饮食总览_<TS>.html (手册 §4.1 · v2.4.8 中文化)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- v2.4.8 修:列名对齐 db.py schema(daily_goal/food_log 2026-07-12 重构后)
  · daily_goal: calorie → calorie_goal, protein → protein_goal,
                carbohydrates → carbs_goal, fat → fat_goal, water_ml → water_goal
  · food_log: meal_type 不存在(按 time 用 diet.infer_meal_type 推断 → 英文 key),
              calorie → calories, carbohydrates → carbs, water_ml 不存在
              (饮水以 food_name='💧水' 标记,sum(grams) 替代)
"""
import argparse, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'today_diet.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


# 模板 today_diet.html 用英文 key(.meal-tag.breakfast/lunch/dinner/snack + JS mealLabels)
MEAL_TYPE_LABELS = {'breakfast':'早餐', 'lunch':'午餐', 'dinner':'晚餐', 'snack':'加餐'}
MEAL_TARGETS = {'breakfast':450, 'lunch':650, 'dinner':550, 'snack':150}

# diet.infer_meal_type 返回中文 → 模板需要的英文 key 映射
_MEAL_CN_TO_KEY = {
    '早餐':   'breakfast',
    '午餐':   'lunch',
    '下午茶': 'snack',     # 模板只有 4 类,下午茶 → 加餐
    '晚餐':   'dinner',
    '夜宵':   'snack',
    '其他':   'snack',
}


def _meal_key(time_str):
    """time_str → 模板英文 key(breakfast/lunch/dinner/snack)"""
    cn = infer_meal_type(time_str)
    return _MEAL_CN_TO_KEY.get(cn, 'snack')


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError(f"数据状态非 ok: {raw.get('message')}")
    return raw


def build_data(day, mode='diet'):
    """从 calorie_data.db 查 food_log + daily_goal + 餐次聚合

    mode: 'diet'(默认,看今日饮食) | 'nutrition'(看今日营养 · #44 视角分离)
    """
    from db import find_db_path
    import sqlite3

    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # daily_goal:列名按 db.py:117-125
    cur.execute("""
        SELECT calorie_goal, protein_goal, carbs_goal, fat_goal, water_goal
        FROM daily_goal ORDER BY id DESC LIMIT 1
    """)
    goal = cur.fetchone() or {
        'calorie_goal': 1800, 'protein_goal': 120,
        'carbs_goal':   200,  'fat_goal':     60,
        'water_goal':   2000,
    }

    # food_log:列名按 db.py:107-117,meal_type 列不存在(由 time 推断)
    cur.execute("""
        SELECT time, food_name, grams, calories, protein, carbs, fat
        FROM food_log
        WHERE date = ?
        ORDER BY time
    """, (day,))
    rows = cur.fetchall()

    # 饮水聚合:water 用 food_name='💧水' 标记,sum(grams) 作为 ml
    cur.execute("""
        SELECT COALESCE(SUM(grams), 0) FROM food_log
        WHERE date = ? AND food_name = '💧水'
    """, (day,))
    water_row = cur.fetchone()
    water = water_row[0] if water_row else 0

    conn.close()

    meals = []
    for r in rows:
        m = dict(r)
        m['meal_type'] = _meal_key(m.get('time') or '')  # 注入 meal_type 给模板
        m['calorie']   = m.get('calories', 0) or 0       # 模板用 calorie key
        m['carb']      = m.get('carbs', 0) or 0
        m['protein']   = m.get('protein', 0) or 0
        m['fat']       = m.get('fat', 0) or 0
        meals.append(m)

    # 餐次汇总(用模板英文 key)
    summary_meals = {}
    for m in meals:
        k = m['meal_type']
        if k not in summary_meals:
            summary_meals[k] = {'calorie': 0, 'target': MEAL_TARGETS.get(k, 200)}
        summary_meals[k]['calorie'] += m['calorie']

    total_cal   = sum(m['calorie'] for m in meals)
    total_prot  = sum(m['protein'] for m in meals)
    total_carb  = sum(m['carb'] for m in meals)
    total_fat   = sum(m['fat'] for m in meals)

    def pct(v, t):
        return round(v / t * 100) if t else 0

    return {
        'status': 'ok',
        'data': {
            'summary': {
                'calorie':        total_cal,
                'target':         goal['calorie_goal'],
                'record_count':   len(meals),
                'protein_g':      total_prot,
                'protein_target': goal['protein_goal'],
                'protein_pct':    pct(total_prot, goal['protein_goal']),
                'carb_g':         total_carb,
                'carb_target':    goal['carbs_goal'],
                'carb_pct':       pct(total_carb, goal['carbs_goal']),
                'fat_g':          total_fat,
                'fat_target':     goal['fat_goal'],
                'fat_pct':        pct(total_fat, goal['fat_goal']),
                'water_ml':       water,
                'water_target':   goal['water_goal'],
                'meals':          summary_meals,
            },
            'meals': meals,
            'meta': {
                'date':  day,
                'today': date.today().isoformat(),
                'mode':  mode,   # #44 审查:看今日营养(视角分离)
            },
        },
        'message': f'已生成 {day} 今日饮食({len(meals)} 条)',
    }


# 复用 diet.infer_meal_type(已在 diet.py:32 导出)
from diet import infer_meal_type  # noqa: E402


def diet_filename_label(day, today=None):
    """按查询日期生成文件名标签(issue #53 · 2026-08-09)

    规则:
      - day == today      → '今日饮食总览'
      - day == today-1    → '昨日饮食总览'
      - 其他历史日期       → '饮食总览_<YYYYMMDD>'(按日期归一,一眼可辨)

    Args:
        day: 查询日期 'YYYY-MM-DD'(或 'YYYYMMDD',自动归一)
        today: 参考今天(默认 date.today();测试可注入)

    Returns:
        str: 文件名标签(不含 TS 后缀)
    """
    today = today or date.today()
    d = day.replace('-', '')
    t = today.isoformat().replace('-', '')
    if d == t:
        return '今日饮食总览'
    if d == (today - timedelta(days=1)).isoformat().replace('-', ''):
        return '昨日饮食总览'
    return f'饮食总览_{d}'


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 或 重复出现')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace('<!--INJECT-DATA-->', inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染今日饮食/今日营养 HTML(报告型 · 单日)')
    p.add_argument('--date', help='日期 YYYY-MM-DD(默认今天)')
    p.add_argument('--mode', choices=['diet', 'nutrition'], default='diet',
                   help='视图模式:diet=看今日饮食(明细视角) / nutrition=看今日营养(完成度视角 · #44)')
    p.add_argument('--mock', help='从 mock JSON 文件加载(代替 DB 查询)')
    p.add_argument('--output', help='输出文件路径(默认 calorie_html/今日饮食总览_<TS>.html)')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()

    day = args.date or date.today().isoformat()
    try:
        if args.mock:
            data = _load_data(args.mock)
        else:
            data = build_data(day, mode=args.mode)
        if args.chain:
            data['data']['meta']['chain'] = args.chain
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    if args.output:
        out_path = Path(args.output)
    else:
        # issue #53(2026-08-09):文件名随查询日期动态,不再写死「今日饮食总览」
        out_path = html_path(SKILL_DIR, diet_filename_label(day))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data['data']['summary']
    remain = s['target'] - s['calorie']
    print(f'✅ {out_path}')
    print(f'   日期: {day} | 热量: {s["calorie"]:,} / {s["target"]} | 剩余: {remain} 卡 | {len(data["data"]["meals"])} 条记录')
    return 0


if __name__ == '__main__':
    sys.exit(main())
