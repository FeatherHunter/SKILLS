# validators.py - SM1 规格校验(v2.0 定稿口径 · 与旧 validators.py 硬规则并存不冲突)
#
# SM1 录入定稿(2026-08-04):
#   必填字段: 名称+分类=必填;位置=可选
#   写库过校验: 命名规范/分类存在/位置规范
#   状态机: 已废弃 → 仅可恢复(在家/备用),其余流转一律拦截
# 旧公共层 hard rules(≥10 标签/备注非空/位置必填)为 v1.x 遗留约束,
# 本域写路径按 v2.0 规格口径;遗留口径是否退役走公共层 ISSUE(见 #106 决议)。
from typing import Any


def _coerce_tags(tags: Any) -> list[str]:
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    if isinstance(tags, str):
        return [t.strip() for t in tags.split(",") if t.strip()]
    return []


def validate_draft(draft: dict, conn=None) -> tuple[dict, list[str]]:
    """SM1 采集表单校验(预填度 0-100% 连续)

    检查项:
      has_name      名称非空(必填)
      has_category  category_id 非空且存在+激活(必填)
      location_ok   位置规范(若填: 至少两级含 '/')
      price_ok      价格是数字 ≥ 0(选填)
      date_ok       日期格式 YYYY-MM-DD(选填)
      tags_ok       标签个数 ≤ 30(防滥用,选填)
    返回 (checks, missing)
    """
    name = (draft.get("name") or "").strip()
    category_id = draft.get("category_id")
    location = (draft.get("location") or "").strip()
    price = draft.get("price")
    purchase_date = draft.get("purchase_date") or ""
    expiration_date = draft.get("expiration_date") or ""
    tags = _coerce_tags(draft.get("tags"))

    checks = {
        "has_name": bool(name),
        "has_category": _category_ok(conn, category_id),
        "location_ok": (not location) or ("/" in location.strip("/")),
        "price_ok": _price_ok(price),
        "date_ok": _dates_ok(purchase_date, expiration_date),
        "tags_ok": len(tags) <= 30,
    }
    missing = []
    if not checks["has_name"]:
        missing.append("还缺:名称")
    if not checks["has_category"]:
        missing.append("还缺:分类")
    if not checks["location_ok"]:
        missing.append("位置必须至少两级(含'/'),如 卧室/衣柜")
    if not checks["price_ok"]:
        missing.append(f"价格必须是 ≥0 的数字(当前 {price!r})")
    if not checks["date_ok"]:
        missing.append("日期必须是 YYYY-MM-DD 格式")
    if not checks["tags_ok"]:
        missing.append("标签最多 30 个")

    checks["ready_score"] = sum(
        1 for k, v in checks.items() if k != "ready_score" and v
    ) / sum(1 for k in checks if k != "ready_score")
    return checks, missing


def _category_ok(conn, category_id) -> bool:
    if category_id in (None, ""):
        return False
    try:
        category_id = int(category_id)
    except (TypeError, ValueError):
        return False
    if conn is None:
        return True
    row = conn.execute(
        "SELECT id FROM categories WHERE id = ? AND is_active = 1", (category_id,)
    ).fetchone()
    return row is not None


def _price_ok(price) -> bool:
    if price in (None, ""):
        return True
    try:
        return float(price) >= 0
    except (TypeError, ValueError):
        return False


def _dates_ok(*dates) -> bool:
    from datetime import date
    for d in dates:
        if not d:
            continue
        try:
            date.fromisoformat(str(d))
        except (TypeError, ValueError):
            return False
    return True


# ── 状态机(SM1 场景 3-4 / 6-2)───────────────────────────────────────────────

# 合法状态:沿用公共层 VALID_STATUSES + 「找不到」(丢失,D1 #12 状态机扩展预埋)
STATUSES = ["在家", "备用", "穿着中", "旅游中", "洗护中", "借用中", "维修中",
            "已用完", "快递中", "待处理", "已废弃", "找不到"]
RESTORE_FROM_DISCARDED = ["在家", "备用", "找不到"]


def check_status_transition(current: str, target: str) -> tuple[bool, str]:
    """状态机校验(非法流转拦截)

    - target 必须是合法状态
    - 已废弃 → 仅 在家/备用/找不到(恢复);其余拦截(「已废弃→维修直接拦」)
    - 找不到(丢失) → 回到 在家(找到)
    """
    if target not in STATUSES:
        return False, f"非法状态「{target}」,可选: {'/'.join(STATUSES)}"
    if current == target:
        return True, ""
    if current == "已废弃":
        if target not in RESTORE_FROM_DISCARDED:
            return False, f"已废弃物品不可流转到「{target}」(仅可恢复为 {'/'.join(RESTORE_FROM_DISCARDED)})"
        return True, ""
    if current == "找不到" and target in ("维修中", "穿着中", "借用中", "旅游中", "洗护中", "快递中", "已用完"):
        return False, f"丢失物品「{current}」需先恢复为「在家」,再流转到「{target}」"
    if target == "已废弃":
        return True, "废弃 = 软删除:默认隐藏(查找/统计/盘点不出现),历史可查,可恢复"
    return True, ""
