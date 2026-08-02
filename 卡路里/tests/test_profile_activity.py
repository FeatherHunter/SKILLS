#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ticket #8 · 基础信息 4 场景 — activity_level schema + TDEE 系数 + profile CLI 测试

覆盖:
  1. user_profile.activity_level 列迁移(默认 moderate)
  2. CHECK trigger 拒绝非法活动量
  3. profile.set_activity_level() 单字段设置
  4. profile.update_profile_field() 单字段更新 + 影响提示
  5. TDEE_ACTIVITY_FACTORS / get_activity_factor 映射
  6. calc_tdee 使用 activity_level
"""

import os
import sqlite3
import sys
import tempfile

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from db import init_db  # noqa: E402
from analysis._utils import (  # noqa: E402
    TDEE_ACTIVITY_FACTORS,
    calc_tdee,
    get_activity_factor,
)


@pytest.fixture()
def tmp_db(tmp_path):
    """独立临时 DB(避开 session temp_db,本组测试需要干净 user_profile)"""
    db_path = tmp_path / "calorie_data.db"
    init_db(str(db_path))
    return db_path


@pytest.fixture()
def profile_env(tmp_db, monkeypatch):
    """monkeypatch SKILLS_DB_PATH 指向 tmp_db + 重置 profile 模块缓存"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_db.parent))
    import importlib
    import db as db_mod
    import profile as prof_mod
    importlib.reload(prof_mod)
    importlib.reload(db_mod)
    return prof_mod


def test_activity_level_column_migrated(tmp_db):
    """schema 迁移:user_profile 有 activity_level 列且默认 moderate"""
    conn = sqlite3.connect(str(tmp_db))
    cols = [r[1] for r in conn.execute("PRAGMA table_info(user_profile)").fetchall()]
    assert "activity_level" in cols
    conn.execute(
        "INSERT INTO user_profile (id, age, gender, height_cm) VALUES (1, 30, 'male', 177)"
    )
    conn.commit()
    row = conn.execute("SELECT activity_level FROM user_profile WHERE id = 1").fetchone()
    assert row[0] == "moderate"
    conn.close()


def test_activity_level_check_trigger_rejects_invalid(tmp_db):
    """CHECK trigger:非法活动量被拒"""
    conn = sqlite3.connect(str(tmp_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO user_profile (id, activity_level) VALUES (1, 'insane')"
        )
        conn.commit()
    conn.close()


def test_activity_level_check_trigger_accepts_valid(tmp_db):
    """CHECK trigger:5 档合法值全部可写"""
    conn = sqlite3.connect(str(tmp_db))
    for i, level in enumerate(["sedentary", "light", "moderate", "active", "very_active"]):
        conn.execute(
            "UPDATE user_profile SET activity_level = ? WHERE id = 1", (level,)
        )
    conn.commit()
    conn.close()


def test_set_activity_level(profile_env):
    """profile activity <level> 单字段设置,返回系数对比"""
    prof = profile_env
    result = prof.set_activity_level("active")
    assert result["activity_level"] == "active"
    assert result["activity_factor"] == 1.725
    assert result["old_level"] == "moderate"
    assert result["old_factor"] == 1.55
    # 验证落库
    p = prof.get_profile()
    assert p["activity_level"] == "active"


def test_set_activity_level_invalid(profile_env):
    """非法活动量抛 InvalidActivityLevelError"""
    prof = profile_env
    with pytest.raises(prof.InvalidActivityLevelError):
        prof.set_activity_level("insane")


def test_update_profile_field_height(profile_env):
    """改档案:改身高 → 影响提示(BMI 重算)"""
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177)
    result = prof.update_profile_field("height", 180)
    assert result["old_value"] == 177.0
    assert result["new_value"] == 180.0
    assert "BMI" in result["impact"]
    assert prof.get_profile()["height_cm"] == 180.0


def test_update_profile_field_activity_impact(profile_env):
    """改档案:改活动量 → TDEE 系数变化提示"""
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177, activity_level="moderate")
    result = prof.update_profile_field("activity", "active")
    assert result["old_value"] == "moderate"
    assert result["new_value"] == "active"
    assert "1.55" in result["impact"] and "1.725" in result["impact"]


def test_update_profile_field_unknown(profile_env):
    """不支持的字段抛 InvalidFieldError"""
    prof = profile_env
    with pytest.raises(prof.InvalidFieldError):
        prof.update_profile_field("weight", 70)


def test_update_profile_field_age_string(profile_env):
    """改档案:CLI 层 age 传字符串('30')应自动转 int(对抗审查 #8 修复)"""
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177)
    result = prof.update_profile_field("age", "35")
    assert result["old_value"] == 30
    assert result["new_value"] == 35
    assert prof.get_profile()["age"] == 35
    with pytest.raises(prof.InvalidAgeError):
        prof.update_profile_field("age", "abc")


def test_live_profile_update_multi_field(profile_env):
    """改档案多字段:一次改多项,影响提示逐字段注入 __impact_ 键(对抗审查 #8 修复)"""
    import render_crud_receipt
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177, activity_level="moderate")
    data = render_crud_receipt.build_live_profile_update(
        [("height", "180"), ("activity", "active"), ("age", "35")])
    new_record = data["data"]["new_record"]
    # 3 字段全改 + 影响提示注入
    assert new_record["height_cm"] == 180.0
    assert new_record["activity_level"] == "active"
    assert new_record["age"] == 35
    assert "BMI" in new_record["__impact_height_cm"]
    assert "1.725" in new_record["__impact_activity_level"]
    # 无影响提示的字段不注入
    assert "__impact_note" not in new_record
    # 信息唯一性(2026-08-02):KPI 不再填(与 summary/diff 重复)
    assert data["data"]["context"]["kpis"] == []
    # 落库验证
    p = prof.get_profile()
    assert p["height_cm"] == 180.0 and p["activity_level"] == "active" and p["age"] == 35


def test_profile_receipt_summary(profile_env):
    """改档案回执:1 句话总结 + 中文标签 + TDEE 综合影响(用户拍板 2026-08-02)"""
    import render_crud_receipt
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177, activity_level="moderate")
    data = render_crud_receipt.build_live_profile_update(
        [("height", "180"), ("activity", "active")])
    # 1 句话总结
    assert "已修改 2 项" in data["data"]["summary"]
    assert "身高" in data["data"]["summary"]
    assert "活动量" in data["data"]["summary"]
    # 中文标签映射
    assert render_crud_receipt._label_for("height_cm") == "身高"
    assert render_crud_receipt._label_for("activity_level") == "活动量"
    assert render_crud_receipt._label_for("unknown_col") == "unknown_col"
    # 设置档案总结
    d2 = render_crud_receipt.build_live_profile_set(age=30, gender="male", height=177, activity="moderate")
    assert "档案已" in d2["data"]["summary"]


def test_chain_required_live_modes(profile_env, capsys):
    """思考链强制校验:live 模式不传/无效 → 报错退出(用户拍板 2026-08-02)"""
    import render_crud_receipt
    import render_crud_view
    # 无效链被拒
    assert render_crud_view._chain_valid("xxx") is False
    assert render_crud_view._chain_valid("") is False
    assert render_crud_view._chain_valid("1.识别→2.读DB→3.算TDEE") is True
    assert render_crud_view._chain_valid("第一步 解析用户意图") is True
    # 偷懒占位被拒
    assert render_crud_view._chain_valid("chain") is False
    assert render_crud_view._chain_valid("无") is False
    assert render_crud_receipt._chain_valid("1.解析→2.写库→3.回执") is True


def test_set_profile_with_activity(profile_env):
    """profile set --activity 透传"""
    prof = profile_env
    prof.set_profile(age=30, gender="male", height_cm=177, activity_level="light")
    assert prof.get_profile()["activity_level"] == "light"


def test_tdee_factors_map():
    """5 档系数映射(唯一来源)"""
    assert TDEE_ACTIVITY_FACTORS == {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }


def test_get_activity_factor_defaults():
    """缺省 / 未知回退 moderate(1.55)"""
    assert get_activity_factor(None) == 1.55
    assert get_activity_factor("ACTIVE") == 1.725  # 大小写不敏感
    assert get_activity_factor("unknown") == 1.55


def test_calc_tdee_uses_activity_level():
    """calc_tdee 用 activity_level 计算(同 BMR,系数不同 → TDEE 不同)"""
    bmr = 10 * 70 + 6.25 * 177 - 5 * 30 + 5
    tdee_moderate = calc_tdee(70, 177, 30, "male", "moderate")
    tdee_active = calc_tdee(70, 177, 30, "male", "active")
    assert tdee_moderate == round(bmr * 1.55)
    assert tdee_active == round(bmr * 1.725)
    assert tdee_active > tdee_moderate
