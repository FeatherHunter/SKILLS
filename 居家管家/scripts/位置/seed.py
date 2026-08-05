# 位置/seed.py - 收纳建议冷启动种子(静态分类↔位置关联表)
#
# SM2 规格(待细化):冷启动用静态分类↔位置关联表(种子,实施任务)。
# 匹配优先级:categories.seed_key > 分类名(名称含关键字的子分类也能命中)。
# 种子仅作冷启动兜底(该分类无任何物品位置数据时);用户数据优先(现有物品位置分布)。

_SEED_BY_KEY = {
    "food": "厨房/食品柜",
    "clothing": "卧室/衣柜",
    "home": "客厅/收纳柜",
    "tool": "阳台/工具箱",
    "digital": "客厅/数码抽屉",
    "health": "卧室/药箱",
    "sport": "客厅/文体柜",
    "asset": "卧室/文件柜",
}

# 分类名关键字 → 默认位置(名称命中即可,覆盖 seed_key 缺失的老分类)
_SEED_BY_NAME = [
    ("食物", "厨房/食品柜"),
    ("食品", "厨房/食品柜"),
    ("零食", "厨房/食品柜"),
    ("干货", "厨房/食品柜"),
    ("粮油", "厨房/食品柜"),
    ("调味", "厨房/调味区"),
    ("饮", "厨房/食品柜"),
    ("衣", "卧室/衣柜"),
    ("鞋", "玄关/鞋柜"),
    ("家居", "客厅/收纳柜"),
    ("家具", "客厅/收纳柜"),
    ("工具", "阳台/工具箱"),
    ("器材", "阳台/工具箱"),
    ("数码", "客厅/数码抽屉"),
    ("电子", "客厅/数码抽屉"),
    ("健康", "卧室/药箱"),
    ("医药", "卧室/药箱"),
    ("文体", "客厅/文体柜"),
    ("娱乐", "客厅/文体柜"),
    ("资产", "卧室/文件柜"),
    ("凭证", "卧室/文件柜"),
    ("证件", "卧室/文件柜"),
]


def default_location(seed_key=None, category_name=None):
    """分类 → 默认位置(seed_key 优先,其次分类名关键字,无命中返回 None)"""
    if seed_key:
        hit = _SEED_BY_KEY.get(str(seed_key).strip().lower())
        if hit:
            return hit
    if category_name:
        for kw, loc in _SEED_BY_NAME:
            if kw in category_name:
                return loc
    return None


def all_seeds():
    """全部种子(调试/测试用)"""
    return list(_SEED_BY_KEY.items())
