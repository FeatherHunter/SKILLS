"""批量改分类向导(batch-update-category)契约 + 过程型 HTML 测试"""
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
    """3 条备忘 + 2 条心愿(改分类操作的主要源)"""
    for c in ["买咖啡", "买橘子", "买苹果"]:
        _run_cli("add", c, env=env_with_tmp_db)
    for w in ["学 Python", "练吉他"]:
        _run_cli("add", w, "-c", "心愿", env=env_with_tmp_db)
    return env_with_tmp_db


class TestBatchUpdateCategoryContract:
    def test_from_category_filter(self, seeded_db):
        """--from-category 过滤"""
        rc, out, _ = _run_cli("batch-update-category", "--from-category", "备忘", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert data["status"] == "ok"
        assert {x["content"] for x in data["data"]} == {"买咖啡", "买橘子", "买苹果"}

    def test_invalid_from_category(self, seeded_db):
        rc, out, _ = _run_cli("batch-update-category", "--from-category", "无效", env=seeded_db)
        assert rc == 1
        assert "无效原分类" in json.loads(out)["message"]

    def test_invalid_to_category(self, seeded_db):
        rc, out, _ = _run_cli("batch-update-category", "--to-category", "无效", env=seeded_db)
        assert rc == 1
        assert "无效目标分类" in json.loads(out)["message"]

    def test_same_category_reject(self, seeded_db):
        rc, out, _ = _run_cli("batch-update-category", "--from-category", "备忘", "--to-category", "备忘",
                              env=seeded_db)
        assert rc == 1
        assert "相同" in json.loads(out)["message"]


class TestBatchUpdateCategoryHtml:
    def test_html_flag_generates_change_category(self, seeded_db):
        rc, out, _ = _run_cli("batch-update-category", "--from-category", "备忘",
                              "--to-category", "打卡", "--html", env=seeded_db)
        assert rc == 0
        data = json.loads(out)
        assert "change_category_" in data["data"]["html_path"]
        assert Path(data["data"]["html_path"]).exists()

    def test_html_contains_four_part_prompt(self, seeded_db):
        rc, out, _ = _run_cli("batch-update-category", "--from-category", "备忘",
                              "--to-category", "心愿", "--html", env=seeded_db)
        assert rc == 0
        text = Path(json.loads(out)["data"]["html_path"]).read_text(encoding="utf-8")
        assert "① 场景" in text
        assert "② 数据" in text
        assert "③ 期望" in text
        assert "④ 来源" in text
        assert "update-category" in text
        assert "采纳并复制" in text

    def test_render_does_not_pollute_other_templates(self, seeded_db):
        from memo_render import render_change_category
        template_dir = Path(__file__).parent.parent / "templates"
        files = ["memo_query.html", "wish_plan.html", "wish_complete.html",
                 "sync_report.html", "change_category.html"]
        before = {f: (template_dir / f).read_text(encoding="utf-8") for f in files}
        payload = {
            "status": "ok",
            "data": {
                "title": "批量改分类向导",
                "command": "batch-update-category",
                "generated_at": "2026-07-24",
                "from_category": "备忘",
                "to_category": "心愿",
                "target_conflict_count": 0,
                "items": [],
            },
            "message": "ok",
        }
        render_change_category(payload)
        for f in files:
            assert (template_dir / f).read_text(encoding="utf-8") == before[f], f"{f} 被污染"