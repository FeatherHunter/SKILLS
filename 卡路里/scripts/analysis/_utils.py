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

BMR_ACTIVITY_FACTOR = 1.3


def _get_db():
    """获取数据库连接（调用方需 conn.close()）

    若 DB 不存在则先初始化。
    """
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


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