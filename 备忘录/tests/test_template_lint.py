"""templates 层 lint 静态测试(template_lint.py 上的契约)。

Seam:通过 `script/template_lint.py` 3 个入口函数实现纯静态 JS-side 校验。测试只通过
公开 seam(`lint_undefined_funcs` / `lint_escape_asymmetry` / `lint_copy_fallback` /
`lint_templates_dir`)验证,不依赖 HTML 浏览器渲染。

RULES:
- 类 1(规则 1):inline `<script>` 内 `funcName(` 调用但文件无 `function funcName` 定义 → 报警
- 类 2(规则 2):`esc(` 调用,但反序列化 (.replace(/&[#\\w]+;/g, ...)) 处理的 entity 集合不全
  转义集合 → 报警(典型:esc 输出 5 entity,反解只 2)
- 类 3(规则 3):`<button ...>` 节点无对应 `.addEventListener('click'` 或 `onclick=` handler
  → 报警(违反总纲 §04 原则 10 HTML 单工铁律:过程型 HTML 必有复制路径)
"""
import re
from pathlib import Path

import pytest

from template_lint import (
    lint_undefined_funcs,
    lint_escape_asymmetry,
    lint_copy_fallback,
    lint_templates_dir,
    ESC_ENTITY_PATTERN,
    ESC_ENTITY_SET,
)


# ============================================================
# 测试 seeder:故意构造"应被报警"的样本 HTML
# ============================================================

HTML_HAS_UNDEFINED_CALL = """
<script>
function init() {
  renderList();
  // copyText never defined anywhere
  copyText('foo');
}
</script>
"""


HTML_ALL_DEFINED = """
<script>
function init() {
  renderList();
}
function renderList() { /* defined above */ }
function copyText(t) { return t; }
init();
</script>
"""


HTML_ESC_ASYMMETRY = """
<script>
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);
  });
}
function load() {
  // 反序列化只解 2 个 entity,不对称
  const text = el.innerHTML.replace(/&quot;/g, '"').replace(/&amp;/g, '&');
}
</script>
"""


HTML_ESC_SYMMETRIC = """
<script>
function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);
  });
}
function unesc(s) {
  // 反序列化 5 个 entity,对称
  return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
}
</script>
"""


HTML_BUTTON_WITHOUT_HANDLER = """
<div>
  <button class="primary" onclick="adopt()">采纳</button>
  <button class="back-to-top-static">↑</button>  <!-- 无 handler,应报警 -->
</div>
<script>
function adopt() { /* defined above */ }
</script>
"""


HTML_BUTTON_WITH_HANDLER = """
<div>
  <button class="primary" onclick="adopt()">采纳</button>
  <button class="back-to-top">↑</button>
</div>
<script>
function adopt() { /* defined above */ }
function initBackToTop() {
  document.querySelector('.back-to-top').addEventListener('click', function () {
    window.scrollTo(0, 0);
  });
}
initBackToTop();
</script>
"""


# ============================================================
# Test · 规则 1(引用未定义函数)
# ============================================================

class TestUndefinedFuncs:
    def test_seam_exists(self):
        """seam 入口暴露"""
        assert callable(lint_undefined_funcs)

    def test_reports_undefined_call(self):
        """故意调用 copyText 但不定义,应报警"""
        findings = lint_undefined_funcs(HTML_HAS_UNDEFINED_CALL)
        names = [f["name"] for f in findings if f["name"]]
        assert "copyText" in names

    def test_clean_when_all_defined(self):
        """全部已定义,无报警"""
        findings = lint_undefined_funcs(HTML_ALL_DEFINED)
        # 应该 0 finding 或没有名字为 init/renderList/copyText 的报警
        bad = [f for f in findings if f["name"] in {"init", "renderList", "copyText"}]
        assert bad == []

    def test_does_not_report_window_globals(self):
        """白名单:window.onload / window.alert / navigator.* / document.* / window.* 不视作未定义"""
        findings = lint_undefined_funcs("""
<script>
function init() {
  window.scrollTo(0,0);
  document.getElementById('x');
  navigator.clipboard.writeText('a');
  alert('hi');
  console.log('c');
}
</script>
""")
        bad = [f for f in findings
               if f.get("name") in {"scrollTo", "getElementById", "writeText", "alert", "log"}]
        assert bad == []


# ============================================================
# Test · 规则 2(escape/unescape 对称)
# ============================================================

class TestEscapeAsymmetry:
    def test_seam_exists(self):
        assert callable(lint_escape_asymmetry)

    def test_reports_asymmetry(self):
        """esc 输出 5 entity,反序列化只 2 → 报警"""
        findings = lint_escape_asymmetry(HTML_ESC_ASYMMETRY)
        assert any("esc" in f.get("msg", "").lower() for f in findings)

    def test_clean_when_symmetric(self):
        """esc / unesc 共同覆盖 5 entity → 无报警"""
        findings = lint_escape_asymmetry(HTML_ESC_SYMMETRIC)
        bad = [f for f in findings if "不对称" in f.get("msg", "")]
        assert bad == [], f"对称样本不该报警: {bad}"


# ============================================================
# Test · 规则 3(HTML 单工铁律:button 无 handler)
# ============================================================

class TestCopyFallback:
    def test_seam_exists(self):
        assert callable(lint_copy_fallback)

    def test_reports_button_without_handler(self):
        """back-to-top-static 无 handler → 应报警"""
        findings = lint_copy_fallback(HTML_BUTTON_WITHOUT_HANDLER)
        # button name 应在 findings
        bad = [f for f in findings if "back-to-top-static" in f.get("source", "")
               or "back-to-top-static" in f.get("msg", "")]
        assert bad, f"未报警:{findings}"

    def test_clean_when_handlers_attached(self):
        """所有 button 都有 handler → 无报警"""
        findings = lint_copy_fallback(HTML_BUTTON_WITH_HANDLER)
        bad = [f for f in findings if "未 handler" in f.get("msg", "")]
        assert bad == []


# ============================================================
# Test · 整体入口(lint_templates_dir)
# ============================================================

class TestLintTemplatesDir:
    def test_runs_on_real_memo_query_and_lint_passes(self):
        """T02 修复后:memo_query.html 不应在 lint 中报警(说明 Bug 全清)。"""
        tmpl_dir = Path(__file__).parent.parent / "templates"
        html = (tmpl_dir / "memo_query.html").read_text(encoding="utf-8")
        findings = (lint_undefined_funcs(html)
                    + lint_escape_asymmetry(html)
                    + lint_copy_fallback(html))
        # 注意:memo_query.html L61 `copyText is not defined` 已被 copyReceipt 自包含修复
        # 现不应再有 "copyText" 在未定义函数列表里
        names = [f["name"] for f in findings if f.get("name")]
        assert "copyText" not in names, (
            f"memo_query.html 仍残留 copyText() 未定义调用 — T02 修复回潮。{findings}"
        )


# ============================================================
# Test · 边界保护
# ============================================================

class TestBoundary:
    def test_no_script_no_crash(self):
        """无 <script> 的 HTML 不应崩"""
        assert lint_undefined_funcs("<div>static</div>") == []
        assert lint_escape_asymmetry("<div>static</div>") == []
        assert lint_copy_fallback("<div>static</div>") == []

    def test_ESC_ENTITY_SET_constant_exposed(self):
        """5 个 entity 集合"""
        assert ESC_ENTITY_SET == {"amp", "lt", "gt", "quot", "#39"}

    def test_ESC_ENTITY_PATTERN_matches(self):
        """regex 必须捕获全部 5 entity 字面"""
        s = "&amp; &lt; &gt; &quot; &#39;"
        found = set(ESC_ENTITY_PATTERN.findall(s))
        assert found == {"amp", "lt", "gt", "quot", "#39"}
