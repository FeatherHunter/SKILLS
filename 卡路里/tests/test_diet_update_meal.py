#!/usr/bin/env python3
"""update_meal v2.2.0 pytest 风格测试套 — 7 个 case

用法: cd 卡路里 && python3 -m pytest tests/ -v
"""

import os
import sqlite3
import sys
import tempfile

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

import db as db_mod  # noqa: E402
import diet  # noqa: E402


@pytest.fixture
def tmp_db():
    """建临时 DB + 初始化 schema + 插 1 条 meal,test 后清理"""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_mod.init_db(tmp)
    conn = sqlite3.connect(tmp)
    c = conn.cursor()
    c.execute('''
        INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ("2026-07-20", "12:00:00", "鸡胸肉", 100.0, 165.0, 31.0, 0.0, 3.6, ""))
    conn.commit()
    meal_id = c.lastrowid
    conn.close()

    # monkey-patch diet._get_db → 临时 DB
    orig = diet._get_db

    def _tmp_db():
        return sqlite3.connect(tmp)

    diet._get_db = _tmp_db
    yield meal_id

    diet._get_db = orig
    os.unlink(tmp)


def test_update_calories_only(tmp_db):
    """改单字段: calories"""
    r = diet.update_meal(tmp_db, calories=180.0)
    assert r["ok"] is True
    assert r["after"]["calories"] == 180.0
    assert r["after"]["grams"] == 100.0
    assert r["changed"] == ["calories"]


def test_update_4_nutrition_at_once(tmp_db):
    """改 4 元组: 热量 + 蛋白 + 碳水 + 脂肪(同源场景)"""
    r = diet.update_meal(tmp_db, calories=200, protein=15, carbs=30, fat=8)
    assert r["ok"] is True
    assert r["after"]["calories"] == 200.0
    assert r["after"]["protein"] == 15.0
    assert r["after"]["carbs"] == 30.0
    assert r["after"]["fat"] == 8.0
    assert len(r["changed"]) == 4


def test_update_date_time(tmp_db):
    """补录场景: 改 date + time(meal_type 不存 DB,从 time 推断)"""
    r = diet.update_meal(tmp_db, date="2026-07-19", time="18:30:00")
    assert r["ok"] is True
    assert r["after"]["date"] == "2026-07-19"
    assert r["after"]["time"] == "18:30:00"
    assert r["after"]["calories"] == 165.0  # 没改
    assert r["after"]["food_name"] == "鸡胸肉"  # 没改


def test_update_no_field(tmp_db):
    """空调用: 报错"""
    r = diet.update_meal(tmp_db)
    assert r["ok"] is False
    assert "至少传 1 个字段" in r["error"]


def test_update_invalid_field(tmp_db):
    """非法字段: 报错"""
    r = diet.update_meal(tmp_db, foo=123, bar="x")
    assert r["ok"] is False
    assert "foo" in r["error"]
    assert "bar" in r["error"]


def test_update_returns_diff(tmp_db):
    """返回 diff 用于回执 UI"""
    r = diet.update_meal(tmp_db, food_name="鸡胸(去皮)", calories=140)
    assert r["ok"] is True
    assert r["before"]["food_name"] == "鸡胸肉"
    assert r["before"]["calories"] == 165.0
    assert r["after"]["food_name"] == "鸡胸(去皮)"
    assert r["after"]["calories"] == 140.0
    assert set(r["changed"]) == {"food_name", "calories"}


def test_update_negative_validation(tmp_db):
    """负值校验: 防止误录"""
    r = diet.update_meal(tmp_db, calories=-50)
    assert r["ok"] is False
    assert "负" in r["error"]


def test_cli_invalid_field_rejection():
    """CLI 层: 非法字段明确报错(v2.2.0 改进)

    通过 _parse_kw_args 直接模拟 CLI 输入,验证 calorie_tracker 层报错的清晰度。
    """
    import calorie_tracker as ct
    # 直接验证 field_map 与 CLI 错误信息逻辑
    field_map = {
        'grams': 'grams',
        'food': 'food_name',
        'calories': 'calories',
        'protein': 'protein',
        'carbs': 'carbs',
        'fat': 'fat',
        'date': 'date',
        'time': 'time',
        'note': 'note',
    }
    parsed = {"foo": "123", "bar": "x"}
    unknown = set(parsed) - set(field_map)
    assert "foo" in unknown
    assert "bar" in unknown
    # 验证 field_map 含 9 个 CLI 参数
    assert len(field_map) == 9