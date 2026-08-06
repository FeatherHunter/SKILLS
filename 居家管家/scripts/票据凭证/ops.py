"""SM6 票据凭证域 · 业务操作(ops)

第一性原理: 本域 = 时间权益 + 敏感凭证
  - 权益状态计算(统一原语): days_left = 截止日 - 今天
  - 状态三态: 已过(days_left<0) / 即将到期(0<=days_left<=阈值) / 有效(>阈值)
  - 阈值: 保修/证件 = 30 天; 保养 = 7 天(规则集中定义, 便于调整)
"""
from datetime import datetime, date

# ── 规则常量(集中可调) ──────────────────────────────────────────────
WARRANTY_WARN_DAYS = 30      # 保修: 距到期 ≤30 天 = 即将到期
CERT_WARN_DAYS = 30          # 证件: 距到期 ≤30 天 = 即将到期
MAINTENANCE_WARN_DAYS = 7    # 保养: 距下次保养 ≤7 天 = 即将到期
DEFAULT_RETURN_WINDOW = 7    # 默认退货窗口天数

# 证件/账号类型枚举(规格待细化项, 实施定稿)
CERT_TYPES = ("护照", "身份证", "驾照", "签证", "保险单", "其他")
ACCOUNT_TYPES = ("购物", "银行", "社交", "其他")


def today_str():
    return date.today().isoformat()


def parse_date(s):
    """YYYY-MM-DD 校验, 非法抛 ValueError"""
    if not s:
        raise ValueError("日期不能为空")
    return datetime.strptime(s, "%Y-%m-%d").date()


def days_left(end_date_str):
    """截止日剩余天数(负 = 已过); 非法日期抛 ValueError"""
    end = parse_date(end_date_str)
    return (end - date.today()).days


def mask_number(s):
    """证件号脱敏: 保留后 4 位, 其余 ****; 空值返回 ''"""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) <= 4:
        return "****"
    return "****" + s[-4:]


# ── 购买记录 ────────────────────────────────────────────────────────

def purchase_add(conn, item_id, purchased_at, price=None, channel="",
                 merchant_contact="", receipt_photo="",
                 return_window_days=DEFAULT_RETURN_WINDOW, note=""):
    parse_date(purchased_at)
    if return_window_days < 0:
        raise ValueError("退货窗口天数不能为负")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO purchase_records (item_id, purchased_at, price, channel, "
        "merchant_contact, receipt_photo, return_window_days, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (item_id, purchased_at, price, channel, merchant_contact,
         receipt_photo, return_window_days, note),
    )
    conn.commit()
    return cur.lastrowid


def purchase_item_name(conn, item_id):
    """从 items 表取物品名(只读公共表, 不改)"""
    row = conn.execute("SELECT name FROM items WHERE id = ?", (item_id,)).fetchone()
    return row["name"] if row else f"#{item_id}"


def purchase_list(conn, item_id=None, year=None, month=None):
    """购买记录列表(按购买日倒序)"""
    sql = ("SELECT pr.*, i.name AS item_name FROM purchase_records pr "
           "LEFT JOIN items i ON i.id = pr.item_id WHERE 1=1")
    args = []
    if item_id is not None:
        sql += " AND pr.item_id = ?"
        args.append(item_id)
    if year:
        sql += " AND substr(pr.purchased_at, 1, 4) = ?"
        args.append(str(year))
    if month:
        sql += " AND substr(pr.purchased_at, 6, 2) = ?"
        args.append(f"{int(month):02d}")
    sql += " ORDER BY pr.purchased_at DESC, pr.id DESC"
    rows = conn.execute(sql, args).fetchall()
    out = []
    from datetime import timedelta
    for r in rows:
        d = dict(r)
        d["item_name"] = d["item_name"] or f"#{d['item_id']}"
        if d.get("return_window_days"):
            end = parse_date(d["purchased_at"]) + timedelta(days=d["return_window_days"])
            d["return_end"] = end.isoformat()
            d["return_days_left"] = (end - date.today()).days
        else:
            d["return_end"] = None
            d["return_days_left"] = None
        out.append(d)
    return out


def purchase_stats(conn, year=None):
    """消费统计: 按年过滤 + 按分类聚合(今年/全部)"""
    from collections import defaultdict
    rows = purchase_list(conn, year=year)
    total_price = 0.0
    count = len(rows)
    by_category = defaultdict(lambda: {"count": 0, "total": 0.0})
    for r in rows:
        price = r.get("price") or 0
        total_price += price
        cat = "未分类"
        if r["item_id"]:
            row = conn.execute("SELECT c.name AS cat FROM items i "
                               "LEFT JOIN categories c ON c.id = i.category_id "
                               "WHERE i.id = ?", (r["item_id"],)).fetchone()
            if row and row["cat"]:
                cat = row["cat"]
        by_category[cat]["count"] += 1
        by_category[cat]["total"] += price
    return {
        "count": count,
        "total_price": round(total_price, 2),
        "by_category": [
            {"category": k, "count": v["count"], "total": round(v["total"], 2)}
            for k, v in sorted(by_category.items(), key=lambda x: -x[1]["total"])
        ],
    }


# ── 保修与保养 ──────────────────────────────────────────────────────

def warranty_register(conn, item_id, kind, start_date, duration_days,
                      last_done_date=None, note=""):
    if kind not in ("保修", "保养"):
        raise ValueError("kind 必须是 保修 或 保养")
    parse_date(start_date)
    if duration_days <= 0:
        raise ValueError("时长必须为正整数")
    if kind == "保养" and last_done_date:
        parse_date(last_done_date)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO warranties (item_id, kind, start_date, duration_days, "
        "last_done_date, note) VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, kind, start_date, duration_days, last_done_date, note),
    )
    conn.commit()
    return cur.lastrowid


def _warranty_status(kind, start_date, duration_days, last_done_date):
    """权益状态计算(统一原语)"""
    from datetime import timedelta
    if kind == "保修":
        start = parse_date(start_date)
        end = start + timedelta(days=duration_days)
        dl = (end - date.today()).days
        if dl < 0:
            return {"status": "已过", "days_left": dl, "end_date": end.isoformat()}
        if dl <= WARRANTY_WARN_DAYS:
            return {"status": "即将到期", "days_left": dl, "end_date": end.isoformat()}
        return {"status": "在保", "days_left": dl, "end_date": end.isoformat()}
    # 保养: next_due = last_done + 周期
    base = parse_date(last_done_date or start_date)
    end = base + timedelta(days=duration_days)
    dl = (end - date.today()).days
    if dl < 0:
        return {"status": "到期未做", "days_left": dl, "end_date": end.isoformat()}
    if dl <= MAINTENANCE_WARN_DAYS:
        return {"status": "即将到期", "days_left": dl, "end_date": end.isoformat()}
    return {"status": "已做", "days_left": dl, "end_date": end.isoformat()}


def warranty_list(conn, status_filter=None):
    rows = conn.execute(
        "SELECT w.*, i.name AS item_name FROM warranties w "
        "LEFT JOIN items i ON i.id = w.item_id ORDER BY w.id DESC"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["item_name"] = d["item_name"] or f"#{d['item_id']}"
        st = _warranty_status(d["kind"], d["start_date"], d["duration_days"],
                              d["last_done_date"])
        d.update(st)
        d["events"] = warranty_events(conn, d["id"])
        d["repair_count"] = sum(1 for e in d["events"] if e["event_type"] == "维修")
        out.append(d)
    if status_filter and status_filter != "全部":
        out = [d for d in out if d["status"] == status_filter]
    return out


def warranty_repair(conn, warranty_id, occurred_at, cost=0, note=""):
    """记录维修(服务事件)"""
    parse_date(occurred_at)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO service_events (warranty_id, occurred_at, event_type, cost, note) "
        "VALUES (?, ?, '维修', ?, ?)",
        (warranty_id, occurred_at, cost, note),
    )
    conn.commit()
    return cur.lastrowid


def warranty_maintain(conn, warranty_id, occurred_at, note=""):
    """保养执行: 更新 last_done_date + 记事件(同事务)"""
    parse_date(occurred_at)
    cur = conn.cursor()
    cur.execute("SELECT kind FROM warranties WHERE id = ?", (warranty_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"保修/保养记录 #{warranty_id} 不存在")
    if row["kind"] != "保养":
        raise ValueError("只有保养类记录可以执行保养")
    cur.execute(
        "INSERT INTO service_events (warranty_id, occurred_at, event_type, cost, note) "
        "VALUES (?, ?, '保养执行', 0, ?)",
        (warranty_id, occurred_at, note),
    )
    cur.execute("UPDATE warranties SET last_done_date = ?, updated_at = "
                "datetime('now','localtime') WHERE id = ?", (occurred_at, warranty_id))
    conn.commit()
    return cur.lastrowid


def warranty_events(conn, warranty_id):
    rows = conn.execute(
        "SELECT * FROM service_events WHERE warranty_id = ? ORDER BY occurred_at DESC",
        (warranty_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── 证件 ────────────────────────────────────────────────────────────

def cert_add(conn, cert_type, holder, cert_number, issued_at, expires_at,
             photo="", note=""):
    if cert_type not in CERT_TYPES:
        raise ValueError(f"证件类型必须是 {'/'.join(CERT_TYPES)}")
    parse_date(expires_at)
    if issued_at:
        parse_date(issued_at)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO certificates (cert_type, holder, cert_number, issued_at, "
        "expires_at, photo, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (cert_type, holder, cert_number, issued_at, expires_at, photo, note),
    )
    conn.commit()
    return cur.lastrowid


def cert_list(conn):
    """证件清单(按到期日升序; 号码一律脱敏输出)"""
    rows = conn.execute(
        "SELECT * FROM certificates ORDER BY expires_at ASC, id DESC"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        # 敏感: 明文证件号仅落库, 永不进入 payload/HTML/复制数据
        d.pop("cert_number", None)
        d["number_masked"] = mask_number(r["cert_number"] or "")
        d["days_left"] = days_left(d["expires_at"])
        if d["days_left"] < 0:
            d["cert_status"] = "已过期"
        elif d["days_left"] <= CERT_WARN_DAYS:
            d["cert_status"] = "即将到期"
        else:
            d["cert_status"] = "有效"
        out.append(d)
    return out


# ── 顺路提醒(到期类互提, 无 cron) ───────────────────────────────────

def reminders_warranty(conn, warn_days=WARRANTY_WARN_DAYS):
    """保修/保养即将到期或已过 → 供其他到期类页面注入"""
    out = []
    for w in warranty_list(conn):
        if w["status"] in ("已过", "即将到期", "到期未做"):
            out.append({
                "kind": w["kind"],
                "item_name": w["item_name"],
                "status": w["status"],
                "days_left": w["days_left"],
                "end_date": w["end_date"],
            })
    return out


def reminders_cert(conn, warn_days=CERT_WARN_DAYS):
    """证件即将到期/已过期 → 供其他到期类页面注入"""
    return [
        {"cert_type": c["cert_type"], "holder": c["holder"],
         "status": c["cert_status"], "days_left": c["days_left"],
         "expires_at": c["expires_at"]}
        for c in cert_list(conn)
        if c["cert_status"] in ("即将到期", "已过期")
    ]
