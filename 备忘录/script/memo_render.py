#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
SYNC_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "sync_report.html"
WISH_PLAN_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_plan.html"
WISH_COMPLETE_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_complete.html"
CHANGE_CATEGORY_TEMPLATE_PATH = SKILL_DIR / "templates" / "change_category.html"
OUTPUT_DIR = SKILL_DIR / "output"


def _inject(template: str, payload: dict) -> str:
    """统一注入:占位符 </ 转义防断标签,锚点 <body>(原模板必有)"""
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("<body>", f"<body>\n<script>window.__DATA__ = {safe_payload};</script>", 1)


def _write_output(name: str, html: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{name}_{ts}.html"
    out_path.write_text(html, encoding="utf-8")
    return str(out_path)


def render_query(payload, name="memo_query"):
    """渲染查询结果页(模板 memo_query.html),供 search/get/search-date/reminders/completed 共用"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    injected = _inject(template, payload)
    return _write_output(name, injected)


def render_sync_report(payload, name="sync_report"):
    """渲染同步报告页(模板 sync_report.html),供 sync-from-feishu 命令 --html 使用

    payload.data 期望字段(参考 feishu_sync.sync_from_feishu 返回):
      backfilled / scanned_done / synced / scanned_pending
      due_added / due_overridden / due_removed
      skipped_no_memo_id / skipped_already_done / skipped_no_local_note
      errors: [str]
    """
    template = SYNC_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    injected = _inject(template, payload)
    return _write_output(name, injected)


def render_wish_plan(payload, name="wish_plan"):
    """渲染心愿排期向导页(模板 wish_plan.html),过程型 HTML

    payload.data 期望字段:
      title / command / generated_at
      suggest_due: str|None(全局建议排期)
      all: bool(是否含已排期心愿)
      items: [{
        id, content, category, sub_category, current_due, feishu_task_guid,
        selected: bool, suggested_due: str|None
      }, ...]
    """
    template = WISH_PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
    injected = _inject(template, payload)
    return _write_output(name, injected)


def render_wish_complete(payload, name="wish_complete"):
    """渲染心愿完成向导页(模板 wish_complete.html),过程型 HTML

    payload.data 期望字段:
      title / command / generated_at
      default_content: str|None(默认打卡内容)
      items: [{
        id, content, category, sub_category, due, feishu_task_guid,
        selected: bool
      }, ...]
    """
    template = WISH_COMPLETE_TEMPLATE_PATH.read_text(encoding="utf-8")
    injected = _inject(template, payload)
    return _write_output(name, injected)


def render_change_category(payload, name="change_category"):
    """渲染批量改分类向导页(模板 change_category.html),过程型 HTML

    payload.data 期望字段:
      title / command / generated_at
      from_category: str(原分类)
      to_category: str|None(建议目标分类,HTML 可改)
      items: [{
        id, content, sub_category, media_path, due,
        selected: bool
      }, ...]
    """
    template = CHANGE_CATEGORY_TEMPLATE_PATH.read_text(encoding="utf-8")
    injected = _inject(template, payload)
    return _write_output(name, injected)


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
