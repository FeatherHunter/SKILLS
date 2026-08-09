#!/usr/bin/env python3
"""
私家大厨 · 数据质量报告 HTML 渲染器
使用独立模板 templates/data_quality_report.html(不依赖 data_view.html)
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
from output_config import get_output_root, get_output_dir
from align_08 import (build_copy_data, build_copy_log, inject_08_layer, unique_output_path)
TEMPLATE_PATH = SKILL_DIR / "templates" / "data_quality_report.html"


def inject_data(template_html: str, payload: dict) -> str:
    """注入数据到 <!--INJECT-DATA--> 占位符"""
    placeholder = "<!--INJECT-DATA-->"
    count = template_html.count(placeholder)
    if count != 1:
        raise ValueError(f"占位符必须唯一 1 次,实际 {count} 次")
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")
    script_tag = f'<script>window.__DATA__ = {payload_json};</script>'
    return template_html.replace(placeholder, script_tag, 1)


def transform_quality_payload(report: dict) -> dict:
    """把数据质量报告转为模板 payload"""
    # KPI 卡
    kpis = [
        {"label": "总菜数", "value": str(report["total_recipes"]), "style": "primary"},
        {"label": "完整 (≥80分)", "value": str(report["summary"]["full_complete"]),
         "style": "success" if report["summary"]["full_complete"] > 0 else "primary"},
        {"label": "部分 (40-79)", "value": str(report["summary"]["partial"]),
         "style": "warn" if report["summary"]["partial"] > 0 else "primary"},
        {"label": "待补 (<40)", "value": str(report["summary"]["minimal"]),
         "style": "danger" if report["summary"]["minimal"] > 0 else "primary"},
    ]

    # 每道菜直接放 items(模板会渲染)
    items = []
    for r in report["recipes"]:
        items.append({
            "recipe_name": r["recipe_name"],
            "score": r["score"],
            "difficulty": r.get("difficulty"),
            "total_time": r.get("total_time_minutes"),
            "ingredients_count": r["ingredients_count"],
            "steps_count": r["steps_count"],
            "tips_count": r["tips_count"],
            "techniques_count": r["techniques_count"],
            "has_background": r["has_background"],
            "history_count": r.get("history_count", 0),
            "missing": r.get("missing", []),
        })

    return {
        "title": f"📊 数据质量报告 · {report['generated_at']}",
        "generated_at": report["generated_at"],
        "total_recipes": report["total_recipes"],
        "kpis": kpis,
        "items": items,
        "items_count": len(items),
    }


def render_html_report(report: dict) -> str:
    """渲染数据质量报告 HTML"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在:{TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = transform_quality_payload(report)
    output = inject_data(template, payload)

    # 08 对齐:复制数据(5 段)/复制日志(6 段)
    copy_data = build_copy_data(
        scene_id="quality-1",
        command_cn="数据体检",
        target="全部食谱",
        payload={
            "total_recipes": payload.get("total_recipes"),
            "kpis": payload.get("kpis"),
            "generated_at": payload.get("generated_at"),
        },
    )
    copy_log = build_copy_log(
        scene_id="quality-1",
        command_cn="数据体检",
        wake_word="数据体检 / 数据质量",
        thinking="意图理解 → 数据体检 → 逐菜评估 5 维度 → 聚合 KPI + 明细",
        data_structure="window.__DATA__(kpis/items)· 读库(只读)",
        call_chain="python data_quality_report.py | python render_quality_report.py",
    )
    output = inject_08_layer(output, copy_data, copy_log)

    out_dir = get_output_root() / "quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = unique_output_path(out_dir, f"数据质量报告_{ts}")
    out_path.write_text(output, encoding="utf-8")
    return str(out_path)


if __name__ == "__main__":
    data = json.load(sys.stdin)
    out = render_html_report(data)
    print(out)