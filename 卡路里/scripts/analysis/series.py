#!/usr/bin/env python3
"""analysis/series.py — 日序列 series[] 构建器(ticket #10 · 分析 154 场景)

统一把多张表聚合为「按天对齐」的日序列,是 A1(组合分析)/ A3(整体趋势)/
A4(自动分析)/ A5(营养分析)/ A6(预测模拟) 的数据地基。

每日一条 dict:
    date           YYYY-MM-DD
    calories       当日摄入热量(卡,不含饮水记录)
    protein        当日蛋白(g)
    carbs          当日碳水(g)
    fat            当日脂肪(g)
    sodium_mg      当日钠(mg,来自 nutrition_products 每 100g × 克数 / 100)
    sugar_g        当日糖(g)
    fiber_g        当日膳食纤维(g)
    water_ml       当日饮水(ml,💧水 记录)
    exercise_kcal  当日运动消耗(卡)
    weight_kg      当日体重(kg,取当日最早一条)
    body_fat_pct   当日体脂率(%)
    waist_cm       当日腰围(cm)
    tdee           当日 TDEE(静态值:档案 BMR × 活动系数)
    deficit        热量缺口 = 摄入 - (TDEE + 运动消耗)(负数 = 盈余)
    calorie_goal   当日热量目标(静态值)

窗口选择器 resolve_window:统一解析 7d/15d/30d/60d/90d/180d/365d/本周/上周/
本月/上月/今年/自定义(start/end 显式给)。
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from analysis._utils import _get_db, calc_tdee, get_profile_activity_level  # noqa: E402
from profile import get_profile  # noqa: E402

WATER_NAME = '💧水'


def resolve_window(window: str, start: str | None = None, end: str | None = None) -> tuple[str, str]:
    """解析时间窗口 → (start, end)(含首尾)

    支持:
      '7d'/'15d'/'30d'/'60d'/'90d'/'180d'/'365d' → 最近 N 天(含今天)
      '本周' / '上周' / '本月' / '上月' / '今年'  → 周/月/年窗口
      'custom' → 必须给 start/end;缺省回退最近 30 天
    """
    today = date.today()
    if window == 'custom':
        if start and end:
            return start, end
        end = (today - timedelta(days=1)).isoformat()
        start = (today - timedelta(days=30)).isoformat()
        return start, end

    if window.endswith('d') and window[:-1].isdigit():
        n = int(window[:-1])
        return (today - timedelta(days=n - 1)).isoformat(), today.isoformat()

    if window == '本周' or window == 'week_cur':
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat(), today.isoformat()
    if window == '上周' or window == 'week_prev':
        monday = today - timedelta(days=today.weekday() + 7)
        sunday = today - timedelta(days=today.weekday() + 1)
        return monday.isoformat(), sunday.isoformat()
    if window == '本月' or window == 'month_cur':
        return today.replace(day=1).isoformat(), today.isoformat()
    if window == '上月' or window == 'month_prev':
        first_this = today.replace(day=1)
        first_last = (first_this - timedelta(days=1)).replace(day=1)
        last_last = first_this - timedelta(days=1)
        return first_last.isoformat(), last_last.isoformat()
    if window == '今年' or window == 'year_cur':
        return today.replace(month=1, day=1).isoformat(), today.isoformat()

    # 默认:最近 30 天
    return (today - timedelta(days=29)).isoformat(), today.isoformat()


def _load_profile_tdee() -> float:
    """读取档案并计算 TDEE(缺档案回退 1800)"""
    try:
        prof = get_profile() or {}
        weight = prof.get('latest_weight_kg') or 70.0
        height = prof.get('height_cm') or 170.0
        age = prof.get('age') or 30
        gender = prof.get('gender') or 'male'
        return calc_tdee(weight, height, age, gender, get_profile_activity_level())
    except Exception:
        return 1800.0


def build_series(start: str, end: str) -> list[dict]:
    """构建 [start, end] 的日序列(每天一条,含无数据日)"""
    conn = _get_db()
    try:
        c = conn.cursor()

        tdee = _load_profile_tdee()

        # 摄入(排除饮水记录;饮水量单独算)
        diet_rows = c.execute(
            "SELECT date, "
            "  SUM(calories) AS calories, SUM(protein) AS protein, SUM(carbs) AS carbs, "
            "  SUM(fat) AS fat, SUM(sodium_mg) AS sodium_mg, SUM(sugar_g) AS sugar_g, "
            "  SUM(fiber_g) AS fiber_g "
            "FROM food_log WHERE date BETWEEN ? AND ? AND food_name != ? "
            "GROUP BY date",
            (start, end, WATER_NAME),
        ).fetchall()

        # 饮水
        water_rows = c.execute(
            "SELECT date, SUM(grams) AS ml FROM food_log "
            "WHERE date BETWEEN ? AND ? AND food_name = ? GROUP BY date",
            (start, end, WATER_NAME),
        ).fetchall()

        # 运动
        ex_rows = c.execute(
            "SELECT date, SUM(calories_burned) AS kcal FROM exercise_log "
            "WHERE date BETWEEN ? AND ? GROUP BY date",
            (start, end),
        ).fetchall()

        # 体重(当日最早一条)
        w_rows = c.execute(
            "SELECT date, weight_kg FROM weight_log "
            "WHERE date BETWEEN ? AND ? ORDER BY date, time ASC, id ASC",
            (start, end),
        ).fetchall()

        # 体脂(当日最早一条)
        bf_rows = c.execute(
            "SELECT date, body_fat_pct FROM body_composition "
            "WHERE date BETWEEN ? AND ? AND is_deprecated = 0 "
            "ORDER BY date, id ASC",
            (start, end),
        ).fetchall()

        # 腰围(当日最早一条;无腰围取臀围兜底)
        bm_rows = c.execute(
            "SELECT date, waist_cm, hip_cm FROM body_measurements "
            "WHERE date BETWEEN ? AND ? AND is_deprecated = 0 "
            "ORDER BY date, id ASC",
            (start, end),
        ).fetchall()

        # 目标(静态,单行表)
        goal_row = c.execute(
            "SELECT calorie_goal, water_goal FROM daily_goal WHERE id = 1"
        ).fetchone()

        # 索引聚合结果
        def _idx(rows, key):
            return {r[0]: r for r in rows}

        diet_i, water_i, ex_i = _idx(diet_rows, 'date'), _idx(water_rows, 'date'), _idx(ex_rows, 'date')
        weight_first, bf_first, bm_first = {}, {}, {}
        for r in w_rows:
            weight_first.setdefault(r[0], r[1])
        for r in bf_rows:
            bf_first.setdefault(r[0], r[1])
        for r in bm_rows:
            bm_first.setdefault(r[0], (r[1], r[2]))

        # 逐日组装
        series = []
        cur = datetime.strptime(start, '%Y-%m-%d').date()
        end_d = datetime.strptime(end, '%Y-%m-%d').date()
        while cur <= end_d:
            d = cur.isoformat()
            dr = diet_i.get(d)
            wr = water_i.get(d)
            er = ex_i.get(d)
            bm = bm_first.get(d)
            waist = bm[0] if bm and bm[0] is not None else (bm[1] if bm else None)

            calories = dr[1] if dr else None
            exercise_kcal = er[1] if er else None
            deficit = None
            if calories is not None:
                exp = tdee + (exercise_kcal or 0)
                deficit = round(calories - exp, 1)

            series.append({
                'date':           d,
                'calories':       calories,
                'protein':        dr[2] if dr else None,
                'carbs':          dr[3] if dr else None,
                'fat':            dr[4] if dr else None,
                'sodium_mg':      dr[5] if dr else None,
                'sugar_g':        dr[6] if dr else None,
                'fiber_g':        dr[7] if dr else None,
                'water_ml':       wr[1] if wr else None,
                'exercise_kcal':  exercise_kcal,
                'weight_kg':      weight_first.get(d),
                'body_fat_pct':   bf_first.get(d),
                'waist_cm':       waist,
                'tdee':           tdee,
                'deficit':        deficit,
                'calorie_goal':   goal_row[0] if goal_row else 1800,
                'water_goal':     goal_row[1] if goal_row and goal_row[1] else 2000,
            })
            cur += timedelta(days=1)

        return series
    finally:
        conn.close()


def series_avg(series: list[dict], field: str, skip_none: bool = True) -> float | None:
    """序列均值(None 跳过;全空返回 None)"""
    vals = [s[field] for s in series if s.get(field) is not None] if skip_none \
        else [s.get(field) for s in series]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def series_sum(series: list[dict], field: str) -> float:
    """序列求和(None 按 0)"""
    return round(sum(s.get(field) or 0 for s in series), 1)


def series_count(series: list[dict], field: str) -> int:
    """序列非空计数"""
    return sum(1 for s in series if s.get(field) is not None)


def series_delta(series: list[dict], field: str) -> float | None:
    """序列净变化 = 最后非空 - 最前非空"""
    vals = [s[field] for s in series if s.get(field) is not None]
    if len(vals) < 2:
        return None
    return round(vals[-1] - vals[0], 1)
