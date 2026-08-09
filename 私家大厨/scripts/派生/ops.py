# ops.py - 私家大厨 · 派生域(relation)数据层
#
# 职责: 母本读取 / 同事务派生写库(recipe+relation) / 家族树组装 / 母本差异 diff
# 隔离契约: 本域只动 scripts/派生/ + templates/派生/ + render_派生.py + scenes/派生.yaml + tests/test_派生.py
#
# G9 grilling 定案(2026-08-08)+ T12 实施(2026-08-09):
#   1. rel-3 从已有派生新菜: AI 拉母本全字段按差异预填(标色)→ 过程 HTML 用户改 →
#      确认 → 创建新菜谱 + 自动建派生关系一次完成(同事务)
#   2. rel-2 家族树: 根=当前菜,向上祖先/向下后代,多代连链;list-all 全量关系组装
#   3. rel-1 添加派生关系: 过程 HTML 确认卡 → 确认 → 写库 → 回执
#   4. 边界: 母本废弃/不存在 → 拒绝+提示(不造值);派生自身非法(底层校验);派生深度不限
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import query, transaction
import recipe_manager
import import_orchestrator

# 母本剥离: 时间戳不继承;history/relations 置空数组(校验链要求键存在,可为空)
_DERIVE_STRIP_KEYS = ("created_at", "updated_at")
_EMPTY_LIST_KEYS = ("history", "relations")


def _resolve_recipe_id(name_or_id: str) -> str | None:
    """菜名(模糊)或 recipe_id → id(与 relation_manager 同口径)"""
    if not name_or_id:
        return None
    r = query("SELECT id, name, status FROM recipes WHERE id = ?", (name_or_id,))
    if r:
        return r[0]["id"]
    r = query("SELECT id, name, status FROM recipes WHERE name LIKE ?", (f"%{name_or_id}%",))
    if r:
        return r[0]["id"]
    return None


def _recipe_status(recipe_id: str) -> str | None:
    r = query("SELECT status FROM recipes WHERE id = ?", (recipe_id,))
    return r[0]["status"] if r else None


def get_mother(name_or_id: str) -> dict:
    """rel-3 母本读取: 返回符合导入契约的完整菜谱 dict(剥离时间戳/history/relations)

    Raises:
        ValueError: 母本不存在 / 母本已废弃(边界:G9 拒绝+提示,不造值)
    """
    if not name_or_id:
        raise ValueError("请提供母本菜名或 ID")
    rid = _resolve_recipe_id(name_or_id)
    if not rid:
        raise ValueError(f"未找到母本食谱「{name_or_id}」(不存在,不能派生)")
    if _recipe_status(rid) == "已废弃":
        raise ValueError(f"母本食谱「{name_or_id}」已废弃,不能作为派生母本")
    data = recipe_manager.export_as_dict(rid)
    if not data:
        raise ValueError(f"未找到母本食谱「{name_or_id}」(不存在,不能派生)")
    cleaned = {k: v for k, v in data.items() if k not in _DERIVE_STRIP_KEYS}
    for k in _EMPTY_LIST_KEYS:
        cleaned[k] = []
    return cleaned


# ── 母本 vs 派生 diff(回执展示 · 标色来源)────────────────────────────

_DIFF_KEYS = (
    "name", "description", "difficulty", "servings", "total_time", "status",
    "category.cuisine", "category.region", "category.country",
    "seasons", "cooking_methods", "flavors", "diet_tags", "meal_types",
    "cookware.name", "nutrition.serving_size", "nutrition.serving_unit",
    "nutrition.calories", "nutrition.protein", "nutrition.fat", "nutrition.carbs",
    "nutrition.fiber", "nutrition.sodium",
    "background.origin_story", "background.historical_background", "background.cultural_significance",
    "ingredients.name", "ingredients.quantity", "ingredients.unit", "ingredients.category",
    "ingredients.quantity_text", "ingredients.is_optional", "ingredients.substitute",
    "steps.action", "steps.duration", "steps.heat_level", "steps.temperature", "steps.expected_result",
    "techniques.technique_name", "techniques.description", "techniques.key_points",
    "tips.content", "tips.category", "tips.priority",
)


def _get_path(node: dict, path: str):
    """按 a.b 路径取值(数组元素路径由调用方按索引展开)"""
    cur = node
    for part in path.split("."):
        if cur is None:
            return None
        cur = cur.get(part)
    return cur


# 数组段的行主键(按 section 区分)
_ROW_NAME_KEY = {
    "ingredients": "name",
    "cookware": "name",
    "steps": "action",
    "techniques": "technique_name",
    "tips": "content",
}
# 数组段比对的字段(避免整行比对炸屏: 只比关键字段)
_ROW_FIELDS = {
    "ingredients": ("name", "quantity", "unit", "category", "quantity_text", "is_optional", "substitute"),
    "cookware": ("name",),
    "steps": ("action", "duration", "heat_level", "temperature", "expected_result"),
    "techniques": ("technique_name", "description", "key_points"),
    "tips": ("content", "category", "priority"),
}


def _rows(data: dict, section: str) -> list:
    return data.get(section) or []


def diff_mother_derived(mother: dict, derived: dict) -> list:
    """逐叶比对母本 vs 派生,产出 diff 行(回执/标色用)

    返回: [{action: add|mod|del, field, summary}] — summary 形如「牛腩 → 鸡」
    数组段: 行级增删只报一次(add/del),行内字段差异报 mod(避免逐字段重复)
    """
    diffs = []
    # 1) 数组段行级增删(一次一行)
    for section in _ROW_NAME_KEY:
        key = _ROW_NAME_KEY[section]
        m_rows = _rows(mother, section)
        d_rows = _rows(derived, section)
        m_keys = {r.get(key) for r in m_rows}
        d_keys = {r.get(key) for r in d_rows}
        for mkey in m_keys - d_keys:
            diffs.append({"action": "del", "field": f"{section}:{mkey}",
                          "summary": f"{section}「{mkey}」已删除"})
        for dkey in d_keys - m_keys:
            diffs.append({"action": "add", "field": f"{section}:{dkey}",
                          "summary": f"{section}「{dkey}」新增(未在母本中)"})
    # 2) 标量段 + 数组段行内字段 diff
    for path in _DIFF_KEYS:
        if path in ("seasons", "cooking_methods", "flavors", "diet_tags", "meal_types"):
            m = sorted(mother.get(path) or [])
            d = sorted(derived.get(path) or [])
            if m == d:
                continue
            diffs.append({
                "action": "mod",
                "field": path,
                "summary": f"{','.join(m)} → {','.join(d)}",
            })
            continue
        section = path.split(".")[0]
        if section in _ROW_NAME_KEY:
            key = _ROW_NAME_KEY[section]
            field = path.split(".")[-1]
            m_map = {r.get(key): r for r in _rows(mother, section)}
            d_map = {r.get(key): r for r in _rows(derived, section)}
            for mkey in m_map.keys() & d_map.keys():
                if field not in _ROW_FIELDS[section]:
                    continue
                mv = m_map[mkey].get(field)
                dv = d_map[mkey].get(field)
                if mv != dv:
                    diffs.append({"action": "mod",
                                  "field": f"{section}「{mkey}」.{field}",
                                  "summary": f"{mv} → {dv}"})
            continue
        # 标量段(category/nutrition/background 叶子 / name/description/...)
        mv = _get_path(mother, path)
        dv = _get_path(derived, path)
        if mv == dv:
            continue
        diffs.append({
            "action": "mod",
            "field": path,
            "summary": f"{mv} → {dv}" if mv is not None else f"新增: {dv}",
        })
    return diffs


# ── rel-3 同事务写库 ────────────────────────────────────────────────

def derive_commit(payload: dict) -> dict:
    """从母本派生新菜: 新菜谱创建 + 派生关系插入 = 同一事务(经 import_orchestrator)

    Args:
        payload: {
            "recipe": {...导入契约菜谱 dict...},   # AI 按差异预填后的新菜
            "parent_name": "咖喱牛腩",              # 母本菜名
            "relation_type": "派生",                # 派生/变体/改良
            "change_summary": "牛腩换鸡,减咖喱量"     # 差异总结(必填)
        }

    Returns:
        {"status": "success"|"error", "recipe_id", "name", "relation": {...},
         "diff": [...], "message"}
    """
    recipe = payload.get("recipe") or {}
    parent_name = payload.get("parent_name") or ""
    relation_type = payload.get("relation_type") or "派生"
    change_summary = payload.get("change_summary") or ""
    if not recipe.get("name"):
        return {"status": "error", "message": "新菜名缺失(payload.recipe.name)", "diff": []}
    if not parent_name:
        return {"status": "error", "message": "母本菜名缺失(payload.parent_name)", "diff": []}
    if not change_summary:
        return {"status": "error", "message": "改动说明缺失(payload.change_summary,差异总结必填)", "diff": []}

    # 母本校验(存在/未废弃)+ 派生自身非法
    try:
        mother = get_mother(parent_name)
    except ValueError as e:
        return {"status": "error", "message": str(e), "diff": []}
    if mother.get("name") == recipe.get("name"):
        return {"status": "error", "message": f"不能派生自身:「{recipe.get('name')}」→ 自身", "diff": []}

    import_data = dict(recipe)
    import_data["relations"] = [{
        "parent_name": parent_name,
        "relation_type": relation_type,
        "change_summary": change_summary,
    }]
    result = import_orchestrator.orchestrate_import(import_data)
    if result["status"] != "success":
        return {
            "status": "error",
            "message": result.get("message") or "派生写库失败",
            "errors": result.get("errors", []),
            "diff": [],
        }
    diff = diff_mother_derived(mother, recipe)
    return {
        "status": "success",
        "recipe_id": result["data"]["recipe_id"],
        "name": recipe.get("name"),
        "relation": {
            "parent_name": parent_name,
            "child_name": recipe.get("name"),
            "relation_type": relation_type,
            "change_summary": change_summary,
        },
        "diff": diff,
        "child_ids": result["data"].get("child_ids", {}),
        "message": result.get("message") or f"派生成功:「{parent_name}」→「{recipe.get('name')}」",
    }


# ── rel-2 家族树(list-all 组装 · 根=当前菜)──────────────────────────

def relation_tree(name_or_id: str) -> dict:
    """家族树: 根=当前菜,向上祖先(派生自)/向下后代(派生出了),多代连链

    实现: 全量关系拉取 → 邻接表 → BFS 双向扩展(visited 防环)
    废弃菜默认不入树(G9 边界: 母本废弃不可派生;树的「可用」语义)
    """
    rid = _resolve_recipe_id(name_or_id)
    if not rid:
        return {"found": False, "root": None, "ancestors": [], "descendants": [], "count": 0}
    root_row = query(
        "SELECT id, name, status FROM recipes WHERE id = ? AND status != '已废弃'", (rid,))
    if not root_row:
        return {"found": False, "root": None, "ancestors": [], "descendants": [], "count": 0}

    rows = query("""
        SELECT rr.parent_id, rr.child_id, rr.relation_type, rr.change_summary,
               p.name AS parent_name, c.name AS child_name
        FROM recipe_relations rr
        JOIN recipes p ON rr.parent_id = p.id
        JOIN recipes c ON rr.child_id = c.id
        WHERE p.status != '已废弃' AND c.status != '已废弃'
    """)
    children: dict[str, list] = {}
    parents: dict[str, list] = {}
    for r in rows:
        children.setdefault(r["parent_id"], []).append(r)
        parents.setdefault(r["child_id"], []).append(r)

    def _walk(start_id: str, edges: dict, visited: set) -> list:
        """沿边集 BFS 扩展: parents(按 child 索引)→ 向上祖先;children(按 parent 索引)→ 向下后代"""
        out = []
        level = 1
        frontier = edges.get(start_id, [])
        while frontier:
            nxt = []
            for e in frontier:
                other_id = e["parent_id"] if edges is parents else e["child_id"]
                if other_id in visited:
                    continue
                visited.add(other_id)
                other_name = e["parent_name"] if edges is parents else e["child_name"]
                out.append({
                    "id": other_id,
                    "name": other_name,
                    "level": level,
                    "relation_type": e["relation_type"],
                    "change_summary": e["change_summary"],
                })
                nxt.extend(edges.get(other_id, []))
            frontier = nxt
            level += 1
        return out

    # 注意: parents 边集合里 child_id 是本端 → 向上祖先链;children 边集合里 parent_id 是本端 → 向下后代链
    ancestors = _walk(rid, parents, {rid})
    descendants = _walk(rid, children, {rid})
    return {
        "found": True,
        "root": {"id": rid, "name": root_row[0]["name"]},
        "ancestors": ancestors,
        "descendants": descendants,
        "count": len(ancestors) + len(descendants),
    }
