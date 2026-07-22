from cli_formatter import emit, parse_json_flag, error  # L3
#!/usr/bin/env python3
"""
私家大厨 - 采购清单管理(5 层架构版)

数据流:
    recipes / ingredients 表 → generate() → JSON 输出

支持:
    generate         多食谱合并采购清单 JSON
    list-allergens   列出所有涉及过敏原(选填字段触发)

设计:
    - 5 层架构:文档(features/shopping.md) / 契约(本文件 CLI) / 业务(本文件核心)
    - 数据走 db.py query(),不直连数据库
    - 跨食谱自动合并同名同 unit 食材
    - allergy_tags 选填,有数据时显示
"""
import sys
import json
from datetime import datetime
from collections import defaultdict

# 复用 db.py(数据层统一入口)
from db import query


# ─────────────────────────────────────────────
# ③ 业务层 · 核心查询
# ─────────────────────────────────────────────

CATEGORY_ORDER = [
    "肉类",        # 主料 · 鲜
    "海鲜",        # 主料 · 鲜
    "蛋类",        # 主料 · 鲜
    "蔬菜",        # 主料 · 鲜
    "葱姜蒜",      # v5.2 新增 · 中式基础主料
    "香草",        # v5.2 新增 · 整株鲜香草
    "调料",        # 粉末/液体/干香料
    "豆制品",      # 加工
    "主食",        # 加工
    "干货",        # 干货
    "其他",        # 兜底
]
"""采购清单分类顺序(v5.2 · 11 类)
顺序反映真实采购动线:鲜货区 → 香料区 → 干货区
葱姜蒜插在蔬菜后,符合超市货架顺序
"""

ALLERGEN_KEYWORDS = {
    "花生": "花生",
    "芝麻": "芝麻",
    "牛奶": "乳制品",
    "黄油": "乳制品",
    "奶酪": "乳制品",
    "虾": "甲壳类",
    "蟹": "甲壳类",
    "小麦": "麸质",
    "面粉": "麸质",
    "鸡蛋": "蛋类",
    "大豆": "大豆",
    "豆豉": "大豆",
    "黄豆": "大豆",
}


def detect_allergens(ingredients: list) -> list:
    """从食材名自动检测常见过敏原(基于关键词映射)"""
    detected = set()
    for ing in ingredients:
        name = ing.get("name", "")
        for keyword, allergen in ALLERGEN_KEYWORDS.items():
            if keyword in name:
                detected.add(allergen)
    return sorted(detected)


def merge_ingredients(ingredients_by_recipe: dict, multipliers: dict = None) -> dict:
    """
    跨食谱合并:同 name + 同 unit → 数量相加,记录来自哪几道菜及各自用量

    Args:
        ingredients_by_recipe: {recipe_id: [{name, quantity, unit, ...}, ...]}
        multipliers: {recipe_id: 倍数(默认 1,2 菜共用显示"2 份")}

    Returns:
        {category: [{merged_ingredient}, ...]}
    """
    if multipliers is None:
        multipliers = {}

    # 第一轮:同 name+unit 合并
    merged = {}  # key: (name, unit) → {merged data}
    for recipe_id, ings in ingredients_by_recipe.items():
        multiplier = multipliers.get(recipe_id, 1)
        for ing in ings:
            key = (ing["name"], ing["unit"])
            if key not in merged:
                merged[key] = {
                    "name": ing["name"],
                    "unit": ing["unit"],
                    "quantity": 0,
                    "category": ing.get("category") or "其他",
                    "is_optional": ing.get("is_optional", False),
                    "substitute": ing.get("substitute"),
                    "sources": [],          # [{recipe_id, recipe_name, multiplier, quantity, quantity_text}]
                    "merged_count": 0,      # 几道菜共用
                }
            item = merged[key]
            # 数量按倍数放大
            per_recipe_qty = ing.get("quantity", 0) * multiplier
            item["quantity"] += per_recipe_qty
            item["merged_count"] += 1
            item["sources"].append({
                "recipe_id": recipe_id,
                "recipe_name": ing.get("_recipe_name", "未知"),  # generate 时注入
                "color_index": ing.get("_color_index", 1),       # 同一食谱固定同色
                "multiplier": multiplier,
                "quantity": per_recipe_qty,        # 该菜贡献的量(已乘倍数)
                "quantity_text": ing.get("quantity_text"),
            })

    # 第二轮:按 category 分组,组内按 name 排序
    grouped = defaultdict(list)
    for item in merged.values():
        grouped[item["category"]].append(item)

    # 第三轮:按 category 固定顺序输出
    ordered = {}
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            ordered[cat] = sorted(grouped[cat], key=lambda x: x["name"])
    # 漏网 category(其他)
    for cat in grouped:
        if cat not in ordered:
            ordered[cat] = sorted(grouped[cat], key=lambda x: x["name"])

    return ordered


# 注:v5.2 价格预估已删除。第一性原理:用户知道自己花多少钱,
# AI 硬编码价格(2024 北京 ±50%)反而误导。让用户自己估。


# ─────────────────────────────────────────────
# ② 契约层 · CLI 入口
# ─────────────────────────────────────────────

def generate(args):
    """
    生成采购清单 JSON

    Args:
        args["<recipe_id>"]: 逗号分隔的食谱 ID(1 个或多个)
        args["--exclude-optional"]: 是否排除可选食材
        args["--multipliers"]: 逗号分隔的份数倍数,顺序对应 recipe_ids
                              例如 "2,1" 表示第 1 道菜做 2 份,第 2 道菜做 1 份
                              默认全 1
    """
    recipe_ids_str = args.get("<recipe_id>") or args.get("<recipe_ids>")
    if not recipe_ids_str:
        return {
            "status": "error",
            "error": "missing_recipe_id",
            "message": "请提供食谱ID",
            "how_to_fix": "用法:python shopping_manager.py generate <recipe_id>[,<recipe_id2>,...] [--exclude-optional]"
        }

    recipe_ids = [rid.strip() for rid in recipe_ids_str.split(",") if rid.strip()]
    if not recipe_ids:
        return {
            "status": "error",
            "error": "empty_recipe_id_list",
            "message": "提供的食谱ID为空",
            "how_to_fix": "检查 --exclude-optional 前面的参数,确保至少 1 个有效的 recipe_id"
        }

    exclude_optional = bool(args.get("--exclude-optional"))

    # 解析 multipliers(v5.2 · 份数倍数)
    multipliers_str = args.get("--multipliers", "")
    if multipliers_str:
        try:
            multipliers_list = [int(x.strip()) for x in multipliers_str.split(",") if x.strip()]
        except ValueError:
            return {
                "status": "error",
                "error": "invalid_multipliers",
                "message": "--multipliers 必须为逗号分隔的正整数",
                "how_to_fix": "例:--multipliers 2,1 表示菜 1 做 2 份,菜 2 做 1 份"
            }
        # 数量不够自动补 1,数量太多截断
        multipliers_list = multipliers_list + [1] * (len(recipe_ids) - len(multipliers_list))
        multipliers_list = multipliers_list[:len(recipe_ids)]
        multipliers = {rid: m for rid, m in zip(recipe_ids, multipliers_list)}
    else:
        multipliers = {rid: 1 for rid in recipe_ids}

    # ① 拿食谱基本信息
    placeholders = ",".join(["?" for _ in recipe_ids])
    recipes_rows = query(
        f"SELECT id, name, servings FROM recipes WHERE id IN ({placeholders})",
        tuple(recipe_ids)
    )
    if not recipes_rows:
        return {
            "status": "error",
            "error": "recipes_not_found",
            "message": f"未找到任何食谱(共请求 {len(recipe_ids)} 个ID)",
            "data": {"recipe_ids": recipe_ids},
            "how_to_fix": "1) 用 recipe_manager.py search <菜名> 确认菜名对应正确的 ID 2) 用 recipe_manager.py list 看所有菜 3) 确认 ID 没有拼错(标准 UUID 格式)"
        }

    recipes_map = {}
    for idx, r in enumerate(recipes_rows, start=1):
        color_index = ((idx - 1) % 6) + 1  # 1-6 循环,和 shopping_view.html 的 --r1..--r6 对齐
        recipes_map[r["id"]] = {
            "id": r["id"],
            "name": r["name"],
            "servings": r["servings"],
            "servings_base": r["servings"],  # 菜谱原份数
            "servings_multiplier": multipliers.get(r["id"], 1),  # 用户倍数
            "servings_actual": r["servings"] * multipliers.get(r["id"], 1),  # 实际份数 = base × 倍数
            "ingredient_count": 0,
            "color_index": color_index,      # v5.2 UI:同一食谱固定同色
        }

    # ② 拿食材
    conditions = [f"recipe_id IN ({placeholders})"]
    params = list(recipe_ids)
    if exclude_optional:
        conditions.append("is_optional = 0")

    ingredients_rows = query(
        f"""SELECT id, recipe_id, name, quantity, unit, quantity_text,
                   category, is_optional, substitute
            FROM ingredients
            WHERE {' AND '.join(conditions)}
            ORDER BY category, sequence""",
        tuple(params)
    )

    # ③ 按 recipe_id 聚合食材(为合并做准备)+ 注入菜名(让 sources 知道来自哪道菜)
    ingredients_by_recipe = defaultdict(list)
    for row in ingredients_rows:
        rid = row["recipe_id"]
        # 给 row 注入菜名,供 merge 时塞入 sources
        row["_recipe_name"] = recipes_map[rid]["name"] if rid in recipes_map else "未知"
        row["_color_index"] = recipes_map[rid]["color_index"] if rid in recipes_map else 1
        ingredients_by_recipe[rid].append(row)
        if rid in recipes_map:
            recipes_map[rid]["ingredient_count"] += 1

    # ④ 跨食谱合并(带 multipliers)
    grouped = merge_ingredients(ingredients_by_recipe, multipliers)

    # ⑤ 过敏原检测(选填字段,有数据时才有意义)
    all_ingredients_flat = [ing for ings in ingredients_by_recipe.values() for ing in ings]
    allergens = detect_allergens(all_ingredients_flat)

    # ⑥ 输出
    total_items = sum(len(items) for items in grouped.values())
    return {
        "status": "success",
        "data": {
            "generated_at": datetime.now().isoformat(),
            "recipe_ids": recipe_ids,
            "recipe_names": [r["name"] for r in recipes_rows],
            "exclude_optional": exclude_optional,
            "multipliers": multipliers,        # v5.2 新增 · {rid: 倍数}
            "summary": {
                "recipe_count": len(recipes_rows),
                "ingredient_count": total_items,
                "allergens": allergens,        # 选填字段
            },
            "recipes": list(recipes_map.values()),
            "ingredients_by_category": grouped,
        }
    }


def list_allergens(args):
    """列出本次生成涉及的过敏原(独立子命令,方便 AI 单独查询)"""
    recipe_ids_str = args.get("<recipe_id>")
    if not recipe_ids_str:
        return {"status": "error", "message": "请提供食谱ID"}
    recipe_ids = [rid.strip() for rid in recipe_ids_str.split(",") if rid.strip()]

    placeholders = ",".join(["?" for _ in recipe_ids])
    ingredients_rows = query(
        f"SELECT name FROM ingredients WHERE recipe_id IN ({placeholders})",
        tuple(recipe_ids)
    )
    allergens = detect_allergens(ingredients_rows)
    return {
        "status": "success",
        "data": {
            "recipe_ids": recipe_ids,
            "allergens": allergens,
            "note": "过敏原基于食材名自动检测,仅供参考;录入时建议显式标 allergy_tags 字段",
        }
    }


# ─────────────────────────────────────────────
# CLI 解析
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "message": "用法:python shopping_manager.py generate <recipe_id>[,<recipe_id2>,...] [--exclude-optional] | list-allergens <recipe_ids>"
        }, ensure_ascii=False))
        return

    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])  # L3: --json 标志
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
            if "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            i += 1

    if action == "generate":
        result = generate(args)
    elif action == "list-allergens":
        result = list_allergens(args)
    else:
        result = {"status": "error", "message": f"未知操作:{action}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()