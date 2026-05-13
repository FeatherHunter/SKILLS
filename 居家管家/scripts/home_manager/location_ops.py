# location_ops.py - 位置读写（location_status per-location）
from datetime import datetime
from .db import get_conn


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


def _record_location(conn, location_path):
    """记录位置到 locations 表（autocomplete 历史）"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO locations (location_path, use_count, last_used)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(location_path) DO UPDATE SET
            use_count = use_count + 1,
            last_used = CURRENT_TIMESTAMP
    """, (location_path,))
