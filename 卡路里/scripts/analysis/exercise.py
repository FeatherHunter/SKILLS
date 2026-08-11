#!/usr/bin/env python3
"""运动分析 — 趋势/类型分布/缺口贡献/复盘训练

提供：
- exercise_trend                  — 运动趋势（天数/时长/消耗/最长连续/最长休息）
- exercise_type_breakdown         — 运动类型分布（消耗/频次/时长占比）
- exercise_deficit_contribution   — 运动对热量缺口的贡献占比
- exercise_review                 — 复盘训练（计划 vs 实绩对比）

2026-07-23 D1 重构：所有函数加 as_dict=False 参数
- as_dict=True  → 返回结构化 dict {status, data, message}
- as_dict=False → 保持原 print 输出（向后兼容，默认）
"""
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from analysis._utils import _get_db, _parse_date, _days_between, get_activity_factor, get_profile_activity_level

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def exercise_trend(start_date, end_date=None, as_dict=False):
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
        msg = f"无运动记录（{start_date} ~ {end_date}）"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
        return None

    span = _days_between(start_date, end_date) + 1
    days_with_ex = len(set(r[0] for r in rows))
    total_cal = sum(r[3] for r in rows)
    total_dur = sum(r[2] or 0 for r in rows)
    avg_cal = total_cal / span
    avg_dur = total_dur / span

    # B-103 修复：duration_minutes 字段在 2026-07-13 之前为 NULL（旧代码未写入）
    # 检测：如果所有记录都是 NULL，说明是历史数据缺失，标注 is_duration_missing=True
    duration_missing = all(r[2] is None for r in rows)

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

    # 2026-07-23 D1 增
    data = {
        "days_with_exercise": days_with_ex,
        "total_days": span,
        "coverage_pct": round(days_with_ex / span * 100),
        "total_calories": total_cal,
        "total_minutes": total_dur,
        "avg_calories_per_day": round(avg_cal),
        "avg_minutes_per_day": round(avg_dur) if not duration_missing else None,
        "longest_streak_days": longest_streak,
        "longest_rest_days": max_gap,
        "alert": "建议动起来" if max_gap >= 7 else None,
        "duration_missing": duration_missing,  # B-103：标记时长数据是否缺失
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"运动 {days_with_ex}/{span} 天，总消耗 {total_cal} 卡"}

    # 原 print
    print(f"""🏃 运动趋势（{start_date} ~ {end_date}）
{'-'*40}
  运动天数：{days_with_ex}/{span}天（{days_with_ex/span*100:.0f}%）
  总时长：{total_dur}分钟 | 总消耗：{total_cal}卡
  日均消耗：{avg_cal:.0f}卡/天 | 日均时长：{avg_dur:.0f}分钟/天
  最长连续运动：{longest_streak}天
  最长休息：{max_gap}天{" ⚠️ 建议动起来" if max_gap >= 7 else ""}
{'-'*40}""")
    return rows


def exercise_type_breakdown(start_date, end_date=None, as_dict=False):
    """运动类型分布（按消耗降序）"""
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
        msg = f"无运动记录（{start_date} ~ {end_date}）"
        if as_dict:
            return {"status": "error", "data": None, "message": msg}
        print(f"⚠️ {msg}")
        return None

    total_cal = sum(r[1] for r in rows)
    total_cnt = sum(r[2] for r in rows)
    total_dur = sum(r[3] or 0 for r in rows)

    # 2026-07-23 D1 增
    types = [
        {
            "type": r[0],
            "calories": r[1],
            "count": r[2],
            "minutes": r[3] or 0,
            "cal_pct": round(r[1] / total_cal * 100),
            "count_pct": round(r[2] / total_cnt * 100) if total_cnt else 0,
            "minutes_pct": round((r[3] or 0) / total_dur * 100) if total_dur else 0,
        }
        for r in rows
    ]
    data = {
        "total_calories": total_cal,
        "total_count": total_cnt,
        "total_minutes": total_dur,
        "types": types,
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"{len(types)} 种运动类型"}

    print(f"📊 运动类型分布（{start_date} ~ {end_date}）\n{'-'*40}")
    for r in rows:
        etype, cal, cnt, dur = r
        pct = cal / total_cal * 100
        print(f"  {etype:15} 消耗{cal}卡（{pct:.0f}%）| {cnt}次 | {dur or 0}分钟")
    print(f"\n  总计：{total_cal}卡 | {total_cnt}次 | {total_dur}分钟")
    print(f"{'-'*40}")
    return rows


def exercise_deficit_contribution(start_date, end_date=None, as_dict=False):
    """运动对热量缺口的贡献占比"""
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
    bmr = current_weight * 24 * get_activity_factor(get_profile_activity_level())

    bmr_total = bmr * span
    diet_deficit = bmr_total - total_intake
    total_deficit = bmr_total - total_intake + total_ex

    if total_deficit == 0:
        diet_pct = 50
        ex_pct = 50
    else:
        diet_pct = abs(diet_deficit) / abs(total_deficit) * 100
        ex_pct = total_ex / abs(total_deficit) * 100

    if ex_pct < 15:
        eval_label = "运动贡献偏低，建议增加运动比例"
    elif ex_pct > 25:
        eval_label = "运动贡献较高"
    else:
        eval_label = "运动贡献适中"

    # 2026-07-23 D1 增
    data = {
        "diet_deficit": round(diet_deficit),
        "diet_contrib_pct": round(diet_pct),
        "exercise_deficit": round(total_ex),
        "exercise_contrib_pct": round(ex_pct),
        "evaluation": eval_label,
        "bmr": round(bmr),
        "current_weight": round(current_weight, 1),
    }

    if as_dict:
        return {"status": "ok", "data": data, "message": f"运动贡献 {round(ex_pct)}% — {eval_label}"}

    print(f"""💪 运动缺口贡献（{start_date} ~ {end_date}）
{'-'*40}
  饮食缺口：{diet_deficit:.0f}卡（{diet_pct:.0f}%）
  运动缺口：{total_ex:.0f}卡（{ex_pct:.0f}%）
  评估：{eval_label}{'' if '较低' in eval_label or '较高' in eval_label else ''}
{'-'*40}""")
    return {'diet_pct': diet_pct, 'ex_pct': ex_pct}


def exercise_review(start_date, end_date=None, as_dict=False, silent=False):
    """复盘训练 — 计划 vs 实绩对比

    对 [start_date, end_date] 范围内每一天：
    - 查 workout_plans 当天所有 session
    - 查 exercise_log 当天所有记录
    - 对比：完成组数 vs 计划组数
    - 标出漏做 / 超额 / 异常

    Args:
        as_dict: True 返回 dict；False print（默认）
        silent: 兼容旧调用，等同 as_dict=True（不打印）
    """
    from workout_plan import get_day_plan

    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    conn = _get_db()
    c = conn.cursor()

    results = {}
    cur = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    # #257 容量聚合（Σ kg×次数，仅 weight>0 & unit=kg / load_kg>0）
    vol_plan_week = defaultdict(float)      # 自然周 -> 计划容量
    vol_actual_week = defaultdict(float)    # 自然周 -> 实绩容量
    vol_plan_mov = defaultdict(float)       # (周, 动作名) -> 计划容量
    vol_actual_mov = defaultdict(float)     # (周, 动作名) -> 实绩容量
    vol_mov_total = defaultdict(lambda: {'plan': 0.0, 'actual': 0.0})  # 动作名 -> 容量合计(TOP4 用)
    vol_weeks = []                          # 有序自然周列表 ['2026-W30', ...]
    week_monday = {}                        # 自然周 -> 该周周一日期(date)

    def _iso_week(d):
        iso = d.isocalendar()
        return f'{iso[0]}-W{iso[1]:02d}'

    while cur <= end_dt:
        date_str = cur.strftime('%Y-%m-%d')
        wk = _iso_week(cur)
        if not vol_weeks or vol_weeks[-1] != wk:
            vol_weeks.append(wk)
            week_monday[wk] = cur

        plan = get_day_plan(cur)
        plan_sessions = plan.get('sessions', [])
        plan_total_sets = sum(s.get('total_sets') or 0 for s in plan_sessions)
        session_labels = [s.get('session_label', '') for s in plan_sessions]

        # 计划容量：movements[].sets[].weight × reps，仅 unit=kg 且 weight>0
        for s in plan_sessions:
            for m in s.get('movements', []):
                name = m.get('name', '')
                for st in m.get('sets', []) or []:
                    try:
                        w = float(st.get('weight') or 0)
                        reps = int(float(st.get('reps') or 0))
                    except (TypeError, ValueError):
                        w, reps = 0, 0
                    if w <= 0 or reps <= 0:
                        continue
                    # unit 缺省/空/显式 kg 都计入；min/秒/次 等非重量单位排除
                    unit = st.get('unit') or ''
                    if unit and unit != 'kg':
                        continue
                    ton = w * reps
                    vol_plan_week[wk] += ton
                    vol_plan_mov[(wk, name)] += ton
                    vol_mov_total[name]['plan'] += ton

        c.execute('''
            SELECT id, exercise_type, duration_minutes, calories_burned,
                   set_index, reps, load_kg
            FROM exercise_log
            WHERE date = ?
            ORDER BY exercise_type, set_index
        ''', (date_str,))
        ex_rows = c.fetchall()

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
            # #257 实绩容量：Σ load_kg × reps
            load = r[6] or 0
            reps = r[5] or 0
            if load > 0 and reps > 0:
                ton = load * reps
                vol_actual_week[wk] += ton
                vol_actual_mov[(wk, etype)] += ton
                vol_mov_total[etype]['actual'] += ton
        actual_total_sets = sum(v['sets'] for v in actual.values())

        anomalies = []
        note = None
        if plan.get('unstarted'):
            note = f'计划尚未开始(起始 {plan["config"]["start_date"]})'
            completion_rate = None
        elif plan_total_sets == 0 and actual_total_sets == 0:
            note = '休息日 / 无计划无实绩'
            completion_rate = None
        elif plan_total_sets == 0 and actual_total_sets > 0:
            note = f'计划休息但实做了 {actual_total_sets} 组'
            completion_rate = None
            anomalies.append({'type': 'rest_but_done', 'msg': f'⚠️ {note}'})
        elif plan_total_sets > 0 and actual_total_sets == 0:
            note = '计划有训练但完全未做'
            completion_rate = 0.0
            anomalies.append({'type': 'no_actual', 'msg': f'❌ {note}'})
        else:
            # B-305 修复：完成率定义 = 实际组数 / 计划组数 × 100
            # 之前曾有"按动作名匹配"和"按组数"两种算法混用，2026-07-23 统一为"按组数"
            # 设计理由：动作级匹配复杂（plan 的动作可能多个变体），组数最直接
            completion_rate = actual_total_sets / plan_total_sets * 100
            completion_metric = "组数"
            if completion_rate < 50:
                anomalies.append({'type': 'low_completion', 'msg': f'⚠️ 完成率仅 {completion_rate:.0f}%（实做 {actual_total_sets}/{plan_total_sets} {completion_metric}）'})
            elif completion_rate > 130:
                anomalies.append({'type': 'over_completion', 'msg': f'⚠️ 超额完成 ({completion_rate:.0f}%)（{actual_total_sets}/{plan_total_sets} {completion_metric}）'})

        results[date_str] = {
            'date': date_str,
            'plan_week': plan.get('plan_week'),
            'sessions': session_labels,
            'plan_total_sets': plan_total_sets,
            'actual_total_sets': actual_total_sets,
            'calories_burned': sum(v['calories'] for v in actual.values()),  # 2026-08-02 ticket #6:复盘消耗 KPI
            'completion_rate': completion_rate,
            'anomalies': anomalies,
            'note': note,
            'is_rest_day': plan_total_sets == 0 and actual_total_sets == 0,
        }

        cur += timedelta(days=1)

    conn.close()

    # B-304 修复：聚合 by_severity（异常严重度统计）
    # 让 HTML 模板能展示"哪些类型异常最多"
    by_severity_count = {'low_completion': 0, 'over_completion': 0, 'no_actual': 0, 'rest_but_done': 0}
    by_severity_by_movement = defaultdict(lambda: defaultdict(int))  # {type: {movement_name: cnt}}
    for date_str, r in results.items():
        for a in r.get('anomalies', []):
            atype = a.get('type')
            if atype in by_severity_count:
                by_severity_count[atype] += 1

    # #257 组装 volume：周容量柱状（计划 vs 实做）+ 主项 TOP4 负荷折线
    def _week_label(wk):
        """'2026-W30' -> '7/20~26'（ISO 周一到周日）"""
        try:
            monday = week_monday[wk]
            sunday = monday + timedelta(days=6)
            if monday.month == sunday.month:
                return f'{monday.month}/{monday.day}~{sunday.day}'
            return f'{monday.month}/{monday.day}~{sunday.month}/{sunday.day}'
        except Exception:
            return wk

    volume_weeks = []
    for wk in vol_weeks:
        volume_weeks.append({
            'week': wk,
            'label': _week_label(wk),
            'plan': round(vol_plan_week.get(wk, 0.0)),
            'actual': round(vol_actual_week.get(wk, 0.0)),
            'actual_sets': 0,  # 由模板按需补充（不额外查询）
        })

    # 主项 TOP4：按 (计划+实绩) 容量合计排序
    top_names = sorted(vol_mov_total.keys(),
                       key=lambda n: -(vol_mov_total[n]['plan'] + vol_mov_total[n]['actual']))[:4]
    volume_movements = []
    for name in top_names:
        weeks = []
        for wk in vol_weeks:
            weeks.append({
                'week': wk,
                'label': _week_label(wk),
                'plan': round(vol_plan_mov.get((wk, name), 0.0)),
                'actual': round(vol_actual_mov.get((wk, name), 0.0)),
            })
        volume_movements.append({
            'name': name,
            'plan_total': round(vol_mov_total[name]['plan']),
            'actual_total': round(vol_mov_total[name]['actual']),
            'weeks': weeks,
        })

    total_actual_ton = sum(vol_actual_week.values())
    enriched_meta = {
        'by_severity_count': by_severity_count,
        'total_days': len(results),
        'train_days': sum(1 for r in results.values() if not r.get('is_rest_day')),
        'rest_days': sum(1 for r in results.values() if r.get('is_rest_day')),
        'total_calories': sum(r.get('calories_burned') or 0 for r in results.values()),
        'volume': {
            'weeks': volume_weeks,
            'movements': volume_movements,
            'total_plan': round(sum(vol_plan_week.values())),
            'total_actual': round(total_actual_ton),
            'has_actual': total_actual_ton > 0,
        },
    }

    if as_dict or silent:
        return {
            "status": "ok",
            "data": {**results, "__meta__": enriched_meta},
            "message": f"训练复盘 {len(results)} 天"
        }

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
            print(f"  {a['msg']}")
        print(f"\n{'='*50}")
    return results