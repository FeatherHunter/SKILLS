#!/usr/bin/env python3
"""
饼干记账 · 洞察生成器接口(公共层 · T0 #164 清单第 5 项)

第一性:洞察 = 规则事实 + AI 解读两层。
本模块 = **规则层(纯计算·零 AI 判断)**:把 bills 记录聚合成结构化事实,
供「看洞察 / 看异常」场景的 AI 解读使用(判断留给 AI,结合用户语境)。

边界(对抗式审查 2026-08-08):
- 只输出确定性可测试的聚合事实,不做任何「异常判定/值得说」判断
- 小样本友好:不设统计阈值(2σ 已否决),只给月度序列 + 均值/中位数 + 偏离度事实
- 输入只 bills;goals.json 等扩展标注演进

用法(供 AI 场景调用):
    from insights import build_insight_facts
    facts = build_insight_facts(records, months=6)

返回 facts:
    period:        区间汇总(总支出/总收入/净额/笔数/起止)
    category_dist: 分类分布(L1 聚合:支出/笔数/占比)
    monthly_trend: 月度序列(支出/收入/净额/笔数)+ mean/median/max_deviation(偏离度事实)
    top_expense:   大额支出 TOP N
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime


def _month_of(time_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' → 'YYYY-MM'"""
    return time_str[:7]


def _l1(category: str) -> str:
    """多级分类取 L1('餐饮/外卖/午餐' → '餐饮')"""
    return (category or "其他").split("/", 1)[0].strip() or "其他"


def build_insight_facts(records: list, months: int = 6, top_n: int = 10) -> dict:
    """规则层聚合:bills 记录 → 结构化洞察事实(纯计算,无 AI 判断)

    Args:
        records: fetch_all 结果(每项可 dict 访问: category/time/amount/note)
        months: 趋势窗口(近 N 个月,默认 6)
        top_n: 大额 TOP 条数

    Returns:
        结构化事实 dict(见模块 docstring)
    """
    # ── period 汇总 ──
    expense = income = 0.0
    count = 0
    times = []
    for r in records:
        amt = float(r["amount"] or 0)
        if amt < 0:
            expense += -amt
        else:
            income += amt
        count += 1
        times.append(str(r["time"]))
    times.sort()

    period = {
        "expense": round(expense, 2),
        "income": round(income, 2),
        "net": round(income - expense, 2),
        "count": count,
        "from": times[0] if times else "",
        "to": times[-1] if times else "",
    }

    # ── category_dist(L1 聚合,按支出降序) ──
    cat_tot = defaultdict(lambda: {"expense": 0.0, "count": 0})
    for r in records:
        amt = float(r["amount"] or 0)
        if amt < 0:
            l1 = _l1(r["category"])
            cat_tot[l1]["expense"] += -amt
            cat_tot[l1]["count"] += 1
    cat_total = sum(v["expense"] for v in cat_tot.values()) or 1.0
    category_dist = [
        {
            "category": c,
            "expense": round(v["expense"], 2),
            "count": v["count"],
            "pct": round(v["expense"] / cat_total * 100, 1),
        }
        for c, v in sorted(cat_tot.items(), key=lambda kv: -kv[1]["expense"])
    ]

    # ── monthly_trend(近 N 个月,含空月) ──
    by_month = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
    for r in records:
        m = _month_of(str(r["time"]))
        amt = float(r["amount"] or 0)
        by_month[m]["count"] += 1
        if amt < 0:
            by_month[m]["expense"] += -amt
        else:
            by_month[m]["income"] += amt

    # 生成近 N 个月序列(含无数据月,补零)
    months_seq = []
    if times:
        end = _month_of(times[-1])
        try:
            y, mo = int(end[:4]), int(end[5:7])
        except ValueError:
            y, mo = datetime.now().year, datetime.now().month
        for _ in range(max(months, 1)):
            months_seq.append(f"{y:04d}-{mo:02d}")
            mo -= 1
            if mo == 0:
                mo = 12
                y -= 1
        months_seq.reverse()

    monthly_trend = []
    for m in months_seq:
        d = by_month.get(m, {"expense": 0.0, "income": 0.0, "count": 0})
        monthly_trend.append({
            "month": m,
            "expense": round(d["expense"], 2),
            "income": round(d["income"], 2),
            "net": round(d["income"] - d["expense"], 2),
            "count": d["count"],
        })

    # 统计事实:均值/中位数/最大偏离度(不做异常判定,留给 AI)
    trend_stats = {}
    if monthly_trend:
        exp_vals = [m["expense"] for m in monthly_trend]
        mean = statistics.mean(exp_vals)
        median = statistics.median(exp_vals)
        devs = [
            (m["month"], round((m["expense"] - mean) / mean * 100, 1) if mean else 0.0)
            for m in monthly_trend
        ]
        max_dev = max(devs, key=lambda x: abs(x[1]))
        trend_stats = {
            "mean_expense": round(mean, 2),
            "median_expense": round(median, 2),
            "max_deviation": {"month": max_dev[0], "deviation_pct": max_dev[1]},
        }

    # ── top_expense(支出金额降序 TOP N) ──
    expenses = sorted(
        (r for r in records if float(r["amount"] or 0) < 0),
        key=lambda r: float(r["amount"]),
    )[:top_n]
    top_expense = [
        {
            "amount": round(float(r["amount"]), 2),
            "category": str(r["category"]),
            "time": str(r["time"]),
            "note": str(r["note"] or ""),
        }
        for r in expenses
    ]

    return {
        "period": period,
        "category_dist": category_dist,
        "monthly_trend": {"months": monthly_trend, **trend_stats},
        "top_expense": top_expense,
    }


def load_records(from_time: str = None, to_time: str = None) -> list:
    """便捷入口:直接查库拿记录(供 AI 场景调用)"""
    from db import fetch_all
    return fetch_all(from_time=from_time, to_time=to_time)


if __name__ == "__main__":
    import json
    import sys
    recs = load_records()
    facts = build_insight_facts(recs)
    print(json.dumps(facts, ensure_ascii=False, indent=2))
