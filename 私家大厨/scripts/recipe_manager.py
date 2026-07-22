#!/usr/bin/env python3
"""
私家大厨 - 食谱管理
管理表：recipes
支持：add / show / list / search / update
"""

import sys
import uuid
import json
from datetime import datetime
from db import get_connection, query, execute, transaction  # L4: 函数体迁 db API
from cli_formatter import emit, parse_json_flag, error, success  # L3-补漏

def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def add(args):
    """添加食谱"""
    name = args.get("name") or args.get("<菜名>")
    if not name:
        print("错误：请提供菜名")
        return False
    
    
    # 检查是否已有同名食谱（非废弃）
    rows = query("""
        SELECT id, name, status FROM recipes 
        WHERE name = ? AND status != '已废弃'
    """, (name,))
    existing = rows[0] if rows else None
    
    if existing:
        # 检查是否有 --choice 参数（AI传递的选择）
        choice = args.get("--choice")

        # 如果有选择参数，直接执行
        if choice:
            if choice == "view":
                show({"<菜名>": existing['id']})
                return True
            elif choice == "update":
                update({"<recipe_id>": existing['id']})
                return True
            elif choice == "cancel":
                print(json.dumps({"status": "cancelled", "message": "已取消"}, ensure_ascii=False))
                return False
            elif choice == "derive":
                new_name = args.get("--new_name")
                if not new_name:
                    print(json.dumps({"error": "派生需要 --new_name 参数"}, ensure_ascii=False))
                    return False
                return add({**args, "name": new_name})
            else:
                print(json.dumps({"error": f"无效选择: {choice}", "valid_choices": ["view", "derive", "update", "cancel"]}, ensure_ascii=False))
                return False

        # 没有选择参数，输出JSON格式的冲突信息供AI决策
        hist_rows = query("""
            SELECT COUNT(*) as cnt, AVG(rating) as avg
            FROM recipe_history WHERE recipe_id = ?
        """, (existing['id'],))
        hist = hist_rows[0] if hist_rows else {"cnt": 0, "avg": None}
        hist_cnt = int(hist['cnt']) if hist['cnt'] else 0
        hist_avg = round(float(hist['avg']), 1) if hist['avg'] else 0

    
        # 输出JSON格式的冲突信息
        conflict_info = {
            "conflict": True,
            "message": f"发现同名食谱「{name}」",
            "existing_recipe": {
                "id": existing['id'],
                "name": existing['name'],
                "status": existing['status'],
                "cook_count": hist_cnt,
                "avg_rating": hist_avg
            },
            "choices": [
                {"action": "view", "description": "查看现有食谱详情"},
                {"action": "derive", "description": "基于现有食谱创建新变体（需提供 --new_name）"},
                {"action": "update", "description": "更新现有食谱内容"},
                {"action": "cancel", "description": "放弃本次录入"}
            ],
            "usage": "再次调用时添加 --choice <action> 参数"
        }
        print(json.dumps(conflict_info, ensure_ascii=False, indent=2))
        return True
    
    recipe_id = str(uuid.uuid4())
    now = get_now()
    
    execute("""
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
    
    
    print(f"✅ 食谱添加成功！")
    print(f"   ID: {recipe_id}")
    print(f"   菜名: {name}")
    return True

def show(args, json_mode=False):
    """查看食谱详情(人类友好格式)

    json_mode 参数 L3-补漏 增加,但函数体保留人类友好输出;
    JSON 输出走 show_as_dict() 函数(避免动 show 主体的 361 行 print)
    """
    name = args.get("name") or args.get("<菜名>") or args.get("<recipe_id>")
    if not name:
        if json_mode:
            return error("请提供菜名或ID")
        print("错误：请提供菜名或ID")
        return False
    

    # 1. 精确匹配(优先) — show 是"看这一道",不是"找一找",必须精确
    #    v5.2 修复:之前用 LIKE 模糊匹配,导致拼错菜名也"找到"——用户做错菜
    rows = query("SELECT * FROM recipes WHERE id = ? OR name = ?", (name, name))
    recipe = rows[0] if rows else None

    if not recipe:
        # 2. fallback:用 search 的逻辑找相似,给用户友好提示
        rows = query("SELECT name FROM recipes WHERE name LIKE ? LIMIT 5", (f"%{name}%",))
        similar = rows
        if similar:
            similar_names = [s['name'] for s in similar]
            print(f"未找到食谱:{name}")
            print(f"  但找到 {len(similar_names)} 个相似菜:")
            for n in similar_names:
                print(f"    - {n}")
            print(f"  提示:输入 '查看食谱 完整菜名' 重新查看")
        else:
            print(f"未找到食谱:{name}(也没找到相似菜)")
            print(f"  试试 '搜索食谱 {name}' 模糊搜,或 '查看全部' 列所有菜")
        return False

    recipe_status = recipe["status"]
    if recipe_status == '已废弃':
        print(f"⚠️ 「{recipe['name']}」已废弃")
        return True

    recipe_id = recipe["id"]
    
    # 查分类
    rows = query("SELECT * FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    categories = rows
    
    rows = query("SELECT season FROM recipe_seasons WHERE recipe_id = ?", (recipe_id,))
    seasons = [row["season"] for row in rows]
    
    rows = query("SELECT method FROM recipe_cooking_methods WHERE recipe_id = ?", (recipe_id,))
    methods = [row["method"] for row in rows]
    
    rows = query("SELECT flavor FROM recipe_flavors WHERE recipe_id = ?", (recipe_id,))
    flavors = [row["flavor"] for row in rows]
    
    rows = query("SELECT tag FROM recipe_diet_tags WHERE recipe_id = ?", (recipe_id,))
    diet_tags = [row["tag"] for row in rows]
    
    rows = query("SELECT meal_type FROM recipe_meal_types WHERE recipe_id = ?", (recipe_id,))
    meal_types = [row["meal_type"] for row in rows]
    
    # 查食材
    rows = query("SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY sequence", (recipe_id,))
    ingredients = list(rows)
    
    # 查步骤
    rows = query("SELECT * FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence", (recipe_id,))
    steps = list(rows)
    
    # 查步骤食材投入
    step_ingredients_map = {}
    if steps:
        step_ids = [step['id'] for step in steps]
        placeholders = ','.join(['?' for _ in step_ids])
        rows = query(f"""
            SELECT si.step_id, si.quantity_used, si.introduced_at, 
                   i.name, i.unit, i.quantity as total_quantity, i.sequence as ing_seq
            FROM step_ingredients si
            JOIN ingredients i ON si.ingredient_id = i.id
            WHERE si.step_id IN ({placeholders})
            ORDER BY si.step_id, i.sequence
        """, step_ids)
        for row in rows:
            sid = row['step_id']
            if sid not in step_ingredients_map:
                step_ingredients_map[sid] = []
            step_ingredients_map[sid].append(row)
    
    # 查步骤技法
    step_techniques_map = {}
    if steps:
        step_ids = [step['id'] for step in steps]
        placeholders = ','.join(['?' for _ in step_ids])
        rows = query(f"""
            SELECT st.step_id, st.technique_name, st.description, st.key_points
            FROM step_techniques st
            WHERE st.step_id IN ({placeholders})
        """, step_ids)
        for row in rows:
            sid = row['step_id']
            if sid not in step_techniques_map:
                step_techniques_map[sid] = []
            step_techniques_map[sid].append(row)
    
    # 查步骤小贴士
    step_tips_map = {}
    rows = query("SELECT step_id, category, content, priority FROM tips WHERE recipe_id = ?", (recipe_id,))
    for row in rows:
        sid = row['step_id']
        if sid:
            if sid not in step_tips_map:
                step_tips_map[sid] = []
            step_tips_map[sid].append(row)
    
    # 查全局小贴士
    global_tips = []
    rows = query("SELECT category, content, priority FROM tips WHERE recipe_id = ? AND step_id IS NULL", (recipe_id,))
    global_tips = list(rows)
    
    # 查炊具
    rows = query("SELECT * FROM cookware WHERE recipe_id = ?", (recipe_id,))
    cookware_list = rows
    
    # 查背景
    rows = query("SELECT * FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    background = rows[0] if rows else None
    
    # 查营养
    rows = query("SELECT * FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    nutrition = rows[0] if rows else None
    
    # 查历史统计
    rows = query("SELECT COUNT(*) as cnt, AVG(rating) as avg_rating FROM recipe_history WHERE recipe_id = ?", (recipe_id,))
    history_stats = rows[0] if rows else None
    
    # 查历史详情
    rows = query("SELECT * FROM recipe_history WHERE recipe_id = ? ORDER BY cook_date DESC", (recipe_id,))
    history_list = list(rows)
    
    # 查派生关系
    rows = query("SELECT * FROM recipe_relations WHERE parent_id = ? OR child_id = ?", (recipe_id, recipe_id))
    relations = list(rows)

    # 食材在哪些步骤使用
    ing_steps_map = {}
    rows = query("""
        SELECT si.ingredient_id, cs.sequence
        FROM step_ingredients si
        JOIN cooking_steps cs ON si.step_id = cs.id
        WHERE cs.recipe_id = ?
    """, (recipe_id,))
    for row in rows:
        ing_id, seq = row
        if ing_id not in ing_steps_map:
            ing_steps_map[ing_id] = []
        ing_steps_map[ing_id].append(f"{seq}")

    
    # ==================== 格式设计开始 ====================
    SEP = "─" * 54
    SEP_MID = "─" * 10
    
    # 1. 头部信息
    print(f"\n{'═' * 54}")
    print(f"  🍳 {recipe['name']}")
    print(f"{'═' * 54}")
    
    # 基本信息横排
    basic_info = []
    basic_info.append(f"难度 {recipe['difficulty'] or '?'}")
    basic_info.append(f"总时间 {recipe['total_time_minutes'] or '?'}分钟")
    basic_info.append(f"份量 {recipe['servings'] or '?'}人份")
    print(f"\n  📊 {' | '.join(basic_info)}")
    
    if history_stats["cnt"]:
        print(f"  ✅ {recipe_status}（做过{history_stats['cnt']}次，评分{history_stats['avg_rating']:.1f}）")
    else:
        print(f"  📌 {recipe_status}")
    
    if recipe['source']:
        print(f"  📖 来源：{recipe['source']}")
    if recipe['description']:
        print(f"  💬 {recipe['description']}")
    
    # 2. 分类信息（横排，紧凑）
    cat = categories[0] if categories else {}
    tags_list = []
    if cat['cuisine_type']:
        tags_list.append(cat['cuisine_type'])
    if seasons:
        tags_list.extend(seasons)
    if methods:
        tags_list.extend(methods)
    if flavors:
        tags_list.extend(flavors)
    if diet_tags:
        tags_list.extend(diet_tags)
    if meal_types:
        tags_list.extend(meal_types)
    
    if tags_list:
        print(f"\n  🏷️  {' · '.join(tags_list)}")
    
    # 3. 炊具
    if cookware_list:
        cw_names = [f"{cw['name']}({cw['category'] or '其他'})" for cw in cookware_list]
        print(f"\n  🍳 炊具：{', '.join(cw_names)}")
    
    # 4. 食材清单
    if ingredients:
        print(f"\n{'═' * 54}")
        print(f"  🥬 食材清单（共{len(ingredients)}种）")
        print(f"{'═' * 54}")
        
        for ing in ingredients:
            seq = ing['sequence']
            name_ing = ing['name']
            qty = f"{ing['quantity']}{ing['unit']}" if ing['quantity'] else ""
            qty_text = ing['quantity_text'] or ""
            opt = " ⭐可选" if ing['is_optional'] else ""
            sub = f" → 可用{ing['substitute']}" if ing['substitute'] else ""
            used = ing_steps_map.get(ing['id'], [])
            used_str = f" [步{','.join(used)}]" if used else ""
            print(f"  {seq:>2}. {name_ing} {qty}{qty_text}{opt}{sub}{used_str}")
    
    # 5. 完整步骤
    if steps:
        print(f"\n{'═' * 54}")
        print(f"  👨‍🍳 烹饪步骤（共{len(steps)}步）")
        print(f"{'═' * 54}")
        
        for step in steps:
            sid = step['id']
            seq = step['sequence']
            
            # 步骤标题框
            print(f"\n  ┌{'─' * 22} 第{seq}步 {'─' * 22}┐")
            
            # 元信息：时长/火候/温度
            dur = f"{step['duration_minutes']}分钟" if step['duration_minutes'] else "?"
            heat = step['heat_level'] or "?"
            temp = step['temperature'] or "?"
            print(f"  │ ⏱ {dur}  🔥 {heat}  🌡 {temp}")
            
            # 操作（最突出）
            print(f"  │")
            print(f"  │ 📝 操作")
            action_lines = step['action'].split('；')
            bullets = ['①', '②', '③', '④', '⑤', '⑥']
            for i, line in enumerate(action_lines):
                line = line.strip()
                if line:
                    bullet = bullets[i] if i < len(bullets) else "•"
                    print(f"  │    {bullet} {line}")
            
            # 预期结果
            if step['expected_result']:
                print(f"  │")
                print(f"  │ 🎯 预期：{step['expected_result']}")
            
            # 投入食材
            if sid in step_ingredients_map:
                print(f"  │")
                print(f"  │ 🥬 投入")
                for si in step_ingredients_map[sid]:
                    ing_seq = si['ing_seq']
                    ing_name = si['name']
                    qty_used = f"{si['quantity_used']}{si['unit']}" if si['quantity_used'] else si['unit'] or ""
                    intro = si['introduced_at'] or ""
                    intro_str = f" ({intro})" if intro else ""
                    print(f"  │    • [#{ing_seq}] {ing_name} {qty_used}{intro_str}")
            
            # 技法
            if sid in step_techniques_map:
                print(f"  │")
                print(f"  │ 🔪 技法")
                for tech in step_techniques_map[sid]:
                    print(f"  │    ◆ {tech['technique_name']}")
                    if tech['key_points']:
                        kp = tech['key_points'].replace('/', ' | ')
                        print(f"  │       要点：{kp}")
            
            # 小贴士
            if sid in step_tips_map:
                print(f"  │")
                print(f"  │ 💡 贴士")
                for tip in step_tips_map[sid]:
                    print(f"  │    ★ [{tip['category']}] {tip['content']}")
            
            print(f"  └{'─' * 48}┘")
    
    # 6. 全局小贴士
    if global_tips:
        print(f"\n{'═' * 54}")
        print(f"  💡 全局小贴士")
        print(f"{'═' * 54}")
        for tip in global_tips:
            print(f"  ★ [{tip['category']}] {tip['content']}")
    
    # 7. 背景知识
    if background:
        print(f"\n{'═' * 54}")
        print(f"  📖 背景故事")
        print(f"{'═' * 54}")
        if background['origin_story']:
            print(f"  📜 起源：{background['origin_story']}")
        if background['historical_background']:
            print(f"  📚 历史：{background['historical_background']}")
        if background['cultural_significance']:
            print(f"  🎭 文化：{background['cultural_significance']}")
    
    # 8. 烹饪历史
    if history_list:
        print(f"\n{'═' * 54}")
        print(f"  📅 烹饪记录（共{len(history_list)}次）")
        print(f"{'═' * 54}")
        for h in history_list:
            seq = h['cook_sequence'] or "?"
            rating = h['rating'] or "?"
            feedback = h['feedback'] or ""
            print(f"  第{seq}次  ⭐{rating}  {h['cook_date']}")
            if feedback:
                print(f"         \\\"{feedback}\\\"")
    
    # 9. 营养信息
    if nutrition:
        print(f"\n{'═' * 54}")
        serving_size = nutrition['serving_size'] or '?'
        serving_unit = nutrition['serving_unit'] or 'g'
        print(f"  📊 营养信息（每{serving_size}{serving_unit}）")
        print(f"{'═' * 54}")
        nutri_items = []
        if nutrition['calories']:
            nutri_items.append(f"热量 {nutrition['calories']}kcal")
        if nutrition['protein']:
            nutri_items.append(f"蛋白 {nutrition['protein']}g")
        if nutrition['fat']:
            nutri_items.append(f"脂肪 {nutrition['fat']}g")
        if nutrition['carbs']:
            nutri_items.append(f"碳水 {nutrition['carbs']}g")
        if nutrition['fiber'] is not None:
            nutri_items.append(f"纤维 {nutrition['fiber']}g")
        if nutrition['sodium'] is not None:
            nutri_items.append(f"钠 {nutrition['sodium']}mg")
        print(f"  {' | '.join(nutri_items)}")
    
    # 10. 派生关系
    if relations:
        print(f"\n{'═' * 54}")
        print(f"  🔗 派生关系")
        print(f"{'═' * 54}")
        for r in relations:
            rel_type = r['relation_type'] or '?'
            print(f"  → {r['parent_id'][:20]}... [{rel_type}] {r['child_id'][:20]}...")
    
    print(f"\n{'═' * 54}")
    print(f"  ID: {recipe_id}")
    print(f"{'═' * 54}\n")

    return True


def show_as_dict(name: str) -> dict:
    """show() 的 JSON 三段式版本(L3-补漏)。

    与 show() 同样的查询逻辑,但返回结构化 dict,
    让 AI / 程序可直接解析(避免 AI 自己 grep 361 行人类友好 print)。
    """

    # 精确匹配(name 或 id)
    rows = query("SELECT * FROM recipes WHERE id = ? OR name = ?", (name, name))
    recipe = rows[0] if rows else None

    if not recipe:
        # fallback:相似菜名
        rows = query("SELECT name FROM recipes WHERE name LIKE ? LIMIT 5", (f"%{name}%",))
        similar = rows
        similar_names = [s['name'] for s in similar]
        return error(f"未找到食谱:{name}", data={"similar": similar_names})

    recipe_id = recipe['id']

    # 关联子表全量
    rows = query("SELECT cuisine_type, region, country FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    cats = rows
    rows = query("SELECT season FROM recipe_seasons WHERE recipe_id = ?", (recipe_id,))
    seasons = [r['season'] for r in rows]
    rows = query("SELECT method FROM recipe_cooking_methods WHERE recipe_id = ?", (recipe_id,))
    methods = [r['method'] for r in rows]
    rows = query("SELECT flavor FROM recipe_flavors WHERE recipe_id = ?", (recipe_id,))
    flavors = [r['flavor'] for r in rows]
    rows = query("SELECT tag FROM recipe_diet_tags WHERE recipe_id = ?", (recipe_id,))
    diet_tags = [r['tag'] for r in rows]
    rows = query("SELECT meal_type FROM recipe_meal_types WHERE recipe_id = ?", (recipe_id,))
    meal_types = [r['meal_type'] for r in rows]
    rows = query("""SELECT id, name, category, quantity, unit, quantity_text, is_optional, substitute, sequence
                      FROM ingredients WHERE recipe_id = ? ORDER BY sequence""", (recipe_id,))
    ingredients = [dict(r) for r in rows]
    rows = query("""SELECT id, sequence, action, duration_minutes, heat_level, temperature, expected_result
                      FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence""", (recipe_id,))
    steps = [dict(r) for r in rows]

    # step_ingredients 按 step_id 分组
    step_id_to_ings = {s['id']: [] for s in steps}
    if steps:
        ids = tuple(s['id'] for s in steps)
        ph = ','.join('?' * len(ids))
        rows = query(f"""SELECT step_id, ingredient_id, quantity_used, introduced_at, unit
                            FROM step_ingredients WHERE step_id IN ({ph})""", ids)
        for si in rows:
            step_id_to_ings[si['step_id']].append(dict(si))

    # 装配 step.ingredients_used
    for step in steps:
        step['ingredients_used'] = step_id_to_ings.get(step['id'], [])

    rows = query("""SELECT id, technique_name, description, key_points
                      FROM step_techniques WHERE recipe_id = ?""", (recipe_id,))
    techniques = [dict(r) for r in rows]
    rows = query("""SELECT id, name, category FROM cookware WHERE recipe_id = ?""", (recipe_id,))
    cookware = [dict(r) for r in rows]
    rows = query("""SELECT id, content, category, priority, step_id, ingredient_id
                      FROM tips WHERE recipe_id = ?""", (recipe_id,))
    tips = [dict(r) for r in rows]
    rows = query("""SELECT id, cook_date, cook_sequence, rating, feedback
                      FROM recipe_history WHERE recipe_id = ? ORDER BY cook_date""", (recipe_id,))
    history = [dict(r) for r in rows]
    rows = query("""SELECT id, origin_story, historical_background, cultural_significance
                      FROM background_knowledge WHERE recipe_id = ?""", (recipe_id,))
    bg_rows = rows
    background = dict(bg_rows[0]) if bg_rows else None
    rows = query("""SELECT id, serving_size, serving_unit, calories, protein, fat, carbs, fiber, sodium
                      FROM nutrition_info WHERE recipe_id = ?""", (recipe_id,))
    nu_rows = rows
    nutrition = dict(nu_rows[0]) if nu_rows else None
    rows = query("""SELECT id, parent_id, child_id, relation_type, change_summary
                      FROM recipe_relations WHERE child_id = ?""", (recipe_id,))
    relations = [dict(r) for r in rows]


    # 主表 dict(排除非业务字段)
    recipe_dict = {
        "id": recipe_id,
        "name": recipe['name'],
        "description": recipe['description'],
        "difficulty": recipe['difficulty'],
        "servings": recipe['servings'],
        "total_time_minutes": recipe['total_time_minutes'],
        "status": recipe['status'],
        "photo_url": recipe['photo_url'],
        "source": recipe['source'],
        "source_url": recipe['source_url'],
        "created_at": recipe['created_at'],
        "updated_at": recipe['updated_at'],
    }

    return success(
        data={
            "recipe": recipe_dict,
            "category": dict(cats[0]) if cats else None,
            "seasons": seasons,
            "cooking_methods": methods,
            "flavors": flavors,
            "diet_tags": diet_tags,
            "meal_types": meal_types,
            "ingredients": ingredients,
            "steps": steps,
            "techniques": techniques,
            "cookware": cookware,
            "tips": tips,
            "history": history,
            "background": background,
            "nutrition": nutrition,
            "relations": relations,
            "tables_summary": {
                "ingredients": len(ingredients),
                "steps": len(steps),
                "tips": len(tips),
                "techniques": len(techniques),
                "cookware": len(cookware),
                "history": len(history),
                "relations": len(relations),
            },
        },
        message=f"已查到食谱「{recipe['name']}」(ID: {recipe_id[:8]}...)"
    )


def list_recipes(args):
    """列出食谱"""

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

    rows = query(f"SELECT id, name, difficulty, total_time_minutes, status FROM recipes{where} ORDER BY name", tuple(params))

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


def list_recipes_as_dict(difficulty=None, status=None) -> list:
    """list_recipes 的 JSON 版本(L3-polish):返回结构化 dict 列表"""
    conditions = ["status != '已废弃'"]
    params = []
    if difficulty:
        conditions.append("difficulty = ?")
        params.append(difficulty)
    if status:
        conditions.append("status = ?")
        params.append(status)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = query(f"SELECT id, name, difficulty, total_time_minutes, status FROM recipes{where} ORDER BY name", tuple(params))
    rows = [dict(r) for r in rows]
    return rows

def search(args):
    """搜索食谱"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误：请提供关键词")
        return False
    
    
    rows = query("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, r.status
        FROM recipes r
        LEFT JOIN ingredients i ON r.id = i.recipe_id
        WHERE (r.name LIKE ? OR i.name LIKE ?)
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%", f"%{keyword}%"))
    
    
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


def search_as_dict(keyword: str) -> list:
    """search 的 JSON 版本(L3-polish)"""
    rows = query("""
        SELECT DISTINCT r.id, r.name, r.difficulty, r.total_time_minutes, r.status
        FROM recipes r
        LEFT JOIN ingredients i ON r.id = i.recipe_id
        WHERE (r.name LIKE ? OR i.name LIKE ?)
        AND r.status != '已废弃'
        ORDER BY r.name
    """, (f"%{keyword}%", f"%{keyword}%"))
    rows = [dict(r) for r in rows]
    return rows

def update(args):
    """更新食谱"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    
    # 检查是否存在
    rows = query("SELECT id, name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = rows[0] if rows else None
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
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
        params.append(int(args["--servings"]))
    if args.get("--total_time"):
        updates.append("total_time_minutes = ?")
        params.append(int(args["--total_time"]))
    if args.get("--status"):
        updates.append("status = ?")
        params.append(args["--status"])
    if args.get("--photo_url"):
        updates.append("photo_url = ?")
        params.append(args["--photo_url"])
    if args.get("--source"):
        updates.append("source = ?")
        params.append(args["--source"])
    if args.get("--source_url"):
        updates.append("source_url = ?")
        params.append(args["--source_url"])
    
    if not updates:
        print("错误：没有提供要更新的字段")
        return False
    
    updates.append("updated_at = ?")
    params.append(get_now())
    params.append(recipe_id)
    
    execute(f"UPDATE recipes SET {', '.join(updates)} WHERE id = ?", tuple(params))
    
    print(f"✅ 食谱更新成功！")
    return True

def lint(args):
    """健康检查"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    
    rows = query("SELECT id, name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = rows[0] if rows else None
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        return False
    
    issues = []
    
    # 检查食材
    rows = query("SELECT COUNT(*) as cnt FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    if rows and rows[0]["cnt"] == 0:
        issues.append("⚠️ 没有食材")
    
    # 检查步骤
    rows = query("SELECT COUNT(*) as cnt FROM cooking_steps WHERE recipe_id = ?", (recipe_id,))
    if rows and rows[0]["cnt"] == 0:
        issues.append("⚠️ 没有步骤")
    
    # 检查分类
    rows = query("SELECT COUNT(*) as cnt FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    if rows and rows[0]["cnt"] == 0:
        issues.append("⚠️ 没有分类标签")
    

    print(f"\n【{recipe['name']} - 健康检查】")
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("✅ 数据完整，无问题")

    return True


def lint_as_dict(recipe_id: str) -> list:
    """lint 的 JSON 版本(L3-polish)"""
    rows = query("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
    if not rows:
        return [{"error": f"未找到食谱:{recipe_id}"}]

    issues = []
    checks = [
        ("ingredients", "食材"),
        ("cooking_steps", "步骤"),
        ("recipe_categories", "分类标签"),
        ("recipe_cooking_methods", "烹饪方式"),
        ("recipe_flavors", "口味"),
    ]
    for table_name, label in checks:
        rows = query(f"""SELECT COUNT(*) as cnt FROM {table_name} WHERE recipe_id = ?""", (recipe_id,))
        if rows and rows[0]["cnt"] == 0:
            issues.append({"type": "missing", "label": label, "table": table_name})
    return issues

def discard(args):
    """废弃食谱（标记为已废弃）"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    
    rows = query("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = rows[0] if rows else None
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        return False
    
    execute("UPDATE recipes SET status = '已废弃' WHERE id = ?", (recipe_id,))
    
    print(f"✅ 食谱「{recipe['name']}」已废弃")
    return True


def export_as_dict(name):
    """组装完整食谱导出 dict(供 json_mode + 模板渲染)。

    CLI-005 + CLI-007 修复(2026-07-22):
    - 从 export_json 拆出 dict 组装层,允许 main() json_mode 复用
    - 修复 4 处 `for r in rows` 引用错变量 bug(techniques/tips/history/relations 都误拿了 ingredients)

    Args:
        name: 菜名或 recipe_id

    Returns:
        dict - 完整食谱数据(17 张表),或 None(未找到 / name 为空)
    """
    if not name:
        return None

    # 1. 定位菜谱(id 精确匹配或 name 模糊)
    find_rows = query("""SELECT id, name FROM recipes WHERE id = ? OR name LIKE ? LIMIT 1""",
        (name, f"%{name}%")
    )
    if not find_rows:
        return None
    rid = find_rows[0]["id"]

    # 2. 主表
    main_rows = query("SELECT * FROM recipes WHERE id = ?", (rid,))
    main = main_rows[0] if main_rows else None

    # 3. 1:1 关联表(改名避免 shadow 上面的 rows)
    cat_rows = query("SELECT * FROM recipe_categories WHERE recipe_id = ?", (rid,))
    cat = cat_rows[0] if cat_rows else None

    nut_rows = query("SELECT * FROM nutrition_info WHERE recipe_id = ?", (rid,))
    nut = nut_rows[0] if nut_rows else None

    bg_rows = query("SELECT * FROM background_knowledge WHERE recipe_id = ?", (rid,))
    bg = bg_rows[0] if bg_rows else None

    # 4. 1:N 标量数组
    def list_col(table, col):
        rows_local = query(f"SELECT {col} FROM {table} WHERE recipe_id = ? ORDER BY rowid", (rid,))
        return [r[col] for r in rows_local]

    seasons = list_col("recipe_seasons", "season")
    methods = list_col("recipe_cooking_methods", "method")
    flavors = list_col("recipe_flavors", "flavor")
    diet_tags = list_col("recipe_diet_tags", "tag")
    meal_types = list_col("recipe_meal_types", "meal_type")

    # 5. 食材(按 sequence)
    ing_rows = query(
        "SELECT sequence, name, category, quantity, unit, quantity_text, is_optional, substitute "
        "FROM ingredients WHERE recipe_id = ? ORDER BY sequence",
        (rid,)
    )
    ingredients = [{
        "name": r["name"],
        "quantity": r["quantity"],
        "unit": r["unit"],
        "category": r["category"],
        "sequence": r["sequence"],
        "is_optional": bool(r["is_optional"]),
        "substitute": r["substitute"],
        "quantity_text": r["quantity_text"],
    } for r in ing_rows]

    # 6. 步骤 + 步骤用材(N+1 不可避免 - 步骤 id 是变量)
    steps_rows = query(
        "SELECT id, sequence, action, duration_minutes, heat_level, temperature, expected_result "
        "FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence",
        (rid,)
    )
    steps = []
    for s in steps_rows:
        sid = s["id"]
        ing_used_rows = query(
            "SELECT si.quantity_used, si.introduced_at, i.name "
            "FROM step_ingredients si "
            "JOIN ingredients i ON si.ingredient_id = i.id "
            "WHERE si.step_id = ?",
            (sid,)
        )
        ing_used = [{
            "name": r["name"],
            "quantity_used": r["quantity_used"],
            "introduced_at": r["introduced_at"],
        } for r in ing_used_rows]

        # G3 修复:把 step_techniques 嵌进 step,让模板能在步骤内 inline 显示
        tech_rows = query(
            "SELECT technique_name, description, key_points "
            "FROM step_techniques WHERE step_id = ? ORDER BY rowid",
            (sid,)
        )
        techs_inline = [{
            "technique_name": r["technique_name"],
            "description": r["description"],
            "key_points": r["key_points"],
        } for r in tech_rows]

        steps.append({
            "sequence": s["sequence"],
            "action": s["action"],
            "duration": s["duration_minutes"],
            "heat_level": s["heat_level"],
            "temperature": s["temperature"],
            "expected_result": s["expected_result"],
            "ingredients_used": ing_used,
            "techniques": techs_inline,
        })

    # 7. 技法(修复:迭代 tech_all_rows,不是上面的 rows shadow)
    tech_all_rows = query(
        "SELECT st.technique_name, st.description, st.key_points, cs.sequence AS step_seq "
        "FROM step_techniques st "
        "JOIN cooking_steps cs ON st.step_id = cs.id "
        "WHERE st.recipe_id = ? ORDER BY cs.sequence",
        (rid,)
    )
    techniques = [{
        "step_sequence": r["step_seq"],
        "technique_name": r["technique_name"],
        "description": r["description"],
        "key_points": r["key_points"],
    } for r in tech_all_rows]

    # 8. 小贴士(修复:迭代 tip_rows)
    tip_rows = query(
        "SELECT t.content, t.category, t.priority, t.ingredient_id, "
        "       cs.sequence AS step_seq, "
        "       i.name AS ingredient_name "
        "FROM tips t "
        "LEFT JOIN cooking_steps cs ON t.step_id = cs.id "
        "LEFT JOIN ingredients i ON t.ingredient_id = i.id "
        "WHERE t.recipe_id = ? "
        "ORDER BY COALESCE(cs.sequence, 0), t.priority",
        (rid,)
    )
    tips = [{
        "step_sequence": r["step_seq"],
        "content": r["content"],
        "category": r["category"],
        "priority": r["priority"],
        "ingredient_id": r["ingredient_id"],
        "ingredient_name": r["ingredient_name"],
    } for r in tip_rows]

    # 9. 炊具
    cookware_rows = query(
        "SELECT name, category FROM cookware WHERE recipe_id = ?",
        (rid,)
    )
    cookware = [{"name": r["name"], "category": r["category"]} for r in cookware_rows]

    # 10. 烹饪历史(修复:迭代 history_rows)
    history_rows = query(
        "SELECT cook_date, cook_sequence, rating, feedback "
        "FROM recipe_history WHERE recipe_id = ? "
        "ORDER BY cook_date DESC, cook_sequence DESC",
        (rid,)
    )
    history = [{
        "cook_date": r["cook_date"],
        "cook_sequence": r["cook_sequence"],
        "rating": r["rating"],
        "feedback": r["feedback"],
    } for r in history_rows]

    # 11. 派生关系(修复:迭代 rel_rows)
    rel_rows = query(
        "SELECT r.parent_id, r.child_id, r.relation_type, r.change_summary, "
        "       p.name AS parent_name, c.name AS child_name, "
        "       CASE WHEN r.parent_id = ? THEN 'parent' ELSE 'child' END AS direction "
        "FROM recipe_relations r "
        "LEFT JOIN recipes p ON r.parent_id = p.id "
        "LEFT JOIN recipes c ON r.child_id = c.id "
        "WHERE r.parent_id = ? OR r.child_id = ? "
        "ORDER BY r.relation_type, p.name, c.name",
        (rid, rid, rid)
    )
    relations = [{
        "direction": r["direction"],
        "relation_type": r["relation_type"],
        "parent_id": r["parent_id"],
        "parent_name": r["parent_name"],
        "child_id": r["child_id"],
        "child_name": r["child_name"],
        "change_summary": r["change_summary"],
    } for r in rel_rows]

    # 12. 组装(CLI-007 修复:source_url 单次出现,去重)
    result = {
        "name": main["name"],
        "description": main["description"],
        "difficulty": main["difficulty"],
        "servings": main["servings"],
        "total_time": main["total_time_minutes"],
        "status": main["status"],
        "photo_url": main["photo_url"],
        "source": main["source"],
        "source_url": main["source_url"],
        "created_at": main["created_at"],
        "updated_at": main["updated_at"],
        "category": {
            "cuisine": cat["cuisine_type"] if cat else None,
            "region": cat["region"] if cat else None,
            "country": cat["country"] if cat else None,
        },
        "seasons": seasons,
        "cooking_methods": methods,
        "flavors": flavors,
        "diet_tags": diet_tags,
        "meal_types": meal_types,
        "ingredients": ingredients,
        "steps": steps,
        "techniques": techniques,
        "tips": tips,
        "cookware": cookware,
        "nutrition": {
            "serving_size": nut["serving_size"] if nut else None,
            "serving_unit": nut["serving_unit"] if nut else None,
            "calories": nut["calories"] if nut else None,
            "protein": nut["protein"] if nut else None,
            "fat": nut["fat"] if nut else None,
            "carbs": nut["carbs"] if nut else None,
            "fiber": nut["fiber"] if nut else None,
            "sodium": nut["sodium"] if nut else None,
        },
        "background": {
            "origin_story": bg["origin_story"] if bg else None,
            "historical_background": bg["historical_background"] if bg else None,
            "cultural_significance": bg["cultural_significance"] if bg else None,
        },
        "history": history,
        "relations": relations,
    }

    return result


def export_json(args):
    """CLI 入口(人类友好:打印完整 JSON 到 stdout)

    修复(2026-07-22):CLI-005 主要修复 — 让 export_as_dict 复用,本函数只负责打印。
    """
    name = args.get("name") or args.get("<菜名>") or args.get("<recipe_id>")
    if not name:
        print("错误:请提供菜名或 ID")
        return False
    result = export_as_dict(name)
    if result is None:
        print(f"未找到食谱:{name}")
        return False
    # 输出 - pretty 默认, --compact 给管线用
    if args.get("--compact"):
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
    python recipe_manager.py export-json <菜名或ID> [--compact]

选项：
    --description "描述"
    --difficulty 难度（快手菜/简单/中等/困难/大师）
    --servings 份量
    --total_time 总时间（分钟）
    --status 状态（未做/已做/熟练）
    --source 来源
    --photo_url 图片URL
    --source_url 来源链接
    --choice 冲突时的选择（view/derive/update/cancel）
    --new_name 派生时的新菜名
""")
        return
    
    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
    
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
            elif action == "export-json" and i == 2:
                args["<菜名>"] = arg
            else:
                args[f"arg{i}"] = arg
            i += 1
    
    if action == "add":
        if json_mode:
            # L3-polish:add 返回最少结果
            emit(success(message="add 命令 json_mode 返回值未实现,人类模式有 print"), json_mode=True)
        else:
            add(args)
    elif action == "show":
        if json_mode:
            # L3-补漏:show 输出 JSON 三段式
            name = args.get("name") or args.get("<菜名>") or args.get("<recipe_id>")
            if not name:
                emit(error("请提供菜名或ID"), json_mode=True)
            else:
                result = show_as_dict(name)
                emit(result, json_mode=True)
        else:
            show(args)
    elif action == "list":
        if json_mode:
            rows = list_recipes_as_dict()
            emit(success(data={"count": len(rows), "recipes": rows}, message=f"共 {len(rows)} 道菜"), json_mode=True)
        else:
            list_recipes(args)
    elif action == "search":
        if json_mode:
            keyword = args.get("name") or args.get("<关键词>")
            if not keyword:
                emit(error("请提供搜索关键词"), json_mode=True)
            else:
                rows = search_as_dict(keyword)
                emit(success(data={"keyword": keyword, "count": len(rows), "results": rows},
                              message=f"关键词「{keyword}」匹配 {len(rows)} 道菜"), json_mode=True)
        else:
            search(args)
    elif action == "update":
        if json_mode:
            emit(success(message="update 命令 json_mode 返回值未实现,人类模式有 print"), json_mode=True)
        else:
            update(args)
    elif action == "lint":
        if json_mode:
            recipe_id = args.get("<recipe_id>")
            if not recipe_id:
                emit(error("请提供 recipe_id"), json_mode=True)
            else:
                issues = lint_as_dict(recipe_id)
                emit(success(data={"recipe_id": recipe_id, "issue_count": len(issues), "issues": issues},
                              message="数据完整,无问题" if not issues else f"发现 {len(issues)} 个问题"),
                     json_mode=True)
        else:
            lint(args)
    elif action == "discard":
        if json_mode:
            emit(success(message="discard 命令 json_mode 返回值未实现"), json_mode=True)
        else:
            discard(args)
    elif action == "export-json":
        if json_mode:
            # CLI-005 修复:复用 export_as_dict,emit 三段式
            name = args.get("name") or args.get("<菜名>") or args.get("<recipe_id>")
            if not name:
                emit(error("请提供菜名或 ID"), json_mode=True)
            else:
                result = export_as_dict(name)
                if result is None:
                    emit(error(f"未找到食谱:{name}"), json_mode=True)
                else:
                    emit(success(data=result, message=f"已导出「{result.get('name', name)}」完整 JSON"), json_mode=True)
        else:
            export_json(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)

if __name__ == "__main__":
    main()