#!/usr/bin/env python3
"""
私家大厨 - 口味管理
管理表:recipe_flavors
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加口味(多 INSERT,事务包裹)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    flavors_raw = args.get("--flavor", "")
    flavors = [x.strip() for x in flavors_raw.split(",") if x.strip()]

    if not flavors:
        print("错误:请提供口味(如 --flavor 辣)")
        return False

    # L4: db.query 替代 conn/cursor
    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # L4: 多 INSERT 用 transaction 包裹
    try:
        with transaction() as conn:
            for flavor in flavors:
                execute(
                    "INSERT INTO recipe_flavors (id, recipe_id, flavor) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), recipe_id, flavor)
                )
    except Exception as e:
        print(f"添加失败:{e}")
        return False

    print(f"✅ 口味添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   口味:{'/'.join(flavors)}")
    return True


def list_items(args):
    """查看某食谱的口味(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    rows = query("""
        SELECT r.name, rf.flavor
        FROM recipe_flavors rf
        JOIN recipes r ON rf.recipe_id = r.id
        WHERE rf.recipe_id = ?
    """, (recipe_id,))

    if not rows:
        print("没有口味信息")
        return True

    print(f"\n{rows[0]['name']} - 口味:")
    for row in rows:
        print(f"  - {row['flavor']}")

    return True


def search(args):
    """按口味搜索(L4:db.query)"""
    flavor = args.get("<口味>")
    if not flavor:
        print("错误:请提供口味")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rf.flavor
        FROM recipes r
        JOIN recipe_flavors rf ON r.id = rf.recipe_id
        WHERE rf.flavor LIKE ?
        ORDER BY r.name
    """, (f"%{flavor}%",))

    if not rows:
        print(f"未找到口味:{flavor}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'口味':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['flavor']:<8} {row['difficulty'] or '-':<8} {time_str}")

    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python flavor_manager.py add <recipe_id> --flavor <口味>[,<口味2>,...]
    python flavor_manager.py list <recipe_id>
    python flavor_manager.py search <口味>

口味:酸/甜/辣/咸/鲜/苦/麻
""")
        return

    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])

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
        list_items(args)
    elif action == "search":
        search(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)


if __name__ == "__main__":
    main()