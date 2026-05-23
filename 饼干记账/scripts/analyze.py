"""
分析模块
负责：今日摘要、月度汇总、周期对比
"""

import sys
from pathlib import Path
_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from datetime import date, timedelta
import sqlite3

import db as db_module
init_db = db_module.init_db
TABLE_NAME = db_module.TABLE_NAME


def _get_totals(from_time: str, to_time: str) -> dict:
    """获取指定时间范围的支出/收入汇总"""
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                COUNT(*) as count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
            FROM {TABLE_NAME}
            WHERE time >= ? AND time <= ?
        """, (from_time, to_time))

        row = cursor.fetchone()
        return {
            "count": row['count'] or 0,
            "expense": row['expense'] or 0,
            "income": row['income'] or 0,
            "net": (row['income'] or 0) - (row['expense'] or 0)
        }
    finally:
        conn.close()


def get_today_summary() -> dict:
    """获取今日摘要"""
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    start = f"{today_str} 00:00:00"
    end = f"{tomorrow_str} 00:00:00"
    totals = _get_totals(start, end)
    totals["date"] = today_str
    return totals


def get_date_summary(date_str: str) -> dict:
    """获取指定日期的摘要"""
    next_day = date.fromisoformat(date_str) + timedelta(days=1)
    next_day_str = next_day.strftime("%Y-%m-%d")
    start = f"{date_str} 00:00:00"
    end = f"{next_day_str} 00:00:00"
    totals = _get_totals(start, end)
    totals["date"] = date_str
    return totals


def monthly_summary(month: str) -> dict:
    """月度汇总（YYYY-MM格式）"""
    year_int = int(month.split("-")[0])
    month_int = int(month.split("-")[1])

    # 计算下月初
    if month_int == 12:
        next_month_str = f"{year_int + 1}-01-01"
    else:
        next_month_str = f"{year_int}-{month_int + 1:02d}-01"

    start_str = f"{month}-01 00:00:00"
    next_month_start = f"{next_month_str} 00:00:00"

    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT category,
                   SUM(ABS(amount)) as total,
                   COUNT(*) as count
            FROM {TABLE_NAME}
            WHERE time >= ? AND time < ? AND amount < 0
            GROUP BY category
            ORDER BY total DESC
        """, (start_str, next_month_start))

        rows = cursor.fetchall()
        totals = _get_totals(start_str, next_month_start)

        return {
            "month": month,
            "categories": [dict(row) for row in rows],
            "expense": totals["expense"],
            "income": totals["income"],
            "net": totals["net"]
        }
    finally:
        conn.close()


def compare_periods(period: str = "week") -> dict:
    """
    周期对比
    - period: "week" (本周 vs 上周) 或 "month" (本月 vs 上月)
    """
    today = date.today()

    if period == "week":
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        tomorrow = today + timedelta(days=1)

        this_start_str = this_week_start.strftime("%Y-%m-%d 00:00:00")
        this_end_str = tomorrow.strftime("%Y-%m-%d 00:00:00")
        last_start_str = last_week_start.strftime("%Y-%m-%d 00:00:00")
        last_end_str = this_week_start.strftime("%Y-%m-%d 00:00:00")

        this_totals = _get_totals(this_start_str, this_end_str)
        last_totals = _get_totals(last_start_str, last_end_str)

        return {
            "period": "week",
            "this": {**this_totals, "label": f"本周 ({this_week_start.strftime('%m/%d')} ~ 今天)"},
            "last": {**last_totals, "label": f"上周 ({last_week_start.strftime('%m/%d')} ~ {(this_week_start - timedelta(days=1)).strftime('%m/%d')})"},
            "change": {
                "expense_diff": this_totals["expense"] - last_totals["expense"],
                "expense_pct": ((this_totals["expense"] - last_totals["expense"]) / last_totals["expense"] * 100) if last_totals["expense"] else 0
            }
        }

    elif period == "month":
        this_month = today.strftime("%Y-%m")
        this_year = today.year
        this_month_num = today.month

        if this_month_num == 1:
            last_year = this_year - 1
            last_month = 12
        else:
            last_year = this_year
            last_month = this_month_num - 1

        last_month_str = f"{last_year}-{last_month:02d}"

        this_summary = monthly_summary(this_month)
        last_summary = monthly_summary(last_month_str)

        return {
            "period": "month",
            "this": {**this_summary, "label": f"{this_month}月"},
            "last": {**last_summary, "label": f"{last_month_str}月"},
            "change": {
                "expense_diff": this_summary["expense"] - last_summary["expense"],
                "expense_pct": ((this_summary["expense"] - last_summary["expense"]) / last_summary["expense"] * 100) if last_summary["expense"] else 0
            }
        }

    else:
        return {"error": f"不支持的周期: {period}，可选: week, month"}


def get_category_breakdown(from_date: str = None, to_date: str = None) -> dict:
    """获取分类支出明细（不指定日期范围时默认本月）"""
    today = date.today()
    if not from_date:
        from_date = f"{today.year}-{today.month:02d}-01"
    if not to_date:
        to_date = today.strftime("%Y-%m-%d")

    # 计算 to_date 的下一天（用 < 而非 <=）
    to_date_obj = date.fromisoformat(to_date) + timedelta(days=1)
    next_day_str = to_date_obj.strftime("%Y-%m-%d")

    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT category,
                   SUM(ABS(amount)) as total,
                   COUNT(*) as count,
                   AVG(ABS(amount)) as avg
            FROM {TABLE_NAME}
            WHERE time >= ? AND time < ? AND amount < 0
            GROUP BY category
            ORDER BY total DESC
        """, (f"{from_date} 00:00:00", f"{next_day_str} 00:00:00"))

        rows = cursor.fetchall()

        grand_total = sum(row['total'] for row in rows)

        return {
            "from": from_date,
            "to": to_date,
            "categories": [dict(row) for row in rows],
            "grand_total": grand_total,
            "category_pct": [
                {**dict(row), "pct": (row['total'] / grand_total * 100) if grand_total else 0}
                for row in rows
            ]
        }
    finally:
        conn.close()
