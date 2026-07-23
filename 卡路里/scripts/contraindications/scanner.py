"""contraindications.scanner — 编排层:读 workout_plans + 调 validators + 汇总 Hit

本模块不写 SQL(用 db.py),不做关键字判断(用 validators),
只负责"读取 + 调用 + 汇总"。

5 层架构:③ 业务层 / 编排子层
数据层(④ db.py)的接入通过 find_db_path + get_db,不直接 sqlite3.connect。
"""
from __future__ import annotations
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Literal

from db import find_db_path, connection  # 卡路里 ④ 数据层公共 API

from .soft_rules import rules_for
from .validators import Hit, scan_all_movements, worst_severity


Severity = Literal["info", "warn", "error"]
PartFilter = Literal["腰", "膝", "肩", "all"]


# 卡路里 skill 目录(用于 find_db_path)
SKILL_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_db_path(db: str | None) -> Path:
    """解析 DB 路径:
    1. --db 显式传 → 用之
    2. 否则用 db.find_db_path(SKILL_DIR, "calorie_data.db")
       (会查 SKILLS_DB_PATH 环境变量,再找 .db 目录)
    """
    if db:
        return Path(db)
    return find_db_path(SKILL_DIR, "calorie_data.db")


def _iter_plans(conn) -> list[dict]:
    """从 workout_plans 读所有 plan 行的轻量数据。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT week_number, day_of_week, session_index, session_label, "
        "movements FROM workout_plans ORDER BY week_number, day_of_week, session_index"
    )
    return [
        {
            "week_number": r[0],
            "day_of_week": r[1],
            "session_index": r[2],
            "session_label": r[3],
            "movements": json.loads(r[4] or "[]"),
        }
        for r in cur.fetchall()
    ]


def _scan_one_movement(
    movement: dict,
    week: int,
    dow: int,
    label: str,
    parts: tuple[str, ...],
) -> list[Hit]:
    """对一个动作 + 上下文,生成带 used_in 的 Hit 列表。"""
    usage = f"W{week}D{dow}({label})"
    hits = scan_all_movements([movement], parts)
    return [
        Hit(
            movement_name=h.movement_name,
            part=h.part,
            rule_name=h.rule_name,
            severity=h.severity,
            reason=h.reason,
            used_in=(usage,),
            safe_variant=h.safe_variant,
        )
        for h in hits
    ]


def scan_plan(
    part: PartFilter = "all",
    db: str | None = None,
) -> dict:
    """扫描整个 plan。

    Returns:
        {
            "scanned_sessions": N,
            "scanned_movements": M,
            "hits": [Hit(...)],
            "by_movement": {name: {"count": int, "severity": str, "rule": str, "used_in": [...]}},
            "by_severity": {"error": int, "warn": int, "info": int},
            "summary_status": "ok" | "warn" | "fail"
        }
    """
    parts: tuple[str, ...]
    if part == "all":
        parts = ("腰", "膝", "肩")
    else:
        parts = (part,)

    db_path = _resolve_db_path(db)
    if not db_path.exists():
        raise FileNotFoundError(
            f"DB 不存在:{db_path}\n"
            f"解决:确认 .db 目录存在,或用 --db 指定其他路径"
        )

    with connection(db_path) as conn:
        plans = _iter_plans(conn)

    hits: list[Hit] = []
    safe_skipped_count = 0
    movement_count = 0
    # 按动作聚合 hits
    by_movement: dict[str, list[Hit]] = defaultdict(list)

    for plan in plans:
        for m in plan["movements"]:
            movement_count += 1
            for hit in _scan_one_movement(
                m, plan["week_number"], plan["day_of_week"],
                plan["session_label"], parts,
            ):
                # 安全变体(白名单命中)只统计,不计入禁忌 hits
                if hit.safe_variant:
                    safe_skipped_count += 1
                    continue
                hits.append(hit)
                by_movement[hit.movement_name].append(hit)

    # 严重级别统计
    by_severity: dict[str, int] = {"error": 0, "warn": 0, "info": 0}
    for h in hits:
        by_severity[h.severity] = by_severity.get(h.severity, 0) + 1

    # 聚合每个动作的"最高严重级别 + 全部 rule_name + 全部 used_in"
    by_movement_summary: dict[str, dict] = {}
    for name, hit_list in by_movement.items():
        all_used_in = tuple(sorted(set(u for h in hit_list for u in h.used_in)))
        sev = worst_severity(hit_list) or "info"
        rules = sorted({h.rule_name for h in hit_list})
        by_movement_summary[name] = {
            "count": len(hit_list),
            "severity": sev,
            "rules": rules,
            "used_in": list(all_used_in),
            "parts": sorted({h.part for h in hit_list}),
        }

    # 整体状态
    if by_severity["error"] > 0:
        status = "fail"
    elif by_severity["warn"] > 0:
        status = "warn"
    else:
        status = "ok"

    # B-407 修复：自动生成"替代建议"
    # 基于 SAFE_VARIANTS 白名单 + 同一动作库的"安全变体"提示
    suggestions = []
    seen_actions = set()
    for hit in hits:
        if hit.movement_name in seen_actions or hit.safe_variant:
            continue
        seen_actions.add(hit.movement_name)
        # 找白名单里"安全变体"提示
        from contraindications.soft_rules import SAFE_VARIANTS
        sug = {
            "禁忌动作": hit.movement_name,
            "触发规则": hit.rule_name,
            "理由": hit.reason,
            "建议替换": f"用含 {'/'.join(SAFE_VARIANTS[:3])} 等关键字的安全变体",
            "已安全变体示例": [v for v in SAFE_VARIANTS][:4],
        }
        suggestions.append(sug)

    return {
        "scanned_sessions": len(plans),
        "scanned_movements": movement_count,
        "scanned_parts": list(parts),
        "safe_skipped": safe_skipped_count,
        "hits": hits,
        "by_movement": by_movement_summary,
        "by_severity": by_severity,
        "summary_status": status,
        "suggestions": suggestions,
    }