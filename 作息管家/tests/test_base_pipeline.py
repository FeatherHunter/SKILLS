# -*- coding: utf-8 -*-
"""作息管家 Base 管线守卫测试（#269 试点 · 漏迁即红）

覆盖:
- 全部 19 模板: INJECT-DATA / SHARED-HELPERS / SHARED-CSS 占位符恰 1（漏迁/重复 → 红）
- Base 资产注入完整性: 渲染产物含 base.js 函数 + base.css token
- 缺占位符渲染失败: 故意删占位符 → inject 抛错（守卫生效）
- 无生产库接触: 全部走临时目录/内存, 不设 SKILLS_DB_PATH 写生产
"""
import io
import os
import pathlib
import re
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))

TEMPLATES = sorted((SKILL_DIR / "templates").glob("*.html"))
PLACEHOLDERS = ["<!--INJECT-DATA-->", "<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->"]

# engine 薄壳模板的 INJECT-DATA 也必须是占位符形式（已迁移）
# help_center 特殊: INJECT-DATA 在 JS 赋值上下文, 但占位符个数仍须为 1


# ── 占位符契约（全部模板恰 1）────────────────────────────

@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda p: p.name)
def test_template_placeholders_exact_one(tpl):
    """每个模板的 3 个占位符必须恰 1（漏迁/重复 → 红）"""
    c = tpl.read_text(encoding="utf-8")
    for ph in PLACEHOLDERS:
        n = c.count(ph)
        assert n == 1, f"{tpl.name}: {ph} 应为 1 个, 实际 {n} 个（漏迁或重复）"


# ── 渲染产物 Base 注入完整性 ─────────────────────────────

def test_render_injects_base_assets(tmp_path, monkeypatch):
    """render_and_write 产物: base.js 函数 + base.css token + 占位符 0 残留"""
    from schedule_html_render import render_and_write

    out = tmp_path / "out.html"
    payload = {
        "status": "ok",
        "data": {
            "meta": {"mode": "list-events", "date": "2026-08-11",
                     "generated_at": "2026-08-11 20:00",
                     "command_cn": "查日程", "occurred_at": "2026-08-11 20:00"},
            "summary": {"total_active": 0, "total_inactive": 0},
            "events": [], "gap": [], "feishu": {}, "inactive": [], "errors": [],
            "scene": {"scene_id": "list-events",
                      "snapshot": {"title": "查日程", "summary": ["0 条"],
                                   "sections": [{"heading": "明细", "rows": []}]}},
        },
        "message": "t",
    }
    r = render_and_write(payload, out)
    assert r["status"] == "ok", r.get("message")
    h = out.read_text(encoding="utf-8")
    # base.js 函数（toast 是 window.toast = function 形式）
    for fn in ["function copyText", "window.toast = function", "function buildDataText",
               "function buildLogText", "function actionBar", "function formPrompt",
               "function selectList", "function confirm"]:
        assert fn in h, f"产物缺 base.js 函数: {fn}"
    # base.css token
    assert "--blue: #007aff" in h, "产物缺 base.css token"
    # 占位符 0 残留（INJECT-DATA 必须 0; SHARED 字样可能出现在资产注释, 排除）
    assert h.count("<!--INJECT-DATA-->") == 0, "INJECT-DATA 残留"


# ── 缺占位符渲染失败（守卫生效）──────────────────────────

def test_missing_placeholder_blocks_render(monkeypatch):
    """故意删掉 SHARED-HELPERS → Base injector 硬拦截报错（漏迁即红）"""
    from injector import inject

    base_dir = SKILL_DIR.parent / "公共组件"
    js = (base_dir / "assets" / "base.js").read_text(encoding="utf-8").strip()
    css = (base_dir / "assets" / "base.css").read_text(encoding="utf-8").strip()

    tpl = ('<html><body>'
           '<script id="payload" type="application/json"><!--INJECT-DATA--></script>'
           '<script><!--SHARED-HELPERS--></script>'
           '<style><!--SHARED-CSS--></style>'
           '</body></html>')
    payload = {"status": "ok", "data": {"meta": {"command_cn": "x", "occurred_at": "t"},
                                        "scene": {}}}

    # 正常
    html, err = inject(tpl, payload, js_asset=js, css_asset=css)
    assert err is None

    # 删 SHARED-HELPERS → 失败
    html2, err2 = inject(tpl.replace("<!--SHARED-HELPERS-->", ""), payload,
                         js_asset=js, css_asset=css)
    assert err2 is not None and "SHARED-HELPERS" in err2

    # 删 SHARED-CSS → 失败
    html3, err3 = inject(tpl.replace("<!--SHARED-CSS-->", ""), payload,
                         js_asset=js, css_asset=css)
    assert err3 is not None and "SHARED-CSS" in err3

    # 删 INJECT-DATA → 失败
    html4, err4 = inject(tpl.replace("<!--INJECT-DATA-->", ""), payload,
                         js_asset=js, css_asset=css)
    assert err4 is not None and "INJECT-DATA" in err4


# ── 各 render 模式冒烟（隔离 DB）─────────────────────────

@pytest.mark.parametrize("mode,args", [
    ("list-events", ["render-list-events", "2026-08-11"]),
    ("query-plans", ["render-query-plans", "2026-08-11"]),
    ("record-day", ["render-record-day", "2026-08-11"]),
    ("plan-review", ["render-plans-review", "2026-08-11"]),
])
def test_cli_render_modes_ok(mode, args, tmp_path, monkeypatch):
    """关键模式 CLI 端到端渲染成功（隔离 DB, 不写生产）"""
    import subprocess
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_path / "db")
    env["PYTHONUTF8"] = "1"
    cwd = str(SKILL_DIR)
    # init + 渲染
    subprocess.run([sys.executable, "scripts/schedule_cli.py", "init"],
                   capture_output=True, env=env, cwd=cwd, timeout=30)
    r = subprocess.run([sys.executable, "scripts/schedule_cli.py"] + args,
                       capture_output=True, env=env, cwd=cwd, timeout=40)
    out = r.stdout.decode("utf-8", errors="replace")
    m = re.search(r'\{.*\}', out, re.S)
    assert m, f"{mode}: 无 JSON 输出\n{out[:200]}"
    result = __import__("json").loads(m.group(0))
    assert result["status"] == "ok", f"{mode}: {result.get('message')}"
    # 产物含 base 资产
    fp = pathlib.Path(result["data"]["file_path"])
    h = fp.read_text(encoding="utf-8")
    assert "function copyText" in h, f"{mode}: 产物缺 base.js"
    assert "--blue: #007aff" in h, f"{mode}: 产物缺 base.css"
