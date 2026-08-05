# 位置/tree.py - 位置树组件(共享组件 · T3 归属并冻结)
#
# map 并发约定(2026-08-05):共享组件归属 = 位置树=T3(随首个使用域创建并冻结);
# 演进(供 SM1 筛选浏览 2-4 等复用)= 公共层 ISSUE + review。
#
# 纯展示数据构建:树结构隐含在规范化路径字符串;节点 = 路径段聚合,
# 空位置 = location_nodes 中无物品引用的节点(先建后放)。
# 活跃口径:排除 location_status IN (已废弃, 已用完)(与 stats _active_condition 一致)。
from .schema import normalize_path, SEP


def _active_location_rows(conn):
    """全部活跃位置条目(排除 已废弃/已用完): [(location, item_id, ...)]"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT il.location, il.item_id, il.quantity, il.location_status,
               i.name AS item_name, i.photo, i.id
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE il.location IS NOT NULL AND il.location != ''
          AND il.location_status NOT IN ('已废弃', '已用完')
        ORDER BY il.location, i.id
        """
    )
    return [dict(r) for r in cursor.fetchall()]


def _node_paths(conn):
    """location_nodes 全部规范化路径(空位置节点也在此)"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT path FROM location_nodes ORDER BY path")
    except Exception:
        return []
    return [r["path"] for r in cursor.fetchall()]


def all_paths(conn):
    """全部有效位置路径:条目位置 ∪ 节点位置(规范化,去重,排序)"""
    seen = {}
    for row in _active_location_rows(conn):
        p = normalize_path(row["location"])
        if p:
            seen[p] = seen.get(p, 0) + row["quantity"]
    for p in _node_paths(conn):
        np = normalize_path(p)
        if np:
            seen.setdefault(np, 0)
    return sorted(seen.items())  # [(path, 数量), ...]


def _items_at(conn, path):
    """位于 path 自身(非子树)的活跃物品(位置条目)"""
    rows = _active_location_rows(conn)
    out = []
    for r in rows:
        p = normalize_path(r["location"])
        if p == path:
            out.append({
                "id": r["item_id"],
                "name": r["item_name"],
                "quantity": r["quantity"],
                "location_status": r["location_status"] or "在家",
                "photo": r["photo"],
            })
    return out


def _subtree_count(conn, path):
    """path 子树(含自身)活跃物品条目数(按位置条目计件)"""
    n = 0
    for r in _active_location_rows(conn):
        p = normalize_path(r["location"])
        if p and (p == path or p.startswith(path + SEP)):
            n += r["quantity"]
    return n


def build_tree(conn, current_path=None, with_empty=True):
    """位置树组件(冻结接口):构建当前层视图数据

    参数:
      current_path: 当前所在路径(None = 顶层)
      with_empty: 是否包含空位置节点(location_nodes 无物品引用)

    返回 dict:
      current_path / current_name / breadcrumbs [{name, path}]
      children [{name, path, count, has_children, empty}]  下一层节点(聚合段)
      items [{id, name, quantity, location_status, photo}] 当前层自身物品
      empty_hints [{path, name}] 子树内的空位置节点(导航空层时引导)
    """
    paths = all_paths(conn)
    if current_path is None:
        depth = 0
        prefix = ""
        cur = ""
        parent_name = "(全屋)"
    else:
        cur = normalize_path(current_path)
        if cur is None:
            cur = ""
        depth = len(cur.split(SEP)) if cur else 0
        prefix = cur + SEP if cur else ""
        parent_name = cur.split(SEP)[-1] if cur else "(全屋)"

    # 下一层 = 第 depth+1 段
    children = {}
    for p, qty in paths:
        if not p.startswith(prefix):
            continue
        rest = p[len(prefix):]
        segs = rest.split(SEP)
        if not segs or not segs[0]:
            continue
        child_name = segs[0]
        child_path = (cur + SEP if cur else "") + child_name
        node = children.setdefault(child_name, {
            "name": child_name, "path": child_path,
            "count": 0, "has_children": False, "empty": False,
        })
        node["count"] += qty
        if len(segs) > 1:
            node["has_children"] = True

    # 空位置节点补进 children(无物品引用)
    if with_empty:
        for p, qty in paths:
            if qty > 0:
                continue
            if not p.startswith(prefix):
                continue
            rest = p[len(prefix):]
            segs = rest.split(SEP)
            if not segs or not segs[0]:
                continue
            child_path = (cur + SEP if cur else "") + segs[0]
            if child_path == p and child_path not in {c["path"] for c in children.values()}:
                children[segs[0]] = {"name": segs[0], "path": child_path,
                                     "count": 0, "has_children": False, "empty": True}

    # 当前层自身物品 + 空位置引导
    items = _items_at(conn, cur) if cur else _items_at_root(conn, paths)
    empty_hints = []
    if with_empty:
        for p, qty in paths:
            if qty > 0 or not p:
                continue
            if p.startswith(prefix) and p != (cur + SEP if cur else "") and not any(
                    c["path"] == p for c in children.values()):
                empty_hints.append({"path": p, "name": p.split(SEP)[-1]})

    breadcrumbs = []
    if cur:
        parts = cur.split(SEP)
        acc = ""
        for i, part in enumerate(parts):
            acc = part if not acc else acc + SEP + part
            breadcrumbs.append({"name": part, "path": acc})

    children_list = sorted(children.values(), key=lambda c: (-c["count"], c["name"]))
    for c in children_list:
        c["count"] = _subtree_count(conn, c["path"])
        c["empty"] = c["count"] == 0

    return {
        "current_path": cur,
        "current_name": parent_name,
        "breadcrumbs": breadcrumbs,
        "children": children_list,
        "items": items,
        "empty_hints": empty_hints,
        "total_paths": len(paths),
    }


def _items_at_root(conn, paths):
    """顶层(无前缀)自身物品:位置路径仅 1 段"""
    out = []
    for r in _active_location_rows(conn):
        p = normalize_path(r["location"])
        if p and SEP not in p:
            out.append({
                "id": r["item_id"], "name": r["item_name"],
                "quantity": r["quantity"],
                "location_status": r["location_status"] or "在家",
                "photo": r["photo"],
            })
    return out


def tree_overview(conn):
    """位置树总览(位置管理 1-1 查看):全树节点(含层级) + 每节点计数

    返回: [{path, name, depth, count, has_children, empty}] 前序遍历
    """
    paths = all_paths(conn)
    rows = []
    for p, qty in paths:
        depth = len(p.split(SEP))
        rows.append({
            "path": p,
            "name": p.split(SEP)[-1],
            "depth": depth,
            "count": _subtree_count(conn, p),
            "empty": qty == 0,
        })
    return rows
