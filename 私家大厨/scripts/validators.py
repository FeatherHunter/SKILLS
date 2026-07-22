#!/usr/bin/env python3
"""
私家大厨 - 业务层校验器(硬规则 · v5.1 升级)

按 5 层架构,业务层硬规则集中在本文件,无跳过通道。

v5.1 升级(2026-07-21):
- 枚举强校验:从 references/enums.py 读合法值,不再硬编码
- 新增 validate_step_structure():校验每个 step 必填子字段
- 新增 validate_step_ingredient_inventory():校验 step.ingredients_used 引用的食材都在 ingredients 里
- 现有 validate_value_types() 改用 enums

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

import sys
import os
import json
from typing import Any, Dict, List

# 让 references 目录可 import
_SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _SKILL_ROOT)
sys.path.insert(0, os.path.join(_SKILL_ROOT, "references"))

import enums  # references/enums.py(5 层架构:业务层读 references)

# v5.2:11 类食材分类 + 别名映射
INGREDIENT_CATEGORIES = enums.INGREDIENT_CATEGORIES
INGREDIENT_CATEGORY_ALIASES = enums.ALIASES.get("ingredient_categories", {})


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

# 数组字段名 → 对应 enums 枚举名(用于强校验)
ARRAY_FIELD_TO_ENUM = {
    "seasons": "seasons",
    "cooking_methods": "cooking_methods",
    "flavors": "flavors",
    "diet_tags": "diet_tags",
    "meal_types": "meal_types",
}


# ====================================================================
# 全字段必填校验
# ====================================================================

REQUIRED_TOP_LEVEL_FIELDS: List[str] = list(FIELD_LABELS.keys())


def validate_full_coverage(data: Any) -> List[Dict[str, Any]]:
    """全字段必填校验:检查 JSON 是否包含所有必需字段。"""
    errors: List[Dict[str, Any]] = []

    if not isinstance(data, dict):
        errors.append({
            "type": "type_error",
            "field": "(顶层)",
            "current_value": type(data).__name__,
            "expected": "dict",
            "hint": "JSON 顶层必须是对象 {}"
        })
        return errors

    missing: List[Dict[str, str]] = []
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            missing.append({"field": field, "label": FIELD_LABELS.get(field, field)})

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
# 占位符黑名单(L2 阶段新增)
# ====================================================================

# 字符串占位符(13 个,L2 用户决策)
PLACEHOLDER_STRINGS = {
    "", "未知", "未提供", "不详", "未填",
    "n/a", "N/A", "null", "None",
    "暂时不知道", "不知道", "我没数据", "-"
}

# 数字占位符
PLACEHOLDER_NUMBERS = {-1}

# 数字字段白名单(7 个,允许传 0)
LEGITIMATE_ZERO_FIELDS = {
    "calories", "protein", "fat", "carbs",
    "fiber", "sodium", "serving_size"
}


def validate_no_placeholder(value: Any, field_name: str) -> Dict[str, Any]:
    """检查单字段是否含占位符。

    Args:
        value: 字段值
        field_name: 字段名(用于错误信息,支持 "nutrition.calories" 这种带前缀路径)

    Returns:
        {"valid": True/False, "error": "..." / None}
    """
    # 提取纯字段名(去掉点前缀,白名单按纯字段名匹配)
    pure_name = field_name.rsplit(".", 1)[-1] if "." in field_name else field_name

    # 字符串检查
    if isinstance(value, str):
        if value.strip() in PLACEHOLDER_STRINGS:
            return {
                "valid": False,
                "error": f"字段 {field_name}='{value}' 是占位符,必须填真实数据(占位符黑名单含 13 种)"
            }
        if not value.strip():
            return {
                "valid": False,
                "error": f"字段 {field_name} 是空字符串,必须填值"
            }

    # 数字检查
    if isinstance(value, (int, float)):
        if value in PLACEHOLDER_NUMBERS:
            return {
                "valid": False,
                "error": f"字段 {field_name}={value} 是占位符(-1)"
            }
        # 0 值检查按纯字段名匹配(支持 "nutrition.calories" 这类带前缀的)
        if value == 0 and pure_name not in LEGITIMATE_ZERO_FIELDS:
            return {
                "valid": False,
                "error": f"字段 {field_name}=0 疑似占位符(7 个白名单字段除外:calories/protein/fat/carbs/fiber/sodium/serving_size)"
            }

    return {"valid": True, "error": None}


def validate_full_no_placeholder(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """全字段占位符检查 + 0 值检查。

    应用范围:所有顶层字段 + 子对象字段 + 数组元素字段。
    """
    errors = []
    if not isinstance(data, dict):
        return errors

    # 1. 顶层字符串字段
    string_fields = ["name", "description", "difficulty", "status",
                     "photo_url", "source", "source_url"]
    for field in string_fields:
        if field in data:
            result = validate_no_placeholder(data[field], field)
            if not result["valid"]:
                errors.append({
                    "type": "placeholder",
                    "field": field,
                    **result
                })

    # 2. 数字字段(顶层)
    if "servings" in data:
        result = validate_no_placeholder(data["servings"], "servings")
        if not result["valid"]:
            errors.append({"type": "placeholder", "field": "servings", **result})

    if "total_time_minutes" in data:
        result = validate_no_placeholder(data["total_time_minutes"], "total_time_minutes")
        if not result["valid"]:
            errors.append({"type": "placeholder", "field": "total_time_minutes", **result})

    # 3. nutrition 子对象字段
    if "nutrition" in data and isinstance(data["nutrition"], dict):
        for nf, nv in data["nutrition"].items():
            result = validate_no_placeholder(nv, f"nutrition.{nf}")
            if not result["valid"]:
                errors.append({
                    "type": "placeholder",
                    "field": f"nutrition.{nf}",
                    **result
                })

    # 4. background 子对象字段
    if "background" in data and isinstance(data["background"], dict):
        for bf, bv in data["background"].items():
            result = validate_no_placeholder(bv, f"background.{bf}")
            if not result["valid"]:
                errors.append({
                    "type": "placeholder",
                    "field": f"background.{bf}",
                    **result
                })

    return errors


# ====================================================================
# tips 业务规则校验(L2 阶段新增 · 用户决策 R4)
# ====================================================================

def validate_tip_minimum(tip_data: Dict[str, Any]) -> Dict[str, Any]:
    """tips 表业务校验(CLI 警告版,非强制)。

    用户决策 R4:优先要求 recipe_id + step_id + ingredient_id 都填,迫不得已才允许不全。

    返回:
    {
        "status": "pass" / "warning" / "error",
        "missing": [...],                 # 缺的字段清单
        "warning_msg": "...",             # 警告文案
        "user_question": "..."            # 建议 AI 反问用户
    }
    """
    recipe_id = tip_data.get("recipe_id", "")
    step_id = tip_data.get("step_id", "")
    ingredient_id = tip_data.get("ingredient_id", "")

    # 1. recipe_id 缺则拒(error,非 warning)
    if not recipe_id or (isinstance(recipe_id, str) and not recipe_id.strip()):
        return {
            "status": "error",
            "missing": ["recipe_id"],
            "warning_msg": "recipe_id 必填",
            "user_question": "recipe_id 是必填的,tip 必须挂在某个菜上。"
        }

    # 2. step_id 和 ingredient_id 都缺
    if (not step_id or (isinstance(step_id, str) and not step_id.strip())) \
       and (not ingredient_id or (isinstance(ingredient_id, str) and not ingredient_id.strip())):
        return {
            "status": "warning",
            "missing": ["step_id", "ingredient_id"],
            "warning_msg": "step_id 和 ingredient_id 都缺(疑似菜级 tip)",
            "user_question": (
                "这条 tip 跟具体的步骤或食材都没关系吗?\n"
                "如果是,这是「菜级 tip」,validators 默认允许(传入正常)。\n"
                "如果否,告诉 AI 补一下 step_id 或 ingredient_id。"
            )
        }

    # 3. 只缺一个(警告,不阻断)
    missing = []
    if not step_id or (isinstance(step_id, str) and not step_id.strip()):
        missing.append("step_id")
    if not ingredient_id or (isinstance(ingredient_id, str) and not ingredient_id.strip()):
        missing.append("ingredient_id")

    if missing:
        return {
            "status": "warning",
            "missing": missing,
            "warning_msg": f"缺 {', '.join(missing)}",
            "user_question": (
                f"tip 没填 {', '.join(missing)}。"
                f"如确认这是 ingredient 级(仅 ingredient)或 step 级(仅 step)tip,继续通过;"
                f"否则请 AI 主动询问用户是否要补全。"
            )
        }

    return {"status": "pass", "missing": [], "warning_msg": None, "user_question": None}


# ====================================================================
# 字段值类型校验(枚举强校验)
# ====================================================================

def validate_value_types(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """字段值类型校验 + 枚举强校验(从 enums.py 读合法值)"""
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

    # 2. difficulty 必须是枚举值(从 enums)
    if "difficulty" in data and data["difficulty"] is not None:
        valid = enums.get_valid_values("difficulty")
        if data["difficulty"] not in valid:
            errors.append({
                "type": "value_error",
                "field": "difficulty",
                "current_value": data["difficulty"],
                "expected": f"枚举值之一: {', '.join(valid)}",
                "hint": f"difficulty 必须是以下之一: {', '.join(valid)}"
            })

    # 3. status 必须是枚举值
    if "status" in data and data["status"] is not None:
        valid = enums.get_valid_values("status")
        if data["status"] not in valid:
            errors.append({
                "type": "value_error",
                "field": "status",
                "current_value": data["status"],
                "expected": f"枚举值之一: {', '.join(valid)}",
                "hint": f"status 必须是以下之一: {', '.join(valid)}"
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

    # 7. 枚举强校验(从 enums 读合法值,5 张标签表)
    for field, enum_name in ARRAY_FIELD_TO_ENUM.items():
        if field in data and isinstance(data[field], list):
            valid_values = enums.get_valid_values(enum_name)
            invalid_items = []
            for i, item in enumerate(data[field]):
                if not isinstance(item, str):
                    continue  # 类型错已在上面捕获
                if not enums.is_valid_value(enum_name, item):
                    # 提示用户用归一化值
                    try:
                        normalized = enums.normalize_value(enum_name, item)
                        invalid_items.append({
                            "index": i,
                            "value": item,
                            "normalized": normalized,
                        })
                    except ValueError:
                        # 完全不合法
                        invalid_items.append({
                            "index": i,
                            "value": item,
                            "normalized": None,
                        })
            if invalid_items:
                # 区分"有别名"和"完全不合法"两种
                for item in invalid_items:
                    if item["normalized"]:
                        # 有别名,建议归一化
                        errors.append({
                            "type": "value_error",
                            "field": f"{field}[{item['index']}]",
                            "current_value": item["value"],
                            "expected": f"枚举值或别名(可归一为 '{item['normalized']}')",
                            "hint": f"'{item['value']}' 不是标准值,建议改为 '{item['normalized']}'。合法值: {', '.join(valid_values)}"
                        })
                    else:
                        # 完全不合法
                        errors.append({
                            "type": "value_error",
                            "field": f"{field}[{item['index']}]",
                            "current_value": item["value"],
                            "expected": f"枚举值之一: {', '.join(valid_values)}",
                            "hint": f"'{item['value']}' 不是合法值。合法值: {', '.join(valid_values)}"
                        })

    # 8. category 必须是 dict(可以为空 {})
    if "category" in data and data["category"] is not None:
        if not isinstance(data["category"], dict):
            errors.append({
                "type": "value_error",
                "field": "category",
                "current_value": type(data["category"]).__name__,
                "expected": "object (dict) 或 null",
                "hint": "category 必须是对象 {} 或 null"
            })

    # 9. 嵌套对象字段
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

    # 10. cookware 内部 category 枚举校验
    if "cookware" in data and isinstance(data["cookware"], list):
        valid_categories = enums.get_valid_values("cookware_categories")
        for i, cw in enumerate(data["cookware"]):
            if isinstance(cw, dict) and cw.get("category") is not None:
                if cw["category"] not in valid_categories:
                    errors.append({
                        "type": "value_error",
                        "field": f"cookware[{i}].category",
                        "current_value": cw["category"],
                        "expected": f"枚举值之一: {', '.join(valid_categories)}",
                        "hint": f"炊具分类必须是: {', '.join(valid_categories)}"
                    })

    # 11. ingredients 内部:每个元素必须有 name
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

    return errors


# ====================================================================
# 步骤结构校验(新增 v5.1)
# ====================================================================

REQUIRED_STEP_FIELDS = ["sequence", "action"]
RECOMMENDED_STEP_FIELDS = ["duration", "heat_level", "temperature", "expected_result", "ingredients_used"]


def validate_step_structure(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    校验每个 step 的子结构:
    - 必填:sequence(整数), action(非空字符串)
    - 推荐填:duration(数字), heat_level(字符串), temperature(字符串),
              expected_result(字符串), ingredients_used(数组)
    - 任一缺失 → 警告(不阻断),用"推荐填但缺失"提示
    """
    errors: List[Dict[str, Any]] = []

    if "steps" not in data or not isinstance(data["steps"], list):
        return errors  # 类型错已在 validate_value_types 捕获

    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            continue  # 类型错已在上面捕获

        # 必填字段
        for req in REQUIRED_STEP_FIELDS:
            if req not in step or step.get(req) is None:
                errors.append({
                    "type": "missing_field",
                    "field": f"steps[{i}].{req}",
                    "current_value": "(缺失)",
                    "expected": "必填" if req == "sequence" or req == "action" else "推荐填",
                    "hint": f"步骤 {i+1} 缺少 {req} 字段"
                })
            else:
                # 类型校验
                if req == "sequence" and not isinstance(step["sequence"], int):
                    errors.append({
                        "type": "value_error",
                        "field": f"steps[{i}].sequence",
                        "current_value": step["sequence"],
                        "expected": "整数",
                        "hint": f"步骤 {i+1} 的 sequence 必须是整数"
                    })
                if req == "action" and (not isinstance(step["action"], str) or not step["action"].strip()):
                    errors.append({
                        "type": "value_error",
                        "field": f"steps[{i}].action",
                        "current_value": step["action"],
                        "expected": "非空字符串",
                        "hint": f"步骤 {i+1} 的 action 必须是描述性字符串"
                    })

        # 推荐字段(duration 类型校验)
        if "duration" in step and step["duration"] is not None:
            if not isinstance(step["duration"], (int, float)) or step["duration"] < 0:
                errors.append({
                    "type": "value_error",
                    "field": f"steps[{i}].duration",
                    "current_value": step["duration"],
                    "expected": "非负数",
                    "hint": f"步骤 {i+1} 的 duration 必须是非负数(单位:分钟)"
                })

        # ingredients_used 必须是数组(若提供)
        if "ingredients_used" in step and step["ingredients_used"] is not None:
            if not isinstance(step["ingredients_used"], list):
                errors.append({
                    "type": "value_error",
                    "field": f"steps[{i}].ingredients_used",
                    "current_value": type(step["ingredients_used"]).__name__,
                    "expected": "array (list) 或 null",
                    "hint": f"步骤 {i+1} 的 ingredients_used 必须是数组"
                })
            else:
                for j, si in enumerate(step["ingredients_used"]):
                    if not isinstance(si, dict):
                        continue
                    if "name" not in si or not si.get("name"):
                        errors.append({
                            "type": "missing_field",
                            "field": f"steps[{i}].ingredients_used[{j}].name",
                            "current_value": "(缺失)",
                            "expected": "非空字符串",
                            "hint": f"步骤 {i+1} 的 ingredients_used 第 {j+1} 项必须包含 name"
                        })
                    # introduced_at 枚举校验
                    if "introduced_at" in si and si["introduced_at"] is not None:
                        if not enums.is_valid_value("introduced_at", si["introduced_at"]):
                            try:
                                normalized = enums.normalize_value("introduced_at", si["introduced_at"])
                                errors.append({
                                    "type": "value_error",
                                    "field": f"steps[{i}].ingredients_used[{j}].introduced_at",
                                    "current_value": si["introduced_at"],
                                    "expected": f"枚举值或别名(可归一为 '{normalized}')",
                                    "hint": f"建议改为 '{normalized}'。合法值: {', '.join(enums.get_valid_values('introduced_at'))}"
                                })
                            except ValueError:
                                errors.append({
                                    "type": "value_error",
                                    "field": f"steps[{i}].ingredients_used[{j}].introduced_at",
                                    "current_value": si["introduced_at"],
                                    "expected": f"枚举值: {', '.join(enums.get_valid_values('introduced_at'))}",
                                    "hint": f"introduced_at 必须是合法值"
                                })

    return errors


# ====================================================================
# 步骤食材引用校验(新增 v5.1)
# ====================================================================

def validate_step_ingredient_inventory(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    校验 step.ingredients_used 引用的食材 name 都在 ingredients 里。
    避免"步骤里用了没定义的食材"。
    """
    errors: List[Dict[str, Any]] = []

    if "ingredients" not in data or not isinstance(data["ingredients"], list):
        return errors
    if "steps" not in data or not isinstance(data["steps"], list):
        return errors

    # 食材 name 集合
    defined_names = {ing.get("name") for ing in data["ingredients"] if isinstance(ing, dict) and ing.get("name")}

    for i, step in enumerate(data["steps"]):
        if not isinstance(step, dict):
            continue
        ingredients_used = step.get("ingredients_used")
        if not isinstance(ingredients_used, list):
            continue
        for j, si in enumerate(ingredients_used):
            if not isinstance(si, dict):
                continue
            ref_name = si.get("name")
            if ref_name and ref_name not in defined_names:
                errors.append({
                    "type": "value_error",
                    "field": f"steps[{i}].ingredients_used[{j}].name",
                    "current_value": ref_name,
                    "expected": f"必须在 ingredients 数组中定义。已有食材: {', '.join(sorted(defined_names))}",
                    "hint": f"步骤 {i+1} 引用了食材 '{ref_name}',但 ingredients 里没定义。请把 '{ref_name}' 加到 ingredients,或改正步骤里的引用"
                })

    return errors


# ====================================================================
# 食材分类校验(v5.2 新增 · 11 类强校验)
# ====================================================================

def validate_ingredient_categories(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    校验所有 ingredients[].category 必须是 11 类之一。

    v5.2 起引入 11 类系统(原 9 类拆出"葱姜蒜"和"香草")。
    录入时 category 必须严格匹配,否则报错。

    Returns:
        错误列表,每个错误包含 field / current / expected / how_to_fix
    """
    errors = []
    ingredients = data.get("ingredients", [])
    if not isinstance(ingredients, list):
        return errors

    valid_categories = set(INGREDIENT_CATEGORIES)
    invalid_items = []
    for i, ing in enumerate(ingredients):
        if not isinstance(ing, dict):
            continue
        cat = ing.get("category")
        if cat is None:
            invalid_items.append((i, ing.get("name", "?"), None))
        elif cat not in valid_categories:
            invalid_items.append((i, ing.get("name", "?"), cat))

    for idx, name, cat in invalid_items:
        # 给推荐:基于食材名粗略推荐
        suggested = None
        for keyword, target in INGREDIENT_CATEGORY_ALIASES.items():
            if keyword in name:
                suggested = target
                break
        errors.append({
            "field": f"ingredients[{idx}].category",
            "ingredient_name": name,
            "current": cat,
            "expected": sorted(valid_categories),
            "suggested": suggested,
            "how_to_fix": (
                f"食材「{name}」的 category '{cat}' 不是 11 类标准值。"
                f"{' 推荐: ' + suggested if suggested else ''} "
                f"查看 references/categories.md 边界规则。"
            ),
        })
    return errors


# ====================================================================
# 用户问题生成
# ====================================================================

def build_user_question(missing_field_names: List[str]) -> str:
    """生成"一次性问用户"的问题:把多个缺失字段打包成一个综合问题。"""
    if not missing_field_names:
        return ""

    labels = [FIELD_LABELS.get(f, f) for f in missing_field_names]
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
    """校验导入用的食谱 JSON,返回 {valid, errors, suggested_user_question, warnings, warnings_for_ai}。"""
    # 1. 全字段必填校验
    coverage_errors = validate_full_coverage(data)
    # 2. 值类型 + 枚举强校验
    type_errors = validate_value_types(data) if isinstance(data, dict) else []
    # 3. 步骤子结构校验(v5.1 新增)
    step_errors = validate_step_structure(data) if isinstance(data, dict) else []
    # 4. 步骤食材引用校验(v5.1 新增)
    inventory_errors = validate_step_ingredient_inventory(data) if isinstance(data, dict) else []
    # 5. 食材分类 11 类强校验(v5.2 新增)
    category_errors = validate_ingredient_categories(data) if isinstance(data, dict) else []
    # 6. 占位符黑名单 + 0 值白名单(L2 新增)
    placeholder_errors = validate_full_no_placeholder(data) if isinstance(data, dict) else []

    all_errors = coverage_errors + type_errors + step_errors + inventory_errors + category_errors + placeholder_errors

    # 7. tips 业务规则(警告版,L2 新增)—— 不阻断,只警告
    tips_warnings = []
    if isinstance(data, dict) and isinstance(data.get("tips"), list):
        for i, tip in enumerate(data["tips"]):
            if not isinstance(tip, dict):
                continue
            tip_result = validate_tip_minimum(tip)
            if tip_result["status"] in ("warning", "error"):
                tips_warnings.append({
                    "index": i,
                    "status": tip_result["status"],
                    "missing": tip_result["missing"],
                    "warning_msg": tip_result["warning_msg"],
                    "user_question": tip_result["user_question"]
                })

    if not all_errors:
        return {
            "valid": True,
            "errors": [],
            "suggested_user_question": None,
            "tips_warnings": tips_warnings or None  # None = 没警告
        }

    # 5. 收集所有缺失字段名(给 suggested_user_question 用)
    missing_names: List[str] = []
    for err in all_errors:
        if err.get("type") == "missing_fields":
            missing_names.extend(err.get("field_names", []))
        elif err.get("type") == "missing_field":
            missing_names.append(err.get("field", "(未知)"))

    suggested_question = build_user_question(missing_names) if missing_names else None

    return {
        "valid": False,
        "errors": all_errors,
        "suggested_user_question": suggested_question,
        "tips_warnings": tips_warnings or None
    }


# ====================================================================
# CLI 入口(独立可调用)
# ====================================================================

def main():
    """CLI:从 stdin 读 JSON,跑校验,输出结果。"""
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
