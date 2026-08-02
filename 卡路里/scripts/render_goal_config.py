#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_config.py — 目标配置 HTML 渲染器(G6)

对应 SKILL.md 唤醒词:定营养目标 / 定营养目标(自动算) / 定体重目标 / 定体重目标(自动算截止) / 定体重目标(含起始日) / 定饮水目标 / 定饮水目标(自动算) / 一键定全套目标 / 改营养目标 / 改体重目标 / 改饮水目标 / 暂停所有目标 / 重启所有目标

设计原则(与 G2-G5 一致):
- 过程型 HTML(AI 协同模式 · 原则 10)
- 3 个复制按钮:采纳全部 / 仅营养 / 仅体重
- 4 部分 prompt:场景 + 数据 + 期望 + 来源
- Apple 风:系统字体 / 浅灰底 / 主色蓝

用法:
    python scripts/render_goal_config.py --live                # 读 DB(当前目标 + 昨日实际 + 体重进度)
    python scripts/render_goal_config.py --recommend <方向>    # 自动算推荐注入(减脂/维持/增肌),用户微调后采纳
    python scripts/render_goal_config.py --mock <JSON>        # mock 数据(测试用)
    python scripts/render_goal_config.py --live --output <p>  # 指定输出
"""
import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_config.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_goal_config',
        description='渲染目标配置 HTML(G6 · 5 个 slider + mini chart)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument('--mock', help='目标配置 JSON 文件路径(mock 或真实数据)')
    g.add_argument('--live', action='store_true', help='读 DB 生成(默认模式)')
    g.add_argument('--recommend', choices=['cut', 'maintain', 'bulk', '减脂', '维持', '增肌'],
                   help='自动算推荐注入(映射:减脂=cut/维持=maintain/增肌=bulk)')
    p.add_argument('--output', help='输出文件路径')
    return p


def load_data(json_path: Path) -> dict:
    if not json_path.exists():
        raise FileNotFoundError(f'输入文件不存在: {json_path}')
    raw = json.loads(json_path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'JSON 顶层必须是 dict,实际是 {type(raw).__name__}')
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def build_live_data() -> dict:
    """读 DB 组装 goal_config 数据契约(current_goal / yesterday_actual / weight_progress)"""
    from db import find_db_path, get_db
    from nutrition_goal import get_nutrition_goal

    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)

    # current_goal: daily_goal(id=1) 当前目标
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

    # yesterday_actual: 昨日 food_log 聚合(卡/蛋白/碳水/脂肪/饮水 ml)
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

    # weight_progress: weight_goal.get_weight_goal() + 最新体重
    from weight_goal import get_weight_goal
    wg = get_weight_goal()
    weight_progress = None
    if wg and wg[0] is not None:
        weight_goal_val, deadline, days_left, _, calorie_adj = wg
        cur = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1').fetchone()
        weight_progress = {
            'current': cur[0] if cur else None,
            'target': weight_goal_val,
            'days_left': days_left,
            'calorie_adjustment': calorie_adj,
        }

    conn.close()
    return {
        'current_goal': current_goal,
        'yesterday_actual': yesterday_actual,
        'weight_progress': weight_progress,
    }


def build_recommend_data(profile: str) -> dict:
    """自动算推荐:调 recommend_nutrition_goal 生成推荐值 → 注入 current_goal,用户微调后采纳

    返回与 live 相同契约(current_goal / yesterday_actual / weight_progress),
    current_goal 为推荐值(含 tdee/weekly_rate 等依据字段)。
    """
    from nutrition_goal import recommend_nutrition_goal

    profile_key = {'减脂': 'cut', '维持': 'maintain', '增肌': 'bulk'}.get(profile, profile)
    rec = recommend_nutrition_goal(profile=profile_key)
    current_goal = {
        'calorie_goal': rec['calorie_goal'],
        'protein_goal': rec['protein_goal'],
        'carbs_goal': rec['carbs_goal'],
        'fat_goal': rec['fat_goal'],
        'water_goal': rec['water_goal'],
    }
    data = build_live_data()
    data['current_goal'] = current_goal
    data['recommend'] = {
        'profile': rec['profile'],
        'profile_label': rec['profile_label'],
        'tdee': rec['tdee'],
        'bmr': rec['bmr'],
        'weekly_rate_kg': rec['weekly_rate_kg'],
        'basis': rec['basis'],
        'plan_reasons': rec['plan_reasons'],
        'missing': rec['missing'],
    }
    return data


def normalize(data: dict) -> dict:
    """标准化字段(防御性补全)"""
    if not isinstance(data, dict):
        return {'current_goal': {}, 'yesterday_actual': {}, 'weight_progress': None}
    return {
        'current_goal': data.get('current_goal', {}) if isinstance(data.get('current_goal'), dict) else {},
        'yesterday_actual': data.get('yesterday_actual', {}) if isinstance(data.get('yesterday_actual'), dict) else {},
        'weight_progress': data.get('weight_progress') if isinstance(data.get('weight_progress'), dict) else None,
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标配置已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    try:
        if args.mock:
            data = normalize(load_data(Path(args.mock)))
            label = Path(args.mock).stem
        elif args.recommend:
            data = normalize(build_recommend_data(args.recommend))
            label = f'recommend_{args.recommend}'
        else:
            data = normalize(build_live_data())
            label = 'live'
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'目标配置_{label}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    cg = data.get('current_goal', {})
    print(f'✅ {out_path}')
    print(f'   目标: 卡 {cg.get("calorie_goal", "?")} / 蛋白 {cg.get("protein_goal", "?")}g / 碳水 {cg.get("carbs_goal", "?")}g / 脂肪 {cg.get("fat_goal", "?")}g / 水 {cg.get("water_goal", "?")}ml')
    wp = data.get('weight_progress')
    if wp:
        print(f'   体重: 当前 {wp.get("current", "?")}kg → 目标 {wp.get("target", "?")}kg ({wp.get("days_left", "?")}天)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
