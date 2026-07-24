"""相对时间换算测试(SKILL.md 路由规则 · AI 必读)

锁住 scripts/routing.py 的 12 个相对表达式 + 跨月/跨年边界。
任何路由规则改动都要先过这些测试。

注意:routing.py 是纯函数,不需要 DB fixture。
"""
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import routing


# 固定 today = 2026-07-24(周五)用于测试
TODAY = date(2026, 7, 24)


# ===== relative_to_date 单日 =====

def test_relative_today():
    assert routing.relative_to_date("今天", TODAY) == "2026-07-24"


def test_relative_yesterday():
    assert routing.relative_to_date("昨天", TODAY) == "2026-07-23"


def test_relative_qiantian():
    assert routing.relative_to_date("前天", TODAY) == "2026-07-22"


def test_relative_daqiantian():
    assert routing.relative_to_date("大前天", TODAY) == "2026-07-21"


def test_relative_tomorrow():
    assert routing.relative_to_date("明天", TODAY) == "2026-07-25"


def test_relative_houtian():
    assert routing.relative_to_date("后天", TODAY) == "2026-07-26"


def test_relative_dahoutian():
    assert routing.relative_to_date("大后天", TODAY) == "2026-07-27"


def test_relative_unknown_raises():
    """未知表达式抛 ValueError(不静默返回今天)"""
    import pytest
    with pytest.raises(ValueError, match="未知相对日期表达式"):
        routing.relative_to_date("上周一", TODAY)


# ===== relative_to_range 范围 =====

def test_range_this_week_friday():
    """2026-07-24 周五 → 本周 = 2026-07-20(周一)~2026-07-26(周日)"""
    s, e = routing.relative_to_range("本周", TODAY)
    assert s == "2026-07-20"
    assert e == "2026-07-26"


def test_range_this_week_monday():
    """今天=周一 → 本周 = 今天~今天+6"""
    s, e = routing.relative_to_range("本周", date(2026, 7, 20))
    assert s == "2026-07-20"
    assert e == "2026-07-26"


def test_range_this_week_sunday():
    """今天=周日 → 本周 = 今天-6~今天"""
    s, e = routing.relative_to_range("本周", date(2026, 7, 26))
    assert s == "2026-07-20"
    assert e == "2026-07-26"


def test_range_last_week():
    """上周 = 本周一 - 7 ~ 本周一 - 1"""
    s, e = routing.relative_to_range("上周", TODAY)
    assert s == "2026-07-13"
    assert e == "2026-07-19"


def test_range_two_weeks_ago():
    """上上周"""
    s, e = routing.relative_to_range("上上周", TODAY)
    assert s == "2026-07-06"
    assert e == "2026-07-12"


def test_range_this_month():
    """本月 7 月 → 2026-07-01 ~ 2026-07-31"""
    s, e = routing.relative_to_range("本月", TODAY)
    assert s == "2026-07-01"
    assert e == "2026-07-31"


def test_range_this_month_synonym():
    """本月 / 这个月 同义"""
    s1, e1 = routing.relative_to_range("本月", TODAY)
    s2, e2 = routing.relative_to_range("这个月", TODAY)
    assert (s1, e1) == (s2, e2)


def test_range_last_month():
    """上月 = 2026-06-01 ~ 2026-06-30"""
    s, e = routing.relative_to_range("上月", TODAY)
    assert s == "2026-06-01"
    assert e == "2026-06-30"


def test_range_last_month_synonym():
    """上月 / 上个月 同义"""
    s1, e1 = routing.relative_to_range("上月", TODAY)
    s2, e2 = routing.relative_to_range("上个月", TODAY)
    assert (s1, e1) == (s2, e2)


# ===== 跨月/跨年边界 =====

def test_range_last_month_year_boundary():
    """跨年:2026-01-15 问"上月" → 2025-12-01 ~ 2025-12-31"""
    s, e = routing.relative_to_range("上月", date(2026, 1, 15))
    assert s == "2025-12-01"
    assert e == "2025-12-31"


def test_range_this_month_february_leap():
    """闰年 2 月:2024-02-15 问"本月" → 2024-02-01 ~ 2024-02-29"""
    s, e = routing.relative_to_range("本月", date(2024, 2, 15))
    assert s == "2024-02-01"
    assert e == "2024-02-29"


def test_range_this_month_february_normal():
    """非闰年 2 月:2025-02-15 问"本月" → 2025-02-01 ~ 2025-02-28"""
    s, e = routing.relative_to_range("本月", date(2025, 2, 15))
    assert s == "2025-02-01"
    assert e == "2025-02-28"


def test_range_this_month_december():
    """12 月:2026-12-15 问"本月" → 2026-12-01 ~ 2026-12-31"""
    s, e = routing.relative_to_range("本月", date(2026, 12, 15))
    assert s == "2026-12-01"
    assert e == "2026-12-31"


def test_relative_yesterday_month_boundary():
    """跨月:今天=2026-08-01 问"昨天" → 2026-07-31"""
    assert routing.relative_to_date("昨天", date(2026, 8, 1)) == "2026-07-31"


def test_relative_tomorrow_year_boundary():
    """跨年:今天=2026-12-31 问"明天" → 2027-01-01"""
    assert routing.relative_to_date("明天", date(2026, 12, 31)) == "2027-01-01"


# ===== recent_n_days =====

def test_recent_7_days():
    """最近 7 天 = 今天 - 6 ~ 今天(共 7 天)"""
    s, e = routing.recent_n_days(7, TODAY)
    assert s == "2026-07-18"
    assert e == "2026-07-24"


def test_recent_1_day():
    """最近 1 天 = 今天~今天"""
    s, e = routing.recent_n_days(1, TODAY)
    assert s == "2026-07-24"
    assert e == "2026-07-24"


def test_recent_30_days():
    """最近 30 天 = 2026-06-25 ~ 2026-07-24(跨月)"""
    s, e = routing.recent_n_days(30, TODAY)
    assert s == "2026-06-25"
    assert e == "2026-07-24"


def test_recent_invalid_n_raises():
    """n < 1 抛 ValueError"""
    import pytest
    with pytest.raises(ValueError, match="n 必须 ≥ 1"):
        routing.recent_n_days(0, TODAY)
    with pytest.raises(ValueError, match="n 必须 ≥ 1"):
        routing.recent_n_days(-5, TODAY)


# ===== today_str helper =====

def test_today_str_default():
    """today_str() 默认 = date.today()"""
    assert routing.today_str() == date.today().isoformat()


def test_today_str_inject():
    """today_str(today=...) 接受注入"""
    assert routing.today_str(TODAY) == "2026-07-24"