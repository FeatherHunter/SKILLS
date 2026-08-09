#!/usr/bin/env python3
"""饼干记账 · 分析域 CLI(25 场景 · 直达式 · scenes/analysis.yaml)

场景 → 子命令:
    汇总 4:  看月度 → monthly --month | 看年度 → yearly --year
             看总览 → overview [--from --to|--month] | 看周报 → week [--offset 0|1]
    结构 4:  看分类 → category [--from --to --account --type]
             看账户 → account | 看账本 → ledger | 看结构 → structure
    对比 4:  看对比 → compare --period week|month
             看双区间 → range_compare --from1 --to1 --from2 --to2
             看同比 → yoy --month | 看分类对比 → cat_compare --from1 --to1 --from2 --to2
    趋势 2:  看趋势 → trend --months N | 看分类趋势 → cat_trend --category X --months N
    金额 3:  看大额 → top --limit N [--from --to]
             看高频 → top_freq [--from --to] | 看分布 → distribution [--from --to --type]
    统计洞察 4: 做统计 → stats | 看活跃 → activity
             看洞察 → insight [--months N] | 看异常 → anomaly [--months N]
    状态聚合 4: 看借贷 → debt_summary | 看报销 → reimburse_summary
             看分期 → installment_summary | 看退款 → refund_summary

数据单一源 = fetch_all(软删排除);聚合纯计算,判定留给 AI。

用法:
    python3 scripts/analysis/cli.py monthly --month 2026-05
    python3 scripts/analysis/cli.py yearly --year 2026
    python3 scripts/analysis/cli.py category --from 2026-05-01 --to 2026-05-31 --account 支付宝
    python3 scripts/analysis/cli.py range_compare --from1 2026-05-01 --to1 2026-05-31 --from2 2026-04-01 --to2 2026-04-30
    python3 scripts/analysis/cli.py trend --months 12
    python3 scripts/analysis/cli.py insight --months 6
    python3 scripts/analysis/cli.py debt_summary
"""

import sys
import re
import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import fetch_all
from analyze import monthly_summary, compare_periods, get_category_breakdown
from cli_utils import reconfigure_utf8, emit_ok, emit_error
from insights import build_insight_facts

reconfigure_utf8()


# ── 通用工具(纯计算 · 单一数据源 = fetch_all)────────────────────────────────

def _l1(category: str) -> str:
    """多级分类取 L1('餐饮/外卖/午餐' → '餐饮')"""
    return (category or "其他").split("/", 1)[0].strip() or "其他"


def _month_of(time_str: str) -> str:
    """'YYYY-MM-DD HH:MM:SS' → 'YYYY-MM'"""
    return (time_str or "")[:7]


def _month_range(month: str) -> tuple:
    """'YYYY-MM' → (起 'YYYY-MM-DD 00:00:00', 止 'YYYY-MM-DD 23:59:59')"""
    try:
        y, mo = int(month[:4]), int(month[5:7])
        last = calendar.monthrange(y, mo)[1]
        return f"{month}-01 00:00:00", f"{month}-{last:02d} 23:59:59"
    except (ValueError, IndexError):
        raise ValueError(f"月份格式应为 YYYY-MM,收到: {month}")


def _year_range(year: int) -> tuple:
    return f"{year}-01-01 00:00:00", f"{year}-12-31 23:59:59"


def _calc_kpi(records: list) -> dict:
    """KPI:笔数/支出/收入/净额(支出按绝对值累计)"""
    count = len(records)
    expense = sum(abs(r["amount"]) for r in records if r.get("amount", 0) < 0)
    income = sum(r["amount"] for r in records if r.get("amount", 0) > 0)
    return {"count": count, "expense": round(expense, 2), "income": round(income, 2),
            "net": round(income - expense, 2)}


def _fetch(from_time: str = None, to_time: str = None) -> list:
    return fetch_all(from_time=from_time, to_time=to_time)


def _filter(records: list, *, account=None, ledger=None, type_=None, category_l1=None):
    """组合筛选:账户/账本/收支方向/L1 分类前缀"""
    out = records
    if account:
        out = [r for r in out if r.get("account") == account]
    if ledger:
        out = [r for r in out if r.get("ledger") == ledger]
    if type_ == "expense":
        out = [r for r in out if r.get("amount", 0) < 0]
    elif type_ == "income":
        out = [r for r in out if r.get("amount", 0) > 0]
    if category_l1:
        out = [r for r in out
               if _l1(r.get("category")) == category_l1
               or (r.get("category") or "").startswith(category_l1 + "/")]
    return out


def _agg_expense_by(records: list, key_fn, *, top_n=None, direction: str = "expense") -> list:
    """按 key 聚合(expense=支出绝对值 / income=收入):[{key, expense|income, count}] 降序"""
    agg = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
    for r in records:
        amt = r.get("amount", 0)
        if direction == "expense":
            if amt >= 0:
                continue
            agg[key_fn(r)]["expense"] += abs(amt)
        else:
            if amt <= 0:
                continue
            agg[key_fn(r)]["income"] += amt
        agg[key_fn(r)]["count"] += 1
    metric = "expense" if direction == "expense" else "income"
    out = [{"key": k, metric: round(v[metric], 2), "count": v["count"]} for k, v in agg.items()]
    out.sort(key=lambda x: x[metric], reverse=True)
    if top_n:
        out = out[:top_n]
    total = sum(x[metric] for x in out) or 1.0
    for x in out:
        x["pct"] = round(x[metric] / total * 100, 1)
    return out


def _month_series(records: list, months: int) -> list:
    """近 N 个月逐月序列(含空月补零):[{month, expense, income, net, count}]"""
    by_month = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
    for r in records:
        m = _month_of(str(r.get("time") or ""))
        amt = float(r.get("amount") or 0)
        by_month[m]["count"] += 1
        if amt < 0:
            by_month[m]["expense"] += -amt
        else:
            by_month[m]["income"] += amt
    # 序列终点 = 最新一条记录所在月(fetch_all 按 time DESC,records[0] 最新)
    end = _month_of(str(records[0].get("time") or "")) if records else ""
    if not end:
        end = date.today().strftime("%Y-%m")
    try:
        y, mo = int(end[:4]), int(end[5:7])
    except ValueError:
        y, mo = date.today().year, date.today().month
    seq = []
    for _ in range(max(months, 1)):
        seq.append(f"{y:04d}-{mo:02d}")
        mo -= 1
        if mo == 0:
            mo = 12
            y -= 1
    seq.reverse()
    return [{"month": m, "expense": round(by_month[m]["expense"], 2),
             "income": round(by_month[m]["income"], 2),
             "net": round(by_month[m]["income"] - by_month[m]["expense"], 2),
             "count": by_month[m]["count"]} for m in seq]


def _compare_two(r1: list, r2: list, label1: str, label2: str) -> dict:
    """双段对比:双 KPI + 变化率(支出侧)"""
    k1, k2 = _calc_kpi(r1), _calc_kpi(r2)
    diff = k1["expense"] - k2["expense"]
    pct = round(diff / k2["expense"] * 100, 1) if k2["expense"] else 0.0
    return {
        "period_a": {**k1, "label": label1},
        "period_b": {**k2, "label": label2},
        "change": {"expense_diff": round(diff, 2), "expense_pct": pct},
    }


# ── 汇总 4 ──────────────────────────────────────────────────────────────────

def cmd_monthly(args):
    """看月度:KPI4 + 分类排行条 + 区间标注(兼容旧接口)"""
    result = monthly_summary(args.month)
    result["count"] = result.get("count", 0)
    if getattr(args, 'json', False):
        emit_ok(result, f"{args.month} 月度汇总")
        return result
    print(f"=== {args.month} 月度汇总 ===")
    print(f"支出: {result.get('expense', 0):.2f} / 收入: {result.get('income', 0):.2f} / 净额: {result.get('net', 0):.2f}")
    for c in result.get('categories', []):
        print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('count', 0)}笔)")
    return result


def cmd_yearly(args):
    """看年度:总 KPI + 逐月趋势表 + 大额分类 TOP"""
    year = args.year or date.today().year
    from_time, to_time = _year_range(int(year))
    records = _fetch(from_time, to_time)
    kpi = _calc_kpi(records)
    monthly = _month_series(records, 12)
    cats = _agg_expense_by(records, lambda r: _l1(r.get("category")), top_n=8)
    data = {"year": year, **kpi, "monthly": monthly, "top_categories": cats}
    if getattr(args, 'json', False):
        emit_ok(data, f"{year} 年度汇总")
        return data
    print(f"=== {year} 年度汇总 ===")
    print(f"支出: {kpi['expense']:.2f} / 收入: {kpi['income']:.2f} / 净额: {kpi['net']:.2f} / {kpi['count']}笔")
    for m in monthly:
        print(f"  {m['month']}: 支出 {m['expense']:.2f} / 收入 {m['income']:.2f} / {m['count']}笔")
    return data


def cmd_overview(args):
    """看总览:4 KPI + 日均支出 + 区间标注(兼容旧 --month)"""
    if args.from_date or args.to_date:
        from_time = f"{args.from_date} 00:00:00" if args.from_date else None
        to_time = f"{args.to_date} 23:59:59" if args.to_date else None
        if bool(from_time) != bool(to_time):
            raise ValueError("--from 和 --to 必须同时指定")
        label = f"{args.from_date} ~ {args.to_date}"
        days = max((date.fromisoformat(args.to_date) - date.fromisoformat(args.from_date)).days + 1, 1)
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        label = month
        y, mo = int(month[:4]), int(month[5:7])
        days = calendar.monthrange(y, mo)[1]
    records = _fetch(from_time, to_time)
    kpi = _calc_kpi(records)
    kpi["daily_avg"] = round(kpi["expense"] / days, 2)
    data = {"period": label, "from": (from_time or "")[:10], "to": (to_time or "")[:10], **kpi}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 收支总览")
        return data
    print(f"=== {label} 收支总览 ===")
    print(f"笔数: {kpi['count']} / 支出: {kpi['expense']:.2f} / 收入: {kpi['income']:.2f} / 净额: {kpi['net']:.2f} / 日均支出: {kpi['daily_avg']:.2f}")
    return data


def cmd_week(args):
    """看周报:本周 KPI + 本周 vs 上周双卡 + 本周大额支出"""
    offset = args.offset or 0
    today = date.today()
    this_week_start = today - timedelta(days=today.weekday() + 7 * offset)
    this_week_end = this_week_start + timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end = this_week_start - timedelta(days=1)

    this = _fetch(f"{this_week_start} 00:00:00", f"{this_week_end} 23:59:59")
    last = _fetch(f"{last_week_start} 00:00:00", f"{last_week_end} 23:59:59")
    kpi = _calc_kpi(this)
    cmp = _compare_two(
        this, last,
        f"{this_week_start:%m/%d}~{this_week_end:%m/%d} 周",
        f"{last_week_start:%m/%d}~{last_week_end:%m/%d} 周",
    )
    top = sorted((r for r in this if r.get("amount", 0) < 0), key=lambda r: r["amount"])[:5]
    data = {"week": f"{this_week_start:%Y-%m-%d}~{this_week_end:%Y-%m-%d}", **kpi,
            "compare": cmp, "top_expenses": top}
    if getattr(args, 'json', False):
        emit_ok(data, "本周简报")
        return data
    print(f"=== 本周简报 {this_week_start:%m/%d}~{this_week_end:%m/%d} ===")
    print(f"支出: {kpi['expense']:.2f} / 收入: {kpi['income']:.2f} / 净额: {kpi['net']:.2f} / {kpi['count']}笔")
    c = cmp["change"]
    print(f"对比上周: 支出 {'↑' if c['expense_diff'] > 0 else '↓' if c['expense_diff'] < 0 else '→'} {abs(c['expense_diff']):.2f} ({abs(c['expense_pct']):.1f}%)")
    return data


# ── 结构 4 ──────────────────────────────────────────────────────────────────

def cmd_category(args):
    """看分类:SVG 环形图数据(L1 聚合)+ 排行(总额/占比/笔数/均值)"""
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        from_time, to_time = f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59"
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        label = month
    records = _filter(_fetch(from_time, to_time), account=args.account, type_=args.type)
    cats = _agg_expense_by(records, lambda r: _l1(r.get("category")),
                           direction="income" if args.type == "income" else "expense")
    metric = "income" if args.type == "income" else "expense"
    total = sum(c[metric] for c in cats)
    for c in cats:
        c["avg"] = round(c[metric] / c["count"], 2) if c["count"] else 0
    data = {"period": label, "from": from_time[:10], "to": to_time[:10],
            "grand_total": round(total, 2), "categories": cats,
            "filter": {"account": args.account} if args.account else {},
            "records": records}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 分类占比")
        return data
    print(f"=== {label} 分类占比 ===")
    for c in cats:
        print(f"  {c['key']}: {c['expense']:.2f} ({c['pct']:.1f}%) [{c['count']}笔, 均{c['avg']:.1f}]")
    return data


def cmd_account(args):
    """看账户:账户占比条 + 各账户汇总(支出/收入/净额)"""
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        from_time, to_time = f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59"
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        label = month
    records = _fetch(from_time, to_time)
    agg = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
    for r in records:
        acc = r.get("account") or "未填账户"
        amt = float(r.get("amount") or 0)
        agg[acc]["count"] += 1
        if amt < 0:
            agg[acc]["expense"] += -amt
        else:
            agg[acc]["income"] += amt
    items = [{"account": k, "expense": round(v["expense"], 2), "income": round(v["income"], 2),
              "net": round(v["income"] - v["expense"], 2), "count": v["count"]}
             for k, v in agg.items()]
    items.sort(key=lambda x: x["expense"], reverse=True)
    total_expense = sum(x["expense"] for x in items) or 1.0
    for x in items:
        x["pct"] = round(x["expense"] / total_expense * 100, 1)
    data = {"period": label, "from": from_time[:10], "to": to_time[:10],
            "accounts": items, "count": len(records)}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 账户占比")
        return data
    print(f"=== {label} 账户占比 ===")
    for x in items:
        print(f"  {x['account']}: 支出 {x['expense']:.2f} ({x['pct']:.1f}%) / 收入 {x['income']:.2f} / 净额 {x['net']:.2f}")
    return data


def cmd_ledger(args):
    """看账本:各账本汇总卡(支出/收入/净额)+ 占比"""
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        from_time, to_time = f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59"
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        label = month
    records = _fetch(from_time, to_time)
    agg = defaultdict(lambda: {"expense": 0.0, "income": 0.0, "count": 0})
    for r in records:
        lg = r.get("ledger") or "未分账本"
        amt = float(r.get("amount") or 0)
        agg[lg]["count"] += 1
        if amt < 0:
            agg[lg]["expense"] += -amt
        else:
            agg[lg]["income"] += amt
    items = [{"ledger": k, "expense": round(v["expense"], 2), "income": round(v["income"], 2),
              "net": round(v["income"] - v["expense"], 2), "count": v["count"]}
             for k, v in agg.items()]
    items.sort(key=lambda x: x["expense"], reverse=True)
    total_expense = sum(x["expense"] for x in items) or 1.0
    for x in items:
        x["pct"] = round(x["expense"] / total_expense * 100, 1)
    data = {"period": label, "from": from_time[:10], "to": to_time[:10],
            "ledgers": items, "count": len(records)}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 账本汇总")
        return data
    print(f"=== {label} 账本汇总 ===")
    for x in items:
        print(f"  {x['ledger']}: 支出 {x['expense']:.2f} ({x['pct']:.1f}%) / 收入 {x['income']:.2f} / 净额 {x['net']:.2f}")
    return data


def cmd_structure(args):
    """看结构:双环形图数据(收入来源 L1 + 支出去向 L1)"""
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        from_time, to_time = f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59"
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        label = month
    records = _fetch(from_time, to_time)
    inc = _agg_expense_by([r for r in records if r.get("amount", 0) > 0],
                          lambda r: _l1(r.get("category")), direction="income")
    exp = _agg_expense_by([r for r in records if r.get("amount", 0) < 0], lambda r: _l1(r.get("category")))
    data = {"period": label, "from": from_time[:10], "to": to_time[:10],
            "income_structure": inc, "expense_structure": exp,
            "income_total": round(sum(x["income"] for x in inc), 2),
            "expense_total": round(sum(x["expense"] for x in exp), 2)}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 收支结构")
        return data
    print(f"=== {label} 收支结构 ===")
    print("收入来源:")
    for x in inc:
        print(f"  {x['key']}: {x['income']:.2f}")
    print("支出去向:")
    for x in exp:
        print(f"  {x['key']}: {x['expense']:.2f}")
    return data


# ── 对比 4 ──────────────────────────────────────────────────────────────────

def cmd_compare(args):
    """看对比:本期 vs 上期(兼容旧接口 week/month)"""
    result = compare_periods(args.period)
    if "error" in result:
        raise ValueError(result["error"])
    # 变化率统一 round 1 位(与其他对比命令一致;analyze.py 原样返回未 round)
    if "change" in result and result["change"]:
        result["change"]["expense_pct"] = round(result["change"].get("expense_pct") or 0, 1)
    if getattr(args, 'json', False):
        emit_ok(result, f"{'周' if args.period == 'week' else '月'}度对比")
        return result
    t, l, c = result.get('this', {}), result.get('last', {}), result.get('change', {})
    diff, pct = c.get('expense_diff', 0), c.get('expense_pct', 0)
    direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
    print(f"=== {t.get('label', '本期')} vs {l.get('label', '上期')} ===")
    print(f"本期: 支出 {t.get('expense', 0):.2f} / 收入 {t.get('income', 0):.2f} / 净额 {t.get('net', 0):.2f}")
    print(f"上期: 支出 {l.get('expense', 0):.2f} / 收入 {l.get('income', 0):.2f} / 净额 {l.get('net', 0):.2f}")
    print(f"支出 {direction} {abs(diff):.2f} ({abs(pct):.1f}%)")
    return result


def cmd_range_compare(args):
    """看双区间:两段时间对比(双卡 + 变化率 + 分类差异 TOP)"""
    if not (args.from1 and args.to1 and args.from2 and args.to2):
        raise ValueError("--from1/--to1/--from2/--to2 必须全部指定")
    r1 = _fetch(f"{args.from1} 00:00:00", f"{args.to1} 23:59:59")
    r2 = _fetch(f"{args.from2} 00:00:00", f"{args.to2} 23:59:59")
    cmp = _compare_two(r1, r2, f"{args.from1}~{args.to1}", f"{args.from2}~{args.to2}")
    c1 = _agg_expense_by(r1, lambda r: _l1(r.get("category")))
    c2 = {x["key"]: x for x in _agg_expense_by(r2, lambda r: _l1(r.get("category")))}
    diffs = []
    for x in c1:
        other = c2.get(x["key"], {"expense": 0, "count": 0})
        diffs.append({"category": x["key"], "a": x["expense"], "b": other["expense"],
                      "diff": round(x["expense"] - other["expense"], 2)})
    for x in _agg_expense_by(r2, lambda r: _l1(r.get("category"))):
        if x["key"] not in {d["category"] for d in diffs}:
            diffs.append({"category": x["key"], "a": 0, "b": x["expense"],
                          "diff": round(-x["expense"], 2)})
    diffs.sort(key=lambda d: abs(d["diff"]), reverse=True)
    data = {**cmp, "category_diffs": diffs[:8]}
    if getattr(args, 'json', False):
        emit_ok(data, "双区间对比")
        return data
    c = cmp["change"]
    print(f"=== {cmp['period_a']['label']} vs {cmp['period_b']['label']} ===")
    print(f"支出 {'↑' if c['expense_diff'] > 0 else '↓' if c['expense_diff'] < 0 else '→'} {abs(c['expense_diff']):.2f} ({abs(c['expense_pct']):.1f}%)")
    return data


def cmd_yoy(args):
    """看同比:今年某月 vs 去年同月"""
    month = args.month or date.today().strftime("%Y-%m")
    y = int(month[:4])
    if y < 2000:
        raise ValueError(f"月份年份异常: {month}")
    last_month = f"{y - 1}-{month[5:]}"
    r1 = _fetch(*_month_range(month))
    r2 = _fetch(*_month_range(last_month))
    cmp = _compare_two(r1, r2, f"{month} 今年", f"{last_month} 去年")
    data = {"month": month, "last_month": last_month, **cmp}
    if getattr(args, 'json', False):
        emit_ok(data, f"{month} 同比")
        return data
    c = cmp["change"]
    print(f"=== {month}(今年) vs {last_month}(去年) ===")
    print(f"支出 {'↑' if c['expense_diff'] > 0 else '↓' if c['expense_diff'] < 0 else '→'} {abs(c['expense_diff']):.2f} ({abs(c['expense_pct']):.1f}%)")
    return data


def cmd_cat_compare(args):
    """看分类对比:两段时间分类差异 TOP(金额变化最大/笔数变化最大)"""
    if not (args.from1 and args.to1 and args.from2 and args.to2):
        raise ValueError("--from1/--to1/--from2/--to2 必须全部指定")
    r1 = _filter(_fetch(f"{args.from1} 00:00:00", f"{args.to1} 23:59:59"), type_="expense")
    r2 = _filter(_fetch(f"{args.from2} 00:00:00", f"{args.to2} 23:59:59"), type_="expense")
    agg1 = defaultdict(lambda: {"expense": 0.0, "count": 0})
    for r in r1:
        k = _l1(r.get("category"))
        agg1[k]["expense"] += abs(r["amount"])
        agg1[k]["count"] += 1
    agg2 = defaultdict(lambda: {"expense": 0.0, "count": 0})
    for r in r2:
        k = _l1(r.get("category"))
        agg2[k]["expense"] += abs(r["amount"])
        agg2[k]["count"] += 1
    keys = set(agg1) | set(agg2)
    rows = []
    for k in keys:
        a, b = agg1.get(k, {"expense": 0, "count": 0}), agg2.get(k, {"expense": 0, "count": 0})
        rows.append({"category": k, "a_expense": round(a["expense"], 2), "b_expense": round(b["expense"], 2),
                     "amount_diff": round(a["expense"] - b["expense"], 2),
                     "a_count": a["count"], "b_count": b["count"],
                     "count_diff": a["count"] - b["count"]})
    rows.sort(key=lambda x: abs(x["amount_diff"]), reverse=True)
    data = {"from1": args.from1, "to1": args.to1, "from2": args.from2, "to2": args.to2,
            "rows": rows[:10]}
    if getattr(args, 'json', False):
        emit_ok(data, "分类对比")
        return data
    print(f"=== 分类差异 TOP({args.from1}~{args.to1} vs {args.from2}~{args.to2}) ===")
    for x in rows[:10]:
        d = x["amount_diff"]
        print(f"  {x['category']}: {'↑' if d > 0 else '↓' if d < 0 else '→'} {abs(d):.2f}")
    return data


# ── 趋势 2 ──────────────────────────────────────────────────────────────────

def cmd_trend(args):
    """看趋势:SVG 双线折线(支出/收入逐月)+ 峰值 + 月均"""
    months = args.months or 12
    records = _fetch()
    series = _month_series(records, months)
    exp_vals = [m["expense"] for m in series]
    peak = max(exp_vals, default=0)
    peak_month = next((m["month"] for m in series if m["expense"] == peak), "")
    avg = round(sum(exp_vals) / len(exp_vals), 2) if exp_vals else 0
    data = {"months": months, "series": series, "peak": {"month": peak_month, "expense": peak},
            "avg_expense": avg}
    if getattr(args, 'json', False):
        emit_ok(data, "收支趋势")
        return data
    print(f"=== 近 {months} 个月收支趋势 ===")
    for m in series:
        bar = "█" * min(int(m["expense"] / (peak or 1) * 20), 20)
        print(f"  {m['month']}: {m['expense']:.2f} {bar}")
    print(f"峰值: {peak_month} {peak:.2f} / 月均支出: {avg:.2f}")
    return data


def cmd_cat_trend(args):
    """看分类趋势:某分类逐月支出 + 月均 + 峰值月"""
    cat = args.category or "餐饮"
    months = args.months or 12
    records = _fetch()
    cat_recs = _filter(records, category_l1=cat)
    series = _month_series(cat_recs, months)
    exp_vals = [m["expense"] for m in series]
    peak = max(exp_vals, default=0)
    peak_month = next((m["month"] for m in series if m["expense"] == peak), "")
    avg = round(sum(exp_vals) / len(exp_vals), 2) if exp_vals else 0
    data = {"category": cat, "months": months, "series": series,
            "peak": {"month": peak_month, "expense": peak}, "avg_expense": avg}
    if getattr(args, 'json', False):
        emit_ok(data, f"{cat} 分类趋势")
        return data
    print(f"=== {cat} 近 {months} 个月趋势 ===")
    for m in series:
        bar = "█" * min(int(m["expense"] / (peak or 1) * 20), 20)
        print(f"  {m['month']}: {m['expense']:.2f} {bar}")
    print(f"峰值: {peak_month} {peak:.2f} / 月均: {avg:.2f}")
    return data


# ── 金额 3 ──────────────────────────────────────────────────────────────────

def cmd_top(args):
    """看大额:支出 TOP N 排行(金额/分类/日期/备注)"""
    limit = args.limit or 10
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        records = _fetch(f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59")
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        records = _fetch()
        label = "全部时间"
    expenses = sorted((r for r in records if r.get("amount", 0) < 0), key=lambda r: r["amount"])[:limit]
    items = [{"amount": round(r["amount"], 2), "category": r.get("category", ""),
              "time": r.get("time", ""), "note": r.get("note", ""), "id": r.get("id")}
             for r in expenses]
    data = {"limit": limit, "period": label, "items": items, "count": len(items)}
    if getattr(args, 'json', False):
        emit_ok(data, f"大额支出 TOP{limit}")
        return data
    print(f"=== 大额支出 TOP{limit} ({label}) ===")
    for i, x in enumerate(items, 1):
        print(f"  {i}. {x['time']} | {x['category']} | {x['amount']:.2f} | {x['note']}")
    return data


def cmd_top_freq(args):
    """看高频:分类笔数 TOP(笔数/总金额/单均/最近一笔时间)"""
    limit = args.limit or 10
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        records = _fetch(f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59")
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        records = _fetch()
        label = "全部时间"
    agg = defaultdict(lambda: {"count": 0, "total": 0.0, "last": ""})
    for r in records:
        if r.get("amount", 0) >= 0:
            continue
        k = _l1(r.get("category"))
        agg[k]["count"] += 1
        agg[k]["total"] += abs(r["amount"])
        if r.get("time", "") > agg[k]["last"]:
            agg[k]["last"] = r.get("time", "")
    items = [{"category": k, "count": v["count"], "total": round(v["total"], 2),
              "avg": round(v["total"] / v["count"], 2), "last_time": v["last"]}
             for k, v in agg.items()]
    items.sort(key=lambda x: x["count"], reverse=True)
    items = items[:limit]
    data = {"limit": limit, "period": label, "items": items, "count": len(items)}
    if getattr(args, 'json', False):
        emit_ok(data, f"高频消费 TOP{limit}")
        return data
    print(f"=== 高频消费 TOP{limit} ({label}) ===")
    for i, x in enumerate(items, 1):
        print(f"  {i}. {x['category']}: {x['count']}笔 / {x['total']:.2f}元 / 单均{x['avg']:.2f} / 最近{x['last_time']}")
    return data


def cmd_distribution(args):
    """看分布:金额区间直方(<10/10-50/50-100/100-500/500+)"""
    buckets = [("10 元以下", 0, 10), ("10~50", 10, 50), ("50~100", 50, 100),
               ("100~500", 100, 500), ("500 以上", 500, None)]
    if args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        records = _fetch(f"{args.from_date} 00:00:00", f"{args.to_date} 23:59:59")
        label = f"{args.from_date} ~ {args.to_date}"
    else:
        month = args.month or date.today().strftime("%Y-%m")
        from_time, to_time = _month_range(month)
        records = _fetch(from_time, to_time)
        label = month
    type_ = args.type or "expense"
    recs = [r for r in records if (r.get("amount", 0) < 0 if type_ == "expense" else r.get("amount", 0) > 0)]
    total = len(recs) or 1
    items = []
    for name, lo, hi in buckets:
        if hi is None:
            cnt = sum(1 for r in recs if abs(r["amount"]) >= lo)
        else:
            cnt = sum(1 for r in recs if lo <= abs(r["amount"]) < hi)
        items.append({"bucket": name, "count": cnt, "pct": round(cnt / total * 100, 1)})
    data = {"period": label, "type": "支出" if type_ == "expense" else "收入",
            "total": len(recs), "buckets": items}
    if getattr(args, 'json', False):
        emit_ok(data, f"{label} 金额分布")
        return data
    print(f"=== {label} 金额分布({data['type']}) ===")
    for x in items:
        bar = "█" * min(x["count"], 30)
        print(f"  {x['bucket']}: {x['count']}笔 ({x['pct']:.1f}%) {bar}")
    return data


# ── 统计洞察 4 ──────────────────────────────────────────────────────────────

def cmd_stats(args):
    """做统计:总笔数/记账天数/日均笔数/首末记录时间 + 月度分布(兼容旧接口)"""
    records = _fetch()
    kpi = _calc_kpi(records)
    days = len({str(r.get("time") or "")[:10] for r in records})
    times = sorted(str(r.get("time") or "") for r in records)
    by_month = defaultdict(int)
    for r in records:
        by_month[_month_of(str(r.get("time") or ""))] += 1
    monthly = [{"month": k, "count": v} for k, v in sorted(by_month.items())]
    data = {"total_records": kpi["count"], "total_days": days,
            "daily_avg": round(kpi["count"] / days, 2) if days else 0,
            "first_record": times[0] if times else None,
            "last_record": times[-1] if times else None,
            "monthly_dist": monthly}
    if getattr(args, 'json', False):
        emit_ok(data, "记账统计")
        return data
    print(f"=== 记账统计 ===")
    print(f"总笔数: {data['total_records']} / 记账天数: {data['total_days']} / 日均: {data['daily_avg']}")
    print(f"首笔: {data['first_record'] or 'N/A'} / 最近: {data['last_record'] or 'N/A'}")
    return data


def cmd_activity(args):
    """看活跃:周几分布柱状 + 时段分布"""
    records = _fetch()
    weekday = defaultdict(int)
    hour = defaultdict(int)
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    for r in records:
        ts = str(r.get("time") or "")
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", ts)
        if m:
            try:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                weekday[weekday_names[d.weekday()]] += 1
            except ValueError:
                pass
        hm = re.search(r"(\d{2}):", ts)
        if hm:
            hour[int(hm.group(1))] += 1
    weekdays = [{"weekday": w, "count": weekday.get(w, 0)} for w in weekday_names]
    hours = [{"hour": f"{h:02d}", "count": hour.get(h, 0)} for h in range(24)]
    data = {"weekdays": weekdays, "hours": hours, "total": len(records)}
    if getattr(args, 'json', False):
        emit_ok(data, "记账活跃度")
        return data
    print(f"=== 记账活跃度 ===")
    for x in weekdays:
        print(f"  {x['weekday']}: {x['count']}")
    return data


def cmd_insight(args):
    """看洞察:洞察生成器事实(period/category_dist/monthly_trend/top_expense)"""
    months = args.months or 6
    records = _fetch()
    facts = build_insight_facts(records, months=months, top_n=args.top_n or 10)
    facts["window_months"] = months
    if getattr(args, 'json', False):
        emit_ok(facts, f"AI 消费洞察(近{months}个月)")
        return facts
    print(f"=== AI 消费洞察(近{months}个月) ===")
    p = facts["period"]
    print(f"区间: {p['from']} ~ {p['to']} · 支出 {p['expense']:.2f} / 收入 {p['income']:.2f} / 净额 {p['net']:.2f}")
    for c in facts["category_dist"][:8]:
        print(f"  {c['category']}: {c['expense']:.2f} ({c['pct']:.1f}%)")
    return facts


def cmd_anomaly(args):
    """看异常:月度序列 + 环比变化 + 分类环比暴涨(事实层,判定留给 AI)"""
    months = args.months or 6
    records = _fetch()
    if not records:
        data = {"window_months": months, "series": [], "month_over_month": [],
                "category_surge": [], "total": 0}
        if getattr(args, 'json', False):
            emit_ok(data, "异常波动检测(空)")
            return data
        print("(无记录)")
        return data
    facts = build_insight_facts(records, months=months)
    series = facts["monthly_trend"]["months"]
    mom = []
    for i in range(1, len(series)):
        prev, cur = series[i - 1]["expense"], series[i]["expense"]
        if prev > 0:
            mom.append({"month": series[i]["month"], "prev": prev, "cur": cur,
                        "diff": round(cur - prev, 2),
                        "pct": round((cur - prev) / prev * 100, 1)})
    # 分类环比暴涨:最近月 vs 上一月
    by_month = defaultdict(lambda: defaultdict(float))
    for r in records:
        by_month[_month_of(str(r.get("time") or ""))][_l1(r.get("category"))] += abs(r.get("amount") or 0)
    months_sorted = sorted(by_month.keys())
    surge = []
    if len(months_sorted) >= 2:
        last, prev = months_sorted[-1], months_sorted[-2]
        for cat in by_month[last]:
            cur_v = by_month[last][cat]
            prev_v = by_month[prev].get(cat, 0.0)
            if prev_v > 0 and cur_v > prev_v:
                surge.append({"category": cat, "month": last, "prev_month": prev,
                              "prev": round(prev_v, 2), "cur": round(cur_v, 2),
                              "pct": round((cur_v - prev_v) / prev_v * 100, 1)})
    surge.sort(key=lambda x: x["pct"], reverse=True)
    data = {"window_months": months, "series": series, "month_over_month": mom,
            "category_surge": surge[:10], "total": len(records)}
    if getattr(args, 'json', False):
        emit_ok(data, "异常波动检测")
        return data
    print(f"=== 异常波动检测(近{months}个月) ===")
    for x in mom:
        print(f"  {x['month']}: {'↑' if x['pct'] > 0 else '↓'} {abs(x['pct']):.1f}% ({x['prev']:.2f} → {x['cur']:.2f})")
    for x in surge:
        print(f"  分类 {x['category']}: {x['prev']:.2f} → {x['cur']:.2f} (+{x['pct']:.1f}%)")
    return data


# ── 状态聚合 4(#tag 聚合)────────────────────────────────────────────────────

def _tag_match(note: str, tag: str) -> bool:
    """#tag 精确匹配(与查询域同规则)"""
    if not note:
        return False
    sep = r"[\s,，。.．;；:：!！?？)）]"
    return re.search(rf"(^|{sep})#{re.escape(tag)}(?={sep}|$)", note) is not None


def _tag_records(tag: str) -> list:
    from db import search_keyword
    return [r for r in search_keyword(f"#{tag}") if _tag_match(r.get("note") or "", tag)]


def cmd_debt_summary(args):
    """看借贷:借出/借入未还总额 + 对象列表 + 已还/未还统计"""
    lent = _tag_records("借出")
    borrowed = _tag_records("借入")
    unpaid_lent = [r for r in lent if _tag_match(r.get("note") or "", "未还")]
    unpaid_borrowed = [r for r in borrowed if _tag_match(r.get("note") or "", "未还")]
    paid_lent = [r for r in lent if _tag_match(r.get("note") or "", "已还")]
    paid_borrowed = [r for r in borrowed if _tag_match(r.get("note") or "", "已还")]

    def _target(note, direction):
        m = re.search(r"#借给\s*([^\s#]+)", note) if direction == "借出" else re.search(r"#向\s*([^\s#]+)借", note)
        return m.group(1) if m else ""

    by_obj = defaultdict(lambda: {"借出未还": 0.0, "借入未还": 0.0})
    for r in unpaid_lent:
        by_obj[_target(r.get("note"), "借出") or "未知对象"]["借出未还"] += abs(r.get("amount") or 0)
    for r in unpaid_borrowed:
        by_obj[_target(r.get("note"), "借入") or "未知对象"]["借入未还"] += abs(r.get("amount") or 0)
    objects = [{"target": k, "lent_unpaid": round(v["借出未还"], 2), "borrowed_unpaid": round(v["借入未还"], 2),
                "total": round(v["借出未还"] + v["借入未还"], 2)}
               for k, v in by_obj.items()]
    objects.sort(key=lambda x: x["total"], reverse=True)
    data = {
        "lent_unpaid_total": round(sum(abs(r.get("amount", 0)) for r in unpaid_lent), 2),
        "borrowed_unpaid_total": round(sum(abs(r.get("amount", 0)) for r in unpaid_borrowed), 2),
        "lent_unpaid_count": len(unpaid_lent), "borrowed_unpaid_count": len(unpaid_borrowed),
        "lent_paid_count": len(paid_lent), "borrowed_paid_count": len(paid_borrowed),
        "objects": objects,
    }
    if getattr(args, 'json', False):
        emit_ok(data, "借贷总览")
        return data
    print(f"=== 借贷总览 ===")
    print(f"借出未还: {data['lent_unpaid_total']:.2f} ({data['lent_unpaid_count']}笔) / 借入未还: {data['borrowed_unpaid_total']:.2f} ({data['borrowed_unpaid_count']}笔)")
    print(f"已还: 借出 {data['lent_paid_count']}笔 / 借入 {data['borrowed_paid_count']}笔")
    for x in objects:
        print(f"  {x['target']}: 借出未还 {x['lent_unpaid']:.2f} / 借入未还 {x['borrowed_unpaid']:.2f}")
    return data


def cmd_reimburse_summary(args):
    """看报销:待报销总额 + 已到账总额 + 历史报销列表"""
    pending = _tag_records("待报销")
    received = _tag_records("报销到账")
    pending_total = round(sum(abs(r.get("amount", 0)) for r in pending), 2)
    received_total = round(sum(abs(r.get("amount", 0)) for r in received), 2)
    history = [{"time": r.get("time", ""), "amount": r.get("amount", 0),
                "category": r.get("category", ""), "note": r.get("note", ""),
                "status": "待报销"} for r in pending]
    history += [{"time": r.get("time", ""), "amount": r.get("amount", 0),
                 "category": r.get("category", ""), "note": r.get("note", ""),
                 "status": "已到账"} for r in received]
    history.sort(key=lambda x: x["time"], reverse=True)
    data = {"pending_total": pending_total, "received_total": received_total,
            "pending_count": len(pending), "received_count": len(received),
            "history": history}
    if getattr(args, 'json', False):
        emit_ok(data, "报销汇总")
        return data
    print(f"=== 报销汇总 ===")
    print(f"待报销: {pending_total:.2f} ({len(pending)}笔) / 已到账: {received_total:.2f} ({len(received)}笔)")
    return data


def _parse_installment_note(note: str) -> tuple:
    """解析分期备注:#分期 {名目} 第X期/N → (名目, 期序, 总期数)"""
    if not note:
        return None, None, None
    m = re.search(r"#分期\s+(.+?)\s+第(\d+)期/(\d+)", note)
    if not m:
        return None, None, None
    return m.group(1).strip(), int(m.group(2)), int(m.group(3))


def cmd_installment_summary(args):
    """看分期:进行中分期卡 + 历史分期"""
    records = _tag_records("分期")
    today_str = date.today().strftime("%Y-%m-%d")
    groups: dict = {}
    for r in records:
        name, seq, total_n = _parse_installment_note(r.get("note") or "")
        name = name or "未命名分期"
        g = groups.setdefault(name, {"name": name, "total": 0.0, "count": 0,
                                     "periods": total_n or 0, "paid": 0, "first_date": None,
                                     "amounts": [], "future_amount": 0.0})
        g["total"] += abs(r.get("amount", 0))
        g["count"] += 1
        g["amounts"].append(abs(r.get("amount", 0)))
        d = str(r.get("time") or "")[:10]
        if d and d <= today_str:
            g["paid"] += 1
        else:
            g["future_amount"] += abs(r.get("amount", 0))
        if g["first_date"] is None or (d and d < g["first_date"]):
            g["first_date"] = d
    active, done = [], []
    for name, g in groups.items():
        amounts = g["amounts"]
        mode = max(set(amounts), key=lambda a: amounts.count(a)) if amounts else 0
        each = mode if amounts.count(mode) >= 2 else (min(amounts) if amounts else 0)
        first = max(amounts) if amounts else 0
        remaining = max(g["periods"] - g["paid"], 0)
        card = {"name": name, "total": round(g["total"], 2), "each": round(each, 2),
                "first": round(first, 2), "periods": g["periods"], "paid": g["paid"],
                "remaining": remaining, "remaining_amount": round(g["future_amount"], 2),
                "first_date": g["first_date"], "count": g["count"],
                "status": "进行中" if remaining > 0 else "已还清"}
        (active if remaining > 0 else done).append(card)
    active.sort(key=lambda x: x["total"], reverse=True)
    done.sort(key=lambda x: x["first_date"] or "", reverse=True)
    data = {"active": active, "history": done, "count": len(records),
            "active_count": len(active), "history_count": len(done)}
    if getattr(args, 'json', False):
        emit_ok(data, "分期总览")
        return data
    print(f"=== 分期总览 ===")
    for c in active:
        print(f"  [进行中] {c['name']}: 总额 {c['total']:.2f} · 每期 {c['each']:.2f} × {c['periods']}期 · 已还 {c['paid']} · 剩 {c['remaining']}期 {c['remaining_amount']:.2f}")
    for c in done:
        print(f"  [已还清] {c['name']}: 总额 {c['total']:.2f} · {c['periods']}期")
    return data


def cmd_refund_summary(args):
    """看退款:退款总额/次数 + 月份分布 + 退款明细"""
    refunds = _tag_records("退款")
    total = round(sum(abs(r.get("amount", 0)) for r in refunds), 2)
    by_month = defaultdict(int)
    for r in refunds:
        by_month[_month_of(str(r.get("time") or ""))] += 1
    monthly = [{"month": k, "count": v} for k, v in sorted(by_month.items())]
    details = [{"time": r.get("time", ""), "amount": r.get("amount", 0),
                "category": r.get("category", ""), "note": r.get("note", ""), "id": r.get("id")}
               for r in sorted(refunds, key=lambda r: r.get("time") or "", reverse=True)]
    data = {"total": total, "count": len(refunds), "monthly": monthly, "details": details}
    if getattr(args, 'json', False):
        emit_ok(data, "退款统计")
        return data
    print(f"=== 退款统计 ===")
    print(f"退款总额: {total:.2f} / 次数: {len(refunds)}")
    for x in monthly:
        print(f"  {x['month']}: {x['count']}次")
    return data


# ── 入口 ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 分析域 v2.0(25 场景)")
    sub = parser.add_subparsers(dest='command', help='子命令')

    def _add_range_args(p):
        p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
        p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
        p.add_argument('--month', default=None, help='月份 YYYY-MM(默认当月)')

    # 汇总 4
    p = sub.add_parser('monthly', help='月度汇总(看月度)')
    p.add_argument('--month', required=True, help='月份 YYYY-MM')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('yearly', help='年度汇总(看年度)')
    p.add_argument('--year', type=int, default=None, help='年份(默认今年)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('overview', help='收支总览(看总览)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('week', help='本周简报(看周报)')
    p.add_argument('--offset', type=int, default=0, help='0=本周 1=上周')
    p.add_argument('--json', action='store_true')

    # 结构 4
    p = sub.add_parser('category', help='分类占比(看分类)')
    _add_range_args(p)
    p.add_argument('--account', default=None, help='账户筛选')
    p.add_argument('--type', default=None, choices=['expense', 'income'], help='收支方向')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('account', help='账户占比(看账户)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('ledger', help='账本汇总(看账本)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('structure', help='收支结构(看结构)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    # 对比 4
    p = sub.add_parser('compare', help='周期对比(看对比)')
    p.add_argument('--period', default='week', choices=['week', 'month'], help='对比周期')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('range_compare', help='双区间对比(看双区间)')
    p.add_argument('--from1', dest='from1', default=None, help='区间一 开始')
    p.add_argument('--to1', dest='to1', default=None, help='区间一 结束')
    p.add_argument('--from2', dest='from2', default=None, help='区间二 开始')
    p.add_argument('--to2', dest='to2', default=None, help='区间二 结束')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('yoy', help='同比(看同比)')
    p.add_argument('--month', default=None, help='月份 YYYY-MM(默认本月)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('cat_compare', help='分类对比(看分类对比)')
    p.add_argument('--from1', dest='from1', default=None)
    p.add_argument('--to1', dest='to1', default=None)
    p.add_argument('--from2', dest='from2', default=None)
    p.add_argument('--to2', dest='to2', default=None)
    p.add_argument('--json', action='store_true')

    # 趋势 2
    p = sub.add_parser('trend', help='收支趋势(看趋势)')
    p.add_argument('--months', type=int, default=None, help='近 N 个月(默认 12)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('cat_trend', help='分类趋势(看分类趋势)')
    p.add_argument('--category', default=None, help='分类(L1)')
    p.add_argument('--months', type=int, default=None, help='近 N 个月(默认 12)')
    p.add_argument('--json', action='store_true')

    # 金额 3
    p = sub.add_parser('top', help='大额排行(看大额)')
    p.add_argument('--limit', type=int, default=None, help='条数(默认 10)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('top_freq', help='高频排行(看高频)')
    p.add_argument('--limit', type=int, default=None, help='条数(默认 10)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('distribution', help='金额分布(看分布)')
    _add_range_args(p)
    p.add_argument('--type', default='expense', choices=['expense', 'income'], help='收支方向')
    p.add_argument('--json', action='store_true')

    # 统计洞察 4
    p = sub.add_parser('stats', help='记账统计(做统计)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('activity', help='记账活跃度(看活跃)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('insight', help='AI 消费洞察(看洞察)')
    p.add_argument('--months', type=int, default=None, help='近 N 个月(默认 6)')
    p.add_argument('--top-n', dest='top_n', type=int, default=None, help='大额 TOP 条数')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('anomaly', help='异常波动检测(看异常)')
    p.add_argument('--months', type=int, default=None, help='近 N 个月(默认 6)')
    p.add_argument('--json', action='store_true')

    # 状态聚合 4
    p = sub.add_parser('debt_summary', help='借贷总览(看借贷)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('reimburse_summary', help='报销汇总(看报销)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('installment_summary', help='分期总览(看分期)')
    p.add_argument('--json', action='store_true')

    p = sub.add_parser('refund_summary', help='退款统计(看退款)')
    p.add_argument('--json', action='store_true')

    # 兼容旧命令
    p = sub.add_parser('breakdown', help='分类明细(旧口径)')
    _add_range_args(p)
    p.add_argument('--json', action='store_true')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {
        'monthly': cmd_monthly, 'yearly': cmd_yearly, 'overview': cmd_overview, 'week': cmd_week,
        'category': cmd_category, 'account': cmd_account, 'ledger': cmd_ledger, 'structure': cmd_structure,
        'compare': cmd_compare, 'range_compare': cmd_range_compare, 'yoy': cmd_yoy, 'cat_compare': cmd_cat_compare,
        'trend': cmd_trend, 'cat_trend': cmd_cat_trend,
        'top': cmd_top, 'top_freq': cmd_top_freq, 'distribution': cmd_distribution,
        'stats': cmd_stats, 'activity': cmd_activity, 'insight': cmd_insight, 'anomaly': cmd_anomaly,
        'debt_summary': cmd_debt_summary, 'reimburse_summary': cmd_reimburse_summary,
        'installment_summary': cmd_installment_summary, 'refund_summary': cmd_refund_summary,
        'breakdown': cmd_breakdown,
    }
    cmd = commands.get(args.command)
    if cmd:
        try:
            cmd(args)
        except ValueError as e:
            emit_error(f"参数错误：{e}") if getattr(args, 'json', False) else print(f"参数错误：{e}")
        except Exception as e:
            emit_error(f"执行出错：{e}") if getattr(args, 'json', False) else print(f"执行出错：{e}")
    else:
        parser.print_help()


def cmd_breakdown(args):
    """看分类(旧口径兼容):分类明细 + 环形图数据"""
    from_date = args.from_date
    to_date = args.to_date
    result = get_category_breakdown(from_date, to_date)
    if getattr(args, 'json', False):
        emit_ok(result, "分类支出明细")
        return result
    print(f"=== 分类支出明细 ===")
    for c in result.get('category_pct', []):
        print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('pct', 0):.1f}%)")
    return result


if __name__ == "__main__":
    main()
