"""
测试: 查看域(8 场景 · T6 实施)

覆盖:
- 模板门禁: 零 Jinja2({{ }} / {% %}/{# #} 全清零 · T1 移交验收)+ 占位符唯一
- 渲染: 种子食谱 → recipe_render.py render → window.__RECIPE__ 可解析(军规 11)
- view-3 替换食材预览: --swap 注入 view.swap + scene_id=view-3 + 不落库
- 只看 X: --focus 注入 view.focus + scene_id=view-4/6/7/8 + 锚点 id 保留
- 每步内联本步食材: export-json steps[].ingredients_used 真数据入 payload
- 营养随份量重算: data-base-servings + td[data-base] 缩放逻辑存在
- chef:// 来源解析: 模板含 chef:// → file:/// 拼路径逻辑
"""
import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
RENDER = SCRIPT_DIR / "recipe_render.py"
TEMPLATE = SCRIPT_DIR.parent / "templates" / "recipe_view.html"
FIXTURE = SCRIPT_DIR.parent / "templates" / "recipe_template.json"  # 宫保虾球
CLI_INIT = SCRIPT_DIR / "开始使用" / "cli.py"
IMPORT = SCRIPT_DIR / "recipe_import.py"


def make_env(tmp_path: Path) -> dict:
    """隔离环境: 临时 DB 目录 + 临时输出目录(覆盖外部 env)"""
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def run(env: dict, script: Path, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def seed_recipe(tmp_path: Path) -> dict:
    """建库 + 导入宫保虾球(recipe_template.json),返回 env"""
    env = make_env(tmp_path)
    r = run(env, CLI_INIT, "init")
    assert r["rc"] == 0, r["err"]
    r = run(env, IMPORT, "import", str(FIXTURE), "--merge")
    assert r["rc"] == 0, r["err"]
    return env


def extract_payload(html: str) -> dict:
    """军规 11 · DOM 渲染级断言: 提取可执行的 window.__RECIPE__ 注入"""
    import re
    m = re.search(r"<script>window\.__RECIPE__ = (\{.*?\});</script>", html, re.S)
    assert m, "未找到可执行的 window.__RECIPE__ 注入脚本"
    return json.loads(m.group(1))


def recipe_count(db_path: Path) -> int:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    finally:
        conn.close()


class TestTemplateGates:
    """模板门禁: T1 移交「recipe_view 动态区 JS 化」验收"""

    def test_zero_jinja2(self):
        """342 处 Jinja2 清零: {{ }} / {% %}/{# #} 全部不得出现"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "{{" not in content, "Jinja2 变量语法残留 {{"
        assert "{%" not in content, "Jinja2 控制语法残留 {%"
        assert "{#" not in content, "Jinja2 注释语法残留 {#"

    def test_unique_placeholders(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1
        assert content.count("<!--INJECT-08-->") == 1

    def test_copy_buttons_hard_standard_via_08(self):
        """08 §4: 双按钮经 INJECT-08 注入(渲染后必有复制数据/复制日志)"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "INJECT-08" in content
        assert "复制" in content  # 页面自带复制食材/做菜/采购按钮

    def test_js_renders_from_recipe_payload(self):
        """全 JS 渲染: 模板以 JS 从 __RECIPE__ 取数,不依赖服务端拼串"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "window.__RECIPE__" in content or "__RECIPE__" in content
        assert "document.getElementById('section-ingredients')" in content

    def test_section_anchors_kept(self):
        """锚点 id 保留(只看 X 隐藏其他 section,锚点不删): section-* 4 个"""
        content = TEMPLATE.read_text(encoding="utf-8")
        for sid in ("section-ingredients", "section-steps", "section-nutrition", "section-background"):
            assert f'id="{sid}"' in content, f"锚点 {sid} 缺失"

    def test_inline_step_ingredients_logic_present(self):
        """每步内联本步食材: 模板 JS 引用 ingredients_used(step_ingredients 真数据)"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "ingredients_used" in content
        assert "step_unit" in content

    def test_nutrition_rescale_logic_present(self):
        """营养随份量重算: data-base-servings + td[data-base] 缩放"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert 'data-base-servings' in content
        assert "td[data-base]" in content
        assert "nutrition-table" in content

    def test_chef_source_parsing_logic_present(self):
        """chef:// 来源解析: 模板含 chef:// 前缀判定 + file:/// 拼路径"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "chef://" in content
        assert "file:///" in content

    def test_cookware_at_steps_top(self):
        """菜级炊具顶部(G3): 步骤区渲染菜级炊具条"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "cookware-strip" in content
        assert "R.cookware" in content

    def test_swap_preview_logic_present(self):
        """view-3 替换食材预览: 对照行 + 用量换算 + 确认(不落库)"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "swap-preview" in content
        assert "swap-qty" in content
        assert "不落库" in content or "不会写入数据库" in content


class TestRenderFlow:
    """渲染冒烟: 种子食谱 → HTML 产物 → payload 可解析"""

    def test_render_writes_html_with_parseable_payload(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        files = list(out.glob("*.html"))
        assert files, "查看食谱 HTML 未输出"
        html = files[0].read_text(encoding="utf-8")
        assert "{{" not in html and "{%" not in html, "渲染产物残留 Jinja2"
        payload = extract_payload(html)
        recipe = payload["recipe"]
        assert recipe["name"] == "宫保虾球"
        assert len(recipe["ingredients"]) >= 2
        assert len(recipe["steps"]) >= 1

    def test_render_payload_has_step_ingredients(self, tmp_path):
        """内联食材来自 step_ingredients 真数据: steps[].ingredients_used 非空"""
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[0].read_text(encoding="utf-8")
        payload = extract_payload(html)
        steps = payload["recipe"]["steps"]
        used = [s.get("ingredients_used") or [] for s in steps]
        assert any(u for u in used), "steps[].ingredients_used 应为空集(宫保虾球模板步骤含食材引用)"

    def test_render_08_scene_default_view1(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[0].read_text(encoding="utf-8")
        assert "复制数据" in html and "复制日志" in html
        import re
        m = re.search(r"window\.__A08__ = (\{.*?\});", html, re.S)
        assert m
        a = json.loads(m.group(1))
        assert a["copy_data"]["scene_id"] == "view-1"
        assert a["copy_data"]["command_cn"] == "查看食谱"


class TestFocusMode:
    """只看 X: 隐藏其他 section(锚点保留)"""

    def test_focus_ingredients(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球", "--focus", "食材")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        payload = extract_payload(html)
        assert payload["view"]["focus"] == "食材"
        import re
        m = re.search(r"window\.__A08__ = (\{.*?\});", html, re.S)
        a = json.loads(m.group(1))
        assert a["copy_data"]["scene_id"] == "view-4"
        # 只看 X JS 逻辑: 隐藏其他 section + 锚点 id 保留
        assert "FOCUS_MAP" in html and "style.display = 'none'" in html
        assert 'id="section-ingredients"' in html

    def test_focus_nutrition(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球", "--focus", "营养")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        payload = extract_payload(html)
        assert payload["view"]["focus"] == "营养"

    def test_invalid_focus_ignored(self, tmp_path):
        """非法 focus 值 → 回退完整视图(不崩)"""
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球", "--focus", "不存在")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        payload = extract_payload(html)
        assert "focus" not in payload["view"]


class TestSwapPreview:
    """view-3 替换食材预览(临时假设 · 不落库)"""

    def test_swap_single(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球", "--swap", "花生:腰果")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        payload = extract_payload(html)
        assert payload["view"]["swap"] == [{"from": "花生", "to": "腰果"}]
        import re
        m = re.search(r"window\.__A08__ = (\{.*?\});", html, re.S)
        a = json.loads(m.group(1))
        assert a["copy_data"]["scene_id"] == "view-3"
        # 页面含替换对照行渲染逻辑
        assert "swap-orig" in html and "swap-arrow" in html

    def test_swap_multiple_with_qty(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球",
                "--swap", "花生:腰果:80", "--swap", "虾:鸡胸肉:200")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        payload = extract_payload(html)
        assert payload["view"]["swap"] == [
            {"from": "花生", "to": "腰果", "qty": 80.0},
            {"from": "虾", "to": "鸡胸肉", "qty": 200.0},
        ]

    def test_swap_does_not_write_db(self, tmp_path):
        """替换预览不落库: 渲染前后食谱数不变"""
        env = seed_recipe(tmp_path)
        db = tmp_path / "chef_data.db"
        before = recipe_count(db)
        r = run(env, RENDER, "render", "宫保虾球", "--swap", "花生:腰果")
        assert r["rc"] == 0, r["err"]
        after = recipe_count(db)
        assert before == after == 1

    def test_swap_unknown_ingredient_graceful(self, tmp_path):
        """替换目标不存在 → 渲染不崩(前端兜底)"""
        env = seed_recipe(tmp_path)
        r = run(env, RENDER, "render", "宫保虾球", "--swap", "不存在食材:某某")
        assert r["rc"] == 0, r["err"]
        out = tmp_path / "chef_out" / "recipes"
        html = sorted(out.glob("*.html"))[-1].read_text(encoding="utf-8")
        assert "swap-preview" in html
