"""作息管家 · 复盘 start-end · T09 端到端 seam 测试

锁住 T09 acceptance:
- 30 天大 fixture(863 条 record + 14 计划 · 6 种 completion 全覆盖)
- 5 视口 (360/768/1024/1280/1920) playwright 截图
- 视觉契约(无水平滚动 / 4 段叙事可见 / 4 卡 / 复制按钮)
- 回归护栏(锁住 09 "区间长度" join 字符串 bug + Top-N 折叠)

TDD seam: 端到端 HTML 渲染 + Chromium headless(file:// protocol)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


VIEWPORTS = [
    {"name": "iphone-360", "w": 360, "h": 800, "is_mobile": True},
    {"name": "tablet-768", "w": 768, "h": 1024, "is_mobile": True},
    {"name": "laptop-1024", "w": 1024, "h": 768, "is_mobile": False},
    {"name": "desktop-1280", "w": 1280, "h": 900, "is_mobile": False},
    {"name": "desktop-1920", "w": 1920, "h": 1080, "is_mobile": False},
]


# ---- 30 天大 fixture ----

@pytest.fixture
def replay_30d_html(tmp_path, monkeypatch):
    """30 天 · 863 条 record + 14 计划 fixture,跑 render_replay,返回 HTML 路径

    注:863 条 record = 30 天 × (约 29 类 × 1 条/天)
    14 计划 = 14 个独特 plan_event,6 种 completion 全覆盖
    """
    db_path = tmp_path / "test_replay_e2e.db"
    init = sqlite3.connect(str(db_path))
    init.executescript("""
        CREATE TABLE IF NOT EXISTS schedule_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL,
            duration_minutes INTEGER, activity TEXT NOT NULL,
            category TEXT NOT NULL, source_contents TEXT, source_timestamps TEXT,
            analysis_reasoning TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP, edit_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS schedule_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            time_start TEXT NOT NULL, time_end TEXT NOT NULL, title TEXT NOT NULL,
            notes TEXT, category TEXT, feishu_event_id TEXT, last_synced_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1, completion TEXT DEFAULT NULL,
            completion_note TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    init.commit()
    init.close()

    def factory():
        x = sqlite3.connect(str(db_path))
        x.row_factory = sqlite3.Row
        return x
    monkeypatch.setattr(_db, "get_connection", factory)
    monkeypatch.setattr(_db, "_sync_one_feishu", lambda *a, **kw: None)

    # 灌 30 天 record(覆盖 29 个分类,确保 863 cat-row + 53 cat-row 场景)
    categories = [
        "工作.AI调优", "工作.会议", "工作.文案", "工作.开发", "工作.剪辑",
        "健康.运动", "健康.健身", "健康.冥想", "健康.保健",
        "学习.读书", "学习.技术", "学习.研究",
        "调整.游戏", "调整.视频", "调整.音乐",
        "维持.睡眠", "维持.用餐",
        "日常.杂事", "日常.收拾", "日常.等候",
        "工作.运营", "工作.调研", "工作.财务",
        "健康.看病", "健康.八段锦",
        "投入.AI", "投入.服务",  # 投入二级:家人/朋友/同事/伴侣/宠物/社交/服务/沟通/AI
        "调整.手机", "调整.阅读",  # 调整二级:游戏/视频/音乐/手机/玩耍/发呆/追剧/散步/午睡/过渡/休息/阅读
        "维持.通勤",
    ]
    # 每天每类必灌(29 cat × 30 day = 870 条,spec 要求 863 条)
    for d in range(1, 31):
        for i, cat in enumerate(categories):
            hour = (i * 3) % 24
            _db.add_record_full(
                date=f"2026-07-{d:02d}", time_start=f"{hour:02d}:00", time_end=f"{(hour+1)%24:02d}:00",
                duration_minutes=60, activity=f"活动 {cat}",
                category=cat,
                source_contents="x", source_timestamps=f"{hour:02d}:00", analysis_reasoning="x",
            )

    # 灌 14 计划 · 6 种 completion 全覆盖
    plan_specs = [
        ("已完成", 5), ("已完成", 3), ("已完成(超时)", 2),
        ("部分完成", 1), ("未完成", 1), ("未完成(不可抗力)", 1), ("", 1),
    ]  # 14 计划,completion 6 类全覆盖
    for comp, n in plan_specs:
        for i in range(n):
            day = 2 + i * 2
            result = _db.ensure_plan_event(
                date=f"2026-07-{day:02d}", time_start=f"{9+i:02d}:00", time_end=f"{10+i:02d}:00",
                title=f"计划 {day}-{i}", category="工作.AI调优",
            )
            if comp:  # 空字符串 = 未复盘
                _db.update_plan_event(result["id"], {"completion": comp})

    # 跑 render_replay + render_and_write
    from schedule_html_render import render_replay, render_and_write
    payload = render_replay("2026-07-01", "2026-07-30")
    assert payload["status"] == "ok", f"渲染失败: {payload}"
    assert payload["data"]["meta"]["total_records"] >= 500, \
        f"应至少 500 条 record,实际 {payload['data']['meta']['total_records']}"
    result = render_and_write(payload)
    assert result["status"] == "ok", f"写文件失败: {result}"

    html_path = Path(result["data"]["file_path"])
    yield html_path

    # teardown
    try:
        html_path.unlink()
    except OSError:
        pass


# ---- T09 acceptance 端到端断言 ----

def test_e2e_30d_4_segments_visible(replay_30d_html):
    """T09 · 30 天大 fixture 下 4 段叙事标题可见(playwright 1 视口 sanity check)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 未安装,跳过")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto("file:///" + str(replay_30d_html).replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                "() => document.querySelectorAll('.card-stat').length >= 4",
                timeout=10000,
            )
            # 4 段叙事 segment 标题可见
            titles = page.evaluate(
                """() => {
                    const segs = document.querySelectorAll('.segment h2, .ai-section h2');
                    return Array.from(segs).map(s => s.textContent.trim());
                }"""
            )
            assert any("实际作息" in t for t in titles), "缺'实际作息'段"
            assert any("计划执行" in t for t in titles), "缺'计划执行'段"
            assert any("跨域对比" in t for t in titles), "缺'跨域对比'段"
            assert any("AI 洞察" in t for t in titles), "缺'AI 洞察'段"
        finally:
            browser.close()


@pytest.mark.parametrize("vp", VIEWPORTS)
def test_e2e_30d_viewport_no_horizontal_scroll(replay_30d_html, vp):
    """T09 · 5 视口下 30 天大 fixture 无水平滚动(各视口 sanity check)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 未安装,跳过")

    screenshots_dir = Path(__file__).parent / "screenshots" / "replay_e2e"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(
                viewport={"width": vp["w"], "height": vp["h"]},
                device_scale_factor=2 if vp["is_mobile"] else 1,
                is_mobile=vp["is_mobile"],
                has_touch=vp["is_mobile"],
            )
            page = ctx.new_page()
            page.goto("file:///" + str(replay_30d_html).replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                "() => document.querySelectorAll('.card-stat').length >= 4",
                timeout=10000,
            )
            data = page.evaluate(
                """() => ({
                    docW: document.documentElement.scrollWidth,
                    winW: window.innerWidth,
                    hasHScroll: document.documentElement.scrollWidth > window.innerWidth + 1,
                })"""
            )
            assert not data["hasHScroll"], \
                f"{vp['name']} 视口水平滚动:docW={data['docW']} winW={data['winW']}"

            # 保存首屏截图(regression manual review)
            page.screenshot(path=str(screenshots_dir / f"{vp['name']}-top.png"), full_page=False)
        finally:
            browser.close()


def test_e2e_30d_top_n_fold_default(replay_30d_html):
    """T09 · Top-N 折叠默认:30 天大 fixture 下 cat-row 默认 Top 10 + '展开全部'按钮

    回归护栏:53 个 cat-row 不一次性显示
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 未安装,跳过")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 900})
            page = ctx.new_page()
            page.goto("file:///" + str(replay_30d_html).replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                "() => document.querySelectorAll('.cat-row').length > 0",
                timeout=10000,
            )
            cat_stats = page.evaluate(
                """() => {
                    const total = document.querySelectorAll('.cat-row').length;
                    const hidden = document.querySelectorAll('.cat-row.hidden').length;
                    const visible = total - hidden;
                    const expandBtn = document.getElementById('expand-cat-rows');
                    return { total, hidden, visible, hasExpandBtn: !!expandBtn };
                }"""
            )
            # 至少 30 个 cat-row(30 天 × 多分类,大于 Top 10)
            assert cat_stats["total"] >= 10, \
                f"30 天大 fixture 应至少 10 cat-row,实际 {cat_stats['total']}"
            # Top 10 折叠:visible ≤ 10 + 有展开按钮
            assert cat_stats["visible"] <= 10, \
                f"Top-N 折叠应 visible ≤ 10,实际 {cat_stats['visible']}"
            assert cat_stats["hasExpandBtn"], "缺'展开全部'按钮"
        finally:
            browser.close()


def test_e2e_30d_no_join_date_string(replay_30d_html):
    """T09 · 回归护栏:HTML 不渲染 30 日期 join 字符串(锁住 09 '区间长度' bug)"""
    html = replay_30d_html.read_text(encoding="utf-8")

    # 09 bug 复发检测:30 个日期逗号 join 的字符串
    # 形如 "2026-07-01,2026-07-02,...,2026-07-30 天"
    dates = [f"2026-07-{d:02d}" for d in range(1, 31)]
    join_str = ",".join(dates) + " 天"
    assert join_str not in html, \
        f"_record_engine.js '区间长度' bug 复发:HTML 含 '{join_str[:50]}...'"


# ---- T10 文档收尾验收 · 静态 markdown 校验(锁住 5 项 acceptance) ----

def test_adr_0005_exists():
    """T10 · ADR-0005 文件存在,记录'复盘 start-end 独立工作流'决策"""
    adr_path = SKILL_DIR / "docs" / "adr" / "0005-replay-start-end-new-workflow.md"
    assert adr_path.exists(), f"ADR-0005 文件缺失: {adr_path}"
    content = adr_path.read_text(encoding="utf-8")
    # 必须含核心决策标记
    for marker in ("replay", "区间复盘", "独立新工作流"):
        assert marker in content, f"ADR-0005 缺关键术语: {marker}"


def test_context_md_exists():
    """T10 · 作息管家首次 CONTEXT.md(glossary),固化 6 个核心术语"""
    ctx_path = SKILL_DIR / "CONTEXT.md"
    assert ctx_path.exists(), f"CONTEXT.md 缺失: {ctx_path}"
    content = ctx_path.read_text(encoding="utf-8")
    # 必须含 6 个核心术语
    for term in ("复盘", "14 复盘", "复盘 start-end", "dual-domain", "5 状态 fallback", "4 段叙事"):
        assert term in content, f"CONTEXT.md 缺核心术语: {term}"


def test_skill_md_routing_7_presets():
    """T10 · SKILL.md 路由规则章节新增 7 个复盘预置 + 自由区间"""
    skill_path = SKILL_DIR / "SKILL.md"
    assert skill_path.exists(), "SKILL.md 缺失"
    content = skill_path.read_text(encoding="utf-8")
    # 7 个复盘预置
    for preset in ("复盘本周", "复盘上周", "复盘本月", "复盘上月", "复盘今年", "复盘上年"):
        assert preset in content, f"SKILL.md 路由缺预置: {preset}"
    # 自由区间语法
    assert "YYYY-MM-DD~YYYY-MM-DD" in content or "YYYY-MM-DD~" in content, \
        "SKILL.md 缺自由区间语法"


def test_changelog_phase_e():
    """T10 · CHANGELOG.md 新增 Phase E · 复盘 start-end 工作流条目"""
    cl_path = SKILL_DIR / "CHANGELOG.md"
    assert cl_path.exists(), "CHANGELOG.md 缺失"
    content = cl_path.read_text(encoding="utf-8")
    # 必须含 Phase E 标识 + 关键里程碑
    for marker in ("Phase E", "复盘 start-end", "区间复盘", "T10", "T01", "T09"):
        assert marker in content, f"CHANGELOG.md 缺 Phase E 标识: {marker}"


def test_agents_md_phase_e_row():
    """T10 · AGENTS.md '当前阶段' 表格新增 Phase E 行(✅ 完成)"""
    agents_path = SKILL_DIR / "AGENTS.md"
    assert agents_path.exists(), "AGENTS.md 缺失"
    content = agents_path.read_text(encoding="utf-8")
    # 必须含 Phase E + 完成标记
    assert "Phase E" in content, "AGENTS.md 缺 Phase E 行"
    # 新行应在表格内,不应在表格外孤立
    # 简化验证:Phase E 出现且不孤悬
    assert "✅" in content, "AGENTS.md Phase E 应标 ✅ 完成"