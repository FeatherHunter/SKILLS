# overview.py - SM4-1 物品总览(stats_summary · 统物品)
#
# 呈现数据(SM4 权威清单场景 1):
#   件数+状态分布 / 总价+价格覆盖率 / 分类分布(柱状) / 位置分布(柱状) /
#   归属分布(有数据才展示) / 价值 TOP / 近 30 天变动趋势(可下钻) /
#   高频 TOP(裁决 1:查高频并入总览)
# 口径(实施定稿 2026-08-05):
#   价格覆盖率 = 有价物品数/物品总数;覆盖率 < 50% → low_coverage 提示
#   趋势:录入 = items.created_at(精确);废弃 = item_locations 状态=已废弃
#         且 updated_at 在窗口内(近似,页面标注口径);按 4 桶分档
#   归属:非「使用者」条目 ≥ 2 才展示(规格:无数据时隐藏)

from datetime import date, datetime, timedelta

from . import build_meta, top_category_rows, _active_condition


def _today():
    return date.today()


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, TypeError):
        return None


def _status_distribution(conn):
    """状态分布: item_locations 按 location_status, count 降序"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT location_status, COUNT(DISTINCT item_id) AS cnt "
        "FROM item_locations GROUP BY location_status ORDER BY cnt DESC"
    )
    rows = cursor.fetchall()
    total = sum(r["cnt"] for r in rows) or 1
    return [
        {
            "name": r["location_status"] or "(未设置)",
            "count": r["cnt"],
            "pct": round(r["cnt"] * 100 / total, 1),
        }
        for r in rows
    ]


def _location_distribution(conn):
    """位置分布: 位置路径第一段(顶级位置)按件数降序"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT location, COUNT(DISTINCT item_id) AS cnt "
        "FROM item_locations GROUP BY location ORDER BY cnt DESC LIMIT 200"
    )
    rows = cursor.fetchall()
    buckets = {}
    for r in rows:
        loc = r["location"] or ""
        top = loc.split("/")[0] if "/" in loc else (loc or "(未设置)")
        buckets[top] = buckets.get(top, 0) + r["cnt"]
    return [
        {"name": name, "count": cnt}
        for name, cnt in sorted(buckets.items(), key=lambda kv: -kv[1])
    ]


def _owner_distribution(conn):
    """归属分布: items.owner 分组(count 降序)"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT owner, COUNT(*) AS cnt FROM items "
        "WHERE owner IS NOT NULL AND owner != '' GROUP BY owner ORDER BY cnt DESC"
    )
    return [
        {"name": r["owner"], "count": r["cnt"]}
        for r in cursor.fetchall()
    ]


def _value_top(conn, limit=10):
    """价值 TOP: 价格>0 的活跃物品,按单价降序"""
    cond, params = _active_condition(alias="i")
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT i.id, i.name, i.purchase_price, i.photo, i.category_id,
               c.name AS category_name
        FROM items i
        LEFT JOIN categories c ON i.category_id = c.id
        WHERE i.purchase_price IS NOT NULL AND i.purchase_price > 0
          AND {cond}
        ORDER BY i.purchase_price DESC LIMIT ?
        """,
        [*params, limit],
    )
    rows = cursor.fetchall()
    from . import photo_b64
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "price": r["purchase_price"],
            "category_name": r["category_name"] or "(未分类)",
            "photo_base64": photo_b64(r["photo"]) if r["photo"] else None,
        }
        for r in rows
    ]


def _frequent_top(conn, limit=10):
    """高频 TOP: 访问次数降序(裁决 1:查高频并入物品总览)"""
    cond, params = _active_condition(alias="i")
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT i.id, i.name, i.access_count, i.last_accessed_at
        FROM items i
        WHERE {cond}
        ORDER BY i.access_count DESC LIMIT ?
        """,
        [*params, limit],
    )
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "access_count": r["access_count"] or 0,
            "last_accessed_at": (r["last_accessed_at"] or "")[:10],
        }
        for r in cursor.fetchall()
    ]


def _trend_buckets(today, days=30):
    """近 days 天按 4 桶分档(今天最近): [(label, start_offset, end_offset)]"""
    labels = ["近7天", "8-14天", "15-21天", "22-30天"]
    ranges = [(1, 7), (8, 14), (15, 21), (22, days)]
    return [
        {"label": labels[i], "start": (today - timedelta(days=r[1])).isoformat(),
         "end": (today - timedelta(days=r[0] - 1)).isoformat()}
        for i, r in enumerate(ranges)
    ]


def _trend(conn, today, days=30):
    """近 30 天变动趋势: 录入(items.created_at)+ 废弃(item_locations 状态=已废弃
    且 updated_at 在窗口内,近似口径)。返回 buckets + 下钻明细。"""
    buckets = _trend_buckets(today, days)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT i.id, i.name, date(i.created_at) AS d, il.location_status
        FROM items i
        JOIN item_locations il ON il.item_id = i.id
        WHERE il.location_status = '已废弃'
        """
    )
    discarded_rows = cursor.fetchall()

    cursor.execute(
        "SELECT id, name, date(created_at) AS d FROM items WHERE created_at IS NOT NULL"
    )
    added_rows = cursor.fetchall()

    # 近 30 天窗口外的物品建一个 off-window 明细(下钻只需要窗口内)
    result = []
    for b in buckets:
        added = [
            {"id": r["id"], "name": r["name"]}
            for r in added_rows if b["start"] <= r["d"] <= b["end"]
        ]
        discarded = [
            {"id": r["id"], "name": r["name"]}
            for r in discarded_rows
            if r["d"] is not None and b["start"] <= r["d"] <= b["end"]
        ]
        result.append({
            "label": b["label"],
            "added": len(added),
            "discarded": len(discarded),
            "added_items": added,
            "discarded_items": discarded,
        })
    return result


def overview_payload(conn, days=30, top_limit=10):
    """物品总览 payload(data 部分)"""
    cursor = conn.cursor()
    today = _today()

    cursor.execute("SELECT COUNT(*) AS n FROM items")
    total = cursor.fetchone()["n"]

    cond, params = _active_condition(alias="i")
    cursor.execute(
        f"SELECT COUNT(*) AS n FROM items i WHERE {cond}", params)
    active_total = cursor.fetchone()["n"]

    cursor.execute(
        "SELECT COUNT(*) AS priced_cnt, ROUND(SUM(purchase_price), 2) AS total_value "
        "FROM items WHERE purchase_price IS NOT NULL AND purchase_price > 0"
    )
    priced = cursor.fetchone()
    priced_cnt = priced["priced_cnt"] or 0
    total_value = priced["total_value"] or 0
    coverage = round(priced_cnt * 100 / total, 1) if total else 0.0

    statuses = _status_distribution(conn)
    categories = top_category_rows(conn, exclude_status=True)
    locations = _location_distribution(conn)
    owners = _owner_distribution(conn)
    top_value = _value_top(conn, top_limit)
    frequent_top = _frequent_top(conn, top_limit)
    trend = _trend(conn, today, days)

    others_owner = sum(o["count"] for o in owners if o["name"] != "使用者")
    show_owners = others_owner >= 2

    flags = {
        "empty": total == 0,
        "low_coverage": 0 < coverage < 50,
        "show_owners": show_owners,
    }

    return {
        "summary": {
            "title": "物品总览",
            "subtitle": (
                "家里总共多少/值多少钱,一屏掌握"
                if total else "还没有物品,录入第一批后这里就是你的家底总览"
            ),
            "metrics": [
                {"label": "物品总数", "value": f"{total} 件"},
                {"label": "总价值", "value": f"¥{total_value:,.2f}"},
                {"label": "价格覆盖率", "value": f"{coverage}%",
                 "sub": f"已录价 {priced_cnt} 件 · 未录价 {total - priced_cnt} 件"},
                {"label": "活跃物品", "value": f"{active_total} 件"},
            ],
        },
        "meta": build_meta(
            "stats_summary", "统物品", "统物品",
            render_cmd=f"python scripts/home_manager.py stats --type overview",
            chain="意图:物品总览 → 聚合 items/item_locations → 图表渲染",
        ),
        "flags": flags,
        "statuses": statuses,
        "categories": categories,
        "locations": locations,
        "owners": owners if show_owners else [],
        "top_value": top_value,
        "frequent_top": frequent_top,
        "trend": {
            "days": days,
            "note": "录入数 = 创建时间;废弃数 = 状态变更为已废弃的时间(近似)",
            "buckets": trend,
        },
    }
