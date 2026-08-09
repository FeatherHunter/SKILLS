"""SM4 统计总览域测试(G6: fixture 模拟库,不碰生产库)

fixture 库模式:
  - 每个测试用独立临时库(SKILLS_DB_PATH → tmp_path)
  - reload home_manager.db 让模块级 DB_PATH 指向临时库
  - teardown 恢复(monkeypatch 撤销 env + 再 reload)
种子: 顶级分类 食物与饮品/衣物与穿戴 + 二级;测试物品 TEST_ 前缀。
"""
import importlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """独立临时库 fixture(种子分类;每测试独立,不碰生产库)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import home_manager.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    conn = db_mod.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (1, NULL, '食物与饮品')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (2, NULL, '衣物与穿戴')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (3, 1, '零食')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (4, 2, '上装')")
    conn.commit()
    yield conn
    conn.close()
    monkeypatch.undo()
    importlib.reload(db_mod)


def _seed_item(conn, iid, name, cat_id, location, price=None, status="在家",
               created_days_ago=3, last_acc_days_ago=None, exp_days=None, qty=1):
    """直接 SQL 种子一个物品(绕过 add_item 的标签硬约束)"""
    # 用 UTC 日期对齐 SQL 的 date('now')/julianday('now') 口径(本地凌晨会 ±1 漂移)
    today = datetime.now(timezone.utc).date()
    created = (today - timedelta(days=created_days_ago)).isoformat() + " 09:00:00"
    last_acc = ((today - timedelta(days=last_acc_days_ago)).isoformat() + " 09:00:00"
                if last_acc_days_ago is not None else None)
    exp = ((today + timedelta(days=exp_days)).isoformat() if exp_days is not None else None)
    c = conn.cursor()
    c.execute(
        "INSERT INTO items (id, name, category_id, purchase_price, created_at, updated_at, "
        "last_accessed_at, access_count) VALUES (?,?,?,?,?,?,?,?)",
        (iid, name, cat_id, price, created, today.isoformat() + " 09:00:00", last_acc, 0))
    c.execute(
        "INSERT INTO item_locations (item_id, location, quantity, location_status, expiration_date) "
        "VALUES (?,?,?,?,?)",
        (iid, location, qty, status, exp))
    conn.commit()


@pytest.fixture
def seeded(tmp_db):
    """标准种子: 3 活跃 + 1 废弃(用于多场景共享断言)"""
    _seed_item(tmp_db, 1, "TEST_牛奶", 3, "厨房/冰箱", price=12.5,
               created_days_ago=3, last_acc_days_ago=2, exp_days=5)
    _seed_item(tmp_db, 2, "TEST_旧毛衣", 4, "卧室/衣柜", price=None,
               created_days_ago=200)
    _seed_item(tmp_db, 3, "TEST_废弃物", 3, "客厅/茶几", price=99.0,
               status="已废弃", created_days_ago=10)
    _seed_item(tmp_db, 4, "TEST_健身垫", 2, "客厅/角落", price=50.0,
               created_days_ago=300, last_acc_days_ago=100)
    return tmp_db


# ═══════════ SM4-1 物品总览 ═══════════

def test_overview_structure(seeded):
    from stats.overview import overview_payload
    d = overview_payload(seeded)
    assert d["summary"]["metrics"][0]["value"] == "4 件"      # 物品总数(含废弃)
    assert d["summary"]["metrics"][1]["value"] == "¥161.50"   # 总价值
    assert d["summary"]["metrics"][2]["value"] == "75.0%"     # 覆盖率 3/4
    assert d["flags"]["empty"] is False
    assert d["flags"]["low_coverage"] is False
    # 状态分布
    st = {s["name"]: s["count"] for s in d["statuses"]}
    assert st.get("在家") == 3 and st.get("已废弃") == 1
    # 分类分布(排除废弃 → 衣物 1 件)
    cats = {c["name"]: c["count"] for c in d["categories"]}
    assert cats.get("衣物与穿戴") == 1
    # 位置分布: 顶级位置
    locs = {l["name"]: l["count"] for l in d["locations"]}
    assert locs.get("客厅") == 2 and locs.get("厨房") == 1
    # 归属: 全默认 → 隐藏
    assert d["owners"] == []
    assert d["flags"]["show_owners"] is False
    # 价值 TOP: 排除废弃(99 元废弃物不出现),降序
    assert [x["name"] for x in d["top_value"]] == ["TEST_健身垫", "TEST_牛奶"]
    # 高频 TOP 区块(查高频并入)
    assert len(d["frequent_top"]) == 3
    # 趋势
    buckets = d["trend"]["buckets"]
    assert len(buckets) == 4
    near7 = buckets[0]
    assert near7["added"] == 1 and near7["added_items"][0]["name"] == "TEST_牛奶"
    assert d["trend"]["note"]


def test_overview_empty(tmp_db):
    from stats.overview import overview_payload
    d = overview_payload(tmp_db)
    assert d["flags"]["empty"] is True
    assert d["summary"]["metrics"][2]["value"] == "0.0%"


def test_overview_low_coverage(tmp_db):
    from stats.overview import overview_payload
    _seed_item(tmp_db, 10, "TEST_A", 3, "厨房/冰箱", price=None, created_days_ago=1)
    _seed_item(tmp_db, 11, "TEST_B", 4, "卧室/衣柜", price=5.0, created_days_ago=1)
    _seed_item(tmp_db, 12, "TEST_C", 3, "厨房/冰箱", price=None, created_days_ago=1)
    d = overview_payload(tmp_db)
    assert d["flags"]["low_coverage"] is True  # 1/3 = 33% < 50%


def test_overview_owners_shown(tmp_db):
    from stats.overview import overview_payload
    _seed_item(tmp_db, 20, "TEST_妈妈的", 3, "厨房/冰箱", price=1.0, created_days_ago=1)
    c = tmp_db.cursor()
    c.execute("UPDATE items SET owner='妈妈' WHERE id=20")
    _seed_item(tmp_db, 21, "TEST_宝宝的", 4, "卧室/衣柜", price=1.0, created_days_ago=1)
    c.execute("UPDATE items SET owner='宝宝' WHERE id=21")
    tmp_db.commit()
    d = overview_payload(tmp_db)
    assert d["flags"]["show_owners"] is True
    names = {o["name"]: o["count"] for o in d["owners"]}
    assert names.get("妈妈") == 1 and names.get("宝宝") == 1


# ═══════════ SM4-2 闲置检测 ═══════════

def test_idle_structure_and_sources(seeded):
    from stats.idle import idle_payload
    d = idle_payload(seeded, days=90)
    by_name = {x["name"]: x for x in d["items"]}
    assert set(by_name.keys()) == {"TEST_旧毛衣", "TEST_健身垫"}
    assert by_name["TEST_旧毛衣"]["days_idle"] == 200
    assert by_name["TEST_旧毛衣"]["source"] == "估算"
    assert by_name["TEST_健身垫"]["source"] == "访问记录"
    assert d["suggestion"]
    assert d["threshold"] == 90
    assert d["allowed"] == [90, 180, 365]
    assert "TEST_废弃物" not in by_name  # 排除废弃


def test_idle_threshold_filter(seeded):
    from stats.idle import idle_payload
    d = idle_payload(seeded, days=180)
    assert {x["name"] for x in d["items"]} == {"TEST_旧毛衣"}  # 健身垫 100 天 < 180


def test_idle_invalid_threshold(seeded):
    from stats.idle import idle_payload
    with pytest.raises(ValueError):
        idle_payload(seeded, days=45)


def test_idle_empty(tmp_db):
    from stats.idle import idle_payload
    _seed_item(tmp_db, 30, "TEST_新物品", 3, "厨房/冰箱", created_days_ago=1)
    d = idle_payload(tmp_db, days=90)
    assert d["empty"] is True
    assert "衣橱状态良好" in d["suggestion"]


def test_idle_category_filter(seeded):
    from stats.idle import idle_payload
    # 顶级分类 2(衣物与穿戴)展开到子分类 → 旧毛衣(上装)+ 健身垫都算
    d = idle_payload(seeded, days=90, category_id=2)
    assert {x["name"] for x in d["items"]} == {"TEST_旧毛衣", "TEST_健身垫"}
    # 二级分类 4(上装)→ 只命中旧毛衣
    d2 = idle_payload(seeded, days=90, category_id=4)
    assert {x["name"] for x in d2["items"]} == {"TEST_旧毛衣"}


# ═══════════ SM4-3 过期检查 ═══════════

def test_expiring_structure(seeded):
    from stats.expiring import expiring_payload
    d = expiring_payload(seeded, days=30)
    items = {x["name"]: x for x in d["items"]}
    assert "TEST_牛奶" in items
    assert items["TEST_牛奶"]["days_left"] == 5
    assert items["TEST_牛奶"]["severity"] == "warn"
    metrics = {m["label"]: m for m in d["summary"]["metrics"]}
    assert metrics["已过期"]["value"] == "0 件"
    assert metrics["30天内"]["value"] == "1 件"
    assert d["days"] == 30
    assert d["allowed"] == [7, 30, 90]


def test_expiring_days_validation(seeded):
    from stats.expiring import expiring_payload
    with pytest.raises(ValueError):
        expiring_payload(seeded, days=14)


def test_expiring_expired_only(tmp_db):
    from stats.expiring import expiring_payload
    _seed_item(tmp_db, 40, "TEST_过期品", 3, "厨房/冰箱", exp_days=-10)
    d = expiring_payload(tmp_db, days=30, expired_only=True)
    assert {x["name"] for x in d["items"]} == {"TEST_过期品"}
    assert d["items"][0]["severity"] == "danger"


def test_expiring_empty(tmp_db):
    from stats.expiring import expiring_payload
    _seed_item(tmp_db, 41, "TEST_无期限", 3, "厨房/冰箱")
    d = expiring_payload(tmp_db, days=30)
    assert d["empty"] is True


# ═══════════ SM4-4 盘点统计 ═══════════

def test_inventory_stat_empty_when_no_table(seeded):
    from stats.inventory_stat import inventory_stat_payload
    d = inventory_stat_payload(seeded)
    assert d["has_data"] is False
    assert "首次盘点" in d["suggestion"]
    assert d["review_action"]["label"]


def test_inventory_stat_with_d1_table(seeded):
    """模拟 D1 建表后: 盘点记录数据正确呈现"""
    from stats.inventory_stat import inventory_stat_payload
    c = seeded.cursor()
    c.execute(
        "CREATE TABLE inventory_records (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "scope TEXT, occurred_at TEXT, 缺N INTEGER DEFAULT 0, 多N INTEGER DEFAULT 0, "
        "异N INTEGER DEFAULT 0, status TEXT)")
    c.execute("INSERT INTO inventory_records (scope, occurred_at, 缺N, 多N, 异N, status) "
              "VALUES ('卧室', '2026-07-01 10:00:00', 2, 1, 0, 'done')")
    c.execute("INSERT INTO inventory_records (scope, occurred_at, 缺N, 多N, 异N, status) "
              "VALUES ('客厅', '2026-08-01 10:00:00', 1, 0, 1, 'done')")
    seeded.commit()
    d = inventory_stat_payload(seeded)
    assert d["has_data"] is True
    assert len(d["history"]) == 2
    assert d["history"][0]["scope"] == "客厅"
    assert d["total_missing"] == 3
    assert "卧室" in d["suggestion"]  # 最久未盘: 卧室
    assert d["summary"]["metrics"][0]["value"] == "2 次"


# ═══════════ 端到端 CLI(每场景 ≥ 1) ═══════════

def _run_cli(tmp_path, *args, data_dir=None):
    env = dict(os.environ)
    env["SKILLS_DB_PATH"] = str(tmp_path)
    if data_dir:
        env["SKILLS_DATA_DIR"] = str(data_dir)
    return subprocess.run(
        [sys.executable, "home_manager.py", *args],
        capture_output=True, text=True, timeout=60,
        cwd=str(SCRIPTS_DIR), env=env, encoding="utf-8", errors="replace",
    )


@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    """CLI 端到端环境: 独立临时库 + 种子"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import home_manager.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    conn = db_mod.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (1, NULL, '食物与饮品')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (2, NULL, '衣物与穿戴')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (3, 1, '零食')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (4, 2, '上装')")
    conn.commit()
    _seed_item(conn, 50, "TEST_牛奶", 3, "厨房/冰箱", price=12.5,
               created_days_ago=3, exp_days=5)
    _seed_item(conn, 51, "TEST_旧毛衣", 4, "卧室/衣柜", price=None, created_days_ago=200)
    conn.close()
    monkeypatch.undo()
    importlib.reload(db_mod)
    yield tmp_path
    monkeypatch.undo()
    importlib.reload(db_mod)


def test_cli_overview_e2e(cli_env, tmp_path):
    out = tmp_path / "overview.html"
    r = _run_cli(cli_env, "stats", "--type", "overview", "--output", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "物品总览" in html
    assert "价格覆盖率" in html


def test_cli_idle_e2e(cli_env, tmp_path):
    out = tmp_path / "idle.html"
    r = _run_cli(cli_env, "stats", "--type", "idle", "--days", "90", "--output", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "闲置物品检测" in html
    assert "估算" in html  # 旧毛衣估算标注


def test_cli_expiring_e2e(cli_env, tmp_path):
    out = tmp_path / "expiring.html"
    r = _run_cli(cli_env, "stats", "--type", "expiring", "--days", "30", "--output", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "过期检查与预告" in html


def test_cli_inventory_stat_e2e(cli_env, tmp_path):
    out = tmp_path / "invstat.html"
    r = _run_cli(cli_env, "stats", "--type", "inventory-stat", "--output", str(out))
    assert r.returncode == 0, r.stderr
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "盘点统计" in html
    assert "首次盘点" in html


# ═══════════ 对抗式: 非法参数优雅降级(08 规范 §6,无裸 traceback) ═══════════

def test_cli_idle_invalid_threshold_graceful(cli_env, tmp_path):
    """闲置阈值非法(如 7 天)→ 结构化 error JSON,不裸 traceback(08 §6)"""
    out = tmp_path / "idle_bad.html"
    r = _run_cli(cli_env, "stats", "--type", "idle", "--days", "7", "--output", str(out))
    assert r.returncode == 1
    assert "Traceback" not in r.stdout and "Traceback" not in r.stderr
    data = json.loads(r.stdout)
    assert data["status"] == "error"
    assert "90/180/365" in data["message"]


def test_cli_expiring_invalid_days_graceful(cli_env, tmp_path):
    """预告天数非法(如 14 天)→ 结构化 error JSON,不裸 traceback(08 §6)"""
    out = tmp_path / "exp_bad.html"
    r = _run_cli(cli_env, "stats", "--type", "expiring", "--days", "14", "--output", str(out))
    assert r.returncode == 1
    assert "Traceback" not in r.stdout and "Traceback" not in r.stderr
    data = json.loads(r.stdout)
    assert data["status"] == "error"
    assert "7/30/90" in data["message"]


def test_cli_html_type_requires_output(cli_env):
    """HTML 类型无 --output → 明确提示,非「未知统计类型」误导"""
    r = _run_cli(cli_env, "stats", "--type", "idle")
    assert r.returncode == 1
    assert "Traceback" not in r.stdout and "Traceback" not in r.stderr
    assert "--output" in r.stdout
