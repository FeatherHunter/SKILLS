"""tests/test_setup.py — 开始使用域 6 场景 CLI/HTML 测试(隔离契约:scripts/setup/ + templates/开始使用/)

覆盖(对齐 scenes/setup.yaml 6 场景):
- 首次使用向导(init 环境检测只读/建库幂等自愈/4 步状态;完成页「记第一笔」引导)
- 初始化状态(init-status 三重判定:存在+schema+版本;schema 过期迁移提示)
- 一键备份(backup-create 包装公共层 backup.py → JSON 回执)
- 查看备份(backup-list 列表 + 空态)
- 从备份恢复(restore 默认最新/指定名称/无备份错误)
- 导入 CSV(import 自动猜测/显式映射/时间归一化/方向列/失败行收集/dry-run)
- HTML 渲染(6 模板:BOM + charset + payload + 复制按钮 + 弹层三选一 + B1 toast + meta 对齐 yaml)

外部行为校验:CLI --json 三段式 {status, data, message};render.py 输出合法 HTML。
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

SETUP_CLI = SCRIPTS_DIR / "setup" / "cli.py"
SETUP_RENDER = SCRIPTS_DIR / "setup" / "render.py"


def _env(tmp_db_dir):
    return {
        **os.environ.copy(),
        "SKILLS_DB_PATH": str(tmp_db_dir),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }


def _run_cli(tmp_db_dir, *args):
    """跑 setup/cli.py <args> --json,返回解析后的 dict"""
    result = subprocess.run(
        [sys.executable, str(SETUP_CLI)] + list(args) + ["--json"],
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )
    assert result.returncode == 0, (
        f"setup/cli.py {' '.join(args)} rc={result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return json.loads(result.stdout)


def _run_render(tmp_db_dir, mode, *extra, out_name="out.html"):
    out_dir = tmp_db_dir / "html_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / out_name
    result = subprocess.run(
        [sys.executable, str(SETUP_RENDER), mode, "--out", str(out_path)] + list(extra),
        capture_output=True, text=True, encoding="utf-8", env=_env(tmp_db_dir), timeout=30,
    )
    return result, out_path


def _write_csv(tmp_db_dir, name, content: str, encoding="utf-8-sig"):
    """写测试 CSV(默认带 BOM,兼容 Windows 记事本)"""
    p = tmp_db_dir / name
    p.write_bytes(content.encode(encoding))
    return p


# ── 首次使用向导(setup-1-1) ─────────────────────────────────────────────────

class TestInitWizard:
    def test_check_readonly_no_db_created(self, tmp_db_dir):
        """init --check 只读:未初始化不建库"""
        data = _run_cli(tmp_db_dir, "init", "--check")
        assert data["status"] == "ok"
        assert data["data"]["status"]["ready"] is False
        assert data["data"]["env"]["ok"] is True
        assert not (tmp_db_dir / "biscuit_accountant.db").exists(), "check 不应建库"

    def test_check_env_checks_present(self, tmp_db_dir):
        """环境检测 6 项:操作系统/Python/PyYAML/数据目录/HTML 目录/SKILL 目录"""
        data = _run_cli(tmp_db_dir, "init", "--check")
        names = [c["name"] for c in data["data"]["env"]["checks"]]
        assert names == ["操作系统", "Python", "PyYAML", "数据目录", "HTML 目录", "SKILL 目录"]

    def test_init_creates_db_and_verifies(self, tmp_db_dir):
        """init 执行:建库幂等自愈 + 只读验证"""
        data = _run_cli(tmp_db_dir, "init")
        assert data["status"] == "ok"
        assert data["data"]["ready"] is True
        assert (tmp_db_dir / "biscuit_accountant.db").exists()
        steps = [s["step"] for s in data["data"]["steps"]]
        assert "建库(幂等自愈)" in steps and "只读验证" in steps

    def test_init_idempotent(self, tmp_db_dir):
        """重复 init 幂等(不报错,records 保持)"""
        first = _run_cli(tmp_db_dir, "init")
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
                "VALUES ('餐饮', '2026-08-01 12:00:00', -10.0, '测试')")
            conn.commit()
        finally:
            conn.close()
        second = _run_cli(tmp_db_dir, "init")
        assert second["data"]["records"] == 1
        assert second["data"]["ready"] is True

    def test_init_wizard_render(self, tmp_db_dir):
        """向导 HTML:未初始化状态渲染 4 步 + 开始初始化按钮"""
        result, out_path = _run_render(tmp_db_dir, "init-wizard")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "初始化", "setup_init_wizard")
        d = payload["data"]
        assert len(d["steps"]) == 4
        assert d["ready"] is False
        assert "开始初始化" in text

    def test_init_wizard_done_state(self, tmp_db_dir):
        """向导 HTML 完成态:4 步全绿 + 「记第一笔」引导"""
        _run_cli(tmp_db_dir, "init")
        result, out_path = _run_render(tmp_db_dir, "init-wizard")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "初始化", "setup_init_wizard")
        assert payload["data"]["ready"] is True
        assert all(s["done"] for s in payload["data"]["steps"])
        assert "记第一笔" in text


# ── 初始化状态(setup-1-2 · 三重判定) ────────────────────────────────────────

class TestInitStatus:
    def test_uninitialized_triple_fail(self, tmp_db_dir):
        """未初始化:存在/schema/版本 全不通过,ready=False"""
        data = _run_cli(tmp_db_dir, "init-status")
        assert data["status"] == "ok"
        d = data["data"]
        assert d["ready"] is False
        assert d["db_exists"] is False and d["schema_ok"] is False and d["version_ok"] is False
        names = [c["name"] for c in d["checks"]]
        assert names == ["数据存在", "schema", "版本"]

    def test_initialized_triple_pass(self, tmp_db_dir):
        """初始化后:三重判定全过,版本 = v2.0"""
        _run_cli(tmp_db_dir, "init")
        data = _run_cli(tmp_db_dir, "init-status")
        d = data["data"]
        assert d["ready"] is True
        assert d["version"] == "2.0"
        assert all(c["ok"] for c in d["checks"])
        assert d["migration_hint"] is None

    def test_schema_outdated_migration_hint(self, tmp_db_dir):
        """旧版 schema(缺 deleted_at 列)→ schema 不完整 + 显式迁移提示"""
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            conn.execute(
                "CREATE TABLE bills (id INTEGER PRIMARY KEY, category TEXT NOT NULL, "
                "time TEXT NOT NULL, amount REAL NOT NULL, account TEXT DEFAULT '', "
                "ledger TEXT DEFAULT '生活', currency TEXT DEFAULT '人民币', "
                "note TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            conn.commit()
        finally:
            conn.close()
        data = _run_cli(tmp_db_dir, "init-status")
        d = data["data"]
        assert d["db_exists"] is True
        assert d["schema_ok"] is False
        assert d["version_ok"] is False
        assert d["ready"] is False
        assert d["migration_hint"] is not None
        assert "deleted_at" in d["migration_hint"]

    def test_init_status_render(self, tmp_db_dir):
        """初始化状态 HTML:三重判定卡 + 未就绪引导初始化"""
        result, out_path = _run_render(tmp_db_dir, "init-status")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "初始化状态", "setup_init_status")
        assert len(payload["data"]["checks"]) == 3
        assert "去初始化" in text

    def test_init_status_render_ready(self, tmp_db_dir):
        """就绪态 HTML:三重判定全过 + 无迁移提示"""
        _run_cli(tmp_db_dir, "init")
        result, out_path = _run_render(tmp_db_dir, "init-status")
        payload, _ = _assert_well_formed(out_path, "初始化状态", "setup_init_status")
        assert payload["data"]["ready"] is True
        assert payload["data"]["migration_hint"] is None


# ── 一键备份(setup-2-1) ─────────────────────────────────────────────────────

class TestBackupCreate:
    def test_create_returns_receipt(self, tmp_db_dir):
        """一键备份 → 回执含路径/名称/内容/文件清单"""
        _run_cli(tmp_db_dir, "init")
        data = _run_cli(tmp_db_dir, "backup-create")
        assert data["status"] == "ok"
        d = data["data"]
        assert d["target"] and d["name"]
        names = [f["name"] for f in d["files"]]
        assert "biscuit_accountant.db" in names
        assert (tmp_db_dir / "biscuit_accountant_backups" / d["name"]).is_dir()

    def test_create_includes_goals_when_present(self, tmp_db_dir):
        """goals.json 存在时一并备份"""
        _run_cli(tmp_db_dir, "init")
        (tmp_db_dir / "goals.json").write_text('{"budgets":[]}', encoding="utf-8")
        data = _run_cli(tmp_db_dir, "backup-create")
        names = [f["name"] for f in data["data"]["files"]]
        assert "goals.json" in names

    def test_backup_render_receipt(self, tmp_db_dir):
        """一键备份 HTML:回执卡 + 路径 + 文件清单"""
        _run_cli(tmp_db_dir, "init")
        result, out_path = _run_render(tmp_db_dir, "backup-create")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "备份", "setup_backup_create")
        assert payload["data"]["target"]
        assert "备份成功" in text
        assert "biscuit_accountant.db" in text


# ── 查看备份(setup-2-2) ─────────────────────────────────────────────────────

class TestBackupList:
    def test_list_empty(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "backup-list")
        assert data["status"] == "ok"
        assert data["data"]["count"] == 0
        assert data["data"]["backups"] == []

    def test_list_after_create(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "init")
        _run_cli(tmp_db_dir, "backup-create")
        data = _run_cli(tmp_db_dir, "backup-list")
        assert data["data"]["count"] == 1
        b = data["data"]["backups"][0]
        assert b["name"] and b["time"] and b["size"] > 0
        assert "biscuit_accountant.db" in b["files"]

    def test_backup_list_render(self, tmp_db_dir):
        """查看备份 HTML:空态引导一键备份"""
        result, out_path = _run_render(tmp_db_dir, "backup-list")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "备份", "setup_backup_list")
        assert payload["data"]["count"] == 0
        assert "还没有备份" in text
        assert "一键备份" in text

    def test_backup_list_render_with_items(self, tmp_db_dir):
        _run_cli(tmp_db_dir, "init")
        _run_cli(tmp_db_dir, "backup-create")
        result, out_path = _run_render(tmp_db_dir, "backup-list")
        payload, text = _assert_well_formed(out_path, "备份", "setup_backup_list")
        assert payload["data"]["count"] == 1
        assert payload["data"]["backups"][0]["name"]
        assert "biscuit_accountant.db" in text


# ── 从备份恢复(setup-2-3) ───────────────────────────────────────────────────

class TestRestore:
    def test_restore_default_latest(self, tmp_db_dir):
        """默认最新备份:改数据后恢复回备份时状态"""
        from db import init_db, TABLE_NAME
        conn = init_db()
        try:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
                "VALUES ('餐饮', '2026-08-01 12:00:00', -10.0, '备份前')")
            conn.commit()
        finally:
            conn.close()
        _run_cli(tmp_db_dir, "backup-create")

        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            conn.execute(
                f"INSERT INTO {TABLE_NAME} (category, time, amount, note) "
                "VALUES ('出行', '2026-08-02 12:00:00', -5.0, '污染')")
            conn.commit()
        finally:
            conn.close()

        data = _run_cli(tmp_db_dir, "restore")
        assert data["status"] == "ok"
        assert data["data"]["restored"] is True
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
        finally:
            conn.close()
        assert n == 1, f"恢复后应回到备份时 1 条,实际 {n}"

    def test_restore_named_backup(self, tmp_db_dir):
        """显式指定备份名恢复"""
        _run_cli(tmp_db_dir, "init")
        _run_cli(tmp_db_dir, "backup-create")
        data = _run_cli(tmp_db_dir, "restore", "--name", "不存在")
        assert data["status"] == "error"
        assert "恢复失败" in data["message"]

    def test_restore_no_backups_error(self, tmp_db_dir):
        """无备份 → 明确错误"""
        data = _run_cli(tmp_db_dir, "restore")
        assert data["status"] == "error"
        assert "暂无备份" in data["message"]

    def test_restore_render_wizard(self, tmp_db_dir):
        """恢复向导 HTML:备份详情预览 + 确认按钮 + 覆盖警示"""
        _run_cli(tmp_db_dir, "init")
        _run_cli(tmp_db_dir, "backup-create")
        result, out_path = _run_render(tmp_db_dir, "restore")
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "恢复备份", "setup_restore")
        assert payload["data"]["selected"]["name"]
        assert "确认恢复" in text
        assert "覆盖当前数据" in text

    def test_restore_render_empty_error(self, tmp_db_dir):
        """无备份时渲染 → 错误页(exit 0)"""
        result, out_path = _run_render(tmp_db_dir, "restore")
        assert result.returncode == 0, result.stderr
        raw = out_path.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf"
        text = raw.decode("utf-8-sig")
        assert "暂无备份" in text


# ── 导入 CSV(setup-3-1 · G1 最小方案) ───────────────────────────────────────

class TestImport:
    def test_missing_file_errors(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "import", "--file", "C:/不存在的.csv")
        assert data["status"] == "error"
        assert "文件不存在" in data["message"]

    def test_empty_file_arg_errors(self, tmp_db_dir):
        data = _run_cli(tmp_db_dir, "import")
        assert data["status"] == "error"
        assert "文件路径不能为空" in data["message"]

    def test_auto_guess_mapping(self, tmp_db_dir):
        """表头自动猜测:日期/金额/分类/备注 命中"""
        csv_path = _write_csv(tmp_db_dir, "auto.csv",
                              "日期,分类,金额,备注\n2026-08-01,餐饮/外卖/午餐,-35,午饭\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path), "--dry-run")
        assert data["status"] == "ok"
        m = data["data"]["mapping"]
        assert m["date"] == 1 and m["category"] == 2 and m["amount"] == 3 and m["note"] == 4
        assert data["data"]["total_rows"] == 1
        assert data["data"]["preview"][0]["cols"][1] == "餐饮/外卖/午餐"

    def test_explicit_mapping(self, tmp_db_dir):
        """显式映射优先于自动猜测"""
        csv_path = _write_csv(tmp_db_dir, "explicit.csv",
                              "金额,备注,日期,分类\n-20,打车,2026-08-05,出行/网约车\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path),
                        "--mapping", "date=3,amount=1,category=4,note=2", "--dry-run")
        m = data["data"]["mapping"]
        assert m == {"date": 3, "amount": 1, "category": 4, "note": 2}

    def test_import_writes_rows(self, tmp_db_dir):
        """执行导入:逐行校验写入,返回成功行数"""
        _run_cli(tmp_db_dir, "init")
        csv_path = _write_csv(tmp_db_dir, "ok.csv",
                              "日期,分类,金额,备注\n"
                              "2026-08-01,餐饮/外卖/午餐,-35,午饭\n"
                              "2026/08/02,餐饮/咖啡奶茶/奶茶,-18,下午茶\n"
                              "2026-08-03,工资/基本工资,8000,工资\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path))
        assert data["status"] == "ok"
        assert data["data"]["imported"] == 3
        assert data["data"]["failed"] == []
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            n = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
            amounts = [r[0] for r in conn.execute("SELECT amount FROM bills ORDER BY id")]
        finally:
            conn.close()
        assert n == 3
        assert amounts == [-35.0, -18.0, 8000.0]

    def test_time_normalization(self, tmp_db_dir):
        """时间归一化:纯日期补 00:00:00;斜杠格式转换"""
        _run_cli(tmp_db_dir, "init")
        csv_path = _write_csv(tmp_db_dir, "time.csv",
                              "日期,分类,金额\n2026-08-01,餐饮,1\n2026/08/02,出行,2\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path))
        assert data["data"]["imported"] == 2
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            times = [r[0] for r in conn.execute("SELECT time FROM bills ORDER BY id")]
        finally:
            conn.close()
        assert times == ["2026-08-01 00:00:00", "2026-08-02 00:00:00"]

    def test_direction_column(self, tmp_db_dir):
        """收支方向列:含"收"→正,含"支"→负(忽略金额符号)"""
        _run_cli(tmp_db_dir, "init")
        csv_path = _write_csv(tmp_db_dir, "dir.csv",
                              "日期,分类,金额,收/支\n"
                              "2026-08-01,餐饮,35,支出\n"
                              "2026-08-02,工资,5000,收入\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path))
        assert data["data"]["imported"] == 2
        conn = sqlite3.connect(str(tmp_db_dir / "biscuit_accountant.db"))
        try:
            amounts = [r[0] for r in conn.execute("SELECT amount FROM bills ORDER BY id")]
        finally:
            conn.close()
        assert amounts == [-35.0, 5000.0]

    def test_failed_rows_collected(self, tmp_db_dir):
        """失败行收集:非法分类/零金额/坏日期 → failed 列表,不中断"""
        _run_cli(tmp_db_dir, "init")
        csv_path = _write_csv(tmp_db_dir, "bad.csv",
                              "日期,分类,金额\n"
                              "2026-08-01,餐饮/外卖/午餐,-35\n"
                              "2026-08-02,非法分类,-10\n"
                              "bad-date,餐饮,-5\n"
                              "2026-08-04,餐饮,0\n")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path))
        assert data["status"] == "ok"
        assert data["data"]["imported"] == 1
        assert data["data"]["failed_count"] == 3
        rows = [f["row"] for f in data["data"]["failed"]]
        assert rows == [3, 4, 5]  # 表头=第1行;数据行 2 成功,3/4/5 失败

    def test_gbk_encoding(self, tmp_db_dir):
        """GBK 编码自动探测"""
        _run_cli(tmp_db_dir, "init")
        csv_path = _write_csv(tmp_db_dir, "gbk.csv",
                              "日期,分类,金额\n2026-08-01,餐饮,5\n", encoding="gbk")
        data = _run_cli(tmp_db_dir, "import", "--file", str(csv_path), "--dry-run")
        assert data["data"]["encoding"] == "gbk"

    def test_import_render_wizard(self, tmp_db_dir):
        """导入向导 HTML:文件卡 + 映射下拉 + 预览表 + 确认导入"""
        csv_path = _write_csv(tmp_db_dir, "wiz.csv",
                              "日期,分类,金额,备注\n2026-08-01,餐饮/外卖/午餐,-35,午饭\n")
        result, out_path = _run_render(tmp_db_dir, "import", "--file", str(csv_path))
        assert result.returncode == 0, result.stderr
        payload, text = _assert_well_formed(out_path, "导入", "setup_import")
        assert payload["data"]["name"] == "wiz.csv"
        assert payload["data"]["mapping"]["date"] == 1
        assert "列映射" in text and "确认导入" in text

    def test_import_render_missing_file_error(self, tmp_db_dir):
        """缺文件路径 → 渲染错误页(缺参 AI 反问 · 场景 result)"""
        result, out_path = _run_render(tmp_db_dir, "import")
        assert result.returncode == 0, result.stderr
        text = out_path.read_bytes().decode("utf-8-sig")
        assert "缺少文件路径" in text


# ── HTML 渲染通用断言(08 §4 硬标准 · 门禁 A 层 1) ───────────────────────────

def _assert_well_formed(html_path, expect_wake=None, expect_scene=None):
    assert html_path.exists(), f"输出 HTML 不存在: {html_path}"
    raw = html_path.read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "缺 UTF-8 BOM"
    text = raw.decode("utf-8-sig")
    assert 'charset="UTF-8"' in text, "缺 charset"
    m = re.search(r'<script id="payload"[^>]*>(.*?)</script>', text, re.DOTALL)
    assert m, "缺 payload 注入点"
    payload = json.loads(m.group(1))
    # #300 Base 统一:复制数据/日志按钮 = actionBar 控件,toast 走 Base
    assert "复制数据" in text and "复制日志" in text, "缺复制数据/日志按钮"
    assert "hm-actions" in text and "window.actionBar" in text, "复制按钮必须走 Base actionBar"
    assert "hm-toast" in text and "4500" in text, "缺 Base toast(4.5s 自动消失)"
    # meta 对齐 scenes/setup.yaml(门禁 A 层 1)
    meta = payload.get("data", {}).get("meta", {})
    if expect_wake:
        assert meta.get("wake_word") == expect_wake, f"wake_word 期望 {expect_wake},实际 {meta.get('wake_word')}"
    if expect_scene:
        assert meta.get("scene_id") == expect_scene, f"scene_id 期望 {expect_scene},实际 {meta.get('scene_id')}"
    return payload, text


class TestRenderAllTemplates:
    def test_all_six_templates(self, tmp_db_dir):
        """6 模板全部输出合法 HTML(成功态)"""
        _run_cli(tmp_db_dir, "init")
        _run_cli(tmp_db_dir, "backup-create")
        csv_path = _write_csv(tmp_db_dir, "all.csv", "日期,分类,金额\n2026-08-01,餐饮,5\n")
        cases = [
            ("init-wizard", [], "初始化", "setup_init_wizard"),
            ("init-status", [], "初始化状态", "setup_init_status"),
            ("backup-create", [], "备份", "setup_backup_create"),
            ("backup-list", [], "备份", "setup_backup_list"),
            ("restore", [], "恢复备份", "setup_restore"),
            ("import", ["--file", str(csv_path)], "导入", "setup_import"),
        ]
        for i, (mode, extra, wake, scene) in enumerate(cases):
            result, out_path = _run_render(tmp_db_dir, mode, *extra, out_name=f"{i}.html")
            assert result.returncode == 0, f"{mode}: {result.stderr}"
            _assert_well_formed(out_path, wake, scene)
