# ops.py - SM1 物品管理域 · 29 场景业务操作(payload 生成 + 写库 + 记录契约)
#
# 口径: SM1 权威清单(2026-08-04 定稿)· 08-HTML 交互规范 v1 · D1 记录契约
# 依赖: scripts/home_manager/{db,item_ops,location_ops,tag_ops} 只读调用(公共层)
# 所有写操作: 数据变更 + item_events 同一事务(记录契约 #1 原子性)
import json
from datetime import datetime

from home_manager.db import get_conn, PHOTOS_DIR
from home_manager.item_ops import (
    _item_to_dict, _get_photo_base64, _load_top_category_cache,
    _category_in_clause, get_photo_full_path,
)
from home_manager.location_ops import add_location, _locations_str
from home_manager.tag_ops import get_tags, set_tags, add_tag, remove_tag

from . import events as ev
from .validators import validate_draft, check_status_transition, STATUSES

# 废弃(软删除)默认隐藏
DISCARDED_STATUS = "已废弃"


# ── 基础助手 ────────────────────────────────────────────────────────────────


def _conn():
    conn = get_conn()
    ev.ensure_tables(conn)
    return conn


def _cat_name(conn, category_id):
    if not category_id:
        return ""
    row = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    return row["name"] if row else ""


def _item_card(row, conn):
    """物品卡片 dict(照片/名称/位置/状态/数量/标签/分类)"""
    item_id = row["id"]
    cur = conn.execute(
        "SELECT location, quantity, location_status, purchase_date, expiration_date "
        "FROM item_locations WHERE item_id = ? ORDER BY id", (item_id,)
    ).fetchall()
    locations = [dict(r) for r in cur]
    status = (locations[0]["location_status"] if locations else "在家") or "在家"
    total_qty = sum((l["quantity"] or 0) for l in locations)
    tags = conn.execute(
        "SELECT tag FROM item_tags WHERE item_id = ? ORDER BY tag", (item_id,)
    ).fetchall()
    photos = ev.get_photos(conn, item_id)
    main_photo = photos[0]["file_path"] if photos else (row["photo"] or "")
    return {
        "id": item_id,
        "name": row["name"],
        "category_id": row["category_id"],
        "category_name": _cat_name(conn, row["category_id"]) or "(未分类)",
        "locations": locations,
        "location": locations[0]["location"] if locations else "",
        "status": status,
        "quantity": total_qty,
        "tags": [t["tag"] for t in tags],
        "photo": main_photo,
        "photo_base64": _get_photo_base64(main_photo),
        "remark": row["remark"] or "",
        "purchase_price": row["purchase_price"],
        "access_count": row["access_count"] or 0,
        "last_accessed_at": row["last_accessed_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _find_item(conn, item_id):
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def _default_status(location):
    """录入状态推断(定稿细节 7): 快递 → 快递中;无法推断 → 在家"""
    if location and "快递" in location:
        return "快递中"
    return "在家"


def _loc_row(conn, item_id, location=None):
    rows = conn.execute(
        "SELECT * FROM item_locations WHERE item_id = ? ORDER BY id", (item_id,)
    ).fetchall()
    if not rows:
        return None
    if location:
        for r in rows:
            if r["location"] == location:
                return dict(r)
        return None
    return dict(rows[0])


# ── 子功能 1 · 录入 ─────────────────────────────────────────────────────────


def similar_items_check(name, category_id=None, exclude_ids=None, limit=5):
    """同款检测(1-1/1-2: 同名/同分类已有 N 件,合并 or 新建)

    返回 [{id, name, category_name, location, quantity, status}]
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM items WHERE name = ? AND id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?)",
            (name, DISCARDED_STATUS),
        ).fetchall()
        if not rows and category_id:
            rows = conn.execute(
                "SELECT * FROM items WHERE category_id = ? AND id NOT IN "
                "(SELECT item_id FROM item_locations WHERE location_status = ?) LIMIT ?",
                (category_id, DISCARDED_STATUS, limit),
            ).fetchall()
        exclude_ids = exclude_ids or []
        return [_item_card(dict(r), conn) for r in rows if r["id"] not in exclude_ids][:limit]
    finally:
        conn.close()


def suggest_locations_for(name, category_id, limit=6):
    """位置建议(1-1: 该分类常用位置)"""
    conn = _conn()
    try:
        from home_manager.location_ops import suggest_locations_with_examples
        return suggest_locations_with_examples(conn, category_id, limit=limit)
    finally:
        conn.close()


def add_item_v2(draft, event_type=ev.EVENT_CREATED, scene_id=None, cli_cmd=None):
    """规格口径录入(1-1/1-4: 名称+分类必填,位置可选)

    写库 + item_events 原子写入。返回 (ok, message, item_id)
    """
    conn = _conn()
    try:
        checks, missing = validate_draft(draft, conn)
        if not checks["has_name"] or not checks["has_category"]:
            return False, "还缺:" + "/".join(missing), None
        if not checks["location_ok"] or not checks["price_ok"] or not checks["date_ok"]:
            return False, "校验不过:" + "/".join(missing), None

        name = (draft.get("name") or "").strip()
        category_id = int(draft["category_id"])
        location = (draft.get("location") or "").strip() or None
        owner = draft.get("owner") or "使用者"
        quantity = int(draft.get("quantity") or 1)
        price = draft.get("price")
        price = float(price) if price not in (None, "") else None
        remark = draft.get("remark") or ""
        tags = draft.get("tags") or ""
        photo = draft.get("photo") or ""
        location_status = draft.get("location_status") or _default_status(location)
        purchase_date = draft.get("purchase_date") or None
        expiration_date = draft.get("expiration_date") or None
        backfill_date = draft.get("backfill_date")  # 1-4 补录日期(录入/购买日期回显)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 照片先校验(与 add_item 同契约)
        if photo:
            photos_dir = str(PHOTOS_DIR)
            if not photo.startswith(photos_dir):
                return False, f"照片路径必须放在 {photos_dir} 下,当前 {photo}", None
            photo = photo[len(photos_dir):].lstrip("\\/")

        cursor = conn.cursor()
        created_at = backfill_date if backfill_date else now
        cursor.execute(
            "INSERT INTO items (name, category_id, owner, purchase_price, remark, photo, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (name, category_id, owner, price, remark, photo, created_at, now),
        )
        item_id = cursor.lastrowid

        if location:
            add_location(conn, item_id, location, quantity,
                         location_status=location_status,
                         purchase_date=purchase_date,
                         expiration_date=expiration_date)
        elif quantity:
            add_location(conn, item_id, "待定", quantity,
                         location_status=location_status,
                         purchase_date=purchase_date,
                         expiration_date=expiration_date)
        set_tags(conn, item_id, tags)

        ev.record_event(conn, item_id, event_type,
                        f"录入物品「{name}」×{quantity}[{location_status}]",
                        payload={"before": {}, "after": {"name": name, "category_id": category_id,
                                                         "location": location, "quantity": quantity}},
                        scene_id=scene_id, cli_cmd=cli_cmd)
        conn.commit()
        return True, f"已录入「{name}」×{quantity}", item_id
    finally:
        conn.close()


def add_batch_payload(drafts):
    """批量录入预览(1-3): 批内重复检测 + 库内重复检测 + 分类分布

    drafts: [{name, category_id, quantity, location, tags, remark, price, ...}]
    返回 payload data(前端逐条采集表单组件 + 勾选确认)
    """
    conn = _conn()
    try:
        items = []
        for i, d in enumerate(drafts, 1):
            similar = similar_items_check(d.get("name"), d.get("category_id"))
            checks, missing = validate_draft(d, conn)
            items.append({
                "seq": i,
                "draft": d,
                "checks": checks,
                "missing": missing,
                "similar": similar,
                "batch_dup": None,  # 由下面批内检测填充
            })
        # 批内重复(同名)
        names = [d.get("name", "").strip() for d in drafts]
        for it in items:
            dup = [j for j, n in enumerate(names, 1) if n == it["draft"].get("name", "").strip() and j != it["seq"]]
            it["batch_dup"] = dup or None
        # 分类分布
        from collections import Counter
        dist = Counter(_cat_name(conn, d.get("category_id")) or "(未分类)" for d in drafts)
        return {
            "total": len(items),
            "items": items,
            "category_dist": [{"name": k, "count": v} for k, v in dist.items()],
        }
    finally:
        conn.close()


def add_batch_commit(drafts, cli_cmd=None):
    """批量录入写库(1-3): 每条独立事件,共用 scene_id(批量归组)"""
    scene_id = f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    results = []
    for d in drafts:
        ok, msg, item_id = add_item_v2(d, event_type=ev.EVENT_BATCH_CREATED,
                                       scene_id=scene_id, cli_cmd=cli_cmd)
        results.append({"ok": ok, "message": msg, "item_id": item_id, "draft": d})
    ok_count = sum(1 for r in results if r["ok"])
    return {"ok": ok_count == len(results),
            "message": f"批量录入完成:{ok_count}/{len(results)} 件成功",
            "results": results}


# ── 子功能 2 · 查找 ─────────────────────────────────────────────────────────


def search_payload_v2(name=None, category_id=None, location=None, tag=None,
                      status=None, price_min=None, price_max=None,
                      include_discarded=False, sort="relevance", limit=50,
                      match_keywords=None):
    """语义搜索(2-1): 命中列表 + 匹配依据 + 相关性排序

    match_keywords: AI 解析出的关键词列表(前端展示匹配依据)
    软删除默认隐藏(include_discarded=False)
    """
    conn = _conn()
    try:
        conditions, params = [], []
        joins = []
        if not include_discarded:
            conditions.append("i.id NOT IN (SELECT item_id FROM item_locations WHERE location_status = ?)")
            params.append(DISCARDED_STATUS)
        if name:
            conditions.append("(i.name LIKE ? OR i.remark LIKE ?)")
            params += [f"%{name}%", f"%{name}%"]
        if category_id:
            clause, c_params = _category_in_clause(conn, category_id)
            conditions.append("i." + clause)
            params.extend(c_params)
        if location:
            joins.append("LEFT JOIN item_locations il ON i.id = il.item_id")
            conditions.append("il.location LIKE ?")
            params.append(f"%{location}%")
        if tag:
            joins.append("LEFT JOIN item_tags t ON i.id = t.item_id")
            conditions.append("t.tag = ?")
            params.append(tag)
        if status:
            joins.append("LEFT JOIN item_locations il2 ON i.id = il2.item_id")
            conditions.append("il2.location_status = ?")
            params.append(status)
        if price_min is not None:
            conditions.append("i.purchase_price >= ?")
            params.append(price_min)
        if price_max is not None:
            conditions.append("i.purchase_price <= ?")
            params.append(price_max)

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = ("SELECT DISTINCT i.* FROM items i " + " ".join(set(joins)) + where)
        order = {
            "relevance": "i.access_count DESC, i.updated_at DESC",
            "name": "i.name ASC",
            "recent": "i.created_at DESC",
            "price": "i.purchase_price ASC",
            "price_desc": "i.purchase_price DESC",
        }.get(sort, "i.access_count DESC")
        sql += f" ORDER BY {order} LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        cards = [_item_card(dict(r), conn) for r in rows]

        # 匹配依据: 名称命中 / 位置命中 / 标签命中 / 备注命中
        kw = [k for k in (match_keywords or [name] if name else match_keywords or []) if k]
        for c in cards:
            reasons = []
            if name and (name in c["name"] or name.lower() in c["name"].lower()):
                reasons.append("名称")
            if kw:
                for k in kw:
                    if k and k in c["name"]:
                        reasons.append(f"含关键词「{k}」")
            if location and location in c["location"]:
                reasons.append("位置")
            if tag and tag in c["tags"]:
                reasons.append("标签")
            c["reasons"] = reasons or ["相关"]
        return {"summary": {"title": "查物品结果", "metrics": [{"label": "命中", "value": f"{len(cards)} 件"}]},
                "items": cards, "include_discarded": include_discarded}
    finally:
        conn.close()


def detail_payload_v2(item_id):
    """物品详情(2-2): 全字段 + 同位置邻居 + 相似物品 + 关联 + 照片 + 历史入口"""
    conn = _conn()
    try:
        row = _find_item(conn, item_id)
        if not row:
            return None
        card = _item_card(row, conn)
        # 同位置邻居
        loc = card["location"]
        neighbors = []
        if loc:
            rows = conn.execute(
                "SELECT DISTINCT i.* FROM items i JOIN item_locations il ON i.id = il.item_id "
                "WHERE il.location = ? AND i.id != ? AND il.location_status != ? LIMIT 8",
                (loc, item_id, DISCARDED_STATUS),
            ).fetchall()
            neighbors = [_item_card(dict(r), conn) for r in rows]
        # 相似物品(同分类)
        similar = []
        if card["category_id"]:
            rows = conn.execute(
                "SELECT * FROM items WHERE category_id = ? AND id != ? AND id NOT IN "
                "(SELECT item_id FROM item_locations WHERE location_status = ?) LIMIT 6",
                (card["category_id"], item_id, DISCARDED_STATUS),
            ).fetchall()
            similar = [_item_card(dict(r), conn) for r in rows]
        relations = ev.get_relations(conn, item_id)
        photos = ev.get_photos(conn, item_id)
        history = ev.query_item_events(conn, item_id, limit=30)
        return {
            "item": card,
            "neighbors": neighbors,
            "similar": similar,
            "relations": relations,
            "photos": photos,
            "history": history,
            "last_used": row["last_accessed_at"],
        }
    finally:
        conn.close()


def locate_payload_v2(name):
    """紧急定位(2-3): 一屏直达只要位置

    重要物品 = 访问频次高的常用件(固定位机制联动 SM2,实施期用 access_count 近似)
    超时警告 = 距最后使用/录入超 30 天
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM items WHERE name LIKE ? AND id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?) LIMIT 10",
            (f"%{name}%", DISCARDED_STATUS),
        ).fetchall()
        cards = [_item_card(dict(r), conn) for r in rows]
        cards.sort(key=lambda c: -c["access_count"])
        from datetime import datetime as dt
        today = dt.now()
        for c in cards:
            last = c["last_accessed_at"] or c["created_at"]
            try:
                days = (today - dt.strptime(last[:10], "%Y-%m-%d")).days
            except (ValueError, TypeError):
                days = 0
            c["idle_days"] = max(0, days)
        return {"items": cards, "query": name}
    finally:
        conn.close()


def browse_payload_v2(group_by=None, category_id=None, location=None, tag=None,
                      price_min=None, price_max=None, sort="name",
                      include_discarded=False, limit=200):
    """筛选浏览(2-4): 分组列表 + 多条件组合 + 排序 + 计数"""
    conn = _conn()
    try:
        conditions, params = [], []
        if not include_discarded:
            conditions.append("i.id NOT IN (SELECT item_id FROM item_locations WHERE location_status = ?)")
            params.append(DISCARDED_STATUS)
        if category_id:
            clause, c_params = _category_in_clause(conn, category_id)
            conditions.append("i." + clause)
            params.extend(c_params)
        if location:
            conditions.append("EXISTS (SELECT 1 FROM item_locations il WHERE il.item_id = i.id AND il.location LIKE ?)")
            params.append(f"%{location}%")
        if tag:
            conditions.append("EXISTS (SELECT 1 FROM item_tags t WHERE t.item_id = i.id AND t.tag = ?)")
            params.append(tag)
        if price_min is not None:
            conditions.append("i.purchase_price >= ?")
            params.append(price_min)
        if price_max is not None:
            conditions.append("i.purchase_price <= ?")
            params.append(price_max)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        order = {"name": "i.name ASC", "recent": "i.created_at DESC",
                 "price": "i.purchase_price ASC"}.get(sort, "i.name ASC")
        rows = conn.execute(f"SELECT DISTINCT i.* FROM items i{where} ORDER BY {order} LIMIT ?",
                            params + [limit]).fetchall()
        cards = [_item_card(dict(r), conn) for r in rows]

        group_key = group_by or "category"
        groups = {}
        for c in cards:
            if group_key == "location":
                g = c["location"] or "(未设置)"
            elif group_key == "status":
                g = c["status"]
            elif group_key == "tags":
                g = c["tags"][0] if c["tags"] else "(无标签)"
            else:
                g = c["category_name"]
            groups.setdefault(g, []).append(c)
        ordered = [{"name": g, "items": items} for g, items in sorted(groups.items())]
        return {"summary": {"title": "筛选浏览", "metrics": [
                    {"label": "共", "value": f"{len(cards)} 件"},
                    {"label": "分组", "value": f"{len(ordered)} 组"}]},
                "group_by": group_key, "groups": ordered, "items": cards}
    finally:
        conn.close()


def duplicates_payload_v2():
    """查重复(2-6): 同名物品组(名称/分类/数量/位置对比)"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT name, COUNT(*) AS n FROM items WHERE id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?) "
            "GROUP BY name HAVING n > 1 ORDER BY n DESC",
            (DISCARDED_STATUS,),
        ).fetchall()
        groups = []
        for r in rows:
            items = conn.execute(
                "SELECT * FROM items WHERE name = ? AND id NOT IN "
                "(SELECT item_id FROM item_locations WHERE location_status = ?) ORDER BY id",
                (r["name"], DISCARDED_STATUS),
            ).fetchall()
            groups.append({
                "name": r["name"],
                "count": r["n"],
                "items": [_item_card(dict(x), conn) for x in items],
            })
        return {"groups": groups, "total_duplicate_items": sum(g["count"] for g in groups),
                "group_count": len(groups)}
    finally:
        conn.close()


# ── 子功能 3 · 更新 ─────────────────────────────────────────────────────────


def update_item_v2(item_id, fields, cli_cmd=None):
    """修改物品信息(3-1): 字段级 before→after + 事件

    fields: {name/category_id/owner/remark/purchase_price/purchase_date/expiration_date}
    返回 (ok, message, payload)
    """
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        before = {k: cur[k] for k in ("name", "category_id", "owner", "remark", "purchase_price")}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates, params = [], []
        for k, v in fields.items():
            if v is None:
                continue
            if k == "category_id":
                if conn.execute("SELECT id FROM categories WHERE id = ? AND is_active = 1", (v,)).fetchone() is None:
                    return False, f"分类 {v} 不存在或未激活", None
            updates.append(f"{k} = ?")
            params.append(v)
        if not updates:
            return False, "没有要修改的字段", None
        updates.append("updated_at = ?")
        params.append(now)
        params.append(item_id)
        conn.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)

        after = _find_item(conn, item_id)
        after_slim = {k: after[k] for k in before}
        diff = {k: v for k, v in after_slim.items() if before[k] != v}
        summary = f"修改物品「{after['name']}」: " + ", ".join(f"{k}:{before[k]}→{after_slim[k]}" for k in diff) if diff else f"修改物品「{after['name']}」(无字段变化)"
        ev.record_event(conn, item_id, ev.EVENT_UPDATED, summary,
                        payload=ev.diff_payload(before, after_slim), cli_cmd=cli_cmd)
        conn.commit()
        return True, f"已更新「{after['name']}」", {
            "item": _item_card(after, conn), "diff": diff, "before": before, "after": after_slim}
    finally:
        conn.close()


def move_item_v2(item_id, new_location, cli_cmd=None):
    """移动物品位置(3-2): 原位置→新位置 + 邻居 + 冲突提示 + 事件"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        new_location = (new_location or "").strip().strip("/")
        if "/" not in new_location:
            return False, f"位置必须至少两级(含'/'),当前 {new_location!r}", None
        loc = _loc_row(conn, item_id)
        if not loc:
            return False, "该物品没有位置记录,无法移动", None
        old_location = loc["location"]
        before = {"location": old_location, "quantity": loc["quantity"],
                  "location_status": loc["location_status"]}
        conn.execute("UPDATE item_locations SET location = ?, updated_at = ? WHERE id = ?",
                     (new_location, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), loc["id"]))

        # 邻居(新位置同住客)
        neighbors = conn.execute(
            "SELECT DISTINCT i.* FROM items i JOIN item_locations il ON i.id = il.item_id "
            "WHERE il.location = ? AND i.id != ? AND il.location_status != ? LIMIT 10",
            (new_location, item_id, DISCARDED_STATUS),
        ).fetchall()
        # 冲突(新位置已有同名)
        conflict = conn.execute(
            "SELECT i.id, i.name FROM items i JOIN item_locations il ON i.id = il.item_id "
            "WHERE il.location = ? AND i.id != ? AND i.name = ? AND il.location_status != ? LIMIT 3",
            (new_location, item_id, cur["name"], DISCARDED_STATUS),
        ).fetchall()

        after = _loc_row(conn, item_id)
        ev.record_event(conn, item_id, ev.EVENT_LOCATION_MOVED,
                        f"移动「{cur['name']}」:{old_location} → {new_location}",
                        payload=ev.diff_payload(before, dict(after)), cli_cmd=cli_cmd)
        conn.commit()
        return True, f"已从「{old_location}」搬到「{new_location}」", {
            "item": _item_card(_find_item(conn, item_id), conn),
            "old_location": old_location, "new_location": new_location,
            "neighbors": [_item_card(dict(r), conn) for r in neighbors],
            "conflicts": [{"id": r["id"], "name": r["name"]} for r in conflict],
        }
    finally:
        conn.close()


def change_quantity_v2(item_id, delta=0, absolute=None, cli_cmd=None):
    """数量变更(3-3): 补充/消耗;减到 0 → 位置记录删除 + 「已用完」+补货建议"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        loc = _loc_row(conn, item_id)
        if not loc:
            return False, "该物品没有位置记录", None
        old_qty = loc["quantity"] or 0
        new_qty = absolute if absolute is not None else old_qty + delta
        if new_qty < 0:
            return False, f"数量不能为负(当前 {new_qty})", None
        before = {"quantity": old_qty, "location": loc["location"]}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = None
        if new_qty == 0:
            conn.execute("DELETE FROM item_locations WHERE id = ?", (loc["id"],))
            status = "已用完"
        else:
            conn.execute("UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
                         (new_qty, now, loc["id"]))
        after = {"quantity": new_qty, "location": loc["location"]}
        summary = f"「{cur['name']}」数量 {old_qty} → {new_qty}"
        if new_qty == 0:
            summary += "(已用完,位置记录删除)"
        ev.record_event(conn, item_id, ev.EVENT_QUANTITY_CHANGED, summary,
                        payload=ev.diff_payload(before, after), cli_cmd=cli_cmd)
        conn.commit()
        return True, summary, {
            "item": _item_card(_find_item(conn, item_id), conn),
            "before_qty": old_qty, "after_qty": new_qty,
            "exhausted": new_qty == 0,
            "restock_tip": "已用完,建议补货" if new_qty == 0 else None,
        }
    finally:
        conn.close()


def change_status_v2(item_id, target_status, location=None, cli_cmd=None):
    """状态变更(3-4): 状态机校验 + 废弃确认(软删除)/恢复 + 事件"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        loc = _loc_row(conn, item_id, location)
        if not loc:
            locs = conn.execute("SELECT location FROM item_locations WHERE item_id = ?", (item_id,)).fetchall()
            locs_str = "、".join(r["location"] for r in locs) or "(无位置记录)"
            return False, f"该物品无位置记录或未找到位置「{location}」,可用: {locs_str}", None
        ok, msg = check_status_transition(loc["location_status"], target_status)
        if not ok:
            return False, msg, None
        before = {"location_status": loc["location_status"], "location": loc["location"]}
        conn.execute("UPDATE item_locations SET location_status = ?, updated_at = ? WHERE id = ?",
                     (target_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), loc["id"]))
        after = _loc_row(conn, item_id, loc["location"])
        summary = f"「{cur['name']}」状态 {before['location_status']} → {target_status}"
        ev.record_event(conn, item_id, ev.EVENT_STATUS_CHANGED, summary,
                        payload=ev.diff_payload(before, dict(after)), cli_cmd=cli_cmd)
        conn.commit()
        return True, msg, {
            "item": _item_card(_find_item(conn, item_id), conn),
            "before_status": before["location_status"], "after_status": target_status,
            "discarded": target_status == DISCARDED_STATUS,
            "restored": before["location_status"] == DISCARDED_STATUS,
        }
    finally:
        conn.close()


def merge_items_v2(target_id, source_ids, cli_cmd=None):
    """合并重复物品(3-5): 保留主条 + 字段合并 + 数量相加 + 事件

    源物品标记「已废弃」(软删除,历史可查);数量并入目标。
    """
    conn = _conn()
    try:
        target = _find_item(conn, target_id)
        if not target:
            return False, f"未找到主物品 ID={target_id}", None
        tgt_loc = _loc_row(conn, target_id)
        results = []
        scene_id = f"merge-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for src_id in source_ids:
            if src_id == target_id:
                continue
            src = _find_item(conn, src_id)
            if not src:
                results.append({"id": src_id, "ok": False, "message": "源物品不存在"})
                continue
            src_loc = _loc_row(conn, src_id)
            tgt_before_qty = tgt_loc["quantity"] if tgt_loc else 0
            src_qty = src_loc["quantity"] if src_loc else 1
            # 数量相加到目标
            if tgt_loc:
                conn.execute("UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
                             (tgt_before_qty + src_qty, now, tgt_loc["id"]))
            # 标签并集
            src_tags = get_tags(conn, src_id)
            for t in [x.strip() for x in src_tags.split(",") if x.strip()]:
                add_tag(conn, target_id, t)
            # 备注追加
            if src["remark"]:
                merged_remark = (target["remark"] + "\n[合并自#" + str(src_id) + "] " + src["remark"]).strip()
                conn.execute("UPDATE items SET remark = ? WHERE id = ?", (merged_remark, target_id))
            # 源物品软删除(废弃)
            if src_loc:
                conn.execute("UPDATE item_locations SET location_status = ?, updated_at = ? WHERE item_id = ?",
                             (DISCARDED_STATUS, now, src_id))
            before = {"source_item_id": src_id, "source_name": src["name"],
                      "source_status": src_loc["location_status"] if src_loc else "在家",
                      "source_quantity": src_qty, "target_quantity": tgt_before_qty}
            after = {"source_item_id": src_id, "target_quantity": tgt_before_qty + src_qty}
            ev.record_event(conn, target_id, ev.EVENT_MERGED,
                            f"合并「{src['name']}」→「{target['name']}」(数量+{src_qty})",
                            payload={"before": before, "after": after},
                            scene_id=scene_id, cli_cmd=cli_cmd)
            results.append({"id": src_id, "ok": True, "message": f"已并入(数量+{src_qty})"})
            tgt_loc = _loc_row(conn, target_id)
        conn.commit()
        ok = all(r["ok"] for r in results) and len(results) > 0
        return ok, (f"合并完成: {len(results)} 件并入「{target['name']}」" if ok else "合并失败"), {
            "target": _item_card(_find_item(conn, target_id), conn),
            "results": results,
        }
    finally:
        conn.close()


def relate_items_v2(item_id, related_item_id, relation_type="配件", cli_cmd=None):
    """设置物品关联(3-7)"""
    conn = _conn()
    try:
        a = _find_item(conn, item_id)
        b = _find_item(conn, related_item_id)
        if not a:
            return False, f"未找到主物品 ID={item_id}", None
        if not b:
            return False, f"未找到关联物品 ID={related_item_id}", None
        if item_id == related_item_id:
            return False, "不能关联自己", None
        conn.execute(
            "INSERT OR IGNORE INTO item_relations (item_id, related_item_id, relation_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (item_id, related_item_id, relation_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        ev.record_event(conn, item_id, ev.EVENT_RELATED,
                        f"「{a['name']}」{relation_type} ↔ 「{b['name']}」",
                        payload={"before": {}, "after": {"related_item_id": related_item_id,
                                                          "relation_type": relation_type}},
                        cli_cmd=cli_cmd)
        conn.commit()
        return True, f"已建立关联:「{a['name']}」{relation_type}「{b['name']}」", {
            "item": _item_card(a, conn), "related": _item_card(b, conn), "relation_type": relation_type}
    finally:
        conn.close()


def unrelate_items_v2(item_id, related_item_id, cli_cmd=None):
    """解除关联(3-7)"""
    conn = _conn()
    try:
        a = _find_item(conn, item_id)
        b = _find_item(conn, related_item_id)
        row = conn.execute(
            "SELECT relation_type FROM item_relations WHERE item_id = ? AND related_item_id = ?",
            (item_id, related_item_id)).fetchone()
        if not row:
            return False, "该关联不存在", None
        conn.execute("DELETE FROM item_relations WHERE item_id = ? AND related_item_id = ?",
                     (item_id, related_item_id))
        ev.record_event(conn, item_id, ev.EVENT_UNLINKED,
                        f"解除关联:「{a['name']}」—「{b['name']}」",
                        payload={"before": {"related_item_id": related_item_id,
                                            "relation_type": row["relation_type"]},
                                 "after": {}},
                        cli_cmd=cli_cmd)
        conn.commit()
        return True, "已解除关联", {"item": _item_card(a, conn), "related": _item_card(b, conn)}
    finally:
        conn.close()


def tag_item_v2(item_id, add_tags=None, remove_tags=None, cli_cmd=None):
    """修改物品标签(3-8): 去旧+加新,单件或批量(循环调用)"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        before_tags = get_tags(conn, item_id)
        before_list = [t for t in before_tags.split(",") if t] if before_tags else []
        for t in (remove_tags or []):
            remove_tag(conn, item_id, t)
        for t in (add_tags or []):
            add_tag(conn, item_id, t)
        after_list = [t for t in get_tags(conn, item_id).split(",") if t] if get_tags(conn, item_id) else []
        ev.record_event(conn, item_id, ev.EVENT_TAGGED,
                        f"「{cur['name']}」标签: +{len(add_tags or [])} -{len(remove_tags or [])}",
                        payload=ev.diff_payload({"tags": before_list}, {"tags": after_list}),
                        cli_cmd=cli_cmd)
        conn.commit()
        return True, f"标签已更新(现 {len(after_list)} 个)", {
            "item": _item_card(_find_item(conn, item_id), conn),
            "before_tags": before_list, "after_tags": after_list}
    finally:
        conn.close()


def use_item_v2(item_id, cli_cmd=None):
    """标记使用(2-3「我找到了」/3-1 快捷操作): 更新最后使用时间"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("UPDATE items SET access_count = access_count + 1, last_accessed_at = ?, updated_at = ? WHERE id = ?",
                     (now, now, item_id))
        ev.record_event(conn, item_id, ev.EVENT_FOUND_USED, f"标记使用「{cur['name']}」",
                        payload={"before": {}, "after": {"last_accessed_at": now}}, cli_cmd=cli_cmd)
        conn.commit()
        return True, f"已标记使用「{cur['name']}」", {"item": _item_card(_find_item(conn, item_id), conn)}
    finally:
        conn.close()


def undo_v2(event_id, cli_cmd=None):
    """撤销操作(3-6): 委托 events.undo_event(读 before 回滚 + 追加 undo 事件)"""
    conn = _conn()
    try:
        ok, msg, item_id = ev.undo_event(conn, event_id)
        return ok, msg, {"event_id": event_id, "item_id": item_id}
    finally:
        conn.close()


# ── 子功能 4 · 标签与分类 ───────────────────────────────────────────────────


def tag_overview_payload():
    """标签总览(4-1): 标签名/使用物品数/使用次数 + 未使用标签(清理提示)"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT tag, COUNT(DISTINCT item_id) AS item_cnt, COUNT(*) AS use_cnt "
            "FROM item_tags GROUP BY tag ORDER BY use_cnt DESC").fetchall()
        tags = [dict(r) for r in rows]
        unused = [{"tag": r["tag"], "use_cnt": r["use_cnt"]} for r in rows if r["item_cnt"] == 0]
        return {"tags": tags, "total": len(tags), "unused": unused}
    finally:
        conn.close()


def tag_purge(limit=None):
    """清理未使用标签(4-1 删除): 仅删标签,不删物品(已无物品引用,直接删)"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT tag, COUNT(DISTINCT item_id) AS n FROM item_tags GROUP BY tag HAVING n = 0").fetchall()
        removed = []
        for r in rows[:limit] if limit else rows:
            conn.execute("DELETE FROM item_tags WHERE tag = ?", (r["tag"],))
            removed.append(r["tag"])
        conn.commit()
        return {"removed": removed, "count": len(removed)}
    finally:
        conn.close()


def similar_tags_payload(threshold=2):
    """相近标签检测(4-3 整理建议): 编辑距离 ≤ threshold 的标签对

    AI 侧可再用语义增强;这里提供确定性基线(合并影响预估)
    """
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT tag, COUNT(DISTINCT item_id) AS item_cnt FROM item_tags GROUP BY tag").fetchall()
        tags = [(r["tag"], r["item_cnt"]) for r in rows]
        pairs = []
        n = len(tags)
        for i in range(n):
            for j in range(i + 1, n):
                a, ca = tags[i]
                b, cb = tags[j]
                if abs(len(a) - len(b)) > threshold * 2:
                    continue
                d = _edit_distance(a, b)
                if d <= threshold:
                    pairs.append({
                        "a": a, "b": b, "distance": d,
                        "items_a": ca, "items_b": cb,
                        "impact": ca + cb,
                    })
        pairs.sort(key=lambda p: -p["impact"])
        return {"pairs": pairs[:20], "total": len(pairs)}
    finally:
        conn.close()


def _edit_distance(a, b):
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1,
                           dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return dp[m][n]


def category_overview_payload():
    """分类树总览(4-2): 8 顶级 + 二级,每类物品计数"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, parent_id, name, sort_order FROM categories ORDER BY sort_order, id").fetchall()
        cats = [dict(r) for r in rows]
        id2name = {c["id"]: c["name"] for c in cats}
        for c in cats:
            cnt = conn.execute("SELECT COUNT(*) AS n FROM items WHERE category_id = ?", (c["id"],)).fetchone()["n"]
            c["item_count"] = cnt
        tree = []
        for c in cats:
            if c["parent_id"] is None:
                c["children"] = [x for x in cats if x["parent_id"] == c["id"]]
                tree.append(c)
        return {"tree": tree, "total": len(cats)}
    finally:
        conn.close()


def _validate_category_name(name, conn, parent_id=None):
    """分类命名校验(违规抛 ValueError 已捕获;含同父唯一)"""
    from category_manager import _validate_name
    parent_name = None
    if parent_id:
        row = conn.execute("SELECT name FROM categories WHERE id = ?", (parent_id,)).fetchone()
        if not row:
            raise ValueError(f"父分类 {parent_id} 不存在")
        parent_name = row["name"]
    try:
        return _validate_name(name, parent_name=parent_name, conn=conn), None
    except ValueError as e:
        return None, str(e)


def category_add_v2(name, parent_id=None):
    """新建分类(4-2): 命名校验(禁数字前缀/禁emoji/同父唯一/1-30 字)"""
    conn = _conn()
    try:
        checked, err = _validate_category_name(name, conn, parent_id)
        if err:
            return False, err, None
        cur = conn.execute("SELECT MAX(sort_order) AS m FROM categories WHERE parent_id IS ?", (parent_id,)).fetchone()
        sort_order = (cur["m"] or 0) + 1
        conn.execute("INSERT INTO categories (parent_id, name, sort_order) VALUES (?, ?, ?)",
                     (parent_id, checked, sort_order))
        conn.commit()
        return True, f"已新建分类「{checked}」", {"name": checked, "parent_id": parent_id}
    finally:
        conn.close()


def category_rename_v2(cat_id, new_name):
    """重命名分类(4-2): 影响统计/导航/录入推荐(即全库引用自动生效)"""
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
        if not row:
            return False, f"分类 {cat_id} 不存在", None
        checked, err = _validate_category_name(new_name, conn, row["parent_id"])
        if err:
            return False, err, None
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (checked, cat_id))
        conn.commit()
        return True, f"已改名「{row['name']}」→「{checked}」", {"old_name": row["name"], "new_name": checked}
    finally:
        conn.close()


def category_merge_v2(from_id, to_id):
    """合并分类(4-2): 被并分类的子分类 + 物品全部迁移到目标"""
    conn = _conn()
    try:
        a = conn.execute("SELECT * FROM categories WHERE id = ?", (from_id,)).fetchone()
        b = conn.execute("SELECT * FROM categories WHERE id = ?", (to_id,)).fetchone()
        if not a or not b:
            return False, "源或目标分类不存在", None
        if from_id == to_id:
            return False, "不能合并到自身", None
        moved_items = 0
        # 物品迁移(含子分类下的物品)
        moved_items = conn.execute(
            "UPDATE items SET category_id = ? WHERE category_id IN "
            "(WITH RECURSIVE sub AS (SELECT ? AS id UNION ALL SELECT c.id FROM categories c "
            "JOIN sub s ON c.parent_id = s.id) SELECT id FROM sub)",
            (to_id, from_id)).rowcount
        # 子分类重新挂到目标
        conn.execute("UPDATE categories SET parent_id = ? WHERE parent_id = ?", (to_id, from_id))
        # 源分类删除(已无物品/子类;分类可改不可删的例外 = 合并)
        conn.execute("DELETE FROM categories WHERE id = ?", (from_id,))
        conn.commit()
        return True, f"已合并「{a['name']}」→「{b['name']}」({moved_items} 件物品迁移)", {
            "from": a["name"], "to": b["name"], "moved_items": moved_items}
    finally:
        conn.close()


# ── 子功能 5 · 照片档案 ─────────────────────────────────────────────────────


def photos_payload(item_id):
    """查看物品照片(5-1): 主图大图 + 多图缩略 + 类型标记 + 拍摄时间"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return None
        photos = ev.get_photos(conn, item_id)
        for p in photos:
            p["photo_base64"] = _get_photo_base64(p["file_path"])
            p["full_path"] = str(get_photo_full_path(p["file_path"])) if p["file_path"] else None
        return {"item": _item_card(cur, conn), "photos": photos}
    finally:
        conn.close()


def photo_update_v2(item_id, photos, cli_cmd=None):
    """管理物品照片(5-2 落地): photos = [{file_path, photo_type}] 全量替换(新顺序/主图/类型)

    排序变更 = 本地操作 + 统一确认(08 §4 普通确认式)
    """
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return False, f"未找到 ID={item_id} 的物品", None
        photos_dir = str(PHOTOS_DIR)
        cleaned = []
        for p in photos:
            path = p.get("file_path") or ""
            if not path:
                continue
            if not path.startswith(photos_dir):
                return False, f"照片路径必须放在 {photos_dir} 下,当前 {path}", None
            cleaned.append({"file_path": path[len(photos_dir):].lstrip("\\/"),
                            "photo_type": p.get("photo_type") or "普通"})
        before = ev.get_photos(conn, item_id)
        result = ev.replace_photos(conn, item_id, cleaned)
        summary = f"「{cur['name']}」照片更新为 {len(result)} 张"
        ev.record_event(conn, item_id, ev.EVENT_PHOTOS_CHANGED, summary,
                        payload=ev.diff_payload(
                            {"photos": [p["file_path"] for p in before]},
                            {"photos": [p["file_path"] for p in result]}),
                        cli_cmd=cli_cmd)
        conn.commit()
        return True, summary, {"item": _item_card(_find_item(conn, item_id), conn),
                               "photos": result, "main": result[0] if result else None}
    finally:
        conn.close()


def photo_wall_payload(group_by="category", photo_type=None, location=None):
    """照片墙浏览(5-3): 按分类/位置分组 + 类型筛选 + 空态(无照片物品补拍引导)"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM items WHERE id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?) "
            "AND (photo != '' OR photo IS NOT NULL) ORDER BY name",
            (DISCARDED_STATUS,),
        ).fetchall()
        cards = []
        for r in rows:
            photos = ev.get_photos(conn, r["id"])
            if not photos and not r["photo"]:
                continue
            c = _item_card(dict(r), conn)
            typed = [p for p in photos if not photo_type or p["photo_type"] == photo_type]
            if photo_type and not typed and not (photo_type == "普通" and not photos and r["photo"]):
                continue
            c["photos"] = photos
            cards.append(c)

        if group_by == "location":
            groups = {}
            for c in cards:
                g = c["location"] or "(未设置)"
                groups.setdefault(g, []).append(c)
        else:
            groups = {}
            for c in cards:
                g = c["category_name"]
                groups.setdefault(g, []).append(c)
        ordered = [{"name": g, "items": items} for g, items in sorted(groups.items())]

        # 空态:无照片物品
        no_photo = conn.execute(
            "SELECT COUNT(*) AS n FROM items WHERE (photo IS NULL OR photo = '') AND id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?)",
            (DISCARDED_STATUS,)).fetchone()["n"]
        return {"groups": ordered, "total": len(cards), "no_photo_count": no_photo,
                "group_by": group_by, "photo_type": photo_type}
    finally:
        conn.close()


# ── 子功能 6 · 盘点 ─────────────────────────────────────────────────────────


def _inv_scope_items(scope_type, value):
    """按范围取盘点清单: 位置 / 分类 / 全屋"""
    conn = _conn()
    try:
        conditions, params = [], []
        if scope_type == "location":
            conditions.append("EXISTS (SELECT 1 FROM item_locations il WHERE il.item_id = i.id AND il.location LIKE ?)")
            params.append(f"%{value}%")
        elif scope_type == "category":
            clause, c_params = _category_in_clause(conn, value)
            conditions.append("i." + clause)
            params.extend(c_params)
        where = (" AND " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT DISTINCT i.* FROM items i WHERE i.id NOT IN "
            f"(SELECT item_id FROM item_locations WHERE location_status = ?){where} ORDER BY i.name",
            [DISCARDED_STATUS] + params).fetchall()
        return [_item_card(dict(r), conn) for r in rows]
    finally:
        conn.close()


def _latest_inventory_detail(conn):
    """上次盘点差异(6-1 复查置顶区: 上次缺的 N 件)"""
    row = conn.execute("SELECT * FROM inventory_records ORDER BY id DESC LIMIT 1").fetchone()
    empty_flags = {"review": [], "missing": [], "extra": [], "diff": [], "pending": []}
    if not row:
        return None, empty_flags
    try:
        detail = json.loads(row["detail_json"] or "[]")
    except ValueError:
        detail = []
    flags = {"review": [], "missing": [], "extra": [], "diff": [], "pending": []}
    for d in detail:
        if isinstance(d, dict):
            for k in flags:
                if d.get(k):
                    flags[k].append(d)
    return dict(row), flags


def inventory_round_payload(scope_type, value):
    """盘点核对(6-1): 范围 + 清单 + 上次差异置顶区"""
    conn = _conn()
    try:
        items = _inv_scope_items(scope_type, value)
        last_record, flags = _latest_inventory_detail(conn)
        return {
            "scope": {"type": scope_type, "value": value},
            "items": items,
            "total": len(items),
            "last_record": last_record,
            "review_items": flags["review"],
            "statuses": STATUSES,
        }
    finally:
        conn.close()


def inventory_commit_v2(scope, results, cli_cmd=None):
    """盘点提交(6-1 完成): 写 inventory_records + 差异落地事件(逐物品)

    results: {"present": [ids], "missing": [ids], "extra": [{name, qty, location}],
              "diff": [{id, field, before, after}], "pending": [ids],
              "not_present": [ids], "review": [ids]}
    """
    conn = _conn()
    try:
        missing = results.get("missing") or []
        extra = results.get("extra") or []
        diff = results.get("diff") or []
        pending = results.get("pending") or []
        review = results.get("review") or []

        detail = [{"missing": i} for i in missing] + \
                 [{"extra": e} for e in extra] + \
                 [{"diff": d} for d in diff] + \
                 [{"pending": i} for i in pending] + \
                 [{"review": i} for i in review]

        record_id = ev.record_inventory(conn, scope, missing_cnt=len(missing),
                                        extra_cnt=len(extra), diff_cnt=len(diff),
                                        pending_cnt=len(pending), detail=detail,
                                        status="已完成")

        scene_id = f"inv-{record_id}"
        for iid in missing:
            cur = _find_item(conn, iid)
            if cur:
                ev.record_event(conn, iid, ev.EVENT_INVENTORY,
                                f"盘点缺(记录#{record_id}):「{cur['name']}」不在场",
                                payload={"before": {}, "after": {"inventory_record_id": record_id}},
                                scene_id=scene_id, cli_cmd=cli_cmd)
        for d in diff:
            iid = d.get("id")
            cur = _find_item(conn, iid)
            if cur:
                ev.record_event(conn, iid, ev.EVENT_INVENTORY,
                                f"盘点差异(记录#{record_id}):「{cur['name']}」{d.get('field')} {d.get('before')}→{d.get('after')}",
                                payload={"before": {d.get("field"): d.get("before")},
                                         "after": {d.get("field"): d.get("after")}},
                                scene_id=scene_id, cli_cmd=cli_cmd)
        conn.commit()
        return True, f"盘点完成:缺{len(missing)}/多{len(extra)}/异{len(diff)}/待确认{len(pending)}", {
            "record_id": record_id, "scope": scope, "missing": missing, "extra": extra,
            "diff": diff, "pending": pending, "review": review}
    finally:
        conn.close()


def inventory_records_payload():
    """查看盘点记录(6-3): 列表 + 单次详情(差异+处理结果)+ 复查入口"""
    conn = _conn()
    try:
        records = ev.query_inventory_records(conn)
        for r in records:
            try:
                r["detail"] = json.loads(r["detail_json"] or "[]")
            except ValueError:
                r["detail"] = []
        return {"records": records}
    finally:
        conn.close()


def inventory_diff_payload(record_id=None):
    """差异处理(6-2): 取指定/最近盘点记录的差异分组(缺/多/异/待确认)"""
    conn = _conn()
    try:
        if record_id:
            row = conn.execute("SELECT * FROM inventory_records WHERE id = ?", (record_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM inventory_records ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        record = dict(row)
        try:
            detail = json.loads(record["detail_json"] or "[]")
        except ValueError:
            detail = []
        missing, extra, diff, pending, review = [], [], [], [], []
        for d in detail:
            if "missing" in d:
                cur = _find_item(conn, d["missing"])
                missing.append({"item": _item_card(cur, conn) if cur else {"id": d["missing"], "name": f"#{d['missing']}"},
                                "record_id": record_id})
            elif "extra" in d:
                extra.append({"description": d["extra"]})
            elif "diff" in d:
                cur = _find_item(conn, d["diff"].get("id"))
                dd = dict(d["diff"])
                if cur:
                    dd["item"] = _item_card(cur, conn)
                diff.append(dd)
            elif "pending" in d:
                cur = _find_item(conn, d["pending"])
                pending.append({"item": _item_card(cur, conn) if cur else {"id": d["pending"], "name": f"#{d['pending']}"}})
            elif "review" in d:
                cur = _find_item(conn, d["review"])
                review.append({"item": _item_card(cur, conn) if cur else {"id": d["review"], "name": f"#{d['review']}"}})
        return {
            "record": record,
            "missing": missing, "extra": extra, "diff": diff, "pending": pending, "review": review,
            "actions": {
                "missing": ["标记废弃", "标记丢失", "标记挪走", "标记借出", "先不处理"],
                "extra": ["录入为新物品", "忽略"],
                "diff": ["按实际更新", "忽略"],
                "pending": ["标记复查", "先不处理"],
            },
        }
    finally:
        conn.close()


def resolve_diff_v2(record_id, actions, cli_cmd=None):
    """差异处理落地(6-2): 批量执行

    actions: {"missing": [{id, action, new_location?}],
              "extra": [{description, draft?}],   # draft 非空 → 生成采集预览待确认,不直接写库
              "diff": [{id, apply: bool}],
              "pending": [{id, mark_review: bool}]}
    返回 (ok, message, payload)
    """
    conn = _conn()
    try:
        record = conn.execute("SELECT * FROM inventory_records WHERE id = ?", (record_id,)).fetchone()
        if not record:
            return False, f"盘点记录 {record_id} 不存在", None
        results = []
        scene_id = f"invres-{record_id}-{datetime.now().strftime('%H%M%S')}"

        for m in actions.get("missing") or []:
            iid = m["id"]
            action = m.get("action")
            cur = _find_item(conn, iid)
            if not cur:
                continue
            if action == "标记废弃":
                ok, msg, _ = change_status_v2(iid, DISCARDED_STATUS, cli_cmd=cli_cmd)
                results.append({"type": "missing", "id": iid, "action": action, "ok": ok, "message": msg})
            elif action == "标记丢失":
                ok, msg, _ = change_status_v2(iid, "找不到", cli_cmd=cli_cmd)
                results.append({"type": "missing", "id": iid, "action": action, "ok": ok, "message": msg})
            elif action == "标记挪走":
                new_loc = m.get("new_location")
                if not new_loc:
                    results.append({"type": "missing", "id": iid, "action": action,
                                    "ok": False, "message": "缺少新位置"})
                else:
                    ok, msg, _ = move_item_v2(iid, new_loc, cli_cmd=cli_cmd)
                    results.append({"type": "missing", "id": iid, "action": action, "ok": ok, "message": msg})
            elif action == "标记借出":
                ok, msg, _ = change_status_v2(iid, "借用中", cli_cmd=cli_cmd)
                results.append({"type": "missing", "id": iid, "action": action, "ok": ok, "message": msg})
            else:
                results.append({"type": "missing", "id": iid, "action": "先不处理", "ok": True, "message": "跳过"})

        extra_drafts = []
        for e in actions.get("extra") or []:
            if e.get("draft"):
                extra_drafts.append(e["draft"])  # 生成采集预览待确认(不直接写库)
            results.append({"type": "extra", "action": "录入为新物品" if e.get("draft") else "忽略",
                            "ok": True, "message": "待预览" if e.get("draft") else "忽略"})

        for d in actions.get("diff") or []:
            iid = d.get("id")
            if d.get("apply"):
                fields = {}
                if d.get("field") == "quantity" and d.get("after") is not None:
                    ok, msg, _ = change_quantity_v2(iid, absolute=int(d["after"]), cli_cmd=cli_cmd)
                elif d.get("field") == "location_status" and d.get("after"):
                    ok, msg, _ = change_status_v2(iid, d["after"], cli_cmd=cli_cmd)
                elif d.get("field") == "location" and d.get("after"):
                    ok, msg, _ = move_item_v2(iid, d["after"], cli_cmd=cli_cmd)
                else:
                    ok, msg = False, f"不支持的差异字段 {d.get('field')}"
                results.append({"type": "diff", "id": iid, "action": "按实际更新", "ok": ok, "message": msg})
            else:
                results.append({"type": "diff", "id": iid, "action": "忽略", "ok": True, "message": "跳过"})

        for p in actions.get("pending") or []:
            results.append({"type": "pending", "id": p.get("id"),
                            "action": "标记复查" if p.get("mark_review") else "先不处理",
                            "ok": True, "message": "已标记复查(下次盘点置顶)" if p.get("mark_review") else "跳过"})

        conn.execute("UPDATE inventory_records SET status = ? WHERE id = ?",
                     ("已处理" if not extra_drafts else "进行中", record_id))
        conn.commit()
        summary = "差异处理完成:" + "".join(
            f"{r['action']}{'✓' if r['ok'] else '✗'} " for r in results)
        return True, summary, {"record_id": record_id, "results": results, "extra_drafts": extra_drafts}
    finally:
        conn.close()


def move_checklist_payload():
    """搬家打包盘点(6-4): 全屋清单(按位置分组)+ 二态【带走/不带走】"""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT i.* FROM items i WHERE i.id NOT IN "
            "(SELECT item_id FROM item_locations WHERE location_status = ?) ORDER BY i.name",
            (DISCARDED_STATUS,),
        ).fetchall()
        cards = [_item_card(dict(r), conn) for r in rows]
        groups = {}
        for c in cards:
            groups.setdefault(c["location"] or "(未设置)", []).append(c)
        return {"groups": [{"name": k, "items": v} for k, v in sorted(groups.items())],
                "total": len(cards)}
    finally:
        conn.close()


# ── 子功能 7 · 物品历史 ─────────────────────────────────────────────────────


def history_payload(item_id):
    """查看物品历史(7-1): 时间线(倒序)+ 类型筛选 + 位置轨迹(可选)"""
    conn = _conn()
    try:
        cur = _find_item(conn, item_id)
        if not cur:
            return None
        events = ev.query_item_events(conn, item_id, limit=200)
        for e in events:
            try:
                e["payload"] = json.loads(e["payload_json"] or "{}")
            except ValueError:
                e["payload"] = {}
        # 位置轨迹: location_moved 事件串成 客厅→卧室→车里(含起点)
        trajectory = []
        first = True
        for e in reversed(events):
            if e["event_type"] == ev.EVENT_LOCATION_MOVED:
                p = e.get("payload") or {}
                before_loc = (p.get("before") or {}).get("location")
                after_loc = (p.get("after") or {}).get("location")
                if first and before_loc:
                    trajectory.append(before_loc)
                first = False
                if after_loc:
                    trajectory.append(after_loc)
        # 类型筛选选项
        filter_types = [
            {"key": ev.EVENT_CREATED, "label": "录入"},
            {"key": ev.EVENT_BACKFILLED, "label": "补录"},
            {"key": ev.EVENT_UPDATED, "label": "更新"},
            {"key": ev.EVENT_QUANTITY_CHANGED, "label": "数量"},
            {"key": ev.EVENT_STATUS_CHANGED, "label": "状态"},
            {"key": ev.EVENT_LOCATION_MOVED, "label": "位置"},
            {"key": ev.EVENT_INVENTORY, "label": "盘点"},
            {"key": ev.EVENT_MERGED, "label": "合并"},
            {"key": ev.EVENT_UNDONE, "label": "撤销"},
        ]
        return {"item": _item_card(cur, conn), "events": events,
                "trajectory": trajectory, "filter_types": filter_types}
    finally:
        conn.close()
