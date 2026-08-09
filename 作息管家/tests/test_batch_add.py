"""批量导入 batch-add 测试（实施 T4 · fixture DB）

锁定契约（R2 §4 + T4 票面）：
- batch_scenarios.py 自带 COMMANDS 注册表 → CLI 自动发现 dispatch（渐进式注册通道）
- 命令：batch-add <date> --json @records.json [--dry-run] [--stop-on-error]
- 校验复用 add 链路：必填字段同 cmd_add_record field_map；category 白名单下沉 add_record_full；
  时间归一 24:00→23:59；duration 省略按 (end-start) 分钟差计算（负值 +24*60）
- 输出：stdout 单 JSON（status ok/partial/error + data{date,total,success,failed,ids,errors}），
  逐条进度写 stderr
- 幂等性不提供：重复执行重复插入（记录无唯一键，既定设计）
"""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_cli
import batch_scenarios
import schedule_db

OK_REC = {
    "time_start": "14:00",
    "time_end": "15:00",
    "activity": "写测试",
    "category": "工作.AI调优",
    "source_contents": "批量导入",
}


def _db_rows():
    conn = schedule_db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM schedule_records ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _out(capsys):
    return json.loads(capsys.readouterr().out)


# ===== 基本写入 =====

def test_batch_add_ok(conn, capsys):
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([OK_REC])])
    result = _out(capsys)
    assert result["status"] == "ok"
    assert result["data"]["total"] == 1
    assert result["data"]["success"] == 1
    assert result["data"]["failed"] == 0
    assert len(result["data"]["ids"]) == 1
    rows = _db_rows()
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-07-15"
    assert rows[0]["activity"] == "写测试"


def test_batch_add_multiple_and_date_default(conn, capsys):
    rec_no_date = {**OK_REC, "time_start": "09:00", "time_end": "10:30",
                   "activity": "开会"}
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([OK_REC, rec_no_date])])
    result = _out(capsys)
    assert result["status"] == "ok"
    assert result["data"]["success"] == 2
    rows = _db_rows()
    assert len(rows) == 2
    assert {r["activity"] for r in rows} == {"写测试", "开会"}
    assert all(r["date"] == "2026-07-15" for r in rows)


def test_batch_add_duration_computed(conn, capsys):
    """duration 省略 → (end-start) 分钟差；跨日负值 +24*60"""
    recs = [
        {**OK_REC, "time_start": "14:00", "time_end": "15:30", "activity": "甲"},
        {**OK_REC, "time_start": "23:30", "time_end": "00:30", "activity": "乙"},
    ]
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps(recs)])
    result = _out(capsys)
    assert result["status"] == "ok"
    rows = _db_rows()
    assert rows[0]["duration_minutes"] == 90
    assert rows[1]["duration_minutes"] == 60


def test_batch_add_normalize_24h(conn, capsys):
    """时间归一 24:00 → 23:59（对齐 add 链路，batch_add.py 原未处理）"""
    rec = {**OK_REC, "time_start": "23:00", "time_end": "24:00"}
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([rec])])
    assert _out(capsys)["status"] == "ok"
    rows = _db_rows()
    assert rows[0]["time_end"] == "23:59"
    assert rows[0]["duration_minutes"] == 59


def test_batch_add_date_normalized(conn, capsys):
    """命令行 <date> 走 _normalize_date 归一（YYYYMMDD → YYYY-MM-DD）"""
    batch_scenarios.batch_add_main(["20260715", "--json", json.dumps([OK_REC])])
    assert _out(capsys)["status"] == "ok"
    assert _db_rows()[0]["date"] == "2026-07-15"


def test_batch_add_default_empty_fields(conn, capsys):
    """source_timestamps / analysis_reasoning 缺省填空串（对齐 batch_add.py:45-46 语义）"""
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([OK_REC])])
    assert _out(capsys)["status"] == "ok"
    row = _db_rows()[0]
    assert row["source_timestamps"] == ""
    assert row["analysis_reasoning"] == ""


# ===== 容错与状态 =====

def test_batch_add_partial_continues(conn, capsys):
    """单条失败不打断：缺字段那条进 errors，其余照写 → partial"""
    bad = {**OK_REC, "activity": ""}
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([OK_REC, bad, OK_REC])])
    result = _out(capsys)
    assert result["status"] == "partial"
    assert result["data"]["total"] == 3
    assert result["data"]["success"] == 2
    assert result["data"]["failed"] == 1
    assert result["data"]["errors"][0]["index"] == 1
    assert "activity" in result["data"]["errors"][0]["message"]
    assert len(_db_rows()) == 2


def test_batch_add_stop_on_error(conn, capsys):
    """--stop-on-error：遇错即停，剩余不处理"""
    bad = {**OK_REC, "category": "不存在.类别"}
    recs = [bad, OK_REC, OK_REC]
    batch_scenarios.batch_add_main(
        ["2026-07-15", "--json", json.dumps(recs), "--stop-on-error"])
    result = _out(capsys)
    assert result["status"] == "error"
    assert result["data"]["failed"] == 1
    assert result["data"]["success"] == 0
    assert "category" in result["data"]["errors"][0]["message"]
    assert "遇错即停" in result["message"]
    assert _db_rows() == []


def test_batch_add_all_failed_is_error(conn, capsys):
    """全部失败 → status error"""
    bad = {**OK_REC, "category": "不存在.类别"}
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([bad, bad])])
    result = _out(capsys)
    assert result["status"] == "error"
    assert result["data"]["failed"] == 2
    assert _db_rows() == []


def test_batch_add_dry_run(conn, capsys):
    """--dry-run：只校验不写库"""
    recs = [OK_REC, {**OK_REC, "time_start": "16:00", "time_end": "17:00", "activity": "丙"}]
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps(recs), "--dry-run"])
    result = _out(capsys)
    assert result["status"] == "ok"
    assert result["data"]["success"] == 2
    assert result["data"]["ids"] == []
    assert "DRY-RUN" in result["message"]
    assert _db_rows() == []


def test_batch_add_not_idempotent(conn, capsys):
    """幂等性不提供：同一批重复执行 → 重复插入（既定设计，记录无唯一键）"""
    for _ in range(2):
        batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([OK_REC])])
    assert len(_db_rows()) == 2


# ===== 参数与输入错误 =====

def test_batch_add_missing_args(conn, capsys):
    batch_scenarios.batch_add_main([])
    assert _out(capsys)["status"] == "error"


def test_batch_add_invalid_json(conn, capsys):
    batch_scenarios.batch_add_main(["2026-07-15", "--json", "not-json"])
    assert _out(capsys)["status"] == "error"


def test_batch_add_not_list(conn, capsys):
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps(OK_REC)])
    assert _out(capsys)["status"] == "error"


def test_batch_add_empty_list(conn, capsys):
    batch_scenarios.batch_add_main(["2026-07-15", "--json", "[]"])
    result = _out(capsys)
    assert result["status"] == "error"
    assert result["data"]["total"] == 0


def test_batch_add_invalid_date(conn, capsys):
    batch_scenarios.batch_add_main(["2026-13-99", "--json", json.dumps([OK_REC])])
    assert _out(capsys)["status"] == "error"


def test_batch_add_duration_not_int(conn, capsys):
    rec = {**OK_REC, "duration_minutes": "abc"}
    batch_scenarios.batch_add_main(["2026-07-15", "--json", json.dumps([rec])])
    result = _out(capsys)
    assert result["status"] == "error"
    assert "duration_minutes" in result["data"]["errors"][0]["message"]


# ===== 注册通道 E2E =====

def test_discovery_registers_batch_add():
    """真实 scripts/ 目录发现 batch-add（渐进式注册通道契约）"""
    old = sys.modules.pop("batch_scenarios", None)
    try:
        registry = schedule_cli.discover_domain_commands(SCRIPTS_DIR)
    finally:
        if old is not None:
            sys.modules["batch_scenarios"] = old
    assert "batch-add" in registry
    assert callable(registry["batch-add"])


def test_batch_add_via_cli_dispatch(conn, capsys, tmp_path):
    """CLI main() 全链路：batch-add 未在 49 if/elif 中 → else 钩子域 dispatch 命中"""
    records_file = tmp_path / "records.json"
    records_file.write_text(json.dumps([OK_REC, {**OK_REC, "time_start": "16:00",
                                                 "time_end": "17:00", "activity": "丁"}]),
                            encoding="utf-8")
    old = sys.modules.pop("batch_scenarios", None)
    try:
        schedule_cli._DOMAIN_COMMANDS = None
        schedule_cli.main(["batch-add", "2026-07-15", "--json", "@" + str(records_file)])
    finally:
        schedule_cli._DOMAIN_COMMANDS = None
        if old is not None:
            sys.modules["batch_scenarios"] = old
    result = _out(capsys)
    assert result["status"] == "ok"
    assert result["data"]["success"] == 2
    assert len(_db_rows()) == 2
