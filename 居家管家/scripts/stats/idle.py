# idle.py - SM4-2 闲置物品检测(stats_idle · 查闲置)
#
# 口径(实施定稿 2026-08-05):
#   闲置天数 = last_accessed_at 有值 → (今天 - 该日)天,来源「访问记录」;
#              无值 → (今天 - created_at 日)天,来源「估算」(规格明示:无最后
#              使用时间 → 录入时间估算 + 标注「估算」)
#   阈值默认 90 天,可调 90/180/365(CLI --days 校验,非法拒绝)
#   排除 已废弃/已用完(物品至少一个位置非这两种状态)
#   AI 断舍离建议一句:规则式生成(按顶级分类集中度)

from datetime import datetime, timezone

from . import (
    build_meta, item_with_photo, expand_category_ids, _active_condition,
    ACTIVE_STATUS_EXCLUDE,
)

ALLOWED_THRESHOLDS = (90, 180, 365)
DEFAULT_THRESHOLD = 90


def _today():
    # 对齐 SQL date('now') 口径(UTC): 本地凌晨 0-8 点 date.today() 与 UTC 差一天,
    # 导致 days_idle 凌晨漂移 ±1(test seed 已是 UTC 口径, 2026-08-10 修复)
    return datetime.now(timezone.utc).date()


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, TypeError):
        return None


def _idle_rows(conn, threshold, category_id=None):
    """活跃物品 + 闲置天数 + 来源(访问记录/估算),闲置天数降序"""
    cursor = conn.cursor()
    cond, params = _active_condition(alias="i")
    cat_sql = ""
    if category_id:
        ids = expand_category_ids(conn, category_id)
        if not ids:
            return []
        ph = ",".join("?" * len(ids))
        cat_sql = f" AND i.category_id IN ({ph})"
        params = [*params, *ids]

    cursor.execute(
        f"""
        SELECT i.id, i.name, i.photo, i.category_id,
               i.last_accessed_at, i.created_at,
               c.name AS category_name,
               il.location, il.quantity, il.location_status
        FROM items i
        JOIN item_locations il ON il.item_id = i.id
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE {cond} {cat_sql}
        """,
        params,
    )
    rows = cursor.fetchall()

    # 每物品取一个代表位置(闲置统计按物品,不按位置)
    by_item = {}
    for r in rows:
        if r["id"] not in by_item:
            by_item[r["id"]] = dict(r)
    today = _today()
    items = []
    for it in by_item.values():
        la = _parse_dt(it["last_accessed_at"])
        if la is not None:
            days_idle = (today - la).days
            source = "访问记录"
        else:
            created = _parse_dt(it["created_at"])
            if created is None:
                continue
            days_idle = (today - created).days
            source = "估算"
        if days_idle < threshold:
            continue
        items.append({
            "id": it["id"],
            "name": it["name"],
            "category_id": it["category_id"],
            "category_name": it["category_name"] or "(未分类)",
            "location": it["location"],
            "quantity": it["quantity"] or 1,
            "location_status": it["location_status"] or "在家",
            "days_idle": days_idle,
            "source": source,
            "photo_base64": None,  # 下方统一补
            "tags": [],
        })

    # 补照片/标签/顶级分类
    cursor2 = conn.cursor()
    for it in items:
        cursor2.execute("SELECT photo FROM items WHERE id = ?", (it["id"],))
        prow = cursor2.fetchone()
        from . import photo_b64
        from home_manager.tag_ops import get_tags
        it["photo_base64"] = photo_b64(prow["photo"]) if prow and prow["photo"] else None
        it["tags"] = get_tags(conn, it["id"])
        cursor2.execute(
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
            (it["category_id"],),
        )
        tro = cursor2.fetchone()
        if tro:
            it["top_category_id"] = tro["top_id"]
            it["top_category_name"] = tro["top_name"] or "(未分类)"
        else:
            it["top_category_id"] = None
            it["top_category_name"] = "(未分类)"

    items.sort(key=lambda x: -x["days_idle"])
    return items


def _suggestion(items):
    """AI 断舍离建议一句(规则式): 按顶级分类集中度"""
    if not items:
        return "没有闲置物品,衣橱状态良好 ✨"
    from collections import Counter
    c = Counter(it["top_category_name"] or "其他" for it in items)
    top_name, top_cnt = c.most_common(1)[0]
    n = len(items)
    if top_cnt == n:
        return f"{n} 件闲置全部集中在「{top_name}」,处理它收益最大"
    pct = round(top_cnt * 100 / n)
    return f"{n} 件闲置中 {top_cnt} 件是「{top_name}」({pct}%),建议优先处理{top_name}"


def _category_filter(conn, items):
    """闲置物品的顶级分类分布(前端下拉)"""
    seen = {}
    for it in items:
        tid = it["top_category_id"]
        if tid is None:
            continue
        if tid not in seen:
            seen[tid] = {"id": tid, "name": it["top_category_name"], "count": 0}
        seen[tid]["count"] += 1
    return sorted(seen.values(), key=lambda x: -x["count"])


def idle_payload(conn, days=DEFAULT_THRESHOLD, category_id=None):
    """闲置检测 payload(data 部分)"""
    if days not in ALLOWED_THRESHOLDS:
        raise ValueError(
            f"闲置阈值必须为 {'/'.join(str(t) for t in ALLOWED_THRESHOLDS)} 天,当前 {days}")
    items = _idle_rows(conn, days, category_id)
    return {
        "summary": {
            "title": "闲置物品检测",
            "subtitle": f"超过 {days} 天未使用 · 处理决策:扔/送/先留着",
            "metrics": [
                {"label": "闲置件数", "value": f"{len(items)} 件"},
                {"label": "闲置阈值", "value": f"{days} 天"},
            ],
        },
        "meta": build_meta(
            "stats_idle", "查闲置", "查闲置",
            render_cmd=f"python scripts/home_manager.py stats --type idle --days {days}",
            chain=f"意图:闲置检测 → last_accessed_at/created_at 估算({days} 天) → 处理闭环",
        ),
        "threshold": days,
        "allowed": list(ALLOWED_THRESHOLDS),
        "suggestion": _suggestion(items),
        "categories": _category_filter(conn, items),
        "items": items,
        "empty": not items,
    }
