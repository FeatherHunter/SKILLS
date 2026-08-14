#!/usr/bin/env python3
"""analysis/cross.py — 跨表 JOIN 组合分析(ticket #10 · 分析 A1/A5)

把日序列 series[] 里的两个字段配对,产出:
  - 双轴序列 line[](含单边日)
  - 散点数据 scatter[](仅双边对齐日)
  - 皮尔逊相关系数 correlation{r, n}
  - 一元线性回归 regression{slope, intercept, n}
  - 延迟相关性 lag[](前 1-3 天 B 值 vs 当日 A 值)
  - 分层对比 strat[](周末/工作日 · 运动日/休息日 · 力量/有氧 · 达标日/未达标日 · 缺口正负)
  - 一句话洞察 insight(规则生成)

配对表:
  A1: weight_calorie / weight_exercise / weight_protein / weight_deficit /
      calorie_exercise / weight_bodyfat / weight_waist / water_weight
  A5: protein_carbs / protein_fat / carbs_fat
"""
from __future__ import annotations

import sys
from math import sqrt
from pathlib import Path

# 配对 → (字段 A, 字段 B, A 显示名, B 显示名, 分层模式)
PAIRS: dict[str, tuple[str, str, str, str, str]] = {
    # A1 组合分析
    'weight_calorie':   ('weight_kg',     'calories',      '体重(kg)',  '摄入(卡)',        'weekday'),
    'weight_exercise':  ('weight_kg',     'exercise_kcal', '体重(kg)',  '运动消耗(卡)',    'exercise'),
    'weight_protein':   ('weight_kg',     'protein',       '体重(kg)',  '蛋白摄入(g)',     'protein'),
    'weight_deficit':   ('weight_kg',     'deficit',       '体重(kg)',  '热量缺口(卡)',    'deficit'),
    'calorie_exercise': ('calories',      'exercise_kcal', '摄入(卡)',  '运动消耗(卡)',    'deficit_src'),
    'weight_bodyfat':   ('weight_kg',     'body_fat_pct',  '体重(kg)',  '体脂率(%)',       'divergence'),
    'weight_waist':     ('weight_kg',     'waist_cm',      '体重(kg)',  '腰围(cm)',        'waist_divergence'),
    'water_weight':     ('water_ml',      'weight_kg',     '饮水(ml)',  '体重(kg)',        'water'),
    # A5 营养交叉
    'protein_carbs':    ('protein',       'carbs',         '蛋白(g)',   '碳水(g)',         'ratio'),
    'protein_fat':      ('protein',       'fat',           '蛋白(g)',   '脂肪(g)',         'ratio'),
    'carbs_fat':        ('carbs',         'fat',           '碳水(g)',   '脂肪(g)',         'ratio'),
}


def pearson(pairs: list[tuple[float, float]]) -> float | None:
    """皮尔逊相关系数(≥2 对且 B 有方差);数据不足返回 None"""
    n = len(pairs)
    if n < 2:
        return None
    sx = sy = sxy = sx2 = sy2 = 0.0
    for x, y in pairs:
        sx += x; sy += y; sxy += x * y; sx2 += x * x; sy2 += y * y
    denom = sqrt((n * sx2 - sx * sx) * (n * sy2 - sy * sy))
    if denom == 0:
        return None
    r = (n * sxy - sx * sy) / denom
    return round(max(-1.0, min(1.0, r)), 3)


def linear_regression(pairs: list[tuple[float, float]]) -> dict | None:
    """y = slope * x + intercept(最小二乘);数据不足返回 None"""
    n = len(pairs)
    if n < 2:
        return None
    sx = sy = sxy = sx2 = 0.0
    for x, y in pairs:
        sx += x; sy += y; sxy += x * y; sx2 += x * x
    denom = n * sx2 - sx * sx
    if denom == 0:
        return None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return {'slope': round(slope, 4), 'intercept': round(intercept, 2), 'n': n}


def _aligned(series: list[dict], fa: str, fb: str) -> list[tuple[float, float]]:
    """双边对齐日期的 (a, b) 对"""
    return [(s[fa], s[fb]) for s in series if s.get(fa) is not None and s.get(fb) is not None]


def _delta(vals: list[float]) -> float | None:
    if len(vals) < 2:
        return None
    return round(vals[-1] - vals[0], 2)


def _strat(series: list[dict], mode: str, a: str, b: str) -> dict:
    """分层统计。mode 决定分层逻辑,输出统一 dict:
    {
      'rows':  [{'label', 'days', 'a_delta', 'b_avg', 'note'}],  # 表格行
      'extra': [str, ...],                                        # 补充说明(背离/TOP/构成)
    }
    """
    from datetime import datetime

    rows: list[dict] = []
    extra: list[str] = []

    def _d(s):
        return datetime.strptime(s['date'], '%Y-%m-%d').date()

    def _mk(label, rows_in):
        av = [s[a] for s in rows_in]
        bv = [s[b] for s in rows_in if s.get(b) is not None]
        return {
            'label': label,
            'days':  len(rows_in),
            'a_delta': _delta(av),
            'b_avg': round(sum(bv) / len(bv), 1) if bv else None,
            'note': '',
        }

    if mode in ('weekday', 'exercise', 'protein', 'deficit', 'water'):
        cond, non = [], []
        for s in series:
            is_cond = False
            if mode == 'weekday':
                is_cond = _d(s).weekday() < 5
            elif mode == 'exercise':
                is_cond = (s.get('exercise_kcal') or 0) > 0
            elif mode == 'protein':
                is_cond = (s.get('protein') or 0) >= (s.get('calorie_goal') or 0) / 10 * 0.4
            elif mode == 'deficit':
                # 热量缺口 = 消耗 − 摄入 (正=缺口 · ADR-0013): deficit>0 = 有缺口日
                is_cond = (s.get('deficit') or 0) > 0
            elif mode == 'water':
                is_cond = (s.get('water_ml') or 0) >= (s.get('water_goal') or 2000)
            if s.get(a) is None:
                continue
            (cond if is_cond else non).append(s)
        labels = {'weekday': ('工作日', '周末'), 'exercise': ('运动日', '休息日'),
                  'protein': ('蛋白达标日', '未达标日'), 'deficit': ('有缺口日', '无缺口日'),
                  'water': ('饮水达标日', '未达标日')}[mode]
        rows = [_mk(labels[0], cond), _mk(labels[1], non)]
        d1 = rows[0]['a_delta'] or 0
        d2 = rows[1]['a_delta'] or 0
        if rows[0]['days'] and rows[1]['days'] and abs(d1 - d2) > 0.2:
            rows[0]['note'] = f'Δ差异 {d1 - d2:+.2f}'
            rows[1]['note'] = f'Δ差异 {d2 - d1:+.2f}'

        if mode == 'exercise':
            # 力量 vs 有氧分层(直接查 exercise_log)
            conn = None
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
                from analysis._utils import _get_db
                conn = _get_db()
                start, end = series[0]['date'], series[-1]['date']
                strength = conn.execute(
                    "SELECT SUM(calories_burned) FROM exercise_log "
                    "WHERE date BETWEEN ? AND ? AND category = '力量'", (start, end)).fetchone()[0] or 0
                cardio = conn.execute(
                    "SELECT SUM(calories_burned) FROM exercise_log "
                    "WHERE date BETWEEN ? AND ? AND category = '有氧'", (start, end)).fetchone()[0] or 0
                extra.append(f'力量消耗合计 {strength:.0f} 卡 vs 有氧 {cardio:.0f} 卡')
            except Exception as e:
                extra.append(f'力量/有氧分层不可用: {e}')
            finally:
                if conn:
                    conn.close()
    elif mode == 'deficit_src':
        cal = [s['calories'] for s in series if s.get('calories') is not None]
        ex = [s['exercise_kcal'] for s in series if s.get('exercise_kcal') is not None]
        tdee = series[0].get('tdee') if series else None
        cal_avg = round(sum(cal) / len(cal), 1) if cal else None
        ex_avg = round(sum(ex) / len(ex), 1) if ex else None
        rows = [
            {'label': '日均摄入', 'days': len(cal), 'a_delta': None, 'b_avg': cal_avg, 'note': ''},
            {'label': '日均运动', 'days': len(ex), 'a_delta': None, 'b_avg': ex_avg, 'note': ''},
        ]
        if cal_avg and tdee:
            # 热量缺口 = 消耗 − 摄入 (正=缺口 · ADR-0013): 缺口 = (TDEE + 运动) − 摄入
            extra.append(f'缺口构成:(TDEE {tdee} + 运动 {ex_avg or 0}) − 摄入 {cal_avg} = 日均缺口 {tdee + (ex_avg or 0) - cal_avg:+.0f} 卡')
    elif mode == 'divergence':
        wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
        bv = [s['body_fat_pct'] for s in series if s.get('body_fat_pct') is not None]
        w_delta = _delta(wv)
        b_delta = _delta(bv)
        extra.append(f'体重净变化 {w_delta:+.2f} kg;体脂净变化 {b_delta:+.2f} 个百分点' if w_delta is not None and b_delta is not None
                     else '体重/体脂样本不足,无法背离检测')
        if w_delta is not None and b_delta is not None:
            if w_delta < -0.3 and b_delta > -0.5:
                extra.append('⚠️ 背离:体重降但体脂未同步降,警惕肌肉流失')
            else:
                extra.append('体重与体脂同向变化,脂肪确实在减少')
    elif mode == 'waist_divergence':
        wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
        w_delta = _delta(wv)
        extra.append(f'体重净变化 {w_delta:+.2f} kg' if w_delta is not None else '体重样本不足')
        # 各部位变化 TOP(body_measurements 多部位)
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from analysis._utils import _get_db
            conn = _get_db()
            start, end = series[0]['date'], series[-1]['date']
            cols = ['chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm', 'shoulder_cm',
                    'left_thigh_cm', 'right_thigh_cm', 'left_calf_cm', 'right_calf_cm',
                    'left_arm_cm', 'right_arm_cm', 'left_forearm_cm', 'right_forearm_cm']
            labels = {'chest_cm': '胸围', 'waist_cm': '腰围', 'abdomen_cm': '腹围', 'hip_cm': '臀围',
                      'shoulder_cm': '肩围', 'left_thigh_cm': '左大腿', 'right_thigh_cm': '右大腿',
                      'left_calf_cm': '左小腿', 'right_calf_cm': '右小腿', 'left_arm_cm': '左上臂',
                      'right_arm_cm': '右上臂', 'left_forearm_cm': '左前臂', 'right_forearm_cm': '右前臂'}
            part_deltas = []
            for col in cols:
                first = conn.execute(
                    f"SELECT {col} FROM body_measurements WHERE date BETWEEN ? AND ? "
                    f"AND {col} IS NOT NULL AND is_deprecated = 0 ORDER BY date, id LIMIT 1",
                    (start, end)).fetchone()
                last = conn.execute(
                    f"SELECT {col} FROM body_measurements WHERE date BETWEEN ? AND ? "
                    f"AND {col} IS NOT NULL AND is_deprecated = 0 ORDER BY date DESC, id DESC LIMIT 1",
                    (start, end)).fetchone()
                if first and last and first[0] is not None and last[0] is not None:
                    part_deltas.append((labels[col], round(last[0] - first[0], 2)))
            part_deltas.sort(key=lambda x: abs(x[1]), reverse=True)
            top = '、'.join(f'{n} {d:+.1f}cm' for n, d in part_deltas[:3])
            extra.append('各部位变化 TOP:' + (top if top else '窗口内无围度数据'))
            conn.close()
        except Exception as e:
            extra.append(f'围度明细不可用: {e}')
    elif mode == 'ratio':
        ab = [(s.get('protein') or 0, s.get('carbs') or 0, s.get('fat') or 0) for s in series
              if s.get('protein') is not None or s.get('carbs') is not None or s.get('fat') is not None]
        if len(ab) >= 4:
            half = len(ab) // 2

            def _ratio(rows_in):
                p = sum(r[0] for r in rows_in) or 1
                return (f'蛋白{sum(r[0] for r in rows_in) / p * 100:.0f}%'
                        f' 碳水{sum(r[1] for r in rows_in) / p * 100:.0f}%'
                        f' 脂肪{sum(r[2] for r in rows_in) / p * 100:.0f}%')
            extra.append(f'前段占比:{_ratio(ab[:half])}')
            extra.append(f'后段占比:{_ratio(ab[half:])}')
    return {'rows': rows, 'extra': extra}


def _insight(pair: str, r: float | None, lag: list, strat: dict, days: int) -> str:
    """规则生成一句话洞察"""
    b_label = PAIRS[pair][3]
    if r is None:
        return f'数据不足,无法判断“{b_label}”与目标指标的关联。'
    strength = '强' if abs(r) >= 0.5 else ('中' if abs(r) >= 0.3 else '弱')
    direction = '正相关' if r > 0 else '负相关'
    line = f'{strength}{direction}(r={r:+.2f})'
    if pair == 'weight_calorie' and lag:
        best = max(lag, key=lambda x: abs(x['r']) if x['r'] is not None else 0)
        if best.get('r') is not None and abs(best['r']) > abs(r or 0):
            line += f';滞后 {best["lag"]} 天相关性更强(r={best["r"]:+.2f})'
    ext = '\n'.join(strat.get('extra', []))
    if '背离' in ext:
        line += ';⚠️ 体重与体脂/围度存在背离信号'
    if '⚠️ 背离' in ext:
        line += ';⚠️ 体重降但体脂未同步降,警惕肌肉流失'
    return f'窗口内共 {days} 天,{b_label}与目标指标呈{line}。'


def analyze_pair(series: list[dict], pair: str, window: str = '30d') -> dict:
    """组合分析主入口"""
    if pair not in PAIRS:
        raise ValueError(f'未知配对 {pair},可选: {", ".join(PAIRS)}')
    fa, fb, la, lb, mode = PAIRS[pair]

    # 双轴序列:任一边有值的日
    line = [{'date': s['date'], 'a': s[fa], 'b': s[fb]}
            for s in series if s.get(fa) is not None or s.get(fb) is not None]
    # 散点:双边对齐
    aligned = _aligned(series, fa, fb)
    scatter = [{'x': a, 'y': b} for a, b in aligned]

    r = pearson(aligned)
    reg = linear_regression(aligned)

    # 延迟相关(仅对 weight_calorie / weight_exercise / weight_protein 有意义)
    lag = []
    if pair in ('weight_calorie', 'weight_exercise', 'weight_protein'):
        for l in (1, 2, 3):
            pairs = []
            for i in range(l, len(series)):
                if (series[i].get(fa) is not None
                        and series[i - l].get(fb) is not None):
                    pairs.append((series[i][fa], series[i - l][fb]))
            lag.append({'lag': l, 'r': pearson(pairs)})

    strat = _strat(series, mode, fa, fb)

    # 超标日标注(摄入 > 目标 × 1.3)
    over_limit_days = []
    if pair == 'weight_calorie':
        goal = series[0].get('calorie_goal') or 1800
        over_limit_days = [s['date'] for s in series
                           if s.get('calories') is not None and s['calories'] > goal * 1.3]

    # 缺口大小分桶(看体重 vs 缺口 · 正=缺口 ADR-0013)
    deficit_buckets = []
    if pair == 'weight_deficit':
        buckets = {'深缺口(>500卡)': 0, '标准缺口(100~500)': 0, '小幅盈余(-100~100)': 0, '盈余(<-100)': 0}
        for s in series:
            d = s.get('deficit')
            if d is None:
                continue
            if d > 500:
                buckets['深缺口(>500卡)'] += 1
            elif d > 100:
                buckets['标准缺口(100~500)'] += 1
            elif d >= -100:
                buckets['小幅盈余(-100~100)'] += 1
            else:
                buckets['盈余(<-100)'] += 1
        deficit_buckets = [{'label': k, 'days': v} for k, v in buckets.items() if v > 0]

    av = [s[fa] for s in series if s.get(fa) is not None]
    bv = [s[fb] for s in series if s.get(fb) is not None]

    return {
        'pair':        pair,
        'labels':      {'a': la, 'b': lb},
        'window':      window,
        'start':       series[0]['date'] if series else None,
        'end':         series[-1]['date'] if series else None,
        'days':        len(series),
        'a_avg':       round(sum(av) / len(av), 2) if av else None,
        'b_avg':       round(sum(bv) / len(bv), 2) if bv else None,
        'a_delta':     _delta(av),
        'b_delta':     _delta(bv),
        'a_count':     len(av),
        'b_count':     len(bv),
        'line':        line,
        'scatter':     scatter,
        'over_limit_days': over_limit_days,
        'deficit_buckets': deficit_buckets,
        'correlation': {'r': r, 'n': len(aligned)},
        'regression':  reg,
        'lag':         lag,
        'strat':       strat,
        'insight':     _insight(pair, r, lag, strat, len(series)),
    }
