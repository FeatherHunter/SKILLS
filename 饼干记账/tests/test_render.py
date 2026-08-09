"""tests/test_render.py — 9 类 query_type + 空数据 + 错误 CLI 输出 + BOM

接缝 = `bill_inject.py <query_type> [args]` 端到端调用（spec.md §Implementation
Decisions #1 唯一最高级 seam）。

外部行为校验：
- 输出 HTML 文件存在
- 含 `<meta charset="UTF-8">`
- 含 BOM（`bytes[0:3] == b'\xef\xbb\xbf'`）
- 含 `<script id="payload"` 占位符
- 含 5 状态 fallback 之一（空态/错误态等命中）
- 不依赖内部函数（`_find_db_path` / `html_name` 算法）
"""

from __future__ import annotations

import os
import subprocess
import sys
import json
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

BILL_INJECT = SCRIPTS_DIR / "bill_inject.py"
RENDER_HELP = SCRIPTS_DIR / "render_help.py"


def _run_bill_inject(tmp_db_dir, query_type, *extra_args, expect_rc=0, out_suffix=""):
    """跑 bill_inject.py query_type [args] --out <tmp_path>，返回 (rc, out, err, output_html_path)

    用 --out 指定输出路径，避免从 stdout 解析路径（Windows drive: 冲突）。
    """
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    # 用 tmp_db_dir 下的可控路径
    out_dir = tmp_db_dir / "html_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{query_type}{out_suffix}.html"
    cmd = [sys.executable, str(BILL_INJECT), query_type, "--out", str(out_path)] + list(extra_args)
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=30,
    )
    assert result.returncode == expect_rc, (
        f"bill_inject {query_type} rc={result.returncode}（期望 {expect_rc}）\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return result.returncode, result.stdout, result.stderr, out_path


def _run_render_help(tmp_db_dir, *, out_path=None):
    """跑 render_help.py，返回 (rc, out, err, output_html_path)"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_db_dir)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    if out_path is None:
        out_dir = tmp_db_dir / "html_out"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "help.html"
    cmd = [sys.executable, str(RENDER_HELP), "--out", str(out_path)]
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", env=env, timeout=30,
    )
    assert result.returncode == 0, f"render_help 失败: {result.stderr}"
    return result.returncode, result.stdout, result.stderr, out_path


def _assert_html_well_formed(html_path: Path, *, allow_error_state: bool = False):
    """断言 HTML 文件含必需元素：BOM + charset + payload + 5 状态 fallback"""
    assert html_path is not None, "未解析到输出 HTML 路径"
    assert html_path.exists(), f"输出 HTML 不存在: {html_path}"

    raw = html_path.read_bytes()
    # BOM
    assert raw[:3] == b"\xef\xbb\xbf", (
        f"输出 HTML 缺 UTF-8 BOM（前 3 字节 = {raw[:3]!r}）"
    )
    text = raw.decode("utf-8-sig")

    # <meta charset="UTF-8">
    assert 'charset="UTF-8"' in text or "charset='UTF-8'" in text or \
           'charset=utf-8' in text.lower(), "缺 <meta charset=UTF-8>"

    # <script id="payload"
    assert '<script id="payload"' in text, "缺 <script id=\"payload\"> 注入点"

    # 5 状态 fallback：renderError / empty / payload.status 等代码存在
    # （模板里都有这些 JS 函数；我们只校验关键关键词存在）
    # query_view.html 用 escapeHTML()，help.html 用 esc() —— 都是 XSS 守卫
    assert "escapeHTML" in text or ("function esc(" in text and "esc(" in text), \
        "缺 XSS 守卫函数（escapeHTML 或 esc）"
    assert "error-card" in text or "renderError" in text or "渲染失败" in text or "加载失败" in text, \
        "缺错误态 fallback"


# ── 13 类 query_type 全跑(9 原有 + 查询域 4 新:tag/debt/reimburse/installment) ──

class TestNineQueryTypesRender:
    """全部 query_type 端到端：每类都生成合法 HTML"""

    @pytest.mark.parametrize("query_type,extra_args", [
        ("summary",   []),
        ("list",      ["--date", "2026-01-02"]),
        ("recent",    ["--limit", "5"]),
        ("search",    ["午饭"]),
        ("tag",       ["--tag", "旅行"]),
        ("debt",      []),
        ("reimburse", []),
        ("installment", []),
        ("monthly",   ["--month", "2026-01"]),
        ("compare",   ["--period", "week"]),
        ("breakdown", []),
        ("overview",  ["--month", "2026-01"]),
        ("stats",     []),
    ])
    def test_each_query_type_generates_valid_html(self, seeded_db, query_type, extra_args):
        rc, out, err, html_path = _run_bill_inject(seeded_db, query_type, *extra_args)
        _assert_html_well_formed(html_path)


# ── 分析域 25 场景端到端(2026-08-09 实施 · 最大域)────────────────────────────

class TestAnalysisDomainRender:
    """分析域全部类型：每类都生成合法 HTML(隔离契约 templates/分析/analysis_view.html)"""

    @pytest.mark.parametrize("query_type,extra_args", [
        # 汇总 4
        ("monthly",   ["--month", "2026-01"]),
        ("yearly",    ["--year", "2026"]),
        ("overview",  ["--from", "2026-01-01", "--to", "2026-01-31"]),
        ("week",      []),
        # 结构 4
        ("category",  ["--month", "2026-01"]),
        ("account",   ["--month", "2026-01"]),
        ("ledger",    ["--month", "2026-01"]),
        ("structure", ["--month", "2026-01"]),
        # 对比 4
        ("compare",   ["--period", "month"]),
        ("range_compare", ["--from1", "2026-01-01", "--to1", "2026-01-31", "--from2", "2025-12-01", "--to2", "2025-12-31"]),
        ("yoy",       ["--month", "2026-01"]),
        ("cat_compare", ["--from1", "2026-01-01", "--to1", "2026-01-31", "--from2", "2025-12-01", "--to2", "2025-12-31"]),
        # 趋势 2
        ("trend",     ["--months", "6"]),
        ("cat_trend", ["--category", "餐饮", "--months", "6"]),
        # 金额 3
        ("top",       ["--limit", "5"]),
        ("top_freq",  ["--limit", "5"]),
        ("distribution", ["--month", "2026-01"]),
        # 统计洞察 4
        ("stats",     []),
        ("activity",  []),
        ("insight",   ["--months", "6"]),
        ("anomaly",   ["--months", "6"]),
        # 状态聚合 4
        ("debt_summary", []),
        ("reimburse_summary", []),
        ("installment_summary", []),
        ("refund_summary", []),
    ])
    def test_each_analysis_type_generates_valid_html(self, seeded_db, query_type, extra_args):
        rc, out, err, html_path = _run_bill_inject(seeded_db, query_type, *extra_args)
        _assert_html_well_formed(html_path)

    def test_analysis_types_use_analysis_template(self, seeded_db):
        """分析域类型注入分析域模板(analysis_view.html 特征:SVG 折线 lineChart + 图表图例)"""
        for qt, extra in [("yearly", ["--year", "2026"]), ("trend", ["--months", "6"])]:
            rc, out, err, html_path = _run_bill_inject(seeded_db, qt, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            assert "lineChart" in text, f"{qt} 应使用分析域模板(含 lineChart)"
            assert "分析视图" in text, f"{qt} 应使用分析域模板标题"

    def test_analysis_empty_db(self, empty_db):
        """分析域空库 → HTML 空态正常生成(不崩)"""
        for qt, extra in [
            ("yearly", ["--year", "2026"]), ("week", []), ("category", []),
            ("structure", []), ("range_compare", ["--from1", "2026-01-01", "--to1", "2026-01-31", "--from2", "2025-12-01", "--to2", "2025-12-31"]),
            ("trend", ["--months", "6"]), ("top", []), ("distribution", []),
            ("activity", []), ("insight", []), ("anomaly", []),
            ("debt_summary", []), ("reimburse_summary", []),
            ("installment_summary", []), ("refund_summary", []),
        ]:
            rc, out, err, html_path = _run_bill_inject(empty_db, qt, *extra)
            _assert_html_well_formed(html_path, allow_error_state=True)

    def test_analysis_status_family_with_data(self, tmp_db_dir):
        """状态聚合有数据:debt_summary/reimburse_summary/installment_summary/refund_summary payload 含聚合值"""
        import re
        import sqlite3
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            cur = conn.cursor()
            rows = [
                ("借贷/借出", "2026-07-01 10:00:00", -500.0, "", "借贷", "#借出 #借给小明 #未还"),
                ("借贷/借入", "2026-07-05 10:00:00", 300.0, "", "借贷", "#借入 #向小红借 #未还"),
                ("借贷/借出", "2026-06-01 10:00:00", -200.0, "", "借贷", "#借出 #借给老王 #已还"),
                ("餐饮", "2026-07-10 12:00:00", -88.0, "", "生活", "客户午餐 #待报销"),
                ("餐饮", "2026-07-15 12:00:00", 88.0, "", "生活", "报销到账 #报销到账"),
                ("分期/手机", "2026-07-01 00:00:00", -3400.0, "", "生活", "#分期 手机 第1期/3"),
                ("分期/手机", "2026-09-01 00:00:00", -3300.0, "", "生活", "#分期 手机 第3期/3"),
                ("餐饮", "2026-07-08 12:00:00", 30.0, "", "生活", "外卖退款 #退款"),
            ]
            for c, t, a, acc, l, n in rows:
                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (c, t, a, acc, l, "人民币", n),
                )
            conn.commit()
        finally:
            conn.close()

        def _payload(qt, *extra):
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, qt, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            return json.loads(m.group(1))

        p = _payload("debt_summary")
        assert p["status"] == "ok"
        assert p["data"]["lent_unpaid_total"] == 500.0
        assert p["data"]["borrowed_unpaid_total"] == 300.0
        assert p["data"]["lent_paid_count"] == 1

        p = _payload("reimburse_summary")
        assert p["status"] == "ok" and p["data"]["pending_total"] == 88.0
        assert p["data"]["received_total"] == 88.0

        p = _payload("installment_summary")
        assert p["status"] == "ok"
        g = p["data"]["active"][0]
        assert g["name"] == "手机" and g["total"] == 6700.0 and g["periods"] == 3

        p = _payload("refund_summary")
        assert p["status"] == "ok" and p["data"]["total"] == 30.0 and p["data"]["count"] == 1


# ── 空数据场景 ─────────────────────────────────────────────────────────────

class TestEmptyDataRender:
    """DB 0 条 → HTML 应能生成（空态）"""

    def test_summary_on_empty_db(self, empty_db):
        rc, out, err, html_path = _run_bill_inject(empty_db, "summary")
        _assert_html_well_formed(html_path)

    def test_recent_on_empty_db(self, empty_db):
        rc, out, err, html_path = _run_bill_inject(empty_db, "recent", "--limit", "10")
        _assert_html_well_formed(html_path)

    def test_monthly_on_empty_db(self, empty_db):
        rc, out, err, html_path = _run_bill_inject(empty_db, "monthly", "--month", "2026-01")
        _assert_html_well_formed(html_path)

    def test_breakdown_on_empty_db(self, empty_db):
        rc, out, err, html_path = _run_bill_inject(empty_db, "breakdown")
        _assert_html_well_formed(html_path)

    def test_search_no_match(self, seeded_db):
        """关键词无匹配 → HTML 含空态"""
        rc, out, err, html_path = _run_bill_inject(seeded_db, "search", "外星人不存在")
        _assert_html_well_formed(html_path)

    def test_tag_no_match(self, seeded_db):
        """查标签无命中 → HTML 空态"""
        rc, out, err, html_path = _run_bill_inject(seeded_db, "tag", "--tag", "不存在的标签")
        _assert_html_well_formed(html_path)

    def test_debt_reimburse_installment_on_empty_db(self, empty_db):
        """状态族 3 类空库 → HTML 空态正常生成"""
        for qt, extra in [("debt", []), ("reimburse", []), ("installment", [])]:
            rc, out, err, html_path = _run_bill_inject(empty_db, qt, *extra)
            _assert_html_well_formed(html_path)

    def test_status_family_with_data(self, tmp_db_dir):
        """状态族有数据:debt/reimburse/installment payload 含聚合值(HTML 渲染数据源)"""
        import json
        import re
        from db import init_db, TABLE_NAME
        import sqlite3
        conn = init_db()
        try:
            cur = conn.cursor()
            rows = [
                ("借贷/借出", "2026-07-01 10:00:00", -500.0, "", "借贷", "#借出 #借给小明 #未还"),
                ("借贷/借入", "2026-07-05 10:00:00", 300.0, "", "借贷", "#借入 #向小红借 #未还"),
                ("餐饮/外卖/午餐", "2026-07-10 12:00:00", -88.0, "", "生活", "客户午餐 #待报销"),
                ("分期/手机", "2026-07-01 00:00:00", -3400.0, "", "生活", "#分期 手机 第1期/3"),
                ("分期/手机", "2026-09-01 00:00:00", -3300.0, "", "生活", "#分期 手机 第3期/3"),
            ]
            for c, t, a, acc, l, n in rows:
                cur.execute(
                    f"INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (c, t, a, acc, l, "人民币", n),
                )
            conn.commit()
        finally:
            conn.close()

        def _payload(qt, *extra):
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, qt, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            return json.loads(m.group(1))

        p = _payload("debt")
        assert p["status"] == "ok"
        assert p["data"]["lent_unpaid_total"] == 500.0
        assert p["data"]["borrowed_unpaid_total"] == 300.0

        p = _payload("reimburse")
        assert p["status"] == "ok" and p["data"]["total"] == 88.0

        p = _payload("installment")
        assert p["status"] == "ok"
        g = p["data"]["groups"][0]
        assert g["name"] == "手机" and g["total"] == 6700.0 and g["periods"] == 3


# ── 错误 CLI 输出 ──────────────────────────────────────────────────────────

class TestErrorCliOutput:
    """CLI 抛异常 → HTML 含错误卡片"""

    def test_monthly_bad_format(self, seeded_db):
        """monthly 传非法月份格式"""
        rc, out, err, html_path = _run_bill_inject(
            seeded_db, "monthly", "--month", "not-a-month"
        )
        # bill_inject 把 CLI 错误也包成 HTML 错误页
        _assert_html_well_formed(html_path, allow_error_state=True)

    def test_list_only_from_without_to(self, seeded_db):
        """list 只传 --from 不传 --to → CLI 报错 → HTML 错误页"""
        rc, out, err, html_path = _run_bill_inject(
            seeded_db, "list", "--from", "2026-01-01"
        )
        _assert_html_well_formed(html_path, allow_error_state=True)


# ── BOM 字节序列 ────────────────────────────────────────────────────────────

class TestBomBytes:
    """HTML 输出含 UTF-8 BOM（防御 Windows 老旧工具按 GBK 误判）"""

    def test_summary_html_has_bom(self, seeded_db):
        rc, out, err, html_path = _run_bill_inject(seeded_db, "summary")
        raw = html_path.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf", f"前 3 字节 = {raw[:3]!r}，期望 BOM"


# ── SKILL.md 边界章节关键词校验（ticket 12）──────────────────────────────

class TestSkillMdBoundarySection:
    """SKILL.md 含 §与其他工具的边界 章节 + 关键词"""

    SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"

    def test_skill_md_contains_boundary_section(self):
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "## 与其他工具的边界" in text, "SKILL.md 缺 §与其他工具的边界 章节"

    def test_skill_md_contains_boundary_keywords(self):
        """章节含关键词：SkillBoard / 独立维护 / config-cookie-accounting / 5 层骨架"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        for kw in ["SkillBoard", "独立维护", "config-cookie-accounting.ts", "5 层骨架"]:
            assert kw in text, f"SKILL.md 缺边界关键词: {kw}"

    def test_skill_md_references_categories_mapping(self):
        """§与其他工具的边界 章节引用 references/categories-mapping.md"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "references/categories-mapping.md" in text, \
            "SKILL.md 未引用 references/categories-mapping.md"

    def test_skill_md_has_section_12ab_declaration(self):
        """§📌 输出位置 章节显式声明 §04 原则 12.A / 12.B（ticket 09）"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        assert "## 📌 输出位置" in text, "SKILL.md 缺 §📌 输出位置 章节"
        assert "§04 原则 12.A / 12.B" in text or "12.A / 12.B" in text, \
            "SKILL.md §📌 输出位置 缺 §04 原则 12.A / 12.B 显式声明"

    def test_skill_md_help_wake_words_are_four(self):
        """§唤醒词总表 HELP 行写 4 条唤醒词（ticket 08）"""
        text = self.SKILL_MD.read_text(encoding="utf-8")
        # HELP 行应含 4 条
        for ww in ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]:
            assert ww in text, f"SKILL.md 缺 HELP 唤醒词: {ww}"


# ── HELP HTML ──────────────────────────────────────────────────────────────

class TestHelpHtmlRender:
    """render_help.py 也生成合法 HTML + BOM + 4 条 HELP 唤醒词"""

    def test_help_html_has_bom_and_payload(self, tmp_db_dir):
        rc, out, err, html_path = _run_render_help(tmp_db_dir)
        _assert_html_well_formed(html_path)

    def test_help_html_contains_four_wake_words(self, tmp_db_dir):
        """HELP HTML 含 4 条 HELP 唤醒词字符串"""
        rc, out, err, html_path = _run_render_help(tmp_db_dir)
        text = html_path.read_text(encoding="utf-8-sig")
        for ww in ["饼干记账 HELP", "饼干记账 帮助", "查帮助", "能做什么"]:
            assert ww in text, f"HELP HTML 缺唤醒词: {ww}"

    def test_help_html_filename_starts_with_skill_help_prefix(self, tmp_db_dir):
        """默认输出文件名以「饼干记账_HELP_」开头（§12.B 标准）

        不传 --out，让 render_help.py 用 default_output_path() 生成默认文件名。
        从 stdout 中用「已生成」行解析（这里只校验文件名，不解析完整路径）。
        """
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cmd = [sys.executable, str(RENDER_HELP)]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", env=env, timeout=30,
        )
        assert result.returncode == 0, f"render_help 失败: {result.stderr}"

        # 从 stdout 最后一行提取文件名（不解析完整路径避免 Windows drive: 问题）
        fname = None
        for line in result.stdout.splitlines():
            if "已生成" in line:
                # 取最后一个反斜杠或斜杠后的部分（文件名）
                # 同时处理 Windows \ 和 POSIX /
                last_part = line.replace("\\", "/").rsplit("/", 1)[-1].strip()
                # 去掉可能的尾随标点
                for suffix in [".", ",", ")", "]"]:
                    if last_part.endswith(suffix):
                        last_part = last_part[:-1]
                if last_part.endswith(".html"):
                    fname = last_part
                    break
        assert fname is not None, f"未从 stdout 解析到 HTML 文件名: {result.stdout}"
        assert fname.startswith("饼干记账_HELP_"), \
            f"HELP 文件名应以 '饼干记账_HELP_' 开头，实际: {fname}"
        assert "能力速查" not in fname, \
            f"HELP 文件名不应含 '能力速查'，实际: {fname}"

    def test_help_html_no_sc_dim(self, tmp_db_dir):
        """B2 契约(G4)：渲染输出无 .sc-dim(v15 遗留维度标签),含 B2 四级折叠类名"""
        rc, out, err, html_path = _run_render_help(tmp_db_dir)
        text = html_path.read_text(encoding="utf-8-sig")
        assert 'class="sc-dim"' not in text, \
            "B2 模板不应再渲染 .sc-dim 维度标签(v15 设计契约)"
        # G4 轮次 1:类名 .module/.sub-module/.scene 兼容 tools/双浏览器审查.py
        assert ".module" in text and ".sub-module" in text and ".scene{" in text, \
            "B2 模板应含四级折叠类名 .module/.sub-module/.scene(G4 契约)"
        assert "scene-title" in text, \
            "B2 模板应渲染 .scene-title 场景标题"

    def test_help_html_root_mirror_synced(self, tmp_db_dir):
        """v15 落地契约：render_help.py 末尾 auto-copy 把同一份 HTML 写到 SKILL 根目录的 饼干记账.html

        守 SKILL.md L10 的"功能变更必须同步更新"——从规则下沉为代码。
        用 setup/teardown 备份/恢复根目录的真实文件，不污染 skill 根目录。
        """
        # --- setup: 备份根目录 饼干记账.html (如果存在) ---
        skill_root = Path(__file__).resolve().parent.parent
        root_html = skill_root / "饼干记账.html"
        backup = tmp_db_dir / "饼干记账.html.backup"
        had_root_file = root_html.exists()
        if had_root_file:
            backup.write_bytes(root_html.read_bytes())

        try:
            # --- act: 跑 render_help.py 不传 --out,触发 auto-copy 到根目录 ---
            env = os.environ.copy()
            env["SKILLS_DB_PATH"] = str(tmp_db_dir)
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            result = subprocess.run(
                [sys.executable, str(RENDER_HELP)],
                capture_output=True, text=True,
                encoding="utf-8", env=env, timeout=30,
            )
            assert result.returncode == 0, f"render_help 失败: {result.stderr}"
            assert "已同步" in result.stdout, (
                f"render_help.py stdout 应含 '已同步' 字样（auto-copy 工作证明），实际: {result.stdout}"
            )

            # --- assert: 根目录文件存在 + BOM + 无 .sc-dim + payload 跟 timestamped 一致 ---
            assert root_html.exists(), "auto-copy 后 skill 根目录 饼干记账.html 应存在"

            root_raw = root_html.read_bytes()
            assert root_raw[:3] == b"\xef\xbb\xbf", (
                f"根目录 饼干记账.html 缺 UTF-8 BOM（前 3 字节 = {root_raw[:3]!r}）"
            )
            root_text = root_raw.decode("utf-8-sig")
            assert 'class="sc-dim"' not in root_text, \
                "auto-copy 到根目录的文件也应是 v15 布局（无 .sc-dim）"

            # 从 stdout 的 "已生成" 行解析 timestamped 文件名,跟根目录对比 payload
            ts_fname = None
            for line in result.stdout.splitlines():
                if "已生成" in line:
                    last_part = line.replace("\\", "/").rsplit("/", 1)[-1].strip()
                    for suffix in [".", ",", ")", "]"]:
                        if last_part.endswith(suffix):
                            last_part = last_part[:-1]
                    if last_part.endswith(".html"):
                        ts_fname = last_part
                        break
            assert ts_fname, f"未从 stdout 解析到 timestamped 文件名: {result.stdout}"

            # timestamped 文件路径
            html_dir = skill_root.parent / "biscuit_accountant_html"  # via html_paths.find_db_path
            # 实际 html_dir 来自 find_db_path() = $SKILLS_DB_PATH 父目录 / SKILL_HTML_NAME_html
            # SKILLS_DB_PATH=tmp_db_dir,所以 html_dir = tmp_db_dir / "biscuit_accountant_html"
            ts_path = tmp_db_dir / "biscuit_accountant_html" / ts_fname
            assert ts_path.exists(), f"timestamped 文件不存在: {ts_path}"

            # 提取两边的 payload 段(从 <script id="payload"> 到 </script>)对比
            import re
            payload_re = re.compile(r'<script id="payload"[^>]*>(.*?)</script>', re.DOTALL)
            ts_payload = payload_re.search(ts_path.read_text(encoding="utf-8-sig"))
            root_payload = payload_re.search(root_text)
            assert ts_payload, "timestamped 文件缺 <script id=\"payload\">"
            assert root_payload, "根目录文件缺 <script id=\"payload\">"
            assert ts_payload.group(1) == root_payload.group(1), (
                "根目录 饼干记账.html 的 payload 段必须跟 timestamped 文件的 payload 段字节一致"
            )
        finally:
            # --- teardown: 恢复备份（无论测试成功失败） ---
            if had_root_file:
                root_html.write_bytes(backup.read_bytes())
            elif root_html.exists():
                root_html.unlink()


# ── 模板能力接口(08 §4 硬标准 · G4 决议)─────────────────────────────────────

class TestTemplateCapability:
    """业务 HTML 交互标准:复制数据弹层三选一 + 复制日志 + B1 toast + meta 注入"""

    def test_query_html_has_copy_actions(self, tmp_db_dir):
        """query_view 输出含:复制数据/日志按钮 + 弹层三选一 + B1 toast"""
        rc, out, err, html_path = _run_bill_inject(tmp_db_dir, "summary")
        text = html_path.read_text(encoding="utf-8-sig")
        assert 'id="copyDataBtn"' in text, "缺复制数据按钮(08 §4 硬标准)"
        assert 'id="copyLogBtn"' in text, "缺复制日志按钮(08 §4 硬标准)"
        # 弹层三选一(G4 轮次 2):纯文本/JSON/CSV 三选项
        assert 'data-f="text"' in text and 'data-f="json"' in text and 'data-f="csv"' in text, \
            "缺复制数据弹层三选一(纯文本/JSON/CSV)"
        # B1 toast:知道了按钮 + 4.5s 自动消失
        assert 'id="toastClose"' in text and "4500" in text, "缺 B1 toast(知道了按钮/4.5s)"
        # 5 段/6 段组装函数
        assert "buildData5" in text and "buildLogText" in text, "缺 5 段数据/6 段日志组装"
        # 5 状态之离线态兜底
        assert "data.offline" in text, "缺离线态分支(5 状态契约)"

    def test_bill_inject_injects_meta(self, tmp_db_dir):
        """bill_inject payload 注入 meta(复制数据/日志数据源:scene_id/command_cn/wake_word/version)"""
        import json
        import re
        rc, out, err, html_path = _run_bill_inject(tmp_db_dir, "summary")
        text = html_path.read_text(encoding="utf-8-sig")
        m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
        assert m, "缺 payload 注入点"
        payload = json.loads(m.group(1))
        meta = payload["data"].get("meta", {})
        assert meta.get("scene_id") == "query_today", f"scene_id 期望 query_today,实际 {meta.get('scene_id')}"
        assert meta.get("wake_word") == "查今天", f"wake_word 期望 查今天,实际 {meta.get('wake_word')}"
        assert meta.get("version") == "2.0"
        assert meta.get("command_cn") and meta.get("occurred_at") and meta.get("render_cmd"), \
            "meta 缺 command_cn/occurred_at/render_cmd"

    def test_new_query_types_meta_mapping(self, tmp_db_dir):
        """查询域 4 新类型:scene_id/wake_word 对齐 scenes/query.yaml(门禁 A 层 1 数据源)"""
        import json
        import re
        expect = {
            "tag": ("query_tag", "查标签", ["--tag", "旅行"]),
            "debt": ("query_debt", "查欠款", []),
            "reimburse": ("query_pending_reimburse", "查待报销", []),
            "installment": ("query_installment", "查分期", []),
        }
        for qt, (scene_id, wake_word, extra) in expect.items():
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, qt, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            payload = json.loads(m.group(1))
            assert payload.get("status") == "ok", f"{qt} 状态应 ok:{payload}"
            meta = payload["data"]["meta"]
            assert meta["scene_id"] == scene_id, f"{qt} scene_id 期望 {scene_id},实际 {meta['scene_id']}"
            assert meta["wake_word"] == wake_word, f"{qt} wake_word 期望 {wake_word},实际 {meta['wake_word']}"

    def test_list_output_filename_variant(self, tmp_db_dir):
        """list 变体输出文件名细分(查日期/查区间/查分类/查账户/查账本 · 不传 --out 走默认路径)"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cases = [
            (["list", "--date", "2026-01-02"], "查日期"),
            (["list", "--from", "2026-01-01", "--to", "2026-01-31"], "查区间"),
            (["list", "--category", "餐饮"], "查分类"),
            (["list", "--account", "支付宝"], "查账户"),
            (["list", "--ledger", "旅行"], "查账本"),
        ]
        for args, prefix in cases:
            result = subprocess.run(
                [sys.executable, str(BILL_INJECT)] + args,
                capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
            )
            assert result.returncode == 0, f"bill_inject {' '.join(args)} 失败: {result.stderr}"
            fname = None
            for line in result.stdout.splitlines():
                if "已生成" in line:
                    last_part = line.replace("\\", "/").rsplit("/", 1)[-1].strip()
                    for suffix in [".", ",", ")", "]"]:
                        if last_part.endswith(suffix):
                            last_part = last_part[:-1]
                    if last_part.endswith(".html"):
                        fname = last_part
                        break
            assert fname is not None, f"未从 stdout 解析文件名: {result.stdout}"
            assert fname.startswith(prefix), \
                f"list 变体 {args} 文件名期望以 {prefix} 开头,实际 {fname}"

    def test_list_variant_meta(self, tmp_db_dir):
        """list 变体 meta 对齐 scenes/query.yaml(查某天/查区间/查分类/查账户/查账本)"""
        import json
        import re
        cases = [
            (["--date", "2026-01-02"], "query_date", "查某天"),
            (["--from", "2026-01-01", "--to", "2026-01-31"], "query_range", "查区间"),
            (["--category", "餐饮"], "query_category", "查分类"),
            (["--account", "支付宝"], "query_account", "查账户"),
            (["--ledger", "旅行"], "query_ledger", "查账本"),
        ]
        for extra, scene_id, wake_word in cases:
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, "list", *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            payload = json.loads(m.group(1))
            assert payload.get("status") == "ok", f"list {extra} 状态应 ok:{payload}"
            meta = payload["data"]["meta"]
            assert meta["scene_id"] == scene_id, \
                f"list {extra} scene_id 期望 {scene_id},实际 {meta['scene_id']}"
            assert meta["wake_word"] == wake_word, \
                f"list {extra} wake_word 期望 {wake_word},实际 {meta['wake_word']}"

    def test_analysis_types_meta_mapping(self, tmp_db_dir):
        """分析域 21 新类型:scene_id/wake_word 对齐 scenes/analysis.yaml(门禁 A 层 1 数据源)"""
        import json
        import re
        expect = {
            "yearly": ("yearly_summary", "看年度", ["--year", "2026"]),
            "week": ("week_brief", "看周报", []),
            "category": ("category_breakdown", "看分类", []),
            "account": ("account_breakdown", "看账户", []),
            "ledger": ("ledger_summary", "看账本", []),
            "structure": ("income_expense_structure", "看结构", []),
            "range_compare": ("range_compare", "看双区间", ["--from1", "2026-01-01", "--to1", "2026-01-31", "--from2", "2025-12-01", "--to2", "2025-12-31"]),
            "yoy": ("year_over_year", "看同比", ["--month", "2026-01"]),
            "cat_compare": ("category_compare", "看分类对比", ["--from1", "2026-01-01", "--to1", "2026-01-31", "--from2", "2025-12-01", "--to2", "2025-12-31"]),
            "trend": ("monthly_trend", "看趋势", ["--months", "6"]),
            "cat_trend": ("category_trend", "看分类趋势", ["--category", "餐饮", "--months", "6"]),
            "top": ("top_expense", "看大额", ["--limit", "5"]),
            "top_freq": ("top_frequency", "看高频", ["--limit", "5"]),
            "distribution": ("amount_distribution", "看分布", []),
            "activity": ("activity", "看活跃", []),
            "insight": ("insight", "看洞察", []),
            "anomaly": ("anomaly", "看异常", []),
            "debt_summary": ("debt_summary", "看借贷", []),
            "reimburse_summary": ("reimburse_summary", "看报销", []),
            "installment_summary": ("installment_summary", "看分期", []),
            "refund_summary": ("refund_summary", "看退款", []),
        }
        for qt, (scene_id, wake_word, extra) in expect.items():
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, qt, *extra)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            payload = json.loads(m.group(1))
            assert payload.get("status") == "ok", f"{qt} 状态应 ok:{payload}"
            meta = payload["data"]["meta"]
            assert meta["scene_id"] == scene_id, f"{qt} scene_id 期望 {scene_id},实际 {meta['scene_id']}"
            assert meta["wake_word"] == wake_word, f"{qt} wake_word 期望 {wake_word},实际 {meta['wake_word']}"

    def test_analysis_output_filename_variant(self, tmp_db_dir):
        """分析域新类型输出文件名中文细分(不传 --out 走默认路径)"""
        env = os.environ.copy()
        env["SKILLS_DB_PATH"] = str(tmp_db_dir)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cases = [
            (["yearly", "--year", "2026"], "年度汇总"),
            (["week"], "周报"),
            (["category"], "分类占比"),
            (["insight"], "消费洞察"),
            (["debt_summary"], "借贷总览"),
            (["refund_summary"], "退款统计"),
        ]
        for args, prefix in cases:
            result = subprocess.run(
                [sys.executable, str(BILL_INJECT)] + args,
                capture_output=True, text=True, encoding="utf-8", env=env, timeout=30,
            )
            assert result.returncode == 0, f"bill_inject {' '.join(args)} 失败: {result.stderr}"
            fname = None
            for line in result.stdout.splitlines():
                if "已生成" in line:
                    last_part = line.replace("\\", "/").rsplit("/", 1)[-1].strip()
                    for suffix in [".", ",", ")", "]"]:
                        if last_part.endswith(suffix):
                            last_part = last_part[:-1]
                    if last_part.endswith(".html"):
                        fname = last_part
                        break
            assert fname is not None, f"未从 stdout 解析文件名: {result.stdout}"
            assert fname.startswith(prefix), \
                f"分析域 {args} 文件名期望以 {prefix} 开头,实际 {fname}"

    def test_meta_present_in_all_query_types(self, tmp_db_dir):
        """全部 query_type:正常态注入 meta;错误态(如 list 无参数)仍带复制按钮(08 硬标准)"""
        import json
        import re
        for qt in ["summary", "list", "recent", "search", "tag", "debt", "reimburse", "installment",
                   "monthly", "compare", "breakdown", "overview", "stats",
                   "yearly", "week", "category", "account", "ledger", "structure",
                   "range_compare", "yoy", "cat_compare", "trend", "cat_trend",
                   "top", "top_freq", "distribution", "activity", "insight", "anomaly",
                   "debt_summary", "reimburse_summary", "installment_summary", "refund_summary"]:
            rc, out, err, html_path = _run_bill_inject(tmp_db_dir, qt)
            text = html_path.read_text(encoding="utf-8-sig")
            m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
            payload = json.loads(m.group(1))
            if payload.get("status") == "error":
                # 错误回执页也必带复制数据/日志按钮(08 §6.1 错误回执 HTML)
                assert 'id="copyDataBtn"' in text and 'id="copyLogBtn"' in text, \
                    f"{qt} 错误页缺复制按钮(08 硬标准)"
                continue
            meta = payload["data"].get("meta", {})
            assert meta.get("scene_id"), f"{qt} 缺 meta.scene_id"
            assert meta.get("wake_word"), f"{qt} 缺 meta.wake_word"
