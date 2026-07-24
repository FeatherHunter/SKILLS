"""计划事件CRUD幂等性测试(plan 域)

锁住 ensure / get / list / upsert / update / deactivate等函数。
ensure_plan_event是回执型族依赖的核心幂等函数。

注意:schedule_db 函数不接 conn 参数,靠 conftest.py 的 monkeypatch 路由。
每个 get_connection() 调用返回新的 in-memory conn(共享 schema),
所以测试中不能用 cursor 跨调用拿 id;改用 ensure_plan_event 返回值。
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


def test_ensure_plan_event_create():
    """ensure_plan_event 新建:返回 action=created + 新 id"""
    result = _db.ensure_plan_event(
        date="2026-07-15",
        time_start="10:00",
        time_end="11:00",
        title="测试晨间冥想",
        category="健康.修行",
    )
    assert result["action"] == "created"
    assert isinstance(result["id"], int)
    assert result["id"] > 0


def test_ensure_plan_event_reuse():
    """ensure_plan_event 复用:再次同 (date+time_start+time_end) → action=found,id 不变"""
    r1 = _db.ensure_plan_event(
        date="2026-07-15",
        time_start="10:00",
        time_end="11:00",
        title="测试",
        category="健康.修行",
    )
    r2 = _db.ensure_plan_event(
        date="2026-07-15",
        time_start="10:00",
        time_end="11:00",
        title="测试",
        category="健康.修行",
    )
    assert r2["action"] == "found"
    assert r2["id"] == r1["id"]


def test_upsert_plan_events_24h_constraint():
    """upsert_plan_events(批量)违反 24h 录满约束时抛 ValueError。
    ensure_plan_event 是单条追加,不触发 24h 校验;24h 校验在 upsert_plan_events 里。
    """
    import pytest
    with pytest.raises(ValueError, match="首事件 time_start 必须为 00:00"):
        _db.upsert_plan_events(
            date="2026-07-15",
            events=[
                {"time_start": "08:00", "time_end": "09:00",
                 "title": "断", "category": "工作.AI调优"},
            ],
            validate_24h=True,
        )


def test_get_plan_event():
    """get_plan_event 能取回完整字段"""
    created = _db.ensure_plan_event(
        date="2026-07-15",
        time_start="22:00",
        time_end="23:00",
        title="测试",
        category="调整.休息",
    )
    plan_id = created["id"]
    plan = _db.get_plan_event(plan_id)
    assert plan is not None
    assert plan["title"] == "测试"
    assert plan["is_active"] == 1


def test_list_plan_events_includes_inactive():
    """list_plan_events(include_inactive=True) 能看到 deactivate 的事件"""
    created = _db.ensure_plan_event(
        date="2026-07-15",
        time_start="15:00",
        time_end="16:00",
        title="测试",
        category="工作.AI调优",
    )
    plan_id = created["id"]
    _db.deactivate_plan_event(plan_id)
    events_active = _db.list_plan_events("2026-07-15", include_inactive=False)
    assert plan_id not in [e["id"] for e in events_active]
    events_all = _db.list_plan_events("2026-07-15", include_inactive=True)
    assert plan_id in [e["id"] for e in events_all]
    inactive = [e for e in events_all if e["id"] == plan_id][0]
    assert inactive["is_active"] == 0