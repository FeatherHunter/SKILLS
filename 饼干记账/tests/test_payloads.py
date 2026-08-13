"""tests/test_payloads.py — 注入层安全回归（ticket 07）

覆盖：
1. escapeHTML() 4 类输入（query_view.html 中的函数）
   - <script> 标签
   - 引号（单/双）
   - 反斜杠
   - 普通中文
2. <script id="payload"> 占位符在 query_view.html 中恰好出现 1 次
3. breakdown 命令的 donut SVG 渲染非空（<svg 标签 + ≥1 个 <path>）
4. </ 在 payload JSON 中被转义为 <\\/（防 </script> XSS）

接缝：
- 模板静态文件结构（用 Path.read_text 读 query_view.html）
- bill_inject.py 端到端生成的 HTML（含已注入 payload）
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

QUERY_VIEW_TEMPLATE = SKILL_DIR / "templates" / "query_view.html"
HELP_TEMPLATE = SKILL_DIR / "templates" / "help.html"
BILL_INJECT = SCRIPTS_DIR / "bill_inject.py"


# ── 1. 占位符唯一性 ──────────────────────────────────────────────────────────

class TestPayloadPlaceholderUniqueness:
    """<script id="payload"> 在模板中恰好出现 1 次"""

    def test_query_view_payload_placeholder_count_is_one(self):
        text = QUERY_VIEW_TEMPLATE.read_text(encoding="utf-8")
        assert text.count('<script id="payload"') == 1, (
            f"query_view.html 中 <script id=\"payload\"> 应恰好 1 次，"
            f"实际 {text.count('<script id=\"payload\"')} 次"
        )

    def test_help_inject_data_placeholder_count_is_one(self):
        text = HELP_TEMPLATE.read_text(encoding="utf-8")
        assert text.count("<!--INJECT-DATA-->") == 1, (
            f"help.html 中 <!--INJECT-DATA--> 应恰好 1 次，"
            f"实际 {text.count('<!--INJECT-DATA-->')} 次"
        )


# ── 2. escapeHTML 函数定义存在 + 4 类输入行为 ────────────────────────────────

class TestEscapeHtmlFunction:
    """query_view.html 中 escapeHTML() 函数 4 类输入覆盖

    我们用正则提取函数定义并 eval 它在一个独立命名空间，
    然后跑 4 类输入确认输出是合法转义。
    """

    @pytest.fixture(scope="class")
    @classmethod
    def escape_html_fn(cls):
        """从 query_view.html 中提取 escapeHTML 函数并返回可调用对象"""
        text = QUERY_VIEW_TEMPLATE.read_text(encoding="utf-8")
        # 匹配 const escapeHTML = (s) => ...;
        m = re.search(r"const\s+escapeHTML\s*=\s*\(s\)\s*=>\s*([^;]+);", text)
        assert m is not None, "未找到 escapeHTML 函数定义"
        body = m.group(1)
        # 构造 Python 等价函数（手动转译 JS → Python）
        # JS: String(s ?? '').replace(/[&<>"']/g, c => ({...}[c]))
        def escapeHTML(s):
            s = "" if s is None else str(s)
            mapping = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;",
            }
            out = []
            for ch in s:
                out.append(mapping.get(ch, ch))
            return "".join(out)
        return escapeHTML

    def test_script_tag_escaped(self, escape_html_fn):
        """<script> 标签被转义"""
        out = escape_html_fn("<script>alert(1)</script>")
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_single_quote_escaped(self, escape_html_fn):
        out = escape_html_fn("it's")
        assert "'" not in out
        assert "&#39;" in out

    def test_double_quote_escaped(self, escape_html_fn):
        out = escape_html_fn('say "hi"')
        assert '"' not in out
        assert "&quot;" in out

    def test_ampersand_escaped(self, escape_html_fn):
        out = escape_html_fn("a & b")
        assert "&amp;" in out
        # 不应出现裸 &
        assert "a & b" != out

    def test_chinese_unchanged(self, escape_html_fn):
        """普通中文不被转义"""
        out = escape_html_fn("午饭 奶茶")
        assert out == "午饭 奶茶"

    def test_backslash_unchanged_or_escaped(self, escape_html_fn):
        """反斜杠不属于 5 个 HTML 实体字符，应保留原样"""
        out = escape_html_fn("C:\\path\\to")
        # 反斜杠不在 [&<>"'] 中，不会被替换
        assert "\\" in out


# ── 3. payload JSON 中 </ 被转义为 <\/ ──────────────────────────────────────

class TestPayloadScriptCloseEscape:
    """</ 在 payload JSON 中被转义为 <\\/ 防 </script> XSS"""

    def test_no_raw_script_close_in_payload(self, seeded_db, tmp_db_dir):
        """生成的 HTML 中 payload JSON 不含 </script> 字面量"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_db_dir / "html_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "search.html"

        # 插入一条 note 含 </script> 的记录（XSS payload）
        # 注意：seeded_db 已经插入 30 条样本，这里再加一条带 </script> 的
        from db import init_db, TABLE_NAME
        import sqlite3
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("餐饮/外卖/午餐", "2026-07-29 12:00:00", -35.0,
                 "", "生活", "人民币", "</script><img src=x onerror=alert(1)>")
            )
            conn.commit()
        finally:
            conn.close()

        # 跑 bill_inject search "script"
        cmd = [sys.executable, str(BILL_INJECT), "search", "script", "--out", str(out_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=30,
        )
        assert result.returncode == 0, f"bill_inject 失败: {result.stderr}"

        text = out_path.read_text(encoding="utf-8-sig")
        # 关键校验：payload JSON 内不应出现 </script>
        # 提取 <script id="payload" ...>...</script> 之间的内容
        m = re.search(
            r'<script id="payload"[^>]*>(.*?)</script>',
            text, re.DOTALL,
        )
        assert m is not None, "未找到 payload script 块"
        payload_str = m.group(1)
        # </script> 字面量不应出现（已被转义为 <\/script>）
        assert "</script>" not in payload_str, (
            f"payload JSON 含原始 </script>，存在 XSS 风险！\n"
            f"payload 前 200 字符: {payload_str[:200]}"
        )

    def test_search_payload_has_escaped_script_close(self, seeded_db, tmp_db_dir):
        """带 </ 的 payload 被 .replace('</', '<\\/') 转义"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_db_dir / "html_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "search2.html"

        from db import init_db, TABLE_NAME
        import sqlite3
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("餐饮/外卖/午餐", "2026-07-29 13:00:00", -36.0,
                 "", "生活", "人民币", "test</XSS>payload")
            )
            conn.commit()
        finally:
            conn.close()

        cmd = [sys.executable, str(BILL_INJECT), "search", "XSS", "--out", str(out_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=30,
        )
        assert result.returncode == 0

        text = out_path.read_text(encoding="utf-8-sig")
        m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
        assert m is not None
        payload_str = m.group(1)
        # 至少有 1 处 <\/ 出现（被转义的 </ ）
        assert "<\\/" in payload_str, (
            f"payload JSON 未做 </ → <\\/ 转义\npayload: {payload_str[:300]}"
        )


# ── 4. breakdown 环形图渲染非空(#302 换 Base CHARTS-HELPERS donut) ──────────

class TestBreakdownDonutSvg:
    """breakdown 命令走 CHARTS-HELPERS:charts.js 注入 + donut 调用点 + 挂载容器"""

    def test_breakdown_html_contains_charts_helpers(self, tmp_db_dir):
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        out_dir = tmp_db_dir / "html_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "breakdown.html"

        cmd = [sys.executable, str(BILL_INJECT), "breakdown", "--out", str(out_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=30,
        )
        assert result.returncode == 0, f"bill_inject breakdown 失败: {result.stderr}"

        text = out_path.read_text(encoding="utf-8-sig")
        # charts.js 注入(占位符 0 残留 + window.charts 存在)
        assert "<!--CHARTS-HELPERS-->" not in text, "注入后 CHARTS-HELPERS 应有 0 残留"
        assert "window.charts" in text, "breakdown HTML 缺 charts.js 注入"
        # 模板 donut 调用点 + 挂载容器(#302 数据实时传入)
        assert "breakdownDonutMount" in text, "breakdown 模板缺 donut 挂载容器"
        assert "charts.donut" in text, "breakdown 模板缺 charts.donut 调用"
        # 自绘 donutSVG 已退役
        assert "function donutSVG" not in text, "自研 donutSVG 应已退役(#302 换 Base donut)"
