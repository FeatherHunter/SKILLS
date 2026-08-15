# -*- coding: utf-8 -*-
"""tests/test_plan_builder_wizard_sidx.py — #318 回归测试

保障:
  - plan_builder_wizard 周视图按周渲染时,sessions.map 回调的 sIdx 不再触发
    「sIdx is not defined」ReferenceError
  - swap 按钮可点击、候选动作可应用,目标动作名被替换
  - 修复前(reverted)两类断言都会失败,锁住 bug 不复现

Mock 夹具 tests/fixtures/mock/mock_plan_builder.json 内 day 1 有 2 个 session
(上午·胸 + 下午·背),足以触发多 session 路径的 sIdx 引用。

DB 隔离:本测试走 --mock 路径,render_plan_builder.py 仅读 JSON mock,**不触 DB**。
        conftest.py 的 iso_db autouse fixture 仍兜底 SKILLS_DB_PATH → mktemp 做双保险。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
MOCK_PATH = SKILL_DIR / "tests" / "fixtures" / "mock" / "mock_plan_builder.json"
TEMPLATE_PATH = SKILL_DIR / "templates" / "plan_builder_wizard.html"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ── 1. 静态守门:模板存档「sIdx 被未声明就引用」的根本模式 ────────────────
class TestTemplateSource:
    """锁住会话 map 回调的形参签名;防止 sIdx 形参意外再次丢失。"""

    def test_sessions_map_has_sidx_param(self) -> None:
        """sessions.map 的回调必须接收 sIdx(mIdx 已对齐的命名一致)。"""
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        pattern = re.compile(r"sessions\.map\(\s*\(\s*s\s*,\s*sIdx\s*\)", re.MULTILINE)
        matches = pattern.findall(text)
        assert matches, (
            "plan_builder_wizard.html 未找到 `sessions.map((s, sIdx) =>` 签名。"
            "Bug #318 复发迹象。"
        )

    def test_sidx_references_inside_sessions_callback(self) -> None:
        """sIdx 出现在 sessions.map 回调块内;若签名丢了,这些引用就会抛 ReferenceError。"""
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        sidx_occurrences = text.count("sIdx")
        assert sidx_occurrences >= 2, (
            f"sIdx 引用不足 {sidx_occurrences} 次;swapKey 与 doSwap 至少 2 处,"
            f"签名丢了就是 bug #318 复发。"
        )

    def test_midx_pattern_kept_for_consistency(self) -> None:
        """movements.map((m, mIdx) 仍存在 — 防止有人修复 sIdx 时意外破坏 mIdx 对称。"""
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert re.search(r"movements\.map\(\s*\(\s*m\s*,\s*mIdx\s*\)", text), \
            "movements.map((m, mIdx) 签名丢失,改 sIdx 时连带改坏了 mIdx"


# ── 2. 端到端:render mock → Playwright 打开 → 0 pageerror + swap 生效 ───────
class TestWeekViewRuntime:
    """复现 issue 318 报告链路:render mock → Playwright 打开 → 无 pageerror。"""

    @pytest.fixture(scope="class")
    def rendered_html(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        out_dir = tmp_path_factory.mktemp("kl318_out")
        out_html = out_dir / "plan_builder_wizard.html"
        cmd = [
            sys.executable, str(SCRIPTS_DIR / "render_plan_builder.py"),
            "--mock", str(MOCK_PATH),
            "--output", str(out_html),
        ]
        result = subprocess.run(
            cmd, cwd=str(SKILL_DIR),
            capture_output=True, text=True, encoding="utf-8",
        )
        assert result.returncode == 0, (
            f"render_plan_builder.py 失败: stdout={result.stdout!r}\n"
            f"stderr={result.stderr!r}"
        )
        assert out_html.exists() and out_html.stat().st_size > 0, \
            "render 产出空文件"
        return out_html

    def test_render_week_view_has_no_sidx_reference_error(self, rendered_html: Path) -> None:
        """按周查看(默认视图)渲染时,页面 JS 不抛 sIdx is not defined。"""
        from playwright.sync_api import sync_playwright

        page_errors: list[str] = []
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            page.on("pageerror", lambda exc: page_errors.append(str(exc)))
            page.goto(f"file:///{rendered_html.resolve()}")
            page.wait_for_load_state("networkidle")
            # 默认视图是按周查看(line 476 viewByWeek class=active),
            # 加载时 renderWeekView → renderWeekDetail 已触发 bug #318。
            page.wait_for_timeout(300)
            browser.close()

        offending = [e for e in page_errors if "sIdx" in e]
        assert not offending, (
            f"周视图渲染触发 sIdx is not defined ReferenceError;"
            f"bug #318 复发。所有 pageerror: {page_errors}"
        )
        assert not page_errors, f"页面有 JS 错误: {page_errors}"

    def test_swap_button_changes_movement_name(self, rendered_html: Path) -> None:
        """点 swap 按钮 → 选候选动作 → 同页面内动作名被替换(doSwap 触发的 renderWeekDetail 重渲)。"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(f"file:///{rendered_html.resolve()}")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(300)

            swap_btns = page.locator(".move-swap")
            assert swap_btns.count() > 0, "周视图未渲染任何 .move-swap 按钮"
            first_btn = swap_btns.first
            first_btn.scroll_into_view_if_needed()

            row = first_btn.locator("xpath=ancestor::tr").first
            original_name = row.locator(".name").first.text_content().strip()
            original_name = original_name.split("\n")[0].strip()
            assert original_name, "swap 按钮所在行缺少动作名"

            first_btn.click()
            page.wait_for_timeout(100)
            menu_btn = page.locator(".move-swap-menu button").first
            assert menu_btn.count() > 0, "swap 菜单未出现,doSwap 链路未通"
            new_name = menu_btn.text_content().strip()
            assert new_name and new_name != original_name, (
                f"候选动作名 {new_name!r} 应与原名 {original_name!r} 不同"
            )
            menu_btn.click()
            page.wait_for_timeout(200)

            post_row = page.locator(".session-card .movement-table tbody tr").first
            post_name = post_row.locator(".name").first.text_content().strip().split("\n")[0].strip()
            browser.close()

        assert post_name == new_name, (
            f"swap 未生效: 动作名 {original_name!r} 未被替换为 {new_name!r},"
            f"实际为 {post_name!r}"
        )


# ── 3. 留空给后续扩展:多 session 同 day 的 swapKey 唯一性 ──────────────────
class TestSwapKeyUniqueness:
    """回归保护:多 session 同 day 时,swapKey 包含 sIdx 后不冲突。"""

    def test_mock_has_multiple_sessions_on_day_one(self) -> None:
        """Lock 住 mock 夹具中 day 1 多 session 形态 — 防止有人改 mock 后失去触发条件。"""
        data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
        day1 = next(d for w in data["weeks"] for d in w["days"] if d["day_of_week"] == 1)
        assert len(day1["sessions"]) >= 2, (
            "mock 第 1 天需有 ≥ 2 个 session 才触发 sIdx 路径;"
            "夹具被改弱了,sIdx 回归测试将失效。"
        )
