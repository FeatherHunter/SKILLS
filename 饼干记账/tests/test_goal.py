"""tests/test_goal.py — 目标域 4 场景 CLI/模板/渲染测试(隔离契约:scripts/goal/ + templates/目标/)

覆盖(对齐 scenes/goal.yaml 4 场景):
- 设定预算(set-budget → goals.json;覆盖冲突 + --force)/ 看预算(budget → bills 聚合进度)
- 设定目标(set-saving → goals.json)/ 看目标(saving → 目标期内收入-支出累计 + 预计达成日)
- 渲染:goal/render.py 4 模式(采集表单 ×2 + 进度条视图 ×2)合法 HTML + 复制数据/日志 + B1 toast
- meta.scene_id/wake_word 对齐 scenes/goal.yaml(门禁 A 层 1 数据源)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

GOAL_CLI = SCRIPTS_DIR / "goal" / "cli.py"
GOAL_RENDER = SCRIPTS_DIR / "goal" / "render.py"


def _run_goal_cli(tmp_db_dir, *args):
    """跑 goal/cli.py <args> --json,返回解析后的 dict"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(GOAL_CLI)] + list(args) + ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env, timeout=30)
    assert result.returncode == 0, (
        f"goal/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def _insert(tmp_db_dir, category, amount, time_str, note="", account="", ledger="生活"):
    """直接向临时库插记录(与 test_query.py 同约定)"""
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


def _goals(tmp_db_dir):
    """读临时库 goals.json(不存在 → 空结构)"""
    gf = tmp_db_dir / "goals.json"
    if not gf.exists():
        return {"budgets": [], "savings": []}
    return json.loads(gf.read_text(encoding="utf-8"))


def _run_goal_render(tmp_db_dir, mode, *extra_args, expect_rc=0):
    """跑 goal/render.py <mode> [args] --out <tmp>，返回 (rc, out, err, html_path)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    out_dir = tmp_db_dir / "html_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{mode}.html"
    cmd = [sys.executable, str(GOAL_RENDER), mode, "--out", str(out_path)] + list(extra_args)
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", env=env, timeout=30)
    assert result.returncode == expect_rc, (
        f"goal/render.py {mode} rc={result.returncode}(期望 {expect_rc})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result.returncode, result.stdout, result.stderr, out_path


def _payload_of(html_path):
    """提取 HTML 中注入的 payload JSON"""
    text = html_path.read_text(encoding="utf-8-sig")
    m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
    assert m, "缺 payload 注入点"
    return json.loads(m.group(1))


def _assert_html_well_formed(html_path, *, require_error_fallback: bool = True):
    """断言 HTML:存在 + BOM + charset + payload + XSS 守卫 + 错误态兜底

    采集表单(对齐既有写入表单约定:payload 非 ok 静默)不需要错误态 fallback。
    """
    assert html_path.exists(), f"输出 HTML 不存在: {html_path}"
    raw = html_path.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", f"缺 UTF-8 BOM(前 3 字节 = {raw[:3]!r})"
    text = raw.decode("utf-8-sig")
    assert 'charset="UTF-8"' in text or "charset=utf-8" in text.lower(), "缺 <meta charset>"
    assert '<script id="payload"' in text, "缺 <script id=\"payload\"> 注入点"
    assert "escapeHTML" in text or "function esc(" in text or "var esc = function" in text, \
        "缺 XSS 守卫函数"
    if require_error_fallback:
        assert "error-card" in text or "renderError" in text, "缺错误态 fallback"


# ── 设定预算(set-budget · 采集型)─────────────────────────────────────────────

class TestSetBudget:
    def test_set_budget_default_month(self, tmp_db_dir):
        """默认月份 = 当前月;写入 goals.json/budgets"""
        from datetime import date
        data = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3000")
        assert data["status"] == "ok"
        b = data["data"]["budget"]
        assert b["month"] == date.today().strftime("%Y-%m")
        assert b["amount"] == 3000.0 and b["category"] == ""
        assert b["id"] == 1

    def test_set_budget_with_month_category(self, tmp_db_dir):
        """分类预算:--month + --category 落库"""
        data = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "500",
                             "--month", "2026-08", "--category", "餐饮")
        b = data["data"]["budget"]
        assert b["month"] == "2026-08" and b["category"] == "餐饮" and b["amount"] == 500.0
        goals = _goals(tmp_db_dir)
        assert goals["budgets"][0]["category"] == "餐饮"

    def test_set_budget_conflict_then_force(self, tmp_db_dir):
        """覆盖语义:同月同类已存在 → conflict;--force 覆盖"""
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3000", "--month", "2026-08")
        data = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3500", "--month", "2026-08")
        assert data["data"]["conflict"] is True
        assert data["data"]["existing"]["amount"] == 3000.0
        # 未 force → 不写入
        goals = _goals(tmp_db_dir)
        assert len(goals["budgets"]) == 1 and goals["budgets"][0]["amount"] == 3000.0

        data2 = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3500",
                              "--month", "2026-08", "--force")
        assert data2["data"]["conflict"] is False
        assert data2["data"]["overwritten"]["amount"] == 3000.0
        goals2 = _goals(tmp_db_dir)
        assert len(goals2["budgets"]) == 1 and goals2["budgets"][0]["amount"] == 3500.0

    def test_set_budget_validation(self, tmp_db_dir):
        """金额 ≤ 0 / 月份格式错误 → status=error"""
        data = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "-100")
        assert data["status"] == "error"
        data2 = _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "100", "--month", "2026-13")
        assert data2["status"] == "error"


# ── 看预算(budget · 结果型)───────────────────────────────────────────────────

class TestBudget:
    def _seed(self, tmp_db_dir):
        _insert(tmp_db_dir, "餐饮/外卖/午餐", -286.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "餐饮/咖啡奶茶/咖啡", -28.0, "2026-08-02 09:00:00", "美式")
        _insert(tmp_db_dir, "出行/网约车", -50.0, "2026-08-03 18:00:00", "打车")
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-08-05 09:00:00", "工资")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "1000", "--month", "2026-08")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "500", "--month", "2026-08",
                      "--category", "餐饮")

    def test_budget_aggregation_l1_prefix(self, tmp_db_dir):
        """总预算 + 分类预算(L1 前缀:餐饮 命中 餐饮/*);实际 = 当月支出"""
        self._seed(tmp_db_dir)
        data = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")
        d = data["data"]
        assert d["month"] == "2026-08"
        assert len(d["budgets"]) == 2
        total = next(b for b in d["budgets"] if b["category"] == "")
        cat = next(b for b in d["budgets"] if b["category"] == "餐饮")
        # 总预算:实际 = 286+28+50 = 364
        assert total["actual"] == 364.0 and total["remaining"] == 636.0
        assert total["status"] == "ok" and round(total["pct"], 1) == 36.4
        # 分类预算(餐饮):实际 = 286+28 = 314
        assert cat["actual"] == 314.0 and cat["count"] == 2
        assert cat["remaining"] == 186.0
        # 汇总:总预算存在 → (总预算 1000, 当月全部支出 364),不重复计数
        assert d["totals"]["budget"] == 1000.0 and d["totals"]["actual"] == 364.0
        assert d["totals"]["remaining"] == 636.0
        assert d["totals"]["over_count"] == 0

    def test_budget_status_warn_over(self, tmp_db_dir):
        """状态机:>90% warn / >100% over(警示色数据源)"""
        _insert(tmp_db_dir, "餐饮", -490.0, "2026-08-01 12:00:00", "a")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "500", "--month", "2026-08",
                      "--category", "餐饮")
        d = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")["data"]
        assert d["budgets"][0]["status"] == "warn"  # 98%

        _insert(tmp_db_dir, "餐饮", -20.0, "2026-08-02 12:00:00", "b")
        d2 = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")["data"]
        assert d2["budgets"][0]["status"] == "over"  # 102%
        assert d2["totals"]["over_count"] == 1

    def test_budget_empty(self, tmp_db_dir):
        """无预算 → 空态(count=0)"""
        data = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")
        assert data["data"]["budgets"] == [] and data["data"]["count"] == 0

    def test_budget_month_filter(self, tmp_db_dir):
        """--month 只看该月预算(其他月不出现)"""
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3000", "--month", "2026-08")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "2000", "--month", "2026-09")
        d = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")["data"]
        assert len(d["budgets"]) == 1 and d["budgets"][0]["amount"] == 3000.0

    def test_budget_month_end_projection(self, tmp_db_dir):
        """月底预测(门禁 B 复查采纳):当月有日均/月底预计;过去月预测=实际;未来月无预测"""
        _insert(tmp_db_dir, "餐饮", -300.0, "2026-08-01 12:00:00", "a")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "1000", "--month", "2026-08")
        b = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-08")["data"]["budgets"][0]
        assert b["daily_avg"] is not None and b["month_end_proj"] is not None
        assert b["days_elapsed"] >= 1
        # 过去月(2026-07):预测 = 实际
        _insert(tmp_db_dir, "餐饮", -200.0, "2026-07-01 12:00:00", "b")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "1000", "--month", "2026-07")
        b7 = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-07")["data"]["budgets"][0]
        assert b7["month_end_proj"] == b7["actual"]
        # 未来月(2026-12):无预测
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "1000", "--month", "2026-12")
        b12 = _run_goal_cli(tmp_db_dir, "budget", "--month", "2026-12")["data"]["budgets"][0]
        assert b12["month_end_proj"] is None and b12["daily_avg"] is None


# ── 设定目标(set-saving · 采集型)─────────────────────────────────────────────

class TestSetSaving:
    def test_set_saving_basic(self, tmp_db_dir):
        """目标名/金额/截止日期落库"""
        data = _run_goal_cli(tmp_db_dir, "set-saving", "--name", "换手机",
                             "--amount", "10000", "--deadline", "2026-12-31")
        s = data["data"]["saving"]
        assert s["name"] == "换手机" and s["amount"] == 10000.0 and s["deadline"] == "2026-12-31"
        assert _goals(tmp_db_dir)["savings"][0]["name"] == "换手机"

    def test_set_saving_deadline_optional(self, tmp_db_dir):
        """无截止日期 → deadline=None"""
        data = _run_goal_cli(tmp_db_dir, "set-saving", "--name", "旅行基金", "--amount", "5000")
        assert data["data"]["saving"]["deadline"] is None

    def test_set_saving_validation(self, tmp_db_dir):
        """缺名 / 金额 ≤ 0 / 日期格式错 → status=error"""
        assert _run_goal_cli(tmp_db_dir, "set-saving", "--name", "", "--amount", "100")["status"] == "error"
        assert _run_goal_cli(tmp_db_dir, "set-saving", "--name", "x", "--amount", "-1")["status"] == "error"
        assert _run_goal_cli(tmp_db_dir, "set-saving", "--name", "x", "--amount", "100",
                             "--deadline", "2026-13-01")["status"] == "error"


# ── 看目标(saving · 结果型)───────────────────────────────────────────────────

class TestSaving:
    def _seed(self, tmp_db_dir, deadline="2026-12-31"):
        _insert(tmp_db_dir, "餐饮", -434.0, "2026-08-01 12:00:00", "午饭")
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-08-05 09:00:00", "工资")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "换手机",
                      "--amount", "10000", "--deadline", deadline)

    def test_saving_progress(self, tmp_db_dir):
        """已存 = 目标期内收入-支出累计;百分比/剩余/月均/预计达成日"""
        self._seed(tmp_db_dir)
        data = _run_goal_cli(tmp_db_dir, "saving")["data"]
        assert data["count"] == 1
        s = data["savings"][0]
        assert s["name"] == "换手机"
        assert s["saved"] == 7566.0  # 8000 - 434
        assert s["remaining"] == 2434.0
        assert s["pct"] == 75.7
        assert s["status"] == "on_track"
        assert s["monthly_avg"] == 7566.0
        assert s["eta"] == "2026-09"  # 2434 / 7566 → 1 个月 → 2026-09

    def test_saving_done(self, tmp_db_dir):
        """已存 ≥ 目标 → done"""
        _insert(tmp_db_dir, "工资/基本工资", 20000.0, "2026-08-05 09:00:00", "大工资")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "小目标", "--amount", "5000")
        s = _run_goal_cli(tmp_db_dir, "saving")["data"]["savings"][0]
        assert s["status"] == "done" and s["eta"] is None

    def test_saving_na_without_income(self, tmp_db_dir):
        """无净存 → status=na,eta=None(无法预计)"""
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "空目标", "--amount", "10000")
        s = _run_goal_cli(tmp_db_dir, "saving")["data"]["savings"][0]
        assert s["status"] == "na" and s["eta"] is None

    def test_saving_behind_deadline(self, tmp_db_dir):
        """预计达成日晚于截止日 → behind"""
        _insert(tmp_db_dir, "工资/基本工资", 1000.0, "2026-08-05 09:00:00", "小工资")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "急目标",
                      "--amount", "100000", "--deadline", "2026-08-31")
        s = _run_goal_cli(tmp_db_dir, "saving")["data"]["savings"][0]
        assert s["status"] == "behind"

    def test_saving_name_filter(self, tmp_db_dir):
        """--name 过滤 + 无目标空态"""
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "换手机", "--amount", "10000")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "旅行", "--amount", "5000")
        d = _run_goal_cli(tmp_db_dir, "saving", "--name", "旅行")["data"]
        assert d["count"] == 1 and d["savings"][0]["name"] == "旅行"
        d2 = _run_goal_cli(tmp_db_dir, "saving")["data"]
        assert d2["count"] == 2
        d3 = _run_goal_cli(tmp_db_dir, "saving", "--name", "不存在")["data"]
        assert d3["savings"] == []

    def test_saving_empty(self, tmp_db_dir):
        """无目标 → 空态"""
        data = _run_goal_cli(tmp_db_dir, "saving")
        assert data["data"]["savings"] == [] and data["data"]["count"] == 0

    def test_saving_needed_monthly(self, tmp_db_dir):
        """达标所需月存(门禁 B 复查采纳):有截止日且未达成 → 剩余/剩余月数;无截止日 → None"""
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-08-05 09:00:00", "工资")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "换手机",
                      "--amount", "10000", "--deadline", "2026-12-31")
        s = _run_goal_cli(tmp_db_dir, "saving")["data"]["savings"][0]
        assert s["needed_monthly"] is not None and s["needed_monthly"] > 0
        # 无截止日 → None
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "旅行", "--amount", "5000")
        s2 = _run_goal_cli(tmp_db_dir, "saving", "--name", "旅行")["data"]["savings"][0]
        assert s2["needed_monthly"] is None
        # 已达成 → None
        _insert(tmp_db_dir, "工资/基本工资", 30000.0, "2026-08-06 09:00:00", "大额")
        s3 = _run_goal_cli(tmp_db_dir, "saving", "--name", "换手机")["data"]["savings"][0]
        assert s3["status"] == "done" and s3["needed_monthly"] is None


# ── 渲染(goal/render.py · 4 模式)─────────────────────────────────────────────

class TestGoalRender:
    @pytest.mark.parametrize("mode,extra", [
        ("set-budget", ["--amount", "3000", "--month", "2026-08"]),
        ("budget", ["--month", "2026-08"]),
        ("set-saving", ["--name", "换手机", "--amount", "10000", "--deadline", "2026-12-31"]),
        ("saving", []),
    ])
    def test_four_modes_generate_valid_html(self, tmp_db_dir, mode, extra):
        rc, out, err, html_path = _run_goal_render(tmp_db_dir, mode, *extra)
        _assert_html_well_formed(
            html_path, require_error_fallback=(mode in ("budget", "saving")))

    def test_view_html_has_copy_actions_and_b1(self, tmp_db_dir):
        """结果型视图:复制数据/日志按钮 + 弹层三选一 + B1 toast(08 §4 硬标准)"""
        for mode, extra in [("budget", []), ("saving", [])]:
            rc, out, err, html_path = _run_goal_render(tmp_db_dir, mode, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            assert 'id="copyDataBtn"' in text and 'id="copyLogBtn"' in text, f"{mode} 缺复制按钮"
            assert 'data-f="text"' in text and 'data-f="json"' in text and 'data-f="csv"' in text, \
                f"{mode} 缺弹层三选一"
            assert 'id="toastClose"' in text and "4500" in text, f"{mode} 缺 B1 toast(4.5s)"
            assert "buildData5" in text and "buildLogText" in text, f"{mode} 缺 5/6 段组装"
            assert "data.offline" in text, f"{mode} 缺离线态兜底"

    def test_form_html_has_confirm_prompt(self, tmp_db_dir):
        """采集表单:确认按钮(复制 prompt)+ 复制数据/日志 + B1 toast"""
        for mode, extra in [("set-budget", ["--amount", "3000"]),
                            ("set-saving", ["--name", "换手机", "--amount", "10000"])]:
            rc, out, err, html_path = _run_goal_render(tmp_db_dir, mode, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            assert 'id="copyPromptBtn"' in text, f"{mode} 缺确认按钮"
            assert 'id="copyDataBtn"' in text and 'id="copyLogBtn"' in text, f"{mode} 缺复制按钮"
            assert 'id="toastClose"' in text and "4500" in text, f"{mode} 缺 B1 toast"

    def test_meta_aligned_with_scenes_goal_yaml(self, tmp_db_dir):
        """meta.scene_id/wake_word 对齐 scenes/goal.yaml(门禁 A 层 1)"""
        cases = [
            ("set-budget", ["--amount", "3000"], "goal_set_budget", "设定预算"),
            ("budget", [], "goal_budget_status", "看预算"),
            ("set-saving", ["--name", "x", "--amount", "1"], "goal_set_saving", "设定目标"),
            ("saving", [], "goal_saving_status", "看目标"),
        ]
        for mode, extra, scene_id, wake in cases:
            rc, out, err, html_path = _run_goal_render(tmp_db_dir, mode, *extra)
            p = _payload_of(html_path)
            assert p["status"] == "ok", f"{mode} 状态应 ok:{p}"
            meta = p["data"]["meta"]
            assert meta["scene_id"] == scene_id, f"{mode} scene_id 期望 {scene_id},实际 {meta['scene_id']}"
            assert meta["wake_word"] == wake, f"{mode} wake_word 期望 {wake},实际 {meta['wake_word']}"
            assert meta["version"] == "2.0" and meta["command_cn"] and meta["render_cmd"]

    def test_form_fields_echoed(self, tmp_db_dir):
        """采集表单 payload.form.fields 回显 AI 解析字段"""
        rc, out, err, html_path = _run_goal_render(
            tmp_db_dir, "set-budget", "--amount", "3000", "--month", "2026-08", "--category", "餐饮")
        p = _payload_of(html_path)
        fields = p["data"]["form"]["fields"]
        assert fields["amount"] == "3000" and fields["month"] == "2026-08" and fields["category"] == "餐饮"

        rc, out, err, html_path = _run_goal_render(
            tmp_db_dir, "set-saving", "--name", "换手机", "--amount", "10000", "--deadline", "2026-12-31")
        p = _payload_of(html_path)
        fields = p["data"]["form"]["fields"]
        assert fields["name"] == "换手机" and fields["amount"] == "10000" and fields["deadline"] == "2026-12-31"

    def test_form_conflict_existing_warning(self, tmp_db_dir):
        """采集前冲突检查:同月同类预算已存在 → payload.form.existing(表单警示数据源)"""
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "3000", "--month", "2026-08")
        rc, out, err, html_path = _run_goal_render(
            tmp_db_dir, "set-budget", "--amount", "3500", "--month", "2026-08")
        p = _payload_of(html_path)
        existing = p["data"]["form"]["existing"]
        assert existing is not None and existing["amount"] == 3000.0
        # 模板含冲突提示节点
        text = html_path.read_text(encoding="utf-8-sig")
        assert 'id="conflictBox"' in text, "表单模板缺冲突提示节点"

    def test_view_payload_has_progress_data(self, tmp_db_dir):
        """结果型 payload 含进度数据(HTML 渲染数据源):预算进度条 + 目标进度"""
        _insert(tmp_db_dir, "餐饮", -460.0, "2026-08-01 12:00:00", "午饭")  # 92% → warn
        _insert(tmp_db_dir, "工资/基本工资", 8000.0, "2026-08-05 09:00:00", "工资")
        _run_goal_cli(tmp_db_dir, "set-budget", "--amount", "500", "--month", "2026-08",
                      "--category", "餐饮")
        _run_goal_cli(tmp_db_dir, "set-saving", "--name", "换手机", "--amount", "10000",
                      "--deadline", "2026-12-31")

        rc, out, err, html_path = _run_goal_render(tmp_db_dir, "budget", "--month", "2026-08")
        p = _payload_of(html_path)
        assert p["status"] == "ok"
        b = p["data"]["budgets"][0]
        assert b["amount"] == 500.0 and b["actual"] == 460.0 and b["status"] == "warn"
        assert "budget-bar" in html_path.read_text(encoding="utf-8-sig"), "模板缺进度条组件"

        rc, out, err, html_path = _run_goal_render(tmp_db_dir, "saving")
        p = _payload_of(html_path)
        s = p["data"]["savings"][0]
        assert s["name"] == "换手机" and s["pct"] > 0 and s["eta"] == "2026-09"
        assert "saving-bar" in html_path.read_text(encoding="utf-8-sig"), "模板缺目标进度组件"

    def test_default_output_filename_prefix(self, tmp_db_dir):
        """默认输出文件名:设定预算/看预算/设定目标/看目标 前缀(§12.A 中文 command)"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cases = [
            (["set-budget", "--amount", "3000"], "设定预算"),
            (["budget"], "看预算"),
            (["set-saving", "--name", "x", "--amount", "1"], "设定目标"),
            (["saving"], "看目标"),
        ]
        for args, prefix in cases:
            result = subprocess.run(
                [sys.executable, str(GOAL_RENDER)] + args,
                capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
            )
            assert result.returncode == 0, f"goal/render.py {' '.join(args)} 失败: {result.stderr}"
            fname = None
            for line in result.stdout.splitlines():
                if "已生成" in line:
                    last_part = line.replace("\\", "/").rsplit("/", 1)[-1].strip()
                    for suffix in [".", ",", ")", "]"]:
                        if last_part.endswith(suffix):
                            last_part = last_part[:-1]
                    if last_part.endswith(".html"):
                        fname = last_part
                        break
            assert fname is not None, f"未从 stdout 解析文件名: {result.stdout}"
            assert fname.startswith(prefix), \
                f"{args} 文件名期望以 {prefix} 开头,实际 {fname}"
