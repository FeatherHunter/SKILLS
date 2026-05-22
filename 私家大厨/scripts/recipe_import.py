#!/usr/bin/env python3
"""
私家大厨 - JSON导入脚本
将JSON格式的食谱数据一次性导入数据库

用法：
    python recipe_import.py import <json_file>
    python recipe_import.py validate <json_file>
    python recipe_import.py template
"""

import sys
import os
import json
import uuid
from datetime import datetime

# 添加scripts目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import get_connection


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_recipe(data):
    """验证食谱JSON数据，返回错误列表"""
    errors = []

    # 1. 必填字段检查
    if not data.get("name"):
        errors.append("缺少必填字段: name（菜名）")
    if not data.get("ingredients"):
        errors.append("缺少必填字段: ingredients（食材列表）")
    if not data.get("steps"):
        errors.append("缺少必填字段: steps（步骤列表）")

    # 2. 数据类型检查
    if "name" in data and not isinstance(data["name"], str):
        errors.append("name 必须是字符串")
    if "servings" in data and data["servings"] is not None:
        if not isinstance(data["servings"], int):
            errors.append("servings 必须是整数")
    if "total_time" in data and data["total_time"] is not None:
        if not isinstance(data["total_time"], (int, float)):
            errors.append("total_time 必须是数字")
    if "difficulty" in data and data["difficulty"] is not None:
        valid_difficulty = ["快手菜", "简单", "中等", "困难", "大师"]
        if data["difficulty"] not in valid_difficulty:
            errors.append(f"difficulty 必须是以下之一: {', '.join(valid_difficulty)}")

    # 3. 食材验证
    if "ingredients" in data and not isinstance(data["ingredients"], list):
        errors.append("ingredients 必须是数组")
    for i, ing in enumerate(data.get("ingredients", [])):
        if not isinstance(ing, dict):
            errors.append(f"ingredients[{i}] 必须是对象")
            continue
        if not ing.get("name"):
            errors.append(f"ingredients[{i}] 缺少 name（食材名）")
        if "quantity" in ing and ing["quantity"] is not None:
            if not isinstance(ing["quantity"], (int, float)):
                errors.append(f"ingredients[{i}].quantity 必须是数字")

    # 4. 步骤验证
    if "steps" in data and not isinstance(data["steps"], list):
        errors.append("steps 必须是数组")
    for i, step in enumerate(data.get("steps", [])):
        if not isinstance(step, dict):
            errors.append(f"steps[{i}] 必须是对象")
            continue
        if not step.get("action"):
            errors.append(f"steps[{i}] 缺少 action（步骤描述）")
        if "sequence" in step and step["sequence"] is not None:
            if not isinstance(step["sequence"], int):
                errors.append(f"steps[{i}].sequence 必须是整数")
        if "duration" in step and step["duration"] is not None:
            if not isinstance(step["duration"], (int, float)):
                errors.append(f"steps[{i}].duration 必须是数字")

    # 5. 营养信息验证
    if "nutrition" in data and data["nutrition"]:
        nutri = data["nutrition"]
        for field in ["calories", "protein", "fat", "carbs", "fiber", "sodium", "serving_size"]:
            if field in nutri and nutri[field] is not None:
                if not isinstance(nutri[field], (int, float)):
                    errors.append(f"nutrition.{field} 必须是数字")

    return errors


def check_conflict(conn, name, choice=None, new_name=None):
    """检查同名食谱冲突，返回 (has_conflict, result)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, status FROM recipes
        WHERE name = ? AND status != '已废弃'
    """, (name,))
    existing = cursor.fetchone()

    if not existing:
        return False, None

    # 有冲突，且没有指定choice
    if not choice:
        cursor.execute("""
            SELECT COUNT(*) as cnt, AVG(rating) as avg
            FROM recipe_history WHERE recipe_id = ?
        """, (existing['id'],))
        hist = cursor.fetchone()
        hist_cnt = int(hist['cnt']) if hist['cnt'] else 0
        hist_avg = round(float(hist['avg']), 1) if hist['avg'] else 0

        return True, {
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

    # 有冲突，且指定了choice
    if choice == "cancel":
        return True, {"status": "cancelled", "message": "已取消"}
    elif choice == "view":
        return True, {"status": "view", "recipe_id": existing['id']}
    elif choice == "derive":
        if new_name:
            # 有new_name，允许继续导入（返回无冲突）
            return False, None
        return True, {"status": "derive", "message": "请提供 --new_name 参数"}
    elif choice == "update":
        return True, {"status": "update", "recipe_id": existing['id']}
    else:
        return True, {"error": f"无效选择: {choice}", "valid_choices": ["view", "derive", "update", "cancel"]}


def create_recipe(conn, data):
    """创建食谱主记录，返回recipe_id"""
    recipe_id = str(uuid.uuid4())
    now = get_now()

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recipes (
            id, name, description, difficulty, servings, total_time_minutes,
            status, photo_url, source, source_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recipe_id,
        data["name"],
        data.get("description"),
        data.get("difficulty"),
        data.get("servings"),
        data.get("total_time"),
        data.get("status", "未做"),
        data.get("photo_url"),
        data.get("source"),
        data.get("source_url"),
        now,
        now
    ))

    return recipe_id


def add_category(conn, recipe_id, category):
    """添加分类信息"""
    if not category:
        return
    cursor = conn.cursor()
    cat_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO recipe_categories (id, recipe_id, cuisine_type, region, country)
        VALUES (?, ?, ?, ?, ?)
    """, (
        cat_id,
        recipe_id,
        category.get("cuisine"),
        category.get("region"),
        category.get("country")
    ))


def add_tag_list(conn, recipe_id, tags, table, column):
    """通用：添加标签列表（季节/烹饪方式/口味/饮食标签/用餐类型）"""
    if not tags:
        return
    cursor = conn.cursor()
    for tag in tags:
        tag_id = str(uuid.uuid4())
        cursor.execute(f"""
            INSERT INTO {table} (id, recipe_id, {column})
            VALUES (?, ?, ?)
        """, (tag_id, recipe_id, tag))


def add_seasons(conn, recipe_id, seasons):
    add_tag_list(conn, recipe_id, seasons, "recipe_seasons", "season")

def add_cooking_methods(conn, recipe_id, methods):
    add_tag_list(conn, recipe_id, methods, "recipe_cooking_methods", "method")

def add_flavors(conn, recipe_id, flavors):
    add_tag_list(conn, recipe_id, flavors, "recipe_flavors", "flavor")

def add_diet_tags(conn, recipe_id, tags):
    add_tag_list(conn, recipe_id, tags, "recipe_diet_tags", "tag")

def add_meal_types(conn, recipe_id, types):
    add_tag_list(conn, recipe_id, types, "recipe_meal_types", "meal_type")


def add_ingredients(conn, recipe_id, ingredients):
    """添加食材列表，返回 {name: id} 映射"""
    if not ingredients:
        return {}
    cursor = conn.cursor()
    name_id_map = {}

    for i, ing in enumerate(ingredients):
        ingredient_id = str(uuid.uuid4())
        name = ing["name"]
        name_id_map[name] = ingredient_id

        cursor.execute("""
            INSERT INTO ingredients (
                id, recipe_id, sequence, name, category, quantity, unit,
                quantity_text, is_optional, substitute
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ingredient_id,
            recipe_id,
            ing.get("sequence", i + 1),
            name,
            ing.get("category"),
            ing.get("quantity"),
            ing.get("unit"),
            ing.get("quantity_text"),
            1 if ing.get("is_optional") else 0,
            ing.get("substitute")
        ))

    return name_id_map


def add_steps(conn, recipe_id, steps, name_id_map):
    """添加步骤列表，返回 {sequence: id} 映射"""
    if not steps:
        return {}
    cursor = conn.cursor()
    seq_id_map = {}

    for i, step in enumerate(steps):
        step_id = str(uuid.uuid4())
        seq = step.get("sequence", i + 1)
        seq_id_map[seq] = step_id

        cursor.execute("""
            INSERT INTO cooking_steps (
                id, recipe_id, sequence, action, duration_minutes,
                heat_level, temperature, expected_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id,
            recipe_id,
            seq,
            step["action"],
            step.get("duration"),
            step.get("heat_level"),
            step.get("temperature"),
            step.get("expected_result")
        ))

        # 处理步骤×食材关联
        for si in step.get("ingredients_used", []):
            ing_name = si.get("name")
            if ing_name and ing_name in name_id_map:
                link_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO step_ingredients (id, step_id, ingredient_id, quantity_used, introduced_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    link_id,
                    step_id,
                    name_id_map[ing_name],
                    si.get("quantity_used"),
                    si.get("introduced_at", f"第{seq}步加入")
                ))

    return seq_id_map


def add_tips(conn, recipe_id, tips, seq_id_map):
    """添加小贴士"""
    if not tips:
        return
    cursor = conn.cursor()
    for tip in tips:
        tip_id = str(uuid.uuid4())
        step_id = None
        if tip.get("step_sequence") and tip["step_sequence"] in seq_id_map:
            step_id = seq_id_map[tip["step_sequence"]]

        cursor.execute("""
            INSERT INTO tips (id, recipe_id, step_id, ingredient_id, category, content, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tip_id,
            recipe_id,
            step_id,
            tip.get("ingredient_id"),
            tip.get("category"),
            tip["content"],
            tip.get("priority")
        ))


def add_techniques(conn, recipe_id, techniques, seq_id_map):
    """添加技法"""
    if not techniques:
        return
    cursor = conn.cursor()
    for tech in techniques:
        tech_id = str(uuid.uuid4())
        step_id = None
        if tech.get("step_sequence") and tech["step_sequence"] in seq_id_map:
            step_id = seq_id_map[tech["step_sequence"]]

        cursor.execute("""
            INSERT INTO step_techniques (id, step_id, recipe_id, technique_name, description, key_points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            step_id,
            recipe_id,
            tech["technique_name"],
            tech.get("description"),
            tech.get("key_points")
        ))


def add_cookware(conn, recipe_id, cookware_list):
    """添加炊具"""
    if not cookware_list:
        return
    cursor = conn.cursor()
    for cw in cookware_list:
        cw_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO cookware (id, recipe_id, name, category)
            VALUES (?, ?, ?, ?)
        """, (cw_id, recipe_id, cw["name"], cw.get("category")))


def add_nutrition(conn, recipe_id, nutrition):
    """添加营养信息"""
    if not nutrition:
        return
    cursor = conn.cursor()
    nutri_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO nutrition_info (
            id, recipe_id, serving_size, serving_unit,
            calories, protein, fat, carbs, fiber, sodium
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nutri_id,
        recipe_id,
        nutrition.get("serving_size"),
        nutrition.get("serving_unit"),
        nutrition.get("calories"),
        nutrition.get("protein"),
        nutrition.get("fat"),
        nutrition.get("carbs"),
        nutrition.get("fiber"),
        nutrition.get("sodium")
    ))


def add_background(conn, recipe_id, background):
    """添加背景知识"""
    if not background:
        return
    cursor = conn.cursor()
    bg_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO background_knowledge (id, recipe_id, origin_story, historical_background, cultural_significance)
        VALUES (?, ?, ?, ?, ?)
    """, (
        bg_id,
        recipe_id,
        background.get("origin_story"),
        background.get("historical_background"),
        background.get("cultural_significance")
    ))


def import_recipe(json_file, choice=None, new_name=None):
    """主导入函数：加载JSON → 验证 → 检查冲突 → 事务导入"""
    # 1. 加载JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"success": False, "errors": [f"JSON格式错误: {str(e)}"]}
    except FileNotFoundError:
        return {"success": False, "errors": [f"文件不存在: {json_file}"]}

    # 2. 验证
    errors = validate_recipe(data)
    if errors:
        return {"success": False, "errors": errors, "hint": "请修正JSON后重新导入"}

    # 3. 检查同名冲突
    conn = get_connection()
    try:
        has_conflict, conflict_result = check_conflict(conn, data["name"], choice, new_name)
        if has_conflict:
            conn.close()
            return conflict_result

        # 4. 处理derive需要new_name的情况
        if choice == "derive" and new_name:
            data["name"] = new_name

        # 5. 开启事务导入
        conn.execute("BEGIN")

        # 创建主记录
        recipe_id = create_recipe(conn, data)

        # 添加分类
        add_category(conn, recipe_id, data.get("category"))

        # 添加标签
        add_seasons(conn, recipe_id, data.get("seasons"))
        add_cooking_methods(conn, recipe_id, data.get("cooking_methods"))
        add_flavors(conn, recipe_id, data.get("flavors"))
        add_diet_tags(conn, recipe_id, data.get("diet_tags"))
        add_meal_types(conn, recipe_id, data.get("meal_types"))

        # 添加食材（返回name→id映射）
        name_id_map = add_ingredients(conn, recipe_id, data.get("ingredients"))

        # 添加步骤（返回seq→id映射，同时处理步骤×食材关联）
        seq_id_map = add_steps(conn, recipe_id, data.get("steps"), name_id_map)

        # 添加可选数据
        add_tips(conn, recipe_id, data.get("tips"), seq_id_map)
        add_techniques(conn, recipe_id, data.get("techniques"), seq_id_map)
        add_cookware(conn, recipe_id, data.get("cookware"))
        add_nutrition(conn, recipe_id, data.get("nutrition"))
        add_background(conn, recipe_id, data.get("background"))

        # 提交事务
        conn.execute("COMMIT")

        # 统计
        stats = {
            "success": True,
            "recipe_id": recipe_id,
            "name": data["name"],
            "ingredients_count": len(data.get("ingredients", [])),
            "steps_count": len(data.get("steps", []))
        }

        # 可选统计
        if data.get("tips"):
            stats["tips_count"] = len(data["tips"])
        if data.get("techniques"):
            stats["techniques_count"] = len(data["techniques"])
        if data.get("cookware"):
            stats["cookware_count"] = len(data["cookware"])
        if data.get("nutrition"):
            stats["has_nutrition"] = True
        if data.get("background"):
            stats["has_background"] = True

        return stats

    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except:
            pass
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def show_template():
    """显示JSON模板路径"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "templates", "recipe_template.json")
    if os.path.exists(template_path):
        print(f"模板文件: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print(f"模板文件不存在: {template_path}")


def main():
    if len(sys.argv) < 2:
        print("""用法：
    python recipe_import.py import <json_file> [--choice <action>] [--new_name <新菜名>]
    python recipe_import.py validate <json_file>
    python recipe_import.py template

说明：
    import   - 导入JSON食谱文件
    validate - 仅验证JSON格式（不导入）
    template - 显示JSON模板

冲突处理选项 (--choice)：
    view     - 查看现有食谱
    derive   - 基于现有食谱创建新变体（需 --new_name）
    update   - 更新现有食谱
    cancel   - 取消导入
""")
        return

    action = sys.argv[1]

    if action == "template":
        show_template()
        return

    if action in ("import", "validate"):
        if len(sys.argv) < 3:
            print(f"错误：请提供JSON文件路径")
            return

        json_file = sys.argv[2]

        if action == "validate":
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                errors = validate_recipe(data)
                if errors:
                    print(f"验证失败：")
                    for err in errors:
                        print(f"  - {err}")
                else:
                    print(f"验证通过！")
            except json.JSONDecodeError as e:
                print(f"JSON格式错误: {e}")
            except FileNotFoundError:
                print(f"文件不存在: {json_file}")
            return

        # import
        choice = None
        new_name = None

        # 解析可选参数
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--choice" and i + 1 < len(sys.argv):
                choice = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--new_name" and i + 1 < len(sys.argv):
                new_name = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        result = import_recipe(json_file, choice=choice, new_name=new_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"未知操作：{action}")


if __name__ == "__main__":
    main()
