#!/usr/bin/env python3
"""
私家大厨 - 炊具管理
管理表：cookware
支持：add / list / search / update
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加炊具"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    name = args.get("--name")
    if not name:
        print("错误：请提供炊具名称（--name）")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    cookware_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO cookware (id, recipe_id, name, category)
        VALUES (?, ?, ?, ?)
    """, (
        cookware_id,
        recipe_id,
        name,
        args.get("--category")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 炊具添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   炊具：{name}")
    if args.get("--category"):
        print(f"   分类：{args['--category']}")
    return True

def list_items(args):
    """查看某食谱的炊具"""
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
        SELECT * FROM cookware 
        WHERE recipe_id = ? 
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有炊具记录")
        return True
    
    print(f"\n{recipe['name']} - 需要炊具：")
    for row in rows:
        cat = f"[{row['category']}]" if row['category'] else ""
        print(f"  - {cat}{row['name']}")
    
    return True

def search(args):
    """按炊具名称搜索"""
    keyword = args.get("<炊具名>")
    if not keyword:
        print("错误：请提供炊具名称")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, c.name as cookware_name
        FROM recipes r
        JOIN cookware c ON r.id = c.recipe_id
        WHERE c.name LIKE ?
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到需要'{keyword}'的食谱")
        return True
    
    print(f"\n需要「{keyword}」的食谱（共{len(rows)}道）：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间'}")
    print("-" * 50)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str}")
    
    return True

def update(args):
    """更新炊具"""
    cookware_id = args.get("<cookware_id>")
    if not cookware_id:
        print("错误：请提供炊具ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM cookware WHERE id = ?", (cookware_id,))
    cookware = cursor.fetchone()
    if not cookware:
        print(f"未找到炊具：{cookware_id}")
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
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(cookware_id)
    cursor.execute(f"UPDATE cookware SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 炊具更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python cookware_manager.py add <recipe_id> --name <炊具名> [--category <分类>]
    python cookware_manager.py list <recipe_id>
    python cookware_manager.py search <炊具名>
    python cookware_manager.py update <cookware_id> [选项]
    python cookware_manager.py 

炊具分类：锅/炉/刀/其他
炊具示例：炒锅/砂锅/烤箱/蒸笼/电饭锅/高压锅/空气炸锅
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
            elif action == "search" and "<炊具名>" not in args:
                args["<炊具名>"] = arg
            elif action in ("update", "discard") and "<cookware_id>" not in args:
                args["<cookware_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()