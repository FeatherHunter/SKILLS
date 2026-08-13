"""T02 决策 4 钉死测试 + memo_query.html 真 Bug 验证。

用户拍板(2026-07-29 grill R2-4):memo_query.html 搜索框**只**匹配 note.content 字段。
不回退、不扩展、不"为了贴心"搜 id/UUID。

测试 seam:
- 解析 memo_query.html 的 inline <script> 内 `rowsFiltered()` 函数体
- 检测 JSON.stringify 是否仍被用作搜索谓词
- 检测 escape/unescape 是否对称(规则 2)
- 检测 copyText 函数是否被定义(规则 1)

为什么测试 + lint 双层:
- 静态 lint(script/template_lint.py 规则 1 / 2)负责"违规形态"检测
- 本测试负责"修复后的预期行为"断言(substring → 仅 content;5 entity 反解对称)
"""
from pathlib import Path

import pytest
import re

TEMPLATE = Path(__file__).parent.parent / "templates" / "memo_query.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


def _extract_row_filter_snippet(html: str) -> str:
    """提取 rowsFiltered() 函数体片段(行级切片)。"""
    start = html.find("function rowsFiltered()")
    if start < 0:
        return ""
    end = html.find("\n}\n", start)
    if end < 0:
        end = start + 800
    return html[start:end + 3]


# ============================================================
# 决策 4 钉死测试
# ============================================================

class TestMemoQuerySearchContentOnly:
    """grill 决策 R2-4 + to-spec 决策 4:memo_query 搜索仅 content 字段"""

    def test_does_not_search_full_JSON_stringify(self):
        """rowsFiltered() 不能用 JSON.stringify 整串 .includes() 搜索"""
        snippet = _extract_row_filter_snippet(TEMPLATE_TEXT)
        assert "JSON.stringify(" not in snippet, (
            "搜索实现不能依赖 JSON 整串 substring — 这会让 UUID 含 '37' 等"
            "场景全命中假象(grill 决策 R2-4)。已修应改为 x.content.includes(q)"
        )

    def test_searches_content_field_only(self):
        """搜索谓词应基于 .content 字段做 match"""
        snippet = _extract_row_filter_snippet(TEMPLATE_TEXT)
        # 接受任意 x.content / content.includes / 内容字段 substring
        assert ("x.content" in snippet or "content.includes" in snippet), (
            f"rowsFiltered() 应该访问 x.content 字段以做字段级搜索,实际:{snippet}"
        )


# ============================================================
# 规则 2(escape/unescape 对称)钉死
# ============================================================

class TestMemoQueryEscapeSymmetry:
    """memo_query 反序列化必须解全 5 entity:"""

    def test_reverse_replaces_all_5_entities(self):
        """copyInfo 的 btn.getAttribute('data-item').replace(...) 必须解完 5 entity"""
        # copyInfo 函数是含反序列化的代表性函数
        idx = TEMPLATE_TEXT.find("function copyInfo(")
        assert idx > 0
        end = TEMPLATE_TEXT.find("\n}\n", idx)
        snippet = TEMPLATE_TEXT[idx:end]
        # 必须全部存在 5 个 entity 字面
        for ent in ["&lt;", "&gt;", "&quot;", "&#39;", "&amp;"]:
            assert ent in snippet, f"copyInfo 反序列化缺少 entity 解码: {ent}"


# ============================================================
# 规则 1(引用未定义函数)钉死 — copyReceipt 必须自包含(不再调未定义 copyText)
# ============================================================

class TestMemoQueryCopyTextDefined:
    """#299 Base 重构:L61 `copyText is not defined` 历史修复验证升级。

    旧修复 = copyReceipt 自包含 safeWriteText;新 = 复制全走 Base window.copyText
    (SHARED-HELPERS 注入),模板不再自研复制实现。
    """

    def test_copyFiltered_uses_base_copytext(self):
        """copyFiltered 必须调 window.copyText(Base 注入,含 fallback)"""
        idx = TEMPLATE_TEXT.find("function copyFiltered(")
        assert idx > 0, "copyFiltered 函数必须存在(原 copyReceipt)"
        end = TEMPLATE_TEXT.find("\n}\n", idx)
        snippet = TEMPLATE_TEXT[idx:end]
        assert "window.copyText" in snippet, (
            f"copyFiltered 必须调 Base window.copyText · 实际:{snippet}"
        )

    def test_no_self_made_copy_anymore(self):
        """自研复制(safeWriteText/flashBtn)必须清零,全走 Base"""
        calls = re.findall(r"\b(safeWriteText|flashBtn|fallbackCopy)\s*\(", TEMPLATE_TEXT)
        assert calls == [], (
            f"自研复制残留: {calls}。Base copyText 已含 execCommand fallback"
        )

    def test_base_helpers_placeholder_exists(self):
        """Base 公共 JS 占位符存在(复制/taost 由 公共组件/assets/base.js 注入)"""
        assert "<!--SHARED-HELPERS-->" in TEMPLATE_TEXT, (
            "memo_query.html 应有 SHARED-HELPERS 占位符 · Base copyText/toast 注入点"
        )
