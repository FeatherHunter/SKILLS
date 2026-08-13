# -*- coding: utf-8 -*-
"""tests/test_base_pipeline.py — Base 管线守卫测试(#314 task ① · 2026-08-13)

对齐公共组件/README §5 验收清单 + 饼干 #300 守卫范式:
  1. 72 个业务模板:3 占位符(INJECT-DATA / SHARED-HELPERS / SHARED-CSS)各恰好 1 个
  2. 注入后:占位符 0 残留(输出为真实页面)
  3. 缺占位符:渲染失败(硬拦截)
  4. 每个业务模板挂 Base actionBar(复制数据/日志按钮唯一来源),旧静态按钮已删除
  5. 自研复制/toast 实现已删除(showToast/doCopy/fallbackCopy/execCommand/navigator.clipboard)
  6. payload 信封:data.meta + data.scene.snapshot + data.copy_log
  7. BOM 契约:输出 utf-8-sig
  help_center.html 豁免(走 task ④ #316,本波不碰)。
  业务模板口径: templates/ 下含 INJECT-DATA 的模板 − help_center.html = 72
  (#291 盘点「73 业务模板」含 help_center,本波豁免,见 #314 偏离记录)。
"""

from __future__ import annotations

import json
import os
import re
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

PLACEHOLDERS = ("<!--INJECT-DATA-->", "<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->")

SELF_MADE_MARKERS = (
    "function showToast", "function doCopy", "function flashCopied",
    "function fallbackCopy", "function toast", "function copyData",
    "function copyLog", "function buildDataText", "function buildLogText",
    "function doCopyText", "function copyText2", "function doCopyStd",
    "execCommand", "navigator.clipboard", "window.__DATA__",
)


def _template_text(rel: str) -> str:
    return (TEMPLATES_DIR / rel).read_text(encoding="utf-8")


# ── 1. 72 业务模板:3 占位符各恰 1 ─────────────────────────────────────────────

class TestPlaceholders:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_has_three_placeholders_exactly_once(self, rel):
        text = _template_text(rel)
        for ph in PLACEHOLDERS:
            assert text.count(ph) == 1, f"{rel} 的 {ph} 应恰好 1 个,实际 {text.count(ph)} 个"

    def test_business_template_count_is_72(self):
        assert len(BUSINESS_TEMPLATES) == 72, \
            f"业务模板应为 72 个,实际 {len(BUSINESS_TEMPLATES)}:{BUSINESS_TEMPLATES}"

    def test_help_template_exempted(self):
        assert "help_center.html" not in BUSINESS_TEMPLATES


# ── 8. HELP: scene-data 契约 v1 转换层 + Base 参数化渲染(#316 task ④) ─────────

class TestHelpParameterized:
    """#316 · HELP 归一化: _triggers.py 唯一权威 → 契约 v1 → Base help_template"""

    def test_build_contract_passes_validation(self):
        from render_help_center import build_contract, _base_injector
        contract = build_contract()
        mod = _base_injector()
        ok, msg = mod.validate_help_data(contract)
        assert ok, f"转换层产物未过 scene-data 契约 v1: {msg}"
        assert contract["skill_name"] == "卡路里"
        assert len(contract["groups"]) == 10, "技能协同 36 条不迁入 → 10 分组"
        total = sum(len(sg["scenes"]) for g in contract["groups"] for sg in g["subgroups"])
        assert total == 436, f"场景数零丢失(_triggers 436 全进), 实际 {total}"
        ids = [s["id"] for g in contract["groups"]
               for sg in g["subgroups"] for s in sg["scenes"]]
        assert len(ids) == len(set(ids)), "场景 id 重复"

    def test_help_center_template_retired(self):
        """自研 help_center.html 已退役(#316); 渲染走 Base help_template"""
        assert not (TEMPLATES_DIR / "help_center.html").exists(), \
            "templates/help_center.html 应已退役删除(#316)"

    def test_render_help_timestamp_copy_no_residual(self, tmp_path):
        """时间戳副本产出 + 占位符 0 残留 + Base 资产注入(DB 隔离)"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_help_center.py"), "--no-mirror"],
            cwd=SKILL_DIR, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90, env=env,
        )
        assert r.returncode == 0, f"render_help_center 失败: {r.stderr}"
        out = list((tmp_path / "calorie_html").glob("卡路里_HELP_*.html"))
        assert out, "时间戳副本必写"
        h = out[-1].read_text(encoding="utf-8")
        for ph in PLACEHOLDERS:
            assert ph not in h, f"HELP 注入后仍有占位符残留: {ph}"
        assert "function copyText" in h, "HELP 产物缺 base.js"
        assert 'id="help-data"' in h, "HELP 产物缺 scene-data 契约注入点"


# ── 2. 注入后:占位符 0 残留(渲染脚本全链路输出真实页面) ──────────────────────

class TestInjectionNoResidual:
    """代表脚本端到端跑一遍 → 输出 0 占位符残留 + BOM"""

    def _run(self, tmp_db_dir, script, args, out_name):
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_db_dir / "guard_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / out_name
        full = [sys.executable, str(SCRIPTS_DIR / script)] + args + ["--output", str(out_path)]
        r = subprocess.run(full, capture_output=True, timeout=90, env=env)
        assert r.returncode == 0, f"{script} {args} 失败: {(r.stderr or r.stdout).decode('utf-8', errors='replace')[:400]}"
        return out_path.read_bytes()

    def _assert_clean(self, raw, label):
        text = raw.decode("utf-8-sig")
        assert raw[:3] == b"\xef\xbb\xbf", f"{label} 缺 BOM"
        for ph in PLACEHOLDERS:
            assert ph not in text, f"{label} 注入后仍有占位符残留: {ph}"

    def _seed_db(self, tmp_path):
        from db import init_db
        db_file = tmp_path / "calorie_data.db"
        init_db(str(db_file))
        return tmp_path

    def test_home_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_home.py",
                        ["--section", "diet", "--chain", "1.读DB→2.渲染"],
                        "home.html")
        self._assert_clean(raw, "render_home")

    def test_today_diet_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_today_diet.py",
                        ["--date", "2026-08-13"], "diet.html")
        self._assert_clean(raw, "render_today_diet")

    def test_today_water_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_today_water.py",
                        ["--date", "2026-08-13"], "water.html")
        self._assert_clean(raw, "render_today_water")

    def test_weight_history_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_weight_history.py", [], "wh.html")
        self._assert_clean(raw, "render_weight_history")

    def test_weight_dashboard_inject_no_residual(self, tmp_path):
        seed = self._seed_db(tmp_path)
        import sqlite3
        conn = sqlite3.connect(str(seed / "calorie_data.db"))
        conn.execute(
            "INSERT INTO weight_log (date, time, weight_kg) VALUES ('2026-08-13', '08:00', 70.0)")
        conn.commit()
        conn.close()
        raw = self._run(seed, "render_weight_dashboard.py",
                        ["--chain", "1.识别→2.读DB→3.渲染"], "wd.html")
        self._assert_clean(raw, "render_weight_dashboard")

    def test_exercise_summary_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_exercise_summary.py",
                        ["--today", "--chain", "1.识别→2.读DB→3.渲染"], "es.html")
        self._assert_clean(raw, "render_exercise_summary")

    def test_goal_weight_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_goal_weight.py",
                        ["--mode", "basic", "--chain", "1.识别→2.读DB→3.渲染"], "gw.html")
        self._assert_clean(raw, "render_goal_weight")

    def test_body_composition_view_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_body_composition_view.py",
                        ["--mode", "list", "--chain", "1.读DB→2.渲染"], "bc.html")
        self._assert_clean(raw, "render_body_composition_view")

    def test_body_photo_log_wizard_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_body_photo_log_wizard.py",
                        [], "bpw.html")
        self._assert_clean(raw, "render_body_photo_log_wizard")

    def test_food_library_inject_no_residual(self, tmp_path):
        raw = self._run(self._seed_db(tmp_path), "render_food_library.py",
                        ["--limit", "5"], "fl.html")
        self._assert_clean(raw, "render_food_library")


# ── 3. 缺占位符:渲染失败(硬拦截) ─────────────────────────────────────────────

class TestHardBlock:
    def test_missing_placeholder_render_fails(self):
        from _base_render import inject_base
        tmpl = _template_text("today_diet.html")
        broken = tmpl.replace("<!--SHARED-HELPERS-->", "", 1)
        payload = {"status": "ok", "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}}}
        with pytest.raises(RuntimeError, match="SHARED-HELPERS"):
            inject_base(broken, payload)

    def test_duplicate_placeholder_render_fails(self):
        from _base_render import inject_base
        tmpl = _template_text("today_diet.html")
        broken = tmpl.replace("<!--SHARED-CSS-->", "<!--SHARED-CSS--><!--SHARED-CSS-->", 1)
        payload = {"status": "ok", "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}}}
        with pytest.raises(RuntimeError, match="SHARED-CSS"):
            inject_base(broken, payload)

    def test_missing_inject_data_render_fails(self):
        from _base_render import inject_base
        tmpl = _template_text("today_diet.html")
        broken = tmpl.replace("<!--INJECT-DATA-->", "", 1)
        payload = {"status": "ok", "data": {"meta": {"command_cn": "测试", "occurred_at": "now"}}}
        with pytest.raises(RuntimeError, match="INJECT-DATA"):
            inject_base(broken, payload)


# ── 4. 每个业务模板含复制数据 + 复制日志按钮(Base actionBar) ─────────────────

class TestCopyButtons:
    # error_receipt.html 例外: 波② #315 改用 Base errorReceipt 控件(自带修正重试+复制数据/日志),
    # 不再挂 actionBar(避免与控件复制按钮重复); 其余模板仍走 actionBar。
    ERROR_RECEIPT_TEMPLATE = "error_receipt.html"

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_uses_base_actionbar(self, rel):
        if rel == self.ERROR_RECEIPT_TEMPLATE:
            pytest.skip("error_receipt.html 用 Base errorReceipt 控件自带复制按钮(#315 波②)")
        text = _template_text(rel)
        assert "actionBar" in text, f"{rel} 未使用 Base actionBar(复制按钮必须走 Base 控件)"
        assert "actionbar-zone" in text, f"{rel} 缺 actionBar 挂载区"

    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_static_copy_buttons_remain(self, rel):
        text = _template_text(rel)
        assert 'id="copyDataBtn"' not in text, f"{rel} 仍有旧复制数据按钮"
        assert 'id="copyLogBtn"' not in text, f"{rel} 仍有旧复制日志按钮"
        assert 'id="copyBtn"' not in text, f"{rel} 仍有旧复制按钮"

    def test_rendered_outputs_contain_copy_buttons(self, tmp_path):
        from db import init_db
        db_file = tmp_path / "calorie_data.db"
        init_db(str(db_file))
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_path / "copybtn_out"
        out_dir.mkdir(exist_ok=True)
        cases = [
            ("render_home.py", ["--section", "diet", "--chain", "1.识别→2.读DB→3.渲染"]),
            ("render_today_diet.py", ["--date", "2026-08-13"]),
            ("render_weight_history.py", []),
            ("render_goal_weight.py", ["--mode", "basic", "--chain", "1.识别→2.读DB→3.渲染"]),
        ]
        for i, (script, args) in enumerate(cases):
            out_path = out_dir / f"c{i}.html"
            full = [sys.executable, str(SCRIPTS_DIR / script)] + args + ["--output", str(out_path)]
            r = subprocess.run(full, capture_output=True, timeout=90, env=env)
            assert r.returncode == 0, f"{script} {args} 失败: {(r.stderr or r.stdout).decode('utf-8', errors='replace')[:300]}"
            text = out_path.read_text(encoding="utf-8-sig")
            assert "复制数据" in text, f"{script} {args} 输出缺「复制数据」按钮"
            assert "复制日志" in text, f"{script} {args} 输出缺「复制日志」按钮"
            assert "function copyText" in text, f"{script} {args} 输出缺 Base copyText(base.js 未注入)"


# ── 5. 自研复制/toast 实现已删除 ──────────────────────────────────────────────

class TestSelfMadeRemoved:
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_no_self_made_copy_toast_impl(self, rel):
        text = _template_text(rel)
        for marker in SELF_MADE_MARKERS:
            assert marker not in text, f"{rel} 仍有自研复制/toast 实现残留: {marker}"


# ── 6. payload 信封(渲染脚本输出) ────────────────────────────────────────────

class TestEnvelope:
    def test_query_payload_envelope(self, tmp_path):
        from db import init_db
        db_file = tmp_path / "calorie_data.db"
        init_db(str(db_file))
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out = tmp_path / "env.html"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_today_diet.py"), "--date", "2026-08-13",
             "--output", str(out)],
            capture_output=True, timeout=90, env=env,
        )
        assert r.returncode == 0, r.stderr
        text = out.read_text(encoding="utf-8-sig")
        m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
        payload = json.loads(m.group(1))
        assert payload["status"] == "ok"
        meta = payload["data"]["meta"]
        assert meta["command_cn"] and meta["occurred_at"]
        assert meta.get("skill_name") == "卡路里"
        scene = payload["data"]["scene"]
        snap = scene["snapshot"]
        assert snap["title"] and isinstance(snap["summary"], list)
        assert isinstance(snap["sections"], list)
        assert "copy_log" in payload["data"]

    def test_error_payload_has_snapshot(self):
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


# ── 8. 图表(#317 task ③):CHARTS-HELPERS 0/1 + 注入后 charts.js 就位 ─────────

CHART_TEMPLATES = sorted(
    str(p.relative_to(TEMPLATES_DIR)).replace("\\", "/")
    for p in TEMPLATES_DIR.rglob("*.html")
    if "CHARTS-HELPERS" in p.read_text(encoding="utf-8")
)


class TestChartPlaceholder:
    def test_chart_template_list(self):
        """25 个图表模板全部声明 CHARTS-HELPERS(实盘盘点 25 模板 31 处 SVG, 全迁)"""
        assert len(CHART_TEMPLATES) == 25, (
            f"图表模板应为 25 个,实际 {len(CHART_TEMPLATES)}:{CHART_TEMPLATES}"
        )

    @pytest.mark.parametrize("rel", CHART_TEMPLATES)
    def test_chart_placeholder_exactly_once(self, rel):
        assert _template_text(rel).count("<!--CHARTS-HELPERS-->") == 1

    def test_no_svg_left_in_chart_templates(self):
        """迁移后 25 个图表模板零 <svg>(自绘 SVG 全退役)"""
        for rel in CHART_TEMPLATES:
            assert "<svg" not in _template_text(rel), f"{rel} 仍有自绘 <svg>"

    def test_charts_loaded_for_chart_templates(self, tmp_path):
        """含 CHARTS-HELPERS 的模板经 inject_base 后注入 charts.js 且占位符 0 残留"""
        from db import init_db
        init_db(str(tmp_path / "calorie_data.db"))
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_path)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_path / "chart_out"
        out_dir.mkdir(exist_ok=True)
        cases = [
            ("render_weight_history.py", []),
            ("render_today_diet.py", ["--date", "2026-08-13"]),
            ("render_today_water.py", []),
            ("render_exercise_summary.py", ["--chain", "1.识别→2.读DB→3.渲染"]),
        ]
        for i, (script, args) in enumerate(cases):
            out_path = out_dir / f"c{i}.html"
            full = [sys.executable, str(SCRIPTS_DIR / script)] + args + ["--output", str(out_path)]
            r = subprocess.run(full, capture_output=True, timeout=90, env=env)
            assert r.returncode == 0, f"{script} 失败: {(r.stderr or r.stdout).decode('utf-8', errors='replace')[:300]}"
            text = out_path.read_text(encoding="utf-8-sig")
            assert "<!--CHARTS-HELPERS-->" not in text, f"{script} 输出仍有 CHARTS-HELPERS 占位符残留"
            assert "window.charts=" in text or "__chartsLoaded" in text, (
                f"{script} 输出缺 charts.js(charts 资产未注入)"
            )

    def test_charts_not_injected_without_placeholder(self, tmp_path):
        """不含 CHARTS-HELPERS 的模板不注入 charts.js(占位符 0/1 契约)"""
        from _base_render import inject_base
        html = "<html><body><!--INJECT-DATA--></body></html>"
        payload = {
            "status": "ok",
            "data": {
                "meta": {"command_cn": "测试", "occurred_at": "2026-08-13"},
                "scene": {"snapshot": {"title": "t", "summary": [], "sections": []}},
            },
        }
        out, err = None, None
        # 直接构造无 CHARTS 占位符的模板 → 注入器不注入 charts
        import injector
        base_js = (Path(__file__).resolve().parent.parent.parent / "公共组件" / "assets" / "base.js").read_text(encoding="utf-8")
        base_css = (Path(__file__).resolve().parent.parent.parent / "公共组件" / "assets" / "base.css").read_text(encoding="utf-8")
        # 手动替换占位符验证 0/1: 不含 CHARTS-HELPERS → charts_asset=None
        tpl = "<html><body><!--INJECT-DATA--><!--SHARED-HELPERS--><!--SHARED-CSS--></body></html>"
        html2, err2 = injector.inject(tpl, payload, js_asset=base_js, css_asset=base_css, charts_asset=None, strict=False)
        assert err2 is None
        assert "__chartsLoaded" not in html2, "无占位符模板不应注入 charts.js"
