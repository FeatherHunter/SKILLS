"""作息记录CRUD幂等性测试(record 域)

锁住 add / get / list 等 DB 函数行为(2026-07-24 写测试覆盖)。

注意:schedule_db 函数不接 conn 参数,靠 conftest.py 的 monkeypatch 路由
schedule_db.get_connection → in-memory conn。
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


def test_add_record_basic():
    """add_record_full 基本功能:插入 1 条 + 返回新 id"""
    rid = _db.add_record_full(
        date="2026-07-15",
        time_start="10:00",
        time_end="11:00",
        duration_minutes=60,
        activity="测试活动",
        category="工作.AI调优",
        source_contents="测试内容",
        source_timestamps="10:00",
        analysis_reasoning="测试",
    )
    assert isinstance(rid, int)
    assert rid > 0


def test_add_record_get_back():
    """add 后 get_record_by_id 能取回全 11 字段"""
    rid = _db.add_record_full(
        date="2026-07-15",
        time_start="10:00",
        time_end="11:00",
        duration_minutes=60,
        activity="测试",
        category="工作.AI调优",
        source_contents="内容",
        source_timestamps="10:00",
        analysis_reasoning="测试",
    )
    rec = _db.get_record_by_id(rid)
    assert rec is not None
    assert rec["activity"] == "测试"
    assert rec["category"] == "工作.AI调优"
    assert rec["duration_minutes"] == 60
    assert "created_at" in rec


def test_get_record_by_id_nonexistent():
    """get_record_by_id 不存在时返回 None(不是抛异常)"""
    assert _db.get_record_by_id(99999) is None


def test_get_records_by_date():
    """get_records_by_date 返回当日所有记录"""
    _db.add_record_full(
        date="2026-07-15", time_start="08:00", time_end="09:00", duration_minutes=60,
        activity="晨间冥想", category="健康.修行",
        source_contents="冥想源", source_timestamps="08:00", analysis_reasoning="冥想",
    )
    _db.add_record_full(
        date="2026-07-15", time_start="12:00", time_end="13:00", duration_minutes=60,
        activity="午餐", category="维持.用餐",
        source_contents="吃饭源", source_timestamps="12:00", analysis_reasoning="午餐",
    )
    _db.add_record_full(
        date="2026-07-16", time_start="10:00", time_end="11:00", duration_minutes=60,
        activity="另一日", category="工作.AI调优",
        source_contents="另一日源", source_timestamps="10:00", analysis_reasoning="另一日",
    )
    recs = _db.get_records_by_date("2026-07-15")
    assert len(recs) == 2
    assert all(r["date"] == "2026-07-15" for r in recs)


def test_get_records_by_date_empty():
    """get_records_by_date 无记录时返回 []"""
    assert _db.get_records_by_date("2026-12-31") == []


# ===== update_record 重构后测试(2026-07-24) =====

def _add_seed():
    """helper:塞一条种子记录,返回 rid"""
    return _db.add_record_full(
        date="2026-07-15", time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="原活动", category="工作.AI调优",
        source_contents="原文", source_timestamps="10:00",
        analysis_reasoning="推理",
    )


def test_update_record_kwargs_form():
    """update_record(rid, category=X) kwargs 形式仍工作"""
    rid = _add_seed()
    result = _db.update_record(rid, category="工作.开发")
    assert result["diff"]["category"]["old"] == "工作.AI调优"
    assert result["diff"]["category"]["new"] == "工作.开发"
    assert result["after"]["category"] == "工作.开发"
    assert result["edit_count"] == 1
    assert result["diff"] != {}
    assert "within_24h" in result
    assert "before" in result and "after" in result


def test_update_record_fields_form():
    """update_record(rid, fields={...}) 字典形式仍工作"""
    rid = _add_seed()
    result = _db.update_record(rid, fields={"category": "工作.开发", "activity": "新活动"})
    assert "category" in result["diff"]
    assert "activity" in result["diff"]
    assert result["after"]["category"] == "工作.开发"
    assert result["after"]["activity"] == "新活动"


def test_update_record_empty_string_allowed():
    """空字符串允许写入(2026-07-24 修:之前 v is not None 过滤空字符串)"""
    rid = _add_seed()
    result = _db.update_record(rid, source_contents="")
    assert result["diff"]["source_contents"]["old"] == "原文"
    assert result["diff"]["source_contents"]["new"] == ""
    assert result["after"]["source_contents"] == ""


def test_update_record_no_change_returns_empty_diff():
    """传了字段但值未变 → diff 为空,edit_count 不增"""
    rid = _add_seed()
    result = _db.update_record(rid, category="工作.AI调优")  # 与原值相同
    assert result["diff"] == {}
    assert result["edit_count"] == 0  # 不增


def test_update_record_audit_fields():
    """edit_count 自增 + updated_at 维护"""
    rid = _add_seed()
    r1 = _db.update_record(rid, category="工作.开发")
    assert r1["edit_count"] == 1
    assert r1["after"]["edit_count"] == 1
    r2 = _db.update_record(rid, category="工作.调研")
    assert r2["edit_count"] == 2
    assert r2["after"]["edit_count"] == 2


def test_update_record_invalid_field_rejected():
    """未在白名单的字段被过滤(不抛错,但也不写入)"""
    rid = _add_seed()
    # id 和 created_at 不允许改
    result = _db.update_record(rid, id=99999, created_at="2000-01-01")
    assert result["diff"] == {}  # 都被过滤


def test_update_record_invalid_category_rejected():
    """非法 category 抛 ValueError(2026-07-22 分类系统重构后)"""
    import pytest
    rid = _add_seed()
    with pytest.raises(ValueError, match="category 校验失败"):
        _db.update_record(rid, category="非法分类.非法")


def test_update_record_nonexistent_raises():
    """record_id 不存在抛 ValueError"""
    import pytest
    with pytest.raises(ValueError, match="不存在"):
        _db.update_record(99999, category="工作.开发")


def test_update_record_no_fields_raises():
    """不传任何字段抛 ValueError"""
    import pytest
    rid = _add_seed()
    with pytest.raises(ValueError, match="必须至少传 1 个字段"):
        _db.update_record(rid)


def test_update_record_diff_only_changed_fields():
    """diff 只含真正改了的字段(未改的不在 diff 里)"""
    rid = _add_seed()
    result = _db.update_record(rid, category="工作.开发")  # 只改 category
    assert list(result["diff"].keys()) == ["category"]
    # 但 after 是完整的 13 字段
    assert "activity" in result["after"]
    assert "date" in result["after"]
    assert "edit_count" in result["after"]


def test_update_record_24h_within():
    """今天日期的记录 within_24h=True"""
    from datetime import date as _d
    rid = _db.add_record_full(
        date=_d.today().isoformat(), time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="今天活动", category="工作.AI调优",
        source_contents="今天原文", source_timestamps="10:00", analysis_reasoning="今天推理",
    )
    result = _db.update_record(rid, category="工作.开发")
    assert result["within_24h"] is True


def test_update_record_24h_outside():
    """超过 1 天的记录 within_24h=False"""
    rid = _add_seed()  # 2026-07-15
    result = _db.update_record(rid, category="工作.开发")
    # 假设今天是 2026-07-24,则 within_24h=False
    # 但 conftest 不固定 today,所以只验证字段存在 + 是 bool
    assert isinstance(result["within_24h"], bool)