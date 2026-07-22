#!/usr/bin/env python3
"""
私家大厨 - 饮食标签管理
管理表：recipe_diet_tags
支持：add / list / search
"""

import sys
import uuid
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection
from cli_formatter import emit, parse_json_flag, error  # L3

def add(args):
    """添加饮食标签"""
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
    
    tags_raw = args.get("--tag", "")
    tags = [x.strip() for x in tags_raw.split(",") if x.strip()]
    
    if not tags:
        print("错误：请提供饮食标签（如 --tag 素食）")
        conn.close()
        return False
    
    added = []
    for tag in tags:
        tag_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO recipe_diet_tags (id, recipe_id, tag)
            VALUES (?, ?, ?)
        """, (tag_id, recipe_id, tag))
        added.append(tag)
    
    conn.commit()
    conn.close()
    
    print(f"✅ 饮食标签添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   标签：{'/'.join(added)}")
    return True

def list_items(args):
    """查看某食谱的饮食标签"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.name, rdt.tag
        FROM recipe_diet_tags rdt
        JOIN recipes r ON rdt.recipe_id = r.id
        WHERE rdt.recipe_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有饮食标签信息")
        return True
    
    print(f"\n{rows[0]['name']} - 饮食标签：")
    for row in rows:
        print(f"  - {row['tag']}")
    
    return True

def search(args):
    """按饮食标签搜索"""
    tag = args.get("<标签>")
    if not tag:
        print("错误：请提供饮食标签")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rdt.tag
        FROM recipes r
        JOIN recipe_diet_tags rdt ON r.id = rdt.recipe_id
        WHERE rdt.tag LIKE ?
        ORDER BY r.name
    """, (f"%{tag}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到饮食标签：{tag}")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'标签':<10} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['tag']:<10} {row['difficulty'] or '-':<8} {time_str}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python diet_tag_manager.py add <recipe_id> --tag <标签>[,<标签2>,...]
    python diet_tag_manager.py list <recipe_id>
    python diet_tag_manager.py search <标签>

饮食标签：素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白
""")
        return
    
    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
    
    args = {}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--tag"):
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
            elif action == "search" and "<标签>" not in args:
                args["<标签>"] = arg
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