"""render_record_receipt_edit 测试(Phase 3 闭环,2026-07-24)

锁住:
- payload 关键字段(meta.mode + diff + diff_list + stats.edit_count)
- diff 渲染(field/old/new 3 列)
- 无 diff 模式(独立调用)
- 命名合规
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


def _add_and_correct():
    """helper:塞一条记录并纠正,返回 (rid, diff)"""
    rid = _db.add_record_full(
        date="2026-07-15", time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="原活动", category="工作.AI调优",
        source_contents="原原文", source_timestamps="10:00", analysis_reasoning="原推理",
    )
    result = _db.update_record(rid, fields={"category": "工作.开发", "activity": "新活动"})
    return rid, result["diff"]


def test_render_record_receipt_edit_basic():
    """基本功能:返回 status=ok,含 diff"""
    from schedule_html_render import render_record_receipt_edit
    rid, diff = _add_and_correct()
    result = render_record_receipt_edit(rid, diff=diff)
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "record-receipt-edit"
    assert d["meta"]["title"] == "已纠正"
    assert d["meta"]["record_id"] == rid
    assert d["stats"]["diff_count"] == 2
    assert d["stats"]["edit_count"] == 1
    assert "category" in d["diff"]
    assert "activity" in d["diff"]


def test_render_record_receipt_edit_diff_list():
    """diff_list 含 field/old/new 3 元素(给模板渲染用)"""
    from schedule_html_render import render_record_receipt_edit
    rid, diff = _add_and_correct()
    result = render_record_receipt_edit(rid, diff=diff)
    dlist = result["data"]["diff_list"]
    assert len(dlist) == 2
    # 验证每条都有 field/old/new
    for d in dlist:
        assert "field" in d
        assert "old" in d
        assert "new" in d
    # 验证 category 字段被正确转换
    cat = [d for d in dlist if d["field"] == "category"][0]
    assert cat["old"] == "工作.AI调优"
    assert cat["new"] == "工作.开发"


def test_render_record_receipt_edit_no_diff():
    """不传 diff → diff={}(独立查看模式)"""
    from schedule_html_render import render_record_receipt_edit
    rid, _ = _add_and_correct()
    result = render_record_receipt_edit(rid)  # 不传 diff
    assert result["status"] == "ok"
    assert result["data"]["diff"] == {}
    assert result["data"]["diff_list"] == []
    assert result["data"]["stats"]["diff_count"] == 0


def test_render_record_receipt_edit_nonexistent():
    """不存在 record_id → status=error"""
    from schedule_html_render import render_record_receipt_edit
    result = render_record_receipt_edit(99999)
    assert result["status"] == "error"
    assert "未找到" in result["message"]


def test_render_record_receipt_edit_meta_audit():
    """meta 含 edit_count + updated_at(审计字段)"""
    from schedule_html_render import render_record_receipt_edit
    rid, diff = _add_and_correct()
    result = render_record_receipt_edit(rid, diff=diff)
    meta = result["data"]["meta"]
    assert "edit_count" in meta
    assert meta["edit_count"] == 1
    assert "updated_at" in meta
    assert meta["updated_at"]  # 非空


def test_render_record_receipt_edit_record_full_fields():
    """record 字段含完整 13 字段(含 updated_at + edit_count)"""
    from schedule_html_render import render_record_receipt_edit
    rid, diff = _add_and_correct()
    result = render_record_receipt_edit(rid, diff=diff)
    record = result["data"]["record"]
    assert "updated_at" in record
    assert "edit_count" in record
    assert record["edit_count"] == 1
    assert record["category"] == "工作.开发"  # 纠正后


def test_render_record_receipt_edit_prompts():
    """3 个 prompt(continue / overview / review)都存在 + 含 diff 上下文"""
    from schedule_html_render import render_record_receipt_edit
    rid, diff = _add_and_correct()
    result = render_record_receipt_edit(rid, diff=diff)
    prompts = result["data"]["prompts"]
    assert "continue" in prompts
    assert "overview" in prompts
    assert "review" in prompts
    # continue prompt 应含"纠正"
    assert "纠正" in prompts["continue"]
    # review prompt 应含"复盘"
    assert "复盘" in prompts["review"]


def test_render_record_receipt_edit_filename_compliance(tmp_path, monkeypatch):
    """命名合规:<command>_<YYYYMMDD>_<HHMMSS>.html"""
    import re
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    from schedule_html_render import record_output_path
    p = record_output_path("record-receipt-edit", {"record_id": 1})
    assert re.match(r"^[a-z_]+_\d{8}_\d{6}\.html$", p.name), p.name
    assert p.name.startswith("record_receipt_edit_")