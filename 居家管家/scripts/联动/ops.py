# ops.py - SM9 联动功能域 · 3 场景业务操作(prompt 生成 + 场景数据)
#
# 口径: scenes/SM9-联动功能.md(2026-08-04 定稿)· 08-HTML 交互规范 v1 · 跨技能契约
# 本质: 跨技能协作 —— 居家管家持物品数据,卡路里/饼干记账持各自领域数据;
#       联动执行 = 复制 prompt 到对应技能(单工闭环),本域只做能力展示与触发引导。
# 依赖: scripts/home_manager/* 公共层只读调用,不修改。
#
# 2026-08-10 用户裁定: 删除联动偏好(三态频控/link_prefs.json/sm9-prefs)——
#   顺路建议无条件生成(录食品/有价物品即提醒),用户看到可自由使用或无视。
import os
from pathlib import Path

from home_manager.item_ops import item_detail_payload, search_items_payload
from home_manager.db import DB_PATH

# ── 联动契约表(能力索引 · 3 条)────────────────────────────────────────────────
# 每条: 联动名 / 触发词 / 依赖技能 / 数据流 / 示例 prompt / 对应场景
# 双按钮语义(G6 审查 2026-08-10 裁定):
#   entry_prompt = 「复制触发 prompt」→ 粘贴给 **目标技能**(卡路里/饼干记账),直接执行
#   scene_prompt = 「前往业务场景」→ 粘贴给 **居家管家**,走物品确认流程(与 HELP prompt 同款)
LINK_CATALOG = [
    {
        "id": "food",
        "name": "食品联动",
        "trigger": "记到卡路里",
        "skill": "卡路里",
        "data_flow": "居家管家物品(名称/数量/单位) → 卡路里「记一餐 / 查食品」",
        "example_prompt": "把牛奶记到卡路里",
        "scene": "SM9-2",
        "entry_prompt": "请加载「卡路里」技能,帮我记一餐(唤醒词:记一餐):\n  食物(如牛奶): ___\n  数量(如 2 件/个): ___",
        "scene_prompt": "请加载「居家管家」技能,帮我把食品记到卡路里(唤醒词:记到卡路里):\n\n  物  品(如牛奶): ___\n  操  作(记到今日饮食/查热量): ___",
    },
    {
        "id": "price",
        "name": "价格联动",
        "trigger": "记到记账",
        "skill": "饼干记账",
        "data_flow": "居家管家物品(名称/价格/分类) → 饼干记账「记支出」",
        "example_prompt": "把牛奶的价格记到记账",
        "scene": "SM9-3",
        "entry_prompt": "请加载「饼干记账」技能,帮我记一笔支出(唤醒词:记支出):\n  物品(如牛奶): ___\n  金额(如 ¥11.8): ___\n  分类(餐饮/家居/数码/工具/医疗/娱乐/服饰/其他): ___",
        "scene_prompt": "请加载「居家管家」技能,帮我把价格记到记账(唤醒词:记到记账):\n\n  物  品(如牛奶): ___\n  方  向(支出/收入): ___",
    },
    {
        "id": "fitness",
        "name": "健身计划联动",
        "trigger": "去健身",
        "skill": "卡路里 → 穿搭出行",
        "data_flow": "卡路里健身计划(唤醒词:看今天练什么/看本周计划) → 出行清单「健身」类型(基础物品 + 护具知识表)",
        "example_prompt": "带物品(联动健身计划)",
        "scene": "SM3-4",
        "entry_prompt": "请加载「卡路里」技能,帮我看健身计划(唤醒词:看今天练什么/看本周计划):\n  天  数(今天/本周): ___",
        "scene_prompt": "请加载「居家管家」技能,帮我做出行带物清单(唤醒词:带物品):\n  行程类型: 健身\n  天  数: 1\n  操  作: 带出\n  (健身联动两层推荐: 力量/有氧/休息日 → 基础物品;动作 → 护具知识表)",
    },
]

# 食品判定关键词(seed_key 为 D1 字段,本批按分类名 + 名称启发,诚实标注)
FOOD_CATEGORY_KEYWORDS = (
    "食物", "饮品", "饮料", "零食", "酒", "乳", "茶", "咖啡",
    "调味", "粮油", "生鲜", "水果", "蔬菜", "肉", "蛋", "水",
)
FOOD_NAME_KEYWORDS = ("水", "奶", "茶", "咖啡", "果汁", "酒", "酸奶", "面包",
                      "饼干", "米", "面", "油", "酱", "糖", "盐", "果", "菜",
                      "肉", "蛋", "零食", "薯片", "巧克力")

# 物品分类 → 饼干记账分类映射(可扩展;未命中 → 其他)
CATEGORY_TO_LEDGER = {
    "食物与饮品": "餐饮", "饮品": "餐饮", "食物": "餐饮",
    "家居与陈设": "家居", "清洁用品": "家居",
    "数码与电子": "数码", "工具与器材": "工具",
    "健康与医药": "医疗", "文体与娱乐": "娱乐",
    "衣物与穿戴": "服饰", "资产与凭证": "其他",
}


# ── 物品查询(公共层只读调用)────────────────────────────────────────────────────


def search_food_candidates(name: str, limit: int = 8) -> list[dict]:
    """按名称搜物品候选(物品确认前置)"""
    return search_items_payload(name=name, limit=limit)


def get_item(item_id: int) -> dict | None:
    """按 ID 取物品详情(公共层 item_ops,只读)"""
    return item_detail_payload(item_id)


# ── 食品判定(无 seed_key 的启发式 + 诚实标注)──────────────────────────────────


def is_food_item(item: dict) -> tuple[bool, str]:
    """判定物品是否为食品/饮品。

    返回 (is_food, reason): reason 说明判定依据(分类名 / 名称启发),
    页面标注「按分类/名称判断,可修正」——不冒充权威。
    """
    cat = (item.get("category") or "").strip()
    name = (item.get("name") or "").strip()
    if not cat and not name:
        return False, "物品无分类无名称,无法判定"
    if cat:
        for kw in FOOD_CATEGORY_KEYWORDS:
            if kw in cat:
                return True, f"分类「{cat}」属食品/饮品"
    for kw in FOOD_NAME_KEYWORDS:
        if name and kw in name:
            return True, f"名称含「{kw}」,疑似食品/饮品"
    if cat:
        return False, f"分类「{cat}」不在食品/饮品范围"
    return False, "名称未命中食品关键词"


# ── 价格提取(单价 × 数量 → 总价)──────────────────────────────────────────────


def item_price_info(item: dict) -> dict:
    """价格信息: 单价(元) × 总数量 → 总价;无单价 → has_price=False"""
    price = item.get("purchase_price")
    locations = item.get("locations") or []
    total_qty = sum((l.get("quantity") or 0) for l in locations) or 1
    if price is None or price == "":
        return {"has_price": False, "unit_price": None,
                "quantity": total_qty, "total_price": None}
    price = float(price)
    return {"has_price": True, "unit_price": price,
            "quantity": total_qty, "total_price": round(price * total_qty, 2)}


def ledger_category(item: dict) -> str:
    """物品分类 → 饼干记账分类(映射表,未命中 → 其他)"""
    cat = (item.get("category") or "").strip()
    for key, val in CATEGORY_TO_LEDGER.items():
        if key in cat:
            return val
    return "其他"


# ── 跨技能 prompt 生成(单工闭环 · 复制到对应技能)──────────────────────────────


def build_calorie_prompt(item: dict, action: str) -> str:
    """食品联动 prompt → 卡路里技能。

    action: "log" = 记到今日饮食 / "query" = 查热量
    数据契约: 居家管家只提供名称/数量/单位;热量由卡路里侧查食品库补全
    (居家管家无热量数据,不冒充)。
    """
    name = item.get("name") or "该物品"
    qty = _qty_str(item)
    if action == "log":
        return (
            f"请加载「卡路里」技能,帮我记一餐(唤醒词:记一餐):\n"
            f"  食物: {name}\n"
            f"  数量: {qty}(来自居家管家联动)\n"
            f"  (热量/蛋白请在卡路里食品库查询补充;查不到请引导存食品)"
        )
    return (
        f"请加载「卡路里」技能,帮我查食品热量(唤醒词:查食品):\n"
        f"  食物: {name}\n"
        f"  数量: {qty}(来自居家管家联动)"
    )


def build_accounting_prompt(item: dict, direction: str) -> str:
    """价格联动 prompt → 饼干记账技能。

    direction: "expense" = 记支出 / "income" = 记收入(退货退款)
    """
    name = item.get("name") or "该物品"
    info = item_price_info(item)
    if not info["has_price"]:
        return None
    price = info["total_price"]
    cat = ledger_category(item)
    if direction == "income":
        return (
            f"请加载「饼干记账」技能,帮我记一笔收入(唤醒词:记收入):\n"
            f"  物品: {name}(退货退款,来自居家管家联动)\n"
            f"  金额: +¥{price}\n"
            f"  分类: {cat}"
        )
    return (
        f"请加载「饼干记账」技能,帮我记一笔支出(唤醒词:记支出):\n"
        f"  物品: {name}(来自居家管家联动)\n"
        f"  金额: ¥{price}\n"
        f"  分类: {cat}"
    )


def build_fitness_prompt() -> str:
    """健身计划联动 prompt → 居家管家出行清单(SM3-4 已实现,本域只索引)。

    契约统一(SM3 权威枚举): 行程类型 = 健身/出差/旅行/超市/游泳/爬山/滑雪/自定义,
    健身联动走「健身」类型(两层推荐: 力量/有氧/休息日 → 基础物品;动作 → 护具知识表)。
    """
    return (
        f"请加载「居家管家」技能,帮我做出行带物清单(唤醒词:带物品):\n"
        f"  行程类型: 健身\n"
        f"  天  数: 1\n"
        f"  操  作: 带出\n"
        f"  (健身联动两层推荐: 力量/有氧/休息日 → 基础物品;动作 → 护具知识表)"
    )


def _qty_str(item: dict) -> str:
    """数量字符串: N 件/个(单位未录入,诚实标注)"""
    locations = item.get("locations") or []
    total = sum((l.get("quantity") or 0) for l in locations) or 1
    return f"{total} 件/个(单位未录入,请按实际修正)"


def build_entry_reminders(item: dict) -> list[dict]:
    """录入顺路建议(SM9 规格): 录物品/拍物品(1-1/1-2)回执后调用。

    无条件生成(2026-08-10 用户裁定: 删联动偏好,顺路建议无需防打扰):
      - 食品/饮品物品 → 建议「记到卡路里」(含复制 prompt)
      - 有价格物品 → 建议「记到记账」(含复制 prompt)
    用户看到建议可自由使用或无视。
    返回 [{type: "link", key, label, prompt}],附到回执 HTML 顺路提醒区。
    """
    reminders = []
    is_food, reason = is_food_item(item)
    if is_food:
        reminders.append({
            "type": "link",
            "key": "food",
            "label": "记到卡路里",
            "prompt": build_calorie_prompt(item, "log"),
            "reason": reason,
        })
    info = item_price_info(item)
    if info["has_price"]:
        reminders.append({
            "type": "link",
            "key": "price",
            "label": "记到记账",
            "prompt": build_accounting_prompt(item, "expense"),
            "reason": f"单价 ¥{info['unit_price']} × {info['quantity']} = ¥{info['total_price']}",
        })
    return reminders


# ── 场景数据(render 信封的 data.scene 部分)───────────────────────────────────


def overview_data() -> dict:
    """SM9-1 联动总览: 契约条目列表(2026-08-10: 偏好区已删)"""
    entries = [{
        "id": c["id"], "name": c["name"], "trigger": c["trigger"],
        "skill": c["skill"], "data_flow": c["data_flow"],
        "example_prompt": c["example_prompt"], "scene": c["scene"],
        "entry_prompt": c.get("entry_prompt", ""),
        "scene_prompt": c.get("scene_prompt", ""),
    } for c in LINK_CATALOG]
    return {"entries": entries}


def food_data(item: dict, action: str = "log") -> tuple[bool, str, dict]:
    """SM9-2 食品联动: (ok, msg, scene_data)"""
    is_food, reason = is_food_item(item)
    if not is_food:
        return False, f"「{item.get('name', '')}」不是食品/饮品: {reason}", {
            "item": _item_light(item),
            "suggest": "换一个食品/饮品物品;或先用「改物品」把分类补成食品/饮品",
        }
    actions = [
        {"id": "log", "label": "记到今日饮食", "prompt": build_calorie_prompt(item, "log")},
        {"id": "query", "label": "查热量", "prompt": build_calorie_prompt(item, "query")},
    ]
    return True, "食品联动 prompt 已生成", {
        "item": _item_light(item),
        "food_reason": reason,
        "actions": actions,
        "prompt": build_calorie_prompt(item, action),
    }


def price_data(item: dict, direction: str = "expense") -> tuple[bool, str, dict]:
    """SM9-3 价格联动: (ok, msg, scene_data)"""
    info = item_price_info(item)
    if not info["has_price"]:
        return False, f"「{item.get('name', '')}」没有价格信息", {
            "item": _item_light(item),
            "suggest": "先用「改物品」补录价格(或录入购买记录时填价格),再联动",
        }
    actions = [
        {"id": "expense", "label": "记支出", "prompt": build_accounting_prompt(item, "expense")},
        {"id": "income", "label": "记收入(退货退款)", "prompt": build_accounting_prompt(item, "income")},
    ]
    return True, "价格联动 prompt 已生成", {
        "item": _item_light(item),
        "price": info,
        "ledger_category": ledger_category(item),
        "actions": actions,
        "prompt": build_accounting_prompt(item, direction),
    }


def _item_light(item: dict) -> dict:
    """物品精简卡(照片/名称/分类/状态/数量)"""
    locations = item.get("locations") or []
    total = sum((l.get("quantity") or 0) for l in locations) or 0
    status = (locations[0].get("location_status") if locations else "在家") or "在家"
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "category": item.get("category") or "",
        "status": status,
        "quantity": total,
        "photo_base64": item.get("photo_base64"),
    }
