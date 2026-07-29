"""T11 · clipboard fallback 共享化 钉死测试。

根因:4 模板复制同一段 fallbackCopy + copyTimer。
修法:script/_shared/clipboard.js 单一真相源 · injector.py 加 placeholder
     <!--INJECT-SHARED--> · render 时 inline 注入
     模板不再含 inline `function fallbackCopy` / `var copyTimer`

Seam:
- 模板文件不再含 inline clipboard helper 定义
- 渲染后的 HTML(经过 injector)含 inline helper(透明)
- 单一真相源在 script/_shared/clipboard.js
"""
import re
from pathlib import Path

import pytest

from injector import inject_shared_js

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
SHARED_DIR = Path(__file__).parent.parent / "script" / "_shared"


# ============================================================
# 1. 模板不再含 inline clipboard helper
# ============================================================

class TestTemplatesNoLongerInlineClipboard:
    FILES = ["memo_query.html", "wish_plan.html",
             "wish_complete.html", "change_category.html"]

    def test_no_inline_fallbackCopy(self):
        for name in self.FILES:
            text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            assert "function fallbackCopy(" not in text, (
                f"{name} 不应再含 inline `function fallbackCopy(` · "
                f"已迁入共享脚本 script/_shared/clipboard.js"
            )

    def test_no_inline_copyTimer(self):
        for name in self.FILES:
            text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            assert "var copyTimer=" not in text, (
                f"{name} 不应再含 inline `var copyTimer=` · 已迁入共享"
            )

    def test_no_inline_execCommand_fallback(self):
        """4 模板不应再含 inline `document.execCommand('copy')` 兜底"""
        for name in self.FILES:
            text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            assert "execCommand('copy')" not in text, (
                f"{name} 不应再含 inline execCommand 兜底 · 已迁入共享"
            )


# ============================================================
# 2. 单一真相源 script/_shared/clipboard.js
# ============================================================

class TestSharedClipboardJsExists:
    def test_shared_clipboard_file_exists(self):
        assert (SHARED_DIR / "clipboard.js").exists(), (
            "script/_shared/clipboard.js 必须存在(共享 clipboard helper 单一真相源)"
        )

    def test_shared_clipboard_defines_fallbackCopy(self):
        text = (SHARED_DIR / "clipboard.js").read_text(encoding="utf-8")
        assert "function fallbackCopy(" in text, (
            "clipboard.js 必须定义 fallbackCopy"
        )


# ============================================================
# 3. injector 接入 · placeholder 注入
# ============================================================

class TestInjectorSharedJsInjection:
    TEMPLATE_WITH_PLACEHOLDER = (
        '<!doctype html><html><head>'
        '<!--INJECT-SHARED-->'
        '<title>T</title></head>'
        '<body><script>init()</script></body></html>'
    )

    def test_inject_shared_js_seam_exists(self):
        assert callable(inject_shared_js), (
            "injector.inject_shared_js 必须暴露"
        )

    def test_inject_shared_replaces_placeholder(self):
        out = inject_shared_js(self.TEMPLATE_WITH_PLACEHOLDER, "alert(1);")
        assert "<!--INJECT-SHARED-->" not in out, (
            "placeholder 必须被替换"
        )
        assert "alert(1);" in out, (
            "替换文本必须出现在结果里"
        )

    def test_inject_shared_wraps_in_script_tag(self):
        """共享 JS 应被 <script>...</script> 包住(inline 模式)"""
        out = inject_shared_js(self.TEMPLATE_WITH_PLACEHOLDER, "var x=1;")
        assert re.search(r"<script[^>]*>var x=1;</script>", out), (
            "共享 JS 必须 <script>...</script> 包住 · 形态:<script>{code}</script>"
        )

    def test_inject_shared_template_without_placeholder_raises(self):
        """模板没有 placeholder → 抛 ValueError(类似 INJECT-DATA 行为)"""
        bad = "<html><head></head><body></body></html>"
        with pytest.raises(ValueError):
            inject_shared_js(bad, "alert(1);")

    def test_inject_shared_template_with_two_placeholders_raises(self):
        """placeholder 出现 2 次 → 抛 ValueError(类似 INJECT-DATA 行为)"""
        bad = "<html><!--INJECT-SHARED--><body><!--INJECT-SHARED--></body></html>"
        with pytest.raises(ValueError):
            inject_shared_js(bad, "alert(1);")

    def test_memo_render_integration_injects_shared_js(self):
        """端到端:render_query 渲染后 HTML 必含 clipboard.js 内容"""
        # 触发真实 render 链路
        from memo_render import render_query
        result_path = render_query({
            "status": "ok",
            "data": {"title": "测试", "command": "search", "items": []},
            "message": "ok",
        })
        text = Path(result_path).read_text(encoding="utf-8")
        # 共享 helper 必被 inline 注入
        assert "function fallbackCopy(" in text, (
            "render 后 HTML 必须含 clipboard.js 注入的 fallbackCopy"
        )
        assert "var copyTimer" in text, (
            "render 后 HTML 必须含 copyTimer 全局变量"
        )