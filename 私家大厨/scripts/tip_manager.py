#!/usr/bin/env python3
"""
私家大厨 - 小贴士管理
管理表：tips
支持：add / list / search / update
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加小贴士"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    content = args.get("--content")
    if not content:
        print("错误：请提供小贴士内容（--content）")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    tip_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO tips (id, recipe_id, step_id, ingredient_id, category, content, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        tip_id,
        recipe_id,
        args.get("--step_id"),
        args.get("--ingredient_id"),
        args.get("--category"),
        content,
        args.get("--priority")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 小贴士添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   内容：{content}")
    if args.get("--category"):
        print(f"   分类：{args['--category']}")
    return True

def list_items(args):
    """查看某食谱的小贴士"""
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
        SELECT t.*, cs.sequence as step_seq, i.name as ingredient_name
        FROM tips t
        LEFT JOIN cooking_steps cs ON t.step_id = cs.id
        LEFT JOIN ingredients i ON t.ingredient_id = i.id
        WHERE t.recipe_id = ?
        ORDER BY t.priority, t.category
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有小贴士")
        return True
    
    print(f"\n{recipe['name']} - 小贴士：")
    for row in rows:
        scope = ""
        if row['step_seq']:
            scope = f"[第{row['step_seq']}步]"
        elif row['ingredient_name']:
            scope = f"[{row['ingredient_name']}]"
        
        cat = f"（{row['category']}）" if row['category'] else ""
        print(f"  {scope}{cat}{row['content']}")
    
    return True

def list_by_step(args):
    """查看某步骤的小贴士"""
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
        SELECT * FROM tips WHERE step_id = ? 
        ORDER BY priority
    """, (step_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n第{step['sequence']}步的小贴士：")
    if rows:
        for row in rows:
            cat = f"（{row['category']}）" if row['category'] else ""
            print(f"  {cat}{row['content']}")
    else:
        print(f"  没有小贴士")
    
    return True

def list_by_ingredient(args):
    """查看某食材的小贴士"""
    ingredient_id = args.get("<ingredient_id>")
    if not ingredient_id:
        print("错误：请提供食材ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM ingredients WHERE id = ?", (ingredient_id,))
    ingredient = cursor.fetchone()
    if not ingredient:
        print(f"未找到食材：{ingredient_id}")
        conn.close()
        return False
    
    cursor.execute("""
        SELECT t.*, r.name as recipe_name
        FROM tips t
        JOIN recipes r ON t.recipe_id = r.id
        WHERE t.ingredient_id = ?
        ORDER BY r.name, t.priority
    """, (ingredient_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n食材「{ingredient['name']}」的小贴士：")
    if rows:
        for row in rows:
            cat = f"（{row['category']}）" if row['category'] else ""
            print(f"  [{row['recipe_name']}] {cat}{row['content']}")
    else:
        print(f"  没有小贴士")
    
    return True

def search(args):
    """搜索小贴士"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误：请提供关键词")
        return False
    
    recipe_id = args.get("--recipe-id")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    if recipe_id:
        cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
        recipe = cursor.fetchone()
        if not recipe:
            print(f"未找到食谱：{recipe_id}")
            conn.close()
            return False
        cursor.execute("""
            SELECT t.*, r.name as recipe_name
            FROM tips t
            JOIN recipes r ON t.recipe_id = r.id
            WHERE t.content LIKE ?
            AND t.recipe_id = ?
            AND r.status != '已废弃'
            ORDER BY t.priority
        """, (f"%{keyword}%", recipe_id))
    else:
        cursor.execute("""
            SELECT t.*, r.name as recipe_name
            FROM tips t
            JOIN recipes r ON t.recipe_id = r.id
            WHERE t.content LIKE ?
            AND r.status != '已废弃'
            ORDER BY r.name, t.priority
        """, (f"%{keyword}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        scope = f"在食谱 {recipe_id} 中" if recipe_id else ""
        print(f"未找到包含'{keyword}'的小贴士 {scope}")
        return True
    
    scope = f"[{recipe['name']}]" if recipe_id else ""
    print(f"\n找到 {len(rows)} 条小贴士 {scope}：")
    for row in rows:
        cat = f"（{row['category']}）" if row['category'] else ""
        step_info = f"[第{row['step_id']}步]" if row['step_id'] else ""
        ing_info = f"[{row['ingredient_id']}]" if row['ingredient_id'] else ""
        print(f"  {step_info}{ing_info}{cat}{row['content']}")
    
    return True


def update(args):
    """更新小贴士"""
    tip_id = args.get("<tip_id>")
    if not tip_id:
        print("错误：请提供小贴士ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM tips WHERE id = ?", (tip_id,))
    tip = cursor.fetchone()
    if not tip:
        print(f"未找到小贴士：{tip_id}")
        conn.close()
        return False
    
    updates = []
    params = []
    
    if args.get("--content"):
        updates.append("content = ?")
        params.append(args["--content"])
    if args.get("--category"):
        updates.append("category = ?")
        params.append(args["--category"])
    if args.get("--priority"):
        updates.append("priority = ?")
        params.append(args["--priority"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(tip_id)
    cursor.execute(f"UPDATE tips SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 小贴士更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python tip_manager.py add <recipe_id> --content <内容> [选项]
    python tip_manager.py list <recipe_id>
    python tip_manager.py list-by-step <step_id>
    python tip_manager.py list-by-ingredient <ingredient_id>
    python tip_manager.py search <关键词> [--recipe-id <食谱ID>]
    python tip_manager.py update <tip_id> [选项]

选项：
    --step_id 关联步骤ID
    --ingredient_id 关联食材ID
    --category 分类（火候/刀工/调味/采购/设备/保存）
    --content 小贴士内容
    --priority 优先级
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
            if action == "add" and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "list" and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "search" and "<关键词>" not in args:
                args["<关键词>"] = arg
            elif action in ("list-by-step",) and "<step_id>" not in args:
                args["<step_id>"] = arg
            elif action in ("list-by-ingredient",) and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            elif action in ("update", "disable") and "<tip_id>" not in args:
                args["<tip_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "list-by-step":
        list_by_step(args)
    elif action == "list-by-ingredient":
        list_by_ingredient(args)
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