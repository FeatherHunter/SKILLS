"""
测试: 历史域(T10 · v4.0 历史域实施)
- global-stats: 全局画像单查询(做过几道菜/总次数/最爱/最近/还没做过)
- delete: 回执撤销(删记录 · 末条回滚状态)
- receipt 渲染: 成功=diff+撤销 / 失败=原因+重试(08 双按钮 · 军规 11 DOM 级断言)
- global 渲染: 画像 HTML(08 双按钮 + 可执行注入)
"""
import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
HISTORY_CLI = SCRIPT_DIR / "history_manager.py"
RENDER_HISTORY = SCRIPT_DIR / "render_历史.py"
TEMPLATE_RECEIPT = SCRIPT_DIR.parent / "templates" / "历史" / "record_receipt.html"
TEMPLATE_GLOBAL = SCRIPT_DIR.parent / "templates" / "历史" / "data_view_global.html"
SETUP_CLI = SCRIPT_DIR / "开始使用" / "cli.py"


def make_env(tmp_path: Path) -> dict:
    """隔离环境: 临时 DB 目录 + 临时输出目录(覆盖外部 env)"""
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def run_cli(env: dict, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(HISTORY_CLI), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def run_render(env: dict, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(RENDER_HISTORY), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def init_db(env: dict) -> Path:
    """建库(17 表)→ 返回 DB 路径"""
    r = subprocess.run(
        [sys.executable, str(SETUP_CLI), "init"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert r.returncode == 0, r.stderr
    return Path(env["SKILLS_DB_PATH"]) / "chef_data.db"


def seed_recipe(db_path: Path, name: str, rid: str = None) -> str:
    """插一条最小可用食谱(recipes 表 10 字段 NOT NULL),返回 id"""
    import uuid
    rid = rid or str(uuid.uuid4())
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO recipes (id, name, description, difficulty, servings, total_time_minutes, status, photo_url, source, source_url) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (rid, name, "测试菜谱", "简单", 2, 15, "未做", "", "测试", "")
    )
    conn.commit()
    conn.close()
    return rid


def seed_history(db_path: Path, recipe_id: str, cook_date: str, seq: int, rating: float, feedback: str) -> str:
    """插一条烹饪历史,返回 history id"""
    import uuid
    hid = str(uuid.uuid4())
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO recipe_history (id, recipe_id, cook_date, cook_sequence, rating, feedback) VALUES (?,?,?,?,?,?)",
        (hid, recipe_id, cook_date, seq, rating, feedback)
    )
    conn.commit()
    conn.close()
    return hid


def simulate_browser_parse(html: str) -> dict:
    """军规 11 · DOM 渲染级断言(#127 教训): 注入必须是可执行的 script,不是被 JSON 元素吞没的死 payload"""
    import re as _re
    assert '<script id="payload"' not in html, "模板不得再用 json-payload 元素"
    m = _re.search(r'<script>window\.__DATA__ = (\{.*\});</script>', html, _re.S)
    assert m, "未找到可执行的 window.__DATA__ 注入脚本(可能被 JSON 元素吞没)"
    return json.loads(m.group(1))


class TestGlobalStats:
    """hist-4 全局画像 · 一次查询即得(单 SQL 聚合)"""

    def test_global_stats_portrait(self, tmp_path):
        """造数: 2 菜有历史 + 1 菜未做 → 画像字段全对"""
        env = make_env(tmp_path)
        db = init_db(env)
        rid_a = seed_recipe(db, "宫保虾球")
        rid_b = seed_recipe(db, "酸菜鱼")
        seed_recipe(db, "红烧肉")  # 未做
        seed_history(db, rid_a, "2026-08-01", 1, 4.5, "虾很Q")
        seed_history(db, rid_a, "2026-08-03", 2, 5.0, "完美")
        seed_history(db, rid_b, "2026-08-02", 1, 3.0, "有点辣")
        # 宫保虾球状态应为已做
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE recipes SET status='已做' WHERE id=?", (rid_a,))
        conn.commit()
        conn.close()

        r = run_cli(env, "global-stats", "--json")
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "success"
        g = data["data"]["global"]
        assert g["cooked_count"] == 2
        assert g["total_cooks"] == 3
        assert g["never_cooked_count"] == 1
        assert g["recipe_total"] == 3
        assert g["favorite_avg"]["name"] == "宫保虾球"
        assert g["favorite_avg"]["avg_rating"] == 4.75
        assert g["favorite_most"]["name"] == "宫保虾球"
        assert g["favorite_most"]["times"] == 2
        assert [x["name"] for x in g["recent"]] == ["宫保虾球", "酸菜鱼"]  # 按最近日期倒序
        assert g["never_cooked"] == ["红烧肉"]

    def test_global_stats_empty(self, tmp_path):
        """空库(无食谱)→ 画像全零不崩"""
        env = make_env(tmp_path)
        init_db(env)
        r = run_cli(env, "global-stats", "--json")
        assert r["rc"] == 0, r["err"]
        g = json.loads(r["out"])["data"]["global"]
        assert g["cooked_count"] == 0
        assert g["total_cooks"] == 0
        assert g["favorite_avg"] is None
        assert g["favorite_most"] is None
        assert g["recent"] == []
        assert g["never_cooked"] == []

    def test_global_stats_human_mode(self, tmp_path):
        """文本模式(无 --json)输出画像要点"""
        env = make_env(tmp_path)
        db = init_db(env)
        rid = seed_recipe(db, "宫保虾球")
        seed_history(db, rid, "2026-08-01", 1, 4.5, "好")
        r = run_cli(env, "global-stats")
        assert r["rc"] == 0, r["err"]
        assert "做过几道菜" in r["out"]
        assert "宫保虾球" in r["out"]


class TestDeleteUndo:
    """回执撤销 · 反悔(删记录 · 末条回滚状态)"""

    def test_delete_removes_record(self, tmp_path):
        env = make_env(tmp_path)
        db = init_db(env)
        rid = seed_recipe(db, "宫保虾球")
        hid = seed_history(db, rid, "2026-08-01", 1, 4.5, "好")
        r = run_cli(env, "delete", hid, "--json")
        assert r["rc"] == 0, r["err"]
        data = json.loads(r["out"])
        assert data["status"] == "success"
        conn = sqlite3.connect(str(db))
        n = conn.execute("SELECT COUNT(*) FROM recipe_history WHERE id=?", (hid,)).fetchone()[0]
        conn.close()
        assert n == 0

    def test_delete_last_record_reverts_status(self, tmp_path):
        """末条记录删除 → 食谱状态 已做 → 未做(首做翻转的回滚)"""
        env = make_env(tmp_path)
        db = init_db(env)
        rid = seed_recipe(db, "宫保虾球")
        hid = seed_history(db, rid, "2026-08-01", 1, 4.5, "好")
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE recipes SET status='已做' WHERE id=?", (rid,))
        conn.commit()
        conn.close()
        r = run_cli(env, "delete", hid)
        assert r["rc"] == 0, r["err"]
        assert "回滚" in r["out"]
        conn = sqlite3.connect(str(db))
        st = conn.execute("SELECT status FROM recipes WHERE id=?", (rid,)).fetchone()[0]
        conn.close()
        assert st == "未做"

    def test_delete_nonexistent_friendly_error(self, tmp_path):
        env = make_env(tmp_path)
        init_db(env)
        r = run_cli(env, "delete", "no-such-id", "--json")
        data = json.loads(r["out"])
        assert data["status"] == "error"
        assert "未找到记录" in data["message"]


class TestReceiptRender:
    """hist-1 记录做菜回执: 成功=diff+撤销 / 失败=原因+重试(08 双按钮)"""

    def test_template_has_unique_placeholder(self):
        content = TEMPLATE_RECEIPT.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_template_has_copy_buttons_hard_standard(self):
        content = TEMPLATE_RECEIPT.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_render_success_receipt(self, tmp_path):
        """成功回执: 结果 + diff + 撤销按钮"""
        env = make_env(tmp_path)
        payload = {
            "mode": "success",
            "scene_id": "record_cook",
            "scene_title": "记录做菜(完整 + 快速 + 补录)",
            "wake_word": "记录做菜",
            "command_cn": "记录做菜",
            "occurred_at": "2026-08-09 12:00:00",
            "operation": "记录做菜",
            "target": "宫保虾球",
            "result": "已记录:宫保虾球 · 第 2 次做 · 评分 4.5 · 反馈「虾很Q,下次少放盐」",
            "diff": [
                {"action": "add", "field": "recipe_history", "summary": "cook_date=2026-08-09 · sequence=2 · rating=4.5"},
                {"action": "mod", "field": "recipes.status", "summary": "未做 → 已做(首次做菜)"},
            ],
            "history_id": "abc12345-6789",
            "undo_prompt": "请撤销刚才的记录做菜:python scripts/history_manager.py delete abc12345-6789",
            "reminder": "撤销后该菜若再无历史,状态会回滚为「未做」。",
        }
        p = tmp_path / "receipt_success.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = run_render(env, "receipt", str(p))
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "历史"
        files = list(out_dir.glob("记录做菜回执_*.html"))
        assert files, "回执 HTML 未输出"
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["mode"] == "success"
        assert data["undo_prompt"]
        assert "撤销" in html
        assert "复制数据" in html and "复制日志" in html
        assert "虾很Q" in html

    def test_render_failure_receipt(self, tmp_path):
        """失败回执: 原因 + 重试按钮"""
        env = make_env(tmp_path)
        payload = {
            "mode": "failure",
            "scene_id": "record_cook",
            "scene_title": "记录做菜",
            "wake_word": "记录做菜",
            "command_cn": "记录做菜",
            "occurred_at": "2026-08-09 12:00:00",
            "operation": "记录做菜",
            "failure_reason": "缺少 --feedback(L1 NOT NULL 兜底)",
            "key_data": {"recipe": "宫保虾球", "rating": "4.5"},
            "next_step": "请先问用户:这次做菜的反馈/改进建议是什么?",
            "retry_prompt": "记录做菜 宫保虾球 --rating 4.5 --feedback 用户反馈内容",
        }
        p = tmp_path / "receipt_fail.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r = run_render(env, "receipt", str(p))
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "历史"
        files = list(out_dir.glob("记录做菜回执_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["mode"] == "failure"
        assert "失败原因" in html
        assert "修改重试" in html
        assert "复制数据" in html and "复制日志" in html

    def test_render_no_clobber_suffix(self, tmp_path):
        """同秒重复渲染 → _N 后缀防覆盖(08 12.A)"""
        env = make_env(tmp_path)
        payload = {"mode": "success", "target": "宫保虾球", "operation": "记录做菜",
                   "result": "ok", "diff": [], "history_id": "h1"}
        p = tmp_path / "r.json"
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        r1 = run_render(env, "receipt", str(p))
        assert r1["rc"] == 0, r1["err"]
        out_dir = tmp_path / "chef_out" / "历史"
        first = list(out_dir.glob("记录做菜回执_*.html"))
        assert len(first) == 1
        r2 = run_render(env, "receipt", str(p))
        assert r2["rc"] == 0, r2["err"]
        files = sorted(out_dir.glob("记录做菜回执_*.html"))
        assert len(files) == 2, "重复渲染必须 _N 防覆盖,不能覆盖旧文件"
        assert files[0].name != files[1].name


class TestGlobalRender:
    """hist-4 全局画像 HTML 渲染(08 双按钮 + 可执行注入)"""

    def test_template_has_unique_placeholder(self):
        content = TEMPLATE_GLOBAL.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1

    def test_template_has_copy_buttons_hard_standard(self):
        content = TEMPLATE_GLOBAL.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_render_global_html(self, tmp_path):
        """造数 → render global → HTML 含画像 + 双按钮 + 可执行注入"""
        env = make_env(tmp_path)
        db = init_db(env)
        rid_a = seed_recipe(db, "宫保虾球")
        seed_recipe(db, "红烧肉")
        seed_history(db, rid_a, "2026-08-03", 1, 5.0, "完美")
        conn = sqlite3.connect(str(db))
        conn.execute("UPDATE recipes SET status='已做' WHERE id=?", (rid_a,))
        conn.commit()
        conn.close()

        r = run_render(env, "global")
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "dashboard"
        files = list(out_dir.glob("数据视图_global_*.html"))
        assert files, "全局画像 HTML 未输出"
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["global"]["cooked_count"] == 1
        assert data["global"]["total_cooks"] == 1
        assert data["global"]["favorite_avg"]["name"] == "宫保虾球"
        assert data["global"]["never_cooked"] == ["红烧肉"]
        assert "复制数据" in html and "复制日志" in html
        assert "<!--INJECT-DATA-->" not in html

    def test_render_global_empty(self, tmp_path):
        """空库 → 画像 HTML 正常渲染(0 项不崩)"""
        env = make_env(tmp_path)
        init_db(env)
        r = run_render(env, "global")
        assert r["rc"] == 0, r["err"]
        out_dir = tmp_path / "chef_out" / "dashboard"
        files = list(out_dir.glob("数据视图_global_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        data = simulate_browser_parse(html)
        assert data["global"]["cooked_count"] == 0
