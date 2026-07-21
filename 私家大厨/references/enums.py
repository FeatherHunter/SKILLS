#!/usr/bin/env python3
"""
私家大厨 - 统一枚举定义(5 层架构改造)

按"5 层架构"原则,所有枚举值集中在本文件,业务层/契约层都读这一份。
避免规则散落在 validators.py / recipe_import.py / recipe_json_validate.py 三处。

使用:
    from enums import normalize_value, get_valid_values
    # 用户输入"中午" → 归一化为"中"
    normalized = normalize_value("meal_types", "中午")
    # 获取某枚举的所有合法值
    all_values = get_valid_values("cooking_methods")
"""

# ====================================================================
# 枚举定义(value + 别名)
# ====================================================================

DIFFICULTY = ["快手菜", "简单", "中等", "困难", "大师"]
"""难度(主表 recipes.difficulty)"""

STATUS = ["未做", "已做", "熟练"]
"""状态(主表 recipes.status)— 业务可见的 3 个状态"""

ARCHIVED_STATUS = "已废弃"
"""软删除状态(主表 recipes.status) — 不在 STATUS 列表里,表示该菜已废弃不显示
recipe_import.py / recipe_manager.py 的 list / search 都用这个常量过滤"""

COOKING_METHODS = ["炒", "蒸", "煮", "烤", "炸", "煎", "焖", "炖", "拌", "卤", "熏", "生食", "煸"]
"""烹饪方式(recipe_cooking_methods.method)"""

FLAVORS = ["酸", "甜", "辣", "咸", "鲜", "苦", "麻", "香"]
"""口味(recipe_flavors.flavor)— 含"香"作描述性味道"""

MEAL_TYPES = ["早", "中", "晚", "夜宵", "下午茶", "聚会"]
"""用餐类型(recipe_meal_types.meal_type)"""

SEASONS = ["春", "夏", "秋", "冬"]
"""适合季节(recipe_seasons.season)"""

DIET_TAGS = [
    "高蛋白", "低蛋白",
    "高脂肪", "低脂肪",
    "高碳水", "低碳水",
    "低糖", "低盐",
    "高纤维", "素食",
    "无麸质", "低卡"
]
"""饮食标签(recipe_diet_tags.tag)"""

COOKWARE_CATEGORIES = ["锅", "炉", "刀", "其他"]
"""炊具分类(cookware.category)"""

INTRODUCED_AT = ["开局", "开局加入", "中途加入", "最后加入"]
"""食材加入时机(step_ingredients.introduced_at)"""

INGREDIENT_CATEGORIES = ["肉类", "海鲜", "蔬菜", "调料", "豆制品", "蛋类", "主食", "干货", "其他"]
"""食材分类(ingredients.category)"""

TIP_CATEGORIES = ["火候", "刀工", "调味", "采购", "设备", "保存", "文化"]
"""贴士分类(tips.category)"""

HEAT_LEVELS = ["微火", "小火", "中火", "大火", "猛火"]
"""火候(cooking_steps.heat_level)"""

CUISINE_TYPES = [
    "川菜", "粤菜", "湘菜", "闽菜", "浙菜", "苏菜",
    "鲁菜", "东北菜", "京菜", "沪菜", "台湾菜", "本帮菜"
]
"""菜系(recipe_categories.cuisine_type)"""

RELATION_TYPES = ["派生", "变体", "改良"]
"""派生关系类型(recipe_relations.relation_type)"""

# ====================================================================
# 别名表(用户口语 → 标准值)
# ====================================================================
# 设计:不是"枚举多值",而是"输入归一化"
# 用户输入"中午" → 内部归一为"中" → 写入 DB
# 这样枚举只有一份合法值,DB 数据保持一致

ALIASES = {
    "meal_types": {
        "中午": "中",
        "早饭": "早",
        "早餐": "早",
        "晚饭": "晚",
        "晚餐": "晚",
        "午饭": "中",
        "午餐": "中",
        "夜宵": "夜宵",  # 标准值
    },
    "introduced_at": {
        "第1步加入": "开局加入",
        "开局": "开局加入",
        "一开始": "开局加入",
        "最开始": "开局加入",
        "最后": "最后加入",
        "最后一步": "最后加入",
        "中间": "中途加入",
        "中途": "中途加入",
        "回锅": "中途加入",  # 回锅 = 中途再加一次
    },
    "cooking_methods": {
        "干煸": "煸",  # 干煸 = 煸
        "清蒸": "蒸",
        "水煮": "煮",
        "烧烤": "烤",
        "油炸": "炸",
        "焖煮": "焖",
    },
    "flavors": {
        "麻辣": "麻",  # 麻辣优先用"麻"(更基础)
        "香辣": "辣",
        "微辣": "辣",
        "特辣": "辣",
    },
}


# ====================================================================
# 主索引:所有枚举的集中访问
# ====================================================================

ENUMS = {
    "difficulty": DIFFICULTY,
    "status": STATUS,
    "cooking_methods": COOKING_METHODS,
    "flavors": FLAVORS,
    "meal_types": MEAL_TYPES,
    "seasons": SEASONS,
    "diet_tags": DIET_TAGS,
    "cookware_categories": COOKWARE_CATEGORIES,
    "introduced_at": INTRODUCED_AT,
    "ingredient_categories": INGREDIENT_CATEGORIES,
    "tip_categories": TIP_CATEGORIES,
    "heat_levels": HEAT_LEVELS,
    "cuisine_types": CUISINE_TYPES,
    "relation_types": RELATION_TYPES,
}


# ====================================================================
# 函数
# ====================================================================

def get_valid_values(enum_name: str) -> list:
    """获取某枚举的所有合法值"""
    if enum_name not in ENUMS:
        raise ValueError(f"未知枚举: {enum_name}(不是合法枚举名: {list(ENUMS.keys())})")
    return list(ENUMS[enum_name])


def normalize_value(enum_name: str, user_input: str) -> str:
    """
    把用户输入归一化为标准枚举值。

    Args:
        enum_name: 枚举名(从 ENUMS 选)
        user_input: 用户输入(可能是别名)

    Returns:
        标准枚举值

    Raises:
        ValueError: 输入不在合法值也不在别名表里
    """
    if enum_name not in ENUMS:
        raise ValueError(f"未知枚举: {enum_name}")

    valid = ENUMS[enum_name]
    aliases = ALIASES.get(enum_name, {})

    # 1. 直接命中合法值
    if user_input in valid:
        return user_input

    # 2. 查别名表
    if user_input in aliases:
        return aliases[user_input]

    # 3. 都不命中 → 报错
    raise ValueError(
        f"'{user_input}' 不是 '{enum_name}' 的合法值。"
        f"合法值: {valid}。别名: {list(aliases.keys())}"
    )


def is_valid_value(enum_name: str, value: str) -> bool:
    """检查值是否合法(标准值或别名都算合法)"""
    if enum_name not in ENUMS:
        return False
    return value in ENUMS[enum_name] or value in ALIASES.get(enum_name, {})


# ====================================================================
# CLI(独立可调用)
# ====================================================================

def main():
    """CLI:列出所有枚举,或查询某枚举"""
    import sys
    import json
    if len(sys.argv) < 2:
        print("""用法:
    python enums.py list                    # 列出所有枚举
    python enums.py show <enum_name>        # 展示某枚举的合法值+别名
    python enums.py normalize <enum> <val>  # 归一化某值
""")
        return

    action = sys.argv[1]
    if action == "list":
        print(json.dumps({"enums": list(ENUMS.keys())}, ensure_ascii=False, indent=2))
    elif action == "show":
        if len(sys.argv) < 3:
            print("请提供枚举名")
            return
        name = sys.argv[2]
        print(json.dumps({
            "enum": name,
            "valid_values": get_valid_values(name),
            "aliases": ALIASES.get(name, {})
        }, ensure_ascii=False, indent=2))
    elif action == "normalize":
        if len(sys.argv) < 4:
            print("请提供枚举名和值")
            return
        name = sys.argv[2]
        val = sys.argv[3]
        try:
            normalized = normalize_value(name, val)
            print(json.dumps({"input": val, "normalized": normalized}, ensure_ascii=False, indent=2))
        except ValueError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
    else:
        print(f"未知操作: {action}")


if __name__ == "__main__":
    main()
