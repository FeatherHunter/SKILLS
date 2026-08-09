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
        # env 优先:无论是否已存在,都用 env 指定的路径
        # (修复:原版 "if exists 提前 return" 导致生产库存在时 env 失效)
        p = Path(env_path) / db_filename
        p.parent.mkdir(parents=True, exist_ok=True)
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

    # ── P0-1 补丁:建齐 5 张表 + items.category 放宽 nullable ──────
    # categories 表(总纲要求建表幂等;Phase 1 前装机需手跑 category_manager init)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE RESTRICT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name)")

    # accounts 表(原本靠 accounts.py lazy init,新机器直接崩)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL DEFAULT '',
            encrypted_password TEXT NOT NULL DEFAULT '',
            tags TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # ── T9 SM8 前置批:categories.seed_key(种子标识,分类兼容设计 G5)──
    # 老库零修改:seed_key 为空 → 代码层 fallback 名称查(三级解析器)
    migrate_add_seed_key_column(conn)

    # items.category 老字段:若仍 NOT NULL 则放宽(新 add_item 不写 category 字符串)
    cursor.execute("PRAGMA table_info(items)")
    items_cols_meta = {row[1]: row for row in cursor.fetchall()}
    if "category" in items_cols_meta and items_cols_meta["category"][3] == 1:
        # notnull=1 → 重建 items 表,category 改 nullable
        # 老 items 表可能还没 category_id 列(新装机),先补上避免 SELECT 失败
        if "category_id" not in items_cols_meta:
            cursor.execute("ALTER TABLE items ADD COLUMN category_id INTEGER REFERENCES categories(id)")
        # D1 #120:源表若已有 fixed_location(T3 ensure_schema 已加),重建必须保留,
        # 否则列与数据被重建补丁丢弃(对抗审查 2026-08-09 修复)
        has_fixed_location = "fixed_location" in items_cols_meta
        fixed_ddl = ", fixed_location TEXT" if has_fixed_location else ""
        fixed_io = ", fixed_location" if has_fixed_location else ""
        cursor.execute(f"""
            CREATE TABLE items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                owner TEXT DEFAULT '使用者',
                purchase_price REAL,
                remark TEXT,
                photo TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP,
                category_id INTEGER REFERENCES categories(id){fixed_ddl},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"""
            INSERT INTO items_new (id, name, category, owner, purchase_price, remark,
                photo, access_count, last_accessed_at, category_id{fixed_io}, created_at, updated_at)
            SELECT id, name, category, owner, purchase_price, remark,
                photo, access_count, last_accessed_at, category_id{fixed_io}, created_at, updated_at
            FROM items
        """)
        cursor.execute("DROP TABLE items")
        cursor.execute("ALTER TABLE items_new RENAME TO items")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category_id ON items(category_id)")

    migrate_add_date_columns(conn)
    migrate_add_category_id_column(conn)

    # ── D1 批:位置体系 + 固定位(D1 总账 #103 → #119/#120,SM2 实施载体收编)──
    # 注意:必须先于 items 重建补丁之后执行——category-notnull 补丁与
    # migrate_add_date_columns 会重建 items 表,若在此之前 ALTER 加列会被重建丢弃。
    migrate_add_location_nodes(conn)
    migrate_add_fixed_location_column(conn)

    conn.commit()
    conn.close()
    return True


def migrate_add_location_nodes(conn):
    """迁移:#119 location_nodes 位置体系表(树/规范化)+ 全量回填

    位置 = 自由层级(树),树结构隐含在路径字符串;节点只存规范化路径。
    回填语义:段 trim + 空段剔除 + 全角斜杠统一(与位置/schema.py normalize_path 一致)。
    来源:SM2 实施载体 scripts/位置/schema.py ensure_schema → 本批正式收编。
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 回填:从 item_locations.location 去重导入既有路径(全量,展示层过滤);
    # 规范化后再入库,避免全角斜杠/首尾空白造成重复节点(对抗审查 2026-08-09 收紧)
    rows = cursor.execute(
        "SELECT DISTINCT location FROM item_locations "
        "WHERE location IS NOT NULL AND trim(location) != ''"
    ).fetchall()
    seen = set()
    for (loc,) in rows:
        segs = [s.strip() for s in str(loc).replace("／", "/").split("/")]
        segs = [s for s in segs if s]
        if not segs:
            continue
        p = "/".join(segs)
        if p in seen:
            continue
        seen.add(p)
        cursor.execute("INSERT OR IGNORE INTO location_nodes (path) VALUES (?)", (p,))


def migrate_add_fixed_location_column(conn):
    """迁移:#120 items.fixed_location 固定位锚定路径(可空,规范化)

    固定位 = 物品一等属性,与「当前位置」分离;老数据零迁移(全新属性)。
    索引始终幂等创建:items 重建补丁可能保留列但丢掉索引(对抗审查 2026-08-09)。
    来源:SM2 实施载体 scripts/位置/schema.py ensure_schema → 本批正式收编。
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(items)")
    items_cols = {row[1] for row in cursor.fetchall()}
    if "fixed_location" not in items_cols:
        cursor.execute("ALTER TABLE items ADD COLUMN fixed_location TEXT")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_fixed_location ON items(fixed_location)"
    )


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
        # D1 #120:源表若已有 fixed_location(T3 ensure_schema 已加),重建必须保留,
        # 否则列与数据被重建补丁丢弃(对抗审查 2026-08-09 修复)
        has_fixed_location = "fixed_location" in items_columns
        fixed_ddl = ", fixed_location TEXT" if has_fixed_location else ""
        fixed_io = ", fixed_location" if has_fixed_location else ""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                owner TEXT DEFAULT '使用者',
                purchase_price REAL,
                remark TEXT,
                photo TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TIMESTAMP{fixed_ddl},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"""
            INSERT INTO items_new (id, name, category, owner, purchase_price, remark, photo, access_count, last_accessed_at{fixed_io}, created_at, updated_at)
            SELECT id, name, category, owner, purchase_price, remark, photo, access_count, last_accessed_at{fixed_io}, created_at, updated_at FROM items
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


def migrate_add_seed_key_column(conn):
    """迁移：给 categories 表加 seed_key 列(种子标识:food/clothing…)

    来源:分类兼容设计(seed_key+resolve 三级 fallback)· D1 拆批 seed_key 前置批(T9)
    - 新库:初始化建分类时写入 seed_key
    - 老库:列存在但为空 → 代码层按名称查(零修改)
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(categories)")
    columns = {row[1] for row in cursor.fetchall()}
    if "seed_key" not in columns:
        cursor.execute("ALTER TABLE categories ADD COLUMN seed_key TEXT")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_seed_key ON categories(seed_key)")


