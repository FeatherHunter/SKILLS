"""tests/test_query.py — 查询域 15 场景 CLI 测试(隔离契约:scripts/query/)

覆盖(对齐 scenes/query.yaml 15 场景):
- 时间族 7:查今天(summary)/查昨天/查某天(list --date)/查最近(recent --limit/--days/--sort)/查周/查月/查区间(list --from --to)
- 条件族 5:查分类(组合参数)/搜备注(search)/查标签(tag)/查账户(list --account)/查账本(list --ledger)
- 状态族 3:查欠款(debt #未还)/查待报销(reimburse #待报销)/查分期(installment #分期)
外部行为校验:CLI --json 三段式 {status, data, message};KPI 聚合正确;空态不崩。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

QUERY_CLI = SCRIPTS_DIR / "query" / "cli.py"


def _run_query_cli(tmp_db_dir, *args):
    """跑 query/cli.py <args> --json,返回解析后的 dict(rc!=0 时断言失败并打印输出)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(QUERY_CLI)] + list(args) + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
    assert result.returncode == 0, (
        f"query/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
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


# ── 时间族 7 ────────────────────────────────────────────────────────────────

class TestTimeFamily:
    """查今天/查某天/查最近/查周/查月/查区间"""

    def test_summary_today(self, tmp_db_dir):
        """查今天:4 KPI + 今日明细 + 分类聚合(seeded_db 含今天数据 → 非空)"""
        today = date.today()
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, f"{today:%Y-%m-%d} 12:00:00", "午饭", "支付宝")
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, f"{today:%Y-%m-%d} 09:00:00", "工资")
        data = _run_query_cli(tmp_db_dir, "summary")
        assert data["status"] == "ok"
        d = data["data"]
        assert d["count"] == 2
        assert d["expense"] == 35.0 and d["income"] == 8000.0 and d["net"] == 7965.0
        assert len(d["records"]) == 2
        assert len(d["categories"]) >= 1 and d["categories"][0]["category"].startswith("餐饮")

    def test_summary_empty_db(self, empty_db):
        """查今天:空库 → count=0 + 空态数据"""
        data = _run_query_cli(empty_db, "summary")
        assert data["data"]["count"] == 0 and data["data"]["records"] == []

    def test_list_date(self, tmp_db_dir):
        """查某天:list --date 2026-08-01 → 只返回当天记录"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/堂食/晚餐", -120.0, "2026-08-02 19:00:00", "跨天")
        data = _run_query_cli(tmp_db_dir, "list", "--date", "2026-08-01")
        assert data["data"]["count"] == 1
        assert data["data"]["records"][0]["time"].startswith("2026-08-01")

    def test_list_range_inclusive(self, tmp_db_dir):
        """查区间:list --from 2026-08-01 --to 2026-08-02 → 两天都含(闭区间)"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/堂食/晚餐", -120.0, "2026-08-02 19:00:00", "晚饭")
        _insert(tmp_db_dir, "餐饮/外卖/早餐", -10.0, "2026-08-03 08:00:00", "早饭")
        data = _run_query_cli(tmp_db_dir, "list", "--from", "2026-08-01", "--to", "2026-08-02")
        assert data["data"]["count"] == 2

    def test_list_week_semantics(self, tmp_db_dir):
        """查周:AI 传周一~周日 → CLI 按区间执行(2026-08-03 周一 ~ 08-09 周日)"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-08-03 12:00:00", "周一")
        _insert(tmp_db_dir, "餐饮", -20.0, "2026-08-09 18:00:00", "周日")
        _insert(tmp_db_dir, "餐饮", -99.0, "2026-08-10 10:00:00", "下周一")
        data = _run_query_cli(tmp_db_dir, "list", "--from", "2026-08-03", "--to", "2026-08-09")
        assert data["data"]["count"] == 2
        assert data["data"]["expense"] == 55.0

    def test_list_month_semantics(self, tmp_db_dir):
        """查月:AI 传 1 日~末日 → 整月数据"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-03-01 12:00:00", "1号")
        _insert(tmp_db_dir, "餐饮", -45.0, "2026-03-31 20:00:00", "31号")
        _insert(tmp_db_dir, "餐饮", -10.0, "2026-04-01 08:00:00", "4月")
        data = _run_query_cli(tmp_db_dir, "list", "--from", "2026-03-01", "--to", "2026-03-31")
        assert data["data"]["count"] == 2

    def test_list_from_without_to_errors(self, tmp_db_dir):
        """缺参(只传 --from)→ CLI 报错(三段式 status=error)"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [sys.executable, str(QUERY_CLI), "list", "--from", "2026-08-01", "--json"],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
        )
        assert result.returncode == 0  # ValueError 被捕获 → JSON error
        out = json.loads(result.stdout)
        assert out["status"] == "error"

    def test_recent_limit(self, tmp_db_dir):
        """查最近:--limit 5 → 最多 5 条(时间倒序)"""
        for i in range(8):
            _insert(tmp_db_dir, "餐饮", -float(i + 1), f"2026-08-{(i % 28) + 1:02d} 12:00:00", f"记录{i}")
        data = _run_query_cli(tmp_db_dir, "recent", "--limit", "5")
        assert data["data"]["count"] == 5

    def test_recent_days(self, tmp_db_dir):
        """查最近:--days 7 → 近 7 天(今天起往回)"""
        today = date.today()
        _insert(tmp_db_dir, "餐饮", -35.0, f"{today:%Y-%m-%d} 12:00:00", "今天")
        _insert(tmp_db_dir, "餐饮", -20.0, f"{(today - timedelta(days=3)):%Y-%m-%d} 12:00:00", "3天前")
        _insert(tmp_db_dir, "餐饮", -10.0, f"{(today - timedelta(days=10)):%Y-%m-%d} 12:00:00", "10天前")
        data = _run_query_cli(tmp_db_dir, "recent", "--days", "7")
        assert data["data"]["count"] == 2

    def test_recent_sort_amount_desc(self, tmp_db_dir):
        """查最近:--sort amount_desc → 金额从大到小"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-08-01 12:00:00", "小")
        _insert(tmp_db_dir, "餐饮", -3000.0, "2026-08-02 12:00:00", "大")
        data = _run_query_cli(tmp_db_dir, "recent", "--limit", "10", "--sort", "amount_desc")
        assert data["data"]["records"][0]["amount"] == -3000.0


# ── 条件族 5 ────────────────────────────────────────────────────────────────

class TestConditionFamily:
    """查分类(组合)/搜备注/查标签/查账户/查账本"""

    def test_category_l1_prefix(self, tmp_db_dir):
        """查分类:传 L1「餐饮」→ 命中 餐饮/* 全部子分类"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -18.0, "2026-08-02 15:00:00", "奶茶")
        _insert(tmp_db_dir, "出行/网约车", -20.0, "2026-08-03 18:00:00", "打车")
        data = _run_query_cli(tmp_db_dir, "list", "--category", "餐饮")
        assert data["data"]["count"] == 2

    def test_category_combo_params(self, tmp_db_dir):
        """查分类组合参数:分类 + 账户 + 收支方向"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭", account="支付宝")
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -25.0, "2026-08-02 12:00:00", "午饭", account="微信")
        _insert(tmp_db_dir, "餐饮/外卖/午餐", 100.0, "2026-08-03 12:00:00", "退款", account="支付宝")
        data = _run_query_cli(tmp_db_dir, "list", "--category", "餐饮", "--account", "支付宝", "--type", "expense")
        assert data["data"]["count"] == 1
        assert data["data"]["records"][0]["account"] == "支付宝"

    def test_category_pct(self, tmp_db_dir):
        """查分类契约:占比 = 该分类支出 / 同期全部支出"""
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -35.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/奶茶", -15.0, "2026-08-02 12:00:00", "奶茶")
        _insert(tmp_db_dir, "出行/网约车", -50.0, "2026-08-03 12:00:00", "打车")
        data = _run_query_cli(tmp_db_dir, "list", "--category", "餐饮")
        # 餐饮支出 50 / 全部支出 100 = 50%
        assert data["data"]["category_pct"] == 50.0
        assert data["data"]["category"] == "餐饮"

    def test_search_keyword(self, tmp_db_dir):
        """搜备注:关键词命中备注"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-08-01 12:00:00", "午饭 牛肉面")
        _insert(tmp_db_dir, "餐饮", -20.0, "2026-08-02 12:00:00", "晚饭 饺子")
        data = _run_query_cli(tmp_db_dir, "search", "牛肉面")
        assert data["data"]["count"] == 1

    def test_tag_aggregation(self, tmp_db_dir):
        """查标签:#旅行 聚合(总笔数/支出) + 不误伤 #旅行计划"""
        _insert(tmp_db_dir, "玩乐/旅游", -800.0, "2026-08-01 10:00:00", "订酒店 #旅行")
        _insert(tmp_db_dir, "出行/机票", -1500.0, "2026-08-02 10:00:00", "机票 #旅行")
        _insert(tmp_db_dir, "餐饮", -30.0, "2026-08-03 10:00:00", "零食 #旅行计划")
        data = _run_query_cli(tmp_db_dir, "tag", "--tag", "旅行")
        assert data["data"]["count"] == 2
        assert data["data"]["expense"] == 2300.0
        assert data["data"]["tag"] == "旅行"

    def test_account_filter(self, tmp_db_dir):
        """查账户:--account 支付宝 → 该账户流水 + KPI"""
        _insert(tmp_db_dir, "餐饮", -35.0, "2026-08-01 12:00:00", "午饭", account="支付宝")
        _insert(tmp_db_dir, "餐饮", -20.0, "2026-08-02 12:00:00", "晚饭", account="微信")
        data = _run_query_cli(tmp_db_dir, "list", "--account", "支付宝")
        assert data["data"]["count"] == 1
        assert data["data"]["expense"] == 35.0

    def test_ledger_filter(self, tmp_db_dir):
        """查账本:--ledger 旅行 → 该账本记录"""
        _insert(tmp_db_dir, "玩乐/旅游", -800.0, "2026-08-01 10:00:00", "酒店", ledger="旅行")
        _insert(tmp_db_dir, "餐饮", -30.0, "2026-08-02 10:00:00", "午饭", ledger="生活")
        data = _run_query_cli(tmp_db_dir, "list", "--ledger", "旅行")
        assert data["data"]["count"] == 1


# ── 状态族 3 ────────────────────────────────────────────────────────────────

class TestStatusFamily:
    """查欠款(#未还)/查待报销(#待报销)/查分期(#分期)"""

    def _seed_status_db(self, tmp_db_dir):
        """插入借贷/报销/分期样本"""
        # 借出未还(对象 小明)
        _insert(tmp_db_dir, "借贷/借出", -500.0, "2026-07-01 10:00:00", "#借出 #借给小明 #未还", ledger="借贷")
        # 借入未还(对象 小红)
        _insert(tmp_db_dir, "借贷/借入", 300.0, "2026-07-05 10:00:00", "#借入 #向小红借 #未还", ledger="借贷")
        # 已还(应排除)
        _insert(tmp_db_dir, "借贷/借出", -200.0, "2026-06-01 10:00:00", "#借出 #借给老王 #已还", ledger="借贷")
        # 待报销
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -88.0, "2026-07-10 12:00:00", "客户午餐 #待报销")
        _insert(tmp_db_dir, "出行/网约车", -45.0, "2026-07-11 12:00:00", "出差打车 #待报销")
        # 分期(手机 3 期:7/8/9 月,首期 3400 + 每期 3300)
        _insert(tmp_db_dir, "分期/手机", -3400.0, "2026-07-01 00:00:00", "#分期 手机 第1期/3")
        _insert(tmp_db_dir, "分期/手机", -3300.0, "2026-08-01 00:00:00", "#分期 手机 第2期/3")
        _insert(tmp_db_dir, "分期/手机", -3300.0, "2026-09-01 00:00:00", "#分期 手机 第3期/3")

    def test_debt_aggregation(self, tmp_db_dir):
        """查欠款:借出未还总额 + 借入未还总额 + 对象解析;已还排除"""
        self._seed_status_db(tmp_db_dir)
        data = _run_query_cli(tmp_db_dir, "debt")
        d = data["data"]
        assert d["lent_unpaid_total"] == 500.0
        assert d["borrowed_unpaid_total"] == 300.0
        assert d["count"] == 2
        directions = {it["direction"] for it in d["records"]}
        assert directions == {"借出", "借入"}
        by_dir = {it["direction"]: it for it in d["records"]}
        assert by_dir["借出"]["target"] == "小明"
        assert by_dir["借入"]["target"] == "小红"

    def test_debt_target_filter(self, tmp_db_dir):
        """查欠款:--target 小明 → 只留小明"""
        self._seed_status_db(tmp_db_dir)
        data = _run_query_cli(tmp_db_dir, "debt", "--target", "小明")
        d = data["data"]
        assert d["count"] == 1 and d["records"][0]["target"] == "小明"

    def test_debt_empty(self, tmp_db_dir):
        """查欠款:无 #未还 → 空态"""
        data = _run_query_cli(tmp_db_dir, "debt")
        assert data["data"]["count"] == 0 and data["data"]["records"] == []

    def test_reimburse_aggregation(self, tmp_db_dir):
        """查待报销:#待报销 总额 + 列表"""
        self._seed_status_db(tmp_db_dir)
        data = _run_query_cli(tmp_db_dir, "reimburse")
        d = data["data"]
        assert d["count"] == 2
        assert d["total"] == 133.0

    def test_reimburse_empty(self, tmp_db_dir):
        """查待报销:无 → 空态"""
        data = _run_query_cli(tmp_db_dir, "reimburse")
        assert data["data"]["count"] == 0

    def test_installment_groups(self, tmp_db_dir):
        """查分期:#分期 按名目分组 → 分期卡(总额/首期/每期/期数/已还/剩余)"""
        self._seed_status_db(tmp_db_dir)
        data = _run_query_cli(tmp_db_dir, "installment")
        d = data["data"]
        assert d["count"] == 3
        groups = d["groups"]
        assert len(groups) == 1
        g = groups[0]
        assert g["name"] == "手机"
        assert g["total"] == 10000.0
        assert g["periods"] == 3
        # 首期补差 3400,常规期 3300(众数判定)
        assert g["first"] == 3400.0
        assert g["each"] == 3300.0
        # 已还期数按日期 ≤ 今天(2026-07/08 期已到)
        assert g["paid"] >= 1
        assert g["remaining"] == g["periods"] - g["paid"]
        # 剩余金额 = 未来期实际金额(2026-09 期 3300)
        assert g["remaining_amount"] == 3300.0

    def test_installment_name_filter(self, tmp_db_dir):
        """查分期:--name 手机 → 只留手机;--name 不存在 → 空"""
        self._seed_status_db(tmp_db_dir)
        data = _run_query_cli(tmp_db_dir, "installment", "--name", "手机")
        assert len(data["data"]["groups"]) == 1
        data2 = _run_query_cli(tmp_db_dir, "installment", "--name", "不存在")
        assert data2["data"]["groups"] == []

    def test_installment_empty(self, tmp_db_dir):
        """查分期:无 → 空态"""
        data = _run_query_cli(tmp_db_dir, "installment")
        assert data["data"]["groups"] == [] and data["data"]["count"] == 0
