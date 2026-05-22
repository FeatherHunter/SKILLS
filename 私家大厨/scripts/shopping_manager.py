#!/usr/bin/env python3
"""
私家大厨 - 采购清单管理
返回 JSON 数据，供 AI 生成 HTML 使用
支持：generate
"""

import sys
import json
from datetime import datetime
from db_config import get_connection

def generate(args):
    """生成采购清单 JSON"""
    # 解析 recipe_ids（支持逗号分隔的多个ID）
    recipe_ids_str = args.get("<recipe_id>")
    if not recipe_ids_str:
        print(json.dumps({"error": "请提供食谱ID"}, ensure_ascii=False))
        return False
    
    recipe_ids = [rid.strip() for rid in recipe_ids_str.split(",")]
    exclude_optional = args.get("--exclude-optional")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取食谱信息
    placeholders = ",".join(["?" for _ in recipe_ids])
    cursor.execute(f"SELECT id, name, servings FROM recipes WHERE id IN ({placeholders})", recipe_ids)
    recipes_map = {row["id"]: {"id": row["id"], "name": row["name"], "servings": row["servings"], "ingredients": []} for row in cursor.fetchall()}
    
    if not recipes_map:
        print(json.dumps({"error": "未找到食谱", "recipe_ids": recipe_ids}, ensure_ascii=False))
        conn.close()
        return False
    
    # 获取食材
    conditions = [f"recipe_id IN ({placeholders})"]
    params = list(recipe_ids)
    
    if exclude_optional and exclude_optional != "false":
        conditions.append("is_optional = 0")
    
    cursor.execute(f"""
        SELECT id, recipe_id, name, quantity, unit, quantity_text, category, is_optional, substitute
        FROM ingredients
        WHERE {' AND '.join(conditions)}
        ORDER BY category, sequence
    """, params)
    
    for row in cursor.fetchall():
        recipe_id = row["recipe_id"]
        if recipe_id in recipes_map:
            ingredient = {
                "id": row["id"],
                "name": row["name"],
                "quantity": row["quantity"],
                "unit": row["unit"],
                "quantity_text": row["quantity_text"],
                "category": row["category"] or "其他",
                "is_optional": bool(row["is_optional"]),
                "substitute": row["substitute"]
            }
            recipes_map[recipe_id]["ingredients"].append(ingredient)
    
    conn.close()
    
    # 组装输出
    recipes_list = list(recipes_map.values())
    
    result = {
        "generated_at": datetime.now().isoformat(),
        "recipe_ids": recipe_ids,
        "exclude_optional": bool(exclude_optional),
        "recipes": recipes_list
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return True

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "用法：python shopping_manager.py generate <recipe_id>[,<recipe_id2>,...] [--exclude-optional]"
        }, ensure_ascii=False))
        return
    
    action = sys.argv[1]
    
    args = {}
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
            if "<recipe_id>" not in args and "<recipe_ids>" not in args:
                args["<recipe_id>"] = arg
            i += 1
    
    if action == "generate":
        generate(args)
    else:
        print(json.dumps({"error": f"未知操作：{action}"}, ensure_ascii=False))

if __name__ == "__main__":
    main()