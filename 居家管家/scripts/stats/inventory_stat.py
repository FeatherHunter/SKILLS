# inventory_stat.py - SM4-4 盘点统计(stats_inventory · 盘点统计)
#
# 数据基础: inventory_records(D1 新表 #2,物理建表归 D1 批)。
# 本域按 D1 约定结构查询:id/scope/occurred_at/缺N/多N/异N/status;
# 表不存在 → 优雅空态(has_data=False) + 引导首次盘点(→ 6-1 盘点核对)。
# D1 建表后本模块自动生效,无需改动。

import sqlite3
from datetime import date, datetime, timedelta

from . import build_meta

# D1 约定结构(与 D1 总账 #103 一致,查询契约)
D1_TABLE = "inventory_records"
D1_FIELDS = ("id", "scope", "occurred_at", "缺N", "多N", "异N", "status")


def _today():
    return date.today()


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:19], "%Y-%m-%d %H:%M:%S").date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def _table_exists(conn, name):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cursor.fetchone() is not None


def _query_records(conn):
    """按 D1 结构查盘点记录;表不存在返回 None"""
    if not _table_exists(conn, D1_TABLE):
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"SELECT {', '.join(D1_FIELDS)} FROM {D1_TABLE} "
            f"ORDER BY occurred_at DESC")
        return [dict(r) for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        return None


def inventory_stat_payload(conn):
    """盘点统计 payload(data 部分)"""
    records = _query_records(conn)
    has_data = records is not None and len(records) > 0
    today = _today()

    if not has_data:
        return {
            "summary": {
                "title": "盘点统计",
                "subtitle": "还没有盘点记录 · 完成首次盘点后这里会显示差异趋势",
                "metrics": [
                    {"label": "盘点次数", "value": "0 次"},
                    {"label": "距上次盘点", "value": "-"},
                    {"label": "差异遗留", "value": "0 件"},
                ],
            },
            "meta": build_meta(
                "stats_inventory", "盘点统计", "盘点统计",
                render_cmd="python scripts/home_manager.py stats --type inventory-stat",
                chain="意图:盘点统计 → inventory_records(D1 表,暂无数据) → 引导首次盘点",
                source="inventory_records",
            ),
            "has_data": False,
            "records": [],
            "suggestion": "还没有盘点记录,建议先完成首次盘点(→ 盘点核对)",
            "review_action": {
                "label": "去盘点核对",
                "prompt": "请加载「居家管家」技能,帮我盘点核对(唤醒词:盘点):\n  范围(全屋/某个位置/某个分类,选填): ______",
            },
        }

    records = [dict(r) for r in records]
    last_occurred = _parse_dt(records[0].get("occurred_at"))
    days_since = (today - last_occurred).days if last_occurred else None

    total_missing = sum(int(r.get("缺N") or 0) for r in records)
    total_diff = sum(
        int(r.get("缺N") or 0) + int(r.get("多N") or 0) + int(r.get("异N") or 0)
        for r in records
    )

    # 建议优先盘点 X: 距上次盘点最久的 scope(按 scope 聚合取最早 occurred_at)
    by_scope = {}
    for r in records:
        scope = r.get("scope") or "(未命名范围)"
        when = _parse_dt(r.get("occurred_at"))
        if scope not in by_scope or (when and (by_scope[scope] is None or when < by_scope[scope])):
            by_scope[scope] = when
    oldest_scope = None
    oldest_days = -1
    for scope, when in by_scope.items():
        if when is None:
            continue
        d = (today - when).days
        if d > oldest_days:
            oldest_days = d
            oldest_scope = scope
    if oldest_scope:
        suggestion = f"「{oldest_scope}」已 {oldest_days} 天没盘,建议优先盘点"
    else:
        suggestion = "有盘点记录,建议挑最久未盘的范围复查"

    history = [
        {
            "occurred_at": (r.get("occurred_at") or "")[:19],
            "scope": r.get("scope") or "(未命名范围)",
            "missing": int(r.get("缺N") or 0),
            "extra": int(r.get("多N") or 0),
            "diff": int(r.get("异N") or 0),
            "status": r.get("status") or "",
        }
        for r in records
    ]

    return {
        "summary": {
            "title": "盘点统计",
            "subtitle": "盘过没有 · 差异趋势 · 下次盘哪",
            "metrics": [
                {"label": "盘点次数", "value": f"{len(records)} 次"},
                {"label": "距上次盘点", "value": f"{days_since} 天" if days_since is not None else "-"},
                {"label": "差异遗留", "value": f"{total_diff} 件"},
            ],
        },
        "meta": build_meta(
            "stats_inventory", "盘点统计", "盘点统计",
            render_cmd="python scripts/home_manager.py stats --type inventory-stat",
            chain="意图:盘点统计 → inventory_records 聚合 → 建议优先盘点范围",
            source="inventory_records",
        ),
        "has_data": True,
        "records": records,
        "history": history,
        "total_missing": total_missing,
        "suggestion": suggestion,
        "review_action": {
            "label": "复查盘点",
            "prompt": "请加载「居家管家」技能,帮我盘点核对(唤醒词:盘点):\n  范围(全屋/某个位置/某个分类,选填): ______",
        },
    }
