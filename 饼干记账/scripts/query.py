"""
查询模块
负责：今日查询、单日查询、日期范围查询、分类查询、关键词搜索
"""

from datetime import date
import sys
from pathlib import Path
_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from db import fetch_all

TODAY = date.today()
DATE_FILE_STR = TODAY.strftime("%Y-%m-%d")


def list_today() -> list:
    """查询今日所有记录"""
    start = f"{DATE_FILE_STR} 00:00:00"
    end = f"{DATE_FILE_STR} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date(date_str: str) -> list:
    """查询指定日期所有记录"""
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date_range(from_date: str, to_date: str) -> list:
    """
    查询日期范围记录
    - from_date / to_date: YYYY-MM-DD 格式（必须同时提供）
    """
    if not from_date or not to_date:
        raise ValueError("list_date_range requires both from_date and to_date")
    start = f"{from_date} 00:00:00"
    end = f"{to_date} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_by_category(category: str) -> list:
    """按分类查询所有记录"""
    return fetch_all(category=category)


def search_keyword(keyword: str) -> list:
    """搜索备注关键词"""
    return fetch_all(keyword=keyword)


def list_recent(limit: int = 10) -> list:
    """查询最近N条记录"""
    return fetch_all(limit=limit)


