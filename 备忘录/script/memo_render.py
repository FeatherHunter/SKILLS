#!/usr/bin/env python3
"""备忘录 HTML 渲染器

v1.1.0(2026-07-25) · 修复 v1.0.9 真实运行时 bug:
  - 之前 v1.0.6 时抽出共享模块到 _shared/injector.py
  - f304e4f (2026-07-24 16:56) commit "清理已沉淀的旧模板目录" 把 _shared/injector.py 删了
  - 之前的 `from injector import` 引用失效,跑 --html 必 ImportError
  - 现在改用**本地私有 `script/injector.py`** · 不依赖外部模块
  - 历史增强(占位符唯一性、</ 转义、同秒冲突保护)全部保留

输出目录(v1.0.5) · 输出 = DB_PATH.parent / f"{SKILL_HTML_NAME}_html"
"""
import json
from pathlib import Path

from injector import inject_html, write_output  # noqa: F401 · 同目录私有模块
from memo_cli import DB_PATH  # noqa: E402  · 复用 memo_cli 的 DB_PATH 计算逻辑

# v1.0.5:skill ASCII 短码(避免中文路径跨平台编码问题)
SKILL_HTML_NAME = "memo"

SKILL_DIR = Path(__file__).parent.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "memo_query.html"
SYNC_REPORT_TEMPLATE_PATH = SKILL_DIR / "templates" / "sync_report.html"
WISH_PLAN_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_plan.html"
WISH_COMPLETE_TEMPLATE_PATH = SKILL_DIR / "templates" / "wish_complete.html"
CHANGE_CATEGORY_TEMPLATE_PATH = SKILL_DIR / "templates" / "change_category.html"


def _get_html_output_dir():
    """HTML 输出目录 = DB_PATH.parent / f"{SKILL_HTML_NAME}_html"

    v1.0.5 设计(第一性):
      - HTML 是 DB 的快照视图 → 与 DB 在同一目录
      - DB_PATH 复用 memo_cli._find_db_path() 逻辑(SKILLS_DB_PATH 环境变量优先)
      - skill 子目录(SKILL_HTML_NAME)隔离多 skill 共用 SKILLS_DB_PATH 时文件名冲突
      - fallback:D:/.db/ (Windows) 或 /mnt/d/.db/ (WSL/Linux)
    """
    return DB_PATH.parent / f"{SKILL_HTML_NAME}_html"


def _inject_body(template: str, payload: dict) -> str:
    """以 <body> 锚点注入(window.__DATA__ 全局变量)

    4 个原模板都用 <body>(恰好 1 处) 做锚点 · 兼容 injector 占位符型
    """
    safe_payload = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("<body>", f"<body>\n<script>window.__DATA__ = {safe_payload};</script>", 1)


def _write(name: str, html: str) -> str:
    """v1.0.5:HTML 输出到与 DB 同级目录的 skill 子目录"""
    return write_output(_get_html_output_dir(), name, html)


def render_query(payload, name="备忘录查询"):
    """渲染查询结果页(模板 memo_query.html)"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_sync_report(payload, name="同步报告"):
    """渲染同步报告页(模板 sync_report.html)

    payload.data 期望字段(参考 feishu_sync.sync_from_feishu 返回):
      backfilled / scanned_done / synced / scanned_pending
      due_added / due_overridden / due_removed
      skipped_no_memo_id / skipped_already_done / skipped_no_local_note
      errors: [str]
    """
    template = SYNC_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_wish_plan(payload, name="心愿排期"):
    """渲染心愿排期向导页(过程型 HTML)"""
    template = WISH_PLAN_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_wish_complete(payload, name="心愿完成"):
    """渲染心愿完成向导页(过程型 HTML)"""
    template = WISH_COMPLETE_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def render_change_category(payload, name="批量改分类"):
    """渲染批量改分类向导页(过程型 HTML)"""
    template = CHANGE_CATEGORY_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _write(name, _inject_body(template, payload))


def main():
    payload = json.load(sys.stdin)
    path = render_query(payload)
    print(json.dumps({"status": "ok", "data": {"path": path}, "message": "HTML 已生成"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
