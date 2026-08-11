"""相对时间换算规则 · 参考实现(G5 Q3 决议 · #249 落地)

定位:SKILL.md「路由规则」章节的可执行参考实现 + 测试锚点。
⚠️ 仅供规则参考,不进运行时 —— AI 按 SKILL.md「路由规则」章节语义换算,
CLI 始终接收具体日期(如 --date 2026-08-10 / --from --to)。

与 SKILL.md「## 路由规则」章节保持同步:修改任何一方必须同步另一方。

「本周」= 周一~周日(ISO 语义,周一=1...周日=7)。
"""

from __future__ import annotations

import re
from datetime import date, timedelta

# 周几名称 → ISO weekday(周一=1 ... 周日=7)
# 同时接受单字(本周五→"五")与双字(本周五→"周五")两种形态
_WEEKDAY_MAP = {
    "一": 1, "周一": 1,
    "二": 2, "周二": 2, "星期二": 2,
    "三": 3, "周三": 3, "星期三": 3,
    "四": 4, "周四": 4, "星期四": 4,
    "五": 5, "周五": 5, "星期五": 5,
    "六": 6, "周六": 6, "星期六": 6,
    "日": 7, "天": 7, "周日": 7, "周天": 7, "星期日": 7,
}

# 周偏移名称 → 相对本周的周数偏移(本周=0, 上周=-1, 上上周=-2)
# 注意:长的放前面,防 startswith 误匹配
_WEEK_OFFSET = {"上上周": -2, "上周": -1, "本周": 0}


def _this_monday(today: date) -> date:
    """本周一"""
    return today - timedelta(days=today.isoweekday() - 1)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """某年月的首日与末日"""
    first = date(year, month, 1)
    if month == 12:
        next_first = date(year + 1, 1, 1)
    else:
        next_first = date(year, month + 1, 1)
    return first, next_first - timedelta(days=1)


def relative_to_date(expr: str, today: date) -> date:
    """单日相对表达 → 具体日期。

    支持:今天 / 昨天 / 前天 / N天前 / 周几(本周五·上周五·上上周五)
    """
    expr = expr.strip()
    if expr == "今天":
        return today
    if expr == "昨天":
        return today - timedelta(days=1)
    if expr == "前天":
        return today - timedelta(days=2)

    m = re.fullmatch(r"(\d+)\s*天前", expr)
    if m:
        return today - timedelta(days=int(m.group(1)))

    for offset_name, week_off in _WEEK_OFFSET.items():
        if expr.startswith(offset_name):
            day_name = expr[len(offset_name):]
            if day_name in _WEEKDAY_MAP:
                monday = _this_monday(today) + timedelta(weeks=week_off)
                return monday + timedelta(days=_WEEKDAY_MAP[day_name] - 1)

    raise ValueError(f"不支持的单日相对表达: {expr!r} (支持 今天/昨天/前天/N天前/本周X/上周X/上上周X)")


def relative_to_range(expr: str, today: date) -> tuple[date, date]:
    """区间相对表达 → (起, 止)。

    支持:本周 / 上周 / 本月 / 上月。
    「本周」= 周一~周日(含今天所在周);「本月」= 1 日 ~ 末日。
    """
    expr = expr.strip()
    if expr == "本周":
        monday = _this_monday(today)
        return monday, monday + timedelta(days=6)
    if expr == "上周":
        monday = _this_monday(today) - timedelta(weeks=1)
        return monday, monday + timedelta(days=6)
    if expr == "本月":
        return _month_bounds(today.year, today.month)
    if expr == "上月":
        if today.month == 1:
            return _month_bounds(today.year - 1, 12)
        return _month_bounds(today.year, today.month - 1)

    raise ValueError(f"不支持的区间相对表达: {expr!r} (支持 本周/上周/本月/上月)")


def recent_n_days(n: int, today: date) -> tuple[date, date]:
    """最近 N 天 → (起, 止),含今天(如 N=1 → 今天~今天)。

    n 必须 >= 1。
    """
    if n < 1:
        raise ValueError(f"recent_n_days 的 n 必须 >= 1,收到 {n}")
    return today - timedelta(days=n - 1), today
