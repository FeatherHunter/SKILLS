#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
SYNC_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "sync_report.html"
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


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
