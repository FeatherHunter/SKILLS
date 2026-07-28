#!/usr/bin/env python3
"""
私家大厨 - 用餐类型管理
管理表:recipe_meal_types
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加用餐类型(多 INSERT,事务包裹)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    meal_types_raw = args.get("--meal_type", "")
    meal_types = [x.strip() for x in meal_types_raw.split(",") if x.strip()]

    if not meal_types:
        print("错误:请提供用餐类型(如 --meal_type 晚)")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    try:
        with transaction() as conn:
            for meal_type in meal_types:
                execute(
                    "INSERT INTO recipe_meal_types (id, recipe_id, meal_type) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), recipe_id, meal_type)
                )
    except Exception as e:
        print(f"添加失败:{e}")
        return False

    print(f"✅ 用餐类型添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   类型:{'/'.join(meal_types)}")
    return True


def list_items(args):
    """查看某食谱的用餐类型(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    rows = query("""
        SELECT r.name, rmt.meal_type
        FROM recipe_meal_types rmt
        JOIN recipes r ON rmt.recipe_id = r.id
        WHERE rmt.recipe_id = ?
    """, (recipe_id,))

    if not rows:
        print("没有用餐类型信息")
        return True

    print(f"\n{rows[0]['name']} - 用餐类型:")
    for row in rows:
        print(f"  - {row['meal_type']}")

    return True


def search(args):
    """按用餐类型搜索(L4:db.query)"""
    meal_type = args.get("<类型>")
    if not meal_type:
        print("错误:请提供用餐类型")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rmt.meal_type
        FROM recipes r
        JOIN recipe_meal_types rmt ON r.id = rmt.recipe_id
        WHERE rmt.meal_type LIKE ?
        ORDER BY r.name
    """, (f"%{meal_type}%",))

    if not rows:
        print(f"未找到用餐类型:{meal_type}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'类型':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['meal_type']:<8} {row['difficulty'] or '-':<8} {time_str}")

    return True


def main():
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 用餐类型管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加用餐类型标签")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("type", help="用餐类型(早/中/晚/夜宵/下午茶/聚会)")

    p_list = sub.add_parser("list", help="列出某菜谱的用餐类型")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按用餐类型搜索")
    p_search.add_argument("type", help="用餐类型(早/中/晚/夜宵/下午茶/聚会)")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<type>"] = args.type

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)


if __name__ == "__main__":
    main()
