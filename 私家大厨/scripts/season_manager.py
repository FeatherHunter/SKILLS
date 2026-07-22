#!/usr/bin/env python3
"""
私家大厨 - 季节管理
管理表:recipe_seasons
支持:add / list / search

L4 阶段:函数体迁 db.execute/query/transaction(消除 conn/cursor 模式)
"""

import sys
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
    if len(sys.argv) < 2:
        print("""用法:
    python season_manager.py add <recipe_id> --season <季节>[,<季节2>,...]
    python season_manager.py list <recipe_id>
    python season_manager.py search <季节>

季节选项:春/夏/秋/冬
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
            if i == 2:
                if action == "search":
                    args["<季节>"] = arg
                else:
                    args["<recipe_id>"] = arg
            else:
                args[f"arg{i}"] = arg
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