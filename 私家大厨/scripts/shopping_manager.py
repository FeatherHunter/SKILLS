#!/usr/bin/env python3
"""
私家大厨 - 采购清单管理
跨表联动，生成采购清单
支持：generate / generate-multi / generate-by-filter
"""

import sys
from db_config import get_connection

def generate(args):
    """生成单菜采购清单"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    exclude_optional = args.get("--exclude-optional")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取食谱信息
    cursor.execute("SELECT id, name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    # 获取食材
    conditions = ["recipe_id = ?"]
    params = [recipe_id]
    
    if exclude_optional:
        conditions.append("is_optional = 0")
    
    cursor.execute(f"""
        SELECT name, quantity, unit, quantity_text, category, is_optional, substitute
        FROM ingredients
        WHERE {' AND '.join(conditions)}
        ORDER BY category, sequence
    """, params)
    
    ingredients = cursor.fetchall()
    conn.close()
    
    if not ingredients:
        print(f"\n{recipe['name']} - 没有食材记录")
        return True
    
    # 按分类分组
    groups = {}
    for ing in ingredients:
        cat = ing["category"] or "其他"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(ing)
    
    # 输出
    print(f"\n【采购清单 - {recipe['name']}】")
    
    for cat, items in groups.items():
        print(f"\n【{cat}】")
        for item in items:
            qty = f"{item['quantity']}{item['unit']}" if item['quantity'] else ""
            qty_text = item['quantity_text'] or ""
            opt = "（可选）" if item['is_optional'] and not exclude_optional else ""
            sub = f" → 可用{item['substitute']}代替" if item['substitute'] else ""
            print(f"  - {item['name']} {qty}{qty_text} {opt}{sub}")
    
    print("\n---")
    print("AI采购建议：")
    for item in ingredients:
        name = item['name']
        cat = item['category'] or ""
        # 简单建议
        if cat in ("海鲜",):
            print(f"  {name}：推荐去菜市场买，比较新鲜")
        elif cat in ("肉类",):
            print(f"  {name}：超市或菜市场购买")
        elif cat in ("调料",):
            print(f"  {name}：超市调料区常见，也可网购")
        else:
            print(f"  {name}：超市购买")
    
    return True

def generate_multi(args):
    """生成多菜合并采购清单"""
    recipe_ids_str = args.get("<recipe_ids>")
    if not recipe_ids_str:
        print("错误：请提供多个食谱ID，用逗号分隔")
        return False
    
    recipe_ids = [rid.strip() for rid in recipe_ids_str.split(",")]
    exclude_optional = args.get("--exclude-optional")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取食谱名称
    placeholders = ",".join(["?" for _ in recipe_ids])
    cursor.execute(f"SELECT id, name FROM recipes WHERE id IN ({placeholders})", recipe_ids)
    recipes = {row["id"]: row["name"] for row in cursor.fetchall()}
    
    if not recipes:
        print("未找到任何食谱")
        conn.close()
        return False
    
    # 获取食材
    conditions = [f"recipe_id IN ({placeholders})"]
    params = list(recipe_ids)
    
    if exclude_optional:
        conditions.append("is_optional = 0")
    
    cursor.execute(f"""
        SELECT name, quantity, unit, quantity_text, category, is_optional, substitute, recipe_id
        FROM ingredients
        WHERE {' AND '.join(conditions)}
        ORDER BY category, name
    """, params)
    
    ingredients = cursor.fetchall()
    conn.close()
    
    if not ingredients:
        print("没有食材记录")
        return True
    
    # 合并同类食材
    merged = {}
    for ing in ingredients:
        key = (ing["name"], ing["unit"])
        if key not in merged:
            merged[key] = {
                "name": ing["name"],
                "quantity": ing["quantity"] if ing["quantity"] else 0,
                "quantity_text": ing["quantity_text"],
                "unit": ing["unit"],
                "category": ing["category"],
                "is_optional": ing["is_optional"],
                "substitute": ing["substitute"],
                "sources": [recipes.get(ing["recipe_id"], "未知")]
            }
        else:
            if ing["quantity"]:
                merged[key]["quantity"] += ing["quantity"]
            merged[key]["sources"].append(recipes.get(ing["recipe_id"], "未知"))
    
    # 按分类分组
    groups = {}
    for item in merged.values():
        cat = item["category"] or "其他"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)
    
    # 输出
    recipe_names = [recipes.get(rid, rid) for rid in recipe_ids]
    print(f"\n【采购清单 - {', '.join(recipe_names)}】")
    
    for cat, items in groups.items():
        print(f"\n【{cat}】")
        for item in items:
            qty = f"{item['quantity']}{item['unit']}" if item['quantity'] else ""
            qty_text = item['quantity_text'] or ""
            opt = "（可选）" if item['is_optional'] and not exclude_optional else ""
            sub = f" → 可用{item['substitute']}代替" if item['substitute'] else ""
            src = f" ({', '.join(set(item['sources']))})" if len(set(item['sources'])) > 1 else ""
            print(f"  - {item['name']} {qty}{qty_text}{src} {opt}{sub}")
    
    return True

def generate_by_filter(args):
    """按条件生成采购清单"""
    cuisine = args.get("--cuisine")
    difficulty = args.get("--difficulty")
    season = args.get("--season")
    flavor = args.get("--flavor")
    exclude_optional = args.get("--exclude-optional")
    
    if not any([cuisine, difficulty, season, flavor]):
        print("错误：请至少提供一个筛选条件（--cuisine/--difficulty/--season/--flavor）")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 构建查询
    recipe_ids = None
    
    if cuisine:
        cursor.execute("""
            SELECT DISTINCT recipe_id FROM recipe_categories WHERE cuisine_type LIKE ?
        """, (f"%{cuisine}%",))
        ids = {row["recipe_id"] for row in cursor.fetchall()}
        recipe_ids = recipe_ids & ids if recipe_ids else ids
    
    if difficulty:
        cursor.execute("""
            SELECT id FROM recipes WHERE difficulty = ?
        """, (difficulty,))
        ids = {row["id"] for row in cursor.fetchall()}
        recipe_ids = recipe_ids & ids if recipe_ids else ids
    
    if season:
        cursor.execute("""
            SELECT DISTINCT recipe_id FROM recipe_seasons WHERE season LIKE ?
        """, (f"%{season}%",))
        ids = {row["recipe_id"] for row in cursor.fetchall()}
        recipe_ids = recipe_ids & ids if recipe_ids else ids
    
    if flavor:
        cursor.execute("""
            SELECT DISTINCT recipe_id FROM recipe_flavors WHERE flavor LIKE ?
        """, (f"%{flavor}%",))
        ids = {row["recipe_id"] for row in cursor.fetchall()}
        recipe_ids = recipe_ids & ids if recipe_ids else ids
    
    if not recipe_ids:
        print("没有找到符合条件的食谱")
        conn.close()
        return True
    
    # 获取食材
    conditions = [f"recipe_id IN ({','.join(['?' for _ in recipe_ids])})"]
    params = list(recipe_ids)
    
    if exclude_optional:
        conditions.append("is_optional = 0")
    
    cursor.execute(f"""
        SELECT name, quantity, unit, quantity_text, category, is_optional, substitute, recipe_id
        FROM ingredients
        WHERE {' AND '.join(conditions)}
        ORDER BY category, name
    """, params)
    
    ingredients = cursor.fetchall()
    
    # 获取食谱名
    placeholders = ",".join(["?" for _ in recipe_ids])
    cursor.execute(f"SELECT id, name FROM recipes WHERE id IN ({placeholders})", params)
    recipes = {row["id"]: row["name"] for row in cursor.fetchall()}
    conn.close()
    
    if not ingredients:
        print("没有食材记录")
        return True
    
    # 合并同类食材
    merged = {}
    for ing in ingredients:
        key = (ing["name"], ing["unit"])
        if key not in merged:
            merged[key] = {
                "name": ing["name"],
                "quantity": ing["quantity"] if ing["quantity"] else 0,
                "quantity_text": ing["quantity_text"],
                "unit": ing["unit"],
                "category": ing["category"],
                "is_optional": ing["is_optional"],
                "substitute": ing["substitute"],
                "sources": [recipes.get(ing["recipe_id"], "未知")]
            }
        else:
            if ing["quantity"]:
                merged[key]["quantity"] += ing["quantity"]
            merged[key]["sources"].append(recipes.get(ing["recipe_id"], "未知"))
    
    # 按分类分组
    groups = {}
    for item in merged.values():
        cat = item["category"] or "其他"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(item)
    
    # 输出
    filter_desc = []
    if cuisine: filter_desc.append(f"菜系={cuisine}")
    if difficulty: filter_desc.append(f"难度={difficulty}")
    if season: filter_desc.append(f"季节={season}")
    if flavor: filter_desc.append(f"口味={flavor}")
    
    print(f"\n【采购清单 - 筛选: {', '.join(filter_desc)}】")
    print(f"共 {len(recipes)} 道菜")
    
    for cat, items in groups.items():
        print(f"\n【{cat}】")
        for item in items:
            qty = f"{item['quantity']}{item['unit']}" if item['quantity'] else ""
            qty_text = item['quantity_text'] or ""
            opt = "（可选）" if item['is_optional'] and not exclude_optional else ""
            sub = f" → 可用{item['substitute']}代替" if item['substitute'] else ""
            src_count = len(set(item['sources']))
            src = f" ({src_count}道菜)" if src_count > 1 else ""
            print(f"  - {item['name']} {qty}{qty_text}{src} {opt}{sub}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python shopping_manager.py generate <recipe_id> [--exclude-optional]
    python shopping_manager.py generate-multi <recipe_id_1>,<recipe_id_2>,... [--exclude-optional]
    python shopping_manager.py generate-by-filter [--cuisine <菜系>] [--difficulty <难度>] [--season <季节>] [--flavor <口味>] [--exclude-optional]

示例：
    python shopping_manager.py generate <recipe_id>
    python shopping_manager.py generate-multi <id1>,<id2>,<id3>
    python shopping_manager.py generate-by-filter --cuisine 川菜 --difficulty 简单
    python shopping_manager.py generate <recipe_id> --exclude-optional
""")
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
            if action == "generate" and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "generate-multi" and "<recipe_ids>" not in args:
                args["<recipe_ids>"] = arg
            i += 1
    
    if action == "generate":
        generate(args)
    elif action == "generate-multi":
        generate_multi(args)
    elif action == "generate-by-filter":
        generate_by_filter(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()