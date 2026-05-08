#!/usr/bin/env python3
"""
居家管家 - 家庭物品管理系统 v1.0
- SQLite 数据库存储（3张表：items / item_tags / locations）
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
        if p.exists() or Path(env_path).is_dir():
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
            # .db 目录存在但没有这个文件，返回None，让调用方在目录创建
            return p  # 返回目标路径（可能在目录中不存在）
    return p  # 最后返回技能目录下的默认路径

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
PHOTOS_DIR = SKILL_DIR / "photos"

# ── 状态常量 ──────────────────────────────────────────────────────────────────

VALID_STATUSES = ("在家", "备用", "穿着中", "旅游中", "洗护中", "借用中",
                  "维修中", "已用完", "待处理", "已废弃")

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
            location TEXT NOT NULL,
            owner TEXT DEFAULT '使用者',
            status TEXT DEFAULT '在家',
            quantity INTEGER DEFAULT 1,
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
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_path TEXT UNIQUE NOT NULL,
            use_count INTEGER DEFAULT 1,
            last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_name ON items(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_location ON items(location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_status ON items(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_access_count ON items(access_count)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_item_id ON item_tags(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_tags_tag ON item_tags(tag)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_path ON locations(location_path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_locations_use_count ON locations(use_count)")

    conn.commit()
    conn.close()
    return True

# ── 辅助函数 ─────────────────────────────────────────────────────────────────

def _get_conn():
    """获取数据库连接（自动初始化）"""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
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

def _format_item(row, tags_str=None):
    """格式化单个物品为文本"""
    tags = tags_str if tags_str is not None else ""
    price = f"¥{row['purchase_price']:.2f}" if row["purchase_price"] else ""
    photo = "[图]" if row["photo"] else ""
    return (
        f"ID:{row['id']} | {row['name']} | {row['category']} | "
        f"{row['location']} | {row['status']} | x{row['quantity']} "
        f"| {price} | {tags} | {row['remark'] or ''} {photo}"
    ).strip()

# ── 添加物品 ─────────────────────────────────────────────────────────────────

def add_item(name, category, location, owner="使用者", status="在家",
             quantity=1, purchase_price=None, purchase_date=None, expiration_date=None,
             remark="", tags="", photo=""):
    """添加新物品"""
    conn = _get_conn()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO items (name, category, location, owner, status, quantity,
                          purchase_price, purchase_date, expiration_date, remark, photo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category, location, owner, status, quantity,
          purchase_price, purchase_date, expiration_date, remark, photo, now, now))

    item_id = cursor.lastrowid

    _set_tags(conn, item_id, tags)
    _record_location(conn, location)
    conn.commit()

    tags_display = _get_tags(conn, item_id)
    item = dict(cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())
    conn.close()

    print(f"✓ 物品已添加")
    print(_format_item(item, tags_display))
    return 0

# ── 搜索物品 ─────────────────────────────────────────────────────────────────

def search_items(name=None, category=None, location=None, tag=None, status=None,
                 limit=20, exact=False):
    """搜索物品（支持多条件组合）"""
    conn = _get_conn()
    cursor = conn.cursor()

    query = "SELECT DISTINCT i.* FROM items i"
    params = []

    if tag:
        query += " JOIN item_tags t ON i.id = t.item_id"

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
        conditions.append("i.location LIKE ?")
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
            print(_format_item(row, tags_str))

    conn.close()
    return 0

# ── 更新物品 ─────────────────────────────────────────────────────────────────

def update_item(item_id, location=None, status=None, quantity=None,
                remark=None, tags=None, name=None, category=None, owner=None,
                purchase_price=None, purchase_date=None, expiration_date=None, photo=None):
    """更新物品字段（支持部分更新）"""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    old = dict(row)

    updates = []
    params_list = []

    if location is not None:
        updates.append("location = ?")
        params_list.append(location)
    if status is not None:
        if status not in VALID_STATUSES:
            print(f"✗ 无效状态: {status}，有效值: {', '.join(VALID_STATUSES)}")
            conn.close()
            return 1
        updates.append("status = ?")
        params_list.append(status)
    if quantity is not None:
        updates.append("quantity = ?")
        params_list.append(quantity)
        # 数量归零自动标记已用完
        if quantity == 0 and status is None:
            updates.append("status = ?")
            params_list.append("已用完")
    if remark is not None:
        updates.append("remark = ?")
        params_list.append(remark)
    if name is not None:
        updates.append("name = ?")
        params_list.append(name)
    if category is not None:
        updates.append("category = ?")
        params_list.append(category)
    if owner is not None:
        updates.append("owner = ?")
        params_list.append(owner)
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

    # 标签变更单独判断（不走SQL）
    has_tag_change = tags is not None

    if not updates and not has_tag_change and location is None:
        print("(无变更)")
        conn.close()
        return 0

    if updates:
        updates.append("updated_at = ?")
        params_list.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        params_list.append(item_id)
        sql = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params_list)

    # 记录旧标签（在_set_tags前读取）
    old_tags = _get_tags(conn, item_id)

    # 更新标签
    if has_tag_change:
        _set_tags(conn, item_id, tags)

    # 记录位置变化
    if location is not None:
        _record_location(conn, location)

    # 访问计数+1
    _touch_item(conn, item_id)

    conn.commit()

    # 读取更新后的记录
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    new_row = dict(cursor.fetchone())
    tags_str = _get_tags(conn, item_id)

    # 输出变更摘要
    changes = []
    if location and location != old["location"]:
        changes.append(f"位置: {old['location']} → {location}")
    if status and status != old["status"]:
        changes.append(f"状态: {old['status']} → {status}")
    if quantity is not None and quantity != old["quantity"]:
        changes.append(f"数量: {old['quantity']} → {quantity}")
    if tags is not None:
        new_tags = _get_tags(conn, item_id)
        if old_tags != new_tags:
            changes.append(f"标签: {old_tags or '无'} → {new_tags}")

    print(f"✓ 已更新 ID:{item_id} ({old['name']})")
    if changes:
        print(" | ".join(changes))
    # Show auto status change
    if quantity is not None and quantity == 0 and (status is None or status != "已用完"):
        status_text = "已用完"
        print(f" | (自动) 状态 → {status_text}")
    print(_format_item(new_row, tags_str))

    conn.close()
    return 0

# ── 列表查询 ─────────────────────────────────────────────────────────────────

def list_items(location=None, status=None, category=None, owner=None,
               sort_by="name", limit=100):
    """按条件列出物品"""
    conn = _get_conn()
    cursor = conn.cursor()

    conditions = []
    params = []

    if location:
        conditions.append("location LIKE ?")
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
            print(_format_item(row, tags_str))

    conn.close()
    return 0

# ── 盘点 ─────────────────────────────────────────────────────────────────────

def inventory(location):
    """盘点指定位置的所有物品"""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM items
        WHERE location LIKE ?
        ORDER BY category, name
    """, (f"%{location}%",))
    rows = cursor.fetchall()

    if not rows:
        print(f"位置 '{location}' 下没有物品")
    else:
        print(f"盘点「{location}」：共 {len(rows)} 件")
        print("-" * 80)
        for row in rows:
            tags_str = _get_tags(conn, row["id"])
            print(_format_item(row, tags_str))

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
    """查看物品详细信息"""
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

    print(f"===== 物品详情 =====")
    print(f"ID:       {item['id']}")
    print(f"名称:     {item['name']}")
    print(f"分类:     {item['category']}")
    print(f"位置:     {item['location']}")
    print(f"所有者:   {item['owner']}")
    print(f"状态:     {item['status']}")
    print(f"数量:     {item['quantity']}")
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
    p_add.add_argument("--location", required=True, help="存放位置（路径格式）")
    p_add.add_argument("--owner", default="使用者", help="所有者")
    p_add.add_argument("--status", default="在家", help="状态")
    p_add.add_argument("--quantity", type=int, default=1, help="数量（默认1）")
    p_add.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_add.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_add.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_add.add_argument("--remark", default="", help="备注")
    p_add.add_argument("--tags", default="", help="标签（逗号分隔）")
    p_add.add_argument("--photo", default="", help="图片路径")

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
    p_update.add_argument("--location", default=None, help="存放位置")
    p_update.add_argument("--owner", default=None, help="所有者")
    p_update.add_argument("--status", default=None, help="状态")
    p_update.add_argument("--quantity", type=int, default=None, help="数量")
    p_update.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_update.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_update.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_update.add_argument("--remark", default=None, help="备注")
    p_update.add_argument("--tags", default=None, help="标签（逗号分隔，覆盖）")
    p_update.add_argument("--photo", default=None, help="图片路径")

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
            name=args.name, category=args.category, location=args.location,
            owner=args.owner, status=args.status, quantity=args.quantity,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, remark=args.remark, tags=args.tags,
            photo=args.photo
        )

    elif args.command == "search":
        return search_items(
            name=args.name, category=args.category, location=args.location,
            tag=args.tag, status=args.status, limit=args.limit, exact=args.exact
        )

    elif args.command == "update":
        return update_item(
            item_id=args.id, location=args.location, status=args.status,
            quantity=args.quantity, remark=args.remark, tags=args.tags,
            name=args.name, category=args.category, owner=args.owner,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, photo=args.photo
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
