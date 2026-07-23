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
    """物品总数应 ≥ 800, 异常低说明 DB 损坏或被错误清理"""
    count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    assert count > 800, f"物品数 {count} 异常低, 可能 DB 损坏"


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