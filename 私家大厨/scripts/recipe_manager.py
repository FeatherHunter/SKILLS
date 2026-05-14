#!/usr/bin/env python3
"""
私家大厨 - 食谱管理
管理表：recipes
支持：add / show / list / search / update
"""

import sys
import uuid
from datetime import datetime
from db_config import get_connection

def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def add(args):
    """添加食谱"""
    name = args.get("name") or args.get("<菜名>")
    if not name:
        print("错误：请提供菜名")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否已有同名食谱（非废弃）
    cursor.execute("""
        SELECT id, name, status FROM recipes 
        WHERE name = ? AND status != '已废弃'
    """, (name,))
    existing = cursor.fetchone()
    
    if existing:
        # 查询历史次数
        cursor.execute("""
            SELECT COUNT(*) as cnt, AVG(rating) as avg 
            FROM recipe_history WHERE recipe_id = ?
        """, (existing['id'],))
        hist = cursor.fetchone()
        hist_cnt = int(hist['cnt']) if hist['cnt'] else 0
        hist_avg = hist['avg'] if hist['avg'] else 0
        
        print(f"\n⚠️ 发现同名食谱「{name}」（ID: {existing['id']}，状态：{existing['status']}）")
        if hist_cnt > 0:
            print(f"   做过 {hist_cnt} 次，平均评分 {hist_avg:.1f}")
        print()
        print("请选择：")
        print("1. 查看 — 查看现有食谱详情")
        print("2. 派生 — 基于现有食谱创建新变体（自行输入新菜名）")
        print("3. 更新 — 更新现有食谱内容")
        print("4. 取消 — 放弃本次录入")
        print()
        choice = input("请输入序号（1-4）：").strip()
        
        if choice == "1":
            conn.close()
            show({"<菜名>": existing['id']})
            return True
        elif choice == "2":
            conn.close()
            print()
            new_name = input("请输入新菜名：").strip()
            if not new_name:
                print("已取消")
                return False
            return add({"name": new_name})
        elif choice == "3":
            conn.close()
            update({"<recipe_id>": existing['id']})
            return True
        elif choice == "4":
            conn.close()
            print("已取消")
            return False
        else:
            conn.close()
            print("无效选择，已取消")
            return False
    
    recipe_id = str(uuid.uuid4())
    now = get_now()
    
    cursor.execute("""
        INSERT INTO recipes (
            id, name, description, difficulty, servings, total_time_minutes,
            status, photo_url, source, source_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recipe_id,
        name,
        args.get("--description"),
        args.get("--difficulty"),
        args.get("--servings"),
        args.get("--total_time"),
        args.get("--status") or "未做",
        args.get("--photo_url"),
        args.get("--source"),
        args.get("--source_url"),
        now,
        now
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 食谱添加成功！")
    print(f"   ID: {recipe_id}")
    print(f"   菜名: {name}")
    return True

def show(args):
    """查看食谱详情"""
    name = args.get("name") or args.get("<菜名>") or args.get("<recipe_id>")
    if not name:
        print("错误：请提供菜名或ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 先查主表
    cursor.execute("SELECT * FROM recipes WHERE id = ? OR name LIKE ?", (name, f"%{name}%"))
    recipe = cursor.fetchone()
    
    if not recipe:
        print(f"未找到食谱：{name}")
        conn.close()
        return False
    
    if recipe['status'] == '已废弃':
        print(f"⚠️ 「{recipe['name']}」已废弃")
        conn.close()
        return True
    
    recipe_id = recipe["id"]
    
    # 查分类
    cursor.execute("SELECT * FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    categories = cursor.fetchall()
    
    # 查季节
    cursor.execute("SELECT season FROM recipe_seasons WHERE recipe_id = ?", (recipe_id,))
    seasons = [row["season"] for row in cursor.fetchall()]
    
    # 查烹饪方式
    cursor.execute("SELECT method FROM recipe_cooking_methods WHERE recipe_id = ?", (recipe_id,))
    methods = [row["method"] for row in cursor.fetchall()]
    
    # 查口味
    cursor.execute("SELECT flavor FROM recipe_flavors WHERE recipe_id = ?", (recipe_id,))
    flavors = [row["flavor"] for row in cursor.fetchall()]
    
    # 查饮食标签
    cursor.execute("SELECT tag FROM recipe_diet_tags WHERE recipe_id = ?", (recipe_id,))
    diet_tags = [row["tag"] for row in cursor.fetchall()]
    
    # 查用餐类型
    cursor.execute("SELECT meal_type FROM recipe_meal_types WHERE recipe_id = ?", (recipe_id,))
    meal_types = [row["meal_type"] for row in cursor.fetchall()]
    
    # 查食材
    cursor.execute("SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY sequence", (recipe_id,))
    ingredients = cursor.fetchall()
    
    # 查步骤
    cursor.execute("SELECT * FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence", (recipe_id,))
    steps = cursor.fetchall()
    
    # 查所有步骤的食材投入（用于展示每步用了哪些食材）
    step_ingredients_map = {}
    if steps:
        step_ids = [step['id'] for step in steps]
        placeholders = ','.join(['?' for _ in step_ids])
        cursor.execute(f"""
            SELECT si.step_id, si.quantity_used, si.introduced_at, 
                   i.name, i.unit, i.quantity as total_quantity
            FROM step_ingredients si
            JOIN ingredients i ON si.ingredient_id = i.id
            WHERE si.step_id IN ({placeholders})
            ORDER BY si.step_id
        """, step_ids)
        for row in cursor.fetchall():
            sid = row['step_id']
            if sid not in step_ingredients_map:
                step_ingredients_map[sid] = []
            step_ingredients_map[sid].append(row)
    
    # 查炊具
    cursor.execute("SELECT * FROM cookware WHERE recipe_id = ?", (recipe_id,))
    cookware_list = cursor.fetchall()
    
    # 查背景
    cursor.execute("SELECT * FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    background = cursor.fetchone()
    
    # 查营养
    cursor.execute("SELECT * FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    nutrition = cursor.fetchone()
    
    # 查历史
    cursor.execute("SELECT COUNT(*) as cnt, AVG(rating) as avg_rating FROM recipe_history WHERE recipe_id = ?", (recipe_id,))
    history_stats = cursor.fetchone()
    
    conn.close()
    
    # 打印
    print(f"\n【{recipe['name']}】")
    print(f"难度：{recipe['difficulty'] or '未知'}")
    print(f"总时间：{recipe['total_time_minutes'] or '未知'}分钟")
    print(f"份量：{recipe['servings'] or '未知'}人份")
    
    if history_stats["cnt"]:
        print(f"状态：{recipe['status']}（做过{history_stats['cnt']}次，评分{history_stats['avg_rating']:.1f}）")
    else:
        print(f"状态：{recipe['status']}")
    
    if recipe['source']:
        print(f"来源：{recipe['source']}")
    
    if categories:
        cat = categories[0]
        if cat["cuisine_type"]:
            print(f"菜系：{cat['cuisine_type']}")
        if cat["region"]:
            print(f"地区：{cat['region']}")
        if cat["country"]:
            print(f"国家：{cat['country']}")
    
    if seasons:
        print(f"季节：{'/'.join(seasons)}")
    if methods:
        print(f"烹饪方式：{'/'.join(methods)}")
    if flavors:
        print(f"口味：{'/'.join(flavors)}")
    if diet_tags:
        print(f"饮食标签：{'/'.join(diet_tags)}")
    if meal_types:
        print(f"用餐类型：{'/'.join(meal_types)}")
    
    if cookware_list:
        print(f"\n需要的厨具：")
        for cw in cookware_list:
            print(f"  - {cw['name']}（{cw['category'] or '其他'}）")
    
    if ingredients:
        print(f"\n食材清单（共{len(list(ingredients))}种）：")
        for ing in ingredients:
            qty = f"{ing['quantity']}{ing['unit']}" if ing['quantity'] else ""
            qty_text = ing['quantity_text'] or ""
            opt = "（可选）" if ing['is_optional'] else ""
            print(f"  {ing['sequence']}. {ing['name']} {qty}{qty_text} {opt}")
    
    if steps:
        print(f"\n完整步骤：")
        for step in steps:
            dur = f"（{step['duration_minutes']}分钟）" if step['duration_minutes'] else ""
            heat = f" [{step['heat_level']}]" if step['heat_level'] else ""
            print(f"  第{step['sequence']}步{dur}{heat}：{step['action']}")
            # 展示该步骤投入的食材
            if step['id'] in step_ingredients_map:
                for si in step_ingredients_map[step['id']]:
                    qty_used = f"{si['quantity_used']}{si['unit']}" if si['quantity_used'] else si['unit'] or ""
                    intro = f"（{si['introduced_at']}）" if si['introduced_at'] else ""
                    print(f"    → 投入：{si['name']} {qty_used}{intro}")
    
    if background:
        if background['origin_story']:
            print(f"\n背景故事：{background['origin_story']}")
    
    if nutrition:
        print(f"\n营养信息（每{nutrition['serving_size'] or '份'}{nutrition['serving_unit'] or 'g'}）：")
        if nutrition['calories']:
            print(f"  热量：{nutrition['calories']}kcal")
        if nutrition['protein']:
            print(f"  蛋白质：{nutrition['protein']}g")
        if nutrition['fat']:
            print(f"  脂肪：{nutrition['fat']}g")
        if nutrition['carbs']:
            print(f"  碳水：{nutrition['carbs']}g")
    
    print(f"\nID: {recipe_id}")
    return True

def list_recipes(args):
    """列出食谱"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 组合条件
    conditions = ["status != '已废弃'"]
    params = []
    
    if args.get("--difficulty"):
        conditions.append("difficulty = ?")
        params.append(args["--difficulty"])
    
    if args.get("--status"):
        conditions.append("status = ?")
        params.append(args["--status"])
    
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    
    cursor.execute(f"SELECT id, name, difficulty, total_time_minutes, status FROM recipes{where} ORDER BY name", params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("没有找到食谱")
        return True
    
    print(f"\n共 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间':<8} {'状态'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str:<8} {row['status']}")
    
    return True

def search(args):
    """搜索食谱"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误：请提供关键词")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, r.status
        FROM recipes r
        LEFT JOIN ingredients i ON r.id = i.recipe_id
        WHERE (r.name LIKE ? OR i.name LIKE ?)
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%", f"%{keyword}%"))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到包含'{keyword}'的食谱")
        return True
    
    print(f"\n找到 {len(rows)} 道菜：")
    print(f"{'序号':<4} {'菜名':<20} {'难度':<8} {'时间':<8} {'状态'}")
    print("-" * 60)
    for i, row in enumerate(rows, 1):
        time_str = f"{row['total_time_minutes']}分钟" if row['total_time_minutes'] else "-"
        print(f"{i:<4} {row['name']:<20} {row['difficulty'] or '-':<8} {time_str:<8} {row['status']}")
    
    return True

def update(args):
    """更新食谱"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否存在
    cursor.execute("SELECT id, name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    # 构建更新语句
    updates = []
    params = []
    
    if args.get("--name"):
        updates.append("name = ?")
        params.append(args["--name"])
    if args.get("--description"):
        updates.append("description = ?")
        params.append(args["--description"])
    if args.get("--difficulty"):
        updates.append("difficulty = ?")
        params.append(args["--difficulty"])
    if args.get("--servings"):
        updates.append("servings = ?")
        params.append(args["--servings"])
    if args.get("--total_time"):
        updates.append("total_time_minutes = ?")
        params.append(args["--total_time"])
    if args.get("--status"):
        updates.append("status = ?")
        params.append(args["--status"])
    if args.get("--photo_url"):
        updates.append("photo_url = ?")
        params.append(args["--photo_url"])
    if args.get("--source"):
        updates.append("source = ?")
        params.append(args["--source"])
    
    if not updates:
        print("错误：没有提供要更新的字段")
        conn.close()
        return False
    
    updates.append("updated_at = ?")
    params.append(get_now())
    params.append(recipe_id)
    
    cursor.execute(f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 食谱更新成功！")
    return True

def lint(args):
    """健康检查"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    issues = []
    
    # 检查食材
    cursor.execute("SELECT COUNT(*) as cnt FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()["cnt"] == 0:
        issues.append("⚠️ 没有食材")
    
    # 检查步骤
    cursor.execute("SELECT COUNT(*) as cnt FROM cooking_steps WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()["cnt"] == 0:
        issues.append("⚠️ 没有步骤")
    
    # 检查分类
    cursor.execute("SELECT COUNT(*) as cnt FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()["cnt"] == 0:
        issues.append("⚠️ 没有分类标签")
    
    conn.close()
    
    print(f"\n【{recipe['name']} - 健康检查】")
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✅ 数据完整，无问题")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python recipe_manager.py add <菜名> [选项]
    python recipe_manager.py show <菜名或ID>
    python recipe_manager.py list [选项]
    python recipe_manager.py search <关键词>
    python recipe_manager.py update <recipe_id> [选项]
    python recipe_manager.py lint <recipe_id>
    python recipe_manager.py discard <recipe_id>

选项：
    --description "描述"
    --difficulty 难度（快手菜/简单/中等/困难/大师）
    --servings 份量
    --total_time 总时间（分钟）
    --status 状态（未做/已做/熟练）
    --source 来源
    --photo_url 图片URL
""")
        return
    
    action = sys.argv[1]
    
    # 解析参数
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
            if action == "add" and i == 2:
                args["name"] = arg
            elif action == "show" and i == 2:
                args["<菜名>"] = arg
            elif action == "search" and i == 2:
                args["<关键词>"] = arg
            elif action == "update" and i == 2:
                args["<recipe_id>"] = arg
            elif action in ("lint", "discard") and i == 2:
                args["<recipe_id>"] = arg
            else:
                args[f"arg{i}"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "show":
        show(args)
    elif action == "list":
        list_recipes(args)
    elif action == "search":
        search(args)
    elif action == "update":
        update(args)
    elif action == "lint":
        lint(args)
    elif action == "discard":
        discard(args)
    else:
        print(f"未知操作：{action}")



def discard(args):
    """废弃食谱（标记为已废弃）"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    cursor.execute("UPDATE recipes SET status = '已废弃' WHERE id = ?", (recipe_id,))
    conn.commit()
    conn.close()
    
    print(f"✅ 食谱「{recipe['name']}」已废弃")
    return True

if __name__ == "__main__":
    main()