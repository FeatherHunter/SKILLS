"""作息管家 · 复盘 start-end · T08 视觉/UX 端到端断言

锁住 T08 acceptance:
- 顶部 4 卡总览(总时长 / 记录数 / 完成率 / 健康分)
- 复制 prompt 4 部分结构按钮 + 剪贴板降级
- 移动端 (360px) / 平板 (768px) / 桌面 (1280px+) 适配
- 5 状态徽章(✅ ok / 📭 empty / ⚠️ incomplete / ❌ error / 📡 offline)
- 4 段叙事渲染( record_aggregate / plan_aggregate / cross_domain / ai_insights)

TDD seam:HTML 渲染输出(file:// protocol + playwright headless)
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


# ---- 共享 fixture:灌 fixture 数据 + 渲染完整 HTML ----

@pytest.fixture
def replay_html_file(tmp_path, monkeypatch):
    """灌 14 天 fixture,跑 render_replay + render_and_write,返回 HTML 路径"""
    import sqlite3
    db_path = tmp_path / "test_replay_visual.db"
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

    # 灌 14 天数据:工作 + 睡眠 + 健身 各一天 + 1 条 plan 已完成
    for d in range(1, 15):
        _db.add_record_full(
            date=f"2026-07-{d:02d}", time_start="09:00", time_end="10:00",
            duration_minutes=60, activity="代码", category="工作.AI调优",
            source_contents="x", source_timestamps="09:00", analysis_reasoning="x",
        )
        _db.add_record_full(
            date=f"2026-07-{d:02d}", time_start="00:00", time_end="08:00",
            duration_minutes=480, activity="睡觉", category="维持.睡眠",
            source_contents="x", source_timestamps="00:00", analysis_reasoning="x",
        )
    plan_result = _db.ensure_plan_event(
        date="2026-07-05", time_start="14:00", time_end="15:00",
        title="健身", category="健康.运动",
    )
    _db.update_plan_event(plan_result["id"], {"completion": "已完成"})

    # 跑 render_replay + render_and_write
    from schedule_html_render import render_replay, render_and_write
    payload = render_replay("2026-07-01", "2026-07-14")
    assert payload["status"] == "ok", f"渲染失败: {payload}"
    result = render_and_write(payload)
    assert result["status"] == "ok", f"写文件失败: {result}"

    html_path = Path(result["data"]["file_path"])
    yield html_path
    # teardown:删 html
    try:
        html_path.unlink()
    except OSError:
        pass


# ---- T08 acceptance 端到端断言 ----

def test_replay_html_4_cards(replay_html_file):
    """T08 · 顶部 4 卡总览:总时长 / 记录数 / 完成率 / 健康分(playwright 加载后断言)"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 未安装,跳过")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(viewport={"width": 1280, "height": 800})
            page = ctx.new_page()
            page.goto("file:///" + str(replay_html_file).replace("\\", "/"), wait_until="load")
            page.wait_for_function(
                "() => document.querySelectorAll('.card-stat').length >= 4",
                timeout=5000,
            )
            labels = page.evaluate(
                """() => {
                    const cards = document.querySelectorAll('.card-stat .label');
                    return Array.from(cards).map(c => c.textContent.trim());
                }"""
            )
            values = page.evaluate(
                """() => {
                    const cards = document.querySelectorAll('.card-stat .value');
                    return Array.from(cards).map(c => c.textContent.trim());
                }"""
            )
            assert set(labels) == {"总时长", "记录数", "完成率", "健康分"}, \
                f"4 卡标签不完整: {labels}"
            # 总时长应有 126h(14 天 × (60+480)min = 7560min = 126h)
            assert any("126" in v for v in values), \
                f"总时长应含 126h,实际 values: {values}"
            # 记录数应有 28 条(14 天 × 2 record/天)
            assert any("28" in v for v in values), \
                f"记录数应含 28 条,实际 values: {values}"
        finally:
            browser.close()


def test_replay_html_copy_prompt_button(replay_html_file):
    """T08 · 复制 prompt 4 部分结构按钮(单工铁律,总纲 §04 原则 10)"""
    html = replay_html_file.read_text(encoding="utf-8")
    # 复制按钮元素
    assert "copy-prompt-btn" in html or "复制 prompt" in html, \
        "缺复制 prompt 按钮"
    # 3 部分结构(① 技能与唤醒词 / ② 参数 / ③ 执行)
    for marker in ("①", "②", "③"):
        assert marker in html, f"copy_prompt 缺第{marker}部分(3 部分结构)"


def test_replay_html_4_segments(replay_html_file):
    """T08 · 4 段叙事渲染:record_aggregate / plan_aggregate / cross_domain / ai_insights"""
    html = replay_html_file.read_text(encoding="utf-8")
    for seg in ("record_aggregate", "plan_aggregate", "cross_domain", "ai_insights"):
        assert seg in html or seg.replace("_", " ") in html, \
            f"4 段叙事缺段: {seg}"


def test_replay_html_status_badge(replay_html_file):
    """T08 · 状态徽章 ✅ ok / 📭 empty / ⚠️ incomplete / ❌ error / 📡 offline"""
    html = replay_html_file.read_text(encoding="utf-8")
    # status_badge 在 meta 里,JS 应在 hero 区渲染徽章
    assert "✅" in html or "📭" in html or "⚠️" in html or "❌" in html or "📡" in html, \
        "5 状态徽章 emoji 必至少 1 个出现(此 fixture 是 ok 状态)"
    # ok 状态 badge
    assert "✅" in html, "14 天数据 ok 状态徽章应 = ✅"


def test_replay_html_mobile_no_horizontal_scroll(replay_html_file):
    """T08 · 移动端 (360px) 适配:无水平滚动"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright 未安装,跳过 viewport 视觉断言")

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
            page.goto("file:///" + str(replay_html_file).replace("\\", "/"), wait_until="load")
            # 等 payload script 渲染完成
            page.wait_for_function(
                "() => document.querySelectorAll('.card, [class*=\"segment\"]').length > 0",
                timeout=5000,
            )
            data = page.evaluate(
                """() => ({
                    docW: document.documentElement.scrollWidth,
                    winW: window.innerWidth,
                    hasHScroll: document.documentElement.scrollWidth > window.innerWidth + 1,
                })"""
            )
            assert not data["hasHScroll"], \
                f"360px 视口出现水平滚动:docW={data['docW']} winW={data['winW']}"
        finally:
            browser.close()