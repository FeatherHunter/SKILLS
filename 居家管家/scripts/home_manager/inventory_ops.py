# inventory_ops.py - 盘点与统计
from .db import get_conn
from .tag_ops import get_tags


def _expand_inv(conn, cat_id):
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


def inventory(location):
    """盘点指定位置的所有物品"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT i.*, il.location as matched_location,
               il.quantity as matched_quantity, il.location_status,
               c.name AS category_name
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE il.location LIKE ?
        ORDER BY c.name, i.name
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
        print(f"ID:{row['id']} | {row['name']} | {row['category_name'] or '(未分类)'} | "
              f"{locs_str} | {tags_str}")

    conn.close()
    return 0


ALL_STATUSES = ["在家", "备用", "穿着中", "旅游中", "洗护中",
                "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"]


def inventory_payload(conn, location):
    """盘点指定位置,返回结构化数据供 inventory_check.html 使用

    返回结构:
      {
        "summary":   {title, subtitle, metrics[]},
        "location":  位置字符串,
        "statuses":  全部可选状态(供下拉框),
        "items":     [{id, name, category_name, matched_location,
                       matched_quantity, location_status, tags[]}, ...]
      }
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT i.id, i.name, c.name AS category_name,
               il.location as matched_location,
               il.quantity as matched_quantity,
               il.location_status
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE il.location LIKE ?
        ORDER BY c.name, i.name
    """, (f"%{location}%",))
    rows = cursor.fetchall()

    items = []
    for row in rows:
        tags = get_tags(conn, row['id'])
        items.append({
            "id": row['id'],
            "name": row['name'],
            "category_name": row['category_name'] or '(未分类)',
            "matched_location": row['matched_location'],
            "matched_quantity": row['matched_quantity'],
            "location_status": row['location_status'] or '在家',
            "tags": tags,
        })

    return {
        "summary": {
            "title": f"盘点 · {location}",
            "subtitle": "逐件确认状态；完成后点「复制回执」发给 AI",
            "metrics": [
                {"label": "物品数", "value": f"{len(items)} 件"},
                {"label": "位置", "value": location},
            ],
        },
        "location": location,
        "statuses": ALL_STATUSES,
        "items": items,
    }


def stats(stat_type="frequent", limit=20, days=30, expired_only=False, category_id=None):
    """频率统计 + 过期检查

    参数:
        stat_type: frequent / dormant / summary / expiring
        limit: 返回数量上限
        days: (expiring 用) 提前预警天数窗口，默认 30
        expired_only: (expiring 用) 只看已过期
        category: (expiring 用) 按分类筛选
    """
    conn = get_conn()
    try:
        cursor = conn.cursor()

        if stat_type == "frequent":
            cursor.execute("""
                SELECT i.*, c.name AS category_name
                FROM items i LEFT JOIN categories c ON i.category_id = c.id
                ORDER BY access_count DESC LIMIT ?
            """, (limit,))
            title = f"高频物品 TOP{limit}"
        elif stat_type == "dormant":
            cursor.execute("""
                SELECT i.*, c.name AS category_name
                FROM items i LEFT JOIN categories c ON i.category_id = c.id
                WHERE last_accessed_at IS NOT NULL
                ORDER BY last_accessed_at ASC LIMIT ?
            """, (limit,))
            title = f"长期未访问 TOP{limit}"
        elif stat_type == "expiring":
            return _stats_expiring(conn, limit, days, expired_only, category_id)
        elif stat_type == "summary":
            return _stats_summary(conn)
        else:
            print(f"未知统计类型: {stat_type}，可选: frequent / dormant / summary / expiring")
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
                      f"ID:{row['id']} | {row['name']} | {row['category_name'] or '(未分类)'} | "
                      f"{tags_str}")
        return 0
    finally:
        conn.close()


def _stats_expiring_query(conn, days=30, expired_only=False, category_id=None, limit=20):
    """过期预警共享查询 (DRY 单一权威源)

    返回:
      rows:       物品行 (含 days_left)
      thresholds: 桶分档列表 (例如 days=30 → [3, 7, 30])
    """
    cursor = conn.cursor()

    conditions = [
        "il.expiration_date IS NOT NULL",
        "il.expiration_date != ''",
        "julianday(il.expiration_date) - julianday('now') <= ?"
    ]
    params = [days]

    if category_id:
        ids = _expand_inv(conn, category_id)
        if len(ids) == 1:
            conditions.append("i.category_id = ?")
            params.append(ids[0])
        else:
            placeholders = ",".join("?" * len(ids))
            conditions.append(f"i.category_id IN ({placeholders})")
            params.extend(ids)

    if expired_only:
        conditions.append("date(il.expiration_date) < date('now')")

    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT i.id, i.name, c.name as category, il.location, il.quantity,
               il.location_status, il.expiration_date,
               CAST(julianday(date(il.expiration_date)) - julianday(date('now')) AS INTEGER) as days_left
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE {where_clause}
        ORDER BY days_left ASC
        LIMIT ?
    """
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    thresholds = [min(3, days)]
    if days >= 7:
        thresholds.append(7)
    if days > 7:
        thresholds.append(days)
    thresholds = sorted(set(thresholds))

    return rows, thresholds


def _stats_expiring(conn, limit, days=30, expired_only=False, category_id=None):
    """过期预警统计（心愿 ID: 1）

    按 expiration_date 升序排列，列出：
      - 红色标记已过期（剩余天数 < 0）
      - 黄色标记快过期（剩余天数 0~days）
    """
    cursor = conn.cursor()

    rows, thresholds = _stats_expiring_query(
        conn, days=days, expired_only=expired_only,
        category_id=category_id, limit=limit
    )

    # 标题
    if expired_only:
        title = f"⛔ 已过期物品 TOP{limit}"
    else:
        title = f"⏰ 快过期物品（{days}天内） TOP{limit}"

    # 概要统计（不受 limit 影响）
    case_clauses = [
        "COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) < 0 THEN 1 ELSE 0 END), 0) as expired_cnt"
    ]
    prev = 0
    for t in thresholds:
        if t == 3:
            case_clauses.append(
                f"COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) BETWEEN 0 AND 3 THEN 1 ELSE 0 END), 0) as days_3"
            )
        else:
            case_clauses.append(
                f"COALESCE(SUM(CASE WHEN CAST(julianday(il.expiration_date) - julianday('now') AS INTEGER) BETWEEN {prev+1} AND {t} THEN 1 ELSE 0 END), 0) as days_{t}"
            )
        prev = t

    summary_query = f"""
        SELECT
            {', '.join(case_clauses)}
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE il.expiration_date IS NOT NULL AND il.expiration_date != ''
        {('AND i.category_id IN (' + ','.join('?' * len(_expand_inv(conn, category_id))) + ')' if category_id else '')}
    """
    summary_params = _expand_inv(conn, category_id) if category_id else []
    cursor.execute(summary_query, summary_params)
    s = cursor.fetchone()

    # 动态拼接概要行
    summary_parts = [f"已过期：{s['expired_cnt']}"]
    for t in thresholds:
        if t == 3:
            summary_parts.append(f"3天内：{s['days_3']}")
        elif t == 7:
            summary_parts.append(f"7天内：{s['days_7']}")
        else:
            summary_parts.append(f"{t}天内：{s[f'days_{t}']}")

    print(title)
    print("-" * 70)
    print("  " + "  |  ".join(summary_parts))
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


def _trip_payload(conn, mode="pack"):
    """返回 travel_trip.html 需要的旅行清单数据

    mode='pack'   (出门前打包): 列出所有'在家'物品, 用户挑选打钩
    mode='return' (回家后归位): 列出所有'旅游中'物品, 用户标'已归位'

    返回结构:
      {
        "summary": {title, subtitle, metrics[]},
        "mode":    "pack" | "return",
        "items":   [{id, name, category_name, location, location_status, tags[]}, ...]
      }
    """
    cursor = conn.cursor()
    if mode == "pack":
        status = "在家"
        title = "出门打包清单"
        subtitle = "挑选要带的物品；完成后点「复制打包回执」发给 AI 标'旅游中'"
    elif mode == "return":
        status = "旅游中"
        title = "回家归位清单"
        subtitle = "标'已归位'或'换位置'；完成后点「复制归位回执」发给 AI 更新"
    else:
        return {
            "status": "error",
            "data": {},
            "message": f"未知 mode: {mode}，可选: pack | return"
        }

    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name,
                 id AS top_id, name AS top_name, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name,
                 cp.top_id, cp.top_name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT DISTINCT i.id, i.name, i.category_id, c.name AS category_name,
               cp.top_id AS top_category_id, cp.top_name AS top_category_name,
               il.location, il.location_status
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        JOIN cat_path cp ON cp.id = i.category_id
        WHERE il.location_status = ?
        ORDER BY c.name, i.name
    """, (status,))
    rows = cursor.fetchall()

    items = []
    for r in rows:
        tags = get_tags(conn, r['id'])
        items.append({
            "id": r['id'],
            "name": r['name'],
            "category_id": r['category_id'],
            "category_name": r['category_name'] or '(未分类)',
            "top_category_id": r['top_category_id'],
            "top_category_name": r['top_category_name'] or '(未分类)',
            "location": r['location'],
            "location_status": r['location_status'],
            "tags": tags,
        })

    # 顶级分类统计 (用于前端下拉过滤)
    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT cp_top.id, cp_top.name, COUNT(i.id) AS cnt
        FROM cat_path cp_top
        LEFT JOIN items i ON i.category_id IN (
          WITH RECURSIVE sub AS (
            SELECT id FROM categories WHERE id = cp_top.id
            UNION ALL
            SELECT c.id FROM categories c JOIN sub s ON c.parent_id = s.id
          )
          SELECT id FROM sub
        )
        WHERE cp_top.lvl = 1
        GROUP BY cp_top.id, cp_top.name
        HAVING cnt > 0
        ORDER BY cnt DESC
    """)
    categories = [
        {"id": r['id'], "name": r['name'], "count": r['cnt']}
        for r in cursor.fetchall()
    ]

    return {
        "summary": {
            "title": title,
            "subtitle": subtitle,
            "metrics": [
                {"label": "待处理", "value": f"{len(items)} 件"},
                {"label": "模式", "value": "出门打包" if mode == "pack" else "回家归位"},
            ],
        },
        "mode": mode,
        "categories": categories,
        "items": items,
    }


def _outfit_payload(conn, status_filter="在家"):
    """返回 outfit_picker.html 需要的衣物分类数据

    衣物分类结构(居家管家):
      138 衣物与穿戴 (顶级)
        144 上装 / 178 外套 (按"上装"组合)
        145 下装
      148 鞋类 (二级,直接是顶级域 148 的子)
      149 帽饰配件

    返回结构:
      {
        "summary": {title, subtitle, metrics[]},
        "groups": [
          {"key": "top",    "label": "上装",   "items": [...]},
          {"key": "bottom", "label": "下装",   "items": [...]},
          {"key": "shoes",  "label": "鞋帽",   "items": [...]},
        ]
      }
    """
    cursor = conn.cursor()

    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, name AS full_path, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name,
                 cp.full_path || '/' || c.name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT i.id, i.name, c.name AS category_name, c.id AS category_id,
               cp.lvl, cp.full_path
        FROM items i
        JOIN cat_path cp ON i.category_id = cp.id
        JOIN categories c ON c.id = cp.id
        WHERE cp.lvl >= 2
          AND (
            cp.full_path LIKE '衣物与穿戴/上装%'
            OR cp.full_path LIKE '衣物与穿戴/下装%'
            OR cp.full_path LIKE '衣物与穿戴/帽饰配件%'
            OR cp.full_path LIKE '鞋类/%'
          )
        ORDER BY cp.lvl, c.name, i.name
    """)
    rows = cursor.fetchall()

    def _fetch_items_for(items_meta):
        result = []
        for r in items_meta:
            cursor.execute("""
                SELECT location, quantity, location_status
                FROM item_locations WHERE item_id = ? ORDER BY updated_at DESC LIMIT 1
            """, (r['id'],))
            loc = cursor.fetchone()
            if loc and loc['location_status'] != status_filter:
                continue
            tags = get_tags(conn, r['id'])
            photo = None
            cursor.execute("SELECT photo FROM items WHERE id = ?", (r['id'],))
            prow = cursor.fetchone()
            photo_name = prow['photo'] if prow else None
            result.append({
                "id": r['id'],
                "name": r['name'],
                "category_name": r['category_name'],
                "full_path": r['full_path'],
                "tags": tags,
                "photo": photo_name,
                "location_status": loc['location_status'] if loc else status_filter,
            })
        return result

    top_items = [r for r in rows if r['full_path'].startswith('衣物与穿戴/上装')]
    bottom_items = [r for r in rows if r['full_path'].startswith('衣物与穿戴/下装')]
    shoes_items = [r for r in rows if r['full_path'].startswith('鞋类/')
                   or r['full_path'].startswith('衣物与穿戴/帽饰配件')]

    groups = [
        {"key": "top",    "label": "上装（含外套）", "items": _fetch_items_for(top_items)},
        {"key": "bottom", "label": "下装",           "items": _fetch_items_for(bottom_items)},
        {"key": "shoes",  "label": "鞋帽",           "items": _fetch_items_for(shoes_items)},
    ]

    total = sum(len(g['items']) for g in groups)
    return {
        "summary": {
            "title": "今天穿什么",
            "subtitle": "从上装/下装/鞋帽各选一件，标\"今天穿\"后 AI 更新状态为\"穿着中\"",
            "metrics": [
                {"label": "可选上装", "value": f"{len(groups[0]['items'])} 件"},
                {"label": "可选下装", "value": f"{len(groups[1]['items'])} 件"},
                {"label": "可选鞋帽", "value": f"{len(groups[2]['items'])} 件"},
                {"label": "总可选", "value": f"{total} 件"},
            ],
        },
        "groups": groups,
    }


def _stats_summary_payload(conn):
    """返回 list_overview.html 需要的结构化统计数据

    与 _stats_summary 镜像查询,但返回 dict 而非打印文本。
    返回结构:
      {
        "summary":   {"title": ..., "subtitle": ..., "metrics": [{label,value}, ...]},
        "categories": [{"name", "count", "total_value"}, ...],  # 仅顶级 L1
        "statuses":  [{"name", "count", "pct"}, ...],          # 按 count 降序
      }
    """
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS n FROM items")
    total = cursor.fetchone()['n']

    cursor.execute("""
        SELECT COUNT(*) AS priced_cnt, ROUND(SUM(purchase_price), 2) AS total_value
        FROM items WHERE purchase_price IS NOT NULL AND purchase_price > 0
    """)
    priced = cursor.fetchone()

    cursor.execute("""
        SELECT location_status, COUNT(DISTINCT item_id) AS cnt
        FROM item_locations GROUP BY location_status ORDER BY cnt DESC
    """)
    status_rows = cursor.fetchall()
    total_locations = sum(r['cnt'] for r in status_rows) or 1

    statuses = [
        {
            "name": r['location_status'] or '(未设置)',
            "count": r['cnt'],
            "pct": round(r['cnt'] * 100 / total_locations, 1),
        }
        for r in status_rows
    ]

    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT cp.id, cp.name,
               COUNT(i.id) AS cnt,
               ROUND(SUM(COALESCE(i.purchase_price, 0)), 2) AS total_value
        FROM cat_path cp
        LEFT JOIN items i ON i.category_id = cp.id
        WHERE cp.lvl = 1
        GROUP BY cp.id, cp.name
        HAVING cnt > 0
        ORDER BY cnt DESC
    """)
    cat_rows = cursor.fetchall()
    categories = [
        {"name": r['name'], "count": r['cnt'], "total_value": r['total_value'] or 0}
        for r in cat_rows
    ]

    return {
        "summary": {
            "title": "统物品概览",
            "subtitle": "居家管家统计概览",
            "metrics": [
                {"label": "物品总数", "value": f"{total} 件"},
                {"label": "有价物品", "value": f"{priced['priced_cnt']} 件"},
                {"label": "总价值", "value": f"¥{priced['total_value'] or 0:.2f}"},
            ],
        },
        "categories": categories,
        "statuses": statuses,
    }


def _stats_expiring_payload(conn, limit=50, days=30, expired_only=False, category_id=None):
    """返回 expiring_alert.html 需要的结构化过期预警数据

    返回结构:
      {
        "summary": {title, subtitle, metrics[{label,value,severity}]},
        "items":   [{id, name, category_name, location, quantity,
                     location_status, expiration_date, days_left, tags[]}, ...]
      }

    severity 字段: 'danger'(已过期) / 'warn'(≤7天) / 'info'(>7天)
    """
    rows, thresholds = _stats_expiring_query(
        conn, days=days, expired_only=expired_only,
        category_id=category_id, limit=limit
    )

    items = []
    for r in rows:
        days_left = r['days_left']
        if days_left < 0:
            severity = 'danger'
        elif days_left <= 7:
            severity = 'warn'
        else:
            severity = 'info'
        tags = get_tags(conn, r['id'])
        items.append({
            "id": r['id'],
            "name": r['name'],
            "category_name": r['category'] or '(未分类)',
            "location": r['location'],
            "quantity": r['quantity'],
            "location_status": r['location_status'] or '在家',
            "expiration_date": r['expiration_date'],
            "days_left": days_left,
            "severity": severity,
            "tags": tags,
        })

    expired = sum(1 for it in items if it['days_left'] < 0)
    in_3 = sum(1 for it in items if 0 <= it['days_left'] <= 3)
    in_7 = sum(1 for it in items if 0 <= it['days_left'] <= 7)
    in_days = sum(1 for it in items if it['days_left'] <= days)

    return {
        "summary": {
            "title": f"过期预警 · {days}天内",
            "subtitle": "按紧急度排序；标\"已处理\"后 AI 执行 update",
            "metrics": [
                {"label": "已过期", "value": f"{expired} 件", "severity": "danger"},
                {"label": "3天内", "value": f"{in_3} 件", "severity": "warn"},
                {"label": "7天内", "value": f"{in_7} 件", "severity": "warn"},
                {"label": f"{days}天内", "value": f"{in_days} 件", "severity": "info"},
            ],
        },
        "items": items,
    }


def _stats_summary(conn):
    """总体统计:总览 + 3 层分类树 + 总价值(items.purchase_price 累加)

    设计要点:
      - 用 WITH RECURSIVE 一次性拿全 categories 树 + 累计每节点物品数 / 总价值
      - l1_id / l2_id 在 SQL 里带下来,Python 累加用 ID 比较(避免名字前缀冲突)
      - 0 件的叶子分类(L3)不展示,符合 categories.md 原则#3:叶子 ≥ 3 件才独立
      - 0 件的顶级域(L1)也不展示,避免噪音
    """
    from collections import defaultdict
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS n FROM items")
    total = cursor.fetchone()['n']

    cursor.execute("SELECT COUNT(DISTINCT item_id) AS n FROM item_locations")
    total_in_items = cursor.fetchone()['n']

    cursor.execute("""
        SELECT location_status, COUNT(DISTINCT item_id) AS cnt
        FROM item_locations GROUP BY location_status ORDER BY cnt DESC
    """)
    status_counts = {r['location_status']: r['cnt'] for r in cursor.fetchall()}

    cursor.execute("""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, name AS full_path, 1 AS lvl,
                 id AS l1_id, 0 AS l2_id
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name,
                 cp.full_path || '/' || c.name, cp.lvl + 1,
                 CASE WHEN cp.lvl+1 = 1 THEN c.id ELSE cp.l1_id END,
                 CASE WHEN cp.lvl+1 = 2 THEN c.id
                      WHEN cp.lvl+1 = 3 THEN cp.id
                      ELSE 0 END
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT cp.lvl, cp.id, cp.name, cp.full_path, cp.l1_id, cp.l2_id,
               COUNT(i.id) AS cnt,
               ROUND(SUM(COALESCE(i.purchase_price, 0)), 2) AS total_value
        FROM cat_path cp
        LEFT JOIN items i ON i.category_id = cp.id
        GROUP BY cp.id, cp.lvl, cp.name, cp.full_path, cp.l1_id, cp.l2_id
    """)
    tree_rows = [dict(r) for r in cursor.fetchall()]

    by_lvl = defaultdict(list)
    for r in tree_rows:
        by_lvl[r['lvl']].append(r)

    # 累加:L3 → L2(用 l2_id 精确匹配)→ L1(用 l1_id 精确匹配)
    for r2 in list(by_lvl.get(2, [])):
        sub = [s for s in by_lvl.get(3, []) if s['l2_id'] == r2['id']]
        r2['cnt'] += sum(s['cnt'] for s in sub)
        r2['total_value'] += sum(s['total_value'] for s in sub)
    for r1 in list(by_lvl.get(1, [])):
        sub = [s for s in by_lvl.get(2, []) if s['l1_id'] == r1['id']]
        r1['cnt'] += sum(s['cnt'] for s in sub)
        r1['total_value'] += sum(s['total_value'] for s in sub)

    cursor.execute("""
        SELECT COUNT(*) AS priced_cnt, ROUND(SUM(purchase_price), 2) AS total_value
        FROM items WHERE purchase_price IS NOT NULL AND purchase_price > 0
    """)
    priced = cursor.fetchone()

    all_statuses = ["在家", "备用", "穿着中", "旅游中", "洗护中",
                    "借用中", "维修中", "已用完", "快递中", "待处理", "已废弃"]

    print(f"物品总数:{total} 件  |  有价物品:{priced['priced_cnt']} 件  |  总价值:¥{priced['total_value']:.2f}")
    print(f"位置记录总数:{total_in_items}")
    print("-" * 40)
    print("各状态分布:")
    for s in all_statuses:
        cnt = status_counts.get(s, 0)
        bar = "█" * min(cnt, 50)
        print(f"  {s:<4} {cnt:>4}  {bar}")
    print("-" * 40)
    print("分类分布(按 3 层树):")
    for r1 in sorted(by_lvl.get(1, []), key=lambda x: -x['cnt']):
        if r1['cnt'] == 0:
            continue
        val1 = f"¥{r1['total_value']:>9.2f}" if r1['total_value'] > 0 else f"{' ':>10}"
        print(f"  📁 {r1['name']:<8} {r1['cnt']:>4} 件  {val1}")
        l2_children = [s for s in by_lvl.get(2, []) if s['l1_id'] == r1['id']]
        for r2 in sorted(l2_children, key=lambda x: -x['cnt']):
            if r2['cnt'] == 0:
                continue
            val2 = f"¥{r2['total_value']:>9.2f}" if r2['total_value'] > 0 else f"{' ':>10}"
            print(f"     ├ {r2['name']:<8} {r2['cnt']:>4} 件  {val2}")
            l3_children = [s for s in by_lvl.get(3, []) if s['l2_id'] == r2['id']]
            for r3 in sorted(l3_children, key=lambda x: -x['cnt']):
                if r3['cnt'] == 0:
                    continue
                val3 = f"¥{r3['total_value']:>9.2f}" if r3['total_value'] > 0 else f"{' ':>10}"
                print(f"     │   └ {r3['name']:<8} {r3['cnt']:>4} 件  {val3}")
    return 0
