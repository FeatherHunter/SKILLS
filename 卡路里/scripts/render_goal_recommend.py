#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_recommend.py — 目标推荐 HTML 渲染器(推荐型)

对应 SKILL.md 唤醒词: 定营养目标(自动算) / 定饮水目标(自动算) / 一键定全套目标
对应模板: templates/goal_recommend.html
- 输出目录: $DATA_DIR/calorie_html/目标推荐_<TS>.html
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据: TDEE/推荐值/每周减重速率/4 项 + 依据 + 方案理由(一键全套含体重目标)

用法:
    python scripts/render_goal_recommend.py --profile 减脂
    python scripts/render_goal_recommend.py --profile cut --output /path/out.html
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_recommend.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from nutrition_goal import recommend_nutrition_goal, recommend_water_goal  # noqa: E402
from render_goal_common import build_meta, chain_valid, scene_path  # noqa: E402


PROFILE_MAP = {'减脂': 'cut', '维持': 'maintain', '增肌': 'bulk', 'cut': 'cut',
               'maintain': 'maintain', 'bulk': 'bulk'}


def build_data(profile='cut', water_only=False):
    pkey = PROFILE_MAP.get(profile, 'cut')
    rec = recommend_nutrition_goal(profile=pkey)
    current_goal = {
        'calorie_goal': rec['calorie_goal'],
        'protein_goal': rec['protein_goal'],
        'carbs_goal': rec['carbs_goal'],
        'fat_goal': rec['fat_goal'],
        'water_goal': rec['water_goal'],
    }
    if water_only:
        # 定饮水目标(自动算): 只推荐饮水, 依据(体重/季节) + 与旧值对比
        wrec = recommend_water_goal()
        current_goal = {'water_goal': wrec['recommended_water_ml']}
        return {
            'title': '定饮水目标(自动算)',
            'subtitle': f"按体重 {wrec['weight_kg']} kg × {wrec['ml_per_kg']} ml/kg({wrec['season']}季)推荐",
            'current_goal': current_goal,
            'old_water_goal': wrec['old_water_goal'],
            'recommend': {
                'basis': wrec['basis'],
                'plan_reasons': [wrec['basis'],
                                 f"旧值 {wrec['old_water_goal']} ml → 推荐 {wrec['recommended_water_ml']} ml"],
                'missing': [],
            },
        }
    return {
        'title': '定营养目标(自动算)',
        'subtitle': f"{rec['profile_label']}方案 · 基于档案(身高 {rec['basis']['height_cm']} cm / "
                    f"体重 {rec['basis']['weight_kg']} kg / {rec['basis']['age']} 岁)",
        'current_goal': current_goal,
        'recommend': {
            'profile': rec['profile'],
            'profile_label': rec['profile_label'],
            'tdee': rec['tdee'],
            'bmr': rec['bmr'],
            'weekly_rate_kg': rec['weekly_rate_kg'],
            'plan_reasons': rec['plan_reasons'],
            'missing': rec['missing'],
        },
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标推荐已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染目标推荐 HTML(推荐型)')
    p.add_argument('--profile', default='cut', help='推荐方向: 减脂/维持/增肌(或 cut/maintain/bulk)')
    p.add_argument('--water-only', action='store_true', help='仅推荐饮水目标(定饮水目标(自动算))')
    p.add_argument('--full-kit', action='store_true', help='一键定全套目标模式(营养+饮水,体重目标由 AI 确认)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    # R3 思考链强制(live 模式必传)
    if not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读档案→3.算TDEE/推荐"', file=sys.stderr)
        return 2

    # R4 自描述:场景名推断
    if args.full_kit:
        scene_name, output_type = '一键定全套目标', 'receipt'
    elif args.water_only:
        scene_name, output_type = '定饮水目标(自动算)', 'receipt'
    else:
        scene_name, output_type = '定营养目标(自动算)', 'receipt'

    try:
        data = build_data(profile=args.profile, water_only=args.water_only)
        if args.full_kit:
            data['title'] = '一键定全套目标'
            data['subtitle'] = '营养 + 饮水自动推荐(体重目标请确认后由 AI 写入)'
        # R1 视图分离:meta 不进 UI(复制日志带出)
        data['meta'] = build_meta(
            wake_word=scene_name,
            source='user_profile + weight_log + recommend_nutrition_goal',
            chain=args.chain,
        )
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    # R5 命名:<场景名>_<类型中文>_<TS>.html
    out_path = Path(args.output) if args.output else scene_path(scene_name, output_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    cg = data.get('current_goal', {})
    print(f'✅ {out_path}')
    print(f'   推荐: 卡 {cg.get("calorie_goal", "?")} / 蛋白 {cg.get("protein_goal", "?")}g / '
          f'水 {cg.get("water_goal", "?")}ml')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
