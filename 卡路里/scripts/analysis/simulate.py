#!/usr/bin/env python3
"""analysis/simulate.py — 预测模拟(ticket #10 · 分析 A6 20 场景)

预测模型:线性外推 + 置信区间(±2σ 按 sqrt(天数) 扩张)
硬规则:< 14 天数据不预测(数据不足降级,degraded=True)。

  A6.1 预测体重 6   kind: weight_forecast(1周/1月/3月/6月/自定义时间/自定义目标)
  A6.2 模拟减重 7   kind: weight_sim_cut(-300/-500/-700) / weight_sim_target(30/60/90/自定义天减X kg)
  A6.3 摄入预测 7   kind: calorie_forecast(1周/1月/3月/自定义) / calorie_goal / calorie_deficit / calorie_stability
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from analysis.series import series_avg  # noqa: E402

MIN_DAYS = 14
KCAL_PER_KG = 7700  # 减 1kg 脂肪 ≈ 7700 卡
HEALTHY_RATE = (0.5, 1.0)  # kg/周


def _degrade(kind: str, title: str, series: list[dict], need: str) -> dict:
    return {
        'kind': kind, 'title': title, 'degraded': True,
        'degrade_msg': f'数据不足:需要 {need},当前只有 {len(series)} 天。',
        'series': [], 'insight': '数据不足,无法预测。',
    }


def _linear_rate(series: list[dict], field: str) -> tuple[float | None, float | None]:
    """线性回归斜率(每日变化)+ 当前值。返回 (rate_per_day, latest_value)"""
    vals = [(datetime.strptime(s['date'], '%Y-%m-%d').toordinal(), s[field])
            for s in series if s.get(field) is not None]
    if len(vals) < 2:
        return None, (vals[-1][1] if vals else None)
    xs = [v[0] for v in vals]
    ys = [v[1] for v in vals]
    n = len(xs)
    sx = sum(xs); sy = sum(ys); sxy = sum(x * y for x, y in vals); sx2 = sum(x * x for x in xs)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return None, ys[-1]
    slope = (n * sxy - sx * sy) / denom
    return slope, ys[-1]


def _residual_std(series: list[dict], field: str, slope: float) -> float:
    """残差标准差(每日波动 σ)"""
    vals = [(datetime.strptime(s['date'], '%Y-%m-%d').toordinal(), s[field])
            for s in series if s.get(field) is not None]
    if len(vals) < 3:
        return 0.0
    base = vals[0][0]
    resid = [y - (vals[0][1] + slope * (x - base)) for x, y in vals]
    m = sum(resid) / len(resid)
    return (sum((r - m) ** 2 for r in resid) / (len(resid) - 1)) ** 0.5


def _forecast_series(current: float, rate_per_day: float, sigma: float, horizon_days: int,
                     start_date: str, label: str) -> dict:
    """生成预测序列(今日 + 每 7 天一个点)"""
    pts = [{'date': start_date, 'value': round(current, 2), 'lo': round(current, 2), 'hi': round(current, 2)}]
    base = datetime.strptime(start_date, '%Y-%m-%d')
    for d in range(7, horizon_days + 1, 7):
        t = d
        v = current + rate_per_day * d
        band = 2 * sigma * (d ** 0.5) / (7 ** 0.5)  # 按周扩张
        day = (base + timedelta(days=d)).isoformat()
        pts.append({'date': day, 'value': round(v, 2),
                    'lo': round(v - band, 2), 'hi': round(v + band, 2)})
    return {'label': label, 'horizon_days': horizon_days, 'points': pts}


# ---------- A6.1 预测体重 ----------

def weight_forecast(series: list[dict], horizon_days: int, title: str, kind: str = 'weight_forecast') -> dict:
    wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
    if len(wv) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天体重记录')
    rate, latest = _linear_rate(series, 'weight_kg')
    if rate is None:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天有效体重记录')
    sigma = _residual_std(series, 'weight_kg', rate)
    fc = _forecast_series(latest, rate, sigma, horizon_days, series[-1]['date'], title)
    weekly = rate * 7
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'current': round(latest, 2), 'rate_per_week': round(weekly, 2),
        'rate_note': f'按近 {len(series)} 天线性趋势外推,当前 {weekly:+.2f} kg/周',
        'assumption': '假设趋势延续:体重 = 当前值 + 日速率 × 天数;置信带按残差 σ 扩张',
        'forecast': fc,
        'insight': f'按当前趋势,{horizon_days} 天后体重约 {fc["points"][-1]["value"]} kg'
                   f'({fc["points"][-1]["lo"]} ~ {fc["points"][-1]["hi"]},95% 置信带)。',
    }


def weight_target(series: list[dict], target_kg: float, title: str, kind: str = 'weight_target') -> dict:
    """自定义目标:按当前速率推算达成日期"""
    wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
    if len(wv) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天体重记录')
    rate, latest = _linear_rate(series, 'weight_kg')
    if rate is None or abs(rate) < 1e-6:
        return _degrade(kind, title, series, '体重处于平台期(无趋势)')
    days_left = (latest - target_kg) / rate
    if days_left < 0:
        return {'kind': kind, 'title': title, 'degraded': True,
                'degrade_msg': '目标体重与当前趋势方向相反(当前在上涨)。', 'insight': '先纠正趋势再预测。'}
    eta = (datetime.strptime(series[-1]['date'], '%Y-%m-%d') + timedelta(days=round(days_left))).isoformat()
    weekly = rate * 7
    feasible = HEALTHY_RATE[0] <= weekly <= HEALTHY_RATE[1]
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'current': round(latest, 2), 'target': target_kg, 'eta': eta,
        'days_left': round(days_left), 'rate_per_week': round(weekly, 2),
        'feasible': feasible,
        'assumption': f'按当前速率 {weekly:+.2f} kg/周 线性外推;健康范围 0.5-1.0 kg/周',
        'insight': f'按当前趋势,预计 {eta} 前后达到 {target_kg} kg'
                   + ('。' if feasible else ';⚠️ 当前速率超出健康范围,建议调整目标或策略。'),
    }


# ---------- A6.2 模拟减重 ----------

def weight_sim_cut(series: list[dict], cut_kcal: int, title: str, kind: str = 'weight_sim_cut') -> dict:
    """每天多减 X 卡的模拟:新缺口 = 当前缺口 + cut"""
    df_avg = series_avg(series, 'deficit')
    cal_avg = series_avg(series, 'calories')
    tdee = series[0].get('tdee') or 1800
    wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
    if not wv:
        return _degrade(kind, title, series, '至少 1 条体重记录')
    current = wv[-1]
    new_deficit = (df_avg or 0) + cut_kcal
    weekly_loss = new_deficit * 7 / KCAL_PER_KG
    horizon = 90
    pts = [{'date': series[-1]['date'], 'value': round(current, 2)}]
    base = datetime.strptime(series[-1]['date'], '%Y-%m-%d')
    for d in range(7, horizon + 1, 7):
        pts.append({'date': (base + timedelta(days=d)).isoformat(),
                    'value': round(current - weekly_loss * d / 7, 2)})
    feasible = HEALTHY_RATE[0] <= weekly_loss <= HEALTHY_RATE[1]
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'current': round(current, 2), 'cut_kcal': cut_kcal,
        'new_deficit': round(new_deficit, 0), 'weekly_loss': round(weekly_loss, 2),
        'feasible': feasible,
        'assumption': f'当前日均缺口 {df_avg or 0:+.0f} 卡,再每天多减 {cut_kcal} 卡'
                      f'(≈ 每周 {round(cut_kcal * 7 / KCAL_PER_KG, 2)} kg);90 天轨迹见下',
        'forecast': {'label': title, 'horizon_days': 90, 'points': pts},
        'insight': f'模拟 90 天:约减 {round(weekly_loss * 90 / 7, 1)} kg,'
                   f'速率 {weekly_loss:.2f} kg/周({"健康范围内" if feasible else "⚠️ 超出健康范围 0.5-1.0,建议减量"})。',
    }


def weight_sim_target(series: list[dict], target_kg: float, days: int, title: str,
                      kind: str = 'weight_sim_target') -> dict:
    """N 天减 X kg → 所需每日缺口 + 可行性"""
    wv = [s['weight_kg'] for s in series if s.get('weight_kg') is not None]
    if not wv:
        return _degrade(kind, title, series, '至少 1 条体重记录')
    current = wv[-1]
    weekly_rate = target_kg / (days / 7)
    needed_deficit = round(target_kg * KCAL_PER_KG / days)
    feasible = HEALTHY_RATE[0] <= weekly_rate <= HEALTHY_RATE[1]
    pts = [{'date': series[-1]['date'], 'value': round(current, 2)}]
    base = datetime.strptime(series[-1]['date'], '%Y-%m-%d')
    for d in range(7, days + 1, 7):
        pts.append({'date': (base + timedelta(days=d)).isoformat(),
                    'value': round(current - target_kg * min(d, days) / days, 2)})
    pts[-1]['value'] = round(current - target_kg, 2)
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'current': round(current, 2), 'target_loss': target_kg, 'days_target': days,
        'weekly_rate': round(weekly_rate, 2), 'needed_deficit': needed_deficit,
        'feasible': feasible,
        'assumption': f'{days} 天减 {target_kg} kg = 每周 {weekly_rate:.2f} kg,'
                      f'需日均缺口 {needed_deficit} 卡(≈ 每天少吃 2 碗米饭 + 30 分钟快走)',
        'forecast': {'label': title, 'horizon_days': days, 'points': pts},
        'insight': f'所需日均缺口 {needed_deficit} 卡,速率 {weekly_rate:.2f} kg/周'
                   f'({"可行,在健康范围内" if feasible else "⚠️ 不可行:超出每周 0.5-1.0 kg 安全范围,拉长时间或降低目标"})。',
    }


# ---------- A6.3 摄入预测 ----------

def calorie_forecast(series: list[dict], horizon_days: int, title: str,
                     kind: str = 'calorie_forecast') -> dict:
    cal = [s['calories'] for s in series if s.get('calories') is not None]
    if len(cal) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天摄入记录')
    rate, latest = _linear_rate(series, 'calories')
    sigma = _residual_std(series, 'calories', rate)
    fc = _forecast_series(latest, rate, sigma, horizon_days, series[-1]['date'], title)
    goal = series[0].get('calorie_goal')
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'current': round(latest, 0), 'goal': goal,
        'daily_rate': round(rate, 1),
        'assumption': f'按近 {len(series)} 天摄入趋势外推(日变化 {rate:+.1f} 卡/天)',
        'forecast': fc,
        'insight': f'{horizon_days} 天后日均摄入预计 {fc["points"][-1]["value"]:.0f} 卡'
                   f'(目标 {goal} 卡,{"" if goal and abs(fc["points"][-1]["value"] - goal) <= 100 else "⚠️ "}偏离 {abs((fc["points"][-1]["value"] or 0) - (goal or 0)):.0f} 卡)。',
    }


def calorie_goal_eta(series: list[dict], title: str, kind: str = 'calorie_goal') -> dict:
    """营养目标达成预测:当前摄入 vs 目标,缺口方向与达成判断"""
    cal = [s['calories'] for s in series if s.get('calories') is not None]
    if len(cal) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天摄入记录')
    avg = sum(cal) / len(cal)
    goal = series[0].get('calorie_goal') or 1800
    on_target = abs(avg - goal) <= goal * 0.1
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'avg': round(avg, 0), 'goal': goal, 'on_target': on_target,
        'gap': round(goal - avg, 0),
        'assumption': '目标 = daily_goal 表当日热量目标;达成判定 = 日均偏离 ≤10%',
        'insight': f'日均摄入 {avg:.0f} 卡 vs 目标 {goal} 卡,'
                   f'{"已在目标 ±10% 内 ✅" if on_target else ("⚠️ 超出目标 " + f"{avg - goal:.0f} 卡,先查超标日来源" if avg > goal else "⚠️ 低于目标,注意别低于 BMR")}。',
    }


def calorie_deficit_eta(series: list[dict], title: str, kind: str = 'calorie_deficit') -> dict:
    """卡路里缺口预测:当前缺口 → 每周减重估计"""
    df = [s['deficit'] for s in series if s.get('deficit') is not None]
    if len(df) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天摄入+运动记录')
    avg_df = sum(df) / len(df)
    weekly = avg_df * 7 / KCAL_PER_KG
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'avg_deficit': round(avg_df, 0), 'weekly_loss': round(weekly, 2),
        'assumption': '缺口 = 摄入 - (TDEE + 运动消耗);每 7700 卡 ≈ 1 kg',
        'insight': f'日均缺口 {avg_df:+.0f} 卡 → 每周约 {weekly:+.2f} kg'
                   f'({"健康范围内" if 0.3 <= weekly <= 1.2 else "⚠️ 缺口过大或不足,建议调整到 -300~-500 卡/天"})。',
    }


def calorie_stability(series: list[dict], title: str, kind: str = 'calorie_stability') -> dict:
    """摄入稳定性预测:σ>300 = 不稳定"""
    cal = [s['calories'] for s in series if s.get('calories') is not None]
    if len(cal) < MIN_DAYS:
        return _degrade(kind, title, series, f'≥{MIN_DAYS} 天摄入记录')
    avg = sum(cal) / len(cal)
    sigma = (sum((c - avg) ** 2 for c in cal) / (len(cal) - 1)) ** 0.5
    stable = sigma <= 300
    return {
        'kind': kind, 'title': title, 'degraded': False,
        'start': series[0]['date'], 'end': series[-1]['date'], 'days': len(series),
        'avg': round(avg, 0), 'sigma': round(sigma, 0), 'stable': stable,
        'assumption': '稳定性判据:σ ≤ 300 卡 = 稳定;σ > 300 = 摄入忽高忽低',
        'insight': f'摄入波动 σ = {sigma:.0f} 卡(日均 {avg:.0f}),'
                   f'{"稳定,按当前节奏预测可信度较高" if stable else "⚠️ 波动大:预测可信度低,先规律化进食(固定三餐+加餐)再谈预测"}。',
    }
