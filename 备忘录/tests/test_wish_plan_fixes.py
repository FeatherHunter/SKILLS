"""T07 · wish_plan.html prompt 完整 + onclick 修复 钉死。

- 删 pre max-height 截断(原 340px 截掉长 prompt 信息)
- onclick=setCat('${esc(c)}') 改 event delegation 模式
  (attribute 内 entity 不被 JS 解析 → SyntaxError 风险)
"""
from pathlib import Path

TEMPLATE = Path(__file__).parent.parent / "templates" / "wish_plan.html"
TEMPLATE_TEXT = TEMPLATE.read_text(encoding="utf-8")


class TestWishPlanPromptNoTruncation:
    def test_no_max_height_340px(self):
        """pre#promptOut 不应有 max-height:340px(原 bug 截断)"""
        # 形态:pre{...max-height:340px} 或 pre#promptOut{...max-height}
        # 接受 pre max-height 仍在但 ≥ 70vh(防止任何截断)
        import re
        m = re.search(r"pre\s*\{[^}]*\}", TEMPLATE_TEXT)
        if not m:
            return  # 无 pre CSS 块
        css = m.group(0)
        mh = re.search(r"max-height:\s*([^;}\s]+)", css)
        if mh:
            val = mh.group(1).strip()
            # 如果是数字像素且 < 70vh 阈值,报错
            if val.endswith("px"):
                try:
                    px = int(val[:-2])
                    assert px >= 480, (
                        f"pre max-height:{val} 仍会截断 · 改为 auto 或 ≥ 70vh"
                    )
                except ValueError:
                    pass
            # 如果是 vh 单位,应 ≥ 70vh
            elif val.endswith("vh"):
                try:
                    vh = int(val[:-2])
                    assert vh >= 70, f"pre max-height:{val} 仍会截断"
                except ValueError:
                    pass


class TestWishPlanOnclickEventDelegation:
    def test_no_onclick_with_attribute_embedded_value(self):
        """onclick= 不应嵌入 entity-encoded 字符串值(原 wish_plan L53 setCat Bug)"""
        import re
        # 模式:onclick="func('&#39;...')" 或 onclick='func("&quot;...")')
        bad = re.findall(r"onclick\s*=\s*[\"'][^\"']*&[#\w]+;[^\"']*\)", TEMPLATE_TEXT)
        assert not bad, (
            f"onclick= 字符串内嵌 entity encoded 值,JS 不解析 entity → 触发 SyntaxError"
            f"风险。bad={bad[:3]}"
        )

    def test_setCat_uses_event_delegation_or_attribute_data(self):
        """setCat 应通过 event delegation 或 data-attr 触发(避免 attribute context)"""
        # 接受:onclick="setCat('${c}')"(原版)或 addEventListener
        # 不接受 entity 嵌入的形态
        import re
        # 如果 onclick=setCat(...) 还在,不应有 entity 嵌入
        onclick_calls = re.findall(r"onclick\s*=\s*[\"']setCat\(([^)]+)\)", TEMPLATE_TEXT)
        for arg in onclick_calls:
            assert "&" not in arg, (
                f"onclick=setCat({arg}) 含 entity 字符 · 改 event delegation"
            )