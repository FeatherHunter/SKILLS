"""tests/test_form_selector_dom.py — 三表单 smartSelect 接入 DOM 守卫（wayfinder #312 T6）

覆盖（T6 验收 ①③ + 回填协议端到端）:
- expense_form: 三字段挂载 3 个 ss-root · #298 场景(photo + --account-source inferred → 卡片「美团」+「AI 推断」徽章)
- 点击候选 chip → 隐藏 input 回填（input.value + dataset.source/new, buildPrompt 读取通道）
- 联动表单: default_category 兜底（买东西 → 居家/家电 标「已有」）· 账户推断
- 降级: 无 goals 键 → 普通输入（ss-plain）
- 0 JS 错误

隔离: SKILLS_DB_PATH → tmp_path（conftest.tmp_db_dir）; 浏览器无 DB 接触。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _has_playwright():
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(
    not _has_playwright(), reason='需要 playwright'
)

from playwright.sync_api import sync_playwright  # noqa: E402


def _run_renderer(tmp_db_dir, script, args):
    env = {
        **os.environ.copy(),
        "SKILLS_DB_PATH": str(tmp_db_dir),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / script)] + args,
        capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
    )


def _write_goals(tmp_db_dir, data: dict):
    (tmp_db_dir / "goals.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


GOALS = {
    "accounts": [
        {"name": "美团", "disabled": False},
        {"name": "微信", "disabled": False},
        {"name": "支付宝", "disabled": True},
    ],
    "ledgers": [
        {"name": "生活", "disabled": False},
        {"name": "旅行", "disabled": False},
    ],
}


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _open_html(browser, path: Path):
    """打开渲染产物, 返回 (page, errors)"""
    page = browser.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(path.resolve().as_uri())
    page.wait_for_timeout(300)
    return page, errs


class TestExpenseFormSelector:
    def test_photo_meituan_inferred_and_writeback(self, tmp_db_dir, browser):
        """#298 场景: photo 表单账户「美团」AI 推断卡片 + 点候选回填隐藏 input"""
        _write_goals(tmp_db_dir, GOALS)
        out = tmp_db_dir / "photo.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["photo", "--amount", "38.9", "--category-hint", "外卖",
                                "--account", "美团", "--account-source", "inferred",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        page, errs = _open_html(browser, out)
        assert errs == [], errs
        # 三字段 3 个组件
        assert page.evaluate("document.querySelectorAll('.ss-root').length") == 3
        # 账户卡片: 美团 + AI 推断徽章
        nm = page.evaluate("document.querySelector('#fAccount ~ .ss-root .ss-nm').textContent")
        badge = page.evaluate("document.querySelector('#fAccount ~ .ss-root .ss-card .ss-badge').textContent")
        assert nm == '美团' and badge == 'AI 推断'
        # 分类 hint「外卖」→ 推荐新建
        cat_nm = page.evaluate("document.querySelector('#fCategory ~ .ss-root .ss-nm').textContent")
        assert cat_nm == '外卖'
        # 回填协议: 隐藏 input 已被组件写值
        st = page.evaluate("""() => {
          const a = document.getElementById('fAccount');
          return { v: a.value, src: a.dataset.source, isNew: a.dataset.new };
        }""")
        assert st == {'v': '美团', 'src': 'inferred', 'isNew': '0'}
        # 点击「微信」chip → 隐藏 input 回填 existing
        page.locator('#fAccount ~ .ss-root .ss-chip', has_text='微信').click()
        st2 = page.evaluate("""() => {
          const a = document.getElementById('fAccount');
          return { v: a.value, src: a.dataset.source, isNew: a.dataset.new };
        }""")
        assert st2 == {'v': '微信', 'src': 'existing', 'isNew': '0'}
        # 停用账户不可点
        page.evaluate("document.querySelector('#fAccount ~ .ss-root .ss-chip.ss-chip-dis').click()")
        assert page.evaluate("document.getElementById('fAccount').value") == '微信'
        page.close()

    def test_expense_history_prefill_and_degrade(self, tmp_db_dir, browser):
        """历史预填走 input.value(组件推导 history); 无键降级普通输入"""
        out = tmp_db_dir / "expense.html"
        # 无 goals.json → account/ledger options 空 → 降级普通输入; 分类 L1 候选仍在
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--category-hint", "餐饮",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        page, errs = _open_html(browser, out)
        assert errs == [], errs
        # 分类 inferred 餐饮
        assert page.evaluate("document.querySelector('#fCategory ~ .ss-root .ss-nm').textContent") == '餐饮'
        # 账户/账本 options 空 → 降级 ss-plain 可见输入
        plain = page.evaluate("document.querySelectorAll('.ss-plain').length")
        assert plain == 2
        acc_visible = page.evaluate("getComputedStyle(document.getElementById('fAccount')).display")
        assert acc_visible != 'none'
        page.close()

    def test_ledger_history_badge(self, tmp_db_dir, browser):
        """账本历史预填(_prefill 通道): input.value=旅行 → 卡片「旅行」+「历史」徽章"""
        _write_goals(tmp_db_dir, {"ledgers": [{"name": "生活"}, {"name": "旅行"}]})
        # 历史记录: 同分类 → _prefill 补 ledger=旅行(不进 selector, 走 input.value → 组件推导 history)
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            conn.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note, deleted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("餐饮/外卖/午餐", "2026-08-01 12:00", -35, "微信", "旅行", "人民币", "", None))
            conn.commit()
        finally:
            conn.close()
        out = tmp_db_dir / "expense3.html"
        result = _run_renderer(tmp_db_dir, "render_write.py",
                               ["expense", "--amount", "35", "--category", "餐饮/外卖/午餐",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        page, errs = _open_html(browser, out)
        assert errs == [], errs
        nm = page.evaluate("document.querySelector('#fLedger ~ .ss-root .ss-nm').textContent")
        badge = page.evaluate("document.querySelector('#fLedger ~ .ss-root .ss-card .ss-badge').textContent")
        assert nm == '旅行' and badge == '历史'
        page.close()


class TestLinkFormSelector:
    def test_purchase_default_category_and_account(self, tmp_db_dir, browser):
        """买东西联动: 场景默认分类「居家/家电」标已有 + 账户推断"""
        _write_goals(tmp_db_dir, GOALS)
        out = tmp_db_dir / "purchase.html"
        result = _run_renderer(tmp_db_dir, "link/cli.py",
                               ["form", "purchase", "--amount", "199", "--item", "空气炸锅",
                                "--account", "美团", "--account-source", "inferred",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        page, errs = _open_html(browser, out)
        assert errs == [], errs
        assert page.evaluate("document.querySelectorAll('.ss-root').length") == 3
        # 默认分类: 居家/家电(已有)
        cat_nm = page.evaluate("document.querySelector('#fCategory ~ .ss-root .ss-nm').textContent")
        cat_badge = page.evaluate("document.querySelector('#fCategory ~ .ss-root .ss-card .ss-badge').textContent")
        assert cat_nm == '居家/家电' and cat_badge == '已有'
        # 账户: 美团(AI 推断)
        acc_nm = page.evaluate("document.querySelector('#fAccount ~ .ss-root .ss-nm').textContent")
        acc_badge = page.evaluate("document.querySelector('#fAccount ~ .ss-root .ss-card .ss-badge').textContent")
        assert acc_nm == '美团' and acc_badge == 'AI 推断'
        page.close()

    def test_meal_default_category(self, tmp_db_dir, browser):
        """吃饭联动: 默认分类「餐饮」"""
        out = tmp_db_dir / "meal.html"
        result = _run_renderer(tmp_db_dir, "link/cli.py",
                               ["form", "meal", "--amount", "35", "--ate", "鸡腿饭",
                                "--out", str(out)])
        assert result.returncode == 0, result.stderr
        page, errs = _open_html(browser, out)
        assert errs == [], errs
        cat_nm = page.evaluate("document.querySelector('#fCategory ~ .ss-root .ss-nm').textContent")
        assert cat_nm == '餐饮'
        page.close()
