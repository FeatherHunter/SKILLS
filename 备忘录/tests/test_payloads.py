"""
CLI 各命令的 JSON 输出契约测试(需 DB)
- status/data/message 三段式
- 写命令回执字段:id, content, category, sub_category
- 5 个查询命令(search / get / search-date / reminders / completed)的契约
- sub_category 自由文本原则(不预设白名单)
"""
import json
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT_DIR = Path(__file__).parent.parent / "script"


def _run_cli(*args, env=None):
    """调 memo_cli.py 子进程,捕获 stdout"""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def env_with_tmp_db(tmp_path, monkeypatch):
    """用 tmp 目录建库,环境变量隔离不污染真实 D:/.db"""
    db_dir = tmp_path
    db_path = db_dir / "memo.db"
    init_sql = (SCRIPT_DIR / "init.sql").read_text(encoding="utf-8")
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript(init_sql)
    conn.commit()
    conn.close()
    env = {"SKILLS_DB_PATH": str(db_dir), "PATH": "/usr/bin:/bin"}
    return env


class TestAddNoteContract:
    def test_add_minimal(self, env_with_tmp_db):
        rc, out, err = _run_cli("add", "测试内容", env=env_with_tmp_db)
        assert rc == 0, f"stderr={err}"
        data = json.loads(out)
        assert data["status"] == "ok"
        assert data["data"]["content"] == "测试内容"
        assert data["data"]["category"] == "备忘"  # 默认
        assert "id" in data["data"]

    def test_add_with_sub_category(self, env_with_tmp_db):
        """sub_category 自由文本,任何 2 字都接受"""
        rc, out, _ = _run_cli("add", "跑步 5 公里", "-c", "打卡", "-s", "跑步",
                              env=env_with_tmp_db)
        assert rc == 0
        data = json.loads(out)
        assert data["data"]["sub_category"] == "跑步"

    def test_add_invalid_category(self, env_with_tmp_db):
        rc, out, _ = _run_cli("add", "x", "-c", "无效分类", env=env_with_tmp_db)
        assert rc == 1
        data = json.loads(out)
        assert data["status"] == "error"
        assert "无效分类" in data["message"]

    def test_add_empty_content(self, env_with_tmp_db):
        rc, out, _ = _run_cli("add", "", env=env_with_tmp_db)
        assert rc == 1
        data = json.loads(out)
        assert "不能为空" in data["message"]


class TestSearchContract:
    def test_search_returns_array(self, env_with_tmp_db):
        """search 无关键字时按分类列,返回 array"""
        rc, out, _ = _run_cli("search", "-c", "备忘", env=env_with_tmp_db)
        assert rc == 0
        data = json.loads(out)
        assert data["status"] == "ok"
        assert isinstance(data["data"], list)

    def test_search_with_keyword(self, env_with_tmp_db):
        _run_cli("add", "跑步 5 公里", "-c", "打卡", env=env_with_tmp_db)
        _run_cli("add", "今天开会", "-c", "备忘", env=env_with_tmp_db)
        rc, out, _ = _run_cli("search", "跑步", env=env_with_tmp_db)
        assert rc == 0
        data = json.loads(out)
        assert any("跑步" in item["content"] for item in data["data"])


class TestHtmlFlag:
    """--html flag 在 5 个查询命令上都应存在"""

    @pytest.mark.parametrize("cmd", [
        ["search", "x"],
        ["get", "1"],
        ["search-date", "2026-07-01", "2026-07-31"],
        ["reminders"],
        ["completed"],
        ["sync-from-feishu"],
    ])
    def test_html_flag_exists(self, cmd):
        """--help 应含 --html 描述"""
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), *cmd, "--help"],
            capture_output=True, text=True, encoding="utf-8",
        )
        assert proc.returncode == 0
        assert "--html" in proc.stdout, f"{cmd} 缺 --html flag"


class TestSyncReportContract:
    """备忘录同步(sync-from-feishu)的统计字段契约
    当飞书 CLI 不可用时,feishu_sync.py 走 fast-fail 分支返回 7 个字段 + errors"""

    def test_no_feishu_returns_partial_report(self, env_with_tmp_db, monkeypatch):
        # 强制 is_feishu_available 返回 False
        monkeypatch.setattr("feishu_sync.is_feishu_available", lambda: False)
        rc, out, _ = _run_cli("sync-from-feishu", env=env_with_tmp_db)
        assert rc == 0
        data = json.loads(out)
        assert data["status"] == "ok"
        d = data["data"]
        # fast-fail 分支保证 5 个核心字段全在(backfilled/scanned_done/synced/scanned_pending/errors)
        for field in ["backfilled", "scanned_done", "synced", "scanned_pending", "errors"]:
            assert field in d, f"缺字段 {field}"
        # 飞书不可用时 errors 非空(说明已记录原因)
        assert len(d["errors"]) >= 1
        assert "feishu" in d["errors"][0].lower() or "not available" in d["errors"][0].lower()

    def test_html_flag_generates_report(self, env_with_tmp_db, monkeypatch, tmp_path):
        """--html 应生成 sync_report_*.html,data 含 html_path"""
        monkeypatch.setattr("feishu_sync.is_feishu_available", lambda: False)
        # 让 output/ 指向临时目录,避免污染真实输出
        monkeypatch.chdir(tmp_path)
        rc, out, _ = _run_cli("sync-from-feishu", "--html", env=env_with_tmp_db)
        assert rc == 0, f"stderr={_}"
        data = json.loads(out)
        assert data["status"] == "ok"
        assert "html_path" in data["data"]
        assert "sync_report_" in data["data"]["html_path"]
        assert data["data"]["html_path"].endswith(".html")
        # 验证 HTML 文件实际生成
        from pathlib import Path
        html_path = Path(data["data"]["html_path"])
        assert html_path.exists()
        text = html_path.read_text(encoding="utf-8")
        assert "window.__DATA__" in text
        assert "备忘录同步报告" in text