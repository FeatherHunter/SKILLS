#!/usr/bin/env python3
"""
卡路里 - 分析系统
11个分析函数 + 4个统一入口
"""

import sqlite3
import os
import sys
import statistics
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# 确保 scripts/ 目录在 sys.path 中（支持从父目录导入）
_scripts_dir = str(Path(__file__).resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from db_utils import find_db_path, get_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)
BMR_ACTIVITY_FACTOR = 1.3


def _get_db():
    return get_db(DB_PATH)


def _get_goal():
    """获取每日目标"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row


def _get_weight_goal():
    """获取体重目标（合并为单次连接）"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        return None

    weight_goal, deadline = row

    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = c.fetchone()
    if not wrow:
        conn.close()
        return (weight_goal, deadline, None, None, None)

    current_weight, current_date = wrow

    days_left = None
    calorie_adjustment = None

    if deadline:
        try:
            deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
            today_dt = datetime.strptime(current_date, '%Y-%m-%d')
            days_left = (deadline_dt - today_dt).days
        except (ValueError, TypeError):
            days_left = None

    if days_left is not None and days_left > 0:
        gap = current_weight - weight_goal
        required_daily = gap / days_left
        calorie_adjustment = int(required_daily * 7700)

    conn.close()
    return (weight_goal, deadline, days_left, None, calorie_adjustment)


# ============================================================
# 分析函数
# ============================================================

def _parse_date(s):
    """解析日期字符串为 YYYY-MM-DD"""
    if s is None:
        return None
    s = str(s).strip()
    # 支持 YYYYMMDD 和 YYYY-MM-DD
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _days_between(d1, d2):
    """计算两个日期之间的天数差"""
    try:
        return (datetime.strptime(d2, '%Y-%m-%d') - datetime.strptime(d1, '%Y-%m-%d')).days
    except Exception:
        return 0


# ---- 体重分析 ----

def weight_trend(start_date, end_date=None):
    """体重趋势分析，近30天或指定范围"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, weight_kg, note FROM weight_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无体重记录（{start_date} ~ {end_date}）")
        return None

    weights = [(r[0], r[1], r[2] or '') for r in rows]
    count = len(weights)
    avg_w = sum(w[1] for w in weights) / count
    max_w = max(w[1] for w in weights)
    min_w = min(w[1] for w in weights)
    first_w = weights[0][1]
    last_w = weights[-1][1]
    change = last_w - first_w
    span = _days_between(weights[0][0], weights[-1][0]) + 1
    daily_rate = (change / span) * 1000  # g/天

    if abs(daily_rate) < 10:
        trend_label = "平稳 ✓"
    elif change > 0:
        trend_label = "上升 ↑"
    else:
        trend_label = "下降 ✓"

    print(f"""
📊 体重趋势（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{count}条
  均重：{avg_w:.1f}kg | 最高：{max_w:.1f}kg | 最低：{min_w:.1f}kg
  首日：{weights[0][0]} {first_w:.1f}kg
  末日：{weights[-1][0]} {last_w:.1f}kg
  变化：{change:+.1f}kg | 日均变化：{daily_rate:+.0f}g/天
  趋势判断：{trend_label}
{'-'*40}""")
    return rows


def weight_compare(start_date, end_date, compare_start, compare_end):
    """两个时间段体重对比"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    compare_start = _parse_date(compare_start)
    compare_end = _parse_date(compare_end)

    conn = _get_db()
    c = conn.cursor()

    def avg_weight(s, e):
        c.execute('''SELECT AVG(weight_kg) FROM weight_log WHERE date >= ? AND date <= ?''', (s, e))
        r = c.fetchone()[0]
        return r

    def first_last(s, e):
        c.execute('''SELECT weight_kg, date FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date ASC LIMIT 1''', (s, e))
        r1 = c.fetchone()
        c.execute('''SELECT weight_kg FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT 1''', (s, e))
        r2 = c.fetchone()
        return (r1[0], r1[1]) if r1 else None, r2[0] if r2 else None

    avg1 = avg_weight(start_date, end_date)
    avg2 = avg_weight(compare_start, compare_end)
    fl1 = first_last(start_date, end_date)
    fl2 = first_last(compare_start, compare_end)
    conn.close()

    if avg1 is None or avg2 is None:
        print("⚠️ 对比时间段内无体重记录，无法对比")
        return None

    avg_diff = avg1 - avg2
    first_w1, first_d1 = fl1[0] if fl1[0] else (None, None)
    last_w1 = fl1[1]
    change1 = (last_w1 - first_w1) if first_w1 and last_w1 else 0
    first_w2, first_d2 = fl2[0] if fl2[0] else (None, None)
    last_w2 = fl2[1]
    change2 = (last_w2 - first_w2) if first_w2 and last_w2 else 0
    change_diff = change1 - change2

    if change_diff > 0:
        speed_label = "较上期加速下降" if change1 < 0 else "较上期加速上升"
    elif change_diff < 0:
        speed_label = "较上期减速下降" if change1 < 0 else "较上期减速上升"
    else:
        speed_label = "节奏与上期相同"

    print(f"""
⚖️ 体重对比
{'-'*40}
  本期（{start_date} ~ {end_date}）
    均重：{avg1:.1f}kg
    首→末：{first_w1:.1f} → {last_w1:.1f}kg（{change1:+.1f}kg）
  对比（{compare_start} ~ {compare_end}）
    均重：{avg2:.1f}kg
    首→末：{first_w2:.1f} → {last_w2:.1f}kg（{change2:+.1f}kg）
  变化：{avg_diff:+.1f}kg（{'下降' if avg_diff < 0 else '上升'}）
  趋势：{speed_label}
{'-'*40}""")
    return avg_diff


def weight_milestone():
    """体重目标进度分析"""
    result = _get_weight_goal()
    if not result or result[0] is None:
        print("⚠️ 未设定体重目标，请说「设定体重目标 XXkg」")
        return None

    weight_goal, deadline, days_left, daily_change_rate, calorie_adj = result

    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    row = c.fetchone()
    if not row:
        print("⚠️ 未记录体重")
        conn.close()
        return None
    current_weight, current_date = row

    gap = current_weight - weight_goal

    # 计算实际日均变化（近30天，用首尾差值）
    c.execute('''SELECT weight_kg, date FROM weight_log
                 WHERE date >= date('now', '-30 days')
                 ORDER BY date ASC''')
    rows_30 = c.fetchall()
    conn.close()

    actual_daily = None
    if rows_30 and len(rows_30) >= 2:
        first_w_30, first_d_30 = rows_30[0][0], rows_30[0][1]
        last_w_30, last_d_30 = rows_30[-1][0], rows_30[-1][1]
        span_30 = _days_between(first_d_30, last_d_30) + 1
        if span_30 > 0:
            actual_daily = (last_w_30 - first_w_30) / span_30

    # 估算剩余时间
    if days_left is not None:
        est_days = days_left
    elif actual_daily and actual_daily != 0:
        est_days = abs(gap / actual_daily)
    else:
        est_days = None

    if est_days and est_days > 0:
        est_date = (datetime.strptime(current_date, '%Y-%m-%d') + timedelta(days=est_days)).strftime('%Y-%m-%d')
    else:
        est_date = "未知"

    # 状态判断
    if days_left is not None and actual_daily:
        required = gap / days_left if days_left > 0 else 0
        diff = actual_daily - required
        if abs(diff) < 0.02:
            status = "进度正常 ✓"
        elif diff > 0:
            status = "进度超前 ✓"
        else:
            status = "进度偏慢 ⚠️"
    else:
        status = "无法评估"

    gap_str = f"{gap:+.1f}kg"
    actual_str = f"{actual_daily:.2f}kg/天" if actual_daily else "数据不足"
    est_date_str = est_date if isinstance(est_date, str) else "未知"
    est_days_str = f"{est_days:.0f}天" if est_days else "未知"

    print(f"""🎯 体重目标进度
{'-'*40}
  当前：{current_weight:.1f}kg（{current_date}）
  目标：{weight_goal:.1f}kg""" + (f" | 目标日期：{deadline}" if deadline else "") + f"""
  差距：{gap_str} | 实际日均变化：{actual_str}（近30天）
  预计达成：{est_date_str}（约{est_days_str}）
  状态：{status}
{'-'*40}""")
    return result


def weight_volatility(start_date, end_date=None):
    """体重波动分析"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, weight_kg, note FROM weight_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows or len(rows) < 3:
        print(f"⚠️ 记录不足（{start_date} ~ {end_date}），需要至少3条记录")
        return None

    weights = [r[1] for r in rows]
    dates = [r[0] for r in rows]

    std_dev = statistics.stdev(weights) if len(weights) >= 2 else 0

    # 计算周间波动
    week_weights = defaultdict(list)
    for d, w in zip(dates, weights):
        week_key = datetime.strptime(d, '%Y-%m-%d').strftime('%Y-W%W')
        week_weights[week_key].append(w)

    week_avgs = [sum(v) / len(v) for v in week_weights.values()]
    week_std = statistics.stdev(week_avgs) if len(week_avgs) >= 2 else 0

    # 标记异常（单日涨跌幅 > 0.5kg）
    anomalies = []
    for i in range(1, len(rows)):
        diff = rows[i][1] - rows[i-1][1]
        if abs(diff) > 0.5:
            note = rows[i][2] or ""
            anomalies.append(f"{rows[i][0]} {diff:+.1f}kg（{note}）")

    if std_dev < 0.3:
        vol_label = "波动正常 ✓"
    elif std_dev < 0.6:
        vol_label = "波动中等"
    else:
        vol_label = "波动较大 ⚠️"

    print(f"""📉 体重波动分析（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{len(rows)}条
  日间波动：±{std_dev:.2f}kg（标准差）
  周间波动：±{week_std:.2f}kg""")
    if anomalies:
        print(f"  异常记录（单日>0.5kg）：")
        for a in anomalies:
            print(f"    - {a}")
    else:
        print(f"  异常记录：无")
    print(f"  评估：{vol_label}")
    print(f"{'-'*40}")


# ---- 饮食分析 ----

def diet_calorie_trend(start_date, end_date=None):
    """饮食热量趋势"""
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

    goal = _get_goal()
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
    """营养素占比分析"""
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

    goal = _get_goal()

    def eval_pct(pct, macro_name):
        if pct is None:
            return "未设目标"
        # Calculate target percentage from actual goals
        if goal:
            cal_goal = goal[1] or 1800
            if macro_name == '蛋白':
                target_pct = (goal[2] or 150) * 4 / cal_goal * 100
            elif macro_name == '碳':
                target_pct = (goal[3] or 200) * 4 / cal_goal * 100
            else:  # 脂肪
                target_pct = (goal[4] or 60) * 9 / cal_goal * 100
        else:
            target_pct = 35  # Default reference when no goal set
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
    """食物TOP榜
    category: high_calorie | low_calorie | frequent | high_carb | high_protein
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
    """热量缺口分析"""
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

    c2 = _get_db()
    cur2 = c2.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    c2.close()
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


# ---- 运动分析 ----

def exercise_trend(start_date, end_date=None):
    """运动趋势"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT date, exercise_type, duration_minutes, calories_burned
        FROM exercise_log
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无运动记录（{start_date} ~ {end_date}）")
        return None

    span = _days_between(start_date, end_date) + 1
    days_with_ex = len(set(r[0] for r in rows))
    total_cal = sum(r[3] for r in rows)
    total_dur = sum(r[2] or 0 for r in rows)
    avg_cal = total_cal / span
    avg_dur = total_dur / span

    dates = sorted(set(r[0] for r in rows))
    longest_streak = 1
    current_streak = 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], '%Y-%m-%d')
        d2 = datetime.strptime(dates[i], '%Y-%m-%d')
        if (d2 - d1).days == 1:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 1

    if len(dates) >= 2:
        max_gap = max((datetime.strptime(dates[i], '%Y-%m-%d') - datetime.strptime(dates[i-1], '%Y-%m-%d')).days - 1
                      for i in range(1, len(dates)))
    else:
        max_gap = span - 1

    print(f"""🏃 运动趋势（{start_date} ~ {end_date}）
{'-'*40}
  运动天数：{days_with_ex}/{span}天（{days_with_ex/span*100:.0f}%）
  总时长：{total_dur}分钟 | 总消耗：{total_cal}卡
  日均消耗：{avg_cal:.0f}卡/天 | 日均时长：{avg_dur:.0f}分钟/天
  最长连续运动：{longest_streak}天
  最长休息：{max_gap}天{" ⚠️ 建议动起来" if max_gap >= 7 else ""}
{'-'*40}""")
    return rows


def exercise_type_breakdown(start_date, end_date=None):
    """运动类型分布"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        SELECT exercise_type, SUM(calories_burned), COUNT(*), SUM(duration_minutes)
        FROM exercise_log
        WHERE date >= ? AND date <= ?
        GROUP BY exercise_type
        ORDER BY SUM(calories_burned) DESC
    ''', (start_date, end_date))
    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"⚠️ 无运动记录（{start_date} ~ {end_date}）")
        return None

    total_cal = sum(r[1] for r in rows)
    total_cnt = sum(r[2] for r in rows)
    total_dur = sum(r[3] or 0 for r in rows)

    print(f"📊 运动类型分布（{start_date} ~ {end_date}）\n{'-'*40}")
    for r in rows:
        etype, cal, cnt, dur = r
        pct = cal / total_cal * 100
        print(f"  {etype:15} 消耗{cal}卡（{pct:.0f}%）| {cnt}次 | {dur or 0}分钟")
    print(f"\n  总计：{total_cal}卡 | {total_cnt}次 | {total_dur}分钟")
    print(f"{'-'*40}")
    return rows


def exercise_deficit_contribution(start_date, end_date=None):
    """运动对热量缺口的贡献"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('''SELECT SUM(calories_burned) FROM exercise_log WHERE date >= ? AND date <= ?''', (start_date, end_date))
    total_ex = c.fetchone()[0] or 0
    c.execute('''SELECT SUM(calories) FROM entries WHERE date >= ? AND date <= ?''', (start_date, end_date))
    total_intake = c.fetchone()[0] or 0
    conn.close()

    span = _days_between(start_date, end_date) + 1

    c2 = _get_db()
    cur2 = c2.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    c2.close()
    current_weight = wrow[0] if wrow else 70
    bmr = current_weight * 24 * BMR_ACTIVITY_FACTOR

    bmr_total = bmr * span
    diet_deficit = bmr_total - total_intake
    total_deficit = bmr_total - total_intake + total_ex

    if total_deficit == 0:
        diet_pct = 50
        ex_pct = 50
    else:
        diet_pct = abs(diet_deficit) / abs(total_deficit) * 100
        ex_pct = total_ex / abs(total_deficit) * 100

    print(f"""💪 运动缺口贡献（{start_date} ~ {end_date}）
{'-'*40}
  饮食缺口：{diet_deficit:.0f}卡（{diet_pct:.0f}%）
  运动缺口：{total_ex:.0f}卡（{ex_pct:.0f}%）
  评估：{'运动贡献偏低，建议增加运动比例' if ex_pct < 15 else ('运动贡献较高 ✓' if ex_pct > 25 else '运动贡献适中')}
{'-'*40}""")
    return {'diet_pct': diet_pct, 'ex_pct': ex_pct}


# ---- 综合报告 ----

def weight_analysis(start_date, end_date=None, analysis_type='trend',
                    compare_start=None, compare_end=None):
    """体重分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'trend': 趋势分析（均重/日均变化/趋势判断）
            - 'compare': 同期对比（需要 compare_start/compare_end）
            - 'milestone': 目标进度（预计达成日/状态）
            - 'volatility': 波动分析（标准差/异常记录）
        compare_start: 对比期开始日期（compare 模式可选）
        compare_end: 对比期结束日期（compare 模式可选）
    """
    if analysis_type == 'trend':
        return weight_trend(start_date, end_date)
    elif analysis_type == 'compare':
        if compare_start and compare_end:
            return weight_compare(start_date, end_date or start_date,
                                  compare_start, compare_end)
        else:
            # Default: compare with previous period of same length
            span = _days_between(start_date, end_date or start_date)
            end_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)
            cs = (end_dt - timedelta(days=span)).strftime('%Y-%m-%d')
            ce = end_dt.strftime('%Y-%m-%d')
            return weight_compare(start_date, end_date or start_date, cs, ce)
    elif analysis_type == 'milestone':
        return weight_milestone()
    elif analysis_type == 'volatility':
        return weight_volatility(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用趋势分析")
        return weight_trend(start_date, end_date)


def diet_analysis(start_date, end_date=None, analysis_type='calorie_trend'):
    """饮食分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'calorie_trend': 热量趋势（工作日vs周末/合规率）
            - 'macro_ratio': 碳水/蛋白质/脂肪占比分析
            - 'food_ranking': 食物TOP榜（热量炸弹/低热量/频繁吃/高碳水/高蛋白）
            - 'deficit_analysis': 热量缺口分析（饮食+运动贡献）
    """
    if analysis_type == 'calorie_trend':
        return diet_calorie_trend(start_date, end_date)
    elif analysis_type == 'macro_ratio':
        return diet_macro_ratio(start_date, end_date)
    elif analysis_type == 'food_ranking':
        return diet_food_ranking(start_date, end_date, category='high_calorie')
    elif analysis_type == 'deficit_analysis':
        return diet_deficit_analysis(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用热量趋势")
        return diet_calorie_trend(start_date, end_date)


def exercise_analysis(start_date, end_date=None, analysis_type='exercise_trend'):
    """运动分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同start_date单日）
        analysis_type: 分析类型
            - 'exercise_trend': 运动趋势（天数/时长/消耗/间隔）
            - 'type_breakdown': 运动类型分布（消耗/频次/时长占比）
            - 'deficit_contribution': 运动对缺口的贡献占比
    """
    if analysis_type == 'exercise_trend':
        return exercise_trend(start_date, end_date)
    elif analysis_type == 'type_breakdown':
        return exercise_type_breakdown(start_date, end_date)
    elif analysis_type == 'deficit_contribution':
        return exercise_deficit_contribution(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用运动趋势")
        return exercise_trend(start_date, end_date)


def dashboard(start_date, end_date=None):
    """综合健康报告"""
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    print(f"""
{'='*55}
  📋 综合健康报告（{start_date} ~ {end_date}）
{'='*55}""")

    print("\n📊 体重趋势")
    try:
        weight_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取体重数据: {e}")

    print("\n🔥 热量趋势")
    try:
        diet_calorie_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取热量数据: {e}")

    print("\n🏃 运动趋势")
    try:
        exercise_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取运动数据: {e}")

    print("\n📉 热量缺口")
    try:
        diet_deficit_analysis(start_date, end_date)
    except Exception as e:
        print(f"  无法获取缺口数据: {e}")

    print(f"\n{'='*55}")
