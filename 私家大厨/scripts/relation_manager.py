#!/usr/bin/env python3
"""
私家大厨 - 食谱派生关系管理
管理表：recipe_relations
支持：add / list-parent / list-child / list-all / update
"""

import sys
import uuid
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection
from cli_formatter import emit, parse_json_flag, error  # L3

def add(args):
    """创建派生关系"""
    parent_id = args.get("--parent_id")
    child_id = args.get("--child_id")
    
    if not parent_id or not child_id:
        print("错误：请提供 --parent_id 和 --child_id")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查父食谱
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (parent_id,))
    parent = cursor.fetchone()
    if not parent:
        print(f"未找到父食谱：{parent_id}")
        conn.close()
        return False
    
    # 检查子食谱
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (child_id,))
    child = cursor.fetchone()
    if not child:
        print(f"未找到子食谱：{child_id}")
        conn.close()
        return False
    
    relation_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO recipe_relations (id, parent_id, child_id, relation_type, change_summary)
        VALUES (?, ?, ?, ?, ?)
    """, (
        relation_id,
        parent_id,
        child_id,
        args.get("--relation_type"),
        args.get("--change_summary")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 派生关系创建成功！")
    print(f"   父食谱：{parent['name']}")
    print(f"   子食谱：{child['name']}")
    if args.get("--relation_type"):
        print(f"   类型：{args['--relation_type']}")
    return True

def list_parent(args):
    """查看某食谱的父级"""
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
        SELECT r.name, rr.relation_type, rr.change_summary
        FROM recipe_relations rr
        JOIN recipes r ON rr.parent_id = r.id
        WHERE rr.child_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有父级（是原创食谱）")
        return True
    
    print(f"\n{recipe['name']} - 派生自：")
    for row in rows:
        rel_type = f"（{row['relation_type']}）" if row['relation_type'] else ""
        change = f" - {row['change_summary']}" if row['change_summary'] else ""
        print(f"  {row['name']} {rel_type}{change}")
    
    return True

def list_child(args):
    """查看某食谱的子级"""
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
        SELECT r.name, rr.relation_type, rr.change_summary
        FROM recipe_relations rr
        JOIN recipes r ON rr.child_id = r.id
        WHERE rr.parent_id = ?
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有派生菜")
        return True
    
    print(f"\n{recipe['name']} - 派生出的菜：")
    for row in rows:
        rel_type = f"（{row['relation_type']}）" if row['relation_type'] else ""
        change = f" - {row['change_summary']}" if row['change_summary'] else ""
        print(f"  {row['name']} {rel_type}{change}")
    
    return True

def list_all(args):
    """列出所有派生关系"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
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
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有派生关系记录")
        return True
    
    print(f"\n所有派生关系（共{len(rows)}条）：")
    for row in rows:
        rel_type = f"[{row['relation_type']}]" if row['relation_type'] else ""
        print(f"  {row['parent_name']} → {row['child_name']} {rel_type}")
    
    return True

def update(args):
    """更新关系说明"""
    relation_id = args.get("<relation_id>")
    if not relation_id:
        print("错误：请提供关系ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM recipe_relations WHERE id = ?", (relation_id,))
    relation = cursor.fetchone()
    if not relation:
        print(f"未找到关系：{relation_id}")
        conn.close()
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
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(relation_id)
    cursor.execute(f"UPDATE recipe_relations SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 关系更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python relation_manager.py add --parent_id <id> --child_id <id> [选项]
    python relation_manager.py list-parent <recipe_id>
    python relation_manager.py list-child <recipe_id>
    python relation_manager.py list-all
    python relation_manager.py update <relation_id> [选项]

选项：
    --relation_type 关系类型（派生/变体/改良）
    --change_summary 改动说明
""")
        return
    
    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
    
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