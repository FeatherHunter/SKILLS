"""tests/test_analysis.py — 分析域 25 场景 CLI 测试(隔离契约:scripts/analysis/)

覆盖(对齐 scenes/analysis.yaml 25 场景):
- 汇总 4:看月度(monthly)/看年度(yearly)/看总览(overview)/看周报(week)
- 结构 4:看分类(category)/看账户(account)/看账本(ledger)/看结构(structure)
- 对比 4:看对比(compare)/看双区间(range_compare)/看同比(yoy)/看分类对比(cat_compare)
- 趋势 2:看趋势(trend)/看分类趋势(cat_trend)
- 金额 3:看大额(top)/看高频(top_freq)/看分布(distribution)
- 统计洞察 4:做统计(stats)/看活跃(activity)/看洞察(insight)/看异常(anomaly)
- 状态聚合 4:看借贷(debt_summary)/看报销(reimburse_summary)/看分期(installment_summary)/看退款(refund_summary)
外部行为校验:CLI --json 三段式 {status, data, message};聚合正确;空态不崩。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

ANALYSIS_CLI = SCRIPTS_DIR / "analysis" / "cli.py"


def _run_analysis_cli(tmp_db_dir, *args):
    """跑 analysis/cli.py <args> --json,返回解析后的 dict(rc!=0 时断言失败并打印输出)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(ANALYSIS_CLI)] + list(args) + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
    assert result.returncode == 0, (
        f"analysis/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def _insert(tmp_db_dir, category, amount, time_str, note="", account="", ledger="生活"):
    """直接向临时库插记录(数据层 fixture 复用 conftest 的 db 模块)"""
    from db import init_db, TABLE_NAME
    import sqlite3
    conn = init_db()
    try:
        cur = conn.cursor()
        cur.execute(
            f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (category, time_str, amount, account, ledger, "人民币", note),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── 汇总 4 ────────────────────────────────────────────────────────────────────

class TestSummaryFamily:
    """看月度/看年度/看总览/看周报"""

    def test_monthly_kpi_and_categories(self, tmp_db_dir):
        """看月度:KPI(支出/收入/净额)+ 分类排行"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-03-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/外卖/晚餐", -45.0, "2026-03-02 19:00:00", "晚饭")
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-03-10 09:00:00", "工资")
        _insert(tmp_db_dir, "餐饮", -10.0, "2026-04-01 08:00:00", "4月")
        data = _run_analysis_cli(tmp_db_dir, "monthly", "--month", "2026-03")
        d = data["data"]
        assert d["month"] == "2026-03"
        assert d["expense"] == 80.0 and d["income"] == 8000.0 and d["net"] == 7920.0
        cats = d["categories"]
        assert sum(c["total"] for c in cats) == 80.0

    def test_monthly_empty(self, empty_db):
        """看月度:空库 → 0 不崩"""
        data = _run_analysis_cli(empty_db, "monthly", "--month", "2026-03")
        assert data["data"]["expense"] == 0

    def test_yearly_kpi_and_monthly_series(self, tmp_db_dir):
        """看年度:全年 KPI + 逐月趋势表(含空月补零)+ 大额分类 TOP"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-01-05 12:00:00", "1月")
        _insert(tmp_db_dir, "餐饮", -200.0, "2026-03-05 12:00:00", "3月")
        _insert(tmp_db_dir, "工资", 5000.0, "2026-01-10 09:00:00", "工资")
        _insert(tmp_db_dir, "餐饮", -50.0, "2025-12-20 12:00:00", "跨年")
        data = _run_analysis_cli(tmp_db_dir, "yearly", "--year", "2026")
        d = data["data"]
        assert d["year"] == 2026
        assert d["expense"] == 300.0 and d["income"] == 5000.0
        assert len(d["monthly"]) == 12
        jan = next(m for m in d["monthly"] if m["month"] == "2026-01")
        assert jan["expense"] == 100.0
        feb = next(m for m in d["monthly"] if m["month"] == "2026-02")
        assert feb["expense"] == 0.0  # 空月补零
        assert d["top_categories"][0]["key"] == "餐饮"

    def test_overview_range_daily_avg(self, tmp_db_dir):
        """看总览:区间 + 日均支出"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-05-01 12:00:00", "1号")
        _insert(tmp_db_dir, "餐饮", -50.0, "2026-05-02 12:00:00", "2号")
        data = _run_analysis_cli(tmp_db_dir, "overview", "--from", "2026-05-01", "--to", "2026-05-02")
        d = data["data"]
        assert d["expense"] == 150.0 and d["count"] == 2
        assert d["daily_avg"] == 75.0  # 150 / 2 天

    def test_overview_month_compat(self, tmp_db_dir):
        """看总览:--month 兼容旧接口"""
        _insert(tmp_db_dir, "餐饮", -30.0, "2026-06-15 12:00:00", "月中")
        data = _run_analysis_cli(tmp_db_dir, "overview", "--month", "2026-06")
        assert data["data"]["expense"] == 30.0
        assert data["data"]["daily_avg"] == 1.0  # 30 / 30 天

    def test_week_compare_and_top(self, tmp_db_dir):
        """看周报:本周 KPI + 对比上周变化率 + 本周大额"""
        from datetime import date, timedelta
        today = date.today()
        this_w = today - timedelta(days=today.weekday())
        last_w = this_w - timedelta(days=7)
        _insert(tmp_db_dir, "餐饮", -100.0, f"{this_w} 12:00:00", "本周")
        _insert(tmp_db_dir, "餐饮", -50.0, f"{last_w} 12:00:00", "上周")
        data = _run_analysis_cli(tmp_db_dir, "week")
        d = data["data"]
        assert d["expense"] == 100.0
        cmp = d["compare"]
        assert cmp["period_a"]["expense"] == 100.0
        assert cmp["period_b"]["expense"] == 50.0
        assert cmp["change"]["expense_pct"] == 100.0  # 100 vs 50
        assert len(d["top_expenses"]) == 1

    def test_week_empty(self, empty_db):
        """看周报:空库 → 0 不崩"""
        data = _run_analysis_cli(empty_db, "week")
        assert data["data"]["expense"] == 0


# ── 结构 4 ────────────────────────────────────────────────────────────────────

class TestStructureFamily:
    """看分类/看账户/看账本/看结构"""

    def test_category_l1_aggregation(self, tmp_db_dir):
        """看分类:L1 聚合(餐饮/外卖/午餐 + 餐饮/咖啡奶茶 → 餐饮)"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-03-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -18.0, "2026-03-02 15:00:00", "奶茶")
        _insert(tmp_db_dir, "出行/网约车", -20.0, "2026-03-03 18:00:00", "打车")
        data = _run_analysis_cli(tmp_db_dir, "category", "--month", "2026-03")
        d = data["data"]
        cats = {c["key"]: c for c in d["categories"]}
        assert cats["餐饮"]["expense"] == 53.0 and cats["餐饮"]["count"] == 2
        assert cats["出行"]["expense"] == 20.0
        assert d["grand_total"] == 73.0
        assert cats["餐饮"]["pct"] == round(53 / 73 * 100, 1)

    def test_category_account_filter(self, tmp_db_dir):
        """看分类:账户筛选"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-01 12:00:00", "午饭", account="支付宝")
        _insert(tmp_db_dir, "餐饮", -20.0, "2026-03-02 12:00:00", "晚饭", account="微信")
        data = _run_analysis_cli(tmp_db_dir, "category", "--month", "2026-03", "--account", "支付宝")
        assert data["data"]["grand_total"] == 35.0

    def test_category_expense_income_filter(self, tmp_db_dir):
        """看分类:收支方向(默认支出)"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "退款/购物", 100.0, "2026-03-02 12:00:00", "退款")
        data = _run_analysis_cli(tmp_db_dir, "category", "--month", "2026-03")
        assert data["data"]["grand_total"] == 35.0  # 默认只看支出
        data_inc = _run_analysis_cli(tmp_db_dir, "category", "--month", "2026-03", "--type", "income")
        assert data_inc["data"]["grand_total"] == 100.0

    def test_account_breakdown(self, tmp_db_dir):
        """看账户:各账户支出/收入/净额 + 占比"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-03-01 12:00:00", "午饭", account="支付宝")
        _insert(tmp_db_dir, "餐饮", -50.0, "2026-03-02 12:00:00", "晚饭", account="微信")
        _insert(tmp_db_dir, "工资", 5000.0, "2026-03-05 09:00:00", "工资", account="招行")
        data = _run_analysis_cli(tmp_db_dir, "account", "--month", "2026-03")
        d = data["data"]
        by = {x["account"]: x for x in d["accounts"]}
        assert by["支付宝"]["expense"] == 100.0 and by["支付宝"]["income"] == 0
        assert by["招行"]["income"] == 5000.0 and by["招行"]["expense"] == 0
        # 占比按支出:支付宝 100 / 150
        assert by["支付宝"]["pct"] == round(100 / 150 * 100, 1)

    def test_ledger_summary(self, tmp_db_dir):
        """看账本:各账本汇总卡"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-03-01 12:00:00", "午饭", ledger="生活")
        _insert(tmp_db_dir, "玩乐/旅游", -500.0, "2026-03-02 12:00:00", "酒店", ledger="旅行")
        data = _run_analysis_cli(tmp_db_dir, "ledger", "--month", "2026-03")
        d = data["data"]
        by = {x["ledger"]: x for x in d["ledgers"]}
        assert by["生活"]["expense"] == 100.0
        assert by["旅行"]["expense"] == 500.0

    def test_structure_dual(self, tmp_db_dir):
        """看结构:收入来源 + 支出去向"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-03-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-03-05 09:00:00", "工资")
        _insert(tmp_db_dir, "奖金", 2000.0, "2026-03-06 09:00:00", "奖金")
        data = _run_analysis_cli(tmp_db_dir, "structure", "--month", "2026-03")
        d = data["data"]
        inc = {x["key"]: x for x in d["income_structure"]}
        assert set(inc.keys()) == {"工资", "奖金"}
        assert inc["工资"]["income"] == 8000.0
        exp = {x["key"]: x for x in d["expense_structure"]}
        assert exp["餐饮"]["expense"] == 100.0
        assert d["income_total"] == 10000.0 and d["expense_total"] == 100.0

    def test_structure_empty(self, empty_db):
        """看结构:空库 → 空结构不崩"""
        data = _run_analysis_cli(empty_db, "structure", "--month", "2026-03")
        assert data["data"]["income_structure"] == [] and data["data"]["expense_structure"] == []


# ── 对比 4 ────────────────────────────────────────────────────────────────────

class TestCompareFamily:
    """看对比/看双区间/看同比/看分类对比"""

    def test_compare_month(self, tmp_db_dir):
        """看对比:本月 vs 上月(支出变化率)"""
        from datetime import date
        today = date.today()
        this_m = today.strftime("%Y-%m")
        last_m = (today.replace(day=1) - __import__("datetime").timedelta(days=1)).strftime("%Y-%m")
        _insert(tmp_db_dir, "餐饮", -100.0, f"{this_m}-05 12:00:00", "本月")
        _insert(tmp_db_dir, "餐饮", -50.0, f"{last_m}-05 12:00:00", "上月")
        data = _run_analysis_cli(tmp_db_dir, "compare", "--period", "month")
        d = data["data"]
        assert d["this"]["expense"] == 100.0 and d["last"]["expense"] == 50.0
        assert d["change"]["expense_pct"] == 100.0

    def test_compare_week(self, tmp_db_dir):
        """看对比:本周 vs 上周"""
        from datetime import date, timedelta
        today = date.today()
        this_w = today - timedelta(days=today.weekday())
        last_w = this_w - timedelta(days=7)
        _insert(tmp_db_dir, "餐饮", -80.0, f"{this_w} 12:00:00", "本周")
        _insert(tmp_db_dir, "餐饮", -60.0, f"{last_w} 12:00:00", "上周")
        data = _run_analysis_cli(tmp_db_dir, "compare", "--period", "week")
        assert data["data"]["change"]["expense_pct"] == round(20 / 60 * 100, 1)

    def test_range_compare(self, tmp_db_dir):
        """看双区间:两段时间双卡 + 变化率 + 分类差异 TOP"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-05-01 12:00:00", "5月餐饮")
        _insert(tmp_db_dir, "餐饮", -60.0, "2026-04-01 12:00:00", "4月餐饮")
        _insert(tmp_db_dir, "出行", -40.0, "2026-05-02 12:00:00", "5月出行")
        data = _run_analysis_cli(tmp_db_dir, "range_compare",
                                 "--from1", "2026-05-01", "--to1", "2026-05-31",
                                 "--from2", "2026-04-01", "--to2", "2026-04-30")
        d = data["data"]
        assert d["period_a"]["expense"] == 140.0
        assert d["period_b"]["expense"] == 60.0
        diffs = {x["category"]: x for x in d["category_diffs"]}
        assert diffs["餐饮"]["diff"] == 40.0

    def test_range_compare_missing_args(self, tmp_db_dir):
        """看双区间:缺参数 → 三段式 status=error"""
        data = _run_analysis_cli(tmp_db_dir, "range_compare",
                                 "--from1", "2026-05-01", "--to1", "2026-05-31")
        assert data["status"] == "error"

    def test_yoy(self, tmp_db_dir):
        """看同比:今年某月 vs 去年同月"""
        _insert(tmp_db_dir, "餐饮", -120.0, "2026-03-05 12:00:00", "今年3月")
        _insert(tmp_db_dir, "餐饮", -80.0, "2025-03-05 12:00:00", "去年3月")
        data = _run_analysis_cli(tmp_db_dir, "yoy", "--month", "2026-03")
        d = data["data"]
        assert d["period_a"]["expense"] == 120.0
        assert d["period_b"]["expense"] == 80.0
        assert d["change"]["expense_pct"] == 50.0

    def test_cat_compare(self, tmp_db_dir):
        """看分类对比:金额变化最大 TOP"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-05-01 12:00:00", "5月")
        _insert(tmp_db_dir, "餐饮", -30.0, "2026-04-01 12:00:00", "4月")
        _insert(tmp_db_dir, "出行", -20.0, "2026-05-02 12:00:00", "5月")
        data = _run_analysis_cli(tmp_db_dir, "cat_compare",
                                 "--from1", "2026-05-01", "--to1", "2026-05-31",
                                 "--from2", "2026-04-01", "--to2", "2026-04-30")
        d = data["data"]
        rows = {x["category"]: x for x in d["rows"]}
        assert rows["餐饮"]["amount_diff"] == 70.0  # 100 - 30
        assert rows["餐饮"]["count_diff"] == 0

    def test_cat_compare_new_category(self, tmp_db_dir):
        """看分类对比:区间二新增分类(区间一为 0)"""
        _insert(tmp_db_dir, "宠物", -200.0, "2026-04-15 12:00:00", "4月新增")
        data = _run_analysis_cli(tmp_db_dir, "cat_compare",
                                 "--from1", "2026-05-01", "--to1", "2026-05-31",
                                 "--from2", "2026-04-01", "--to2", "2026-04-30")
        rows = {x["category"]: x for x in data["data"]["rows"]}
        assert rows["宠物"]["amount_diff"] == -200.0  # 5月 0 - 4月 200


# ── 趋势 2 ────────────────────────────────────────────────────────────────────

class TestTrendFamily:
    """看趋势/看分类趋势"""

    def test_trend_series_and_peak(self, tmp_db_dir):
        """看趋势:近 N 个月序列(含空月)+ 峰值 + 月均"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-06-05 12:00:00", "6月")
        _insert(tmp_db_dir, "餐饮", -50.0, "2026-04-05 12:00:00", "4月")
        data = _run_analysis_cli(tmp_db_dir, "trend", "--months", "6")
        d = data["data"]
        assert len(d["series"]) == 6
        months = {m["month"]: m for m in d["series"]}
        assert months["2026-04"]["expense"] == 50.0
        assert months["2026-05"]["expense"] == 0.0  # 空月补零
        assert months["2026-06"]["expense"] == 100.0
        assert d["peak"]["month"] == "2026-06" and d["peak"]["expense"] == 100.0
        assert d["avg_expense"] == 25.0  # 150 / 6

    def test_cat_trend(self, tmp_db_dir):
        """看分类趋势:某分类逐月 + 峰值月"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -80.0, "2026-05-05 12:00:00", "5月")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -20.0, "2026-05-06 15:00:00", "奶茶")
        _insert(tmp_db_dir, "出行/网约车", -30.0, "2026-05-07 18:00:00", "打车")
        data = _run_analysis_cli(tmp_db_dir, "cat_trend", "--category", "餐饮", "--months", "6")
        d = data["data"]
        assert d["category"] == "餐饮"
        months = {m["month"]: m for m in d["series"]}
        assert months["2026-05"]["expense"] == 100.0  # L1 前缀聚合
        assert d["peak"]["month"] == "2026-05"

    def test_trend_empty(self, empty_db):
        """看趋势:空库 → 空序列不崩"""
        data = _run_analysis_cli(empty_db, "trend", "--months", "6")
        assert len(data["data"]["series"]) == 6
        assert data["data"]["peak"]["expense"] == 0


# ── 金额 3 ────────────────────────────────────────────────────────────────────

class TestAmountFamily:
    """看大额/看高频/看分布"""

    def test_top_n(self, tmp_db_dir):
        """看大额:支出 TOP N(金额降序)"""
        _insert(tmp_db_dir, "居家", -3000.0, "2026-03-01 10:00:00", "房租")
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-02 12:00:00", "午饭")
        _insert(tmp_db_dir, "出行", -150.0, "2026-03-03 18:00:00", "打车")
        data = _run_analysis_cli(tmp_db_dir, "top", "--limit", "2", "--from", "2026-03-01", "--to", "2026-03-31")
        d = data["data"]
        assert len(d["items"]) == 2
        assert d["items"][0]["amount"] == -3000.0
        assert d["items"][1]["amount"] == -150.0

    def test_top_excludes_income(self, tmp_db_dir):
        """看大额:收入不计入支出排行"""
        _insert(tmp_db_dir, "工资", 8000.0, "2026-03-05 09:00:00", "工资")
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-02 12:00:00", "午饭")
        data = _run_analysis_cli(tmp_db_dir, "top", "--limit", "10", "--from", "2026-03-01", "--to", "2026-03-31")
        assert len(data["data"]["items"]) == 1

    def test_top_freq(self, tmp_db_dir):
        """看高频:分类笔数 TOP(笔数/总金额/单均/最近一笔)"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-03-01 12:00:00", "1")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -18.0, "2026-03-02 15:00:00", "2")
        _insert(tmp_db_dir, "餐饮/外卖/晚餐", -45.0, "2026-03-03 19:00:00", "3")
        _insert(tmp_db_dir, "出行/网约车", -20.0, "2026-03-04 18:00:00", "4")
        data = _run_analysis_cli(tmp_db_dir, "top_freq", "--from", "2026-03-01", "--to", "2026-03-31")
        d = data["data"]
        assert d["items"][0]["category"] == "餐饮"
        assert d["items"][0]["count"] == 3
        assert d["items"][0]["total"] == 98.0
        assert d["items"][0]["avg"] == round(98 / 3, 2)
        assert d["items"][0]["last_time"].startswith("2026-03-03")

    def test_distribution_buckets(self, tmp_db_dir):
        """看分布:5 区间直方(<10/10-50/50-100/100-500/500+)"""
        _insert(tmp_db_dir, "餐饮", -5.0, "2026-03-01 12:00:00", "5元")
        _insert(tmp_db_dir, "餐饮", -30.0, "2026-03-02 12:00:00", "30元")
        _insert(tmp_db_dir, "餐饮", -70.0, "2026-03-03 12:00:00", "70元")
        _insert(tmp_db_dir, "餐饮", -300.0, "2026-03-04 12:00:00", "300元")
        _insert(tmp_db_dir, "餐饮", -2000.0, "2026-03-05 12:00:00", "2000元")
        data = _run_analysis_cli(tmp_db_dir, "distribution", "--month", "2026-03")
        d = data["data"]
        by = {x["bucket"]: x for x in d["buckets"]}
        assert by["10 元以下"]["count"] == 1
        assert by["10~50"]["count"] == 1
        assert by["50~100"]["count"] == 1
        assert by["100~500"]["count"] == 1
        assert by["500 以上"]["count"] == 1
        assert d["total"] == 5

    def test_distribution_income(self, tmp_db_dir):
        """看分布:收入口径"""
        _insert(tmp_db_dir, "工资", 8000.0, "2026-03-05 09:00:00", "工资")
        _insert(tmp_db_dir, "奖金", 200.0, "2026-03-06 09:00:00", "奖金")
        data = _run_analysis_cli(tmp_db_dir, "distribution", "--month", "2026-03", "--type", "income")
        by = {x["bucket"]: x for x in data["data"]["buckets"]}
        assert by["500 以上"]["count"] == 1
        assert by["100~500"]["count"] == 1


# ── 统计洞察 4 ────────────────────────────────────────────────────────────────

class TestInsightFamily:
    """做统计/看活跃/看洞察/看异常"""

    def test_stats(self, tmp_db_dir):
        """做统计:总笔数/记账天数/日均/首末时间 + 月度分布"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-01 12:00:00", "1")
        _insert(tmp_db_dir, "餐饮", -45.0, "2026-03-02 12:00:00", "2")
        _insert(tmp_db_dir, "餐饮", -55.0, "2026-04-01 12:00:00", "3")
        data = _run_analysis_cli(tmp_db_dir, "stats")
        d = data["data"]
        assert d["total_records"] == 3
        assert d["total_days"] == 3
        assert d["daily_avg"] == 1.0
        assert d["first_record"].startswith("2026-03-01")
        assert d["last_record"].startswith("2026-04-01")
        assert len(d["monthly_dist"]) == 2

    def test_stats_empty(self, empty_db):
        """做统计:空库 → 0 不崩"""
        data = _run_analysis_cli(empty_db, "stats")
        assert data["data"]["total_records"] == 0
        assert data["data"]["daily_avg"] == 0

    def test_activity_weekday_hour(self, tmp_db_dir):
        """看活跃:周几分布 + 时段分布"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-02 12:00:00", "周一中午")  # 2026-03-02 周一
        _insert(tmp_db_dir, "餐饮", -20.0, "2026-03-03 08:00:00", "周二早上")  # 周二
        _insert(tmp_db_dir, "餐饮", -10.0, "2026-03-03 20:00:00", "周二晚上")
        data = _run_analysis_cli(tmp_db_dir, "activity")
        d = data["data"]
        assert d["total"] == 3
        wd = {x["weekday"]: x["count"] for x in d["weekdays"]}
        assert wd["周一"] == 1 and wd["周二"] == 2
        hr = {x["hour"]: x["count"] for x in d["hours"]}
        assert hr["12"] == 1 and hr["08"] == 1 and hr["20"] == 1

    def test_insight_facts(self, tmp_db_dir):
        """看洞察:洞察生成器事实(period/category_dist/monthly_trend/top_expense)"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-03-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -18.0, "2026-03-02 15:00:00", "奶茶")
        _insert(tmp_db_dir, "工资", 8000.0, "2026-03-05 09:00:00", "工资")
        data = _run_analysis_cli(tmp_db_dir, "insight", "--months", "6")
        d = data["data"]
        assert d["period"]["expense"] == 53.0
        assert d["period"]["income"] == 8000.0
        cats = {c["category"]: c for c in d["category_dist"]}
        assert cats["餐饮"]["expense"] == 53.0
        assert len(d["monthly_trend"]["months"]) == 6
        assert len(d["top_expense"]) >= 1

    def test_insight_empty(self, empty_db):
        """看洞察:空库 → 空事实不崩"""
        data = _run_analysis_cli(empty_db, "insight", "--months", "6")
        d = data["data"]
        assert d["period"]["expense"] == 0 and d["category_dist"] == []

    def test_anomaly_mom_and_surge(self, tmp_db_dir):
        """看异常:月度环比 + 分类暴涨检测(事实层)"""
        _insert(tmp_db_dir, "餐饮", -100.0, "2026-04-05 12:00:00", "4月")
        _insert(tmp_db_dir, "餐饮", -500.0, "2026-05-05 12:00:00", "5月暴涨")
        data = _run_analysis_cli(tmp_db_dir, "anomaly", "--months", "6")
        d = data["data"]
        mom = {x["month"]: x for x in d["month_over_month"]}
        # 4月→5月 +400%
        may = next(x for x in d["month_over_month"] if x["month"] == "2026-05")
        assert may["pct"] == 400.0
        surge = {x["category"]: x for x in d["category_surge"]}
        assert surge["餐饮"]["pct"] == 400.0

    def test_anomaly_empty(self, empty_db):
        """看异常:空库 → 空列表不崩"""
        data = _run_analysis_cli(empty_db, "anomaly", "--months", "6")
        assert data["data"]["total"] == 0


# ── 状态聚合 4(#tag 聚合)──────────────────────────────────────────────────────

class TestStatusAggregateFamily:
    """看借贷/看报销/看分期/看退款"""

    def _seed_status_db(self, tmp_db_dir):
        _insert(tmp_db_dir, "借贷/借出", -500.0, "2026-07-01 10:00:00", "#借出 #借给小明 #未还", ledger="借贷")
        _insert(tmp_db_dir, "借贷/借入", 300.0, "2026-07-05 10:00:00", "#借入 #向小红借 #未还", ledger="借贷")
        _insert(tmp_db_dir, "借贷/借出", -200.0, "2026-06-01 10:00:00", "#借出 #借给老王 #已还", ledger="借贷")
        _insert(tmp_db_dir, "餐饮", -88.0, "2026-07-10 12:00:00", "客户午餐 #待报销")
        _insert(tmp_db_dir, "餐饮", 88.0, "2026-07-15 12:00:00", "报销到账 #报销到账")
        _insert(tmp_db_dir, "分期/手机", -3400.0, "2026-07-01 00:00:00", "#分期 手机 第1期/3")
        _insert(tmp_db_dir, "分期/手机", -3300.0, "2026-08-01 00:00:00", "#分期 手机 第2期/3")
        _insert(tmp_db_dir, "分期/手机", -3300.0, "2026-09-01 00:00:00", "#分期 手机 第3期/3")
        _insert(tmp_db_dir, "餐饮", 30.0, "2026-07-08 12:00:00", "外卖退款 #退款")

    def test_debt_summary(self, tmp_db_dir):
        """看借贷:借出/借入未还总额 + 对象列表 + 已还统计"""
        self._seed_status_db(tmp_db_dir)
        data = _run_analysis_cli(tmp_db_dir, "debt_summary")
        d = data["data"]
        assert d["lent_unpaid_total"] == 500.0
        assert d["borrowed_unpaid_total"] == 300.0
        assert d["lent_paid_count"] == 1
        by = {x["target"]: x for x in d["objects"]}
        assert by["小明"]["lent_unpaid"] == 500.0
        assert by["小红"]["borrowed_unpaid"] == 300.0

    def test_debt_summary_empty(self, empty_db):
        """看借贷:空库 → 0 不崩"""
        data = _run_analysis_cli(empty_db, "debt_summary")
        d = data["data"]
        assert d["lent_unpaid_total"] == 0 and d["objects"] == []

    def test_reimburse_summary(self, tmp_db_dir):
        """看报销:待报销 + 已到账 + 历史"""
        self._seed_status_db(tmp_db_dir)
        data = _run_analysis_cli(tmp_db_dir, "reimburse_summary")
        d = data["data"]
        assert d["pending_total"] == 88.0 and d["pending_count"] == 1
        assert d["received_total"] == 88.0 and d["received_count"] == 1
        statuses = {x["status"] for x in d["history"]}
        assert statuses == {"待报销", "已到账"}

    def test_installment_summary(self, tmp_db_dir):
        """看分期:进行中分期卡 + 历史分期"""
        self._seed_status_db(tmp_db_dir)
        data = _run_analysis_cli(tmp_db_dir, "installment_summary")
        d = data["data"]
        assert d["active_count"] == 1
        g = d["active"][0]
        assert g["name"] == "手机"
        assert g["total"] == 10000.0 and g["periods"] == 3
        assert g["status"] == "进行中"
        assert g["remaining"] == g["periods"] - g["paid"]

    def test_refund_summary(self, tmp_db_dir):
        """看退款:总额/次数 + 月份分布 + 明细"""
        self._seed_status_db(tmp_db_dir)
        data = _run_analysis_cli(tmp_db_dir, "refund_summary")
        d = data["data"]
        assert d["total"] == 30.0 and d["count"] == 1
        assert d["monthly"][0]["month"] == "2026-07"
        assert d["details"][0]["amount"] == 30.0

    def test_refund_summary_empty(self, empty_db):
        """看退款:空库 → 0 不崩"""
        data = _run_analysis_cli(empty_db, "refund_summary")
        assert data["data"]["total"] == 0 and data["data"]["count"] == 0
