#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_decimal_precision.py — 扫描生成的 HTML,确保数字字段小数位 ≤ 2

ticket 01 · 2026-07-29 卡路里 HTML 重设计基础设施
依据:.scratch/card-html-redesign/spec.md Testing Decisions seam 4 + D5 落地守护。

触发动机:用户实测看到 `-141.6550000000002` / `2905.255` 等浮点精度泄漏(查热量趋势)。
对策:
  - 后端 render 脚本序列化前 round(2)
  - 后端防御性巡检:扫描已生成的 HTML,parse window.__DATA__ JSON,逐字段检查小数位

检查范围:
  - 路径: <SKILL_DIR>/calorie_html/*.html
  - 提取: `<script>window.__DATA__ = {...}</script>`(若 status=ok 才检查)
  - 字段白名单(可扩展):
    summary.trend_value / start_avg / end_avg / weekday_avg / weekend_avg / avg / total_calorie / avg_calorie
    series[*].calorie / items[*].calorie
  - 规则:数字字段 round(2) 后必须 == 自身(差 ≤ 1e-9),否则 fail

退出码:
  0 = pass
  1 = 发现精度泄漏

用法:
    python scripts/check_decimal_precision.py [--mock <html>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def _resolve_html_dir() -> Path:
    """优先 $SKILLS_DB_PATH/calorie_html(手册 §4.1 · v2.4.8 设计),fallback SKILL_DIR/calorie_html/"""
    import os
    sdb = os.environ.get('SKILLS_DB_PATH')
    if sdb:
        cand = Path(sdb) / 'calorie_html'
        if cand.exists():
            return cand
    return SKILL_DIR / 'calorie_html'


HTML_DIR = _resolve_html_dir()

# 字段白名单:dotted path → 列表中每个 item 的 sub-key(可选)
PRECISION_FIELDS: list[tuple[str, str | None]] = [
    ("summary.trend_value",        None),
    ("summary.start_avg",          None),
    ("summary.end_avg",            None),
    ("summary.weekday_avg",        None),
    ("summary.weekend_avg",        None),
    ("summary.avg",                None),
    ("summary.avg_calorie",        None),
    ("summary.total_calorie",      None),
    ("summary.kg_equivalent",      None),
    ("series",                     "calorie"),
    ("items",                      "calorie"),
    ("series",                     "total_cal"),
    ("items",                      "total_cal"),
    ("meals",                      "calorie"),
    ("meals",                      "carb"),
    ("meals",                      "protein"),
    ("meals",                      "fat"),
]

# data shape 顶层可能存在的容器 key 集合(白名单外但作为 list 容器)
LIST_CONTAINER_KEYS = {"series", "items", "meals", "recent_logs"}


def _extract_data_payload(html_text: str) -> dict | None:
    """从 HTML 抽取 window.__DATA__ = {...};脚本内容转义 </"""
    m = re.search(
        r'<script>\s*window\.__DATA__\s*=\s*(\{.*?\});?\s*</script>',
        html_text, re.DOTALL,
    )
    if not m:
        return None
    # 反转义 </(render 脚本注入时替换)
    raw = m.group(1).replace('<\\/', '</')
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"⚠ JSON parse fail: {e}", file=sys.stderr)
        return None


def _check_path(payload: dict, path: str, sub_key: str | None) -> list[float]:
    """检查单字段,返回 越界值 列表(空 = pass)"""
    out: list[float] = []
    parts = path.split('.')
    cur = payload
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return []
        cur = cur[p]
    if isinstance(cur, list):
        for item in cur:
            if isinstance(item, dict) and (sub_key is None or sub_key in item):
                v = item.get(sub_key) if sub_key else item
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if abs(v - round(v, 2)) > 1e-9:
                        out.append(float(v))
    elif isinstance(cur, (int, float)) and not isinstance(cur, bool):
        if abs(cur - round(cur, 2)) > 1e-9:
            out.append(float(cur))
    return out


def _check_file(html_path: Path) -> tuple[int, list[str]]:
    """扫描单个 HTML 文件,返回 (issue_count, issue_msgs)"""
    text = html_path.read_text(encoding="utf-8")
    payload = _extract_data_payload(text)
    if payload is None:
        return 0, []  # 跳过:未找到 __DATA__ 注入(不是我们生成的)
    if payload.get("status") != "ok":
        return 0, []  # 跳过:render 失败 fallback 不检查

    issues: list[str] = []
    n = 0
    data = payload.get("data", payload)
    for path, sub_key in PRECISION_FIELDS:
        leaks = _check_path(data, path, sub_key)
        if leaks:
            sample = leaks[0]
            more = f" (+{len(leaks) - 1} 处)" if len(leaks) > 1 else ""
            issues.append(
                f"  {path}{('.' + sub_key) if sub_key else ''}: "
                f"{sample!r} 小数 > 2 位{more}"
            )
            n += len(leaks)
    return n, issues


def main() -> int:
    p = argparse.ArgumentParser(description="扫描生成的 HTML,检查小数精度")
    p.add_argument("--mock", help="指定单个 HTML 文件(调试用)")
    args = p.parse_args()

    if args.mock:
        files = [Path(args.mock)]
    elif not HTML_DIR.exists():
        print(f"⚠ HTML_DIR 不存在: {HTML_DIR}(暂无可扫描文件,skip)")
        return 0
    else:
        files = sorted(HTML_DIR.glob("*.html"))

    if not files:
        print(f"ℹ {HTML_DIR} 下无 *.html(skip)")
        return 0

    total_issues = 0
    scanned = 0
    for f in files:
        scanned += 1
        n, issues = _check_file(f)
        if issues:
            total_issues += n
            print(f"❌ {f.name}: {n} 处精度泄漏")
            for line in issues:
                print(line)

    if total_issues:
        print(f"\n❌ 共 {total_issues} 处精度泄漏({scanned} 文件)")
        return 1
    print(f"✅ 扫描 {scanned} 个 HTML 文件,数字字段精度 ≤ 2 位 pass")
    return 0


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    sys.exit(main())