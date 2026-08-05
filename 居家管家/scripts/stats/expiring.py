# expiring.py - SM4-3 过期检查与预告(stats_expiring · 查过期)
#
# 升级自 v1 _stats_expiring_payload(inventory_ops):
#   + META 注入(复制数据/复制日志 08 契约)
#   + 预告天数参数 7/30/90(CLI --days 校验)
#   + 顶级分类筛选下拉
#   + 空态/照片/标签完整
# 数据基础: item_locations.expiration_date(现状 schema 已有)

from datetime import date

from home_manager.inventory_ops import _stats_expiring_query
from . import build_meta

ALLOWED_DAYS = (7, 30, 90)
DEFAULT_DAYS = 30


def _today():
    return date.today()


def _top_category_of(conn, category_id):
    """category_id → (top_id, top_name)"""
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH RECURSIVE anc AS (
          SELECT id, parent_id, id AS top_id, name AS top_name, 1 AS lvl
          FROM categories WHERE id = ?
          UNION ALL
          SELECT c.id, c.parent_id, anc.top_id, anc.top_name, anc.lvl + 1
          FROM categories c JOIN anc ON c.id = anc.parent_id
        )
        SELECT top_id, top_name FROM anc ORDER BY lvl DESC LIMIT 1
        """,
        (category_id,),
    )
    r = cursor.fetchone()
    return (r["top_id"], r["top_name"] or "(未分类)") if r else (None, "(未分类)")


def _category_filter(conn, items):
    """过期物品的顶级分类分布(前端下拉)"""
    seen = {}
    for it in items:
        tid = it["top_category_id"]
        if tid is None:
            continue
        if tid not in seen:
            seen[tid] = {"id": tid, "name": it["top_category_name"], "count": 0}
        seen[tid]["count"] += 1
    return sorted(seen.values(), key=lambda x: -x["count"])


def expiring_payload(conn, limit=50, days=DEFAULT_DAYS, expired_only=False,
                     category_id=None):
    """过期检查与预告 payload(data 部分)"""
    if days not in ALLOWED_DAYS:
        raise ValueError(
            f"预告天数必须为 {'/'.join(str(d) for d in ALLOWED_DAYS)} 天,当前 {days}")

    rows, thresholds = _stats_expiring_query(
        conn, days=days, expired_only=expired_only,
        category_id=category_id, limit=limit,
    )

    from home_manager.tag_ops import get_tags
    from . import photo_b64
    cursor = conn.cursor()
    items = []
    for r in rows:
        days_left = r["days_left"]
        if days_left < 0:
            severity = "danger"
        elif days_left <= 7:
            severity = "warn"
        else:
            severity = "info"
        cursor.execute("SELECT photo FROM items WHERE id = ?", (r["id"],))
        prow = cursor.fetchone()
        cursor.execute("SELECT category_id FROM items WHERE id = ?", (r["id"],))
        crow = cursor.fetchone()
        top_id, top_name = None, "(未分类)"
        if crow and crow["category_id"]:
            top_id, top_name = _top_category_of(conn, crow["category_id"])
        items.append({
            "id": r["id"],
            "name": r["name"],
            "category_name": r["category"] or "(未分类)",
            "top_category_id": top_id,
            "top_category_name": top_name,
            "location": r["location"],
            "quantity": r["quantity"],
            "location_status": r["location_status"] or "在家",
            "expiration_date": r["expiration_date"],
            "days_left": days_left,
            "severity": severity,
            "photo_base64": photo_b64(prow["photo"]) if prow and prow["photo"] else None,
            "tags": get_tags(conn, r["id"]),
        })

    expired = sum(1 for it in items if it["days_left"] < 0)
    in_3 = sum(1 for it in items if 0 <= it["days_left"] <= 3)
    in_7 = sum(1 for it in items if 0 <= it["days_left"] <= 7)
    in_days = sum(1 for it in items if it["days_left"] <= days)

    return {
        "summary": {
            "title": "过期检查与预告",
            "subtitle": (
                f"已过期 + 未来 {days} 天到期预告 · 勾选处理闭环"
                if items else "没有即将过期的物品,放心 ✨"
            ),
            "metrics": [
                {"label": "已过期", "value": f"{expired} 件", "severity": "danger"},
                {"label": "3天内", "value": f"{in_3} 件", "severity": "warn"},
                {"label": "7天内", "value": f"{in_7} 件", "severity": "warn"},
                {"label": f"{days}天内", "value": f"{in_days} 件", "severity": "info"},
            ],
        },
        "meta": build_meta(
            "stats_expiring", "查过期", "查过期",
            render_cmd=f"python scripts/home_manager.py stats --type expiring --days {days}",
            chain="意图:过期检查 → item_locations.expiration_date → 勾选处理闭环",
        ),
        "days": days,
        "allowed": list(ALLOWED_DAYS),
        "categories": _category_filter(conn, items),
        "items": items,
        "empty": not items,
    }
