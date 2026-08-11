#!/usr/bin/env python3
"""分析模块共享工具

- BMR_ACTIVITY_FACTOR: 基础代谢活动系数
- _get_db: 数据库连接（调用方需 conn.close()）
- _parse_date: 日期字符串解析（支持 YYYYMMDD / YYYY-MM-DD）
- _days_between: 计算两个日期之间的天数差
"""

import sys
from datetime import datetime
from pathlib import Path

from db import find_db_path, get_db, init_db

# 确保 scripts/ 在 sys.path（兼容从不同目录调用）
_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

SKILL_DIR = Path(__file__).parent.parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)

BMR_ACTIVITY_FACTOR = 1.3  # 旧常量，兼容保留；新代码请用 TDEE_ACTIVITY_FACTORS / get_activity_factor()

# activity_level → TDEE 系数（2026-08-02 · ticket #8 · 唯一来源）
# Mifflin-St Jeor 活动系数表（Harris-Benedict 修订版）
TDEE_ACTIVITY_FACTORS = {
    'sedentary':    1.2,
    'light':        1.375,
    'moderate':     1.55,
    'active':       1.725,
    'very_active':  1.9,
}

ACTIVITY_LEVEL_LABELS = {
    'sedentary':    '久坐',
    'light':        '轻度活动',
    'moderate':     '中度活动',
    'active':       '活跃',
    'very_active':  '高度活跃',
}


def get_activity_factor(level=None):
    """根据 activity_level 返回 TDEE 系数，缺省/未知回退 moderate(1.55)

    Args:
        level: 'sedentary' / 'light' / 'moderate' / 'active' / 'very_active' / None
    """
    if not level:
        return TDEE_ACTIVITY_FACTORS['moderate']
    return TDEE_ACTIVITY_FACTORS.get(str(level).lower(), TDEE_ACTIVITY_FACTORS['moderate'])


def calc_tdee(weight_kg, height_cm, age, gender='male', activity_level=None):
    """Mifflin-St Jeor BMR × activity_factor（读取 user_profile.activity_level）

    TDEE = BMR × activity_factor（日常活动部分）
    当日运动消耗由 exercise_log 单独累加，不在此函数内。

    Args:
        weight_kg: 体重(kg)
        height_cm: 身高(cm)
        age: 年龄(岁)
        gender: 'male' / 'female'
        activity_level: 活动量档位（None 时读 user_profile，仍缺则默认 moderate）
    """
    if activity_level is None:
        activity_level = get_profile_activity_level()
    if not weight_kg or not height_cm:
        return 1800  # fallback

    if gender == 'male':
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    factor = get_activity_factor(activity_level)
    return round(bmr * factor)


def get_profile_activity_level():
    """读 user_profile.activity_level；无档案/异常回退 'moderate'"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import profile
        return profile.get_profile().get('activity_level') or 'moderate'
    except Exception:
        return 'moderate'


def _get_db():
    """获取数据库连接（调用方需 conn.close()）

    2026-08-11 #257 事故根治: 改为动态解析 find_db_path(不再用模块级 DB_PATH
    缓存)——模块级常量在 pytest collection 时固化为生产路径, 导致测试
    monkeypatch SKILLS_DB_PATH 后 analysis 仍读写生产库(曾清空 exercise_log 8297 行)。
    动态解析行为与旧逻辑一致(环境变量优先级不变), 但抗 monkeypatch。
    若 DB 不存在则先初始化。
    """
    from db import find_db_path, get_db, init_db
    from pathlib import Path as _P
    _skill = _P(__file__).resolve().parent.parent.parent
    db_path = find_db_path(_skill, DB_FILENAME)
    if not db_path.exists():
        init_db(db_path)
    return get_db(db_path)


def _parse_date(s):
    """解析日期字符串为 YYYY-MM-DD

    支持：
    - 'YYYY-MM-DD' → 原样返回
    - 'YYYYMMDD' → 转换为带分隔符格式
    - None → 返回 None
    """
    if s is None:
        return None
    s = str(s).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _days_between(d1, d2):
    """计算两个日期之间的天数差（d2 - d1）

    返回整数；解析失败返回 0。
    """
    try:
        return (datetime.strptime(d2, '%Y-%m-%d') - datetime.strptime(d1, '%Y-%m-%d')).days
    except Exception:
        return 0