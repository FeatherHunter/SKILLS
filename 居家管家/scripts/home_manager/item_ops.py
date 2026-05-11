# item_ops.py - 物品 CRUD 操作
from datetime import datetime
from .db import get_conn
from .location_ops import (
    get_locations, add_location, remove_location,
    update_location_quantity, update_location_status,
    find_location_by_path, _locations_str, _record_location
)
from .tag_ops import get_tags, set_tags


VALID_STATUSES = ("在家", "备用", "穿着中", "旅游中", "洗护中", "借用中",
                  "维修中", "已用完", "快递中", "待处理", "已废弃")


# ── 辅助 ──────────────────────────────────────────────────────────────────


def _touch_item(conn, item_id):
    """更新物品访问计数"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items SET access_count = access_count + 1,
        last_accessed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (item_id,))


def _format_item(row, tags_str=None, locations_str=None):
    """格式化单个物品为文本"""
    tags = tags_str if tags_str is not None else ""
    price = f"¥{row['purchase_price']:.2f}" if row["purchase_price"] else ""
    photo = "[图]" if row["photo"] else ""
    locs = locations_str if locations_str is not None else "(未设置位置)"
    return (
        f"ID:{row['id']} | {row['name']} | {row['category']} | "
        f"{locs} | {row['status'] or ''} | {price} | {tags} | {row['remark'] or ''} {photo}"
    ).strip()


# ── add ─────────────────────────────────────────────────────────────────────


def add_item(name, category, primary_location, owner="使用者", status="在家",
             primary_quantity=1, purchase_price=None, purchase_date=None, expiration_date=None,
             remark="", tags="", photo="",
             extra_location=None, extra_quantity=None, extra_reason=None,
             primary_location_status=None, extra_location_status=None):
    """添加新物品（per-location status）"""
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # status 参数现在是主位置的 location_status（向后兼容）
    primary_loc_status = primary_location_status if primary_location_status else (status or "在家")

    cursor.execute("""
        INSERT INTO items (name, category, owner, status,
                          purchase_price, purchase_date, expiration_date, remark, photo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, owner, status,
          purchase_price, purchase_date, expiration_date, remark, photo, now, now))

    item_id = cursor.lastrowid

    # 主位置
    add_location(conn, item_id, primary_location, primary_quantity,
                reason=None, location_status=primary_loc_status)
    # 额外位置
    if extra_location:
        extra_loc_status = extra_location_status if extra_location_status else primary_loc_status
        add_location(conn, item_id, extra_location, extra_quantity or 1,
                    extra_reason, location_status=extra_loc_status)

    set_tags(conn, item_id, tags)
    _record_location(conn, primary_location)
    if extra_location:
        _record_location(conn, extra_location)
    conn.commit()

    tags_display = get_tags(conn, item_id)
    item = dict(cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())
    locations_str = _locations_str(item_id)
    conn.close()

    print(f"✓ 物品已添加 (ID:{item_id})")
    print(_format_item(item, tags_display, locations_str))
    return 0


# ── search ──────────────────────────────────────────────────────────────────


def search_items(name=None, category=None, location=None, tag=None, status=None,
                limit=20, exact=False):
    """搜索物品（支持多条件组合，per-location status 搜索）"""
    conn = get_conn()
    cursor = conn.cursor()

    query = "SELECT DISTINCT i.* FROM items i"
    params = []

    join_item_locations = tag or location or status
    if join_item_locations:
        query += " LEFT JOIN item_locations il ON i.id = il.item_id"
    if tag:
        query += " LEFT JOIN item_tags t ON i.id = t.item_id"

    conditions = []
    if name:
        if exact:
            conditions.append("i.name = ?")
            params.append(name)
        else:
            conditions.append("i.name LIKE ?")
            params.append(f"%{name}%")
    if category:
        conditions.append("i.category = ?")
        params.append(category)
    if location:
        conditions.append("(il.location LIKE ? OR il.location IS NULL)")
        params.append(f"%{location}%")
    if status:
        # 搜索位置状态：任意一个位置的 location_status 匹配即命中
        conditions.append("(il.location_status = ? OR il.location_status = ?)")
        params.append(status)
        params.append(status)
    if tag:
        conditions.append("t.tag = ?")
        params.append(tag)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY i.access_count DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("(未找到匹配物品)")
    else:
        print(f"找到 {len(rows)} 件物品：")
        print("-" * 80)
        for row in rows:
            tags_str = get_tags(conn, row["id"])
            locations_str = _locations_str(row["id"])
            print(_format_item(row, tags_str, locations_str))

    conn.close()
    return 0


# ── update ───────────────────────────────────────────────────────────────


def update_item(item_id, name=None, category=None, owner=None, status=None,
               remark=None, tags=None, purchase_price=None, purchase_date=None,
               expiration_date=None, photo=None,
               primary_location=None, primary_quantity=None,
               extra_location=None, extra_quantity=None, extra_reason=None,
               extra_delta=None,
               location=None, location_status=None):
    """更新物品字段（per-location status）"""
    conn = get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    old = dict(row)

    # 1. 更新 items 表字段（不含 status）
    updates = []
    params_list = []

    if name is not None:
        updates.append("name = ?")
        params_list.append(name)
    if category is not None:
        updates.append("category = ?")
        params_list.append(category)
    if owner is not None:
        updates.append("owner = ?")
        params_list.append(owner)
    if remark is not None:
        updates.append("remark = ?")
        params_list.append(remark)
    if purchase_price is not None:
        updates.append("purchase_price = ?")
        params_list.append(purchase_price)
    if purchase_date is not None:
        updates.append("purchase_date = ?")
        params_list.append(purchase_date)
    if expiration_date is not None:
        updates.append("expiration_date = ?")
        params_list.append(expiration_date)
    if photo is not None:
        updates.append("photo = ?")
        params_list.append(photo)

    # items.status 不再写入（保留字段但废弃）
    # status 参数暂时兼容（忽略），提示用户使用 --location-status

    if updates:
        updates.append("updated_at = ?")
        params_list.append(now)
        params_list.append(item_id)
        sql = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params_list)

    # 2. 处理 extra_delta 数量变更（指定位置）
    if extra_delta is not None and extra_location:
        loc = find_location_by_path(conn, item_id, extra_location)
        if loc:
            new_qty = loc["quantity"] + extra_delta
            if new_qty <= 0:
                remove_location(conn, loc["id"])
                print(f"✓ 位置「{extra_location}」物品已耗尽，删除该位置记录")
            else:
                cursor.execute("""
                    UPDATE item_locations
                    SET quantity = ?, updated_at = ?
                    WHERE id = ?
                """, (new_qty, now, loc["id"]))
                print(f"✓ 位置「{extra_location}」数量更新为 {new_qty}")

    # 3. 处理 primary_location 变更（位置路径变化时）
    if primary_location is not None:
        cursor.execute("""
            SELECT id FROM item_locations
            WHERE item_id = ? AND location = ?
        """, (item_id, primary_location))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE item_locations
                SET location = ?, quantity = ?, updated_at = ?
                WHERE id = ?
            """, (primary_location, primary_quantity or 1, now, existing["id"]))
        else:
            # 找不到原主位置就新增
            add_location(conn, item_id, primary_location, primary_quantity or 1,
                        reason=None, location_status=primary_location_status or "在家")
        _record_location(conn, primary_location)

    # 4. 处理新增/更新 extra_location（非数量变更）
    if extra_location and extra_delta is None:
        loc = find_location_by_path(conn, item_id, extra_location)
        if loc:
            if extra_quantity is not None:
                cursor.execute("""
                    UPDATE item_locations
                    SET quantity = ?, reason = ?, updated_at = ?
                    WHERE id = ?
                """, (extra_quantity, extra_reason, now, loc["id"]))
        else:
            add_location(conn, item_id, extra_location, extra_quantity or 1,
                        extra_reason, location_status=extra_location_status or "在家")
        _record_location(conn, extra_location)

    # 5. 更新指定位置的 location_status（核心新功能）
    if location is not None and location_status is not None:
        if location_status not in VALID_STATUSES:
            print(f"✗ 无效状态: {location_status}，有效值: {', '.join(VALID_STATUSES)}")
            conn.close()
            return 1
        loc = find_location_by_path(conn, item_id, location)
        if not loc:
            print(f"✗ 未找到该位置「{location}」，请检查路径是否正确")
            conn.close()
            return 1
        update_location_status(conn, loc["id"], location_status)
        print(f"✓ 位置「{location}」状态已更新为「{location_status}」")

    # 5b. 警告：旧 --status 参数（无 --location）
    if status is not None and location is None and location_status is None:
        print(f"⚠️  提示：「--status {status}」已废除，请改用「--location <位置路径> --location-status {status}\」")
        print(f"   或直接用「--location-status {status}」配合「--location <位置路径>」")

    # 6. 标签变更
    old_tags = get_tags(conn, item_id)
    if tags is not None:
        set_tags(conn, item_id, tags)

    # 7. 访问计数+1
    _touch_item(conn, item_id)

    conn.commit()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    new_row = dict(cursor.fetchone())
    tags_str = get_tags(conn, item_id)
    locations_str = _locations_str(item_id)

    changes = []
    if name and name != old["name"]:
        changes.append(f"名称: {old['name']} → {name}")

    print(f"✓ 已更新 ID:{item_id} ({old['name']})")
    if changes:
        print(" | ".join(changes))
    print(_format_item(new_row, tags_str, locations_str))

    conn.close()
    return 0


# ── list ───────────────────────────────────────────────────────────────────


def list_items(location=None, status=None, category=None, owner=None,
              sort_by="name", limit=100):
    """按条件列出物品"""
    conn = get_conn()
    cursor = conn.cursor()

    conditions = []
    params = []

    if location:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM item_locations il
                WHERE il.item_id = items.id AND il.location LIKE ?
            )
        """)
        params.append(f"%{location}%")
    if status:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM item_locations il
                WHERE il.item_id = items.id AND il.location_status = ?
            )
        """)
        params.append(status)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if owner:
        conditions.append("owner = ?")
        params.append(owner)

    sort_map = {
        "name": "name ASC",
        "recent": "last_accessed_at DESC",
        "frequent": "access_count DESC",
        "updated": "updated_at DESC",
        "dormant": "last_accessed_at ASC",
    }
    order = sort_map.get(sort_by, "name ASC")

    query = "SELECT * FROM items"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += f" ORDER BY {order} LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("(无匹配物品)")
    else:
        print(f"共 {len(rows)} 件：")
        print("-" * 80)
        for row in rows:
            tags_str = get_tags(conn, row["id"])
            locations_str = _locations_str(row["id"])
            print(_format_item(row, tags_str, locations_str))

    conn.close()
    return 0


# ── detail ────────────────────────────────────────────────────────────────


def item_detail(item_id):
    """查看物品详细信息（per-location status）"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    item = dict(row)
    tags_str = get_tags(conn, item_id)

    cursor.execute("""
        SELECT location, quantity, reason, location_status
        FROM item_locations
        WHERE item_id = ?
        ORDER BY id
    """, (item_id,))
    locations = cursor.fetchall()

    print(f"===== 物品详情 =====")
    print(f"ID:       {item['id']}")
    print(f"名称:     {item['name']}")
    print(f"分类:     {item['category']}")

    if locations:
        print("位置分布：")
        for loc in locations:
            reason_str = f" - {loc['reason']}" if loc["reason"] else ""
            print(f"  {loc['location']} × {loc['quantity']} [{loc['location_status']}]{reason_str}")
    else:
        print("位置:     (未设置)")

    print(f"所有者:   {item['owner']}")
    print(f"状态:     {item['status'] or '(已废除，运行时推导)'}")
    total_qty = sum(loc["quantity"] for loc in locations)
    print(f"总数量:   {total_qty}")
    if item["purchase_price"]:
        print(f"购买价:   ¥{item['purchase_price']:.2f}")
    print(f"标签:     {tags_str or '(无)'}")
    print(f"备注:     {item['remark'] or '(无)'}")
    print(f"图片:     {item['photo'] or '(无)'}")
    print(f"访问次数: {item['access_count']}")
    print(f"最后访问: {item['last_accessed_at'] or '从未'}")
    print(f"创建时间: {item['created_at']}")
    print(f"更新时间: {item['updated_at']}")

    _touch_item(conn, item_id)
    conn.commit()
    conn.close()
    return 0
