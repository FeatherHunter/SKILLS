"""
测试: 采购域 T9 已有vs需买详情层(联动居家管家 · G6)

覆盖:
- --stock-json: 库存按名精确匹配并入清单(已有项灰勾 + 双量标注 + 摘要已有 N 项)
- --stock-check 无数据/无匹配: 不打勾 + 顶部淡提示(unavailable)
- 不核对: 无提示无灰勾
- --stock-file: 从文件读库存
- 坏 JSON: 降级报错(不裸 traceback)
- 进度只统计需买项(分组分母排除已有项 · 模板 JS 逻辑断言)
"""
import os
import sys
import json
import sqlite3
import subprocess
import re as _re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent / "scripts"
RENDER = SCRIPT_DIR / "shopping_render.py"
INIT_CLI = SCRIPT_DIR / "开始使用" / "cli.py"
TEMPLATE = SCRIPT_DIR.parent / "templates" / "shopping_view.html"

RENDERED_ENVELOPE_KEYS = ("data",)


def make_env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    env["CHEF_OUTPUT_DIR"] = str(tmp_path / "chef_out")
    return env


def seed_recipe(tmp_path: Path) -> dict:
    """建 17 表库 + 1 道菜 2 食材(鸡蛋×3个 / 猪肉×200g)"""
    env = make_env(tmp_path)
    r = subprocess.run(
        [sys.executable, str(INIT_CLI), "init"],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    assert r.returncode == 0, r.stderr
    db = tmp_path / "chef_data.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            "INSERT INTO recipes (id,name,description,difficulty,servings,total_time_minutes,"
            "status,photo_url,source,source_url) "
            "VALUES ('r-t9','测试采购菜','','简单',2,15,'未做','','','')"
        )
        conn.execute(
            "INSERT INTO ingredients (id,recipe_id,sequence,name,category,quantity,unit,"
            "quantity_text,is_optional,substitute) VALUES "
            "('i-t9-1','r-t9',1,'鸡蛋','蛋类',3,'个','3个',0,''),"
            "('i-t9-2','r-t9',2,'猪肉','肉类',200,'g','200g',0,'')"
        )
        conn.commit()
    finally:
        conn.close()
    return env


def run_render(env: dict, *args) -> dict:
    r = subprocess.run(
        [sys.executable, str(RENDER), "render", "测试采购菜", *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    return {"rc": r.returncode, "out": r.stdout, "err": r.stderr}


def last_output_html(env: dict) -> str:
    out_dir = Path(env["CHEF_OUTPUT_DIR"]) / "shopping"
    files = sorted(out_dir.glob("采购清单_*.html"))
    assert files, "采购清单 HTML 未输出"
    return files[-1].read_text(encoding="utf-8")


def parse_data(html: str) -> dict:
    """军规 11 · DOM 渲染级断言:注入必须是可执行的 script(裸注释占位符约定)"""
    assert '<script id="payload"' not in html
    m = _re.search(r'<script>window\.__DATA__ = (\{.*\});</script>', html, _re.S)
    assert m, "未找到可执行的 window.__DATA__ 注入脚本"
    return json.loads(m.group(1))["data"]


STOCK_EGG = json.dumps({"items": [{"name": "鸡蛋", "qty": 2, "unit": "盒"}]}, ensure_ascii=False)


class TestStockAttach:
    """纯函数:库存按名精确匹配并入清单(AI 已完成同名/同义匹配)"""

    def test_attach_matched(self):
        sys.path.insert(0, str(SCRIPT_DIR))
        import shopping_render
        data = {"ingredients_by_category": {"蛋类": [{"name": "鸡蛋", "quantity": 3, "unit": "个"}]}}
        stock = {"checked": True, "items": [{"name": "鸡蛋", "qty": 2, "unit": "盒"}]}
        out = shopping_render.attach_stock(data, stock)
        assert out["ingredients_by_category"]["蛋类"][0]["stock"] == {"qty": 2, "unit": "盒"}
        assert out["stock"] == {"checked": True, "unavailable": False, "count": 1}

    def test_attach_no_match_unavailable(self):
        sys.path.insert(0, str(SCRIPT_DIR))
        import shopping_render
        data = {"ingredients_by_category": {"蛋类": [{"name": "鸡蛋"}]}}
        stock = {"checked": True, "items": [{"name": "酱油", "qty": 1}]}
        out = shopping_render.attach_stock(data, stock)
        assert out["stock"] == {"checked": True, "unavailable": True, "count": 0}
        assert "stock" not in data["ingredients_by_category"]["蛋类"][0]

    def test_attach_empty_no_hint_when_not_checked(self):
        sys.path.insert(0, str(SCRIPT_DIR))
        import shopping_render
        data = {"ingredients_by_category": {"蛋类": [{"name": "鸡蛋"}]}}
        out = shopping_render.attach_stock(data, {"checked": False, "items": []})
        assert out["stock"] == {"checked": False, "unavailable": False, "count": 0}


class TestRenderStock:
    """渲染:已有项灰勾 + 双量标注 + 摘要已有 N 项(数据层 + 模板 JS 逻辑层断言)"""

    def test_stock_json_annotates_items(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run_render(env, "--stock-check", "--stock-json", STOCK_EGG)
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["stock"] == {"checked": True, "unavailable": False, "count": 1}
        egg = data["ingredients_by_category"]["蛋类"][0]
        assert egg["stock"] == {"qty": 2, "unit": "盒"}
        pork = data["ingredients_by_category"]["肉类"][0]
        assert "stock" not in pork
        # 模板 JS:已有项灰勾(has-stock)+ 双量标注 pill(已有 N盒)+ 摘要已有 N 项
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "has-stock" in content
        assert "function stockPill(stock)" in content
        assert "已有 '" in content
        assert 'id="sum-stock"' in content
        # 淡提示不触发(unavailable=false → JS 保持 hidden)
        assert 'id="stock-hint" hidden' in content

    def test_stock_file_equivalent(self, tmp_path):
        env = seed_recipe(tmp_path)
        stock_file = tmp_path / "stock.json"
        stock_file.write_text(STOCK_EGG, encoding="utf-8")
        r = run_render(env, "--stock-check", "--stock-file", str(stock_file))
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["stock"]["count"] == 1
        assert data["ingredients_by_category"]["蛋类"][0]["stock"] == {"qty": 2, "unit": "盒"}

    def test_stock_without_unit_marks_bare(self, tmp_path):
        env = seed_recipe(tmp_path)
        stock = json.dumps({"items": [{"name": "猪肉", "qty": 1}]}, ensure_ascii=False)
        r = run_render(env, "--stock-check", "--stock-json", stock)
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["ingredients_by_category"]["肉类"][0]["stock"] == {"qty": 1, "unit": ""}


class TestStockDegradation:
    """降级:核对但无数据/无匹配 → 不打勾 + 顶部淡提示"""

    def test_check_without_data_shows_hint(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run_render(env, "--stock-check")
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["stock"]["checked"] is True
        assert data["stock"]["unavailable"] is True
        assert data["stock"]["count"] == 0
        # 食材均无 stock 标注(不打勾)
        for cat, ings in data["ingredients_by_category"].items():
            for ing in ings:
                assert "stock" not in ing
        # 顶部淡提示元素 + 文案(JS 将移除 hidden 显示)
        assert 'id="stock-hint"' in html
        assert "未核对库存(居家管家暂无数据)" in html

    def test_no_match_shows_hint(self, tmp_path):
        env = seed_recipe(tmp_path)
        stock = json.dumps({"items": [{"name": "酱油", "qty": 5}]}, ensure_ascii=False)
        r = run_render(env, "--stock-check", "--stock-json", stock)
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["stock"]["unavailable"] is True
        for cat, ings in data["ingredients_by_category"].items():
            for ing in ings:
                assert "stock" not in ing

    def test_no_check_flag_no_hint_no_mark(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run_render(env)
        assert r["rc"] == 0, r["err"]
        html = last_output_html(env)
        data = parse_data(html)
        assert data["stock"] == {"checked": False, "unavailable": False, "count": 0}
        # 提示元素默认 hidden(JS 不触发显示)
        assert 'id="stock-hint" hidden' in html

    def test_bad_stock_json_reports_error(self, tmp_path):
        env = seed_recipe(tmp_path)
        r = run_render(env, "--stock-check", "--stock-json", "{bad json")
        assert "库存 JSON 解析失败" in r["err"]
        assert "Traceback" not in r["err"]


class TestTemplateProgressLogic:
    """进度只统计需买项(G6 4b):分母不含已有项 · 模板 JS 逻辑断言"""

    def test_group_denominator_excludes_stock(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "items.filter(it => !(it.stock && it.stock.qty != null))" in content

    def test_update_progress_excludes_stock(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "if (!it.classList.contains('has-stock'))" in content

    def test_stock_items_not_toggleable(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "if (itemEl.classList.contains('has-stock')) return;" in content

    def test_template_has_hint_slot_and_stock_card(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert 'class="stock-hint" id="stock-hint"' in content
        assert 'id="sum-stock"' in content
        assert "el.hidden = !(DATA && DATA.stock && DATA.stock.unavailable)" in content

    def test_copy_text_has_stock_mark(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "已有 ' + DATA.stock.count + ' 项(居家管家库存)" in content
        assert "stockMark" in content
