#!/usr/bin/env python3
"""
私家大厨 · 数据质量报告 HTML 渲染器
复用 data_view.html(dashboard type)+ 内联 1 个新 "quality_cards" type
"""
import json
import re
import os
import sys
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "data_view.html"


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


def transform_quality_to_dashboard(report: dict) -> dict:
    """把数据质量报告转为 data_view.html 的 dashboard type payload。
    用 dashboard type 展示 KPI(总菜/完整/部分/待补)+ 用 items 字段携带每道菜详情。
    """
    # KPI 卡:总菜 / 完整 / 部分 / 最差
    kpis = [
        {"label": "总菜数", "value": str(report["total_recipes"]), "style": "primary"},
        {"label": "完整 (≥80分)", "value": str(report["summary"]["full_complete"]),
         "style": "success" if report["summary"]["full_complete"] > 0 else "primary"},
        {"label": "部分 (40-79)", "value": str(report["summary"]["partial"]),
         "style": "warn" if report["summary"]["partial"] > 0 else "primary"},
        {"label": "待补 (<40)", "value": str(report["summary"]["minimal"]),
         "style": "danger" if report["summary"]["minimal"] > 0 else "primary"},
    ]

    return {
        "type": "dashboard",
        "title": f"📊 数据质量报告 · {report['generated_at']}",
        "kpis": kpis,
        "items_count": report["total_recipes"],
        "empty_msg": "未找到菜谱",
        "generated_at": report["generated_at"],
    }


def render_html_report(report: dict) -> str:
    """渲染数据质量报告 HTML"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在:{TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload = transform_quality_to_dashboard(report)
    output = inject_data(template, payload)

    # 输出路径
    out_dir = Path(os.environ.get("CHEF_OUTPUT_DIR", "D:/CookHub")) / "quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"数据质量报告_{ts}.html"
    out_path.write_text(output, encoding="utf-8")
    return str(out_path)


if __name__ == "__main__":
    # 直接读 stdin JSON → 输出 HTML
    data = json.load(sys.stdin)
    out = render_html_report(data)
    print(out)
