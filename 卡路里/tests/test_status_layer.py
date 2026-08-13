# -*- coding: utf-8 -*-
"""tests/test_status_layer.py — 状态层守卫测试(#315 task ② · 2026-08-13)

对齐饼干 #301 守卫范式(1ca80f9):
  1. 自研状态样式零残留: pill/.empty/empty-card/empty-tip/empty-state/log-empty/
     st-ok/st-fail/st-skip/本地 statusBadge 定义 → 全部退役(Base 三控件接管)
  2. Base 三控件正向断言: 全业务模板接 errorReceipt(错误回执必达);
     空态模板接 emptyState; 状态徽章模板接 statusBadge
  3. error_receipt.html = Base errorReceipt 控件(data/log 字符串直传), 无自研实现
  4. 错误信封注入端到端: error_envelope → inject_base → 输出可渲染
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

TEMPLATES_DIR = SKILL_DIR / "templates"

BUSINESS_TEMPLATES = sorted(
    str(p.relative_to(TEMPLATES_DIR)).replace("\\", "/")
    for p in TEMPLATES_DIR.rglob("*.html")
    if p.name != "help_center.html" and "INJECT-DATA" in p.read_text(encoding="utf-8")
)

# 自研状态样式标记(全部退役, 防漏迁/防回退)
# 精确语义: 'class="pill '(带尾空格)命中带修饰的 pill(pill-good/warn/bad/info/自定义色),
# 不命中裸信息标签 <span class="pill">必走</span>(非状态语义, 视觉统一走公共层 ISSUE,
# 对齐饼干 #301 .chips 保留先例)与容器 class="pills"(纯布局)
SELF_MADE_STATE_MARKERS = (
    'class="pill ', "pill pill-", "pill-good", "pill-warn", "pill-bad", "pill-info",
    'class="empty"', "empty-card", "empty-tip", "empty-state", "log-empty",
    "st-ok", "st-fail", "st-skip",
    "function statusBadge",
)

# errorReceipt 豁免(全业务模板断言除外, 原因见注释)
ERROR_RECEIPT_EXEMPT = {
    "plan_builder_wizard.html": "#318 预存 bug(周视图 sIdx)归属, 状态层改造随 #318 修复一并做",
    "body_photo_log_wizard.html": "纯客户端交互向导, 不消费 payload 信封(payload script 在其主脚本之后), 无错误面",
}

# 状态徽章模板(含 pill 或 st-* 或 status 语义)→ 必须接 Base statusBadge
BADGE_TEMPLATES = (
    "lint_health.html",
    "body_photo_receipt.html",
    "crud_receipt.html",
    "weight_volatility_v2.html",
    "contraindication_report.html",
    "calorie_trend.html",
    "calorie_deficit.html",
    "nutrition_ratio.html",
    "today_diet.html",
    "today_water.html",
    "six_factors.html",
    "combined_analysis.html",
)

# 空态模板(含 .empty/暂无/empty-card 语义)→ 必须接 Base emptyState
EMPTY_TEMPLATES = (
    "food_search.html",
    "body_photo_gallery.html",
    "exercise_cardio.html",
    "exercise_strength.html",
    "exercise_recap.html",
    "exercise_trend.html",
    "contraindication_report.html",
    "weight_volatility_v2.html",
    "body_composition_view.html",
    "body_measurements_view.html",
    "cross_skill_sleep.html",
    "goal_progress.html",
    "exercise_goal_view.html",
    "weight_history.html",
    "home_dashboard.html",
)


def _template_text(rel: str) -> str:
    return (TEMPLATES_DIR / rel).read_text(encoding="utf-8")


# ── 1. 自研状态样式零残留 ───────────────────────────────────────────────────

class TestNoSelfMadeState:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_self_made_state_markers(self, rel):
        """全部业务模板无自研状态样式残留(对齐饼干 #301 反向断言)"""
        text = _template_text(rel)
        for marker in SELF_MADE_STATE_MARKERS:
            assert marker not in text, f"{rel} 仍有自研状态样式残留: {marker}"


# ── 2. Base 三控件正向接入 ──────────────────────────────────────────────────

class TestBaseStateControls:
    @pytest.mark.parametrize("rel", BADGE_TEMPLATES)
    def test_badge_templates_use_status_badge(self, rel):
        """状态徽章模板接入 Base statusBadge(ok/warn/danger/empty 白名单)"""
        text = _template_text(rel)
        assert "statusBadge" in text, f"{rel} 未接入 Base statusBadge"

    @pytest.mark.parametrize("rel", EMPTY_TEMPLATES)
    def test_empty_templates_use_empty_state(self, rel):
        """空态模板接入 Base emptyState"""
        text = _template_text(rel)
        assert "emptyState" in text, f"{rel} 未接入 Base emptyState"

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_has_error_receipt(self, rel):
        """每个业务模板接入 Base errorReceipt(08 §6.1:错误不静默,可读可行动可反馈)"""
        if rel in ERROR_RECEIPT_EXEMPT:
            pytest.skip(f"{rel}: {ERROR_RECEIPT_EXEMPT[rel]}")
        text = _template_text(rel)
        assert "errorReceipt" in text, f"{rel} 未接入 Base errorReceipt(错误回执必达)"


# ── 3. error_receipt.html = Base errorReceipt 控件(自研实现全废弃) ──────────

class TestErrorReceiptTemplate:
    def test_uses_base_error_receipt_control(self):
        """error_receipt.html 调用 Base errorReceipt 控件(data/log 字符串直传)"""
        text = _template_text("error_receipt.html")
        assert "window.errorReceipt(" in text, "error_receipt.html 未调用 Base errorReceipt 控件"
        assert "window.statusBadge" in text, "error_receipt.html 失败徽章未走 Base statusBadge"

    def test_no_self_built_error_ui_remains(self):
        """error_receipt.html 无自研错误 UI 残留(fail-banner/copy-bar/自研 toast)"""
        text = _template_text("error_receipt.html")
        for marker in ("fail-banner", "copy-bar", "copyFixBtn", "btn-fix"):
            assert marker not in text, f"error_receipt.html 仍有自研错误 UI 残留: {marker}"

    def test_error_envelope_injects_into_error_receipt(self):
        """错误信封 payload 注入 error_receipt:输出含错误状态 + 控件调用(管线可用)"""
        from _base_render import error_envelope, inject_base
        p = error_envelope("测试错误: 数据库打不开", command_cn="补记体脂")
        html = inject_base(_template_text("error_receipt.html"), p)
        assert "window.errorReceipt" in html, "注入后错误回执 JS 应存在"
        assert '"status": "error"' in html, "注入后 payload 应带 error 状态"
        assert "测试错误" in html, "错误消息应进 payload(message)"

    def test_render_error_receipt_script_end_to_end(self, tmp_path):
        """render_error_receipt.py 端到端:输出 0 占位符残留 + BOM"""
        out = tmp_path / "err.html"
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        env["SKILLS_BASE_DIR"] = str(TEMPLATES_DIR.parent.parent / "公共组件")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_error_receipt.py"),
             "--scene-name", "补记体脂", "--op", "补记体脂", "--reason", "同日重复写入需确认",
             "--data", '{"date":"2026-07-20"}', "--fix-prompt", "请覆盖记录", "--output", str(out)],
            capture_output=True, timeout=90, env=env,
        )
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8-sig")
        for ph in ("<!--INJECT-DATA-->", "<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->"):
            assert ph not in text, f"注入后仍有占位符残留: {ph}"
        assert out.read_bytes()[:3] == b"\xef\xbb\xbf", "输出应带 BOM(utf-8-sig)"
        assert "window.errorReceipt" in text, "输出缺 Base errorReceipt 控件"
