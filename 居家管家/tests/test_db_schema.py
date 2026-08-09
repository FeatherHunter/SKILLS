"""数据库 schema 完整性测试

防 schema 破坏:
  - 删表 → 这里拦截
  - 删字段 → 这里拦截
  - 关外键 → 这里拦截
  - 误改导致数据重复 → 这里拦截
"""


def test_required_tables_exist(conn):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = {row[0] for row in cursor.fetchall()}
    required = {"items", "item_locations", "item_tags", "categories"}
    missing = required - tables
    assert not missing, f"缺失核心表: {missing}"


def test_items_has_required_columns(conn):
    cursor = conn.execute("PRAGMA table_info(items)")
    cols = {row[1] for row in cursor.fetchall()}
    required = {"id", "name", "category_id", "owner", "remark",
                "photo", "access_count", "created_at", "updated_at"}
    missing = required - cols
    assert not missing, f"items 表缺失字段: {missing}"


def test_item_locations_has_required_columns(conn):
    cursor = conn.execute("PRAGMA table_info(item_locations)")
    cols = {row[1] for row in cursor.fetchall()}
    required = {"id", "item_id", "location", "quantity", "location_status",
                "purchase_date", "expiration_date"}
    missing = required - cols
    assert not missing, f"item_locations 缺失字段: {missing}"


def test_item_tags_has_required_columns(conn):
    cursor = conn.execute("PRAGMA table_info(item_tags)")
    cols = {row[1] for row in cursor.fetchall()}
    required = {"id", "item_id", "tag"}
    missing = required - cols
    assert not missing, f"item_tags 缺失字段: {missing}"


def test_categories_has_required_columns(conn):
    cursor = conn.execute("PRAGMA table_info(categories)")
    cols = {row[1] for row in cursor.fetchall()}
    required = {"id", "name", "parent_id"}
    missing = required - cols
    assert not missing, f"categories 缺失字段: {missing}"


def test_foreign_keys_enabled(conn):
    """SQLite 外键默认关闭, 必须显式启用"""
    result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "外键未启用, item_locations.item_id 可能悬空"


def test_item_ids_are_unique(conn):
    """item.id 必须唯一, 重复说明 schema 损坏"""
    duplicates = conn.execute(
        "SELECT id, COUNT(*) FROM items GROUP BY id HAVING COUNT(*) > 1"
    ).fetchall()
    assert not duplicates, f"存在重复 item_id: {duplicates[:3]}"


def test_real_data_count_is_sane(conn):
    """items 表可写(issue #125: 不再断言生产库真实数据量, 隔离后为临时库)

    原断言 `count > 800` 依赖生产库真实数据, conftest conn 已改为临时库
    (issue #125 测试隔离), 该断言失义。改造为写-读-删的 schema 功能验证,
    保留「表可正常使用」的防破坏意图。
    """
    name = "TEST_SCHEMA_PROBE"
    cur = conn.execute("INSERT INTO items (name, category) VALUES (?, '测试')", (name,))
    iid = cur.lastrowid
    row = conn.execute("SELECT id, name FROM items WHERE id = ?", (iid,)).fetchone()
    assert row is not None and row["name"] == name, "items 表不可写, schema 异常"
    conn.execute("DELETE FROM items WHERE id = ?", (iid,))
    conn.commit()


def test_no_orphan_test_items(conn):
    """不应有 TEST_ 前缀残留 (应被 fixture 清理)"""
    orphans = conn.execute(
        "SELECT id, name FROM items WHERE name LIKE 'TEST\\_%' ESCAPE '\\'"
    ).fetchall()
    assert not orphans, f"TEST_ 残留: {orphans[:5]}"


def test_unique_constraint_on_item_tags(conn):
    """item_tags 表应有 UNIQUE(item_id, tag) 约束"""
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='item_tags'"
    ).fetchone()
    sql = schema[0] if schema else ""
    assert "UNIQUE" in sql.upper(), f"item_tags 缺 UNIQUE 约束: {sql}"


# ═══════════════════ D1 批 schema(#119/#120)═══ 2026-08-09 追加 ═══════════════════

def test_location_nodes_table_exists(conn):
    """D1 #119:location_nodes 位置体系表必须存在(防删表拦截)"""
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert "location_nodes" in tables, "缺失 location_nodes 位置体系表"


def test_location_nodes_path_unique(conn):
    """location_nodes.path 必须 UNIQUE(规范化路径去重语义)"""
    schema = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name='location_nodes'"
    ).fetchone()
    sql = schema[0] if schema else ""
    assert "UNIQUE" in sql.upper(), f"location_nodes 缺 UNIQUE(path): {sql}"


def test_items_has_fixed_location_column(conn):
    """D1 #120:items.fixed_location 固定位字段必须存在(防删字段拦截)"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(items)")}
    assert "fixed_location" in cols, "items 缺失 fixed_location 固定位字段"


def test_location_nodes_backfill_from_item_locations(tmp_path, monkeypatch):
    """回填:item_locations 既有路径去重导入 location_nodes(规范化 + 幂等)"""
    import importlib
    import home_manager.db as db_mod

    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    importlib.reload(db_mod)
    db_mod.init_db()
    conn = db_mod.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (1, NULL, '食物与饮品')")
    c.execute("INSERT INTO items (id, name, category_id) VALUES (1, '物品', 1)")
    # 全角斜杠 + 首尾空白 + 重复 → 应规范化去重为 2 节点
    c.execute("INSERT INTO item_locations (item_id, location) VALUES (1, '卧室／衣柜')")
    c.execute("INSERT INTO item_locations (item_id, location) VALUES (1, ' 客厅 /架子 ')")
    c.execute("INSERT INTO item_locations (item_id, location) VALUES (1, '卧室/衣柜')")
    conn.commit()

    db_mod.init_db()  # 再次 init 触发回填
    paths = {r[0] for r in c.execute("SELECT path FROM location_nodes")}
    conn.close()

    assert paths == {"卧室/衣柜", "客厅/架子"}, f"回填规范化/去重失败: {paths}"


def test_rebuild_preserves_fixed_location_category_patch(tmp_path, monkeypatch):
    """对抗审查回归:category-NOTNULL 重建路径必须保留 fixed_location 列与数据"""
    import importlib
    import sqlite3
    import home_manager.db as db_mod

    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    importlib.reload(db_mod)
    # 构造老库:category NOT NULL,已由 T3 ensure_schema 加 fixed_location 并有数据
    conn = sqlite3.connect(str(tmp_path / "home.db"))
    conn.execute("""CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
        owner TEXT DEFAULT '使用者', purchase_price REAL, remark TEXT, photo TEXT,
        access_count INTEGER DEFAULT 0, last_accessed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("INSERT INTO items (name, category) VALUES ('物品', '食物')")
    conn.execute("ALTER TABLE items ADD COLUMN fixed_location TEXT")
    conn.execute("UPDATE items SET fixed_location = '厨房/冰箱' WHERE id = 1")
    conn.commit()
    conn.close()

    db_mod.init_db()
    conn = sqlite3.connect(str(tmp_path / "home.db"))
    row = conn.execute("SELECT fixed_location FROM items WHERE id = 1").fetchone()
    conn.close()
    assert row is not None and row[0] == "厨房/冰箱", \
        f"category 重建路径丢 fixed_location 数据: {row}"


def test_rebuild_preserves_fixed_location_date_migration(tmp_path, monkeypatch):
    """对抗审查回归:日期列重建路径(migrate_add_date_columns)必须保留 fixed_location"""
    import importlib
    import sqlite3
    import home_manager.db as db_mod

    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    importlib.reload(db_mod)
    # 构造老库:category 已 nullable,items 仍有日期列(触发日期重建),fixed_location 已有数据
    conn = sqlite3.connect(str(tmp_path / "home.db"))
    conn.execute("""CREATE TABLE items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT,
        owner TEXT DEFAULT '使用者', purchase_price REAL, remark TEXT, photo TEXT,
        access_count INTEGER DEFAULT 0, last_accessed_at TIMESTAMP,
        purchase_date TEXT, expiration_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("INSERT INTO items (name, category, purchase_date) VALUES ('物品', '衣物', '2026-01-01')")
    conn.execute("ALTER TABLE items ADD COLUMN fixed_location TEXT")
    conn.execute("UPDATE items SET fixed_location = '卧室/衣柜' WHERE id = 1")
    conn.commit()
    conn.close()

    db_mod.init_db()
    conn = sqlite3.connect(str(tmp_path / "home.db"))
    row = conn.execute("SELECT fixed_location FROM items WHERE id = 1").fetchone()
    # 日期列应已迁出(重建发生),fixed_location 数据保留
    conn.close()
    assert row is not None and row[0] == "卧室/衣柜", \
        f"日期重建路径丢 fixed_location 数据: {row}"