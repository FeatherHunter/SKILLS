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


class InvalidActivityLevelError(ProfileError):
    """活动量无效"""
    pass


class InvalidFieldError(ProfileError):
    """update_profile_field 字段不支持"""
    pass


# ==================== 校验 ====================

VALID_GENDERS = ('male', 'female')

# 活动量 5 档（英文字典值，中文 label 映射 · #19A 决策 2026-08-01）
VALID_ACTIVITY_LEVELS = ('sedentary', 'light', 'moderate', 'active', 'very_active')
ACTIVITY_LEVEL_LABELS = {
    'sedentary':    '久坐',
    'light':        '轻度活动',
    'moderate':     '中度活动',
    'active':       '活跃',
    'very_active':  '高度活跃',
}

# TDEE 系数（唯一来源 = analysis/_utils.py TDEE_ACTIVITY_FACTORS，此处 import 避免双源）
try:
    from analysis._utils import TDEE_ACTIVITY_FACTORS
except Exception:  # 独立运行时回退（不应发生）
    TDEE_ACTIVITY_FACTORS = {
        'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725, 'very_active': 1.9,
    }


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


def _validate_activity_level(level):
    """活动量 5 档（sedentary/light/moderate/active/very_active）"""
    if level is None:
        return None
    level = str(level).lower().strip()
    if level not in VALID_ACTIVITY_LEVELS:
        raise InvalidActivityLevelError(
            f"活动量必须是 {VALID_ACTIVITY_LEVELS} 之一,当前: '{level}'"
        )
    return level


def _validate_height(height_cm):
    """身高 > 0"""
    if height_cm is None:
        return None
    height_cm = float(height_cm)
    if height_cm <= 0:
        raise ProfileError(f"身高必须 > 0,当前: {height_cm}")
    return height_cm


# ==================== CRUD ====================

def _skill_dir():
    """技能根目录(scripts 的父级)"""
    return Path(__file__).parent.parent


def _db_path():
    """DB 路径 + 确保 schema 迁移已应用（init_db 幂等 · ticket #8）

    已有 DB 不会自动重跑 init_db，这里每次操作前确保
    user_profile.activity_level 列存在（2026-08-02 迁移）。
    """
    db_path = db_module.find_db_path(_skill_dir())
    db_module.init_db(db_path)
    return db_path


def set_profile(age=None, gender=None, height_cm=None, note=None, activity_level=None):
    """设置用户档案(单行表,upsert)

    Args:
        age: 年龄(1-150)
        gender: 'male' / 'female'
        height_cm: 身高(cm)
        note: 备注
        activity_level: 'sedentary' / 'light' / 'moderate' / 'active' / 'very_active'

    Returns:
        dict: 操作摘要 + 当前档案值
    """
    # 校验
    age = _validate_age(age)
    gender = _validate_gender(gender)
    height_cm = _validate_height(height_cm)
    activity_level = _validate_activity_level(activity_level)

    db_path = _db_path()
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
            if activity_level is not None:
                updates.append('activity_level = ?')
                params.append(activity_level)

            if updates:
                updates.append('updated_at = ?')
                params.append(now)
                params.append(1)
                sql = f'UPDATE user_profile SET {", ".join(updates)} WHERE id = ?'
                conn.execute(sql, params)
        else:
            # INSERT
            conn.execute('''
                INSERT INTO user_profile (id, age, gender, height_cm, note, activity_level, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ''', (age, gender, height_cm, note, activity_level, now, now))

    # 返回最新档案
    return get_profile()


def get_profile():
    """读取用户档案

    Returns:
        dict: 档案字段(可能字段为 None),不存在任何字段时返回空 dict
    """
    db_path = _db_path()

    with db_module.connection(db_path) as conn:
        row = conn.execute('SELECT * FROM user_profile WHERE id = 1').fetchone()

    if not row:
        return {}

    return {
        'age': row['age'],
        'gender': row['gender'],
        'height_cm': row['height_cm'],
        'note': row['note'] or '',
        'activity_level': row['activity_level'] or 'moderate',
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def set_activity_level(level):
    """只设置活动量(单字段 · 设活动量 场景)

    Args:
        level: 5 档之一(sedentary/light/moderate/active/very_active)

    Returns:
        dict: {activity_level, activity_label, activity_factor, old_level, tdee_estimate}
    """
    level = _validate_activity_level(level)
    if level is None:
        raise ProfileError("活动量不能为空")

    db_path = _db_path()
    now = datetime.now().isoformat(timespec='seconds')
    old = get_profile().get('activity_level') or 'moderate'

    with db_module.connection(db_path) as conn:
        existing = conn.execute('SELECT id FROM user_profile WHERE id = 1').fetchone()
        if existing:
            conn.execute(
                'UPDATE user_profile SET activity_level = ?, updated_at = ? WHERE id = 1',
                (level, now),
            )
        else:
            conn.execute('''
                INSERT INTO user_profile (id, activity_level, created_at, updated_at)
                VALUES (1, ?, ?, ?)
            ''', (level, now, now))

    return {
        'activity_level': level,
        'activity_label': ACTIVITY_LEVEL_LABELS[level],
        'activity_factor': TDEE_ACTIVITY_FACTORS[level],
        'old_level': old,
        'old_factor': TDEE_ACTIVITY_FACTORS.get(old, TDEE_ACTIVITY_FACTORS['moderate']),
        'updated_at': now,
    }


# update_profile_field 支持的字段映射: field → (列名, 校验器, 中文 label)
_PROFILE_FIELD_MAP = {
    'height':     ('height_cm', _validate_height, '身高'),
    'height_cm':  ('height_cm', _validate_height, '身高'),
    'age':        ('age', _validate_age, '年龄'),
    'gender':     ('gender', _validate_gender, '性别'),
    'activity':   ('activity_level', _validate_activity_level, '活动量'),
    'activity_level': ('activity_level', _validate_activity_level, '活动量'),
    'note':       ('note', None, '备注'),
}


def update_profile_field(field, value):
    """单字段更新 user_profile（改档案 场景 · #22C 决策）

    Args:
        field: 'height' / 'age' / 'gender' / 'activity' / 'note'
        value: 新值

    Returns:
        dict: {field, label, old_value, new_value, impact}
    """
    if field not in _PROFILE_FIELD_MAP:
        raise InvalidFieldError(
            f"不支持的字段: {field},支持 {sorted(set(_PROFILE_FIELD_MAP.keys()))}"
        )

    col, validator, label = _PROFILE_FIELD_MAP[field]
    if field == 'age' and not isinstance(value, int):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise InvalidAgeError(f"年龄必须是整数,当前: {value!r}")
    if validator:
        value = validator(value)
    if value is None:
        raise ProfileError(f"字段 {field} 的新值不能为空")

    db_path = _db_path()
    now = datetime.now().isoformat(timespec='seconds')
    old_profile = get_profile()

    with db_module.connection(db_path) as conn:
        existing = conn.execute('SELECT id FROM user_profile WHERE id = 1').fetchone()
        if existing:
            conn.execute(
                f'UPDATE user_profile SET {col} = ?, updated_at = ? WHERE id = 1',
                (value, now),
            )
        else:
            conn.execute(
                f'INSERT INTO user_profile (id, {col}, created_at, updated_at) VALUES (1, ?, ?, ?)',
                (value, now, now),
            )

    old_value = old_profile.get(col) if old_profile else None
    return {
        'field': field,
        'label': label,
        'old_value': old_value,
        'new_value': value,
        'impact': _compute_impact(field, old_value, value),
        'updated_at': now,
    }


def _compute_impact(field, old_value, new_value):
    """影响提示：改身高 → BMI 重算说明；改活动量 → TDEE 系数变化"""
    if field in ('activity', 'activity_level'):
        old_f = TDEE_ACTIVITY_FACTORS.get(str(old_value).lower(), TDEE_ACTIVITY_FACTORS['moderate'])
        new_f = TDEE_ACTIVITY_FACTORS.get(str(new_value).lower(), TDEE_ACTIVITY_FACTORS['moderate'])
        delta_pct = round((new_f - old_f) / old_f * 100, 1) if old_f else 0
        return (
            f"活动量 {ACTIVITY_LEVEL_LABELS.get(str(old_value), old_value)} → "
            f"{ACTIVITY_LEVEL_LABELS.get(str(new_value), new_value)},"
            f"TDEE 系数 {old_f} → {new_f}({delta_pct:+.1f}%)"
        )
    if field in ('height', 'height_cm'):
        return "身高已更新,BMI 将按新身高重算(体重记录时自动读档案)"
    if field == 'age':
        return "年龄已更新,BMR/TDEE 将按新年龄重算"
    if field == 'gender':
        return "性别已更新,BMR 公式将按新性别切换"
    if field == 'note':
        return "备注已更新"
    return ""


def print_profile(profile=None):
    """打印用户档案(CLI 用)"""
    if profile is None:
        profile = get_profile()

    if not profile:
        print("(档案未设置)")
        print("  用 profile set 设置,例如:calorie_tracker profile set 30 male --height 177")
        return

    print(f"年龄:   {profile.get('age', '(未设)')}")
    print(f"性别:   {profile.get('gender', '(未设)')}")
    print(f"身高:   {profile.get('height_cm', '(未设)')} cm")
    _al = profile.get('activity_level') or 'moderate'
    print(f"活动量: {ACTIVITY_LEVEL_LABELS.get(_al, _al)} ({_al} · 系数 {TDEE_ACTIVITY_FACTORS.get(_al, 1.55)})")
    if profile.get('note'):
        print(f"备注:   {profile['note']}")
    print(f"更新时间: {profile.get('updated_at', '(未知)')}")