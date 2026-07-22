#!/usr/bin/env python3
"""
私家大厨 - 背景知识管理
管理表：background_knowledge
支持：add / get / update
"""

import sys
import uuid
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection
from cli_formatter import emit, parse_json_flag, error  # L3

def add(args):
    """添加背景知识"""
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
    
    # 检查是否已有背景
    cursor.execute("SELECT id FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    existing = cursor.fetchone()
    
    if existing:
        print(f"警告：{recipe['name']}已有背景知识，使用update命令更新")
        conn.close()
        return False
    
    bg_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO background_knowledge (id, recipe_id, origin_story, historical_background, cultural_significance)
        VALUES (?, ?, ?, ?, ?)
    """, (
        bg_id,
        recipe_id,
        args.get("--origin_story"),
        args.get("--historical_background"),
        args.get("--cultural_significance")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 背景知识添加成功！")
    print(f"   食谱：{recipe['name']}")
    if args.get("--origin_story"):
        print(f"   起源：{args['--origin_story'][:50]}...")
    return True

def get(args):
    """查看背景知识"""
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
    
    cursor.execute("SELECT * FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    bg = cursor.fetchone()
    conn.close()
    
    if not bg:
        print(f"\n{recipe['name']} - 没有背景知识")
        return True
    
    print(f"\n{recipe['name']} - 背景知识：")
    if bg['origin_story']:
        print(f"\n起源故事：")
        print(f"  {bg['origin_story']}")
    if bg['historical_background']:
        print(f"\n历史背景：")
        print(f"  {bg['historical_background']}")
    if bg['cultural_significance']:
        print(f"\n文化意义：")
        print(f"  {bg['cultural_significance']}")
    
    return True

def update(args):
    """更新背景知识"""
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
    
    # 检查是否有背景
    cursor.execute("SELECT id FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    existing = cursor.fetchone()
    
    updates = []
    params = []
    
    if args.get("--origin_story"):
        updates.append("origin_story = ?")
        params.append(args["--origin_story"])
    if args.get("--historical_background"):
        updates.append("historical_background = ?")
        params.append(args["--historical_background"])
    if args.get("--cultural_significance"):
        updates.append("cultural_significance = ?")
        params.append(args["--cultural_significance"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    if existing:
        params.append(recipe_id)
        cursor.execute(f"UPDATE background_knowledge SET {', '.join(updates)} WHERE recipe_id = ?", params)
        conn.commit()
        print(f"✅ 背景知识更新成功！")
    else:
        # 创建新的
        bg_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO background_knowledge (id, recipe_id, origin_story, historical_background, cultural_significance)
            VALUES (?, ?, ?, ?, ?)
        """, (
            bg_id,
            recipe_id,
            args.get("--origin_story"),
            args.get("--historical_background"),
            args.get("--cultural_significance")
        ))
        conn.commit()
        print(f"✅ 背景知识添加成功！")
    
    conn.close()
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python background_manager.py add <recipe_id> --origin_story <故事> [--historical_background <背景>] [--cultural_significance <意义>]
    python background_manager.py get <recipe_id>
    python background_manager.py update <recipe_id> [选项]

选项：
    --origin_story 起源故事
    --historical_background 历史背景
    --cultural_significance 文化意义
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
            if "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "get":
        get(args)
    elif action == "update":
        update(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)

if __name__ == "__main__":
    main()