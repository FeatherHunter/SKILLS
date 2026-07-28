#!/usr/bin/env python3
"""
私家大厨 - 烹饪方式管理
管理表:recipe_cooking_methods
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加烹饪方式(多 INSERT,事务包裹)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    methods_raw = args.get("--method", "")
    methods = [x.strip() for x in methods_raw.split(",") if x.strip()]

    if not methods:
        print("错误:请提供烹饪方式(如 --method 炒)")
        return False

    # L4: db.query 替代 conn/cursor
    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # L4: 多 INSERT 用 transaction 包裹
    try:
        with transaction() as conn:
            for method in methods:
                execute(
                    "INSERT INTO recipe_cooking_methods (id, recipe_id, method) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), recipe_id, method)
                )
    except Exception as e:
        print(f"添加失败:{e}")
        return False

    print(f"✅ 烹饪方式添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   方式:{'/'.join(methods)}")
    return True


def list_items(args):
    """查看某食谱的烹饪方式(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    rows = query("""
        SELECT r.name, rcm.method
        FROM recipe_cooking_methods rcm
        JOIN recipes r ON rcm.recipe_id = r.id
        WHERE rcm.recipe_id = ?
    """, (recipe_id,))

    if not rows:
        print("没有烹饪方式信息")
        return True

    print(f"\n{rows[0]['name']} - 烹饪方式:")
    for row in rows:
        print(f"  - {row['method']}")

    return True


def search(args):
    """按烹饪方式搜索(L4:db.query)"""
    method = args.get("<方式>")
    if not method:
        print("错误:请提供烹饪方式")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rcm.method
        FROM recipes r
        JOIN recipe_cooking_methods rcm ON r.id = rcm.recipe_id
        WHERE rcm.method LIKE ?
        ORDER BY r.name
    """, (f"%{method}%",))

    if not rows:
        print(f"未找到烹饪方式:{method}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'方式':<8} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['method']:<8} {row['difficulty'] or '-':<8} {time_str}")

    return True


def main():
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 烹饪方式管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加烹饪方式标签")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("method", help="烹饪方式(炒/蒸/煮/烤/炸/煎/焖/炖/拌/卤/熏/生食)")

    p_list = sub.add_parser("list", help="列出某菜谱的烹饪方式")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按烹饪方式搜索")
    p_search.add_argument("method", help="烹饪方式(炒/蒸/煮/烤/炸/煎/焖/炖/拌/卤/熏/生食)")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<method>"] = args.method

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)


if __name__ == "__main__":
    main()
