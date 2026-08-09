"""
测试: 修改域(update-1/2/3 对比+确认+回执 · update-4 废弃 · T11)
- 模板: 占位符唯一 / 08 双按钮硬标准 / 守卫顶层信封
- 渲染: compare(对比栏旧→新高亮 + 填写位) / receipt(成功 diff+撤销 / 失败 08§6.1) / discard(确认+回执+撤销恢复)
- 注入: 浏览器模拟解析(军规 11 · 可执行 script,非 JSON 元素吞没)
- e2e: 撤销反写旧值成功(recipe_manager add → update → 反写 → 验证 DB 旧值)
"""
import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
RENDER = SCRIPT_DIR / "render_修改.py"
RECIPE_CLI = SCRIPT_DIR / "recipe_manager.py"
INIT_CLI = SCRIPT_DIR / "开始使用" / "cli.py"
TEMPLATE_COMPARE = SCRIPT_DIR.parent / "templates" / "修改" / "update_compare.html"
TEMPLATE_DISCARD = SCRIPT_DIR.parent / "templates" / "修改" / "discard_receipt.html"

EXPECTED_TABLES = 17


def make_env(tmp_path: Path) -> dict:
    """隔离环境: 临时 DB 目录 + 临时输出目录(覆盖外部 env)"""
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def run_cli(env: dict, script: Path, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def simulate_browser_parse(html: str) -> dict:
    """军规 11 · DOM 渲染级断言: 注入必须是可执行 script(私家大厨约定 = 裸注释占位符)"""
    import re as _re
    assert '<script id="payload"' not in html, "模板不得再用 json-payload 元素(私家大厨约定 = 裸注释占位符)"
    m = _re.search(r'<script>window\.__DATA__ = (\{.*\});</script>', html, _re.S)
    assert m, "未找到可执行的 window.__DATA__ 注入脚本(可能被 JSON 元素吞没)"
    return json.loads(m.group(1))


def write_payload(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "payload.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def base_payload(mode: str = "compare", **extra) -> dict:
    d = {
        "mode": mode,
        "scene_id": "update_main_fields",
        "scene_title": "修改食谱主信息",
        "wake_word": "修改食谱",
        "command_cn": "修改食谱",
        "occurred_at": "2026-08-09 12:00:00",
        "target": "宫保虾球",
        "recipe_id": "r-0001",
        "changes": [
            {"path": "difficulty", "label": "难度", "old": "中等", "new": "简单", "state": "confirmed"},
            {"path": "servings", "label": "份量", "old": "2", "new": "4", "state": "confirmed"},
        ],
        "payload": {"difficulty": "简单", "servings": "4"},
        "logs": {"thought_chain": "意图理解 → 取旧值 → 对比确认 → 写库"},
    }
    d.update(extra)
    return d


class TestTemplateStatic:
    """模板静态契约(08 §4 + 军规 11 + 守卫)"""

    def test_compare_template_unique_placeholder(self):
        content = TEMPLATE_COMPARE.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_discard_template_unique_placeholder(self):
        content = TEMPLATE_DISCARD.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_compare_template_copy_buttons_hard_standard(self):
        """08 §4: 复制数据 + 复制日志 = 全部 HTML 硬标准"""
        content = TEMPLATE_COMPARE.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_discard_template_copy_buttons_hard_standard(self):
        content = TEMPLATE_DISCARD.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_compare_template_guard_top_level_envelope(self):
        """守卫必须读顶层信封(window.__DATA__),禁止 payload.data 残留"""
        content = TEMPLATE_COMPARE.read_text(encoding="utf-8")
        assert "window.__DATA__" in content
        assert "payload.data" not in content

    def test_discard_template_guard_top_level_envelope(self):
        content = TEMPLATE_DISCARD.read_text(encoding="utf-8")
        assert "window.__DATA__" in content
        assert "payload.data" not in content


class TestRenderCompare:
    """update_compare.html · compare 模式(对比栏 + 填写位 + 确认按钮)"""

    def test_render_compare_writes_html_with_data(self, tmp_path):
        env = make_env(tmp_path)
        p = write_payload(tmp_path, base_payload("compare"))
        r = run_cli(env, RENDER, "compare", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("修改对比_*.html"))
        assert files, "compare HTML 未输出"
        html = files[0].read_text(encoding="utf-8")
        assert "<!--INJECT-DATA-->" not in html
        data = simulate_browser_parse(html)
        assert data["mode"] == "compare"
        assert data["target"] == "宫保虾球"
        assert len(data["changes"]) == 2

    def test_compare_html_shows_old_to_new_diff(self, tmp_path):
        """验收: 对比栏正确显示旧→新差异"""
        env = make_env(tmp_path)
        p = write_payload(tmp_path, base_payload("compare"))
        r = run_cli(env, RENDER, "compare", str(p))
        assert r["rc"] == 0, r["err"]
        html = sorted((tmp_path / "chef_out" / "修改").glob("修改对比_*.html"))[-1].read_text(encoding="utf-8")
        assert "改前" in html and "改后" in html
        data = simulate_browser_parse(html)
        old_vals = [c["old"] for c in data["changes"]]
        new_vals = [c["new"] for c in data["changes"]]
        assert "中等" in old_vals and "简单" in new_vals
        assert "难度" in html

    def test_compare_missing_field_renders_fill_spot(self, tmp_path):
        """填写位: missing 字段渲染为待补充输入(红框)"""
        env = make_env(tmp_path)
        payload = base_payload("compare", changes=[
            {"path": "difficulty", "label": "难度", "old": "中等", "new": "简单", "state": "confirmed"},
            {"path": "source", "label": "来源", "old": "", "new": "", "state": "missing"},
        ])
        p = write_payload(tmp_path, payload)
        r = run_cli(env, RENDER, "compare", str(p))
        assert r["rc"] == 0, r["err"]
        html = sorted((tmp_path / "chef_out" / "修改").glob("修改对比_*.html"))[-1].read_text(encoding="utf-8")
        assert "待补充" in html
        assert "cmp-new-missing" in html

    def test_compare_confirm_button_prompt_includes_new_values(self, tmp_path):
        """确认按钮: 复制带参数的确认 prompt(08 §4 普通确认式)"""
        env = make_env(tmp_path)
        p = write_payload(tmp_path, base_payload("compare"))
        r = run_cli(env, RENDER, "compare", str(p))
        assert r["rc"] == 0, r["err"]
        html = sorted((tmp_path / "chef_out" / "修改").glob("修改对比_*.html"))[-1].read_text(encoding="utf-8")
        assert "确认变更" in html


class TestRenderReceipt:
    """update_compare.html · receipt 模式(成功 diff+撤销 / 失败 08§6.1)"""

    def test_render_success_receipt_with_undo(self, tmp_path):
        env = make_env(tmp_path)
        p = write_payload(tmp_path, base_payload("success",
            result="已修改",
            diff=[
                {"action": "mod", "field": "难度", "summary": "中等 → 简单"},
                {"action": "mod", "field": "份量", "summary": "2 → 4"},
            ],
            undo_prompt="请撤销刚才对「宫保虾球」的修改:把「难度」从「简单」改回「中等」;把「份量」从「4」改回「2」(不建版本表,直接反写旧值)。",
            reminder="难度与份量已同步更新",
        ))
        r = run_cli(env, RENDER, "receipt", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("修改回执_成功_*.html"))
        assert files, "success receipt 未输出"
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["mode"] == "success"
        assert "撤销" in html
        assert "中等 → 简单" in html
        assert data["undo_prompt"] and "改回" in data["undo_prompt"]

    def test_render_failure_receipt(self, tmp_path):
        """08 §6.1 错误回执: 操作名/失败原因/关键数据/建议下一步"""
        env = make_env(tmp_path)
        p = write_payload(tmp_path, base_payload("failure",
            operation="修改食谱",
            failure_reason="菜名不存在或已废弃",
            key_data={"target": "宫保虾球"},
            next_step="确认菜名后重试,或用「查看全部」确认现有食谱",
            retry_prompt="请修正菜名后重新修改",
        ))
        r = run_cli(env, RENDER, "receipt", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("修改回执_失败_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        assert "失败原因" in html
        assert "修正重试" in html
        data = simulate_browser_parse(html)
        assert data["mode"] == "failure"
        assert data["failure_reason"] == "菜名不存在或已废弃"


class TestRenderDiscard:
    """discard_receipt.html · 废弃食谱(确认 + 回执 + 撤销恢复)"""

    def test_render_discard_confirm(self, tmp_path):
        env = make_env(tmp_path)
        p = write_payload(tmp_path, {
            "mode": "confirm",
            "scene_id": "discard_recipe",
            "scene_title": "废弃食谱(只增不删)",
            "wake_word": "废弃食谱",
            "command_cn": "废弃食谱",
            "occurred_at": "2026-08-09 12:00:00",
            "target": "宫保虾球",
            "recipe_id": "r-0001",
            "recipe": {"name": "宫保虾球", "difficulty": "中等", "servings": "2", "status": "未做"},
        })
        r = run_cli(env, RENDER, "discard", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("废弃确认_*.html"))
        assert files, "discard confirm 未输出"
        html = files[0].read_text(encoding="utf-8")
        assert "废弃 = 标记不用,不物理删除" in html
        assert "确认废弃" in html
        data = simulate_browser_parse(html)
        assert data["mode"] == "confirm"

    def test_render_discard_success_with_undo_restore(self, tmp_path):
        env = make_env(tmp_path)
        p = write_payload(tmp_path, {
            "mode": "success",
            "scene_id": "discard_recipe",
            "scene_title": "废弃食谱(只增不删)",
            "wake_word": "废弃食谱",
            "command_cn": "废弃食谱",
            "occurred_at": "2026-08-09 12:00:00",
            "target": "宫保虾球",
            "recipe_id": "r-0001",
            "result": "已废弃(标记不用,不物理删除)",
            "diff": [{"action": "mod", "field": "status", "summary": "未做 → 已废弃"}],
            "old_status": "未做",
            "undo_prompt": "请撤销刚才的废弃,把食谱「宫保虾球」状态改回「未做」,恢复为可用。",
            "reminder": "列表/搜索已自动过滤该食谱",
        })
        r = run_cli(env, RENDER, "discard", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("废弃已废弃_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        assert "撤销废弃" in html
        data = simulate_browser_parse(html)
        assert data["mode"] == "success"
        assert data["undo_prompt"] and "恢复" in data["undo_prompt"]

    def test_render_discard_failure(self, tmp_path):
        env = make_env(tmp_path)
        p = write_payload(tmp_path, {
            "mode": "failure",
            "scene_id": "discard_recipe",
            "scene_title": "废弃食谱(只增不删)",
            "wake_word": "废弃食谱",
            "command_cn": "废弃食谱",
            "occurred_at": "2026-08-09 12:00:00",
            "target": "宫保虾球",
            "operation": "废弃食谱",
            "failure_reason": "未找到该食谱",
            "key_data": {"target": "宫保虾球"},
            "next_step": "用「查看全部」确认菜名后重试",
            "retry_prompt": "请修正菜名后重新废弃",
        })
        r = run_cli(env, RENDER, "discard", str(p))
        assert r["rc"] == 0, r["err"]
        files = list((tmp_path / "chef_out" / "修改").glob("废弃失败_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        assert "失败原因" in html and "未找到该食谱" in html


class TestUndoE2E:
    """e2e: 撤销反写旧值成功(不建表 · recipe_manager update 反写)"""

    @classmethod
    def setup_class(cls):
        pass

    def _init_and_add(self, env, name="宫保虾球"):
        r = run_cli(env, INIT_CLI, "init")
        assert r["rc"] == 0, r["err"]
        r = run_cli(env, RECIPE_CLI, "add", name, "--difficulty", "中等", "--servings", "2", "--total_time", "30", "--photo_url", "https://example.com/p.png", "--source", "测试", "--source_url", "https://example.com/r", "--description", "测试菜谱")
        assert r["rc"] == 0, r["err"]
        rid = None
        for line in r["out"].splitlines():
            if line.strip().startswith("ID:"):
                rid = line.split(":", 1)[1].strip()
        assert rid, f"未解析到 recipe_id: {r['out']}"
        return rid

    def _db_value(self, tmp_path, rid, field="difficulty"):
        db = tmp_path / "chef_data.db"
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            return conn.execute(f"SELECT {field} FROM recipes WHERE id = ?", (rid,)).fetchone()[0]
        finally:
            conn.close()

    def test_undo_write_back_old_value_via_cli(self, tmp_path):
        """修改 → 反写旧值: difficulty 中等→简单 → 撤销改回 中等,DB 验证"""
        env = make_env(tmp_path)
        rid = self._init_and_add(env)
        assert self._db_value(tmp_path, rid) == "中等"

        r = run_cli(env, RECIPE_CLI, "update", rid, "--difficulty", "简单")
        assert r["rc"] == 0, r["err"]
        assert self._db_value(tmp_path, rid) == "简单"

        # 撤销 = 反写旧值(不建表): 把「简单」改回「中等」
        r = run_cli(env, RECIPE_CLI, "update", rid, "--difficulty", "中等")
        assert r["rc"] == 0, r["err"]
        assert self._db_value(tmp_path, rid) == "中等"

    def test_discard_and_restore_status_via_cli(self, tmp_path):
        """废弃 → 撤销恢复: status 未做→已废弃 → 恢复 未做,DB 验证"""
        env = make_env(tmp_path)
        rid = self._init_and_add(env)
        assert self._db_value(tmp_path, rid, "status") == "未做"

        r = run_cli(env, RECIPE_CLI, "discard", rid)
        assert r["rc"] == 0, r["err"]
        assert self._db_value(tmp_path, rid, "status") == "已废弃"

        # 撤销废弃 = 恢复可用: status 改回「未做」
        r = run_cli(env, RECIPE_CLI, "update", rid, "--status", "未做")
        assert r["rc"] == 0, r["err"]
        assert self._db_value(tmp_path, rid, "status") == "未做"

    def test_undo_prompt_carries_old_value_for_ai_execution(self, tmp_path):
        """回执撤销按钮的 prompt 携带旧值(反写旧值的参数)"""
        env = make_env(tmp_path)
        payload = base_payload("success",
            result="已修改",
            diff=[{"action": "mod", "field": "难度", "summary": "中等 → 简单"}],
            undo_prompt="请撤销刚才对「宫保虾球」的修改:把「难度」从「简单」改回「中等」(不建版本表,直接反写旧值)。",
        )
        p = write_payload(tmp_path, payload)
        r = run_cli(env, RENDER, "receipt", str(p))
        assert r["rc"] == 0, r["err"]
        html = sorted((tmp_path / "chef_out" / "修改").glob("修改回执_成功_*.html"))[-1].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        prompt = data["undo_prompt"]
        assert "中等" in prompt
        assert "简单" in prompt
        assert "改回" in prompt
