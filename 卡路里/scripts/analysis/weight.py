#!/usr/bin/env python3
"""体重分析 — 趋势/对比/目标进度/波动

提供：
- weight_trend       — 趋势（均重/日均变化/趋势判断）
- weight_compare     — 两时段对比
- weight_milestone   — 目标进度（实际日均变化/预计达成日/状态）
- weight_volatility  — 波动分析（日间标准差/周间波动/异常记录）

2026-07-23 D1 重构：所有函数加 as_dict=False 参数
- as_dict=True  → 返回结构化 dict {status, data, message}（机器可读）
- as_dict=False → 保持原 print 输出（向后兼容，默认）
"""
import sys
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from db import init_db
from analysis._utils import _get_db, _parse_date, _days_between

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def weight_trend(start_date, end_date=None, as_dict=False):
    """体重趋势分析

    Args:
        start_date: 开始日期（YYYY-MM-DD 或 YYYYMMDD）
        end_date: 结束日期，可选（默认同日单日查询）
        as_dict: True 返回 dict {status, data, message}；False print（默认）

    Returns:
        as_dict=True  → dict {status, data, message}
        as_dict=False → list of Row 或 None（向后兼容）
    """
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
        msg = f"无体重记录（{start_date} ~ {end_date}）"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
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
        trend_label = "stable"
    elif change > 0:
        trend_label = "up"
    else:
        trend_label = "down"

    # 2026-07-23 D1 增：组装 dict
    data = {
        "record_count": count,
        "avg_weight": round(avg_w, 1),
        "max_weight": round(max_w, 1),
        "min_weight": round(min_w, 1),
        "first_date": weights[0][0],
        "first_weight": round(first_w, 1),
        "last_date": weights[-1][0],
        "last_weight": round(last_w, 1),
        "change_kg": round(change, 1),
        "daily_change_g": round(daily_rate, 0),
        "trend": trend_label,
        "logs": [
            {"date": r[0], "weight_kg": r[1], "note": r[2] or ""}
            for r in rows
        ],
    }

    if as_dict:
        return {
            "status": "ok",
            "data": data,
            "message": f"体重趋势 {count} 条记录，趋势 {trend_label}",
        }

    # 原 print 输出（向后兼容）
    trend_emoji = "✓" if abs(daily_rate) < 10 else ("↑" if change > 0 else "✓")
    print(f"""
📊 体重趋势（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{count}条
  均重：{avg_w:.1f}kg | 最高：{max_w:.1f}kg | 最低：{min_w:.1f}kg
  首日：{weights[0][0]} {first_w:.1f}kg
  末日：{weights[-1][0]} {last_w:.1f}kg
  变化：{change:+.1f}kg | 日均变化：{daily_rate:+.0f}g/天
  趋势判断：{trend_label}{trend_emoji}
{'-'*40}""")
    return rows


def weight_compare(start_date, end_date, compare_start, compare_end, as_dict=False):
    """两个时间段体重对比

    Args:
        as_dict: True 返回 dict；False print（默认）
    Returns:
        as_dict=True  → dict
        as_dict=False → float: 平均差值（本期 - 对比期）
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    compare_start = _parse_date(compare_start)
    compare_end = _parse_date(compare_end)

    conn = _get_db()
    c = conn.cursor()

    def avg_weight(s, e):
        c.execute('SELECT AVG(weight_kg) FROM weight_log WHERE date >= ? AND date <= ?', (s, e))
        return c.fetchone()[0]

    def first_last(s, e):
        c.execute('SELECT weight_kg, date FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date ASC LIMIT 1', (s, e))
        r1 = c.fetchone()
        c.execute('SELECT weight_kg FROM weight_log WHERE date >= ? AND date <= ? ORDER BY date DESC LIMIT 1', (s, e))
        r2 = c.fetchone()
        return (r1[0], r1[1]) if r1 else None, r2[0] if r2 else None

    avg1 = avg_weight(start_date, end_date)
    avg2 = avg_weight(compare_start, compare_end)
    fl1 = first_last(start_date, end_date)
    fl2 = first_last(compare_start, compare_end)
    conn.close()

    if avg1 is None or avg2 is None:
        msg = "对比时间段内无体重记录，无法对比"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
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

    # 2026-07-23 D1 增：组装 dict
    data = {
        "avg_diff": round(avg_diff, 1),
        "direction": "down" if avg_diff < 0 else "up",
        "speed_label": speed_label,
        "current_period": {
            "start": start_date, "end": end_date,
            "avg_weight": round(avg1, 1),
            "first_weight": round(first_w1, 1) if first_w1 else None,
            "first_date": first_d1,
            "last_weight": round(last_w1, 1),
            "change_kg": round(change1, 1),
        },
        "compare_period": {
            "start": compare_start, "end": compare_end,
            "avg_weight": round(avg2, 1),
            "first_weight": round(first_w2, 1) if first_w2 else None,
            "first_date": first_d2,
            "last_weight": round(last_w2, 1),
            "change_kg": round(change2, 1),
        },
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"本期 vs 对比期: {avg_diff:+.1f}kg"}

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


def weight_milestone(as_dict=False):
    """体重目标进度分析

    Args:
        as_dict: True 返回 dict；False print（默认）
    Returns:
        as_dict=True  → dict
        as_dict=False → tuple(向后兼容)
    """
    from weight_goal import get_weight_goal
    result = get_weight_goal()
    if not result or result[0] is None:
        msg = "未设定体重目标，请说「设定体重目标 XXkg」"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
        return None

    weight_goal, deadline, days_left, daily_change_rate, calorie_adj = result

    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    row = c.fetchone()
    if not row:
        conn.close()
        msg = "未记录体重"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
        return None
    current_weight, current_date = row

    gap = current_weight - weight_goal

    c.execute('''
        SELECT weight_kg, date FROM weight_log
        WHERE date >= date('now', '-30 days')
        ORDER BY date ASC
    ''')
    rows_30 = c.fetchall()
    conn.close()

    actual_daily = None
    if rows_30 and len(rows_30) >= 2:
        first_w_30, first_d_30 = rows_30[0][0], rows_30[0][1]
        last_w_30, last_d_30 = rows_30[-1][0], rows_30[-1][1]
        span_30 = _days_between(first_d_30, last_d_30) + 1
        if span_30 > 0:
            actual_daily = (last_w_30 - first_w_30) / span_30

    if days_left is not None:
        est_days = days_left
    elif actual_daily and actual_daily != 0:
        est_days = abs(gap / actual_daily)
    else:
        est_days = None

    if est_days and est_days > 0:
        est_date = (datetime.strptime(current_date, '%Y-%m-%d') + timedelta(days=est_days)).strftime('%Y-%m-%d')
    else:
        est_date = None

    if days_left is not None and actual_daily:
        required = gap / days_left if days_left > 0 else 0
        diff = actual_daily - required
        if abs(diff) < 0.02:
            status = "进度正常"
        elif diff > 0:
            status = "进度超前"
        else:
            status = "进度偏慢"
    else:
        status = "无法评估"

    # 2026-07-23 D1 增：组装 dict
    data = {
        "current_weight": round(current_weight, 1),
        "current_date": current_date,
        "weight_goal": round(weight_goal, 1),
        "deadline": deadline,
        "gap_kg": round(gap, 1),
        "actual_daily_change_kg": round(actual_daily, 2) if actual_daily else None,
        "est_date": est_date,
        "est_days": round(est_days) if est_days else None,
        "status": status,
        "calorie_adjustment": calorie_adj,
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"目标进度: {status}"}

    # 原 print 输出
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


def weight_volatility(start_date, end_date=None, as_dict=False):
    """体重波动分析

    Args:
        as_dict: True 返回 dict；False print（默认）
    Returns:
        as_dict=True  → dict
        as_dict=False → None（向后兼容）
    """
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
        msg = f"记录不足（{start_date} ~ {end_date}），需要至少3条记录"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
        return None

    weights = [r[1] for r in rows]
    dates = [r[0] for r in rows]

    std_dev = statistics.stdev(weights) if len(weights) >= 2 else 0

    week_weights = defaultdict(list)
    for d, w in zip(dates, weights):
        week_key = datetime.strptime(d, '%Y-%m-%d').strftime('%Y-W%W')
        week_weights[week_key].append(w)

    week_avgs = [sum(v) / len(v) for v in week_weights.values()]
    week_std = statistics.stdev(week_avgs) if len(week_avgs) >= 2 else 0

    anomalies = []
    for i in range(1, len(rows)):
        diff = rows[i][1] - rows[i-1][1]
        if abs(diff) > 0.5:
            note = rows[i][2] or ""
            anomalies.append({
                "date": rows[i][0],
                "diff_kg": round(diff, 1),
                "note": note,
            })

    if std_dev < 0.3:
        vol_label = "波动正常"
        vol_status = "ok"
    elif std_dev < 0.6:
        vol_label = "波动中等"
        vol_status = "warn"
    else:
        vol_label = "波动较大"
        vol_status = "error"

    # 2026-07-23 D1 增：组装 dict
    data = {
        "record_count": len(rows),
        "daily_std_kg": round(std_dev, 2),
        "weekly_std_kg": round(week_std, 2),
        "label": vol_label,
        "status": vol_status,
        "anomalies": anomalies,
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"波动: {vol_label}"}

    # 原 print 输出
    print(f"""📉 体重波动分析（{start_date} ~ {end_date}）
{'-'*40}
  记录数：{len(rows)}条
  日间波动：±{std_dev:.2f}kg（标准差）
  周间波动：±{week_std:.2f}kg""")
    if anomalies:
        print(f"  异常记录（单日>0.5kg）：")
        for a in anomalies:
            print(f"    - {a['date']} {a['diff_kg']:+.1f}kg（{a['note']}）")
    else:
        print(f"  异常记录：无")
    print(f"  评估：{vol_label}{' ⚠️' if vol_status == 'error' else (' ✓' if vol_status == 'ok' else '')}")
    print(f"{'-'*40}")