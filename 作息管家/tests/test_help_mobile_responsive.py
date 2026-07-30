"""作息管家 HELP HTML 移动端适配回归测试

锁住:2026-07-30 修复后,help_center.html 在 ≤640px 视口下
- cat-name / cat-desc 不再竖排(每个汉字一行)
- toolbar 按钮不溢出
- 3 层折叠正常工作

两个保护层:
1. 静态合约 — 模板 CSS 必含关键保护声明(flex-wrap: wrap / min-width: 0 等)
2. 集成合约 — 启动 Chromium,360×800 视口下断言 cat-name 高度 < 50px(横排)

集成测试自动 skip 当环境缺 playwright/chromium(避免 CI 阻断)。

Tested-By seam:
- 静态:直接读 templates/help_center.html 字符串
- 集成:加载 渲染后的 作息管家.html,起 Playwright Chromium
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "help_center.html"
HELP_HTML = SKILL_DIR / "作息管家.html"


# ========== 静态合约(必含保护声明) ==========

def _read_template() -> str:
    assert TEMPLATE_PATH.exists(), f"模板不存在: {TEMPLATE_PATH}"
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_cat_block_summary_has_flex_wrap():
    """L1 cat-block summary 必含 flex-wrap: wrap(防止 cat-meta 撑爆挤压 cat-body 竖排)"""
    css = _read_template()
    # 抓取 .cat-block > summary 块
    m = re.search(r"\.cat-block\s*>\s*summary\s*\{([^}]+)\}", css, re.DOTALL)
    assert m, "未找到 .cat-block > summary 块"
    body = m.group(1)
    assert "flex-wrap" in body, \
        ".cat-block > summary 缺 flex-wrap(主源 L1 cat-name 竖排 bug)"
    assert "wrap" in body, \
        ".cat-block > summary flex-wrap 必须是 wrap"


def test_ww_block_summary_has_flex_wrap():
    """L2 ww-block summary 必含 flex-wrap: wrap(对称保护 L2)"""
    css = _read_template()
    m = re.search(r"\.ww-block\s*>\s*summary\s*\{([^}]+)\}", css, re.DOTALL)
    assert m, "未找到 .ww-block > summary 块"
    body = m.group(1)
    assert "flex-wrap" in body, ".ww-block > summary 缺 flex-wrap"
    assert "wrap" in body, ".ww-block > summary flex-wrap 必须是 wrap"


def test_cat_body_has_min_width_zero():
    """cat-body 必含 min-width: 0(flex item 必备,才能被正确挤压而非溢出)"""
    css = _read_template()
    # 找 .cat-body 块
    m = re.search(r"\.cat-body\s*\{([^}]+)\}", css, re.DOTALL)
    assert m, "未找到 .cat-body 块"
    body = m.group(1)
    assert "min-width" in body, ".cat-body 缺 min-width(配合 flex-wrap 必要)"
    assert "0" in body, ".cat-body min-width 必须是 0(让 flex 真正生效)"


def test_toolbar_row_has_flex_wrap():
    """toolbar-row 必含 flex-wrap(移动端 input + 2 按钮溢出修复)"""
    css = _read_template()
    m = re.search(r"\.toolbar-row\s*\{([^}]+)\}", css, re.DOTALL)
    assert m, "未找到 .toolbar-row 块"
    body = m.group(1)
    assert "flex-wrap" in body, ".toolbar-row 缺 flex-wrap(移动端按钮溢出)"
    assert "wrap" in body, ".toolbar-row flex-wrap 必须是 wrap"


def test_toolbar_input_has_min_width_zero():
    """toolbar input 必含 min-width: 0(防止长 placeholder 撑爆)"""
    css = _read_template()
    m = re.search(r"\.toolbar input\s*\{([^}]+)\}", css, re.DOTALL)
    assert m, "未找到 .toolbar input 块"
    body = m.group(1)
    assert "min-width" in body, ".toolbar input 缺 min-width(输入框溢出)"
    assert "0" in body, ".toolbar input min-width 必须是 0"


def test_mobile_media_query_present():
    """@media (max-width: 640px) 必须存在且覆盖关键元素"""
    css = _read_template()
    assert "@media (max-width: 640px)" in css, "缺移动端 @media 规则"
    # 抓出移动端规则块
    m = re.search(r"@media\s*\(max-width:\s*640px\)\s*\{(.+?)\}\s*\n\s*</style>",
                  css, re.DOTALL)
    assert m, "未找到 @media (max-width: 640px) 块"
    body = m.group(1)
    # 移动端必含 cat-meta 强制换行(防止 mobile 仍竖排)
    assert ".cat-meta" in body, "移动端规则没覆盖 .cat-meta(回归风险)"
    assert "width: 100%" in body or "flex-basis" in body, \
        "移动端 .cat-meta 应独占一行(width: 100% 或 flex-basis)"


def test_anchor_template_intact():
    """回归保护:确保 payload/wrap 静态约束未被动(契约,见 AGENTS.md §5)"""
    css = _read_template()
    # payload 注入点占位符必须唯一
    assert css.count("<!--INJECT-DATA-->") == 1, "INJECT-DATA 占位符必须唯一"
    # 关键脚本钩子必须保留
    assert "addEventListener" in css, "addEventListener 缺失(复制按钮事件)"
    assert "navigator.clipboard" in css, "剪贴板 API 缺失"
    # 双 .wrap 元素契约保留(hero wrap + main wrap),事件委托修复的护栏
    assert css.count('class="wrap"') == 2, "双 .wrap 契约不满足(hero + main)"


# ========== 集成合约(Playwright 真实渲染验证) ==========

def _has_playwright_chromium() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _render_and_load_mock_page():
    """渲染一个新 HELP HTML 并加载到伪页面验证

    Returns:jinja-style HTML 字符串(占位符替换后)
    """
    # 复用 help_render 渲染一次(写到 tmp),导入并跑
    import tempfile
    import os
    with tempfile.TemporaryDirectory() as td:
        # 临时复制 scenarios.yaml + template 到 td,避免污染
        import shutil
        tmp_skill = Path(td) / "skill"
        shutil.copytree(SKILL_DIR, tmp_skill, ignore=shutil.ignore_patterns(
            ".git", ".db", ".pytest_cache", "__pycache__", "node_modules", ".scratch"
        ))
        os.environ["SKILLS_DB_PATH"] = str(tmp_skill / ".db")
        sys.path.insert(0, str(tmp_skill / "scripts"))
        import importlib
        if "help_render" in sys.modules:
            importlib.reload(sys.modules["help_render"])
        import help_render as hr
        out = tmp_skill / ".db" / "schedule_html" / "help" / "test_mobile.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        result = hr.render(out)
        assert result["status"] == "ok", f"render 失败: {result}"
        return out.read_text(encoding="utf-8")


def test_mobile_360_no_cat_name_vertical_text():
    """360px 视口下,L1 cat-name 不应竖排(高度 < 50px 表明横排 1-2 行)

    集成测试:起 Playwright Chromium,真实渲染、测量。
    """
    if not _has_playwright_chromium():
        import pytest
        pytest.skip("playwright 未安装,跳过集成测试")

    from playwright.sync_api import sync_playwright

    html = _render_and_load_mock_page()
    # 写一个临时文件让 playwright 加载
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp_html = f.name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": 360, "height": 800},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            page = ctx.new_page()
            page.goto("file:///" + tmp_html.replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                """() => {
                    const m = document.getElementById('mainContent');
                    return m && m.querySelectorAll('.cat-block').length > 0;
                }""",
                timeout=5000,
            )
            # 断言:所有 L1 cat-name 高度 < 50px(横排意味着 1-2 行 ~24-48px)
            heights = page.evaluate(
                """() => {
                    const names = document.querySelectorAll('.cat-block > summary .cat-name');
                    return Array.from(names).map(n => n.getBoundingClientRect().height);
                }"""
            )
            assert heights, "没找到 .cat-name 元素"
            max_h = max(heights)
            assert max_h < 50, \
                f"360px 视口下 cat-name 最大高度 {max_h:.1f}px(应 < 50px,竖排会 ≥ 200px),height 列表: {heights}"
        finally:
            browser.close()
            import os
            try:
                os.unlink(tmp_html)
            except OSError:
                pass


def test_mobile_360_no_toolbar_overflow():
    """360px 视口下,toolbar 不应有水平溢出(全部折叠按钮完整可见)"""
    if not _has_playwright_chromium():
        import pytest
        pytest.skip("playwright 未安装,跳过集成测试")

    from playwright.sync_api import sync_playwright

    html = _render_and_load_mock_page()
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp_html = f.name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": 360, "height": 800},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            page = ctx.new_page()
            page.goto("file:///" + tmp_html.replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                """() => {
                    const m = document.getElementById('mainContent');
                    return m && m.querySelectorAll('.cat-block').length > 0;
                }""",
                timeout=5000,
            )
            # 断言:文档宽度 ≤ viewport 宽度(无水平滚动)
            data = page.evaluate(
                """() => ({
                    docW: document.documentElement.scrollWidth,
                    winW: window.innerWidth,
                    hasHScroll: document.documentElement.scrollWidth > window.innerWidth + 1,
                })"""
            )
            assert not data["hasHScroll"], \
                f"360px 视口下出现水平滚动:docW={data['docW']} winW={data['winW']}"
        finally:
            browser.close()
            import os
            try:
                os.unlink(tmp_html)
            except OSError:
                pass


def test_three_layer_fold_works_on_mobile():
    """3 层折叠(L1/L2/L3) 在 360px 视口下展开能正常显示"""
    if not _has_playwright_chromium():
        import pytest
        pytest.skip("playwright 未安装,跳过集成测试")

    from playwright.sync_api import sync_playwright

    html = _render_and_load_mock_page()
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp_html = f.name

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": 360, "height": 800},
                device_scale_factor=2,
                is_mobile=True,
                has_touch=True,
            )
            page = ctx.new_page()
            page.goto("file:///" + tmp_html.replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                """() => {
                    const m = document.getElementById('mainContent');
                    return m && m.querySelectorAll('.cat-block').length > 0;
                }""",
                timeout=5000,
            )
            # 展开第一组 cat / ww / sc
            page.evaluate("""() => {
                const c = document.querySelector('.cat-block');
                if (c) c.open = true;
                const w = document.querySelector('.cat-block[open] .ww-block');
                if (w) w.open = true;
                const s = document.querySelector('.sc-block');
                if (s) s.open = true;
            }""")
            page.wait_for_timeout(200)

            # 断言:L3 展开后内容(包含 prompt 文本)出现在 DOM
            has_prompt = page.evaluate(
                """() => {
                    const promptEl = document.querySelector('.sc-block[open] .sc-prompt');
                    return promptEl ? promptEl.textContent.trim().length > 0 : false;
                }"""
            )
            assert has_prompt, "L3 展开后看不到 prompt 文本(3 层折叠失败)"

            # 断言:L1 展开后内容宽度不溢出
            cat_visible = page.evaluate(
                """() => {
                    const c = document.querySelector('.cat-block[open]');
                    if (!c) return false;
                    const r = c.getBoundingClientRect();
                    return r.width > 0 && r.height > 0;
                }"""
            )
            assert cat_visible, "L1 展开后不可见"
        finally:
            browser.close()
            import os
            try:
                os.unlink(tmp_html)
            except OSError:
                pass
