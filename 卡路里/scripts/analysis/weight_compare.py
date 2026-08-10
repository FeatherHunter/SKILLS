#!/usr/bin/env python3
"""体重对比分析 — 18 个对比体重场景(A1-A8/B1/B8/E1-E6/C5/D4 · ticket #4)

纯分析层:输入 = weight_log 记录,输出 = 对比数据契约(render_weight_compare.py 消费)

场景:
  a1 最近 30 天 vs 之前 30 天       a2 自定义两段时间
  a3 本周 vs 上周                   a4 本月 vs 上月
  a5 近 N 天 vs 上一个 N 天          a6 今天 vs 一年前今天
  a7 今天 vs 半年后今天              a8 今天 vs 三月前今天
  b1 当前 vs 目标体重                b8 当前 vs 平台期首日
  e1 当前 vs 历史最低                e2 当前 vs 历史最高
  e3 减重 N kg 那天 vs 今天(5/10)     e5 当前 vs 入夏最低
  e6 当前 vs 入冬最低                c5 运动多 vs 运动少的两个月
  d4 工作日 vs 周末

规则(2026-08-02 · 用户拍板,SKILL.md 落地):
  - a3 每段记录数 ≥3 才对比,否则「样本不足」
  - a6-a8 同期对比 ±3 天容差,容差命中说明
  - b8 平台期 = 至少连续 14 天波动 ≤ ±0.5kg;取最近一次;统计第几次 + 历史平均突破耗时
  - e3 里程碑 = 从历史最高起累计减重 N kg 的第一个达标日
  - e5 入夏 = 当年 6/1-8/31;e6 入冬 = 12/1-次年 2/28(最近一个冬天)
  - c5 极端月 = 运动总量最高/最低的自然月;睡眠数据缺失 → 标注缺失(只读外部技能)
"""
import statistics
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from db import find_db_path, get_db  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent


def _db():
    p = find_db_path(SKILL_DIR)
    return get_db(p)


def _fetch_rows(start, end):
    """升序取区间记录 [(date, kg), ...]"""
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT date, weight_kg FROM weight_log WHERE date BETWEEN ? AND ? ORDER BY date', (start, end))
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _fetch_all():
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT date, weight_kg FROM weight_log ORDER BY date')
    rows = cur.fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def _seg(rows, label):
    """段统计(均值/起止/净变化/波动)"""
    if not rows:
        return None
    kgs = [r[1] for r in rows]
    return {
        'label': label,
        'range': f"{rows[0][0]} ~ {rows[-1][0]}",
        'count': len(rows),
        'avg': round(statistics.mean(kgs), 2),
        'start_kg': rows[0][1],
        'end_kg': rows[-1][1],
        'net_change': round(rows[-1][1] - rows[0][1], 2),
        'volatility': round(max(kgs) - min(kgs), 2),
    }


def _rate(seg):
    d0 = date.fromisoformat(seg['range'][:10])
    d1 = date.fromisoformat(seg['range'][-10:])
    days = max(1, (d1 - d0).days)
    return seg['net_change'] / days


def compare_pair(a, b, label_a, label_b):
    """两段对比:Δkg/方向/速率差 g/天/速度判断

    速度语义(2026-08-02 对抗审查修复):减重速度 = -net_change/days(正值=下降快)。
    后段速度 - 前段速度:正 = 后段更快,负 = 后段更慢,|差| ≤ 0.005 kg/天 = 持平。
    """
    delta = round(b['avg'] - a['avg'], 2)
    direction = '下降' if delta < -0.05 else ('上升' if delta > 0.05 else '持平')
    speed_a = -_rate(a)
    speed_b = -_rate(b)
    diff = speed_b - speed_a
    rate_diff_g = round(diff * 1000)
    if abs(diff) <= 0.005:
        speed = '持平'
    elif diff < 0:
        speed = '慢了'
    else:
        speed = '快了'
    return {
        'delta_kg': delta,
        'direction': direction,
        'rate_diff_g': rate_diff_g,
        'speed': speed,
    }


def _month_range(offset):
    """offset=0 本月;offset=-1 上月(自然月起止)"""
    today = date.today()
    first = today.replace(day=1)
    if offset == 0:
        return first.isoformat(), today.isoformat()
    prev_end = first - timedelta(days=1)
    return prev_end.replace(day=1).isoformat(), prev_end.isoformat()


def _sub_months(d, months):
    y, m = d.year, d.month - months
    while m <= 0:
        m += 12
        y -= 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return d.replace(year=y, month=m, day=day)


def _nearest(rows, target_d, tolerance=3):
    """±tolerance 天容差内最近的记录 → (hit_row, offset_days)"""
    best, best_off = None, None
    for r in rows:
        off = abs((date.fromisoformat(r[0]) - target_d).days)
        if off <= tolerance and (best_off is None or off < best_off):
            best, best_off = r, off
    return best, best_off


# ---------------- 18 场景 ----------------

def scenario_a1():
    """最近 30 天 vs 之前 30 天"""
    today = date.today()
    seg2 = today - timedelta(days=29)
    seg1_end = seg2 - timedelta(days=1)
    seg1_start = seg1_end - timedelta(days=29)
    a = _seg(_fetch_rows(seg1_start.isoformat(), seg1_end.isoformat()), '之前 30 天')
    b = _seg(_fetch_rows(seg2.isoformat(), today.isoformat()), '最近 30 天')
    if not a or not b:
        return None, '数据不足(需两段各有记录)'
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'a', 'b')}, None


def scenario_a2(start_a, end_a, start_b, end_b):
    a = _seg(_fetch_rows(start_a, end_a), '第一段')
    b = _seg(_fetch_rows(start_b, end_b), '第二段')
    if not a or not b:
        return None, '数据不足(某段无记录)'
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'a', 'b')}, None


def scenario_a3():
    """本周 vs 上周(自然周;每段 ≥3 条才对比)"""
    today = date.today()
    this_mon = today - timedelta(days=today.weekday())
    last_mon = this_mon - timedelta(days=7)
    a = _seg(_fetch_rows(last_mon.isoformat(), (last_mon + timedelta(days=6)).isoformat()), '上周')
    b = _seg(_fetch_rows(this_mon.isoformat(), today.isoformat()), '本周')
    if not a or not b:
        return None, '数据不足(本周/上周无记录)'
    if a['count'] < 3 or b['count'] < 3:
        return {'seg_a': a, 'seg_b': b, 'sample_warning': '样本不足(每段需 ≥3 条记录才能对比)'}, None
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'a', 'b')}, None


def scenario_a4():
    """本月 vs 上月"""
    a_s, a_e = _month_range(-1)
    b_s, b_e = _month_range(0)
    a = _seg(_fetch_rows(a_s, a_e), '上月')
    b = _seg(_fetch_rows(b_s, b_e), '本月')
    if not a or not b:
        return None, '数据不足(本月/上月无记录)'
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'a', 'b')}, None


def scenario_a5(n):
    """近 N 天 vs 上 N 天(滚动窗口)"""
    today = date.today()
    b_start = today - timedelta(days=n - 1)
    a_end = b_start - timedelta(days=1)
    a_start = a_end - timedelta(days=n - 1)
    a = _seg(_fetch_rows(a_start.isoformat(), a_end.isoformat()), f'上一个 {n} 天')
    b = _seg(_fetch_rows(b_start.isoformat(), today.isoformat()), f'最近 {n} 天')
    if not a or not b:
        return None, '数据不足(两段需各有记录)'
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'a', 'b')}, None


def _same_day_compare(months_back, label):
    """今天 vs N 月前今天(±3 天容差)"""
    today = date.today()
    target = _sub_months(today, months_back)
    rows = _fetch_all()
    hit, off = _nearest(rows, target)
    current = rows[-1][1] if rows else None
    if current is None:
        return None, '无体重记录'
    if not hit:
        return {'seg_a': {'label': label, 'range': '±3 天无记录', 'count': 0,
                          'avg': None, 'start_kg': None, 'end_kg': None,
                          'net_change': None, 'volatility': None},
                'seg_b': {'label': '今天', 'range': today.isoformat(), 'count': 1,
                          'avg': current, 'start_kg': current, 'end_kg': current,
                          'net_change': 0, 'volatility': 0},
                'compare': {'delta_kg': None, 'direction': '—', 'rate_diff_g': None, 'speed': '—'},
                'tolerance': {'hit': False, 'target': target.isoformat(), 'note': f'{target.isoformat()} ±3 天内无记录'},
                'extra_rows': [{'label': '容差命中', 'value': '未命中'}]}, None
    delta = round(current - hit[1], 2)
    direction = '下降' if delta < -0.05 else ('上升' if delta > 0.05 else '持平')
    # 区间段均值(一年内 / 半年内 / 三个月内)
    window = {'一年前': 365, '半年前': 182, '三月前': 91}[label]
    w_rows = _fetch_rows((today - timedelta(days=window)).isoformat(), today.isoformat())
    w_avg = round(statistics.mean([r[1] for r in w_rows]), 2) if w_rows else None
    return {
        'seg_a': {'label': label, 'range': hit[0], 'count': 1,
                  'avg': hit[1], 'start_kg': hit[1], 'end_kg': hit[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '今天', 'range': today.isoformat(), 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': delta, 'direction': direction, 'rate_diff_g': None, 'speed': '—'},
        'tolerance': {'hit': True, 'target': target.isoformat(),
                      'hit_date': hit[0], 'offset_days': off},
        'extra_rows': [
            {'label': '容差命中', 'value': f"{hit[0]}(±{off} 天)" if off else f"精确命中 {hit[0]}"},
            {'label': f'{label}内区间均值', 'value': f'{w_avg} kg' if w_avg is not None else '—'},
        ],
    }, None


def scenario_a6():
    return _same_day_compare(12, '一年前')


def scenario_a7():
    return _same_day_compare(6, '半年前')


def scenario_a8():
    return _same_day_compare(3, '三月前')


def scenario_b1():
    """当前 vs 目标体重(Δ/完成%/预计达成/BMI/达标)"""
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    conn = _db()
    cur = conn.cursor()
    cur.execute('SELECT weight_goal FROM daily_goal WHERE id = 1')
    g = cur.fetchone()
    cur.execute('SELECT height_cm FROM user_profile ORDER BY id DESC LIMIT 1')
    h = cur.fetchone()
    conn.close()
    goal = g[0] if g and g[0] else None
    if goal is None:
        return None, '未设置目标体重(请先「定体重目标」)'
    current = rows[-1][1]
    max_kg = max(r[1] for r in rows)
    height_m = (h[0] / 100) if h and h[0] else None
    delta = round(current - goal, 2)
    direction = '已达标' if delta <= 0 else f'还差 {delta:.1f} kg'
    pct_done = None
    if max_kg > goal:
        pct_done = round((max_kg - current) / (max_kg - goal) * 100, 1)
    # 预计达成(按近 30 天速率)
    today = date.today()
    recent = _fetch_rows((today - timedelta(days=29)).isoformat(), today.isoformat())
    eta = None
    if recent and len(recent) >= 2 and current > goal:
        rate = (recent[-1][1] - recent[0][1]) / max(1, len(recent) - 1)
        if rate < -0.001:
            days_left = int((current - goal) / abs(rate))
            eta = (today + timedelta(days=days_left)).isoformat()
    cur_bmi = round(current / (height_m ** 2), 1) if height_m else None
    goal_bmi = round(goal / (height_m ** 2), 1) if height_m else None
    return {
        'seg_a': {'label': '目标体重', 'range': f'目标 {goal} kg', 'count': 1,
                  'avg': goal, 'start_kg': goal, 'end_kg': goal,
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': delta, 'direction': direction, 'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [
            {'label': '已完成', 'value': f'{pct_done}%' if pct_done is not None else '—'},
            {'label': '预计达成', 'value': eta or '—'},
            {'label': '当前 BMI', 'value': cur_bmi or '—'},
            {'label': '目标 BMI', 'value': goal_bmi or '—'},
            {'label': '是否达标', 'value': '✅ 已达标' if delta <= 0 else '未达标'},
        ],
    }, None


def _find_plateau(rows):
    """识别平台期:连续日期跨度 ≥14 天且段内 max-min ≤ 0.5kg 的段,取最近一个"""
    segs = []
    n = len(rows)
    for i in range(n):
        j = i
        lo = hi = rows[i][1]
        while j + 1 < n:
            nd = (date.fromisoformat(rows[j + 1][0]) - date.fromisoformat(rows[j][0])).days
            if nd > 2:  # 允许 1-2 天缺口
                break
            j += 1
            lo = min(lo, rows[j][1])
            hi = max(hi, rows[j][1])
            if hi - lo > 0.5:
                break
        span = (date.fromisoformat(rows[j][0]) - date.fromisoformat(rows[i][0])).days + 1
        if span >= 14 and hi - lo <= 0.5:
            segs.append((rows[i], rows[j], span))
    if not segs:
        return None
    # 取最近一个(结束日期最新)
    segs.sort(key=lambda s: s[1][0])
    return segs[-1]


def scenario_b8():
    """当前 vs 平台期首日(自动识别最近平台期)"""
    rows = _fetch_all()
    if not rows or len(rows) < 14:
        return None, '数据不足(需至少 14 天记录)'
    p = _find_plateau(rows)
    current = rows[-1][1]
    if not p:
        return None, '未识别到平台期(需至少连续 14 天波动 ≤ ±0.5kg)'
    start_row, end_row, span = p
    # 突破后变化:平台期结束后的第一段 vs 平台期均值
    after = [r for r in rows if r[0] > end_row[0]]
    plateau_avg = statistics.mean([r[1] for r in rows if start_row[0] <= r[0] <= end_row[0]])
    delta_after = round(current - plateau_avg, 2)
    # 第几次平台期 + 历史平均突破耗时
    plateau_count = 1
    break_days = []
    remaining = rows[:]
    while len(remaining) >= 14:
        q = _find_plateau(remaining)
        if not q:
            break
        plateau_count += 1
        s2, e2, sp2 = q
        nxt = [r for r in remaining if r[0] > e2[0]]
        if nxt:
            br = (date.fromisoformat(nxt[0][0]) - date.fromisoformat(e2[0])).days
            break_days.append(br)
        remaining = [r for r in remaining if r[0] < s2[0]]
    avg_break = round(statistics.mean(break_days), 0) if break_days else None
    return {
        'seg_a': {'label': '平台期首日', 'range': f"{start_row[0]}(持续 {span} 天)", 'count': span,
                  'avg': round(plateau_avg, 2), 'start_kg': start_row[1], 'end_kg': end_row[1],
                  'net_change': round(end_row[1] - start_row[1], 2),
                  'volatility': round(abs(end_row[1] - start_row[1]), 2)},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - plateau_avg, 2),
                    'direction': '下降' if current < plateau_avg else ('上升' if current > plateau_avg else '持平'),
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [
            {'label': '平台期持续', 'value': f'{span} 天'},
            {'label': '突破后变化', 'value': f'{delta_after:+.1f} kg'},
            {'label': '第几次平台期', 'value': f'第 {plateau_count} 次'},
            {'label': '历史平均突破耗时', 'value': f'{avg_break:.0f} 天' if avg_break else '—'},
        ],
    }, None


def scenario_e1():
    """当前 vs 历史最低"""
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    min_row = min(rows, key=lambda r: r[1])
    days_since = (date.today() - date.fromisoformat(min_row[0])).days
    return {
        'seg_a': {'label': '历史最低', 'range': min_row[0], 'count': 1,
                  'avg': min_row[1], 'start_kg': min_row[1], 'end_kg': min_row[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - min_row[1], 2),
                    'direction': '上升' if current > min_row[1] else '持平',
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [{'label': '距历史最低', 'value': f'{days_since} 天'}],
    }, None


def scenario_e2():
    """当前 vs 历史最高"""
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    max_row = max(rows, key=lambda r: r[1])
    dropped = round(max_row[1] - current, 2)
    days = max(1, (date.fromisoformat(rows[-1][0]) - date.fromisoformat(max_row[0])).days)
    rate = round(dropped / days, 3)
    return {
        'seg_a': {'label': '历史最高', 'range': max_row[0], 'count': 1,
                  'avg': max_row[1], 'start_kg': max_row[1], 'end_kg': max_row[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - max_row[1], 2),
                    'direction': '下降' if current < max_row[1] else '持平',
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [
            {'label': '已下降', 'value': f'{dropped:.1f} kg'},
            {'label': '下降速率', 'value': f'{rate:.3f} kg/天'},
        ],
    }, None


def scenario_e3(delta_kg):
    """减重 N kg 达成日 vs 今天(从历史最高起累计减 N kg 的第一个达标日)"""
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    max_kg = max(r[1] for r in rows)
    th = max_kg - delta_kg
    hit = next((r for r in rows if r[1] <= th), None)
    if not hit:
        diff = round(max_kg - current, 1)
        return None, f'未达成减重 {delta_kg}kg 里程碑(当前距历史最高已减 {diff}kg)'
    elapsed = max(1, (date.fromisoformat(rows[-1][0]) - date.fromisoformat(hit[0])).days)
    rate = round((current - hit[1]) / elapsed, 3)
    # 2026-08-10 #43 审查:轨迹改为结构化 spark 数据(模板渲染 SVG 迷你折线,取代文本长串)
    pts = [r for r in rows if r[0] >= hit[0]]
    cross_year = len(pts) > 1 and pts[0][0][:4] != pts[-1][0][:4]
    def _fmt(d):
        return d[-5:] if not cross_year else d[2:]  # MM-DD 或跨年 YY-MM-DD
    if len(pts) > 10:
        step = (len(pts) - 1) / 9
        idxs = sorted({int(i * step) for i in range(10)} | {len(pts) - 1})
        pts = [pts[i] for i in idxs]
    spark = [{'d': _fmt(r[0]), 'kg': r[1]} for r in pts]
    trajectory = f"{hit[1]} → {current} kg · {elapsed} 天"
    return {
        'seg_a': {'label': f'减重 {delta_kg}kg 那天', 'range': hit[0], 'count': 1,
                  'avg': hit[1], 'start_kg': hit[1], 'end_kg': hit[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '今天', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - hit[1], 2),
                    'direction': '下降' if current < hit[1] else ('上升' if current > hit[1] else '持平'),
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [
            {'label': '用时', 'value': f'{elapsed} 天'},
            {'label': '期间速率', 'value': f'{rate:.3f} kg/天'},
            {'label': '体重轨迹', 'value': trajectory, 'spark': spark},
        ],
    }, None


def _season_min(rows, season):
    """season='summer':当年 6/1-8/31;'winter':最近一个冬天 12/1-次年 2/28"""
    today = date.today()
    if season == 'summer':
        s, e = date(today.year, 6, 1), date(today.year, 8, 31)
    else:
        if today.month >= 12:
            s, e = date(today.year, 12, 1), date(today.year + 1, 2, 28)
        elif today.month <= 2:
            s, e = date(today.year - 1, 12, 1), date(today.year, 2, 28)
        else:
            s, e = date(today.year - 1, 12, 1), date(today.year, 2, 28)
    in_season = [r for r in rows if s.isoformat() <= r[0] <= e.isoformat()]
    if not in_season:
        return None, None
    return min(in_season, key=lambda r: r[1])


def scenario_e5():
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    m = _season_min(rows, 'summer')
    if not m:
        return None, '今年夏天(6-8 月)无体重记录'
    days_since = max(0, (date.today() - date.fromisoformat(m[0])).days)
    return {
        'seg_a': {'label': '入夏最低', 'range': m[0], 'count': 1,
                  'avg': m[1], 'start_kg': m[1], 'end_kg': m[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - m[1], 2),
                    'direction': '上升' if current > m[1] else ('下降' if current < m[1] else '持平'),
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [{'label': '距入夏最低', 'value': f'{days_since} 天'}],
    }, None


def scenario_e6():
    rows = _fetch_all()
    if not rows:
        return None, '无体重记录'
    current = rows[-1][1]
    m = _season_min(rows, 'winter')
    if not m:
        return None, '最近一个冬天(12-2 月)无体重记录'
    days_since = max(0, (date.today() - date.fromisoformat(m[0])).days)
    return {
        'seg_a': {'label': '入冬最低', 'range': m[0], 'count': 1,
                  'avg': m[1], 'start_kg': m[1], 'end_kg': m[1],
                  'net_change': 0, 'volatility': 0},
        'seg_b': {'label': '当前', 'range': rows[-1][0], 'count': 1,
                  'avg': current, 'start_kg': current, 'end_kg': current,
                  'net_change': 0, 'volatility': 0},
        'compare': {'delta_kg': round(current - m[1], 2),
                    'direction': '上升' if current > m[1] else ('下降' if current < m[1] else '持平'),
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [{'label': '距入冬最低', 'value': f'{days_since} 天'}],
    }, None


def _month_total(conn, month_start, month_end, table, col_sum, date_col='date'):
    """月内聚合(运动消耗/摄入):无记录 → None(标注缺失,避免 0 伪装)"""
    cur = conn.cursor()
    try:
        cur.execute(f'SELECT COUNT(*), COALESCE(SUM({col_sum}), 0) FROM {table} WHERE {date_col} BETWEEN ? AND ?',
                    (month_start, month_end))
        row = cur.fetchone()
        if not row or row[0] == 0:
            return None
        return round(row[1], 0)
    except Exception:
        return None


def _sleep_hours(conn, month_start, month_end):
    """只读外部技能(作息管家 schedule_data.db)睡眠时长(小时);读不到/无记录 → None"""
    try:
        import os
        db_dir = os.environ.get('SKILLS_DB_PATH', '')
        if not db_dir:
            from db import find_db_path as _fdp
            db_dir = str(_fdp(SKILL_DIR).parent)
        sched_db = Path(db_dir) / 'schedule_data.db'
        if not sched_db.exists():
            return None
        import sqlite3
        c = sqlite3.connect(str(sched_db))
        cur = c.cursor()
        cur.execute('''
            SELECT COUNT(*), COALESCE(SUM(duration_minutes), 0) FROM schedule_records
            WHERE date BETWEEN ? AND ? AND (category LIKE '%睡眠%' OR activity LIKE '%睡眠%')
        ''', (month_start, month_end))
        row = cur.fetchone()
        c.close()
        if not row or row[0] == 0:
            return None
        return round(row[1] / 60, 1)
    except Exception:
        return None


def scenario_c5():
    """运动多 vs 运动少的两个月(协变量:摄入 kcal + 睡眠时长)"""
    conn = _db()
    cur = conn.cursor()
    cur.execute('''
        SELECT strftime('%Y-%m', date) AS m, COALESCE(SUM(calories_burned), 0)
        FROM exercise_log WHERE date IS NOT NULL GROUP BY m ORDER BY m
    ''')
    months = cur.fetchall()
    if len(months) < 2:
        conn.close()
        return None, '数据不足(需至少 2 个月有运动记录)'
    low_m, high_m = months[0][0], months[-1][0]
    low_t, high_t = 0, 0
    for m, total in months:
        if total > high_t:
            high_t, high_m = total, m
        if low_t == 0 or total < low_t:
            low_t, low_m = total, m
    if low_m == high_m:
        conn.close()
        return None, '数据不足(各月运动量相同)'
    def m_range(m):
        y, mo = int(m[:4]), int(m[5:7])
        import calendar
        return f'{m}-01', f'{m}-{calendar.monthrange(y, mo)[1]}'
    low_s, low_e = m_range(low_m)
    high_s, high_e = m_range(high_m)
    a = _seg(_fetch_rows(low_s, low_e), f'{low_m}(运动最少)')
    b = _seg(_fetch_rows(high_s, high_e), f'{high_m}(运动最多)')
    cal_low = _month_total(conn, low_s, low_e, 'food_log', 'calories')
    cal_high = _month_total(conn, high_s, high_e, 'food_log', 'calories')
    sleep_low = _sleep_hours(conn, low_s, low_e)
    sleep_high = _sleep_hours(conn, high_s, high_e)
    conn.close()
    if not a or not b:
        return None, '数据不足(极端月无体重记录)'
    extra = [
        {'label': f'{low_m} 运动总量', 'value': f'{low_t:.0f} 卡'},
        {'label': f'{high_m} 运动总量', 'value': f'{high_t:.0f} 卡'},
    ]
    extra += [{'label': f'{low_m} 摄入', 'value': f'{cal_low:.0f} 卡'} if cal_low is not None else
              {'label': f'{low_m} 摄入', 'value': '缺失(无记录)'},
              {'label': f'{high_m} 摄入', 'value': f'{cal_high:.0f} 卡'} if cal_high is not None else
              {'label': f'{high_m} 摄入', 'value': '缺失(无记录)'}]
    if sleep_low is not None:
        extra += [{'label': f'{low_m} 睡眠', 'value': f'{sleep_low} 小时'},
                  {'label': f'{high_m} 睡眠', 'value': f'{sleep_high} 小时'}]
    else:
        extra.append({'label': '睡眠数据', 'value': '缺失(外部技能未记录)'})
    return {'seg_a': a, 'seg_b': b, 'compare': compare_pair(a, b, 'low', 'high'), 'extra_rows': extra}, None


def scenario_d4():
    """工作日 vs 周末(最近一周聚合)"""
    today = date.today()
    start = today - timedelta(days=6)
    rows = _fetch_rows(start.isoformat(), today.isoformat())
    if not rows:
        return None, '最近 7 天无记录'
    wd = [r for r in rows if date.fromisoformat(r[0]).weekday() < 5]
    we = [r for r in rows if date.fromisoformat(r[0]).weekday() >= 5]
    if not wd or not we:
        return None, '样本不足(工作日/周末需各有记录)'
    def stats(rr):
        kgs = [r[1] for r in rr]
        return round(statistics.mean(kgs), 2), round(statistics.stdev(kgs), 2) if len(kgs) > 1 else 0
    wd_avg, wd_vol = stats(wd)
    we_avg, we_vol = stats(we)
    delta = round(we_avg - wd_avg, 2)
    # 一致率:工作日与周末均值接近度(1 - |Δ|/1kg,封顶 100%)
    agreement = round(max(0, 1 - min(1, abs(delta))) * 100)
    return {
        'seg_a': {'label': '工作日', 'range': f'{wd[0][0]} ~ {wd[-1][0]}', 'count': len(wd),
                  'avg': wd_avg, 'start_kg': wd[0][1], 'end_kg': wd[-1][1],
                  'net_change': round(wd[-1][1] - wd[0][1], 2), 'volatility': round(wd_vol, 2)},
        'seg_b': {'label': '周末', 'range': f'{we[0][0]} ~ {we[-1][0]}', 'count': len(we),
                  'avg': we_avg, 'start_kg': we[0][1], 'end_kg': we[-1][1],
                  'net_change': round(we[-1][1] - we[0][1], 2), 'volatility': round(we_vol, 2)},
        'compare': {'delta_kg': delta, 'direction': '周末更高' if delta > 0.05 else ('周末更低' if delta < -0.05 else '持平'),
                    'rate_diff_g': None, 'speed': '—'},
        'extra_rows': [
            {'label': '工作日波动', 'value': f'±{wd_vol} kg'},
            {'label': '周末波动', 'value': f'±{we_vol} kg'},
            {'label': '一致率', 'value': f'{agreement}%'},
        ],
    }, None


SCENARIO_LABELS = {
    'a1': '对比体重：最近 30 天 vs 之前 30 天',
    'a2': '对比体重：自定义两段时间',
    'a3': '对比体重：本周 vs 上周',
    'a4': '对比体重：本月 vs 上月',
    'a5': '对比体重：近 N 天 vs 上一个 N 天',
    'a6': '对比体重：今天 vs 一年前今天',
    'a7': '对比体重：今天 vs 半年前今天',
    'a8': '对比体重：今天 vs 三月前今天',
    'b1': '对比体重：当前 vs 目标体重',
    'b8': '对比体重：当前 vs 平台期首日',
    'e1': '对比体重：当前 vs 历史最低',
    'e2': '对比体重：当前 vs 历史最高',
    'e3': '对比体重：减重 N kg 那天 vs 今天',
    'e5': '对比体重：当前 vs 入夏最低',
    'e6': '对比体重：当前 vs 入冬最低',
    'c5': '对比体重：运动多 vs 运动少的两个月',
    'd4': '对比体重：工作日 vs 周末',
}


def run_scenario(name, **kw):
    """统一入口:返回 (data_dict, error)"""
    handlers = {
        'a1': scenario_a1,
        'a2': lambda: scenario_a2(kw['start_a'], kw['end_a'], kw['start_b'], kw['end_b']),
        'a3': scenario_a3,
        'a4': scenario_a4,
        'a5': lambda: scenario_a5(int(kw.get('n', 30))),
        'a6': scenario_a6,
        'a7': scenario_a7,
        'a8': scenario_a8,
        'b1': scenario_b1,
        'b8': scenario_b8,
        'e1': scenario_e1,
        'e2': scenario_e2,
        'e3': lambda: scenario_e3(float(kw.get('delta', 5))),
        'e5': scenario_e5,
        'e6': scenario_e6,
        'c5': scenario_c5,
        'd4': scenario_d4,
    }
    if name not in handlers:
        return None, f'未知场景 {name}'
    return handlers[name]()
