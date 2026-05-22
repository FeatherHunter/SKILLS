"""
私家大厨 - 数据库配置
所有manager脚本都导入此配置获取数据库路径

三层查找DB路径：环境变量 > 技能目录 > 父目录.db

并发读写支持：
- WAL 模式：允许并发读和单个写
- 连接重试：数据库锁定时自动重试
- 上下文管理器：确保连接正确关闭
"""

import os
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager

# Database path - three-tier lookup
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "chef_data.db"

# 并发配置
MAX_RETRY_ATTEMPTS = 5  # 最大重试次数
RETRY_DELAY = 0.1  # 重试间隔（秒）
BUSY_TIMEOUT = 5000  # 忙等待超时（毫秒）

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

def _configure_connection(conn):
    """配置数据库连接，启用并发支持"""
    # 启用 WAL 模式（Write-Ahead Logging）
    # WAL 模式允许并发读和单个写，性能更好
    conn.execute("PRAGMA journal_mode=WAL")

    # 设置忙等待超时（毫秒）
    # 当数据库被锁定时，等待指定时间后重试
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT}")

    # 启用外键约束
    conn.execute("PRAGMA foreign_keys=ON")

    # 设置同步模式为 NORMAL（平衡性能和安全）
    conn.execute("PRAGMA synchronous=NORMAL")

    # 设置缓存大小（负数表示 KB）
    conn.execute("PRAGMA cache_size=-8000")  # 8MB 缓存

    return conn

def get_db_path():
    """获取数据库路径"""
    return DB_PATH

def get_connection():
    """获取数据库连接（带并发支持）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _configure_connection(conn)
    return conn

def get_connection_with_retry(max_retries=MAX_RETRY_ATTEMPTS, retry_delay=RETRY_DELAY):
    """获取数据库连接（带重试机制）

    当数据库被锁定时，自动重试指定次数。
    适用于高并发场景。
    """
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=BUSY_TIMEOUT/1000)
            conn.row_factory = sqlite3.Row
            _configure_connection(conn)
            # 测试连接是否可用
            conn.execute("SELECT 1")
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # 指数退避
                continue
            raise
    raise sqlite3.OperationalError("数据库锁定，重试次数已用完")

@contextmanager
def get_db_connection():
    """上下文管理器：自动管理数据库连接

    使用方式：
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
            conn.commit()

    特点：
    - 自动关闭连接
    - 异常时自动回滚
    - 带重试机制
    """
    conn = None
    try:
        conn = get_connection_with_retry()
        yield conn
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@contextmanager
def get_read_only_connection():
    """上下文管理器：只读连接（并发性能更好）

    使用方式：
        with get_read_only_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")

    特点：
    - 只读模式，不支持写操作
    - 并发性能更好
    - 自动关闭连接
    """
    conn = None
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        _configure_connection(conn)
        yield conn
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def ensure_wal_mode():
    """确保数据库使用 WAL 模式

    应在应用启动时调用一次。
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA journal_mode=WAL")
        result = conn.execute("PRAGMA journal_mode").fetchone()
        conn.close()
        return result[0] == "wal"
    except:
        return False

def get_db_stats():
    """获取数据库统计信息（用于调试）"""
    try:
        conn = get_connection()
        stats = {
            "db_path": str(DB_PATH),
            "db_size_mb": round(DB_PATH.stat().st_size / (1024 * 1024), 2) if DB_PATH.exists() else 0,
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
            "page_count": conn.execute("PRAGMA page_count").fetchone()[0],
            "page_size": conn.execute("PRAGMA page_size").fetchone()[0],
            "cache_size": conn.execute("PRAGMA cache_size").fetchone()[0],
            "busy_timeout": conn.execute("PRAGMA busy_timeout").fetchone()[0],
        }
        conn.close()
        return stats
    except Exception as e:
        return {"error": str(e)}

# 初始化：确保 WAL 模式
ensure_wal_mode()
