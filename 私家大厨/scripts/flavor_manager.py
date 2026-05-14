#!/usr/bin/env python3
"""
私家大厨 - 口味管理
管理表：recipe_flavors
支持：add / list / search
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加口味"""
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
    
    flavors_raw = args.get("--flavor", "")
    flavors = [x.strip() for x in flavors_raw.split(",") if x.strip()]
    
    if not flavors:
        print("错误：请提供口味（如 --flavor 辣）")
        conn.close()
        return False
    
    added = []
    for flavor in flavors:
        flavor_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO recipe_flavors (id, recipe_id, flavor)
            VALUES (?, ?, ?)
        """, (flavor_id, recipe_id, flavor))
        added.append(flavor)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 口味添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   口味：{'/'.join(added)}")
    return True

def list(args):
    """查看某食谱的口味"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.name, rf.flavor
        FROM recipe_flavors rf
        JOIN recipes r ON rf.recipe_id = r.id
        WHERE rf.recipe_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有口味信息")
        return True
    
    print(f"\n{rows[0]['name']} - 口味：")
    for row in rows:
        print(f"  - {row['flavor']}")
    
    return True

def search(args):
    """按口味搜索"""
    flavor = args.get("<口味>")
    if not flavor:
        print("错误：请提供口味")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rf.flavor
        FROM recipes r
        JOIN recipe_flavors rf ON r.id = rf.recipe_id
        WHERE rf.flavor LIKE ?
        ORDER BY r.name
    """, (f"%{flavor}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到口味：{flavor}")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'口味':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['flavor']:<8} {row['difficulty'] or '-':<8} {time_str}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python flavor_manager.py add <recipe_id> --flavor <口味>[,<口味2>,...]
    python flavor_manager.py list <recipe_id>
    python flavor_manager.py search <口味>

口味：酸/甜/辣/咸/鲜/苦/麻
""")
        return
    
    action = sys.argv[1]
    
    args = {}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--flavor"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        elif arg.startswith("--"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        else:
            if "<recipe_id>" not in args and action != "search":
                args["<recipe_id>"] = arg
            elif action == "search" and "<口味>" not in args:
                args["<口味>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list(args)
    elif action == "search":
        search(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()