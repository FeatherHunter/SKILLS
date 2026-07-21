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
import tempfile
from pathlib import Path
from datetime import datetime

# 添加scripts目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/references")
from db_config import get_connection
import validators  # 业务层校验器(5 层架构改造)
import enums  # references/enums.py(5 层架构:契约层读 references)


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
    cursor.execute(f"""
        SELECT id, name, status FROM recipes
        WHERE name = ? AND status != '{enums.ARCHIVED_STATUS}'
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


def create_recipe(conn, data, force_id=None):
    """创建食谱主记录,返回 recipe_id。
    force_id 非空时用该 ID(merge 模式)。"""
    recipe_id = force_id or str(uuid.uuid4())
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

        # 处理步骤×食材关联(v5.1 加 unit 列)
        for si in step.get("ingredients_used", []):
            ing_name = si.get("name")
            if ing_name and ing_name in name_id_map:
                link_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO step_ingredients (id, step_id, ingredient_id, quantity_used, introduced_at, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    link_id,
                    step_id,
                    name_id_map[ing_name],
                    si.get("quantity_used"),
                    si.get("introduced_at", "中途加入"),
                    si.get("unit")
                ))
            elif ing_name:
                print(f"警告：步骤引用的食材 '{ing_name}' 未在食材列表中找到，跳过关联")

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


def _delete_recipe_keep_history(conn, recipe_id):
    """删除食谱全部数据,但保留烹饪历史(recipe_history)。
    利用 CASCADE 删主表会自动清理依赖,但 recipe_history 是单独的 FK 行为(无 ON DELETE 限制)。"""
    cursor = conn.cursor()
    # 取消 recipe_history 的外键,避免被一起删(SQLite 需要 PRAGMA)
    cursor.execute("PRAGMA foreign_keys = OFF")
    # 先删全部依赖(显式,因为关了 FK)
    for table in ("recipe_categories", "recipe_seasons", "recipe_cooking_methods",
                  "recipe_flavors", "recipe_diet_tags", "recipe_meal_types",
                  "ingredients", "step_ingredients", "step_techniques", "tips",
                  "cookware", "nutrition_info", "background_knowledge",
                  "recipe_relations"):
        try:
            cursor.execute(f"DELETE FROM {table} WHERE recipe_id = ?", (recipe_id,))
        except Exception:
            pass  # 表可能 schema 不同
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    cursor.execute("PRAGMA foreign_keys = ON")


def _log_import(entry):
    """追加一行 JSON 到 import_log.jsonl(若用户配置了 DB 目录)。"""
    try:
        from db_config import DB_PATH  # type: ignore
        log_path = Path(DB_PATH).parent / "import_log.jsonl"
    except Exception:
        log_path = Path.cwd() / "import_log.jsonl"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # 日志失败不影响主流程


def add_history(conn, recipe_id, history):
    """添加烹饪历史(Option A 扩展)。
    cook_sequence 留空 → 自动递增(从 DB 当前最大 +1)。"""
    if not history:
        return 0
    cursor = conn.cursor()
    # 拿当前最大 cook_sequence(自动递增起点)
    cursor.execute(
        "SELECT COALESCE(MAX(cook_sequence), 0) FROM recipe_history WHERE recipe_id = ?",
        (recipe_id,)
    )
    next_seq = (cursor.fetchone()[0] or 0) + 1

    count = 0
    for h in history:
        seq = h.get("cook_sequence") or next_seq
        cursor.execute(
            "INSERT INTO recipe_history (id, recipe_id, cook_date, cook_sequence, rating, feedback) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                recipe_id,
                h["cook_date"],
                seq,
                h.get("rating"),
                h.get("feedback"),
            )
        )
        count += 1
        if not h.get("cook_sequence"):
            next_seq += 1  # 自动递增
    return count


def add_relations(conn, child_id, relations, child_name):
    """添加派生关系(Option A 扩展)。
    parent_name 查 DB 找 parent_id;若不存在则报错(允许用户先单独录父本)。
    本菜作为 child(子本),relation.relation_type 是固定枚举。"""
    if not relations:
        return 0
    cursor = conn.cursor()
    count = 0
    for r in relations:
        parent_name = r["parent_name"]
        # 自引用检查
        if parent_name == child_name:
            raise ValueError(f"不能派生自身:{parent_name} -> {child_name}")

        # 查父本 ID
        cursor.execute(
            f"SELECT id FROM recipes WHERE name = ? AND status != '{enums.ARCHIVED_STATUS}' LIMIT 1",
            (parent_name,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"未找到父本食谱「{parent_name}」(请先录入父本,或在本批次中提前录入)")
        parent_id = row[0]

        # 重复检查(避免同一对 parent-child 多次登记)
        cursor.execute(
            "SELECT id FROM recipe_relations WHERE parent_id = ? AND child_id = ?",
            (parent_id, child_id)
        )
        if cursor.fetchone():
            # 跳过而非失败(允许幂等)
            continue

        cursor.execute(
            "INSERT INTO recipe_relations (id, parent_id, child_id, relation_type, change_summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                parent_id,
                child_id,
                r.get("relation_type", "派生"),
                r.get("change_summary"),
            )
        )
        count += 1
    return count


def import_recipe(json_file, choice=None, new_name=None, merge=False):
    """主导入函数:加载 JSON → 验证 → 检查冲突 → 事务导入。
    merge=True 时:若同名菜已存在,删除旧数据(保留烹饪历史),复用 recipe_id 重建。"""
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
        existing_recipe_id = None
        if merge:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id FROM recipes WHERE name = ? AND status != '{enums.ARCHIVED_STATUS}' LIMIT 1",
                (data["name"],)
            )
            row = cursor.fetchone()
            if row:
                existing_recipe_id = row["id"]
        else:
            has_conflict, conflict_result = check_conflict(conn, data["name"], choice, new_name)
            if has_conflict:
                conn.close()
                return conflict_result

        # 4. 处理derive需要new_name的情况
        if choice == "derive" and new_name:
            data["name"] = new_name

        # 5. 开启事务导入
        conn.execute("BEGIN")

        # 5a. merge 模式:删旧数据(保留 history),后续插入会复用 recipe_id
        if existing_recipe_id:
            _delete_recipe_keep_history(conn, existing_recipe_id)

        # 创建主记录(merge 模式复用 ID,否则新生成 UUID)
        recipe_id = create_recipe(conn, data, force_id=existing_recipe_id)

        # 添加分类
        add_category(conn, recipe_id, data.get("category"))

        # 添加标签
        add_seasons(conn, recipe_id, data.get("seasons"))
        add_cooking_methods(conn, recipe_id, data.get("cooking_methods"))
        add_flavors(conn, recipe_id, data.get("flavors"))
        add_diet_tags(conn, recipe_id, data.get("diet_tags"))
        add_meal_types(conn, recipe_id, data.get("meal_types"))

        # 添加食材(返回name→id映射)
        name_id_map = add_ingredients(conn, recipe_id, data.get("ingredients"))

        # 添加步骤(返回seq→id映射,同时处理步骤×食材关联)
        seq_id_map = add_steps(conn, recipe_id, data.get("steps"), name_id_map)

        # 添加可选数据
        add_tips(conn, recipe_id, data.get("tips"), seq_id_map)
        add_techniques(conn, recipe_id, data.get("techniques"), seq_id_map)
        add_cookware(conn, recipe_id, data.get("cookware"))
        add_nutrition(conn, recipe_id, data.get("nutrition"))
        add_background(conn, recipe_id, data.get("background"))

        # ── Option A 扩展:history + relations(本菜作为 child)──
        add_history(conn, recipe_id, data.get("history"))
        add_relations(conn, recipe_id, data.get("relations"), data["name"])

        # 提交事务
        conn.execute("COMMIT")

        # 统计(5 层架构改造:统一 {status, data, message} 三段式)
        stats = {
            "status": "success",  # 新标准格式
            "data": {
                "recipe_id": recipe_id,
                "name": data["name"],
                "mode": "merge" if existing_recipe_id else "create",
                "ingredients_count": len(data.get("ingredients", [])),
                "steps_count": len(data.get("steps", []))
            },
            "message": f"成功导入食谱「{data['name']}」(ID: {recipe_id[:8]}...)",
            # 保留旧字段(向后兼容)
            "success": True,
            "recipe_id": recipe_id,
            "name": data["name"],
            "mode": "merge" if existing_recipe_id else "create",
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

        # 写 import_log
        _log_import({
            "ts": get_now(),
            "file": str(json_file),
            "name": data["name"],
            "recipe_id": recipe_id,
            "mode": stats["mode"],
            "success": True,
        })

        return stats

    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        err_result = {
            "status": "error",  # 5 层架构:统一 status
            "data": {"error": str(e)},
            "message": f"导入失败: {str(e)}",
            # 保留旧字段
            "success": False,
            "error": str(e)
        }
        _log_import({
            "ts": get_now(),
            "file": str(json_file),
            "name": data.get("name", "?"),
            "success": False,
            "error": str(e),
        })
        return err_result
    finally:
        conn.close()
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

        # ── Option A 扩展:history + relations(本菜作为 child)──
        add_history(conn, recipe_id, data.get("history"))
        add_relations(conn, recipe_id, data.get("relations"), data["name"])

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
        except Exception:
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
    python recipe_import.py import <json_file> [--choice <action>] [--new_name <新菜名>] [--merge]
    python recipe_import.py validate <json_file>
    python recipe_import.py template

说明：
    import   - 导入JSON食谱文件(支持数组批量、--merge 覆盖同名菜)
    validate - 仅验证JSON格式（不导入）
    template - 显示JSON模板

冲突处理选项 (--choice)：
    view     - 查看现有食谱
    derive   - 基于现有食谱创建新变体（需 --new_name）
    update   - 更新现有食谱(同 --merge,保留烹饪历史)
    cancel   - 取消导入

--merge  : 若同名菜已存在,自动覆盖(保留烹饪历史);无冲突时等同普通 import
数组批量 : JSON 顶层为数组时,逐道导入,失败不影响后续(aggregate result)
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
                # 数组批量校验
                if isinstance(data, list):
                    total_err = 0
                    for i, item in enumerate(data):
                        errors = validate_recipe(item)
                        if errors:
                            print(f"[{i}] {item.get('name', '?')}: {len(errors)} 错")
                            for err in errors[:3]:
                                print(f"  - {err}")
                            total_err += len(errors)
                    print(f"批量校验:{len(data)} 道菜,共 {total_err} 错")
                else:
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
        merge = False

        # 解析可选参数
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--choice" and i + 1 < len(sys.argv):
                choice = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--new_name" and i + 1 < len(sys.argv):
                new_name = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--merge":
                merge = True
                i += 1
            else:
                i += 1

        # 检测是否为数组批量
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                peek_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2))
            return

        if isinstance(peek_data, list):
            # 数组批量模式:每道菜单独导入,merge 按各自同名决定
            results = []
            ok = fail = 0
            for i, item in enumerate(peek_data):
                # 把单道菜 dump 到临时文件,复用 import_recipe 流程
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tf:
                    json.dump(item, tf, ensure_ascii=False)
                    tmp_path = tf.name
                try:
                    r = import_recipe(tmp_path, choice=None, new_name=None, merge=merge)
                    r["_index"] = i
                    r["_name"] = item.get("name", "?")
                    results.append(r)
                    if r.get("success"):
                        ok += 1
                    else:
                        fail += 1
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            aggregate = {
                "batch": True,
                "total": len(peek_data),
                "succeeded": ok,
                "failed": fail,
                "results": results,
            }
            print(json.dumps(aggregate, ensure_ascii=False, indent=2))
        else:
            # 单菜模式
            result = import_recipe(json_file, choice=choice, new_name=new_name, merge=merge)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"未知操作：{action}")


if __name__ == "__main__":
    main()
