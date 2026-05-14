#!/usr/bin/env python3
"""
私家大厨 - 数据库路径配置 v1.0
所有脚本共用此配置
"""

import os
import sqlite3
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "chef_data.db"


def _find_db_path():
    """四层查找DB路径：固定路径 > 环境变量 > 技能目录 > 父目录.db"""
    # 0. 固定路径：/mnt/d/2Study/StudyNotes/.db/（优先级最高）
    study_notes_db = Path('/mnt/d/2Study/StudyNotes/.db') / DB_FILENAME
    if study_notes_db.exists():
        return study_notes_db
    
    # 1. 环境变量
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / DB_FILENAME
        if p.exists():
            return p
    
    # 2. 技能目录
    p = SKILL_DIR / DB_FILENAME
    if p.exists():
        return p
    
    # 3. 父目录层层找 .db 文件夹
    for parent in SKILL_DIR.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / DB_FILENAME
            if p.exists():
                return p
    
    # 4. 都找不到则创建在固定路径
    study_notes_db.parent.mkdir(parents=True, exist_ok=True)
    return study_notes_db


DB_PATH = _find_db_path()


def get_conn():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn