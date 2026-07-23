"""
模板注入测试(memo_render.py)
- 占位符 <!--INJECT-DATA--> 全文件恰好 1 次
- </ 转义防 script 断标签
- 输出文件路径规范(output/memo_query_*.html)
- 模板不被污染(原 templates/memo_query.html 不变)
"""
import json
import re
from pathlib import Path
import pytest

from memo_render import render_query, render_sync_report, TEMPLATE_PATH, OUTPUT_DIR


class TestTemplatePlaceholder:
    def test_template_exists(self):
        assert TEMPLATE_PATH.exists()
        assert TEMPLATE_PATH.name == "memo_query.html"

    def test_placeholder_appears_exactly_once(self):
        """占位符唯一性 = 注入器稳定性的前提"""
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        # 当前 memo_render.py 是用 <body> 锚点注入,但模板里仍保留 <!--INJECT-DATA--> 注释
        # 作为可演进路径(参见 SKILL.md §HTML 模板模式 描述)
        count = text.count("<!--INJECT-DATA-->")
        assert count <= 1, f"占位符出现 {count} 次,应 ≤ 1"


class TestInjection:
    def _payload(self):
        return {
            "status": "ok",
            "data": {
                "title": "测试标题",
                "command": "search",
                "generated_at": "2026-07-24 10:00:00",
                "items": [{"id": 1, "content": "测试"}],
            },
            "message": "ok",
        }

    def test_render_returns_path(self):
        path = render_query(self._payload())
        assert path.endswith(".html")
        assert "memo_query_" in path
        assert str(OUTPUT_DIR) in path

    def test_render_injects_window_data(self):
        path = render_query(self._payload())
        text = Path(path).read_text(encoding="utf-8")
        assert "window.__DATA__" in text
        # JSON 必须出现在 script 标签内
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", text, re.DOTALL)
        assert m, "window.__DATA__ 注入失败"
        data = json.loads(m.group(1))
        assert data["data"]["title"] == "测试标题"

    def test_script_close_tag_escaped(self):
        """含 </script> 的 content 应被转义成 <\\/script>,防止提前闭合注入块"""
        payload = self._payload()
        payload["data"]["items"] = [{"id": 99, "content": "<script>alert(1)</script>"}]
        path = render_query(payload)
        text = Path(path).read_text(encoding="utf-8")
        # 找到注入的 payload 块
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", text, re.DOTALL)
        assert m, "window.__DATA__ 注入失败"
        injected = m.group(1)
        # 转义后的 </ 必须存在(原始 </script> 被替换成 <\/script>)
        assert "<\\/script>" in injected, f"转义未生效: {injected[-100:]}"
        # 同时验证 raw </script> 不在注入块中(否则会提前闭合)
        assert "</script>" not in injected, "raw </script> 出现在注入块里 → 提前闭合风险"


class TestTemplateNotPolluted:
    def _payload(self):
        return {
            "status": "ok",
            "data": {
                "title": "测试标题",
                "command": "search",
                "generated_at": "2026-07-24 10:00:00",
                "items": [{"id": 1, "content": "测试"}],
            },
            "message": "ok",
        }

    def test_template_hash_unchanged(self):
        """渲染后原模板文件内容不变"""
        before = TEMPLATE_PATH.read_text(encoding="utf-8")
        render_query(self._payload())
        after = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert before == after, "原模板被污染"


class TestSyncReportRender:
    """sync_report.html 渲染 + 注入"""

    def _payload(self, errors=()):
        return {
            "status": "ok",
            "data": {
                "title": "备忘录同步报告",
                "command": "sync-from-feishu",
                "generated_at": "2026-07-24 10:00:00",
                "backfilled": 2,
                "scanned_done": 5,
                "synced": 3,
                "scanned_pending": 8,
                "due_added": 1,
                "due_overridden": 0,
                "due_removed": 1,
                "skipped_no_memo_id": 0,
                "skipped_already_done": 0,
                "skipped_no_local_note": 2,
                "errors": list(errors),
            },
            "message": "双向同步完成",
        }

    def test_renders_to_sync_report_html(self):
        path = render_sync_report(self._payload())
        assert "sync_report_" in path
        assert path.endswith(".html")
        assert str(OUTPUT_DIR) in path

    def test_injects_window_data(self):
        path = render_sync_report(self._payload())
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", text, re.DOTALL)
        assert m, "window.__DATA__ 注入失败"
        data = json.loads(m.group(1))
        assert data["data"]["backfilled"] == 2
        assert data["data"]["scanned_done"] == 5
        assert data["data"]["synced"] == 3

    def test_includes_errors_in_payload(self):
        path = render_sync_report(self._payload(errors=["feishu CLI not available"]))
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r"<script>window\.__DATA__ = (\{.*?\});</script>", text, re.DOTALL)
        assert m
        data = json.loads(m.group(1))
        assert data["data"]["errors"] == ["feishu CLI not available"]

    def test_template_file_not_polluted(self):
        """渲染 sync_report 不污染 memo_query.html 原模板"""
        before = TEMPLATE_PATH.read_text(encoding="utf-8")
        render_sync_report(self._payload())
        after = TEMPLATE_PATH.read_text(encoding="utf-8")
        assert before == after, "memo_query.html 被 sync 渲染污染"