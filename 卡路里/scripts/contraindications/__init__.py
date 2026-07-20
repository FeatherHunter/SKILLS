"""contraindications — 卡路里禁忌动作检测包

5 层架构位置:③ 业务层
  ├── soft_rules.py    心法(为什么这个动作禁忌)
  ├── validators.py    硬规则(关键字匹配 + 严重级别判定)
  └── scanner.py       编排(读 DB + 调 validators + 汇总)

公开 API:
    from contraindications import scan_plan
    result = scan_plan(part="腰")
"""
from .scanner import scan_plan
from .soft_rules import (
    ContraindicationRule,
    LUMBAR_RULES,
    KNEE_RULES,
    SHOULDER_RULES,
    ALL_RULES,
    rules_for,
)
from .validators import Hit, match_one, scan_movement, worst_severity

__all__ = [
    "scan_plan",
    "ContraindicationRule",
    "LUMBAR_RULES",
    "KNEE_RULES",
    "SHOULDER_RULES",
    "ALL_RULES",
    "rules_for",
    "Hit",
    "match_one",
    "scan_movement",
    "worst_severity",
]