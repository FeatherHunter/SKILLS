#!/usr/bin/env python3
"""运动分析 — 趋势/类型分布/缺口贡献

提供：
- exercise_trend              — 运动趋势（天数/时长/消耗/最长连续/最长休息）
- exercise_type_breakdown     — 运动类型分布（消耗/频次/时长占比）
- exercise_deficit_contribution — 运动对热量缺口的贡献占比
"""

import sys
from datetime import datetime, timedelta
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
    c.execute('SELECT SUM(calories) FROM food_log WHERE date >= ? AND date <= ?', (start_date, end_date))
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


def exercise_review(start_date, end_date=None, silent=False):
    """复盘训练 — 计划 vs 实绩对比

    对 [start_date, end_date] 范围内每一天：
    - 查 workout_plans 当天所有 session
    - 查 exercise_log 当天所有记录
    - 对比：完成组数 vs 计划组数
    - 标出漏做 / 超额 / 异常

    Args:
        start_date: 开始日期
        end_date: 结束日期（默认同日）
        silent: True 时不打印报告（仅 return data），供 HTML 渲染器调用避免污染输出

    Returns:
        dict: {date_str: {plan_week, sessions, plan_total_sets, actual_total_sets,
                          completion_rate, anomalies, note}}
    """
    from workout_plan import get_day_plan  # 懒加载,避免循环 import

    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()

    results = {}
    cur = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    while cur <= end_dt:
        date_str = cur.strftime('%Y-%m-%d')

        # 1) 拉 plan
        plan = get_day_plan(cur)
        plan_sessions = plan.get('sessions', [])
        plan_total_sets = sum(s.get('total_sets') or 0 for s in plan_sessions)
        session_labels = [s.get('session_label', '') for s in plan_sessions]

        # 2) 拉 exercise_log 当天所有记录
        c.execute('''
            SELECT id, exercise_type, duration_minutes, calories_burned,
                   set_index, reps, load_kg
            FROM exercise_log
            WHERE date = ?
            ORDER BY exercise_type, set_index
        ''', (date_str,))
        ex_rows = c.fetchall()

        # 3) 聚合实绩
        actual = {}
        for r in ex_rows:
            etype = r[1]
            if etype not in actual:
                actual[etype] = {'sets': 0, 'reps_total': 0, 'load_max': 0,
                                 'calories': 0, 'minutes': 0}
            actual[etype]['sets'] += 1
            actual[etype]['reps_total'] += r[5] or 0
            actual[etype]['load_max'] = max(actual[etype]['load_max'], r[6] or 0)
            actual[etype]['calories'] += r[3] or 0
            actual[etype]['minutes'] += r[2] or 0
        actual_total_sets = sum(v['sets'] for v in actual.values())

        # 4) 对比 + 异常
        anomalies = []
        note = None
        # 2026-07-13 加:date 早于 plan.start_date 时,plan 返 unstarted=True,独立分支
        if plan.get('unstarted'):
            note = f'计划尚未开始(起始 {plan["config"]["start_date"]})'
            completion_rate = None
        elif plan_total_sets == 0 and actual_total_sets == 0:
            note = '休息日 / 无计划无实绩'
            completion_rate = None
        elif plan_total_sets == 0 and actual_total_sets > 0:
            note = f'计划休息但实做了 {actual_total_sets} 组'
            completion_rate = None
            anomalies.append(f'⚠️ {note}')
        elif plan_total_sets > 0 and actual_total_sets == 0:
            note = '计划有训练但完全未做'
            completion_rate = 0.0
            anomalies.append(f'❌ {note}')
        else:
            completion_rate = actual_total_sets / plan_total_sets * 100
            if completion_rate < 50:
                anomalies.append(f'⚠️ 完成率仅 {completion_rate:.0f}%')
            elif completion_rate > 130:
                anomalies.append(f'⚠️ 超额完成 ({completion_rate:.0f}%)')

        results[date_str] = {
            'plan_week': plan.get('plan_week'),
            'sessions': session_labels,
            'plan_total_sets': plan_total_sets,
            'actual_total_sets': actual_total_sets,
            'completion_rate': completion_rate,
            'anomalies': anomalies,
            'note': note,
        }

        cur += timedelta(days=1)

    conn.close()

    # 5) 输出报告（silent=True 时不打印，仅 return）
    if not silent:
        print(f"📋 训练复盘（{start_date} ~ {end_date}）\n{'='*50}")
        for date_str, r in results.items():
            week_str = f" week {r['plan_week']}" if r['plan_week'] else ''
            print(f"\n【{date_str}】{week_str}")
            if r['sessions']:
                print(f"  计划: {' / '.join(r['sessions'])}")
            print(f"  计划组数: {r['plan_total_sets']} | 实做组数: {r['actual_total_sets']}")
            if r['completion_rate'] is not None:
                print(f"  完成率: {r['completion_rate']:.0f}%")
            if r['note']:
                print(f"  {r['note']}")
            for a in r['anomalies']:
                print(f"  {a}")
            print(f"\n{'='*50}")
    return results