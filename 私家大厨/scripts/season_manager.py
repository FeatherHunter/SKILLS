#!/usr/bin/env python3
"""
私家大厨 - 季节管理
管理表:recipe_seasons
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction(消除 conn/cursor 模式)
"""

import sys
import argparse
import uuid
# L4: 函数体迁 db.execute/query/transaction
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error, success  # L3


def add(args):
    """添加季节(多 INSERT,事务包裹)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    seasons_raw = args.get("--season", "")
    seasons = [x.strip() for x in seasons_raw.split(",") if x.strip()]

    if not seasons:
        print("错误:请提供季节(如 --season 春)")
        return False

    # 检查食谱是否存在(L4:db.query)
    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # 多 INSERT → 事务包裹
    try:
        with transaction() as conn:
            for season in seasons:
                execute(
                    "INSERT INTO recipe_seasons (id, recipe_id, season) VALUES (?, ?, ?)",
                    (str(uuid.uuid4()), recipe_id, season)
                )
    except Exception as e:
        print(f"添加失败:{e}")
        return False

    print(f"✅ 季节添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   季节:{'/'.join(seasons)}")
    return True


def list_items(args):
    """查看某食谱的季节(L4:db.query)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    # 改用 db.query
    rows = query("""
        SELECT r.name, rs.season
        FROM recipe_seasons rs
        JOIN recipes r ON rs.recipe_id = r.id
        WHERE rs.recipe_id = ?
    """, (recipe_id,))

    if not rows:
        print("没有季节信息")
        return True

    print(f"\n{rows[0]['name']} - 适合季节:")
    for row in rows:
        print(f"  - {row['season']}")

    return True


def search(args):
    """按季节搜索(L4:db.query)"""
    season = args.get("<季节>")
    if not season:
        print("错误:请提供季节")
        return False

    rows = query("""
        SELECT r.id, r.name, r.difficulty, r.total_time_minutes, rs.season
        FROM recipes r
        JOIN recipe_seasons rs ON r.id = rs.recipe_id
        WHERE rs.season LIKE ?
        ORDER BY r.name
    """, (f"%{season}%",))

    if not rows:
        print(f"未找到季节:{season}")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'季节':<6} {'难度':<8} {'时间'}")
    print("-" * 55)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['season']:<6} {row['difficulty'] or '-':<8} {time_str}")

    return True


def main():
    """主入口:argparse 子命令模式(§05 改动前 3 问 模板)"""
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit("/", 1)[-1],
        description="私有大厨 · 季节标签管理(§05 改动前 3 问 argparse 模板)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON 三段式(§02 L3)")
    sub = parser.add_subparsers(dest="action", required=True, metavar="<action>")

    p_add = sub.add_parser("add", help="添加季节标签")
    p_add.add_argument("recipe_id", help="菜谱 UUID")
    p_add.add_argument("season", help="季节(春/夏/秋/冬)")

    p_list = sub.add_parser("list", help="列出某菜谱的季节")
    p_list.add_argument("recipe_id", help="菜谱 UUID")

    p_search = sub.add_parser("search", help="按季节搜索")
    p_search.add_argument("season", help="季节(春/夏/秋/冬)")

    args = parser.parse_args()
    args_dict = vars(args).copy()
    if args.action in ("add", "list"):
        args_dict["<recipe_id>"] = args.recipe_id
    elif args.action == "search":
        args_dict["<season>"] = args.season

    if args.action == "add":
        add(args_dict)
    elif args.action == "list":
        list_items(args_dict)
    elif args.action == "search":
        search(args_dict)


if __name__ == "__main__":
    main()
