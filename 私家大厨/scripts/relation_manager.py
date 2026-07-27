#!/usr/bin/env python3
"""
私家大厨 - 食谱派生关系管理
管理表:recipe_relations
支持:add / list-parent / list-child / list-all / update

L4 阶段:函数体迁 db.execute/query/transaction
L3 补漏(2026-07-27):全部函数加 --json 支持(对抗式审查发现)
"""

import sys
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error
import validators  # 决策 3:接入 validate_relation_type


def _resolve_recipe_id(name_or_id: str) -> str | None:
    """接受菜名或 recipe_id,返 ID(优先精确匹配,fallback 模糊匹配)"""
    if not name_or_id:
        return None
    # 先精确匹配 ID
    r = query("SELECT id, name FROM recipes WHERE id = ?", (name_or_id,))
    if r:
        return r[0]["id"]
    # fallback 模糊匹配菜名
    r = query("SELECT id, name FROM recipes WHERE name LIKE ?", (f"%{name_or_id}%",))
    if r:
        return r[0]["id"]
    return None


def _out(json_mode: bool, status: str, data: dict = None, message: str = "", **kwargs):
    """统一 emit helper:json_mode 走 emit(JSON),否则 print(人类友好)
    L3 补漏:所有子函数用此 helper 输出,避免 print + JSON 混用"""
    if json_mode:
        result = {"status": status}
        if data is not None:
            result["data"] = data
        result["message"] = message
        if kwargs:
            result.update(kwargs)
        emit(result, json_mode=True)
    # else:子函数外层 print 已处理人类友好输出


def add(args):
    """创建派生关系(单 INSERT)"""
    json_mode = args.get("_json_mode", False)
    parent_id = args.get("--parent_id")
    child_id = args.get("--child_id")

    if not parent_id or not child_id:
        _out(json_mode, "error", message="请提供 --parent_id 和 --child_id",
             error="missing_required", missing=["--parent_id", "--child_id"])
        if not json_mode:
            print("错误:请提供 --parent_id 和 --child_id")
        return False

    # L4: db.query
    parent = query("SELECT name FROM recipes WHERE id = ?", (parent_id,))
    if not parent:
        _out(json_mode, "error", message=f"未找到父食谱:{parent_id}",
             error="recipe_not_found", parent_id=parent_id)
        if not json_mode:
            print(f"未找到父食谱:{parent_id}")
        return False

    child = query("SELECT name FROM recipes WHERE id = ?", (child_id,))
    if not child:
        _out(json_mode, "error", message=f"未找到子食谱:{child_id}",
             error="recipe_not_found", child_id=child_id)
        if not json_mode:
            print(f"未找到子食谱:{child_id}")
        return False

    # L1 NOT NULL 兜底(2026-07-22):relation_type + change_summary 必填 + enum 校验
    relation_type = args.get("--relation_type")
    change_summary = args.get("--change_summary")
    missing = []
    if not relation_type:
        missing.append({"flag": "--relation_type", "hint": "关系类型(派生 / 变体 / 改良)"})
    if not change_summary:
        missing.append({"flag": "--change_summary", "hint": "改动说明(如「用山西陈醋替代米醋,减糖」)"})
    if missing:
        _out(json_mode, "error",
             message="缺少以下必填字段(L1 NOT NULL 兜底,DB 不允许 NULL)",
             error="missing_required", missing=missing,
             hint="这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。请拿这些 hint 去问用户,拿到答案后用 --flag <值> 重试。")
        if not json_mode:
            print("错误:缺少以下必填字段(L1 NOT NULL 兜底,DB 不允许 NULL):")
            for m in missing:
                print(f"   - {m['flag']}:{m['hint']}")
            print("   怎么修:这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。")
            print("   请拿这些 hint 去问用户,拿到答案后用 --flag <值> 重试。")
        return False

    rt_validation = validators.validate_relation_type(relation_type)
    if not rt_validation["valid"]:
        _out(json_mode, "error", message=rt_validation["error"],
             error="invalid_enum",
             enum_value=relation_type,
             enum_valid=["派生", "变体", "改良"],
             hint="请拿 hint 去问用户,确认关系类型后重试。")
        if not json_mode:
            print(f"错误:{rt_validation['error']}")
            print("   怎么修:请拿 hint 去问用户,确认关系类型后重试。")
        return False

    execute(
        "INSERT INTO recipe_relations (id, parent_id, child_id, relation_type, change_summary) VALUES (?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            parent_id,
            child_id,
            relation_type,
            change_summary
        )
    )

    _out(json_mode, "success",
         data={"parent_name": parent[0]["name"], "child_name": child[0]["name"],
               "relation_type": relation_type, "change_summary": change_summary},
         message=f"派生关系创建成功:{parent[0]['name']} → {child[0]['name']}")
    if not json_mode:
        print(f"✅ 派生关系创建成功!")
        print(f"   父食谱:{parent[0]['name']}")
        print(f"   子食谱:{child[0]['name']}")
        print(f"   类型:{relation_type}")
        print(f"   改动:{change_summary}")
    return True


def list_parent(args):
    """查看某食谱的父级"""
    json_mode = args.get("_json_mode", False)
    name_or_id = args.get("<recipe_id>")
    if not name_or_id:
        _out(json_mode, "error", message="请提供食谱ID或菜名", error="missing_recipe_id")
        if not json_mode:
            print("错误:请提供食谱ID")
        return False

    # 接受菜名或 recipe_id(list_parent/list_child 友好接口)
    recipe_id = _resolve_recipe_id(name_or_id)
    if not recipe_id:
        _out(json_mode, "error", message=f"未找到食谱:{name_or_id}",
             error="recipe_not_found", query=name_or_id)
        if not json_mode:
            print(f"未找到食谱:{name_or_id}")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        _out(json_mode, "error", message=f"未找到食谱:{recipe_id}",
             error="recipe_not_found", recipe_id=recipe_id)
        if not json_mode:
            print(f"未找到食谱:{recipe_id}")
        return False

    rows = query("""
        SELECT r.name, rr.relation_type, rr.change_summary
        FROM recipe_relations rr
        JOIN recipes r ON rr.parent_id = r.id
        WHERE rr.child_id = ?
    """, (recipe_id,))

    relations = [{"name": r["name"], "relation_type": r["relation_type"],
                 "change_summary": r["change_summary"]} for r in rows]
    _out(json_mode, "success",
         data={"recipe_id": recipe_id, "recipe_name": recipe[0]["name"],
               "direction": "parent", "relations": relations, "count": len(relations)},
         message=f"父级查询完成:{len(relations)} 条")
    if not json_mode:
        if not rows:
            print(f"\n{recipe[0]['name']} - 没有父级(是原创食谱)")
            return True
        print(f"\n{recipe[0]['name']} - 派生自:")
        for row in rows:
            rel_type = f"({row['relation_type']})" if row['relation_type'] else ""
            change = f" - {row['change_summary']}" if row['change_summary'] else ""
            print(f"  {row['name']} {rel_type}{change}")

    return True


def list_child(args):
    """查看某食谱的子级"""
    json_mode = args.get("_json_mode", False)
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        _out(json_mode, "error", message="请提供食谱ID", error="missing_recipe_id")
        if not json_mode:
            print("错误:请提供食谱ID")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        _out(json_mode, "error", message=f"未找到食谱:{recipe_id}",
             error="recipe_not_found", recipe_id=recipe_id)
        if not json_mode:
            print(f"未找到食谱:{recipe_id}")
        return False

    rows = query("""
        SELECT r.name, rr.relation_type, rr.change_summary
        FROM recipe_relations rr
        JOIN recipes r ON rr.child_id = r.id
        WHERE rr.parent_id = ?
    """, (recipe_id,))

    relations = [{"name": r["name"], "relation_type": r["relation_type"],
                 "change_summary": r["change_summary"]} for r in rows]
    _out(json_mode, "success",
         data={"recipe_id": recipe_id, "recipe_name": recipe[0]["name"],
               "direction": "child", "relations": relations, "count": len(relations)},
         message=f"子级查询完成:{len(relations)} 条")
    if not json_mode:
        if not rows:
            print(f"\n{recipe[0]['name']} - 没有派生菜")
            return True
        print(f"\n{recipe[0]['name']} - 派生出的菜:")
        for row in rows:
            rel_type = f"({row['relation_type']})" if row['relation_type'] else ""
            change = f" - {row['change_summary']}" if row['change_summary'] else ""
            print(f"  {row['name']} {rel_type}{change}")

    return True


def list_all(args):
    """列出所有派生关系"""
    json_mode = args.get("_json_mode", False)
    rows = query("""
        SELECT
            p.name as parent_name,
            c.name as child_name,
            rr.relation_type,
            rr.change_summary
        FROM recipe_relations rr
        JOIN recipes p ON rr.parent_id = p.id
        JOIN recipes c ON rr.child_id = c.id
        ORDER BY p.name, c.name
    """)

    relations = [{"parent_name": r["parent_name"], "child_name": r["child_name"],
                 "relation_type": r["relation_type"], "change_summary": r["change_summary"]} for r in rows]
    _out(json_mode, "success",
         data={"relations": relations, "count": len(relations)},
         message=f"全部查询完成:{len(relations)} 条")
    if not json_mode:
        if not rows:
            print("没有派生关系记录")
            return True
        print(f"\n所有派生关系(共{len(rows)}条):")
        for row in rows:
            rel_type = f"[{row['relation_type']}]" if row['relation_type'] else ""
            print(f"  {row['parent_name']} → {row['child_name']} {rel_type}")

    return True


def update(args):
    """更新关系说明(L4:动态 SQL)"""
    json_mode = args.get("_json_mode", False)
    relation_id = args.get("<relation_id>")
    if not relation_id:
        _out(json_mode, "error", message="请提供关系ID", error="missing_relation_id")
        if not json_mode:
            print("错误:请提供关系ID")
        return False

    relation = query("SELECT id FROM recipe_relations WHERE id = ?", (relation_id,))
    if not relation:
        _out(json_mode, "error", message=f"未找到关系:{relation_id}",
             error="relation_not_found", relation_id=relation_id)
        if not json_mode:
            print(f"未找到关系:{relation_id}")
        return False

    updates = []
    params = []

    if args.get("--relation_type"):
        updates.append("relation_type = ?")
        params.append(args["--relation_type"])
    if args.get("--change_summary"):
        updates.append("change_summary = ?")
        params.append(args["--change_summary"])

    if not updates:
        _out(json_mode, "error", message="没有提供要更新的字段",
             error="no_updates", hint="至少提供 --relation_type 或 --change_summary")
        if not json_mode:
            print("没有提供要更新的字段")
        return False

    params.append(relation_id)
    execute(f"UPDATE recipe_relations SET {', '.join(updates)} WHERE id = ?", params)

    _out(json_mode, "success",
         data={"relation_id": relation_id, "updated_fields": updates},
         message="关系更新成功")
    if not json_mode:
        print(f"✅ 关系更新成功!")
    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python relation_manager.py add --parent_id <id> --child_id <id> [选项]
    python relation_manager.py list-parent <recipe_id>
    python relation_manager.py list-child <recipe_id>
    python relation_manager.py list-all
    python relation_manager.py update <relation_id> [选项]

选项:
    --relation_type 关系类型(派生/变体/改良)
    --change_summary 改动说明
""")
        return

    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])

    args = {"_json_mode": json_mode}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        else:
            if action in ("list-parent", "list-child") and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "update" and "<relation_id>" not in args:
                args["<relation_id>"] = arg
            i += 1

    if action == "add":
        add(args)
    elif action == "list-parent":
        list_parent(args)
    elif action == "list-child":
        list_child(args)
    elif action == "list-all":
        list_all(args)
    elif action == "update":
        update(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)


if __name__ == "__main__":
    main()