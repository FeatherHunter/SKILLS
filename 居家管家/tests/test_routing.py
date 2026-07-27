"""routing.py 单元测试(总纲 03 §必覆盖:跨月/跨年/闰年/12 月)"""
import pytest
from datetime import date
from routing import (
    today_str,
    relative_to_date,
    relative_to_range,
    recent_n_days,
)


# ── 今日 ──
def test_today_str():
    assert today_str(date(2026, 7, 24)) == "2026-07-24"
    assert today_str(None) is not None  # 默认今天


# ── 单日相对日期 ──
@pytest.mark.parametrize("expr,expected", [
    ("今天", "2026-07-24"),
    ("今天", "2026-07-24"),
    ("昨天", "2026-07-23"),
    ("前天", "2026-07-22"),
    ("大前天", "2026-07-21"),
    ("明天", "2026-07-25"),
    ("后天", "2026-07-26"),
    ("大后天", "2026-07-27"),
])
def test_relative_to_date(expr, expected):
    assert relative_to_date(expr, date(2026, 7, 24)) == expected


def test_relative_to_date_unknown():
    with pytest.raises(ValueError):
        relative_to_date("上周", date(2026, 7, 24))  # 不是单日
    with pytest.raises(ValueError):
        relative_to_date("随便", date(2026, 7, 24))


# ── 范围相对日期 ──
def test_this_week():
    # 2026-07-24 是周五(weekday=4)
    # 本周 = 2026-07-20(周一) ~ 2026-07-26(周日)
    assert relative_to_range("本周", date(2026, 7, 24)) == ("2026-07-20", "2026-07-26")


def test_last_week():
    assert relative_to_range("上周", date(2026, 7, 24)) == ("2026-07-13", "2026-07-19")


def test_this_month():
    assert relative_to_range("本月", date(2026, 7, 24)) == ("2026-07-01", "2026-07-31")


def test_last_month():
    # 2026-07-24 → 上月 = 2026-06-01 ~ 2026-06-30
    assert relative_to_range("上月", date(2026, 7, 24)) == ("2026-06-01", "2026-06-30")


def test_relative_to_range_unknown():
    with pytest.raises(ValueError):
        relative_to_range("随便", date(2026, 7, 24))


# ── 最近 N 天 ──
def test_recent_7_days():
    # 2026-07-24, N=7 → (2026-07-18, 2026-07-24)
    assert recent_n_days(7, date(2026, 7, 24)) == ("2026-07-18", "2026-07-24")


def test_recent_1_day():
    assert recent_n_days(1, date(2026, 7, 24)) == ("2026-07-24", "2026-07-24")


def test_recent_n_days_invalid():
    with pytest.raises(ValueError):
        recent_n_days(0, date(2026, 7, 24))
    with pytest.raises(ValueError):
        recent_n_days(-5, date(2026, 7, 24))


# ── 边界:跨月 ──
def test_yesterday_cross_month():
    # 2026-08-01 的昨天 = 2026-07-31
    assert relative_to_date("昨天", date(2026, 8, 1)) == "2026-07-31"


def test_this_week_monday():
    # 2026-07-20 是周一(weekday=0) → 本周还是同一周
    assert relative_to_range("本周", date(2026, 7, 20)) == ("2026-07-20", "2026-07-26")


def test_this_week_sunday():
    # 2026-07-26 是周日(weekday=6) → 本周
    assert relative_to_range("本周", date(2026, 7, 26)) == ("2026-07-20", "2026-07-26")


# ── 边界:跨年 ──
def test_yesterday_cross_year():
    # 2026-01-01 的昨天 = 2025-12-31
    assert relative_to_date("昨天", date(2026, 1, 1)) == "2025-12-31"


def test_last_month_cross_year():
    # 2026-01-15 → 上月 = 2025-12-01 ~ 2025-12-31
    assert relative_to_range("上月", date(2026, 1, 15)) == ("2025-12-01", "2025-12-31")


# ── 边界:闰年 2 月 ──
def test_relative_to_range_feb_leap():
    # 2024 是闰年,二月 29 天
    assert relative_to_range("本月", date(2024, 2, 15)) == ("2024-02-01", "2024-02-29")


def test_relative_to_range_feb_nonleap():
    # 2025 是平年,二月 28 天
    assert relative_to_range("本月", date(2025, 2, 15)) == ("2025-02-01", "2025-02-28")


def test_yesterday_feb_leap_to_march():
    # 2024-03-01 的昨天 = 2024-02-29(闰年)
    assert relative_to_date("昨天", date(2024, 3, 1)) == "2024-02-29"


# ── 边界:12 月跨年 ──
def test_tomorrow_cross_year():
    # 2026-12-31 的明天 = 2027-01-01
    assert relative_to_date("明天", date(2026, 12, 31)) == "2027-01-01"
