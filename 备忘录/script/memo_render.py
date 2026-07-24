#!/usr/bin/env python3
"""备忘录 HTML 渲染器

2026-07-24 Step 6 · 复用 模板HTML并注入数据/_shared/injector.py
  - _inject → injector.inject_html(用 <body> 锚点,代替原 <!--INJECT-DATA--> 占位符)
  - _write_output → injector.write_output
  - 4 个 render 函数 + 1 个 main
"""
import json
import sys
from pathlib import Path

# 把模板HTML并注入数据/_shared/ 加到 sys.path
_SHARED_DIR = Path(__file__).parent.parent.parent / "模板HTML并注入数据" / "_shared"
sys.path.insert(0, str(_SHARED_DIR))

from injector import inject_html, write_output  # noqa: E402

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
SYNC_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "sync_report.html"
WISH_PLAN_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_plan.html"
WISH_COMPLETE_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_complete.html"
CHANGE_CATEGORY_TEMPLATE_PATH = SKILL_DIR / "templates" / "change_category.html"
OUTPUT_DIR = SKILL_DIR / "output"


def _inject_body(template: str, payload: dict) -> str:
    """以 <body> 锚点注入(window.__DATA__ 全局变量)

    4 个原模板都用 <body>(恰好 1 处) 做锚点 · 兼容 injector 占位符型
    """
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("<body>", f"<body>\n<script>window.__DATA__ = {safe_payload};</script>", 1)


def _write(name: str, html: str) -> str:
    return write_output(OUTPUT_DIR, name, html)


def render_query(payload, name="memo_query"):
    """渲染查询结果页(模板 memo_query.html)"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_sync_report(payload, name="sync_report"):
    """渲染同步报告页(模板 sync_report.html)

    payload.data 期望字段(参考 feishu_sync.sync_from_feishu 返回):
      backfilled / scanned_done / synced / scanned_pending
      due_added / due_overridden / due_removed
      skipped_no_memo_id / skipped_already_done / skipped_no_local_note
      errors: [str]
    """
    template = SYNC_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_wish_plan(payload, name="wish_plan"):
    """渲染心愿排期向导页(过程型 HTML)"""
    template = WISH_PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_wish_complete(payload, name="wish_complete"):
    """渲染心愿完成向导页(过程型 HTML)"""
    template = WISH_COMPLETE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_change_category(payload, name="change_category"):
    """渲染批量改分类向导页(过程型 HTML)"""
    template = CHANGE_CATEGORY_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
