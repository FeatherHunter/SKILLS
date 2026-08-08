"""insights.py 洞察生成器测试(公共层 · T0 #164 第 5 项)

覆盖:period 汇总 / category L1 聚合 / monthly_trend(含空月补零·统计事实)/
     top_expense / 空数据 / 偏离度事实(无 AI 判定)
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from insights import build_insight_facts  # noqa: E402


def _rec(category, amount, time_str, note=""):
    return {"category": category, "amount": amount, "time": time_str, "note": note}


RECORDS = [
    _rec("餐饮/外卖/午餐", -35.0, "2026-06-01 12:00:00", "午饭"),
    _rec("餐饮/咖啡奶茶/奶茶", -18.0, "2026-06-02 15:00:00"),
    _rec("工资/基本工资", 8000.0, "2026-06-10 09:00:00", "工资"),
    _rec("出行/网约车", -20.0, "2026-06-15 18:30:00"),
    _rec("餐饮/堂食/晚餐", -120.0, "2026-07-01 19:00:00", "聚餐"),
    _rec("居家/房租水电", -2500.0, "2026-07-05 10:00:00", "房租"),
    _rec("玩乐/旅游", -800.0, "2026-07-20 14:00:00", "旅行"),
]


class TestPeriod:
    def test_totals(self):
        f = build_insight_facts(RECORDS)
        p = f["period"]
        assert p["expense"] == 3493.0  # 35+18+20+120+2500+800
        assert p["income"] == 8000.0
        assert p["net"] == 4507.0
        assert p["count"] == 7
        assert p["from"] == "2026-06-01 12:00:00"

    def test_empty_records(self):
        f = build_insight_facts([])
        assert f["period"]["count"] == 0
        assert f["category_dist"] == []
        assert f["monthly_trend"]["months"] == []
        assert f["top_expense"] == []


class TestCategoryDist:
    def test_l1_aggregation(self):
        f = build_insight_facts(RECORDS)
        cats = {c["category"]: c for c in f["category_dist"]}
        assert cats["餐饮"]["expense"] == 173.0  # 35+18+120
        assert cats["餐饮"]["count"] == 3
        assert cats["居家"]["expense"] == 2500.0
        # 按支出降序
        vals = [c["expense"] for c in f["category_dist"]]
        assert vals == sorted(vals, reverse=True)

    def test_pct(self):
        f = build_insight_facts(RECORDS)
        total = sum(c["expense"] for c in f["category_dist"])
        assert abs(sum(c["pct"] for c in f["category_dist"]) - 100.0) < 1.5


class TestMonthlyTrend:
    def test_sequence_with_zero_fill(self):
        f = build_insight_facts(RECORDS, months=6)
        months = f["monthly_trend"]["months"]
        assert len(months) == 6
        # 2026-07 是最后一个月,序列应覆盖 2026-02 ~ 2026-07(含空月)
        assert months[-1]["month"] == "2026-07"
        assert months[0]["month"] == "2026-02"
        # 空月补零
        assert months[0]["expense"] == 0.0

    def test_stats_facts(self):
        f = build_insight_facts(RECORDS, months=6)
        t = f["monthly_trend"]
        assert "mean_expense" in t and "median_expense" in t
        assert "max_deviation" in t  # 偏离度事实(不做异常判定)
        assert t["max_deviation"]["month"]  # 有月份


class TestTopExpense:
    def test_top_n_by_amount(self):
        f = build_insight_facts(RECORDS, top_n=3)
        tops = f["top_expense"]
        assert len(tops) == 3
        # 金额升序(负值越大越靠前: -2500 < -800 < -120)
        assert tops[0]["amount"] == -2500.0
        assert tops[2]["amount"] == -120.0

    def test_top_n_limited(self):
        f = build_insight_facts(RECORDS, top_n=2)
        assert len(f["top_expense"]) == 2
