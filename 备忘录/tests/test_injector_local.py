"""v1.1.0 注入器测试(本地私有)

测试 `备忘录/script/injector.py`(v1.1.0 后改本地)的所有公共 API:
  - inject_html(template, payload) — 占位符替换 + </ 转义
  - write_output(out_dir, name, html) — 自动 mkdir + 时间戳 + 冲突保护
  - render(payload, template_path) — 一站式

**关键**:v1.0.6-v1.0.9 时这段测试在 tests/test_shared_injector.py,但测试通过率不可信
(测试 module 顶部 from injector import 实际指向一个**被删的** _shared/injector.py 路径,
 而 sys.path.insert 的查找顺序实际指向 `备忘录/script/injector.py`(占位符版本),但那个文件
 不导出 inject_html / write_output,所以严格来说 import 应该 ImportError。
 这是 v1.1.0 修复的真实问题:测试需要保护**实际文件**真实存在 + API 真实可导入。
"""
import json
import subprocess
import sys
from pathlib import Path
import pytest

from injector import inject_html, write_output, render  # 本地模块 · 关键 import 必须成功


class TestInjectorModuleExists:
    """v1.1.0 守护:本地 injector 模块真实存在并可导入"""

    def test_injector_module_path(self):
        """injector 模块路径是 memo skill 私有(不走 _shared/)"""
        import injector
        path = Path(injector.__file__).resolve()
        # 必须在 备忘录/script/ 下,不能在 _shared/ 下
        assert "/备忘录/script/" in str(path) or "\\备忘录\\script\\" in str(path), \
            f"injector 必须在备忘录私有,实际: {path}"
        # 必须不存在 _shared/ 引用(避免依赖被清理的模块)
        assert "_shared/injector" not in str(path) and "_shared\\injector" not in str(path), \
            f"injector 不应在 _shared/(v1.0.6 抽取的模块已被清理): {path}"

    def test_inject_html_importable(self):
        """import 真实存在"""
        # 测试是从同目录 module 顶部 import 的,这一行不报 ImportError 就过
        assert inject_html is not None

    def test_write_output_importable(self):
        assert write_output is not None

    def test_render_importable(self):
        assert render is not None


class TestInjectHtml:
    """公共 API:inject_html(占位符唯一性 + </ 转义)"""

    def test_basic_replacement(self):
        tpl = "<body><h1>X</h1><!--INJECT-DATA--></body>"
        out = inject_html(tpl, {"k": "v"})
        assert "window.__DATA__" in out
        assert '"k"' in out or 'k' in out
        assert '"v"' in out or 'v' in out

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

    def test_empty_placeholder_rejected(self):
        with pytest.raises(ValueError):
            inject_html("<body></body>", {}, placeholder="")

    def test_script_close_escaped(self):
        """含 </script> 的 payload 应被转义"""
        tpl = "<!--INJECT-DATA-->"
        out = inject_html(tpl, {"x": "</script><script>alert(1)</script>"})
        # </ 应被转义成 <\/
        assert "<\\/script>" in out
        # 注入块中不应有 raw </script>
        import re
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", out, re.DOTALL)
        assert m
        assert "</script>" not in m.group(1)


class TestWriteOutput:
    """公共 API:write_output(自动 mkdir + 时间戳 + 冲突保护)"""

    def test_creates_dir(self, tmp_path):
        """自动创建不存在的目录"""
        out_dir = tmp_path / "deep" / "nested" / "output"
        p = write_output(out_dir, "memo", "<html>x</html>")
        assert Path(p).exists()
        assert p.endswith(".html")
        assert "memo_" in p

    def test_writes_utf8(self, tmp_path):
        p = write_output(tmp_path, "中文", "<html>内容</html>")
        text = Path(p).read_text(encoding="utf-8")
        assert "内容" in text

    def test_collision_appends_underscore_n(self, tmp_path):
        """同秒第 2 次生成自动 _2"""
        p1 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        p2 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        assert p1 != p2
        assert Path(p2).name.endswith("_2.html"), \
            f"p2 应以 _2.html 结尾: {Path(p2).name}"

    def test_three_collisions(self, tmp_path):
        """同秒 3 次生成 _2 / _3"""
        p1 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        p2 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        p3 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        assert Path(p2).name.endswith("_2.html")
        assert Path(p3).name.endswith("_3.html")
        for p in [p1, p2, p3]:
            assert Path(p).exists()

    def test_no_collision_when_different_ts(self, tmp_path):
        """不同 ts 不触发 _2"""
        p1 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120000")
        p2 = write_output(tmp_path, "memo", "<html>x</html>", ts="20260601_120001")
        assert not Path(p1).name.endswith("_2.html")
        assert not Path(p2).name.endswith("_2.html")


class TestRenderIntegration:
    """公共 API:render(一站式)"""

    def test_render_writes_to_default_dir(self, tmp_path):
        template = tmp_path / "view.html"
        template.write_text(
            "<!doctype html><body><h1>页</h1><!--INJECT-DATA--></body>",
            encoding="utf-8",
        )
        out = render({"k": "v"}, template, name="view")
        assert Path(out).exists()
        assert "view_" in out


class TestMemoRenderCanUseInjector:
    """v1.1.0 关键:备忘录/script/memo_render.py 能导入本地 injector"""

    def test_subprocess_memo_render_imports_injector(self):
        """起一个子进程模拟 memo_cli 调用 memo_render 触发 --html"""
        # memo_render 的 `from injector import` 必须能解析到本地模块
        proc = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'script'); "
             "from memo_render import render_query, render_sync_report, "
             "render_wish_plan, render_wish_complete, render_change_category; "
             "print('ok')"],
            capture_output=True, text=True,
            cwd="/mnt/d/2Study/StudyNotes/SKILLS/备忘录",
            timeout=10,
        )
        assert proc.returncode == 0, \
            f"memo_render 仍需能 import 5 个 render 函数,实际失败:\n{proc.stderr}"
        assert "ok" in proc.stdout
