#!/usr/bin/env python3
"""运动分析 — 趋势/类型分布/缺口贡献

提供：
- exercise_trend              — 运动趋势（天数/时长/消耗/最长连续/最长休息）
- exercise_type_breakdown     — 运动类型分布（消耗/频次/时长占比）
- exercise_deficit_contribution — 运动对热量缺口的贡献占比
"""

import sys
from datetime import datetime
from pathlib import Path

from analysis._utils import _get_db, _parse_date, _days_between, BMR_ACTIVITY_FACTOR

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def exercise_trend(start_date, end_date=None):
    """运动趋势

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        list of Row
    """
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
    """运动类型分布（按消耗降序）

    Returns:
        list of Row
    """
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
    """运动对热量缺口的贡献占比

    评估：
    - ex_pct < 15% → 偏低，建议增加运动
    - ex_pct > 25% → 较高 ✓
    - 其他 → 适中
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT SUM(calories_burned) FROM exercise_log WHERE date >= ? AND date <= ?', (start_date, end_date))
    total_ex = c.fetchone()[0] or 0
    c.execute('SELECT SUM(calories) FROM entries WHERE date >= ? AND date <= ?', (start_date, end_date))
    total_intake = c.fetchone()[0] or 0
    conn.close()

    span = _days_between(start_date, end_date) + 1

    conn = _get_db()
    cur2 = conn.cursor()
    cur2.execute('SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = cur2.fetchone()
    conn.close()
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