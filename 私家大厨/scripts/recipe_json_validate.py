#!/usr/bin/env python3
"""
私家大厨 - JSON食谱校验脚本
校验JSON文件是否完整、格式正确，用于导入前的质量检查

用法：
    python recipe_json_validate.py <json_file>

校验内容：
    1. 字段完整性：所有字段是否都存在（值可以为null/空数组）
    2. 必填字段：name/ingredients[].name/steps[].action 不能为空
    3. 数据类型：数值字段是否为数字、数组字段是否为数组
    4. 外键引用：步骤引用的食材是否在ingredients中存在
    5. 枚举警告：非标准值给出警告（不阻断）

输出：
    ❌ 错误（必须修正）
    ⚠️ 警告（建议修正）
    ✅ 校验通过
"""

import sys
import os
import json
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# ── jsonschema 路径格式化 ──
SCRIPT_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = SCRIPT_DIR.parent / "templates" / "recipe_schema.json"
_SCHEMA_CACHE = None

def _load_schema():
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


def _format_path(absolute_path):
    """把 jsonschema 错误路径转成 jq 风格(.ingredients[0].name)"""
    parts = []
    for p in absolute_path:
        if isinstance(p, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{p}]"
            else:
                parts.append(f"[{p}]")
        else:
            parts.append(f".{p}" if parts else p)
    return "".join(parts) or "(root)"


def validate_with_jsonschema(data):
    """用 jsonschema 做结构 + 枚举 + 类型校验。
    返回 (errors, warnings) 元组,errors 是致命,warnings 是非致命(实际 jsonschema 没 warnings,所以总是空)。"""
    if not HAS_JSONSCHEMA:
        return (["⚠️ jsonschema 未安装,跳过 schema 校验(只跑了手动校验)"], [])

    try:
        schema = _load_schema()
    except FileNotFoundError:
        return ([f"❌ Schema 文件不存在:{SCHEMA_PATH}"], [])

    validator = Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        path = _format_path(err.absolute_path)
        msg = err.message[:200]  # 截断过长消息
        errors.append(f"❌ {path}  {msg}")
    return (errors, [])

# ══════════════════════════════════════════════════════════════
# 标准枚举值
# ══════════════════════════════════════════════════════════════

ENUMS = {
    "difficulty": ["快手菜", "简单", "中等", "困难", "大师"],
    "status": ["未做", "已做", "熟练", "已废弃"],
    "season": ["春", "夏", "秋", "冬"],
    "cooking_method": ["炒", "蒸", "煮", "烤", "炸", "煎", "焖", "炖", "拌", "卤", "熏", "生食"],
    "flavor": ["酸", "甜", "辣", "咸", "鲜", "苦", "麻"],
    "diet_tag": ["素食", "清真", "无辣", "低碳", "无糖", "低脂", "无麸质", "高蛋白"],
    "meal_type": ["早", "中", "晚", "夜宵", "下午茶", "聚会"],
    "ingredient_category": ["肉类", "海鲜", "蔬菜", "调料", "豆制品", "蛋类", "主食", "干货", "其他"],
    "cookware_category": ["锅", "炉", "刀", "其他"],
    "tip_category": ["火候", "刀工", "调味", "采购", "设备", "保存", "文化"],
    "heat_level": ["微火", "小火", "中火", "大火", "猛火"],
    "introduced_at": ["开局", "开局加入", "中途加入", "最后加入"],
    "cuisine_type": ["川菜", "粤菜", "湘菜", "闽菜", "浙菜", "苏菜", "鲁菜", "东北菜", "京菜", "沪菜", "台湾菜", "本帮菜"],
    "relation_type": ["派生", "变体", "改良"],
}

# ══════════════════════════════════════════════════════════════
# 完整字段定义
# ══════════════════════════════════════════════════════════════

# 顶层字段
TOP_LEVEL_FIELDS = {
    "name": {"type": "str", "required": True},
    "description": {"type": "str", "required": False},
    "difficulty": {"type": "str", "required": False},
    "servings": {"type": "int", "required": False},
    "total_time": {"type": "number", "required": False},
    "status": {"type": "str", "required": False},
    "photo_url": {"type": "str", "required": False},
    "source": {"type": "str", "required": False},
    "source_url": {"type": "str", "required": False},
    "category": {"type": "object", "required": False},
    "seasons": {"type": "array", "required": False},
    "cooking_methods": {"type": "array", "required": False},
    "flavors": {"type": "array", "required": False},
    "diet_tags": {"type": "array", "required": False},
    "meal_types": {"type": "array", "required": False},
    "ingredients": {"type": "array", "required": True},
    "steps": {"type": "array", "required": True},
    "tips": {"type": "array", "required": False},
    "techniques": {"type": "array", "required": False},
    "cookware": {"type": "array", "required": False},
    "nutrition": {"type": "object", "required": False},
    "background": {"type": "object", "required": False},
    "history": {"type": "array", "required": False},
    "relations": {"type": "array", "required": False},
}

# category 子字段
CATEGORY_FIELDS = {
    "cuisine": {"type": "str"},
    "region": {"type": "str"},
    "country": {"type": "str"},
}

# ingredient 子字段
INGREDIENT_FIELDS = {
    "name": {"type": "str", "required": True},
    "quantity": {"type": "number", "required": False},
    "unit": {"type": "str", "required": False},
    "category": {"type": "str", "required": False},
    "sequence": {"type": "int", "required": False},
    "is_optional": {"type": "bool", "required": False},
    "substitute": {"type": "str", "required": False},
    "quantity_text": {"type": "str", "required": False},
}

# step 子字段
STEP_FIELDS = {
    "sequence": {"type": "int", "required": False},
    "action": {"type": "str", "required": True},
    "duration": {"type": "number", "required": False},
    "heat_level": {"type": "str", "required": False},
    "temperature": {"type": "str", "required": False},
    "expected_result": {"type": "str", "required": False},
    "ingredients_used": {"type": "array", "required": False},
}

# step.ingredients_used 子字段
STEP_INGREDIENT_FIELDS = {
    "name": {"type": "str", "required": True},
    "quantity_used": {"type": "number", "required": False},
    "introduced_at": {"type": "str", "required": False},
}

# tip 子字段
TIP_FIELDS = {
    "step_sequence": {"type": "int", "required": False},
    "content": {"type": "str", "required": True},
    "category": {"type": "str", "required": False},
    "priority": {"type": "int", "required": False},
    "ingredient_id": {"type": "str", "required": False},
}

# technique 子字段
TECHNIQUE_FIELDS = {
    "step_sequence": {"type": "int", "required": False},
    "technique_name": {"type": "str", "required": True},
    "description": {"type": "str", "required": False},
    "key_points": {"type": "str", "required": False},
}

# cookware 子字段
COOKWARE_FIELDS = {
    "name": {"type": "str", "required": True},
    "category": {"type": "str", "required": False},
}

# nutrition 子字段
NUTRITION_FIELDS = {
    "serving_size": {"type": "number", "required": False},
    "serving_unit": {"type": "str", "required": False},
    "calories": {"type": "number", "required": False},
    "protein": {"type": "number", "required": False},
    "fat": {"type": "number", "required": False},
    "carbs": {"type": "number", "required": False},
    "fiber": {"type": "number", "required": False},
    "sodium": {"type": "number", "required": False},
}

# background 子字段
BACKGROUND_FIELDS = {
    "origin_story": {"type": "str", "required": False},
    "historical_background": {"type": "str", "required": False},
    "cultural_significance": {"type": "str", "required": False},
}

# history 子字段
HISTORY_FIELDS = {
    "cook_date": {"type": "str", "required": True},
    "cook_sequence": {"type": "int", "required": False},
    "rating": {"type": "number", "required": False},
    "feedback": {"type": "str", "required": False},
}

# relation 子字段
RELATION_FIELDS = {
    "target_recipe_name": {"type": "str", "required": True},
    "relation_type": {"type": "str", "required": False},
    "change_summary": {"type": "str", "required": False},
}


def check_type(value, expected_type, path, errors):
    """检查数据类型，返回是否通过"""
    if value is None:
        return True  # null 跳过类型检查

    if expected_type == "str":
        if not isinstance(value, str):
            errors.append(f"❌ {path} 应为字符串，实际为 {type(value).__name__}")
            return False
    elif expected_type == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"❌ {path} 应为整数，实际为 {type(value).__name__}")
            return False
    elif expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"❌ {path} 应为数字，实际为 {type(value).__name__}")
            return False
    elif expected_type == "bool":
        if not isinstance(value, bool):
            errors.append(f"❌ {path} 应为布尔值，实际为 {type(value).__name__}")
            return False
    elif expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"❌ {path} 应为数组，实际为 {type(value).__name__}")
            return False
    elif expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"❌ {path} 应为对象，实际为 {type(value).__name__}")
            return False
    return True


def check_enum(value, enum_key, path, warnings):
    """检查枚举值，不在标准值中则警告"""
    if value is None:
        return
    if enum_key in ENUMS:
        valid = ENUMS[enum_key]
        if isinstance(value, list):
            for i, v in enumerate(value):
                if isinstance(v, str) and v not in valid:
                    warnings.append(f"⚠️ {path}[{i}] \"{v}\" 不在标准值 {valid} 中")
        elif isinstance(value, str) and value not in valid:
            warnings.append(f"⚠️ {path} \"{value}\" 不在标准值 {valid} 中")


def check_fields(data, field_defs, path_prefix, errors, warnings, missing_fields):
    """通用字段检查：完整性 + 必填 + 类型"""
    if not isinstance(data, dict):
        errors.append(f"❌ {path_prefix} 应为对象")
        return

    # 检查字段完整性（所有定义的字段是否都存在）
    for field_name in field_defs:
        if field_name not in data:
            missing_fields.append(f"{path_prefix}.{field_name}")

    # 检查每个存在的字段
    for field_name, field_def in field_defs.items():
        path = f"{path_prefix}.{field_name}"
        value = data.get(field_name)

        # 必填检查
        if field_def.get("required"):
            if value is None or (isinstance(value, str) and value.strip() == ""):
                errors.append(f"❌ {path} 为必填字段，不能为空")

        # 类型检查
        if value is not None:
            check_type(value, field_def["type"], path, errors)


def validate_recipe(data):
    """校验食谱JSON，返回 (errors, warnings, missing_fields)"""
    errors = []
    warnings = []
    missing_fields = []

    if not isinstance(data, dict):
        errors.append("❌ JSON顶层应为对象")
        return errors, warnings, missing_fields

    # ── 1. 顶层字段检查 ──
    check_fields(data, TOP_LEVEL_FIELDS, "root", errors, warnings, missing_fields)

    # ── 2. category 检查 ──
    if "category" in data and data["category"]:
        check_fields(data["category"], CATEGORY_FIELDS, "root.category", errors, warnings, missing_fields)
        if data["category"].get("cuisine"):
            check_enum(data["category"]["cuisine"], "cuisine_type", "root.category.cuisine", warnings)

    # ── 3. seasons 检查 ──
    if "seasons" in data and data["seasons"]:
        check_enum(data["seasons"], "season", "root.seasons", warnings)

    # ── 4. cooking_methods 检查 ──
    if "cooking_methods" in data and data["cooking_methods"]:
        check_enum(data["cooking_methods"], "cooking_method", "root.cooking_methods", warnings)

    # ── 5. flavors 检查 ──
    if "flavors" in data and data["flavors"]:
        check_enum(data["flavors"], "flavor", "root.flavors", warnings)

    # ── 6. diet_tags 检查 ──
    if "diet_tags" in data and data["diet_tags"]:
        check_enum(data["diet_tags"], "diet_tag", "root.diet_tags", warnings)

    # ── 7. meal_types 检查 ──
    if "meal_types" in data and data["meal_types"]:
        check_enum(data["meal_types"], "meal_type", "root.meal_types", warnings)

    # ── 8. difficulty/status 检查 ──
    if data.get("difficulty"):
        check_enum(data["difficulty"], "difficulty", "root.difficulty", warnings)
    if data.get("status"):
        check_enum(data["status"], "status", "root.status", warnings)

    # ── 9. ingredients 检查 ──
    ingredient_names = set()
    if "ingredients" in data and data["ingredients"]:
        if not isinstance(data["ingredients"], list):
            errors.append("❌ root.ingredients 应为数组")
        else:
            for i, ing in enumerate(data["ingredients"]):
                path = f"root.ingredients[{i}]"
                check_fields(ing, INGREDIENT_FIELDS, path, errors, warnings, missing_fields)
                if ing.get("name"):
                    ingredient_names.add(ing["name"])
                if ing.get("category"):
                    check_enum(ing["category"], "ingredient_category", f"{path}.category", warnings)

    # ── 10. steps 检查 ──
    step_sequences = set()
    if "steps" in data and data["steps"]:
        if not isinstance(data["steps"], list):
            errors.append("❌ root.steps 应为数组")
        else:
            for i, step in enumerate(data["steps"]):
                path = f"root.steps[{i}]"
                check_fields(step, STEP_FIELDS, path, errors, warnings, missing_fields)
                if step.get("sequence"):
                    step_sequences.add(step["sequence"])
                if step.get("heat_level"):
                    check_enum(step["heat_level"], "heat_level", f"{path}.heat_level", warnings)

                # ingredients_used 子检查
                if "ingredients_used" in step and step["ingredients_used"]:
                    for j, si in enumerate(step["ingredients_used"]):
                        si_path = f"{path}.ingredients_used[{j}]"
                        check_fields(si, STEP_INGREDIENT_FIELDS, si_path, errors, warnings, missing_fields)
                        # 外键引用检查
                        ing_name = si.get("name")
                        if ing_name and ing_name not in ingredient_names:
                            errors.append(f"❌ {si_path}.name \"{ing_name}\" 在 ingredients 中不存在")
                        if si.get("introduced_at"):
                            check_enum(si["introduced_at"], "introduced_at", f"{si_path}.introduced_at", warnings)

    # ── 11. tips 检查 ──
    if "tips" in data and data["tips"]:
        for i, tip in enumerate(data["tips"]):
            path = f"root.tips[{i}]"
            check_fields(tip, TIP_FIELDS, path, errors, warnings, missing_fields)
            if tip.get("category"):
                check_enum(tip["category"], "tip_category", f"{path}.category", warnings)
            # step_sequence 引用检查
            if tip.get("step_sequence") and tip["step_sequence"] not in step_sequences:
                warnings.append(f"⚠️ {path}.step_sequence {tip['step_sequence']} 在 steps 中不存在对应序号")

    # ── 12. techniques 检查 ──
    if "techniques" in data and data["techniques"]:
        for i, tech in enumerate(data["techniques"]):
            path = f"root.techniques[{i}]"
            check_fields(tech, TECHNIQUE_FIELDS, path, errors, warnings, missing_fields)
            if tech.get("step_sequence") and tech["step_sequence"] not in step_sequences:
                warnings.append(f"⚠️ {path}.step_sequence {tech['step_sequence']} 在 steps 中不存在对应序号")

    # ── 13. cookware 检查 ──
    if "cookware" in data and data["cookware"]:
        for i, cw in enumerate(data["cookware"]):
            path = f"root.cookware[{i}]"
            check_fields(cw, COOKWARE_FIELDS, path, errors, warnings, missing_fields)
            if cw.get("category"):
                check_enum(cw["category"], "cookware_category", f"{path}.category", warnings)

    # ── 14. nutrition 检查 ──
    if "nutrition" in data and data["nutrition"]:
        check_fields(data["nutrition"], NUTRITION_FIELDS, "root.nutrition", errors, warnings, missing_fields)

    # ── 15. background 检查 ──
    if "background" in data and data["background"]:
        check_fields(data["background"], BACKGROUND_FIELDS, "root.background", errors, warnings, missing_fields)

    # ── 16. history 检查 ──
    if "history" in data and data["history"]:
        for i, h in enumerate(data["history"]):
            path = f"root.history[{i}]"
            check_fields(h, HISTORY_FIELDS, path, errors, warnings, missing_fields)

    # ── 17. relations 检查 ──
    if "relations" in data and data["relations"]:
        for i, r in enumerate(data["relations"]):
            path = f"root.relations[{i}]"
            check_fields(r, RELATION_FIELDS, path, errors, warnings, missing_fields)
            if r.get("relation_type"):
                check_enum(r["relation_type"], "relation_type", f"{path}.relation_type", warnings)

    return errors, warnings, missing_fields


def main():
    if len(sys.argv) < 2:
        print("用法：python recipe_json_validate.py <json_file>")
        print()
        print("校验JSON食谱文件的完整性和格式")
        sys.exit(1)

    json_file = sys.argv[1]

    # 加载JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON格式错误: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ 文件不存在: {json_file}")
        sys.exit(1)

    # 校验 - 先 jsonschema(结构 + 枚举 + 类型),再手动(语义 + 引用)
    schema_errors, _ = validate_with_jsonschema(data)
    manual_errors, warnings, missing_fields = validate_recipe(data)

    # schema 错误优先(更基础)
    errors = schema_errors + manual_errors

    # 输出结果
    print(f"\n📋 校验报告：{json_file}")
    print("=" * 50)

    if missing_fields:
        print(f"\n📎 缺失字段（{len(missing_fields)}个）：建议补充，值填 null 或空数组")
        for f in missing_fields:
            print(f"  📎 {f}")

    if errors:
        print(f"\n❌ 错误（{len(errors)}个）：必须修正")
        for e in errors:
            print(f"  {e}")

    if warnings:
        print(f"\n⚠️ 警告（{len(warnings)}个）：建议修正")
        for w in warnings:
            print(f"  {w}")

    if not errors and not warnings and not missing_fields:
        print("\n✅ 校验通过！JSON完整且格式正确。")
    elif not errors:
        print(f"\n✅ 校验通过（{len(warnings)}个警告，{len(missing_fields)}个缺失字段）")
    else:
        print(f"\n❌ 校验未通过（{len(errors)}个错误）请修正后重新校验。")

    print()
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
