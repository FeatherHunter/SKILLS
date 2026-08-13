#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_weight.py — 体重目标 HTML 渲染器(体重型)

对应 SKILL.md 唤醒词: 定体重目标 / 定体重目标(自动算截止) / 定体重目标(含起始日) / 改体重目标
对应模板: templates/goal_weight.html
- 输出目录: $DATA_DIR/calorie_html/体重目标_<TS>.html
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- 呈现数据: 当前体重/目标值/截止/Δkg/建议速率(自动算截止含推算截止+速率校验,含起始日含起始日+起点体重)

用法:
    python scripts/render_goal_weight.py --mode basic              # 定体重目标(填写页)
    python scripts/render_goal_weight.py --mode auto_deadline     # 定体重目标(自动算截止)(填写页)
    python scripts/render_goal_weight.py --mode with_start        # 定体重目标(含起始日)(填写页)
    python scripts/render_goal_weight.py --mode modify            # 改体重目标(填写页)
    python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> [--start-kg] [--start-date] [--scene] --chain <思考链>  # 写库 + 结果回执(#79)
"""

from _base_render import render_template, write_html  # noqa: E402
import argparse
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_weight.html'
RESULT_TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_weight_result.html'
COMMAND_CN = "定体重目标"

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from weight_goal import get_weight_goal  # noqa: E402
from render_goal_common import build_meta, chain_valid, scene_path  # noqa: E402

# #78 2026-08-05:速率健康带(医学常识沿用代码库既有 0.25~1.0 kg/周),
# 极端目标判定阈值 = 上限 1.0 kg/周(issue 拍板 · 必须 > 1.0 的约束满足)
RATE_BAND_MIN = 0.25
RATE_BAND_MAX = 1.0
# V2 文案固定「健康带 0.25–1.0」(issue 验收原句,避免 1.00/1 这类格式噪音)
RATE_BAND_TEXT = '0.25–1.0'


def build_rate_info(gap_kg, days):
    """速率计算(纯函数 · #78 算式透明 + 极端判定)

    Args:
        gap_kg: 需减/增的体重差(带符号:正=需减,负=需增)
        days: 剩余天数(>0)

    Returns:
        dict: per_week / per_month / formula / ok / extreme / text;
        参数不足(无天数/天数<=0)返回 None
    """
    if gap_kg is None or not days or days <= 0:
        return None
    per_week = abs(gap_kg) / days * 7
    per_month = per_week * 52 / 12
    # 1e-9:消除 x/7x*7 = 0.9999999999999999 这类浮点噪声(V2 语义:>= 1.0 即警示)
    ok = RATE_BAND_MIN - 1e-9 <= per_week <= RATE_BAND_MAX + 1e-9
    extreme = per_week >= RATE_BAND_MAX - 1e-9
    formula = f'{abs(gap_kg):.1f}kg ÷ {days}天 × 7 = {per_week:.2f} kg/周 ≈ {per_month:.1f} kg/月'
    if extreme:
        verdict = f'⚠️ 这是极端目标,建议速率 {per_week:.2f} kg/周(健康带 {RATE_BAND_TEXT})'
    elif ok:
        verdict = f'✅ 速率合理 {per_week:.2f} kg/周(健康带 {RATE_BAND_TEXT})'
    else:
        verdict = f'ℹ️ 速率偏低 {per_week:.2f} kg/周(健康带 {RATE_BAND_TEXT},达成周期偏长)'
    return {
        'gap': round(abs(gap_kg), 1),
        'days': days,
        'per_week': round(per_week, 2),
        'per_month': round(per_month, 1),
        'formula': formula,
        'ok': ok,
        'extreme': extreme,
        'text': f'{verdict} · {formula}',
    }


def _days_until(deadline):
    """截止日 → 剩余天数(非法日期返回 None)"""
    if not deadline:
        return None
    try:
        dl = date.fromisoformat(deadline)
    except ValueError:
        return None
    return (dl - date.today()).days


def _latest_weight():
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    row = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1').fetchone()
    conn.close()
    return row[0] if row else None


def build_data(mode='basic'):
    current = _latest_weight()
    wg = get_weight_goal()
    current_goal = wg[0] if wg else None
    deadline = wg[1] if wg else None
    # #52 2026-08-04:起点体重/日期(设定时快照),回执页展示「起点行」
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    sw = conn.execute('SELECT start_weight, start_date FROM daily_goal WHERE id = 1').fetchone()
    conn.close()
    start_weight = sw[0] if sw and sw[0] is not None else None
    start_date = sw[1] if sw and sw[1] else None
    data = {
        'mode': mode,
        'current_weight': round(current, 1) if current else None,
        'target_weight': current_goal,
        'deadline': deadline,
        'start_weight': start_weight,
        'start_date': start_date,
    }

    if mode == 'basic':
        data['title'] = '定体重目标'
        data['subtitle'] = '目标 kg + 可选截止日期'
        if current is not None and current_goal:
            data['delta_kg'] = round(current - current_goal, 1)
            # #78 2026-08-05:速率用真实剩余天数(此前写死 90 天,用户给了截止日也算错)
            days = _days_until(deadline) or 90
            data['rate_check'] = build_rate_info(current - current_goal, days)
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'deadline', 'label': '截止日期', 'unit': '', 'placeholder': '如 2026-12-31(选填)'},
        ]
        data['extraPrompt'] = ('若我未提供目标或档案缺失,请先询问补齐;已明确则直接执行。\n'
                               '速率与数字一律采用页面预计算的「建议速率」行,禁止自行推算或编造数字。')

    elif mode == 'auto_deadline':
        data['title'] = '定体重目标(自动算截止)'
        data['subtitle'] = '目标 kg + 期望速率 → 自动推算截止日 + 速率校验'
        # 简单速率校验: 0.25~1.0 kg/周 为合理带
        data['rate_check'] = {'ok': True, 'text': '合理速率带 0.25~1.0 kg/周,超范围会提示'}
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'rate', 'label': '期望每周速率', 'unit': 'kg/周', 'placeholder': '如 0.5'},
        ]
        data['extraPrompt'] = ('请按我给的速率推算合理截止日,并校验速率是否在安全范围'
                               '(0.25~1.0 kg/周)。速率按页面预计算数字执行,禁止自行推算或编造。')

    elif mode == 'with_start':
        data['title'] = '定体重目标(含起始日)'
        data['subtitle'] = '完整 setup: 目标 + 起始日 + 截止日 + 起点体重'
        data['fields'] = [
            {'key': 'weight-goal', 'label': '目标体重', 'unit': 'kg', 'placeholder': '如 70'},
            {'key': 'start-date', 'label': '起始日', 'unit': '', 'placeholder': '如 2026-08-01'},
            {'key': 'deadline', 'label': '截止日期', 'unit': '', 'placeholder': '如 2026-12-31'},
            {'key': 'start-weight', 'label': '起点体重', 'unit': 'kg', 'placeholder': '如 75'},
        ]
        data['extraPrompt'] = ('请完整记录起始日与起点体重,作为目标起点。\n'
                               '速率与数字一律采用页面预计算的「建议速率」行,禁止自行推算或编造数字。')

    elif mode == 'modify':
        data['title'] = '改体重目标'
        data['subtitle'] = '改目标值或截止日,显示改前/改后 + 新建议速率'
        data['old_goal'] = {'weight_goal': current_goal, 'deadline': deadline}
        data['fields'] = [
            {'key': 'weight-goal', 'label': '新目标体重', 'unit': 'kg', 'placeholder': f'当前 {current_goal}' if current_goal else '如 70'},
            {'key': 'deadline', 'label': '新截止日期', 'unit': '', 'placeholder': f'当前 {deadline}' if deadline else '选填'},
        ]
        data['extraPrompt'] = '请显示改前/改后,并按新目标给出建议速率。速率按页面预计算数字执行,禁止自行推算或编造。'

    return data


def build_live_result(kg, deadline=None, start_kg=None, start_date=None):
    """定体重目标写库 + 结果回执(#79 · 输出侧闭环)

    - 写库:weight_goal.set_weight_goal(起点缺省 = 最新体重快照 / 今日)
    - 进度:差距 / 剩余天数 / 建议速率(公式透明 + 极端目标警示,#78)
    - 旅程:起点→目标 完成% + 按 0.5kg/周 推算达成日(对抗审查 2026-08-05 补)
    - 数字全部由代码计算,AI 只回显,禁止心算

    Returns:
        dict: written(落库字段)/ current_weight / gap / days_left / rate /
              journey(起点→目标进度)/ est_date(0.5kg/周 推算达成日)/ one_line
    """
    import weight_goal as wg
    written = wg.set_weight_goal(kg, deadline=deadline, start_weight=start_kg, start_date=start_date)
    current = _latest_weight()
    days_left = _days_until(deadline)
    gap = round(current - kg, 1) if current is not None else None
    rate = build_rate_info(current - kg, days_left) if gap is not None else None

    # 旅程进度:起点 → 目标,当前体重所处位置(完成%)
    journey = None
    start = written['start_weight']
    if start and written['weight_goal'] and current is not None:
        total = abs(start - written['weight_goal'])
        if total > 0:
            done = abs(start - current)
            pct = max(0.0, min(100.0, done / total * 100))
            journey = {
                'start': round(start, 1),
                'target': round(written['weight_goal'], 1),
                'current': round(current, 1),
                'pct': round(pct, 1),
                'done': round(min(done, total), 1),
                'total': round(total, 1),
            }

    # 按 0.5kg/周 推算达成日(与填写页同口径)
    est_date = None
    if gap and days_left is not None and days_left > 0:
        weeks = max(1, math.ceil(abs(gap) / 0.5))
        est_date = (date.today() + timedelta(days=weeks * 7)).isoformat()

    parts = [f"已写入体重目标 {kg:g}kg"]
    if deadline:
        parts.append(f"截止 {deadline}")
    if gap is not None:
        parts.append(f"差距 {abs(gap):.1f}kg")
    if days_left is not None:
        parts.append(f"剩余 {days_left} 天")
    if rate:
        parts.append(f"速率 {rate['per_week']:.2f} kg/周" + ('(⚠️ 极端目标)' if rate['extreme'] else ''))
    return {
        'written': {k: written[k] for k in ('weight_goal', 'deadline', 'start_weight', 'start_date', 'updated_at')},
        'current_weight': round(current, 1) if current else None,
        'gap': gap,
        'days_left': days_left,
        'rate': rate,
        'journey': journey,
        'est_date': est_date,
        'one_line': ' · '.join(parts),
    }


def render_html(data: dict):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def render_result_html(data: dict) -> str:
    """结果回执模板(goal_weight_result.html · #79)"""
    return render_template(RESULT_TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染体重目标 HTML(填写页 + 结果回执)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mode', choices=['basic', 'auto_deadline', 'with_start', 'modify'],
                   help='填写页模式(定体重目标 / 自动算截止 / 含起始日 / 改体重目标)')
    g.add_argument('--live', action='store_true', help='写库 + 结果回执(#79):AI 写库后渲染结果 HTML 回给用户')
    p.add_argument('--kg', type=float, help='目标体重(kg · --live 必填)')
    p.add_argument('--deadline', help='截止日期 YYYY-MM-DD(--live)')
    p.add_argument('--start-kg', type=float, help='起点体重 kg(--live · 缺省=最新体重快照)')
    p.add_argument('--start-date', help='起点日期 YYYY-MM-DD(--live · 缺省=今日)')
    p.add_argument('--scene', default='basic',
                   choices=['basic', 'auto_deadline', 'with_start', 'modify'],
                   help='原场景名(供回执自描述 · --live)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    # R3 思考链强制(live 模式必传)
    if not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读体重记录→3.校验速率"', file=sys.stderr)
        return 2

    # R4 自描述:场景名推断
    SCENE = {
        'basic': ('定体重目标', 'receipt'),
        'auto_deadline': ('定体重目标(自动算截止)', 'receipt'),
        'with_start': ('定体重目标(含起始日)', 'receipt'),
        'modify': ('改体重目标', 'receipt'),
    }
    SCENE_ID = {
        'basic': 'goal_set_weight',
        'auto_deadline': 'goal_set_weight_auto_deadline',
        'with_start': 'goal_set_weight_with_start',
        'modify': 'goal_modify_weight',
    }

    try:
        if args.live:
            if args.kg is None:
                print('❌ --live 需要 --kg <目标体重>', file=sys.stderr)
                return 1
            scene_name, _ = SCENE[args.scene]
            data = build_live_result(args.kg, deadline=args.deadline,
                                     start_kg=args.start_kg, start_date=args.start_date)
            # R1 视图分离:meta 不进 UI(复制日志带出)
            data['meta'] = build_meta(
                wake_word=scene_name,
                source='weight_log + daily_goal(weight_goal/goal_deadline/start_weight/start_date) · 写库回执',
                chain=args.chain,
                extra={'scene_id': SCENE_ID[args.scene]},
            )
            html = render_result_html(data)
            out_path = Path(args.output) if args.output else scene_path(scene_name, 'result')
        else:
            data = build_data(mode=args.mode)
            # R1 视图分离:meta 不进 UI(复制日志带出)
            data['meta'] = build_meta(
                wake_word=SCENE[args.mode][0],
                source='weight_log + daily_goal(weight_goal/goal_deadline)',
                chain=args.chain,
            )
            html = render_html(data)
            out_path = Path(args.output) if args.output else scene_path(SCENE[args.mode][0], 'receipt')
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    # R5 命名:<场景名>_<类型中文>_<TS>.html
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    if args.live:
        r = data.get('rate') or {}
        print(f'   已写入: 目标 {data["written"]["weight_goal"]}kg'
              + (f' · 截止 {data["written"]["deadline"]}' if data["written"]["deadline"] else ''))
        print(f'   进度: 差距 {data.get("gap")}kg · 剩余 {data.get("days_left")} 天'
              + (f' · 速率 {r.get("per_week")} kg/周' if r else ''))
        print(f'   {data.get("one_line")}')
        return 0
    print(f'   mode={args.mode} · 当前 {data.get("current_weight")} kg → 目标 {data.get("target_weight")} kg')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
