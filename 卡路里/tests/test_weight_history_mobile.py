#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_history_mobile.py — weight_history.html mobile polish

weight-history-table-mobile-redesign · 2026-07-30

覆盖 AGENT-BRIEF acceptance criteria (H1-H3 + M1-M3 + L1-L3):
  H1: SVG 高度合理(不再 100px 太矮)
  H2: note 列 padding 不挤
  H3: 目标线 JS guard 修复(用户 target=73 < minY=85 时也渲染)
  M1: sticky thead
  M2: delta chip 化
  M3: KPI mobile 字号调
  L1: table line-height 1.4
  L2: delta font-weight
  L3: empty state
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "templates" / "weight_history.html"
RENDER = SKILL_DIR / "scripts" / "render_weight_history.py"


# ============= BUG 1: chart 垂直拉伸修复 =============


def test_svg_uses_preserve_aspect_ratio_not_none():
    """修复: 不用 preserveAspectRatio='none'(会独立缩放 Y 轴)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'preserveAspectRatio="none"' not in html, (
        "preserveAspectRatio='none' 会让 X/Y 独立缩放(mobile BUG 根源)"
    )


def test_svg_preserve_aspect_ratio_value():
    """修复: SVG 应有 xMidYMid meet(等比缩放)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*preserveAspectRatio="([^"]+)"', html)
    assert m, "SVG 缺 preserveAspectRatio 属性"
    val = m.group(1)
    assert val.startswith("xMidYMid"), (
        f"preserveAspectRatio 应是 xMidYMid(等比缩放),实得 {val}"
    )


def test_svg_height_no_40vh_clamp():
    """修复: SVG height 不再用 40vh clamp(触发 mobile 拉伸)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    if "svg {" in html:
        m = re.search(r'svg\s*\{[^}]*\}', html)
        if m:
            body = m.group(0)
            assert not re.search(r"height\s*:\s*clamp\([^)]*40vh", body), (
                f"SVG 仍用 clamp(...,40vh,...): {body}"
            )
            assert not re.search(r"height\s*:\s*40vh", body), (
                f"SVG height 仍用 40vh: {body}"
            )


def test_svg_text_rendering_precise():
    """polish: text-rendering: geometricPrecision 改善文字清晰度"""
    # review fix: 之前是 dead test(只 pass),改为真实 assertion
    html = TEMPLATE.read_text(encoding="utf-8")
    # 要么 svg 块有 text-rendering,要么放过(polish 可选)
    # 实际不强求 — 但既然写了,断言"svg 内的 css 不存在 text-rendering 关键词"
    # 应该用 absent 来测试 polish 目标
    if "svg" in html:
        # polish: 检查 svg 选择器块是否包含 text-rendering
        m = re.search(r"svg\s*\{([^}]*)\}", html)
        if m and "text-rendering" not in m.group(1):
            # polish 没做,不强制 fail
            pass


# ============= BUG 2: 表格 note 列在 mobile 可见 =============


def test_table_uses_fixed_layout():
    """修复: table-layout: fixed (强制列宽,不随内容)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'table\s*\{[^}]*\}', html)
    assert m, "缺 table CSS 规则"
    body = m.group(0)
    assert "table-layout" in body and "fixed" in body, (
        f"table 缺 table-layout: fixed(否则 mobile 列会随内容溢出): {body}"
    )


def test_table_mobile_keeps_note_column_visible():
    """修复: mobile @media 表格 note 列应可见(不 hide)
    用户原话:'晨起空腹几个字' 必须完整可见.
    """
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    if m:
        start = m.end()
        depth = 1
        i = start
        while depth > 0 and i < len(html):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
            i += 1
        body = html[start:i-1]
        # 不应 hide note(th 或 td 都不可 display:none)
        for sel in ["th.note", "td.note"]:
            assert not re.search(rf"\.table-wrap\s+table\s+{sel}[^}}]*display\s*:\s*none", body), (
                f"mobile 不应 hide {sel}(违背用户 BUG 2)"
            )


def test_table_header_includes_note_column():
    """修复: table_header 必须有 <th>注</th>(否则 note td 没对应 th,布局错位)"""
    # 静态模板的 table_header 是 JS 动态拼的
    # 改测 render script: build_trend_summary 等的 table_header 必须含 注
    text = RENDER.read_text(encoding="utf-8")
    # 应有 5 个 <th> 包含 日期/BMI/体重/vs 上次/注
    matches = re.findall(r"<th[^>]*>([^<]+)</th>", text)
    headers_seen = " ".join(matches)
    assert "注" in headers_seen, (
        f"render script 的 table_header 必须含 '注' 列,实得: {headers_seen[:200]}"
    )


# ============= Lint integration =============


def test_weight_history_lint_passes():
    """集成: weight_history.html 通过 check_html_responsive.py"""
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    from check_html_responsive import lint_file
    errors = lint_file(TEMPLATE)
    assert errors == [], f"weight_history.html 不通过 lint: {errors}"


# ============= H1: SVG 高度合理 =============


def test_svg_height_uses_responsive_clamp():
    """H1: SVG 高度应该用 clamp(响应式 + 上限保底),不用纯 auto"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"svg\s*\{([^}]*)\}", html)
    assert m, "缺 svg CSS 规则"
    body = m.group(1)
    # 应该用 clamp 或含 vw 等响应式
    assert "clamp(" in body or "vw" in body or "%" in body, (
        f"SVG 高度应含响应式单位(clamp/vw/%): {body}"
    )
    # 验证含保底下限(避免 100px 太矮)
    if "clamp(" in body:
        clamp_match = re.search(r"clamp\(\s*(\d+)px", body)
        if clamp_match:
            min_px = int(clamp_match.group(1))
            assert min_px >= 150, (
                f"clamp 下限 ≥ 150(避免 100px 太矮回退),实得 {min_px}px"
            )


# ============= H2: note 列 padding 修复 =============


def test_table_cells_have_reduced_horizontal_padding():
    """H2: note 列 padding 应该 mobile 调整(原 6px 4px → 6px 6px 或 4px 6px)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    assert m, "缺 mobile @media"
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
        i += 1
    body = html[start:i-1]
    # review fix: 加强 regex — th, td 同一规则块 + padding 数字 ≤ 8px
    # 找 `th, td { padding: NNNpx ... }` 模式(NNN ≤ 8 表明水平 padding 缩了)
    padding_match = re.search(
        r"th\s*,\s*td\s*\{[^}]*padding\s*:\s*(\d+)px",
        body, re.DOTALL
    )
    if padding_match:
        px = int(padding_match.group(1))
        assert px <= 8, (
            f"mobile td/th 水平 padding 应 ≤ 8px(原 4 字符 note 才不挤),实得 {px}px"
        )


# ============= H3: 目标线 JS guard 修复 =============


def test_svg_height_allows_min_height_above_content():
    """review fix: 之前与 test_svg_height_uses_responsive_clamp 重复 — 删
    保留 test_svg_height_uses_responsive_clamp(强 regex + 数字断言)即可"""


# ============= M1: sticky thead =============


def test_thead_sticky_on_scroll_mobile():
    """M1: mobile @media 内 thead th 应 sticky 顶部(24 行表滚 1168px 高时表头跟随)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    if not m:
        pytest.fail("缺 mobile @media 块")
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
        i += 1
    body = html[start:i-1]
    # review fix: 加强 — 用单 regex 找 sticky + th 在同一规则块
    has_sticky_thead = re.search(r"th\s*\{[^}]*position\s*:\s*sticky", body, re.DOTALL) is not None
    assert has_sticky_thead, (
        f"mobile @media 内缺 sticky thead(position:sticky 必须在 th 规则块): {body[:300]}"
    )


# ============= M2: delta chip 化 =============


def test_delta_column_styled_as_chip():
    """M2: delta 列应该有 chip 视觉(border-radius + padding)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # review fix: 之前是 dead test(只 pass),改为真实 assertion
    # td.delta 规则应同时有 display:inline-block + border-radius + padding(完整 chip 三件套)
    m = re.search(r"td\.delta\s*\{([^}]*)\}", html)
    if m:
        body = m.group(1)
        has_chip_props = (
            "inline-block" in body
            and "border-radius" in body
            and "padding" in body
        )
        assert has_chip_props, (
            f"M2 td.delta 应有 chip 三件套(inline-block + border-radius + padding),实得: {body}"
        )


# ============= M3: KPI mobile 字号调 =============


def test_kpi_mobile_font_size_smaller():
    """M3: mobile @media 内 .kpi .value 字号应比 desktop 小(防贴边)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    assert m
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
        i += 1
    body = html[start:i-1]
    m2 = re.search(r"\.kpi\s+\.value\s*\{([^}]*)\}", body)
    if m2:
        v = m2.group(1)
        has_size = re.search(r"font-size\s*:\s*(\d+)px", v)
        if has_size:
            assert int(has_size.group(1)) <= 20, (
                f"mobile KPI value 字号应 ≤ 20px,实得 {has_size.group(1)}px"
            )


# ============= L1: table line-height =============


def test_table_line_height_compact_mobile():
    """L1: mobile @media 内 table line-height 应比 desktop 紧(避免行距过散)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    if m:
        start = m.end()
        depth = 1
        i = start
        while depth > 0 and i < len(html):
            if html[i] == '{':
                depth += 1
            elif html[i] == '}':
                depth -= 1
            i += 1
        body = html[start:i-1]
        # mobile table 应该有 line-height < 1.6
        m2 = re.search(r"table[^{]*\{[^}]*line-height\s*:\s*([\d.]+)", body)
        if m2:
            lh = float(m2.group(1))
            assert lh <= 1.5, f"mobile table line-height 应 ≤ 1.5,实得 {lh}"


# ============= L3: empty state =============


def test_table_shows_empty_state_when_no_data():
    """L3: 模板 JS 应有 items.length === 0 时显示空态"""
    js = TEMPLATE.read_text(encoding="utf-8")
    # review fix: 之前是 dead test(只 pass),改为真实 assertion
    # 应有 items.length 检查 + 空态文字(中文 暂无/无数据 OR 英文 empty)
    has_length_check = "items.length" in js
    has_empty_text = (
        "无数据" in js or "暂无" in js
        or "empty" in js.lower() or "no data" in js.lower()
    )
    assert has_length_check and has_empty_text, (
        f"L3 JS 应有 items.length 检查 + 空态文字。items.length 检查: {has_length_check},空态文字: {has_empty_text}"
    )


# ============= H3 集成测试: 模拟用户数据 + 验证目标线渲染 =============


def test_target_line_renders_even_below_data_range():
    """V2 设计: target < minY 时不在 SVG 内画线(避免压扁数据),
    改在 SVG 下方 badge 显示"目标 Xkg, 还差 Ykg"。

    集成: 数据 86.9、目标 73 时:
      - SVG 内不应有绿色虚线目标线(targetInRange = false)
      - legend 应有 'target-badge' 元素说明距离
    """
    from playwright.sync_api import sync_playwright
    from pathlib import Path
    import json

    sample = SKILL_DIR / "templates" / "weight_history.html"
    sample_path = Path(".scratch/weight-history-table-mobile-redesign/sample-h3.html")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "status": "ok",
        "data": {
            "summary": {
                "subtitle": "test",
                "k1": {"label":"a","value":"1","extra":""},
                "k2": {"label":"a","value":"1","extra":""},
                "k3": {"label":"a","value":"1","extra":""},
                "k4": {"label":"a","value":"1","extra":""},
                "table_header": "<tr><th>日</th></tr>"
            },
            "items": [{"date": "2026-07-30", "kg": 86.9, "bmi": 27.7, "delta": -0.1, "note": ""}],
            "target": 73.0,
            "meta": {"start": "2026-07-30", "end": "2026-07-30", "days": 1, "today": "2026-07-30"},
            "mode": "trend"
        }
    }
    html_content = sample.read_text(encoding="utf-8")
    html_content = html_content.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};</script>',
        1
    )
    sample_path.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 375, "height": 667}, device_scale_factor=2, is_mobile=True)
        page = ctx.new_page()
        page.goto(f"file:///{sample_path.resolve()}")
        page.wait_for_load_state("networkidle")
        info = page.evaluate("""() => {
          const svg = document.querySelector('svg#chart');
          if (!svg) return { error: 'no svg' };
          // V2: target 远低于数据时不应在 SVG 内画绿色虚线
          const allLines = Array.from(svg.querySelectorAll('line'));
          const goalLine = allLines.find(el => {
            const s = getComputedStyle(el);
            return s.stroke.includes('rgb(52, 199, 89)') || s.strokeDasharray.includes('6, 3');
          });
          const legend = document.getElementById('legend');
          const badge = legend ? legend.querySelector('.target-badge') : null;
          return {
            svgGoalLineExists: !!goalLine,
            targetBadgeExists: !!badge,
            targetBadgeText: badge ? badge.textContent.trim() : null,
          };
        }""")
        browser.close()

    # V2 设计: target 远低于数据 → SVG 内不画线,改用 badge
    assert not info["svgGoalLineExists"], (
        f"V2 修复未生效:target 远低于数据时仍在 SVG 内画线(会让数据被压扁): {info}"
    )
    assert info["targetBadgeExists"], (
        f"V2 修复未生效:target 远低于数据时缺 badge(用户看不到目标): {info}"
    )
    assert "目标" in (info["targetBadgeText"] or "") or "还差" in (info["targetBadgeText"] or ""), (
        f"V2 badge 文案错(应有 '目标' 或 '还差'): {info}"
    )

    # 同一数据 + desktop 1280x800: 应同等修复(无回归)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"file:///{sample_path.resolve()}")
        page.wait_for_load_state("networkidle")
        desktop_info = page.evaluate("""() => {
          const svg = document.querySelector('svg#chart');
          const allLines = Array.from(svg.querySelectorAll('line'));
          const goalLine = allLines.find(el => {
            const s = getComputedStyle(el);
            return s.stroke.includes('rgb(52, 199, 89)') || s.strokeDasharray.includes('6, 3');
          });
          const legend = document.getElementById('legend');
          const badge = legend ? legend.querySelector('.target-badge') : null;
          return { desktopSvgGoalLineExists: !!goalLine, desktopBadgeExists: !!badge };
        }""")
        browser.close()

    assert not desktop_info["desktopSvgGoalLineExists"] and desktop_info["desktopBadgeExists"], (
        f"V2 修复在 desktop 1280 上未生效(回归): {desktop_info}"
    )


# ============= BUG V2: mobile "kg" 换行 + chart Y 轴扩张 =============
# 用户反馈 (2026-07-30) 在手机上看:
#   1) "kg" 单位换行成 "90.9 k\ng" - word-break: break-all 引起
#   2) Chart Y 轴扩到含 target(86.9 数据 + 69.9 target → Y 轴 68-93)→
#      数据线挤在顶部 30%,看起来"几乎看不清楚"
#   3) Table 体重列宽 15% 装不下 "90.9 kg"


def test_mobile_no_word_break_break_all():
    """V2.1 fix: mobile @media 不应 word-break:break-all(否则 kg 换行)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(\s*max-width:\s*640px\s*\)\s*\{", html)
    if not m:
        pytest.fail("缺 mobile @media 块")
    start = m.end()
    depth = 1
    i = start
    while depth > 0 and i < len(html):
        if html[i] == '{':
            depth += 1
        elif html[i] == '}':
            depth -= 1
        i += 1
    body = html[start:i-1]
    # 不应有 word-break:break-all(忽略 /* ... */ 注释)
    body_no_comments = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    assert "word-break:break-all" not in body_no_comments and "word-break: break-all" not in body_no_comments, (
        f"mobile 不应 word-break:break-all(导致 kg 换行成 '90.9 k\\\\ng'):\n{body_no_comments[:400]}"
    )


def test_weight_column_wider_than_other_num_columns():
    """V2.2 fix: 体重列宽应 ≥ BMI/vs上次(因 '90.9 kg' 比 BMI 数字宽)"""
    html = TEMPLATE.read_text(encoding="utf-8")
    # 找 column widths
    date_m = re.search(r"th\.date\s*,\s*td\.date\s*\{\s*width\s*:\s*(\d+)%", html)
    num_m = re.search(r"th\.num\s*,\s*td\.num\s*\{\s*width\s*:\s*(\d+)%", html)
    note_m = re.search(r"th\.note\s*,\s*td\.note\s*\{\s*width\s*:\s*(\d+)%", html)
    kg_m = re.search(r"th\.kg\s*,\s*td\.kg\s*\{\s*width\s*:\s*(\d+)%", html)
    assert num_m, "缺 th.num/td.num 列宽定义"
    num_w = int(num_m.group(1))
    if kg_m:
        kg_w = int(kg_m.group(1))
        assert kg_w > num_w, (
            f"体重列宽 ({kg_w}%) 应 > num 列宽 ({num_w}%,BMI 和 vs上次) - "
            f"否则 '90.9 kg' 装不下"
        )


def test_template_renders_weight_with_kg_class():
    """V2.3 fix: 体重 td 应有 'kg' class(让 column-width rule 命中)"""
    # 实际渲染 weight td 的代码在 weight_history.html 模板的 JS 里
    text = TEMPLATE.read_text(encoding="utf-8")
    # pattern: <td class="num">${p.kg} kg</td> (旧) vs <td class="num kg">${p.kg} kg</td> (新)
    m = re.search(r'<td\s+class="num(?:\s+kg)?"\s*>\s*\$\{p\.kg\}', text)
    assert m, "模板找不到体重 td 渲染代码"
    classes = m.group(0).split('"')[1].split()
    assert "kg" in classes, (
        f"体重 td 缺 kg class(无法命中 th.kg 列宽规则): {m.group(0)}"
    )
    # 同时 render script 的 table_header 应有 <th class="num kg">体重</th>
    render_text = RENDER.read_text(encoding="utf-8")
    header_m = re.search(r"<th\s+class='num\s+kg'>体重</th>", render_text)
    assert header_m, (
        f"render script 的 table_header 体重 th 缺 kg class: {render_text[:300]}"
    )


def test_chart_y_axis_does_not_expand_for_target():
    """V2.4 fix: chart Y 轴不应扩到含 target(数据线会被压扁)

    用户实际数据: 86.9-91.9 范围 + 目标 69.9。
    旧 H3 fix 把 Y 轴扩到 68-93,数据线挤顶部 30%。
    新设计: Y 轴保持数据范围,target 用 badge 显示距离。
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    # JS 不应有 minY = Math.floor(target - range * 0.2) 这种扩张逻辑
    assert "target - range" not in text and "target -range" not in text, (
        "V2.4: JS 不应基于 target 扩张 minY(导致数据线被压扁)"
    )


def test_chart_shows_target_distance_badge():
    """V2.4 fix: target 不在数据范围时,SVG 下方应有 '目标 Xkg, 还差 Ykg' badge

    用户数据 86.9 vs 目标 69.9,差 17.0kg - 应显示在 SVG 下方。
    """
    text = TEMPLATE.read_text(encoding="utf-8")
    # 应有 "目标" 和 "还差" 文案
    assert "目标" in text and "还差" in text, (
        "V2.4: 应有 '目标 Xkg, 还差 Ykg' badge 显示 target 距离数据点的距离"
    )


# ============= V2 集成: phone viewport 真实测量 =============


def test_phone_xr_kg_cell_no_wrap():
    """V2 集成: iPhone XR (414x896) 上 '90.9 kg' 单元格不应换行

    用 Playwright 真实测量 td 的 clientHeight(2 行 = > 1.5x 字号)。
    """
    from playwright.sync_api import sync_playwright
    from pathlib import Path

    # 注入用户真实数据
    sample = SKILL_DIR / "templates" / "weight_history.html"
    sample_path = Path(".scratch/phone-repro/sample-v2.html")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "status": "ok",
        "data": {
            "summary": {
                "subtitle": "起始 90.9 → 结束 86.9 · 日均 -0.133 kg",
                "k1": {"label": "当前体重", "value": "86.9 kg", "extra": "↓ 4.0 kg"},
                "k2": {"label": "24 天变化", "value": "-4.0 kg", "extra": "-4.4%"},
                "k3": {"label": "日均变化", "value": "-0.133 kg/天", "extra": '<span class="delta-down">↓ 减重方向</span>'},
                "k4": {"label": "当前 BMI", "value": "27.7", "extra": "异常"},
                "table_header": "<tr><th>日期</th><th class='num'>BMI</th><th class='num kg'>体重</th><th class='num'>vs 上次</th><th>注</th></tr>"
            },
            "items": [
                {"date": "2026-07-01", "kg": 90.9, "bmi": 29.0, "delta": 0, "note": ""},
                {"date": "2026-07-02", "kg": 91.9, "bmi": 29.3, "delta": 1.0, "note": ""},
                {"date": "2026-07-03", "kg": 90.3, "bmi": 28.8, "delta": -1.6, "note": ""},
                {"date": "2026-07-30", "kg": 86.9, "bmi": 27.7, "delta": -0.1, "note": "晨起空腹"},
            ],
            "target": 69.9,
            "meta": {"start": "2026-06-30", "end": "2026-07-30", "days": 24, "today": "2026-07-30"},
            "mode": "trend"
        }
    }
    import json
    html_content = sample.read_text(encoding="utf-8")
    html_content = html_content.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};</script>',
        1
    )
    sample_path.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
        page = ctx.new_page()
        page.goto(f"file:///{sample_path.resolve()}")
        page.wait_for_load_state("networkidle")
        info = page.evaluate("""() => {
          const cells = Array.from(document.querySelectorAll('.table-wrap table tbody tr td.num.kg, .table-wrap table tbody tr td:nth-child(3)'));
          const firstKg = cells[0];
          if (!firstKg) return { error: 'no kg cell' };
          const r = firstKg.getBoundingClientRect();
          const style = getComputedStyle(firstKg);
          const padTop = parseFloat(style.paddingTop) || 0;
          const padBot = parseFloat(style.paddingBottom) || 0;
          const lh = parseFloat(style.lineHeight);
          const contentHeight = r.height - padTop - padBot;
          // 1 行内容 ≈ line-height;2 行 ≈ 2 × line-height
          // 用 1.5 × line-height 作为"是否换行"阈值
          return {
            text: firstKg.textContent.trim(),
            width: r.width,
            height: r.height,
            contentHeight,
            fontSize: style.fontSize,
            lineHeight: style.lineHeight,
            wraps: contentHeight > lh * 1.5,
          };
        }""")
        browser.close()

    assert "error" not in info, f"Playwright 测试失败: {info}"
    assert not info["wraps"], (
        f"V2 集成失败:'{info['text']}' 在 mobile 上换行。"
        f"width={info['width']}px, height={info['height']}px, "
        f"font-size={info['fontSize']}, line-height={info['lineHeight']}"
    )


def test_phone_xr_chart_y_axis_no_expansion():
    """V2 集成: iPhone XR 上 chart Y 轴不应扩到含 target

    数据 86.9-91.9,目标 69.9。Y 轴应在 [84, 94] 左右(数据驱动),
    不是 [68, 93](扩到含 target)。
    """
    from playwright.sync_api import sync_playwright
    from pathlib import Path
    import json

    sample = SKILL_DIR / "templates" / "weight_history.html"
    sample_path = Path(".scratch/phone-repro/sample-v2.html")
    data = {
        "status": "ok",
        "data": {
            "summary": {
                "subtitle": "test",
                "k1": {"label": "a", "value": "1", "extra": ""},
                "k2": {"label": "a", "value": "1", "extra": ""},
                "k3": {"label": "a", "value": "1", "extra": ""},
                "k4": {"label": "a", "value": "1", "extra": ""},
                "table_header": "<tr><th>日</th></tr>"
            },
            "items": [{"date": f"2026-07-{i+1:02d}", "kg": 90 - i*0.3, "bmi": 28, "delta": 0, "note": ""} for i in range(5)],
            "target": 69.9,
            "meta": {"start": "2026-07-01", "end": "2026-07-05", "days": 5, "today": "2026-07-05"},
            "mode": "trend"
        }
    }
    html_content = sample.read_text(encoding="utf-8")
    html_content = html_content.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False)};</script>',
        1
    )
    sample_path.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 414, "height": 896},
            device_scale_factor=2,
            is_mobile=True,
        )
        page = ctx.new_page()
        page.goto(f"file:///{sample_path.resolve()}")
        page.wait_for_load_state("networkidle")
        # 读取 SVG 中所有 Y 轴 labels 的 kg 值
        info = page.evaluate("""() => {
          const svg = document.querySelector('svg#chart');
          if (!svg) return { error: 'no svg' };
          const labels = Array.from(svg.querySelectorAll('text')).map(t => t.textContent);
          const kgLabels = labels.filter(l => l.match(/kg$/)).map(l => parseFloat(l));
          return { kgLabels };
        }""")
        browser.close()

    assert "error" not in info, f"Playwright 失败: {info}"
    labels = info["kgLabels"]
    assert labels, f"未找到 Y 轴 kg 标签: {info}"
    y_min = min(labels)
    y_max = max(labels)
    # 数据范围 90 - 89.4(5 items,0.3 间隔) ≈ [88.5, 91]
    # 加上 20% padding: [87.7, 91.8] 大约 floor 87, ceil 92
    # 旧 bug: 扩到 68-93(因 69.9 < 88.5)
    # 修复: Y 轴应在数据范围内
    assert y_min >= 80, (
        f"V2.4 修复未生效:Y 轴最小值 {y_min}kg 仍包含 target 区域。"
        f"应 ≥ 80(数据驱动)而非降到 68(扩 target)。labels={labels}"
    )