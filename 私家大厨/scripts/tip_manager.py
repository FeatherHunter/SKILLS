#!/usr/bin/env python3
"""
私家大厨 - 小贴士管理
管理表:tips
支持:add / list / search / update

L4 阶段:函数体迁 db.execute/query/transaction
"""

import sys
import os
import uuid
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import validators  # L3-tip-bridge: 接 validate_tip_minimum (用户决策 R4)


def add(args):
    """添加小贴士(单 INSERT)"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    content = args.get("--content")
    if not content:
        print("错误:请提供小贴士内容(--content)")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    # 决策 2 · 方案 A+(2026-07-22):--scope 值格式 flag,必须显式传
    scope = args.get("--scope")
    step_id = args.get("--step_id")
    ingredient_id = args.get("--ingredient_id")
    if not scope:
        print("错误:缺少 --scope(决策 2 强制字段)")
        print("   合法值:step / ingredient / recipe")
        print("   - --scope step       → 此 tip 关联某个步骤,需 --step_id")
        print("   - --scope ingredient → 此 tip 关联某个食材,需 --ingredient_id")
        print("   - --scope recipe     → 此 tip 是整道菜级,step_id/ingredient_id 都可空")
        print("   怎么修:请拿 hint 去问用户,确认 scope 类型后用 --scope <值> 重试。")
        return False

    # 决策 2 · 方案 A+:scope 规则校验
    scope_validation = validators.validate_tip_scope(scope, step_id, ingredient_id)
    if not scope_validation["valid"]:
        print(f"错误:{scope_validation['error']}")
        if scope == "step":
            print(f"   当前值:--step_id = {step_id}")
            print(f"   期望:步骤 UUID")
            print(f"   怎么修:请拿 hint 去问用户,这 tip 是哪个步骤的?拿到 --step_id 后重试,")
            print(f"   或改 --scope recipe(整道菜级)。")
        elif scope == "ingredient":
            print(f"   当前值:--ingredient_id = {ingredient_id}")
            print(f"   期望:食材 UUID")
            print(f"   怎么修:请拿 hint 去问用户,这 tip 关联哪个食材?拿到 --ingredient_id 后重试,")
            print(f"   或改 --scope recipe(整道菜级)。")
        else:
            print(f"   怎么修:请拿 hint 去问用户,确认 scope 后重试。")
        return False

    # L1 哲学修复(同 P1.2/1.3):category / priority 必须显式提供 — 移除原有的"其他"/1 默认值
    category = args.get("--category")
    priority = args.get("--priority")
    missing = []
    if not category:
        missing.append(("--category", "贴士分类(8 值合法:火候/刀工/调味/采购/设备/保存/文化/其他)"))
    if priority is None:
        missing.append(("--priority", "优先级整数(如 1=低,2=中,3=高)"))
    if missing:
        print("错误:缺少以下必填字段(L1 NOT NULL 兜底,DB 不允许 NULL):")
        for flag, hint in missing:
            print(f"   - {flag}:{hint}")
        print("   怎么修:这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。")
        print("   请拿这些 hint 去问用户,拿到答案后用 --flag <值> 重试。")
        return False

    # CLI-006 修复:category enum 校验(拦截拼错/超集值)
    cat_validation = validators.validate_tip_category(category)
    if not cat_validation["valid"]:
        print(f"错误:{cat_validation['error']}")
        print("   怎么修:请拿 hint 去问用户,确认分类后重试(8 个合法值)。")
        return False

    execute(
        "INSERT INTO tips (id, recipe_id, step_id, ingredient_id, category, content, priority) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            recipe_id,
            step_id,
            ingredient_id,
            category,
            content,
            priority
        )
    )

    print(f"✅ 小贴士添加成功!")
    print(f"   食谱:{recipe[0]['name']}")
    print(f"   内容:{content}")
    print(f"   scope:{scope}")
    if category:
        print(f"   分类:{category}")
    return True


def list_items(args):
    """查看某食谱的小贴士"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误:请提供食谱ID")
        return False

    recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not recipe:
        print(f"未找到食谱:{recipe_id}")
        return False

    rows = query("""
        SELECT t.*, cs.sequence as step_seq, i.name as ingredient_name
        FROM tips t
        LEFT JOIN cooking_steps cs ON t.step_id = cs.id
        LEFT JOIN ingredients i ON t.ingredient_id = i.id
        WHERE t.recipe_id = ?
        ORDER BY t.priority, t.category
    """, (recipe_id,))

    if not rows:
        print(f"\n{recipe[0]['name']} - 没有小贴士")
        return True

    print(f"\n{recipe[0]['name']} - 小贴士:")
    for row in rows:
        scope = ""
        if row['step_seq']:
            scope = f"[第{row['step_seq']}步]"
        elif row['ingredient_name']:
            scope = f"[{row['ingredient_name']}]"

        cat = f"({row['category']})" if row['category'] else ""
        print(f"  {scope}{cat}{row['content']}")

    return True


def list_by_step(args):
    """查看某步骤的小贴士"""
    step_id = args.get("<step_id>")
    if not step_id:
        print("错误:请提供步骤ID")
        return False

    step = query("SELECT id, sequence, action FROM cooking_steps WHERE id = ?", (step_id,))
    if not step:
        print(f"未找到步骤:{step_id}")
        return False

    rows = query("""
        SELECT * FROM tips WHERE step_id = ?
        ORDER BY priority
    """, (step_id,))

    step = step[0]
    print(f"\n第{step['sequence']}步的小贴士:")
    if rows:
        for row in rows:
            cat = f"({row['category']})" if row['category'] else ""
            print(f"  {cat}{row['content']}")
    else:
        print(f"  没有小贴士")

    return True


def list_by_ingredient(args):
    """查看某食材的小贴士"""
    ingredient_id = args.get("<ingredient_id>")
    if not ingredient_id:
        print("错误:请提供食材ID")
        return False

    ingredient = query("SELECT id, name FROM ingredients WHERE id = ?", (ingredient_id,))
    if not ingredient:
        print(f"未找到食材:{ingredient_id}")
        return False

    rows = query("""
        SELECT t.*, r.name as recipe_name
        FROM tips t
        JOIN recipes r ON t.recipe_id = r.id
        WHERE t.ingredient_id = ?
        ORDER BY r.name, t.priority
    """, (ingredient_id,))

    print(f"\n食材「{ingredient[0]['name']}」的小贴士:")
    if rows:
        for row in rows:
            cat = f"({row['category']})" if row['category'] else ""
            print(f"  [{row['recipe_name']}] {cat}{row['content']}")
    else:
        print(f"  没有小贴士")

    return True


def search(args):
    """搜索小贴士"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误:请提供关键词")
        return False

    recipe_id = args.get("--recipe-id")

    if recipe_id:
        recipe = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
        if not recipe:
            print(f"未找到食谱:{recipe_id}")
            return False
        rows = query("""
            SELECT t.*, r.name as recipe_name
            FROM tips t
            JOIN recipes r ON t.recipe_id = r.id
            WHERE t.content LIKE ?
            AND t.recipe_id = ?
            AND r.status != '已废弃'
            ORDER BY t.priority
        """, (f"%{keyword}%", recipe_id))
    else:
        rows = query("""
            SELECT t.*, r.name as recipe_name
            FROM tips t
            JOIN recipes r ON t.recipe_id = r.id
            WHERE t.content LIKE ?
            AND r.status != '已废弃'
            ORDER BY r.name, t.priority
        """, (f"%{keyword}%",))

    if not rows:
        scope = f"在食谱 {recipe_id} 中" if recipe_id else ""
        print(f"未找到包含'{keyword}'的小贴士 {scope}")
        return True

    scope = f"[{recipe[0]['name']}]" if recipe_id else ""
    print(f"\n找到 {len(rows)} 条小贴士 {scope}:")
    for row in rows:
        cat = f"({row['category']})" if row['category'] else ""
        step_info = f"[第{row['step_id']}步]" if row['step_id'] else ""
        ing_info = f"[{row['ingredient_id']}]" if row['ingredient_id'] else ""
        print(f"  {step_info}{ing_info}{cat}{row['content']}")

    return True


def update(args):
    """更新小贴士(L4:动态 SQL)"""
    tip_id = args.get("<tip_id>")
    if not tip_id:
        print("错误:请提供小贴士ID")
        return False

    tip = query("SELECT id FROM tips WHERE id = ?", (tip_id,))
    if not tip:
        print(f"未找到小贴士:{tip_id}")
        return False

    updates = []
    params = []

    if args.get("--content"):
        updates.append("content = ?")
        params.append(args["--content"])
    if args.get("--category"):
        updates.append("category = ?")
        params.append(args["--category"])
    if args.get("--priority"):
        updates.append("priority = ?")
        params.append(args["--priority"])

    if not updates:
        print("没有提供要更新的字段")
        return False

    params.append(tip_id)
    execute(f"UPDATE tips SET {', '.join(updates)} WHERE id = ?", params)

    print(f"✅ 小贴士更新成功!")
    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python tip_manager.py add <recipe_id> --scope <step|ingredient|recipe> --content <内容> [选项]
    python tip_manager.py list <recipe_id>
    python tip_manager.py list-by-step <step_id>
    python tip_manager.py list-by-ingredient <ingredient_id>
    python tip_manager.py search <关键词> [--recipe-id <食谱ID>]
    python tip_manager.py update <tip_id> [选项]

选项:
    --scope step|ingredient|recipe(必填,2026-07-22 决策 2)
        step        → 关联步骤,需 --step_id
        ingredient  → 关联食材,需 --ingredient_id
        recipe      → 整道菜级,step_id/ingredient_id 都可空
    --step_id 关联步骤ID(scope=step 时必填)
    --ingredient_id 关联食材ID(scope=ingredient 时必填)
    --category 分类(火候/刀工/调味/采购/设备/保存/文化/其他)
    --content 小贴士内容
    --priority 优先级
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
            if action == "add" and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "list" and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action == "search" and "<关键词>" not in args:
                args["<关键词>"] = arg
            elif action in ("list-by-step",) and "<step_id>" not in args:
                args["<step_id>"] = arg
            elif action in ("list-by-ingredient",) and "<ingredient_id>" not in args:
                args["<ingredient_id>"] = arg
            elif action in ("update", "disable") and "<tip_id>" not in args:
                args["<tip_id>"] = arg
            i += 1

    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "list-by-step":
        list_by_step(args)
    elif action == "list-by-ingredient":
        list_by_ingredient(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)


if __name__ == "__main__":
    main()