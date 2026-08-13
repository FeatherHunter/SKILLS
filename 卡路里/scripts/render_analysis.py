#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_analysis.py — 分析 154 场景统一渲染器(ticket #10)

服务:分析分类 154 个场景(A1-A6 + 单点;唤醒词见 SKILL.md frontmatter / _triggers.py category='分析')

7 视图:
  --view combined    A1 组合分析 + A5 宏量交叉   模板 combined_analysis.html
  --view nutrition   A5 钠糖纤维趋势/综合/营养建议 模板 nutrition_analysis.html
  --view report      A2 健康报告 19              模板 health_report.html
  --view trend       A3 整体趋势 15              模板 long_trend.html
  --view anomaly     A4 自动分析 23              模板 anomaly_report.html
  --view predict     A6 预测模拟 20              模板 predict_report.html
  --view six         单点·看每日 6 因素综合       模板 six_factors.html

用法示例:
  python scripts/render_analysis.py --view combined --pair weight_calorie --window 7d
  python scripts/render_analysis.py --view report --kind full --window 本周
  python scripts/render_analysis.py --view trend --group g1 --window 90d
  python scripts/render_analysis.py --view anomaly --diagnose weight_plateau --window 30d
  python scripts/render_analysis.py --view predict --kind weight_forecast --days 30
  python scripts/render_analysis.py --view six --date 2026-08-02
  python scripts/render_analysis.py --view combined --pair weight_calorie --window custom --start 2026-07-01 --end 2026-07-31
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from _base_render import render_template, write_html  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from html_paths import html_scene_path              # noqa: E402
from analysis._utils import _get_db, get_activity_factor  # noqa: E402
from analysis.series import (build_series, resolve_window, series_avg, series_count,  # noqa: E402
                             series_delta, series_sum)
from analysis.cross import analyze_pair, PAIRS      # noqa: E402
from analysis.anomaly import diagnose               # noqa: E402
from analysis import simulate as sim                # noqa: E402

TEMPLATES = {
    'combined':   'templates/combined_analysis.html',
    'nutrition':  'templates/nutrition_analysis.html',
    'report':     'templates/health_report.html',
    'trend':      'templates/long_trend.html',
    'anomaly':    'templates/anomaly_report.html',
    'predict':    'templates/predict_report.html',
    'six':        'templates/six_factors.html',
}

# A3 多指标组 → (字段表, 显示名)
TREND_GROUPS: dict[str, tuple[list[tuple[str, str]], str]] = {
    'g1':  ([('weight_kg', '体重'), ('calories', '摄入'), ('exercise_kcal', '运动')], '体重+摄入+运动'),
    'g2':  ([('weight_kg', '体重'), ('body_fat_pct', '体脂'), ('waist_cm', '腰围')], '体重+体脂+围度'),
    'g3':  ([('calories', '摄入'), ('protein', '蛋白'), ('fiber_g', '纤维')], '饮食+蛋白+纤维'),
    'g4':  ([('exercise_kcal', '运动'), ('strength_kcal', '力量'), ('cardio_kcal', '有氧')], '运动+力量+有氧'),
    'g5':  ([('bmi', 'BMI'), ('body_fat_pct', '体脂'), ('muscle_mass', '肌肉量')], 'BMI+体脂+肌肉量'),
    'g6':  ([('calories', '摄入'), ('protein', '蛋白'), ('exercise_kcal', '运动')], '摄入+蛋白+运动'),
    'g7':  ([('weight_kg', '体重'), ('protein', '蛋白'), ('deficit', '缺口')], '体重+蛋白+缺口'),
    'g8':  ([('weight_kg', '体重'), ('calories', '摄入'), ('deficit', '缺口')], '体重+摄入+缺口'),
    'g9':  ([('weight_kg', '体重'), ('calories', '摄入'), ('exercise_kcal', '运动'), ('deficit', '缺口')], '体重+摄入+运动+缺口'),
    'g10': ([('protein', '蛋白'), ('exercise_kcal', '运动')], '蛋白+运动'),
    'g11': ([('calories', '摄入'), ('protein', '蛋白'), ('exercise_kcal', '运动'),
             ('water_ml', '饮水'), ('weight_kg', '体重'), ('deficit', '缺口')], '综合多指标'),
}

A2_REF = {'bmi_ref': ((18.5, 24.9), 'BMI 健康范围 18.5-24.9'),
          'fiber_ref': (25, 30), 'sodium_ref': 2000, 'sugar_ref': 50}


# ---------- 工具 ----------

def _render(template_name: str, data: dict, scene_name: str = "") -> str:
    return render_template(SKILL_DIR / template_name, data, scene_name or None)


def _out(data: dict, view: str, scene_name: str) -> int:
    """渲染 + 落盘 + 输出 SEND_TO_USER 末行"""
    html = _render(TEMPLATES[view], data, scene_name)
    out_path = html_scene_path(SKILL_DIR, scene_name, 'result')
    write_html(html, out_path)
    print(f"✅ 已生成: {out_path}")
    print(f"   场景: {scene_name} | 窗口: {data.get('window', '')}")
    print(f"   洞察: {data.get('insight', '')[:80]}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


# ---------- A1/A5 组合 ----------

def view_combined(args) -> dict:
    start, end = resolve_window(args.window, args.start, args.end)
    series = build_series(start, end)
    if args.pair not in PAIRS:
        raise ValueError(f'未知配对 {args.pair}')
    return analyze_pair(series, args.pair, args.window)


# ---------- A5 营养 ----------

def _nutrition_nutrients(series: list[dict]) -> dict:
    """钠/糖/纤维 3 营养素汇总(参考值:纤维 25-30g / 钠 ≤2000mg / 糖 ≤50g)"""
    def _stat(field):
        vals = [s[field] for s in series if s.get(field) is not None]
        if not vals:
            return {'avg': None, 'days': 0, 'rate': None}
        avg = sum(vals) / len(vals)
        if field == 'fiber_g':
            ok = sum(1 for v in vals if 25 <= v <= 30)
        else:
            ok = sum(1 for v in vals if v <= (A2_REF['sodium_ref'] if field == 'sodium_mg' else A2_REF['sugar_ref']))
        return {'avg': round(avg, 1), 'days': len(vals),
                'rate': round(ok / len(vals) * 100, 1)}
    return {
        'sodium': _stat('sodium_mg'),
        'sugar':  _stat('sugar_g'),
        'fiber':  _stat('fiber_g'),
        'refs':   {'fiber': '25-30 g/天', 'sodium': '≤2000 mg/天', 'sugar': '≤50 g/天'},
        'series': [{'date': s['date'], 'sodium_mg': s['sodium_mg'],
                    'sugar_g': s['sugar_g'], 'fiber_g': s['fiber_g']} for s in series],
    }


def view_nutrition(args) -> dict:
    start, end = resolve_window(args.window, args.start, args.end)
    series = build_series(start, end)
    if args.group == 'macro3':
        # 三大营养交叉:占比 + 平衡度
        p = series_avg(series, 'protein') or 0
        c = series_avg(series, 'carbs') or 0
        f = series_avg(series, 'fat') or 0
        total = p * 4 + c * 4 + f * 9
        shares = {'protein': round(p * 4 / total * 100, 1),
                  'carbs': round(c * 4 / total * 100, 1),
                  'fat': round(f * 9 / total * 100, 1)} if total > 0 else {}
        off = [k for k in shares
               if not ({'protein': (15, 30), 'carbs': (40, 60), 'fat': (20, 35)}[k][0]
                       <= shares[k] <= {'protein': (15, 30), 'carbs': (40, 60), 'fat': (20, 35)}[k][1])]
        return {
            'view': 'nutrition', 'group': 'macro3', 'window': args.window,
            'start': start, 'end': end, 'days': len(series),
            'shares': shares, 'balanced': not off, 'off_dims': off,
            'series': [{'date': s['date'], 'protein': s['protein'],
                        'carbs': s['carbs'], 'fat': s['fat']} for s in series],
            'insight': ('三大营养占比均衡:蛋白 {}% / 碳水 {}% / 脂肪 {}%。'.format(
                shares.get('protein', '-'), shares.get('carbs', '-'), shares.get('fat', '-'))
                if not off else '占比失衡维度:' + '、'.join(off) + ',建议针对性调整。'),
        }
    if args.group == 'sodium_fiber':
        nuts = _nutrition_nutrients(series)
        return {
            'view': 'nutrition', 'group': 'sodium_fiber', 'window': args.window,
            'start': start, 'end': end, 'days': len(series), **nuts,
            'insight': '钠/糖/纤维趋势:日均钠 {}mg、糖 {}g、纤维 {}g(参考 钠≤2000mg 糖≤50g 纤维25-30g)。'.format(
                nuts['sodium']['avg'] or '-', nuts['sugar']['avg'] or '-', nuts['fiber']['avg'] or '-'),
        }
    if args.group == 'sodium_combined':
        nuts = _nutrition_nutrients(series)
        # 最大缺口:达标率最低者
        rates = {'钠': nuts['sodium']['rate'], '糖': nuts['sugar']['rate'],
                 '纤维': nuts['fiber']['rate']}
        worst = min(rates, key=lambda k: rates[k] if rates[k] is not None else 999)
        return {
            'view': 'nutrition', 'group': 'sodium_combined', 'window': args.window,
            'start': start, 'end': end, 'days': len(series), **nuts,
            'worst': worst,
            'insight': f'钠/糖/纤维综合:最需改进的是「{worst}」(达标率 {rates[worst]}%)。',
        }
    if args.group == 'advice':
        # 营养建议:各维度当前值 vs 参考 → 缺口 → 行动 + 优先级
        nuts = _nutrition_nutrients(series)
        weight = None
        for s in reversed(series):
            if s.get('weight_kg') is not None:
                weight = s['weight_kg']
                break
        protein_avg = series_avg(series, 'protein') or 0
        protein_target = round((weight or 70) * 1.2, 1)
        items = []
        items.append({
            'dim': '蛋白', 'current': f'{protein_avg} g/天',
            'target': f'≥{protein_target} g(体重 × 1.2)',
            'gap': '不足' if protein_avg < protein_target else '达标',
            'action': '每餐加一掌心蛋白:鸡蛋/鸡胸/豆制品/牛奶', 'priority': 1})
        items.append({
            'dim': '纤维', 'current': f'{nuts["fiber"]["avg"] or "-"} g/天',
            'target': '25-30 g/天', 'gap': '不足' if (nuts['fiber']['avg'] or 0) < 25 else '达标',
            'action': '主食换成全谷物/杂豆,每天 500g 蔬菜', 'priority': 2})
        items.append({
            'dim': '钠', 'current': f'{nuts["sodium"]["avg"] or "-"} mg/天',
            'target': '≤2000 mg/天', 'gap': '超标' if (nuts['sodium']['avg'] or 0) > 2000 else '达标',
            'action': '减盐:少外食火锅/卤味,酱油蘸料减半', 'priority': 3})
        items.append({
            'dim': '糖', 'current': f'{nuts["sugar"]["avg"] or "-"} g/天',
            'target': '≤50 g/天', 'gap': '超标' if (nuts['sugar']['avg'] or 0) > 50 else '达标',
            'action': '含糖饮料换成无糖/气泡水,水果一天 1-2 份', 'priority': 4})
        return {
            'view': 'nutrition', 'group': 'advice', 'window': args.window,
            'start': start, 'end': end, 'days': len(series), 'items': items,
            'insight': '优先处理高优先级缺口:' + '、'.join(i['dim'] for i in items if i['gap'] != '达标') + '。'
                       if any(i['gap'] != '达标' for i in items) else '各营养维度均达标,保持。',
        }
    raise ValueError(f'未知 nutrition 组 {args.group}')


# ---------- A2 健康报告 ----------

def _bmi_data(series: list[dict]) -> dict:
    conn = _get_db()
    try:
        prof = conn.execute(
            "SELECT height_cm FROM user_profile WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
    height = (prof[0] if prof else None) or 170
    vals = [{'date': s['date'], 'bmi': round(s['weight_kg'] / ((height / 100) ** 2), 1)}
            for s in series if s.get('weight_kg') is not None]
    current = vals[-1]['bmi'] if vals else None
    def _cat(b):
        if b is None:
            return '—'
        if b < 18.5:
            return '偏瘦'
        if b < 24.9:
            return '正常'
        if b < 28:
            return '超重'
        return '肥胖'
    milestones = []
    prev = None
    for v in vals:
        c = _cat(v['bmi'])
        if prev is not None and c != prev:
            milestones.append({'date': v['date'], 'from': prev, 'to': c})
        prev = c
    return {'height': height, 'current': current, 'category': _cat(current),
            'history': vals, 'milestones': milestones[-3:],
            'insight': f'当前 BMI {current}({_cat(current)}),历史 {len(vals)} 个采样点。'
                       + (f';最近里程碑:{milestones[-1]["date"]} {milestones[-1]["from"]}→{milestones[-1]["to"]}'
                          if milestones else '')}


def _score(series: list[dict]) -> dict:
    """0-100 综合评分(饮食/运动/体重/饮水/体脂/围度 6 项)"""
    goal = series[0].get('calorie_goal') or 1800
    cal = [s['calories'] for s in series if s.get('calories') is not None]
    diet = 100 - min(50, (abs((sum(cal) / len(cal)) - goal) / goal * 100) / 2) if cal else 50
    ex_days = series_count(series, 'exercise_kcal')
    ex = min(100, ex_days / max(len(series) / 7, 1) / 5 * 100) if len(series) >= 7 else 50
    wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
    w_delta = series_delta(series, 'weight_kg')
    weight = 70 if w_delta is None else (50 + (50 if w_delta <= 0 else 0))
    water = [s['water_ml'] for s in series if s.get('water_ml') is not None]
    wg = series[0].get('water_goal') or 2000
    water_score = round(sum(1 for w in water if w >= wg) / len(water) * 100, 1) if water else 50
    bf = [s['body_fat_pct'] for s in series if s.get('body_fat_pct') is not None]
    bf_score = 70 if len(bf) < 2 else (80 if bf[-1] <= bf[0] else 40)
    wa = [s['waist_cm'] for s in series if s.get('waist_cm') is not None]
    wa_score = 70 if len(wa) < 2 else (80 if wa[-1] <= wa[0] else 40)
    items = {'饮食': round(diet, 1), '运动': round(ex, 1), '体重': weight,
             '饮水': water_score, '体脂': bf_score, '围度': wa_score}
    total = round(sum(items.values()) / len(items), 1)
    return {'total': total, 'items': items,
            'history': [{'date': s['date'],
                         'score': round(sum([
                             max(0, 100 - abs((s['calories'] or 0) - goal) / goal * 50),
                             min(100, (100 if (s.get('exercise_kcal') or 0) > 0 else 40)),
                             70 if s.get('weight_kg') is None else (80 if (s.get('weight_kg') or 0) >= 40 else 50),
                             min(100, ((s.get('water_ml') or 0) / wg * 100)),
                         ]) / 4, 1)} for s in series]}


def _anomaly_days(series: list[dict]) -> list[dict]:
    goal = series[0].get('calorie_goal') or 1800
    out = []
    for s in series:
        notes = []
        if s.get('calories') is not None and s['calories'] > goal * 1.3:
            notes.append(f'摄入超标 {s["calories"]}/{goal}')
        if s.get('deficit') is not None and s['deficit'] < -900:
            notes.append(f'缺口过大 {s["deficit"]:.0f}')
        if s.get('weight_kg') is not None:
            pass
        if notes:
            out.append({'date': s['date'], 'notes': notes})
    return out


def view_report(args) -> dict:
    start, end = resolve_window(args.window, args.start, args.end)
    series = build_series(start, end)
    kind = args.kind or 'full'

    if kind == 'full':
        # 8 维综合:KPI + 各维走势小图 + 与上周期 Δ + 异常天 + 建议
        span = (datetime.strptime(end, '%Y-%m-%d') - datetime.strptime(start, '%Y-%m-%d')).days
        prev_end = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=1)).date().isoformat()
        prev_start = (datetime.strptime(prev_end, '%Y-%m-%d') - timedelta(days=span)).date().isoformat()
        prev = build_series(prev_start, prev_end) if span > 0 else []
        cal_avg = series_avg(series, 'calories')
        ex_days = series_count(series, 'exercise_kcal')
        w_delta = series_delta(series, 'weight_kg')
        water_avg = series_avg(series, 'water_ml')
        deficit_avg = series_avg(series, 'deficit')
        bf_delta = series_delta(series, 'body_fat_pct')
        wa_delta = series_delta(series, 'waist_cm')
        prev_ex_days = series_count(prev, 'exercise_kcal') if prev else 0
        prev_water = series_avg(prev, 'water_ml') if prev else None
        prev_deficit = series_avg(prev, 'deficit') if prev else None
        prev_bf = series_delta(prev, 'body_fat_pct') if prev else None
        prev_wa = series_delta(prev, 'waist_cm') if prev else None
        kpis = [
            {'label': '日均摄入', 'value': f'{cal_avg or "-":.0f} 卡',
             'delta': round((cal_avg or 0) - (series_avg(prev, 'calories') or 0), 0) if prev and cal_avg is not None else None},
            {'label': '运动天数', 'value': f'{ex_days} 天',
             'delta': round(ex_days - prev_ex_days, 0) if prev else None},
            {'label': '体重变化', 'value': f'{w_delta or 0:+.2f} kg',
             'delta': round((w_delta or 0) - (series_delta(prev, 'weight_kg') or 0), 2) if prev and w_delta is not None else None},
            {'label': '日均饮水', 'value': f'{(water_avg or 0):.0f} ml',
             'delta': round((water_avg or 0) - (prev_water or 0), 0) if prev and water_avg is not None else None},
            {'label': '日均缺口', 'value': f'{deficit_avg or 0:+.0f} 卡',
             'delta': round((deficit_avg or 0) - (prev_deficit or 0), 0) if prev and deficit_avg is not None else None},
            {'label': '体脂变化', 'value': (f'{bf_delta:+.2f} %' if bf_delta is not None else '—'),
             'delta': round((bf_delta or 0) - (prev_bf or 0), 2) if prev and bf_delta is not None else None},
            {'label': '腰围变化', 'value': (f'{wa_delta:+.2f} cm' if wa_delta is not None else '—'),
             'delta': round((wa_delta or 0) - (prev_wa or 0), 2) if prev and wa_delta is not None else None},
        ]
        return {
            'view': 'report', 'kind': 'full', 'window': args.window,
            'start': start, 'end': end, 'days': len(series),
            'kpis': kpis,
            'series': [{'date': s['date'], 'calories': s['calories'],
                        'exercise_kcal': s['exercise_kcal'], 'weight_kg': s['weight_kg'],
                        'water_ml': s['water_ml'], 'deficit': s['deficit']} for s in series],
            'anomaly_days': _anomaly_days(series),
            'suggestion': ('摄入仍高于目标,先管住超标日(TOP 场景多为外食/零食)。'
                           if (cal_avg or 0) > (series[0].get('calorie_goal') or 1800) * 1.05
                           else ('运动天数偏少,每周提到 3 次。' if ex_days < max(len(series) / 7 * 3, 3)
                                 else '整体执行不错,保持当前节奏,注意记录完整度。')),
            'insight': f'窗口 {start}~{end}:日均摄入 {cal_avg or "-"} 卡 / 运动 {ex_days} 天 / 体重 {w_delta or 0:+.2f} kg。',
        }
    if kind == 'bmi':
        b = _bmi_data(series)
        return {'view': 'report', 'kind': 'bmi', 'window': args.window,
                'start': start, 'end': end, 'days': len(series), **b}
    if kind == 'tdee':
        tdee = series[0].get('tdee')
        cal_avg = series_avg(series, 'calories')
        factor = get_activity_factor()
        return {'view': 'report', 'kind': 'tdee', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'tdee': tdee, 'factor': factor, 'cal_avg': cal_avg,
                'deficit': round((cal_avg or 0) - (tdee or 1800), 0),
                'insight': f'TDEE ≈ {tdee} 卡(BMR × {factor});实际日均摄入 {cal_avg or "-"} 卡,'
                           f'静态缺口 {round((cal_avg or 0) - (tdee or 1800), 0):+.0f} 卡(不含运动)。'}
    if kind == 'bmr':
        tdee = series[0].get('tdee')
        factor = get_activity_factor()
        bmr = round((tdee or 1800) / factor, 0)
        under = [(s['date'], s['calories']) for s in series
                 if s.get('calories') is not None and s['calories'] < bmr * 0.95]
        return {'view': 'report', 'kind': 'bmr', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'bmr': bmr, 'tdee': tdee, 'factor': factor,
                'under_bmr_days': len(under), 'under_bmr_list': under[:7],
                'insight': f'BMR ≈ {bmr} 卡;摄入低于 BMR 共 {len(under)} 天'
                           + (' ⚠️ 长期低于 BMR 会掉代谢,缺口上限应高于 BMR。' if len(under) >= 3
                              else ',风险可控。')}
    if kind == 'protein':
        p = series_avg(series, 'protein') or 0
        weight = next((s['weight_kg'] for s in reversed(series) if s.get('weight_kg') is not None), None)
        target = round((weight or 70) * 1.2, 1)
        goal_cal = series[0].get('calorie_goal') or 1800
        p_goal = round(goal_cal / 10 * 0.4, 1)
        days = sum(1 for s in series if (s.get('protein') or 0) >= p_goal)
        total_days = series_count(series, 'protein')
        return {'view': 'report', 'kind': 'protein', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'avg': round(p, 1), 'target': target, 'p_goal': p_goal,
                'rate': round(days / total_days * 100, 1) if total_days else None,
                'series': [{'date': s['date'], 'protein': s['protein']} for s in series],
                'insight': f'日均蛋白 {p:.1f} g,达标率 {round(days / total_days * 100, 1) if total_days else "-"}%'
                           f'(目标 ≥{target} g,即体重×1.2)。'}
    if kind == 'water':
        water = [s['water_ml'] for s in series if s.get('water_ml') is not None]
        wg = series[0].get('water_goal') or 2000
        days_ok = sum(1 for w in water if w >= wg)
        return {'view': 'report', 'kind': 'water', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'avg': round(sum(water) / len(water), 0) if water else None,
                'goal': wg, 'days_ok': days_ok,
                'rate': round(days_ok / len(water) * 100, 1) if water else None,
                'series': [{'date': s['date'], 'water_ml': s['water_ml']} for s in series],
                'insight': f'日均饮水 {(sum(water) / len(water)):.0f} ml,达标 {days_ok}/{len(water)} 天'
                           + (' ✅' if water and sum(1 for w in water if w >= wg) >= len(water) * 0.7
                              else ' ⚠️ 建议设提醒每小时喝一杯。')}
    if kind == 'score':
        sc = _score(series)
        return {'view': 'report', 'kind': 'score', 'window': args.window,
                'start': start, 'end': end, 'days': len(series), **sc,
                'insight': f'综合评分 {sc["total"]} 分;最低分项:{min(sc["items"], key=sc["items"].get)}({min(sc["items"].values())} 分)。'}
    if kind == 'trend':
        sc = _score(series)
        trend = sc['history']
        n = len(trend)
        if n >= 2:
            first_half = sum(t['score'] for t in trend[:n // 2]) / (n // 2 or 1)
            second_half = sum(t['score'] for t in trend[n // 2:]) / (n - n // 2 or 1)
            direction = '上升' if second_half - first_half > 3 else ('下降' if second_half - first_half < -3 else '平稳')
        else:
            direction, first_half, second_half = '平稳', None, None
        # 拐点标注:分数方向反转的点
        inflections = []
        vals = [t['score'] for t in trend]
        for i in range(1, n - 1):
            if (vals[i] > vals[i - 1] and vals[i] >= vals[i + 1]) or (vals[i] < vals[i - 1] and vals[i] <= vals[i + 1]):
                inflections.append(trend[i]['date'])
        return {'view': 'report', 'kind': 'trend', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'trend': trend, 'direction': direction,
                'first_half': round(first_half, 1) if first_half else None,
                'second_half': round(second_half, 1) if second_half else None,
                'inflections': inflections[:10],
                'insight': f'健康指数走势:{direction}(前段 {first_half or "-"} → 后段 {second_half or "-"} 分,拐点 {len(inflections)} 个)。'}
    if kind == 'compare':
        span = (datetime.strptime(end, '%Y-%m-%d') - datetime.strptime(start, '%Y-%m-%d')).days
        prev_end = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days=1)).date().isoformat()
        prev_start = (datetime.strptime(prev_end, '%Y-%m-%d') - timedelta(days=span)).date().isoformat()
        prev = build_series(prev_start, prev_end) if span > 0 else []
        fields = [('calories', '摄入', '卡'), ('exercise_kcal', '运动消耗', '卡'),
                  ('weight_kg', '体重', 'kg'), ('water_ml', '饮水', 'ml'),
                  ('deficit', '缺口', '卡'), ('protein', '蛋白', 'g')]
        deltas = []
        for f, label, unit in fields:
            cur = series_avg(series, f)
            old = series_avg(prev, f)
            if cur is not None and old is not None:
                deltas.append({'label': label, 'current': round(cur, 1), 'prev': round(old, 1),
                               'delta': round(cur - old, 1), 'unit': unit})
        deltas.sort(key=lambda d: abs(d['delta']), reverse=True)
        return {'view': 'report', 'kind': 'compare', 'window': args.window,
                'start': start, 'end': end, 'days': len(series),
                'prev_start': prev_start, 'prev_end': prev_end,
                'deltas': deltas, 'top3': deltas[:3],
                'insight': '变化最大:' + '、'.join(
                    f'{d["label"]} {d["delta"]:+.1f}{d["unit"]}' for d in deltas[:3]) + '。'}
    raise ValueError(f'未知 report kind {kind}')


# ---------- A3 整体趋势 ----------

def view_trend(args) -> dict:
    start, end = resolve_window(args.window, args.start, args.end)
    series = build_series(start, end)
    fields, label = TREND_GROUPS[args.group]

    # 计算补充字段(bmi/muscle_mass/strength_kcal/cardio_kcal)
    conn = _get_db()
    try:
        height = conn.execute("SELECT height_cm FROM user_profile WHERE id = 1").fetchone()
        ex_rows = conn.execute(
            "SELECT date, category, SUM(calories_burned) AS kcal FROM exercise_log "
            "WHERE date BETWEEN ? AND ? GROUP BY date, category",
            (start, end),
        ).fetchall()
    finally:
        conn.close()
    height = (height[0] if height else None) or 170
    strength_by_day, cardio_by_day = {}, {}
    for d, cat, kcal in ex_rows:
        (strength_by_day if cat == '力量' else cardio_by_day)[d] = kcal

    for s in series:
        if s.get('weight_kg') is not None:
            s['bmi'] = round(s['weight_kg'] / ((height / 100) ** 2), 1)
        if s.get('weight_kg') is not None and s.get('body_fat_pct') is not None:
            s['muscle_mass'] = round(s['weight_kg'] * (1 - s['body_fat_pct'] / 100), 1)
        s['strength_kcal'] = strength_by_day.get(s['date'])
        s['cardio_kcal'] = cardio_by_day.get(s['date'])

    # 归一化(每字段 min-max → 0-100)
    norm = []
    for s in series:
        row = {'date': s['date']}
        for f, _ in fields:
            row[f] = s.get(f)
        norm.append(row)
    stats = {}
    for f, _ in fields:
        vals = [r[f] for r in norm if r.get(f) is not None]
        stats[f] = {'min': min(vals) if vals else None, 'max': max(vals) if vals else None}
    for row in norm:
        for f, _ in fields:
            st = stats[f]
            if st['min'] is None or row[f] is None or st['max'] == st['min']:
                row[f] = None
            else:
                row[f] = round((row[f] - st['min']) / (st['max'] - st['min']) * 100, 1)

    # 月度聚合降采样(≥90 天)
    monthly = None
    if len(series) >= 90:
        by_month: dict[str, list] = {}
        for s in series:
            by_month.setdefault(s['date'][:7], []).append(s)
        monthly = [{'month': m, **{f: round(sum((x.get(f) or 0) for x in rows) / len(rows), 1)
                                   for f, _ in fields}}
                   for m, rows in sorted(by_month.items())]

    # 异常日标注(摄入 > 目标×1.3 或缺口 < -900)
    goal = series[0].get('calorie_goal') or 1800
    anomaly = [s['date'] for s in series
               if (s.get('calories') or 0) > goal * 1.3
               or (s.get('deficit') is not None and s['deficit'] < -900)]

    period = args.period
    period_compare = None
    if period in ('monthly', 'quarterly', 'yearly', 'target'):
        today = date.today()
        if period == 'monthly':
            cur = [s for s in series if s['date'] >= today.replace(day=1).isoformat()]
            prev_m = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            prev = [s for s in series if prev_m.isoformat() <= s['date'] < today.replace(day=1).isoformat()]
            period_compare = {'label': '本月 vs 上月',
                              'current': _group_avg(cur, fields), 'prev': _group_avg(prev, fields)}
        elif period == 'quarterly':
            q = (today.month - 1) // 3
            q_start = date(today.year, q * 3 + 1, 1)
            prev_q_start = date(today.year - 1, q * 3 + 1, 1) if q == 0 else date(today.year, q * 3 - 2, 1)
            cur = [s for s in series if s['date'] >= q_start.isoformat()]
            prev = [s for s in series if prev_q_start.isoformat() <= s['date'] < q_start.isoformat()]
            period_compare = {'label': '本季 vs 上季',
                              'current': _group_avg(cur, fields), 'prev': _group_avg(prev, fields)}
        elif period == 'yearly':
            cur = [s for s in series if s['date'] >= f'{today.year}-01-01']
            prev = [s for s in series if f'{today.year - 1}-01-01' <= s['date'] < f'{today.year}-01-01']
            period_compare = {'label': '今年 vs 去年',
                              'current': _group_avg(cur, fields), 'prev': _group_avg(prev, fields)}
        elif period == 'target':
            period_compare = {'label': 'vs 目标',
                              'current': _group_avg(series, fields), 'prev': None,
                              'goal': {'calorie_goal': goal,
                                       'water_goal': series[0].get('water_goal') or 2000}}

    return {
        'view': 'trend', 'group': args.group, 'group_label': label,
        'window': args.window, 'start': start, 'end': end, 'days': len(series),
        'metrics': [{'field': f, 'label': l} for f, l in fields],
        'norm': norm, 'stats': stats, 'monthly': monthly, 'anomaly': anomaly[:20],
        'period': period, 'period_compare': period_compare,
        'insight': f'「{label}」多指标同图(归一化 0-100),默认窗口 {args.window}'
                   + (f',周期对比:{period_compare["label"]}' if period_compare else '')
                   + (f';异常日 {len(anomaly)} 天' if anomaly else ''),
    }


def _group_avg(rows: list[dict], fields: list) -> dict:
    out = {}
    for f, _ in fields:
        vals = [r[f] for r in rows if r.get(f) is not None]
        out[f] = round(sum(vals) / len(vals), 1) if vals else None
    return out


# ---------- A6 预测 ----------

PREDICT_KINDS = {
    'weight_week':    {'fn': 'weight_forecast', 'days': 7,   'title': '预测体重(1 周后)'},
    'weight_month':   {'fn': 'weight_forecast', 'days': 30,  'title': '预测体重(1 月后)'},
    'weight_3m':      {'fn': 'weight_forecast', 'days': 90,  'title': '预测体重(3 月后)'},
    'weight_6m':      {'fn': 'weight_forecast', 'days': 180, 'title': '预测体重(6 月后)'},
    'weight_custom_t': {'fn': 'weight_forecast', 'days': None, 'title': '预测体重(自定义时间)'},
    'weight_target':  {'fn': 'weight_target', 'days': None, 'title': '预测体重(自定义目标)'},
    'sim_cut_300':    {'fn': 'weight_sim_cut', 'cut': 300,  'title': '模拟减重(每天-300卡)'},
    'sim_cut_500':    {'fn': 'weight_sim_cut', 'cut': 500,  'title': '模拟减重(每天-500卡)'},
    'sim_cut_700':    {'fn': 'weight_sim_cut', 'cut': 700,  'title': '模拟减重(每天-700卡)'},
    'sim_target_30':  {'fn': 'weight_sim_target', 'days': 30, 'title': '模拟减重(30天减Xkg)'},
    'sim_target_60':  {'fn': 'weight_sim_target', 'days': 60, 'title': '模拟减重(60天减Xkg)'},
    'sim_target_90':  {'fn': 'weight_sim_target', 'days': 90, 'title': '模拟减重(90天减Xkg)'},
    'sim_target_custom': {'fn': 'weight_sim_target', 'days': None, 'title': '模拟减重(自定义天数减Xkg)'},
    'cal_week':       {'fn': 'calorie_forecast', 'days': 7,  'title': '摄入预测(按当前速率 1 周)'},
    'cal_month':      {'fn': 'calorie_forecast', 'days': 30, 'title': '摄入预测(按当前速率 1 月)'},
    'cal_3m':         {'fn': 'calorie_forecast', 'days': 90, 'title': '摄入预测(按当前速率 3 月)'},
    'cal_custom':     {'fn': 'calorie_forecast', 'days': None, 'title': '摄入预测(自定义)'},
    'cal_goal':       {'fn': 'calorie_goal_eta', 'title': '摄入预测(营养目标达成预测)'},
    'cal_deficit':    {'fn': 'calorie_deficit_eta', 'title': '摄入预测(卡路里缺口预测)'},
    'cal_stability':  {'fn': 'calorie_stability', 'title': '摄入预测(摄入稳定性预测)'},
}


def view_predict(args) -> dict:
    spec = PREDICT_KINDS.get(args.kind)
    if not spec:
        raise ValueError(f'未知 predict kind {args.kind}')
    start, end = resolve_window(args.window or '90d', args.start, args.end)
    series = build_series(start, end)
    fn = getattr(sim, spec['fn'])
    if spec['fn'] == 'weight_forecast':
        days = args.days or spec.get('days') or 30
        return fn(series, days, spec['title'])
    if spec['fn'] == 'weight_target':
        if not args.target:
            raise ValueError('--target <目标kg> 必填(自定义目标)')
        return fn(series, args.target, spec['title'])
    if spec['fn'] == 'weight_sim_cut':
        return fn(series, args.cut or spec.get('cut') or 300, spec['title'])
    if spec['fn'] == 'weight_sim_target':
        if not args.target:
            raise ValueError('--target <目标kg> 必填(N 天减 X kg)')
        days = args.days or spec.get('days') or 30
        return fn(series, args.target, days, spec['title'])
    if spec['fn'] == 'calorie_forecast':
        days = args.days or spec.get('days') or 30
        return fn(series, days, spec['title'])
    return fn(series, spec['title'])


# ---------- 单点 · 看每日 6 因素 ----------

def view_six(args) -> dict:
    d = args.date or date.today().isoformat()
    series = build_series(d, d)
    if not series:
        raise ValueError(f'{d} 无任何数据')
    s = series[0]
    yesterday = (datetime.strptime(d, '%Y-%m-%d') - timedelta(days=1)).date().isoformat()
    y = build_series(yesterday, yesterday)[0] if build_series(yesterday, yesterday) else None

    def _vs_y(field, fmt='{:.1f}'):
        if s.get(field) is None:
            return None
        if y is None or y.get(field) is None:
            return None
        return round(s[field] - y[field], 1)

    kpis = [
        {'label': '体重', 'value': f'{s["weight_kg"]:.1f} kg' if s.get('weight_kg') is not None else '—',
         'delta': _vs_y('weight_kg')},
        {'label': '摄入', 'value': f'{s["calories"]:.0f} 卡' if s.get('calories') is not None else '—',
         'delta': _vs_y('calories')},
        {'label': '运动', 'value': f'{s["exercise_kcal"]:.0f} 卡' if s.get('exercise_kcal') is not None else '—',
         'delta': _vs_y('exercise_kcal')},
        {'label': '饮水', 'value': f'{s["water_ml"]:.0f} ml' if s.get('water_ml') is not None else '—',
         'delta': _vs_y('water_ml')},
        {'label': '体脂', 'value': f'{s["body_fat_pct"]:.1f} %' if s.get('body_fat_pct') is not None else '—',
         'delta': _vs_y('body_fat_pct')},
        {'label': '围度', 'value': f'{s["waist_cm"]:.1f} cm' if s.get('waist_cm') is not None else '—',
         'delta': _vs_y('waist_cm')},
    ]
    present = [k['label'] for k in kpis if k['value'] != '—']
    degraded = len(present) < 6 and ('体脂' not in present or '围度' not in present)
    # 7 天小图
    week_start = (datetime.strptime(d, '%Y-%m-%d') - timedelta(days=6)).date().isoformat()
    week = build_series(week_start, d)
    return {
        'view': 'six', 'date': d, 'kpis': kpis, 'degraded': degraded,
        'week': [{'date': x['date'], 'calories': x['calories'],
                  'exercise_kcal': x['exercise_kcal'], 'water_ml': x['water_ml'],
                  'weight_kg': x['weight_kg']} for x in week],
        'anomaly': [x['date'] for x in week if (x.get('calories') or 0) > (s.get('calorie_goal') or 1800) * 1.3],
        'insight': f'{d} 六维快照:{"、".join(k["label"] + " " + k["value"] for k in kpis if k["value"] != "—")}'
                   + (';无体脂/围度数据,已自动降级为 4 维。' if degraded else ''),
    }


# ---------- 分发 ----------

def build_parser():
    p = argparse.ArgumentParser(prog='render_analysis', description='分析 154 场景统一渲染器')
    p.add_argument('--view', required=True, choices=list(TEMPLATES), help='视图(combined/nutrition/report/trend/anomaly/predict/six)')
    p.add_argument('--pair', help='combined: 配对(weight_calorie 等)')
    p.add_argument('--group', help='nutrition: macro3/sodium_fiber/sodium_combined/advice; trend: g1-g11')
    p.add_argument('--kind', help='report: full/bmi/tdee/bmr/protein/water/score/trend/compare')
    p.add_argument('--diagnose', help='anomaly: 诊断 kind(weight_plateau 等 23 种)')
    p.add_argument('--window', default='30d', help='窗口: 7d/15d/30d/90d/180d/365d/本周/上周/本月/上月/今年/custom')
    p.add_argument('--start', help='custom 窗口开始 YYYY-MM-DD')
    p.add_argument('--end', help='custom 窗口结束 YYYY-MM-DD')
    p.add_argument('--period', choices=['monthly', 'quarterly', 'yearly', 'target'], help='trend 周期对比')
    p.add_argument('--days', type=int, help='predict: 天数')
    p.add_argument('--target', type=float, help='predict: 目标值')
    p.add_argument('--cut', type=int, help='predict: 每天减多少卡')
    p.add_argument('--date', help='six: 日期 YYYY-MM-DD')
    return p


def main():
    args = build_parser().parse_args()
    try:
        if args.view == 'combined':
            data = view_combined(args)
            scene = f'看{PAIRS[args.pair][2].split("(")[0]} vs {PAIRS[args.pair][3].split("(")[0]} 组合'
        elif args.view == 'nutrition':
            data = view_nutrition(args)
            scene = {'macro3': '看三大营养交叉', 'sodium_fiber': '看钠糖纤维趋势',
                     'sodium_combined': '看钠糖纤维综合', 'advice': '营养建议'}[args.group]
        elif args.view == 'report':
            data = view_report(args)
            scene = '健康报告' if args.kind == 'full' else {
                'bmi': '看BMI报告', 'tdee': '看TDEE报告', 'bmr': '看BMR报告',
                'protein': '看蛋白质摄入报告', 'water': '看水分摄入报告',
                'score': '看综合评分', 'trend': '看健康趋势', 'compare': '健康报告(含对比)'}[args.kind]
        elif args.view == 'trend':
            data = view_trend(args)
            scene = f'看整体趋势({data["group_label"]})'
        elif args.view == 'anomaly':
            start, end = resolve_window(args.window, args.start, args.end)
            series = build_series(start, end)
            data = diagnose(args.diagnose, series)
            data['window'] = args.window
            scene = data['title']
        elif args.view == 'predict':
            data = view_predict(args)
            scene = data['title']
        elif args.view == 'six':
            data = view_six(args)
            scene = '看每日 6 因素综合'
        else:  # pragma: no cover
            raise ValueError(f'未知 view {args.view}')
    except ValueError as e:
        print(f'❌ {e}', file=sys.stderr)
        return 2

    return _out(data, args.view, scene)


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
