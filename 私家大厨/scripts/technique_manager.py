#!/usr/bin/env python3
"""
私家大厨 - 技法管理
管理表：step_techniques
支持：add / list-by-recipe / list-by-step / search / update
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加技法"""
    step_id = args.get("--step_id")
    recipe_id = args.get("--recipe_id")
    technique_name = args.get("--technique_name")
    
    if not technique_name:
        print("错误：请提供技法名称（--technique_name）")
        return False
    
    if not step_id and not recipe_id:
        print("错误：请提供 --step_id 或 --recipe_id")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    technique_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO step_techniques (id, step_id, recipe_id, technique_name, description, key_points)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        technique_id,
        step_id,
        recipe_id,
        technique_name,
        args.get("--description"),
        args.get("--key_points")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 技法添加成功！")
    print(f"   技法：{technique_name}")
    if args.get("--description"):
        print(f"   说明：{args['--description']}")
    return True

def list_by_recipe(args):
    """查看某食谱的所有技法"""
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
        SELECT st.*, cs.sequence as step_sequence
        FROM step_techniques st
        LEFT JOIN cooking_steps cs ON st.step_id = cs.id
        WHERE st.recipe_id = ?
        ORDER BY cs.sequence, st.technique_name
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有技法记录")
        return True
    
    print(f"\n{recipe['name']} - 技法列表：")
    for row in rows:
        step_str = f"第{row['step_sequence']}步" if row['step_sequence'] else "通用"
        print(f"  [{step_str}] {row['technique_name']}")
        if row['description']:
            print(f"      说明：{row['description']}")
        if row['key_points']:
            print(f"      要点：{row['key_points']}")
    
    return True

def list_by_step(args):
    """查看某步骤的技法"""
    step_id = args.get("<step_id>")
    if not step_id:
        print("错误：请提供步骤ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, sequence, action FROM cooking_steps WHERE id = ?", (step_id,))
    step = cursor.fetchone()
    if not step:
        print(f"未找到步骤：{step_id}")
        conn.close()
        return False
    
    cursor.execute("""
        SELECT * FROM step_techniques WHERE step_id = ? 
    """, (step_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n第{step['sequence']}步：{step['action']}")
    if rows:
        print(f"   技法：")
        for row in rows:
            print(f"   - {row['technique_name']}")
            if row['key_points']:
                print(f"     要点：{row['key_points']}")
    else:
        print(f"   没有技法")
    
    return True

def search(args):
    """搜索技法"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误：请提供关键词")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT st.*, r.name as recipe_name, cs.sequence as step_sequence
        FROM step_techniques st
        JOIN recipes r ON st.recipe_id = r.id
        LEFT JOIN cooking_steps cs ON st.step_id = cs.id
        WHERE (st.technique_name LIKE ? OR st.description LIKE ?)
          AND r.status != '已废弃'
        ORDER BY st.technique_name
    """, (f"%{keyword}%", f"%{keyword}%"))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到包含'{keyword}'的技法")
        return True
    
    print(f"\n找到 {len(rows)} 个技法：")
    for row in rows:
        step_str = f"(第{row['step_sequence']}步)" if row['step_sequence'] else ""
        print(f"  {row['recipe_name']}{step_str} - {row['technique_name']}")
        if row['description']:
            print(f"    说明：{row['description']}")
    
    return True

def update(args):
    """更新技法"""
    technique_id = args.get("<technique_id>")
    if not technique_id:
        print("错误：请提供技法ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, technique_name FROM step_techniques WHERE id = ?", (technique_id,))
    technique = cursor.fetchone()
    if not technique:
        print(f"未找到技法：{technique_id}")
        conn.close()
        return False
    
    updates = []
    params = []
    
    if args.get("--technique_name"):
        updates.append("technique_name = ?")
        params.append(args["--technique_name"])
    if args.get("--description"):
        updates.append("description = ?")
        params.append(args["--description"])
    if args.get("--key_points"):
        updates.append("key_points = ?")
        params.append(args["--key_points"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(technique_id)
    cursor.execute(f"UPDATE step_techniques SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 技法更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python technique_manager.py add --recipe_id <id> --technique_name <名称> [选项]
    python technique_manager.py list-by-recipe <recipe_id>
    python technique_manager.py list-by-step <step_id>
    python technique_manager.py search <关键词>
    python technique_manager.py update <technique_id> [选项]

选项：
    --step_id 关联步骤ID
    --recipe_id 关联食谱ID
    --technique_name 技法名称
    --description 技法解释
    --key_points 关键要点（用/分隔）
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
            if action in ("list-by-recipe",) and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "list-by-step" and "<step_id>" not in args:
                args["<step_id>"] = arg
            elif action == "search" and "<关键词>" not in args:
                args["<关键词>"] = arg
            elif action in ("update", "disable") and "<technique_id>" not in args:
                args["<technique_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list-by-recipe":
        list_by_recipe(args)
    elif action == "list-by-step":
        list_by_step(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()