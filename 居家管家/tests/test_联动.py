# test_联动.py - SM9 联动功能域 · 场景端到端测试(G6: fixture 模拟库 + CLI 级)
#
# 隔离: 每个测试会话用临时 SKILLS_DB_PATH(tmp dir),不触碰生产库。
# 方式: subprocess 调 scripts/link_center.py,env 注入 SKILLS_DB_PATH;
#       种子数据用 sqlite3 直连临时库写入(测试侧允许,运行侧禁止直连)。
"""SM9 联动功能域测试"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

_PY = "python3" if sys.platform != "win32" else "python"
if not shutil.which(_PY):
    _PY = "python"

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
LINK_CLI = [_PY, "-m", "联动.cli"]
HOME_CLI = [_PY, "home_manager.py"]


@pytest.fixture()
def link_db(tmp_path):
    """临时库: 建 schema + 种子分类/物品;yield (env, tmp_dir)"""
    env = {**os.environ, "SKILLS_DB_PATH": str(tmp_path)}
    r = subprocess.run([*HOME_CLI, "init"], capture_output=True, text=True,
                       cwd=str(SCRIPTS_DIR), env=env, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"init 失败: {r.stdout} {r.stderr}"

    db = tmp_path / "home.db"
    assert db.exists(), f"home.db 未生成: {tmp_path}"

    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (id, name, parent_id) VALUES (1, '食物与饮品', NULL)")
    cur.execute("INSERT INTO categories (id, name, parent_id) VALUES (2, '工具与器材', NULL)")
    cur.execute("""INSERT INTO items (id, name, category, category_id, purchase_price, photo)
                   VALUES (101, '牛奶', '食物与饮品', 1, 5.9, '')""")
    cur.execute("""INSERT INTO items (id, name, category, category_id, purchase_price, photo)
                   VALUES (102, '螺丝刀', '工具与器材', 2, NULL, '')""")
    cur.execute("""INSERT INTO items (id, name, category, category_id, purchase_price, photo)
                   VALUES (103, '无价格物品', '食物与饮品', 1, NULL, '')""")
    cur.execute("INSERT INTO item_locations (item_id, location, quantity) VALUES (101, '冰箱', 2)")
    cur.execute("INSERT INTO item_locations (item_id, location, quantity) VALUES (102, '工具箱', 1)")
    cur.execute("INSERT INTO item_locations (item_id, location, quantity) VALUES (103, '橱柜', 1)")
    conn.commit()
    conn.close()
    return env, tmp_path


def _run(env, args):
    return subprocess.run([*LINK_CLI, *args], capture_output=True, text=True,
                          cwd=str(SCRIPTS_DIR), env=env, encoding="utf-8", errors="replace")


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ── SM9-1 联动总览 ────────────────────────────────────────────────────────────


def test_overview_ok(link_db):
    env, tmp = link_db
    out = tmp / "overview.html"
    r = _run(env, ["sm9-overview", "--output", str(out)])
    assert r.returncode == 0, f"stderr={r.stderr}"
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "联动功能总览" in html
    assert "食品联动" in html and "价格联动" in html and "健身计划联动" in html
    assert "复制触发 prompt" in html  # 唯一按钮(2026-08-10: 前往业务场景已删)
    assert "记住上次选择" not in html  # 联动偏好已删(2026-08-10)
    assert "--INJECT-DATA--" not in html  # 数据已注入


def test_overview_no_prefs_section(link_db):
    env, tmp = link_db
    r = _run(env, ["sm9-overview", "--output", str(tmp / "o2.html")])
    assert r.returncode == 0
    html = (tmp / "o2.html").read_text(encoding="utf-8")
    assert "联动偏好" not in html  # 偏好区已删
    assert "每次询问" not in html and "关闭" not in html.split("复制触发 prompt")[0]


# ── SM9-2 食品联动 ────────────────────────────────────────────────────────────


def test_food_log_ok(link_db):
    env, tmp = link_db
    out = tmp / "food.html"
    r = _run(env, ["sm9-food", "--item-id", "101", "--action", "log", "--output", str(out)])
    assert r.returncode == 0, f"stderr={r.stderr}"
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "牛奶" in html
    assert "记到今日饮食" in html and "查热量" in html
    assert "卡路里" in html
    assert "食品判定" in html


def test_food_non_food_error(link_db):
    env, tmp = link_db
    out = tmp / "food_err.html"
    r = _run(env, ["sm9-food", "--item-id", "102", "--output", str(out)])
    assert r.returncode == 1  # 业务失败 = 非零退出(与 物品域 emit_error 同约),错误回执 HTML 正常生成
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "不是食品/饮品" in html


def test_food_missing_item(link_db):
    env, tmp = link_db
    out = tmp / "food_miss.html"
    r = _run(env, ["sm9-food", "--item-id", "99999", "--output", str(out)])
    assert r.returncode == 1
    html = out.read_text(encoding="utf-8")
    assert "未找到" in html


# ── SM9-3 价格联动 ────────────────────────────────────────────────────────────


def test_price_expense_ok(link_db):
    env, tmp = link_db
    out = tmp / "price.html"
    r = _run(env, ["sm9-price", "--item-id", "101", "--direction", "expense", "--output", str(out)])
    assert r.returncode == 0, f"stderr={r.stderr}"
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "牛奶" in html
    assert "¥11.8" in html  # 5.9 × 2 件
    assert "餐饮" in html  # 分类映射 食物与饮品 → 餐饮
    assert "记支出" in html and "记收入" in html


def test_price_income_ok(link_db):
    env, tmp = link_db
    out = tmp / "price_in.html"
    r = _run(env, ["sm9-price", "--item-id", "101", "--direction", "income", "--output", str(out)])
    assert r.returncode == 0
    html = out.read_text(encoding="utf-8")
    assert "退货退款" in html


def test_price_no_price_error(link_db):
    env, tmp = link_db
    out = tmp / "price_err.html"
    r = _run(env, ["sm9-price", "--item-id", "103", "--output", str(out)])
    assert r.returncode == 1
    html = out.read_text(encoding="utf-8")
    assert "没有价格信息" in html


# ── 联动偏好已删(2026-08-10)──────────────────────────────────────────────────
# sm9-prefs 命令 / link_prefs.json / PREF 三态 已整体移除;
# 顺路建议改无条件生成,由 test_entry_reminders_* 覆盖。

# ── 双入口顺路建议(1-1/1-2 回执后 · 规格硬要求)────────────────────────────────


def test_entry_reminders_food_and_price(link_db):
    """食品+有价格物品: 无条件给出卡路里 + 记账两条建议(2026-08-10 删偏好后)"""
    import sys as _sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["SKILLS_DB_PATH"] = str(link_db[1])
    from 联动.ops import build_entry_reminders
    item = {
        "id": 1, "name": "牛奶", "category": "食物与饮品",
        "purchase_price": 5.9,
        "locations": [{"quantity": 2, "location_status": "在家"}],
        "photo_base64": None,
    }
    rems = build_entry_reminders(item)
    keys = [r["key"] for r in rems]
    assert "food" in keys and "price" in keys
    food_r = next(r for r in rems if r["key"] == "food")
    assert "记一餐" in food_r["prompt"] and "牛奶" in food_r["prompt"]
    price_r = next(r for r in rems if r["key"] == "price")
    assert "饼干记账" in price_r["prompt"] and "¥11.8" in price_r["prompt"]


def test_entry_reminders_food_only(link_db):
    """食品但无价格: 只给卡路里建议,不给记账"""
    import sys as _sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["SKILLS_DB_PATH"] = str(link_db[1])
    from 联动.ops import build_entry_reminders
    item = {"id": 3, "name": "苹果", "category": "食物与饮品",
            "purchase_price": None,
            "locations": [{"quantity": 5, "location_status": "在家"}],
            "photo_base64": None}
    rems = build_entry_reminders(item)
    keys = [r["key"] for r in rems]
    assert "food" in keys and "price" not in keys


def test_entry_reminders_non_food_no_price(link_db):
    """非食品 + 无价格物品 → 顺路建议为空"""
    import sys as _sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["SKILLS_DB_PATH"] = str(link_db[1])
    from 联动.ops import build_entry_reminders
    item = {"id": 2, "name": "螺丝刀", "category": "工具与器材",
            "purchase_price": None,
            "locations": [{"quantity": 1, "location_status": "在家"}],
            "photo_base64": None}
    assert build_entry_reminders(item) == []


# ── 跨技能契约对齐(票面 #114: 与对应技能实施协商 + SM3 契约统一)───────────────


def test_fitness_prompt_sm3_contract_alignment(link_db):
    """健身联动 prompt 必须与 SM3-4 权威枚举一致(行程类型: 健身)"""
    import sys as _sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["SKILLS_DB_PATH"] = str(link_db[1])
    from 联动.ops import build_fitness_prompt
    p = build_fitness_prompt()
    assert "行程类型: 健身" in p  # SM3-4 枚举 = 健身/出差/旅行/超市/游泳/爬山/滑雪/自定义
    assert "健身联动" not in p.split("行程类型:")[1].split("\n")[0]  # 不是枚举外值
    assert "带物品" in p  # SM3-4 唤醒词


def test_catalog_cross_skill_trigger_words(link_db):
    """契约表 data_flow 必须指向对方技能真实触发词(卡路里/饼干记账 SKILL.md 实测)"""
    import sys as _sys
    sys.path.insert(0, str(SCRIPTS_DIR))
    os.environ["SKILLS_DB_PATH"] = str(link_db[1])
    from 联动.ops import LINK_CATALOG
    entries = {e["id"]: e for e in LINK_CATALOG}
    assert "记一餐" in entries["food"]["data_flow"] or "记一餐" in LINK_CATALOG[0]["data_flow"]
    assert "查食品" in LINK_CATALOG[0]["data_flow"]
    assert "记支出" in LINK_CATALOG[1]["data_flow"]
    assert "看今天练什么" in entries["fitness"]["data_flow"] or "看本周计划" in entries["fitness"]["data_flow"]
