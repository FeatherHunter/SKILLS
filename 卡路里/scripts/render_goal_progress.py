#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_goal_progress.py — 目标进度 HTML 渲染器（G2 看目标 · 11 模式）

对应 SKILL.md 唤醒词: 看今日目标 / 看本周目标 / 看营养目标进度 / 看体重目标进度 / 看饮水目标进度 / 看目标对比实际 / 看目标完成度 / 看即将到期的目标 / 看目标完成率(按周) / 看目标完成率(按月) / 看目标历史完成 / 看目标预测达成
对应模板: templates/goal_progress.html
- 输出目录: $DATA_DIR/calorie_html/目标进度_<TS>.html (手册 §4.1 · 中文化)
- 占位符: <!--INJECT-DATA--> 恰好 1 次
- Apple 风: 系统字体 / 浅灰底 / 主色蓝 / 进度条 + 表格

模式:
  --mode today       看今日目标: 营养 4 项 + 饮水 5 项目标/实际/完成度
  --mode week        看本周目标: 日均 vs 日目标 + 周总量 vs 周目标
  --mode nutrition   看营养目标进度: 4 项进度条 + 完成度% + 缺口
  --mode water       看饮水目标进度: 累计/目标/完成度 + 剩余 ml
  --mode weight_progress  看体重目标进度: 当前/目标/Δ/完成%/预测 + 剩余天数/建议速率
  --mode vs_actual   看目标对比实际: 目标线 vs 实际线 + 偏差 + 时间窗口(默认 30 天)
  --mode completion  看目标完成度: 完成度% + 缺口 + 总评分
  --mode weight --expiring 14   看即将到期的目标: 目标/截止/剩余天数/进度/紧迫度
  --mode nutrition --period week|month   看目标完成率(按周/按月): 每日完成率柱状 + 达标天数
  --mode history     看目标历史完成: 每日达成列表 + 完成/未完成统计
  --mode predict     看目标预测达成: 预测达成日 + 置信度(体重部分复用 weight_milestone)

用法:
    python scripts/render_goal_progress.py --mode today
    python scripts/render_goal_progress.py --mode nutrition --period week
    python scripts/render_goal_progress.py --mode weight --expiring 14
    python scripts/render_goal_progress.py --mode weight_progress
    python scripts/render_goal_progress.py --mode history
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'goal_progress.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from nutrition_goal import get_nutrition_goal  # noqa: E402
import goal_history  # noqa: E402
from render_goal_common import build_meta, chain_valid, scene_path  # noqa: E402


def _get_goal_row():
    """读 daily_goal(id=1),返回 dict 或 None"""
    row = get_nutrition_goal()
    if row is None:
        return None
    return {
        'calorie_goal': row['calorie_goal'],
        'protein_goal': row['protein_goal'],
        'carbs_goal': row['carbs_goal'],
        'fat_goal': row['fat_goal'],
        'water_goal': row['water_goal'],
        'weight_goal': row['weight_goal'],
        'goal_deadline': row['goal_deadline'],
    }


def _today_actual(target_date=None):
    """今日 food_log 实际聚合(卡/蛋白/碳水/脂肪/饮水 ml)"""
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    d = target_date or date.today().isoformat()
    row = conn.execute('''
        SELECT COALESCE(SUM(calories),0), COALESCE(SUM(protein),0),
               COALESCE(SUM(carbs),0), COALESCE(SUM(fat),0)
        FROM food_log WHERE date = ?
    ''', (d,)).fetchone()
    wrow = conn.execute(
        "SELECT COALESCE(SUM(grams),0) FROM food_log WHERE date = ? AND food_name = '💧水'",
        (d,),
    ).fetchone()
    conn.close()
    return {'calorie': row[0], 'protein': row[1], 'carbs': row[2], 'fat': row[3], 'water': wrow[0]}


def _pct(actual, goal):
    return round(actual / goal * 100, 1) if goal else None


def _items_from_actual(actual, goal, keys, labels, units):
    """组装通用 items 列表(actual 取整,避免浮点噪声 · R7/R6)"""
    items = []
    for k, label, unit in zip(keys, labels, units):
        g = goal.get(f'{k}_goal')
        a = actual.get(k, 0)
        items.append({'label': label, 'unit': unit, 'goal': g, 'actual': round(a, 1), 'pct': _pct(a, g)})
    return items


def build_mode_today(goal):
    actual = _today_actual()
    items = _items_from_actual(
        actual, goal,
        ['calorie', 'protein', 'carbs', 'fat', 'water'],
        ['热量', '蛋白', '碳水', '脂肪', '饮水'],
        ['卡', 'g', 'g', 'g', 'ml'],
    )
    # R7 信息唯一性:summary 只给一句话建议,不重复进度条数值
    pcts = [(it['label'], it['pct']) for it in items if it['pct'] is not None]
    if not pcts:
        summary = '未设营养目标'
    else:
        low = min(pcts, key=lambda x: x[1])
        high = max(pcts, key=lambda x: x[1])
        summary = f'完成最好的是{high[0]}({high[1]}%),最需补的是{low[0]}({low[1]}%)'
    return {
        'mode': 'today',
        'title': '看今日目标',
        'subtitle': '营养 4 项 + 饮水 · 目标值/实际/完成度（体重为累计目标,看体重目标进度）',
        'items': items,
        'summary': summary,
    }


def build_mode_week(goal):
    """本周(本周一~今天)累计 vs 目标"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range((today - monday).days + 1)]
    total = {'calorie': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'water': 0}
    for d in days:
        a = _today_actual(d.isoformat())
        for k in total:
            total[k] += a[k]
    n = len(days)
    avg = {k: round(v / n, 1) for k, v in total.items()}

    items = []
    for k, label, unit in zip(
        ['calorie', 'protein', 'carbs', 'fat', 'water'],
        ['热量', '蛋白', '碳水', '脂肪', '饮水'],
        ['卡', 'g', 'g', 'g', 'ml'],
    ):
        g = goal.get(f'{k}_goal')
        items.append({
            'label': f'{label}(日均)', 'unit': unit,
            'goal': g, 'actual': avg[k], 'pct': _pct(avg[k], g),
        })
    week_goal = goal.get('calorie_goal')
    return {
        'mode': 'week',
        'title': '看本周目标',
        'subtitle': f'{monday.isoformat()} ~ {today.isoformat()} · 共 {n} 天',
        'kpis': [
            {'label': '周总量', 'value': total['calorie'], 'unit': '卡'},
            {'label': '周目标', 'value': week_goal * 7 if week_goal else '—', 'unit': '卡'},
            {'label': '日均', 'value': avg['calorie'], 'unit': '卡'},
            {'label': '日均目标', 'value': week_goal if week_goal else '—', 'unit': '卡'},
        ],
        'items': items,
        'summary': f'本周日均热量 {avg["calorie"]} 卡' + (f' · 周目标 {week_goal * 7} 卡' if week_goal else ''),
    }


def build_mode_nutrition(goal, period=None):
    """看营养目标进度(今日) / 看目标完成率(period=week|month)"""
    if period:
        days = 7 if period == 'week' else 30
        hist = goal_history.list_completed_goals(days)
        rows = []
        for h in hist['goal_history']:
            pct = h['pct'] or 0
            rows.append({
                'date': h['date'],
                'calorie_actual': h['calorie_actual'],
                'calorie_goal': h['calorie_goal'] or '—',
                'rate': {'bar': min(pct, 150), 'text': f'{pct}%'},
                'status': {'badge': 'ok' if h['status'] == '完成' else ('bad' if h['status'] == '未完成' else 'neutral'), 'text': h['status']},
            })
        return {
            'mode': 'nutrition_period',
            'title': f'看目标完成率(按{ {"week":"周","month":"月"}[period] })',
            'subtitle': f'近 {days} 天每日热量达成率 · 达标带 80%-120%',
            'kpis': [
                {'label': '达标天数', 'value': hist['completed_count'], 'unit': f'/{days} 天'},
                {'label': '未达标', 'value': hist['incomplete_count'], 'unit': '天'},
            ],
            'table': {
                'title': '每日完成率',
                'hint': '绿色=达标 80-120%',
                'cols': [
                    {'key': 'date', 'label': '日期'},
                    {'key': 'calorie_actual', 'label': '实际'},
                    {'key': 'calorie_goal', 'label': '目标'},
                    {'key': 'rate', 'label': '达成率'},
                    {'key': 'status', 'label': '状态'},
                ],
                'rows': rows,
            },
            'summary': f'达标 {hist["completed_count"]} 天 / 未达标 {hist["incomplete_count"]} 天',
        }

    actual = _today_actual()
    items = _items_from_actual(
        actual, goal,
        ['calorie', 'protein', 'carbs', 'fat'],
        ['热量', '蛋白', '碳水', '脂肪'],
        ['卡', 'g', 'g', 'g'],
    )
    for it in items:
        g = it['goal']
        it['gap'] = (g - it['actual']) if g else None
    if items:
        with_gap = [it for it in items if it.get('gap') is not None and it.get('goal')]
        if with_gap:
            worst = max(with_gap, key=lambda it: abs(it['gap']))
            verb = '刚好达标' if worst['gap'] == 0 else ('还差' if worst['gap'] > 0 else '已超')
            summary = f"差距最大: {worst['label']} {verb} {abs(worst['gap'])} {worst['unit']}"
        else:
            summary = '未设营养目标'
    else:
        summary = '未设营养目标'
    return {
        'mode': 'nutrition',
        'title': '看营养目标进度',
        'subtitle': '4 项宏量进度条 + 完成度% + 缺口',
        'items': items,
        'summary': summary,
    }


def build_mode_water(goal):
    actual = _today_actual()
    g = goal.get('water_goal')
    a = actual['water']
    remaining = (g - a) if g else None
    return {
        'mode': 'water',
        'title': '看饮水目标进度',
        'subtitle': '今日饮水累计/目标/完成度',
        'kpis': [
            {'label': '累计', 'value': a, 'unit': 'ml'},
            {'label': '目标', 'value': g or '—', 'unit': 'ml'},
            {'label': '剩余', 'value': remaining if remaining is not None else '—', 'unit': 'ml'},
        ],
        'items': [{'label': '饮水', 'unit': 'ml', 'goal': g, 'actual': a, 'pct': _pct(a, g)}],
        'summary': f'剩余 {remaining} ml' if remaining is not None else '未设饮水目标',
    }


def build_mode_vs_actual(goal, days=30):
    """目标线 vs 实际线(近 N 天每日热量)+ 偏差"""
    today = date.today()
    start = today - timedelta(days=days - 1)
    g = goal.get('calorie_goal')
    rows = []
    deviations = []
    for i in range(days):
        d = (start + timedelta(days=i)).isoformat()
        if d > today.isoformat():
            break
        a = _today_actual(d)
        pct = _pct(a['calorie'], g)
        rows.append({
            'date': d,
            'actual': round(a['calorie'], 1),
            'goal': g or '—',
            'deviation': {'bar': min(pct, 150) if pct is not None else 0, 'text': f'{pct}%' if pct is not None else '—'},
        })
        if pct is not None:
            deviations.append(pct - 100)
    avg_dev = round(sum(deviations) / len(deviations), 1) if deviations else None
    return {
        'mode': 'vs_actual',
        'title': '看目标对比实际',
        'subtitle': f'目标线 vs 实际线 · 近 {days} 天(默认 30 天可自定义)',
        'kpis': [
            {'label': '平均偏差', 'value': f'{avg_dev:+.1f}' if avg_dev is not None else '—', 'unit': '%'},
            {'label': '目标', 'value': g or '—', 'unit': '卡/天'},
        ],
        'table': {
            'title': '每日目标 vs 实际',
            'hint': '偏差 = 实际/目标',
            'cols': [
                {'key': 'date', 'label': '日期'},
                {'key': 'actual', 'label': '实际'},
                {'key': 'goal', 'label': '目标'},
                {'key': 'deviation', 'label': '偏差'},
            ],
            'rows': rows,
        },
        'summary': f'平均偏差 {avg_dev:+.1f}%' if avg_dev is not None else '未设热量目标',
    }


def build_mode_completion(goal):
    actual = _today_actual()
    items = _items_from_actual(
        actual, goal,
        ['calorie', 'protein', 'carbs', 'fat', 'water'],
        ['热量', '蛋白', '碳水', '脂肪', '饮水'],
        ['卡', 'g', 'g', 'g', 'ml'],
    )
    for it in items:
        g = it['goal']
        it['gap'] = (g - it['actual']) if g else None
    pcts = [it['pct'] for it in items if it['pct'] is not None]
    total_score = round(sum(pcts) / len(pcts), 1) if pcts else None
    return {
        'mode': 'completion',
        'title': '看目标完成度（含缺口）',
        'subtitle': '5 项完成度% + 缺口绝对值 + 总评分',
        'kpis': [{'label': '总评分', 'value': total_score if total_score is not None else '—', 'unit': '%'}],
        'items': items,
        'summary': f'总评分 {total_score}%' if total_score is not None else '未设目标',
    }


def build_mode_weight(goal, expiring=14):
    """看即将到期的目标(体重目标截止日 <= expiring 天)"""
    from weight_goal import get_weight_goal
    result = get_weight_goal()
    if not result or result[0] is None:
        return {
            'mode': 'weight',
            'title': '看即将到期的目标',
            'subtitle': f'截止 {expiring} 天内的目标',
            'empty': '未设定体重目标',
            'summary': '说「定体重目标」先设一个目标',
        }
    weight_goal_val, deadline, days_left, _, calorie_adj = result
    if not deadline or days_left is None or days_left > expiring:
        return {
            'mode': 'weight',
            'title': '看即将到期的目标',
            'subtitle': f'截止 {expiring} 天内的目标',
            'empty': f'当前体重目标 {weight_goal_val} kg 截止 {deadline or "未设"} · {days_left or "?"} 天,不在 {expiring} 天紧迫窗口内',
            'summary': '无即将到期的目标',
        }
    # 进度: 当前体重 vs 目标
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    cur = conn.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1').fetchone()
    conn.close()
    current = cur[0] if cur else None
    urgency = '高' if days_left <= 3 else ('中' if days_left <= 7 else '低')
    return {
        'mode': 'weight',
        'title': '看即将到期的目标',
        'subtitle': f'截止 {expiring} 天内的体重目标',
        'kpis': [
            {'label': '目标', 'value': weight_goal_val, 'unit': 'kg'},
            {'label': '截止', 'value': deadline, 'unit': ''},
            {'label': '剩余', 'value': days_left, 'unit': '天'},
            {'label': '紧迫度', 'value': urgency, 'unit': ''},
        ],
        'table': {
            'title': '即将到期',
            'hint': '紧迫度: ≤3 天高 / ≤7 天中 / 其余低',
            'cols': [
                {'key': 'weight_goal', 'label': '目标'},
                {'key': 'deadline', 'label': '截止'},
                {'key': 'days_left', 'label': '剩余'},
                {'key': 'current', 'label': '当前'},
                {'key': 'urgency', 'label': '紧迫度'},
            ],
            'rows': [{
                'weight_goal': f'{weight_goal_val} kg',
                'deadline': deadline,
                'days_left': f'{days_left} 天',
                'current': f'{current} kg' if current else '—',
                'urgency': {'badge': 'bad' if days_left <= 3 else ('warn' if days_left <= 7 else 'ok'), 'text': urgency},
            }],
        },
        'summary': f'{days_left} 天后到期 · 当前 {current} kg → 目标 {weight_goal_val} kg',
    }


def build_mode_predict(goal):
    """看目标预测达成: 体重部分复用 weight_milestone(est_date), 置信度按数据量"""
    from analysis.weight import weight_milestone
    ms = weight_milestone(as_dict=True)
    if ms.get('status') != 'ok' or not ms.get('data'):
        return {
            'mode': 'predict',
            'title': '看目标预测达成',
            'subtitle': '按当前趋势预测目标达成日 + 置信度',
            'empty': ms.get('message', '数据不足,无法预测'),
            'summary': '先设体重目标并记录体重,才能预测',
        }
    d = ms['data']
    confidence = '低'
    if d.get('actual_daily_change_kg'):
        confidence = '高' if abs(d['actual_daily_change_kg']) > 0.02 else '中'
    return {
        'mode': 'predict',
        'title': '看目标预测达成',
        'subtitle': '按当前趋势(近 30 天日均变化)预测',
        'kpis': [
            {'label': '当前', 'value': d['current_weight'], 'unit': 'kg'},
            {'label': '目标', 'value': d['weight_goal'], 'unit': 'kg'},
            {'label': '预测达成', 'value': d.get('est_date') or '—', 'unit': ''},
            {'label': '置信度', 'value': confidence, 'unit': ''},
        ],
        'items': [{
            'label': '日均变化', 'unit': 'kg/天',
            'goal': None, 'actual': d.get('actual_daily_change_kg') or 0,
            'pct': None,
        }],
        'summary': f"预计 {d.get('est_date') or '—'} 达成 · 置信度 {confidence} · 状态 {d.get('status')}",
    }


def build_mode_weight_progress(goal):
    """看体重目标进度: 当前/目标/Δ/完成%/预测 + 剩余天数/建议速率(weight_milestone)"""
    from analysis.weight import weight_milestone
    ms = weight_milestone(as_dict=True)
    if ms.get('status') != 'ok' or not ms.get('data'):
        return {
            'mode': 'weight_progress',
            'title': '看体重目标进度',
            'subtitle': '当前/目标/Δ/完成%/预测 + 剩余天数/建议速率',
            'empty': ms.get('message', '数据不足'),
            'summary': '先设体重目标并记录体重',
        }
    d = ms['data']
    # 完成% = 已减 / 总需减(起点 = 最早一次体重)
    from db import find_db_path, get_db
    db_path = find_db_path(SKILL_DIR, 'calorie_data.db')
    conn = get_db(db_path)
    start = conn.execute('SELECT weight_kg FROM weight_log ORDER BY date ASC LIMIT 1').fetchone()
    conn.close()
    pct = None
    if start and d['weight_goal'] is not None and d['current_weight'] is not None:
        total = start[0] - d['weight_goal']
        done = start[0] - d['current_weight']
        if total != 0:
            pct = round(done / total * 100, 1)
    rate = d.get('calorie_adjustment')
    rate_text = None
    if rate is not None:
        rate_text = f"{abs(rate)} 卡/天{'缺口' if rate > 0 else '盈余'}"
    return {
        'mode': 'weight_progress',
        'title': '看体重目标进度',
        'subtitle': '当前/目标/Δ/完成%/预测 + 剩余天数/建议速率',
        'kpis': [
            {'label': '当前', 'value': d['current_weight'], 'unit': 'kg'},
            {'label': '目标', 'value': d['weight_goal'], 'unit': 'kg'},
            {'label': '差距', 'value': f"{d['gap_kg']:+.1f}", 'unit': 'kg'},
            {'label': '完成', 'value': pct if pct is not None else '—', 'unit': '%'},
        ],
        'itemsTitle': '预测与建议',
        'itemsHint': '按当前趋势推算',
        'items': [
            {'label': '剩余天数', 'unit': '', 'goal': None, 'actual': d.get('est_days'), 'pct': None},
            {'label': '预计达成', 'unit': '', 'goal': None, 'actual': d.get('est_date'), 'pct': None},
            {'label': '建议速率', 'unit': '', 'goal': None, 'actual': rate_text, 'pct': None},
        ],
        'summary': f"预计 {d.get('est_date') or '—'} 达成 · 状态 {d.get('status')}"
                   + (f' · {rate_text}' if rate_text else ''),
    }


def build_mode_history(goal, days=30):
    """看目标历史完成: 每日达成列表 + 完成/未完成统计"""
    hist = goal_history.list_completed_goals(days)
    rows = []
    for h in hist['goal_history']:
        pct = h['pct'] or 0
        rows.append({
            'date': h['date'],
            'calorie_actual': h['calorie_actual'],
            'calorie_goal': h['calorie_goal'] or '—',
            'rate': {'bar': min(pct, 150), 'text': f'{pct}%'},
            'status': {'badge': 'ok' if h['status'] == '完成' else ('bad' if h['status'] == '未完成' else 'neutral'),
                       'text': h['status']},
        })
    return {
        'mode': 'history',
        'title': '看目标历史完成',
        'subtitle': f'近 {days} 天每日达成列表 · 达标带 80%-120%',
        'kpis': [
            {'label': '完成', 'value': hist['completed_count'], 'unit': f'/{days} 天'},
            {'label': '未完成', 'value': hist['incomplete_count'], 'unit': '天'},
        ],
        'table': {
            'title': '每日达成',
            'hint': '绿色=达标 80-120%',
            'cols': [
                {'key': 'date', 'label': '日期'},
                {'key': 'calorie_actual', 'label': '实际'},
                {'key': 'calorie_goal', 'label': '目标'},
                {'key': 'rate', 'label': '达成率'},
                {'key': 'status', 'label': '状态'},
            ],
            'rows': rows,
        },
        'summary': f'完成 {hist["completed_count"]} 天 / 未完成 {hist["incomplete_count"]} 天',
    }


def render_html(data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')
    payload = json.dumps({'status': 'ok', 'data': data, 'message': '目标进度已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染目标进度 HTML(G2 看目标 · 11 模式)')
    p.add_argument('--mode', required=True,
                   choices=['today', 'week', 'nutrition', 'water', 'vs_actual',
                            'completion', 'weight', 'weight_progress', 'history', 'predict'],
                   help='查看模式')
    p.add_argument('--period', choices=['week', 'month'], help='nutrition 模式周期(完成率)')
    p.add_argument('--expiring', type=int, default=14, help='weight 模式紧迫窗口天数(默认 14)')
    p.add_argument('--days', type=int, default=30, help='vs_actual 时间窗口天数(默认 30)')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则:未传=AI 未按 SKILL.md 流程执行 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    # R3 思考链强制(live 模式必传)
    if not chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        print('   未传 = AI 未按 SKILL.md 流程执行,行为不可控。', file=sys.stderr)
        print('   请传入你的实际处理步骤,例如:', file=sys.stderr)
        print('     --chain "1.识别唤醒词→2.读目标与记录→3.计算完成度"', file=sys.stderr)
        return 2

    # R4 自描述:场景名推断(mode → 场景名/类型)
    SCENE = {
        'today': ('看今日目标', 'result'),
        'week': ('看本周目标', 'result'),
        'nutrition': ('看营养目标进度', 'result'),
        'water': ('看饮水目标进度', 'result'),
        'vs_actual': ('看目标对比实际', 'result'),
        'completion': ('看目标完成度', 'result'),
        'weight': ('看即将到期的目标', 'result'),
        'weight_progress': ('看体重目标进度', 'result'),
        'history': ('看目标历史完成', 'result'),
        'predict': ('看目标预测达成', 'result'),
    }
    scene_name, output_type = SCENE[args.mode]
    if args.mode == 'nutrition' and args.period:
        scene_name = '看目标完成率(按周)' if args.period == 'week' else '看目标完成率(按月)'

    goal = _get_goal_row() or {}
    try:
        if args.mode == 'today':
            data = build_mode_today(goal)
        elif args.mode == 'week':
            data = build_mode_week(goal)
        elif args.mode == 'nutrition':
            data = build_mode_nutrition(goal, period=args.period)
        elif args.mode == 'water':
            data = build_mode_water(goal)
        elif args.mode == 'vs_actual':
            data = build_mode_vs_actual(goal, days=args.days)
        elif args.mode == 'completion':
            data = build_mode_completion(goal)
        elif args.mode == 'weight':
            data = build_mode_weight(goal, expiring=args.expiring)
        elif args.mode == 'weight_progress':
            data = build_mode_weight_progress(goal)
        elif args.mode == 'history':
            data = build_mode_history(goal, days=args.days)
        elif args.mode == 'predict':
            data = build_mode_predict(goal)
        # R1 视图分离:meta 不进 UI(复制日志带出)
        data['meta'] = build_meta(
            wake_word=scene_name,
            source='daily_goal + food_log/exercise_log/weight_log 聚合',
            chain=args.chain,
            extra={'mode': args.mode,
                   'period': args.period if args.period else None,
                   'days': args.days if args.mode in ('vs_actual', 'history') else None,
                   'expiring': args.expiring if args.mode == 'weight' else None},
        )
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    # R5 命名:<场景名>_<类型中文>_<TS>.html
    out_path = Path(args.output) if args.output else scene_path(scene_name, output_type)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   mode={args.mode}' + (f' period={args.period}' if args.period else '')
          + (f' expiring={args.expiring}' if args.mode == 'weight' else '')
          + (f' days={args.days}' if args.mode == 'vs_actual' else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
