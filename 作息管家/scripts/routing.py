"""作息管家路由助手(2026-07-24 补)

第一性:用户说自然语言相对时间(今天/昨天/本周/上月等),AI 必须能精确换算
为绝对日期。本模块锁住 SKILL.md "路由规则"章节定义的 12 个相对时间表达式,
AI 调 CLI 前可 import 本模块做换算。

设计原则:
- 纯函数,无副作用(不读 DB / 不写文件)
- today 参数支持注入(测试用,避免依赖系统时间)
- 跨月/跨年/跨闰年边界必须正确(测试覆盖)
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple


def today_str(today: date = None) -> str:
    """返回今天日期字符串(YYYY-MM-DD)。today 参数用于测试注入。"""
    return (today or date.today()).isoformat()


def relative_to_date(expr: str, today: date = None) -> str:
    """相对日期表达式 → 绝对日期(YYYY-MM-DD 字符串)

    支持 8 个表达式:
      今天 / 昨天 / 前天 / 大前天 / 明天 / 后天 / 大后天 / 今天本身

    Args:
        expr: 相对表达式(如 "今天" "昨天")
        today: 测试用注入日期,默认 = date.today()

    Returns:
        YYYY-MM-DD 格式字符串

    Examples:
        >>> from datetime import date
        >>> relative_to_date("今天", date(2026, 7, 24))
        '2026-07-24'
        >>> relative_to_date("昨天", date(2026, 7, 24))
        '2026-07-23'
        >>> relative_to_date("大前天", date(2026, 7, 24))
        '2026-07-21'
    """
    t = today or date.today()
    expr = expr.strip()
    if expr in ("今天",):
        return t.isoformat()
    if expr in ("昨天",):
        return (t - timedelta(days=1)).isoformat()
    if expr in ("前天",):
        return (t - timedelta(days=2)).isoformat()
    if expr in ("大前天",):
        return (t - timedelta(days=3)).isoformat()
    if expr in ("明天",):
        return (t + timedelta(days=1)).isoformat()
    if expr in ("后天",):
        return (t + timedelta(days=2)).isoformat()
    if expr in ("大后天",):
        return (t + timedelta(days=3)).isoformat()
    raise ValueError(f"未知相对日期表达式: '{expr}'(支持: 今天/昨天/前天/大前天/明天/后天/大后天)")


def relative_to_range(expr: str, today: date = None) -> Tuple[str, str]:
    """相对范围表达式 → (start, end) YYYY-MM-DD 字符串

    支持 7 个表达式:
      本周 / 这周(同日:周一为周首日)
      上周
      上上周
      本月 / 这个月(同日:1 号为月首日)
      上个月 / 上月

    Args:
        expr: 相对表达式(如 "本周" "上月")
        today: 测试用注入日期

    Returns:
        (start, end) 元组,均为 YYYY-MM-DD 字符串

    Examples:
        >>> from datetime import date
        >>> # 2026-07-24 是周五
        >>> relative_to_range("本周", date(2026, 7, 24))
        ('2026-07-20', '2026-07-26')
        >>> relative_to_range("上周", date(2026, 7, 24))
        ('2026-07-13', '2026-07-19')
        >>> relative_to_range("本月", date(2026, 7, 24))
        ('2026-07-01', '2026-07-31')
        >>> # 跨月边界
        >>> relative_to_range("上月", date(2026, 7, 24))
        ('2026-06-01', '2026-06-30')
        >>> # 跨年边界
        >>> relative_to_range("上月", date(2026, 1, 15))
        ('2025-12-01', '2025-12-31')
    """
    t = today or date.today()
    expr = expr.strip()
    # 本周 / 这周:周一首日
    if expr in ("本周", "这周"):
        monday = t - timedelta(days=t.weekday())
        sunday = monday + timedelta(days=6)
        return monday.isoformat(), sunday.isoformat()
    # 上周
    if expr == "上周":
        this_monday = t - timedelta(days=t.weekday())
        last_monday = this_monday - timedelta(days=7)
        last_sunday = this_monday - timedelta(days=1)
        return last_monday.isoformat(), last_sunday.isoformat()
    # 上上周
    if expr == "上上周":
        this_monday = t - timedelta(days=t.weekday())
        prev_monday = this_monday - timedelta(days=14)
        prev_sunday = this_monday - timedelta(days=8)
        return prev_monday.isoformat(), prev_sunday.isoformat()
    # 本月 / 这个月
    if expr in ("本月", "这个月"):
        start = date(t.year, t.month, 1)
        if t.month == 12:
            end = date(t.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(t.year, t.month + 1, 1) - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    # 上个月 / 上月
    if expr in ("上个月", "上月"):
        if t.month == 1:
            prev_year, prev_month = t.year - 1, 12
        else:
            prev_year, prev_month = t.year, t.month - 1
        start = date(prev_year, prev_month, 1)
        # 上月最后一天 = 本月第一天 - 1 天
        if t.month == 1:
            this_first = date(t.year, 1, 1)
        else:
            this_first = date(t.year, t.month, 1)
        end = this_first - timedelta(days=1)
        return start.isoformat(), end.isoformat()
    raise ValueError(
        f"未知相对范围表达式: '{expr}'"
        f"(支持: 本周/这周/上周/上上周/本月/这个月/上个月/上月)"
    )


def recent_n_days(n: int, today: date = None) -> Tuple[str, str]:
    """最近 N 天 → (start, end) YYYY-MM-DD 字符串

    "最近 7 天" = 今天 - 6 ~ 今天(共 7 天)
    "最近 14 天" = 今天 - 13 ~ 今天(共 14 天)

    Args:
        n: 天数(必须 ≥ 1)
        today: 测试用注入日期

    Returns:
        (start, end) 元组

    Examples:
        >>> from datetime import date
        >>> recent_n_days(7, date(2026, 7, 24))
        ('2026-07-18', '2026-07-24')
        >>> recent_n_days(1, date(2026, 7, 24))
        ('2026-07-24', '2026-07-24')
    """
    if n < 1:
        raise ValueError(f"n 必须 ≥ 1,实际 {n}")
    t = today or date.today()
    start = t - timedelta(days=n - 1)
    return start.isoformat(), t.isoformat()