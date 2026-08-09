# stats/__init__.py - SM4 统计总览域(T5)
#
# 隔离契约(实施编排 map):本域只动 scripts/stats/ + templates/stats/ +
# scenes/SM4 + tests/test_sm4.py;公共层(CLI 注册/render 映射)只做最小注册。
# 数据基础:items / item_locations / categories / item_tags(现状 schema);
# inventory_records 为 D1 新表,本域按 D1 约定结构查询,表不存在时优雅空态。

from datetime import datetime

from home_manager.tag_ops import get_tags

SKILL_VERSION = "居家管家 v2.0 (SM4 T5)"
ACTIVE_STATUS_EXCLUDE = ("已废弃", "已用完")


def build_meta(scene_id, wake_word, command_cn, render_cmd, chain="", source="items"):
    """08 规范 · 复制数据/复制日志的 META 字段(与卡路里同构)"""
    return {
        "scene_id": scene_id,
        "wake_word": wake_word,
        "command_cn": command_cn,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "render_cmd": render_cmd,
        "chain": chain,
        "source": source,
        "version": SKILL_VERSION,
    }


def photo_b64(photo, full=False):
    """items.photo 相对路径 → base64 缩略图(无图/读失败 → None)。

    复用 home_manager.item_ops._get_photo_base64 的缩略图逻辑(issue #199:
    统物品/闲置/过期等 stats 页面不再内嵌手机原图,避免 HTML 体积爆炸)。
    """
    from home_manager.item_ops import _get_photo_base64
    return _get_photo_base64(photo, full=full)


def _active_condition(alias="items"):
    """活跃物品条件:至少一个位置非 已废弃/已用完(alias 为 items 表别名)"""
    ph = ",".join("?" * len(ACTIVE_STATUS_EXCLUDE))
    return (
        f"EXISTS (SELECT 1 FROM item_locations il "
        f"WHERE il.item_id = {alias}.id AND il.location_status NOT IN ({ph}))",
        list(ACTIVE_STATUS_EXCLUDE),
    )


def top_category_rows(conn, exclude_status=False):
    """顶级 L1 分类分布: [{id, name, count, total_value}] (count 降序)

    exclude_status=True 时只统计活跃物品(排除 已废弃/已用完)。
    """
    cursor = conn.cursor()
    extra = ""
    params = []
    if exclude_status:
        cond, params = _active_condition(alias="i")
        extra = f" AND {cond}"
    cursor.execute(
        f"""
        WITH RECURSIVE cat_path AS (
          SELECT id, parent_id, name, 1 AS lvl
          FROM categories WHERE parent_id IS NULL
          UNION ALL
          SELECT c.id, c.parent_id, c.name, cp.lvl + 1
          FROM categories c JOIN cat_path cp ON c.parent_id = cp.id
        )
        SELECT cp.id, cp.name,
               COUNT(i.id) AS cnt,
               ROUND(SUM(COALESCE(i.purchase_price, 0)), 2) AS total_value
        FROM cat_path cp
        LEFT JOIN items i ON i.category_id = cp.id
        WHERE cp.lvl = 1 {extra}
        GROUP BY cp.id, cp.name
        HAVING cnt > 0
        ORDER BY cnt DESC
        """,
        params,
    )
    rows = cursor.fetchall()
    return [
        {"id": r["id"], "name": r["name"], "count": r["cnt"],
         "total_value": r["total_value"] or 0}
        for r in rows
    ]


def expand_category_ids(conn, cat_id):
    """从 cat_id 递归展开全部下级 id(含自身)"""
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH RECURSIVE cat_tree AS (
            SELECT id FROM categories WHERE id = ?
            UNION ALL
            SELECT c.id FROM categories c JOIN cat_tree t ON c.parent_id = t.id
        )
        SELECT id FROM cat_tree
        """,
        (cat_id,),
    )
    return [r["id"] for r in cursor.fetchall()]


def item_with_photo(row, conn):
    """row(item_locations JOIN items 行) → 展示 dict(带 tags/照片/顶级分类)"""
    tags = get_tags(conn, row["id"])
    photo = photo_b64(row["photo"]) if row["photo"] else None
    result = {
        "id": row["id"],
        "name": row["name"],
        "category_name": row["category_name"] or "(未分类)",
        "category_id": row["category_id"],
        "top_category_id": row["top_category_id"],
        "top_category_name": row["top_category_name"] or "(未分类)",
        "location": row["location"],
        "quantity": row["quantity"],
        "location_status": row["location_status"] or "在家",
        "photo_base64": photo,
        "tags": tags,
    }
    return result
