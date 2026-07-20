"""contraindications.soft_rules — 禁忌动作心法(为什么这个动作被禁忌)

本模块表达"禁忌的来由",**不是**关键字查表的死规则。
软规则集中在 CONTRAINDICATIONS 字典,每个禁忌是一段心法(为什么 + 怎么识别 + 触发级别)。

设计原则(2026-07-20 用户决策):
- 三类常见禁忌:腰(腰椎间盘突出)、膝(关节问题)、肩(肩袖损伤)
- 每类禁忌独立配置,默认全开(strict 模式才报错)
- 心法写在这里,硬规则(关键字匹配)在 validators.py
- SAFE_VARIANTS 白名单:康复期专门设计的"安全变体"(支撑式/俯卧/坐姿等),
  即使动作名含禁忌关键字,也不报禁忌(2026-07-20 实测:v14.4 计划的
  "支撑式悍马俯身划船""俯卧 T-bar 划船"用俯身但腰部受力小,可放心使用)。

数据来源:
- 临床禁忌:运动康复常见禁忌动作
- 用户声明:在 user_profile 中标注的伤病
- 安全变体:用户复盘/教练确认过"已替代为安全版"的动作
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["info", "warn", "error"]


# ── 安全变体白名单(子串匹配) ──
# 含这些前缀/关键字的动作名,即使包含禁忌关键字,也视为安全变体。
#
# 设计原则(2026-07-20 第一性原理):
# - 白名单 = "重力 / 支撑方式 让禁忌风险消失" 的明确安全变体
# - 不能因为"前缀听起来安全"就豁免 — 2026-07-20 反例:
#   "坐姿腿弯举"含"坐姿",但腿弯举伤腰,绝不能豁免
#   "器械倒蹬"含"器械",但倒蹬伤腰,绝不能豁免
# - 所以白名单只放"重力方向明确安全"的关键字,不放"器械/坐姿"这种宽泛词
#
# 2026-07-20 实测:v14.4 计划的"支撑式悍马俯身划船""俯卧 T-bar 划船"
# 用俯身但腰部受力小(支撑/俯卧 = 重力完全卸力),可放心使用。
SAFE_VARIANTS: tuple[str, ...] = (
    "支撑式",      # 胸/腹有支撑,腰部无需主动稳定(如支撑式悍马俯身划船)
    "俯卧",        # 身体趴在垫上,腰部完全卸力(如俯卧 T-bar 划船)
    "仰卧",        # 仰卧位腰部自然贴垫
    "高位",        # 高位下拉/高位夹胸,重力方向不压腰椎
)


def is_safe_variant(name: str) -> bool:
    """判断动作名是否属于安全变体(白名单命中)。"""
    return any(variant in name for variant in SAFE_VARIANTS)


@dataclass(frozen=True)
class ContraindicationRule:
    """单个禁忌规则(心法层)。

    Attributes:
        part: 禁忌部位(腰/膝/肩)
        name: 规则中文名(如"髋铰链类硬拉")
        reason: 心法描述(为什么禁忌,触发康复原理)
        keywords: 命中关键字(交给 validators.py 做硬匹配)
        severity: 命中后的严重级别
            - info: 仅提示(动作可替代,看用户选择)
            - warn: 警告(动作可能加重,建议替换)
            - error: 错误(动作禁忌,必须移除)
    """
    part: str
    name: str
    reason: str
    keywords: tuple[str, ...]
    severity: Severity = "warn"


# ── 腰椎间盘突出禁忌(用户当前已声明) ──
LUMBAR_RULES: tuple[ContraindicationRule, ...] = (
    ContraindicationRule(
        part="腰",
        name="髋铰链轴向压力",
        reason="硬拉/罗马尼亚硬拉/早安式弯腰会让腰椎承受巨大轴向压力,突出节段受挤压加重",
        keywords=("硬拉", "罗马尼亚", "早安", "good morning", "臀桥"),
        severity="error",
    ),
    ContraindicationRule(
        part="腰",
        name="俯身/弯腰划船类",
        reason="俯身角度超过 45° 时腰部竖脊肌持续等长收缩 + 腰椎剪切力,T-bar 划船最危险",
        keywords=("俯身", "t-bar", "tbar", "t bar", "杠铃划船"),
        severity="warn",
    ),
    ContraindicationRule(
        part="腰",
        name="腿举/倒蹬类",
        reason="倒蹬器械在膝屈曲 + 髋屈曲时腰椎屈曲代偿,突出节段受压(用户已主动删除器械倒蹬)",
        keywords=("倒蹬", "腿举", "smith 机深蹲"),
        severity="error",
    ),
    ContraindicationRule(
        part="腰",
        name="坐姿腿弯举",
        reason="腘绳肌在屈膝时收缩牵拉坐骨结节,导致骨盆前倾 + 腰椎屈曲,加重突出",
        keywords=("腿弯举", "坐姿腿弯举", "俯卧腿弯举"),
        severity="error",
    ),
)

# ── 膝关节常见禁忌 ──
KNEE_RULES: tuple[ContraindicationRule, ...] = (
    ContraindicationRule(
        part="膝",
        name="大重量深蹲/全蹲",
        reason="超过 90° 深度 + 大重量会让髌股关节压力激增,半月板承受剪切",
        keywords=("深蹲", "全蹲", "高杠深蹲", "低杠深蹲", "前蹲"),
        severity="warn",
    ),
    ContraindicationRule(
        part="膝",
        name="跳跃/冲击类",
        reason="跳跃落地时膝关节承受 5-7 倍体重冲击,半月板/韧带风险高",
        keywords=("跳箱", "box jump", "跳跃", "冲刺跑"),
        severity="warn",
    ),
    ContraindicationRule(
        part="膝",
        name="开链伸膝大重量",
        reason="坐姿腿屈伸(开链)大重量时髌腱张力极高,易诱发髌腱炎",
        keywords=("腿屈伸", "leg extension"),
        severity="info",
    ),
)

# ── 肩袖损伤常见禁忌 ──
SHOULDER_RULES: tuple[ContraindicationRule, ...] = (
    ContraindicationRule(
        part="肩",
        name="颈后推举",
        reason="颈后推举时肩关节外旋 + 极度外展,肩峰下撞击综合征风险极高",
        keywords=("颈后推举", "颈后推", "behind neck press"),
        severity="error",
    ),
    ContraindicationRule(
        part="肩",
        name="大重量直立划船",
        reason="直立划船到顶端时肩关节内旋 + 外展,肩峰撞击 + 肩袖肌群挤压",
        keywords=("直立划船", "upright row"),
        severity="warn",
    ),
    ContraindicationRule(
        part="肩",
        name="过头推举大重量",
        reason="过头推举超过头部时肱骨大结节与肩峰撞击,肩袖肌群受压",
        keywords=("过头推举", "overhead press", "推举过头"),
        severity="warn",
    ),
    ContraindicationRule(
        part="肩",
        name="大幅度侧平举",
        reason="侧平举超过 90° 时肩峰下空间消失,冈上肌撞击",
        keywords=("侧平举", "lateral raise"),
        severity="info",
    ),
)

ALL_RULES: dict[str, tuple[ContraindicationRule, ...]] = {
    "腰": LUMBAR_RULES,
    "膝": KNEE_RULES,
    "肩": SHOULDER_RULES,
}


def rules_for(part: str) -> tuple[ContraindicationRule, ...]:
    """取某部位的禁忌规则。part ∈ {"腰", "膝", "肩", "all"}"""
    if part == "all":
        result: list[ContraindicationRule] = []
        for rules in ALL_RULES.values():
            result.extend(rules)
        return tuple(result)
    return ALL_RULES.get(part, ())