#!/usr/bin/env python3
"""饼干记账 · 目标域 CLI(4 场景 · 直达式 · scenes/goal.yaml)

场景 → 子命令:
    设定预算  → set-budget --amount X [--month YYYY-MM] [--category 分类]
    看预算    → budget [--month YYYY-MM](预算 vs 实际/剩余/超支)
    设定目标  → set-saving --name X --amount Y [--deadline YYYY-MM-DD]
    看目标    → saving [--name X](已存/目标/百分比/预计达成日)

载体:goals.json(与 db 同级 · 跟随 SKILLS_DB_PATH · T0 #164 第 8 项约定)
     {"budgets": [{"id", "month", "category", "amount", "created_at"}],
      "savings": [{"id", "name", "amount", "deadline", "created_at"}]}
实际数据 = bills 聚合(预算执行 = 当月支出 vs 预算;目标进度 = 目标期内收入-支出累计)。

覆盖语义(设定预算):同月同分类预算已存在 → 默认拒绝(status=conflict,携带 existing),
AI 层提示用户确认后加 --force 重跑 —— 「覆盖时提示确认」落在数据契约,不猜不覆盖。

用法:
    python3 scripts/goal/cli.py set-budget --amount 3000
    python3 scripts/goal/cli.py set-budget --amount 500 --month 2026-08 --category 餐饮 --force
    python3 scripts/goal/cli.py budget
    python3 scripts/goal/cli.py budget --month 2026-08
    python3 scripts/goal/cli.py set-saving --name 换手机 --amount 10000 --deadline 2026-12-31
    python3 scripts/goal/cli.py saving
"""

import sys
import json
import re
import math
from datetime import date, datetime, timedelta
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from db import DB_PATH, fetch_all  # noqa: E402
from cli_utils import reconfigure_utf8, emit_ok, emit_error  # noqa: E402

reconfigure_utf8()

GOALS_FILE = DB_PATH.parent / "goals.json"
GOALS_VERSION = "2.0"

_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── goals.json 读写(原子写 · 与 conftest goals_rw 同约定)─────────────────────

def load_goals() -> dict:
    """读 goals.json;不存在 → 空结构"""
    if not GOALS_FILE.exists():
        return {"budgets": [], "savings": []}
    try:
        data = json.loads(GOALS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"budgets": [], "savings": []}
    if not isinstance(data, dict):
        return {"budgets": [], "savings": []}
    data.setdefault("budgets", [])
    data.setdefault("savings", [])
    return data


def save_goals(data: dict) -> None:
    """原子写 goals.json(临时文件 + replace,不留 .tmp 残留)"""
    GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = GOALS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(GOALS_FILE)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _next_id(items: list) -> int:
    return max((it.get("id", 0) for it in items), default=0) + 1


def _month_range(month: str) -> tuple:
    """YYYY-MM → (当月首日 00:00:00, 月末 23:59:59)"""
    y, m = int(month[:4]), int(month[5:7])
    last = date(y + (m // 12), (m % 12) + 1, 1) - timedelta(days=1)
    return f"{month}-01 00:00:00", f"{last.strftime('%Y-%m-%d')} 23:59:59"


def _month_expense(month: str, category: str = "") -> tuple:
    """当月支出(分类预算 = 该分类当月支出,L1 前缀匹配)→ (合计, 笔数)"""
    from_time, to_time = _month_range(month)
    records = fetch_all(from_time=from_time, to_time=to_time)
    if category:
        records = [r for r in records
                   if (r.get("category") or "") == category
                   or (r.get("category") or "").startswith(category + "/")]
    total = sum(abs(r["amount"]) for r in records if r.get("amount", 0) < 0)
    return round(total, 2), len([r for r in records if r.get("amount", 0) < 0])


# ── 设定预算(set-budget · 采集型)──────────────────────────────────────────────

def _budget_key(month: str, category: str) -> str:
    return f"{month}|{category or ''}"


def cmd_set_budget(args):
    """写入月度预算;同月同分类已存在 → conflict(需 --force 覆盖确认)"""
    amount = args.amount
    if amount is None or float(amount) <= 0:
        raise ValueError("金额必须 > 0(如:--amount 3000)")
    month = args.month or date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(month):
        raise ValueError(f"月份格式应为 YYYY-MM,实际 {month!r}")
    category = (args.category or "").strip()

    goals = load_goals()
    key = _budget_key(month, category)
    existing = next((b for b in goals["budgets"] if _budget_key(b.get("month", ""), b.get("category", "") or "") == key), None)
    if existing is not None and not args.force:
        emit_ok({"conflict": True, "existing": existing, "amount": float(amount),
                 "month": month, "category": category},
                f"同月同类预算已存在({existing.get('amount')} 元),确认覆盖请加 --force")
        return

    created = {"id": _next_id(goals["budgets"]), "month": month,
               "category": category, "amount": float(amount), "created_at": _now_str()}
    if existing is not None:
        goals["budgets"] = [b for b in goals["budgets"] if b.get("id") != existing.get("id")]
    goals["budgets"].append(created)
    save_goals(goals)

    data = {"budget": created, "conflict": False,
            "overwritten": existing if existing is not None else None}
    emit_ok(data, f"已设定{month}预算 {category or '总'} {float(amount):.2f} 元")
    return data


# ── 看预算(budget · 结果型:预算 vs 实际/剩余/超支)────────────────────────────

def cmd_budget(args):
    """预算执行状态:每预算进度条 + 汇总 KPI(实际数据 = 当月 bills 聚合)"""
    month = args.month or date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(month):
        raise ValueError(f"月份格式应为 YYYY-MM,实际 {month!r}")

    goals = load_goals()
    budgets = [b for b in goals["budgets"] if b.get("month") == month]
    if args.category:
        budgets = [b for b in budgets
                   if (b.get("category") or "") == args.category
                   or (b.get("category") or "").startswith(args.category + "/")]

    items = []
    for b in budgets:
        amount = float(b.get("amount") or 0)
        actual, count = _month_expense(month, b.get("category") or "")
        remaining = round(amount - actual, 2)
        pct = round(actual / amount * 100, 1) if amount else 0.0
        if actual <= amount * 0.9:
            status = "ok"
        elif actual <= amount:
            status = "warn"
        else:
            status = "over"
        items.append({
            "id": b.get("id"), "month": month,
            "category": b.get("category") or "",
            "category_cn": b.get("category") or "总预算",
            "amount": amount, "actual": actual, "count": count,
            "remaining": remaining, "pct": pct, "status": status,
        })
    items.sort(key=lambda x: (0 if x["category"] == "" else 1, x["category"]))

    # 汇总口径:总预算存在 → (总预算金额, 当月全部支出);否则 → 分类预算之和 vs 分类实际之和
    # (避免「总预算 + 分类预算」并存时实际支出重复计数)
    master = next((i for i in items if i["category"] == ""), None)
    if master is not None:
        totals = {"budget": master["amount"], "actual": master["actual"],
                  "remaining": master["remaining"],
                  "over_count": len([i for i in items if i["status"] == "over"])}
    else:
        totals = {"budget": round(sum(i["amount"] for i in items), 2),
                  "actual": round(sum(i["actual"] for i in items), 2),
                  "remaining": round(sum(i["remaining"] for i in items), 2),
                  "over_count": len([i for i in items if i["status"] == "over"])}

    data = {"month": month, "budgets": items, "totals": totals, "count": len(items)}
    emit_ok(data, f"{month} 预算执行")
    return data


# ── 设定目标(set-saving · 采集型)──────────────────────────────────────────────

def cmd_set_saving(args):
    """写入储蓄目标(目标名/金额/截止日期选填)"""
    name = (args.name or "").strip()
    if not name:
        raise ValueError("目标名必填(如:--name 换手机)")
    amount = args.amount
    if amount is None or float(amount) <= 0:
        raise ValueError("目标金额必须 > 0(如:--amount 10000)")
    deadline = (args.deadline or "").strip() or None
    if deadline and not _DATE_RE.match(deadline):
        raise ValueError(f"截止日期格式应为 YYYY-MM-DD,实际 {deadline!r}")
    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"截止日期不是合法日期,实际 {deadline!r}") from None

    goals = load_goals()
    created = {"id": _next_id(goals["savings"]), "name": name,
               "amount": float(amount), "deadline": deadline, "created_at": _now_str()}
    goals["savings"].append(created)
    save_goals(goals)

    data = {"saving": created}
    emit_ok(data, f"已设定储蓄目标「{name}」{float(amount):.2f} 元")
    return data


# ── 看目标(saving · 结果型:已存/目标/百分比/剩余/预计达成日)──────────────────

def _months_elapsed(start_month: str, end: date) -> int:
    """从 start_month 首日到 end 的月数(含首月与当月,不足整月按 1 计)"""
    y, m = int(start_month[:4]), int(start_month[5:7])
    return (end.year - y) * 12 + (end.month - m) + 1


def _saving_progress(s: dict) -> dict:
    """单目标进度:目标期 = 创建当月起 ~ 截止日(无则今天);已存 = 期内收入-支出累计"""
    amount = float(s.get("amount") or 0)
    deadline = s.get("deadline")
    created_at = str(s.get("created_at") or "")[:7]
    start_month = created_at or date.today().strftime("%Y-%m")
    if not _MONTH_RE.match(start_month):
        start_month = date.today().strftime("%Y-%m")

    today = date.today()
    end_day = today
    if deadline:
        try:
            dd = datetime.strptime(deadline, "%Y-%m-%d").date()
            end_day = min(dd, today)
        except ValueError:
            end_day = today

    from_time, to_time = _month_range(start_month)
    to_time = f"{end_day.strftime('%Y-%m-%d')} 23:59:59"
    records = fetch_all(from_time=from_time, to_time=to_time)
    saved = round(sum(r["amount"] for r in records), 2)  # 收入-支出累计
    remaining = round(amount - saved, 2)
    pct = round(max(saved, 0) / amount * 100, 1) if amount else 0.0
    elapsed = _months_elapsed(start_month, today)
    monthly_avg = round(saved / elapsed, 2) if elapsed else 0.0

    # 预计达成日:按月均净存推算(已达成 → None;月均 ≤ 0 → 无法预计)
    eta = None
    if saved < amount and monthly_avg > 0:
        months_needed = math.ceil(remaining / monthly_avg)
        y, m = today.year, today.month
        total_m = y * 12 + (m - 1) + months_needed
        eta = f"{total_m // 12:04d}-{total_m % 12 + 1:02d}"

    if saved >= amount:
        status = "done"
    elif monthly_avg <= 0:
        status = "na"
    elif eta and deadline and eta > deadline[:7]:
        status = "behind"
    else:
        status = "on_track"

    return {"id": s.get("id"), "name": s.get("name") or "未命名目标",
            "amount": amount, "deadline": deadline, "created_at": str(s.get("created_at") or ""),
            "start_month": start_month, "saved": saved, "remaining": remaining,
            "pct": pct, "monthly_avg": monthly_avg, "eta": eta, "status": status}


def cmd_saving(args):
    """目标进度:已存/目标/百分比/剩余/预计达成日(进度 = 目标期内收入-支出累计)"""
    goals = load_goals()
    savings = goals["savings"]
    if args.name:
        savings = [s for s in savings if args.name in (s.get("name") or "")]

    items = [_saving_progress(s) for s in savings]
    items.sort(key=lambda x: x["status"] != "done", reverse=False)
    items.sort(key=lambda x: x["id"])

    data = {"savings": items, "count": len(items),
            "done_count": len([i for i in items if i["status"] == "done"])}
    emit_ok(data, f"储蓄目标进度 {len(items)} 个")
    return data


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 · 目标域 v2.0(4 场景 · goals.json)")
    sub = parser.add_subparsers(dest='command', help='子命令')

    p = sub.add_parser('set-budget', help='设定月度预算(采集 → goals.json)')
    p.add_argument('--amount', type=float, required=True, help='预算金额')
    p.add_argument('--month', default=None, help='月份 YYYY-MM(默认本月)')
    p.add_argument('--category', default=None, help='分类(不填 = 总预算)')
    p.add_argument('--force', action='store_true', help='覆盖同月同类预算(默认拒绝)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('budget', help='查看预算执行(预算 vs 实际/剩余/超支)')
    p.add_argument('--month', default=None, help='月份 YYYY-MM(默认本月)')
    p.add_argument('--category', default=None, help='只看某分类预算')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('set-saving', help='设定储蓄目标(采集 → goals.json)')
    p.add_argument('--name', required=True, help='目标名(如:换手机)')
    p.add_argument('--amount', type=float, required=True, help='目标金额')
    p.add_argument('--deadline', default=None, help='截止日期 YYYY-MM-DD(选填)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    p = sub.add_parser('saving', help='查看目标进度(已存/目标/百分比/预计达成日)')
    p.add_argument('--name', default=None, help='目标名(选填,不填看全部)')
    p.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {'set-budget': cmd_set_budget, 'budget': cmd_budget,
                'set-saving': cmd_set_saving, 'saving': cmd_saving}
    cmd = commands.get(args.command)
    if not cmd:
        parser.print_help()
        return

    try:
        # conflict 也走 emit_ok(三段式可解析,由 AI 层解读 data.conflict)
        cmd(args)
    except ValueError as e:
        emit_error(f"参数错误：{e}") if getattr(args, 'json', False) else print(f"参数错误：{e}")
    except Exception as e:
        emit_error(f"执行出错：{e}") if getattr(args, 'json', False) else print(f"执行出错：{e}")


if __name__ == "__main__":
    main()
