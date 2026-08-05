# ops.py - SM5 快递购物域业务逻辑(购物清单/缺货检测/快递跟踪/囤货盘点)
#
# 规格: .scratch/v2.0-spec-map/scenes/SM5-快递购物.md(2026-08-04 定稿)
# 设计要点:
#   - 采购闭环/收货闭环 = 联动既有流程(1-1 录入 / 3-3 数量 / 状态变更),不造新流程
#   - 写路径原子性: 数据变更 + item_events 事件写入同一 conn/事务(记录契约 · D1 #103)
#   - 阈值: stock_thresholds 为缺货检测的阈值数据源;未设置 → DEFAULT_THRESHOLD 估算+标注
#   - 例行采购: 到期(超过周期未买)→ 查看时自动重新激活为待买 + 顺路提醒
#   - 快递跟踪: 复用 item_locations.location_status='快递中',不建新表
import json

from . import schema
from 物品 import events as item_events
from home_manager.item_ops import _get_photo_base64


# ── 通用查询助手 ────────────────────────────────────────────────────────────


def _expand_category_ids(conn, cat_id):
    """从 cat_id 出发,递归查所有下级 id(包含自身)"""
    cursor = conn.cursor()
    cursor.execute("""
        WITH RECURSIVE cat_tree AS (
            SELECT id FROM categories WHERE id = ?
            UNION ALL
            SELECT c.id FROM categories c JOIN cat_tree t ON c.parent_id = t.id
        )
        SELECT id FROM cat_tree
    """, (cat_id,))
    return [r["id"] for r in cursor.fetchall()]


def _item_available_qty(conn, item_id):
    """当前库存(在家+备用 数量合计;规格: 快递中未收到不算在库)"""
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(schema.STOCK_STATUSES))
    cursor.execute(
        f"SELECT COALESCE(SUM(quantity), 0) AS qty FROM item_locations "
        f"WHERE item_id = ? AND location_status IN ({placeholders})",
        (item_id, *schema.STOCK_STATUSES),
    )
    return cursor.fetchone()["qty"]


def _item_threshold(conn, item_id):
    """阈值: 读 stock_thresholds(囤货设置);未设置返回 None"""
    cursor = conn.cursor()
    cursor.execute("SELECT threshold FROM stock_thresholds WHERE item_id = ?", (item_id,))
    row = cursor.fetchone()
    return row["threshold"] if row else None


def _stock_meta(current, threshold):
    """库存状态与建议量(实施环节细化决策):
      空   = 当前 0
      低   = 0 < 当前 < 阈值
      充足 = 当前 ≥ 阈值
      建议量 = max(2×阈值 − 当前, 1)(采购后保有 2 倍阈值的缓冲)
    """
    if current <= 0:
        status = schema.STOCK_EMPTY
    elif current < threshold:
        status = schema.STOCK_LOW
    else:
        status = schema.STOCK_FULL
    suggest = max(2 * threshold - current, 1)
    return status, suggest


# ── 购物清单(SM5-1)──────────────────────────────────────────────────────────


def list_add(conn, name, quantity=1, source=schema.SOURCE_MANUAL,
             routine=None, note=""):
    """添加清单条目。清单内查重: 同名「待买」条目已存在 → 抛 ValueError(提示合并)"""
    schema.ensure_tables(conn)
    name = (name or "").strip()
    if not name:
        raise ValueError("条目名称不能为空")
    if quantity < 1:
        raise ValueError(f"数量必须 ≥ 1 (当前 {quantity})")
    if routine and routine not in schema.ROUTINE_CYCLE_DAYS:
        raise ValueError(f"例行周期只能是 {'/'.join(schema.ROUTINE_CYCLE_DAYS)} (当前 {routine!r})")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM shopping_items WHERE name = ? AND status = ?",
                   (name, schema.STATUS_PENDING))
    dup = cursor.fetchone()
    if dup:
        raise ValueError(f"「{name}」已在购物清单中(条目 id={dup['id']}),勿重复添加,可改数量")
    occurred = schema.now_str()
    cursor.execute(
        "INSERT INTO shopping_items (name, quantity, source, routine, status, note, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (name, quantity, source, routine, schema.STATUS_PENDING, note, occurred, occurred),
    )
    conn.commit()
    return cursor.lastrowid


def _reactivate_routine(conn):
    """例行采购计划: 到期(超过周期未买)的例行条目重新激活为待买,返回到期列表"""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shopping_items WHERE routine IS NOT NULL AND status = ?",
                   (schema.STATUS_DONE,))
    due = []
    occurred = schema.now_str()
    for row in cursor.fetchall():
        cycle = schema.ROUTINE_CYCLE_DAYS.get(row["routine"])
        if not cycle:
            continue
        last = row["last_done_at"] or row["updated_at"]
        cursor.execute(
            "SELECT CAST(julianday(?) - julianday(?) AS INTEGER) AS days", (occurred, last))
        days = cursor.fetchone()["days"]
        if days is None or days >= cycle:
            cursor.execute(
                "UPDATE shopping_items SET status = ?, updated_at = ? WHERE id = ?",
                (schema.STATUS_PENDING, occurred, row["id"]),
            )
            due.append({"id": row["id"], "name": row["name"], "routine": row["routine"]})
    if due:
        conn.commit()
    return due


def list_view(conn):
    """购物清单视图(未写入状态变化前的纯查询,例行激活为副作用返回到期列表)"""
    schema.ensure_tables(conn)
    routine_due = _reactivate_routine(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM shopping_items WHERE status = ? ORDER BY id
    """, (schema.STATUS_PENDING,))
    items = [dict(r) for r in cursor.fetchall()]

    dupes = []
    seen = {}
    for it in items:
        if it["name"] in seen:
            dupes.append(it["name"])
        else:
            seen[it["name"]] = True
    return {
        "routine_due": routine_due,
        "dupes": sorted(set(dupes)),
        "items": items,
    }


def list_check(conn, ids):
    """销项(已买): 勾选 → 标记已买。例行条目记 last_done_at(周期从此时重算)"""
    schema.ensure_tables(conn)
    if not ids:
        raise ValueError("未选择任何条目(ids 为空)")
    occurred = schema.now_str()
    cursor = conn.cursor()
    done = 0
    for iid in ids:
        cursor.execute("SELECT * FROM shopping_items WHERE id = ?", (iid,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"条目 {iid} 不存在")
        if row["status"] == schema.STATUS_DONE:
            continue
        cursor.execute(
            "UPDATE shopping_items SET status = ?, last_done_at = ?, updated_at = ? WHERE id = ?",
            (schema.STATUS_DONE, occurred, occurred, iid),
        )
        done += 1
    conn.commit()
    return done


# ── 缺货检测(SM5-2)──────────────────────────────────────────────────────────


def _detect_items(conn, category_id=None):
    """缺货候选: 全屋/分类范围内全部物品 + 当前库存 + 阈值(设置或默认) + 库存状态

    返回 [(item, current, threshold, threshold_source, status, suggest), ...]
    阈值来源: 囤货设置 / 默认(规格「阈值未设置物品 → 按默认阈值估算+标注」)
    """
    cursor = conn.cursor()
    params = []
    where = ""
    if category_id:
        ids = _expand_category_ids(conn, category_id)
        if len(ids) == 1:
            where = "WHERE i.category_id = ?"
            params.append(ids[0])
        else:
            placeholders = ",".join("?" * len(ids))
            where = f"WHERE i.category_id IN ({placeholders})"
            params.extend(ids)
    cursor.execute(f"""
        SELECT i.id, i.name, c.name AS category_name
        FROM items i LEFT JOIN categories c ON i.category_id = c.id
        {where}
        ORDER BY c.name, i.name
    """, params)
    rows = cursor.fetchall()
    out = []
    for r in rows:
        current = _item_available_qty(conn, r["id"])
        threshold = _item_threshold(conn, r["id"])
        if threshold is None:
            threshold = schema.DEFAULT_THRESHOLD
            t_source = "默认"
        else:
            t_source = "囤货设置"
        status, suggest = _stock_meta(current, threshold)
        if status == schema.STOCK_FULL:
            continue
        out.append({
            "id": r["id"], "name": r["name"], "category_name": r["category_name"] or "(未分类)",
            "current": current, "threshold": threshold, "threshold_source": t_source,
            "status": status, "suggest": suggest,
        })
    return out


def missing_detect(conn, category_id=None):
    """缺货检测结果(规格: 物品+当前数量+阈值+建议量「当前 0/阈值 1/建议买 2」)"""
    schema.ensure_tables(conn)
    items = _detect_items(conn, category_id)
    return {
        "scope": "全屋" if not category_id else f"分类 id={category_id}",
        "items": items,
        "threshold_default": schema.DEFAULT_THRESHOLD,
    }


def missing_to_list(conn, ids):
    """一键进清单: 缺货物品 → 购物清单(来源=缺货检测,数量=建议量)

    与清单内查重联动: 已在待买清单的同名条目跳过,返回 dup_skips 供提示合并。
    返回 {added: int, dup_skips: [name]}
    """
    schema.ensure_tables(conn)
    if not ids:
        raise ValueError("未选择任何缺货物品(ids 为空)")
    added = 0
    dup_skips = []
    cursor = conn.cursor()
    for iid in ids:
        cursor.execute("SELECT name FROM items WHERE id = ?", (iid,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"物品 {iid} 不存在")
        name = row["name"]
        cursor.execute("SELECT id FROM shopping_items WHERE name = ? AND status = ?",
                       (name, schema.STATUS_PENDING))
        if cursor.fetchone():
            dup_skips.append(name)
            continue
        items = _detect_items(conn)
        match = next((it for it in items if it["id"] == iid), None)
        qty = match["suggest"] if match else schema.DEFAULT_THRESHOLD
        occurred = schema.now_str()
        cursor.execute(
            "INSERT INTO shopping_items (name, quantity, source, status, note, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, qty, schema.SOURCE_MISSING, schema.STATUS_PENDING,
             f"缺货检测自动加入 · 当前 {match['current'] if match else '-'}/阈值 "
             f"{match['threshold'] if match else schema.DEFAULT_THRESHOLD}",
             occurred, occurred),
        )
        added += 1
    conn.commit()
    return {"added": added, "dup_skips": dup_skips}


# ── 快递跟踪(SM5-3)──────────────────────────────────────────────────────────


def express_view(conn, timeout_days=schema.DEFAULT_TIMEOUT_DAYS):
    """快递中物品清单(照片+名称+数量+「快递中」+已等 N 天)+ 超时判定"""
    schema.ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.id, i.name, i.photo, c.name AS category_name,
               il.id AS location_id, il.location, il.quantity, il.created_at
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE il.location_status = '快递中'
        ORDER BY il.created_at ASC
    """)
    items = []
    for r in cursor.fetchall():
        days = 0
        if r["created_at"]:
            cursor.execute(
                "SELECT CAST(julianday('now') - julianday(?) AS INTEGER) AS d",
                (r["created_at"],))
            days = max(cursor.fetchone()["d"], 0)
        items.append({
            "id": r["id"], "name": r["name"], "photo": r["photo"],
            "photo_base64": _get_photo_base64(r["photo"]),
            "category_name": r["category_name"] or "(未分类)",
            "location_id": r["location_id"], "location": r["location"],
            "quantity": r["quantity"], "days": days,
            "overdue": days > timeout_days,
        })
    return {"items": items, "timeout_days": timeout_days}


def express_receive(conn, item_id, to_status="在家", location_id=None):
    """确认收货: 快递中 → 在家/备用(状态变更),写 item_events 状态事件

    规格: 收货确认 = 状态变更(快递中→在家/备用)+ 可选录入新物品(1-1,不在本命令)
    """
    if to_status not in ("在家", "备用"):
        raise ValueError(f"收货后状态只能是 在家/备用 (当前 {to_status!r})")
    cursor = conn.cursor()
    if location_id:
        cursor.execute(
            "SELECT * FROM item_locations WHERE id = ? AND item_id = ? AND location_status = '快递中'",
            (location_id, item_id))
        loc = cursor.fetchone()
    else:
        cursor.execute(
            "SELECT * FROM item_locations WHERE item_id = ? AND location_status = '快递中' "
            "ORDER BY id DESC LIMIT 1",
            (item_id,))
        loc = cursor.fetchone()
    if not loc:
        raise ValueError(f"物品 {item_id} 没有「快递中」的位置记录,无需确认收货")
    before = {"location_status": loc["location_status"]}
    after = {"location_status": to_status}
    occurred = schema.now_str()
    cursor.execute(
        "UPDATE item_locations SET location_status = ?, updated_at = ? WHERE id = ?",
        (to_status, occurred, loc["id"]),
    )
    item_events.record_event(
        conn, item_id, item_events.EVENT_STATUS_CHANGED,
        f"确认收货:{loc['location']} 快递中 → {to_status}",
        payload=item_events.diff_payload(before, after),
        scene_id="SM5-3",
        cli_cmd=f"python scripts/快递购物/cli.py express-receive --id {item_id} --to {to_status}",
    )
    conn.commit()
    return {"location_id": loc["id"], "location": loc["location"],
            "to_status": to_status, "item_id": item_id}


# ── 囤货盘点(SM5-4)──────────────────────────────────────────────────────────


def stock_set_threshold(conn, item_id, threshold):
    """阈值设置(囤货盘点的阈值数据源 · 采集组件落地)"""
    schema.ensure_tables(conn)
    if threshold < 1:
        raise ValueError(f"阈值必须 ≥ 1 (当前 {threshold})")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM items WHERE id = ?", (item_id,))
    if not cursor.fetchone():
        raise ValueError(f"物品 {item_id} 不存在")
    occurred = schema.now_str()
    cursor.execute("""
        INSERT INTO stock_thresholds (item_id, threshold, updated_at) VALUES (?, ?, ?)
        ON CONFLICT(item_id) DO UPDATE SET threshold = excluded.threshold, updated_at = excluded.updated_at
    """, (item_id, threshold, occurred))
    conn.commit()
    return item_id


def _locate_stock_location(conn, item_id, location=None):
    """定位库存位置(在家/备用): 唯一 → 直接用;多个 → 必须 --location 指定"""
    cursor = conn.cursor()
    placeholders = ",".join("?" * len(schema.STOCK_STATUSES))
    if location:
        cursor.execute(
            f"SELECT * FROM item_locations WHERE item_id = ? AND location = ? "
            f"AND location_status IN ({placeholders})",
            (item_id, location, *schema.STOCK_STATUSES))
    else:
        cursor.execute(
            f"SELECT * FROM item_locations WHERE item_id = ? AND location_status IN ({placeholders}) "
            f"ORDER BY id",
            (item_id, *schema.STOCK_STATUSES))
    rows = cursor.fetchall()
    if not rows:
        return None, None
    if len(rows) == 1 or location:
        return rows[0], None
    locs = "、".join(f"{r['location']}×{r['quantity']}" for r in rows)
    return None, f"物品有 {len(rows)} 个库存位置,请用 --location 指定:{locs}"


def stock_fix(conn, item_id, quantity, location=None):
    """盘点修正(实际数量与系统不符 → 修正,联动 3-3),写数量变更事件"""
    schema.ensure_tables(conn)
    if quantity < 0:
        raise ValueError(f"修正数量必须 ≥ 0 (当前 {quantity})")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"物品 {item_id} 不存在")
    loc, err = _locate_stock_location(conn, item_id, location)
    if err:
        raise ValueError(err)
    if loc is None:
        raise ValueError(f"物品 {item_id} 没有「在家/备用」库存位置,请先录入或收货")
    before = {"quantity": loc["quantity"]}
    after = {"quantity": quantity}
    occurred = schema.now_str()
    if quantity == 0:
        cursor.execute("DELETE FROM item_locations WHERE id = ?", (loc["id"],))
    else:
        cursor.execute(
            "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
            (quantity, occurred, loc["id"]),
        )
    item_events.record_event(
        conn, item_id, item_events.EVENT_QUANTITY_CHANGED,
        f"囤货修正:{loc['location']} {loc['quantity']} → {quantity}",
        payload=item_events.diff_payload(before, after),
        scene_id="SM5-4",
        cli_cmd=f"python scripts/快递购物/cli.py stock-fix --id {item_id} --quantity {quantity}",
    )
    conn.commit()
    return {"location_id": loc["id"], "location": loc["location"],
            "quantity": quantity, "item_id": item_id}


def stock_view(conn, hint_limit=10):
    """囤货盘点视图: 有阈值物品(名称+当前数量+阈值+库存状态)+ 无阈值常用品提示"""
    schema.ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT st.item_id, st.threshold, i.name, c.name AS category_name
        FROM stock_thresholds st
        JOIN items i ON i.id = st.item_id
        LEFT JOIN categories c ON i.category_id = c.id
        ORDER BY st.threshold DESC, i.name
    """)
    items = []
    for r in cursor.fetchall():
        current = _item_available_qty(conn, r["item_id"])
        status, _ = _stock_meta(current, r["threshold"])
        items.append({
            "id": r["item_id"], "name": r["name"],
            "category_name": r["category_name"] or "(未分类)",
            "current": current, "threshold": r["threshold"], "status": status,
        })
    # 空态引导: 无阈值但使用频率最高的物品(为常用物品设阈值)
    cursor.execute("""
        SELECT i.id, i.name, c.name AS category_name
        FROM items i
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE NOT EXISTS (SELECT 1 FROM stock_thresholds st WHERE st.item_id = i.id)
        ORDER BY i.access_count DESC LIMIT ?
    """, (hint_limit,))
    hints = [
        {"id": r["id"], "name": r["name"],
         "category_name": r["category_name"] or "(未分类)"}
        for r in cursor.fetchall()
    ]
    return {"items": items, "hints": hints}
