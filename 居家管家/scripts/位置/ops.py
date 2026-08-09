# 位置/ops.py - 位置管理/固定位/收纳建议 DB 操作(SM2)
#
# 记录契约(SM2 通用规则):位置变更写 item_events(本域管理操作同样写事件);
# 事件类型复用 SM1 记录契约底座(event_type 字符串 + 代码层扩展,不加 DB CHECK)。
import json
from datetime import datetime

from .schema import (normalize_path, validate_segments, ensure_schema,
                     _prefix_clause, is_descendant_or_self, SEP)
from . import tree as tree_mod

# 事件类型扩展(代码层枚举 · 记录契约 #4:新域可扩展)
EVENT_FIXED_SPOT_CHANGED = "fixed_spot_changed"
EVENT_LOCATION_RENAMED = "location_renamed"      # 位置管理改名/合并(前缀级联)
EVENT_LOCATION_CREATED = "location_created"      # 新建位置(体系级)

ACTIVE_STATUS_EXCLUDE = ("已废弃", "已用完")


def _conn():
    from home_manager.db import get_conn
    conn = get_conn()
    ensure_schema(conn)
    return conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _record_event(conn, item_id, event_type, summary, payload=None,
                  scene_id=None, cli_cmd=None):
    """写 item_events(同一 conn 原子;表载体 = SM1 记录契约底座)"""
    from 物品.events import record_event
    return record_event(conn, item_id, event_type, summary, payload,
                        scene_id=scene_id, cli_cmd=cli_cmd)


def _find_item(conn, item_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, category_id, purchase_price, remark, photo, "
        "access_count, last_accessed_at FROM items WHERE id = ?",
        (item_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _loc_row(conn, item_id):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, location, quantity, reason, location_status "
        "FROM item_locations WHERE item_id = ? ORDER BY id LIMIT 1",
        (item_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _category_name(conn, category_id):
    cursor = conn.cursor()
    cursor.execute("SELECT name, seed_key FROM categories WHERE id = ?", (category_id,))
    row = cursor.fetchone()
    return (dict(row) if row else None) if row else None


# ═══════════════════ 位置管理(1-1) ═══════════════════

def manage_payload(conn):
    """位置管理查看:树总览 + 相似位置检测(规范化)+ 计数"""
    ensure_schema(conn)
    nodes = tree_mod.tree_overview(conn)
    similar = detect_similar(conn)
    return {
        "nodes": nodes,
        "similar_groups": similar,
        "total_nodes": len(nodes),
    }


def detect_similar(conn):
    """相似位置检测(规范化):段拼接等价分组

    例:「卧室/东南角/小冰箱上」vs「卧室东南角/小冰箱上」——
    段序列不同但 flattened(段串联)相同 → 同一位置两种写法 → 建议合并。
    返回: [{paths: [a, b, ...], items_affected: N, target: 建议保留路径}]
    """
    groups = {}
    for p, _qty in tree_mod.all_paths(conn):
        flattened = p.replace(SEP, "")
        groups.setdefault(flattened, []).append(p)
    out = []
    for flattened, paths in groups.items():
        if len(paths) < 2:
            continue
        # 建议保留 = 段数最少(层级最深拆分的通常更规范)或字典序
        target = min(paths, key=lambda x: (len(x.split(SEP)), x))
        items_affected = 0
        cursor = conn.cursor()
        for p in paths:
            if p == target:
                continue
            clause, params = _prefix_clause(p)
            cursor.execute(
                f"SELECT COUNT(*) AS n FROM item_locations "
                f"WHERE {clause} AND location_status NOT IN "
                f"('已废弃','已用完')", params)
            items_affected += cursor.fetchone()["n"]
        if items_affected or len(paths) > 1:
            out.append({
                "paths": sorted(paths),
                "target": target,
                "items_affected": items_affected,
            })
    return out


def create_node(conn, raw_path, cli_cmd=""):
    """新建位置(体系级,先建后放;采集组件入口共享本函数)"""
    ensure_schema(conn)
    path = normalize_path(raw_path)
    if path is None:
        return False, "位置路径无效(段不能为空)", None
    ok, reason = validate_segments(path)
    if not ok:
        return False, reason, None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM location_nodes WHERE path = ?", (path,))
    if cursor.fetchone():
        return False, f"位置「{path}」已存在", path
    # 祖先节点(父路径)若未建,一并补建(自由层级可只建叶子,但树要能通到根)
    parts = path.split(SEP)
    for i in range(1, len(parts)):
        anc = SEP.join(parts[:i])
        cursor.execute("SELECT id FROM location_nodes WHERE path = ?", (anc,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO location_nodes (path) VALUES (?)", (anc,))
    cursor.execute("INSERT INTO location_nodes (path) VALUES (?)", (path,))
    conn.commit()
    return True, f"位置「{path}」已创建", path


def _rename_cascade(conn, old, new, scene_id="SM2-1", cli_cmd="", event_type=EVENT_LOCATION_RENAMED):
    """前缀级联改名:location_nodes + item_locations.location + items.fixed_location

    返回 {renamed_items: N, events: N, paths: [affected 完整路径样例]}
    """
    cursor = conn.cursor()
    # 受影响物品(条目或固定位引用该路径子树)
    clause, params = _prefix_clause(old)
    cursor.execute(
        f"SELECT DISTINCT item_id FROM item_locations WHERE {clause}", params)
    item_ids = [r["item_id"] for r in cursor.fetchall()]
    cursor.execute(
        f"SELECT DISTINCT id FROM items WHERE fixed_location IS NOT NULL "
        f"AND ({_prefix_clause(old, 'fixed_location')[0].replace('?', '?')})",
        _prefix_clause(old, "fixed_location")[1])
    for r in cursor.fetchall():
        if r["id"] not in item_ids:
            item_ids.append(r["id"])

    # 节点改名
    cursor.execute("UPDATE location_nodes SET path = ? WHERE path = ?", (new, old))
    # 条目改名(前缀级联)
    cursor.execute(
        f"UPDATE item_locations SET location = ? || substr(location, ?), updated_at = ? "
        f"WHERE location LIKE ?",
        (new, len(old) + 1, _now(), old + "/%"))
    cursor.execute(
        "UPDATE item_locations SET location = ?, updated_at = ? WHERE location = ?",
        (new, _now(), old))
    # 固定位级联
    cursor.execute(
        f"UPDATE items SET fixed_location = ? || substr(fixed_location, ?), updated_at = ? "
        f"WHERE fixed_location LIKE ?",
        (new, len(old) + 1, _now(), old + "/%"))
    cursor.execute(
        "UPDATE items SET fixed_location = ?, updated_at = ? WHERE fixed_location = ?",
        (new, _now(), old))

    # 事件:每个受影响物品写一条(位置变更记录契约)
    summary = f"位置改名:{old} → {new}(位置管理)"
    events = 0
    for iid in item_ids:
        _record_event(conn, iid, event_type, summary,
                      payload={"before": {"location_prefix": old},
                               "after": {"location_prefix": new}},
                      scene_id=scene_id, cli_cmd=cli_cmd)
        events += 1
    conn.commit()
    return {"renamed_items": len(item_ids), "events": events,
            "renamed": (old, new)}


def rename_node(conn, old_raw, new_raw, cli_cmd=""):
    """位置改名:目标路径不存在(存在 = 用合并);影响预览见 preview"""
    ensure_schema(conn)
    old = normalize_path(old_raw)
    new = normalize_path(new_raw)
    if not old or not new:
        return False, "位置路径无效", None
    if old == new:
        return False, "新旧路径相同", None
    ok, reason = validate_segments(new)
    if not ok:
        return False, reason, None
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM location_nodes WHERE path = ?", (old,))
    if not cursor.fetchone():
        # 无节点但有物品引用(历史位置)→ 允许改名(补建节点)
        clause, params = _prefix_clause(old)
        cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE {clause}", params)
        if cursor.fetchone()["n"] == 0:
            return False, f"位置「{old}」不存在", None
    cursor.execute("SELECT id FROM location_nodes WHERE path = ?", (new,))
    if cursor.fetchone():
        return False, f"目标「{new}」已是独立位置,请用「合并」", None
    # 目标路径有物品引用(条目) → 冲突拦截(先移走或合并)
    cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE location = ?", (new,))
    if cursor.fetchone()["n"] > 0:
        return False, f"目标「{new}」已有物品,请先移动或使用「合并」", None

    result = _rename_cascade(conn, old, new, cli_cmd=cli_cmd)
    return True, f"已改名:「{old}」→「{new}」(涉及 {result['renamed_items']} 件物品)", result


def rename_preview(conn, old_raw, new_raw):
    """改名影响预览(确认前:涉及 N 件 + 影响路径)"""
    old = normalize_path(old_raw)
    new = normalize_path(new_raw)
    if not old or not new:
        return None
    cursor = conn.cursor()
    clause, params = _prefix_clause(old)
    cursor.execute(f"SELECT DISTINCT location FROM item_locations WHERE {clause} ORDER BY location", params)
    affected = [r["location"] for r in cursor.fetchall()]
    cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE {clause}", params)
    items = cursor.fetchone()["n"]
    cursor.execute(f"SELECT COUNT(*) AS n FROM items WHERE fixed_location IS NOT NULL AND ({_prefix_clause(old, 'fixed_location')[0]})",
                   _prefix_clause(old, "fixed_location")[1])
    fixed = cursor.fetchone()["n"]
    return {"old": old, "new": new, "items_affected": items,
            "fixed_affected": fixed, "paths": affected[:20]}


def _merge_cascade(conn, src, tgt, scene_id="SM2-1", cli_cmd=""):
    """相似位置合并级联:条目/固定位前缀改写 src→tgt(去重)+ 子节点级联 + 删 src 节点 + 空父链清理

    与 _rename_cascade 的区别:合并的目标 tgt 节点通常已存在(相似检测的典型场景:
    同一位置两种写法,两节点都已建),不能对节点做「改名到 tgt」——那会撞
    location_nodes.path 的 UNIQUE 约束;正确做法是条目迁移 + 删源节点。
    """
    cursor = conn.cursor()
    # 1. 受影响物品收集(条目 + 固定位,事件用)
    clause, params = _prefix_clause(src)
    cursor.execute(f"SELECT DISTINCT item_id FROM item_locations WHERE {clause}", params)
    item_ids = [r["item_id"] for r in cursor.fetchall()]
    cursor.execute(
        f"SELECT DISTINCT id FROM items WHERE fixed_location IS NOT NULL "
        f"AND ({_prefix_clause(src, 'fixed_location')[0]})",
        _prefix_clause(src, "fixed_location")[1])
    for r in cursor.fetchall():
        if r["id"] not in item_ids:
            item_ids.append(r["id"])
    # 2. 条目迁移 + 去重(同 item 同目标路径只留一条,数量已在目标行)
    rows = cursor.execute(
        "SELECT id, item_id, location FROM item_locations "
        "WHERE location = ? OR location LIKE ?",
        (src, src + "/%")).fetchall()
    for row in rows:
        new_loc = tgt + row["location"][len(src):]
        dup = cursor.execute(
            "SELECT id FROM item_locations WHERE item_id = ? AND location = ? AND id != ?",
            (row["item_id"], new_loc, row["id"])).fetchone()
        if dup:
            cursor.execute("DELETE FROM item_locations WHERE id = ?", (row["id"],))
        else:
            cursor.execute("UPDATE item_locations SET location = ?, updated_at = ? WHERE id = ?",
                           (new_loc, _now(), row["id"]))
    # 3. 固定位级联(src 前缀改写;fixed_location 无唯一约束,直接 UPDATE)
    cursor.execute(
        f"UPDATE items SET fixed_location = ? || substr(fixed_location, ?), updated_at = ? "
        f"WHERE fixed_location LIKE ?",
        (tgt, len(src) + 1, _now(), src + "/%"))
    cursor.execute(
        "UPDATE items SET fixed_location = ?, updated_at = ? WHERE fixed_location = ?",
        (tgt, _now(), src))
    # 4. 子节点级联:目标子路径已存在 → 删源子节点(条目已在第 2 步迁移),否则改路径
    for row in cursor.execute(
            "SELECT id, path FROM location_nodes WHERE path LIKE ?",
            (src + "/%",)).fetchall():
        new_p = tgt + row["path"][len(src):]
        dup = cursor.execute(
            "SELECT id FROM location_nodes WHERE path = ?", (new_p,)).fetchone()
        if dup:
            cursor.execute("DELETE FROM location_nodes WHERE id = ?", (row["id"],))
        else:
            cursor.execute("UPDATE location_nodes SET path = ? WHERE id = ?",
                           (new_p, row["id"]))
    # 5. 删 src 节点
    cursor.execute("DELETE FROM location_nodes WHERE path = ?", (src,))
    # 6. 空父链清理(父节点无子无条目 → 一并删除)
    parts = src.split(SEP)
    for i in range(len(parts) - 1, 0, -1):
        anc = SEP.join(parts[:i])
        clause_a, params_a = _prefix_clause(anc)
        cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE {clause_a}", params_a)
        if cursor.fetchone()["n"] > 0:
            break
        cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path LIKE ? AND path != ?",
                       (anc + "/%", anc))
        if cursor.fetchone()["n"] > 0:
            break
        cursor.execute("DELETE FROM location_nodes WHERE path = ?", (anc,))
    # 7. 事件:每个受影响物品一条(记录契约)
    summary = f"位置合并:{src} → {tgt}(位置管理)"
    events = 0
    for iid in item_ids:
        _record_event(conn, iid, EVENT_LOCATION_RENAMED, summary,
                      payload={"before": {"location_prefix": src},
                               "after": {"location_prefix": tgt}},
                      scene_id=scene_id, cli_cmd=cli_cmd)
        events += 1
    conn.commit()
    return {"renamed_items": len(item_ids), "events": events,
            "renamed": (src, tgt)}


def merge_node(conn, src_raw, tgt_raw, cli_cmd=""):
    """相似位置合并:src → tgt(tgt 节点通常已存在;条目迁移 + 删源节点,不崩 UNIQUE)"""
    ensure_schema(conn)
    src = normalize_path(src_raw)
    tgt = normalize_path(tgt_raw)
    if not src or not tgt:
        return False, "位置路径无效", None
    if src == tgt:
        return False, "合并双方相同", None
    if is_descendant_or_self(src, tgt) or is_descendant_or_self(tgt, src):
        return False, "父子位置不可互相合并(先确认层级)", None
    result = _merge_cascade(conn, src, tgt, cli_cmd=cli_cmd)
    return True, f"已合并:「{src}」→「{tgt}」(涉及 {result['renamed_items']} 件物品)", result


def delete_node(conn, raw_path, cli_cmd=""):
    """删除位置:子树有物品引用 → 拦截(引导先移物品);否则删节点"""
    ensure_schema(conn)
    path = normalize_path(raw_path)
    if not path:
        return False, "位置路径无效", None
    cursor = conn.cursor()
    clause, params = _prefix_clause(path)
    cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE {clause}", params)
    items = cursor.fetchone()["n"]
    if items > 0:
        return False, f"「{path}」下还有 {items} 件物品,不能删除(先移物品)", None
    cursor.execute("DELETE FROM location_nodes WHERE path = ?", (path,))
    # 空父节点链清理:父节点无子无条目 → 一并删除
    parts = path.split(SEP)
    for i in range(len(parts) - 1, 0, -1):
        anc = SEP.join(parts[:i])
        clause_a, params_a = _prefix_clause(anc)
        cursor.execute(f"SELECT COUNT(*) AS n FROM item_locations WHERE {clause_a}", params_a)
        if cursor.fetchone()["n"] > 0:
            break
        cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path LIKE ? AND path != ?",
                       (anc + "/%", anc))
        if cursor.fetchone()["n"] > 0:
            break
        cursor.execute("DELETE FROM location_nodes WHERE path = ?", (anc,))
    conn.commit()
    return True, f"位置「{path}」已删除", {"deleted": path}


def all_locations_for_selector(conn):
    """位置选择器数据:全部可用位置(条目 ∪ 节点)+ 数量"""
    paths = tree_mod.all_paths(conn)
    return [{"path": p, "count": qty} for p, qty in paths]


# ═══════════════════ 固定位(2-1) ═══════════════════

def fixed_set(conn, item_id, raw_location, cli_cmd=""):
    """设置固定位(位置规范化;允许锚定空位置——先建后放)"""
    ensure_schema(conn)
    item = _find_item(conn, item_id)
    if not item:
        return False, f"未找到 ID={item_id} 的物品", None
    path = normalize_path(raw_location)
    if path is None:
        return False, "固定位路径无效(段不能为空)", None
    ok, reason = validate_segments(path)
    if not ok:
        return False, reason, None
    old = _fixed_of(conn, item_id)
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET fixed_location = ?, updated_at = ? WHERE id = ?",
                   (path, _now(), item_id))
    _record_event(conn, item_id, EVENT_FIXED_SPOT_CHANGED,
                  f"设置固定位:{item['name']} → {path}",
                  payload={"before": {"fixed_location": old},
                           "after": {"fixed_location": path}},
                  scene_id="SM2-2", cli_cmd=cli_cmd)
    conn.commit()
    return True, f"已设置固定位:{item['name']} → {path}", {"item": item, "fixed_location": path}


def fixed_clear(conn, item_id, cli_cmd=""):
    """解除固定位(确认式)"""
    ensure_schema(conn)
    item = _find_item(conn, item_id)
    if not item:
        return False, f"未找到 ID={item_id} 的物品", None
    old = _fixed_of(conn, item_id)
    if not old:
        return False, f"{item['name']} 没有固定位", None
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET fixed_location = NULL, updated_at = ? WHERE id = ?",
                   (_now(), item_id))
    _record_event(conn, item_id, EVENT_FIXED_SPOT_CHANGED,
                  f"解除固定位:{item['name']}",
                  payload={"before": {"fixed_location": old},
                           "after": {"fixed_location": None}},
                  scene_id="SM2-2", cli_cmd=cli_cmd)
    conn.commit()
    return True, f"已解除固定位:{item['name']}", {"item": item, "fixed_location": None}


def _fixed_of(conn, item_id):
    cursor = conn.cursor()
    cursor.execute("SELECT fixed_location FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    return row["fixed_location"] if row else None


def fixed_list_payload(conn):
    """现有固定位清单(物品 + 固定位 + 当前位置对比 ⚠️ 不在固定位)"""
    ensure_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.id, i.name, i.fixed_location, i.photo
        FROM items i
        WHERE i.fixed_location IS NOT NULL AND i.fixed_location != ''
        ORDER BY i.name
        """
    )
    rows = cursor.fetchall()
    out = []
    for r in rows:
        item = dict(r)
        cursor.execute(
            "SELECT location, quantity, location_status FROM item_locations "
            "WHERE item_id = ? AND location_status NOT IN ('已废弃','已用完') "
            "ORDER BY id",
            (item["id"],))
        currents = [dict(x) for x in cursor.fetchall()]
        fixed = normalize_path(item["fixed_location"])
        at_fixed = any(normalize_path(c["location"]) == fixed for c in currents)
        out.append({
            "id": item["id"],
            "name": item["name"],
            "photo": item["photo"],
            "fixed": fixed,
            "currents": currents,
            "at_fixed": at_fixed,
            "warn": not at_fixed,
        })
    return {"fixed_items": out, "total": len(out)}


# ═══════════════════ 收纳建议(3-1) ═══════════════════

def recommend_item(conn, item_id, top_n=3):
    """单件收纳建议:分类常用位置(用户数据优先)+ 关联物品位置 + 种子冷启动

    决策规则(对抗式审查定稿 2026-08-06):
      1. 强证据 = 同分类 ≥2 件共用某位置(排除自身)→ 推荐搬移(当前已是热门位则保持)
      2. 弱证据(1/1/1 分布或无同类)→ 当前位置存在则「保持现状」(理由诚实标注)
      3. 关联证据(关联物品所在位置,即使 1 件)→ 可推荐(关系是明确意图)
      4. 冷启动(无当前位置 + 无证据)→ 种子;种子 == 当前 → 确认「符合分类默认」

    返回: {item, recommend, keep, alternates, seed_used}
    """
    ensure_schema(conn)
    from 物品.events import ensure_tables
    ensure_tables(conn)   # item_relations 关联表载体(SM1 记录契约底座)
    item = _find_item(conn, item_id)
    if not item:
        return None
    cur = _loc_row(conn, item_id)
    current = cur["location"] if cur else None
    current_n = normalize_path(current) if current else None

    cat = _category_name(conn, item["category_id"])
    cat_name = cat["name"] if cat else "?"

    # ① 分类常用位置(同类活跃物品分布,排除自身)
    cat_hits = _category_location_hits(conn, item["category_id"], exclude_item=item_id)
    # ② 关联物品位置(item_relations 双向)
    rel_hits = _related_location_hits(conn, item_id)
    # ③ 种子冷启动(静态表)
    seed = _seed_for(conn, item["category_id"])

    ranked = []
    for loc, cnt, examples in cat_hits:
        ln = normalize_path(loc)
        if not ln or (current_n and ln == current_n):
            continue
        ranked.append({"location": ln, "score": cnt,
                       "reason": f"分类「{cat_name}」常用位置,{cnt} 件同类在此(如 {'、'.join(examples[:2])})"})
    for loc, names in rel_hits:
        ln = normalize_path(loc)
        if not ln or (current_n and ln == current_n):
            continue
        if any(r["location"] == ln for r in ranked):
            continue
        ranked.append({"location": ln, "score": 0.5,
                       "reason": f"关联物品「{'、'.join(names[:2])}」在此"})

    recommend = None
    keep = None
    alternates = []

    strong = [r for r in ranked if r["score"] >= 2]
    if strong:
        strong.sort(key=lambda r: -r["score"])
        recommend = strong[0]
        alternates = [r for r in strong[1:] if r["location"] != recommend["location"]]
        alternates += [r for r in ranked if r["score"] < 2][:top_n]
    elif any(r["score"] == 0.5 for r in ranked):
        # 关联证据(弱分类证据时的明确意图)
        rel = [r for r in ranked if r["score"] == 0.5]
        recommend = rel[0]
        alternates = [r for r in ranked if r["score"] != 0.5][:top_n]
    else:
        # 弱证据 → 现状优先
        if current_n:
            if seed and seed["path"] == current_n:
                keep = {"location": current_n,
                        "reason": f"已在常用位置:「{current_n}」正是「{cat_name}」类默认位置,无需移动"}
            elif current_n in {normalize_path(h[0]) for h in cat_hits}:
                keep = {"location": current_n,
                        "reason": f"已在常用位置:分类「{cat_name}」的物品目前分布在此,无需移动"}
            else:
                keep = {"location": current_n,
                        "reason": "暂无强依据,保持现状(同分类没有更集中的位置)"}
            alternates = ranked[:top_n]
        elif seed:
            recommend = {"location": seed["path"], "score": 0,
                         "reason": f"冷启动建议(「{seed['category']}」类默认):{seed['path']}"}

    return {
        "item": {"id": item["id"], "name": item["name"],
                 "category_name": cat_name,
                 "current_location": current,
                 "fixed_location": _fixed_of(conn, item_id)},
        "recommend": recommend,
        "keep": keep,
        "alternates": alternates,
        "seed_used": bool(not ranked and not current_n and seed),
    }


def recommend_batch(conn, limit=50):
    """批量建议:没有固定位的常用件(用过 = last_accessed_at 非空 或 access_count>0)"""
    ensure_schema(conn)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM items WHERE fixed_location IS NULL "
        "AND (last_accessed_at IS NOT NULL OR access_count > 0) "
        "ORDER BY COALESCE(last_accessed_at, '') DESC, access_count DESC LIMIT ?",
        (limit,))
    ids = [r["id"] for r in cursor.fetchall()]
    return [recommend_item(conn, i) for i in ids]


def recommend_items(conn, item_ids, top_n=3):
    """指定多件建议(prompt「可多件」的落地:sm2-suggest --item-ids)

    逐件推荐(每件独立决策规则);跳过不存在的 ID。
    """
    out = []
    for iid in item_ids:
        rec = recommend_item(conn, iid, top_n=top_n)
        if rec:
            out.append(rec)
    return out


def _category_location_hits(conn, category_id, exclude_item=None, limit=10):
    """同类物品位置分布: [(location, 件数, [示例物品]), ...]"""
    if not category_id:
        return []
    cursor = conn.cursor()
    clause = "category_id = ?"
    params = [category_id]
    if exclude_item:
        clause += " AND i.id != ?"
        params.append(exclude_item)
    cursor.execute(
        f"""
        SELECT il.location, COUNT(DISTINCT i.id) AS cnt
        FROM item_locations il
        JOIN items i ON i.id = il.item_id
        WHERE {clause} AND il.location IS NOT NULL AND il.location != ''
          AND il.location_status NOT IN ('已废弃','已用完')
        GROUP BY il.location ORDER BY cnt DESC LIMIT ?
        """,
        [*params, limit])
    rows = cursor.fetchall()
    out = []
    for r in rows:
        cursor.execute(
            f"SELECT DISTINCT i.name FROM item_locations il JOIN items i ON i.id = il.item_id "
            f"WHERE {clause} AND il.location = ? AND il.location_status NOT IN ('已废弃','已用完') "
            f"ORDER BY il.created_at DESC LIMIT 2",
            [*params, r["location"]])
        examples = [x["name"] for x in cursor.fetchall()]
        out.append((r["location"], r["cnt"], examples))
    return out


def _related_location_hits(conn, item_id, limit=5):
    """关联物品所在位置: [(location, [关联物品名]), ...]"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT related_item_id AS rid FROM item_relations WHERE item_id = ? "
        "UNION SELECT item_id FROM item_relations WHERE related_item_id = ?",
        (item_id, item_id))
    related = [r["rid"] for r in cursor.fetchall()]
    out = {}
    for rid in related:
        cursor.execute(
            "SELECT il.location, i.name FROM item_locations il "
            "JOIN items i ON i.id = il.item_id "
            "WHERE il.item_id = ? AND il.location_status NOT IN ('已废弃','已用完') "
            "AND il.location IS NOT NULL AND il.location != ''",
            (rid,))
        for row in cursor.fetchall():
            out.setdefault(row["location"], []).append(row["name"])
    return [(loc, names) for loc, names in out.items()]


def _seed_for(conn, category_id):
    """冷启动种子:分类 → 默认位置(静态表 seed.py;按 seed_key > 分类名 匹配)"""
    from . import seed as seed_mod
    cat = _category_name(conn, category_id)
    if not cat:
        return None
    path = seed_mod.default_location(cat.get("seed_key"), cat.get("name"))
    if not path:
        return None
    return {"path": path, "category": cat["name"]}
