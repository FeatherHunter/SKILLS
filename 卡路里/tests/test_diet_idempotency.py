# -*- coding: utf-8 -*-
"""test_diet_idempotency.py — 幂等防重验证(#262 数据治理)

隔离: 临时 DB(SKILLS_DB_PATH → tmp_path),不碰生产库
验证:
  1. add_meal 同 date+time+food_name 重复调用 → 第二次 duplicate=True,不新增行
  2. add_meal 不同 food_name → 正常新增
  3. add_meals_batch 含重复条目 → skipped 计数 + 不新增
"""
import sys
import os
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def iso_db(tmp_path, monkeypatch):
    """临时 DB 隔离: SKILLS_DB_PATH → tmp_path, import diet 前设置

    仅本文件测试使用(非 autouse,避免污染其他测试文件的 session temp_db)。
    teardown 恢复 diet 模块(删除重载残留),避免污染后续测试:
    重载后的 diet 带着旧 DB_PATH 常量,若残留会导致后续测试写错库。
    """
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import db as db_mod
    if "diet" in sys.modules:
        del sys.modules["diet"]
    import diet
    yield diet
    # teardown: 清掉重载残留,让后续 import diet 重新解析 DB_PATH
    if "diet" in sys.modules:
        del sys.modules["diet"]


def test_add_meal_idempotent_dup(iso_db):
    """同 date+time+food_name 重复 → 第二次跳过"""
    r1 = iso_db.add_meal("米饭", 232, 4.3, carbs=50, fat=0.5, grams=200,
                         target_date="2026-08-11", target_time="12:30:00")
    assert r1.get("id") is not None
    assert r1.get("rows_affected") == 1

    r2 = iso_db.add_meal("米饭", 232, 4.3, carbs=50, fat=0.5, grams=200,
                         target_date="2026-08-11", target_time="12:30:00")
    assert r2.get("duplicate") is True
    assert r2.get("rows_affected") == 0
    assert "重复" in r2.get("message", "")

    # 库中仅 1 行
    import db
    conn = db.get_db(db.find_db_path(SCRIPTS_DIR.parent, "calorie_data.db"))
    n = conn.execute("SELECT COUNT(*) FROM food_log WHERE food_name='米饭'").fetchone()[0]
    conn.close()
    assert n == 1


def test_add_meal_diff_food_ok(iso_db):
    """不同食物名 → 正常新增(不误拦)"""
    iso_db.add_meal("米饭", 232, 4.3, grams=200, target_date="2026-08-11", target_time="12:30:00")
    r = iso_db.add_meal("面条", 280, 8, grams=200, target_date="2026-08-11", target_time="12:30:00")
    assert r.get("id") is not None
    assert r.get("rows_affected") == 1


def test_batch_skips_dup(iso_db):
    """批量含重复条目 → skipped,不新增"""
    entries = [
        {"food_name": "米饭", "grams": 200, "calories": 232, "protein": 4.3,
         "date": "2026-08-11", "time": "12:30:00"},
        {"food_name": "米饭", "grams": 200, "calories": 232, "protein": 4.3,
         "date": "2026-08-11", "time": "12:30:00"},
        {"food_name": "清蒸鱼", "grams": 150, "calories": 165, "protein": 28,
         "date": "2026-08-11", "time": "12:30:00"},
    ]
    r = iso_db.add_meals_batch(entries)
    assert r["added"] == 2
    assert r["skipped"] == 1
    assert any("重复" in str(f) for f in r["failures"])

    import db
    conn = db.get_db(db.find_db_path(SCRIPTS_DIR.parent, "calorie_data.db"))
    n = conn.execute("SELECT COUNT(*) FROM food_log").fetchone()[0]
    conn.close()
    assert n == 2
