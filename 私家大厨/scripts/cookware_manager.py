#!/usr/bin/env python3
"""
私家大厨 - 炊具管理
管理表:cookware
支持:add / list / search / update

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import argparse
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error
import validators  # 决策 3:接入 validate_cookware_category


def add(args):
    """添加炊具(单 INSERT)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    name = args.get("--name")
    if not name:
        print("错误:请提供炊具名称(--name)")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # L1 NOT NULL 兜底(2026-07-22):category 必填 + enum 校验
    category = args.get("--category")
    if not category:
        print("错误:缺少 --category(L1 NOT NULL 兜底,DB 不允许 NULL)")
        print("   合法值:锅 / 炉 / 刀 / 其他")
        print("   怎么修:这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。")
        print("   请拿 hint 去问用户,拿到答案后用 --category <值> 重试。")
        return False
    cat_validation = validators.validate_cookware_category(category)
    if not cat_validation["valid"]:
        print(f"错误:{cat_validation['error']}")
        print("   怎么修:请拿 hint 去问用户,确认分类后重试。")
        return False

    execute(
        "INSERT INTO cookware (id, recipe_id, name, category) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), recipe_id, name, category)
    )

    print(f"✅ 炊具添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   炊具:{name}")
    print(f"   分类:{category}")
    return True


def list_items(args):
    """查看某食谱的炊具"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    rows = query("SELECT * FROM cookware WHERE recipe_id = ?", (recipe_id,))

    if not rows:
        print(f"\n{recipe[0]['name']} - 没有炊具记录")
        return True

    print(f"\n{recipe[0]['name']} - 需要炊具:")
    for row in rows:
        cat = f"[{row['category']}]" if row['category'] else ""
        print(f"  - {cat}{row['name']}")

    return True


def search(args):
    """按炊具名称搜索"""
    keyword = args.get("<炊具名>")
    if not keyword:
        print("错误:请提供炊具名称")
        return False

    rows = query("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, c.name as cookware_name
        FROM recipes r
        JOIN cookware c ON r.id = c.recipe_id
        WHERE c.name LIKE ?
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%",))

    if not rows:
        print(f"未找到需要'{keyword}'的食谱")
        return True

    print(f"\n需要「{keyword}」的食谱(共{len(rows)}道):")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间'}")
    print("-" * 50)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str}")

    return True


def update(args):
    """更新炊具(L4:动态 SQL)"""
    cookware_id = args.get("<cookware_id>")
    if not cookware_id:
        print("错误:请提供炊具ID")
        return False

    cookware = query("SELECT id FROM cookware WHERE id = ?", (cookware_id,))
    if not cookware:
        print(f"未找到炊具:{cookware_id}")
        return False

    updates = []
    params = []

    if args.get("--name"):
        updates.append("name = ?")
        params.append(args["--name"])
    if args.get("--category"):
        updates.append("category = ?")
        params.append(args["--category"])

    if not updates:
        print("没有提供要更新的字段")
        return False

    params.append(cookware_id)
    execute(f"UPDATE cookware SET {', '.join(updates)} WHERE id = ?", params)

    print(f"✅ 炊具更新成功!")
    return True


def main():
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 炊具管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加炊具")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("name", help="炊具名")
    p_add.add_argument("--category", help="类别(锅/炉/刀/其他)")

    p_list = sub.add_parser("list", help="列出某菜谱的炊具")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按炊具名搜索")
    p_search.add_argument("name", help="炊具名")

    p_update = sub.add_parser("update", help="更新某菜谱的炊具")
    p_update.add_argument("recipe_id", help="菜谱 UUID")
    p_update.add_argument("--name", help="新炊具名")
    p_update.add_argument("--category", help="新类别")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list", "update"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<name>"] = args.name

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
