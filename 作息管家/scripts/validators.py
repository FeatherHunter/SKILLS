"""
作息管家 - 分类校验器 (规则层)
按 5 层架构规范:硬规则集中此处,无 --skip-validation 跳过通道。

用法:
    from validators import validate_category, is_valid_category
    valid, err = validate_category("工作.AI调优")
    if not valid:
        raise ValueError(err)

白名单加载顺序:
    1. .db/category_whitelist.yaml (用户/AI 维护)
    2. 内置 DEFAULT_WHITELIST (兜底,YAML 不存在/损坏时使用)
"""
import re
from pathlib import Path

# === 一级白名单(固定,不可改,严禁动态扩展)===
LEVEL1_WHITELIST = {"维持", "健康", "工作", "学习", "创作", "投入", "调整", "日常"}

# === YAML 白名单路径 ===
WHITELIST_PATH = Path(__file__).parent.parent / ".db" / "category_whitelist.yaml"

# === 内置默认白名单(YAML 不存在/损坏时的兜底)===
DEFAULT_WHITELIST = {
    "维持": ["睡眠", "用餐", "做饭", "洗漱", "通勤", "采购", "就医", "护肤", "散步"],
    "健康": ["运动", "健身", "修行", "冥想", "看病", "康复", "保健", "八段锦"],
    "工作": ["AI调优", "开发", "剪辑", "文案", "运营", "会议", "财务", "调研", "学习"],
    "学习": ["技术", "语言", "考试", "读书", "研究", "AI", "阅读"],
    "创作": ["文字", "视频", "音频", "设计", "编程", "菜谱", "SOP", "教学"],
    "投入": ["家人", "朋友", "同事", "伴侣", "宠物", "社交", "服务", "沟通", "AI"],
    "调整": ["游戏", "视频", "音乐", "手机", "玩耍", "发呆", "追剧", "散步", "午睡", "过渡", "休息", "阅读"],
    "日常": ["代办", "决策", "杂事", "收拾", "行政", "等候"],
}

# === 类别格式:一级 或 一级.二级 ===
# 一级:仅汉字(固定 8 个)
# 二级:汉字 + ASCII 字母数字 + 空格(允许 "AI 调优" "SOP" 等)
_LEVEL1_RE = re.compile(r"^[\u4e00-\u9fa5]+$")
# 二级字符:汉字 / 字母 / 数字 / 空格 / 半角点(允许嵌套)
_LEVEL2_RE = re.compile(r"^[\u4e00-\u9fa5A-Za-z0-9 ]+$")


def load_whitelist() -> dict:
    """
    加载二级白名单。
    优先级:.db/category_whitelist.yaml > DEFAULT_WHITELIST
    YAML 加载失败 fallback 到 DEFAULT,不抛异常(可恢复原则)。
    """
    if not WHITELIST_PATH.exists():
        return {k: list(v) for k, v in DEFAULT_WHITELIST.items()}

    try:
        import yaml
        with open(WHITELIST_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        # YAML 损坏 → 兜底到内置默认,不影响主流程
        return {k: list(v) for k, v in DEFAULT_WHITELIST.items()}

    # 合并:内置默认 + YAML 覆盖/扩展
    merged = {k: list(v) for k, v in DEFAULT_WHITELIST.items()}
    for level1, level2_list in data.items():
        if not isinstance(level2_list, list):
            continue
        if level1 in merged:
            # 取并集(避免 YAML 删了某个二级导致校验失败)
            merged[level1] = list(set(merged[level1] + level2_list))
        else:
            merged[level1] = list(level2_list)
    return merged


def parse_category(category: str):
    """拆分 '工作.AI调优' → ('工作', 'AI调优')"""
    if not category:
        return None, None
    category = category.strip()
    if '.' not in category:
        # 仅一级
        if _LEVEL1_RE.match(category):
            return category, None
        return None, None
    # 一级.二级
    parts = category.split('.', 1)
    level1, level2 = parts[0], parts[1]
    if not _LEVEL1_RE.match(level1):
        return None, None
    if not _LEVEL2_RE.match(level2):
        return None, None
    return level1, level2


def validate_category(category: str):
    """
    校验 category 是否合法。
    返回: (is_valid: bool, error_message: str)
    错误信息包含: 字段名 + 当前值 + 期望值 + 怎么修(申请制流程)。
    """
    if not category:
        return False, "category 不能为空"

    level1, level2 = parse_category(category)
    if not level1:
        return False, (
            f"category 格式错误: '{category}'\n"
            f"  格式: '一级' 或 '一级.二级'\n"
            f"  一级仅支持汉字(8 个固定);二级支持汉字/字母/数字/空格"
        )

    if level1 not in LEVEL1_WHITELIST:
        return False, (
            f"category 一级 '{level1}' 不在白名单。"
            f"允许的一级: {sorted(LEVEL1_WHITELIST)}"
        )

    # 一级合法,二级可选
    if level2 is None:
        return True, ""

    whitelist = load_whitelist()
    allowed = whitelist.get(level1, [])
    if level2 not in allowed:
        return False, (
            f"category 二级 '{level2}' 不在 '{level1}' 白名单。\n"
            f"  当前 '{level1}' 允许的二级: {allowed}\n"
            f"  怎么修: 跟我说 '提议新增 {category}',我会写入白名单 YAML 后再录入。"
        )

    return True, ""


def is_valid_category(category: str) -> bool:
    """简版校验,供其他模块调用"""
    return validate_category(category)[0]


# === 飞书 emoji 映射 (2026-07-22 重构) ===
# 一级 emoji(必须有,所有合法一级都有 emoji)
CATEGORY_EMOJI_MAP = {
    "维持": "🌱",
    "健康": "💪",
    "工作": "💼",
    "学习": "📖",
    "创作": "🎨",
    "投入": "🤝",
    "调整": "😌",
    "日常": "📋",
}

# 二级 emoji(可选,没配的回退到一级 emoji)
CATEGORY_EMOJI_LEVEL2 = {
    "维持": {"睡眠": "😴", "用餐": "🍚", "做饭": "🍳", "洗漱": "🚿", "通勤": "🚴", "采购": "🛒", "就医": "💊", "护肤": "💆", "散步": "🚶"},
    "健康": {"运动": "🏃", "健身": "🏋️", "修行": "🧘", "冥想": "🧠", "看病": "🩺", "康复": "🩹", "保健": "🛡️", "八段锦": "☯️"},
    "工作": {"AI调优": "🤖", "开发": "💻", "剪辑": "🎬", "文案": "📝", "运营": "📊", "会议": "🤝", "财务": "💰", "调研": "🔍", "学习": "📚"},
    "学习": {"技术": "💻", "语言": "🗣️", "考试": "✏️", "读书": "📕", "研究": "🔬", "AI": "🤖", "阅读": "📰"},
    "创作": {"文字": "✍️", "视频": "🎥", "音频": "🎵", "设计": "🖌️", "编程": "💻", "菜谱": "🍴", "SOP": "📋", "教学": "👨‍🏫"},
    "投入": {"家人": "👨‍👩‍👧", "朋友": "🧑‍🤝‍🧑", "同事": "👔", "伴侣": "❤️", "宠物": "🐾", "社交": "👋", "服务": "🛎️", "沟通": "💬", "AI": "🤖"},
    "调整": {"游戏": "🎮", "视频": "📺", "音乐": "🎧", "手机": "📱", "玩耍": "🎈", "发呆": "💭", "追剧": "🍿", "散步": "🚶", "午睡": "😴", "过渡": "⏳", "休息": "🛋️", "阅读": "📰"},
    "日常": {"代办": "☑️", "决策": "🤔", "杂事": "🔧", "收拾": "🧹", "行政": "📑", "等候": "⏳", "园艺": "🌿"},
}


def get_emoji_prefix(category: str) -> str:
    """
    根据 category 返回 emoji 字符串(用于飞书 description 头部)。
    例: get_emoji_prefix('工作.AI调优') → '💼🤖'
        get_emoji_prefix('工作') → '💼'
        get_emoji_prefix('日常.园艺') → '📋🌿'
        get_emoji_prefix('') → ''
    策略(Q3=B): 永远有一级 emoji 兜底,二级 emoji 缺时只显示一级
    """
    if not category:
        return ""
    level1, level2 = parse_category(category)
    if not level1 or level1 not in CATEGORY_EMOJI_MAP:
        return ""
    result = CATEGORY_EMOJI_MAP[level1]
    if level2 and level2 in CATEGORY_EMOJI_LEVEL2.get(level1, {}):
        result += CATEGORY_EMOJI_LEVEL2[level1][level2]
    return result


def format_category_for_feishu(category: str) -> str:
    """
    把 category 渲染成飞书 description 用的格式:
    '工作.AI调优' → '💼🤖 工作.AI调优'
    '工作'         → '💼 工作'
    ''             → ''
    """
    if not category:
        return ""
    emoji = get_emoji_prefix(category)
    return f"{emoji} {category}".strip() if emoji else category


def list_level1() -> list:
    """列出所有一级"""
    return sorted(LEVEL1_WHITELIST)


def list_level2(level1: str = None) -> dict:
    """列出所有二级(或指定一级下的二级)"""
    w = load_whitelist()
    if level1:
        return {level1: w.get(level1, [])}
    return w