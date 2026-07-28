#!/usr/bin/env python3
"""
私家大厨 - 口味管理
管理表:recipe_flavors
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
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
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 口味标签管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加口味标签")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("flavor", help="口味(酸/甜/辣/咸/鲜/苦/麻)")

    p_list = sub.add_parser("list", help="列出某菜谱的口味")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按口味搜索")
    p_search.add_argument("flavor", help="口味(酸/甜/辣/咸/鲜/苦/麻)")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<flavor>"] = args.flavor

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)


if __name__ == "__main__":
    main()
