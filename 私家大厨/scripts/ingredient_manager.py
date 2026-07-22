#!/usr/bin/env python3
"""
私家大厨 - 食材管理
管理表:ingredients
支持:add / list / search / update(只增不删,要废弃食材用 update 把 quantity 改 0 标注不用)

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error


def add(args):
    """添加食材(单 INSERT)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    name = args.get("--name")
    if not name:
        print("错误:请提供食材名称(--name)")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # 获取 sequence(L4:db.query)
    max_seq_rows = query("SELECT MAX(sequence) as max_seq FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    max_seq = max_seq_rows[0]["max_seq"] if max_seq_rows and max_seq_rows[0]["max_seq"] is not None else 0
    sequence = args.get("--sequence") or (max_seq + 1)

    # CLI-001 修复:L1 NOT NULL 兜底 — quantity_text / substitute 必须显式提供(不静默默认值兜底)
    # 设计哲学:L1 NOT NULL 是设计意图,要逼 AI 想清楚再调 CLI。
    quantity_text = args.get("--quantity_text")
    substitute = args.get("--substitute")
    missing = []
    if not quantity_text:
        missing.append(("--quantity_text", "用量文字(如 '适量' / '少许' / '100g')"))
    if not substitute:
        missing.append(("--substitute", "替代食材(如 '可用豆腐代替' / 写'无替代品'表示无)"))
    if missing:
        print("错误:缺少以下必填字段(L1 NOT NULL 兜底,DB 不允许 NULL):")
        for flag, hint in missing:
            print(f"   - {flag}:{hint}")
        print("   怎么修:这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。")
        print("   请拿这些 hint 去问用户,拿到答案后用 --flag <值> 重试。")
        return False

    execute(
        "INSERT INTO ingredients (id, recipe_id, sequence, name, category, quantity, unit, quantity_text, is_optional, substitute) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            recipe_id,
            sequence,
            name,
            args.get("--category"),
            args.get("--quantity"),
            args.get("--unit"),
            quantity_text,
            1 if args.get("--optional") else 0,
            substitute
        )
    )

    print(f"✅ 食材添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   食材:{name}")
    qty = f"{args.get('--quantity', '')}{args.get('--unit', '')}"
    if qty:
        print(f"   用量:{qty}")
    return True


def list_items(args):
    """查看某食谱的食材清单"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    rows = query("""
        SELECT * FROM ingredients
        WHERE recipe_id = ?
        ORDER BY sequence
    """, (recipe_id,))

    if not rows:
        print(f"\n{recipe[0]['name']} - 没有食材记录")
        return True

    print(f"\n{recipe[0]['name']} - 食材清单(共{len(rows)}种):")
    for row in rows:
        qty = f"{row['quantity']}{row['unit']}" if row['quantity'] else ""
        qty_text = row['quantity_text'] or ""
        opt = "(可选)" if row['is_optional'] else ""
        cat = f"[{row['category']}]" if row['category'] else ""
        sub = f" → 可用{row['substitute']}代替" if row['substitute'] else ""
        print(f"  {row['sequence']}. {cat}{row['name']} {qty}{qty_text} {opt}{sub}")

    return True


def search(args):
    """搜索包含某食材的食谱"""
    keyword = args.get("<食材名>")
    if not keyword:
        print("错误:请提供食材名称")
        return False

    rows = query("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, i.name as ingredient
        FROM recipes r
        JOIN ingredients i ON r.id = i.recipe_id
        WHERE i.name LIKE ?
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%",))

    if not rows:
        print(f"未找到包含'{keyword}'的食谱")
        return True

    print(f"\n找到 {len(rows)} 道菜:")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间':<8} {'包含食材'}")
    print("-" * 70)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str:<8} {row['ingredient']}")

    return True


def update(args):
    """更新食材(L4:动态 SQL)"""
    ingredient_id = args.get("<ingredient_id>")
    if not ingredient_id:
        print("错误:请提供食材ID")
        return False

    ingredient = query("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
    if not ingredient:
        print(f"未找到食材:{ingredient_id}")
        return False

    updates = []
    params = []

    if args.get("--name"):
        updates.append("name = ?")
        params.append(args["--name"])
    if args.get("--category"):
        updates.append("category = ?")
        params.append(args["--category"])
    if args.get("--quantity"):
        updates.append("quantity = ?")
        params.append(args["--quantity"])
    if args.get("--unit"):
        updates.append("unit = ?")
        params.append(args["--unit"])
    if args.get("--quantity_text"):
        updates.append("quantity_text = ?")
        params.append(args["--quantity_text"])
    if args.get("--sequence"):
        updates.append("sequence = ?")
        params.append(args["--sequence"])
    if args.get("--substitute"):
        updates.append("substitute = ?")
        params.append(args["--substitute"])

    if not updates:
        print("没有提供要更新的字段")
        return False

    params.append(ingredient_id)
    execute(f"UPDATE ingredients SET {', '.join(updates)} WHERE id = ?", params)

    print(f"✅ 食材更新成功!")
    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python ingredient_manager.py add <recipe_id> --name <食材名> [选项]
    python ingredient_manager.py list <recipe_id>
    python ingredient_manager.py search <食材名>
    python ingredient_manager.py update <ingredient_id> [选项]

选项:
    --name 食材名称
    --category 分类(肉类/蔬菜/调料/海鲜/其他)
    --quantity 用量数值
    --unit 单位(g/kg/ml/个/勺/把等)
    --quantity_text 文字描述(适量/少许)
    --sequence 顺序
    --optional 设为可选
    --substitute 替代食材
""")
        return

    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])

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
            if action in ("add", "list") and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "search" and "<食材名>" not in args:
                args["<食材名>"] = arg
            elif action == "update" and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            elif action == "discard" and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            i += 1

    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)


if __name__ == "__main__":
    main()