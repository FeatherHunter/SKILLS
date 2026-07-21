#!/usr/bin/env python3
"""
私家大厨 - 业务层校验器(硬规则)

按 5 层架构,业务层硬规则集中在本文件,无跳过通道。

设计原则(来自《优秀 Skill 指导手册》):
- 早失败优于晚失败:在校验阶段就拒,不要等 SQL 报错
- 失败信息要具体:含字段名 + 当前值 + 期望值 + 怎么修
- 无 --force / --skip-validation 通道
- 错误要可恢复:报错信息告诉 AI 怎么改

使用方式:
    from validators import validate_recipe_for_import
    result = validate_recipe_for_import(data)
    if not result["valid"]:
        print(result)  # AI 拿到这个 JSON 后必须用 suggested_user_question 问用户
"""

import json
from typing import Any, Dict, List


# ====================================================================
# 字段中文标签(用于错误信息)
# ====================================================================

FIELD_LABELS: Dict[str, str] = {
    # recipes 主表
    "name": "菜名",
    "description": "菜描述",
    "difficulty": "难度",
    "servings": "份量(人份)",
    "total_time": "总时间(分钟)",
    "status": "状态",
    "photo_url": "照片URL",
    "source": "来源",
    "source_url": "来源链接",
    # category 子对象
    "category": "分类(cuisine/region/country)",
    # 5 张标签表
    "seasons": "适合季节",
    "cooking_methods": "烹饪方式",
    "flavors": "口味",
    "diet_tags": "饮食标签",
    "meal_types": "用餐类型",
    # 食材 / 步骤
    "ingredients": "食材清单",
    "steps": "烹饪步骤",
    # 可选数据
    "tips": "烹饪贴士",
    "techniques": "技法",
    "cookware": "炊具",
    "nutrition": "营养信息",
    "background": "背景知识",
    "history": "烹饪历史",
    "relations": "派生关系",
}


# ====================================================================
# 全字段必填校验(核心)
# ====================================================================

# 顶层必填字段(必须是字典里有这个 key,值可以是真实数据或 null)
REQUIRED_TOP_LEVEL_FIELDS: List[str] = list(FIELD_LABELS.keys())


def validate_full_coverage(data: Any) -> List[Dict[str, Any]]:
    """
    全字段必填校验:检查 JSON 是否包含所有必需字段。

    规则:
    - 字段必须存在(可以是真实值,也可以是 null)
    - 字段完全缺失 → 收集到 errors 列表
    - 一次性收集所有缺失字段,不是遇到第一个就停

    Returns:
        list of error dicts (空列表 = 通过校验)
    """
    errors: List[Dict[str, Any]] = []

    # 0. 顶层必须是 dict
    if not isinstance(data, dict):
        errors.append({
            "type": "type_error",
            "field": "(顶层)",
            "current_value": type(data).__name__,
            "expected": "dict",
            "hint": "JSON 顶层必须是对象 {}"
        })
        return errors

    # 1. 收集所有缺失的顶层字段
    missing: List[Dict[str, str]] = []
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            missing.append({
                "field": field,
                "label": FIELD_LABELS.get(field, field)
            })

    if missing:
        errors.append({
            "type": "missing_fields",
            "count": len(missing),
            "fields": [f"{m['field']} ({m['label']})" for m in missing],
            "field_names": [m["field"] for m in missing],
            "hint": "JSON 必须包含所有字段,值可以是真实数据或 null,但字段本身不能缺失"
        })

    return errors


# ====================================================================
# 字段值类型校验
# ====================================================================

VALID_DIFFICULTY = ["快手菜", "简单", "中等", "困难", "大师"]
VALID_STATUS = ["未做", "已做", "熟练"]


def validate_value_types(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    字段值类型校验:检查字段值是否符合期望类型和枚举。

    只校验"有值"的情况,null 视为合法(用户主动标记无数据)。
    """
    errors: List[Dict[str, Any]] = []

    # 1. name 必须是非空字符串
    if "name" in data and data["name"] is not None:
        if not isinstance(data["name"], str) or not data["name"].strip():
            errors.append({
                "type": "value_error",
                "field": "name",
                "current_value": data["name"],
                "expected": "非空字符串",
                "hint": "菜名不能为空字符串"
            })

    # 2. difficulty 必须是枚举值
    if "difficulty" in data and data["difficulty"] is not None:
        if data["difficulty"] not in VALID_DIFFICULTY:
            errors.append({
                "type": "value_error",
                "field": "difficulty",
                "current_value": data["difficulty"],
                "expected": f"枚举值之一: {', '.join(VALID_DIFFICULTY)}",
                "hint": f"difficulty 必须是以下之一: {', '.join(VALID_DIFFICULTY)}"
            })

    # 3. status 必须是枚举值
    if "status" in data and data["status"] is not None:
        if data["status"] not in VALID_STATUS:
            errors.append({
                "type": "value_error",
                "field": "status",
                "current_value": data["status"],
                "expected": f"枚举值之一: {', '.join(VALID_STATUS)}",
                "hint": f"status 必须是以下之一: {', '.join(VALID_STATUS)}"
            })

    # 4. servings 必须是正整数
    if "servings" in data and data["servings"] is not None:
        if not isinstance(data["servings"], int) or data["servings"] <= 0:
            errors.append({
                "type": "value_error",
                "field": "servings",
                "current_value": data["servings"],
                "expected": "正整数",
                "hint": "份量必须是大于 0 的整数(如 2 表示 2 人份)"
            })

    # 5. total_time 必须是正数
    if "total_time" in data and data["total_time"] is not None:
        if not isinstance(data["total_time"], (int, float)) or data["total_time"] <= 0:
            errors.append({
                "type": "value_error",
                "field": "total_time",
                "current_value": data["total_time"],
                "expected": "正数(int 或 float)",
                "hint": "总时间必须是大于 0 的数字(单位:分钟)"
            })

    # 6. 数组字段必须是数组(不能是 null 之外的类型)
    array_fields = ["seasons", "cooking_methods", "flavors", "diet_tags",
                    "meal_types", "ingredients", "steps", "tips", "techniques",
                    "cookware", "history", "relations"]
    for field in array_fields:
        if field in data and data[field] is not None:
            if not isinstance(data[field], list):
                errors.append({
                    "type": "value_error",
                    "field": field,
                    "current_value": type(data[field]).__name__,
                    "expected": "array (list) 或 null",
                    "hint": f"{FIELD_LABELS.get(field, field)} 必须是数组 [] 或 null"
                })

    # 7. category 必须是 dict(可以为空 {})
    if "category" in data and data["category"] is not None:
        if not isinstance(data["category"], dict):
            errors.append({
                "type": "value_error",
                "field": "category",
                "current_value": type(data["category"]).__name__,
                "expected": "object (dict) 或 null",
                "hint": "category 必须是对象 {} 或 null"
            })

    # 8. 嵌套对象字段: nutrition / background
    for field in ["nutrition", "background"]:
        if field in data and data[field] is not None:
            if not isinstance(data[field], dict):
                errors.append({
                    "type": "value_error",
                    "field": field,
                    "current_value": type(data[field]).__name__,
                    "expected": "object (dict) 或 null",
                    "hint": f"{FIELD_LABELS.get(field, field)} 必须是对象 {{}} 或 null"
                })

    # 9. ingredients 内部: 每个元素必须有 name
    if "ingredients" in data and isinstance(data["ingredients"], list):
        for i, ing in enumerate(data["ingredients"]):
            if not isinstance(ing, dict):
                errors.append({
                    "type": "value_error",
                    "field": f"ingredients[{i}]",
                    "current_value": type(ing).__name__,
                    "expected": "object (dict)",
                    "hint": f"食材清单第 {i+1} 项必须是对象"
                })
                continue
            if "name" not in ing or not ing.get("name"):
                errors.append({
                    "type": "missing_field",
                    "field": f"ingredients[{i}].name",
                    "current_value": "(缺失)",
                    "expected": "非空字符串",
                    "hint": f"食材清单第 {i+1} 项必须包含 name 字段"
                })

    # 10. steps 内部: 每个元素必须有 action
    if "steps" in data and isinstance(data["steps"], list):
        for i, step in enumerate(data["steps"]):
            if not isinstance(step, dict):
                errors.append({
                    "type": "value_error",
                    "field": f"steps[{i}]",
                    "current_value": type(step).__name__,
                    "expected": "object (dict)",
                    "hint": f"烹饪步骤第 {i+1} 项必须是对象"
                })
                continue
            if "action" not in step or not step.get("action"):
                errors.append({
                    "type": "missing_field",
                    "field": f"steps[{i}].action",
                    "current_value": "(缺失)",
                    "expected": "非空字符串",
                    "hint": f"烹饪步骤第 {i+1} 项必须包含 action 字段(步骤描述)"
                })

    return errors


# ====================================================================
# 用户问题生成
# ====================================================================

def build_user_question(missing_field_names: List[str]) -> str:
    """
    生成"一次性问用户"的问题:把多个缺失字段打包成一个综合问题。

    Args:
        missing_field_names: 缺失字段名列表(如 ["description", "tips"])

    Returns:
        自然语言问题,引导用户一次性补全
    """
    if not missing_field_names:
        return ""

    # 字段名 → 中文标签
    labels = [FIELD_LABELS.get(f, f) for f in missing_field_names]

    # 编号 ①②③...
    bullets = "①②③④⑤⑥⑦⑧⑨⑩"
    numbered = " ".join(
        f"{bullets[i]} {label}" for i, label in enumerate(labels)
        if i < len(bullets)
    )

    return (
        f"你手写本上没写:{numbered}。"
        f"能现场补一下吗?实在没有,我也用 null 标。"
    )


# ====================================================================
# 主入口:组合所有校验
# ====================================================================

def validate_recipe_for_import(data: Any) -> Dict[str, Any]:
    """
    校验导入用的食谱 JSON,返回 {valid, errors, suggested_user_question}。

    AI 收到这个返回后:
    1. valid=True → 可以调用 recipe_import.py import
    2. valid=False → 用 suggested_user_question 一次性问用户,补全后重跑

    Returns:
        {
            "valid": bool,
            "errors": [...],
            "suggested_user_question": "..." | None
        }
    """
    # 1. 全字段必填校验
    coverage_errors = validate_full_coverage(data)
    # 2. 值类型校验(只在 data 是 dict 时跑)
    type_errors = validate_value_types(data) if isinstance(data, dict) else []

    all_errors = coverage_errors + type_errors

    if not all_errors:
        return {
            "valid": True,
            "errors": [],
            "suggested_user_question": None
        }

    # 3. 收集所有缺失字段名(给 suggested_user_question 用)
    missing_names: List[str] = []
    for err in all_errors:
        if err.get("type") == "missing_fields":
            missing_names.extend(err.get("field_names", []))
        elif err.get("type") == "missing_field":
            # 嵌套缺失(如 ingredients[0].name)
            missing_names.append(err.get("field", "(未知)"))

    suggested_question = build_user_question(missing_names) if missing_names else None

    return {
        "valid": False,
        "errors": all_errors,
        "suggested_user_question": suggested_question
    }


# ====================================================================
# CLI 入口(独立可调用)
# ====================================================================

def main():
    """CLI:从 stdin 读 JSON,跑校验,输出结果。"""
    import sys
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "valid": False,
            "errors": [{"type": "json_error", "message": str(e)}],
            "suggested_user_question": None
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    result = validate_recipe_for_import(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
