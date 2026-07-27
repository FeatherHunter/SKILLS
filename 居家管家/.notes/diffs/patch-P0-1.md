# Patch P0-1: init_db 一次性建齐 5 张表 + items.category nullable

## 目标
- `init_db()` 自动建 categories / accounts 表(不再依赖手动跑 category_manager init)
- items.category 老字段从 `NOT NULL` 改为 nullable(因为新 add_item 不写它)

## 改动文件
- `scripts/home_manager/db.py` init_db()

## diff 草案(还没落盘,先看)

```python
# ── 追加到 init_db() 末尾,conn.commit() 之前 ─────────────
# 1. 建 categories 表(若不存在)
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

# 2. 建 accounts 表(若不存在)
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

# 3. items.category 老字段:若有老 DB 仍是 NOT NULL,放宽为 nullable
cursor.execute("PRAGMA table_info(items)")
items_cols = {row[1]: row for row in cursor.fetchall()}
if "category" in items_cols and items_cols["category"][3] == 1:
    # notnull=1 → 需要重建表(SQLite 不能直接 ALTER column 改 nullable)
    cursor.execute("""
        CREATE TABLE items_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,                -- 改 nullable
            owner TEXT DEFAULT '使用者',
            purchase_price REAL,
            remark TEXT,
            photo TEXT,
            access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP,
            category_id INTEGER REFERENCES categories(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT INTO items_new (id, name, category, owner, purchase_price, remark,
            photo, access_count, last_accessed_at, category_id, created_at, updated_at)
        SELECT id, name, category, owner, purchase_price, remark,
            photo, access_count, last_accessed_at, category_id, created_at, updated_at
        FROM items
    """)
    cursor.execute("DROP TABLE items")
    cursor.execute("ALTER TABLE items_new RENAME TO items")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category_id ON items(category_id)")
```

## 验证脚本(隔离 temp DB)
```bash
T=$(mktemp -d)
SKILLS_DB_PATH="$T" HOME_PHOTOS_DIR="$T/photos" python3 scripts/home_manager.py init
# 期望:5 张表都建了
python3 -c "import sqlite3,os;c=sqlite3.connect(os.path.join('$T','home.db'));print(c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall())"
# 期望:5 张表(category/accounts 也都在)
SKILLS_DB_PATH="$T" python3 -c "import sqlite3,os;c=sqlite3.connect(os.path.join('$T','home.db'));c.execute(\"INSERT INTO categories(name) VALUES('test')\");c.commit()"
# 期望:不报错
SKILLS_DB_PATH="$T" python3 -c "import sqlite3,os;c=sqlite3.connect(os.path.join('$T','home.db'));c.execute(\"INSERT INTO accounts(platform,encrypted_password,created_at,updated_at) VALUES('p','x','2026','2026')\");c.commit()"
# 期望:不报错
rm -rf "$T"
```

## 风险
- items 表重建:**仅在老 DB 中 items.category 仍 NOT NULL 时触发**。生产 DB items.category 已经没了(schema 漂移后),所以这个分支不会执行。
- 5 张表创建幂等(`IF NOT EXISTS`),重复 init 不报错。