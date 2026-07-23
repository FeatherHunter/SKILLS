# item_ops.py - 物品 CRUD 操作
import os
import shutil
from datetime import datetime
from .db import get_conn, PHOTOS_DIR
from . import location_ops
from .location_ops import (
    get_locations, add_location, remove_location,
    update_location_quantity, update_location_status,
    update_location_dates, find_location_by_path, _locations_str
)
from .tag_ops import get_tags, set_tags, add_tag, remove_tag


VALID_STATUSES = ("在家", "备用", "穿着中", "旅游中", "洗护中", "借用中",
                  "维修中", "已用完", "快递中", "待处理", "已废弃")


# ── category_id → category_name 缓存(避免每行 N+1 查询)──
_category_name_cache = {}


def _load_category_cache(conn):
    """从 categories 表加载所有 (id → name) 到模块缓存"""
    global _category_name_cache
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories")
    _category_name_cache = {r['id']: r['name'] for r in cursor.fetchall()}


_category_top_cache = None


def _load_top_category_cache(conn):
    """加载 (category_id → top_category_id) 缓存"""
    global _category_top_cache
    if _category_top_cache is not None:
        return _category_top_cache
    cursor = conn.cursor()
    cursor.execute("""
        WITH RECURSIVE ancestors AS (
          SELECT id, parent_id, id AS top_id, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, a.top_id, a.lvl + 1
          FROM categories c JOIN ancestors a ON c.parent_id = a.id
        )
        SELECT id, top_id FROM ancestors
    """)
    _category_top_cache = {r['id']: r['top_id'] for r in cursor.fetchall()}
    return _category_top_cache


def _expand_category_ids(conn, cat_id):
    """从 cat_id 出发,递归查所有下级 id(包含自身)

    - 顶级 ID(1 级)→ 全部下级(2 级 + 3 级)
    - 二级 ID(2 级)→ 2 级 + 3 级下级
    - 三级 ID(3 级)→ 仅 3 级(精确)
    """
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


def _category_condition(category_id):
    """生成 (conditions, params) 片段:支持二级/顶级自动展开下级"""
    ids = _expand_category_ids(_category_name_cache.get('__conn__'), category_id) \
        if '__conn__' in _category_name_cache else None
    # 上面这行只是占位,实际使用见下
    return None  # 实际在函数里直接展开


def _category_in_clause(conn, category_id):
    """生成 (where_clause, params):单 id 用 =,多 id 用 IN (...)"""
    ids = _expand_category_ids(conn, category_id)
    if len(ids) == 1:
        return "category_id = ?", [ids[0]]
    placeholders = ",".join("?" * len(ids))
    return f"category_id IN ({placeholders})", ids


# ── 辅助 ──────────────────────────────────────────────────────────────────


def get_photo_full_path(photo_relative_path):
    """根据相对路径获取照片的完整路径"""
    if not photo_relative_path:
        return None
    return PHOTOS_DIR / photo_relative_path


def _touch_item(conn, item_id):
    """更新物品访问计数"""
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items SET access_count = access_count + 1,
        last_accessed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (item_id,))


def _safe_photo_name(name):
    invalid = '<>:"/\\|?*'
    safe = ''.join('_' if ch in invalid else ch for ch in name).strip()
    return safe or "物品"


def _prepare_add_photo(photo, item_id, name):
    if not photo:
        return ""
    photos_dir = os.path.abspath(str(PHOTOS_DIR))
    src = os.path.abspath(photo)
    if os.path.commonpath([photos_dir, src]) != photos_dir:
        raise ValueError(
            f"照片路径必须放在环境变量目录下\n  要求路径以: {photos_dir}\n  当前路径:   {photo}\n  请先将图片复制到 {photos_dir} 后再传入"
        )
    ext = os.path.splitext(src)[1] or ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d')}_{item_id}_{_safe_photo_name(name)}{ext}"
    dst = os.path.abspath(os.path.join(photos_dir, filename))
    try:
        if src != dst:
            shutil.copy2(src, dst)
    except OSError as e:
        raise ValueError(f"照片复制失败: {e}")
    return filename


def _format_item(row, tags_str=None, locations_str=None):
    """格式化单个物品为文本"""
    tags = tags_str if tags_str is not None else ""
    price = f"¥{row['purchase_price']:.2f}" if row["purchase_price"] else ""
    if row["photo"]:
        photo_path = get_photo_full_path(row["photo"])
        photo = f"[图:{photo_path}]" if photo_path else "[图]"
    else:
        photo = ""
    locs = locations_str if locations_str is not None else "(未设置位置)"
    # category_id → category_name 派生(用模块级 cache 避免 N+1)
    cat_id = row['category_id'] if 'category_id' in row.keys() else None
    cat_name = _category_name_cache.get(cat_id, f"id={cat_id}") if cat_id else ""
    return (
        f"ID:{row['id']} | {row['name']} | {cat_name} | "
        f"{locs} | {price} | {tags} | {row['remark'] or ''} {photo}"
    ).strip()


# ── add ─────────────────────────────────────────────────────────────────────


def add_item(name, category_id, location, owner="使用者", quantity=1,
             purchase_price=None, purchase_date=None, expiration_date=None,
             remark="", tags="", photo="", location_status=None):
    """添加新物品

    心愿 ID: 标签+备注硬约束（无可绕过通道）
        - tags 数量 < 10 → 报错
        - remark 为空 → 报错

    新分类体系(A.8):--category-id 必选,内部 derive category 字符串写入老字段(向后兼容)
    """
    # ── 硬约束：与 preview 共用 validators, 保证口径一致 ──
    from .validators import validate_hard_rules
    _, missing = validate_hard_rules({
        'name': name, 'category_id': category_id, 'location': location,
        'tags': tags, 'remark': remark,
    })
    location_depth_ok = '/' in (location or '').strip('/')
    if not location_depth_ok:
        print(f"✗ 录入失败：位置必须至少两级（含'/'分隔）")
        print(f"  当前位置: {location or '(空)'}")
        return 1

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    if len(tag_list) < 10:
        print(f"✗ 录入失败：需要 tag 最少十个，备注不能为空且要全面")
        print(f"  当前 tag 数量: {len(tag_list)}（要求 ≥ 10）")
        if tag_list:
            print(f"  当前 tag: {', '.join(tag_list)}")
        return 1
    if not remark or not remark.strip():
        print(f"✗ 录入失败：需要 tag 最少十个，备注不能为空且要全面")
        print(f"  当前备注: 空（要求非空）")
        return 1

    # ── 照片路径先校验，规范命名需等 INSERT 后拿到 item_id ──
    if photo:
        photos_dir = os.path.abspath(str(PHOTOS_DIR))
        photo_path = os.path.abspath(photo)
        if os.path.commonpath([photos_dir, photo_path]) != photos_dir:
            print(f"✗ 照片路径必须放在环境变量目录下")
            print(f"  要求路径以: {photos_dir}")
            print(f"  当前路径:   {photo}")
            print(f"  请先将图片复制到 {photos_dir} 后再传入")
            return 1

    # 最小实现：如果位置路径包含"快递"，则自动设置状态为"快递中"
    if location_status is None:
        if "快递" in location:
            location_status = "快递中"
        else:
            location_status = "在家"

    conn = get_conn()
    cursor = conn.cursor()
    # ── 验证 category_id 存在 + 激活 ──
    cursor.execute("SELECT name FROM categories WHERE id = ? AND is_active = 1", (category_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ category_id={category_id} 不存在或未激活")
        conn.close()
        return 1
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO items (name, category_id, owner, purchase_price, remark, photo, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, category_id, owner, purchase_price, remark, "", now, now))

    item_id = cursor.lastrowid

    try:
        photo = _prepare_add_photo(photo, item_id, name)
    except ValueError as e:
        print(f"✗ {e}")
        conn.close()
        return 1
    if photo:
        cursor.execute(
            "UPDATE items SET photo = ?, updated_at = ? WHERE id = ?",
            (photo, now, item_id)
        )

    # 添加位置（日期记录在位置级别）
    add_location(conn, item_id, location, quantity, reason=None, location_status=location_status,
                 purchase_date=purchase_date, expiration_date=expiration_date)
    set_tags(conn, item_id, tags)
    conn.commit()

    tags_display = get_tags(conn, item_id)
    item = dict(cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone())
    locations_str = _locations_str(item_id)
    conn.close()

    print(f"✓ 物品已添加 (ID:{item_id})")
    print(_format_item(item, tags_display, locations_str))
    return 0


# ── search ──────────────────────────────────────────────────────────────────


def search_items(name=None, category_id=None, location=None, tag=None, status=None,
                limit=20, exact=False):
    """搜索物品（支持多条件组合，per-location status 搜索）"""
    conn = get_conn()
    cursor = conn.cursor()
    _load_category_cache(conn)

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
    if category_id:
        clause, c_params = _category_in_clause(conn, category_id)
        conditions.append("i." + clause)
        params.extend(c_params)
    if location:
        conditions.append("(il.location LIKE ? OR il.location IS NULL)")
        params.append(f"%{location}%")
    if status:
        # 搜索位置状态：任意一个位置的 location_status 匹配即命中
        conditions.append("il.location_status = ?")
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


def update_item(item_id, name=None, category_id=None, owner=None,
               remark=None, tags=None, purchase_price=None, purchase_date=None,
               expiration_date=None, photo=None,
               new_location=None, quantity=None,
               minus=None, plus=None,
               location=None, location_status=None,
               add_location=None, add_quantity=1, add_reason=None,
               add_location_status=VALID_STATUSES[0],
               add_purchase_date=None, add_expiration_date=None,
               add_tags=None, remove_tags=None):
    """更新物品字段

    add_location 系列参数（心愿 ID: 84）：
        - add_location: 指定要追加的新位置路径
        - add_quantity: 新位置数量（默认1）
        - add_reason: 新位置原因（可选备注）
        - add_location_status: 新位置状态（默认"在家"）
        - add_purchase_date / add_expiration_date: 新位置的购买/过期日期
    与 new_location（替换现有位置）的区别：add_location 不动现有位置记录，
    仅插入一条新记录，实现"一物多位置"。
    """
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
    if category_id is not None:
        # 验证 category_id 存在 + 激活
        cursor.execute("SELECT name FROM categories WHERE id = ? AND is_active = 1", (category_id,))
        row_cat = cursor.fetchone()
        if not row_cat:
            print(f"✗ category_id={category_id} 不存在或未激活")
            conn.close()
            return 1
        updates.append("category_id = ?")
        params_list.append(category_id)
    if owner is not None:
        updates.append("owner = ?")
        params_list.append(owner)
    if remark is not None:
        updates.append("remark = ?")
        params_list.append(remark)
    if purchase_price is not None:
        updates.append("purchase_price = ?")
        params_list.append(purchase_price)
    # ── 照片路径校验 & 裁剪（仅当 photo 有值时） ─────────────────
    if photo is not None and photo != "":
        photos_dir = str(PHOTOS_DIR)
        if not photo.startswith(photos_dir):
            print(f"✗ 照片路径必须放在环境变量目录下")
            print(f"  要求路径以: {photos_dir}")
            print(f"  当前路径:   {photo}")
            print(f"  请先将图片复制到 {photos_dir} 后再传入")
            return 1
        # 裁剪掉环境变量前缀，只存相对路径
        photo = photo[len(photos_dir):].lstrip(os.sep)
    # ── 校验 & 裁剪结束 ──────────────────────────────────────────

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

    # ── 统一的位置解析函数 ────────────────────────────────────────────────
    def _resolve_location(item_id, specified_location, conn, cursor):
        """根据指定位置或唯一位置来确定要操作的位置"""
        cursor.execute(
            "SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?",
            (item_id,)
        )
        locations = cursor.fetchall()
        
        if not locations:
            return None, "该物品没有位置记录"
        
        if specified_location:
            # 精确匹配指定位置
            for loc in locations:
                if loc[1] == specified_location:
                    return loc, None
            return None, f"未找到「{specified_location}」，可用位置："
        
        if len(locations) == 1:
            return locations[0], None
        
        locs_str = "、".join([f"{loc[1]}×{loc[2]}" for loc in locations])
        return None, f"该物品有 {len(locations)} 个位置，请用 --location 指定：{locs_str}"


    # ── 1. 数量变化（--minus / --plus）────────────────────────────────────
    if minus is not None or plus is not None:
        delta = -abs(minus) if minus is not None else abs(plus)
        loc, err = _resolve_location(item_id, location, conn, cursor)
        if err:
            print(f"✗ {err}")
            for loc in cursor.execute("SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?", (item_id,)).fetchall():
                print(f"  {loc[1]} × {loc[2]} [{loc[3]}])")
            conn.close()
            return 1
        
        new_qty = loc[2] + delta
        if new_qty <= 0:
            remove_location(conn, loc[0])
            print(f"✓ 位置「{loc[1]}」物品已耗尽，删除该位置记录")
        else:
            cursor.execute(
                "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
                (new_qty, now, loc[0])
            )
            action = "喝掉" if minus else "补充"
            print(f"✓ {action} {abs(delta)}个，剩余 {new_qty} 个（位置：{loc[1]}）")

    # ── 1.5. 直接设置位置数量（--quantity）──────────────────────────────────
    if quantity is not None:
        loc, err = _resolve_location(item_id, location, conn, cursor)
        if err:
            print(f"✗ {err}")
            for loc in cursor.execute(
                "SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?",
                (item_id,)
            ).fetchall():
                print(f"  {loc[1]} × {loc[2]} [{loc[3]}]")
            conn.close()
            return 1

        old_qty = loc[2]
        cursor.execute(
            "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
            (quantity, now, loc[0])
        )
        print(f"✓ 位置「{loc[1]}」数量已从 {old_qty} 设置为 {quantity}")

    # ── 2. 位置移动（--new-location）───────────────────────────────────────
    if new_location is not None:
        loc, err = _resolve_location(item_id, location, conn, cursor)
        if err:
            print(f"✗ {err}")
            for loc in cursor.execute("SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?", (item_id,)).fetchall():
                print(f"  {loc[1]} × {loc[2]} [{loc[3]}]")
            conn.close()
            return 1
        
        old_loc, qty, old_status = loc[1], loc[2], loc[3]
        cursor.execute(
            "UPDATE item_locations SET location = ?, updated_at = ? WHERE id = ?",
            (new_location, now, loc[0])
        )
        print(f"✓ 物品已从「{old_loc}」搬到「{new_location}」")

        # 如果同时有 --location-status，作用于新位置（而非旧位置）
        if location_status is not None:
            if location_status not in VALID_STATUSES:
                print(f"✗ 无效状态: {location_status}，有效值: {', '.join(VALID_STATUSES)}")
                conn.close()
                return 1
            update_location_status(conn, loc[0], location_status)
            print(f"✓ 位置「{new_location}」状态已更新为「{location_status}」")
            location_status = None  # 标记为已处理，避免 Block 3 重复执行

    # ── 3. 状态变更（--location-status）────────────────────────────────────
    if location_status is not None:
        if location_status not in VALID_STATUSES:
            print(f"✗ 无效状态: {location_status}，有效值: {', '.join(VALID_STATUSES)}")
            conn.close()
            return 1
        
        loc, err = _resolve_location(item_id, location, conn, cursor)
        if err:
            print(f"✗ {err}")
            for loc in cursor.execute("SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?", (item_id,)).fetchall():
                print(f"  {loc[1]} × {loc[2]} [{loc[3]}]")
            conn.close()
            return 1
        
        update_location_status(conn, loc[0], location_status)
        print(f"✓ 位置「{loc[1]}」状态已更新为「{location_status}」")

    # ── 4. 位置日期变更（--purchase-date / --expiration-date）──────────────
    if purchase_date is not None or expiration_date is not None:
        loc, err = _resolve_location(item_id, location, conn, cursor)
        if err:
            print(f"✗ {err}")
            for loc in cursor.execute("SELECT id, location, quantity, location_status FROM item_locations WHERE item_id = ?", (item_id,)).fetchall():
                print(f"  {loc[1]} × {loc[2]} [{loc[3]}]")
            conn.close()
            return 1

        update_location_dates(conn, loc[0], purchase_date=purchase_date, expiration_date=expiration_date)
        if purchase_date is not None and expiration_date is not None:
            print(f"✓ 位置「{loc[1]}」日期已更新：购买{purchase_date}，过期{expiration_date}")
        elif purchase_date is not None:
            print(f"✓ 位置「{loc[1]}」购买日期已更新为「{purchase_date}」")
        elif expiration_date is not None:
            print(f"✓ 位置「{loc[1]}」过期日期已更新为「{expiration_date}」")

    # 5. 追加新位置（--add-location 系列，心愿 ID: 84）
    if add_location is not None:
        if add_location_status not in VALID_STATUSES:
            print(f"✗ 无效状态: {add_location_status}，有效值: {', '.join(VALID_STATUSES)}")
            conn.close()
            return 1
        # 检查同位置是否已存在（同一 item_id 不允许重复路径）
        cursor.execute(
            "SELECT id FROM item_locations WHERE item_id = ? AND location = ?",
            (item_id, add_location)
        )
        existing = cursor.fetchone()
        if existing:
            print(f"✗ 该物品在「{add_location}」已有位置记录（id={existing[0]}）")
            print(f"  如需修改该位置，请用 --location 指定；如需增加数量，请用 --plus")
            conn.close()
            return 1
        # 用 location_ops.add_location() 全名调用，避免与形参 add_location 命名冲突
        location_ops.add_location(
            conn, item_id, add_location,
            quantity=add_quantity, reason=add_reason,
            location_status=add_location_status,
            purchase_date=add_purchase_date,
            expiration_date=add_expiration_date
        )
        print(f"✓ 已追加新位置：{add_location} ×{add_quantity}[{add_location_status}]")
        if add_purchase_date or add_expiration_date:
            pd = add_purchase_date or "-"
            ed = add_expiration_date or "-"
            print(f"  日期: 购买{pd}，过期{ed}")

    # 6. 标签变更
    old_tags = get_tags(conn, item_id)
    if tags is not None:
        set_tags(conn, item_id, tags)

    # 6.5. 标签追加/删除（新增）★ ─────────────
    if add_tags:
        for tag in [t.strip() for t in add_tags.split(",") if t.strip()]:
            add_tag(conn, item_id, tag)
            print(f"  + tag: {tag}")

    if remove_tags:
        for tag in [t.strip() for t in remove_tags.split(",") if t.strip()]:
            remove_tag(conn, item_id, tag)
            print(f"  - tag: {tag}")

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


def list_items(location=None, status=None, category_id=None, owner=None,
              sort_by="name", limit=100):
    """按条件列出物品"""
    conn = get_conn()
    cursor = conn.cursor()
    _load_category_cache(conn)

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
    if category_id:
        clause, c_params = _category_in_clause(conn, category_id)
        conditions.append(clause)
        params.extend(c_params)
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

    cursor.execute("""
        SELECT i.*, c.name AS category_name
        FROM items i LEFT JOIN categories c ON i.category_id = c.id
        WHERE i.id = ?
    """, (item_id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 ID={item_id} 的物品")
        conn.close()
        return 1

    item = dict(row)
    tags_str = get_tags(conn, item_id)

    cursor.execute("""
        SELECT location, quantity, reason, location_status, purchase_date, expiration_date
        FROM item_locations
        WHERE item_id = ?
        ORDER BY id
    """, (item_id,))
    locations = cursor.fetchall()

    print(f"===== 物品详情 =====")
    print(f"ID:       {item['id']}")
    print(f"名称:     {item['name']}")
    print(f"分类:     {item['category_name'] or '(未分类)'}")

    if locations:
        print("位置分布：")
        for loc in locations:
            reason_str = f" - {loc['reason']}" if loc["reason"] else ""
            date_str = ""
            if loc["purchase_date"] or loc["expiration_date"]:
                pd = loc["purchase_date"] or "-"
                ed = loc["expiration_date"] or "-"
                date_str = f" | 购买:{pd} 过期:{ed}"
            print(f"  {loc['location']} × {loc['quantity']} [{loc['location_status']}]{reason_str}{date_str}")
    else:
        print("位置:     (未设置)")

    print(f"所有者:   {item['owner']}")
    total_qty = sum(loc["quantity"] for loc in locations) if locations else 0
    print(f"总数量:   {total_qty}")
    if item["purchase_price"]:
        print(f"购买价:   ¥{item['purchase_price']:.2f}")
    print(f"标签:     {tags_str or '(无)'}")
    print(f"备注:     {item['remark'] or '(无)'}")
    if item["photo"]:
        photo_path = get_photo_full_path(item["photo"])
        print(f"图片:     {item['photo']}")
        print(f"完整路径: {photo_path}")
    else:
        print(f"图片:     (无)")
    print(f"访问次数: {item['access_count']}")
    print(f"最后访问: {item['last_accessed_at'] or '从未'}")
    print(f"创建时间: {item['created_at']}")
    print(f"更新时间: {item['updated_at']}")

    _touch_item(conn, item_id)
    conn.commit()
    conn.close()
    return 0


# ── JSON 输出函数（供 Skill 层 HTML 生成用，不打印，只返回结构化数据）──



def _get_photo_base64(photo_relative_path):
    """读取照片文件并返回 base64 编码字符串，失败返回 None"""
    if not photo_relative_path:
        return None
    full_path = get_photo_full_path(photo_relative_path)
    if not full_path or not full_path.exists():
        return None
    try:
        with open(full_path, "rb") as f:
            data = f.read()
        import base64
        return base64.b64encode(data).decode("ascii")
    except Exception:
        return None


def _item_to_dict(row, conn):
    """将 items 行转 dict，并附加 tags 列表和 locations 列表"""
    item_id = row["id"]
    cursor = conn.cursor()
    cursor.execute("SELECT tag FROM item_tags WHERE item_id = ?", (item_id,))
    tags = [r["tag"] for r in cursor.fetchall()]
    cursor.execute("""
        SELECT location, quantity, reason, location_status,
               purchase_date, expiration_date, created_at, updated_at
        FROM item_locations WHERE item_id = ? ORDER BY id
    """, (item_id,))
    locations = [dict(r) for r in cursor.fetchall()]
    photo_b64 = _get_photo_base64(row["photo"]) if row["photo"] else None
    result = dict(row)
    result["tags"] = tags
    result["locations"] = locations
    result["photo_base64"] = photo_b64
    top_cache = _load_top_category_cache(conn)
    cid = row.get("category_id")
    result["top_category_id"] = top_cache.get(cid) if cid else None
    return result


def search_items_payload(name=None, category_id=None, location=None, tag=None, status=None,
                        limit=20, exact=False):
    """搜索物品，返回 items 列表（dict）"""
    conn = get_conn()
    cursor = conn.cursor()
    _load_category_cache(conn)
    query = "SELECT DISTINCT i.* FROM items i"
    params = []
    join_il = tag or location or status
    if join_il:
        query += " LEFT JOIN item_locations il ON i.id = il.item_id"
    if tag:
        query += " LEFT JOIN item_tags t ON i.id = t.item_id"
    conditions = []
    if name:
        conditions.append("i.name = ?" if exact else "i.name LIKE ?")
        params.append(name if exact else f"%{name}%")
    if category_id:
        clause, c_params = _category_in_clause(conn, category_id)
        conditions.append("i." + clause)
        params.extend(c_params)
    if location:
        conditions.append("(il.location LIKE ? OR il.location IS NULL)")
        params.append(f"%{location}%")
    if status:
        conditions.append("il.location_status = ?")
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
    items = [_item_to_dict(dict(r), conn) for r in rows]
    conn.close()
    return items


def item_detail_payload(item_id):
    """查看物品详情，返回 dict；不存在返回 None"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    item = _item_to_dict(dict(row), conn)
    _touch_item(conn, item_id)
    conn.commit()
    conn.close()
    return item


def list_items_payload(location=None, status=None, category_id=None, owner=None,
                      sort_by="name", limit=100):
    """列出物品，返回 items 列表（dict）"""
    conn = get_conn()
    cursor = conn.cursor()
    _load_category_cache(conn)
    conditions = []
    params = []
    if location:
        conditions.append("""
            EXISTS (SELECT 1 FROM item_locations il
                   WHERE il.item_id = items.id AND il.location LIKE ?)
        """)
        params.append(f"%{location}%")
    if status:
        conditions.append("""
            EXISTS (SELECT 1 FROM item_locations il
                   WHERE il.item_id = items.id AND il.location_status = ?)
        """)
        params.append(status)
    if category_id:
        clause, c_params = _category_in_clause(conn, category_id)
        conditions.append(clause)
        params.extend(c_params)
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
    items = [_item_to_dict(dict(r), conn) for r in rows]
    conn.close()
    return items


def search_items_json(name=None, category_id=None, location=None, tag=None, status=None,
                     limit=20, exact=False):
    """搜索物品，输出 JSON 到 stdout"""
    import json
    print(json.dumps(search_items_payload(name, category_id, location, tag, status, limit, exact), ensure_ascii=False))
    return 0


def item_detail_json(item_id):
    """查看物品详情，输出 JSON 到 stdout"""
    item = item_detail_payload(item_id)
    import json
    if not item:
        print(json.dumps({"error": f"未找到 ID={item_id} 的物品"}, ensure_ascii=False))
        return 1
    print(json.dumps(item, ensure_ascii=False))
    return 0


def list_items_json(location=None, status=None, category_id=None, owner=None,
                   sort_by="name", limit=100):
    """列出物品，输出 JSON 到 stdout"""
    import json
    print(json.dumps(list_items_payload(location, status, category_id, owner, sort_by, limit), ensure_ascii=False))
    return 0
