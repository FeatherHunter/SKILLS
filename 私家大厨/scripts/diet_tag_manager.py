#!/usr/bin/env python3
"""
私家大厨 - 饮食标签管理
管理表:recipe_diet_tags
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加饮食标签(多 INSERT,事务包裹)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    tags_raw = args.get("--tag", "")
    tags = [x.strip() for x in tags_raw.split(",") if x.strip()]

    if not tags:
        print("错误:请提供饮食标签(如 --tag 素食)")
        return False

    # L4: db.query
    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # L4: 多 INSERT 用 transaction
    try:
        with transaction() as conn:
            for tag in tags:
                execute(
                    "INSERT INTO recipe_diet_tags (id, recipe_id, tag) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), recipe_id, tag)
                )
    except Exception as e:
        print(f"添加失败:{e}")
        return False

    print(f"✅ 饮食标签添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   标签:{'/'.join(tags)}")
    return True


def list_items(args):
    """查看某食谱的饮食标签(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    rows = query("""
        SELECT r.name, rdt.tag
        FROM recipe_diet_tags rdt
        JOIN recipes r ON rdt.recipe_id = r.id
        WHERE rdt.recipe_id = ?
    """, (recipe_id,))

    if not rows:
        print("没有饮食标签信息")
        return True

    print(f"\n{rows[0]['name']} - 饮食标签:")
    for row in rows:
        print(f"  - {row['tag']}")

    return True


def search(args):
    """按饮食标签搜索(L4:db.query)"""
    tag = args.get("<标签>")
    if not tag:
        print("错误:请提供饮食标签")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rdt.tag
        FROM recipes r
        JOIN recipe_diet_tags rdt ON r.id = rdt.recipe_id
        WHERE rdt.tag LIKE ?
        ORDER BY r.name
    """, (f"%{tag}%",))

    if not rows:
        print(f"未找到饮食标签:{tag}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'标签':<10} {'难度':<8} {'时间'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['tag']:<10} {row['difficulty'] or '-':<8} {time_str}")

    return True


def main():
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 饮食标签管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加饮食标签")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("tag", help="饮食标签(素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白)")

    p_list = sub.add_parser("list", help="列出某菜谱的饮食标签")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按饮食标签搜索")
    p_search.add_argument("tag", help="饮食标签(素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白)")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<tag>"] = args.tag

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)


if __name__ == "__main__":
    main()
