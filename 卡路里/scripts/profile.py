#!/usr/bin/env python3
"""卡路里技能 - 用户档案管理(③ 业务层)

按 5 层架构定位:
- ③ 业务层:user_profile CRUD 封装
- 所有 SQL 走 db.connection()(④ 数据层)
- 单行表(CHECK id=1),get/set 不存在时返回 None / 初始化默认行
"""

import sys
from datetime import datetime
from pathlib import Path

import db as db_module


# ==================== 错误类 ====================

class ProfileError(Exception):
    """用户档案错误基类"""
    pass


class InvalidAgeError(ProfileError):
    """年龄无效"""
    pass


class InvalidGenderError(ProfileError):
    """性别无效"""
    pass


# ==================== 校验 ====================

VALID_GENDERS = ('male', 'female')


def _validate_age(age):
    """年龄 1-150"""
    if age is None:
        return None
    if not isinstance(age, int):
        raise InvalidAgeError(f"年龄必须是整数,当前类型: {type(age).__name__}")
    if age < 1 or age > 150:
        raise InvalidAgeError(f"年龄 {age} 不在有效范围 [1, 150]")
    return age


def _validate_gender(gender):
    """性别 male/female"""
    if gender is None:
        return None
    gender = gender.lower().strip()
    if gender not in VALID_GENDERS:
        raise InvalidGenderError(f"性别必须是 {VALID_GENDERS} 之一,当前: '{gender}'")
    return gender


# ==================== CRUD ====================

def _skill_dir():
    """技能根目录(scripts 的父级)"""
    return Path(__file__).parent.parent


def set_profile(age=None, gender=None, height_cm=None, note=None):
    """设置用户档案(单行表,upsert)

    Args:
        age: 年龄(1-150)
        gender: 'male' / 'female'
        height_cm: 身高(cm)
        note: 备注

    Returns:
        dict: 操作摘要 + 当前档案值
    """
    # 校验
    age = _validate_age(age)
    gender = _validate_gender(gender)
    if height_cm is not None and height_cm <= 0:
        raise ProfileError(f"身高必须 > 0,当前: {height_cm}")

    db_path = db_module.find_db_path(_skill_dir())
    now = datetime.now().isoformat(timespec='seconds')

    with db_module.connection(db_path) as conn:
        # 检查是否已有行
        existing = conn.execute('SELECT * FROM user_profile WHERE id = 1').fetchone()

        if existing:
            # UPDATE(只更新非 None 的字段)
            updates = []
            params = []
            if age is not None:
                updates.append('age = ?')
                params.append(age)
            if gender is not None:
                updates.append('gender = ?')
                params.append(gender)
            if height_cm is not None:
                updates.append('height_cm = ?')
                params.append(height_cm)
            if note is not None:
                updates.append('note = ?')
                params.append(note)

            if updates:
                updates.append('updated_at = ?')
                params.append(now)
                params.append(1)
                sql = f'UPDATE user_profile SET {", ".join(updates)} WHERE id = ?'
                conn.execute(sql, params)
        else:
            # INSERT
            conn.execute('''
                INSERT INTO user_profile (id, age, gender, height_cm, note, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            ''', (age, gender, height_cm, note, now, now))

    # 返回最新档案
    return get_profile()


def get_profile():
    """读取用户档案

    Returns:
        dict: 档案字段(可能字段为 None),不存在任何字段时返回空 dict
    """
    db_path = db_module.find_db_path(_skill_dir())

    with db_module.connection(db_path) as conn:
        row = conn.execute('SELECT * FROM user_profile WHERE id = 1').fetchone()

    if not row:
        return {}

    return {
        'age': row['age'],
        'gender': row['gender'],
        'height_cm': row['height_cm'],
        'note': row['note'] or '',
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def print_profile(profile=None):
    """打印用户档案(CLI 用)"""
    if profile is None:
        profile = get_profile()

    if not profile:
        print("(档案未设置)")
        print("  用 profile set 设置,例如:calorie_tracker profile set 30 male --height 175")
        return

    print(f"年龄:   {profile.get('age', '(未设)')}")
    print(f"性别:   {profile.get('gender', '(未设)')}")
    print(f"身高:   {profile.get('height_cm', '(未设)')} cm")
    if profile.get('note'):
        print(f"备注:   {profile['note']}")
    print(f"更新时间: {profile.get('updated_at', '(未知)')}")


# 2026-07-20 删:sync_height_from_weight_log() 函数已删除
# 身高 SoT = user_profile.height_cm,直接用 profile set 设
# 历史回滚:从 git 找 scripts/profile.py 2026-07-20 前的版本