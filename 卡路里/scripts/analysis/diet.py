#!/usr/bin/env python3
"""饮食分析 — 热量趋势/营养配比/食物排行/缺口分析

提供：
- diet_calorie_trend    — 热量趋势（工作日 vs 周末 / 合规率）
- diet_macro_ratio      — 营养素占比（蛋白/碳水/脂肪）
- diet_food_ranking     — 食物 TOP 榜（热量/低卡/频繁/高碳/高蛋白）
- diet_deficit_analysis — 热量缺口（饮食 vs 运动贡献）
"""

import sys
from datetime import datetime
from pathlib import Path

from analysis._utils import _get_db, _parse_date, BMR_ACTIVITY_FACTOR
from nutrition_goal import get_nutrition_goal

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def diet_calorie_trend(start_date, end_date=None):
    """饮食热量趋势

    Args:
        start_date: 开始日期
        end_date: 结束日期，可选

    Returns:
        list of Row: (date, total_cal, total_pro, total_carbs, total_fat)
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
        FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY date
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    total_cal = sum(r[1] or 0 for r in rows)
    avg_cal = total_cal / len(rows)

    goal = get_nutrition_goal()
    cal_goal = goal[1] if goal else None
    on_target = sum(1 for r in rows if cal_goal and abs((r[1] or 0) - cal_goal) <= cal_goal * 0.1)

    weekday_cal, weekend_cal = 0, 0
    wd_count, we_count = 0, 0
    for r in rows:
        weekday = datetime.strptime(r[0], '%Y-%m-%d').weekday()
        if weekday < 5:
            weekday_cal += r[1] or 0
            wd_count += 1
        else:
            weekend_cal += r[1] or 0
            we_count += 1

    wd_avg = weekday_cal / wd_count if wd_count else 0
    we_avg = weekend_cal / we_count if we_count else 0

    print(f"""🔥 热量趋势（{start_date} ~ {end_date}）
{'-'*40}
  总摄入：{total_cal:.0f}卡 | 日均：{avg_cal:.0f}卡 | 天数：{len(rows)}""")
    if cal_goal:
        print(f"  目标：{cal_goal}卡 | 合规天数：{on_target}/{len(rows)}天")
    print(f"  工作日日均：{wd_avg:.0f}卡 | 周末日均：{we_avg:.0f}卡")
    print(f"{'-'*40}""")
    return rows


def diet_macro_ratio(start_date, end_date=None):
    """营养素占比分析（蛋白/碳水/脂肪 换算热量占比）

    与目标对比：> 3% 偏高 / < -3% 偏低
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT SUM(protein)*4, SUM(carbs)*4, SUM(fat)*9
        FROM entries
        WHERE date >= ? AND date <= ?
    ''', (start_date, end_date))
    row = c.fetchone()
    conn.close()

    if not row or sum(row) == 0:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    cal_from_pro, cal_from_carb, cal_from_fat = row
    total_cal_from_macros = cal_from_pro + cal_from_carb + cal_from_fat
    if total_cal_from_macros == 0:
        total_cal_from_macros = 1

    pct_pro = cal_from_pro / total_cal_from_macros * 100
    pct_carb = cal_from_carb / total_cal_from_macros * 100
    pct_fat = cal_from_fat / total_cal_from_macros * 100

    goal = get_nutrition_goal()

    def eval_pct(pct, macro_name):
        if pct is None:
            return "未设目标"
        if goal:
            cal_goal = goal[1] or 1800
            if macro_name == '蛋白':
                target_pct = (goal[2] or 150) * 4 / cal_goal * 100
            elif macro_name == '碳':
                target_pct = (goal[3] or 200) * 4 / cal_goal * 100
            else:  # 脂肪
                target_pct = (goal[4] or 60) * 9 / cal_goal * 100
        else:
            target_pct = 35
        diff = pct - target_pct
        arrow = "↑" if diff > 3 else ("↓" if diff < -3 else "✓")
        status = "偏高" if diff > 3 else ("偏低" if diff < -3 else "正常")
        return f"{pct:.0f}% {arrow} {status}"

    print(f"""🥗 营养素占比（{start_date} ~ {end_date}）
{'-'*40}
  蛋白质：{eval_pct(pct_pro, '蛋白')}
  碳  水：{eval_pct(pct_carb, '碳')}
  脂  肪：{eval_pct(pct_fat, '脂')}
{'-'*40}""")
    return row


def diet_food_ranking(start_date, end_date=None, category='high_calorie', top_n=5):
    """食物 TOP 榜

    Args:
        start_date: 开始日期
        end_date: 结束日期
        category: 排行类别
            - 'high_calorie'  热量炸弹榜（按总热量降序）
            - 'low_calorie'   低热量健康榜（按单次均热量升序）
            - 'frequent'      频繁吃榜（按出现次数降序）
            - 'high_carb'     高碳水榜（按总碳水降序）
            - 'high_protein'  高蛋白榜（按总蛋白降序）
        top_n: 取前 N 名，默认 5

    Returns:
        list of Row
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT food_name, SUM(calories) as total_cal, SUM(grams) as total_grams,
               SUM(protein), SUM(carbs), SUM(fat), COUNT(*) as cnt
        FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY food_name
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无饮食记录（{start_date} ~ {end_date}）")
        return None

    if category == 'high_calorie':
        sorted_rows = sorted(rows, key=lambda x: x[1], reverse=True)[:top_n]
        title = f"🔥 热量炸弹榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]:>6}卡（{r[6]}次）  均{r[1]//max(r[6],1)}卡/次"
    elif category == 'low_calorie':
        sorted_rows = sorted(rows, key=lambda x: x[1]/max(x[6],1))[:top_n]
        title = f"🥬 低热量健康榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]:>6}卡（{r[6]}次）  均{r[1]//max(r[6],1)}卡/次"
    elif category == 'frequent':
        sorted_rows = sorted(rows, key=lambda x: x[6], reverse=True)[:top_n]
        title = f"📅 频繁吃榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[6]}次 | 总{r[1]}卡 | 均{r[1]//max(r[6],1)}卡/次"
    elif category == 'high_carb':
        sorted_rows = sorted(rows, key=lambda x: x[4] or 0, reverse=True)[:top_n]
        title = f"🍚 高碳水榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[4] or 0:>6}克碳（{r[6]}次）"
    elif category == 'high_protein':
        sorted_rows = sorted(rows, key=lambda x: x[3] or 0, reverse=True)[:top_n]
        title = f"💪 高蛋白榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[3] or 0:>6}克蛋白（{r[6]}次）"
    else:
        sorted_rows = rows[:top_n]
        title = f"📋 食物榜（{start_date} ~ {end_date}）"
        def line(r): return f"  {r[0]:20} {r[1]}卡"

    print(f"{title}\n{'-'*50}")
    for i, r in enumerate(sorted_rows, 1):
        print(f"  {i}. " + line(r))
    print(f"{'-'*50}")
    return sorted_rows


def diet_deficit_analysis(start_date, end_date=None):
    """热量缺口分析（BMR + 运动 - 饮食）

    BMR = weight_kg × 24 × 1.3
    1 kg 脂肪 ≈ 7700 kcal
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, SUM(calories) FROM entries
        WHERE date >= ? AND date <= ?
        GROUP BY date ORDER BY date ASC
    ''', (start_date, end_date))
    diet_rows = c.fetchall()

    c.execute('''
        SELECT date, SUM(calories_burned) FROM exercise_log
        WHERE date >= ? AND date <= ?
        GROUP BY date ORDER BY date ASC
    ''', (start_date, end_date))
    ex_rows = c.fetchall()
    conn.close()

    if not diet_rows:
        print(f"⚠️ 无记录（{start_date} ~ {end_date}）")
        return None

    diet_map = {r[0]: r[1] for r in diet_rows}
    ex_map = {r[0]: r[1] for r in ex_rows}

    all_dates = sorted(set(diet_map.keys()))
    days = len(all_dates)

    total_intake = sum(diet_map.values())
    total_ex = sum(ex_map.values())
    avg_intake = total_intake / days
    avg_ex = total_ex / days

    conn = _get_db()
    cur2 = conn.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    conn.close()
    current_weight = wrow[0] if wrow else 70
    bmr = current_weight * 24 * BMR_ACTIVITY_FACTOR

    avg_deficit = bmr + avg_ex - avg_intake
    total_deficit = avg_deficit * days
    kg_equivalent = total_deficit / 7700

    diet_contrib = abs(total_deficit - total_ex * days) / abs(total_deficit) * 100 if total_deficit != 0 else 0
    ex_contrib = total_ex / abs(total_deficit) * 100 if total_deficit != 0 else 0

    print(f"""📉 热量缺口分析（{start_date} ~ {end_date}）
{'-'*40}
  日均摄入：{avg_intake:.0f}卡 | 基础代谢：约{bmr:.0f}卡（{current_weight:.0f}kg）| 运动消耗：日均{avg_ex:.0f}卡
  日均缺口：{avg_deficit:.0f}卡（{'偏小' if 0 < avg_deficit < 300 else ('过大' if avg_deficit > 700 else '正常')}）
  累计缺口：{total_deficit:.0f}卡 ≈ {kg_equivalent:.2f}kg
  饮食贡献：{diet_contrib:.0f}% | 运动贡献：{ex_contrib:.0f}%
{'-'*40}""")
    return {'avg_deficit': avg_deficit, 'total_deficit': total_deficit, 'kg_equivalent': kg_equivalent}