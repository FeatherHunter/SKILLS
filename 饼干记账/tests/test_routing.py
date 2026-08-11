"""tests/test_routing.py — routing.py 相对时间换算测试(G5 Q3 决议 · #249)

覆盖:9 种表达 × 边界(跨月/跨年/闰年/12 月/跨年+1):
- relative_to_date:今天/昨天/前天/N天前/本周X/上周X/上上周X
- relative_to_range:本周/上周/本月/上月
- recent_n_days:最近 N 天(含今天)

不依赖 db/conftest 数据 —— 纯 datetime 逻辑,today 显式注入。
"""

from __future__ import annotations

from datetime import date

import pytest

from routing import relative_to_date, relative_to_range, recent_n_days


# ── relative_to_date · 单日 ──────────────────────────────────────────────────

class TestRelativeToDate:
    """今天 / 昨天 / 前天 / N天前 / 周几"""

    def test_today(self):
        assert relative_to_date("今天", date(2026, 8, 11)) == date(2026, 8, 11)

    def test_yesterday(self):
        assert relative_to_date("昨天", date(2026, 8, 11)) == date(2026, 8, 10)

    def test_yesterday_cross_month(self):
        """昨天 = 月初 1 号 → 上月末日(跨月)"""
        assert relative_to_date("昨天", date(2026, 8, 1)) == date(2026, 7, 31)

    def test_yesterday_cross_year(self):
        """昨天 = 1 月 1 号 → 去年 12 月 31 日(跨年)"""
        assert relative_to_date("昨天", date(2026, 1, 1)) == date(2025, 12, 31)

    def test_day_before_yesterday(self):
        assert relative_to_date("前天", date(2026, 8, 11)) == date(2026, 8, 9)

    def test_day_before_yesterday_cross_month(self):
        assert relative_to_date("前天", date(2026, 8, 1)) == date(2026, 7, 30)

    def test_n_days_ago(self):
        assert relative_to_date("3天前", date(2026, 8, 11)) == date(2026, 8, 8)

    def test_n_days_ago_spaced(self):
        assert relative_to_date("5 天前", date(2026, 8, 11)) == date(2026, 8, 6)

    def test_n_days_ago_cross_month(self):
        assert relative_to_date("5天前", date(2026, 8, 1)) == date(2026, 7, 27)

    def test_n_days_ago_cross_year(self):
        assert relative_to_date("2天前", date(2026, 1, 1)) == date(2025, 12, 30)

    # ── 周几(ISO 周一=1...周日=7) ──

    def test_this_week_friday(self):
        """本周五 = 本周一 + 4"""
        assert relative_to_date("本周五", date(2026, 8, 11)) == date(2026, 8, 14)

    def test_this_week_sunday_when_today_is_wednesday(self):
        """本周日 = 本周一 + 6(周三时仍在未来)"""
        assert relative_to_date("本周日", date(2026, 8, 11)) == date(2026, 8, 16)

    def test_this_week_monday_when_today_is_monday(self):
        assert relative_to_date("本周一", date(2026, 8, 11)) == date(2026, 8, 10)

    def test_last_week_friday(self):
        """上周五 = 本周一 - 7 + 4"""
        assert relative_to_date("上周五", date(2026, 8, 11)) == date(2026, 8, 7)

    def test_last_week_friday_cross_year(self):
        """上周五跨年:2026-01-05(周一)的上周五 → 2026-01-02(仍在跨年周内)"""
        assert relative_to_date("上周五", date(2026, 1, 5)) == date(2026, 1, 2)

    def test_last_week_sunday_when_today_is_monday(self):
        assert relative_to_date("上周日", date(2026, 8, 11)) == date(2026, 8, 9)

    def test_two_weeks_ago_wednesday(self):
        assert relative_to_date("上上周三", date(2026, 8, 11)) == date(2026, 7, 29)

    def test_invalid_expression(self):
        with pytest.raises(ValueError):
            relative_to_date("明年", date(2026, 8, 11))


# ── relative_to_range · 区间 ─────────────────────────────────────────────────

class TestRelativeToRange:
    """本周(周一~周日) / 上周 / 本月 / 上月"""

    def test_this_week_mid_week(self):
        """周三时:本周 = 本周一 ~ 周日(含今天)"""
        assert relative_to_range("本周", date(2026, 8, 11)) == (date(2026, 8, 10), date(2026, 8, 16))

    def test_this_week_when_today_is_sunday(self):
        """周日时:本周 = 本周一(6 天前) ~ 今天"""
        assert relative_to_range("本周", date(2026, 8, 16)) == (date(2026, 8, 10), date(2026, 8, 16))

    def test_this_week_when_today_is_monday(self):
        assert relative_to_range("本周", date(2026, 8, 10)) == (date(2026, 8, 10), date(2026, 8, 16))

    def test_last_week(self):
        assert relative_to_range("上周", date(2026, 8, 11)) == (date(2026, 8, 3), date(2026, 8, 9))

    def test_last_week_cross_year(self):
        """上周跨年:2026-01-05(周一)的上周 → 2025-12-29 ~ 2026-01-04"""
        assert relative_to_range("上周", date(2026, 1, 5)) == (date(2025, 12, 29), date(2026, 1, 4))

    def test_this_month(self):
        assert relative_to_range("本月", date(2026, 8, 11)) == (date(2026, 8, 1), date(2026, 8, 31))

    def test_this_month_first_day(self):
        assert relative_to_range("本月", date(2026, 8, 1)) == (date(2026, 8, 1), date(2026, 8, 31))

    def test_last_month(self):
        assert relative_to_range("上月", date(2026, 8, 11)) == (date(2026, 7, 1), date(2026, 7, 31))

    def test_last_month_cross_year(self):
        """上月跨年:2026-01 的上月 → 2025-12"""
        assert relative_to_range("上月", date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))

    def test_last_month_after_leap_february(self):
        """闰年 2 月:2024-03 的上月 → 2024-02-01 ~ 2024-02-29"""
        assert relative_to_range("上月", date(2024, 3, 10)) == (date(2024, 2, 1), date(2024, 2, 29))

    def test_last_month_after_non_leap_february(self):
        """平年 2 月:2026-03 的上月 → 2026-02-01 ~ 2026-02-28"""
        assert relative_to_range("上月", date(2026, 3, 10)) == (date(2026, 2, 1), date(2026, 2, 28))

    def test_this_month_december(self):
        """12 月:本月 = 12-01 ~ 12-31"""
        assert relative_to_range("本月", date(2026, 12, 25)) == (date(2026, 12, 1), date(2026, 12, 31))

    def test_last_month_december(self):
        """12 月的上月 = 11 月"""
        assert relative_to_range("上月", date(2026, 12, 10)) == (date(2026, 11, 1), date(2026, 11, 30))

    def test_this_week_cross_year_sunday(self):
        """跨年+1:2026-12-31(周四)的本周 → 12-28 ~ 2027-01-03"""
        assert relative_to_range("本周", date(2026, 12, 31)) == (date(2026, 12, 28), date(2027, 1, 3))

    def test_invalid_expression(self):
        with pytest.raises(ValueError):
            relative_to_range("今年", date(2026, 8, 11))


# ── recent_n_days · 最近 N 天 ────────────────────────────────────────────────

class TestRecentNDays:
    """最近 N 天(含今天)"""

    def test_n_one(self):
        assert recent_n_days(1, date(2026, 8, 11)) == (date(2026, 8, 11), date(2026, 8, 11))

    def test_n_seven(self):
        assert recent_n_days(7, date(2026, 8, 11)) == (date(2026, 8, 5), date(2026, 8, 11))

    def test_n_thirty(self):
        assert recent_n_days(30, date(2026, 8, 11)) == (date(2026, 7, 13), date(2026, 8, 11))

    def test_cross_month(self):
        assert recent_n_days(5, date(2026, 8, 1)) == (date(2026, 7, 28), date(2026, 8, 1))

    def test_cross_year(self):
        assert recent_n_days(3, date(2026, 1, 1)) == (date(2025, 12, 30), date(2026, 1, 1))

    def test_zero_rejected(self):
        with pytest.raises(ValueError):
            recent_n_days(0, date(2026, 8, 11))

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            recent_n_days(-1, date(2026, 8, 11))
