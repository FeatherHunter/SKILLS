# scripts/db_utils.py
"""
Learning System - 共享数据库工具
统一连接管理 + WAL 模式 + busy_timeout
所有 API 模块从此处导入，不再各自实现路径查找和连接管理
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# ============================================
# 数据库路径查找
# ============================================
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "learning-system.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
        return Path(env_path) / db_filename

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
            return p

    # 4. 都找不到则创建在技能目录下的 .db
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(parents=True, exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


def get_connection():
    """获取数据库连接（带 WAL 和 busy_timeout）"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row

    # 启用 WAL 模式（并发安全）
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")  # 5秒等待
    conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全

    return conn


@contextmanager
def get_db():
    """上下文管理器，自动处理 commit/rollback/close"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
