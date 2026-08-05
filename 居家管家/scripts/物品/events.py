# events.py - 记录契约底座(SM1 子功能 7 存储方案 · D1 #103 约定接口)
#
# 规格: scenes/SM1-物品管理.md 「存储方案」+「记录契约」(2026-08-04 对抗式审查修正后定稿)
#   item_events(单物品事件表): id / item_id(索引) / event_type(字符串+代码层枚举) /
#     occurred_at(索引,本地时间·ADR-0001) / summary(CLI 生成) /
#     payload_json(字段级 diff {"before":..,"after":..}) / scene_id(批量归组) / cli_cmd(debug)
#   inventory_records(盘点记录表): id / scope / occurred_at / 缺N·多N·异N / status
#
# D1 边界(2026-08-04 用户裁定): 物理建表归 D1 批(总账 #103 注册);实施期先按本模块约定接口。
# 本模块自带幂等建表(ensure_tables),供本域写路径原子落库;D1 批落地时把 DDL 收编进
# scripts/home_manager/db.py init_db 并迁移 items.photo → photo 表。
#
# 记录契约(横切,所有写操作场景遵守):
#   1. 原子性: 数据变更 + 事件写入同一事务(调用方传同一 conn)
#   2. 级联规则: 物理删除(异常清理 CLI)= 级联清历史;软删除(废弃)= 保留历史
#   3. diff 粒度: 字段级(仅变更字段)
#   4. event_type: 字符串 + 代码层枚举(可扩展,不加 DB CHECK)
#   5. summary: 写库 CLI 生成,AI 不自由发挥
#   6. 撤销: 读 payload_json.before 回滚 + 追加 undo 事件(引用被撤销事件 id);
#      撤销一次性,不无限嵌套;「恢复」弱支持(后置)
from datetime import datetime


# ── 代码层枚举(event_type 字符串值)───────────────────────────────────────────

EVENT_CREATED = "created"            # 录入
EVENT_BACKFILLED = "backfilled"      # 补录(指定日期)
EVENT_BATCH_CREATED = "batch_created"  # 批量录入
EVENT_UPDATED = "updated"            # 修改物品信息
EVENT_LOCATION_MOVED = "location_moved"  # 移动位置
EVENT_QUANTITY_CHANGED = "quantity_changed"  # 数量变更
EVENT_STATUS_CHANGED = "status_changed"  # 状态变更
EVENT_TAGGED = "tagged"              # 打/去标签
EVENT_MERGED = "merged"              # 合并物品
EVENT_UNLINKED = "unlinked"          # 解除关联
EVENT_RELATED = "related"            # 设置关联
EVENT_PHOTOS_CHANGED = "photos_changed"  # 管照片(排序/换主图/加图/删图/标记类型)
EVENT_INVENTORY = "inventory"        # 盘点提交
EVENT_INVENTORY_RESOLVED = "inventory_resolved"  # 差异处理落地
EVENT_MOVED_BATCH = "moved_batch"    # 批量移动
EVENT_FOUND_USED = "found_used"      # 标记使用/找到了(更新最后使用时间)
EVENT_UNDONE = "undone"              # 撤销
EVENT_RESTORED = "restored"          # 恢复(废弃 → 在用)

EVENT_TYPES = {
    EVENT_CREATED, EVENT_BACKFILLED, EVENT_BATCH_CREATED, EVENT_UPDATED,
    EVENT_LOCATION_MOVED, EVENT_QUANTITY_CHANGED, EVENT_STATUS_CHANGED,
    EVENT_TAGGED, EVENT_MERGED, EVENT_UNLINKED, EVENT_RELATED,
    EVENT_PHOTOS_CHANGED, EVENT_INVENTORY, EVENT_INVENTORY_RESOLVED,
    EVENT_MOVED_BATCH, EVENT_FOUND_USED, EVENT_UNDONE, EVENT_RESTORED,
}

# 照片类型(代码层枚举,与 event_type 同模式;不开放用户自定义 · SM1 子功能 5)
PHOTO_TYPES = ["普通", "说明书-使用", "说明书-安装", "说明书-保养"]

# 关联关系类型(3-7 物品关联 · 自由文本)
RELATION_TYPES = ["配件", "配套", "替代", "同捆", "常用搭配"]

# 盘点记录状态
INV_RECORD_STATUS = ["进行中", "已完成", "已处理", "已复查"]


# ── DDL(SM1 规格定义 · 幂等;D1 批正式收编)────────────────────────────────────

_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS item_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMP NOT NULL,
    summary TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    scene_id TEXT,
    cli_cmd TEXT,
    undo_of INTEGER
)
"""
_INVENTORY_DDL = """
CREATE TABLE IF NOT EXISTS inventory_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,
    occurred_at TIMESTAMP NOT NULL,
    missing_cnt INTEGER DEFAULT 0,
    extra_cnt INTEGER DEFAULT 0,
    diff_cnt INTEGER DEFAULT 0,
    pending_cnt INTEGER DEFAULT 0,
    detail_json TEXT NOT NULL DEFAULT '[]',
    status TEXT DEFAULT '进行中',
    created_at TIMESTAMP NOT NULL
)
"""
_PHOTO_DDL = """
CREATE TABLE IF NOT EXISTS photo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    photo_type TEXT NOT NULL DEFAULT '普通',
    file_path TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
)
"""
_RELATIONS_DDL = """
CREATE TABLE IF NOT EXISTS item_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    related_item_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL DEFAULT '配件',
    created_at TIMESTAMP NOT NULL,
    UNIQUE(item_id, related_item_id),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY (related_item_id) REFERENCES items(id) ON DELETE CASCADE
)
"""

_ALL_DDL = [_EVENTS_DDL, _INVENTORY_DDL, _PHOTO_DDL, _RELATIONS_DDL]


def ensure_tables(conn):
    """幂等建表(SM1 域内自持载体;D1 批把 DDL 收编进 db.py init_db)"""
    cursor = conn.cursor()
    for ddl in _ALL_DDL:
        cursor.execute(ddl)
    conn.commit()


def now_str():
    """本地时间(ADR-0001)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 事件写入 ───────────────────────────────────────────────────────────────


def record_event(conn, item_id, event_type, summary, payload=None,
                 scene_id=None, cli_cmd=None):
    """记录一条物品事件(与数据变更同一 conn/事务 = 原子)

    payload: {"before": {...}, "after": {...}} 字段级 diff
    返回: (event_id, occurred_at)
    """
    ensure_tables(conn)
    import json
    occurred = now_str()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO item_events (item_id, event_type, occurred_at, summary, payload_json, scene_id, cli_cmd) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (item_id, event_type, occurred, summary,
         json.dumps(payload or {}, ensure_ascii=False),
         scene_id, cli_cmd),
    )
    return cursor.lastrowid, occurred


def diff_payload(before: dict, after: dict) -> dict:
    """字段级 diff(仅变更字段,粒度契约 #3)"""
    diff = {}
    keys = set(before) | set(after)
    for k in keys:
        if before.get(k) != after.get(k):
            diff[k] = {"before": before.get(k), "after": after.get(k)}
    return {"before": {k: v["before"] for k, v in diff.items()},
            "after": {k: v["after"] for k, v in diff.items()}}


# ── 查询 ───────────────────────────────────────────────────────────────────


def query_item_events(conn, item_id, event_type=None, limit=100):
    """物品事件时间线(倒序;支持类型筛选)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    sql = "SELECT * FROM item_events WHERE item_id = ?"
    params = [item_id]
    if event_type:
        sql += " AND event_type = ?"
        params.append(event_type)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    return [dict(r) for r in rows]


def query_recent_events(conn, limit=50, item_id=None):
    """最近事件(3-6 撤销选择用;item_id 可选过滤)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    sql = "SELECT * FROM item_events WHERE event_type != ?"
    params = [EVENT_UNDONE]
    if item_id:
        sql += " AND item_id = ?"
        params.append(item_id)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(sql, params)
    return [dict(r) for r in cursor.fetchall()]


def is_undone(conn, event_id):
    """事件是否已被撤销(撤销一次性契约)"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS n FROM item_events WHERE undo_of = ?", (event_id,))
    return cursor.fetchone()["n"] > 0


# ── 撤销(契约 #6)───────────────────────────────────────────────────────────


def undo_event(conn, event_id):
    """撤销一条事件:读 payload_json.before 回滚 + 追加 undo 事件

    支持撤销的事件类型: created/backfilled/batch_created(删条目)/updated/
    quantity_changed/location_moved/status_changed/tagged/merged/related/unlinked
    返回: (ok: bool, message: str, item_id: int|None)
    """
    ensure_tables(conn)
    import json
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM item_events WHERE id = ?", (event_id,))
    ev = cursor.fetchone()
    if not ev:
        return False, f"事件 {event_id} 不存在", None
    ev = dict(ev)
    if ev["event_type"] == EVENT_UNDONE:
        return False, "撤销事件不可再撤销", ev["item_id"]
    if is_undone(conn, event_id):
        return False, f"事件 {event_id} 已被撤销,撤销一次性", ev["item_id"]

    try:
        payload = json.loads(ev["payload_json"] or "{}")
    except ValueError:
        payload = {}
    before = payload.get("before") or {}
    et = ev["event_type"]
    item_id = ev["item_id"]

    # 读 items 现值,用于回滚 diff 类事件
    def _current():
        cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    if et in (EVENT_CREATED, EVENT_BACKFILLED, EVENT_BATCH_CREATED):
        # 级联删条目(位置/标签/照片/关联随 FK 级联;item_tags 无 FK,手动清)
        cursor.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        msg = f"已撤销录入,物品 {item_id} 已删除(级联清理位置/标签/照片/关联)"
    elif et == EVENT_UPDATED:
        cur = _current()
        if not cur:
            return False, f"物品 {item_id} 已不存在", item_id
        _apply_fields(conn, cursor, item_id, before)
        msg = f"已回滚字段修改: {', '.join(before.keys()) or '(无字段)'}"
    elif et == EVENT_QUANTITY_CHANGED:
        loc = _locate_by_payload(conn, cursor, payload, item_id)
        if loc is None:
            return False, "找不到变更时的位置记录,撤销失败", item_id
        old_qty = before.get("quantity")
        if old_qty is None:
            return False, "事件缺少数量 before,撤销失败", item_id
        if old_qty <= 0:
            cursor.execute("DELETE FROM item_locations WHERE id = ?", (loc["id"],))
        else:
            cursor.execute(
                "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
                (old_qty, now_str(), loc["id"]),
            )
        msg = f"已回滚数量变更 → {old_qty}"
    elif et == EVENT_LOCATION_MOVED:
        loc = _locate_by_payload(conn, cursor, payload, item_id)
        if loc is None:
            return False, "找不到移动后的位置记录,撤销失败", item_id
        old_loc = before.get("location")
        if not old_loc:
            return False, "事件缺少原位置,撤销失败", item_id
        cursor.execute(
            "UPDATE item_locations SET location = ?, updated_at = ? WHERE id = ?",
            (old_loc, now_str(), loc["id"]),
        )
        msg = f"已回滚位置移动 → {old_loc}"
    elif et == EVENT_STATUS_CHANGED:
        loc = _locate_by_payload(conn, cursor, payload, item_id)
        if loc is None:
            return False, "找不到状态变更时的位置记录,撤销失败", item_id
        old_st = before.get("location_status")
        if not old_st:
            return False, "事件缺少原状态,撤销失败", item_id
        cursor.execute(
            "UPDATE item_locations SET location_status = ?, updated_at = ? WHERE id = ?",
            (old_st, now_str(), loc["id"]),
        )
        msg = f"已回滚状态 → {old_st}"
    elif et == EVENT_TAGGED:
        cur = _current()
        if not cur:
            return False, f"物品 {item_id} 已不存在", item_id
        # before.tags = 变更前完整标签列表
        cursor.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
        for t in before.get("tags") or []:
            cursor.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
                (item_id, t),
            )
        msg = f"已回滚标签: {', '.join(before.get('tags') or []) or '(清空)'}"
    elif et == EVENT_MERGED:
        # 撤销合并: 源物品从「已废弃」恢复 + 目标数量回滚
        src_id = before.get("source_item_id")
        if src_id:
            cursor.execute(
                "UPDATE item_locations SET location_status = ?, updated_at = ? WHERE item_id = ?",
                (before.get("source_status") or "在家", now_str(), src_id),
            )
        cur = _current()
        if cur:
            tgt = before.get("target_quantity")
            if tgt is not None:
                loc = _locate_by_payload(conn, cursor, payload, item_id)
                if loc is not None:
                    cursor.execute(
                        "UPDATE item_locations SET quantity = ?, updated_at = ? WHERE id = ?",
                        (tgt, now_str(), loc["id"]),
                    )
        msg = "已撤销合并(源物品恢复,目标数量回滚)"
    elif et == EVENT_RELATED:
        rid = before.get("related_item_id")
        cursor.execute(
            "DELETE FROM item_relations WHERE item_id = ? AND related_item_id = ?",
            (item_id, rid),
        )
        msg = "已撤销关联"
    elif et == EVENT_UNLINKED:
        rid = before.get("related_item_id")
        cursor.execute(
            "INSERT OR IGNORE INTO item_relations (item_id, related_item_id, relation_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (item_id, rid, before.get("relation_type") or "配件", now_str()),
        )
        msg = "已恢复关联"
    else:
        return False, f"事件类型 {et} 不支持撤销", item_id

    occurred = now_str()
    cursor.execute(
        "INSERT INTO item_events (item_id, event_type, occurred_at, summary, payload_json, scene_id, cli_cmd, undo_of) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (item_id, EVENT_UNDONE, occurred, msg,
         json.dumps({"undone_event_id": event_id, "summary": ev["summary"]}, ensure_ascii=False),
         ev.get("scene_id"), "python home_manager.py sm1-undo", event_id),
    )
    conn.commit()
    return True, msg, item_id


def _apply_fields(conn, cursor, item_id, fields):
    """把 fields(dict) 写回 items 表(撤销 updated 用)"""
    if not fields:
        return
    updates = ["updated_at = ?"]
    params = [now_str()]
    for k, v in fields.items():
        if k in ("id", "created_at", "updated_at"):
            continue
        updates.append(f"{k} = ?")
        params.append(v)
    params.append(item_id)
    cursor.execute(f"UPDATE items SET {', '.join(updates)} WHERE id = ?", params)


def _locate_by_payload(conn, cursor, payload, item_id):
    """按 payload.after 里的位置标识定位位置记录(撤销回滚用)"""
    after = payload.get("after") or {}
    loc_path = after.get("location")
    if loc_path:
        cursor.execute(
            "SELECT * FROM item_locations WHERE item_id = ? AND location = ?",
            (item_id, loc_path),
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    cursor.execute(
        "SELECT * FROM item_locations WHERE item_id = ? ORDER BY id DESC LIMIT 1",
        (item_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


# ── 盘点记录(inventory_records)─────────────────────────────────────────────


def record_inventory(conn, scope, missing_cnt=0, extra_cnt=0, diff_cnt=0,
                     pending_cnt=0, detail=None, status="已完成"):
    """写入一条盘点记录(6-3 查看盘点记录 / 6-1 完成时)
    盘点明细不塞 item_events(位置级/全屋级事件);落地差异时各物品自然写事件。
    返回 record_id
    """
    ensure_tables(conn)
    import json
    occurred = now_str()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO inventory_records (scope, occurred_at, missing_cnt, extra_cnt, "
        "diff_cnt, pending_cnt, detail_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (scope, occurred, missing_cnt, extra_cnt, diff_cnt, pending_cnt,
         json.dumps(detail or [], ensure_ascii=False), status, occurred),
    )
    return cursor.lastrowid


def query_inventory_records(conn, limit=50):
    """盘点记录列表(倒序)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory_records ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in cursor.fetchall()]


# ── 照片(photo 表 · SM1 子功能 5)─────────────────────────────────────────────


def get_photos(conn, item_id):
    """物品照片列表(按 sort_order;第一张 = 主图)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM photo WHERE item_id = ? ORDER BY sort_order ASC, id ASC",
        (item_id,),
    )
    return [dict(r) for r in cursor.fetchall()]


def replace_photos(conn, item_id, photos):
    """整体替换照片集(管照片落地: 排序/类型/主图;photos = [{file_path, photo_type}])

    photos 为空 = 清空照片集。返回新列表。
    """
    ensure_tables(conn)
    occurred = now_str()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM photo WHERE item_id = ?", (item_id,))
    result = []
    for i, p in enumerate(photos):
        ptype = p.get("photo_type") or "普通"
        if ptype not in PHOTO_TYPES:
            raise ValueError(f"非法照片类型: {ptype},可选: {PHOTO_TYPES}")
        cursor.execute(
            "INSERT INTO photo (item_id, sort_order, photo_type, file_path, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (item_id, i, ptype, p["file_path"], occurred),
        )
        result.append({"sort_order": i, "photo_type": ptype, "file_path": p["file_path"]})
    # 主图回写 items.photo(向后兼容老模板;D1 迁移 items.photo → photo 表)
    main = result[0]["file_path"] if result else ""
    cursor.execute("UPDATE items SET photo = ?, updated_at = ? WHERE id = ?",
                   (main, occurred, item_id))
    return result


# ── 关联(item_relations · 3-7)───────────────────────────────────────────────


def get_relations(conn, item_id):
    """物品的关联列表(含反向)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.id, r.item_id, r.related_item_id, r.relation_type, r.created_at, "
        "i.name AS related_name "
        "FROM item_relations r LEFT JOIN items i ON i.id = r.related_item_id "
        "WHERE r.item_id = ? ORDER BY r.id",
        (item_id,),
    )
    out = [dict(r) for r in cursor.fetchall()]
    cursor.execute(
        "SELECT r.id, r.item_id, r.related_item_id, r.relation_type, r.created_at, "
        "i.name AS related_name "
        "FROM item_relations r LEFT JOIN items i ON i.id = r.item_id "
        "WHERE r.related_item_id = ? ORDER BY r.id",
        (item_id,),
    )
    for r in cursor.fetchall():
        d = dict(r)
        d["reverse"] = True
        out.append(d)
    return out
