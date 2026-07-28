#!/usr/bin/env python3
"""
私家大厨 - 分类管理
管理表:recipe_categories
支持:add / list / search / update

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加分类(L4:db.query + db.execute)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    # L4: db.query 替代 conn/cursor
    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # L4: db.execute 替代 cursor.execute + conn.commit
    execute(
        "INSERT INTO recipe_categories (id, recipe_id, cuisine_type, region, country) VALUES (?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            recipe_id,
            args.get("--cuisine"),
            args.get("--region"),
            args.get("--country")
        )
    )

    print(f"✅ 分类添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    if args.get("--cuisine"):
        print(f"   菜系:{args['--cuisine']}")
    if args.get("--region"):
        print(f"   地区:{args['--region']}")
    if args.get("--country"):
        print(f"   国家:{args['--country']}")
    return True


def list_items(args):
    """查看某食谱的分类(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    rows = query("SELECT * FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))

    if not rows:
        print("没有分类信息")
        return True

    print(f"\n分类信息:")
    for row in rows:
        if row["cuisine_type"]:
            print(f"  菜系:{row['cuisine_type']}")
        if row["region"]:
            print(f"  地区:{row['region']}")
        if row["country"]:
            print(f"  国家:{row['country']}")

    return True


def search(args):
    """按菜系搜索(L4:db.query)"""
    cuisine = args.get("<菜系>")
    if not cuisine:
        print("错误:请提供菜系")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, r.status,
               c.cuisine_type, c.region
        FROM recipes r
        JOIN recipe_categories c ON r.id = c.recipe_id
        WHERE c.cuisine_type LIKE ?
        ORDER BY r.name
    """, (f"%{cuisine}%",))

    if not rows:
        print(f"未找到菜系:{cuisine}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'菜系':<10} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['cuisine_type'] or '':<10} {row['difficulty'] or '-':<8} {time_str}")

    return True


def update(args):
    """更新分类(L4:db.query 检查 + db.execute 动态更新)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    # L4: db.query 替代 cursor
    existing = query("SELECT id FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))

    if existing:
        # 更新现有记录
        updates = []
        params = []
        if args.get("--cuisine"):
            updates.append("cuisine_type = ?")
            params.append(args["--cuisine"])
        if args.get("--region"):
            updates.append("region = ?")
            params.append(args["--region"])
        if args.get("--country"):
            updates.append("country = ?")
            params.append(args["--country"])

        if updates:
            params.append(recipe_id)
            # L4: db.execute 自动 commit
            execute(f"UPDATE recipe_categories SET {', '.join(updates)} WHERE recipe_id = ?", params)
            print(f"✅ 分类更新成功!")
        else:
            print("没有提供要更新的字段")
    else:
        # 没有记录,创建新的
        execute(
            "INSERT INTO recipe_categories (id, recipe_id, cuisine_type, region, country) VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                recipe_id,
                args.get("--cuisine"),
                args.get("--region"),
                args.get("--country")
            )
        )
        print(f"✅ 分类添加成功!")

    return True


def main():
    """主入口:argparse 子命令模式(§04 原则 8 argparse + §05 改动前 3 问 模板)

    设计:
      - argparse subparsers 自动生成 --help
      - 保留 --json(L3 三段式)
      - subcommand 列表:add / list / search / update
    """
    parser = argparse.ArgumentParser(
        prog="category_manager.py",
        description="私家大厨 · 菜系/地区/国家 管理(§05 改动前 3 问 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    # add
    p_add = sub.add_parser("add", help="添加菜系/地区/国家")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("--cuisine", required=True, help="菜系(如 湘菜)")
    p_add.add_argument("--region", help="地区(如 中国-湖南)")
    p_add.add_argument("--country", help="国家(如 中国)")

    # list
    p_list = sub.add_parser("list", help="列出某菜谱的菜系/地区/国家")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    # search
    p_search = sub.add_parser("search", help="按菜系搜索")
    p_search.add_argument("cuisine", metavar="<菜系>", help="菜系名(如 湘菜)")

    # update
    p_update = sub.add_parser("update", help="更新某菜谱的菜系/地区/国家")
    p_update.add_argument("recipe_id", help="菜谱 UUID")
    p_update.add_argument("--cuisine", help="新菜系")
    p_update.add_argument("--region", help="新地区")
    p_update.add_argument("--country", help="新国家")

    args = parser.parse_args()
    # 兼容旧 API:add/list_items 等期望 dict-like args
    # 将 argparse Namespace 转为 dict (add 期望 "<recipe_id>")
    args_dict = vars(args).copy()
    if args.action in ("add", "list", "update"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<菜系>"] = args.cuisine

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)
    elif args.action == "update":
        update(args_dict)


if __name__ == "__main__":
    main()