# -*- coding: utf-8 -*-
"""备忘录 Base 管线守卫测试(#299 Base 重构 · 漏迁即红)

覆盖:
- 全部 6 业务模板: INJECT-DATA / SHARED-HELPERS / SHARED-CSS 占位符恰 1(漏迁/重复 → 红)
- 每业务模板含「复制数据」+「复制日志」按钮(08 硬标准 · #269 遗漏教训)
- 渲染产物: base.js 函数 + base.css token 注入完整 + 占位符 0 残留
- 漏迁即红: 故意删占位符 → Base injector 硬拦截报错
- 信封: 每个 render_* 产物含 meta(scene.snapshot 领域无关) + copy_log(6 段)
- HELP: Base help_template + scene-data 契约 v1 校验 + 3 副本机制
- 无生产库接触: 全部走临时目录(SKILLS_DB_PATH 隔离)
"""
import pathlib
import sys

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "script"))

TEMPLATES = sorted((SKILL_DIR / "templates").glob("*.html"))
assert len(TEMPLATES) == 6, f"业务模板应为 6 个, 实际 {len(TEMPLATES)}: {[t.name for t in TEMPLATES]}"
PLACEHOLDERS = ["<!--INJECT-DATA-->", "<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->"]


# ── 占位符契约(全部模板恰 1)────────────────────────────

@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda p: p.name)
def test_template_placeholders_exact_one(tpl):
    c = tpl.read_text(encoding="utf-8")
    for ph in PLACEHOLDERS:
        n = c.count(ph)
        assert n == 1, f"{tpl.name}: {ph} 应为 1 个, 实际 {n} 个(漏迁或重复)"


# ── 08 硬标准: 每业务模板必须有复制数据/复制日志按钮 ─────

@pytest.mark.parametrize("tpl", TEMPLATES, ids=lambda p: p.name)
def test_business_template_has_copy_data_log(tpl):
    c = tpl.read_text(encoding="utf-8")
    assert "复制数据" in c, f"{tpl.name}: 缺「复制数据」(08 规范硬标准)"
    assert "复制日志" in c, f"{tpl.name}: 缺「复制日志」(08 规范硬标准)"


# ── 旧资产退役(自研注入器/clipboard 已删除)───────────────

def test_legacy_assets_retired():
    assert not (SKILL_DIR / "script" / "injector.py").exists(), "自研 injector.py 应已退役(Base 替代)"
    assert not (SKILL_DIR / "script" / "_shared").exists(), "_shared/clipboard.js 应已退役(Base copyText 替代)"


def test_no_inject_shared_placeholder_left():
    for tpl in TEMPLATES:
        c = tpl.read_text(encoding="utf-8")
        assert "<!--INJECT-SHARED-->" not in c, f"{tpl.name}: 残留旧 INJECT-SHARED 占位符"
        assert "fallbackCopy" not in c, f"{tpl.name}: 残留自研 fallbackCopy(Base copyText 替代)"


# ── 渲染产物 Base 注入完整性 + 信封 ──────────────────────

def test_render_injects_base_assets(monkeypatch, tmp_path):
    """render_query 产物: base.js 函数 + base.css token + 占位符 0 残留 + 信封"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import importlib
    import memo_cli
    importlib.reload(memo_cli)
    from memo_render import render_query

    payload = {
        "status": "ok",
        "data": {"title": "备忘录搜索结果", "command": "search",
                 "generated_at": "2026-08-13 20:00",
                 "items": [{"id": 1, "content": "测试", "category": "备忘",
                            "sub_category": None, "created_at": "2026-08-13 20:00"}]},
        "message": "找到 1 条笔记",
    }
    path = render_query(payload)
    h = pathlib.Path(path).read_text(encoding="utf-8")
    for fn in ["function copyText", "window.toast = function", "function buildDataText",
               "function buildLogText", "function actionBar", "function emptyState",
               "function errorReceipt"]:
        assert fn in h, f"产物缺 base.js 函数: {fn}"
    assert "--blue: #007aff" in h, "产物缺 base.css token"
    assert h.count("<!--INJECT-DATA-->") == 0, "INJECT-DATA 残留"
    # 信封: meta + scene.snapshot + copy_log
    assert "command_cn" in h and "skill_name" in h, "产物缺 meta 信封"
    assert "snapshot" in h and "copy_log" in h, "产物缺 scene.snapshot/copy_log"
    assert path.startswith(str(tmp_path)), "产物必须落在临时目录(隔离)"


def test_render_wish_plan_envelope(monkeypatch, tmp_path):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import importlib
    import memo_cli
    importlib.reload(memo_cli)
    from memo_render import render_wish_plan
    payload = {
        "status": "ok",
        "data": {"title": "心愿排期向导", "command": "wish-batch-plan",
                 "items": [{"id": 9, "content": "学做红烧肉", "current_due": None,
                            "feishu_task_guid": None, "selected": True}]},
        "message": "找到 1 个心愿",
    }
    path = render_wish_plan(payload)
    h = pathlib.Path(path).read_text(encoding="utf-8")
    assert "wish-batch-plan" in h and "snapshot" in h, "向导页缺信封"


# ── 漏迁即红(守卫生效)──────────────────────────────────

def test_missing_placeholder_blocks_render():
    """故意删掉 SHARED-HELPERS → Base injector 硬拦截报错(漏迁即红)"""
    from memo_render import _base_injector, _base_assets
    mod = _base_injector()
    js, css = _base_assets()

    tpl = ("<html><body>"
           "<script id='payload' type='application/json'><!--INJECT-DATA--></script>"
           "<script><!--SHARED-HELPERS--></script>"
           "<style><!--SHARED-CSS--></style>"
           "</body></html>")
    payload = {"status": "ok", "data": {"meta": {"command_cn": "x", "occurred_at": "t"},
                                         "scene": {}}}
    html, err = mod.inject(tpl, payload, js_asset=js, css_asset=css)
    assert err is None
    for ph in ["<!--SHARED-HELPERS-->", "<!--SHARED-CSS-->", "<!--INJECT-DATA-->"]:
        html2, err2 = mod.inject(tpl.replace(ph, ""), payload, js_asset=js, css_asset=css)
        assert err2 is not None, f"删 {ph} 应被硬拦截"


# ── HELP: scene-data 契约 v1 + 转换层 ────────────────────

def test_scenarios_to_contract_data():
    from memo_render import _load_scenarios, _scenarios_to_contract_data, _base_injector
    data = _load_scenarios()
    contract = _scenarios_to_contract_data(data)
    mod = _base_injector()
    ok, msg = mod.validate_help_data(contract)
    assert ok, f"转换层产物未过 scene-data 契约 v1: {msg}"
    assert contract["skill_name"] == "备忘录"
    assert len(contract["groups"]) == len(data["categories"]), "分组数 = 分类数"
    total = sum(len(sg["scenes"]) for g in contract["groups"] for sg in g["subgroups"])
    assert total == len(data["scenarios"]), "场景数零丢失"
    # dimensions → editable_fields
    init_scene = data["scenarios"][0]
    if init_scene.get("dimensions"):
        mapped = next(
            s for g in contract["groups"] for sg in g["subgroups"] for s in sg["scenes"]
            if s["id"] == init_scene["scenario_id"]
        )
        assert mapped.get("editable_fields"), "dimensions 应映射为 editable_fields"


def test_render_help_three_copies(monkeypatch, tmp_path):
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    monkeypatch.setenv("HELP_INITIALIZED", "1")
    import importlib
    import memo_cli
    importlib.reload(memo_cli)
    from memo_render import render_help

    out_copy = tmp_path / "额外副本.html"
    r = render_help(output_path=str(out_copy))
    assert r["scenario_count"] == 30
    assert pathlib.Path(r["html_path"]).exists(), "时间戳副本必写"
    assert out_copy.exists(), "--output 额外副本必写"
    h = pathlib.Path(r["html_path"]).read_text(encoding="utf-8")
    assert "function copyText" in h, "HELP 产物缺 base.js"
    assert h.count("<!--INJECT-DATA-->") == 0, "HELP INJECT-DATA 残留"
    # 已初始化 → 无 init_banner
    assert "第一次用备忘录" not in h, "HELP_INITIALIZED=1 不应渲染 init banner"


def test_help_contract_rejects_bad_data():
    from memo_render import _base_injector
    mod = _base_injector()
    ok, msg = mod.validate_help_data({"skill_name": "备忘录", "title": "x", "groups": []})
    assert not ok, "空 groups 应校验失败"
    ok2, _ = mod.validate_help_data({"skill_name": "备忘录", "title": "x",
                                     "groups": [{"id": "g", "label": "G",
                                                 "subgroups": [{"id": "s", "label": "S",
                                                                "scenes": [
                                                                    {"id": "a", "title": "A",
                                                                     "wake_word": "w",
                                                                     "prompt_template": "p",
                                                                     "status": ""}]}]}]})
    assert ok2, "最小合法数据应通过"
