#!/usr/bin/env python3
"""
私家大厨 - 食材管理
管理表：ingredients
支持：add / list / search / update / disable
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加食材"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    name = args.get("--name")
    if not name:
        print("错误：请提供食材名称（--name）")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    # 获取sequence
    cursor.execute("SELECT MAX(sequence) as max_seq FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    max_seq = cursor.fetchone()["max_seq"] or 0
    sequence = args.get("--sequence") or (max_seq + 1)
    
    ingredient_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO ingredients (
            id, recipe_id, sequence, name, category, quantity, unit,
            quantity_text, is_optional, substitute
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ingredient_id,
        recipe_id,
        sequence,
        name,
        args.get("--category"),
        args.get("--quantity"),
        args.get("--unit"),
        args.get("--quantity_text"),
        1 if args.get("--optional") else 0,
        args.get("--substitute")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 食材添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   食材：{name}")
    qty = f"{args.get('--quantity', '')}{args.get('--unit', '')}"
    if qty:
        print(f"   用量：{qty}")
    return True

def list_items(args):
    """查看某食谱的食材清单"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    cursor.execute("""
        SELECT * FROM ingredients 
        WHERE recipe_id = ?
        ORDER BY sequence
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有食材记录")
        return True
    
    print(f"\n{recipe['name']} - 食材清单（共{len(rows)}种）：")
    for row in rows:
        qty = f"{row['quantity']}{row['unit']}" if row['quantity'] else ""
        qty_text = row['quantity_text'] or ""
        opt = "（可选）" if row['is_optional'] else ""
        cat = f"[{row['category']}]" if row['category'] else ""
        sub = f" → 可用{row['substitute']}代替" if row['substitute'] else ""
        print(f"  {row['sequence']}. {cat}{row['name']} {qty}{qty_text} {opt}{sub}")
    
    return True

def search(args):
    """搜索包含某食材的食谱"""
    keyword = args.get("<食材名>")
    if not keyword:
        print("错误：请提供食材名称")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, i.name as ingredient
        FROM recipes r
        JOIN ingredients i ON r.id = i.recipe_id
        WHERE i.name LIKE ?
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到包含'{keyword}'的食谱")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间':<8} {'包含食材'}")
    print("-" * 70)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str:<8} {row['ingredient']}")
    
    return True

def update(args):
    """更新食材"""
    ingredient_id = args.get("<ingredient_id>")
    if not ingredient_id:
        print("错误：请提供食材ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
    ingredient = cursor.fetchone()
    if not ingredient:
        print(f"未找到食材：{ingredient_id}")
        conn.close()
        return False
    
    updates = []
    params = []
    
    if args.get("--name"):
        updates.append("name = ?")
        params.append(args["--name"])
    if args.get("--category"):
        updates.append("category = ?")
        params.append(args["--category"])
    if args.get("--quantity"):
        updates.append("quantity = ?")
        params.append(args["--quantity"])
    if args.get("--unit"):
        updates.append("unit = ?")
        params.append(args["--unit"])
    if args.get("--quantity_text"):
        updates.append("quantity_text = ?")
        params.append(args["--quantity_text"])
    if args.get("--sequence"):
        updates.append("sequence = ?")
        params.append(args["--sequence"])
    if args.get("--substitute"):
        updates.append("substitute = ?")
        params.append(args["--substitute"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(ingredient_id)
    cursor.execute(f"UPDATE ingredients SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 食材更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python ingredient_manager.py add <recipe_id> --name <食材名> [选项]
    python ingredient_manager.py list <recipe_id>
    python ingredient_manager.py search <食材名>
    python ingredient_manager.py update <ingredient_id> [选项]

选项：
    --name 食材名称
    --category 分类（肉类/蔬菜/调料/海鲜/其他）
    --quantity 用量数值
    --unit 单位（g/kg/ml/个/勺/把等）
    --quantity_text 文字描述（适量/少许）
    --sequence 顺序
    --optional 设为可选
    --substitute 替代食材
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
            if action in ("add", "list") and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "search" and "<食材名>" not in args:
                args["<食材名>"] = arg
            elif action == "update" and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            elif action == "discard" and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()