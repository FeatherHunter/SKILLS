#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scan_contraindications.py — 卡路里禁忌动作检测 CLI

对应 SKILL.md 唤醒词:`扫禁忌`

5 层架构位置:② 契约层(CLI 入口)
业务逻辑在 contraindications/ 子包(③ 业务层)

设计原则(优秀 Skill 指导手册):
- argparse schema 文档化(每个参数 + 默认值 + 取值范围)
- 输出统一 {status, data, message} 三段式 JSON
- 错误信息带字段名 + 当前值 + 期望值 + 怎么修
- --strict 控制退出码(普通用户跑 0,有禁忌仍为 warn;CI/严肃场景非 0)

用法:
    python scan_contraindications.py                         # 扫全部位(腰+膝+肩)
    python scan_contraindications.py --part 腰                # 只扫腰
    python scan_contraindications.py --part 膝 --part 肩      # 扫多个
    python scan_contraindications.py --strict                 # 有 warn/error 就退出码非 0
    python scan_contraindications.py --format table           # 表格输出(更适合人读)
    python scan_contraindications.py --format json            # 纯 JSON(机器友好,默认)
    python scan_contraindications.py --db <path>              # 自定义 DB

退出码:
    0  无禁忌 / 仅 info
    1  有 warn(警告)
    2  有 error(必须处理)
    3  参数错(DB 不存在等)
"""
import argparse
import json
import sys
from pathlib import Path

# 让脚本能直接 import contraindications 包
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from contraindications import scan_plan  # noqa: E402


# ── 退出码常量(优秀手册:让退出码自带语义) ──
EXIT_OK = 0
EXIT_WARN = 1
EXIT_ERROR = 2
EXIT_USAGE = 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scan_contraindications",
        description="卡路里禁忌动作检测(腰/膝/肩)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--part", action="append", choices=["腰", "膝", "肩", "all"],
        default=None,
        help="扫描哪些部位(可多次传)。默认 all=全扫。例:--part 腰 --part 膝",
    )
    p.add_argument(
        "--db",
        default=r"D:\2Study\StudyNotes\.db\calorie_data.db",
        help="SQLite DB 路径(默认 D:/2Study/StudyNotes/.db/calorie_data.db)",
    )
    p.add_argument(
        "--format", choices=["json", "table"], default="json",
        help="输出格式:json(机器可读,默认)/ table(人友好)",
    )
    p.add_argument(
        "--strict", action="store_true",
        help="严格模式:有 warn/error 时退出码非 0(默认 warn 不阻塞)",
    )
    return p


def render_table(data: dict) -> str:
    """表格输出,人眼友好。"""
    if not data["hits"]:
        return "✅ 未发现禁忌动作"

    lines = []
    lines.append(f"⚠ 扫描 {data['scanned_sessions']} sessions / "
                 f"{data['scanned_movements']} movements,找到 "
                 f"{len(data['hits'])} 条禁忌\n")
    # 按严重度分组
    sev_emoji = {"error": "🔴", "warn": "🟡", "info": "🔵"}
    for sev in ("error", "warn", "info"):
        items = [(name, info) for name, info in data["by_movement"].items()
                 if info["severity"] == sev]
        if not items:
            continue
        lines.append(f"\n{sev_emoji[sev]} {sev.upper()} ({len(items)} 个动作):")
        for name, info in items:
            safe_tag = "  [✅ 安全变体]" if info.get("safe_variant") else ""
            lines.append(f"  · {name}{safe_tag}  (命中 {info['count']} 次)")
            lines.append(f"    规则: {', '.join(info['rules'])}")
            lines.append(f"    部位: {', '.join(info['parts'])}")
            if info.get("reason"):
                lines.append(f"    理由: {info['reason']}")
            lines.append(f"    使用: {', '.join(info['used_in'][:3])}"
                         + (f" ... +{len(info['used_in'])-3} more" if len(info['used_in']) > 3 else ""))
    return "\n".join(lines)


def _hit_to_dict(h) -> dict:
    """dataclass Hit → dict(JSON 序列化)"""
    return {
        "movement_name": h.movement_name,
        "part": h.part,
        "rule_name": h.rule_name,
        "severity": h.severity,
        "reason": h.reason,
        "used_in": list(h.used_in),
        "safe_variant": h.safe_variant,
    }


def _by_movement_with_reason(data: dict) -> dict:
    """在 by_movement 聚合里补 reason(取第一条 hit 的 reason 作为代表)"""
    reason_map = {}
    safe_set = set()
    for h in data.get("hits", []):
        if h.movement_name not in reason_map:
            reason_map[h.movement_name] = h.reason
        if h.safe_variant:
            safe_set.add(h.movement_name)
    enriched = {}
    for name, info in data["by_movement"].items():
        new_info = dict(info)
        new_info["reason"] = reason_map.get(name, "")
        new_info["safe_variant"] = name in safe_set
        enriched[name] = new_info
    return enriched


def render_output(args: argparse.Namespace, data: dict) -> str:
    if args.format == "table":
        return render_table(data)
    # json(默认):转 dataclass Hit 为 dict,统一 {status, data, message} 三段式
    by_severity = data["by_severity"]
    if by_severity["error"] > 0:
        status = "fail"
        message = (f"发现 {by_severity['error']} 条 error 级禁忌动作,"
                   f"必须移除或替换")
    elif by_severity["warn"] > 0:
        status = "warn"
        message = (f"发现 {by_severity['warn']} 条 warn 级禁忌,"
                   f"建议替换为更安全的变体")
    elif by_severity["info"] > 0:
        status = "ok"
        message = f"未发现禁忌,但有 {by_severity['info']} 条 info 提示"
    else:
        status = "ok"
        message = "✅ 未发现禁忌动作"

    payload = {
        "status": status,
        "data": {
            "scanned_sessions": data["scanned_sessions"],
            "scanned_movements": data["scanned_movements"],
            "scanned_parts": data.get("scanned_parts", ["腰", "膝", "肩"]),
            "safe_skipped": data.get("safe_skipped", 0),
            "by_severity": by_severity,
            "by_movement": _by_movement_with_reason(data),
            "hits": [_hit_to_dict(h) for h in data["hits"]],
            "hit_count": len(data["hits"]),
            "summary_status": status,
        },
        "message": message,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 处理 part 参数
    parts = args.part if args.part else ["all"]

    try:
        # 一次扫描,合并多部位结果
        merged: dict = {
            "scanned_sessions": 0,
            "scanned_movements": 0,
            "safe_skipped": 0,
            "hits": [],
            "by_movement": {},
            "by_severity": {"error": 0, "warn": 0, "info": 0},
            "summary_status": "ok",
            "scanned_parts": [],
        }
        for part in parts:
            r = scan_plan(part=part, db=args.db)  # type: ignore[arg-type]
            merged["scanned_sessions"] = r["scanned_sessions"]
            merged["scanned_movements"] = r["scanned_movements"]
            merged["safe_skipped"] += r.get("safe_skipped", 0)
            # 2026-07-23 A1 增:记录实际扫描了哪些部位
            if part == "all":
                for p in ("腰", "膝", "肩"):
                    if p not in merged["scanned_parts"]:
                        merged["scanned_parts"].append(p)
            elif part not in merged["scanned_parts"]:
                merged["scanned_parts"].append(part)
            merged["hits"].extend(r["hits"])
            # 合并 by_movement:同名动作的 hits 聚合
            for name, info in r["by_movement"].items():
                if name in merged["by_movement"]:
                    old = merged["by_movement"][name]
                    old["count"] += info["count"]
                    old["rules"] = sorted(set(old["rules"]) | set(info["rules"]))
                    old["used_in"] = sorted(set(old["used_in"]) | set(info["used_in"]))
                    old["parts"] = sorted(set(old["parts"]) | set(info["parts"]))
                else:
                    merged["by_movement"][name] = info
            for sev, n in r["by_severity"].items():
                merged["by_severity"][sev] += n

        print(render_output(args, merged))
    except FileNotFoundError as e:
        # 错误信息带字段名 + 当前值 + 期望值 + 怎么修(优秀手册)
        print(json.dumps({
            "status": "fail",
            "data": None,
            "message": (
                f"DB 路径不存在: --db 当前值={args.db}\n"
                f"解决:1) 确认 .db 目录存在,或 2) --db <正确的路径>"
            ),
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return EXIT_USAGE
    except Exception as e:
        print(json.dumps({
            "status": "fail",
            "data": {"error_type": type(e).__name__},
            "message": f"扫禁忌异常: {e}",
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return EXIT_USAGE

    # 退出码
    sev = merged["by_severity"]
    if sev["error"] > 0:
        return EXIT_ERROR
    if args.strict and sev["warn"] > 0:
        return EXIT_WARN
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())