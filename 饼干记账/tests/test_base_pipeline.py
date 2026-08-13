# -*- coding: utf-8 -*-
"""tests/test_base_pipeline.py — Base 管线守卫测试(#300 task ① · 2026-08-13)

对齐公共组件/README §5 验收清单 + #269 试点守卫范式:
  1. 24 个业务模板:3 占位符(INJECT-DATA / SHARED-HELPERS / SHARED-CSS)各恰好 1 个
  2. 注入后:占位符 0 残留(输出为真实页面)
  3. 缺占位符:渲染失败(硬拦截)
  4. 每个业务模板含「复制数据」+「复制日志」按钮(Base actionBar)
  5. 自研复制/toast 实现已删除(doCopy/buildData5/toastFmt/sheetMask)
  6. payload 信封:data.meta + data.scene.snapshot + data.copy_log
  7. BOM 契约:输出 utf-8-sig
  help.html 豁免(走 task ④ #303,本波不碰)。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

TEMPLATES_DIR = SKILL_DIR / "templates"

# 24 个业务模板(help.html 除外 → task ④)
BUSINESS_TEMPLATES = sorted(
    str(p.relative_to(TEMPLATES_DIR)).replace("\\", "/")
    for p in TEMPLATES_DIR.rglob("*.html")
    if p.name not in ("help.html", "help.html.bak.v2.4")
)

PLACEHOLDERS = ("<!--INJECT-DATA-->", "<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->")


def _template_text(rel: str) -> str:
    return (TEMPLATES_DIR / rel).read_text(encoding="utf-8")


# ── 1. 24 业务模板:3 占位符各恰 1 ─────────────────────────────────────────────

class TestPlaceholders:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_has_three_placeholders_exactly_once(self, rel):
        text = _template_text(rel)
        for ph in PLACEHOLDERS:
            assert text.count(ph) == 1, f"{rel} 的 {ph} 应恰好 1 个,实际 {text.count(ph)} 个"

    def test_business_template_count_is_24(self):
        assert len(BUSINESS_TEMPLATES) == 24, \
            f"业务模板应为 24 个,实际 {len(BUSINESS_TEMPLATES)}:{BUSINESS_TEMPLATES}"

    def test_help_template_exempted(self):
        """help.html 不包含在业务模板清单(走 task ④)"""
        assert "help.html" not in BUSINESS_TEMPLATES


# ── 1.5 CHARTS-HELPERS 占位符(0 或 1 · #302 task ③) ────────────────────────

CHARTS_HELPERS = "<!--CHARTS-HELPERS-->"
CHART_TEMPLATES = ("query_view.html", "分析/analysis_view.html")


class TestChartsPlaceholder:
    @pytest.mark.parametrize("rel", CHART_TEMPLATES)
    def test_chart_templates_have_charts_placeholder_exactly_once(self, rel):
        text = _template_text(rel)
        assert text.count(CHARTS_HELPERS) == 1, \
            f"{rel} 的 {CHARTS_HELPERS} 应恰好 1 个,实际 {text.count(CHARTS_HELPERS)} 个"

    @pytest.mark.parametrize("rel", sorted(set(BUSINESS_TEMPLATES) - set(CHART_TEMPLATES)))
    def test_non_chart_templates_have_zero_charts_placeholder(self, rel):
        text = _template_text(rel)
        assert CHARTS_HELPERS not in text, \
            f"{rel} 不应含 {CHARTS_HELPERS}(非图表模板为 0)"

    def test_chart_template_output_injects_charts_js(self, seeded_db):
        """图表模板注入后:CHARTS 0 残留 + charts.js(window.charts)存在"""
        import os
        import subprocess
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(seeded_db)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = seeded_db / "charts_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        cases = [
            ("bill_inject.py", ["breakdown"], "query_view"),
            ("bill_inject.py", ["trend", "--months", "6"], "analysis_view"),
        ]
        for script, args, _tmpl in cases:
            out_path = out_dir / f"c-{args[0]}.html"
            full = [sys.executable, str(SCRIPTS_DIR.joinpath(*script.split("/")))] + args + ["--out", str(out_path)]
            r = subprocess.run(full, capture_output=True, text=True, encoding="utf-8",
                               env=env, timeout=60)
            assert r.returncode == 0, f"{script} {args} 失败: {r.stderr}"
            text = out_path.read_text(encoding="utf-8-sig")
            assert CHARTS_HELPERS not in text, f"{args} 注入后 CHARTS-HELPERS 应有 0 残留"
            assert "window.charts" in text, f"{args} 输出缺 charts.js(window.charts)"

    def test_non_chart_template_output_has_no_charts_js(self, seeded_db):
        """非图表模板(写入域)注入后:不含 charts.js(CHARTS 为 0 不注入)"""
        import os
        import subprocess
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(seeded_db)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = seeded_db / "charts_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "write.html"
        full = [sys.executable, str(SCRIPTS_DIR / "render_write.py"), "expense",
                "--amount", "35", "--out", str(out_path)]
        r = subprocess.run(full, capture_output=True, text=True, encoding="utf-8",
                           env=env, timeout=60)
        assert r.returncode == 0, r.stderr
        text = out_path.read_text(encoding="utf-8-sig")
        assert "window.charts" not in text, "非图表模板不应注入 charts.js"

    def test_duplicate_charts_placeholder_render_fails(self):
        """CHARTS 占位符 ×2 → 注入器硬拦截报错(契约 CHARTS ≤1)"""
        from _base_render import inject_base
        tmpl = _template_text("query_view.html")
        broken = tmpl.replace(CHARTS_HELPERS, CHARTS_HELPERS + CHARTS_HELPERS, 1)
        payload = {
            "status": "ok",
            "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}},
        }
        with pytest.raises(RuntimeError, match="CHARTS-HELPERS"):
            inject_base(broken, payload)


# ── 2. 注入后:占位符 0 残留(渲染脚本全链路输出真实页面) ──────────────────────

class TestInjectionNoResidual:
    """每个渲染脚本端到端跑一遍 → 输出 0 占位符残留 + BOM"""

    def _run(self, tmp_db_dir, cmd, out_name):
        import os
        import subprocess
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out = tmp_db_dir / "guard_out"
        out.mkdir(parents=True, exist_ok=True)
        out_path = out / out_name
        script = SCRIPTS_DIR.joinpath(*cmd[0].split("/"))
        full = [sys.executable, str(script)] + cmd[1:] + ["--out", str(out_path)]
        r = subprocess.run(full, capture_output=True, text=True, encoding="utf-8",
                           env=env, timeout=60)
        assert r.returncode == 0, f"{cmd} 失败: {r.stderr}\n{r.stdout}"
        return out_path.read_bytes()

    def test_query_analysis_inject_no_residual(self, seeded_db):
        raw = self._run(seeded_db, ["bill_inject.py", "summary"], "s1.html")
        text = raw.decode("utf-8-sig")
        assert raw[:3] == b"\xef\xbb\xbf", "summary 缺 BOM"
        for ph in PLACEHOLDERS:
            assert ph not in text, f"summary 注入后仍有占位符残留: {ph}"
        raw2 = self._run(seeded_db, ["bill_inject.py", "monthly", "--month", "2026-08"], "m1.html")
        text2 = raw2.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text2, f"monthly 注入后仍有占位符残留: {ph}"

    def test_write_inject_no_residual(self, seeded_db):
        raw = self._run(seeded_db, ["render_write.py", "expense", "--amount", "35", "--category-hint", "午饭"], "w.html")
        text = raw.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text, f"render_write 注入后仍有占位符残留: {ph}"

    def test_account_inject_no_residual(self, seeded_db):
        raw = self._run(seeded_db, ["account/render.py", "view"], "a.html")
        text = raw.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text, f"account/render 注入后仍有占位符残留: {ph}"

    def test_goal_inject_no_residual(self, seeded_db):
        raw = self._run(seeded_db, ["goal/render.py", "budget"], "g.html")
        text = raw.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text, f"goal/render 注入后仍有占位符残留: {ph}"

    def test_setup_inject_no_residual(self, tmp_db_dir):
        raw = self._run(tmp_db_dir, ["setup/render.py", "init-status"], "s.html")
        text = raw.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text, f"setup/render 注入后仍有占位符残留: {ph}"

    def test_link_form_inject_no_residual(self, seeded_db):
        raw = self._run(seeded_db, ["link/cli.py", "form", "purchase", "--amount", "199", "--item", "空气炸锅"], "l.html")
        text = raw.decode("utf-8-sig")
        for ph in PLACEHOLDERS:
            assert ph not in text, f"link/cli 注入后仍有占位符残留: {ph}"


# ── 3. 缺占位符:渲染失败(硬拦截) ─────────────────────────────────────────────

class TestHardBlock:
    def test_missing_placeholder_render_fails(self):
        from _base_render import inject_base
        tmpl = _template_text("query_view.html")
        broken = tmpl.replace("<!--SHARED-HELPERS-->", "", 1)
        payload = {
            "status": "ok",
            "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}},
        }
        with pytest.raises(RuntimeError, match="SHARED-HELPERS"):
            inject_base(broken, payload)

    def test_duplicate_placeholder_render_fails(self):
        from _base_render import inject_base
        tmpl = _template_text("query_view.html")
        broken = tmpl.replace("<!--SHARED-CSS-->", "<!--SHARED-CSS--><!--SHARED-CSS-->", 1)
        payload = {
            "status": "ok",
            "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}},
        }
        with pytest.raises(RuntimeError, match="SHARED-CSS"):
            inject_base(broken, payload)


# ── 4. 每个业务模板含复制数据 + 复制日志按钮 ─────────────────────────────────

class TestCopyButtons:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_uses_base_actionbar(self, rel):
        """每个业务模板挂 Base actionBar 控件(复制数据/日志按钮的唯一来源)"""
        text = _template_text(rel)
        assert "actionBar" in text, f"{rel} 未使用 Base actionBar(复制按钮必须走 Base 控件)"
        assert "actionbar-zone" in text, f"{rel} 缺 actionBar 挂载区"

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_static_copy_buttons_remain(self, rel):
        """旧静态按钮(id=copyDataBtn/copyLogBtn)已删除,防止绕过 Base 走老路"""
        text = _template_text(rel)
        assert 'id="copyDataBtn"' not in text, f"{rel} 仍有旧复制数据按钮"
        assert 'id="copyLogBtn"' not in text, f"{rel} 仍有旧复制日志按钮"

    def test_rendered_outputs_contain_copy_buttons(self, seeded_db):
        """渲染输出(真实页面)必含「复制数据」+「复制日志」按钮(#269 遗漏教训)"""
        import os
        import subprocess
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(seeded_db)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = seeded_db / "copybtn_out"
        out_dir.mkdir(exist_ok=True)
        cases = [
            ("bill_inject.py", ["summary"]),
            ("bill_inject.py", ["monthly"]),
            ("render_write.py", ["expense", "--amount", "35"]),
            ("account/render.py", ["view"]),
            ("goal/render.py", ["budget"]),
            ("setup/render.py", ["init-status"]),
            ("link/cli.py", ["form", "meal", "--amount", "35", "--ate", "午饭"]),
        ]
        for i, (script, args) in enumerate(cases):
            out_path = out_dir / f"c{i}.html"
            full = [sys.executable, str(SCRIPTS_DIR.joinpath(*script.split("/")))] + args + ["--out", str(out_path)]
            r = subprocess.run(full, capture_output=True, text=True, encoding="utf-8",
                               env=env, timeout=60)
            assert r.returncode == 0, f"{script} {args} 失败: {r.stderr}"
            text = out_path.read_text(encoding="utf-8-sig")
            assert "复制数据" in text, f"{script} {args} 输出缺「复制数据」按钮"
            assert "复制日志" in text, f"{script} {args} 输出缺「复制日志」按钮"
            assert "function copyText" in text, f"{script} {args} 输出缺 Base copyText(base.js 未注入)"


# ── 5. 自研复制/toast 实现已删除 ──────────────────────────────────────────────

SELF_MADE_MARKERS = (
    "function doCopy", "function fallbackCopy", "function buildData5",
    "function showToast", "toastFmt", "sheetMask", "function buildDataText",
    "function buildLogText", "window.buildDataText =",
)


class TestSelfMadeRemoved:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_self_made_copy_toast_impl(self, rel):
        text = _template_text(rel)
        for marker in SELF_MADE_MARKERS:
            assert marker not in text, f"{rel} 仍有自研复制/toast 实现残留: {marker}"


# ── 6. payload 信封(渲染脚本输出) ────────────────────────────────────────────

class TestEnvelope:
    def test_query_payload_envelope(self, tmp_db_dir):
        import os
        import subprocess
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out = tmp_db_dir / "env.html"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bill_inject.py"), "summary", "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
        )
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8-sig")
        m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
        payload = json.loads(m.group(1))
        assert payload["status"] == "ok"
        meta = payload["data"]["meta"]
        assert meta["command_cn"] and meta["occurred_at"]
        assert meta.get("skill_name") == "饼干记账"
        scene = payload["data"]["scene"]
        snap = scene["snapshot"]
        assert snap["title"] and isinstance(snap["summary"], list)
        assert isinstance(snap["sections"], list)
        assert "copy_log" in payload["data"]

    def test_error_payload_has_snapshot(self, tmp_db_dir):
        """错误页 payload 也带 scene.snapshot(复制数据/日志按钮可用)"""
        from _base_render import error_envelope
        p = error_envelope("测试错误")
        assert p["status"] == "error"
        assert p["data"]["scene"]["snapshot"]["summary"] == ["测试错误"]


# ── 7. BOM 契约(注入后输出 utf-8-sig) ────────────────────────────────────────

class TestBomAfterInjection:
    def test_write_html_writes_bom(self, tmp_path):
        from _base_render import write_html
        out = tmp_path / "x.html"
        write_html("<html>测试</html>", out)
        assert out.read_bytes()[:3] == b"\xef\xbb\xbf"


# ── 8. #301 状态层:自研状态样式零残留 + Base 三控件接入 ──────────────────────

SELF_MADE_STATE_MARKERS = (
    'class="error-card"', 'class="card empty"', 'class="empty"',
    "status-chip", 'class="badge', 'class="chip warn"', 'class="chip done"', 'class="chip active"',
    "empty-cand",
)


class TestStateLayer:
    """#301 task ② 守卫:状态层统一走 Base 三控件(emptyState/errorReceipt/statusBadge)

    对应 08 §6.1 三层反馈 + 空态 + 状态徽章:技能零自研状态样式副本。
    """

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_self_made_state_markers(self, rel):
        """24 模板无自研状态样式残留(防漏迁/防回退)"""
        text = _template_text(rel)
        for marker in SELF_MADE_STATE_MARKERS:
            assert marker not in text, f"{rel} 仍有自研状态样式残留: {marker}"

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_has_error_receipt(self, rel):
        """每个业务模板接入 Base errorReceipt(08 §6.1:错误不静默,可读可行动可反馈)"""
        text = _template_text(rel)
        assert "errorReceipt" in text, f"{rel} 未接入 Base errorReceipt(错误回执必达)"

    def test_view_templates_use_base_state_controls(self):
        """视图模板(查询/分析/账户/目标)状态层三控件齐备"""
        views = ("query_view.html", "分析/analysis_view.html", "账户/account_view.html",
                 "目标/budget_view.html", "目标/saving_view.html")
        for rel in views:
            text = _template_text(rel)
            assert "errorReceipt" in text, f"{rel} 缺 errorReceipt"
            assert "emptyState" in text, f"{rel} 缺 emptyState"

    def test_state_badges_use_base_status_badge(self):
        """状态徽章统一走 Base statusBadge(分析 chip / 账户 badge / 目标 status-chip)"""
        for rel in ("分析/analysis_view.html", "账户/account_view.html",
                    "目标/budget_view.html", "目标/saving_view.html"):
            text = _template_text(rel)
            assert "statusBadge" in text, f"{rel} 未接入 Base statusBadge"

    def test_error_envelope_injects_into_query_view(self, tmp_db_dir):
        """错误信封 payload 注入 query_view:输出含错误状态 + errorReceipt 调用(管线可用)"""
        from _base_render import error_envelope, inject_base
        tmpl = _template_text("query_view.html")
        p = error_envelope("测试错误: 数据库打不开")
        html = inject_base(tmpl, p)
        assert "errorReceipt" in html, "注入后错误回执 JS 应存在"
        assert '"status": "error"' in html, "注入后 payload 应带 error 状态"
        assert '"测试错误: 数据库打不开"' in html, "错误消息应进 payload(message)"
