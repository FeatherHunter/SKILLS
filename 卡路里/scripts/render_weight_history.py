#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_history.py — 体重分析 HTML(共用,4 模式)

对应 SKILL.md 唤醒词:
  - 查体重历史 → mode='history' (默认)
  - 查体重趋势 → mode='trend'
  - 查体重波动 → mode='volatility'
  - 对比体重   → mode='compare'
对应模板: templates/weight_history.html
"""
import argparse, json, sys
from datetime import date, timedelta, datetime
from pathlib import Path
import statistics

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_history.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def _fetch_logs(conn, start, end):
    """从 weight_log 取 [start,end] 区间所有记录"""
    cur = conn.cursor()
    cur.execute('''
        SELECT date, weight_kg, note
        FROM weight_log
        WHERE date BETWEEN ? AND ?
        ORDER BY date
    ''', (start, end))
    rows = cur.fetchall()
    items = []
    prev = None
    height_m = None
    cur.execute('SELECT height_cm FROM user_profile ORDER BY id DESC LIMIT 1')
    h = cur.fetchone()
    if h: height_m = h[0] / 100
    for d, kg, note in rows:
        bmi = round(kg / (height_m ** 2), 1) if height_m else None
        delta = round(kg - prev, 1) if prev is not None else 0
        items.append({'date': d, 'kg': kg, 'bmi': bmi, 'delta': delta, 'note': note or ''})
        prev = kg
    return items


def _fetch_target(conn):
    cur = conn.cursor()
    cur.execute('SELECT weight_kg FROM weight_goal ORDER BY id DESC LIMIT 1')
    g = cur.fetchone()
    return g[0] if g else None


def build_data(start, end, mode='history'):
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    items = _fetch_logs(conn, start, end)
    target = _fetch_target(conn)
    conn.close()

    days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
    weights = [i['kg'] for i in items]

    if not items:
        return {'status':'ok', 'data':{'mode':mode, 'summary':empty_summary(mode), 'items':[], 'target':target, 'meta':empty_meta(start, end, days)}, 'message':'无数据'}

    if mode == 'history':
        avg = round(statistics.mean(weights), 2)
        delta_range = round(max(weights) - min(weights), 1)
        summary = build_history_summary(items, avg, delta_range)
    elif mode == 'trend':
        start_avg = weights[0]
        end_avg = weights[-1]
        delta = round(end_avg - start_avg, 2)
        daily_rate = round(delta / max(1, days - 1), 3)
        bmi = items[-1].get('bmi') or 22.5
        summary = build_trend_summary(items, start_avg, end_avg, delta, daily_rate, bmi)
    elif mode == 'volatility':
        std = round(statistics.stdev(weights), 2) if len(weights) > 1 else 0
        anomalies = [i for i in items if abs(i['delta']) > std * 2 if i['delta']]
        # 标记异常
        for i, it in enumerate(items):
            if i > 0 and abs(it['delta']) > std * 2 and std > 0:
                it['anomaly'] = True
        summary = build_volatility_summary(items, std, anomalies)
    else:  # compare
        mid = len(items) // 2
        before = items[:mid]
        after = items[mid:]
        summary = build_compare_summary(before, after)

    return {
        'status': 'ok',
        'data': {
            'summary': summary,
            'items': items,
            'target': target,
            'meta': {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()},
            'mode': mode,
        },
        'message': f'已生成 {mode} ({days} 天)',
    }


def empty_summary(mode):
    return {
        'history':    {'subtitle':'', 'k1':{ 'label':'记录数','value':'0','extra':''},
                        'k2':{ 'label':'平均体重','value':'—','extra':''},
                        'k3':{ 'label':'波动','value':'—','extra':''},
                        'k4':{ 'label':'BMR 估算','value':'—','extra':''},
                        'table_header':"<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"},
        'trend':      {'subtitle':'', 'k1':{ 'label':'当前体重','value':'—','extra':''},
                        'k2':{ 'label':'区间变化','value':'—','extra':''},
                        'k3':{ 'label':'日均变化','value':'—','extra':''},
                        'k4':{ 'label':'BMI','value':'—','extra':''},
                        'table_header':"<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"},
        'volatility': {'subtitle':'', 'k1':{ 'label':'记录数','value':'—','extra':''},
                        'k2':{ 'label':'标准差','value':'—','extra':''},
                        'k3':{ 'label':'波动评估','value':'—','extra':''},
                        'k4':{ 'label':'异常次数','value':'—','extra':''},
                        'table_header':"<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"},
        'compare':    {'subtitle':'', 'k1':{ 'label':'前期','value':'—','extra':''},
                        'k2':{ 'label':'后期','value':'—','extra':''},
                        'k3':{ 'label':'变化','value':'—','extra':''},
                        'k4':{ 'label':'日均','value':'—','extra':''},
                        'table_header':"<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"},
    }[mode]


def empty_meta(start, end, days):
    return {'start': start, 'end': end, 'days': days, 'today': date.today().isoformat()}


def build_history_summary(items, avg, delta_range):
    # 估算 BMR: Mifflin-St Jeor 公式 (假设男 30 岁 70 kg)
    weight = avg
    bmr = round(10 * weight + 6.25 * 175 - 5 * 30 + 5, 0)
    return {
        'subtitle': f'近 {len(items)} 天体重数据汇总',
        'k1': {'label':'记录数', 'value':str(len(items)), 'extra':f'共 {len(items)} 天'},
        'k2': {'label':'平均体重', 'value':f'{avg} kg', 'extra':f'最低 {min(i["kg"] for i in items)} · 最高 {max(i["kg"] for i in items)}'},
        'k3': {'label':'波动', 'value':f'{delta_range} kg', 'extra':'极小波动' if delta_range < 0.5 else '正常波动' if delta_range < 1.0 else '较大波动'},
        'k4': {'label':'BMR 估算', 'value':f'{bmr} 卡', 'extra':'<span style="color:#34c759">标准</span>' if bmr > 1500 else '偏低'},
        'table_header': "<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"
    }


def build_trend_summary(items, start_avg, end_avg, delta, daily_rate, bmi):
    direction = '↓ 下降' if delta < -0.1 else '↑ 上升' if delta > 0.1 else '→ 持平'
    pct = round(delta / start_avg * 100, 1) if start_avg else 0
    color_cls = 'good' if delta < 0 else 'bad'
    return {
        'subtitle': f'起始 {start_avg} → 结束 {end_avg} · 日均 {daily_rate:+.3f} kg',
        'k1': {'label':'当前体重', 'value':f'{end_avg} kg', 'extra':f'<span style="color:#34c759">↓ {abs(delta)} kg</span>' if delta < 0 else f'<span style="color:#ff3b30">↑ {delta} kg</span>'},
        'k2': {'label':f'{len(items)} 天变化', 'value':f'{delta:+} kg', 'extra':f'{pct:+}%'},
        'k3': {'label':'日均变化', 'value':f'{daily_rate:+.3f} kg/天', 'extra':'<span style="color:#34c759">减重方向</span>' if daily_rate < 0 else '稳定'},
        'k4': {'label':'当前 BMI', 'value':str(bmi), 'extra':'正常范围(18.5-24)' if 18.5 <= bmi <= 24 else '异常'},
        'table_header': "<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"
    }


def build_volatility_summary(items, std, anomalies):
    eval_ = '稳定 ✓' if std < 0.3 else '正常' if std < 0.5 else '波动较大 ⚠'
    return {
        'subtitle': f'近 {len(items)} 天日波动分析',
        'k1': {'label':'记录数', 'value':str(len(items)), 'extra':'共 7+ 天'},
        'k2': {'label':'标准差', 'value':f'{std} kg', 'extra':'健康波动 < 0.3'},
        'k3': {'label':'波动评估', 'value':eval_, 'extra':'<span style="color:#34c759">稳定</span>' if std < 0.3 else '<span style="color:#ff9500">关注</span>'},
        'k4': {'label':'异常次数', 'value':str(len(anomalies)), 'extra':'与均值偏差 ≥2σ'},
        'table_header': "<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"
    }


def build_compare_summary(before, after):
    if not before or not after:
        return empty_summary('compare')
    before_avg = round(statistics.mean([i['kg'] for i in before]), 2)
    after_avg = round(statistics.mean([i['kg'] for i in after]), 2)
    delta = round(after_avg - before_avg, 2)
    n_days = max(1, len(after))
    daily_rate = round(delta / n_days, 3)
    return {
        'subtitle': f'前 {len(before)} 天 vs 后 {len(after)} 天对比',
        'k1': {'label':f'前期均值', 'value':f'{before_avg} kg', 'extra':f'{len(before)} 天'},
        'k2': {'label':f'后期均值', 'value':f'{after_avg} kg', 'extra':f'{len(after)} 天'},
        'k3': {'label':'变化', 'value':f'{delta:+} kg', 'extra':'<span style="color:#34c759">减重</span>' if delta < 0 else '<span style="color:#ff3b30">增重</span>'},
        'k4': {'label':'日均', 'value':f'{daily_rate:+.3f} kg/天', 'extra':'对比'},
        'table_header': "<tr><th>日期</th><th class='num'>BMI</th><th class='num'>体重</th><th class='num'>vs 上次</th></tr>"
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染体重分析 HTML(共用模板 4 mode)')
    p.add_argument('--start')
    p.add_argument('--end')
    p.add_argument('--days', type=int, default=30)
    p.add_argument('--mode', choices=['history','trend','volatility','compare'], default='trend')
    p.add_argument('--mock')
    p.add_argument('--output')
    args = p.parse_args()
    if not args.start or not args.end:
        end_d = date.today()
        start_d = end_d - timedelta(days=args.days - 1)
        s, e = start_d.isoformat(), end_d.isoformat()
    else:
        s, e = args.start, args.end
    try:
        data = _load_data(args.mock) if args.mock else build_data(s, e, mode=args.mode)
        if 'mode' not in data['data']: data['data']['mode'] = args.mode
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'weight_{args.mode}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    n = len(data['data']['items'])
    print(f'✅ {out_path}')
    print(f'   模式: {args.mode} | 范围: {s} ~ {e} | {n} 条')
    return 0


if __name__ == '__main__':
    sys.exit(main())
