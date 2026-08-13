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
    @pytest.mark.parametrize("rel", BUSINESS_TEMPLATES)
    def test_each_business_template_uses_base_actionbar(self, rel):
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
