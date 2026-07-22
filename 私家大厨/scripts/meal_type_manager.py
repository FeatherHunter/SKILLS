#!/usr/bin/env python3
"""
私家大厨 - 用餐类型管理
管理表：recipe_meal_types
支持：add / list / search
"""

import sys
import uuid
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection
from cli_formatter import emit, parse_json_flag, error  # L3

def add(args):
    """添加用餐类型"""
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
    
    meal_types_raw = args.get("--meal_type", "")
    meal_types = [x.strip() for x in meal_types_raw.split(",") if x.strip()]
    
    if not meal_types:
        print("错误：请提供用餐类型（如 --meal_type 晚）")
        conn.close()
        return False
    
    added = []
    for meal_type in meal_types:
        type_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO recipe_meal_types (id, recipe_id, meal_type)
            VALUES (?, ?, ?)
        """, (type_id, recipe_id, meal_type))
        added.append(meal_type)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 用餐类型添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   类型：{'/'.join(added)}")
    return True

def list_items(args):
    """查看某食谱的用餐类型"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.name, rmt.meal_type
        FROM recipe_meal_types rmt
        JOIN recipes r ON rmt.recipe_id = r.id
        WHERE rmt.recipe_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有用餐类型信息")
        return True
    
    print(f"\n{rows[0]['name']} - 用餐类型：")
    for row in rows:
        print(f"  - {row['meal_type']}")
    
    return True

def search(args):
    """按用餐类型搜索"""
    meal_type = args.get("<类型>")
    if not meal_type:
        print("错误：请提供用餐类型")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rmt.meal_type
        FROM recipes r
        JOIN recipe_meal_types rmt ON r.id = rmt.recipe_id
        WHERE rmt.meal_type LIKE ?
        ORDER BY r.name
    """, (f"%{meal_type}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到用餐类型：{meal_type}")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'类型':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['meal_type']:<8} {row['difficulty'] or '-':<8} {time_str}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python meal_type_manager.py add <recipe_id> --meal_type <类型>[,<类型2>,...]
    python meal_type_manager.py list <recipe_id>
    python meal_type_manager.py search <类型>

用餐类型：早/中/晚/夜宵/下午茶/聚会
""")
        return
    
    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
    
    args = {}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--meal_type"):
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
            elif action == "search" and "<类型>" not in args:
                args["<类型>"] = arg
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