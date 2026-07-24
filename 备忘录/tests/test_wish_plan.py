"""
心愿排期向导(wish-batch-plan)的契约 + 过程型 HTML 测试

覆盖:
  - 默认搜索(只列 due IS NULL)
  - --all(含已排期)
  - --ids 显式列表
  - --ids 与 --all 互斥硬规则
  - suggest-due 格式校验
  - --html 端到端(生成 HTML + 包含 4 部分 prompt 必需结构)
  - 渲染器不污染原模板
"""
import json
import re
import subprocess
import sys
from pathlib import Path
import pytest

SCRIPT_DIR = Path(__file__).parent.parent / "script"


def _run_cli(*args, env=None):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "memo_cli.py"), *args],
        capture_output=True, text=True, encoding="utf-8",
        env=env, timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.fixture
def seeded_db(env_with_tmp_db):
    """种入测试数据:3 个未排期心愿 + 1 个已排期心愿"""
    rc, _, _ = _run_cli("add", "八段锦 20 分钟", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    rc, _, _ = _run_cli("add", "读《原则》150 页", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    rc, _, _ = _run_cli("add", "练吉他 3 首", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    # 第 4 条:已排期
    rc, out, _ = _run_cli("add", "学 Python 基础", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    wish_id = json.loads(out)["data"]["id"]
    rc, _, _ = _run_cli("set-due", str(wish_id), "--due", "2026-07-15", env=env_with_tmp_db)
    assert rc == 0
    return env_with_tmp_db


class TestWishBatchPlanContract:
    def test_default_lists_only_unset(self, seeded_db):
        """默认(无 --all)只列 due IS NULL,3 条"""
        rc, out, _ = _run_cli("wish-batch-plan", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert data["status"] == "ok"
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 3
        assert all(item["current_due"] is None for item in data["data"])

    def test_all_includes_set_due(self, seeded_db):
        """--all 含已排期,4 条"""
        rc, out, _ = _run_cli("wish-batch-plan", "--all", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert len(data["data"]) == 4
        set_count = sum(1 for x in data["data"] if x["current_due"])
        assert set_count == 1

    def test_ids_explicit_subset(self, seeded_db):
        """--ids 只取指定的心愿"""
        # 先拿到真实 id
        rc, out, _ = _run_cli("wish-batch-plan", env=seeded_db)
        all_items = json.loads(out)["data"]
        ids = [all_items[0]["id"], all_items[1]["id"]]
        rc, out, _ = _run_cli("wish-batch-plan", "--ids", str(ids[0]), str(ids[1]), env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert len(data["data"]) == 2
        assert {x["id"] for x in data["data"]} == set(ids)

    def test_ids_rejects_non_wish(self, seeded_db):
        """--ids 传非心愿 id 应报错"""
        rc, out, _ = _run_cli("add", "普通备忘", env=seeded_db)
        memo_id = json.loads(out)["data"]["id"]
        rc, out, _ = _run_cli("wish-batch-plan", "--ids", str(memo_id), env=seeded_db)
        assert rc == 1
        data = json.loads(out)
        assert data["status"] == "error"
        assert "不是心愿" in data["message"] or "不存在" in data["message"]

    def test_ids_and_all_mutually_exclusive(self, seeded_db):
        """--ids 与 --all 互斥硬规则"""
        rc, out, _ = _run_cli("wish-batch-plan", "--ids", "1", "--all", env=seeded_db)
        assert rc == 1
        data = json.loads(out)
        assert data["status"] == "error"
        assert "互斥" in data["message"]

    def test_suggest_due_validation(self, seeded_db):
        """suggest-due 格式校验"""
        rc, out, _ = _run_cli("wish-batch-plan", "--suggest-due", "2026/07/03", env=seeded_db)
        assert rc == 1
        data = json.loads(out)
        assert "YYYY-MM-DD" in data["message"]


class TestWishPlanHtml:
    def _payload(self):
        return {
            "status": "ok",
            "data": {
                "title": "心愿排期向导",
                "command": "wish-batch-plan",
                "generated_at": "2026-07-24 14:00:00",
                "suggest_due": "2026-07-03",
                "all": False,
                "items": [
                    {"id": 36, "content": "八段锦 20 分钟", "category": "心愿", "sub_category": None,
                     "current_due": None, "feishu_task_guid": None,
                     "selected": True, "suggested_due": "2026-07-03"},
                    {"id": 48, "content": "读《原则》150 页", "category": "心愿", "sub_category": None,
                     "current_due": None, "feishu_task_guid": None,
                     "selected": True, "suggested_due": "2026-07-03"},
                ],
            },
            "message": "找到 2 个心愿",
        }

    def test_html_flag_generates_wish_plan(self, seeded_db):
        """端到端:wish-batch-plan --html 生成 wish_plan_*.html"""
        rc, out, _ = _run_cli("wish-batch-plan", "--suggest-due", "2026-07-03", "--html",
                              env=seeded_db)
        assert rc == 0, f"stderr={_}"
        data = json.loads(out)
        assert "html_path" in data["data"]
        assert "wish_plan_" in data["data"]["html_path"]
        from pathlib import Path
        html_path = Path(data["data"]["html_path"])
        assert html_path.exists()

    def test_html_contains_four_part_prompt_structure(self, seeded_db):
        """HTML 必须包含 4 部分 prompt 的 JS 结构(场景/数据/期望/来源)"""
        rc, out, _ = _run_cli("wish-batch-plan", "--suggest-due", "2026-07-03", "--html",
                              env=seeded_db)
        assert rc == 0
        html_path = json.loads(out)["data"]["html_path"]
        text = Path(html_path).read_text(encoding="utf-8")
        # JS 模板里 4 部分都在(buildPrompt 函数)
        assert "① 场景" in text
        assert "② 数据" in text
        assert "③ 期望" in text
        assert "④ 来源" in text
        # 含 set-due CLI 命令模板
        assert "memo_cli.py set-due" in text
        # 含 "采纳并复制" 按钮(过程型 HTML 必需)
        assert "采纳并复制" in text
        # 含 "全选" / "全不选" 交互
        assert "全选" in text and "全不选" in text

    def test_render_does_not_pollute_other_templates(self, seeded_db):
        """渲染 wish_plan 不污染 memo_query.html 或 sync_report.html"""
        from memo_render import render_wish_plan
        from memo_render import TEMPLATE_PATH
        from pathlib import Path as P
        sync_path = P(__file__).parent.parent / "templates" / "sync_report.html"

        before_query = TEMPLATE_PATH.read_text(encoding="utf-8")
        before_sync = sync_path.read_text(encoding="utf-8")
        render_wish_plan(self._payload())
        after_query = TEMPLATE_PATH.read_text(encoding="utf-8")
        after_sync = sync_path.read_text(encoding="utf-8")
        assert before_query == after_query, "memo_query.html 被污染"
        assert before_sync == after_sync, "sync_report.html 被污染"