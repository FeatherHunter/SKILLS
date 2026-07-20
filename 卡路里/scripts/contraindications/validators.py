"""contraindications.validators — 硬规则层(无跳过通道)

负责"实际匹配":从动作名称 → 命中哪条禁忌 → 输出严重级别。
所有匹配规则都在这里集中,不允许在别处再做关键字判断。

设计原则(优秀 Skill 指导手册):
- 硬规则集中在一处,无绕过通道
- 严重级别一旦确定,不可降级
- 中文/英文关键字都支持(name 是中文,keywords 也覆盖英文)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from .soft_rules import ContraindicationRule, rules_for, Severity, is_safe_variant


@dataclass(frozen=True)
class Hit:
    """一条禁忌命中记录。

    Attributes:
        movement_name: 触发命中的动作名(原始)
        part: 禁忌部位(腰/膝/肩)
        rule_name: 命中的规则名(如"髋铰链轴向压力")
        severity: 严重级别
        reason: 为什么被禁忌(心法层 reason)
        used_in: 这个动作被 plan 引用的位置列表
            例如 ["W1D1(下午·协同)", "W2D3(晚上·补漏)"]
        safe_variant: True 表示这是安全变体,白名单生效(其实不需要禁忌报出)
    """
    movement_name: str
    part: str
    rule_name: str
    severity: Severity
    reason: str
    used_in: tuple[str, ...]
    safe_variant: bool = False


def _matches(name: str, keyword: str) -> bool:
    """大小写不敏感的关键字匹配。中文关键字直接用 in 即可,英文需要 .lower()"""
    name_lower = name.lower()
    keyword_lower = keyword.lower()
    return keyword_lower in name_lower


def match_one(name: str, rule: ContraindicationRule) -> bool:
    """单个规则对单个动作名:是否命中。

    命中条件:任意关键字在动作名中(子串匹配)。
    子串匹配的好处:不需要枚举所有变体(如"杠铃硬拉""罗马尼亚硬拉""六角杠硬拉")。
    """
    return any(_matches(name, kw) for kw in rule.keywords)


def scan_movement(
    name: str,
    parts: Iterable[str] = ("腰", "膝", "肩"),
) -> list[tuple[ContraindicationRule, ...]]:
    """对一个动作名,扫描所有部位的禁忌规则,返回命中规则列表。

    Returns:
        list of (per-part: tuple of matched rules)
        外层 list 长度 = parts 长度(每个部位一个 slot)
        即使该部位无命中,也返回空 tuple(保证顺序稳定)

    Example:
        >>> scan_movement("罗马尼亚硬拉")
        [(rule_axial, rule_hip_hinge), (), ()]
    """
    result = []
    for part in parts:
        rules = rules_for(part)
        matched = tuple(r for r in rules if match_one(name, r))
        result.append(matched)
    return result


def worst_severity(rules: Iterable[ContraindicationRule]) -> Severity | None:
    """取一组规则中最高的严重级别。

    级别排序: error > warn > info
    """
    if not rules:
        return None
    order = {"error": 3, "warn": 2, "info": 1}
    return max(((r.severity, order[r.severity]) for r in rules), key=lambda x: x[1])[0]


def scan_all_movements(
    movements: Iterable[dict],
    parts: Iterable[str] = ("腰", "膝", "肩"),
) -> list[Hit]:
    """扫描一组动作,返回所有命中记录(白名单命中的会标 safe_variant=True)。

    Args:
        movements: plan 的 movements 列表(从 workout_plans.movements JSON 解析)
            每项含 {'name': str, 'part': str, ...}
        parts: 要扫描的部位集合

    Returns:
        list[Hit] - 每个动作的每条命中一条 Hit
        安全变体也会出现在 hits,但 safe_variant=True,可由调用方决定是否过滤
    """
    hits: list[Hit] = []
    for m in movements:
        name = m.get("name", "")
        is_safe = is_safe_variant(name)
        for part, matched in zip(parts, scan_movement(name, parts)):
            for rule in matched:
                hits.append(Hit(
                    movement_name=name,
                    part=part,
                    rule_name=rule.name,
                    severity=rule.severity,
                    reason=rule.reason,
                    used_in=(),
                    safe_variant=is_safe,
                ))
    return hits