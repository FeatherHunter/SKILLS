#!/usr/bin/env python3
"""
私家大厨 - 步骤×食材关联管理
管理表：step_ingredients
支持：add / list-by-step / list-by-ingredient
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """关联食材到步骤"""
    step_id = args.get("--step_id")
    ingredient_id = args.get("--ingredient_id")
    
    if not step_id or not ingredient_id:
        print("错误：请提供 --step_id 和 --ingredient_id")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查step是否存在
    cursor.execute("SELECT id, sequence, recipe_id FROM cooking_steps WHERE id = ?", (step_id,))
    step = cursor.fetchone()
    if not step:
        print(f"未找到步骤：{step_id}")
        conn.close()
        return False
    
    # 检查ingredient是否存在
    cursor.execute("SELECT id, name FROM ingredients WHERE id = ?", (ingredient_id,))
    ingredient = cursor.fetchone()
    if not ingredient:
        print(f"未找到食材：{ingredient_id}")
        conn.close()
        return False
    
    link_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO step_ingredients (id, step_id, ingredient_id, quantity_used, introduced_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        link_id,
        step_id,
        ingredient_id,
        args.get("--quantity_used"),
        args.get("--introduced_at")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 步骤×食材关联成功！")
    print(f"   步骤：第{step['sequence']}步")
    print(f"   食材：{ingredient['name']}")
    if args.get("--quantity_used"):
        print(f"   用量：{args['--quantity_used']}")
    return True

def list_by_step(args):
    """查看某步骤的食材"""
    step_id = args.get("<step_id>")
    if not step_id:
        print("错误：请提供步骤ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取步骤信息
    cursor.execute("SELECT id, sequence, action, recipe_id FROM cooking_steps WHERE id = ?", (step_id,))
    step = cursor.fetchone()
    if not step:
        print(f"未找到步骤：{step_id}")
        conn.close()
        return False
    
    # 获取关联的食材
    cursor.execute("""
        SELECT i.name, i.quantity, i.unit, si.quantity_used, si.introduced_at
        FROM step_ingredients si
        JOIN ingredients i ON si.ingredient_id = i.id
        WHERE si.step_id = ?
    """, (step_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n第{step['sequence']}步：{step['action']}")
    if rows:
        print(f"   使用的食材：")
        for row in rows:
            qty_used = f"{row['quantity_used']}" if row['quantity_used'] is not None else ""
            introduced = f"（{row['introduced_at']}）" if row['introduced_at'] else ""
            print(f"   - {row['name']} {qty_used}{row['unit'] or ''} {introduced}")
    else:
        print(f"   没有关联食材")
    
    return True

def list_by_ingredient(args):
    """查看某食材被哪些步骤使用"""
    ingredient_id = args.get("<ingredient_id>")
    if not ingredient_id:
        print("错误：请提供食材ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 获取食材信息
    cursor.execute("SELECT id, name FROM ingredients WHERE id = ?", (ingredient_id,))
    ingredient = cursor.fetchone()
    if not ingredient:
        print(f"未找到食材：{ingredient_id}")
        conn.close()
        return False
    
    # 获取关联的步骤
    cursor.execute("""
        SELECT cs.sequence, cs.action, si.quantity_used, si.introduced_at,
               r.name as recipe_name
        FROM step_ingredients si
        JOIN cooking_steps cs ON si.step_id = cs.id
        JOIN recipes r ON cs.recipe_id = r.id
        WHERE si.ingredient_id = ?
        ORDER BY r.name, cs.sequence
    """, (ingredient_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"\n食材：{ingredient['name']}")
    if rows:
        print(f"   被用于：")
        for row in rows:
            introduced = f"（{row['introduced_at']}）" if row['introduced_at'] else ""
            print(f"   - {row['recipe_name']} 第{row['sequence']}步：{row['action']} {introduced}")
    else:
        print(f"   未被任何步骤使用")
    
    return True

def remove(args):
    """移除关联"""
    link_id = args.get("<link_id>")
    if not link_id:
        print("错误：请提供关联ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM step_ingredients WHERE id = ?", (link_id,))
    conn.commit()
    conn.close()
    
    print(f"✅ 关联已移除")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python step_ingredient_manager.py add --step_id <step_id> --ingredient_id <ingredient_id> [选项]
    python step_ingredient_manager.py list-by-step <step_id>
    python step_ingredient_manager.py list-by-ingredient <ingredient_id>
    python step_ingredient_manager.py remove <link_id>

选项：
    --quantity_used 该步使用量
    --introduced_at 引入时机描述
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
            if action == "list-by-step":
                args["<step_id>"] = arg
            elif action == "list-by-ingredient":
                args["<ingredient_id>"] = arg
            elif action == "remove":
                args["<link_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list-by-step":
        list_by_step(args)
    elif action == "list-by-ingredient":
        list_by_ingredient(args)
    elif action == "remove":
        remove(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()