# inventory_ops.py - 盘点与统计
from .db import get_conn
from .tag_ops import get_tags


def inventory(location):
    """盘点指定位置的所有物品"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT i.*, il.location as matched_location,
               il.quantity as matched_quantity, il.location_status
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        WHERE il.location LIKE ?
        ORDER BY i.category, i.name
    """, (f"%{location}%",))
    rows = cursor.fetchall()

    if not rows:
        print(f"位置 '{location}' 下没有物品")
        conn.close()
        return 0

    # 按物品聚合
    item_map = {}
    for row in rows:
        iid = row["id"]
        if iid not in item_map:
            item_map[iid] = {"item": row, "matched": []}
        item_map[iid]["matched"].append({
            "location": row["matched_location"],
            "quantity": row["matched_quantity"],
            "location_status": row["location_status"],
        })

    total_items = len(item_map)
    print(f"盘点「{location}」：共 {total_items} 件")
    print("-" * 80)
    for iid, data in item_map.items():
        row = data["item"]
        matched = data["matched"]
        parts = []
        for m in matched:
            parts.append(f"{m['location']} ×{m['quantity']}[{m['location_status']}]")
        locs_str = " | ".join(parts)
        tags_str = get_tags(conn, row["id"])
        print(f"ID:{row['id']} | {row['name']} | {row['category']} | "
              f"{locs_str} | {tags_str}")

    conn.close()
    return 0


def stats(stat_type="frequent", limit=20, days=30, expired_only=False, category=None):
    """频率统计 + 过期检查

    参数:
        stat_type: frequent / dormant / summary / expiring
        limit: 返回数量上限
        days: (expiring 用) 提前预警天数窗口，默认 30
        expired_only: (expiring 用) 只看已过期
        category: (expiring 用) 按分类筛选
    """
    conn = get_conn()
    cursor = conn.cursor()

    if stat_type == "frequent":
        cursor.execute("""
            SELECT * FROM items ORDER BY access_count DESC LIMIT ?
        """, (limit,))
        title = f"高频物品 TOP{limit}"
    elif stat_type == "dormant":
        cursor.execute("""
            SELECT * FROM items
            WHERE last_accessed_at IS NOT NULL
            ORDER BY last_accessed_at ASC LIMIT ?
        """, (limit,))
        title = f"长期未访问 TOP{limit}"
    elif stat_type == "expiring":
        return _stats_expiring(conn, limit, days, expired_only, category)
    elif stat_type == "summary":
        cursor.execute("SELECT COUNT(*) as total FROM items")
        total = cursor.fetchone()["total"]

        # 从 item_locations 实时统计各状态
        cursor.execute("""
            SELECT location_status, COUNT(DISTINCT item_id) as cnt
            FROM item_locations
            GROUP BY location_status
            ORDER BY cnt DESC
        """)
        status_counts = {row["location_status"]: row["cnt"] for row in cursor.fetchall()}

        all_statuses = ["在家", "备用", "穿着中", "旅游中", "洗护中",
                        "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"]
        total_in_items = sum(status_counts.values())

        print(f"总物品数：{total}")
        print(f"位置记录总数：{total_in_items}")
        print("-" * 40)
        print("各状态分布：")
        for s in all_statuses:
            cnt = status_counts.get(s, 0)
            bar = "█" * cnt
            print(f"  {s:　<4} {cnt:>3} {bar}")

        cursor.execute("""
            SELECT category, COUNT(*) as cnt FROM items
            GROUP BY category ORDER BY cnt DESC
        """)
        cats = cursor.fetchall()

        print("-" * 40)
        print("分类分布：")
        for c in cats:
            bar = "█" * c["cnt"]
            print(f"  {c['category']:　<6} {c['cnt']:>3} {bar}")
        conn.close()
        return 0
    else:
        print(f"未知统计类型: {stat_type}，可选: frequent / dormant / summary")
        conn.close()
        return 1

    rows = cursor.fetchall()
    if not rows:
        print("(无数据)")
    else:
        print(title)
        print("-" * 80)
        for row in rows:
            tags_str = get_tags(conn, row["id"])
            accessed = row["last_accessed_at"] or "从未"
            accessed_fmt = accessed[:16] if accessed != "从未" else accessed
            print(f"访问{row['access_count']}次 | 最后:{accessed_fmt} | "
                  f"ID:{row['id']} | {row['name']} | {row['category']} | "
                  f"{tags_str}")

    conn.close()
    return 0


def _stats_expiring(conn, limit, days=30, expired_only=False, category=None):
    """过期预警统计（心愿 ID: 1）

    按 expiration_date 升序排列，列出：
      - 红色标记已过期（剩余天数 < 0）
      - 黄色标记快过期（剩余天数 0~days）
    """
    cursor = conn.cursor()

    # 构造查询（参数化，防注入）
    conditions = [
        "il.expiration_date IS NOT NULL",
        "il.expiration_date != ''",
        "julianday(il.expiration_date) - julianday('now') <= ?"
    ]
    params = [days]

    if category:
        conditions.append("i.category = ?")
        params.append(category)

    if expired_only:
        # 只看已过期
        conditions.append("julianday(il.expiration_date) - julianday('now') < 0")
    else:
        # 包括已过期 + N 天内快过期
        # （条件已在上面加了 <= days）
        pass

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT i.id, i.name, i.category, il.location, il.quantity,
               il.location_status, il.expiration_date,
               CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) as days_left
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE {where_clause}
        ORDER BY days_left ASC
        LIMIT ?
    """
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    # 标题
    if expired_only:
        title = f"⛔ 已过期物品 TOP{limit}"
    else:
        title = f"⏰ 快过期物品（{days}天内） TOP{limit}"

    # 概要统计（先取全部，不受 limit 影响）
    summary_query = f"""
        SELECT
            COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) < 0 THEN 1 ELSE 0 END), 0) as expired_cnt,
            COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) BETWEEN 0 AND 3 THEN 1 ELSE 0 END), 0) as days_3,
            COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) BETWEEN 4 AND 7 THEN 1 ELSE 0 END), 0) as days_7,
            COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) BETWEEN 8 AND 30 THEN 1 ELSE 0 END), 0) as days_30
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE il.expiration_date IS NOT NULL AND il.expiration_date != ''
        {('AND i.category = ?' if category else '')}
    """
    summary_params = [category] if category else []
    cursor.execute(summary_query, summary_params)
    s = cursor.fetchone()

    print(title)
    print("-" * 70)
    print(f"  已过期：{s['expired_cnt']}  |  3天内：{s['days_3']}  |  7天内：{s['days_7']}  |  30天内：{s['days_30']}")
    print("-" * 70)

    if not rows:
        print("  (无数据)")
        conn.close()
        return 0

    for row in rows:
        days_left = row["days_left"]
        if days_left < 0:
            flag = f"❌已过期 {-days_left}天"
        elif days_left == 0:
            flag = "⏰今天到期"
        elif days_left <= 3:
            flag = f"⏰{days_left}天"
        elif days_left <= 7:
            flag = f"⏰{days_left}天"
        else:
            flag = f"📅{days_left}天"

        print(f"  {flag:<14} ID:{row['id']:<4} {row['name'][:30]:<30} ({row['category']})")
        print(f"     └ 📍 {row['location']} ×{row['quantity']}[{row['location_status']}]  到期:{row['expiration_date']}")

    conn.close()
    return 0
