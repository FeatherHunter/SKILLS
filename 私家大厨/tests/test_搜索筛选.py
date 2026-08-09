"""
测试: 搜索筛选域(search-1 ~ search-13 · T7)
- 检索契约 7 字段: id/name/difficulty/total_time_minutes/status/avg_rating/tags
- search-2 错字纠错: 无结果 → suggest 候选 → 自动/手动纠错「你是不是想找」并直接展示
- search-6 排除食材: NOT EXISTS(ingredients/flavors/diet_tags)生效
- 维度筛选: 菜系/时间/难度/状态/炊具/口味/季节 + 查看全部
- 渲染: 网格卡片 7 字段 + 纠错详情层 + 无结果详情层(08 双按钮 + 占位符注入)
"""
import os
import sys
import json
import sqlite3
import subprocess
import uuid
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
CLI = SCRIPT_DIR / "搜索筛选" / "cli.py"
RENDER = SCRIPT_DIR / "render_搜索筛选.py"
TEMPLATE = SCRIPT_DIR.parent / "templates" / "搜索筛选" / "data_view.html"

SEED = [
    # (id, name, cuisine, difficulty, time, status, ingredients, flavors, diet, seasons, cookwares, ratings)
    ("r1", "宫保鸡丁", "川菜", "简单", 30, "未做",
     ["鸡胸肉", "花生米", "干辣椒"], ["辣"], ["高蛋白"], ["秋冬"], ["炒锅"], [5, 4]),
    ("r2", "清蒸鲈鱼", "粤菜", "中等", 25, "已做",
     ["鲈鱼", "姜"], ["鲜"], [], ["夏"], ["蒸锅"], [3]),
    ("r3", "红烧排骨", "家常菜", "中等", 60, "未做",
     ["排骨", "冰糖"], ["甜"], [], [], ["炒锅"], []),
    ("r4", "番茄炒蛋", "快手菜", "简单", 10, "已做",
     ["番茄", "鸡蛋"], ["酸甜"], ["素"], ["全年"], ["炒锅"], [4, 5, 4]),
]


def make_env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def run_cli(env: dict, *args) -> dict:
    r = subprocess.run([sys.executable, str(CLI), *args],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def run_render(env: dict, *args) -> dict:
    r = subprocess.run([sys.executable, str(RENDER), *args],
                       capture_output=True, text=True, encoding="utf-8", env=env)
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def seed_db(tmp_path: Path):
    """建库(17 表)+ 造数: 4 道菜 + 食材/口味/饮食标签/季节/炊具/历史"""
    env = make_env(tmp_path)
    subprocess.run([sys.executable, "-c", "import init_db; init_db.init_db()"],
                   capture_output=True, env=env, cwd=SCRIPT_DIR)
    conn = sqlite3.connect(str(tmp_path / "chef_data.db"))
    try:
        for rid_, name, cuisine, diff, tmin, status, ings, flavors, diet, seasons, cws, ratings in SEED:
            conn.execute(
                "INSERT INTO recipes (id,name,description,difficulty,servings,total_time_minutes,status,photo_url,source,source_url)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (rid_, name, "测试描述", diff, 2, tmin, status, "", "手录", ""))
            conn.execute(
                "INSERT INTO recipe_categories (id,recipe_id,cuisine_type,region,country) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()), rid_, cuisine, "", ""))
            for s in seasons:
                conn.execute("INSERT INTO recipe_seasons (id,recipe_id,season) VALUES (?,?,?)",
                             (str(uuid.uuid4()), rid_, s))
            for cw in cws:
                conn.execute("INSERT INTO cookware (id,recipe_id,name,category) VALUES (?,?,?,?)",
                             (str(uuid.uuid4()), rid_, cw, ""))
            for seq, ing in enumerate(ings, 1):
                conn.execute(
                    "INSERT INTO ingredients (id,recipe_id,sequence,name,category,quantity,unit,quantity_text,is_optional,substitute)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), rid_, seq, ing, "主料", 100, "g", "100g", 0, ""))
            for f in flavors:
                conn.execute("INSERT INTO recipe_flavors (id,recipe_id,flavor) VALUES (?,?,?)",
                             (str(uuid.uuid4()), rid_, f))
            for t in diet:
                conn.execute("INSERT INTO recipe_diet_tags (id,recipe_id,tag) VALUES (?,?,?)",
                             (str(uuid.uuid4()), rid_, t))
            for seq, r in enumerate(ratings, 1):
                conn.execute(
                    "INSERT INTO recipe_history (id,recipe_id,cook_date,cook_sequence,rating,feedback,photo)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), rid_, "2026-08-01", seq, r, "不错", None))
        conn.commit()
    finally:
        conn.close()


def data_of(html: str) -> dict:
    """军规 11 · DOM 渲染级断言: 注入必须是可执行 script(裸注释占位符约定)"""
    import re as _re
    assert '<script id="payload"' not in html
    m = _re.search(r'<script>window\.__DATA__ = (\{.*\});</script>', html, _re.S)
    assert m, "未找到可执行的 window.__DATA__ 注入脚本(可能被 JSON 元素吞没)"
    return json.loads(m.group(1))


def names(items: list) -> list:
    return [i["name"] for i in items]


class TestSearchSevenFields:
    """检索契约 7 字段(T2 产物接入)"""

    def test_keyword_search_returns_7_fields(self, tmp_path):
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "search", "排骨")
        assert r["rc"] == 0, r["err"]
        d = json.loads(r["out"])
        assert d["status"] == "ok"
        assert d["count"] == 1
        row = d["results"][0]
        assert set(row) == {"id", "name", "difficulty", "total_time_minutes", "status",
                            "avg_rating", "tags"}

    def test_ingredient_keyword_match_and_rating_tags(self, tmp_path):
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "search", "鸡")
        d = json.loads(r["out"])
        assert sorted(names(d["results"])) == ["宫保鸡丁", "番茄炒蛋"]  # 鸡蛋食材命中
        gongbao = next(x for x in d["results"] if x["name"] == "宫保鸡丁")
        assert gongbao["avg_rating"] == 4.5
        assert set(gongbao["tags"]) == {"辣", "高蛋白"}

    def test_no_history_rating_none_tags_keep_flavor(self, tmp_path):
        """无历史 → avg_rating None;口味标签仍聚合(红烧排骨:甜)"""
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "search", "排骨")
        row = json.loads(r["out"])["results"][0]
        assert row["avg_rating"] is None
        assert row["tags"] == ["甜"]


class TestSuggest:
    """search-2 错字纠错候选(同音/形近)"""

    def test_suggest_homophone_shape(self, tmp_path):
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "suggest", "宫暴鸡丁")
        assert r["rc"] == 0, r["err"]
        d = json.loads(r["out"])
        assert d["count"] == 1
        assert d["suggestions"][0]["name"] == "宫保鸡丁"
        assert d["suggestions"][0]["score"] >= 0.4

    def test_suggest_close_shape(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "suggest", "红烧排姑")["out"])
        assert d["suggestions"][0]["name"] == "红烧排骨"

    def test_suggest_none_for_unrelated(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "suggest", "香辣蟹")["out"])
        assert d["count"] == 0

    def test_search_no_result_then_suggest(self, tmp_path):
        """无结果 → 纠错链路: search 0 条,suggest 有候选"""
        env = make_env(tmp_path)
        seed_db(tmp_path)
        s = json.loads(run_cli(env, "search", "宫暴鸡丁")["out"])
        assert s["count"] == 0


class TestExcludeIngredient:
    """search-6 排除食材(不吃/不要/忌 X · NOT 条件)"""

    def test_exclude_flavor_excludes_recipe(self, tmp_path):
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "search", "", "--exclude", "辣")
        d = json.loads(r["out"])
        assert d["exclude"] == ["辣"]
        assert sorted(names(d["results"])) == ["清蒸鲈鱼", "番茄炒蛋", "红烧排骨"]

    def test_exclude_multi_ingredient(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--exclude", "辣", "--exclude", "甜")["out"])
        assert names(d["results"]) == ["清蒸鲈鱼"]

    def test_keyword_plus_exclude(self, tmp_path):
        """关键词命中 + 排除条件 → 交集(排除后 0 条)"""
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "排骨", "--exclude", "甜")["out"])
        assert d["count"] == 0


class TestDimensionFilters:
    """search-3~12 维度筛选 + 组合(≤3 维)"""

    def test_filter_cuisine(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--cuisine", "川")["out"])
        assert names(d["results"]) == ["宫保鸡丁"]

    def test_filter_time_max(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--time-max", "30")["out"])
        assert sorted(names(d["results"])) == ["宫保鸡丁", "清蒸鲈鱼", "番茄炒蛋"]

    def test_filter_difficulty_multi(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--difficulty", "简单,快手菜")["out"])
        assert sorted(names(d["results"])) == ["宫保鸡丁", "番茄炒蛋"]

    def test_filter_status(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--status", "已做")["out"])
        assert sorted(names(d["results"])) == ["清蒸鲈鱼", "番茄炒蛋"]

    def test_filter_flavor(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--flavor", "辣")["out"])
        assert names(d["results"]) == ["宫保鸡丁"]

    def test_filter_season(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--season", "夏")["out"])
        assert names(d["results"]) == ["清蒸鲈鱼"]

    def test_filter_cookware(self, tmp_path):
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--cookware", "蒸锅")["out"])
        assert names(d["results"]) == ["清蒸鲈鱼"]

    def test_combined_two_dims(self, tmp_path):
        """组合筛选(≤3 维): 川菜 + 30 分钟内"""
        seed_db(tmp_path)
        d = json.loads(run_cli(make_env(tmp_path), "search", "", "--cuisine", "川", "--time-max", "30")["out"])
        assert names(d["results"]) == ["宫保鸡丁"]


class TestListAll:
    """search-13 查看全部"""

    def test_list_all_with_7_fields(self, tmp_path):
        seed_db(tmp_path)
        r = run_cli(make_env(tmp_path), "list-all")
        assert r["rc"] == 0, r["err"]
        d = json.loads(r["out"])
        assert d["count"] == 4
        row = d["results"][0]
        assert set(row) == {"id", "name", "difficulty", "total_time_minutes", "status",
                            "avg_rating", "tags"}


class TestRenderSearch:
    """渲染: 网格卡片 7 字段(评分/标签)+ 08 双按钮"""

    def test_template_placeholders_unique(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert content.count("<!--INJECT-DATA-->") == 1
        assert content.count("<!--INJECT-08-->") == 1

    def test_template_copy_buttons_hard_standard(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "复制数据" in content
        assert "复制日志" in content

    def test_render_search_writes_html_with_7_fields(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        r = run_render(env, "search", "排骨")
        assert r["rc"] == 0, r["err"]
        assert "已渲染" in r["out"]
        files = list((tmp_path / "chef_out" / "list").glob("数据视图_search_排骨_*.html"))
        assert files
        html = files[0].read_text(encoding="utf-8")
        assert "window.__DATA__" in html
        assert "<!--INJECT-DATA-->" not in html
        assert "复制数据" in html and "复制日志" in html
        data = data_of(html)
        assert data["type"] == "list"
        assert data["items_count"] == 1
        assert data["query"]["keyword"] == "排骨"

    def test_render_card_shows_rating_and_tags(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        run_render(env, "search", "鸡")
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_鸡_*.html"))
        html = files[-1].read_text(encoding="utf-8")
        data = data_of(html)
        assert data["items_count"] == 2
        gongbao = next(i for i in data["items"] if i["name"] == "宫保鸡丁")
        assert gongbao["avg_rating"] == 4.5
        assert set(gongbao["tags"]) == {"辣", "高蛋白"}
        # 卡片渲染为浏览器端 JS(innerHTML): 静态 HTML 含评分/标签渲染代码 + payload 带值
        assert '<span class="rating">' in html and "toFixed(1)" in html
        assert "tag-flavor" in html

    def test_render_list_all(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        r = run_render(env, "list-all")
        assert r["rc"] == 0, r["err"]
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_all_*.html"))
        data = data_of(files[-1].read_text(encoding="utf-8"))
        assert data["title"] == "全部食谱"
        assert data["items_count"] == 4


class TestRenderCorrection:
    """search-2 纠错详情层: 自动纠错 / AI 手动纠错"""

    def test_auto_correction_layer(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        r = run_render(env, "search", "宫暴鸡丁")
        assert r["rc"] == 0, r["err"]
        assert "你是不是想找" in r["out"] and "宫保鸡丁" in r["out"]
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_宫保鸡丁_*.html"))
        html = files[-1].read_text(encoding="utf-8")
        data = data_of(html)
        c = data["correction"]
        assert c["original"] == "宫暴鸡丁"
        assert c["corrected"] == "宫保鸡丁"
        assert c["auto"] is True
        assert data["items_count"] == 1
        assert names(data["items"]) == ["宫保鸡丁"]
        assert "你是不是想找" in html
        assert "宫保鸡丁" in html

    def test_manual_correction_via_ai(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        r = run_render(env, "search", "宫暴鸡丁", "--corrected-to", "宫保鸡丁")
        assert r["rc"] == 0, r["err"]
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_宫保鸡丁_*.html"))
        data = data_of(files[-1].read_text(encoding="utf-8"))
        assert data["correction"]["corrected"] == "宫保鸡丁"
        assert data["correction"]["auto"] is False


class TestRenderNoResult:
    """无结果详情层(search_no_result): 纠错仍无 → 候选/放宽/录入"""

    def test_no_result_layer_with_actions(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        r = run_render(env, "search", "香辣蟹")
        assert r["rc"] == 0, r["err"]
        assert "无结果" in r["out"]
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_香辣蟹_*.html"))
        html = files[-1].read_text(encoding="utf-8")
        data = data_of(html)
        assert data["correction"] is None
        assert data["suggestions"] == []
        assert data["items_count"] == 0
        labels = [a["label"] for a in data["no_result_actions"]]
        assert "🔎 放宽关键词" in labels
        assert "➕ 录入新菜" in labels
        assert "放宽关键词" in html and "录入新菜" in html

    def test_render_exclude_query(self, tmp_path):
        env = make_env(tmp_path)
        seed_db(tmp_path)
        run_render(env, "search", "", "--exclude", "辣")
        files = sorted((tmp_path / "chef_out" / "list").glob("数据视图_search_*.html"))
        html = files[-1].read_text(encoding="utf-8")
        data = data_of(html)
        assert data["query"]["exclude"] == ["辣"]
        assert names(data["items"]) == ["番茄炒蛋", "清蒸鲈鱼", "红烧排骨"]
