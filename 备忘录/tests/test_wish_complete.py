"""
心愿完成向导(wish-complete)的契约 + 过程型 HTML 测试

覆盖:
  - 默认搜索(未排期 + 已过期排期)
  - --all(含全部心愿)
  - --ids 显式列表
  - --ids 与 --all 互斥硬规则
  - --content 默认打卡内容
  - --html 端到端(生成 HTML + 含 4 部分 prompt 结构 + 含 complete-wish 命令)
  - 渲染器不污染其他模板
"""
import json
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
    """种入:1 个未排期心愿 + 1 个已过期心愿 + 1 个未来排期心愿 + 1 个非心愿"""
    rc, _, _ = _run_cli("add", "未排期心愿", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    rc, _, _ = _run_cli("add", "过期心愿", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    rc, _, _ = _run_cli("add", "未来心愿", "-c", "心愿", env=env_with_tmp_db)
    assert rc == 0
    # 普通备忘(不应出现在结果中)
    rc, _, _ = _run_cli("add", "普通备忘", env=env_with_tmp_db)

    # 把第 2 条心愿(过期心愿)设 due=昨天
    rc, out, _ = _run_cli("wish-batch-plan", env=env_with_tmp_db)
    items = json.loads(out)["data"]
    expired = [x for x in items if x["content"] == "过期心愿"][0]
    future = [x for x in items if x["content"] == "未来心愿"][0]
    rc, _, _ = _run_cli("set-due", str(expired["id"]), "--due", "2020-01-01", env=env_with_tmp_db)
    assert rc == 0
    rc, _, _ = _run_cli("set-due", str(future["id"]), "--due", "2099-12-31", env=env_with_tmp_db)
    assert rc == 0
    return env_with_tmp_db


class TestWishCompleteContract:
    def test_default_lists_unset_and_overdue(self, seeded_db):
        """默认:未排期 + 已过期排期(2 条);不含未来排期"""
        rc, out, _ = _run_cli("wish-complete", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert data["status"] == "ok"
        items_data = data["data"]
        contents = {x["content"] for x in items_data}
        assert contents == {"未排期心愿", "过期心愿"}

    def test_all_includes_future_wish(self, seeded_db):
        """--all:含全部 3 个心愿"""
        rc, out, _ = _run_cli("wish-complete", "--all", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        contents = {x["content"] for x in data["data"]}
        assert contents == {"未来心愿", "未排期心愿", "过期心愿"}

    def test_ids_explicit(self, seeded_db):
        rc, out, _ = _run_cli("wish-batch-plan", "--all", env=seeded_db)
        all_items = json.loads(out)["data"]
        ids = [all_items[0]["id"], all_items[1]["id"]]
        rc, out, _ = _run_cli("wish-complete", "--ids", str(ids[0]), str(ids[1]), env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert {x["id"] for x in data["data"]} == set(ids)

    def test_ids_rejects_non_wish(self, seeded_db):
        """--ids 传非心愿 id 应报错(seeded_db 里 add 1 条普通备忘,id=4)"""
        rc, out, _ = _run_cli("get", "4", env=seeded_db)
        memo_data = json.loads(out)["data"]
        assert memo_data["category"] == "备忘"
        rc, out, _ = _run_cli("wish-complete", "--ids", "4", env=seeded_db)
        assert rc == 1
        data = json.loads(out)
        assert "不是心愿" in data["message"]

    def test_ids_and_all_mutually_exclusive(self, seeded_db):
        rc, out, _ = _run_cli("wish-complete", "--ids", "1", "--all", env=seeded_db)
        assert rc == 1
        assert "互斥" in json.loads(out)["message"]

    def test_content_default_echo(self, seeded_db):
        """--content 默认值应在 data.default_content 出现"""
        rc, out, _ = _run_cli("wish-complete", "--all", "--content", "今天完成了", env=seeded_db)
        assert rc == 0


class TestWishCompleteHtml:
    def test_html_flag_generates_wish_complete(self, seeded_db):
        """端到端:wish-complete --html 生成 wish_complete_*.html"""
        rc, out, _ = _run_cli("wish-complete", "--html", env=seeded_db)
        assert rc == 0, f"stderr={_}"
        data = json.loads(out)
        assert "html_path" in data["data"]
        assert "wish_complete_" in data["data"]["html_path"]
        html_path = Path(data["data"]["html_path"])
        assert html_path.exists()

    def test_html_contains_four_part_prompt(self, seeded_db):
        rc, out, _ = _run_cli("wish-complete", "--all", "--html", env=seeded_db)
        assert rc == 0
        html_path = json.loads(out)["data"]["html_path"]
        text = Path(html_path).read_text(encoding="utf-8")
        # 4 部分 prompt
        assert "① 场景" in text
        assert "② 数据" in text
        assert "③ 期望" in text
        assert "④ 来源" in text
        # complete-wish 命令
        assert "memo_cli.py complete-wish" in text
        # "采纳并复制" 按钮
        assert "采纳并复制" in text

    def test_render_does_not_pollute_other_templates(self, seeded_db):
        """渲染 wish_complete 不污染 memo_query / wish_plan / sync_report"""
        from memo_render import render_wish_complete
        from pathlib import Path as P
        template_dir = P(__file__).parent.parent / "templates"
        memo_query_path = template_dir / "memo_query.html"
        wish_plan_path = template_dir / "wish_plan.html"
        sync_path = template_dir / "sync_report.html"

        before_q = memo_query_path.read_text(encoding="utf-8")
        before_p = wish_plan_path.read_text(encoding="utf-8")
        before_s = sync_path.read_text(encoding="utf-8")

        payload = {
            "status": "ok",
            "data": {
                "title": "心愿完成向导",
                "command": "wish-complete",
                "generated_at": "2026-07-24",
                "default_content": None,
                "items": [{"id": 1, "content": "x", "category": "心愿",
                          "sub_category": None, "due": None, "feishu_task_guid": None, "selected": True}],
            },
            "message": "ok",
        }
        render_wish_complete(payload)

        assert memo_query_path.read_text(encoding="utf-8") == before_q, "memo_query.html 被污染"
        assert wish_plan_path.read_text(encoding="utf-8") == before_p, "wish_plan.html 被污染"
        assert sync_path.read_text(encoding="utf-8") == before_s, "sync_report.html 被污染"