#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_config.py — 目标配置 HTML 渲染器(配置型)

对应 SKILL.md 唤醒词: 定营养目标 / 定饮水目标 / 改营养目标 / 改饮水目标
对应模板(2026-08-04 ADR-0009 按形态拆分):
- templates/goal_config_nutrition.html — 营养配置(定/改营养,5 字段 slider 联动)
- templates/goal_config_water.html — 饮水配置(定/改饮水,单字段,无宏量联动/BMR)
- 输出目录: $DATA_DIR/calorie_html/目标配置_<TS>.html
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据: 4 项宏量 + 饮水目标值(slider 可调); 改类含改前/改后对比 + 影响预估

用法:
    python scripts/render_goal_config.py --live                # 定营养目标(读 DB 当前值)
    python scripts/render_goal_config.py --live --water-only   # 定饮水目标(只显饮水)
    python scripts/render_goal_config.py --modify-nutrition    # 改营养目标(带改前/改后)
    python scripts/render_goal_config.py --modify-water        # 改饮水目标(带改前/改后)
    python scripts/render_goal_config.py --mock <JSON>         # mock 数据(测试用)
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
# 2026-08-04 ADR-0009:按形态选模板(营养 5 字段 / 饮水单字段),互不干扰
TEMPLATE_NUTRITION = SKILL_DIR / 'templates' / 'goal_config_nutrition.html'
TEMPLATE_WATER = SKILL_DIR / 'templates' / 'goal_config_water.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from render_goal_common import build_meta, chain_valid, scene_path  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_goal_config',
        description='渲染目标配置 HTML(配置型 · 5 个 slider + mini chart)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument('--mock', help='目标配置 JSON 文件路径(mock 或真实数据)')
    g.add_argument('--live', action='store_true', help='读 DB 生成(默认)')
    p.add_argument('--water-only', action='store_true', help='只显示饮水目标(定饮水目标)')
    p.add_argument('--modify-nutrition', action='store_true', help='改营养目标: 带改前/改后 + 影响预估')
    p.add_argument('--modify-water', action='store_true', help='改饮水目标: 带改前/改后')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    return p


def build_live_data(water_only=False, modify_nutrition=False, modify_water=False) -> dict:
    from db import find_db_path, get_db
    from nutrition_goal import get_nutrition_goal

    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)

    row = get_nutrition_goal()
    current_goal = {}
    if row is not None:
        current_goal = {
            'calorie_goal': row['calorie_goal'],
            'protein_goal': row['protein_goal'],
            'carbs_goal': row['carbs_goal'],
            'fat_goal': row['fat_goal'],
            'water_goal': row['water_goal'],
            'weight_goal': row['weight_goal'],
            'goal_deadline': row['goal_deadline'],
        }

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    r = conn.execute('''
        SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
               COALESCE(SUM(carbs),0), COALESCE(SUM(fat),0)
        FROM food_log WHERE date = ?
    ''', (yesterday,)).fetchone()
    w = conn.execute(
        "SELECT COALESCE(SUM(grams),0) FROM food_log WHERE date = ? AND food_name = '💧水'",
        (yesterday,),
    ).fetchone()
    yesterday_actual = {
        'date': yesterday,
        'calorie': r[0], 'protein': r[1], 'carbs': r[2], 'fat': r[3], 'water': w[0],
    }
    conn.close()

    data = {
        'current_goal': current_goal,
        'yesterday_actual': yesterday_actual,
        'weight_progress': None,
    }

    # 改类: 生成改前/改后 diff(改后 = 当前值, 由 AI 从用户输入更新; HTML 展示改前基准)
    if modify_nutrition or modify_water:
        diff_items = []
        labels = {'calorie_goal': ('热量', '卡'), 'protein_goal': ('蛋白', 'g'),
                  'carbs_goal': ('碳水', 'g'), 'fat_goal': ('脂肪', 'g'),
                  'water_goal': ('饮水', 'ml')}
        keys = ['water_goal'] if modify_water else ['calorie_goal', 'protein_goal',
                                                     'carbs_goal', 'fat_goal', 'water_goal']
        for k in keys:
            label, unit = labels[k]
            diff_items.append({'key': k, 'label': label, 'unit': unit,
                               'old': current_goal.get(k),
                               'new': None, 'impact': '由 AI 按新值给出影响预估'})
        data['diff'] = {'items': diff_items}

    if water_only:
        data['water_only'] = True

    # prompt 承诺「热量明显低于 BMR 时提示」(第一性原理 #3 · 2026-08-02 对抗审查)
    cal = current_goal.get('calorie_goal')
    bmr = _estimate_bmr()
    if cal and bmr:
        data['bmr_warning'] = {
            'bmr': bmr,
            'calorie_goal': cal,
            'below': cal < bmr,
            'text': f'热量目标 {cal} 卡低于基础代谢 BMR {bmr} 卡,长期可能影响健康,建议上调或咨询专业意见'
                    if cal < bmr else f'热量目标 {cal} 卡 ≥ BMR {bmr} 卡,在安全范围内',
        }
    return data


def _estimate_bmr():
    """估算 BMR(Mifflin-St Jeor,档案缺失用默认值)"""
    from db import find_db_path, get_db
    from analysis._utils import get_activity_factor
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    prof = conn.execute('SELECT age, gender, height_cm FROM user_profile WHERE id = 1').fetchone()
    w = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1').fetchone()
    conn.close()
    age = prof['age'] if prof and prof['age'] else 30
    gender = prof['gender'] if prof and prof['gender'] else 'male'
    h = prof['height_cm'] if prof and prof['height_cm'] else 175
    w_kg = w[0] if w else 70
    return round(10 * w_kg + 6.25 * h - 5 * age + (5 if gender == 'male' else -161))


def normalize(data: dict) -> dict:
    if not isinstance(data, dict):
        return {'current_goal': {}, 'yesterday_actual': {}, 'weight_progress': None}
    return {
        'current_goal': data.get('current_goal', {}) if isinstance(data.get('current_goal'), dict) else {},
        'yesterday_actual': data.get('yesterday_actual', {}) if isinstance(data.get('yesterday_actual'), dict) else {},
        'weight_progress': data.get('weight_progress') if isinstance(data.get('weight_progress'), dict) else None,
        'diff': data.get('diff'),
        'water_only': data.get('water_only', False),
        'bmr_warning': data.get('bmr_warning'),
    }


def render_html(data: dict, template_path: Path = None) -> str:
    template = (template_path or TEMPLATE_NUTRITION).read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标配置已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    # R3 思考链强制(live 模式必传,防 AI 偷懒 · 2026-08-02 对齐 #8)
    if not args.mock and not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.调CLI读DB→3.计算目标"', file=sys.stderr)
        return 2

    # R4 自描述:按参数推断场景名(唤醒词)与形态模板(2026-08-04 ADR-0009)
    if args.modify_nutrition:
        scene_name, output_type, template_path = '改营养目标', 'receipt', TEMPLATE_NUTRITION
    elif args.modify_water:
        scene_name, output_type, template_path = '改饮水目标', 'receipt', TEMPLATE_WATER
    elif args.water_only:
        scene_name, output_type, template_path = '定饮水目标', 'receipt', TEMPLATE_WATER
    else:
        scene_name, output_type, template_path = '定营养目标', 'receipt', TEMPLATE_NUTRITION

    try:
        if args.mock:
            data = normalize(load_data(Path(args.mock)))
            label = Path(args.mock).stem
        else:
            data = normalize(build_live_data(
                water_only=args.water_only,
                modify_nutrition=args.modify_nutrition,
                modify_water=args.modify_water,
            ))
            label = 'live'
        # R1 视图分离:meta 不进 UI(复制日志带出)
        data['meta'] = build_meta(
            wake_word=scene_name,
            source='daily_goal + food_log(昨日)',
            chain=args.chain,
        )
        # 场景化标题(2026-08-02 用户验收 #1:定营养目标不应显示「营养/体重目标」)
        data['page_title'] = {
            '定营养目标': '营养目标',
            '改营养目标': '营养目标 · 修改',
            '定饮水目标': '饮水目标',
            '改饮水目标': '饮水目标 · 修改',
        }.get(scene_name, '目标配置')
        data['scene'] = scene_name
        html = render_html(data, template_path)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    # R5 命名:<场景名>_<类型中文>_<TS>.html
    out_path = Path(args.output) if args.output else scene_path(scene_name, output_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    cg = data.get('current_goal', {})
    print(f'✅ {out_path}')
    print(f'   目标: 卡 {cg.get("calorie_goal", "?")} / 蛋白 {cg.get("protein_goal", "?")}g / '
          f'碳水 {cg.get("carbs_goal", "?")}g / 脂肪 {cg.get("fat_goal", "?")}g / 水 {cg.get("water_goal", "?")}ml')
    return 0


def load_data(json_path: Path) -> dict:
    if not json_path.exists():
        raise FileNotFoundError(f'输入文件不存在: {json_path}')
    raw = json.loads(json_path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'JSON 顶层必须是 dict,实际是 {type(raw).__name__}')
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
