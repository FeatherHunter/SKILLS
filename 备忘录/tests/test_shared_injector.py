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