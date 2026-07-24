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