#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_plan_names.py — 扫描卡路里 plan 里非训记官方动作名

对应 SKILL.md 场景:训练计划 push-plan 前 / v14.x 计划改完后必跑,
发现"训记 App 找不到匹配"的动作名,提示换名。

为什么需要:
  2026-07-20 教训:v14.4 计划里写了 "坐姿推举",训记动作库无此动作名,
  App 显示灰色,模板无法复用。verify 一次才发现。

对应 SKILL.md 触发词:(无,内部工具,改 plan 后自己跑)

设计(②契约层):
  - 输出统一 {status, data, message} 三段式 JSON
  - 默认 exit 0(只看报告); --strict 时 exit 1(有不匹配时报错,适合 CI)

Usage:
    python audit_plan_names.py                         # 扫默认 DB
    python audit_plan_names.py --db D:/path/calorie_data.db
    python audit_plan_names.py --strict                # CI 模式,有错即非 0
    python audit_plan_names.py --fix-suggestions      # 模式 2:给出候选名
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from db import find_db_path, connection  # noqa: E402
from xunji_bridge.catalog import load_catalog  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent


def collect_plan_names(conn) -> list[str]:
    """读 workout_plans 里所有唯一动作名。"""
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT json_extract(json_each.value,'$.name') AS name "
        "FROM workout_plans, json_each(workout_plans.movements) "
        "WHERE json_extract(json_each.value,'$.name') IS NOT NULL"
    )
    return [r[0] for r in cur.fetchall()]


def suggest_similar(name: str, catalog: set[str], max_n: int = 5) -> list[str]:
    """简陋的相似度匹配:含相同 2 字及以上子串。"""
    matches = []
    for c in catalog:
        # 取动作名的"关键字"做交集(子串 + 空格分词)
        keys = set()
        for tok in name.replace('-', ' ').split():
            if len(tok) >= 2:
                keys.add(tok)
        for tk in keys:
            if tk in c:
                matches.append(c)
                break
    return sorted(matches)[:max_n]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="扫描卡路里 plan 里非训记官方动作名",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--db", default=None,
        help="SQLite DB 路径(默认走 db.find_db_path(SKILL_DIR, calorie_data.db))",
    )
    p.add_argument(
        "--strict", action="store_true",
        help="严格模式:有不匹配的动作名时退出码非 0(适合 CI)",
    )
    p.add_argument(
        "--fix-suggestions", action="store_true",
        help="为不匹配的动作名给出候选(用于改 plan 时参考)",
    )
    args = p.parse_args(argv)

    db_path = Path(args.db) if args.db else find_db_path(SKILL_DIR, "calorie_data.db")
    if not db_path.exists():
        print(json.dumps({
            "status": "fail",
            "data": None,
            "message": f"DB 不存在: {db_path}",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    try:
        catalog = load_catalog()
    except Exception as e:
        print(json.dumps({
            "status": "fail",
            "data": {"error_type": type(e).__name__},
            "message": f"训记动作库加载失败: {e}",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    with connection(db_path) as conn:
        plan_names = collect_plan_names(conn)

    in_cat = sorted([n for n in plan_names if n in catalog])
    not_in_cat = sorted([n for n in plan_names if n not in catalog])

    if not_in_cat:
        status = "warn"
        message = f"⚠ {len(not_in_cat)} 个动作名不在训记官方库,训记 App 无法匹配"
    else:
        status = "ok"
        message = f"✅ 所有 {len(plan_names)} 个动作名都已对齐训记动作库"

    data = {
        "total_unique_movements": len(plan_names),
        "in_catalog": len(in_cat),
        "not_in_catalog": len(not_in_cat),
        "missing": [],
    }

    if args.fix_suggestions and not_in_cat:
        for n in not_in_cat:
            suggestions = suggest_similar(n, catalog)
            data["missing"].append({
                "current_name": n,
                "suggestions": suggestions,
            })
    elif not_in_cat:
        data["missing"] = [{"current_name": n, "suggestions": []} for n in not_in_cat]

    payload = {
        "status": status,
        "data": data,
        "message": message,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not_in_cat and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())