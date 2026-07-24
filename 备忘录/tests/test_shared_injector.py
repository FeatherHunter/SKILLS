"""_shared/injector.py 单元测试(可被任何 Skill 复用)"""
import json
import re
import subprocess
import sys
from pathlib import Path
import pytest

# 让 _shared/injector 可 import
_SHARED = Path(__file__).parent.parent.parent / "模板HTML并注入数据" / "_shared"
sys.path.insert(0, str(_SHARED))

from injector import inject_html, write_output, render  # noqa: E402


class TestInjectHtml:
    def test_basic_replacement(self):
        tpl = "<body><h1>X</h1><!--INJECT-DATA--></body>"
        out = inject_html(tpl, {"k": "v"})
        assert "window.__DATA__" in out
        assert "{'k': 'v'}" in out or '{"k": "v"}' in out  # accept both quote styles

    def test_placeholder_unique_enforced(self):
        """占位符重复出现应 raise"""
        tpl = "<body><!--INJECT-DATA--><p>AND <!--INJECT-DATA--></p></body>"
        with pytest.raises(ValueError) as exc:
            inject_html(tpl, {})
        assert "2" in str(exc.value) or "期望 1" in str(exc.value)

    def test_placeholder_missing_enforced(self):
        """占位符缺失应 raise"""
        tpl = "<body>no placeholder</body>"
        with pytest.raises(ValueError):
            inject_html(tpl, {})

    def test_custom_placeholder(self):
        tpl = "<body>{{DATA}}</body>"
        out = inject_html(tpl, {"a": 1}, placeholder="{{DATA}}")
        assert "window.__DATA__" in out

    def test_script_close_escaped(self):
        """含 </script> 的 payload 应被转义"""
        tpl = "<!--INJECT-DATA-->"
        out = inject_html(tpl, {"x": "</script><script>alert(1)</script>"})
        # </ 应被转义成 <\/
        assert "<\\/script>" in out
        # 但不应出现 raw </script>(否则提前闭合)
        # 找注入块
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", out, re.DOTALL)
        assert m
        assert "</script>" not in m.group(1)


class TestWriteOutput:
    def test_creates_dir(self, tmp_path):
        """自动创建 output 目录"""
        out_dir = tmp_path / "deep" / "nested" / "output"
        p = write_output(out_dir, "test", "<html>body</html>")
        assert Path(p).exists()
        assert p.endswith(".html")
        assert "test_" in p  # 含时间戳

    def test_writes_utf8(self, tmp_path):
        p = write_output(tmp_path, "中文", "<html>内容</html>")
        text = Path(p).read_text(encoding="utf-8")
        assert "内容" in text


class TestRenderIntegration:
    """render() 一站式函数"""

    def test_render_writes_output(self, tmp_path):
        template = tmp_path / "view.html"
        template.write_text(
            "<!doctype html><body><h1>页</h1><!--INJECT-DATA--></body>",
            encoding="utf-8",
        )
        # out_dir 由 render() 默认推断(template.parent.parent/output)
        out = render({"k": "v"}, template, name="view")
        assert Path(out).exists()
        assert "view_" in out


class TestSharedImportable:
    """其他 Skill 的脚本应能 import 这个 shared 模块"""

    def test_memo_render_can_import(self):
        """memo_render.py 能 import injector"""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; "
             f"sys.path.insert(0, '{_SHARED}'); "
             "from injector import inject_html, write_output; "
             "print('ok')"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "ok" in result.stdout


class TestWriteOutputCollisionProtection:
    """v1.0.5:同秒内多次生成同一文件时自动追加 _2 / _3 后缀"""

    def test_collision_appends_underscore_n(self, tmp_path):
        """同秒第 2 次生成自动追加 _2"""
        from injector import write_output
        html = "<html>x</html>"
        p1 = write_output(tmp_path, "memo", html, ts="20260601_120000")
        p2 = write_output(tmp_path, "memo", html, ts="20260601_120000")
        assert p1 != p2, f"应不同文件,实际: {p1} vs {p2}"
        # p2 应有 _2 后缀(检查 basename 避免日期包含 _2)
        assert Path(p2).name.endswith("_2.html"), f"p2 应以 _2.html 结尾: {Path(p2).name}"

    def test_three_collisions(self, tmp_path):
        """同秒 3 次生成 → _2 / _3"""
        from injector import write_output
        html = "<html>x</html>"
        p1 = write_output(tmp_path, "memo", html)
        p2 = write_output(tmp_path, "memo", html)
        p3 = write_output(tmp_path, "memo", html)
        assert "_2" in p2
        assert "_3" in p3
        # 3 个文件都存在
        assert Path(p1).exists()
        assert Path(p2).exists()
        assert Path(p3).exists()

    def test_no_collision_when_different_ts(self, tmp_path):
        """显式传不同 ts 不触发 _2 后缀"""
        from injector import write_output
        html = "<html>x</html>"
        p1 = write_output(tmp_path, "memo", html, ts="20260601_120000")
        p2 = write_output(tmp_path, "memo", html, ts="20260601_120001")
        # 检查 basename(避免 pytest tmp_path 里出现 _2026... 干扰)
        assert not Path(p1).name.endswith("_2.html")
        assert not Path(p2).name.endswith("_2.html")
        assert p1 != p2


class TestNamingRuleContract:
    """v1.0.5:命名规则明确化为 <name>_<YYYYMMDD>_<HHMMSS>[_<N>].html"""

    def test_default_name_format(self, tmp_path):
        from injector import write_output
        p = write_output(tmp_path, "memo_query", "<html>x</html>", ts="20260724_103045")
        assert p.endswith("memo_query_20260724_103045.html"), f"实际: {p}"

    def test_name_matches_command_pattern(self, tmp_path):
        """name 应该是 CLI 子命令名(备忘录的 5 个模板对应)"""
        from injector import write_output
        for cmd_name in ["memo_query", "sync_report", "wish_plan", "wish_complete", "change_category"]:
            p = write_output(tmp_path, cmd_name, "<html>x</html>", ts="20260724_103045")
            assert Path(p).name.startswith(cmd_name), f"{cmd_name} 不匹配: {p}"


class TestMemoHtmlOutputDir:
    """v1.0.5:HTML 输出目录 = DB_PATH.parent / memo_html/(与 DB 同级)"""

    def test_default_output_dir_is_memo_html_under_db(self, env_with_tmp_db, monkeypatch):
        """SKILLS_DB_PATH=/tmp/x 时,HTML 输出应在 /tmp/x/memo_html/"""
        import json, subprocess, sys
        # 跑 search 命令(强制生成 HTML)
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "script" / "memo_cli.py"),
             "search", "test", "--html"],
            capture_output=True, text=True, encoding="utf-8",
            env=env_with_tmp_db, timeout=10,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        html_path = data["data"]["html_path"]
        # 验证 HTML 在 /tmp/x/memo_html/ 下,不在 SKILL_DIR/output/ 下
        expected_dir = Path(env_with_tmp_db["SKILLS_DB_PATH"]) / "memo_html"
        assert str(expected_dir) in html_path, f"HTML 应在 {expected_dir},实际: {html_path}"
        assert "output" not in html_path.split("/")[-2], f"HTML 不应在旧 output 目录: {html_path}"
        # 验证文件实际生成
        assert Path(html_path).exists()

    def test_output_dir_auto_creates(self, env_with_tmp_db):
        """v1.0.5:首次生成时自动 mkdir memo_html/"""
        from pathlib import Path
        import subprocess, sys
        memo_html_dir = Path(env_with_tmp_db["SKILLS_DB_PATH"]) / "memo_html"
        # 跑前应不存在
        assert not memo_html_dir.exists()
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent / "script" / "memo_cli.py"),
             "search", "x", "--html"],
            capture_output=True, text=True, encoding="utf-8",
            env=env_with_tmp_db, timeout=10,
        )
        assert proc.returncode == 0
        # 跑后 memo_html/ 应已创建
        assert memo_html_dir.exists(), f"memo_html/ 应自动创建"
