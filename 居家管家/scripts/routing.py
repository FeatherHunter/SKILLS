"""居家管家 · 相对时间换算(总纲 03 §变体到 CLI 参数的相对时间换算)

参考作息管家 scripts/routing.py 实现:
- 纯函数,无副作用
- today 参数支持注入(测试友好)
- 未知表达式抛 ValueError(不静默兜底为今天)
- 12 表达式:今天/昨天/前天/大前天/明天/后天/大后天 + 本周/上周/上月 + 最近 N 天

每个 Skill 自己实现自己的换算 helper(不抽到 _shared/),
因为各 Skill 的"周/月"定义可能不同(作息按周一~周日;卡路里按健身周期)。
这里居家管家采用中国日历:周=周一~周日,月=1号~月末。
"""
from datetime import date, timedelta
from typing import Tuple


def today_str(today: date | None = None) -> str:
    """返回今天的 YYYY-MM-DD,支持注入"""
    return (today or date.today()).isoformat()


def relative_to_date(expr: str, today: date | None = None) -> str:
    """单日相对表达式 → YYYY-MM-DD

    支持(单日维度):
      今天 / 昨天 / 前天 / 大前天
      明天 / 后天 / 大后天
    """
    t = today or date.today()
    e = (expr or "").strip().replace(" ", "")
    if e in ("今天", "今日"):
        return t.isoformat()
    if e == "昨天":
        return (t - timedelta(days=1)).isoformat()
    if e == "前天":
        return (t - timedelta(days=2)).isoformat()
    if e == "大前天":
        return (t - timedelta(days=3)).isoformat()
    if e == "明天":
        return (t + timedelta(days=1)).isoformat()
    if e == "后天":
        return (t + timedelta(days=2)).isoformat()
    if e == "大后天":
        return (t + timedelta(days=3)).isoformat()
    raise ValueError(f"未知相对日期表达式: {expr!r}")


def relative_to_range(expr: str, today: date | None = None) -> Tuple[str, str]:
    """周/月范围相对表达式 → (start, end) ISO 日期元组

    居家管家约定:
      本周 = 本周一 ~ 本周日(中国日历)
      本月 = 本月 1 号 ~ 本月最后一天
    """
    t = today or date.today()
    e = (expr or "").strip().replace(" ", "")
    if e in ("本周", "这周", "这个礼拜"):
        start = t - timedelta(days=t.weekday())  # 周一 = 0
        end = start + timedelta(days=6)          # 周日
        return start.isoformat(), end.isoformat()
    if e == "上周":
        last_mon = t - timedelta(days=t.weekday() + 7)
        return last_mon.isoformat(), (last_mon + timedelta(days=6)).isoformat()
    if e in ("本月", "这个月"):
        start = t.replace(day=1)
        end = _last_day_of_month(t)
        return start.isoformat(), end.isoformat()
    if e in ("上月", "上个月"):
        first_this = t.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1).isoformat(), last_prev.isoformat()
    raise ValueError(f"未知相对范围表达式: {expr!r}")


def recent_n_days(n: int, today: date | None = None) -> Tuple[str, str]:
    """最近 N 天 → (start, end) ISO 日期元组,N ≥ 1
    例如今天=2026-01-10, N=7 → (2026-01-04, 2026-01-10)
    """
    if n < 1:
        raise ValueError(f"N 必须 ≥ 1, 当前 {n}")
    t = today or date.today()
    return (t - timedelta(days=n - 1)).isoformat(), t.isoformat()


def _last_day_of_month(t: date) -> date:
    """返回 t 所在月份的最后一天"""
    if t.month == 12:
        return t.replace(year=t.year + 1, month=1, day=1) - timedelta(days=1)
    return t.replace(month=t.month + 1, day=1) - timedelta(days=1)
