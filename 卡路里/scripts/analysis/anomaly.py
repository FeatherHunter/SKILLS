#!/usr/bin/env python3
"""analysis/anomaly.py — 自动分析诊断(ticket #10 · 分析 A4 23 场景)

规则引擎:从日序列 series[] + 明细表取证,输出
    {
      kind, title, window, start, end,
      findings: [ {cause, evidence, confidence, action} ],
      degraded: bool,           # 数据不足 → 降级提示
      degrade_msg: str,
      insight: str
    }

场景分组:
  A4.1 体重诊断 6  kind: weight_volatility / weight_plateau / weight_rebound /
                        weight_loss_cause / weight_anomaly / weight_divergence
  A4.2 饮食诊断 4  kind: diet_over / diet_under / diet_unbalanced / diet_structure
  A4.3 运动诊断 5  kind: exercise_insufficient / exercise_overload /
                        exercise_type_imbalance / exercise_efficiency / exercise_advice
  A4.4 综合诊断 8  kind: why_not_losing / why_losing_fast / rate_reasonable /
                        strategy_check / gap_to_goal / month_highlights / month_improve / overall
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from analysis._utils import _get_db, get_activity_factor  # noqa: E402
from analysis.series import series_avg, series_delta, series_sum  # noqa: E402

MIN_DAYS = 7   # 低于 7 天数据:全部降级
PRED_MIN = 14  # 预测/速度类场景:低于 14 天降级


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return round((sum((v - m) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5, 2)


def _weekday_count(series: list[dict]) -> int:
    return sum(1 for s in series if datetime.strptime(s['date'], '%Y-%m-%d').weekday() < 5)


def _weight_vals(series: list[dict]) -> list[float]:
    return [s['weight_kg'] for s in series if s.get('weight_kg') is not None]


def _top_foods(start: str, end: str, col: str = 'calories', limit: int = 5) -> list[dict]:
    """热量/蛋白/碳水/脂肪超标来源 TOP(按列求和)"""
    conn = _get_db()
    try:
        rows = conn.execute(
            f"SELECT food_name, SUM({col}) AS total, COUNT(*) AS times FROM food_log "
            f"WHERE date BETWEEN ? AND ? AND food_name != '💧水' "
            f"GROUP BY food_name ORDER BY total DESC LIMIT ?",
            (start, end, limit),
        ).fetchall()
        return [{'food': r[0], 'total': round(r[1], 1), 'times': r[2]} for r in rows]
    finally:
        conn.close()


def _meal_structure(start: str, end: str) -> dict:
    """餐次结构:按 time 分桶(早/午/晚/加餐)统计次数与占比"""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT time FROM food_log WHERE date BETWEEN ? AND ? AND food_name != '💧水'",
            (start, end),
        ).fetchall()
        buckets = {'早餐': 0, '午餐': 0, '晚餐': 0, '加餐/夜宵': 0}
        for (t,) in rows:
            h = int((t or '12:00').split(':')[0])
            if h < 10:
                buckets['早餐'] += 1
            elif h < 15:
                buckets['午餐'] += 1
            elif h < 21:
                buckets['晚餐'] += 1
            else:
                buckets['加餐/夜宵'] += 1
        total = sum(buckets.values()) or 1
        return {k: {'times': v, 'share': round(v / total * 100, 1)} for k, v in buckets.items()}
    finally:
        conn.close()


def _exercise_rows(start: str, end: str) -> list[dict]:
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT date, exercise_type, category, duration_minutes, calories_burned "
            "FROM exercise_log WHERE date BETWEEN ? AND ? ORDER BY date, id",
            (start, end),
        ).fetchall()
        return [{'date': r[0], 'type': r[1], 'category': r[2],
                 'minutes': r[3], 'kcal': r[4]} for r in rows]
    finally:
        conn.close()


def _base(series: list[dict], kind: str, title: str) -> dict:
    return {
        'kind': kind,
        'title': title,
        'window': '自定义',
        'start': series[0]['date'] if series else None,
        'end': series[-1]['date'] if series else None,
        'days': len(series),
        'findings': [],
        'degraded': False,
        'degrade_msg': '',
        'insight': '',
    }


def _degrade(out: dict, msg: str) -> dict:
    out['degraded'] = True
    out['degrade_msg'] = msg
    out['insight'] = msg
    return out


# ---------- 体重诊断 6 ----------

def _diag_weight_volatility(series: list[dict]) -> dict:
    out = _base(series, 'weight_volatility', '诊断体重波动原因')
    wv = _weight_vals(series)
    if len(wv) < MIN_DAYS:
        return _degrade(out, f'可用体重数据 {len(wv)} 天,不足 {MIN_DAYS} 天,无法诊断波动。')
    std = _std(wv)
    avg = round(sum(wv) / len(wv), 2)
    out['findings'].append({
        'cause': '波动幅度评估',
        'evidence': f'窗口内 {len(wv)} 个体重值,均值 {avg} kg,标准差 {std} kg',
        'confidence': '高' if std > 0.6 else '中',
        'action': ('波动明显(σ>0.6):优先看水分/盐分/进食时间影响,固定晨起空腹同一条件称重'
                   if std > 0.6 else '波动在正常范围:每日 ±0.3kg 内多为水分波动,不必逐日焦虑'),
    })
    # 波动来源:水分(饮水 vs 体重相关)、盐分(钠均值)、进食(摄入 vs 体重)
    cal_r = [abs((s.get('calories') or 0) - (s.get('calorie_goal') or 0)) for s in series]
    sodium = [s['sodium_mg'] for s in series if s.get('sodium_mg') is not None]
    if sodium:
        na_avg = sum(sodium) / len(sodium)
        out['findings'].append({
            'cause': '钠摄入过高(水分滞留)',
            'evidence': f'日均钠 {round(na_avg):.0f} mg(参考 ≤2000 mg),高钠日次日起体重易虚高',
            'confidence': '中',
            'action': '控制高盐加工食品(火锅/卤味/腌制品),高钠日多喝水排钠',
        })
    avg_cal = series_avg(series, 'calories')
    if avg_cal:
        out['findings'].append({
            'cause': '摄入波动',
            'evidence': f'日均摄入 {avg_cal} 卡,偏离目标 {series[0].get("calorie_goal")} 卡达 {abs(avg_cal - series[0]["calorie_goal"]):.0f} 卡',
            'confidence': '中',
            'action': '周末/聚餐日摄入波动最大,可对每周 1-2 个高卡日单独复盘',
        })
    out['insight'] = f'波动以{"明显" if std > 0.6 else "正常"}为主(σ={std}),建议统一称重条件后继续观察。'
    return out


def _diag_weight_plateau(series: list[dict]) -> dict:
    out = _base(series, 'weight_plateau', '诊断体重停滞(含平台期判断)')
    wv = _weight_vals(series)
    if len(wv) < PRED_MIN:
        return _degrade(out, f'可用体重数据 {len(wv)} 天,不足 {PRED_MIN} 天,无法判断平台期。')
    # 平台期:最近 ≥14 天最高-最低 ≤ ±0.5kg
    recent = wv[-14:]
    span = (max(recent) - min(recent)) if len(recent) >= 14 else 99
    plateau = len(recent) >= 14 and span <= 0.5
    out['findings'].append({
        'cause': '平台期判断',
        'evidence': (f'最近 14 天体重的最高-最低差 {span:.2f} kg(≤0.5 kg 判平台期)'
                     if len(recent) >= 14 else f'最近体重样本 {len(recent)} 天,不足 14 天'),
        'confidence': '高' if plateau else '中',
        'action': ('当前处于平台期:体重保护机制启动,可尝试碳水循环/增加力量训练/调整缺口 10-15%'
                   if plateau else '尚未进入平台期,保持当前节奏'),
    })
    # 停滞期间摄入是否仍达标
    recent_avg = round(sum(recent) / len(recent), 2)
    cal_avg = series_avg(series[-14:], 'calories')
    out['findings'].append({
        'cause': '摄入是否仍在缺口',
        'evidence': f'近 14 天日均摄入 {cal_avg or "—"} 卡 vs 目标 {series[0].get("calorie_goal")} 卡,体重均值 {recent_avg} kg',
        'confidence': '中',
        'action': '若摄入已悄悄回到维持水平,先恢复缺口再谈平台期',
    })
    out['insight'] = ('⚠️ 已持续 14 天体重不变(±0.5kg 内),符合平台期特征。' if plateau
                      else '体重仍在小幅波动,暂未达到平台期标准。')
    return out


def _diag_weight_rebound(series: list[dict]) -> dict:
    out = _base(series, 'weight_rebound', '诊断体重反弹')
    wv = _weight_vals(series)
    if len(wv) < MIN_DAYS:
        return _degrade(out, f'可用体重数据 {len(wv)} 天,不足 {MIN_DAYS} 天,无法诊断反弹。')
    recent = wv[-7:]
    delta = round(recent[-1] - recent[0], 2) if len(recent) >= 2 else None
    rebound = delta is not None and delta > 0.5
    out['findings'].append({
        'cause': '反弹程度',
        'evidence': f'最近 7 天体重从 {recent[0]} → {recent[-1]} kg,变化 {delta:+.2f} kg',
        'confidence': '高' if rebound else '中',
        'action': ('反弹超过 0.5 kg:回看近 1 周摄入/饮水/盐分/压力睡眠,区分真反弹与水分滞留'
                   if rebound else '近 7 天变化在正常波动内'),
    })
    # 反弹期摄入 vs 反弹前
    cal_now = series_avg(series[-7:], 'calories')
    cal_before = series_avg(series[-14:-7], 'calories')
    if cal_now and cal_before:
        out['findings'].append({
            'cause': '摄入变化',
            'evidence': f'反弹期日均摄入 {cal_now} 卡 vs 前 7 天 {cal_before} 卡(Δ{cal_now - cal_before:+.0f})',
            'confidence': '中',
            'action': '若摄入明显上升,反弹来自热量盈余;若摄入持平,先考虑水分/盐分',
        })
    out['insight'] = ('⚠️ 近 7 天反弹 ' + f'{delta:+.2f} kg,需区分真反弹与水分。' if rebound
                      else '近 7 天无实质反弹。')
    return out


def _diag_weight_loss_cause(series: list[dict]) -> dict:
    out = _base(series, 'weight_loss_cause', '诊断体重下降原因')
    wv = _weight_vals(series)
    if len(wv) < PRED_MIN:
        return _degrade(out, f'可用体重数据 {len(wv)} 天,不足 {PRED_MIN} 天,无法评估速度。')
    total_delta = series_delta(series, 'weight_kg') or 0
    days = (datetime.strptime(out['end'], '%Y-%m-%d') - datetime.strptime(out['start'], '%Y-%m-%d')).days or 1
    rate = total_delta / days * 7  # kg/周
    healthy = 0.5 <= rate <= 1.0
    out['findings'].append({
        'cause': '减重速度',
        'evidence': f'窗口内体重净变化 {total_delta:+.2f} kg,折合 {rate:+.2f} kg/周(健康范围 0.5-1.0)',
        'confidence': '高',
        'action': ('速度在健康范围' if healthy else
                   ('速度偏慢:缺口不足或摄入估算偏高' if rate < 0.5 else '⚠️ 速度过快:可能肌肉流失/摄入过低')),
    })
    avg_cal = series_avg(series, 'calories')
    deficit = series_avg(series, 'deficit')
    if avg_cal:
        out['findings'].append({
            'cause': '摄入端',
            'evidence': f'日均摄入 {avg_cal} 卡,日均缺口 {deficit or 0:+.0f} 卡',
            'confidence': '中',
            'action': '缺口主要来自饮食控制,注意蛋白 ≥ 1.2 g/kg 保护肌肉',
        })
    ex_avg = series_avg(series, 'exercise_kcal')
    if ex_avg:
        out['findings'].append({
            'cause': '运动端',
            'evidence': f'日均运动消耗 {ex_avg} 卡',
            'confidence': '中',
            'action': '运动贡献占比较小时,减重主要靠饮食缺口',
        })
    out['insight'] = f'减重速度 {rate:+.2f} kg/周,{"处于健康范围。" if healthy else ("偏慢,建议检查实际缺口。" if rate < 0.5 else "偏快,建议上调摄入保护肌肉。")}'
    return out


def _diag_weight_anomaly(series: list[dict]) -> dict:
    out = _base(series, 'weight_anomaly', '诊断体重异常点')
    wv = _weight_vals(series)
    if len(wv) < MIN_DAYS:
        return _degrade(out, f'可用体重数据 {len(wv)} 天,不足 {MIN_DAYS} 天,无法找异常点。')
    avg = sum(wv) / len(wv)
    std = _std(wv)
    points = []
    for s in series:
        if s.get('weight_kg') is None:
            continue
        z = (s['weight_kg'] - avg) / std if std else 0
        if abs(z) > 1.5:
            points.append({'date': s['date'], 'weight': s['weight_kg'],
                           'z': round(z, 2),
                           'guess': ('偏高' if z > 0 else '偏低')})
    out['findings'].append({
        'cause': '异常点检测(偏离均值 >1.5σ)',
        'evidence': f'窗口内均值 {round(avg, 2)} kg,σ={std},检出 {len(points)} 个异常点' if points
                    else f'窗口内均值 {round(avg, 2)} kg,σ={std},无显著异常点',
        'confidence': '中',
        'action': '异常点先核对当日是否有聚餐/饮酒/腹泻/称重时间不同,勿当作趋势信号',
    })
    for p in points[:5]:
        out['findings'].append({
            'cause': f'异常点 {p["date"]}',
            'evidence': f'{p["weight"]} kg(偏离 {p["z"]}σ,{p["guess"]})',
            'confidence': '中',
            'action': '回看当天饮食/饮水/盐分记录确认成因',
        })
    out['insight'] = f'共检出 {len(points)} 个异常点' if points else '未发现显著异常体重点。'
    return out


def _diag_weight_divergence(series: list[dict]) -> dict:
    out = _base(series, 'weight_divergence', '诊断体重 vs 体脂围度背离')
    wv = _weight_vals(series)
    bf = [s['body_fat_pct'] for s in series if s.get('body_fat_pct') is not None]
    wa = [s['waist_cm'] for s in series if s.get('waist_cm') is not None]
    if len(wv) < MIN_DAYS or (len(bf) < 2 and len(wa) < 2):
        return _degrade(out, '需要 ≥2 个体脂或围度样本才能做背离检测。')
    w_delta = series_delta(series, 'weight_kg')
    if len(bf) >= 2:
        bf_delta = round(bf[-1] - bf[0], 2)
        divergence = (w_delta is not None and w_delta < -0.3 and bf_delta > -0.5)
        out['findings'].append({
            'cause': '体重 vs 体脂',
            'evidence': f'体重 {w_delta:+.2f} kg,体脂率 {bf_delta:+.2f} 个百分点({bf[0]}% → {bf[-1]}%)',
            'confidence': '中',
            'action': ('⚠️ 体重降但体脂未同步降:可能在流失水分/肌肉,检查蛋白摄入与力量训练'
                       if divergence else '体重与体脂同向变化,脂肪确实在减少'),
        })
    if len(wa) >= 2:
        wa_delta = round(wa[-1] - wa[0], 2)
        out['findings'].append({
            'cause': '体重 vs 腰围',
            'evidence': f'腰围 {wa_delta:+.2f} cm({wa[0]} → {wa[-1]} cm)',
            'confidence': '中',
            'action': '腰围下降 = 内脏脂肪减少,即使体重波动也值得肯定',
        })
    out['insight'] = '体重与体脂围度基本同步' if not any(
        f.get('cause', '').startswith('⚠️') for f in out['findings']) else '存在体重与体脂围度背离信号。'
    return out


# ---------- 饮食诊断 4 ----------

def _diag_diet_over(series: list[dict]) -> dict:
    out = _base(series, 'diet_over', '诊断饮食超标')
    goal = series[0].get('calorie_goal') or 1800
    over_days = [(s['date'], s['calories']) for s in series
                 if s.get('calories') is not None and s['calories'] > goal * 1.1]
    avg = series_avg(series, 'calories')
    out['findings'].append({
        'cause': '超标日统计',
        'evidence': f'日均摄入 {avg or "—"} 卡 vs 目标 {goal} 卡;超标 >10% 共 {len(over_days)} 天',
        'confidence': '高',
        'action': '把超标日挑出来看共同的场景(外食/聚餐/零食),针对场景设规则',
    })
    if over_days:
        tops = _top_foods(out['start'], out['end'], 'calories')
        top_text = '、'.join(f'{t["food"]}(累计{t["total"]:.0f}卡)' for t in tops[:3])
        out['findings'].append({
            'cause': '超标来源食物',
            'evidence': f'热量来源 TOP: {top_text}',
            'confidence': '中',
            'action': '对 TOP 食物考虑替换或控量(先记后吃,避免无意识进食)',
        })
    else:
        out['findings'].append({
            'cause': '超标来源食物',
            'evidence': '窗口内无持续超标日',
            'confidence': '中',
            'action': '维持现状,注意别在疲惫/情绪波动日破功',
        })
    out['insight'] = f'日均摄入 {avg or "—"} 卡,超标日 {len(over_days)} 天,{"注意规律性超标。" if over_days else "总体在目标附近。"}'
    return out


def _diag_diet_under(series: list[dict]) -> dict:
    out = _base(series, 'diet_under', '诊断饮食不足')
    tdee = series[0].get('tdee') or 1800
    bmr = round(tdee / get_activity_factor(), 1)
    under_bmr = [(s['date'], s['calories']) for s in series
                 if s.get('calories') is not None and s['calories'] < bmr * 0.95]
    avg = series_avg(series, 'calories')
    out['findings'].append({
        'cause': '低于 BMR 天数',
        'evidence': f'估算 BMR {bmr} 卡,摄入低于 BMR 共 {len(under_bmr)} 天;日均摄入 {avg or "—"} 卡',
        'confidence': '高',
        'action': ('⚠️ 摄入长期低于 BMR 会掉代谢+肌肉:把缺口上限控制在 BMR 之上'
                   if len(under_bmr) >= 3 else '偶尔 1-2 天低摄入可接受,不建议连续'),
    })
    protein = series_avg(series, 'protein')
    if protein:
        out['findings'].append({
            'cause': '蛋白保障',
            'evidence': f'日均蛋白 {protein} g(目标参考:体重 kg × 1.2-1.6 g)',
            'confidence': '中',
            'action': '低摄入期更要保蛋白,优先保证每餐蛋白到位',
        })
    out['insight'] = f'日均摄入 {avg or "—"} 卡,BMR 以下 {len(under_bmr)} 天,{"需警惕代谢损伤。" if len(under_bmr) >= 3 else "风险可控。"}'
    return out


def _diag_diet_unbalanced(series: list[dict]) -> dict:
    out = _base(series, 'diet_unbalanced', '诊断营养不均衡(含均衡判断)')
    p = series_avg(series, 'protein') or 0
    c = series_avg(series, 'carbs') or 0
    f = series_avg(series, 'fat') or 0
    total = p * 4 + c * 4 + f * 9
    if total <= 0:
        return _degrade(out, '窗口内无营养数据,无法判断均衡度。')
    shares = {
        '蛋白': round(p * 4 / total * 100, 1),
        '碳水': round(c * 4 / total * 100, 1),
        '脂肪': round(f * 9 / total * 100, 1),
    }
    ref = {'蛋白': (15, 30), '碳水': (40, 60), '脂肪': (20, 35)}
    off = [k for k in shares if not (ref[k][0] <= shares[k] <= ref[k][1])]
    out['findings'].append({
        'cause': '三大营养占比',
        'evidence': f'蛋白 {shares["蛋白"]}% / 碳水 {shares["碳水"]}% / 脂肪 {shares["脂肪"]}%(参考 蛋白15-30 碳水40-60 脂肪20-35)',
        'confidence': '中',
        'action': ('失衡维度:' + '、'.join(off) + ',针对性调整(蛋白不足→加蛋奶豆肉;碳水过高→减精制碳水;脂肪过高→减油/油炸)'
                   if off else '三大营养占比在均衡范围'),
    })
    sodium = [s['sodium_mg'] for s in series if s.get('sodium_mg') is not None]
    if sodium:
        na = sum(sodium) / len(sodium)
        out['findings'].append({
            'cause': '钠摄入',
            'evidence': f'日均钠 {na:.0f} mg(参考 ≤2000 mg)',
            'confidence': '中',
            'action': '超参考值注意减盐;未超则保持',
        })
    out['insight'] = '三大营养占比均衡' if not off else f'营养占比失衡:{"、".join(off)}。'
    return out


def _diag_diet_structure(series: list[dict]) -> dict:
    out = _base(series, 'diet_structure', '诊断饮食结构问题')
    meals = _meal_structure(out['start'], out['end'])
    late = meals['加餐/夜宵']
    out['findings'].append({
        'cause': '餐次结构',
        'evidence': '、'.join(f'{k} {v["times"]} 次({v["share"]}%)' for k, v in meals.items()),
        'confidence': '中',
        'action': ('夜宵/加餐占比 {late["share"]}%:夜宵最容易累积盈余,尝试睡前 3h 不进食'
                   if late['share'] >= 20 else '餐次分布较合理,注意早餐别跳过'),
    })
    # 跳跃式进食:单日仅 1-2 餐
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT date, COUNT(*) AS n FROM food_log "
            "WHERE date BETWEEN ? AND ? AND food_name != '💧水' GROUP BY date",
            (out['start'], out['end']),
        ).fetchall()
        sparse = [r[0] for r in rows if r[1] <= 1]
    finally:
        conn.close()
    out['findings'].append({
        'cause': '进食频率',
        'evidence': f'单日仅 1 餐的记录 {len(sparse)} 天' + (f'(如 {"、".join(sparse[:5])})' if sparse else ''),
        'confidence': '中',
        'action': '单日 1 餐容易导致后续暴食,保持 3 餐 + 必要时 1-2 次健康加餐',
    })
    out['insight'] = f'夜宵/加餐占 {late["share"]}%,单日一餐 {len(sparse)} 天,结构{"基本合理" if late["share"] < 20 and not sparse else "有改善空间"}。'
    return out


# ---------- 运动诊断 5 ----------

def _diag_exercise_insufficient(series: list[dict]) -> dict:
    out = _base(series, 'exercise_insufficient', '诊断运动不足')
    days = len(series)
    weeks = max(days / 7, 1)
    ex_days = sum(1 for s in series if (s.get('exercise_kcal') or 0) > 0)
    freq = round(ex_days / weeks, 1)
    avg_kcal = series_avg(series, 'exercise_kcal') or 0
    out['findings'].append({
        'cause': '运动频率',
        'evidence': f'窗口 {days} 天运动 {ex_days} 天,折合 {freq}/周(建议 3-5 次/周)',
        'confidence': '高',
        'action': '频率不足时先从 2-3 次/周快走/骑行开始,固定时间比强度重要',
    })
    out['findings'].append({
        'cause': '运动消耗',
        'evidence': f'日均运动消耗 {avg_kcal} 卡',
        'confidence': '中',
        'action': '每周目标 150 分钟中等强度,或日均消耗 150-250 卡',
    })
    out['insight'] = f'运动 {freq}/周,{"不达标,建议提到 3 次以上。" if freq < 3 else "频率达标,保持。"}'
    return out


def _diag_exercise_overload(series: list[dict]) -> dict:
    out = _base(series, 'exercise_overload', '诊断运动过量')
    rows = _exercise_rows(out['start'], out['end'])
    if not rows:
        return _degrade(out, '窗口内无运动记录,无需诊断过量。')
    # 连续训练:≥7 天每天都有运动
    dates = sorted({r['date'] for r in rows})
    streak, max_streak = 1, 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i - 1], '%Y-%m-%d')
        d2 = datetime.strptime(dates[i], '%Y-%m-%d')
        streak = streak + 1 if (d2 - d1).days <= 1 else 1
        max_streak = max(max_streak, streak)
    over = max_streak >= 7
    out['findings'].append({
        'cause': '连续训练检测',
        'evidence': f'最长连续运动 {max_streak} 天(建议每周至少 1 个休息日)',
        'confidence': '高',
        'action': ('⚠️ 连续 {max_streak} 天训练:插入 1-2 个主动恢复日(拉伸/散步),防止过度训练'
                   if over else '训练节奏有休息日,合理'),
    })
    out['insight'] = f'最长连续运动 {max_streak} 天,{"存在过量风险。" if over else "节奏合理。"}'
    return out


def _diag_exercise_type_imbalance(series: list[dict]) -> dict:
    out = _base(series, 'exercise_type_imbalance', '诊断运动类型失衡')
    rows = _exercise_rows(out['start'], out['end'])
    if not rows:
        return _degrade(out, '窗口内无运动记录,无法分析类型分布。')
    by_cat: dict[str, dict] = {}
    for r in rows:
        cat = r['category'] or '有氧'
        d = by_cat.setdefault(cat, {'times': 0, 'kcal': 0, 'minutes': 0})
        d['times'] += 1
        d['kcal'] += r['kcal']
        d['minutes'] += r['minutes'] or 0
    total_times = sum(v['times'] for v in by_cat.values())
    dist = {k: {'times': v['times'], 'share': round(v['times'] / total_times * 100, 1),
                'kcal': v['kcal']} for k, v in by_cat.items()}
    strength_share = dist.get('力量', {}).get('share', 0)
    out['findings'].append({
        'cause': '类型占比',
        'evidence': '、'.join(f'{k} {v["share"]}%({v["times"]}次)' for k, v in dist.items()),
        'confidence': '中',
        'action': ('力量训练占比 {strength_share}%:增肌/保肌建议力量占 40-50%,有氧 30-40%,柔韧 10-20%'
                   if strength_share < 30 else '力量与有氧搭配较均衡'),
    })
    out['insight'] = f'力量 {strength_share}%,{"有氧为主,建议补力量训练。" if strength_share < 30 else "搭配均衡。"}'
    return out


def _diag_exercise_efficiency(series: list[dict]) -> dict:
    out = _base(series, 'exercise_efficiency', '诊断运动效率(含有效判断)')
    rows = _exercise_rows(out['start'], out['end'])
    if not rows:
        return _degrade(out, '窗口内无运动记录,无法评估效率。')
    total_kcal = sum(r['kcal'] for r in rows)
    total_min = sum(r['minutes'] or 0 for r in rows)
    eff = round(total_kcal / total_min, 1) if total_min else None
    by_cat: dict[str, list] = {}
    for r in rows:
        by_cat.setdefault(r['category'] or '有氧', []).append(r)
    cat_eff = {k: round(sum(r['kcal'] for r in v) / (sum(r['minutes'] or 0 for r in v) or 1), 1)
               for k, v in by_cat.items()}
    out['findings'].append({
        'cause': '单位时长消耗',
        'evidence': f'平均 {eff or "—"} 卡/分钟(有氧常见 7-11 卡/分;力量按组算偏低属正常)' + (f';分类: {cat_eff}' if cat_eff else ''),
        'confidence': '中',
        'action': '偏低时优先看强度(是否只是散步)与时长记录是否完整',
    })
    out['insight'] = f'单位消耗 {eff or "—"} 卡/分,{"效率正常。" if eff and eff >= 6 else "效率偏低,建议提高强度或确认时长。"}'
    return out


def _diag_exercise_advice(series: list[dict]) -> dict:
    out = _base(series, 'exercise_advice', '诊断运动建议(含类型推荐)')
    rows = _exercise_rows(out['start'], out['end'])
    by_cat: dict[str, int] = {}
    for r in rows:
        cat = r['category'] or '有氧'
        by_cat[cat] = by_cat.get(cat, 0) + 1
    strength_share = by_cat.get('力量', 0) / (sum(by_cat.values()) or 1)
    out['findings'].append({
        'cause': '类型推荐',
        'evidence': f'当前力量占比 {round(strength_share * 100)}%,有氧为主' if strength_share < 0.3
                    else '力量与有氧已有搭配',
        'confidence': '中',
        'action': ('推荐每周 2 次力量(深蹲/卧推/划船 3 大项)+ 2 次有氧(快走/单车 30-40 分钟),力量优先补上'
                   if strength_share < 0.3 else '维持现有搭配,尝试每周加 1 次高强度间歇(20 分钟)'),
    })
    out['insight'] = '建议补力量训练' if strength_share < 0.3 else '建议加入高强度间歇突破平台。'
    return out


# ---------- 综合诊断 8 ----------

def _common_overall(series: list[dict], kind: str, title: str) -> dict:
    """综合诊断共用取证:摄入/运动/体重/缺口 四个维度的现状"""
    out = _base(series, kind, title)
    wv = _weight_vals(series)
    out['findings'].append({
        'cause': '体重',
        'evidence': f'{"→".join(str(x) for x in [wv[0], wv[-1]])} kg(Δ{series_delta(series, "weight_kg"):+.2f})' if len(wv) >= 2 else '体重样本不足',
        'confidence': '中' if len(wv) >= 2 else '低',
        'action': '',
    })
    avg_cal = series_avg(series, 'calories')
    goal = series[0].get('calorie_goal')
    if avg_cal:
        out['findings'].append({
            'cause': '摄入',
            'evidence': f'日均 {avg_cal} 卡 vs 目标 {goal} 卡(Δ{avg_cal - goal:+.0f})',
            'confidence': '中',
            'action': '',
        })
    ex = series_avg(series, 'exercise_kcal')
    if ex:
        out['findings'].append({
            'cause': '运动',
            'evidence': f'日均消耗 {ex} 卡',
            'confidence': '中',
            'action': '',
        })
    df = series_avg(series, 'deficit')
    if df:
        out['findings'].append({
            'cause': '缺口',
            'evidence': f'日均缺口 {df:+.0f} 卡(减重需要每日 +300~+500)',
            'confidence': '中',
            'action': '',
        })
    return out


def _diag_why_not_losing(series: list[dict]) -> dict:
    out = _common_overall(series, 'why_not_losing', '为什么我没瘦')
    if len(_weight_vals(series)) < MIN_DAYS:
        return _degrade(out, '体重数据不足,先连续记录 1 周以上再诊断。')
    df = series_avg(series, 'deficit')
    if df is None or df < 100:
        out['findings'].append({
            'cause': '缺口不足或为负',
            'evidence': f'日均缺口 {df or 0:+.0f} 卡(减重需 +300~+500)',
            'confidence': '高',
            'action': '先恢复缺口:(TDEE + 运动) − 摄入 ≥ 300 卡。常见偷吃:液体热量/酱料/坚果',
        })
    else:
        out['findings'].append({
            'cause': '缺口存在但体重不动',
            'evidence': f'日均缺口 {df:+.0f} 卡',
            'confidence': '中',
            'action': '缺口存在仍不动:检查称重条件是否统一、是否在平台期(14 天 ±0.5kg)、是否水肿(高钠/经期)',
        })
    out['findings'].append({
        'cause': '优先级',
        'evidence': '缺口 > 蛋白 > 运动 > 睡眠',
        'confidence': '高',
        'action': '按优先级逐项排查,别同时改 5 个变量',
    })
    out['insight'] = '核心先看日均缺口是否真的为正;缺口为正仍不动再看平台期/水分。'
    return out


def _diag_why_losing_fast(series: list[dict]) -> dict:
    out = _common_overall(series, 'why_losing_fast', '为什么我瘦太快')
    wv = _weight_vals(series)
    if len(wv) < PRED_MIN:
        return _degrade(out, '体重数据不足 14 天,无法评估速度。')
    total = series_delta(series, 'weight_kg') or 0
    days = (datetime.strptime(out['end'], '%Y-%m-%d') - datetime.strptime(out['start'], '%Y-%m-%d')).days or 1
    rate = total / days * 7
    out['findings'].append({
        'cause': '减重速度',
        'evidence': f'{rate:+.2f} kg/周(健康范围 0.5-1.0;>1.5 为过快)',
        'confidence': '高',
        'action': ('⚠️ 每周 >1.5kg:多来自水分/肌肉流失,尽快上调摄入 200-300 卡,保蛋白 1.6g/kg'
                   if rate > 1.5 else '速度在健康范围,不必担心'),
    })
    avg_cal = series_avg(series, 'calories')
    tdee = series[0].get('tdee')
    if avg_cal and tdee and avg_cal < tdee * 0.6:
        out['findings'].append({
            'cause': '摄入过低',
            'evidence': f'日均摄入 {avg_cal} 卡,仅为 TDEE({tdee})的 {avg_cal / tdee * 100:.0f}%',
            'confidence': '中',
            'action': '摄入低于 TDEE 60% 会掉代谢:逐步加回,每周 +100 卡',
        })
    out['insight'] = f'速度 {rate:+.2f} kg/周,{"过快,需要立即调整。" if rate > 1.5 else "正常。"}'
    return out


def _diag_rate_reasonable(series: list[dict]) -> dict:
    out = _common_overall(series, 'rate_reasonable', '我的减重速度合理吗')
    wv = _weight_vals(series)
    if len(wv) < PRED_MIN:
        return _degrade(out, '体重数据不足 14 天,无法评估速度。')
    total = series_delta(series, 'weight_kg') or 0
    days = (datetime.strptime(out['end'], '%Y-%m-%d') - datetime.strptime(out['start'], '%Y-%m-%d')).days or 1
    rate = total / days * 7
    verdict = ('偏快' if rate > 1.0 else '健康范围' if rate >= 0.5 else '偏慢')
    out['findings'].append({
        'cause': '速度判定',
        'evidence': f'{rate:+.2f} kg/周 → {verdict}(健康范围 0.5-1.0 kg/周)',
        'confidence': '高',
        'action': {'偏快': '适当上调摄入,优先保住肌肉',
                   '健康范围': '保持当前节奏,规律记录即可',
                   '偏慢': '检查缺口是否 ≥300 卡,是否漏记了加餐'}[verdict],
    })
    out['insight'] = f'当前速度 {rate:+.2f} kg/周,判定为「{verdict}」。'
    return out


def _diag_strategy_check(series: list[dict]) -> dict:
    out = _common_overall(series, 'strategy_check', '我的减肥策略对吗')
    wv = _weight_vals(series)
    if len(wv) < PRED_MIN:
        return _degrade(out, '数据不足 14 天,策略评估先积累数据。')
    df = series_avg(series, 'deficit')
    p = series_avg(series, 'protein')
    ex = series_avg(series, 'exercise_kcal')
    ok_checks = []
    if df is not None and 100 <= df <= 500:
        ok_checks.append('缺口策略合理')
    elif df is not None and df > 800:
        ok_checks.append('⚠️ 缺口过大(>800 卡):可持续性差')
    else:
        ok_checks.append('⚠️ 缺口不足(需 +300~+500 卡)')
    weight = _weight_vals(series)[-1]
    if p and weight:
        ok_checks.append('蛋白达标' if p >= weight * 1.2 else '⚠️ 蛋白不足(建议 ≥1.2g/kg)')
    ok_checks.append('运动有贡献' if ex and ex > 0 else '⚠️ 纯靠饮食,建议加力量')
    out['findings'].append({
        'cause': '策略体检',
        'evidence': ';'.join(ok_checks),
        'confidence': '中',
        'action': '对 ⚠️ 项逐一修正;减脂期最稳的公式:TDEE 以下 300-500 卡 + 蛋白足量 + 每周 2-3 次力量',
    })
    out['insight'] = '策略总体合理' if not any('⚠️' in c for c in ok_checks) else '存在 ' + '、'.join(c.split('⚠️ ')[1] for c in ok_checks if '⚠️' in c) + ' 问题。'
    return out


def _diag_gap_to_goal(series: list[dict]) -> dict:
    out = _common_overall(series, 'gap_to_goal', '我距离目标还差什么')
    conn = _get_db()
    try:
        g = conn.execute(
            "SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1"
        ).fetchone()
    finally:
        conn.close()
    wv = _weight_vals(series)
    if not g or g[0] is None:
        out['findings'].append({
            'cause': '目标未设置',
            'evidence': '还没有体重目标',
            'confidence': '高',
            'action': '先定一个目标体重(建议先设最近 1-2 个月可达到的小目标)',
        })
        out['insight'] = '先设置目标体重,再谈差距。'
        return out
    goal_w = g[0]
    current = wv[-1] if wv else None
    if current is None:
        return _degrade(out, '缺少近期体重记录。')
    gap = round(current - goal_w, 1)
    rate = series_delta(series, 'weight_kg')
    days = (datetime.strptime(out['end'], '%Y-%m-%d') - datetime.strptime(out['start'], '%Y-%m-%d')).days or 1
    weekly = (rate or 0) / days * 7
    weeks_left = (gap / weekly) if weekly > 0 else None
    out['findings'].append({
        'cause': '目标差距',
        'evidence': f'当前 {current} kg vs 目标 {goal_w} kg,还差 {gap:+.1f} kg' + (f',按当前速度约需 {weeks_left:.0f} 周' if weeks_left else ',当前速度无法估算'),
        'confidence': '高',
        'action': '把大目标拆成每周 0.5kg 的小里程碑,每周只盯一个小目标',
    })
    out['insight'] = f'距目标还差 {abs(gap):.1f} kg。'
    return out


def _diag_month_highlights(series: list[dict]) -> dict:
    out = _base(series, 'month_highlights', '我这个月做得好的')
    wv = _weight_vals(series)
    items = []
    if len(wv) >= 2 and series_delta(series, 'weight_kg') < 0:
        items.append(f'体重下降 {abs(series_delta(series, "weight_kg")):.2f} kg')
    days_with = sum(1 for s in series if (s.get('exercise_kcal') or 0) > 0)
    if days_with >= 8:
        items.append(f'运动 {days_with} 天')
    goal = series[0].get('calorie_goal')
    under = sum(1 for s in series if s.get('calories') is not None and s['calories'] <= (goal or 1800))
    if under >= 15:
        items.append(f'{under} 天摄入在目标内')
    if not items:
        items.append('本月暂无亮点,从记录完整度开始(连续记录本身就该表扬)')
    out['findings'].append({'cause': '本月亮点', 'evidence': ';'.join(items), 'confidence': '中',
                            'action': '把做得好的行为固定成习惯(时间/场景/频率),下月复制'})
    out['insight'] = '本月亮点:' + '、'.join(items) + '。'
    return out


def _diag_month_improve(series: list[dict]) -> dict:
    out = _base(series, 'month_improve', '我这个月需要改的')
    goal = series[0].get('calorie_goal') or 1800
    over = sum(1 for s in series if s.get('calories') is not None and s['calories'] > goal * 1.1)
    ex_days = sum(1 for s in series if (s.get('exercise_kcal') or 0) > 0)
    items = []
    if over >= 5:
        items.append(f'超标日 {over} 天')
    if ex_days < 8:
        items.append(f'运动仅 {ex_days} 天')
    water = [s['water_ml'] for s in series if s.get('water_ml') is not None]
    if water and sum(1 for w in water if w < 1500) >= 10:
        items.append('饮水量偏少')
    if not items:
        items.append('各项指标均正常,下月可挑战更高目标')
    out['findings'].append({'cause': '待改进项', 'evidence': ';'.join(items), 'confidence': '中',
                            'action': '挑 1 个最影响结果的先改,改稳了再动下一个'})
    out['insight'] = '下月改进:' + '、'.join(items) + '。'
    return out


def _diag_overall(series: list[dict]) -> dict:
    out = _common_overall(series, 'overall', '综合健康评估')
    wv = _weight_vals(series)
    if len(wv) < MIN_DAYS:
        return _degrade(out, '数据不足:至少需要 7 天体重 + 任意摄入/运动记录。')
    total = series_delta(series, 'weight_kg') or 0
    df = series_avg(series, 'deficit')
    ex = series_avg(series, 'exercise_kcal') or 0
    scores = []
    if total <= -0.3:
        scores.append('体重维度 ✅ 在下降')
    elif total >= 0.3:
        scores.append('体重维度 ⚠️ 在上升')
    else:
        scores.append('体重维度 ➖ 基本持平')
    scores.append('缺口维度 ✅ 在缺口' if (df or 0) > 0 else '缺口维度 ⚠️ 无缺口')
    scores.append('运动维度 ✅ 有规律运动' if ex >= 50 else '运动维度 ⚠️ 运动偏少')
    p = series_avg(series, 'protein')
    scores.append('蛋白维度 ✅ 充足' if p and p >= 70 else '蛋白维度 ⚠️ 偏低')
    out['findings'].append({'cause': '八维体检', 'evidence': ';'.join(scores), 'confidence': '中',
                            'action': '按 ⚠️ 维度优先改进,每个周期只改 1-2 项'})
    # 优先级排序
    pri = [f.split('维度')[0] for f in scores if '⚠️' in f]
    out['findings'].append({'cause': '优先级', 'evidence': '>'.join(pri) if pri else '无短板',
                            'confidence': '中', 'action': '先补缺口,再补运动,最后补蛋白'})
    out['insight'] = '综合评估:' + (';'.join(scores)) + '。'
    return out


# ---------- 分发 ----------

DIAGNOSTICS: dict[str, callable] = {
    # 体重诊断 6
    'weight_volatility':  _diag_weight_volatility,
    'weight_plateau':     _diag_weight_plateau,
    'weight_rebound':     _diag_weight_rebound,
    'weight_loss_cause':  _diag_weight_loss_cause,
    'weight_anomaly':     _diag_weight_anomaly,
    'weight_divergence':  _diag_weight_divergence,
    # 饮食诊断 4
    'diet_over':          _diag_diet_over,
    'diet_under':         _diag_diet_under,
    'diet_unbalanced':    _diag_diet_unbalanced,
    'diet_structure':     _diag_diet_structure,
    # 运动诊断 5
    'exercise_insufficient':      _diag_exercise_insufficient,
    'exercise_overload':          _diag_exercise_overload,
    'exercise_type_imbalance':    _diag_exercise_type_imbalance,
    'exercise_efficiency':        _diag_exercise_efficiency,
    'exercise_advice':            _diag_exercise_advice,
    # 综合诊断 8
    'why_not_losing':     _diag_why_not_losing,
    'why_losing_fast':    _diag_why_losing_fast,
    'rate_reasonable':    _diag_rate_reasonable,
    'strategy_check':     _diag_strategy_check,
    'gap_to_goal':        _diag_gap_to_goal,
    'month_highlights':   _diag_month_highlights,
    'month_improve':      _diag_month_improve,
    'overall':            _diag_overall,
}


def diagnose(kind: str, series: list[dict]) -> dict:
    """诊断主入口"""
    if kind not in DIAGNOSTICS:
        raise ValueError(f'未知诊断 {kind},可选: {", ".join(DIAGNOSTICS)}')
    return DIAGNOSTICS[kind](series)
