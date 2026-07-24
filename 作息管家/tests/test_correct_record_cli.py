"""correct-record CLI 集成测试(2026-07-24 闭环 Phase 2)

锁住 CLI 子命令:
- 参数解析(--field value / --json 形式)
- 错误处理(不存在 id / 非法 category / 无字段)
- 调用 update_record 返回 before/after diff
- edit_count 自增
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = str(SCRIPTS_DIR / "schedule_cli.py")


def _run(args, db_path):
    """跑 CLI + 拿 JSON 输出"""
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_path)
    cwd = str(SCRIPTS_DIR.parent)  # 作息管家目录
    result = subprocess.run(
        [sys.executable, CLI] + args,
        capture_output=True, text=True, env=env, timeout=30, cwd=cwd,
    )
    out = result.stdout.strip()
    if not out:
        return None, result.stderr, result.returncode
    start = out.find("{")
    if start < 0:
        return None, result.stderr, result.returncode
    try:
        return json.loads(out[start:]), None, result.returncode
    except Exception as e:
        return None, f"JSON parse error: {e}\nraw: {out}", result.returncode


def _setup_with_one_record(db_path):
    """init DB + add 一条记录,返回 record_id"""
    _run(["init"], db_path)
    out, err, rc = _run([
        "add",
        "--date", "2026-07-15",
        "--time-start", "10:00",
        "--time-end", "11:00",
        "--duration-minutes", "60",
        "--activity", "原活动",
        "--category", "工作.AI调优",
        "--source-contents", "原文",
        "--source-timestamps", "10:00",
        "--analysis-reasoning", "推理",
    ], db_path)
    assert out and out["status"] == "ok", f"add failed: out={out}, err={err}, rc={rc}"
    return out["data"]["id"]


# ===== 正常场景 =====

def test_correct_record_single_field(tmp_path):
    """改 1 个字段 → 返回 diff 含 1 条"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, err, rc = _run(["correct-record", str(rid),
                       "--category", "工作.开发"], db)
    assert out, f"err={err} rc={rc}"
    assert out["status"] == "ok"
    assert "category" in out["data"]["diff"]
    assert out["data"]["diff"]["category"]["old"] == "工作.AI调优"
    assert out["data"]["diff"]["category"]["new"] == "工作.开发"
    assert out["data"]["edit_count"] == 1
    assert "已纠正 1 个字段" in out["message"]


def test_correct_record_multiple_fields(tmp_path):
    """改多个字段 → diff 含多条"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid),
                       "--category", "工作.调研",
                       "--activity", "新活动",
                       "--source-contents", "新原文"], db)
    assert out and out["status"] == "ok"
    assert len(out["data"]["diff"]) == 3
    assert out["data"]["edit_count"] == 1


def test_correct_record_json_form(tmp_path):
    """--json 形式传入"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid),
                       "--json", '{"category":"工作.开发","activity":"JSON活动"}'], db)
    assert out and out["status"] == "ok"
    assert len(out["data"]["diff"]) == 2
    assert out["data"]["diff"]["category"]["new"] == "工作.开发"


def test_correct_record_json_at_form(tmp_path):
    """--json @file.json 形式"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    json_file = tmp_path / "correction.json"
    json_file.write_text('{"activity":"@file活动"}', encoding="utf-8")
    out, _, _ = _run(["correct-record", str(rid), "--json", f"@{json_file}"], db)
    assert out and out["status"] == "ok"
    assert out["data"]["diff"]["activity"]["new"] == "@file活动"


def test_correct_record_no_change(tmp_path):
    """字段值未变 → diff 空 + edit_count 不增"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid),
                       "--category", "工作.AI调优"], db)
    assert out and out["status"] == "ok"
    assert out["data"]["diff"] == {}
    assert out["data"]["edit_count"] == 0


def test_correct_record_increments_edit_count(tmp_path):
    """多次纠正 → edit_count 自增"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    _run(["correct-record", str(rid), "--category", "工作.开发"], db)
    _run(["correct-record", str(rid), "--category", "工作.调研"], db)
    _run(["correct-record", str(rid), "--activity", "第3次"], db)
    out, _, _ = _run(["get-record", str(rid)], db)
    assert out["data"]["edit_count"] == 3


# ===== 错误场景 =====

def test_correct_record_no_args_shows_usage(tmp_path):
    """无参 → 显示用法(不抛栈)"""
    db = tmp_path / "test.db"
    _setup_with_one_record(db)
    out, _, _ = _run(["correct-record"], db)
    assert out and out["status"] == "error"
    assert "用法" in out["message"]
    assert "available_fields" in out
    assert "category" in out["available_fields"]


def test_correct_record_nonexistent_id(tmp_path):
    """不存在 id 报错(不抛栈)"""
    db = tmp_path / "test.db"
    _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", "999", "--category", "工作.开发"], db)
    assert out and out["status"] == "error"
    assert "不存在" in out["message"]


def test_correct_record_invalid_id_format(tmp_path):
    """id 非整数报错"""
    db = tmp_path / "test.db"
    _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", "abc", "--category", "工作.开发"], db)
    assert out and out["status"] == "error"
    assert "整数" in out["message"]


def test_correct_record_no_fields(tmp_path):
    """不传任何字段报错"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid)], db)
    assert out and out["status"] == "error"
    assert "至少传 1 个字段" in out["message"]


def test_correct_record_invalid_category(tmp_path):
    """非法 category 报错(白名单校验生效)"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid), "--category", "非法.非法"], db)
    assert out and out["status"] == "error"
    assert "category 校验失败" in out["message"]


def test_correct_record_invalid_field_name(tmp_path):
    """非法字段名报错(不在白名单)"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid), "--id", "999"], db)
    assert out and out["status"] == "error"
    assert "非法字段" in out["message"]


def test_correct_record_json_parse_error(tmp_path):
    """--json 解析失败报错"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid), "--json", "{not json}"], db)
    assert out and out["status"] == "error"
    assert "json" in out["message"].lower() or "JSON" in out["message"]


def test_correct_record_unknown_arg(tmp_path):
    """未知参数报错"""
    db = tmp_path / "test.db"
    rid = _setup_with_one_record(db)
    out, _, _ = _run(["correct-record", str(rid), "--unknown", "x"], db)
    assert out and out["status"] == "error"
    assert "未知参数" in out["message"]


# ===== main 分发 =====

def test_correct_command_registered():
    """'correct-record' 命令已注册到 main 分发"""
    db = Path("/tmp/test_register.db")
    if db.exists():
        db.unlink()
    db.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db)
    cwd = str(SCRIPTS_DIR.parent)
    # 跑 init 让 main 识别到 init 命令
    r = subprocess.run(
        [sys.executable, CLI, "correct-record"],
        capture_output=True, text=True, env=env, timeout=30, cwd=cwd,
    )
    # 应该返回 status=error + 用法提示(不是"未知命令")
    out = r.stdout
    assert "未知命令" not in out, f"correct-record 未注册到 main: {out}"
    assert "用法" in out