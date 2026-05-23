#!/usr/bin/env python3
"""共享数据库工具 - 提供 DB 路径查找和连接"""

import os
import sqlite3
from pathlib import Path


def find_db_path(skill_dir, db_filename="calorie_data.db"):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db

    Args:
        skill_dir: 技能目录路径（通常为 Path(__file__).parent.parent）
        db_filename: 数据库文件名

    Returns:
        Path: 数据库文件路径
    """
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


def get_db(db_path):
    """获取数据库连接

    Args:
        db_path: 数据库文件路径（Path 对象）

    Returns:
        sqlite3.Connection: 数据库连接（row_factory=sqlite3.Row）
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
