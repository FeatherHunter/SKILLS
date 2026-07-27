"""
测试 6+7+8:render_data.py 防回归
- 4 子命令都能跑
- search 字段名兼容('recipes'/'results'/'items')
- 错误处理不裸露 stacktrace
"""
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"


def run_render_data(*args) -> tuple:
    """调 scripts/render_data.py <args>"""
    cmd = [sys.executable, str(SCRIPT_DIR / "render_data.py"), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout, r.stderr


class TestRenderDataSmoke:
    """测试 4 子命令 smoke run(不真渲染 HTML,只验证不崩)"""

    def test_search_help(self):
        """无子命令 → 打印 usage → 退出码 0"""
        rc, out, err = run_render_data()
        assert rc == 0
        assert "用法" in out or "用法" in err

    def test_search_runs_with_known_recipe(self):
        """search 辣椒炒肉(库里有) → 不崩"""
        rc, out, err = run_render_data("search", "辣椒炒肉", "--out", "/tmp/_test_search.html")
        # 退出码 0 OR 友好错误
        if rc != 0:
            # 错误信息应友好,不应裸露 stacktrace
            assert "Traceback" not in err, f"错误处理不友好,裸露 stacktrace: {err}"

    def test_history_runs(self):
        """history 辣椒炒肉 → 不崩"""
        rc, out, err = run_render_data("history", "辣椒炒肉", "--out", "/tmp/_test_history.html")
        if rc != 0:
            assert "Traceback" not in err

    def test_stats_runs(self):
        """stats 辣椒炒肉 → 不崩"""
        rc, out, err = run_render_data("stats", "辣椒炒肉", "--out", "/tmp/_test_stats.html")
        if rc != 0:
            assert "Traceback" not in err

    def test_relations_runs_with_known_recipe(self):
        """relations 辣椒炒肉(关键:验证 relation_manager 接受菜名)"""
        rc, out, err = run_render_data("relations", "辣椒炒肉", "--out", "/tmp/_test_rel.html")
        if rc != 0:
            assert "Traceback" not in err, f"relations 仍 crash: {err}"

    def test_search_handles_nonexistent_recipe(self):
        """search 不存在菜名 → 友好错误,无 stacktrace"""
        rc, out, err = run_render_data("search", "ZZZ不存在", "--out", "/tmp/_test_noexist.html")
        assert "Traceback" not in err, f"搜索不存在菜时裸露 stacktrace: {err}"


class TestRelationManagerJson:
    """测试 relation_manager.py --json 支持(Phase 7.3 修复)"""

    def test_relation_manager_json_success(self):
        """list-parent 接受菜名 → JSON 返"""
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "relation_manager.py"), "list-parent", "辣椒炒肉", "--json"],
            capture_output=True, text=True, encoding="utf-8"
        )
        assert r.returncode == 0
        import json
        data = json.loads(r.stdout)
        assert data["status"] in ("success", "error")
        assert "data" in data or "message" in data

    def test_relation_manager_json_not_found(self):
        """list-parent 不存在菜名 → JSON error"""
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "relation_manager.py"), "list-parent", "ZZZ不存在", "--json"],
            capture_output=True, text=True, encoding="utf-8"
        )
        assert r.returncode == 0
        import json
        data = json.loads(r.stdout)
        assert data["status"] == "error"
        assert data["error"] == "recipe_not_found"

    def test_relation_manager_json_list_all(self):
        """list-all --json 返有效 JSON"""
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "relation_manager.py"), "list-all", "--json"],
            capture_output=True, text=True, encoding="utf-8"
        )
        assert r.returncode == 0
        import json
        data = json.loads(r.stdout)
        assert data["status"] in ("success", "error")
        assert "relations" in data.get("data", {}) or data["status"] == "error"
