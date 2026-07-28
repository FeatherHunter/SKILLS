"""规则层 · validators.py（§02 第 ③ 层）

集中持有所有硬规则：
- 分类白名单（10 支出 L1 + 5 收入 L1，支持 L1/L2/L3 多级）
- 金额校验：非零 + 有限数（NaN / Inf 拒绝）
- 时间格式：YYYY-MM-DD HH:MM:SS
- 字段类型 / 默认值

错误信息含「字段名 + 当前值 + 期望值 + 怎么修」四要素。

导出纯函数：
- validate_amount(amount) -> float
- validate_category(category) -> str
- validate_time(time_str) -> str
- validate_record(record: dict) -> dict
- ValidationError
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any


class ValidationError(ValueError):
    """规则校验失败。message 含「字段名 + 当前值 + 期望值 + 怎么修」四要素。"""


# ── 白名单（与 references/categories.md 同步）────────────────────────────────

# 支出 L1（10 个，来自 categories.md §一）
EXPENSE_L1 = frozenset({
    "餐饮", "居家", "穿着", "出行", "玩乐",
    "学习", "健康", "社交", "宠物", "其他",
})

# 收入 L1（5 个，来自 categories.md §二）
INCOME_L1 = frozenset({
    "工资", "奖金", "兼职", "投资", "其他收入",
})

ALL_L1 = EXPENSE_L1 | INCOME_L1

# 字段默认值（与 db.py insert_record 默认值保持一致）
DEFAULTS = {
    "account": "",
    "ledger": "生活",
    "currency": "人民币",
    "note": "",
}

# 合法货币（与 spec Implementation Decision #4 CHECK (currency IN ('CNY', '人民币')) 对齐）
ALLOWED_CURRENCIES = frozenset({"人民币", "CNY"})

# 时间格式 YYYY-MM-DD HH:MM:SS
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


# ── 校验函数 ─────────────────────────────────────────────────────────────────

def validate_amount(amount: Any) -> float:
    """金额校验：非零 + 有限数。

    Args:
        amount: 用户传入的金额值（int/float；负=支出，正=收入）

    Returns:
        float — 校验通过的金额（保留符号）

    Raises:
        ValidationError — 含四要素错误信息
    """
    if amount is None:
        raise ValidationError(
            f"字段「amount/金额」当前值=None，期望=有限浮点数（非零），"
            f"建议=传入数字金额（支出为负，收入为正，例如 -35.0 或 8000.0）"
        )
    try:
        a = float(amount)
    except (TypeError, ValueError):
        raise ValidationError(
            f"字段「amount/金额」当前值={amount!r}，期望=有限浮点数（非零），"
            f"建议=传入数字金额（例如 -35.0 或 8000.0），不能是字符串"
        )

    if math.isnan(a):
        raise ValidationError(
            f"字段「amount/金额」当前值=NaN，期望=有限浮点数（非零），"
            f"建议=NaN 不是合法金额，请改传入有效数字（如 -35.0）"
        )
    if math.isinf(a):
        raise ValidationError(
            f"字段「amount/金额」当前值=Inf，期望=有限浮点数（非零），"
            f"建议=Inf 不是合法金额，请改传入有效数字（如 -35.0）"
        )
    if a == 0.0:
        raise ValidationError(
            f"字段「amount/金额」当前值=0，期望=非零（amount != 0），"
            f"建议=金额必须非零（支出用负数如 -35.0，收入用正数如 8000.0）；"
            f"若是对冲/退款场景，请改用修改记录或调整账本而非录入 0 元"
        )
    return a


def validate_category(category: Any) -> str:
    """分类校验：L1 在白名单，支持多级 L1/L2/L3（用 / 分隔）。

    Args:
        category: 用户传入的分类字符串，如 "餐饮/外卖/午餐"

    Returns:
        str — 校验通过的原始分类字符串

    Raises:
        ValidationError — 含四要素错误信息
    """
    if category is None or not isinstance(category, str) or category.strip() == "":
        raise ValidationError(
            f"字段「category/分类」当前值={category!r}，期望=非空字符串且 L1 在白名单，"
            f"建议=传入分类（如 '餐饮' 或 '餐饮/外卖/午餐'），"
            f"合法 L1 有：{sorted(ALL_L1)}"
        )

    # L1 = 第一个 / 之前的部分
    l1 = category.split("/", 1)[0].strip()
    if l1 not in ALL_L1:
        raise ValidationError(
            f"字段「category/分类」当前值={category!r}（L1='{l1}'），"
            f"期望=L1 在白名单内（餐饮/居家/穿着/出行/玩乐/学习/健康/社交/宠物/其他/"
            f"工资/奖金/兼职/投资/其他收入），"
            f"建议=把 L1 改为上述合法值之一，或在前面加上正确的 L1（如 '出行/网约车'）"
        )

    return category


def validate_time(time_str: Any) -> str:
    """时间校验：格式 YYYY-MM-DD HH:MM:SS。

    Args:
        time_str: 用户传入的时间字符串

    Returns:
        str — 校验通过的时间字符串

    Raises:
        ValidationError — 含四要素错误信息
    """
    if time_str is None or not isinstance(time_str, str):
        raise ValidationError(
            f"字段「time/时间」当前值={time_str!r}，期望=字符串 YYYY-MM-DD HH:MM:SS，"
            f"建议=传入格式化时间，例如 '2026-07-28 12:00:00'"
        )
    if not _TIME_RE.match(time_str):
        raise ValidationError(
            f"字段「time/时间」当前值={time_str!r}，期望=YYYY-MM-DD HH:MM:SS，"
            f"建议=改用正确格式，例如 '2026-07-28 12:00:00'（注意用 '-' 而非 '/'，"
            f"且包含时:分:秒）"
        )
    # 进一步用 datetime 解析确认是合法日期（如月份不能是 13）
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        raise ValidationError(
            f"字段「time/时间」当前值={time_str!r}，期望=有效日期时间，"
            f"建议=检查日期是否合法（如月份 1-12，日期 1-31）：{e}"
        )
    return time_str


def validate_record(record: dict) -> dict:
    """综合校验：amount + category + time 三必填 + 可选字段类型 + 默认值填充。

    Args:
        record: 含 category / amount / time 必填字段 + account/ledger/currency/note 可选字段的 dict

    Returns:
        dict — 校验通过、填好默认值的记录（新 dict，不改入参）

    Raises:
        ValidationError — 第一项失败的字段（含四要素错误信息）
    """
    if not isinstance(record, dict):
        raise ValidationError(
            f"字段「record」当前值={type(record).__name__}，期望=dict，"
            f"建议=传入字典形式的记录"
        )

    # 不修改入参
    out = dict(record)

    # 必填字段校验
    if "category" not in out:
        raise ValidationError(
            f"字段「category/分类」当前值=缺失，期望=非空字符串且 L1 在白名单，"
            f"建议=补上 category 字段（如 '餐饮/外卖/午餐'）"
        )
    out["category"] = validate_category(out["category"])

    if "amount" not in out:
        raise ValidationError(
            f"字段「amount/金额」当前值=缺失，期望=有限浮点数（非零），"
            f"建议=补上 amount 字段（支出用负数如 -35.0，收入用正数如 8000.0）"
        )
    out["amount"] = validate_amount(out["amount"])

    if "time" not in out:
        raise ValidationError(
            f"字段「time/时间」当前值=缺失，期望=YYYY-MM-DD HH:MM:SS，"
            f"建议=补上 time 字段（如 '2026-07-28 12:00:00'）"
        )
    out["time"] = validate_time(out["time"])

    # 可选字段：填默认值 + 简单类型检查
    for k, default in DEFAULTS.items():
        v = out.get(k, default)
        if v is None:
            v = default
        if not isinstance(v, str):
            raise ValidationError(
                f"字段「{k}」当前值={v!r}（类型={type(v).__name__}），期望=字符串，"
                f"建议=传入字符串值或省略以使用默认值 {default!r}"
            )
        out[k] = v

    # currency 必须在合法集合内
    if out["currency"] not in ALLOWED_CURRENCIES:
        raise ValidationError(
            f"字段「currency/货币」当前值={out['currency']!r}，"
            f"期望=在白名单内（人民币/CNY），"
            f"建议=改为 '人民币' 或 'CNY'"
        )

    return out


__all__ = [
    "ValidationError",
    "validate_amount",
    "validate_category",
    "validate_time",
    "validate_record",
    "EXPENSE_L1",
    "INCOME_L1",
    "ALL_L1",
    "ALLOWED_CURRENCIES",
    "DEFAULTS",
]
