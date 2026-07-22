#!/usr/bin/env python3
"""
私家大厨 - 烹饪方式管理
管理表：recipe_cooking_methods
支持：add / list / search
"""

import sys
import uuid
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection
from cli_formatter import emit, parse_json_flag, error  # L3

def add(args):
    """添加烹饪方式"""
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
    
    methods_raw = args.get("--method", "")
    methods = [x.strip() for x in methods_raw.split(",") if x.strip()]
    
    if not methods:
        print("错误：请提供烹饪方式（如 --method 炒）")
        conn.close()
        return False
    
    added = []
    for method in methods:
        method_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO recipe_cooking_methods (id, recipe_id, method)
            VALUES (?, ?, ?)
        """, (method_id, recipe_id, method))
        added.append(method)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 烹饪方式添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   方式：{'/'.join(added)}")
    return True

def list_items(args):
    """查看某食谱的烹饪方式"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.name, rcm.method
        FROM recipe_cooking_methods rcm
        JOIN recipes r ON rcm.recipe_id = r.id
        WHERE rcm.recipe_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有烹饪方式信息")
        return True
    
    print(f"\n{rows[0]['name']} - 烹饪方式：")
    for row in rows:
        print(f"  - {row['method']}")
    
    return True

def search(args):
    """按烹饪方式搜索"""
    method = args.get("<方式>")
    if not method:
        print("错误：请提供烹饪方式")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rcm.method
        FROM recipes r
        JOIN recipe_cooking_methods rcm ON r.id = rcm.recipe_id
        WHERE rcm.method LIKE ?
        ORDER BY r.name
    """, (f"%{method}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到烹饪方式：{method}")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'方式':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['method']:<8} {row['difficulty'] or '-':<8} {time_str}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python cooking_method_manager.py add <recipe_id> --method <方式>[,<方式2>,...]
    python cooking_method_manager.py list <recipe_id>
    python cooking_method_manager.py search <方式>

烹饪方式：炒/蒸/煮/烤/炸/煎/焖/炖/拌/卤/熏
""")
        return
    
    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
    
    args = {}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--method"):
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
            elif action == "search" and "<方式>" not in args:
                args["<方式>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "search":
        search(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)

if __name__ == "__main__":
    main()