"""
私家大厨 - 数据库配置
所有manager脚本都导入此配置获取数据库路径

三层查找DB路径：环境变量 > 技能目录 > 父目录.db
"""

import os
import sqlite3
from pathlib import Path

# Database path - three-tier lookup
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "chef_data.db"

def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
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

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

def get_db_path():
    """获取数据库路径"""
    return DB_PATH

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn