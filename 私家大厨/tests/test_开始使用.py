"""
测试: 开始使用域(setup-1 首次使用 4 步向导 · T4)
- check: 环境检测只读不写库
- init: 全新环境 17 表 / 老库 17 表跳过 / 部分库补全 / 重复幂等
- 渲染: 向导 HTML + 完成回执 HTML(08 双按钮 + 占位符注入)
"""
import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = SCRIPT_DIR / "开始使用" / "cli.py"
RENDER = SCRIPT_DIR / "render_开始使用.py"
TEMPLATE = SCRIPT_DIR.parent / "templates" / "开始使用" / "first_use_wizard.html"

EXPECTED_TABLES = 17


def make_env(tmp_path: Path) -> dict:
    """隔离环境: 临时 DB 目录 + 临时输出目录(覆盖外部 env)"""
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def run_cli(env: dict, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def run_render(env: dict, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(RENDER), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def table_count(db_path: Path) -> int:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    finally:
        conn.close()
    return n


def simulate_browser_parse(html: str) -> dict:
    """军规 11 · DOM 渲染级断言(事故 #127 教训): 模拟浏览器解析注入结果

    私家大厨注入约定 = 裸注释占位符 + <script>window.__DATA__ = {...};</script>;
    浏览器只会执行真正的 script 元素,payload 若被 JSON 元素吞没则解析失败 → 页面死。
    断言: 无嵌套吞没(payload script 直接可执行)+ JSON 可解析。
    """
    import re as _re
    assert '<script id="payload"' not in html, "模板不得再用 json-payload 元素(私家大厨约定 = 裸注释占位符)"
    m = _re.search(r'<script>window\.__DATA__ = (\{.*\});</script>', html, _re.S)
    assert m, "未找到可执行的 window.__DATA__ 注入脚本(可能被 JSON 元素吞没)"
    return json.loads(m.group(1))


class TestEnvCheck:
    """环境检测(check)幂等只读"""

    def test_check_returns_ok_on_fresh_env(self, tmp_path):
        r = run_cli(make_env(tmp_path), "check")
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "ok"
        assert data["db_initialized"] is False

    def test_check_does_not_initialize_db(self, tmp_path):
        """check 只读: 不建表不初始化(db_config 导入会创建空文件,以 0 表判定)"""
        r = run_cli(make_env(tmp_path), "check")
        assert r["rc"] == 0
        data = json.loads(r["out"])
        assert data["db_tables"] == 0


class TestInit:
    """建库(幂等 · 17 表判定)"""

    def test_init_fresh_creates_17_tables(self, tmp_path):
        env = make_env(tmp_path)
        r = run_cli(env, "init")
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "ok"
        assert data["created"] is True
        db = tmp_path / "chef_data.db"
        assert db.exists()
        assert table_count(db) == EXPECTED_TABLES

    def test_init_idempotent_twice(self, tmp_path):
        env = make_env(tmp_path)
        r1 = run_cli(env, "init")
        r2 = run_cli(env, "init")
        assert r1["rc"] == 0 and r2["rc"] == 0
        db = tmp_path / "chef_data.db"
        assert table_count(db) == EXPECTED_TABLES

    def test_old_db_17_tables_skips_with_migration_hint(self, tmp_path):
        env = make_env(tmp_path)
        run_cli(env, "init")  # 先建出 17 表老库
        r = run_cli(env, "init")  # 第二次 = 老库场景
        data = json.loads(r["out"])
        assert data["status"] == "ok"
        assert data.get("created") is not True
        assert "跳过建库" in data["skipped"]
        assert data["migration_hint"] and "migrations/*.sql" in data["migration_hint"]

    def test_empty_db_file_completes_to_17_tables(self, tmp_path):
        """空库文件(0 表)→ init 补全到 17 表(幂等补全)"""
        env = make_env(tmp_path)
        db = tmp_path / "chef_data.db"
        conn = sqlite3.connect(str(db))  # 仅创建空文件
        conn.close()
        r = run_cli(env, "init")
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "ok"
        assert table_count(db) == EXPECTED_TABLES

    def test_incompatible_old_schema_returns_friendly_error(self, tmp_path):
        """schema 不兼容的残缺库 → 友好 error(不裸 stacktrace)"""
        env = make_env(tmp_path)
        db = tmp_path / "chef_data.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE recipes (id TEXT PRIMARY KEY)")
        conn.close()
        r = run_cli(env, "init")
        data = json.loads(r["out"])
        assert data["status"] == "error"
        assert data["error"] == "init_failed"
        assert "Traceback" not in r["err"]

    def test_init_db_path_override(self, tmp_path):
        """--db-path 目标路径接线(实施要点: 设 env 当前进程不生效 → 用目标路径建库)"""
        env = make_env(tmp_path)
        target = tmp_path / "custom_data"
        r = run_cli(env, "init", "--db-path", str(target))
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "ok"
        assert data["created"] is True
        db = target / "chef_data.db"
        assert db.exists()
        assert table_count(db) == EXPECTED_TABLES


class TestRenderWizard:
    """渲染: 向导 + 回执(08 双按钮 + 占位符注入)"""

    def test_template_has_unique_placeholder(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_template_has_copy_buttons_hard_standard(self):
        """08 §4: 复制数据 + 复制日志 = 全部 HTML 硬标准"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_template_guard_reads_top_level_envelope(self):
        """守卫必须读顶层信封(payload.scene),禁止 payload.data 残留(信封无 data 包裹)"""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "!payload.scene" in content
        assert "payload.data" not in content

    def test_render_wizard_writes_html(self, tmp_path):
        env = make_env(tmp_path)
        r = run_render(env, "render")
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        files = list(out_dir.glob("首次使用_*.html"))
        assert files, "向导 HTML 未输出"
        html = files[0].read_text(encoding="utf-8")
        assert "window.__DATA__" in html
        assert "<!--INJECT-DATA-->" not in html
        data = simulate_browser_parse(html)
        assert data["scene"]["wizard"]["stage"] in ("need_env", "need_init", "already", "done")

    def test_render_wizard_html_executes_in_browser_simulation(self, tmp_path):
        """军规 11: 注入必须是可执行的 script,不是被 JSON 元素吞没的死 payload(#127 教训)"""
        env = make_env(tmp_path)
        r = run_render(env, "render")
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        html = sorted(out_dir.glob("首次使用_*.html"))[-1].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        d = data
        assert d["copy_data"]["scene_id"] == "first_use"
        assert "复制数据" in html and "复制日志" in html

    def test_render_receipt_with_init_result(self, tmp_path):
        env = make_env(tmp_path)
        init_json = json.dumps({
            "status": "ok", "created": True, "db_path": str(tmp_path / "chef_data.db"),
            "tables": 17, "migration_hint": None,
        }, ensure_ascii=False)
        r = run_render(env, "render", "--init-json", init_json)
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        files = sorted(out_dir.glob("首次使用_*.html"))
        assert files
        html = files[-1].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["scene"]["wizard"]["stage"] == "done"
        assert data["scene"]["init"]["db_path"] == str(tmp_path / "chef_data.db")

    def test_render_wizard_after_init_shows_already(self, tmp_path):
        env = make_env(tmp_path)
        run_cli(env, "init")
        r = run_render(env, "render")
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        files = sorted(out_dir.glob("首次使用_*.html"))
        assert files
        html = files[-1].read_text(encoding="utf-8")
        assert "already" in html
        assert "跳过建库" in html or "已初始化" in html

    def test_render_out_dir_override(self, tmp_path):
        """--out-dir 目标输出目录接线(设 env 当前进程不生效 → 用目标路径输出)"""
        env = make_env(tmp_path)
        target = tmp_path / "custom_out"
        r = run_render(env, "render", "--out-dir", str(target))
        assert r["rc"] == 0, r["err"]
        files = list((target / "setup").glob("首次使用_*.html"))
        assert files, "--out-dir 未生效"
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["scene"]["env"]["output_root"] == str(target)

    def test_render_error_receipt_on_init_failure(self, tmp_path):
        env = make_env(tmp_path)
        init_json = json.dumps({
            "status": "error", "reason": "磁盘只读", "suggest": "检查数据库目录可写性后重试",
        }, ensure_ascii=False)
        r = run_render(env, "render", "--init-json", init_json)
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        files = sorted(out_dir.glob("首次使用_*.html"))
        assert files
        html = files[-1].read_text(encoding="utf-8")
        assert "磁盘只读" in html

    def test_render_db_path_override_shown_in_wizard(self, tmp_path):
        """--db-path 目标路径在向导中如实显示(复制 prompt 不再带默认值)"""
        env = make_env(tmp_path)
        target = tmp_path / "custom_data"
        r = run_render(env, "render", "--db-path", str(target))
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "setup"
        html = sorted(out_dir.glob("首次使用_*.html"))[-1].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["scene"]["env"]["db_path"] == str(target)
        assert str(target) in data["scene"]["next"]["prompt"]
