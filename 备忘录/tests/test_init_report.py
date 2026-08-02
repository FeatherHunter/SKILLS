"""v1.2.0 · 初始化报告页守护(#8 经验:场景 HTML 承载 AI 执行证据)

- init_report.html 模板:4 状态 fallback + 检查清单/待办/验证清单渲染
- render_init_report 渲染器:注入 payload → HTML
- prompt 契约:Init prompt 承诺生成初始化报告页(承诺↔兑现)
"""
import re
from pathlib import Path
import sys

import pytest

SKILL_DIR = Path(__file__).parent.parent
SCRIPT_DIR = SKILL_DIR / "script"
sys.path.insert(0, str(SCRIPT_DIR))

TEMPLATE = SKILL_DIR / "templates" / "init_report.html"
SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"


class TestInitReportTemplate:
    def test_template_exists(self):
        assert TEMPLATE.exists(), "templates/init_report.html 缺失"

    def test_has_4_state_fallback(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        for sid in ["stateSuccess", "stateEmpty", "stateMissing", "stateError"]:
            assert sid in text, f"缺 {sid} banner"

    def test_has_check_item_rendering(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "check-item" in text, "缺检查清单项渲染"
        assert "todo-card" in text, "缺待办指引渲染"
        assert "verify-item" in text, "缺验证清单渲染"

    def test_has_shared_inject_placeholder(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "<!--INJECT-SHARED-->" in text, "缺共享 JS 占位符(clipboard)"

    def test_window_data_contract(self):
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "window.__DATA__" in text, "缺 window.__DATA__ 数据契约"


class TestRenderInitReport:
    def _payload(self):
        return {
            "status": "ok",
            "data": {
                "title": "备忘录 · 初始化报告",
                "generated_at": "2026-08-02 18:00:00",
                "items": [
                    {"name": "Python 3.10+", "status": "ok",
                     "desc": "Python 3.13 已安装", "action": ""},
                    {"name": "SQLite 全文搜索", "status": "err",
                     "desc": "FTS5 不可用", "action": "重装 SQLite 或改用纯文本搜索"},
                ],
                "todos": [
                    {"title": "修复 SQLite FTS5", "steps": ["卸载重装", "重跑检查"]},
                ],
                "verify": ["数据库可读写", "提醒调度已配置"],
            },
        }

    def test_renders_html(self):
        from memo_render import render_init_report
        path = render_init_report(self._payload())
        p = Path(path)
        assert p.exists()
        text = p.read_text(encoding="utf-8")
        assert "window.__DATA__" in text
        assert "Python 3.10+" in text, "检查项未注入"

    def test_payload_round_trip(self):
        from memo_render import render_init_report
        import json
        path = render_init_report(self._payload())
        text = Path(path).read_text(encoding="utf-8")
        m = re.search(r"window\.__DATA__ = (\{.*?\});</script>", text, re.DOTALL)
        assert m, "找不到 window.__DATA__ 注入"
        payload = json.loads(m.group(1))
        assert len(payload["data"]["items"]) == 2
        assert payload["data"]["todos"][0]["title"] == "修复 SQLite FTS5"


class TestInitCliCommand:
    """init-report CLI 子命令(v1.2.0 · 垂直链路闭环:AI 诊断 → CLI → HTML)"""

    def _run(self, payload_json):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "memo_cli.py"),
             "init-report", "--data", payload_json],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        return r

    def test_cli_generates_html(self):
        import json
        payload = {"data": {
            "items": [{"name": "Python", "status": "ok", "desc": "3.13", "action": ""}],
            "todos": [], "verify": ["数据库可读写"],
        }}
        r = self._run(json.dumps(payload, ensure_ascii=False))
        assert r.returncode == 0, f"rc={r.returncode} stderr={r.stderr}"
        data = json.loads(r.stdout)
        assert data["status"] == "ok"
        assert "html_path" in data["data"]
        assert Path(data["data"]["html_path"]).exists()

    def test_cli_rejects_bad_json(self):
        r = self._run("{not valid json")
        assert r.returncode == 0  # CLI 不崩,返回 error status
        import json
        data = json.loads(r.stdout)
        assert data["status"] == "error", f"坏 JSON 应报 error,实际 {data}"


class TestInitPromptContract:
    """prompt 承诺 ↔ 流程兑现(#8 A3):Init prompt 必须承诺报告页"""
    @pytest.fixture(scope="class")
    def data(self):
        import yaml
        return yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))

    def test_prompt_promises_report_page(self, data):
        init = [s for s in data["scenarios"]
                if s["scenario_id"] == "memo_init_setup"][0]
        assert "初始化报告页" in init["prompt"], \
            "Init prompt 应承诺生成初始化报告页(承诺↔兑现,#8 A3)"
        assert "检查结果清单" in init["prompt"], "prompt 应承诺检查清单"

    def test_prompt_no_cli_leak(self, data):
        init = [s for s in data["scenarios"]
                if s["scenario_id"] == "memo_init_setup"][0]
        for f in ["memo_cli.py", "init.sql", "memo.db", ".py", "templates/"]:
            assert f not in init["prompt"], f"Init prompt 泄漏实现细节: {f}"
