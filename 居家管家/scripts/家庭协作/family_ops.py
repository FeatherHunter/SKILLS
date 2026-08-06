# family_ops.py - SM7 家庭协作域数据层(家人档案 + 借用管理)
#
# 规格: scenes/SM7-家庭协作.md(2026-08-04 定稿 2 场景)+ t8-sm7-design.md 第一性设计
#   family_members(成员): 称呼/关系/备注;物品归属 = items.owner(已有字段,复用)
#   borrow_records(借用): 方向(借出|借入)/item_id(可空·借出必填)/item_name(冗余)/
#     object_name(成员或外部联系人)/借出日期/约定归还日/归还时间
#
# D1 边界(2026-08-04 用户裁定): 物理建表归 D1 批(总账 #103 注册 #9/#10);
# 实施期本模块自带幂等建表(ensure_tables),D1 批落地时把 DDL 收编进 db.py init_db。
# 设计修正: 约定归还日放 borrow_records(记录级),不实施 D1 #8 items.约定归还日
# (同一物品多次借出归还日不同 → 记录级属性,已在 #103 注明)。
#
# 状态机复用(SM1 3-4): 借出 = 物品全部位置 → 借用中;归还 = → 在家。借入不动状态。
# 记录契约: 借用记录写 borrow_records(本域自持);物品状态变更属于 SM1 状态机域,
# 事件留痕由 SM1 实施期统一承接(本域不重复造 item_events 写入)。
from datetime import date, datetime, timedelta

VALID_DIRECTIONS = ("借出", "借入")
DEFAULT_OWNER = "使用者"


# ── DDL(幂等;D1 批正式收编)────────────────────────────────────────────────

_MEMBERS_DDL = """
CREATE TABLE IF NOT EXISTS family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    relation TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""
_BORROW_DDL = """
CREATE TABLE IF NOT EXISTS borrow_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,
    item_id INTEGER,
    item_name TEXT NOT NULL,
    object_name TEXT NOT NULL,
    borrowed_at TEXT NOT NULL,
    due_date TEXT,
    returned_at TEXT,
    remark TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

_ALL_DDL = [_MEMBERS_DDL, _BORROW_DDL]


def ensure_tables(conn):
    """幂等建表(本域自持载体;D1 批把 DDL 收编进 db.py init_db)"""
    cursor = conn.cursor()
    for ddl in _ALL_DDL:
        cursor.execute(ddl)
    conn.commit()


def now_str():
    """本地时间(ADR-0001)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today_str(today=None):
    return (today or date.today()).isoformat()


def _enrich_record(conn, row, today=None):
    """借用记录 dict 富化: 已借天数 + 状态 + 催还文案 + 物品照片(规格: 物品(照片+名称))"""
    r = dict(row)
    t = today or date.today()
    try:
        days = (t - date.fromisoformat(r["borrowed_at"])).days
    except ValueError:
        days = 0
    r["days_borrowed"] = max(days, 0)
    status, _ = borrow_status(r, today=t)
    r["status"] = status
    r["remind"] = remind_text(r, today=t)
    r["photo_base64"] = _item_photo_base64(conn, r.get("item_id"))
    return r


def _item_photo_base64(conn, item_id):
    """库内物品主图 → base64(照片缺失返回空串,不阻断清单)"""
    if not item_id:
        return ""
    try:
        from home_manager.item_ops import _get_photo_base64
        row = conn.execute("SELECT photo FROM items WHERE id = ?", (item_id,)).fetchone()
        return _get_photo_base64(row["photo"]) if row and row["photo"] else ""
    except Exception:
        return ""


# ── 家人档案 · 成员 ────────────────────────────────────────────────────────


def member_add(conn, name, relation="", note=""):
    """添加成员。称呼非空 + 唯一;重复抛 ValueError"""
    name = (name or "").strip()
    if not name:
        raise ValueError("成员称呼不能为空")
    ensure_tables(conn)
    occurred = now_str()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO family_members (name, relation, note, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, relation or "", note or "", occurred, occurred),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise ValueError(f"成员「{name}」已存在")
    return {"id": cursor.lastrowid, "name": name,
            "relation": relation or "", "note": note or ""}


def member_remove(conn, name):
    """移除成员;其归属物品 owner 回「使用者」。返回 {"removed", "reassigned"}"""
    name = (name or "").strip()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM family_members WHERE name = ?", (name,))
    if not cursor.fetchone():
        raise ValueError(f"成员「{name}」不存在")
    cursor.execute("DELETE FROM family_members WHERE name = ?", (name,))
    cursor.execute("UPDATE items SET owner = ?, updated_at = ? WHERE owner = ?",
                   (DEFAULT_OWNER, now_str(), name))
    conn.commit()
    return {"removed": name, "reassigned": cursor.rowcount}


def member_list(conn):
    """成员列表(含归属物品数)"""
    ensure_tables(conn)
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT id, name, relation, note FROM family_members ORDER BY id"
    ).fetchall()
    counts = dict(cursor.execute(
        "SELECT owner, COUNT(*) AS n FROM items GROUP BY owner"
    ).fetchall())
    return [{"id": r["id"], "name": r["name"], "relation": r["relation"] or "",
             "note": r["note"] or "", "item_count": counts.get(r["name"], 0)}
            for r in rows]


def member_assign(conn, name, item_ids):
    """标记物品归属(批量): items.owner ← 成员称呼。返回实际标记件数"""
    name = (name or "").strip()
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM family_members WHERE name = ?", (name,))
    if not cursor.fetchone():
        raise ValueError(f"成员「{name}」不存在,请先添加成员")
    ids = [int(i) for i in (item_ids or [])]
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    cursor.execute(
        f"UPDATE items SET owner = ?, updated_at = ? WHERE id IN ({placeholders})",
        (name, now_str(), *ids),
    )
    conn.commit()
    return cursor.rowcount


# ── 借用管理 ───────────────────────────────────────────────────────────────


def borrow_add(conn, direction, object_name, item_name="", item_id=None,
               borrowed_at=None, due_date=None, remark=""):
    """登记一笔借用(借出/借入)

    - 借出: item_id 必填(库内物品);物品校验(非废弃/非已借用中);全部位置 → 借用中
    - 借入: item_id 可空(外部物品自由文本);不动物品状态
    返回富化记录(days_borrowed/status/remind)
    """
    direction = (direction or "").strip()
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"非法方向: {direction!r},可选: {'/'.join(VALID_DIRECTIONS)}")
    object_name = (object_name or "").strip()
    if not object_name:
        raise ValueError("借用对象不能为空(家人称呼或外部联系人)")
    ensure_tables(conn)
    cursor = conn.cursor()
    occurred = now_str()

    final_name = (item_name or "").strip()
    if item_id:
        cursor.execute("SELECT id, name FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"物品 {item_id} 不存在")
        final_name = final_name or (row["name"] or "")
    if direction == "借出":
        if not item_id:
            raise ValueError("借出必须指定库内物品(item_id)")
        locs = cursor.execute(
            "SELECT location_status FROM item_locations WHERE item_id = ?", (item_id,)
        ).fetchall()
        statuses = [r["location_status"] for r in locs]
        if "已废弃" in statuses:
            raise ValueError(f"物品「{final_name}」已废弃,不能借出")
        if statuses and all(s == "借用中" for s in statuses):
            raise ValueError(f"物品「{final_name}」正在借用中,不能重复借出")
    if not final_name:
        raise ValueError("物品名称不能为空")

    bdate = borrowed_at or _today_str()
    cursor.execute(
        "INSERT INTO borrow_records (direction, item_id, item_name, object_name, "
        "borrowed_at, due_date, remark, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (direction, item_id, final_name, object_name, bdate,
         due_date or None, remark or "", occurred, occurred),
    )
    record_id = cursor.lastrowid
    if direction == "借出":
        cursor.execute(
            "UPDATE item_locations SET location_status = '借用中', updated_at = ? "
            "WHERE item_id = ?",
            (occurred, item_id),
        )
    conn.commit()
    cursor.execute("SELECT * FROM borrow_records WHERE id = ?", (record_id,))
    return _enrich_record(conn, cursor.fetchone())


def borrow_status(record, today=None):
    """借用记录状态: (status, overdue_days)
    - 已归还 → "已归还"
    - 无约定归还日 → "借用中"
    - 超期(due < today) → "已超期 N 天"
    - 今日到期 → "今日到期"
    - 未到期 → "借用中"
    """
    t = today or date.today()
    if record.get("returned_at"):
        return "已归还", 0
    due = record.get("due_date")
    if not due:
        return "借用中", 0
    try:
        days = (t - date.fromisoformat(due)).days
    except ValueError:
        return "借用中", 0
    if days > 0:
        return f"已超期 {days} 天", days
    if days == 0:
        return "今日到期", 0
    return "借用中", 0


def borrow_return(conn, borrow_id, returned_at=None):
    """确认归还: 写 returned_at;借出记录 → 物品全部位置回「在家」"""
    ensure_tables(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM borrow_records WHERE id = ?", (borrow_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"借用记录 {borrow_id} 不存在")
    r = dict(row)
    if r["returned_at"]:
        raise ValueError(f"借用记录 {borrow_id} 已归还,不能重复归还")
    occurred = returned_at or _today_str()
    cursor.execute(
        "UPDATE borrow_records SET returned_at = ?, updated_at = ? WHERE id = ?",
        (occurred, now_str(), borrow_id),
    )
    if r["direction"] == "借出" and r["item_id"]:
        cursor.execute(
            "UPDATE item_locations SET location_status = '在家', updated_at = ? "
            "WHERE item_id = ?",
            (now_str(), r["item_id"]),
        )
    conn.commit()
    cursor.execute("SELECT * FROM borrow_records WHERE id = ?", (borrow_id,))
    return _enrich_record(conn, cursor.fetchone())


def borrow_list(conn, today=None):
    """借用清单: (borrowed_out, borrowed_in),各按未还在前、新的在前排序"""
    ensure_tables(conn)
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT * FROM borrow_records ORDER BY borrowed_at DESC, id DESC"
    ).fetchall()
    out, inn = [], []
    for r in rows:
        rec = _enrich_record(conn, r, today=today)
        (out if rec["direction"] == "借出" else inn).append(rec)
    return out, inn


def remind_text(record, today=None):
    """催还文案(纯文本 · 转移变体)。借出催对方还;借入提醒自己去还"""
    t = today or date.today()
    obj = record["object_name"]
    item = record["item_name"]
    days = max((t - date.fromisoformat(record["borrowed_at"])).days, 0)
    status, _ = borrow_status(record, today=t)
    due = record.get("due_date")
    if record.get("returned_at"):
        return f"感谢{obj},之前借的{item}已还清"
    if status.startswith("已超期"):
        verb = "方便还一下吗" if record["direction"] == "借出" else "我尽快还你"
        return f"{obj},之前借的{item}已经借了{days}天了,{verb}?"
    if status == "今日到期":
        if record["direction"] == "借出":
            return f"{obj},之前借的{item}今天到归还日了,方便还一下吗?"
        return f"{obj},之前借的{item}今天该还了,我尽快送回去"
    if due:
        return f"{obj},之前借的{item}约定{due}号归还,记得哦" if record["direction"] == "借出" \
            else f"{obj},之前借的{item}约定{due}号归还,我记着呢"
    return f"{obj},之前借的{item}借了{days}天了,记得还哦"


# ── payload(模板注入 · 08 骨架)─────────────────────────────────────────────


def _item_options(conn):
    """可借出物品候选(非废弃): 物品选择器数据源"""
    ensure_tables(conn)
    cursor = conn.cursor()
    rows = cursor.execute("""
        SELECT i.id, i.name, i.photo,
               (SELECT location_status FROM item_locations
                WHERE item_id = i.id ORDER BY id LIMIT 1) AS status
        FROM items i
        ORDER BY i.name
    """).fetchall()
    out = []
    for r in rows:
        if r["status"] == "已废弃":
            continue
        if r["status"] == "借用中":
            out.append({"id": r["id"], "name": r["name"], "status": "借用中", "photo": r["photo"] or ""})
        else:
            out.append({"id": r["id"], "name": r["name"], "status": "在家", "photo": r["photo"] or ""})
    return out


def borrow_list_payload(conn, today=None):
    """借用管理 HTML payload(清单 + 登记选择器数据源)"""
    out, inn = borrow_list(conn, today=today)
    active_out = [r for r in out if r["status"] != "已归还"]
    active_in = [r for r in inn if r["status"] != "已归还"]
    overdue = [r for r in out + inn if r["status"].startswith("已超期")]
    members = [m["name"] for m in member_list(conn)]
    data = {
        "summary": {
            "title": "借用管理",
            "subtitle": "双向区隔 · 超期标记 · 催还文案",
            "metrics": [
                {"label": "借出中", "value": len(active_out)},
                {"label": "借入中", "value": len(active_in)},
                {"label": "超期未还", "value": len(overdue)},
            ],
        },
        "borrowed_out": out,
        "borrowed_in": inn,
        "overdue_count": len(overdue),
        "members": members,
        "items": _item_options(conn),
        "scene_id": "SM7-1",
        "command_cn": "借用",
    }
    return {"status": "ok", "data": data,
            "message": f"借用清单: 借出中 {len(active_out)} · 借入中 {len(active_in)} · 超期 {len(overdue)}"}


def member_list_payload(conn):
    """家人档案 HTML payload(成员 + 归属统计 + 物品勾选清单)"""
    members = member_list(conn)
    total = sum(m["item_count"] for m in members)
    cursor = conn.cursor()
    items = [{"id": r["id"], "name": r["name"], "owner": r["owner"] or "使用者"}
             for r in cursor.execute("SELECT id, name, owner FROM items ORDER BY name")]
    data = {
        "summary": {
            "title": "家人档案",
            "subtitle": "成员 · 物品归属标记",
            "metrics": [
                {"label": "成员数", "value": len(members)},
                {"label": "已标记归属物品", "value": total},
            ],
        },
        "members": members,
        "items": items,
        "total_items": len(items),
        "scene_id": "SM7-2",
        "command_cn": "家人档案",
    }
    return {"status": "ok", "data": data,
            "message": f"家人档案: {len(members)} 位成员 · {total} 件物品已标记归属"}
