# location_ops.py - 位置读写（location_status per-location）
from datetime import datetime
from .db import get_conn


def _expand_loc(conn, cat_id):
    """递归查所有下级 id(顶级/二级自动展开)"""
    cursor = conn.cursor()
    cursor.execute("""
        WITH RECURSIVE cat_tree AS (
            SELECT id FROM categories WHERE id = ?
            UNION ALL
            SELECT c.id FROM categories c JOIN cat_tree t ON c.parent_id = t.id
        )
        SELECT id FROM cat_tree
    """, (cat_id,))
    return [r['id'] for r in cursor.fetchall()]


def _category_in(conn, cat_id):
    """生成 (sql_clause, params) — 顶级/二级自动展开"""
    ids = _expand_loc(conn, cat_id)
    if len(ids) == 1:
        return "i.category_id = ?", [ids[0]]
    placeholders = ",".join("?" * len(ids))
    return f"i.category_id IN ({placeholders})", ids


def suggest_locations(conn, category, limit=10):
    """根据物品分类推荐位置（同类物品用过的位置，按使用次数排序）

    返回: [(location, count), ...]  按 count 降序

    用途：录物品时 AI 推荐"同类物品都放哪"
    注意：只推荐仍有物品存在的位置（JOIN 自然过滤已用完的位置）
    """
    cursor = conn.cursor()
    clause, c_params = _category_in(conn, category)
    cursor.execute(f"""
        SELECT il.location, COUNT(DISTINCT il.item_id) as cnt
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE {clause}
        GROUP BY il.location
        ORDER BY cnt DESC
        LIMIT ?
    """, (*c_params, limit))
    rows = cursor.fetchall()
    return [(row['location'], row['cnt']) for row in rows]


def suggest_locations_with_examples(conn, category, limit=10, examples_per_loc=2):
    """位置推荐 + 每个位置附带代表物品名（解决"记忆模糊"痛点）

    返回: [(location, count, [示例物品1, 示例物品2]), ...]  按 count 降序

    用途：用户看到位置时能立即看到具体物品，帮助记忆模糊时指认。
    示例物品按最近添加时间倒序（同一位置最新加入的优先）。
    """
    cursor = conn.cursor()
    # 先拿位置聚合（用 DISTINCT 避免一个物品同位置多条记录被重复计数）
    clause, c_params = _category_in(conn, category)
    cursor.execute(f"""
        SELECT il.location, COUNT(DISTINCT il.item_id) as cnt
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE {clause}
        GROUP BY il.location
        ORDER BY cnt DESC
        LIMIT ?
    """, (*c_params, limit))
    location_rows = cursor.fetchall()

    results = []
    for row in location_rows:
        loc = row['location']
        cnt = row['cnt']
        # 对每个位置，取最近添加的 N 件物品作为代表
        cursor.execute(f"""
            SELECT DISTINCT i.name
            FROM item_locations il
            JOIN items i ON i.id = il.item_id
            WHERE {clause} AND il.location = ?
            ORDER BY il.created_at DESC, il.id DESC
            LIMIT ?
        """, (*c_params, loc, examples_per_loc))
        examples = [r['name'] for r in cursor.fetchall()]
        results.append((loc, cnt, examples))
    return results


def find_location_by_reference(conn, reference_name, limit=5):
    """根据参考物品名找它的所有位置（解决"和XX放一起"痛点）

    参数:
        reference_name: 模糊匹配的物品名
        limit: 候选物品数量上限

    返回: [
        {
            'item_id': ID,
            'item_name': 名称,
            'category': 分类,
            'locations': [
                {'location': 路径, 'quantity': N, 'location_status': 状态}
            ]
        },
        ...
    ]

    用途：用户说"和那件黑卫衣放一起"时，AI 一键调用此函数定位。
    排序：名称精确匹配 > 名称前缀匹配 > 模糊匹配；
          同档内按 last_accessed_at 降序（最近访问的优先），从未访问的排最后。
    """
    cursor = conn.cursor()
    # 模糊搜索参考物品（用 CASE 排序，NULL last 用额外 CASE 兜底）
    cursor.execute("""
        SELECT i.id, i.name, c.name AS category
        FROM items i
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE i.name LIKE ?
        ORDER BY
            CASE WHEN i.name = ? THEN 0
                 WHEN i.name LIKE ? THEN 1
                 ELSE 2 END,
            CASE WHEN i.last_accessed_at IS NULL THEN 1 ELSE 0 END,
            i.last_accessed_at DESC,
            i.id DESC
        LIMIT ?
    """, (f"%{reference_name}%", reference_name, f"{reference_name}%", limit))
    items = cursor.fetchall()

    results = []
    for it in items:
        # 查该物品所有位置
        cursor.execute("""
            SELECT location, quantity, location_status
            FROM item_locations
            WHERE item_id = ?
            ORDER BY id
        """, (it['id'],))
        locs = [dict(r) for r in cursor.fetchall()]
        results.append({
            'item_id': it['id'],
            'item_name': it['name'],
            'category': it['category'],
            'locations': locs
        })
    return results


def get_locations(conn, item_id):
    """返回该物品所有位置，ORDER BY id"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, item_id, location, quantity, reason, location_status,
               purchase_date, expiration_date, created_at, updated_at
        FROM item_locations
        WHERE item_id = ?
        ORDER BY id
    """, (item_id,))
    from .models import ItemLocation
    return [ItemLocation.from_row(dict(row)) for row in cursor.fetchall()]


def add_location(conn, item_id, location, quantity=1, reason=None, location_status="在家",
                 purchase_date=None, expiration_date=None):
    """新增一个位置记录"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO item_locations
            (item_id, location, quantity, reason, location_status, purchase_date, expiration_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (item_id, location, quantity, reason, location_status, purchase_date, expiration_date, now, now))


def remove_location(conn, location_id):
    """删除一个位置记录"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM item_locations WHERE id = ?", (location_id,))


def update_location_quantity(conn, location_id, delta):
    """数量变化，支持负数（自动清理 quantity<=0 的记录）"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, quantity, location FROM item_locations WHERE id = ?",
        (location_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None, None
    new_qty = row["quantity"] + delta
    if new_qty <= 0:
        cursor.execute("DELETE FROM item_locations WHERE id = ?", (location_id,))
        return 0, row["location"]
    else:
        cursor.execute(
            "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
            (new_qty, now, location_id)
        )
        return new_qty, row["location"]


def update_location_status(conn, location_id, location_status):
    """更新指定位置的状态"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE item_locations SET location_status = ?, updated_at = ? WHERE id = ?",
        (location_status, now, location_id)
    )
    return cursor.rowcount > 0


def update_location_dates(conn, location_id, purchase_date=None, expiration_date=None):
    """更新指定位置的购买日期和过期日期"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    updates = ["updated_at = ?"]
    params = [now]

    if purchase_date is not None:
        updates.append("purchase_date = ?")
        params.append(purchase_date)
    if expiration_date is not None:
        updates.append("expiration_date = ?")
        params.append(expiration_date)

    params.append(location_id)
    cursor.execute(
        f"UPDATE item_locations SET {', '.join(updates)} WHERE id = ?",
        params
    )
    return cursor.rowcount > 0


def find_location_by_path(conn, item_id, location_path):
    """按路径精确查找该物品下的位置记录"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, location, quantity, reason, location_status, purchase_date, expiration_date
        FROM item_locations
        WHERE item_id = ? AND location = ?
    """, (item_id, location_path))
    row = cursor.fetchone()
    return dict(row) if row else None


def _locations_str(item_id):
    """获取物品所有位置的格式化字符串"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location, quantity, reason, location_status, purchase_date, expiration_date
        FROM item_locations
        WHERE item_id = ?
        ORDER BY id
    """, (item_id,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return "(未设置位置)"
    parts = []
    for r in rows:
        reason_str = f"({r['reason']})" if r['reason'] else ""
        date_str = ""
        if r['purchase_date'] or r['expiration_date']:
            pd = r['purchase_date'] or "-"
            ed = r['expiration_date'] or "-"
            date_str = f" {pd}~{ed}"
        parts.append(f"{r['location']} ×{r['quantity']}[{r['location_status']}]{reason_str}{date_str}")
    return " | ".join(parts)
