#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_volatility_v2.py — 体重波动 v2 渲染 CLI

ticket 05 · Q8 v2 spec 落地

CLI:
    python scripts/render_weight_volatility_v2.py [--start YYYY-MM-DD] [--end YYYY-MM-DD] \
        [--baseline rolling|goal] [--text] [--output PATH]

默认: --start = 30 天前, --end = 今天, --baseline = rolling, --text = False
输出: HTML 模板 + window.__DATA__ 注入(默认) | 纯文本(--text)

路径:calorie_html/查体重波动_v2_<YYYYMMDD>_<HHMMSS>.html(同秒冲突自动 _2/_3 后缀)
stdout:⚠️ ACTION=SEND_TO_USER | HTML=<绝对路径>(HTML 模式)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

TEMPLATE_PATH = SKILL_DIR / "templates" / "weight_volatility_v2.html"


def _default_output_path() -> Path:
    """calorie_html/查体重波动_v2_<TS>.html(同秒冲突自动 _2/_3 后缀,spec §Output)"""
    skills_db = os.environ.get("SKILLS_DB_PATH")
    if skills_db:
        base = Path(skills_db) / "calorie_html"
    else:
        # fallback:与 calorie_data.db 同级
        # weight.py find_db_path 在 SKILLS_DB_PATH 未设时用 D:\.db
        base = Path("D:/2Study/StudyNotes/.db/calorie_html")
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"\u67e5\u4f53\u91cd\u6ce2\u52a8_v2_{ts}.html"
    out = base / base_name
    suffix = 2
    while out.exists():
        out = base / f"\u67e5\u4f53\u91cd\u6ce2\u52a8_v2_{ts}_{suffix}.html"
        suffix += 1
    return out


def _inject_data(html: str, data: dict) -> str:
    """window.__DATA__ = <json> 注入,唯一占位符(若多个占位符 → ValueError)"""
    count = html.count("<!--INJECT-DATA-->")
    if count != 1:
        raise ValueError(
            f"\u6a21\u677f\u5360\u4f4d\u7b26 <!--INJECT-DATA--> \u51fa\u73b0 {count} \u6b21,\u5e94\u4e3a 1 \u6b21"
        )
    payload = json.dumps(data, ensure_ascii=False, default=str)
    return html.replace(
        "<!--INJECT-DATA-->",
        f'<script>window.__DATA__ = {payload};</script>',
        1,
    )


def _format_text_output(data: dict, start: str, end: str) -> str:
    """--text 模式纯文本输出(spec R2 缓解,给 pipeline)"""
    out = []
    out.append("# MODE=text \u00b7 \u9002\u7528: ... | grep / awk / wc-l \u7b49 pipeline")
    out.append(f"# \u67e5\u4f53\u91cd\u6ce2\u52a8 v2 \u00b7 {start} ~ {end} \u00b7 baseline_mode={data.get('baseline_mode', '?')}")
    out.append(f"# baseline_value={data.get('baseline_value', 0):.2f}kg  baseline_sigma={data.get('baseline_sigma', 0):.4f}kg")
    th = data.get("thresholds", {})
    out.append(f"# thresholds: yellow\u00b11.5\u03c3={th.get('yellow', 0):.4f}  red\u00b12.0\u03c3={th.get('red', 0):.4f}")
    out.append("")
    out.append("date          kg      deviation  level")
    for p in data.get("points", []):
        out.append(f"{p['date']}   {p['kg']:.2f}   {p['deviation_kg']:+.2f}     {p['level']}")
    out.append("")
    out.append(f"# recent_anomalies ({len(data.get('recent_anomalies', []))}):")
    for a in data.get("recent_anomalies", []):
        out.append(f"  {a['date']}  {a['kg']:.2f}kg  {a['deviation_kg']:+.2f}kg  {a['level']}")
    out.append("")
    ew = data.get("early_warning", {})
    out.append(f"# early_warning: {ew.get('level', '?')} - {ew.get('message', '?')}")
    out.append(f"# baseline_toggle_label: {data.get('baseline_toggle_label', '?')}")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="\u4f53\u91cd\u6ce2\u52a8 v2 \u6e32\u67d3\u5668(Q8 v2 spec)"
    )
    parser.add_argument("--start", help="\u8d77\u59cb\u65e5\u671f(YYYY-MM-DD),\u9ed8\u8ba4 30 \u5929\u524d")
    parser.add_argument("--end", help="\u7ed3\u675f\u65e5\u671f(YYYY-MM-DD),\u9ed8\u8ba4\u4eca\u5929")
    parser.add_argument(
        "--baseline", choices=["rolling", "goal"], default="rolling",
        help="baseline mode(rolling=30 \u5929\u5747\u503c / goal=\u76ee\u6807)"
    )
    parser.add_argument("--text", action="store_true", help="\u7eaf\u6587\u672c\u8f93\u51fa(pipeline \u53cb\u597d)")
    parser.add_argument("--output", help="\u8f93\u51fa\u8def\u5f84(\u9ed8\u8ba4 calorie_html/\u67e5\u4f53\u91cd\u6ce2\u52a8_v2_<TS>.html)")
    args = parser.parse_args()

    # \u9ed8\u8ba4\u65e5\u671f\u8303\u56f4:30 \u5929\u524d ~ \u4eca\u5929
    end_date = args.end or date.today().strftime("%Y-%m-%d")
    if args.start:
        start_date = args.start
    else:
        start_dt = date.today() - timedelta(days=30)
        start_date = start_dt.strftime("%Y-%m-%d")

    # \u8c03 backend
    from analysis.weight import weight_volatility_v2
    result = weight_volatility_v2(start_date, end_date, baseline_mode=args.baseline)
    if result.get("status") != "ok":
        print(f"Error: {result.get('message', 'unknown')}", file=sys.stderr)
        return 1

    data = result["data"]

    # --text \u6a21\u5f0f
    if args.text:
        out_text = _format_text_output(data, start_date, end_date)
        sys.stdout.write(out_text + "\n")
        return 0

    # HTML \u6a21\u5f0f
    html = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = _inject_data(html, data)

    out = Path(args.output) if args.output else _default_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    print(f"\u2713 HTML \u5df2\u751f\u6210: {out}")
    print(f"\u26a0\ufe0f ACTION=SEND_TO_USER | HTML={out.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())