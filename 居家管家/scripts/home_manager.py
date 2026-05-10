#!/usr/bin/env python3
"""
居家管家 - 家庭物品管理系统 v1.0
- SQLite 数据库存储（4张表：items / item_tags / locations / item_locations）
- 纯文本输出，供 AI 解析后展示给用户
- 数据库路径：技能根目录 home.db
- 图片路径：技能根目录 photos/
"""

import sqlite3
import os
import sys
from datetime import datetime, date
from pathlib import Path

# 强制 UTF-8 输出（修复 Windows GBK 编码问题）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ── 配置 ─────────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "home.db"  # 可在子类中覆盖

def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
PHOTOS_DIR = SKILL_DIR / "photos"

# ── 状态常量 ──────────────────────────────────────────────────────────────────

VALID_STATUSES = ("在家", "备用", "穿着中", "旅游中", "洗护中", "借用中",
                  "维修中", "已用完", "快递中", "待处理", "已废弃")

# ── 数据库初始化 ─────────────────────────────────────────────────────────────

def init_db():
    """初始化SQLite数据库（创建表和索引）"""
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            owner TEXT DEFAULT '使用者',
            status TEXT DEFAULT '在家',
            purchase_price REAL,
            purchase_date TEXT,
            expiration_date TEXT,
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
            is_primary INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
    # idx_items_location removed - items.location column removed in v2.0
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_item_id ON item_tags(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_tag ON item_tags(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_locations_item_id ON item_locations(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_locations_location ON item_locations(location)")
    cursor.execute("CREATE TABLE IF NOT EXISTS locations (id INTEGER PRIMARY KEY AUTOINCREMENT, location_path TEXT UNIQUE NOT NULL, use_count INTEGER DEFAULT 1, last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_path ON locations(location_path)")

    conn.commit()
    conn.close()
    return True

# ── 辅助函数 ─────────────────────────────────────────────────────────────────

def _get_conn():
    """获取数据库连接（自动初始化）"""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def _record_location(conn, location_path):
    """记录/更新位置到 locations 表"""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO locations (location_path, use_count, last_used)
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(location_path) DO UPDATE SET
            use_count = use_count + 1,
            last_used = CURRENT_TIMESTAMP
    """, (location_path,))

def _touch_item(conn, item_id):
    """更新物品访问计数"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items SET access_count = access_count + 1,
        last_accessed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (item_id,))

def _get_tags(conn, item_id):
    """获取物品的所有标签（逗号分隔）"""
    cursor = conn.cursor()
    cursor.execute("SELECT tag FROM item_tags WHERE item_id = ? ORDER BY tag", (item_id,))
    return ",".join(row["tag"] for row in cursor.fetchall())

def _set_tags(conn, item_id, tags_str):
    """设置物品标签（先删后插）"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
    if tags_str:
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for tag in tags:
            cursor.execute("INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
                           (item_id, tag))

def _format_item(row, tags_str=None, locations_str=None):
    """格式化单个物品为文本（v2.0多位置）"""
    tags = tags_str if tags_str is not None else ""
    price = f"¥{row['purchase_price']:.2f}" if row["purchase_price"] else ""
    photo = "[图]" if row["photo"] else ""
    locs = locations_str if locations_str is not None else "(未设置位置)"
    return (
        f"ID:{row['id']} | {row['name']} | {row['category']} | "
        f"{locs} | {row['status']} | {price} | {tags} | {row['remark'] or ''} {photo}"
    ).strip()

def _get_locations_str(conn, item_id):
    """获取物品的所有位置和数量，格式：主位置×数量（额外×数量）"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location, quantity, reason, is_primary 
        FROM item_locations 
        WHERE item_id = ? 
        ORDER BY is_primary DESC, id
    """, (item_id,))
    rows = cursor.fetchall()
    if not rows:
        return "(未设置位置)"
    
    parts = []
    for r in rows:
        reason_str = f"({r['reason']})" if r['reason'] else ""
        if r['is_primary']:
            parts.append(f"{r['location']} ×{r['quantity']}{reason_str}")
        else:
            parts.append(f"额外:{r['location']} ×{r['quantity']}{reason_str}")
    return " | ".join(parts)

# ── 添加物品 ─────────────────────────────────────────────────────────────────

def add_item(name, category, primary_location, owner="使用者", status="在家",
             primary_quantity=1, purchase_price=None, purchase_date=None, expiration_date=None,
             remark="", tags="", photo="",
             extra_location=None, extra_quantity=None, extra_reason=None):
    """添加新物品（v2.0多位置支持）"""
    conn = _get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO items (name, category, owner, status,
                          purchase_price, purchase_date, expiration_date, remark, photo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, owner, status,
          purchase_price, purchase_date, expiration_date, remark, photo, now, now))

    item_id = cursor.lastrowid

    # 写入主位置（无原因）
    cursor.execute("""
        INSERT INTO item_locations (item_id, location, quantity, reason, is_primary, created_at, updated_at)
        VALUES (?, ?, ?, NULL, 1, ?, ?)
    """, (item_id, primary_location, primary_quantity, now, now))
    
    # 写入额外位置
    if extra_location:
        cursor.execute("""
            INSERT INTO item_locations (item_id, location, quantity, reason, is_primary, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (item_id, extra_location, extra_quantity or 1, extra_reason, now, now))

    _set_tags(conn, item_id, tags)
    _record_location(conn, primary_location)
    if extra_location:
        _record_location(conn, extra_location)
    conn.commit()

    tags_display = _get_tags(conn, item_id)
    item = dict(cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())
    locations_str = _get_locations_str(conn, item_id)
    conn.close()

    print(f"✓ 物品已添加 (ID:{item_id})")
    print(_format_item(item, tags_display, locations_str))
    return 0

# ── 搜索物品 ─────────────────────────────────────────────────────────────────

def search_items(name=None, category=None, location=None, tag=None, status=None,
                 limit=20, exact=False):
    """搜索物品（支持多条件组合，v2.0多位置搜索）"""
    conn = _get_conn()
    cursor = conn.cursor()

    query = "SELECT DISTINCT i.* FROM items i"
    params = []

    if tag or location:
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
        conditions.append("i.status = ?")
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
            tags_str = _get_tags(conn, row["id"])
            locations_str = _get_locations_str(conn, row["id"])
            print(_format_item(row, tags_str, locations_str))

    conn.close()
    return 0

# ── 更新物品 ─────────────────────────────────────────────────────────────────

def update_item(item_id, name=None, category=None, owner=None, status=None,
                remark=None, tags=None, purchase_price=None, purchase_date=None, 
                expiration_date=None, photo=None,
                primary_location=None, primary_quantity=None,
                extra_location=None, extra_quantity=None, extra_reason=None,
                extra_delta=None):
    """更新物品字段（v2.0多位置支持）"""
    conn = _get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    old = dict(row)

    # 1. 更新 items 表字段
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
    if status is not None:
        if status not in VALID_STATUSES:
            print(f"✗ 无效状态: {status}，有效值: {', '.join(VALID_STATUSES)}")
            conn.close()
            return 1
        updates.append("status = ?")
        params_list.append(status)
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

    if updates:
        updates.append("updated_at = ?")
        params_list.append(now)
        params_list.append(item_id)
        sql = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params_list)

    # 2. 处理 extra_delta 数量变更（指定位置的数量变化，如"冰箱的牛奶喝了1瓶"）
    if extra_delta is not None and extra_location:
        cursor.execute("""
            SELECT id, quantity FROM item_locations 
            WHERE item_id = ? AND location = ?
        """, (item_id, extra_location))
        row_il = cursor.fetchone()
        if row_il:
            new_qty = row_il['quantity'] + extra_delta
            if new_qty <= 0:
                cursor.execute("DELETE FROM item_locations WHERE id = ?", (row_il['id'],))
                print(f"✓ 位置「{extra_location}」物品已耗尽，删除该位置记录")
            else:
                cursor.execute("""
                    UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?
                """, (new_qty, now, row_il['id']))
                print(f"✓ 位置「{extra_location}」数量更新为 {new_qty}")
        
        # 检查是否所有位置都空了 -> 更新物品状态为已用完
        cursor.execute("SELECT COUNT(*) as cnt FROM item_locations WHERE item_id = ?", (item_id,))
        remaining = cursor.fetchone()['cnt']
        if remaining == 0:
            cursor.execute("UPDATE items SET status = '已用完', updated_at = ? WHERE id = ?", (now, item_id))
            print(f"✓ 自动标记为「已用完」")

    # 3. 处理 primary_location 变更（主位置变更）
    if primary_location is not None:
        cursor.execute("""
            SELECT id FROM item_locations 
            WHERE item_id = ? AND is_primary = 1
        """, (item_id,))
        row_primary = cursor.fetchone()
        if row_primary:
            cursor.execute("""
                UPDATE item_locations SET location = ?, quantity = ?, updated_at = ? 
                WHERE id = ?
            """, (primary_location, primary_quantity or 1, now, row_primary['id']))
        else:
            cursor.execute("""
                INSERT INTO item_locations (item_id, location, quantity, is_primary, created_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
            """, (item_id, primary_location, primary_quantity or 1, now, now))
        _record_location(conn, primary_location)

    # 4. 处理新增/更新 extra_location（非数量变更）
    if extra_location and extra_delta is None:
        cursor.execute("""
            SELECT id FROM item_locations 
            WHERE item_id = ? AND is_primary = 0 AND location = ?
        """, (item_id, extra_location))
        row_extra = cursor.fetchone()
        if row_extra:
            if extra_quantity is not None:
                cursor.execute("UPDATE item_locations SET quantity = ?, reason = ?, updated_at = ? WHERE id = ?",
                             (extra_quantity, extra_reason, now, row_extra['id']))
        else:
            cursor.execute("""
                INSERT INTO item_locations (item_id, location, quantity, reason, is_primary, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
            """, (item_id, extra_location, extra_quantity or 1, extra_reason, now, now))
        if extra_location:
            _record_location(conn, extra_location)

    # 5. 标签变更
    old_tags = _get_tags(conn, item_id)
    if tags is not None:
        _set_tags(conn, item_id, tags)

    # 6. 访问计数+1
    _touch_item(conn, item_id)

    conn.commit()

    # 读取更新后的记录
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    new_row = dict(cursor.fetchone())
    tags_str = _get_tags(conn, item_id)
    locations_str = _get_locations_str(conn, item_id)

    # 输出变更摘要
    changes = []
    if name and name != old["name"]:
        changes.append(f"名称: {old['name']} → {name}")
    if status and status != old["status"]:
        changes.append(f"状态: {old['status']} → {status}")
    if tags is not None:
        new_tags = _get_tags(conn, item_id)
        if old_tags != new_tags:
            changes.append(f"标签: {old_tags or '无'} → {new_tags}")

    print(f"✓ 已更新 ID:{item_id} ({old['name']})")
    if changes:
        print(" | ".join(changes))
    print(_format_item(new_row, tags_str, locations_str))

    conn.close()
    return 0

    print(_format_item(new_row, tags_str))

    conn.close()
    return 0

# ── 列表查询 ─────────────────────────────────────────────────────────────────

def list_items(location=None, status=None, category=None, owner=None,
               sort_by="name", limit=100):
    """按条件列出物品（v2.0多位置）"""
    conn = _get_conn()
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
        conditions.append("status = ?")
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
            tags_str = _get_tags(conn, row["id"])
            locations_str = _get_locations_str(conn, row["id"])
            print(_format_item(row, tags_str, locations_str))

    conn.close()
    return 0

# ── 盘点 ─────────────────────────────────────────────────────────────────────

def inventory(location):
    """盘点指定位置的所有物品（v2.0多位置搜索）"""
    conn = _get_conn()
    cursor = conn.cursor()

    # 搜索主位置或额外位置匹配的所有物品
    cursor.execute("""
        SELECT DISTINCT i.*, il.location as matched_location, il.quantity as matched_quantity, il.is_primary
        FROM items i
        JOIN item_locations il ON i.id = il.item_id
        WHERE il.location LIKE ?
        ORDER BY i.category, i.name
    """, (f"%{location}%",))
    rows = cursor.fetchall()

    if not rows:
        print(f"位置 '{location}' 下没有物品")
    else:
        # 按物品聚合（同一物品可能匹配多个位置）
        item_map = {}
        for row in rows:
            iid = row['id']
            if iid not in item_map:
                item_map[iid] = {
                    'item': row,
                    'matched': []
                }
            item_map[iid]['matched'].append({
                'location': row['matched_location'],
                'quantity': row['matched_quantity'],
                'is_primary': row['is_primary']
            })

        total_items = len(item_map)
        print(f"盘点「{location}」：共 {total_items} 件")
        print("-" * 80)
        for iid, data in item_map.items():
            row = data['item']
            matched = data['matched']
            # 构建位置字符串
            parts = []
            for m in matched:
                if m['is_primary']:
                    parts.append(f"{m['location']} ×{m['quantity']}[主]")
                else:
                    parts.append(f"{m['location']} ×{m['quantity']}")
            locs_str = " | ".join(parts)
            tags_str = _get_tags(conn, row["id"])
            print(f"ID:{row['id']} | {row['name']} | {row['category']} | {locs_str} | {row['status']} | {tags_str}")

    conn.close()
    return 0

# ── 频率统计 ─────────────────────────────────────────────────────────────────

def stats(stat_type="frequent", limit=20):
    """频率统计"""
    conn = _get_conn()
    cursor = conn.cursor()

    if stat_type == "frequent":
        cursor.execute("""
            SELECT * FROM items
            ORDER BY access_count DESC LIMIT ?
        """, (limit,))
        title = f"高频物品 TOP{limit}"
    elif stat_type == "dormant":
        cursor.execute("""
            SELECT * FROM items
            WHERE last_accessed_at IS NOT NULL
            ORDER BY last_accessed_at ASC LIMIT ?
        """, (limit,))
        title = f"长期未访问 TOP{limit}"
    elif stat_type == "summary":
        cursor.execute("SELECT COUNT(*) as total FROM items")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as n FROM items WHERE status = '已用完'")
        used_up = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) as n FROM items WHERE status = '已废弃'")
        abandoned = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) as n FROM items WHERE status = '借用中'")
        lent = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(*) as n FROM items WHERE status = '旅游中'")
        out = cursor.fetchone()["n"]
        cursor.execute("""
            SELECT category, COUNT(*) as cnt FROM items
            GROUP BY category ORDER BY cnt DESC
        """)
        cats = cursor.fetchall()

        print(f"总物品数：{total}")
        print(f"在家/备用：{total - used_up - abandoned} | 已用完：{used_up} | 已废弃：{abandoned}")
        print(f"借用中：{lent} | 外出中：{out}")
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
            tags_str = _get_tags(conn, row["id"])
            accessed = row["last_accessed_at"] or "从未"
            print(f"访问{row['access_count']}次 | 最后:{accessed[:16] if accessed != '从未' else accessed} | " +
                  _format_item(row, tags_str))

    conn.close()
    return 0

# ── 标签合并 ─────────────────────────────────────────────────────────────────

def tag_merge(from_tag, to_tag):
    """将所有 from_tag 替换为 to_tag"""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM item_tags WHERE tag = ?", (from_tag,))
    from_count = cursor.fetchone()["cnt"]
    if from_count == 0:
        print(f"标签 '{from_tag}' 不存在")
        conn.close()
        return 1

    cursor.execute("SELECT item_id FROM item_tags WHERE tag = ?", (from_tag,))
    item_ids = [row["item_id"] for row in cursor.fetchall()]

    for item_id in item_ids:
        cursor.execute("INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
                       (item_id, to_tag))
        cursor.execute("DELETE FROM item_tags WHERE item_id = ? AND tag = ?",
                       (item_id, from_tag))

    conn.commit()
    conn.close()

    print(f"✓ 已将 {from_count} 个 '{from_tag}' 合并为 '{to_tag}'")
    return 0

# ── 标签列表 ─────────────────────────────────────────────────────────────────

def tag_list():
    """列出所有标签及使用次数"""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tag, COUNT(*) as cnt FROM item_tags
        GROUP BY tag ORDER BY cnt DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("(暂无标签)")
    else:
        print(f"共 {len(rows)} 个标签：")
        for row in rows:
            print(f"  {row['tag']} ({row['cnt']})")

    conn.close()
    return 0

# ── 物品详情 ─────────────────────────────────────────────────────────────────

def item_detail(item_id):
    """查看物品详细信息（v2.0多位置）"""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    item = dict(row)
    tags_str = _get_tags(conn, item_id)

    # 获取所有位置
    cursor.execute("""
        SELECT location, quantity, reason, is_primary 
        FROM item_locations 
        WHERE item_id = ? 
        ORDER BY is_primary DESC, id
    """, (item_id,))
    locations = cursor.fetchall()

    print(f"===== 物品详情 =====")
    print(f"ID:       {item['id']}")
    print(f"名称:     {item['name']}")
    print(f"分类:     {item['category']}")
    
    # 位置信息
    if locations:
        print("位置分布：")
        for loc in locations:
            role = "[主]" if loc['is_primary'] else "[额外]"
            reason_str = f" - {loc['reason']}" if loc['reason'] else ""
            print(f"  {role} {loc['location']} × {loc['quantity']}{reason_str}")
    else:
        print("位置:     (未设置)")
    
    print(f"所有者:   {item['owner']}")
    print(f"状态:     {item['status']}")
    total_qty = sum(loc['quantity'] for loc in locations)
    print(f"总数量:   {total_qty}")
    if item['purchase_price']:
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

# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="居家管家 - 家庭物品管理系统 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python home_manager.py add --name "白T恤" --category 衣物 --location "卧室/衣柜/上层" --tags "白色,短袖"
  python home_manager.py search --name "T恤"
  python home_manager.py search --location "卧室" --status "在家"
  python home_manager.py update --id 1 --status "借用中"
  python home_manager.py list --location "卧室/衣柜"
  python home_manager.py inventory --location "卧室"
  python home_manager.py stats --type summary
  python home_manager.py tag-merge --from "白" --to "白色"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── init ──
    p_init = subparsers.add_parser("init", help="初始化数据库（建表+索引）")

    # ── add ──
    p_add = subparsers.add_parser("add", help="添加物品")
    p_add.add_argument("--name", required=True, help="物品名称")
    p_add.add_argument("--category", required=True, help="分类")
    p_add.add_argument("--location", required=True, help="主存放位置（路径格式）")
    p_add.add_argument("--owner", default="使用者", help="所有者")
    p_add.add_argument("--status", default="在家", help="状态")
    p_add.add_argument("--quantity", type=int, default=1, help="主位置数量（默认1）")
    p_add.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_add.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_add.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_add.add_argument("--remark", default="", help="备注")
    p_add.add_argument("--tags", default="", help="标签（逗号分隔）")
    p_add.add_argument("--photo", default="", help="图片路径")
    p_add.add_argument("--extra-location", default=None, help="额外存放位置")
    p_add.add_argument("--extra-quantity", type=int, default=None, help="额外位置的数量")
    p_add.add_argument("--extra-reason", default=None, help="额外位置的原因")

    # ── search ──
    p_search = subparsers.add_parser("search", help="搜索物品")
    p_search.add_argument("--name", default=None, help="物品名称（支持模糊）")
    p_search.add_argument("--category", default=None, help="分类")
    p_search.add_argument("--location", default=None, help="位置（支持模糊）")
    p_search.add_argument("--tag", default=None, help="标签（精确匹配）")
    p_search.add_argument("--status", default=None, help="状态")
    p_search.add_argument("--exact", action="store_true", help="名称精确匹配")
    p_search.add_argument("--limit", type=int, default=20, help="返回数量上限")

    # ── update ──
    p_update = subparsers.add_parser("update", help="更新物品")
    p_update.add_argument("--id", type=int, required=True, help="物品ID")
    p_update.add_argument("--name", default=None, help="物品名称")
    p_update.add_argument("--category", default=None, help="分类")
    p_update.add_argument("--owner", default=None, help="所有者")
    p_update.add_argument("--status", default=None, help="状态")
    p_update.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_update.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_update.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_update.add_argument("--remark", default=None, help="备注")
    p_update.add_argument("--tags", default=None, help="标签（逗号分隔，覆盖）")
    p_update.add_argument("--photo", default=None, help="图片路径")
    p_update.add_argument("--primary-location", default=None, help="主存放位置")
    p_update.add_argument("--primary-quantity", type=int, default=None, help="主位置数量")
    p_update.add_argument("--extra-location", default=None, help="额外位置（如冰箱里那瓶）")
    p_update.add_argument("--extra-quantity", type=int, default=None, help="额外位置的数量")
    p_update.add_argument("--extra-reason", default=None, help="额外位置的原因")
    p_update.add_argument("--extra-delta", type=int, default=None, help="额外位置数量变化（如-1表示喝了一瓶）")

    # ── list ──
    p_list = subparsers.add_parser("list", help="列出物品")
    p_list.add_argument("--location", default=None, help="位置")
    p_list.add_argument("--status", default=None, help="状态")
    p_list.add_argument("--category", default=None, help="分类")
    p_list.add_argument("--owner", default=None, help="所有者")
    p_list.add_argument("--sort", default="name",
                        choices=["name", "recent", "frequent", "updated", "dormant"],
                        help="排序方式")
    p_list.add_argument("--limit", type=int, default=100, help="返回数量上限")

    # ── inventory ──
    p_inventory = subparsers.add_parser("inventory", help="盘点指定位置")
    p_inventory.add_argument("--location", required=True, help="要盘点的位置")

    # ── stats ──
    p_stats = subparsers.add_parser("stats", help="频率统计")
    p_stats.add_argument("--type", default="summary",
                         choices=["frequent", "dormant", "summary"],
                         help="统计类型：frequent=高频, dormant=长期未碰, summary=总览")
    p_stats.add_argument("--limit", type=int, default=20, help="返回数量上限")

    # ── tag-merge ──
    p_merge = subparsers.add_parser("tag-merge", help="合并标签")
    p_merge.add_argument("--from", dest="from_tag", required=True, help="要被合并的标签")
    p_merge.add_argument("--to", dest="to_tag", required=True, help="合并目标标签")

    # ── tag-list ──
    p_taglist = subparsers.add_parser("tag-list", help="列出所有标签")

    # ── detail ──
    p_detail = subparsers.add_parser("detail", help="查看物品详情")
    p_detail.add_argument("--id", type=int, required=True, help="物品ID")

    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("✓ 数据库初始化完成")
        print(f"  数据库: {DB_PATH}")
        print(f"  图片目录: {PHOTOS_DIR}")

    elif args.command == "add":
        return add_item(
            name=args.name, category=args.category, primary_location=args.location,
            owner=args.owner, status=args.status, primary_quantity=args.quantity,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, remark=args.remark, tags=args.tags,
            photo=args.photo,
            extra_location=args.extra_location, extra_quantity=args.extra_quantity,
            extra_reason=args.extra_reason
        )

    elif args.command == "search":
        return search_items(
            name=args.name, category=args.category, location=args.location,
            tag=args.tag, status=args.status, limit=args.limit, exact=args.exact
        )

    elif args.command == "update":
        return update_item(
            item_id=args.id, name=args.name, category=args.category, owner=args.owner,
            status=args.status, remark=args.remark, tags=args.tags,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, photo=args.photo,
            primary_location=args.primary_location, primary_quantity=args.primary_quantity,
            extra_location=args.extra_location, extra_quantity=args.extra_quantity,
            extra_reason=args.extra_reason, extra_delta=args.extra_delta
        )

    elif args.command == "list":
        return list_items(
            location=args.location, status=args.status, category=args.category,
            owner=args.owner, sort_by=args.sort, limit=args.limit
        )

    elif args.command == "inventory":
        return inventory(location=args.location)

    elif args.command == "stats":
        return stats(stat_type=args.type, limit=args.limit)

    elif args.command == "tag-merge":
        return tag_merge(from_tag=args.from_tag, to_tag=args.to_tag)

    elif args.command == "tag-list":
        return tag_list()

    elif args.command == "detail":
        return item_detail(item_id=args.id)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
