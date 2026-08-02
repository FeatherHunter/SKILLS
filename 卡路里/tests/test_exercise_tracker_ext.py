#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ticket #5 · 运动 39 场景 — exercise_tracker 扩展测试(2026-08-02)

覆盖:
  1. DB 迁移:exercise_log 加 steps/max_heart_rate/is_deleted/is_backfill;daily_goal 加 exercise_goal
  2. add_record 新字段(步数/最高心率/补录标识)
  3. delete_record 软删除 + 快照
  4. update_record 改前/改后 diff
  5. update_day 按日期批量更新
  6. copy_yesterday 复制/跳过判定
  7. batch_add 写入/失败统计
  8. delete_day / delete_range 软删除计数
  9. resolve_window 自然窗口解析
"""

import os
import sqlite3
import sys

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from db import init_db  # noqa: E402


@pytest.fixture()
def tmp_db(tmp_path):
    """独立临时 DB(避开 session temp_db,本组测试需要干净 exercise_log)"""
    db_path = tmp_path / "calorie_data.db"
    init_db(str(db_path))
    return db_path


@pytest.fixture()
def ex_env(tmp_db, monkeypatch):
    """monkeypatch SKILLS_DB_PATH 指向 tmp_db + 重载 exercise_tracker"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_db.parent))
    import importlib
    import db as db_mod
    import exercise_tracker as ex_mod
    importlib.reload(db_mod)
    importlib.reload(ex_mod)
    return ex_mod


# ---------- 1. DB 迁移 ----------

def test_exercise_log_new_columns(tmp_db):
    conn = sqlite3.connect(str(tmp_db))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(exercise_log)").fetchall()]
    for col in ("steps", "max_heart_rate", "is_deleted", "is_backfill"):
        assert col in cols, f"exercise_log 缺列 {col}"
    conn.close()


def test_daily_goal_exercise_goal_column(tmp_db):
    conn = sqlite3.connect(str(tmp_db))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_goal)").fetchall()]
    assert "exercise_goal" in cols
    conn.execute("UPDATE daily_goal SET exercise_goal = 300 WHERE id = 1")
    conn.commit()
    conn.close()


# ---------- 2. add_record 新字段 ----------

def test_add_record_extra_fields(ex_env):
    et = ex_env
    rid, r = et.add_record("2026-07-01", "跑步", 300, minutes=30, category="有氧",
                           distance=5.0, heart_rate=140, max_heart_rate=165)
    assert r["max_heart_rate"] == 165 and r["steps"] is None
    rid2, r2 = et.add_record("2026-07-01", "走路", 80, minutes=20, category="日常",
                             steps=4000, period="晚上")
    assert r2["steps"] == 4000
    rid3, r3 = et.add_record("2026-07-01", "哑铃弯举", 22, category="力量",
                             set_index=1, load_kg=10, reps=10, is_backfill=True)
    assert r3["is_backfill"] == 1


# ---------- 3. 软删除 ----------

def test_delete_record_soft(ex_env):
    et = ex_env
    rid, _ = et.add_record("2026-07-01", "走路", 80, minutes=20)
    snapshot = et.delete_record(rid)
    assert snapshot["exercise_type"] == "走路"
    conn = et.get_db()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT is_deleted FROM exercise_log WHERE id = ?", (rid,)).fetchone()
    assert row["is_deleted"] == 1
    conn.close()


def test_delete_day_and_range(ex_env):
    et = ex_env
    et.add_record("2026-07-01", "跑步", 300, minutes=30)
    et.add_record("2026-07-02", "深蹲", 30, minutes=15)
    et.add_record("2026-07-02", "深蹲", 30, minutes=15)
    et.add_record("2026-07-03", "骑行", 150, minutes=30)
    assert et.delete_day("2026-07-03") == 1
    assert et.delete_range("2026-07-01", "2026-07-02") == 3
    assert et.delete_range("2026-07-01", "2026-07-02") == 0  # 幂等:已删不计


# ---------- 4/5. update_record / update_day ----------

def test_update_record_diff(ex_env):
    et = ex_env
    rid, _ = et.add_record("2026-07-01", "跑步", 300, minutes=30)
    old, new = et.update_record(rid, {"calories_burned": 320, "note": "加量"})
    assert old["calories_burned"] == 300 and new["calories_burned"] == 320
    assert new["note"] == "加量"


def test_update_day_matched_count(ex_env):
    et = ex_env
    et.add_record("2026-07-02", "深蹲", 30, minutes=15, category="力量", reps=8)
    et.add_record("2026-07-02", "深蹲", 30, minutes=15, category="力量", reps=8)
    matched, results = et.update_day("2026-07-02", {"reps": 10})
    assert matched == 2
    assert all(new["reps"] == 10 for _, new in results)


# ---------- 6. copy_yesterday ----------

def test_copy_yesterday_skip_duplicate(ex_env):
    from datetime import date, timedelta
    et = ex_env
    y = (date.today() - timedelta(days=1)).isoformat()
    t = date.today().isoformat()
    et.add_record(y, "跑步", 320, minutes=30)
    et.add_record(y, "哑铃弯举", 22, minutes=10, category="力量")
    et.add_record(t, "跑步", 320, minutes=30)  # 与昨天跑步相同 → 跳过
    copied, skipped, details, source, target = et.copy_yesterday()
    assert copied == 1 and skipped == 1
    assert target == t and source == y


# ---------- 7. batch_add ----------

def test_batch_add_stats(ex_env):
    et = ex_env
    res = et.batch_add([
        {"date": "2026-07-03", "type": "骑行", "calories": 150, "minutes": 30},
        {"date": "2026-07-03", "type": "", "calories": 100},  # 失败:空类型
        {"date": "2026-07-04", "type": "跳绳", "calories": 200, "minutes": 20},
    ])
    assert res["written"] == 2
    assert res["failed"] == 1
    assert res["failures"][0]["reason"]


# ---------- 8. resolve_window ----------

def test_resolve_window(ex_env):
    from datetime import datetime
    et = ex_env
    now = datetime(2026, 7, 15)  # 周三
    assert et.resolve_window("today", now=now) == ("2026-07-15", "2026-07-15")
    assert et.resolve_window("yesterday", now=now) == ("2026-07-14", "2026-07-14")
    assert et.resolve_window("week", now=now) == ("2026-07-13", "2026-07-15")
    assert et.resolve_window("last-week", now=now) == ("2026-07-06", "2026-07-12")
    assert et.resolve_window("month", now=now) == ("2026-07-01", "2026-07-15")
    assert et.resolve_window("last-month", now=now) == ("2026-06-01", "2026-06-30")
    assert et.resolve_window(None, days=7, now=now) == ("2026-07-09", "2026-07-15")
    assert et.resolve_window(None, from_date="2026-06-01", to_date="2026-06-10", now=now) == \
        ("2026-06-01", "2026-06-10")
