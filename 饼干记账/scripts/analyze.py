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

TODAY = date.today()
DATE_FILE_STR = TODAY.strftime("%Y-%m-%d")


def _get_totals(from_time: str, to_time: str) -> dict:
    """获取指定时间范围的支出/收入汇总"""
    conn = init_db()
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
    conn.close()
    return {
        "count": row['count'] or 0,
        "expense": row['expense'] or 0,
        "income": row['income'] or 0,
        "net": (row['income'] or 0) - (row['expense'] or 0)
    }


def get_today_summary() -> dict:
    """获取今日摘要"""
    start = f"{DATE_FILE_STR} 00:00:00"
    end = f"{DATE_FILE_STR} 23:59:59"
    totals = _get_totals(start, end)
    totals["date"] = DATE_FILE_STR
    return totals


def get_date_summary(date_str: str) -> dict:
    """获取指定日期的摘要"""
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    totals = _get_totals(start, end)
    totals["date"] = date_str
    return totals


def monthly_summary(month: str) -> dict:
    """月度汇总（YYYY-MM格式）"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 计算月末最后一秒（正确覆盖整个月，不漏任何时间点）
    month_int = int(month.split("-")[1])
    year_int = int(month.split("-")[0])
    if month_int == 12:
        end_date = date(year_int + 1, 1, 1)
    else:
        end_date = date(year_int, month_int + 1, 1)
    # 向前一天的 23:59:59
    end_date = end_date - timedelta(seconds=1)
    end_str = end_date.strftime("%Y-%m-%d 23:59:59")
    start_str = f"{month}-01 00:00:00"

    cursor.execute(f"""
        SELECT category,
               SUM(ABS(amount)) as total,
               COUNT(*) as count
        FROM {TABLE_NAME}
        WHERE time >= ? AND time <= ? AND amount < 0
        GROUP BY category
        ORDER BY total DESC
    """, (start_str, end_str))

    rows = cursor.fetchall()
    totals = _get_totals(start_str, end_str)

    conn.close()
    return {
        "month": month,
        "categories": [dict(row) for row in rows],
        "expense": totals["expense"],
        "income": totals["income"],
        "net": totals["net"]
    }


def compare_periods(period: str = "week") -> dict:
    """
    周期对比
    - period: "week" (本周 vs 上周) 或 "month" (本月 vs 上月)
    """
    today = TODAY

    if period == "week":
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(seconds=1)

        this_start_str = this_week_start.strftime("%Y-%m-%d 00:00:00")
        last_start_str = last_week_start.strftime("%Y-%m-%d 00:00:00")
        last_end_str = last_week_end.strftime("%Y-%m-%d 23:59:59")

        this_totals = _get_totals(this_start_str, f"{today.strftime('%Y-%m-%d')} 23:59:59")
        last_totals = _get_totals(last_start_str, last_end_str)

        return {
            "period": "week",
            "this": {**this_totals, "label": f"本周 ({this_week_start.strftime('%m/%d')} ~ 今天)"},
            "last": {**last_totals, "label": f"上周 ({last_week_start.strftime('%m/%d')} ~ {last_week_end.strftime('%m/%d')})"},
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
    if not from_date:
        from_date = f"{TODAY.year}-{TODAY.month:02d}-01"
    if not to_date:
        to_date = TODAY.strftime("%Y-%m-%d")

    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT category,
               SUM(ABS(amount)) as total,
               COUNT(*) as count,
               AVG(ABS(amount)) as avg
        FROM {TABLE_NAME}
        WHERE time >= ? AND time <= ? AND amount < 0
        GROUP BY category
        ORDER BY total DESC
    """, (f"{from_date} 00:00:00", f"{to_date} 23:59:59"))

    rows = cursor.fetchall()
    conn.close()

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