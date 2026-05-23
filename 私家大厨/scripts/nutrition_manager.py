#!/usr/bin/env python3
"""
私家大厨 - 营养信息管理
管理表：nutrition_info
支持：add / get / list / search-high-protein / update
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加营养信息"""
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
    
    # 检查是否已有营养信息
    cursor.execute("SELECT id FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"警告：{recipe['name']}已有营养信息，使用update命令更新")
        conn.close()
        return False
    
    nutrition_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO nutrition_info (
            id, recipe_id, serving_size, serving_unit,
            calories, protein, fat, carbs, fiber, sodium
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nutrition_id,
        recipe_id,
        args.get("--serving_size"),
        args.get("--serving_unit"),
        args.get("--calories"),
        args.get("--protein"),
        args.get("--fat"),
        args.get("--carbs"),
        args.get("--fiber"),
        args.get("--sodium")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 营养信息添加成功！")
    print(f"   食谱：{recipe['name']}")
    if args.get("--calories"):
        print(f"   热量：{args['--calories']}kcal/份")
    return True

def get(args):
    """查看营养信息"""
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
    
    cursor.execute("SELECT * FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    nutrition = cursor.fetchone()
    conn.close()
    
    if not nutrition:
        print(f"\n{recipe['name']} - 没有营养信息")
        return True
    
    serving = f"{nutrition['serving_size'] or ''}{nutrition['serving_unit'] or '份'}"
    
    print(f"\n{recipe['name']} - 营养信息（每{serving}）：")
    if nutrition['calories']:
        print(f"  热量：{nutrition['calories']}kcal")
    if nutrition['protein']:
        print(f"  蛋白质：{nutrition['protein']}g")
    if nutrition['fat']:
        print(f"  脂肪：{nutrition['fat']}g")
    if nutrition['carbs']:
        print(f"  碳水：{nutrition['carbs']}g")
    if nutrition['fiber']:
        print(f"  膳食纤维：{nutrition['fiber']}g")
    if nutrition['sodium']:
        print(f"  钠：{nutrition['sodium']}mg")
    
    return True

def list_items(args):
    """列出有营养信息的食谱"""
    conn = get_connection()
    cursor = conn.cursor()
    
    sort_by = args.get("--sort") or "calories"
    
    if sort_by == "calories":
        order = "n.calories ASC"
    elif sort_by == "protein":
        order = "n.protein DESC"
    elif sort_by == "fat":
        order = "n.fat DESC"
    else:
        order = "r.name"
    
    cursor.execute(f"""
        SELECT r.id, r.name, r.difficulty, n.calories, n.protein, n.fat, n.carbs
        FROM recipes r
        JOIN nutrition_info n ON r.id = n.recipe_id
        ORDER BY {order}
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有营养信息记录")
        return True
    
    print(f"\n有营养信息的食谱（共{len(rows)}道）：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'热量':<8} {'蛋白':<8} {'脂肪':<8} {'碳水'}")
    print("-" * 80)
    for i, row in enumerate(rows, 1):
        cal = f"{row['calories']}kcal" if row['calories'] else "-"
        pro = f"{row['protein']}g" if row['protein'] else "-"
        fat = f"{row['fat']}g" if row['fat'] else "-"
        carb = f"{row['carbs']}g" if row['carbs'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {cal:<8} {pro:<8} {fat:<8} {carb}")
    
    return True

def search_high_protein(args):
    """搜索高蛋白食谱"""
    threshold = int(args.get("--threshold") or 20)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.difficulty, n.protein, n.calories
        FROM recipes r
        JOIN nutrition_info n ON r.id = n.recipe_id
        WHERE n.protein >= ?
        ORDER BY n.protein DESC
    """, (threshold,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"没有蛋白质含量>= {threshold}g的食谱")
        return True
    
    print(f"\n高蛋白食谱（蛋白质 >= {threshold}g，共{len(rows)}道）：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'蛋白':<8} {'热量'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        pro = f"{row['protein']}g" if row['protein'] else "-"
        cal = f"{row['calories']}kcal" if row['calories'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {pro:<8} {cal}")
    
    return True

def update(args):
    """更新营养信息"""
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
    
    # 检查是否有营养信息
    cursor.execute("SELECT id FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    existing = cursor.fetchone()
    
    updates = []
    params = []
    
    if args.get("--serving_size"):
        updates.append("serving_size = ?")
        params.append(args["--serving_size"])
    if args.get("--serving_unit"):
        updates.append("serving_unit = ?")
        params.append(args["--serving_unit"])
    if args.get("--calories"):
        updates.append("calories = ?")
        params.append(args["--calories"])
    if args.get("--protein"):
        updates.append("protein = ?")
        params.append(args["--protein"])
    if args.get("--fat"):
        updates.append("fat = ?")
        params.append(args["--fat"])
    if args.get("--carbs"):
        updates.append("carbs = ?")
        params.append(args["--carbs"])
    if args.get("--fiber"):
        updates.append("fiber = ?")
        params.append(args["--fiber"])
    if args.get("--sodium"):
        updates.append("sodium = ?")
        params.append(args["--sodium"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    if existing:
        params.append(recipe_id)
        cursor.execute(f"UPDATE nutrition_info SET {', '.join(updates)} WHERE recipe_id = ?", params)
        conn.commit()
        print(f"✅ 营养信息更新成功！")
    else:
        # 创建新的
        nutrition_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO nutrition_info (
                id, recipe_id, serving_size, serving_unit,
                calories, protein, fat, carbs, fiber, sodium
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nutrition_id,
            recipe_id,
            args.get("--serving_size"),
            args.get("--serving_unit"),
            args.get("--calories"),
            args.get("--protein"),
            args.get("--fat"),
            args.get("--carbs"),
            args.get("--fiber"),
            args.get("--sodium")
        ))
        conn.commit()
        print(f"✅ 营养信息添加成功！")
    
    conn.close()
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python nutrition_manager.py add <recipe_id> [选项]
    python nutrition_manager.py get <recipe_id>
    python nutrition_manager.py list [--sort calories|protein|fat]
    python nutrition_manager.py search-high-protein [--threshold <数值>]
    python nutrition_manager.py update <recipe_id> [选项]

选项：
    --serving_size 每份份量数值
    --serving_unit 每份份量单位（g/克/份/碗）
    --calories 每份热量（kcal）
    --protein 每份蛋白质（g）
    --fat 每份脂肪（g）
    --carbs 每份碳水化合物（g）
    --fiber 每份膳食纤维（g）
    --sodium 每份钠（mg）
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
            if action in ("add", "get", "update") and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "get":
        get(args)
    elif action == "list":
        list_items(args)
    elif action == "search-high-protein":
        search_high_protein(args)
    elif action == "update":
        update(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()