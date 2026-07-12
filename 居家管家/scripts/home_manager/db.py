# db.py - 数据库连接、建表、迁移
import sqlite3
import os
import sys
from pathlib import Path

# ── 配置 ─────────────────────────────────────────────────────────────────────

# 技能根目录：scripts/home_manager 的上两级目录
SKILL_DIR = Path(__file__).parent.parent.parent
DB_FILENAME = "home.db"


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
    env_path = os.environ.get("SKILLS_DB_PATH")
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # fallback: D:\.db\（WSL 自动转 /mnt/d/.db/）
    db_dir = _fallback_db_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


def _find_photos_dir(skill_dir):
    """三层查找照片目录：环境变量 > 父目录photos > 技能目录photos"""
    env_path = os.environ.get("HOME_PHOTOS_DIR")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return p
    for parent in skill_dir.parents:
        photos_dir = parent / "photos"
        if photos_dir.is_dir():
            return photos_dir
    return skill_dir / "photos"


PHOTOS_DIR = _find_photos_dir(SKILL_DIR)

# ── 连接 ──────────────────────────────────────────────────────────────────


def get_conn():
    """获取数据库连接（每次操作新建，不用连接池）"""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ── 建表 ──────────────────────────────────────────────────────────────────


def init_db():
    """初始化SQLite数据库（创建表和索引，幂等）"""
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            owner TEXT DEFAULT '使用者',
            purchase_price REAL,
            remark TEXT,
            photo TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            tag TEXT NOT NULL,
            UNIQUE(item_id, tag)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS item_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            reason TEXT,
            location_status TEXT DEFAULT '在家',
            purchase_date TEXT,
            expiration_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_item_id ON item_tags(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_tag ON item_tags(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_locations_item_id ON item_locations(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_locations_location ON item_locations(location)")
    migrate_add_date_columns(conn)
    migrate_add_category_id_column(conn)

    conn.commit()
    conn.close()
    return True


def migrate_add_date_columns(conn):
    """迁移：添加购买日期和过期日期字段到 item_locations 表，并从 items 表移除"""
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(item_locations)")
    columns = {row[1] for row in cursor.fetchall()}

    if "purchase_date" not in columns:
        cursor.execute("ALTER TABLE item_locations ADD COLUMN purchase_date TEXT")
    if "expiration_date" not in columns:
        cursor.execute("ALTER TABLE item_locations ADD COLUMN expiration_date TEXT")

    cursor.execute("PRAGMA table_info(items)")
    items_columns = {row[1] for row in cursor.fetchall()}

    if "purchase_date" in items_columns or "expiration_date" in items_columns:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                owner TEXT DEFAULT '使用者',
                purchase_price REAL,
                remark TEXT,
                photo TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO items_new (id, name, category, owner, purchase_price, remark, photo, access_count, last_accessed_at, created_at, updated_at)
            SELECT id, name, category, owner, purchase_price, remark, photo, access_count, last_accessed_at, created_at, updated_at FROM items
        """)
        cursor.execute("DROP TABLE items")
        cursor.execute("ALTER TABLE items_new RENAME TO items")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")


def migrate_add_category_id_column(conn):
    """迁移：给 items 表加 category_id 列(指向 categories.id),为新分类体系用

    老 category 字符串字段保留(向后兼容老 list/search 查询)
    新 add 命令必须传 --category-id,内部 derive category 字符串(写入老字段)
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(items)")
    columns = {row[1] for row in cursor.fetchall()}
    if "category_id" not in columns:
        cursor.execute("ALTER TABLE items ADD COLUMN category_id INTEGER REFERENCES categories(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category_id ON items(category_id)")


