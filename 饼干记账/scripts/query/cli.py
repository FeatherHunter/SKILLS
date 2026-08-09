#!/usr/bin/env python3
"""饼干记账 · 查询域 CLI(15 场景 · 直达式 · scenes/query.yaml)

场景 → 子命令:
    查今天/查昨天/查某天  → summary / list --date
    查最近                → recent [--limit N] [--days D] [--sort X]
    查周/查月/查区间      → list --from <周一|1日|X> --to <周日|末日|Y>
    查分类(组合参数)      → list --category X [--from F --to T] [--account A] [--ledger L] [--type 支出|收入]
    搜备注                → search <关键词>
    查标签                → tag --tag X(#tag 聚合)
    查账户                → list --account X
    查账本                → list --ledger X
    查欠款                → debt [--target 对象](#未还 聚合)
    查待报销              → reimburse(#待报销)
    查分期                → installment [--name 名目](#分期 聚合)

用法:
    python3 scripts/query/cli.py list --date 2026-05-01
    python3 scripts/query/cli.py list --from 2026-05-01 --to 2026-05-31 --category 餐饮 --account 支付宝
    python3 scripts/query/cli.py search "午饭"
    python3 scripts/query/cli.py recent --limit 10 --sort amount_desc
    python3 scripts/query/cli.py summary
    python3 scripts/query/cli.py tag --tag 旅行
    python3 scripts/query/cli.py debt --target 小明
    python3 scripts/query/cli.py reimburse
    python3 scripts/query/cli.py installment --name 手机
"""

import sys
import re
from datetime import date, datetime, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import (
    list_today, search_keyword, list_recent,
    fetch_all,
)
from analyze import get_today_summary
from cli_utils import reconfigure_utf8, format_record, emit_ok, emit_error

reconfigure_utf8()


# ── 聚合工具(纯计算 · 单一数据源 = fetch_all)────────────────────────────────

def _calc_kpi(records: list) -> dict:
    """KPI:笔数/支出/收入/净额(支出按绝对值累计)"""
    count = len(records)
    expense = sum(abs(r["amount"]) for r in records if r.get("amount", 0) < 0)
    income = sum(r["amount"] for r in records if r.get("amount", 0) > 0)
    return {"count": count, "expense": round(expense, 2), "income": round(income, 2),
            "net": round(income - expense, 2)}


def _calc_categories(records: list, expense_only: bool = True) -> list:
    """分类聚合(支出侧):[{category, total, count}] 按 total 降序"""
    agg: dict = {}
    for r in records:
        amount = r.get("amount", 0)
        if expense_only and amount >= 0:
            continue
        cat = r.get("category") or "其他"
        item = agg.setdefault(cat, {"category": cat, "total": 0, "count": 0})
        item["total"] += abs(amount)
        item["count"] += 1
    out = sorted(agg.values(), key=lambda x: x["total"], reverse=True)
    for it in out:
        it["total"] = round(it["total"], 2)
    return out


def _tag_match(note: str, tag: str) -> bool:
    """#tag 精确匹配(前后为空白/中文标点/边界):#旅行 命中「#旅行,」与「订酒店 #旅行」,
    但不命中 #旅行计划(后跟汉字 = 不同词)"""
    if not note:
        return False
    sep = r"[\s,，。.．;；:：!！?？)）]"
    return re.search(rf"(^|{sep})#{re.escape(tag)}(?={sep}|$)", note) is not None


# ── 子命令 ──────────────────────────────────────────────────────────────────

def cmd_list(args):
    """查询记录(时间族/条件族 · 组合筛选)"""
    from_time = to_time = None
    if args.date:
        from_time = f"{args.date} 00:00:00"
        to_time = f"{args.date} 23:59:59"
    elif args.from_date or args.to_date:
        if not (args.from_date and args.to_date):
            raise ValueError("--from 和 --to 必须同时指定")
        from_time = f"{args.from_date} 00:00:00"
        to_time = f"{args.to_date} 23:59:59"

    if any([args.date, args.from_date, args.to_date, args.category,
            args.account, args.ledger, args.type]):
        records = fetch_all(from_time=from_time, to_time=to_time)
        if args.category:
            # 分类支持 L1 前缀匹配(查分类:用户说「餐饮」→ 命中 餐饮/外卖/午餐 等)
            cat = args.category
            records = [r for r in records
                       if (r.get("category") or "") == cat or (r.get("category") or "").startswith(cat + "/")]
        if args.account:
            records = [r for r in records if r.get("account") == args.account]
        if args.ledger:
            records = [r for r in records if r.get("ledger") == args.ledger]
        if args.type == "expense":
            records = [r for r in records if r.get("amount", 0) < 0]
        elif args.type == "income":
            records = [r for r in records if r.get("amount", 0) > 0]
    else:
        records = list_today()

    filter_desc = {}
    if args.date:
        filter_desc["date"] = args.date
    if args.from_date:
        filter_desc["from"] = args.from_date
    if args.to_date:
        filter_desc["to"] = args.to_date
    if args.category:
        filter_desc["category"] = args.category
    if args.account:
        filter_desc["account"] = args.account
    if args.ledger:
        filter_desc["ledger"] = args.ledger
    if args.type:
        filter_desc["type"] = "支出" if args.type == "expense" else "收入"

    kpi = _calc_kpi(records)
    data = {
        "filter": filter_desc,
        "count": kpi["count"],
        "expense": kpi["expense"],
        "income": kpi["income"],
        "net": kpi["net"],
        "records": records,
        "categories": _calc_categories(records),
    }
    # 查分类契约:占比 = 该分类支出 / 同期全部支出(时间窗口内全量作分母)
    if args.category:
        all_recs = fetch_all(from_time=from_time, to_time=to_time)
        all_expense = sum(abs(r["amount"]) for r in all_recs if r.get("amount", 0) < 0)
        data["category_pct"] = round(kpi["expense"] / all_expense * 100, 1) if all_expense else 0
        data["category"] = args.category
    if getattr(args, 'json', False):
        emit_ok(data, f"查询结果 {len(records)} 条")
        return data

    if not records:
        print("(无记录)")
        return data
    for r in records:
        print(format_record(r))
    return data


def cmd_search(args):
    """搜索备注关键词(搜备注 / 查标签基础)"""
    records = search_keyword(args.keyword)
    data = {"keyword": args.keyword, "count": len(records), "records": records}
    if getattr(args, 'json', False):
        emit_ok(data, f"搜索结果: {args.keyword}")
        return data
    if not records:
        print(f"(无匹配 '{args.keyword}' 的记录)")
        return data
    print(f"=== 搜索结果: '{args.keyword}' ({len(records)}条) ===")
    for r in records:
        print(format_record(r))
    return data


def cmd_recent(args):
    """最近N条(查最近 · 条数/近几天/排序)"""
    limit = args.limit or 10
    if args.days:
        start = (date.today() - timedelta(days=int(args.days) - 1)).strftime("%Y-%m-%d 00:00:00")
        records = fetch_all(from_time=start)
    else:
        records = list_recent(limit)
    if args.sort == "amount_desc":
        records = sorted(records, key=lambda r: abs(r.get("amount", 0)), reverse=True)
    elif args.sort == "amount_asc":
        records = sorted(records, key=lambda r: abs(r.get("amount", 0)))
    records = records[:limit]

    kpi = _calc_kpi(records)
    data = {"count": kpi["count"], "limit": limit, "expense": kpi["expense"],
            "income": kpi["income"], "net": kpi["net"], "records": records}
    if getattr(args, 'json', False):
        emit_ok(data, f"最近 {len(records)} 条")
        return data
    if not records:
        print("(无记录)")
        return data
    print(f"=== 最近 {len(records)} 条 ===")
    for r in records:
        print(format_record(r))
    return data


def cmd_summary(args):
    """今日摘要(查今天 · 4 KPI + 今日明细 + 分类聚合)"""
    result = get_today_summary()
    records = list_today()
    result["records"] = records
    result["categories"] = _calc_categories(records)
    if getattr(args, 'json', False):
        emit_ok(result, "今日摘要")
        return result
    print(f"今日 {result.get('date', 'N/A')}")
    print(f"记录数: {result.get('count', 0)}")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")
    return result


def cmd_tag(args):
    """查标签(#tag 聚合:总笔数/总金额 + 明细)"""
    tag = args.tag.lstrip("#")
    records = search_keyword(f"#{tag}")
    records = [r for r in records if _tag_match(r.get("note") or "", tag)]
    kpi = _calc_kpi(records)
    data = {"tag": tag, "count": kpi["count"], "expense": kpi["expense"],
            "income": kpi["income"], "net": kpi["net"], "records": records}
    if getattr(args, 'json', False):
        emit_ok(data, f"标签 #{tag} 聚合")
        return data
    if not records:
        print(f"(无 #{tag} 记录)")
        return data
    print(f"=== #{tag} ({len(records)}条 · 支出 {kpi['expense']:.2f} / 收入 {kpi['income']:.2f}) ===")
    for r in records:
        print(format_record(r))
    return data


def _extract_debt_target(note: str, direction: str) -> str:
    """从备注提取借贷对象:#借给{X} / #向{X}借"""
    if not note:
        return ""
    if direction == "借出":
        m = re.search(r"#借给\s*([^\s#]+)", note)
    else:
        m = re.search(r"#向\s*([^\s#]+)借", note)
    return m.group(1) if m else ""


def cmd_debt(args):
    """查欠款(#未还 聚合:借出未还总额 + 借入未还总额 + 未还列表)"""
    records = [r for r in search_keyword("#未还")
               if _tag_match(r.get("note") or "", "未还")]
    if args.target:
        records = [r for r in records
                   if args.target in (r.get("note") or "")]
    lent = [r for r in records if _tag_match(r.get("note") or "", "借出")]
    borrowed = [r for r in records if _tag_match(r.get("note") or "", "借入")]
    lent_total = round(sum(abs(r.get("amount", 0)) for r in lent), 2)
    borrowed_total = round(sum(abs(r.get("amount", 0)) for r in borrowed), 2)

    items = []
    for r in lent:
        items.append({"id": r["id"], "time": r.get("time", ""), "amount": r.get("amount", 0),
                      "direction": "借出", "target": _extract_debt_target(r.get("note"), "借出"),
                      "note": r.get("note", "")})
    for r in borrowed:
        items.append({"id": r["id"], "time": r.get("time", ""), "amount": r.get("amount", 0),
                      "direction": "借入", "target": _extract_debt_target(r.get("note"), "借入"),
                      "note": r.get("note", "")})
    items.sort(key=lambda x: x["time"], reverse=True)

    data = {"lent_unpaid_total": lent_total, "borrowed_unpaid_total": borrowed_total,
            "count": len(items), "records": items,
            "filter": {"target": args.target} if args.target else {}}
    if getattr(args, 'json', False):
        emit_ok(data, "未还欠款聚合")
        return data
    if not items:
        print("(无未还欠款)")
        return data
    print(f"借出未还 {lent_total:.2f} / 借入未还 {borrowed_total:.2f} / 共 {len(items)} 笔")
    for it in items:
        print(f"{it['time']} | {it['direction']} {it['target'] or '?'} | {it['amount']:.2f} | {it['note']}")
    return data


def cmd_reimburse(args):
    """查待报销(#待报销 列表 + 总额)"""
    records = [r for r in search_keyword("#待报销")
               if _tag_match(r.get("note") or "", "待报销")]
    total = round(sum(abs(r.get("amount", 0)) for r in records), 2)
    data = {"count": len(records), "total": total, "records": records}
    if getattr(args, 'json', False):
        emit_ok(data, "待报销清单")
        return data
    if not records:
        print("(无待报销记录)")
        return data
    print(f"=== 待报销 {len(records)} 笔 · 总额 {total:.2f} ===")
    for r in records:
        print(format_record(r))
    return data


def _parse_installment_note(note: str) -> tuple:
    """解析分期备注:#分期 {名目} 第X期/N → (名目, 期序, 总期数);失败 → (None, None, None)"""
    if not note:
        return None, None, None
    m = re.search(r"#分期\s+(.+?)\s+第(\d+)期/(\d+)", note)
    if not m:
        return None, None, None
    return m.group(1).strip(), int(m.group(2)), int(m.group(3))


def cmd_installment(args):
    """查分期(#分期 聚合:分期卡 + 记录明细)

    每期=总价÷期数(首期补差);已还期数 = 日期 ≤ 今天 的期数(写入即固定,按时间推断)。
    """
    records = [r for r in search_keyword("#分期")
               if _tag_match(r.get("note") or "", "分期")]
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
    if args.name:
        groups = {k: v for k, v in groups.items() if args.name in k}

    cards = []
    for name, g in groups.items():
        # 常规期 = 出现次数最多的金额(首期补差只出现一次);无法判定时取最小额
        amounts = g["amounts"]
        mode = max(set(amounts), key=lambda a: amounts.count(a)) if amounts else 0
        each = mode if amounts.count(mode) >= 2 else (min(amounts) if amounts else 0)
        first = max(amounts) if amounts else 0
        remaining = max(g["periods"] - g["paid"], 0)
        cards.append({
            "name": name, "total": round(g["total"], 2), "each": round(each, 2),
            "first": round(first, 2),
            "periods": g["periods"], "paid": g["paid"], "remaining": remaining,
            "remaining_amount": round(g["future_amount"], 2),
            "first_date": g["first_date"], "count": g["count"],
        })
    cards.sort(key=lambda x: x["total"], reverse=True)

    data = {"groups": cards, "count": len(records), "records": records,
            "filter": {"name": args.name} if args.name else {}}
    if getattr(args, 'json', False):
        emit_ok(data, "分期聚合")
        return data
    if not cards:
        print("(无进行中的分期)")
        return data
    for c in cards:
        print(f"{c['name']}: 总额 {c['total']:.2f} · 首期 {c['first']:.2f} / 每期 {c['each']:.2f} × {c['periods']} 期 · "
              f"已还 {c['paid']} 期 · 剩余 {c['remaining']} 期 {c['remaining_amount']:.2f}")
    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 查询域 v2.0(15 场景)")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('list', help='查询记录(组合筛选)')
    p.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--category', default=None, help='按分类筛选')
    p.add_argument('--account', default=None, help='按账户筛选(查账户)')
    p.add_argument('--ledger', default=None, help='按账本筛选(查账本)')
    p.add_argument('--type', default=None, choices=['expense', 'income'], help='收支方向(支出/收入)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('search', help='搜索备注关键词')
    p.add_argument('keyword', help='关键词')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('recent', help='最近N条(查最近)')
    p.add_argument('--limit', type=int, default=10, help='条数')
    p.add_argument('--days', type=int, default=None, help='近 N 天(与条数二选一)')
    p.add_argument('--sort', default=None, choices=['amount_desc', 'amount_asc'],
                   help='排序:金额从大到小/从小到大')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('summary', help='今日摘要(查今天)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('tag', help='查标签(#tag 聚合)')
    p.add_argument('--tag', required=True, help='标签名(可不带 #)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('debt', help='查欠款(#未还 聚合)')
    p.add_argument('--target', default=None, help='对象(选填,不填查全部)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('reimburse', help='查待报销(#待报销)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('installment', help='查分期(#分期 聚合)')
    p.add_argument('--name', default=None, help='名目(选填,不填查全部)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'list': cmd_list, 'search': cmd_search, 'recent': cmd_recent,
                'summary': cmd_summary, 'tag': cmd_tag, 'debt': cmd_debt,
                'reimburse': cmd_reimburse, 'installment': cmd_installment}
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


if __name__ == "__main__":
    main()
