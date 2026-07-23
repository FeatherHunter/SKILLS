"""CLI 入口集成 test - argparse + exit code + stdout JSON 契约

防破坏性修改:
  - 改 --name → --item-name 后 AI 调用全断, 这里拦截
  - 改 exit code 约定后 CI 脚本全错, 这里拦截
"""
import json
import subprocess

CLI = ["python3", "home_manager.py"]
CWD = "/mnt/d/2Study/StudyNotes/SKILLS/居家管家/scripts"


def _run(*args):
    return subprocess.run(
        [*CLI, *args],
        capture_output=True, text=True, timeout=30,
        cwd=CWD,
    )


def test_search_returns_ok_json():
    """search 成功应返回 {status:ok, data, message}"""
    result = _run("search", "--name", "牛奶")
    assert result.returncode == 0, f"stderr={result.stderr}"
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    assert "data" in data
    assert "message" in data


def test_search_with_no_match_returns_empty_ok():
    """search 无结果仍返回 ok, items 为空列表 (允许缺省键)"""
    result = _run("search", "--name", "ZZZZ_NO_MATCH_ZZZZ")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["status"] == "ok"
    items = data["data"].get("items", [])
    assert items == []


def test_unknown_command_fails_gracefully():
    """未知子命令应报错而非崩溃"""
    result = _run("nonexistent_command_xyz")
    assert result.returncode != 0
    assert "Traceback" not in result.stderr, f"Python 崩溃: {result.stderr}"


def test_unknown_flag_fails_gracefully():
    """未知 flag 应被 argparse 拒绝"""
    result = _run("search", "--unknown-flag-xyz", "X")
    assert result.returncode != 0


def test_no_subcommand_shows_usage():
    """无子命令: argparse 标准行为是 exit 0 + usage 输出 (不崩溃)"""
    result = _run()
    assert result.returncode == 0, "argparse 默认 exit 0"
    combined = (result.stdout + result.stderr).lower()
    assert "usage" in combined
    assert "Traceback" not in result.stderr


def test_help_exits_zero():
    """--help 应正常输出并 exit 0"""
    result = _run("--help")
    assert result.returncode == 0
    assert len(result.stdout) > 0


def test_invalid_id_returns_error_not_crash():
    """无效 ID 应返回结构化 error, 非 Python traceback"""
    result = _run("detail", "--id", "99999999")
    assert result.returncode != 0
    assert "Traceback" not in result.stdout
    assert "Traceback" not in result.stderr


def test_stats_summary_exits_zero():
    """stats --type summary 应 exit 0 (纯读取操作)"""
    result = _run("stats", "--type", "summary")
    assert result.returncode == 0