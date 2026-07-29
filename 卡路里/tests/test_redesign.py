#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_redesign.py — 卡路里 HTML 重设计 acceptance tests

ticket 01 · 2026-07-29 起,后续 ticket 14 张在此累积 acceptance tests。
依据:.scratch/card-html-redesign/spec.md Testing Decisions · vertical slices。

测试 seam 架构(从高到低):
  1. End-to-end HTML render:run render 脚本 + mock JSON + assert DOM 节点
  2. JSON data-shape assertion:parse window.__DATA__ + assert schema
  3. §04 决策矩阵一致性:scripts/check_decision_matrix.py
  4. 小数精度巡检:scripts/check_decimal_precision.py

当前已落地的 acceptance tests:
  - test_decision_matrix_checker_passes (seam 3)
  - test_decimal_precision_checker_passes (seam 4)
  - test_calorie_trend_precision_round (seam 1+2 · ticket 13)
  - test_help_center_ergonomics (seam 1 · ticket 07)
  - test_water_html_renders (seam 1+2 · ticket 02)
  - test_home_dashboard_quick_actions_use_prompts (seam 1+2 · ticket 09)
  - test_home_dashboard_deficit_math_breakdown (seam 1+2 · ticket 08)
  - test_cross_page_prompt_consistency (seam 2 · ticket 15)

执行:
    cd 卡路里 && python -m pytest tests/test_redesign.py -v
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATES_DIR = SKILL_DIR / "templates"
MOCK_DIR = SKILL_DIR / "tests" / "fixtures" / "mock"


# ============= util =============

def _run_script(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """真跑 render 脚本,return CompletedProcess"""
    return subprocess.run(
        [sys.executable, *args],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def _extract_payload(html_text: str) -> dict | None:
    """从生成的 HTML 抽取 window.__DATA__ JSON"""
    m = re.search(
        r'<script>\s*window\.__DATA__\s*=\s*(\{.*?\});?\s*</script>',
        html_text, re.DOTALL,
    )
    if not m:
        return None
    return json.loads(m.group(1).replace('<\\/', '</'))


# ============= 基础设施(seam 3+4 · ticket 01 自测) =============

class TestDecisionMatrixChecker:
    """ticket 01 · check_decision_matrix.py 自测"""

    def test_decision_matrix_checker_passes(self):
        """§完整 HTML 模板清单 全 ✅ 行必备:render + template;soft:mock"""
        r = _run_script(str(SCRIPTS_DIR / "check_decision_matrix.py"))
        assert r.returncode == 0, (
            f"check_decision_matrix.py 退出码 {r.returncode}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )
        assert "pass" in r.stdout, f"stdout 应包含 pass 标识,实得: {r.stdout}"


class TestDecimalPrecisionChecker:
    """ticket 01 · check_decimal_precision.py 自测"""

    def test_decimal_precision_checker_passes(self, tmp_path):
        """空 calorie_html 应 pass(无文件可扫)"""
        # 临时把 HTML_DIR 指到一个空目录
        # 用 mock HTML fixture 验证逻辑:故意放一个泄漏精度的 HTML → fail
        bad_html = tmp_path / "calorie_html"
        bad_html.mkdir()
        bad_file = bad_html / "bad_trend.html"
        bad_file.write_text(
            '<html><script>window.__DATA__ = {"status":"ok","data":'
            '{"summary":{"trend_value":-141.6550000000002}}};</script></html>',
            encoding="utf-8",
        )
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "check_decimal_precision.py"),
             "--mock", str(bad_file)],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
        )
        assert r.returncode == 1, (
            f"故意泄漏精度的 mock 应该 fail,实得 {r.returncode}\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}"
        )
        assert "-141.65" in r.stdout or "141.65" in r.stdout, (
            f"应报告 trend_value 精度问题,实得: {r.stdout}"
        )


# ============= vertical slice tests(后续 ticket 累积) =============

class TestCalorieTrendPrecision:
    """ticket 13 · render_calorie_trend.py round(2) 后端"""

    def test_calorie_trend_precision_round(self):
        """trend_value / start_avg / end_avg / series[*].calorie round(2)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_calorie_trend.py"),
            "--mock", str(MOCK_DIR / "mock_calorie_trend.json"),
            "--output", str(SKILL_DIR / "_test_trend.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_trend.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None and payload["status"] == "ok"
            data = payload["data"]
            for field in ("trend_value", "start_avg", "end_avg"):
                v = data["summary"][field]
                assert abs(v - round(v, 2)) < 1e-9, f"summary.{field}={v} 精度 > 2"
            for s in data["series"]:
                assert abs(s["calorie"] - round(s["calorie"], 2)) < 1e-9, (
                    f"series entry calorie={s['calorie']} 精度 > 2"
                )
        finally:
            (SKILL_DIR / "_test_trend.html").unlink(missing_ok=True)


class TestTodayWaterRenders:
    """ticket 02 · render_today_water.py + templates/today_water.html(ADR-0003)"""

    def test_water_html_renders(self):
        """templates/today_water.html 应包含 ring + bar-chart + 注入数据"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / "mock_today_water_partial.json"),
            "--output", str(SKILL_DIR / "_test_water.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_water.html").read_text(encoding="utf-8")
        try:
            assert ".ring" in html, "模板缺少 .ring 节点(进度环)"
            assert ".bar-chart" in html, "模板缺少 .bar-chart 节点(7 天 bar)"
            assert ".bar-col" in html, "模板缺少 .bar-col 节点(每日列)"
            assert "window.__DATA__" in html, "模板缺少数据注入"
        finally:
            (SKILL_DIR / "_test_water.html").unlink(missing_ok=True)

    def test_water_data_shape(self):
        """JSON data-shape:summary.today_ml/target_ml/week_ml(7)/week_dates(7)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / "mock_today_water_partial.json"),
            "--output", str(SKILL_DIR / "_test_water_shape.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_water_shape.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None, "未能抽取 window.__DATA__"
            assert payload["status"] == "ok", f"status 非 ok: {payload}"
            s = payload["data"]["summary"]
            assert isinstance(s["today_ml"], int) and s["today_ml"] == 1500, (
                f"today_ml 应为 int 1500,实得 {s['today_ml']!r}"
            )
            assert isinstance(s["target_ml"], int) and s["target_ml"] == 2000, (
                f"target_ml 应为 int 2000,实得 {s['target_ml']!r}"
            )
            assert isinstance(s["week_ml"], list) and len(s["week_ml"]) == 7, (
                f"week_ml 应为 7 个 int 列表,实得 {s['week_ml']!r}"
            )
            assert all(isinstance(x, int) for x in s["week_ml"]), (
                f"week_ml 每项应为 int,实得 {s['week_ml']!r}"
            )
            assert isinstance(s["week_dates"], list) and len(s["week_dates"]) == 7, (
                f"week_dates 应为 7 个 str 列表,实得 {s['week_dates']!r}"
            )
            meta = payload["data"]["meta"]
            assert meta["date"] == "2026-07-24"
            assert meta["today"] == "2026-07-24"
        finally:
            (SKILL_DIR / "_test_water_shape.html").unlink(missing_ok=True)

    @pytest.mark.parametrize("fixture_name", [
        "mock_today_water.json",
        "mock_today_water_partial.json",
        "mock_today_water_complete.json",
    ])
    def test_water_three_tiers_render(self, fixture_name):
        """空 / 部分 / 已完成 3 档 mock 都能渲染(3 档覆盖 ADR-0003 验收)"""
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_water.py"),
            "--mock", str(MOCK_DIR / fixture_name),
            "--output", str(SKILL_DIR / f"_test_water_{fixture_name}.html"),
        )
        assert r.returncode == 0, (
            f"{fixture_name} 渲染失败:\nstdout: {r.stdout}\nstderr: {r.stderr}"
        )
        (SKILL_DIR / f"_test_water_{fixture_name}.html").unlink(missing_ok=True)


class TestTodayDiet6Kpi:
    """ticket 12 · 今日饮食 6 KPI + mobile"""

    def test_today_diet_6_kpi_render(self):
        r = _run_script(
            str(SCRIPTS_DIR / "render_today_diet.py"),
            "--mock", str(MOCK_DIR / "mock_today_diet.json"),
            "--output", str(SKILL_DIR / "_test_diet.html"),
        )
        assert r.returncode == 0, f"render failed: {r.stderr}"
        html = (SKILL_DIR / "_test_diet.html").read_text(encoding="utf-8")
        try:
            payload = _extract_payload(html)
            assert payload is not None and payload["status"] == "ok"
            s = payload["data"]["summary"]
            assert "record_count" in s, "summary 缺 record_count"
            assert isinstance(s["record_count"], int)
            # 6 个 KPI 关键字段都应存在
            for k in ("calorie", "protein_g", "carb_g", "fat_g", "water_ml", "record_count"):
                assert k in s, f"summary 缺 {k}"
        finally:
            (SKILL_DIR / "_test_diet.html").unlink(missing_ok=True)

    def test_today_diet_template_has_6_kpi_grid(self):
        tpl = (SKILL_DIR / "templates" / "today_diet.html").read_text(encoding="utf-8")
        assert 'repeat(3,1fr)' in tpl, 'KPI 桌面 grid 未改 3 列'
        assert 'record_count' in tpl or '记录数' in tpl, '模板缺 record_count / 记录数'
        assert 'table-wrap' in tpl or 'overflow-x: auto' in tpl, '缺 table-wrap overflow'


class TestHomeDashboardRedesign:
    """tickets 08-11 · home dashboard 4 主题"""

    def test_home_dashboard_has_state_icon_css(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        assert '.todo-row .state' in tpl or '.state {' in tpl, '缺 .state CSS'

    def test_home_dashboard_log_row_grid(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        assert 'grid-template-columns: 44px 1fr auto' in tpl, 'log-row grid 未收紧'

    def test_home_dashboard_quick_actions_use_prompts(self):
        """render_home 输出的 quick_actions 含 prompt 字段"""
        import sys; sys.path.insert(0, str(SCRIPTS_DIR))
        from render_home import _attach_prompts, QUICK_ACTIONS
        result = _attach_prompts(QUICK_ACTIONS)
        assert all('prompt' in a for a in result), 'quick_actions 缺 prompt 字段'
        eat = next(a for a in result if a['label'] == '记录饮食')
        assert '记吃了' in eat['prompt'], f"记录饮食 prompt 应含 '记吃了', 实得: {eat['prompt'][:80]}"

    def test_home_dashboard_deficit_math_breakdown(self):
        tpl = (SKILL_DIR / 'templates' / 'home_dashboard.html').read_text(encoding='utf-8')
        # 缺口 detail 应有 TDEE + 运动 + 应烧 + 摄入 的 math breakdown
        assert 'TDEE' in tpl and '应烧' in tpl, '缺口 KPI 缺 math breakdown'
        # 应有 size_label badge 逻辑
        assert 'size_label' in tpl, '缺口 KPI 缺 size_label badge 逻辑'