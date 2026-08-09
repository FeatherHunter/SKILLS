#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_volatility_v2.py — 体重稳不稳（增强版）渲染 CLI(ticket #4 扩展)

场景:
  - 看体重稳不稳（增强版）→ 默认 30 天
  - 看本月波动 → --start 月初 --end 月末
  - 看最近 90 天波动 / 看最近 180 天波动 → --days 90/180
  - 看波动异常点 → --view anomalies-only(仅异常列表视图)

KPI 权威清单口径(2026-08-02):标准差 / 日均波动 / 异常次数(模板已改造)
+ Canvas 主图(±σ 带 + 目标线 toggle)+ 异常列表(含 reason)

CLI:
    python scripts/render_weight_volatility_v2.py [--days 30] [--start YYYY-MM-DD] [--end YYYY-MM-DD]
        [--baseline rolling|goal] [--view full|anomalies-only] [--text] [--output PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

TEMPLATE_PATH = SKILL_DIR / "templates" / "weight_volatility_v2.html"


def _default_output_path(scene_label: str) -> Path:
    """场景命名(2026-08-02 用户拍板):<场景名>_结果_<TS>.html"""
    skills_db = os.environ.get("SKILLS_DB_PATH")
    if skills_db:
        base = Path(skills_db) / "calorie_html"
    else:
        base = Path("D:/2Study/StudyNotes/.db/calorie_html")
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{scene_label}_{ts}.html"
    out = base / base_name
    suffix = 2
    while out.exists():
        out = base / f"{scene_label}_{ts}_{suffix}.html"
        suffix += 1
    return out


def _inject_data(html: str, data: dict) -> str:
    count = html.count("<!--INJECT-DATA-->")
    if count != 1:
        raise ValueError(f"模板占位符 <!--INJECT-DATA--> 出现 {count} 次,应为 1 次")
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return html.replace("<!--INJECT-DATA-->", f'<script>window.__DATA__ = {payload};</script>', 1)


def _augment_kpis(data: dict) -> dict:
    """权威清单口径 KPI 补充:stdev / daily_delta_avg / anomaly_stats(模板消费)"""
    points = data.get('points', [])
    if len(points) >= 2:
        kgs = [p['kg'] for p in points]
        data['stdev'] = round(statistics.stdev(kgs), 3)
        # 日均波动:近 7 天 |当日−昨日| 均值
        last7 = points[-7:]
        deltas = [abs(last7[i]['kg'] - last7[i - 1]['kg']) for i in range(1, len(last7))]
        data['daily_delta_avg'] = round(statistics.mean(deltas), 3) if deltas else 0
        prev7 = points[-14:-7]
        if len(prev7) >= 2:
            prev_deltas = [abs(prev7[i]['kg'] - prev7[i - 1]['kg']) for i in range(1, len(prev7))]
            data['daily_delta_prev'] = round(statistics.mean(prev_deltas), 3) if prev_deltas else None
        # 异常次数
        anomalies = data.get('recent_anomalies', [])
        yellow = sum(1 for a in anomalies if a.get('level') == 'yellow')
        red = sum(1 for a in anomalies if a.get('level') == 'red')
        data['anomaly_stats'] = {'total': len(anomalies), 'yellow': yellow, 'red': red}
    else:
        data['stdev'] = 0
        data['daily_delta_avg'] = 0
        data['anomaly_stats'] = {'total': 0, 'yellow': 0, 'red': 0}
    # 一句话判断(2026-08-02 · 呈现数据「+ 一句话」)
    std = data['stdev']
    astat = data['anomaly_stats']
    if std < 0.3 and astat['total'] == 0:
        data['summary'] = f"体重很稳:标准差 {std:.2f}kg,无异常点,日均波动 {data['daily_delta_avg']:.3f}kg"
    elif std < 0.5:
        data['summary'] = f"体重基本稳定:标准差 {std:.2f}kg,异常 {astat['total']} 次(黄 {astat['yellow']}/红 {astat['red']})"
    else:
        data['summary'] = f"体重波动较大:标准差 {std:.2f}kg,异常 {astat['total']} 次(黄 {astat['yellow']}/红 {astat['red']}),建议关注饮食与饮水"
    return data


def _format_text_output(data: dict, start: str, end: str) -> str:
    out = []
    out.append("# MODE=text · 适用: pipeline | grep / awk / wc-l 等")
    out.append(f"# 体重稳不稳(增强版) · {start} ~ {end} · baseline_mode={data.get('baseline_mode', '?')}")
    out.append(f"# stdev={data.get('stdev', 0)}kg  daily_delta_avg={data.get('daily_delta_avg', 0)}kg/天  anomaly_stats={data.get('anomaly_stats')}")
    th = data.get("thresholds", {})
    out.append(f"# thresholds: yellow±1.5σ={th.get('yellow', 0):.4f}  red±2.0σ={th.get('red', 0):.4f}")
    out.append("")
    out.append("date          kg      deviation  level")
    for p in data.get("points", []):
        out.append(f"{p['date']}   {p['kg']:.2f}   {p['deviation_kg']:+.2f}     {p['level']}")
    out.append("")
    out.append(f"# recent_anomalies ({len(data.get('recent_anomalies', []))}):")
    for a in data.get("recent_anomalies", []):
        out.append(f"  {a['date']}  {a['kg']:.2f}kg  {a['deviation_kg']:+.2f}kg  {a['level']}")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="体重稳不稳(增强版)渲染器(ticket #4)")
    parser.add_argument("--days", type=int, help="滚动窗口天数(看最近 90/180 天波动)")
    parser.add_argument("--start", help="起始日期(YYYY-MM-DD),默认 30 天前")
    parser.add_argument("--end", help="结束日期(YYYY-MM-DD),默认今天")
    parser.add_argument("--baseline", choices=["rolling", "goal"], default="rolling",
                        help="baseline mode(rolling=近期常态 / goal=目标)")
    parser.add_argument("--view", choices=["full", "anomalies-only"], default="full",
                        help="看波动异常点:anomalies-only(仅异常列表视图)")
    parser.add_argument("--text", action="store_true", help="纯文本输出(pipeline 友好)")
    parser.add_argument("--output", help="输出路径")
    args = parser.parse_args()

    end_date = args.end or date.today().strftime("%Y-%m-%d")
    if args.start:
        start_date = args.start
    elif args.days:
        start_date = (date.today() - timedelta(days=args.days - 1)).strftime("%Y-%m-%d")
    else:
        start_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")

    from analysis.weight import weight_volatility_v2
    result = weight_volatility_v2(start_date, end_date, baseline_mode=args.baseline)
    if result.get("status") != "ok":
        print(f"Error: {result.get('message', 'unknown')}", file=sys.stderr)
        return 1

    data = _augment_kpis(result["data"])

    # 看波动异常点:只保留异常视图数据(模板由 view 字段控制)
    data['view'] = args.view
    if args.view == 'anomalies-only':
        data['points'] = []
        data['early_warning'] = {}
        data['sigma_trend'] = []

    scene_label = '看体重稳不稳（增强版）' if args.view == 'full' else '看波动异常点'

    if args.text:
        out_text = _format_text_output(data, start_date, end_date)
        sys.stdout.write(out_text + "\n")
        return 0

    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = _inject_data(html, data)

    out = Path(args.output) if args.output else _default_output_path(scene_label)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    print(f"✅ {out}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out.absolute()}")
    return 0


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
