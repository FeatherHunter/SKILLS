# -*- coding: utf-8 -*-
"""SM3 穿搭出行域 · 数据层 fixture 测试(T4)

- slot_of / 规则表: 纯函数断言
- 引擎/载荷: 用内存临时库(自建分类树) → 完全确定性,不受真实库噪音干扰
- 结构契约: 对真实库(conn)做一次宽松断言
"""
import sqlite3

import pytest

from home_manager.outfit_ops import (
    slot_of, outfit_payload_v2, wardrobe_payload, season_payload,
    trip_payload_v2, trip_plan_payload, TRIP_RULES,
)

# ── 内存临时库 ───────────────────────────────────────

def _scratch_db():
    """建最小衣物分类树 + 空表(与 db.py DDL 对齐)。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER,
            name TEXT NOT NULL, description TEXT, sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            category TEXT, owner TEXT DEFAULT '使用者', purchase_price REAL,
            remark TEXT, photo TEXT, access_count INTEGER DEFAULT 0,
            last_accessed_at TIMESTAMP, category_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE item_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            tag TEXT NOT NULL, UNIQUE(item_id, tag));
        CREATE TABLE item_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, item_id INTEGER NOT NULL,
            location TEXT NOT NULL, quantity INTEGER NOT NULL DEFAULT 1,
            reason TEXT, location_status TEXT DEFAULT '在家',
            purchase_date TEXT, expiration_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    tree = [
        ("衣物与穿戴", None), ("上装", 1), ("T恤", 2), ("外套", 2),
        ("下装", 1), ("休闲裤", 5), ("鞋类", 1), ("运动鞋", 7),
        ("帽饰配件", 1), ("帽子", 9), ("围巾", 9), ("内衣睡衣", 1), ("睡衣", 12),
    ]
    for name, parent in tree:
        cur.execute("INSERT INTO categories (name, parent_id) VALUES (?, ?)",
                    (name, parent))
    conn.commit()
    return conn


def _path_to_id(conn, path):
    """按路径拿 category id,如 衣物与穿戴/上装/T恤 → 3。"""
    cur = conn.cursor()
    pid = None
    for name in path.split("/"):
        cur.execute("SELECT id FROM categories WHERE name=? AND "
                    "((? IS NULL AND parent_id IS NULL) OR parent_id=?)",
                    (name, pid, pid))
        pid = cur.fetchone()["id"]
    return pid


def _add(conn, name, path, tags, access_count=0, last_accessed_at=None,
         status="在家"):
    cid = _path_to_id(conn, path)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO items (name, category_id, access_count, last_accessed_at,
                           created_at, updated_at)
        VALUES (?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
    """, (name, cid, access_count, last_accessed_at))
    iid = cur.lastrowid
    for t in tags:
        cur.execute("INSERT INTO item_tags (item_id, tag) VALUES (?, ?)", (iid, t))
    cur.execute("""
        INSERT INTO item_locations (item_id, location, quantity, location_status,
                                    created_at, updated_at)
        VALUES (?, '测试/衣柜', 1, ?, datetime('now','localtime'),
                datetime('now','localtime'))
    """, (iid, status))
    conn.commit()
    return iid


@pytest.fixture
def db():
    return _scratch_db()


@pytest.fixture
def full_closet(db):
    """一套完整衣物(每槽位 ≥1 件, 内搭 x2, T恤A 有采纳历史)。"""
    import datetime
    recent = (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat(" ")
    ids = {
        "T恤A": _add(db, "TEST_T恤A", "衣物与穿戴/上装/T恤", ["内搭", "夏季"],
                     access_count=2, last_accessed_at=recent),
        "T恤B": _add(db, "TEST_T恤B", "衣物与穿戴/上装/T恤", ["内搭"]),
        "外套": _add(db, "TEST_西装外套", "衣物与穿戴/上装/外套", ["外套", "上班"]),
        "裤": _add(db, "TEST_休闲裤", "衣物与穿戴/下装/休闲裤", ["夏季"]),
        "鞋": _add(db, "TEST_运动鞋", "衣物与穿戴/鞋类/运动鞋", []),
        "帽": _add(db, "TEST_棒球帽", "衣物与穿戴/帽饰配件/帽子", ["帽子"]),
        "围巾": _add(db, "TEST_围巾", "衣物与穿戴/帽饰配件/围巾", []),
    }
    return ids


# ── 槽位判定(纯函数) ─────────────────────────────────

def test_slot_of_rule():
    assert slot_of("衣物与穿戴/鞋类/运动鞋") == "shoes"
    assert slot_of("衣物与穿戴/下装/牛仔裤") == "bottom"
    assert slot_of("衣物与穿戴/帽饰配件/帽子") == "hat"
    assert slot_of("衣物与穿戴/帽饰配件/围巾") == "acce"
    assert slot_of("衣物与穿戴/帽饰配件/眼镜") == "acce"
    assert slot_of("衣物与穿戴/上装/外套") == "outer"
    assert slot_of("衣物与穿戴/上装/T恤") == "inner"
    assert slot_of("衣物与穿戴/上装/卫衣") == "outer"
    assert slot_of("衣物与穿戴/上装/衬衫") == "inner"
    assert slot_of("衣物与穿戴/内衣睡衣/睡衣") is None
    assert slot_of("衣物与穿戴/袜类/短袜") is None
    assert slot_of("衣物与穿戴/床上用品/被芯") is None


def test_slot_of_tag_role_overrides_subcat():
    assert slot_of("衣物与穿戴/上装/T恤", ["外套"]) == "outer"
    assert slot_of("衣物与穿戴/上装/外套", ["内搭"]) == "inner"
    assert slot_of("衣物与穿戴/帽饰配件/围巾", ["帽子"]) == "hat"


# ── 穿搭推荐引擎 ─────────────────────────────────────

def test_outfit_engine_sets(db, full_closet):
    payload = outfit_payload_v2(db, temperature=28, occasion="上班", limit=5)
    assert payload["sets"], "应有组合"
    first = payload["sets"][0]["slots"]
    assert first["inner"]["name"] == "TEST_T恤A"   # 近期优先: A(有访问) > B
    assert first["outer"]["name"] == "TEST_西装外套"
    assert first["bottom"] and first["shoes"]
    assert first["hat"]["name"] == "TEST_棒球帽"
    assert payload["gap"] == []
    assert payload["summary"]["metrics"]


def test_outfit_prefers_recent(db, full_closet):
    import datetime
    recent = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(" ")
    _add(db, "TEST_T恤C", "衣物与穿戴/上装/T恤", ["内搭"], access_count=3,
         last_accessed_at=recent)
    payload = outfit_payload_v2(db, temperature=28, limit=3)
    first = payload["sets"][0]["slots"]["inner"]
    assert first["name"] == "TEST_T恤C", "最近穿过 → 隐式偏好优先"


def test_outfit_temperature_filter(db, full_closet):
    _add(db, "TEST_冬外套", "衣物与穿戴/上装/外套", ["外套", "冬季"])
    warm = outfit_payload_v2(db, temperature=28, limit=5)
    warm_outer = {s["slots"]["outer"]["name"] for s in warm["sets"]}
    assert "TEST_冬外套" not in warm_outer, "28°C 排除冬季标签"
    cold = outfit_payload_v2(db, temperature=10, limit=5)
    cold_outer = {s["slots"]["outer"]["name"] for s in cold["sets"]}
    assert "TEST_冬外套" in cold_outer


def test_outfit_gap_when_missing(db, full_closet):
    cur = db.cursor()
    cur.execute("UPDATE item_locations SET location_status='旅游中' WHERE item_id=?",
                (full_closet["鞋"],))
    db.commit()
    payload = outfit_payload_v2(db, temperature=28)
    assert "鞋" in payload["gap"]


def test_outfit_suit_group_together(db, full_closet):
    cur = db.cursor()
    cur.execute("INSERT INTO item_tags (item_id, tag) VALUES (?, ?)",
                (full_closet["T恤A"], "成套:通勤A"))
    cur.execute("INSERT INTO item_tags (item_id, tag) VALUES (?, ?)",
                (full_closet["外套"], "成套:通勤A"))
    db.commit()
    payload = outfit_payload_v2(db, temperature=28, limit=3)
    found = False
    for s in payload["sets"]:
        ids = {it["id"] for it in s["slots"].values()}
        if full_closet["T恤A"] in ids:
            assert full_closet["外套"] in ids, "成套件必须一起出现"
            found = True
    assert found


def test_outfit_sets_rotation_no_duplicate(db, full_closet):
    payload = outfit_payload_v2(db, temperature=28, limit=5)
    for s in payload["sets"]:
        ids = [it["id"] for it in s["slots"].values()]
        assert len(ids) == len(set(ids)), "一套内不允许重复物品"


# ── 衣橱分析 ─────────────────────────────────────────

def test_wardrobe_dormant_and_estimate(db, full_closet):
    payload = wardrobe_payload(db)
    dormant = {d["name"]: d for d in payload["dormant"]}
    assert "TEST_T恤B" in dormant            # access_count=0 → 闲置
    assert dormant["TEST_T恤B"]["estimated"] is True   # 无最后访问 → 估算标注
    assert "TEST_T恤A" not in dormant        # 有采纳历史 → 非闲置
    dist = {d["label"]: d["count"] for d in payload["distribution"]}
    assert dist["内搭"] == 2 and dist["鞋"] == 1
    assert payload["advice"]


def test_wardrobe_recent_not_dormant(db, full_closet):
    import datetime
    recent = (datetime.datetime.now() - datetime.timedelta(hours=1)).isoformat(" ")
    cur = db.cursor()
    cur.execute("UPDATE items SET access_count=5, last_accessed_at=? WHERE id=?",
                (recent, full_closet["T恤B"]))
    db.commit()
    payload = wardrobe_payload(db)
    names = {d["name"] for d in payload["dormant"]}
    assert "TEST_T恤B" not in names


def test_wardrobe_ratio_advice(db, full_closet):
    payload = wardrobe_payload(db)
    assert "上装偏多" in payload["advice"] or "均衡" in payload["advice"]


# ── 换季收纳 ─────────────────────────────────────────

def test_season_payload_matches(db, full_closet):
    payload = season_payload(db, season="夏季", action="收纳")
    names = {it["name"] for it in payload["items"]}
    assert "TEST_T恤A" in names
    assert "TEST_西装外套" not in names
    assert payload["season"] == "夏季"


# ── 出行清单 ─────────────────────────────────────────

def test_trip_rules_business(db, full_closet):
    payload = trip_payload_v2(db, trip_type="出差", days=3)
    assert len(payload["items"]) >= 5
    assert payload["unregistered"], "规则物品未录入 → 全部引导录入"


def test_trip_gym_two_layer(db, full_closet):
    payload = trip_payload_v2(db, trip_type="健身", days=1,
                              plan_type="力量", exercises=["深蹲", "卧推"])
    names = [it["name"] for it in payload["items"]]
    assert any("腰带" in n for n in names), "练腿动作 → 深蹲腰带(护具第二层)"
    assert any("健身包" in n for n in names), "第一层基础物品"


def test_trip_gym_matches_db_items(db, full_closet):
    payload = trip_payload_v2(db, trip_type="健身", days=1,
                              plan_type="有氧", exercises=[])
    names = [it["name"] for it in payload["items"]]
    assert "TEST_运动鞋" in names, "有氧 → 跑步鞋 → 库内匹配(带照片)"


def test_trip_rule_table_structure():
    for key in ("出差", "旅行", "超市", "游泳", "爬山", "滑雪"):
        assert callable(TRIP_RULES[key]), f"{key} 规则必须是可调用(days→清单)"


# ── 旅行穿搭计划 ─────────────────────────────────────

def test_trip_plan_conflict_and_luggage(db, full_closet):
    payload = trip_plan_payload(db, days=3)
    assert len(payload["day_plans"]) == 3
    conflicts = {c["slot"]: c for c in payload["conflicts"]}
    assert "内搭" in conflicts, "2 件内搭 3 天 → 冲突提示"
    used_names = {it["name"] for it in payload["luggage"]}
    assert len(payload["luggage"]) == len(used_names), "行李汇总去重"


def test_trip_plan_min_reuse(db, full_closet):
    payload = trip_plan_payload(db, days=2)
    first = payload["day_plans"][0]["slots"]
    second = payload["day_plans"][1]["slots"]
    assert first["inner"]["id"] != second["inner"]["id"], "2 件内搭 2 天 → 不重复穿"


# ── 真实库结构契约(宽松) ─────────────────────────────

def test_real_db_payload_structure(conn):
    payload = outfit_payload_v2(conn, temperature=28)
    assert isinstance(payload["sets"], list)
    assert payload["total"] >= 0
    assert isinstance(payload["gap"], list)
    w = wardrobe_payload(conn)
    assert isinstance(w["dormant"], list)
    assert w["advice"]
