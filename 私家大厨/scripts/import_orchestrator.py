#!/usr/bin/env python3
"""
私家大厨 - 导入编排器(L2 阶段新增,L3 阶段完整迁移)
职责:解析 → 校验 → 写入 → 回执(单入口)

L3 阶段改进:
- 完整事务包裹(自己实现,不再桥接 recipe_import)
- 直接调 recipe_import 的 add_* 函数(零代码迁移)
- 加 --json 标志
- 加 tip 业务警告(用 validators.validate_tip_minimum)

供多个调用方复用:
- recipe_import.py(CLI 导入入口)
- 飞书 webhook(以后)
- 批量脚本(以后)
"""

import sys
import os
import json
import uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/references")

import validators
import recipe_import  # L3: 复用 add_* 函数,不搬代码
from db import transaction, query, get_connection  # L2: 走 db.py 数据层
from cli_formatter import emit, parse_json_flag, success, error  # L3


# ====================================================================
# 主编排函数(完整事务包裹)
# ====================================================================

def orchestrate_import(data: dict, dry_run: bool = False) -> dict:
    """
    单菜导入编排。流程:
    1. 校验(validators 完整链 + 占位符黑名单)
    2. dry-run 短路(只校验不写)
    3. 事务包裹写入(主表 + 17 张子表)
    4. 收 tip 业务警告

    Args:
        data: dict 形式(JSON 解析后)
        dry_run: True 时只校验不写

    Returns:
        {"status": "success"/"error"/"dry_run",
         "data": {"recipe_id": "...", "child_ids": {...}},
         "message": "...",
         "tips_warnings": [...],  # 可选
         "errors": [...]}  # 可选
    """
    # 1. 校验
    validation = validators.validate_recipe_for_import(data)
    if not validation["valid"]:
        return {
            "status": "error",
            "stage": "validation",
            "data": {},
            "message": validation.get("suggested_user_question") or "校验失败",
            "errors": validation.get("errors", []),
            "tips_warnings": validation.get("tips_warnings")
        }

    # 2. dry-run 短路
    if dry_run:
        return {
            "status": "dry_run",
            "stage": "validation",
            "data": {"name": data.get("name")},
            "message": "校验通过,未写入 DB",
            "tips_warnings": validation.get("tips_warnings")
        }

    # 3. 完整事务包裹(L3 关键改进:自己实现,不再桥接)
    recipe_id = None
    child_ids = {}
    tip_warnings = []
    try:
        with transaction() as conn:
            # 3a. 主表
            recipe_id = recipe_import.create_recipe(conn, data)
            child_ids["recipes"] = recipe_id

            # 3b. 1:1 必录(用户决策 2):先 nutrition + background,FAIL FAST
            # 注意:这两张表是 UNIQUE,recipe_id 唯一,所以即使 dry-run 通过,
            # 这里写两次会冲突。L3 不做特殊处理,让 DB 报 unique constraint 即可。
            if data.get("nutrition"):
                recipe_import.add_nutrition(conn, recipe_id, data["nutrition"])
                child_ids["nutrition_info"] = "recorded"
            if data.get("background"):
                recipe_import.add_background(conn, recipe_id, data["background"])
                child_ids["background_knowledge"] = "recorded"

            # 3c. 分类
            if data.get("category"):
                recipe_import.add_category(conn, recipe_id, data["category"])
                child_ids["recipe_categories"] = "recorded"

            # 3d. 5 张标签表
            if data.get("seasons"):
                recipe_import.add_seasons(conn, recipe_id, data["seasons"])
                child_ids["recipe_seasons"] = len(data["seasons"])
            if data.get("cooking_methods"):
                recipe_import.add_cooking_methods(conn, recipe_id, data["cooking_methods"])
                child_ids["recipe_cooking_methods"] = len(data["cooking_methods"])
            if data.get("flavors"):
                recipe_import.add_flavors(conn, recipe_id, data["flavors"])
                child_ids["recipe_flavors"] = len(data["flavors"])
            if data.get("diet_tags"):
                recipe_import.add_diet_tags(conn, recipe_id, data["diet_tags"])
                child_ids["recipe_diet_tags"] = len(data["diet_tags"])
            if data.get("meal_types"):
                recipe_import.add_meal_types(conn, recipe_id, data["meal_types"])
                child_ids["recipe_meal_types"] = len(data["meal_types"])

            # 3e. 食材
            name_id_map = {}
            name_unit_map = {}
            if data.get("ingredients"):
                name_id_map, name_unit_map = recipe_import.add_ingredients(conn, recipe_id, data["ingredients"])
                child_ids["ingredients"] = len(name_id_map)

            # 3f. 步骤
            seq_id_map = {}
            if data.get("steps"):
                seq_id_map = recipe_import.add_steps(conn, recipe_id, data["steps"], name_id_map, name_unit_map)
                child_ids["cooking_steps"] = len(seq_id_map)
                child_ids["step_ingredients"] = sum(
                    1 for s in data["steps"] for si in s.get("ingredients_used", [])
                )

            # 3g. tips(决策 2 · 方案 A+:scope 值格式必填,2026-07-22)
            # validate_tip_minimum 已被 validate_tip_scope 取代:
            # - scope=step 强制 step_id → 等价于"只缺 step_id 警告"
            # - scope=recipe 显式声明 → 等价于"菜级 tip 警告"
            if data.get("tips"):
                for i, tip in enumerate(data["tips"]):
                    scope = tip.get("scope")
                    scope_result = validators.validate_tip_scope(
                        scope,
                        step_id=tip.get("step_id"),
                        ingredient_id=tip.get("ingredient_id"),
                    )
                    if not scope_result["valid"]:
                        raise ValueError(
                            f"tips[{i}]: {scope_result['error']}\n"
                            f"   合法 scope 值:step / ingredient / recipe\n"
                            f"   - scope=step 需 step_id\n"
                            f"   - scope=ingredient 需 ingredient_id\n"
                            f"   - scope=recipe 整道菜级,两个 ID 都可空"
                        )
                recipe_import.add_tips(conn, recipe_id, data["tips"], seq_id_map)
                child_ids["tips"] = len(data["tips"])

            # 3h. 技法
            if data.get("techniques"):
                recipe_import.add_techniques(conn, recipe_id, data["techniques"], seq_id_map)
                child_ids["techniques"] = len(data["techniques"])

            # 3i. 炊具
            if data.get("cookware"):
                recipe_import.add_cookware(conn, recipe_id, data["cookware"])
                child_ids["cookware"] = len(data["cookware"])

            # 3j. history(自动 cook_sequence)
            if data.get("history"):
                count = recipe_import.add_history(conn, recipe_id, data["history"])
                child_ids["recipe_history"] = count

            # 3k. relations(派生关系)
            if data.get("relations"):
                count = recipe_import.add_relations(conn, recipe_id, data["relations"], data["name"])
                child_ids["recipe_relations"] = count

            # 自动 commit(transaction context manager)

    except Exception as e:
        return {
            "status": "error",
            "stage": "write",
            "data": {"recipe_id": recipe_id} if recipe_id else {},
            "message": f"写入失败: {str(e)}",
            "errors": [{"type": "exception", "message": str(e)}]
        }

    return {
        "status": "success",
        "data": {
            "recipe_id": recipe_id,
            "name": data["name"],
            "child_ids": child_ids
        },
        "message": f"成功导入食谱「{data['name']}」(ID: {recipe_id[:8]}...)",
        "tips_warnings": tip_warnings if tip_warnings else None
    }


# ====================================================================
# 加载 JSON + 调编排
# ====================================================================

def orchestrate_from_file(json_file: str, dry_run: bool = False) -> dict:
    """从 JSON 文件加载 + 调 orchestrate_import。"""
    # 1. 加载 JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return error(f"JSON 格式错误: {str(e)}")
    except FileNotFoundError:
        return error(f"文件不存在: {json_file}")

    return orchestrate_import(data, dry_run=dry_run)


# ====================================================================
# CLI 入口(L3 加 --json 标志)
# ====================================================================

def main():
    if len(sys.argv) < 2:
        emit(error(
            "用法: python import_orchestrator.py <json_file> [--dry-run] [--json]"
        ))
        return

    args = sys.argv[1:]
    json_mode = parse_json_flag(args)
    args = [a for a in args if a != "--json"]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    if not args:
        emit(error("请提供 JSON 文件路径"))
        return

    result = orchestrate_from_file(args[0], dry_run=dry_run)
    emit(result, json_mode=json_mode)
    sys.exit(0 if result["status"] in ("success", "dry_run") else 1)


if __name__ == "__main__":
    main()