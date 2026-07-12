# scripts/db_utils.py
"""
Learning System - 共享数据库工具
统一连接管理 + WAL 模式 + busy_timeout
所有 API 模块从此处导入，不再各自实现路径查找和连接管理
"""
import sqlite3
import os
import sys
from pathlib import Path
from contextlib import contextmanager

# ============================================
# 数据库路径查找
# ============================================
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "learning-system.db"


def _fallback_db_dir():
    """全局 fallback DB 目录：Windows → D:/.db，WSL → /mnt/d/.db"""
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    raise RuntimeError(
        'SKILLS_DB_PATH 未设置，且 D: 盘未挂载到 /mnt/d/。'
        '请检查 WSL automount 配置或设置 SKILLS_DB_PATH 环境变量。'
    )

def _find_db_path(skill_dir, db_filename):
    """两层查找DB路径：环境变量 SKILLS_DB_PATH > D:/.db"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
        return Path(env_path) / db_filename
    # 2. fallback: D:\.db\（WSL 自动转 /mnt/d/.db/）
    db_dir = _fallback_db_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / db_filename


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
